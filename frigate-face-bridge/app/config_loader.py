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
LOG_LEVELS = {"trace", "debug", "info", "warning", "error"}


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
        if parts.scheme and parts.netloc:
            host = parts.hostname or ""
            if parts.port:
                host = f"{host}:{parts.port}"
            return urlunsplit((parts.scheme, host, "/***", "", ""))
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
        "mqtt": {"enabled": False, "host": "core-mosquitto", "port": 1883, "username": "", "password": "", "topic_prefix": "ha/frigate_face_bridge", "discovery": True, "discovery_prefix": "homeassistant"},
        "frigate": {"enabled": False, "events_topic": "frigate/events", "camera_name": "", "api_url": "", "person_count_enabled": True, "person_count_interval_seconds": 5, "dog_name": "Maja"},
        "face_recognition": {"enabled": False, "events_topic": "face_recognition/events", "min_confidence": 0.7},
        "announcements": {"enabled": True, "announce_known": True, "announce_unknown": True, "announce_dog": True, "random_texts_enabled": True, "global_cooldown_seconds": 60, "entity_cooldown_seconds": 300, "disabled_entities": "", "custom_texts": ""},
        "terrace_door": {"enabled": False, "open": False, "confidence": 0.0, "last_changed": ""},
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
    if level not in LOG_LEVELS:
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
    mqtt["discovery"] = bool(mqtt.get("discovery", True))
    mqtt["discovery_prefix"] = str(mqtt.get("discovery_prefix") or "homeassistant").strip().strip("/")
    if mqtt["enabled"] and not mqtt["host"]:
        errors.append("mqtt.host is required when MQTT is enabled")
        mqtt["enabled"] = False
    if mqtt["discovery"] and not mqtt["discovery_prefix"]:
        errors.append("mqtt.discovery_prefix is required when MQTT Discovery is enabled")
        mqtt["discovery"] = False

    frigate = config.setdefault("frigate", {})
    if not isinstance(frigate, dict):
        frigate = config["frigate"] = {}
        errors.append("frigate must be an object; using defaults")
    frigate["enabled"] = bool(frigate.get("enabled", False))
    frigate["events_topic"] = str(frigate.get("events_topic") or "frigate/events").strip().strip("/")
    frigate["camera_name"] = re.sub(r"[^A-Za-z0-9_-]+", "_", str(frigate.get("camera_name") or "")).strip("_")
    frigate["api_url"] = str(frigate.get("api_url") or "").strip().rstrip("/")
    frigate["person_count_enabled"] = bool(frigate.get("person_count_enabled", True))
    frigate["person_count_interval_seconds"] = _as_int(frigate.get("person_count_interval_seconds"), 5, 1)
    frigate["dog_name"] = re.sub(r"[^A-Za-z0-9 _-]+", "", str(frigate.get("dog_name") or "Maja")).strip() or "Maja"
    if frigate["api_url"]:
        parts = urlsplit(frigate["api_url"])
        if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
            errors.append("frigate.api_url must be an http or https URL")
            frigate["api_url"] = ""
    if frigate["enabled"] and not mqtt["enabled"]:
        errors.append("frigate.enabled requires mqtt.enabled")
    if frigate["enabled"] and not frigate["events_topic"]:
        errors.append("frigate.events_topic is required when Frigate import is enabled")
        frigate["enabled"] = False

    face_recognition = config.setdefault("face_recognition", {})
    if not isinstance(face_recognition, dict):
        face_recognition = config["face_recognition"] = {}
        errors.append("face_recognition must be an object; using defaults")
    face_recognition["enabled"] = bool(face_recognition.get("enabled", False))
    face_recognition["events_topic"] = str(face_recognition.get("events_topic") or "face_recognition/events").strip().strip("/")
    try:
        min_confidence = float(face_recognition.get("min_confidence", 0.7))
    except (TypeError, ValueError):
        min_confidence = 0.7
        errors.append("face_recognition.min_confidence is invalid; using 0.7")
    face_recognition["min_confidence"] = min(max(min_confidence, 0.0), 1.0)
    if face_recognition["enabled"] and not mqtt["enabled"]:
        errors.append("face_recognition.enabled requires mqtt.enabled")
    if face_recognition["enabled"] and not face_recognition["events_topic"]:
        errors.append("face_recognition.events_topic is required when Face Recognition import is enabled")
        face_recognition["enabled"] = False

    announcements = config.setdefault("announcements", {})
    if not isinstance(announcements, dict):
        announcements = config["announcements"] = {}
        errors.append("announcements must be an object; using defaults")
    announcements["enabled"] = bool(announcements.get("enabled", True))
    announcements["announce_known"] = bool(announcements.get("announce_known", True))
    announcements["announce_unknown"] = bool(announcements.get("announce_unknown", True))
    announcements["announce_dog"] = bool(announcements.get("announce_dog", True))
    announcements["random_texts_enabled"] = bool(announcements.get("random_texts_enabled", True))
    announcements["global_cooldown_seconds"] = _as_int(announcements.get("global_cooldown_seconds"), 60, 0)
    announcements["entity_cooldown_seconds"] = _as_int(announcements.get("entity_cooldown_seconds"), 300, 0)
    announcements["disabled_entities"] = str(announcements.get("disabled_entities") or "")[:1000]
    announcements["custom_texts"] = str(announcements.get("custom_texts") or "")[:5000]

    terrace_door = config.setdefault("terrace_door", {})
    if not isinstance(terrace_door, dict):
        terrace_door = config["terrace_door"] = {}
        errors.append("terrace_door must be an object; using defaults")
    terrace_door["enabled"] = bool(terrace_door.get("enabled", False))
    terrace_door["open"] = bool(terrace_door.get("open", False))
    try:
        door_confidence = float(terrace_door.get("confidence", 0.0))
    except (TypeError, ValueError):
        door_confidence = 0.0
        errors.append("terrace_door.confidence is invalid; using 0.0")
    terrace_door["confidence"] = min(max(door_confidence, 0.0), 1.0)
    terrace_door["last_changed"] = str(terrace_door.get("last_changed") or "")

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


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _validate_topic(value: str, default: str = "") -> str:
    topic = str(value or default).strip().strip("/")
    if topic and not re.fullmatch(r"[A-Za-z0-9_./-]+", topic):
        raise ValueError("MQTT topic contains invalid characters")
    return topic


