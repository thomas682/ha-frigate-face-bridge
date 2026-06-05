from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from flask import Flask, Response, jsonify, request, send_from_directory

from announcements import AnnouncementManager
from camera import camera_status
from config_loader import load_config, redact_url, safe_config, save_app_config, save_camera_config
from detector import create_detector
from face_recognition import known_face_status, parse_face_match_event, save_face, set_face_enabled
from frigate_api import active_person_count_event
from frigate_events import parse_frigate_event
from mqtt_client import MqttPublisher

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
STARTED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
HISTORY_LIMIT = 500
state_lock = threading.RLock()
history: deque[dict[str, Any]] = deque(maxlen=HISTORY_LIMIT)
announcement_history: deque[dict[str, Any]] = deque(maxlen=HISTORY_LIMIT)
state: dict[str, Any] = {
    "started_at": STARTED_AT,
    "last_event": None,
    "event_count": 0,
    "frigate_event_count": 0,
    "frigate_active_count": 0,
    "face_event_count": 0,
    "running": True,
}

config = load_config()


def configure_logging() -> None:
    level_name = str(config.get("log_level") or "info").upper()
    if level_name == "TRACE":
        level_name = "DEBUG"
    logging.basicConfig(level=getattr(logging, level_name, logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s", stream=sys.stdout)


configure_logging()
LOG = logging.getLogger("frigate_face_bridge")
detector = create_detector(config)
announcement_manager = AnnouncementManager()


def handle_frigate_event(payload: bytes) -> None:
    event = parse_frigate_event(payload, config)
    if event is None:
        return
    with state_lock:
        state["last_event"] = event
        state["event_count"] = int(state.get("event_count") or 0) + 1
        state["frigate_event_count"] = int(state.get("frigate_event_count") or 0) + 1
        record_event(event)
    LOG.info(
        "frigate event camera=%s person_count=%s confidence=%s",
        event.get("camera"),
        event.get("person_count"),
        event.get("confidence"),
    )
    publisher.publish_event(event)


def handle_face_event(payload: bytes | dict[str, Any]) -> dict[str, Any] | None:
    event = parse_face_match_event(payload, config)
    if event is None:
        return None
    with state_lock:
        state["last_event"] = event
        state["event_count"] = int(state.get("event_count") or 0) + 1
        state["face_event_count"] = int(state.get("face_event_count") or 0) + 1
        record_event(event)
    LOG.info("face event camera=%s known_faces=%s unknown_faces=%s", event.get("camera"), event.get("known_faces"), event.get("unknown_faces"))
    publisher.publish_event(event)
    return event


publisher = MqttPublisher(config, handle_frigate_event, handle_face_event)


def terrace_door_status(event: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = config.get("terrace_door", {}) if isinstance(config.get("terrace_door"), dict) else {}
    event = event or {}
    return {
        "enabled": bool(settings.get("enabled", False)),
        "open": bool(event.get("terrace_door_open", settings.get("open", False))),
        "confidence": float(event.get("terrace_door_confidence", settings.get("confidence", 0.0)) or 0.0),
        "last_changed": str(event.get("terrace_door_last_changed", settings.get("last_changed") or "")),
    }


def record_event(event: dict[str, Any]) -> None:
    door = terrace_door_status(event)
    announcement = announcement_manager.build(event, config)
    event["announcement"] = announcement
    event["terrace_door_open"] = door["open"]
    event["terrace_door_confidence"] = door["confidence"]
    event["terrace_door_last_changed"] = door["last_changed"]
    entry = {
        "timestamp": event.get("timestamp"),
        "camera": event.get("camera"),
        "source": event.get("source"),
        "person_count": int(event.get("person_count") or 0),
        "dog_count": int(event.get("dog_count") or 0),
        "maja_present": bool(event.get("maja_present")),
        "known_faces": event.get("known_faces") or [],
        "recognized_entities": event.get("recognized_entities") or event.get("known_faces") or [],
        "unknown_faces": int(event.get("unknown_faces") or 0),
        "announcement_text": announcement.get("text") or "",
        "announcement_should_speak": bool(announcement.get("should_speak")),
        "announcement_log_text": announcement.get("log_text") or "",
        "announcement_suppressed_reason": announcement.get("suppressed_reason") or "",
        "terrace_door_open": door["open"],
        "terrace_door_confidence": door["confidence"],
        "terrace_door_last_changed": door["last_changed"],
        "status": event.get("status"),
    }
    history.append(entry)
    announcement_history.append({
        "timestamp": entry["timestamp"],
        "camera": entry["camera"],
        "text": announcement.get("log_text") or "",
        "spoken": bool(announcement.get("should_speak")),
        "entities": announcement.get("entities") or [],
        "suppressed_reason": announcement.get("suppressed_reason") or "",
    })


def _status() -> dict[str, Any]:
    with state_lock:
        last_event = state.get("last_event")
        event_count = state.get("event_count", 0)
        frigate_event_count = state.get("frigate_event_count", 0)
        frigate_active_count = state.get("frigate_active_count", 0)
        face_event_count = state.get("face_event_count", 0)
        recent_history = list(history)[-50:]
        recent_announcements = list(announcement_history)[-50:]
        person_count_series = [
            {"timestamp": item.get("timestamp"), "person_count": item.get("person_count", 0)}
            for item in recent_history
            if item.get("source") == "frigate_active_objects"
        ][-60:]
    return {
        "ok": True,
        "version": os.environ.get("ADDON_VERSION", "0.12.0"),
        "started_at": STARTED_AT,
        "demo_mode": bool(config.get("demo_mode", True)),
        "event_count": event_count,
        "frigate_event_count": frigate_event_count,
        "frigate_active_count": frigate_active_count,
        "face_event_count": face_event_count,
        "last_event": last_event,
        "history": recent_history,
        "announcement_history": recent_announcements,
        "person_count_series": person_count_series,
        "camera": camera_status(config),
        "mqtt": publisher.status(),
        "known_faces": known_face_status(config),
        "terrace_door": terrace_door_status(),
        "config_errors": config.get("config_errors", []),
    }


def event_loop() -> None:
    interval = max(1, int(config.get("event_interval_seconds") or 10))
    LOG.info("event loop started demo_mode=%s interval=%ss camera=%s", config.get("demo_mode"), interval, camera_status(config).get("name"))
    while state.get("running"):
        frigate = config.get("frigate", {}) if isinstance(config.get("frigate"), dict) else {}
        if not bool(config.get("demo_mode", True)) and bool(frigate.get("enabled")) and bool(frigate.get("person_count_enabled", True)) and str(frigate.get("api_url") or "").strip():
            time.sleep(interval)
            continue
        event = detector.detect()
        with state_lock:
            state["last_event"] = event
            state["event_count"] = int(state.get("event_count") or 0) + 1
            record_event(event)
        LOG.info("event camera=%s person_count=%s known_faces=%s unknown_faces=%s", event.get("camera"), event.get("person_count"), len(event.get("known_faces") or []), event.get("unknown_faces"))
        publisher.publish_event(event)
        time.sleep(interval)


def frigate_person_count_loop() -> None:
    LOG.info("Frigate active person count loop started")
    while state.get("running"):
        frigate = config.get("frigate", {}) if isinstance(config.get("frigate"), dict) else {}
        interval = max(1, int(frigate.get("person_count_interval_seconds") or 5))
        try:
            event = active_person_count_event(config)
            if event is not None:
                with state_lock:
                    state["last_event"] = event
                    state["event_count"] = int(state.get("event_count") or 0) + 1
                    state["frigate_active_count"] = int(state.get("frigate_active_count") or 0) + 1
                    record_event(event)
                LOG.info("active Frigate objects camera=%s person_count=%s dog_count=%s", event.get("camera"), event.get("person_count"), event.get("dog_count"))
                publisher.publish_event(event)
        except Exception as exc:
            publisher.last_error = f"Frigate person count failed: {exc}"
            LOG.warning("Frigate person count failed: %s", exc)
        time.sleep(interval)


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/health")
def health():
    return jsonify({"ok": True, "status": "healthy", "started_at": STARTED_AT})


@app.get("/api/status")
def api_status():
    return jsonify(_status())


@app.get("/api/cameras")
def api_cameras():
    return jsonify({"ok": True, "cameras": [camera_status(config)]})


@app.get("/api/last-event")
def api_last_event():
    with state_lock:
        event = state.get("last_event")
    return jsonify({"ok": True, "last_event": event})


@app.get("/api/history")
def api_history():
    with state_lock:
        items = list(history)
    return jsonify({"ok": True, "history": items, "person_count_series": [{"timestamp": item.get("timestamp"), "person_count": item.get("person_count", 0)} for item in items if item.get("source") == "frigate_active_objects"][-120:]})


@app.get("/api/config")
def api_config():
    return jsonify({"ok": True, "config": safe_config(config)})


@app.post("/api/config")
def api_update_config():
    global detector, publisher
    try:
        updated = save_app_config(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        LOG.exception("could not save application configuration")
        return jsonify({"ok": False, "error": "could not save application configuration"}), 500

    old_publisher = publisher
    config.clear()
    config.update(updated)
    detector = create_detector(config)
    publisher = MqttPublisher(config, handle_frigate_event, handle_face_event)
    old_publisher.stop()
    if bool(config.get("mqtt", {}).get("enabled")):
        publisher.connect()
    LOG.info("application configuration updated")
    return jsonify({"ok": True, "config": safe_config(config), "status": _status()})


@app.get("/api/faces")
def api_faces():
    return jsonify({"ok": True, "faces": known_face_status(config)})


@app.post("/api/faces")
def api_create_face():
    try:
        face = save_face(request.get_json(silent=True) or {}, config)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        LOG.exception("could not save face")
        return jsonify({"ok": False, "error": "could not save face"}), 500
    return jsonify({"ok": True, "face": face, "faces": known_face_status(config)})


@app.patch("/api/faces/<path:name>")
def api_update_face(name: str):
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict) or "enabled" not in payload:
        return jsonify({"ok": False, "error": "enabled is required"}), 400
    try:
        face = set_face_enabled(name, bool(payload.get("enabled")), config)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404 if str(exc) == "face not found" else 400
    except Exception:
        LOG.exception("could not update face")
        return jsonify({"ok": False, "error": "could not update face"}), 500
    return jsonify({"ok": True, "face": face, "faces": known_face_status(config)})


@app.post("/api/face-events")
def api_face_event():
    event = handle_face_event(request.get_json(silent=True) or {})
    if event is None:
        return jsonify({"ok": False, "error": "face event did not contain enabled known faces or unknown faces"}), 400
    return jsonify({"ok": True, "event": event})


@app.post("/api/config/camera")
def api_update_camera():
    global detector
    try:
        updated = save_camera_config(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        LOG.exception("could not save camera configuration")
        return jsonify({"ok": False, "error": "could not save camera configuration"}), 500

    config.clear()
    config.update(updated)
    detector = create_detector(config)
    LOG.info("camera configuration updated: %s", camera_status(config))
    return jsonify({"ok": True, "camera": camera_status(config), "config_errors": config.get("config_errors", [])})


@app.get("/api/camera/snapshot")
def api_camera_snapshot():
    camera = config.get("camera", {}) if isinstance(config.get("camera"), dict) else {}
    snapshot_url = str(camera.get("snapshot_url") or "").strip()
    if not snapshot_url:
        return jsonify({"ok": False, "error": "snapshot_url is not configured"}), 400
    parts = urlsplit(snapshot_url)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return jsonify({"ok": False, "error": "snapshot_url must use http or https"}), 400

    try:
        req = Request(snapshot_url, headers={"User-Agent": "frigate-face-bridge/0.11"})
        with urlopen(req, timeout=8) as response:
            content_type = response.headers.get("Content-Type", "image/jpeg").split(";", 1)[0]
            if not content_type.startswith("image/"):
                return jsonify({"ok": False, "error": "snapshot response is not an image"}), 502
            data = response.read(5 * 1024 * 1024 + 1)
    except URLError as exc:
        LOG.warning("snapshot fetch failed url=%s error=%s", redact_url(snapshot_url), exc)
        return jsonify({"ok": False, "error": "snapshot fetch failed"}), 502
    except Exception as exc:
        LOG.warning("snapshot fetch failed url=%s error=%s", redact_url(snapshot_url), exc)
        return jsonify({"ok": False, "error": "snapshot fetch failed"}), 502

    if len(data) > 5 * 1024 * 1024:
        return jsonify({"ok": False, "error": "snapshot is too large"}), 502
    return Response(data, mimetype=content_type, headers={"Cache-Control": "no-store"})


def shutdown(signum: int, frame: Any) -> None:
    LOG.info("shutdown requested signal=%s", signum)
    with state_lock:
        state["running"] = False
    publisher.stop()
    raise SystemExit(0)


def main() -> None:
    LOG.info("Frigate Face Bridge starting version=%s", os.environ.get("ADDON_VERSION", "0.12.0"))
    LOG.info("camera config: %s", camera_status(config))
    publisher.connect()
    thread = threading.Thread(target=event_loop, daemon=True)
    thread.start()
    frigate_thread = threading.Thread(target=frigate_person_count_loop, daemon=True)
    frigate_thread.start()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    app.run(host="0.0.0.0", port=8099)


if __name__ == "__main__":
    main()
