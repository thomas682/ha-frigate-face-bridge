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

from flask import Flask, jsonify, send_from_directory

from camera import camera_status
from config_loader import load_config, safe_config
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
        "version": os.environ.get("ADDON_VERSION", "0.1.0"),
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


def shutdown(signum: int, frame: Any) -> None:
    LOG.info("shutdown requested signal=%s", signum)
    with state_lock:
        state["running"] = False
    publisher.stop()
    raise SystemExit(0)


def main() -> None:
    LOG.info("Frigate Face Bridge starting version=%s", os.environ.get("ADDON_VERSION", "0.1.0"))
    LOG.info("camera config: %s", camera_status(config))
    publisher.connect()
    thread = threading.Thread(target=event_loop, daemon=True)
    thread.start()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    app.run(host="0.0.0.0", port=8099)


if __name__ == "__main__":
    main()
