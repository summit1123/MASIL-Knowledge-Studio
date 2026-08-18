from __future__ import annotations

import json

from .service import KnowledgeService


def main() -> None:
    service = KnowledgeService()
    print(json.dumps(service.stats(), ensure_ascii=False, indent=2))

