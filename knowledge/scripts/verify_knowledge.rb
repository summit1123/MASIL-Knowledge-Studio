#!/usr/bin/env ruby
# frozen_string_literal: true

require "yaml"
require "psych"
require "json"

ROOT = File.expand_path("../..", __dir__)
Dir.chdir(ROOT)

def abort_check(message)
  warn "FAIL: #{message}"
  exit 1
end

files = Dir["knowledge/**/*.yaml"].sort
objects = {}
files.each do |file|
  duplicate_keys = []
  check_mapping_keys = lambda do |node, path|
    case node
    when Psych::Nodes::Mapping
      seen = {}
      node.children.each_slice(2).with_index do |(key_node, value_node), index|
        key = key_node.respond_to?(:value) ? key_node.value : key_node.to_s
        duplicate_keys << "#{path}/#{key}" if seen.key?(key)
        seen[key] = true
        check_mapping_keys.call(value_node, "#{path}/#{key}")
      end
    when Psych::Nodes::Sequence
      node.children.each_with_index { |child, index| check_mapping_keys.call(child, "#{path}[#{index}]") }
    when Psych::Nodes::Stream, Psych::Nodes::Document
      node.children.each { |child| check_mapping_keys.call(child, path) }
    end
  end
  check_mapping_keys.call(Psych.parse_file(file), "$")
  abort_check("duplicate YAML keys in #{file}: #{duplicate_keys.inspect}") unless duplicate_keys.empty?

  objects[file] = YAML.load_file(file)
  puts "YAML_OK #{file}"
end

ids = Hash.new { |hash, key| hash[key] = [] }
walk_ids = lambda do |value, path, file|
  case value
  when Hash
    ids[value["id"]] << "#{file}:#{path}" if value["id"].is_a?(String)
    value.each { |key, child| walk_ids.call(child, "#{path}/#{key}", file) }
  when Array
    value.each_with_index { |child, index| walk_ids.call(child, "#{path}[#{index}]", file) }
  end
end
objects.each { |file, object| walk_ids.call(object, "$", file) }
duplicates = ids.select { |_id, locations| locations.size > 1 }
puts "DUP_IDS=#{duplicates.size}"
abort_check("duplicate IDs: #{duplicates.inspect}") unless duplicates.empty?

deck = objects.fetch("knowledge/claims/deck_claims.yaml")
deck_claims = deck.fetch("pages", []).flat_map do |page|
  page.fetch("claims", []).map { |claim| claim.merge("_page" => page["page"]) }
end
actual_deck_counts = { "total" => deck_claims.size }
deck_claims.group_by { |claim| claim["status"] }.each do |status, items|
  actual_deck_counts[status] = items.size
end
declared_deck_counts = deck.dig("meta", "claim_counts")
puts "DECK_DECLARED=#{declared_deck_counts}"
puts "DECK_ACTUAL=#{actual_deck_counts}"
abort_check("deck claim count mismatch") unless declared_deck_counts == actual_deck_counts

deck_pages = deck_claims.map { |claim| claim["_page"] }.uniq.sort
puts "DECK_PAGES=#{deck_pages.inspect}"
abort_check("deck page coverage mismatch") unless deck_pages == (1..9).to_a

cards_doc = objects.fetch("knowledge/qa/cards.yaml")
cards = cards_doc.fetch("cards", [])
active_cards = cards.select { |card| card["status"] == "active" }
p0_cards = active_cards.select { |card| card["priority"] == "P0" }
expected_scenarios = (1..15).map { |number| format("P0-%02d", number) }
actual_scenarios = p0_cards.map { |card| card["scenario_id"] }.sort
puts "CARDS_TOTAL=#{cards.size} ACTIVE=#{active_cards.size} P0=#{p0_cards.size}"
puts "P0_SCENARIOS=#{actual_scenarios.inspect}"
abort_check("P0 count mismatch") unless p0_cards.size == cards_doc.dig("meta", "p0_expected_count")
abort_check("P0 sequence mismatch") unless actual_scenarios == expected_scenarios
unless p0_cards.all? { |card| card["role"] == "answer_example" && card["canonical_for_facts"] == false }
  abort_check("P0 role mismatch")
end

