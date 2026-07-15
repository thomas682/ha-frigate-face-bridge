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
import announcements
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
    assert data["camera"]["name"] == ""
    assert data["version"] == (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def test_addon_metadata_version_matches_canonical_version():
    config_text = (ROOT / "frigate-face-bridge" / "config.yaml").read_text(encoding="utf-8")
    expected = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert f'version: "{expected}"' in config_text


def test_read_version_supports_actual_addon_layout(monkeypatch):
    addon_version = Path("/app/VERSION")

    def fake_read_text(path, encoding):
        if path == addon_version:
            return "2026.07.003\n"
        raise FileNotFoundError(path)

    monkeypatch.setattr(module, "APP_DIR", Path("/app"))
    monkeypatch.setattr(Path, "read_text", fake_read_text)

    assert module.read_version() == "2026.07.003"


def test_read_version_returns_unknown_when_version_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "APP_DIR", tmp_path / "app")

    assert module.read_version() == "unbekannt"


def test_read_version_returns_unknown_when_version_is_empty(tmp_path, monkeypatch):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "VERSION").write_text(" \n", encoding="utf-8")
    monkeypatch.setattr(module, "APP_DIR", app_dir)

    assert module.read_version() == "unbekannt"


def test_status_exposes_communication_without_secret_urls():
    original = json.loads(json.dumps(module.config))
    try:
        module.config["camera"].update({"host": "camera.local", "rtsp_url": "rtsp://user:pass@camera.local:8554/stream", "snapshot_url": "http://camera.local/snap.jpg"})
        module.config["frigate"].update({"enabled": True, "api_url": "http://frigate.local:5000", "events_topic": "frigate/events", "camera_name": "wohnzimmer"})
        module.config["mqtt"].update({"enabled": True, "host": "core-mosquitto", "port": 1883, "topic_prefix": "ha/frigate_face_bridge"})
        client = module.app.test_client()

        data = client.get("/api/status").get_json()

        communication = data["communication"]
        assert communication["homepage_url"] == "http://homeassistant.localdomain:8123/b3b46a83_frigate_face_bridge"
        assert communication["direct_status_url"] == "http://fossflow.localdomain:8099/health"
        assert communication["elements"]["camera"]["host"] == "camera.local"
        assert communication["elements"]["frigate"]["api"]["display"] == "http://frigate.local:5000"
        assert communication["elements"]["mqtt"]["host"] == "core-mosquitto"
        assert "user:pass" not in json.dumps(communication)
    finally:
        module.config.clear()
        module.config.update(original)


def test_default_camera_options_do_not_force_old_example_values():
    config = config_loader.load_runtime_config({})

    assert config["camera"]["name"] == ""
    assert config["camera"]["host"] == ""


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
    module.announcement_history.clear()
    module.record_event({"timestamp": "2026-06-04T12:00:00Z", "camera": "garage", "source": "test", "person_count": 2, "dog_count": 1, "maja_present": True, "recognized_entities": ["Thomas", "Maja"]})
    client = module.app.test_client()

    response = client.get("/api/history")

    assert response.status_code == 200
    data = response.get_json()
    assert data["history"][-1]["dog_count"] == 1
    assert data["history"][-1]["recognized_entities"] == ["Thomas", "Maja"]
    assert "announcement_history" in module._status()


def test_announcement_manager_speaks_new_entities_and_cools_down(monkeypatch):
    monkeypatch.setattr(announcements.random, "choice", lambda items: "Hallo {names}.")
    manager = announcements.AnnouncementManager()
    config = {"frigate": {"dog_name": "Maja"}, "announcements": {"enabled": True, "global_cooldown_seconds": 0, "entity_cooldown_seconds": 300}}

    first = manager.build({"timestamp": "2026-06-04T12:00:00Z", "known_faces": ["Thomas"], "unknown_faces": 1, "dog_count": 1}, config, now=1000)
    second = manager.build({"timestamp": "2026-06-04T12:00:05Z", "known_faces": ["Thomas"], "unknown_faces": 1, "dog_count": 1}, config, now=1005)
    third = manager.build({"timestamp": "2026-06-04T12:01:00Z", "known_faces": ["Thomas", "Birgit"], "unknown_faces": 0, "dog_count": 0}, config, now=1060)

    assert first["should_speak"] is True
    assert first["text"] == "Hallo Thomas, Maja und eine unbekannte Person."
    assert second["should_speak"] is False
    assert second["suppressed_reason"] == "entity_cooldown"
    assert third["should_speak"] is True
    assert third["spoken_entities"] == ["Birgit"]


