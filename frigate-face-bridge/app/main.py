from __future__ import annotations

import logging
import os
import signal
import socket
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

import paho.mqtt.client as mqtt
from flask import Flask, Response, jsonify, request, send_from_directory

from announcements import AnnouncementManager
from camera import camera_status
from config_loader import display_url, load_config, load_raw_options, redact_url, safe_config, save_app_config, save_camera_config
from detector import create_detector
from face_recognition import known_face_status, parse_face_match_event, save_face, set_face_enabled
from frigate_api import active_person_count_event
from frigate_events import parse_frigate_event
from mqtt_client import MqttPublisher

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
STARTED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_version() -> str:
    for version_file in (APP_DIR / "VERSION", APP_DIR.parents[1] / "VERSION"):
        try:
            version = version_file.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if version:
            return version
    return "unbekannt"


APP_VERSION = read_version()

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
    mqtt_status = publisher.status()
    config_errors = config.get("config_errors", [])
    last_error = mqtt_status.get("last_error") or (config_errors[-1] if config_errors else "")
    return {
        "ok": True,
        "version": APP_VERSION,
        "started_at": STARTED_AT,
        "demo_mode": bool(config.get("demo_mode", False)),
        "event_count": event_count,
        "frigate_event_count": frigate_event_count,
        "frigate_active_count": frigate_active_count,
        "face_event_count": face_event_count,
        "last_event": last_event,
        "history": recent_history,
        "announcement_history": recent_announcements,
        "person_count_series": person_count_series,
        "camera": camera_status(config),
        "mqtt": mqtt_status,
        "mqtt_history": publisher.history(80),
        "mqtt_output_topics": publisher.output_topics(),
        "known_faces": known_face_status(config),
        "terrace_door": terrace_door_status(),
        "storage_status": storage_status(),
        "app_status": {
            "bridge": "online",
            "home_assistant": "via Ingress" if os.environ.get("SUPERVISOR_TOKEN") else "nicht erkannt",
            "go2rtc": go2rtc_status(),
            "frigate": "aktiv" if bool(config.get("frigate", {}).get("enabled")) else "deaktiviert",
            "mqtt": "verbunden" if mqtt_status.get("connected") else ("aktiviert" if mqtt_status.get("enabled") else "deaktiviert"),
            "last_error": last_error,
        },
        "communication": communication_status(mqtt_status),
        "config_errors": config_errors,
    }


def _endpoint_from_url(value: str, default_port: int | None = None) -> dict[str, Any]:
    value = str(value or "").strip()
    if not value:
        return {"configured": False, "scheme": "", "host": "", "port": None, "display": "nicht konfiguriert"}
    try:
        parts = urlsplit(value)
        if not parts.scheme or not parts.hostname:
            return {"configured": False, "scheme": "", "host": "", "port": None, "display": "ungueltig"}
        if parts.port:
            port = parts.port
        elif parts.scheme == "https":
            port = 443
        elif parts.scheme == "http":
            port = 80
        elif parts.scheme == "rtsps":
            port = 7441
        elif parts.scheme == "rtsp":
            port = default_port or 554
        else:
            port = default_port
        display = f"{parts.scheme}://{parts.hostname}{':' + str(port) if port else ''}"
        return {"configured": True, "scheme": parts.scheme, "host": parts.hostname, "port": port, "display": display}
    except Exception:
        return {"configured": False, "scheme": "", "host": "", "port": None, "display": "ungueltig"}


