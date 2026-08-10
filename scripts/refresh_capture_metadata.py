from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "knowledge/evidence/capture_index.yaml"
MANIFEST_PATH = ROOT / "assets/evidence/captures/manifest.json"


def main() -> None:
    index = yaml.safe_load(INDEX_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    group_by_capture: dict[str, dict] = {}
    for group in index["capture_groups"]:
        for capture_id in group["capture_ids"]:
            if capture_id in group_by_capture:
                raise ValueError(f"capture appears in multiple groups: {capture_id}")
            group_by_capture[capture_id] = group

    captures = manifest["captures"]
    manifest_ids = {capture["id"] for capture in captures}
    indexed_ids = set(group_by_capture)
    if manifest_ids != indexed_ids:
        raise ValueError(
            f"capture index mismatch: missing={sorted(manifest_ids - indexed_ids)} "
            f"unknown={sorted(indexed_ids - manifest_ids)}"
        )

    for capture in captures:
        group = group_by_capture[capture["id"]]
        kind = "source" if "-source." in capture["file"] else "deck"
        capture.update(
            {
                "source_key": group["id"],
                "source": group["source"],
                "capture_kind": kind,
                "deck_location": group["deck_location"],
                "card_status": group["card_status"],
                "heading": group["title_ko"],
                "caption": group["note"],
                "context": (
                    f"{group['source']} | {group['deck_location']} | "
                    f"{group['card_status']} | {kind} capture"
                ),
            }
        )

    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"updated {len(captures)} capture records")


if __name__ == "__main__":
    main()