def test_announcement_manager_uses_custom_text_and_disabled_entities():
    manager = announcements.AnnouncementManager()
    config = {"frigate": {"dog_name": "Maja"}, "announcements": {"enabled": True, "disabled_entities": "Maja", "custom_texts": "Thomas=Thomas ist da."}}

    event = manager.build({"known_faces": ["Thomas"], "dog_count": 1, "unknown_faces": 0}, config, now=1000)

    assert event["should_speak"] is True
    assert event["text"] == "Thomas ist da."
    assert event["entities"] == ["Thomas"]


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
    assert payloads["frigate_face_bridge_garage_g3_flex_announcement_text"]["state_topic"] == "ha/frigate_face_bridge/garage_g3_flex/announcement_text"
    assert payloads["frigate_face_bridge_garage_g3_flex_announcement_should_speak"]["value_template"] == "{{ 'on' if value_json.should_speak else 'off' }}"
    assert payloads["frigate_face_bridge_garage_g3_flex_recognition_log"]["state_topic"] == "ha/frigate_face_bridge/garage_g3_flex/recognition_log"
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

    publisher.publish_event({"camera": "garage", "timestamp": "2026-06-04T12:00:01Z", "person_count": 1, "announcement": {"text": "Thomas ist da.", "should_speak": True, "entities": ["Thomas"], "log_text": "Thomas ist da.", "timestamp": "2026-06-04T12:00:01Z"}})

    payloads = {topic: payload for topic, payload in published}
    assert payloads["ha/frigate_face_bridge/garage/terrace_door_open"]["terrace_door_open"] is True
    assert payloads["ha/frigate_face_bridge/garage/terrace_door_confidence"]["terrace_door_confidence"] == 0.87
    assert payloads["ha/frigate_face_bridge/garage/last_event"]["terrace_door_last_changed"] == "2026-06-04T12:00:00Z"
    assert payloads["ha/frigate_face_bridge/garage/announcement_text"]["text"] == "Thomas ist da."
    assert payloads["ha/frigate_face_bridge/garage/announcement_should_speak"]["should_speak"] is True
    assert payloads["ha/frigate_face_bridge/garage/recognition_log"]["text"] == "Thomas ist da."


def test_mqtt_history_masks_secrets_and_urls():
    publisher = mqtt_client.MqttPublisher({"mqtt": {"enabled": True, "topic_prefix": "ha/frigate_face_bridge"}, "camera": {"name": "garage"}})

    publisher.publish_raw(
        "ha/frigate_face_bridge/garage/test",
        {"password": "secret", "rtsp_url": "rtsp://user:pass@camera.local:7447/private", "name": "Thomas"},
    )

    history = publisher.history()
    assert history[-1]["direction"] == "out"
    assert history[-1]["topic"] == "ha/frigate_face_bridge/garage/test"
    assert history[-1]["payload"]["password"] == "***"
    assert "user:pass" not in history[-1]["payload"]["rtsp_url"]
    assert history[-1]["payload"]["name"] == "Thomas"

    publisher.publish_raw("ha/frigate_face_bridge/garage/raw", "token=abc123 status=ok")
    assert publisher.history()[-1]["payload"] == "token=*** status=ok"


def test_status_exposes_mqtt_history_and_output_topics():
    module.publisher.publish_raw("ha/frigate_face_bridge/garage/test", {"known_faces": ["Thomas"]})

    status = module._status()

    assert status["mqtt_history"][-1]["topic"] == "ha/frigate_face_bridge/garage/test"
    assert any(topic.endswith("/known_faces") for topic in status["mqtt_output_topics"])


def test_mqtt_discovery_can_be_disabled():
    publisher = mqtt_client.MqttPublisher({"mqtt": {"enabled": True, "discovery": False}, "camera": {"name": "garage"}})

    assert publisher.discovery_configs() == []


def test_config_validates_mqtt_discovery_defaults():
    config = config_loader.validate_config({"mqtt": {"enabled": False, "discovery": True, "discovery_prefix": ""}})

    assert config["mqtt"]["discovery"] is True
    assert config["mqtt"]["discovery_prefix"] == "homeassistant"


def test_missing_demo_mode_runtime_default_is_false(tmp_path, monkeypatch):
    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps({"mqtt": {"topic_prefix": "/custom/prefix/"}}), encoding="utf-8")
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", options_file)

    config = config_loader.load_config()

    assert config["demo_mode"] is False
    assert json.loads(options_file.read_text(encoding="utf-8")) == {"mqtt": {"topic_prefix": "/custom/prefix/"}}


def test_existing_demo_mode_values_are_preserved_in_raw_options(tmp_path, monkeypatch):
    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps({"demo_mode": True}), encoding="utf-8")
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", options_file)

    assert config_loader.load_config()["demo_mode"] is True
    assert config_loader.load_raw_options()["demo_mode"] is True

    options_file.write_text(json.dumps({"demo_mode": False}), encoding="utf-8")
    assert config_loader.load_config()["demo_mode"] is False
    assert config_loader.load_raw_options()["demo_mode"] is False


