from __future__ import annotations

import json
import logging
from typing import Any

import paho.mqtt.client as mqtt

LOG = logging.getLogger("frigate_face_bridge.mqtt")


class MqttPublisher:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.settings = config.get("mqtt", {}) if isinstance(config.get("mqtt"), dict) else {}
        self.enabled = bool(self.settings.get("enabled"))
        self.connected = False
        self.last_error = ""
        self.client: mqtt.Client | None = None

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

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
        self.connected = False
        LOG.info("MQTT disconnected reason=%s", reason_code)

    def publish_status(self, status: str) -> None:
        self.publish_raw(f"{self.topic_prefix}/status", {"status": status, "source": "frigate_face_bridge"}, retain=True)

    def publish_event(self, event: dict[str, Any]) -> None:
        camera = str(event.get("camera") or "camera")
        self.publish_raw(f"{self.topic_prefix}/{camera}/person_count", {"camera": camera, "person_count": event.get("person_count", 0), "timestamp": event.get("timestamp"), "source": "frigate_face_bridge"})
        self.publish_raw(f"{self.topic_prefix}/{camera}/known_faces", {"camera": camera, "known_faces": event.get("known_faces", []), "timestamp": event.get("timestamp")})
        self.publish_raw(f"{self.topic_prefix}/{camera}/unknown_faces", {"camera": camera, "unknown_faces": event.get("unknown_faces", 0), "timestamp": event.get("timestamp")})
        self.publish_raw(f"{self.topic_prefix}/{camera}/last_event", event)

    def publish_raw(self, topic: str, payload: dict[str, Any], retain: bool = False) -> None:
        if not self.enabled or not self.client:
            return
        try:
            self.client.publish(topic, json.dumps(payload, ensure_ascii=True), qos=0, retain=retain)
        except Exception as exc:
            self.last_error = str(exc)
            LOG.warning("MQTT publish failed on topic %s: %s", topic, exc)

    def status(self) -> dict[str, Any]:
        return {"enabled": self.enabled, "connected": self.connected, "last_error": self.last_error, "topic_prefix": self.topic_prefix}

    def stop(self) -> None:
        if self.client:
            try:
                self.publish_status("offline")
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
