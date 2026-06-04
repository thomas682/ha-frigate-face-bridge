from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FACE_REGISTRY_FILE = Path(os.environ.get("FACE_REGISTRY_FILE", "/data/faces.json"))


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sanitize_name(value: Any) -> str:
    name = re.sub(r"\s+", " ", str(value or "").strip())
    if not name or len(name) > 80:
        raise ValueError("name must be 1-80 characters")
    if not re.fullmatch(r"[A-Za-z0-9_. -]+", name):
        raise ValueError("name contains invalid characters")
    return name


def _load_registry_file() -> list[dict[str, Any]]:
    try:
        if not FACE_REGISTRY_FILE.exists():
            return []
        data = json.loads(FACE_REGISTRY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, dict):
        faces = data.get("faces")
    else:
        faces = data
    return deepcopy(faces) if isinstance(faces, list) else []


def _write_registry_file(faces: list[dict[str, Any]]) -> None:
    FACE_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    FACE_REGISTRY_FILE.write_text(json.dumps({"faces": faces}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _clean_face(item: dict[str, Any]) -> dict[str, Any] | None:
    try:
        name = _sanitize_name(item.get("name"))
    except ValueError:
        return None
    created_at = str(item.get("created_at") or _timestamp())
    updated_at = str(item.get("updated_at") or created_at)
    return {
        "name": name,
        "enabled": bool(item.get("enabled", True)),
        "image_count": max(0, int(item.get("image_count") or 0)),
        "created_at": created_at,
        "updated_at": updated_at,
    }


def _registry_from_config(config: dict[str, Any]) -> list[dict[str, Any]]:
    faces = config.get("known_faces", []) if isinstance(config.get("known_faces"), list) else []
    cleaned = []
    for item in faces:
        if not isinstance(item, dict):
            continue
        face = _clean_face(item)
        if face:
            cleaned.append(face)
    return cleaned


def load_face_registry(config: dict[str, Any]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for face in _registry_from_config(config):
        merged[face["name"].lower()] = face
    for item in _load_registry_file():
        if not isinstance(item, dict):
            continue
        face = _clean_face(item)
        if face:
            merged[face["name"].lower()] = face
    return sorted(merged.values(), key=lambda item: item["name"].lower())


def save_face(payload: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    name = _sanitize_name(payload.get("name"))
    enabled = bool(payload.get("enabled", True))
    now = _timestamp()
    faces = load_face_registry(config)
    for face in faces:
        if face["name"].lower() == name.lower():
            face["name"] = name
            face["enabled"] = enabled
            face["updated_at"] = now
            _write_registry_file(faces)
            return face

    face = {"name": name, "enabled": enabled, "image_count": 0, "created_at": now, "updated_at": now}
    faces.append(face)
    faces.sort(key=lambda item: item["name"].lower())
    _write_registry_file(faces)
    return face


def set_face_enabled(name: str, enabled: bool, config: dict[str, Any]) -> dict[str, Any]:
    target = _sanitize_name(name)
    faces = load_face_registry(config)
    for face in faces:
        if face["name"].lower() == target.lower():
            face["enabled"] = bool(enabled)
            face["updated_at"] = _timestamp()
            _write_registry_file(faces)
            return face
    raise ValueError("face not found")


def known_face_status(config: dict[str, Any]) -> list[dict[str, Any]]:
    return load_face_registry(config)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_known_faces(value: Any, config: dict[str, Any], min_confidence: float) -> list[str]:
    enabled = {face["name"].lower(): face["name"] for face in load_face_registry(config) if face.get("enabled")}
    if not isinstance(value, list):
        return []
    known: list[str] = []
    for item in value:
        if isinstance(item, str):
            name = item.strip()
            confidence = 1.0
        elif isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            confidence = _as_float(item.get("confidence", item.get("score", 1.0)), 0.0)
        else:
            continue
        registry_name = enabled.get(name.lower())
        if registry_name and confidence >= min_confidence and registry_name not in known:
            known.append(registry_name)
    return known


def parse_face_match_event(payload: str | bytes | dict[str, Any], config: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        data = payload
    else:
        try:
            data = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
            return None
    if not isinstance(data, dict):
        return None

    settings = config.get("face_recognition", {}) if isinstance(config.get("face_recognition"), dict) else {}
    min_confidence = _as_float(settings.get("min_confidence", 0.7), 0.7)
    known = _parse_known_faces(data.get("known_faces", data.get("matches", [])), config, min_confidence)
    unknown_faces = max(0, int(_as_float(data.get("unknown_faces", data.get("unknown_count", 0)), 0)))
    if not known and unknown_faces == 0:
        return None

    camera_config = config.get("camera", {}) if isinstance(config.get("camera"), dict) else {}
    camera = str(data.get("camera") or camera_config.get("name") or "camera").strip() or "camera"
    confidence = _as_float(data.get("confidence", data.get("score", 0.0)), 0.0)
    person_count = max(len(known) + unknown_faces, int(_as_float(data.get("person_count", 0), 0)))
    return {
        "camera": camera,
        "person_count": person_count,
        "known_faces": known,
        "unknown_faces": unknown_faces,
        "timestamp": _timestamp(),
        "source": "external_face_recognition",
        "demo_mode": False,
        "confidence": round(confidence, 3),
        "status": "face match received",
        "face_match_count": len(known),
    }
