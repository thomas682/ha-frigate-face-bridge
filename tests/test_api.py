import importlib.util
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "frigate-face-bridge" / "app"
os.environ.setdefault("ADDON_CONFIG_FILE", str(ROOT / "frigate-face-bridge" / "config.yaml"))
os.environ.setdefault("OPTIONS_FILE", str(ROOT / "tests" / "missing-options.json"))
sys.path.insert(0, str(APP_DIR))

import config_loader
import detector
import face_recognition
import frigate_api
import frigate_events
import mqtt_client

spec = importlib.util.spec_from_file_location("face_bridge_main", APP_DIR / "main.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_health():
    client = module.app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_status_json():
    client = module.app.test_client()
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["camera"]["name"] == "garage_g3_flex"


def test_config_redacts_secrets():
    module.config["mqtt"]["password"] = "very-secret"
    credentials = "user:pass"
    module.config["camera"]["rtsp_url"] = f"rtsp://{credentials}@192.168.2.241:7447/stream"
    module.config["camera"]["snapshot_url"] = "http://token@example.local/snap.jpeg?secret=abc"
    client = module.app.test_client()
    data = client.get("/api/config").get_json()["config"]
    assert data["mqtt"]["password"] != "very-secret"
    assert credentials not in data["camera"]["rtsp_url"]
    assert "/stream" not in data["camera"]["rtsp_url"]
    assert "secret=abc" not in data["camera"]["snapshot_url"]


def test_status_redacts_camera_urls():
    module.config["camera"]["rtsp_url"] = "rtsps://192.168.2.1:7441/private-token?enableSrtp"
    module.config["camera"]["snapshot_url"] = "http://user:pass@192.168.2.241/snap.jpeg"
    client = module.app.test_client()

    data = client.get("/api/status").get_json()

    assert data["camera"]["rtsp_url"] == "rtsps://192.168.2.1:7441/***"
    assert data["camera"]["snapshot_url"] == "http://192.168.2.241/***"


def test_update_camera_config_writes_options(tmp_path, monkeypatch):
    options_file = tmp_path / "options.json"
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", options_file)
    client = module.app.test_client()

    response = client.post(
        "/api/config/camera",
        json={"camera": {"name": "Garage G3", "host": "192.168.2.241", "snapshot_url": "http://192.168.2.241/snap.jpg"}},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["camera"]["name"] == "Garage_G3"
    assert data["camera"]["host"] == "192.168.2.241"
    assert options_file.exists()


def test_update_camera_rejects_invalid_host(tmp_path, monkeypatch):
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", tmp_path / "options.json")
    client = module.app.test_client()

    response = client.post("/api/config/camera", json={"camera": {"host": "bad host;rm"}})

    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_snapshot_requires_configured_url():
    module.config["camera"]["snapshot_url"] = ""
    client = module.app.test_client()

    response = client.get("/api/camera/snapshot")

    assert response.status_code == 400
    assert response.get_json()["ok"] is False


class _FakeSnapshotResponse:
    headers = {"Content-Type": "image/jpeg; charset=binary"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size):
        return b"jpeg-bytes"


def test_snapshot_detector_captures_image(monkeypatch):
    monkeypatch.setattr(detector, "urlopen", lambda req, timeout: _FakeSnapshotResponse())
    instance = detector.create_detector({"demo_mode": False, "camera": {"name": "garage", "snapshot_url": "http://camera/snap.jpg"}})

    event = instance.detect()

    assert event["demo_mode"] is False
    assert event["snapshot_available"] is True
    assert event["snapshot_content_type"] == "image/jpeg"
    assert event["snapshot_bytes"] == len(b"jpeg-bytes")
    assert event["person_count"] == 0


def test_snapshot_detector_reports_fetch_failure(monkeypatch):
    def fail(req, timeout):
        raise OSError("network down")

    monkeypatch.setattr(detector, "urlopen", fail)
    instance = detector.create_detector({"demo_mode": False, "camera": {"name": "garage", "snapshot_url": "http://camera/snap.jpg"}})

    event = instance.detect()

    assert event["snapshot_available"] is False
    assert event["status"] == "snapshot fetch failed"


def test_frigate_person_event_creates_detection_event():
    event = frigate_events.parse_frigate_event(
        '{"type":"new","after":{"id":"abc123","camera":"garage_g3_flex","label":"person","score":0.91,"box":[1,2,3,4]}}',
        {"camera": {"name": "garage_g3_flex"}, "frigate": {"camera_name": "garage_g3_flex"}},
    )

    assert event is not None
    assert event["source"] == "frigate_mqtt"
    assert event["camera"] == "garage_g3_flex"
    assert event["person_count"] == 1
    assert event["unknown_faces"] == 1
    assert event["confidence"] == 0.91
    assert event["boxes"] == [[1, 2, 3, 4]]


def test_frigate_non_person_event_is_ignored():
    event = frigate_events.parse_frigate_event(
        '{"type":"new","after":{"id":"abc123","camera":"garage_g3_flex","label":"car","score":0.91}}',
        {"camera": {"name": "garage_g3_flex"}, "frigate": {"camera_name": "garage_g3_flex"}},
    )

    assert event is None


def test_frigate_event_filters_other_camera():
    event = frigate_events.parse_frigate_event(
        '{"type":"new","after":{"id":"abc123","camera":"front_door","label":"person","score":0.91}}',
        {"camera": {"name": "garage_g3_flex"}, "frigate": {"camera_name": "garage_g3_flex"}},
    )

    assert event is None


class _FakeFrigateResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size):
        return json.dumps(self.payload).encode("utf-8")


def test_active_person_count_event_counts_in_progress_persons(monkeypatch):
    def fake_urlopen(req, timeout):
        assert "camera=garage_g3_flex" in req.full_url
        assert "in_progress=1" in req.full_url
        if "label=dog" in req.full_url:
            return _FakeFrigateResponse([])
        return _FakeFrigateResponse(
            [
                {"id": "a", "camera": "garage_g3_flex", "label": "person", "end_time": None, "data": {"score": 0.81, "box": [0, 0, 1, 1]}},
                {"id": "b", "camera": "garage_g3_flex", "label": "person", "end_time": None, "data": {"score": 0.74}},
                {"id": "c", "camera": "garage_g3_flex", "label": "car", "end_time": None},
                {"id": "d", "camera": "garage_g3_flex", "label": "person", "end_time": 123.0},
            ]
        )

    monkeypatch.setattr(frigate_api, "urlopen", fake_urlopen)
    event = frigate_api.active_person_count_event(
        {
            "camera": {"name": "garage_g3_flex"},
            "frigate": {"enabled": True, "camera_name": "garage_g3_flex", "api_url": "http://frigate.local:5000", "person_count_enabled": True},
        }
    )

    assert event is not None
    assert event["source"] == "frigate_active_objects"
    assert event["person_count"] == 2
    assert event["unknown_faces"] == 2
    assert event["confidence"] == 0.81
    assert event["frigate_active_event_ids"] == ["a", "b"]


def test_active_object_count_event_counts_dog_and_known_face(monkeypatch):
    def fake_urlopen(req, timeout):
        if "label=person" in req.full_url:
            return _FakeFrigateResponse([{"id": "p1", "camera": "garage_g3_flex", "label": "person", "end_time": None, "sub_label": "Thomas", "data": {"score": 0.8}}])
        if "label=dog" in req.full_url:
            return _FakeFrigateResponse([{"id": "d1", "camera": "garage_g3_flex", "label": "dog", "end_time": None, "data": {"score": 0.7}}])
        return _FakeFrigateResponse([])

    monkeypatch.setattr(frigate_api, "urlopen", fake_urlopen)

    event = frigate_api.active_object_count_event(
        {
            "camera": {"name": "garage_g3_flex"},
            "frigate": {"enabled": True, "camera_name": "garage_g3_flex", "api_url": "http://frigate.local:5000", "person_count_enabled": True, "dog_name": "Maja"},
        }
    )

    assert event["person_count"] == 1
    assert event["dog_count"] == 1
    assert event["maja_present"] is True
    assert event["known_faces"] == ["Thomas"]
    assert event["recognized_entities"] == ["Thomas", "Maja"]


def test_active_person_count_event_requires_api_url():
    assert frigate_api.active_person_count_event({"frigate": {"enabled": True, "api_url": ""}}) is None


def test_frigate_handler_updates_status_and_publishes(monkeypatch):
    published = []
    monkeypatch.setattr(module.publisher, "publish_event", lambda event: published.append(event))

    module.handle_frigate_event(b'{"type":"new","after":{"id":"abc123","camera":"garage_g3_flex","label":"person","score":0.91}}')

    status = module._status()
    assert status["last_event"]["source"] == "frigate_mqtt"
    assert status["frigate_event_count"] >= 1
    assert published[-1]["person_count"] == 1


def test_history_endpoint_returns_recorded_events():
    module.history.clear()
    module.record_event({"timestamp": "2026-06-04T12:00:00Z", "camera": "garage", "source": "test", "person_count": 2, "dog_count": 1, "maja_present": True, "recognized_entities": ["Thomas", "Maja"]})
    client = module.app.test_client()

    response = client.get("/api/history")

    assert response.status_code == 200
    data = response.get_json()
    assert data["history"][-1]["dog_count"] == 1
    assert data["history"][-1]["recognized_entities"] == ["Thomas", "Maja"]


def test_faces_api_creates_local_face(tmp_path, monkeypatch):
    monkeypatch.setattr(face_recognition, "FACE_REGISTRY_FILE", tmp_path / "faces.json")
    client = module.app.test_client()

    response = client.post("/api/faces", json={"name": "Anna Test", "enabled": True})

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["face"]["name"] == "Anna Test"
    assert data["face"]["enabled"] is True
    assert (tmp_path / "faces.json").exists()


def test_faces_api_updates_enabled_state(tmp_path, monkeypatch):
    monkeypatch.setattr(face_recognition, "FACE_REGISTRY_FILE", tmp_path / "faces.json")
    client = module.app.test_client()
    client.post("/api/faces", json={"name": "Anna Test", "enabled": True})

    response = client.patch("/api/faces/Anna Test", json={"enabled": False})

    assert response.status_code == 200
    data = response.get_json()
    assert data["face"]["name"] == "Anna Test"
    assert data["face"]["enabled"] is False


def test_faces_api_rejects_invalid_name(tmp_path, monkeypatch):
    monkeypatch.setattr(face_recognition, "FACE_REGISTRY_FILE", tmp_path / "faces.json")
    client = module.app.test_client()

    response = client.post("/api/faces", json={"name": "../../secret"})

    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_parse_face_match_event_filters_enabled_known_faces(tmp_path, monkeypatch):
    monkeypatch.setattr(face_recognition, "FACE_REGISTRY_FILE", tmp_path / "faces.json")
    config = {"camera": {"name": "garage"}, "known_faces": [{"name": "Thomas", "enabled": True}, {"name": "Marie", "enabled": False}], "face_recognition": {"min_confidence": 0.8}}

    event = face_recognition.parse_face_match_event(
        {"camera": "garage", "known_faces": [{"name": "Thomas", "confidence": 0.92}, {"name": "Marie", "confidence": 0.99}, {"name": "Birgit", "confidence": 0.99}], "unknown_faces": 1, "confidence": 0.93},
        config,
    )

    assert event is not None
    assert event["source"] == "external_face_recognition"
    assert event["known_faces"] == ["Thomas"]
    assert event["unknown_faces"] == 1
    assert event["person_count"] == 2


def test_parse_face_match_event_ignores_low_confidence(tmp_path, monkeypatch):
    monkeypatch.setattr(face_recognition, "FACE_REGISTRY_FILE", tmp_path / "faces.json")
    config = {"known_faces": [{"name": "Thomas", "enabled": True}], "face_recognition": {"min_confidence": 0.8}}

    event = face_recognition.parse_face_match_event({"known_faces": [{"name": "Thomas", "confidence": 0.5}], "unknown_faces": 0}, config)

    assert event is None


def test_face_event_api_updates_last_event(tmp_path, monkeypatch):
    monkeypatch.setattr(face_recognition, "FACE_REGISTRY_FILE", tmp_path / "faces.json")
    client = module.app.test_client()
    client.post("/api/faces", json={"name": "Thomas", "enabled": True})

    response = client.post("/api/face-events", json={"camera": "garage", "known_faces": [{"name": "Thomas", "confidence": 0.95}], "unknown_faces": 0})

    assert response.status_code == 200
    data = response.get_json()
    assert data["event"]["known_faces"] == ["Thomas"]
    assert module._status()["last_event"]["source"] == "external_face_recognition"
    assert module._status()["face_event_count"] >= 1


def test_mqtt_discovery_configs_reference_existing_topics():
    publisher = mqtt_client.MqttPublisher(
        {
            "mqtt": {"enabled": True, "topic_prefix": "ha/frigate_face_bridge", "discovery": True, "discovery_prefix": "homeassistant"},
            "camera": {"name": "garage_g3_flex"},
        }
    )

    configs = publisher.discovery_configs()
    topics = {topic for topic, payload in configs}
    payloads = {payload["unique_id"]: payload for topic, payload in configs}

    assert "homeassistant/sensor/frigate_face_bridge_garage_g3_flex_person_count/config" in topics
    assert payloads["frigate_face_bridge_garage_g3_flex_person_count"]["state_topic"] == "ha/frigate_face_bridge/garage_g3_flex/person_count"
    assert payloads["frigate_face_bridge_garage_g3_flex_dog_count"]["state_topic"] == "ha/frigate_face_bridge/garage_g3_flex/dog_count"
    assert payloads["frigate_face_bridge_garage_g3_flex_maja_present"]["value_template"] == "{{ 'on' if value_json.maja_present else 'off' }}"
    assert payloads["frigate_face_bridge_garage_g3_flex_terrace_door_open"]["state_topic"] == "ha/frigate_face_bridge/garage_g3_flex/terrace_door_open"
    assert payloads["frigate_face_bridge_garage_g3_flex_terrace_door_confidence"]["value_template"] == "{{ value_json.terrace_door_confidence }}"
    assert payloads["frigate_face_bridge_garage_g3_flex_unknown_faces"]["value_template"] == "{{ value_json.unknown_faces }}"
    assert payloads["frigate_face_bridge_garage_g3_flex_bridge_status"]["availability"]["topic"] == "ha/frigate_face_bridge/status"


def test_mqtt_publish_event_includes_terrace_door_fields():
    publisher = mqtt_client.MqttPublisher(
        {
            "mqtt": {"enabled": True, "topic_prefix": "ha/frigate_face_bridge"},
            "terrace_door": {"open": True, "confidence": 0.87, "last_changed": "2026-06-04T12:00:00Z"},
        }
    )
    published = []
    publisher.client = object()
    publisher.publish_raw = lambda topic, payload, retain=False: published.append((topic, payload))

    publisher.publish_event({"camera": "garage", "timestamp": "2026-06-04T12:00:01Z", "person_count": 1})

    payloads = {topic: payload for topic, payload in published}
    assert payloads["ha/frigate_face_bridge/garage/terrace_door_open"]["terrace_door_open"] is True
    assert payloads["ha/frigate_face_bridge/garage/terrace_door_confidence"]["terrace_door_confidence"] == 0.87
    assert payloads["ha/frigate_face_bridge/garage/last_event"]["terrace_door_last_changed"] == "2026-06-04T12:00:00Z"


def test_mqtt_discovery_can_be_disabled():
    publisher = mqtt_client.MqttPublisher({"mqtt": {"enabled": True, "discovery": False}, "camera": {"name": "garage"}})

    assert publisher.discovery_configs() == []


def test_config_validates_mqtt_discovery_defaults():
    config = config_loader.validate_config({"mqtt": {"enabled": False, "discovery": True, "discovery_prefix": ""}})

    assert config["mqtt"]["discovery"] is True
    assert config["mqtt"]["discovery_prefix"] == "homeassistant"


def test_save_app_config_preserves_masked_mqtt_password(tmp_path, monkeypatch):
    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps({"mqtt": {"password": "real-secret"}}), encoding="utf-8")
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", options_file)

    config_loader.save_app_config({"mqtt": {"password": "re***et", "host": "core-mosquitto"}})

    stored = json.loads(options_file.read_text(encoding="utf-8"))
    assert stored["mqtt"]["password"] == "real-secret"
    assert stored["mqtt"]["host"] == "core-mosquitto"