def test_api_config_exposes_raw_options_without_defaults(tmp_path, monkeypatch):
    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps({"mqtt": {"topic_prefix": "/custom/prefix/"}}), encoding="utf-8")
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", options_file)
    module.config.clear()
    module.config.update(config_loader.load_config())
    client = module.app.test_client()

    response = client.get("/api/config")

    data = response.get_json()
    assert response.status_code == 200
    assert data["config"]["mqtt"]["topic_prefix"] == "custom/prefix"
    assert data["raw_config"] == {"mqtt": {"topic_prefix": "/custom/prefix/"}}


def test_save_app_config_preserves_masked_mqtt_password(tmp_path, monkeypatch):
    options_file = tmp_path / "options.json"
    options_file.write_text(json.dumps({"mqtt": {"password": "real-secret"}}), encoding="utf-8")
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", options_file)

    config_loader.save_app_config({"mqtt": {"password": "re***et", "host": "core-mosquitto"}})

    stored = json.loads(options_file.read_text(encoding="utf-8"))
    assert stored["mqtt"]["password"] == "real-secret"
    assert stored["mqtt"]["host"] == "core-mosquitto"


def test_partial_app_config_does_not_overwrite_existing_values(tmp_path, monkeypatch):
    options_file = tmp_path / "options.json"
    options_file.write_text(
        json.dumps({"mqtt": {"username": "bridge", "password": "real-secret", "host": "core-mosquitto"}, "frigate": {"events_topic": "frigate/events"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", options_file)
    client = module.app.test_client()

    response = client.post("/api/config", json={"mqtt": {"enabled": True}})

    assert response.status_code == 200
    stored = json.loads(options_file.read_text(encoding="utf-8"))
    assert stored["mqtt"]["enabled"] is True
    assert stored["mqtt"]["username"] == "bridge"
    assert stored["mqtt"]["password"] == "real-secret"
    assert stored["frigate"]["events_topic"] == "frigate/events"


def test_config_api_exposes_secret_and_url_status(tmp_path, monkeypatch):
    options_file = tmp_path / "options.json"
    options_file.write_text(
        json.dumps({"mqtt": {"username": "bridge", "password": "real-secret"}, "camera": {"rtsp_url": "rtsp://user:pass@camera/stream", "snapshot_url": "http://camera/snap.jpg"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", options_file)
    module.config.clear()
    module.config.update(config_loader.load_config())
    client = module.app.test_client()

    data = client.get("/api/config").get_json()

    assert data["storage_status"]["mqtt_username_set"] is True
    assert data["storage_status"]["mqtt_password_set"] is True
    assert data["storage_status"]["rtsp_url_set"] is True
    assert data["storage_status"]["snapshot_url_set"] is True
    assert "real-secret" not in json.dumps(data)
    assert "user:pass" not in json.dumps(data)


def test_rtsp_test_endpoint_uses_masked_url(monkeypatch):
    module.config["camera"]["rtsp_url"] = "rtsp://user:pass@camera.local:7447/private"
    monkeypatch.setattr(module, "_tcp_test", lambda host, port, timeout=3.0: {"ok": True, "status": "TCP erreichbar", "host": host, "port": port})
    client = module.app.test_client()

    response = client.post("/api/test/rtsp")

    data = response.get_json()
    assert response.status_code == 200
    assert data["ok"] is True
    assert data["host"] == "camera.local"
    assert "user:pass" not in data["url"]


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


def test_update_app_config_accepts_announcement_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", tmp_path / "options.json")
    client = module.app.test_client()

    response = client.post(
        "/api/config",
        json={"announcements": {"enabled": True, "announce_unknown": False, "global_cooldown_seconds": 30, "entity_cooldown_seconds": 120, "disabled_entities": "Klaus", "custom_texts": "Thomas=Hallo Thomas."}},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["config"]["announcements"]["announce_unknown"] is False
    assert data["config"]["announcements"]["global_cooldown_seconds"] == 30
    assert data["config"]["announcements"]["entity_cooldown_seconds"] == 120
    assert data["config"]["announcements"]["disabled_entities"] == "Klaus"
    assert data["config"]["announcements"]["custom_texts"] == "Thomas=Hallo Thomas."


def test_update_app_config_rejects_invalid_topic(tmp_path, monkeypatch):
    monkeypatch.setattr(config_loader, "OPTIONS_FILE", tmp_path / "options.json")
    client = module.app.test_client()

    response = client.post("/api/config", json={"mqtt": {"topic_prefix": "bad topic/#"}})

    assert response.status_code == 400
    assert response.get_json()["ok"] is False