def _validate_host(value: str) -> str:
    host = str(value or "").strip()
    if host and not re.fullmatch(r"[A-Za-z0-9_.:-]+", host):
        raise ValueError("mqtt.host contains invalid characters")
    return host


def sanitize_app_update(payload: dict[str, Any], current_options: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    current_options = current_options if isinstance(current_options, dict) else {}

    out: dict[str, Any] = {}
    if "demo_mode" in payload:
        out["demo_mode"] = _as_bool(payload.get("demo_mode"))
    if "log_level" in payload:
        level = str(payload.get("log_level") or "info").strip().lower()
        if level not in LOG_LEVELS:
            raise ValueError("log_level is invalid")
        out["log_level"] = level
    if "event_interval_seconds" in payload:
        out["event_interval_seconds"] = _as_int(payload.get("event_interval_seconds"), 10, 1)

    mqtt_payload = payload.get("mqtt")
    if mqtt_payload is not None:
        if not isinstance(mqtt_payload, dict):
            raise ValueError("mqtt must be a JSON object")
        mqtt: dict[str, Any] = {}
        if "enabled" in mqtt_payload:
            mqtt["enabled"] = _as_bool(mqtt_payload.get("enabled"))
        if "host" in mqtt_payload:
            mqtt["host"] = _validate_host(str(mqtt_payload.get("host") or ""))
        if "port" in mqtt_payload:
            mqtt["port"] = _as_int(mqtt_payload.get("port"), 1883, 1)
        if "username" in mqtt_payload:
            mqtt["username"] = str(mqtt_payload.get("username") or "")
        if "password" in mqtt_payload:
            password = str(mqtt_payload.get("password") or "")
            if "***" not in password:
                mqtt["password"] = password
        if "topic_prefix" in mqtt_payload:
            mqtt["topic_prefix"] = _validate_topic(str(mqtt_payload.get("topic_prefix") or "ha/frigate_face_bridge"), "ha/frigate_face_bridge")
        if "discovery" in mqtt_payload:
            mqtt["discovery"] = _as_bool(mqtt_payload.get("discovery"))
        if "discovery_prefix" in mqtt_payload:
            mqtt["discovery_prefix"] = _validate_topic(str(mqtt_payload.get("discovery_prefix") or "homeassistant"), "homeassistant")
        if mqtt:
            out["mqtt"] = mqtt

    frigate_payload = payload.get("frigate")
    if frigate_payload is not None:
        if not isinstance(frigate_payload, dict):
            raise ValueError("frigate must be a JSON object")
        frigate: dict[str, Any] = {}
        if "enabled" in frigate_payload:
            frigate["enabled"] = _as_bool(frigate_payload.get("enabled"))
        if "events_topic" in frigate_payload:
            frigate["events_topic"] = _validate_topic(str(frigate_payload.get("events_topic") or "frigate/events"), "frigate/events")
        if "camera_name" in frigate_payload:
            frigate["camera_name"] = re.sub(r"[^A-Za-z0-9_-]+", "_", str(frigate_payload.get("camera_name") or "")).strip("_")
        if "api_url" in frigate_payload:
            api_url = str(frigate_payload.get("api_url") or "").strip().rstrip("/")
            if api_url:
                parts = urlsplit(api_url)
                if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
                    raise ValueError("frigate.api_url must be an http or https URL")
            frigate["api_url"] = api_url
        if "person_count_enabled" in frigate_payload:
            frigate["person_count_enabled"] = _as_bool(frigate_payload.get("person_count_enabled"))
        if "person_count_interval_seconds" in frigate_payload:
            frigate["person_count_interval_seconds"] = _as_int(frigate_payload.get("person_count_interval_seconds"), 5, 1)
        if "dog_name" in frigate_payload:
            frigate["dog_name"] = re.sub(r"[^A-Za-z0-9 _-]+", "", str(frigate_payload.get("dog_name") or "Maja")).strip() or "Maja"
        if frigate:
            out["frigate"] = frigate

    face_payload = payload.get("face_recognition")
    if face_payload is not None:
        if not isinstance(face_payload, dict):
            raise ValueError("face_recognition must be a JSON object")
        face: dict[str, Any] = {}
        if "enabled" in face_payload:
            face["enabled"] = _as_bool(face_payload.get("enabled"))
        if "events_topic" in face_payload:
            face["events_topic"] = _validate_topic(str(face_payload.get("events_topic") or "face_recognition/events"), "face_recognition/events")
        if "min_confidence" in face_payload:
            try:
                face["min_confidence"] = min(max(float(face_payload.get("min_confidence")), 0.0), 1.0)
            except (TypeError, ValueError):
                raise ValueError("face_recognition.min_confidence is invalid")
        if face:
            out["face_recognition"] = face

    door_payload = payload.get("terrace_door")
    if door_payload is not None:
        if not isinstance(door_payload, dict):
            raise ValueError("terrace_door must be a JSON object")
        door: dict[str, Any] = {}
        if "enabled" in door_payload:
            door["enabled"] = _as_bool(door_payload.get("enabled"))
        if "open" in door_payload:
            door["open"] = _as_bool(door_payload.get("open"))
        if "confidence" in door_payload:
            try:
                door["confidence"] = min(max(float(door_payload.get("confidence")), 0.0), 1.0)
            except (TypeError, ValueError):
                raise ValueError("terrace_door.confidence is invalid")
        if "last_changed" in door_payload:
            door["last_changed"] = str(door_payload.get("last_changed") or "")
        if door:
            out["terrace_door"] = door

    announcement_payload = payload.get("announcements")
    if announcement_payload is not None:
        if not isinstance(announcement_payload, dict):
            raise ValueError("announcements must be a JSON object")
        announcements: dict[str, Any] = {}
        for key in ("enabled", "announce_known", "announce_unknown", "announce_dog", "random_texts_enabled"):
            if key in announcement_payload:
                announcements[key] = _as_bool(announcement_payload.get(key))
        if "global_cooldown_seconds" in announcement_payload:
            announcements["global_cooldown_seconds"] = _as_int(announcement_payload.get("global_cooldown_seconds"), 60, 0)
        if "entity_cooldown_seconds" in announcement_payload:
            announcements["entity_cooldown_seconds"] = _as_int(announcement_payload.get("entity_cooldown_seconds"), 300, 0)
        if "disabled_entities" in announcement_payload:
            announcements["disabled_entities"] = str(announcement_payload.get("disabled_entities") or "")[:1000]
        if "custom_texts" in announcement_payload:
            announcements["custom_texts"] = str(announcement_payload.get("custom_texts") or "")[:5000]
        if announcements:
            out["announcements"] = announcements

    if not out:
        raise ValueError("no application settings supplied")
    return out


def save_app_config(update: dict[str, Any]) -> dict[str, Any]:
    options = _load_options()
    sanitized = sanitize_app_update(update, options)
    for key, value in sanitized.items():
        if isinstance(value, dict):
            existing = options.get(key) if isinstance(options.get(key), dict) else {}
            options[key] = {**existing, **value}
        else:
            options[key] = value
    _write_options(options)
    return load_config()