def communication_status(mqtt_status: dict[str, Any] | None = None) -> dict[str, Any]:
    mqtt_status = mqtt_status or publisher.status()
    mqtt_config = config.get("mqtt", {}) if isinstance(config.get("mqtt"), dict) else {}
    frigate_config = config.get("frigate", {}) if isinstance(config.get("frigate"), dict) else {}
    camera_config = config.get("camera", {}) if isinstance(config.get("camera"), dict) else {}

    rtsp_endpoint = _endpoint_from_url(str(camera_config.get("rtsp_url") or ""), 8554)
    snapshot_endpoint = _endpoint_from_url(str(camera_config.get("snapshot_url") or ""))
    frigate_endpoint = _endpoint_from_url(str(frigate_config.get("api_url") or ""), 5000)
    camera_host = str(camera_config.get("host") or rtsp_endpoint.get("host") or snapshot_endpoint.get("host") or "")
    mqtt_host = str(mqtt_config.get("host") or "")
    mqtt_port = int(mqtt_config.get("port") or 1883)
    go2rtc_state = go2rtc_status()
    rtsp_display = str(rtsp_endpoint.get("display") or "")
    go2rtc_used = bool(frigate_endpoint.get("configured") and go2rtc_state != "nicht konfiguriert") or ":8554" in rtsp_display or "go2rtc" in rtsp_display.lower()

    return {
        "ha_ingress_url": "/b3b46a83_frigate_face_bridge",
        "homepage_url": "http://homeassistant.localdomain:8123/b3b46a83_frigate_face_bridge",
        "direct_status_url": "http://fossflow.localdomain:8099/health",
        "elements": {
            "camera": {
                "title": "Kamera / UniFi Protect",
                "status": "konfiguriert" if camera_host or rtsp_endpoint.get("configured") or snapshot_endpoint.get("configured") else "nicht konfiguriert",
                "host": camera_host,
                "rtsp": rtsp_endpoint,
                "snapshot": snapshot_endpoint,
                "description": "Liefert Video-Stream und optional Snapshot-Bild. Credentials werden nicht angezeigt.",
                "exchange": "Video per RTSP/RTSPS, Einzelbild per HTTP/HTTPS Snapshot.",
            },
            "go2rtc": {
                "title": "go2rtc",
                "used": go2rtc_used,
                "status": go2rtc_state if go2rtc_used else "nicht verwendet/unklar",
                "host": frigate_endpoint.get("host") or "",
                "port": 8554 if go2rtc_used else None,
                "description": "Stream-Konverter, haeufig in Frigate eingebettet. Wandelt UniFi/RTSPS-Streams in nutzbare RTSP-Streams.",
                "exchange": "Stream-Weitergabe an Frigate; Status ueber Frigate go2rtc API, wenn Frigate API konfiguriert ist.",
            },
            "frigate": {
                "title": "Frigate",
                "status": "aktiv" if bool(frigate_config.get("enabled")) else ("API konfiguriert" if frigate_endpoint.get("configured") else "deaktiviert"),
                "api": frigate_endpoint,
                "camera_name": str(frigate_config.get("camera_name") or ""),
                "events_topic": str(frigate_config.get("events_topic") or ""),
                "description": "Erkennt Objekte wie Personen und Hunde und stellt Events sowie aktive Objektlisten bereit.",
                "exchange": "MQTT Events, REST API fuer aktive Personen/Hunde und go2rtc-Status.",
            },
            "bridge": {
                "title": "Face Bridge",
                "status": "online",
                "host": "Add-on intern",
                "port": 8099,
                "description": "Verarbeitet Frigate-/Face-Daten, berechnet Namen, Zaehler, Ansagen und Logs.",
                "exchange": "Liest Frigate/Face-Daten, schreibt MQTT Sensorwerte und stellt HA-Ingress UI/API bereit.",
            },
            "mqtt": {
                "title": "MQTT Broker",
                "status": "verbunden" if mqtt_status.get("connected") else ("aktiviert" if mqtt_status.get("enabled") else "deaktiviert"),
                "host": mqtt_host,
                "port": mqtt_port,
                "topic_prefix": str(mqtt_config.get("topic_prefix") or ""),
                "description": "Transportiert Bridge-Sensorwerte und MQTT Discovery nach Home Assistant.",
                "exchange": "Topics fuer person_count, known_faces, announcements, recognition_log und Discovery Configs.",
            },
            "home_assistant": {
                "title": "Home Assistant",
                "status": "via Ingress" if os.environ.get("SUPERVISOR_TOKEN") else "nicht erkannt",
                "host": "homeassistant.localdomain",
                "port": 8123,
                "description": "Zeigt die Add-on-Weboberflaeche ueber Ingress und nutzt MQTT-Sensoren fuer Dashboard und Automationen.",
                "exchange": "HA Ingress, Add-on Optionen, MQTT Sensoren und TTS/Automation-Ausgabe.",
            },
        },
    }