file_refs = []
walk_file_refs = lambda do |value, path, source_file|
  case value
  when Hash
    value.each do |key, child|
      file_refs << [source_file, "#{path}/#{key}", child] if key == "file" && child.is_a?(String)
      walk_file_refs.call(child, "#{path}/#{key}", source_file)
    end
  when Array
    value.each_with_index { |child, index| walk_file_refs.call(child, "#{path}[#{index}]", source_file) }
  end
end
objects.each { |file, object| walk_file_refs.call(object, "$", file) }
missing_file_refs = file_refs.reject do |_source, _path, target|
  File.exist?(File.join(ROOT, target.split("#", 2).first))
end
puts "FILE_REFS=#{file_refs.size} MISSING=#{missing_file_refs.size}"
abort_check("missing file refs: #{missing_file_refs.inspect}") unless missing_file_refs.empty?

product = objects.fetch("knowledge/product_model.yaml")
domains = product.fetch("domains", [])
product_claims = domains.flat_map { |domain| domain.fetch("claims", []) }
expected_domains = %w[
  problem_definition
  target_and_fairness
  value_proposition
  data_and_privacy
  zone_formation
  monthly_measurement
  monthly_decision
  care_detection_and_support
  annual_discount_and_pricing
  ai_and_human_roles
  simulation_and_validation
  evidence_and_claim_boundaries
  operations_and_delivery
  business_and_roadmap
  language_and_presentation
]
actual_domains = domains.map { |domain| domain["domain_id"] }
puts "PRODUCT_DOMAINS=#{actual_domains.size} CLAIMS=#{product_claims.size}"
abort_check("product domain coverage mismatch") unless actual_domains == expected_domains
abort_check("declared product domain count mismatch") unless product.dig("meta", "domain_count") == domains.size
abort_check("declared product claim count mismatch") unless product.dig("meta", "claim_count") == product_claims.size

allowed_statuses = product.fetch("status_definitions", {}).keys
unknown_statuses = product_claims.map { |claim| claim["status"] }.uniq - allowed_statuses
abort_check("unknown product statuses: #{unknown_statuses.inspect}") unless unknown_statuses.empty?
invalid_unresolved = product_claims.select do |claim|
  claim["status"] == "unresolved" && claim["answer_authority"] != "none"
end
unless invalid_unresolved.empty?
  abort_check("unresolved claims have answer authority: #{invalid_unresolved.map { |claim| claim["id"] }.inspect}")
end
missing_claim_sources = product_claims.select do |claim|
  claim["answer_authority"] != "none" && (!claim["source_refs"].is_a?(Array) || claim["source_refs"].empty?)
end
unless missing_claim_sources.empty?
  abort_check("answerable claims lack sources: #{missing_claim_sources.map { |claim| claim["id"] }.inspect}")
end
product_status_counts = product_claims.group_by { |claim| claim["status"] }.map do |status, items|
  [status, items.size]
end.to_h
puts "PRODUCT_STATUS_COUNTS=#{product_status_counts.inspect}"

unresolved_claims = product_claims.select { |claim| claim["status"] == "unresolved" }
required_unresolved_fields = %w[current_evidence_status recommended_position_ko validation_needed]
incomplete_unresolved = unresolved_claims.select do |claim|
  required_unresolved_fields.any? { |field| !claim[field].is_a?(String) || claim[field].strip.empty? }
end
unless incomplete_unresolved.empty?
  abort_check("unresolved response contract incomplete: #{incomplete_unresolved.map { |claim| claim["id"] }.inspect}")
end

implementation_contract = {
  "model-monthly-display-precedence" => "current",
  "model-care-persistence-rule" => "current",
  "model-annual-base-discount-mapping" => "current",
  "model-annual-extra-discount-rate" => "candidate_parameter"
}
implementation_contract.each do |id, expected_status|
  claim = product_claims.find { |item| item["id"] == id }
  abort_check("missing implementation contract claim #{id}") unless claim
  unless claim["status"] == expected_status
    abort_check("implementation contract status mismatch for #{id}: #{claim["status"]}")
  end
end

whole_project_gap_ids = %w[
  model-target-disparate-impact
  model-data-jurisdiction-portability
  model-zone-seasonality
  model-governance-drift
  model-ops-review-capacity-cost
  model-ops-customer-rights
  model-ops-liability
  model-business-market-channel
  model-business-competition-moat
  model-business-team-partners
  model-business-pilot-design
  model-business-selection-gaming
]
claims_by_id = product_claims.to_h { |claim| [claim["id"], claim] }
missing_whole_project_gaps = whole_project_gap_ids.reject { |id| claims_by_id.key?(id) }
abort_check("whole-project gaps missing: #{missing_whole_project_gaps.inspect}") unless missing_whole_project_gaps.empty?
invalid_whole_project_gaps = whole_project_gap_ids.select do |id|
  claim = claims_by_id.fetch(id)
  claim["status"] != "unresolved" || claim["answer_authority"] != "none"