def test_update_app_config_writes_runtime_settings(tmp_path, monkeypatch):
    options_file = tmp_path / "options.json"
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", options_file)
    client = module.app.test_client()

    response = client.post(
        "/api/config",
        json={
            "demo_mode": True,
            "log_level": "debug",
            "event_interval_seconds": 5,
            "mqtt": {"enabled": False, "host": "core-mosquitto", "port": 1883, "topic_prefix": "ha/frigate_face_bridge", "discovery": True, "discovery_prefix": "homeassistant"},
            "frigate": {"enabled": False, "events_topic": "frigate/events", "camera_name": "Garage G3"},
            "face_recognition": {"enabled": False, "events_topic": "face_recognition/events", "min_confidence": 0.82},
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["config"]["log_level"] == "debug"
    assert data["config"]["event_interval_seconds"] == 5
    assert data["config"]["frigate"]["camera_name"] == "Garage_G3"
    assert data["config"]["face_recognition"]["min_confidence"] == 0.82
    assert options_file.exists()


def test_update_app_config_accepts_frigate_api_person_count(tmp_path, monkeypatch):
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", tmp_path / "options.json")
    client = module.app.test_client()

    response = client.post(
        "/api/config",
        json={"frigate": {"enabled": True, "events_topic": "frigate/events", "camera_name": "Wohnzimmer G3", "api_url": "http://fossflow.localdomain:5000/", "person_count_enabled": True, "person_count_interval_seconds": 3, "dog_name": "Maja!"}},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["config"]["frigate"]["camera_name"] == "Wohnzimmer_G3"
    assert data["config"]["frigate"]["api_url"] == "http://fossflow.localdomain:5000"
    assert data["config"]["frigate"]["person_count_enabled"] is True
    assert data["config"]["frigate"]["person_count_interval_seconds"] == 3
    assert data["config"]["frigate"]["dog_name"] == "Maja"


def test_update_app_config_accepts_terrace_door_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", tmp_path / "options.json")
    client = module.app.test_client()

    response = client.post(
        "/api/config",
        json={"terrace_door": {"enabled": True, "open": True, "confidence": 0.91, "last_changed": "2026-06-04T12:00:00Z"}},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["config"]["terrace_door"]["enabled"] is True
    assert data["config"]["terrace_door"]["open"] is True
    assert data["config"]["terrace_door"]["confidence"] == 0.91
    assert data["status"]["terrace_door"]["last_changed"] == "2026-06-04T12:00:00Z"


def test_update_app_config_rejects_invalid_topic(tmp_path, monkeypatch):
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", tmp_path / "options.json")
    client = module.app.test_client()

    response = client.post("/api/config", json={"mqtt": {"topic_prefix": "bad topic/#"}})

    assert response.status_code == 400
    assert response.get_json()["ok"] is False