def storage_status() -> dict[str, Any]:
    raw = load_raw_options()
    raw_mqtt = raw.get("mqtt") if isinstance(raw.get("mqtt"), dict) else {}
    raw_camera = raw.get("camera") if isinstance(raw.get("camera"), dict) else {}
    return {
        "options_present": bool(raw),
        "mqtt_username_set": bool(str(raw_mqtt.get("username") or config.get("mqtt", {}).get("username") or "")),
        "mqtt_password_set": bool(str(raw_mqtt.get("password") or config.get("mqtt", {}).get("password") or "")),
        "rtsp_url_set": bool(str(raw_camera.get("rtsp_url") or config.get("camera", {}).get("rtsp_url") or "")),
        "snapshot_url_set": bool(str(raw_camera.get("snapshot_url") or config.get("camera", {}).get("snapshot_url") or "")),
        "faces_registry_present": known_face_status(config) != [],
    }


def go2rtc_status() -> str:
    frigate = config.get("frigate", {}) if isinstance(config.get("frigate"), dict) else {}
    api_url = str(frigate.get("api_url") or "").strip().rstrip("/")
    if not api_url:
        return "nicht konfiguriert"
    try:
        parts = urlsplit(api_url)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            return "ungueltige Frigate URL"
        req = Request(f"{api_url}/api/go2rtc/streams", headers={"User-Agent": "frigate-face-bridge"})
        with urlopen(req, timeout=3) as response:
            return "erreichbar" if response.status < 400 else f"HTTP {response.status}"
    except Exception:
        return "nicht erreichbar"


def _tcp_test(host: str, port: int, timeout: float = 3.0) -> dict[str, Any]:
    if not host or port <= 0:
        return {"ok": False, "status": "nicht konfiguriert"}
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "status": "TCP erreichbar"}
    except OSError as exc:
        return {"ok": False, "status": "nicht erreichbar", "error": str(exc)}


def test_mqtt_settings(settings: dict[str, Any]) -> dict[str, Any]:
    host = str(settings.get("host") or "").strip()
    try:
        port = int(settings.get("port") or 1883)
    except Exception:
        port = 1883
    if not host or port <= 0:
        return {"ok": False, "status": "MQTT Host oder Port fehlt", "host": host, "port": port}

    event = threading.Event()
    result: dict[str, Any] = {"ok": False, "status": "keine Antwort", "host": host, "port": port}
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"frigate-face-bridge-test-{int(time.time())}")
    username = str(settings.get("username") or "")
    password = str(settings.get("password") or "")
    if username or password:
        client.username_pw_set(username, password)

    def on_connect(_client: Any, _userdata: Any, _flags: Any, reason_code: Any, _properties: Any = None) -> None:
        connected = int(reason_code) == 0 if str(reason_code).isdigit() else str(reason_code) == "Success"
        result.update({"ok": connected, "status": "MQTT Login erfolgreich" if connected else f"MQTT Login fehlgeschlagen: {reason_code}", "reason": str(reason_code)})
        event.set()

    def on_disconnect(_client: Any, _userdata: Any, _flags: Any, reason_code: Any, _properties: Any = None) -> None:
        if not event.is_set() and str(reason_code) not in {"0", "Normal disconnection"}:
            result.update({"ok": False, "status": f"MQTT getrennt: {reason_code}", "reason": str(reason_code)})
            event.set()

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    try:
        client.connect(host, port, keepalive=10)
        client.loop_start()
        event.wait(5)
    except Exception as exc:
        result.update({"ok": False, "status": "MQTT Test fehlgeschlagen", "error": str(exc)})
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
        try:
            client.loop_stop()
        except Exception:
            pass
    return result


def test_rtsp_url(url: str) -> dict[str, Any]:
    url = str(url or "").strip()
    if not url:
        return {"ok": False, "status": "RTSP URL nicht gesetzt"}
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"rtsp", "rtsps", "http", "https"} or not parts.hostname:
        return {"ok": False, "status": "ungueltige RTSP URL"}
    port = parts.port or (7441 if parts.scheme.lower() == "rtsps" else 7447 if parts.scheme.lower() == "rtsp" else 443 if parts.scheme.lower() == "https" else 80)
    result = _tcp_test(parts.hostname, port)
    result["url"] = redact_url(url)
    return result


