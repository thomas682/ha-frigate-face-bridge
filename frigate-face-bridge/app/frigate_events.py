from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_frigate_event(payload: str | bytes, config: dict[str, Any]) -> dict[str, Any] | None:
    try:
        data = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    obj = data.get("after") if isinstance(data.get("after"), dict) else data
    if not isinstance(obj, dict):
        return None
    if str(obj.get("label") or "").lower() != "person":
        return None
    if obj.get("false_positive") is True:
        return None

    frigate = config.get("frigate", {}) if isinstance(config.get("frigate"), dict) else {}
    camera_config = config.get("camera", {}) if isinstance(config.get("camera"), dict) else {}
    event_camera = str(obj.get("camera") or "").strip()
    expected_camera = str(frigate.get("camera_name") or "").strip()
    if expected_camera and event_camera and event_camera != expected_camera:
        return None

    event_type = str(data.get("type") or "update").lower()
    active = event_type not in {"end", "deleted"}
    score = obj.get("score", obj.get("top_score", 0.0))
    try:
        confidence = round(float(score), 3)
    except (TypeError, ValueError):
        confidence = 0.0

    box = obj.get("box")
    boxes = [box] if isinstance(box, list) and len(box) == 4 else []
    camera_name = event_camera or str(camera_config.get("name") or "camera")

    return {
        "camera": camera_name,
        "person_count": 1 if active else 0,
        "known_faces": [],
        "unknown_faces": 1 if active else 0,
        "timestamp": _timestamp(),
        "source": "frigate_mqtt",
        "demo_mode": False,
        "confidence": confidence if active else 0.0,
        "boxes": boxes,
        "status": "person detected by Frigate" if active else "person event ended by Frigate",
        "frigate_event_id": obj.get("id"),
        "frigate_event_type": event_type,
    }
