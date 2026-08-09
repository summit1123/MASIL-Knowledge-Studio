#!/usr/bin/env ruby
# frozen_string_literal: true

require "yaml"

ROOT = File.expand_path("../..", __dir__)
Dir.chdir(ROOT)

def abort_check(message)
  warn "FAIL: #{message}"
  exit 1
end

files = Dir["knowledge/**/*.yaml"].sort
objects = {}
files.each do |file|
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
claims = deck.fetch("pages", []).flat_map do |page|
  page.fetch("claims", []).map { |claim| claim.merge("_page" => page["page"]) }
end
actual_counts = { "total" => claims.size }
claims.group_by { |claim| claim["status"] }.each do |status, items|
  actual_counts[status] = items.size
end
declared_counts = deck.dig("meta", "claim_counts")
puts "DECK_DECLARED=#{declared_counts}"
puts "DECK_ACTUAL=#{actual_counts}"
abort_check("deck claim count mismatch") unless declared_counts == actual_counts

pages = claims.map { |claim| claim["_page"] }.uniq.sort
puts "DECK_PAGES=#{pages.inspect}"
abort_check("deck page coverage mismatch") unless pages == (1..9).to_a

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
walk_refs = lambda do |value, path, source_file|
  case value
  when Hash
    value.each do |key, child|
      file_refs << [source_file, "#{path}/#{key}", child] if key == "file" && child.is_a?(String)
      walk_refs.call(child, "#{path}/#{key}", source_file)
    end
  when Array
    value.each_with_index { |child, index| walk_refs.call(child, "#{path}[#{index}]", source_file) }
  end
end
objects.each { |file, object| walk_refs.call(object, "$", file) }
missing_refs = file_refs.reject { |_source, _path, target| File.exist?(File.join(ROOT, target)) }
puts "FILE_REFS=#{file_refs.size} MISSING=#{missing_refs.size}"
abort_check("missing file refs: #{missing_refs.inspect}") unless missing_refs.empty?

manifest = objects.fetch("knowledge/mcp_manifest.yaml")
abort_check("team_canon remains in external sources") if manifest.dig("external_sources", "team_canon")
archive = manifest.dig("external_sources", "master_qa_archive")
unless archive && archive["layer"] == "history" && archive["default_retrieval"] == false
  abort_check("Master Q&A archive is not isolated")
end
cards_entry = manifest.fetch("include", []).find { |entry| entry["file"] == "knowledge/qa/cards.yaml" }
unless cards_entry && cards_entry["role"] == "answer_example" && cards_entry["canonical_for_facts"] == false
  abort_check("Q&A cards are not marked as non-canonical examples")
end

snapshot = objects.fetch("knowledge/snapshot.yaml")
unless snapshot.dig("decision_log", "layer") == "history" && snapshot.dig("decision_log", "default_retrieval") == false
  abort_check("decision log is not isolated from default retrieval")
end

public_keys = %w[approved_position_ko direct_answer_ko spoken_answer_en text_en plain_english]
leak_pattern = /old dashboard|legacy demo|V20 contract|Care is not a grade|Care는 등급이 아니/i
public_leaks = []
walk_public = lambda do |value, path, file, active_public|
  case value
  when Hash
    current_public = active_public || (value["status"] == "active" && !%w[deep history].include?(value["layer"]))
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
  /최종 대시보드.*이전 데모 요율/
]
stale_root_hits = root_docs.flat_map do |file|
  text = File.read(file)
  stale_patterns.map { |pattern| [file, pattern.source] if text.match?(pattern) }.compact
end
puts "STALE_ROOT_HITS=#{stale_root_hits.size}"
abort_check("stale root documentation: #{stale_root_hits.inspect}") unless stale_root_hits.empty?

puts "ALL_CHECKS_PASS"