def test_frigate_api_url(url: str) -> dict[str, Any]:
    url = str(url or "").strip().rstrip("/")
    if not url:
        return {"ok": False, "status": "Frigate API URL nicht gesetzt"}
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return {"ok": False, "status": "ungueltige Frigate API URL"}
    checks = ["/api/stats", "/api/config", "/"]
    last_error = ""
    for path in checks:
        try:
            req = Request(f"{url}{path}", headers={"User-Agent": "frigate-face-bridge"})
            with urlopen(req, timeout=5) as response:
                content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
                if response.status < 400:
                    return {"ok": True, "status": f"Frigate erreichbar ({path}, HTTP {response.status})", "url": display_url(url), "content_type": content_type}
                last_error = f"HTTP {response.status} auf {path}"
        except Exception as exc:
            last_error = str(exc)
    return {"ok": False, "status": "Frigate API nicht erreichbar", "url": display_url(url), "error": last_error}


def event_loop() -> None:
    interval = max(1, int(config.get("event_interval_seconds") or 10))
    LOG.info("event loop started demo_mode=%s interval=%ss camera=%s", config.get("demo_mode"), interval, camera_status(config).get("name"))
    while state.get("running"):
        frigate = config.get("frigate", {}) if isinstance(config.get("frigate"), dict) else {}
        if not bool(config.get("demo_mode", False)) and bool(frigate.get("enabled")) and bool(frigate.get("person_count_enabled", True)) and str(frigate.get("api_url") or "").strip():
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
    return jsonify({"ok": True, "config": safe_config(config), "raw_config": safe_config(load_raw_options()), "storage_status": storage_status()})


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
    return jsonify({"ok": True, "config": safe_config(config), "raw_config": safe_config(load_raw_options()), "storage_status": storage_status(), "status": _status()})


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


@app.post("/api/test/mqtt")
def api_test_mqtt():
    payload = request.get_json(silent=True) or {}
    mqtt = payload.get("mqtt") if isinstance(payload.get("mqtt"), dict) else config.get("mqtt", {}) if isinstance(config.get("mqtt"), dict) else {}
    result = test_mqtt_settings(mqtt)
    result.update({"enabled": bool(mqtt.get("enabled")), "host": str(mqtt.get("host") or ""), "port": int(mqtt.get("port") or 0), "connected": bool(publisher.status().get("connected"))})
    return jsonify(result), 200 if result.get("ok") else 502


@app.post("/api/test/frigate")
def api_test_frigate():
    payload = request.get_json(silent=True) or {}
    frigate = payload.get("frigate") if isinstance(payload.get("frigate"), dict) else config.get("frigate", {}) if isinstance(config.get("frigate"), dict) else {}
    result = test_frigate_api_url(str(frigate.get("api_url") or ""))
    return jsonify(result), 200 if result.get("ok") else 502


@app.post("/api/test/rtsp")
def api_test_rtsp():
    payload = request.get_json(silent=True) or {}
    camera = payload.get("camera") if isinstance(payload.get("camera"), dict) else config.get("camera", {}) if isinstance(config.get("camera"), dict) else {}
    result = test_rtsp_url(str(camera.get("rtsp_url") or ""))
    return jsonify(result), 200 if result.get("ok") else 502


@app.post("/api/test/snapshot")
def api_test_snapshot():
    payload = request.get_json(silent=True) or {}
    camera = payload.get("camera") if isinstance(payload.get("camera"), dict) else config.get("camera", {}) if isinstance(config.get("camera"), dict) else {}
    snapshot_url = str(camera.get("snapshot_url") or "").strip()
    if not snapshot_url:
        return jsonify({"ok": False, "status": "Snapshot URL nicht gesetzt"}), 400
    parts = urlsplit(snapshot_url)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return jsonify({"ok": False, "status": "ungueltige Snapshot URL"}), 400
    try:
        req = Request(snapshot_url, headers={"User-Agent": "frigate-face-bridge"})
        with urlopen(req, timeout=5) as response:
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
            return jsonify({"ok": response.status < 400 and content_type.startswith("image/"), "status": "Bild erreichbar" if content_type.startswith("image/") else "Antwort ist kein Bild", "content_type": content_type, "url": redact_url(snapshot_url)})
    except Exception as exc:
        LOG.warning("snapshot test failed url=%s error=%s", redact_url(snapshot_url), exc)
        return jsonify({"ok": False, "status": "Snapshot nicht erreichbar", "url": redact_url(snapshot_url)}), 502


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
    LOG.info("Frigate Face Bridge starting version=%s", APP_VERSION)
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
