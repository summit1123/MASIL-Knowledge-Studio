from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class KnowledgeDocument:
    id: str
    title: str
    body: str
    source_path: str
    authority: str
    status: str = "unspecified"
    layer: str = "unspecified"
    topic: str = "general"
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def searchable_text(self) -> str:
        return "\n".join((self.id, self.title, " ".join(self.tags), self.body))

    @property
    def is_current(self) -> bool:
        return self.authority in {"canonical", "deck", "evidence"} and self.status not in {
            "historical",
            "prohibited",
            "banned",
            "archived",
            "superseded",
            "deprecated",
            "legacy_reference",
            "archived_meeting_note",
            "historical_demo",
        }


@dataclass(slots=True)
class SearchHit:
    document: KnowledgeDocument
    score: float
    snippet: str

    def as_dict(self, include_body: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.document.id,
            "title": self.document.title,
            "score": round(self.score, 4),
            "authority": self.document.authority,
            "status": self.document.status,
            "layer": self.document.layer,
            "topic": self.document.topic,
            "source": self.document.source_path,
            "snippet": self.snippet,
        }
        if include_body:
            payload["body"] = self.document.body
        if self.document.metadata:
            payload["metadata"] = self.document.metadata
        return payload


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]
