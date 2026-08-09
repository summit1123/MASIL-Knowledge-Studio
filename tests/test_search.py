from __future__ import annotations

from masil_mcp.service import KnowledgeService


def test_korean_ngram_handles_compound_query() -> None:
    service = KnowledgeService()
    result = service.search("생활권밖주행", top_k=6, scope="current")
    assert result["results"]
    assert any("생활권" in item["snippet"] for item in result["results"])


def test_literature_search_returns_caveat() -> None:
    service = KnowledgeService()
    result = service.get_evidence("looking but not seeing 71%", top_k=4)
    combined = "\n".join(item["body"] for item in result["literature"])
    assert "71%" in combined
    assert "전체 사고" in combined


def test_open_items_do_not_turn_into_facts() -> None:
    service = KnowledgeService()
    result = service.list_open_items("공정성")
    assert result["items"]
    assert any(item["status"] in {"unresolved", "pilot_hypothesis", "candidate_parameter", "planned_not_implemented"} for item in result["items"])

