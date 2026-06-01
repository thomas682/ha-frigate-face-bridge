import importlib.util
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "frigate-face-bridge" / "app"
os.environ.setdefault("ADDON_CONFIG_FILE", str(ROOT / "frigate-face-bridge" / "config.yaml"))
os.environ.setdefault("OPTIONS_FILE", str(ROOT / "tests" / "missing-options.json"))
sys.path.insert(0, str(APP_DIR))

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
    client = module.app.test_client()
    data = client.get("/api/config").get_json()["config"]
    assert data["mqtt"]["password"] != "very-secret"
    assert credentials not in data["camera"]["rtsp_url"]
