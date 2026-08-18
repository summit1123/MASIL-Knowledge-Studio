from __future__ import annotations

import json
import hashlib
import struct
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "knowledge/evidence/capture_index.yaml"
MANIFEST_PATH = ROOT / "assets/evidence/captures/manifest.json"


def jpeg_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if not data.startswith(b"\xff\xd8"):
        raise ValueError(f"not a JPEG file: {path}")
    offset = 2
    sof_markers = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 2 > len(data):
            break
        segment_length = struct.unpack(">H", data[offset:offset + 2])[0]
        if segment_length < 2 or offset + segment_length > len(data):
            break
        if marker in sof_markers:
            if segment_length < 7:
                break
            height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
            return width, height
        offset += segment_length
    raise ValueError(f"JPEG dimensions not found: {path}")


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
        asset_path = ROOT / capture["file"]
        width, height = jpeg_dimensions(asset_path)
        kind = "source" if "-source." in capture["file"] else "deck"
        capture.update(
            {
                "mime_type": "image/jpeg",
                "sha256": hashlib.sha256(asset_path.read_bytes()).hexdigest(),
                "width": width,
                "height": height,
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
