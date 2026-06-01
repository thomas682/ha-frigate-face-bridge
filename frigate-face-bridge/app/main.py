from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from flask import Flask, Response, jsonify, request, send_from_directory

from camera import camera_status
from config_loader import load_config, redact_url, safe_config, save_camera_config
from detector import create_detector
from face_recognition import known_face_status
from mqtt_client import MqttPublisher

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
STARTED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
state_lock = threading.RLock()
state: dict[str, Any] = {
    "started_at": STARTED_AT,
    "last_event": None,
    "event_count": 0,
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
publisher = MqttPublisher(config)
detector = create_detector(config)


def _status() -> dict[str, Any]:
    with state_lock:
        last_event = state.get("last_event")
        event_count = state.get("event_count", 0)
    return {
        "ok": True,
        "version": os.environ.get("ADDON_VERSION", "0.2.0"),
        "started_at": STARTED_AT,
        "demo_mode": bool(config.get("demo_mode", True)),
        "event_count": event_count,
        "last_event": last_event,
        "camera": camera_status(config),
        "mqtt": publisher.status(),
        "known_faces": known_face_status(config),
        "config_errors": config.get("config_errors", []),
    }


def event_loop() -> None:
    interval = max(1, int(config.get("event_interval_seconds") or 10))
    LOG.info("event loop started demo_mode=%s interval=%ss camera=%s", config.get("demo_mode"), interval, camera_status(config).get("name"))
    while state.get("running"):
        event = detector.detect()
        with state_lock:
            state["last_event"] = event
            state["event_count"] = int(state.get("event_count") or 0) + 1
        LOG.info("event camera=%s person_count=%s known_faces=%s unknown_faces=%s", event.get("camera"), event.get("person_count"), len(event.get("known_faces") or []), event.get("unknown_faces"))
        publisher.publish_event(event)
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


@app.get("/api/config")
def api_config():
    return jsonify({"ok": True, "config": safe_config(config)})


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
        req = Request(snapshot_url, headers={"User-Agent": "frigate-face-bridge/0.2"})
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
    LOG.info("Frigate Face Bridge starting version=%s", os.environ.get("ADDON_VERSION", "0.2.0"))
    LOG.info("camera config: %s", camera_status(config))
    publisher.connect()
    thread = threading.Thread(target=event_loop, daemon=True)
    thread.start()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    app.run(host="0.0.0.0", port=8099)


if __name__ == "__main__":
    main()