end
abort_check("whole-project gaps were promoted to answers: #{invalid_whole_project_gaps.inspect}") unless invalid_whole_project_gaps.empty?

story = objects.fetch("knowledge/presentation_story.yaml")
story_nodes = story.fetch("story_nodes", [])
puts "STORY_NODES=#{story_nodes.size}"
abort_check("story count mismatch") unless story_nodes.size == story.dig("meta", "story_node_count")
unless story_nodes.all? { |node| node["guiding_question_ko"] && node["core_message_ko"] && node["audience_takeaway"] }
  abort_check("story nodes lack question, message, or takeaway")
end

conflict_doc = objects.fetch("knowledge/conflict_map.yaml")
conflicts = conflict_doc.fetch("conflicts", [])
puts "CONFLICTS=#{conflicts.size}"
abort_check("conflict count mismatch") unless conflicts.size == conflict_doc.dig("meta", "conflict_count")
unless conflicts.all? { |conflict| conflict["current_resolution"] && conflict["avoid_as_current"].is_a?(Array) }
  abort_check("conflict entries lack resolution or avoid list")
end

coverage_doc = objects.fetch("knowledge/coverage_matrix.yaml")
coverage_domains = coverage_doc.fetch("domains", [])
coverage_ids = coverage_domains.map { |domain| domain["domain"] }
puts "COVERAGE_DOMAINS=#{coverage_ids.size}"
abort_check("coverage matrix does not match product model") unless coverage_ids == actual_domains
abort_check("coverage domain count mismatch") unless coverage_domains.size == coverage_doc.dig("meta", "domain_count")
coverage_by_id = coverage_domains.to_h { |domain| [domain["domain"], domain["coverage"]] }
product_coverage_by_id = domains.to_h { |domain| [domain["domain_id"], domain["coverage"]] }
abort_check("coverage labels disagree with product model") unless coverage_by_id == product_coverage_by_id
unless coverage_doc.dig("approval_gate", "mcp_implementation_allowed") == true
  abort_check("coverage approval gate must be open")
end

local_ref_values = []
collect_source_refs = lambda do |value|
  case value
  when Hash
    value.each do |key, child|
      if %w[source_refs material_refs historical_material supporting primary gap_evidence_ref].include?(key)
        Array(child).each { |item| local_ref_values << item if item.is_a?(String) }
      end
      collect_source_refs.call(child)
    end
  when Array
    value.each { |child| collect_source_refs.call(child) }
  end
end
[product, story, conflict_doc].each { |object| collect_source_refs.call(object) }
local_paths = local_ref_values.select { |ref| ref.start_with?("knowledge/", "sources/", "IMPLEMENTATION.md") }
missing_local_paths = local_paths.reject do |ref|
  File.exist?(File.join(ROOT, ref.split("#", 2).first))
end
puts "MODEL_LOCAL_REFS=#{local_paths.size} MISSING=#{missing_local_paths.size}"
abort_check("missing model local refs: #{missing_local_paths.inspect}") unless missing_local_paths.empty?

yaml_reference_tokens = Hash.new { |hash, key| hash[key] = [] }
collect_reference_tokens = lambda do |value, file|
  case value
  when Hash
    value.each do |key, child|
      if %w[id key domain_id story_node_id].include?(key) && child.is_a?(String)
        yaml_reference_tokens[file] << child
      end
      collect_reference_tokens.call(child, file)
    end
  when Array
    value.each { |child| collect_reference_tokens.call(child, file) }
  end
end
objects.each do |file, object|
  yaml_reference_tokens[file].concat(object.keys) if object.is_a?(Hash)
  collect_reference_tokens.call(object, file)
end
yaml_fragment_refs = local_ref_values.each_with_object([]) do |ref, refs|
  path, fragment = ref.split("#", 2)
  next unless path && path.end_with?(".yaml") && fragment && !fragment.include?("=")

  refs << [path, fragment, ref]
end
broken_yaml_fragment_refs = yaml_fragment_refs.reject do |path, fragment, _ref|
  yaml_reference_tokens[path].include?(fragment)
