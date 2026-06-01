from __future__ import annotations

from typing import Any


def known_face_status(config: dict[str, Any]) -> list[dict[str, Any]]:
    faces = config.get("known_faces", []) if isinstance(config.get("known_faces"), list) else []
    return [{"name": str(item.get("name") or ""), "enabled": bool(item.get("enabled", True))} for item in faces if isinstance(item, dict) and item.get("name")]
