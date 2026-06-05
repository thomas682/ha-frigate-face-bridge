from __future__ import annotations

import json
import logging
import re
from typing import Any

import paho.mqtt.client as mqtt

LOG = logging.getLogger("frigate_face_bridge.mqtt")


def _slug(value: Any, default: str = "camera") -> str:
    slug = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or default)).strip("_").lower()
    return slug or default


class MqttPublisher:
    def __init__(self, config: dict[str, Any], frigate_event_handler: Any | None = None, face_event_handler: Any | None = None) -> None:
        self.config = config
        self.settings = config.get("mqtt", {}) if isinstance(config.get("mqtt"), dict) else {}
        self.frigate_settings = config.get("frigate", {}) if isinstance(config.get("frigate"), dict) else {}
        self.face_settings = config.get("face_recognition", {}) if isinstance(config.get("face_recognition"), dict) else {}
        self.enabled = bool(self.settings.get("enabled"))
        self.connected = False
        self.last_error = ""
        self.client: mqtt.Client | None = None
        self.frigate_event_handler = frigate_event_handler
        self.face_event_handler = face_event_handler

    @property
    def topic_prefix(self) -> str:
        return str(self.settings.get("topic_prefix") or "ha/frigate_face_bridge").strip().strip("/")

    def connect(self) -> None:
        if not self.enabled:
            LOG.info("MQTT disabled")
            return
        host = str(self.settings.get("host") or "").strip()
        port = int(self.settings.get("port") or 1883)
        if not host:
            self.last_error = "MQTT host is empty"
            LOG.warning(self.last_error)
            return
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="frigate-face-bridge")
            username = str(self.settings.get("username") or "")
            password = str(self.settings.get("password") or "")
            if username or password:
                client.username_pw_set(username, password)
            client.on_connect = self._on_connect
            client.on_disconnect = self._on_disconnect
            client.on_message = self._on_message
            client.connect_async(host, port, keepalive=30)
            client.loop_start()
            self.client = client
            LOG.info("MQTT connecting to %s:%s", host, port)
        except Exception as exc:
            self.last_error = str(exc)
            LOG.warning("MQTT connection setup failed: %s", exc)

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
        self.connected = int(reason_code) == 0 if str(reason_code).isdigit() else str(reason_code) == "Success"
        self.last_error = "" if self.connected else f"connect failed: {reason_code}"
        LOG.info("MQTT connected=%s reason=%s", self.connected, reason_code)
        if self.connected:
            self.publish_status("online")
            self.publish_discovery()
            self._subscribe_event_topic(client, self.frigate_settings, self.frigate_event_handler, "Frigate")
            self._subscribe_event_topic(client, self.face_settings, self.face_event_handler, "Face Recognition")

    def _subscribe_event_topic(self, client: mqtt.Client, settings: dict[str, Any], handler: Any | None, label: str) -> None:
        if not handler or not bool(settings.get("enabled")):
            return
        topic = str(settings.get("events_topic") or "").strip().strip("/")
        if not topic:
            self.last_error = f"{label} events topic is empty"
            LOG.warning(self.last_error)
            return
        try:
            client.subscribe(topic, qos=0)
            LOG.info("MQTT subscribed to %s events topic %s", label, topic)
        except Exception as exc:
            self.last_error = str(exc)
            LOG.warning("MQTT subscribe failed on topic %s: %s", topic, exc)

    def _on_message(self, client: mqtt.Client, userdata: Any, message: Any) -> None:
        payload = getattr(message, "payload", b"")
        if len(payload) > 256 * 1024:
            LOG.warning("ignored oversized MQTT message on topic %s", getattr(message, "topic", ""))
            return
        topic = str(getattr(message, "topic", "")).strip().strip("/")
        face_topic = str(self.face_settings.get("events_topic") or "").strip().strip("/")
        handler = self.face_event_handler if face_topic and topic == face_topic else self.frigate_event_handler
        if not handler:
            return
        try:
            handler(payload)
        except Exception as exc:
            self.last_error = str(exc)
            LOG.warning("MQTT event handler failed: %s", exc)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
        self.connected = False
        LOG.info("MQTT disconnected reason=%s", reason_code)

    def publish_status(self, status: str) -> None:
        self.publish_raw(f"{self.topic_prefix}/status", {"status": status, "source": "frigate_face_bridge"}, retain=True)

    def publish_event(self, event: dict[str, Any]) -> None:
        camera = str(event.get("camera") or "camera")
        self.publish_raw(f"{self.topic_prefix}/{camera}/person_count", {"camera": camera, "person_count": event.get("person_count", 0), "timestamp": event.get("timestamp"), "source": "frigate_face_bridge"})
        self.publish_raw(f"{self.topic_prefix}/{camera}/dog_count", {"camera": camera, "dog_count": event.get("dog_count", 0), "timestamp": event.get("timestamp"), "source": "frigate_face_bridge"})
        self.publish_raw(f"{self.topic_prefix}/{camera}/maja_present", {"camera": camera, "maja_present": bool(event.get("maja_present")), "timestamp": event.get("timestamp"), "source": "frigate_face_bridge"})
        self.publish_raw(f"{self.topic_prefix}/{camera}/known_faces", {"camera": camera, "known_faces": event.get("known_faces", []), "timestamp": event.get("timestamp")})
        self.publish_raw(f"{self.topic_prefix}/{camera}/recognized_entities", {"camera": camera, "recognized_entities": event.get("recognized_entities", event.get("known_faces", [])), "timestamp": event.get("timestamp")})
        self.publish_raw(f"{self.topic_prefix}/{camera}/unknown_faces", {"camera": camera, "unknown_faces": event.get("unknown_faces", 0), "timestamp": event.get("timestamp")})
        announcement = event.get("announcement") if isinstance(event.get("announcement"), dict) else {}
        self.publish_raw(f"{self.topic_prefix}/{camera}/announcement_text", {"camera": camera, "text": announcement.get("text", ""), "should_speak": bool(announcement.get("should_speak")), "timestamp": announcement.get("timestamp") or event.get("timestamp")})
        self.publish_raw(f"{self.topic_prefix}/{camera}/announcement_should_speak", {"camera": camera, "should_speak": bool(announcement.get("should_speak")), "timestamp": announcement.get("timestamp") or event.get("timestamp")})
        self.publish_raw(f"{self.topic_prefix}/{camera}/announcement_entities", {"camera": camera, "entities": announcement.get("entities", []), "timestamp": announcement.get("timestamp") or event.get("timestamp")})
        self.publish_raw(f"{self.topic_prefix}/{camera}/recognition_log", {"camera": camera, "text": announcement.get("log_text", ""), "spoken": bool(announcement.get("should_speak")), "entities": announcement.get("entities", []), "suppressed_reason": announcement.get("suppressed_reason", ""), "timestamp": announcement.get("timestamp") or event.get("timestamp")})
        terrace_door = self.config.get("terrace_door", {}) if isinstance(self.config.get("terrace_door"), dict) else {}
        door_open = bool(event.get("terrace_door_open", terrace_door.get("open", False)))
        door_confidence = float(event.get("terrace_door_confidence", terrace_door.get("confidence", 0.0)) or 0.0)
        door_last_changed = str(event.get("terrace_door_last_changed", terrace_door.get("last_changed") or event.get("timestamp") or ""))
        event_payload = dict(event)
        event_payload["terrace_door_open"] = door_open
        event_payload["terrace_door_confidence"] = door_confidence
        event_payload["terrace_door_last_changed"] = door_last_changed
        self.publish_raw(f"{self.topic_prefix}/{camera}/terrace_door_open", {"camera": camera, "terrace_door_open": door_open, "timestamp": event.get("timestamp"), "source": "frigate_face_bridge"})
        self.publish_raw(f"{self.topic_prefix}/{camera}/terrace_door_confidence", {"camera": camera, "terrace_door_confidence": door_confidence, "timestamp": event.get("timestamp"), "source": "frigate_face_bridge"})
        self.publish_raw(f"{self.topic_prefix}/{camera}/terrace_door_last_changed", {"camera": camera, "terrace_door_last_changed": door_last_changed, "timestamp": event.get("timestamp"), "source": "frigate_face_bridge"})
        self.publish_raw(f"{self.topic_prefix}/{camera}/last_event", event_payload)

    def discovery_configs(self) -> list[tuple[str, dict[str, Any]]]:
        if not bool(self.settings.get("discovery", True)):
            return []
        discovery_prefix = str(self.settings.get("discovery_prefix") or "homeassistant").strip().strip("/")
        if not discovery_prefix:
            return []
        camera_config = self.config.get("camera", {}) if isinstance(self.config.get("camera"), dict) else {}
        camera = str(camera_config.get("name") or "camera")
        camera_slug = _slug(camera)
        base = f"{self.topic_prefix}/{camera}"
        object_base = f"frigate_face_bridge_{camera_slug}"
        availability = {
            "topic": f"{self.topic_prefix}/status",
            "value_template": "{{ value_json.status }}",
            "payload_available": "online",
            "payload_not_available": "offline",
        }
        device = {
            "identifiers": ["frigate_face_bridge"],
            "name": "Frigate Face Bridge",
            "manufacturer": "Frigate Face Bridge",
            "model": "Home Assistant Add-on",
        }
        sensors = [
            ("person_count", "Personen", f"{base}/person_count", "{{ value_json.person_count }}", "mdi:account-group"),
            ("dog_count", "Hunde", f"{base}/dog_count", "{{ value_json.dog_count }}", "mdi:dog"),
            ("maja_present", "Maja anwesend", f"{base}/maja_present", "{{ 'on' if value_json.maja_present else 'off' }}", "mdi:dog-side"),
            ("known_faces", "Bekannte Gesichter", f"{base}/known_faces", "{{ value_json.known_faces | join(', ') }}", "mdi:face-recognition"),
            ("recognized_entities", "Erkannte Personen und Tiere", f"{base}/recognized_entities", "{{ value_json.recognized_entities | join(', ') }}", "mdi:account-eye"),
            ("unknown_faces", "Unbekannte Gesichter", f"{base}/unknown_faces", "{{ value_json.unknown_faces }}", "mdi:account-question"),
            ("announcement_text", "Ansagetext", f"{base}/announcement_text", "{{ value_json.text }}", "mdi:text-to-speech"),
            ("announcement_should_speak", "Ansage ausloesen", f"{base}/announcement_should_speak", "{{ 'on' if value_json.should_speak else 'off' }}", "mdi:bullhorn"),
            ("announcement_entities", "Ansage Entitaeten", f"{base}/announcement_entities", "{{ value_json.entities | join(', ') }}", "mdi:account-voice"),
            ("recognition_log", "Erkennungslog", f"{base}/recognition_log", "{{ value_json.text }}", "mdi:clipboard-text-clock"),
            ("terrace_door_open", "Terrassentuer offen", f"{base}/terrace_door_open", "{{ 'on' if value_json.terrace_door_open else 'off' }}", "mdi:door-sliding-open"),
            ("terrace_door_confidence", "Terrassentuer Confidence", f"{base}/terrace_door_confidence", "{{ value_json.terrace_door_confidence }}", "mdi:gauge"),
            ("terrace_door_last_changed", "Terrassentuer letzte Aenderung", f"{base}/terrace_door_last_changed", "{{ value_json.terrace_door_last_changed }}", "mdi:clock-outline"),
            ("last_event_source", "Letzte Event-Quelle", f"{base}/last_event", "{{ value_json.source }}", "mdi:timeline-clock"),
            ("bridge_status", "Bridge Status", f"{self.topic_prefix}/status", "{{ value_json.status }}", "mdi:connection"),
        ]
        configs = []
        for key, name, state_topic, value_template, icon in sensors:
            unique_id = f"{object_base}_{key}"
            topic = f"{discovery_prefix}/sensor/{unique_id}/config"
            configs.append(
                (
                    topic,
                    {
                        "name": name,
                        "unique_id": unique_id,
                        "object_id": unique_id,
                        "state_topic": state_topic,
                        "value_template": value_template,
                        "availability": availability,
                        "icon": icon,
                        "device": device,
                    },
                )
            )
        return configs

    def publish_discovery(self) -> None:
        if not self.enabled:
            return
        for topic, payload in self.discovery_configs():
            self.publish_raw(topic, payload, retain=True)

    def publish_raw(self, topic: str, payload: dict[str, Any], retain: bool = False) -> None:
        if not self.enabled or not self.client:
            return
        try:
            self.client.publish(topic, json.dumps(payload, ensure_ascii=True), qos=0, retain=retain)
        except Exception as exc:
            self.last_error = str(exc)
            LOG.warning("MQTT publish failed on topic %s: %s", topic, exc)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "connected": self.connected,
            "last_error": self.last_error,
            "topic_prefix": self.topic_prefix,
            "discovery": bool(self.settings.get("discovery", True)),
            "discovery_prefix": str(self.settings.get("discovery_prefix") or "homeassistant").strip().strip("/"),
            "frigate_import": bool(self.frigate_settings.get("enabled")),
            "face_import": bool(self.face_settings.get("enabled")),
        }

    def stop(self) -> None:
        if self.client:
            try:
                self.publish_status("offline")
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
