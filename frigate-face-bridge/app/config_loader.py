from __future__ import annotations

import json
import logging
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import yaml

LOG = logging.getLogger("frigate_face_bridge.config")

APP_DIR = Path(__file__).resolve().parent
ADDON_CONFIG_FILE = Path(os.environ.get("ADDON_CONFIG_FILE", APP_DIR / "addon_config.yaml"))
OPTIONS_FILE = Path(os.environ.get("OPTIONS_FILE", "/data/options.json"))
CAMERA_FIELDS = {"name", "host", "rtsp_url", "snapshot_url", "detect_width", "detect_height", "detect_fps"}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def redact_url(value: str) -> str:
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        if parts.username or parts.password:
            host = parts.hostname or ""
            if parts.port:
                host = f"{host}:{parts.port}"
            return urlunsplit((parts.scheme, f"***:***@{host}", parts.path, parts.query, parts.fragment))
    except Exception:
        pass
    return re.sub(r"//[^/@\s]+@", "//***:***@", value)


def redact_secret(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= 4:
        return "***"
    return f"{text[:2]}***{text[-2:]}"


def safe_config(config: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(config)
    mqtt = out.get("mqtt") if isinstance(out.get("mqtt"), dict) else {}
    if "password" in mqtt:
        mqtt["password"] = redact_secret(mqtt.get("password"))
    camera = out.get("camera") if isinstance(out.get("camera"), dict) else {}
    if "rtsp_url" in camera:
        camera["rtsp_url"] = redact_url(str(camera.get("rtsp_url") or ""))
    if "snapshot_url" in camera:
        camera["snapshot_url"] = redact_url(str(camera.get("snapshot_url") or ""))
    return out


def _defaults_from_addon_config() -> dict[str, Any]:
    try:
        raw = yaml.safe_load(ADDON_CONFIG_FILE.read_text(encoding="utf-8")) or {}
        options = raw.get("options") if isinstance(raw, dict) else {}
        if isinstance(options, dict):
            return options
    except FileNotFoundError:
        LOG.warning("add-on metadata file not found: %s", ADDON_CONFIG_FILE)
    except Exception as exc:
        LOG.warning("could not read add-on defaults: %s", exc)
    return {
        "demo_mode": True,
        "log_level": "info",
        "event_interval_seconds": 10,
        "mqtt": {"enabled": False, "host": "core-mosquitto", "port": 1883, "username": "", "password": "", "topic_prefix": "ha/frigate_face_bridge"},
        "camera": {"name": "garage_g3_flex", "host": "192.168.2.241", "rtsp_url": "", "snapshot_url": "", "detect_width": 640, "detect_height": 360, "detect_fps": 5},
        "known_faces": [{"name": "Thomas", "enabled": True}, {"name": "Birgit", "enabled": True}, {"name": "Marie", "enabled": True}],
    }


def _load_options() -> dict[str, Any]:
    try:
        if not OPTIONS_FILE.exists():
            return {}
        data = json.loads(OPTIONS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            LOG.warning("options file must contain a JSON object; using defaults")
            return {}
        return data
    except json.JSONDecodeError as exc:
        LOG.error("invalid JSON in %s: %s", OPTIONS_FILE, exc)
    except Exception as exc:
        LOG.error("could not read options from %s: %s", OPTIONS_FILE, exc)
    return {}


def _write_options(options: dict[str, Any]) -> None:
    OPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    OPTIONS_FILE.write_text(json.dumps(options, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _as_int(value: Any, default: int, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    if minimum is not None and parsed < minimum:
        return default
    return parsed


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    config["demo_mode"] = bool(config.get("demo_mode", True))
    level = str(config.get("log_level") or "info").lower()
    if level not in {"trace", "debug", "info", "warning", "error"}:
        errors.append("log_level is invalid; using info")
        level = "info"
    config["log_level"] = level
    config["event_interval_seconds"] = _as_int(config.get("event_interval_seconds"), 10, 1)

    mqtt = config.setdefault("mqtt", {})
    if not isinstance(mqtt, dict):
        mqtt = config["mqtt"] = {}
        errors.append("mqtt must be an object; using defaults")
    mqtt["enabled"] = bool(mqtt.get("enabled", False))
    mqtt["host"] = str(mqtt.get("host") or "core-mosquitto").strip()
    mqtt["port"] = _as_int(mqtt.get("port"), 1883, 1)
    mqtt["username"] = str(mqtt.get("username") or "")
    mqtt["password"] = str(mqtt.get("password") or "")
    mqtt["topic_prefix"] = str(mqtt.get("topic_prefix") or "ha/frigate_face_bridge").strip().strip("/")
    if mqtt["enabled"] and not mqtt["host"]:
        errors.append("mqtt.host is required when MQTT is enabled")
        mqtt["enabled"] = False

    camera = config.setdefault("camera", {})
    if not isinstance(camera, dict):
        camera = config["camera"] = {}
        errors.append("camera must be an object; using defaults")
    camera["name"] = re.sub(r"[^A-Za-z0-9_-]+", "_", str(camera.get("name") or "camera")).strip("_") or "camera"
    camera["host"] = str(camera.get("host") or "")
    camera["rtsp_url"] = str(camera.get("rtsp_url") or "")
    camera["snapshot_url"] = str(camera.get("snapshot_url") or "")
    camera["detect_width"] = _as_int(camera.get("detect_width"), 640, 1)
    camera["detect_height"] = _as_int(camera.get("detect_height"), 360, 1)
    camera["detect_fps"] = _as_int(camera.get("detect_fps"), 5, 1)
    if not config["demo_mode"] and not camera["rtsp_url"] and not camera["snapshot_url"]:
        errors.append("demo_mode is false but no camera stream is configured")

    known_faces = config.get("known_faces")
    if not isinstance(known_faces, list):
        known_faces = []
        errors.append("known_faces must be a list; using an empty list")
    cleaned_faces = []
    for item in known_faces:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if name:
            cleaned_faces.append({"name": name, "enabled": bool(item.get("enabled", True))})
    config["known_faces"] = cleaned_faces
    config["config_errors"] = errors
    for error in errors:
        LOG.warning("configuration warning: %s", error)
    return config


def load_config() -> dict[str, Any]:
    return validate_config(_deep_merge(_defaults_from_addon_config(), _load_options()))


def _validate_url(value: str, allowed_schemes: set[str]) -> str:
    value = value.strip()
    if not value:
        return ""
    parts = urlsplit(value)
    if parts.scheme.lower() not in allowed_schemes or not parts.netloc:
        raise ValueError(f"URL scheme must be one of: {', '.join(sorted(allowed_schemes))}")
    return value


def sanitize_camera_update(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    camera = payload.get("camera", payload)
    if not isinstance(camera, dict):
        raise ValueError("camera must be a JSON object")

    out: dict[str, Any] = {}
    if "name" in camera:
        name = re.sub(r"[^A-Za-z0-9_-]+", "_", str(camera.get("name") or "camera")).strip("_") or "camera"
        out["name"] = name
    if "host" in camera:
        host = str(camera.get("host") or "").strip()
        if host and not re.fullmatch(r"[A-Za-z0-9_.:-]+", host):
            raise ValueError("host contains invalid characters")
        out["host"] = host
    if "rtsp_url" in camera:
        out["rtsp_url"] = _validate_url(str(camera.get("rtsp_url") or ""), {"rtsp", "rtsps", "http", "https"})
    if "snapshot_url" in camera:
        out["snapshot_url"] = _validate_url(str(camera.get("snapshot_url") or ""), {"http", "https"})
    for key in ("detect_width", "detect_height", "detect_fps"):
        if key in camera:
            out[key] = _as_int(camera.get(key), 640 if key == "detect_width" else 360 if key == "detect_height" else 5, 1)

    if not out:
        raise ValueError("no camera fields supplied")
    return out


def save_camera_config(camera_update: dict[str, Any]) -> dict[str, Any]:
    options = _load_options()
    camera = options.get("camera") if isinstance(options.get("camera"), dict) else {}
    options["camera"] = {**camera, **sanitize_camera_update(camera_update)}
    _write_options(options)
    return load_config()
