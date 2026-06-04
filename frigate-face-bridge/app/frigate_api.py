from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _face_name(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list) and value:
        return _face_name(value[0])
    if isinstance(value, dict):
        for key in ("name", "label", "sub_label", "person"):
            name = _face_name(value.get(key))
            if name:
                return name
    return ""


def _known_faces_from_person_events(events: list[dict[str, Any]]) -> list[str]:
    known: list[str] = []
    for item in events:
        for candidate in _as_list(item.get("sub_label")):
            name = _face_name(candidate)
            if name and name.lower() not in {"unknown", "none"} and name not in known:
                known.append(name)
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        for attr in _as_list(data.get("attributes")):
            name = _face_name(attr)
            if name and name.lower() not in {"unknown", "face", "person", "none"} and name not in known:
                known.append(name)
    return known


def _frigate_api_url(config: dict[str, Any]) -> str:
    frigate = config.get("frigate", {}) if isinstance(config.get("frigate"), dict) else {}
    url = str(frigate.get("api_url") or "").strip().rstrip("/")
    if not url:
        return ""
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return ""
    return url


def active_object_count_event(config: dict[str, Any]) -> dict[str, Any] | None:
    frigate = config.get("frigate", {}) if isinstance(config.get("frigate"), dict) else {}
    if not bool(frigate.get("enabled")) or not bool(frigate.get("person_count_enabled", True)):
        return None

    base_url = _frigate_api_url(config)
    if not base_url:
        return None

    camera_config = config.get("camera", {}) if isinstance(config.get("camera"), dict) else {}
    camera = str(frigate.get("camera_name") or camera_config.get("name") or "camera").strip() or "camera"
    labels = ["person", "dog"]
    active_by_label: dict[str, list[dict[str, Any]]] = {label: [] for label in labels}
    for label in labels:
        query = urlencode({"camera": camera, "label": label, "in_progress": "1"})
        req = Request(f"{base_url}/api/events?{query}", headers={"User-Agent": "frigate-face-bridge/0.10"})
        with urlopen(req, timeout=8) as response:
            events = json.loads(response.read(512 * 1024).decode("utf-8"))
        if not isinstance(events, list):
            events = []
        for item in events:
            if not isinstance(item, dict):
                continue
            if item.get("label") != label:
                continue
            if item.get("false_positive") is True:
                continue
            if item.get("end_time") is not None:
                continue
            active_by_label[label].append(item)

    scores = []
    boxes = []
    ids = []
    all_active = [item for events in active_by_label.values() for item in events]
    for item in all_active:
        data = item.get("data") if isinstance(item.get("data"), dict) else {}
        score = _as_float(item.get("top_score", data.get("top_score", data.get("score"))), 0.0)
        if score:
            scores.append(score)
        box = data.get("box") or item.get("box")
        if isinstance(box, list) and len(box) == 4:
            boxes.append(box)
        event_id = item.get("id")
        if event_id:
            ids.append(str(event_id))
    person_count = len(active_by_label["person"])
    dog_count = len(active_by_label["dog"])
    known_faces = _known_faces_from_person_events(active_by_label["person"])
    dog_name = str(frigate.get("dog_name") or "Maja").strip() or "Maja"
    recognized_entities = list(known_faces)
    if dog_count and dog_name not in recognized_entities:
        recognized_entities.append(dog_name)

    return {
        "camera": camera,
        "person_count": person_count,
        "dog_count": dog_count,
        "maja_present": dog_count > 0,
        "known_faces": known_faces,
        "unknown_faces": max(person_count - len(known_faces), 0),
        "recognized_entities": recognized_entities,
        "object_counts": {"person": person_count, "dog": dog_count},
        "timestamp": _timestamp(),
        "source": "frigate_active_objects",
        "demo_mode": False,
        "confidence": round(max(scores), 3) if scores else 0.0,
        "boxes": boxes,
        "status": "active Frigate object count",
        "frigate_active_event_ids": ids,
    }


def active_person_count_event(config: dict[str, Any]) -> dict[str, Any] | None:
    return active_object_count_event(config)