end
puts "YAML_FRAGMENT_REFS=#{yaml_fragment_refs.size} BROKEN=#{broken_yaml_fragment_refs.size}"
abort_check("broken YAML fragment refs: #{broken_yaml_fragment_refs.inspect}") unless broken_yaml_fragment_refs.empty?

manifest = objects.fetch("knowledge/mcp_manifest.yaml")
abort_check("MCP implementation gate must be open") unless manifest["mcp_implementation_allowed"] == true
master_origin = manifest.dig("provenance_only", "master_qa_origin")
unless master_origin && master_origin["runtime_retrieval"] == false
  abort_check("Master Q&A URL is not provenance-only")
end
runtime_text = manifest.fetch("runtime_sources", {}).to_s
abort_check("Claude Artifact URL leaked into runtime sources") if runtime_text.include?("claude.ai/code/artifact")

required_includes = %w[
  IMPLEMENTATION.md
  knowledge/product_model.yaml
  knowledge/presentation_story.yaml
  knowledge/conflict_map.yaml
  knowledge/coverage_matrix.yaml
  knowledge/claims/deck_claims.yaml
]
actual_includes = manifest.fetch("include", []).map { |entry| entry["file"] }.compact
missing_includes = required_includes - actual_includes
abort_check("manifest missing model files: #{missing_includes.inspect}") unless missing_includes.empty?

implementation_entry = manifest.fetch("include", []).find { |entry| entry["file"] == "IMPLEMENTATION.md" }
unless implementation_entry && implementation_entry["role"] == "current_working_tree_implementation_audit"
  abort_check("implementation audit manifest entry mismatch")
end

cards_entry = manifest.fetch("include", []).find { |entry| entry["file"] == "knowledge/qa/cards.yaml" }
unless cards_entry && cards_entry["role"] == "answer_example" && cards_entry["canonical_for_facts"] == false
  abort_check("Q&A cards are not non-canonical examples")
end

runtime_excluded = manifest.fetch("runtime_excluded", [])
required_exclusion_terms = ["Master Q&A", "decision history", "archived Q&A", "listed_only"]
missing_exclusion_terms = required_exclusion_terms.reject do |term|
  runtime_excluded.any? { |entry| entry.to_s.include?(term) }
end
abort_check("runtime exclusion contract incomplete: #{missing_exclusion_terms.inspect}") unless missing_exclusion_terms.empty?
abort_check("supporting_include must not exist in the team runtime manifest") if manifest.key?("supporting_include")

registry = objects.fetch("knowledge/evidence/registry.yaml")
capture_origin = registry.dig("meta", "capture_origin")
unless capture_origin && capture_origin["provenance_only"] == true && capture_origin["runtime_retrieval"] == false
  abort_check("evidence capture URL is not provenance-only")
end
presentation_entries = registry.fetch("presentation_entries", [])
old_capture_fields = presentation_entries.select { |entry| entry.key?("capture_available") }
abort_check("ambiguous capture_available fields remain") unless old_capture_fields.empty?
unless presentation_entries.all? do |entry|
  entry["capture_reviewed_in_external_source"] == true && [true, false].include?(entry["local_capture_available"])
end
  abort_check("capture review/local availability fields are incomplete")
end
local_capture_entries = presentation_entries.select { |entry| entry["local_capture_available"] == true }
declared_local_capture_count = registry.dig("meta", "local_capture_asset_count")
capture_manifest_path = registry.dig("meta", "local_capture_manifest")
abort_check("capture manifest missing") unless capture_manifest_path && File.exist?(File.join(ROOT, capture_manifest_path))
capture_manifest = JSON.parse(File.read(File.join(ROOT, capture_manifest_path)))
unless declared_local_capture_count == capture_manifest["capture_count"] &&
       capture_manifest.fetch("captures", []).size == declared_local_capture_count
  abort_check("local capture manifest count mismatch")
end
capture_by_id = capture_manifest.fetch("captures", []).to_h { |capture| [capture["id"], capture] }
missing_capture_assets = capture_manifest.fetch("captures", []).reject do |capture|
  capture["file"].is_a?(String) && File.exist?(File.join(ROOT, capture["file"]))
end
abort_check("missing local capture assets") unless missing_capture_assets.empty?
invalid_capture_links = local_capture_entries.select do |entry|
  !entry["capture_ids"].is_a?(Array) || entry["capture_ids"].empty? || entry["capture_ids"].any? { |id| !capture_by_id.key?(id) }
end
abort_check("invalid presentation capture links") unless invalid_capture_links.empty?
capture_index = objects.fetch("knowledge/evidence/capture_index.yaml")
capture_groups = capture_index.fetch("capture_groups", [])
all_indexed_ids = capture_groups.flat_map { |group| group.fetch("capture_ids", []) }
indexed_id_counts = all_indexed_ids.each_with_object(Hash.new(0)) { |id, counts| counts[id] += 1 }
duplicate_indexed_ids = indexed_id_counts.select { |_id, count| count > 1 }
abort_check("captures appear in multiple index groups: #{duplicate_indexed_ids.inspect}") unless duplicate_indexed_ids.empty?
indexed_ids = all_indexed_ids.uniq
abort_check("capture index is incomplete") unless indexed_ids.sort == capture_by_id.keys.sort
required_capture_metadata = %w[source_key source capture_kind deck_location card_status heading caption context]
incomplete_capture_metadata = capture_manifest.fetch("captures", []).select do |capture|
  required_capture_metadata.any? { |field| !capture[field].is_a?(String) || capture[field].strip.empty? }
end
abort_check("capture metadata is incomplete") unless incomplete_capture_metadata.empty?

presentation_by_key = presentation_entries.to_h { |entry| [entry["key"], entry] }
invalid_group_links = capture_groups.select do |group|
  refs = group.fetch("evidence_refs", [])
  next false if refs.empty?

  refs.any? do |ref|
    entry = presentation_by_key[ref]
    entry.nil? || Array(entry["capture_ids"]).sort != group.fetch("capture_ids", []).sort
  end
end
abort_check("capture groups disagree with literature entries") unless invalid_group_links.empty?

invalid_capture_kinds = presentation_entries.select do |entry|
  deck_ids = Array(entry["deck_capture_ids"])
  source_ids = Array(entry["source_capture_ids"])
  deck_ids.any? { |id| capture_by_id.dig(id, "capture_kind") != "deck" } ||
    source_ids.any? { |id| capture_by_id.dig(id, "capture_kind") != "source" } ||
    (deck_ids + source_ids).sort != Array(entry["capture_ids"]).sort
end
abort_check("deck/source capture classification mismatch") unless invalid_capture_kinds.empty?

active_literature = presentation_entries.select { |entry| entry["citation_tier"] == "stage_citable" }
active_capture_groups = capture_groups.select { |group| group["card_status"] == "active" }
active_group_refs = active_capture_groups.flat_map { |group| group.fetch("evidence_refs", []) }.sort
abort_check("active literature and capture groups disagree") unless active_group_refs == active_literature.map { |entry| entry["key"] }.sort
{
  "qa_only" => "qa_only",
  "listed_only" => "listed_only",
  "banned" => "excluded_banned"
}.each do |tier, group_status|
  entry_keys = presentation_entries.select { |entry| entry["citation_tier"] == tier }.map { |entry| entry["key"] }.sort
  group_refs = capture_groups.select { |group| group["card_status"] == group_status }
                             .flat_map { |group| group.fetch("evidence_refs", []) }.sort
  abort_check("#{tier} literature and capture groups disagree") unless group_refs == entry_keys
end
puts "EVIDENCE_CAPTURES=stage:#{active_literature.size} qa:#{presentation_entries.count { |entry| entry["citation_tier"] == "qa_only" }} listed:#{presentation_entries.count { |entry| entry["citation_tier"] == "listed_only" }} banned:#{presentation_entries.count { |entry| entry["citation_tier"] == "banned" }} local_assets:#{declared_local_capture_count}"

pipeline = manifest.fetch("retrieval_pipeline", [])
expected_stages = %w[current_facts exact_evidence_traversal conflict_resolution response_packet]
actual_stages = pipeline.map { |stage| stage["stage"] }
puts "RETRIEVAL_STAGES=#{actual_stages.inspect}"
abort_check("retrieval pipeline mismatch") unless actual_stages == expected_stages
response_stage = pipeline.find { |stage| stage["stage"] == "response_packet" }
response_fields = response_stage ? response_stage.fetch("fields", []) : []
expected_fields = %w[
  current_conclusion
  answer_facts
  evidence_and_citations
  conflicts_and_avoid_phrases
  plain_wording_material
  exact_evidence_captures
]
abort_check("response packet fields mismatch") unless response_fields == expected_fields

asset_policy = manifest.fetch("asset_policy", {})
unless asset_policy["remote_artifact_runtime_lookup"] == false &&
       asset_policy["text_corpus"] == "local_files_only" &&
       asset_policy["evidence_images"] == "local_assets_only"
  abort_check("local asset policy mismatch")
end
unless manifest.dig("implementation_gate", "status") == "approved_for_server_implementation"
  abort_check("implementation gate status mismatch")
end

snapshot = objects.fetch("knowledge/snapshot.yaml")
unless snapshot.dig("mcp_manifest", "supporting_context_in_default_retrieval") == true &&
       snapshot.dig("mcp_manifest", "supporting_context_can_override_current_canon") == false &&
       snapshot.dig("mcp_manifest", "implementation_allowed") == true
  abort_check("snapshot retrieval and implementation contract mismatch")
end
unless snapshot.dig("implementation_audit", "file") == "IMPLEMENTATION.md" &&
       snapshot.dig("implementation_audit", "observed_state") == "dirty_working_tree"
  abort_check("snapshot implementation audit mismatch")
end
expected_model_anchor_files = {
  "product" => "knowledge/product_model.yaml",
  "story" => "knowledge/presentation_story.yaml",
  "conflicts" => "knowledge/conflict_map.yaml",
  "coverage" => "knowledge/coverage_matrix.yaml"
}
actual_model_anchor_files = snapshot.fetch("model_anchors", {}).map do |name, entry|
  [name, entry["file"]]
end.to_h
abort_check("snapshot model anchors mismatch") unless actual_model_anchor_files == expected_model_anchor_files
# Decision history remains valid repository provenance, but it is deliberately
# absent from the public team runtime and therefore is not a retrieval contract.

approved_sources = snapshot.fetch("approved_sources", [])
missing_approved_sources = approved_sources.reject { |path| File.exist?(File.join(ROOT, path)) }
puts "APPROVED_SUPPORT_SOURCES=#{approved_sources.size} MISSING=#{missing_approved_sources.size}"
abort_check("missing approved support sources: #{missing_approved_sources.inspect}") unless missing_approved_sources.empty?

public_keys = %w[
  approved_position_ko
  direct_answer_ko
  spoken_answer_en
  text_en
  plain_english
  statement_ko
  core_message_ko
]
leak_pattern = /old dashboard|legacy demo|V20 contract|Care is not a grade|Care는 등급이 아니/i
public_leaks = []
walk_public = lambda do |value, path, file, active_public|
  case value
  when Hash
    current_public = active_public ||
                     (value["status"] == "active" && !%w[deep history].include?(value["layer"])) ||
                     (value["status"] == "current" && value["answer_authority"] == "current")
    value.each do |key, child|
      if current_public && public_keys.include?(key) && child.is_a?(String) && child.match?(leak_pattern)
        public_leaks << [file, "#{path}/#{key}", child]
      end
      walk_public.call(child, "#{path}/#{key}", file, current_public)
    end
  when Array
    value.each_with_index do |child, index|
      walk_public.call(child, "#{path}[#{index}]", file, active_public)
    end
  end
end
objects.each { |file, object| walk_public.call(object, "$", file, false) }
puts "PUBLIC_LEAKS=#{public_leaks.size}"
abort_check("public content leaks: #{public_leaks.inspect}") unless public_leaks.empty?

root_docs = %w[README.md INDEX.md REVIEW.md OPEN_ITEMS.md]
stale_patterns = [
  /V20 공식 스탠스/,
  /V20의 두 축 계약/,
  /구 화면은\s*`historical_demo`라고 설명/,
  /최종 대시보드.*이전 데모 요율/,
  /과거.*명시 요청이 없으면 검색하지/,
  /변경 이력.*기본 검색 제외/,
  /외부 Master Q&A.*인증 접근/,
  /최종 제출 덱 9장.*1순위/
]
stale_root_hits = root_docs.flat_map do |file|
  text = File.read(file)
  stale_patterns.map { |pattern| [file, pattern.source] if text.match?(pattern) }.compact
end
puts "STALE_ROOT_HITS=#{stale_root_hits.size}"
abort_check("stale root documentation: #{stale_root_hits.inspect}") unless stale_root_hits.empty?

puts "ALL_CHECKS_PASS"
