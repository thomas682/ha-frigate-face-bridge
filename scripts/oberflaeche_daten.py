#!/usr/bin/env python3
"""Erzeugt echte API-Antworten fuer die Oberflaechen-Pruefung.

scripts/pruefung-oberflaeche.mjs fuehrt app.js unter einem DOM-Ersatz aus. Mit leeren
Antworten liefe dort nur der Leerzustand; erst echte /api/status- und /api/config-Daten
mit einem Erkennungsereignis fuehren durch die Zeichenwege fuer Namen, Hund, Ansagen
und Verlauf. Die Daten kommen deshalb aus der App selbst (Flask-Testclient, ohne Netz,
ohne Kamera, ohne MQTT) und nicht aus einer gepflegten Kopie, die veralten koennte.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "frigate-face-bridge" / "app"


def build_responses() -> dict[str, object]:
    """Startet die App ohne Optionsdatei und liefert die Antworten der Status-Endpunkte."""
    with tempfile.TemporaryDirectory() as data_dir:
        os.environ["ADDON_CONFIG_FILE"] = str(ROOT / "frigate-face-bridge" / "config.yaml")
        os.environ["OPTIONS_FILE"] = str(Path(data_dir) / "options.json")
        os.environ["FACE_REGISTRY_FILE"] = str(Path(data_dir) / "faces.json")
        sys.path.insert(0, str(APP_DIR))
        spec = importlib.util.spec_from_file_location("face_bridge_main", APP_DIR / "main.py")
        if spec is None or spec.loader is None:
            raise RuntimeError("main.py kann nicht geladen werden")
        main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main)
        from detector import DemoDetector

        event = DemoDetector(main.config).detect()
        event.update({"person_count": 2, "known_faces": ["Person A"], "unknown_faces": 1, "dog_count": 1})
        event["maja_present"] = True
        event["recognized_entities"] = ["Person A", "Hund"]
        with main.state_lock:
            main.state["last_event"] = event
            main.state["event_count"] = 1
            main.record_event(event)

        client = main.app.test_client()
        responses: dict[str, object] = {}
        for path in ("api/status", "api/config", "api/history", "api/faces"):
            response = client.get(f"/{path}")
            if response.status_code != 200:
                raise RuntimeError(f"/{path} antwortet mit {response.status_code}")
            responses[path] = response.get_json()
        return responses


def main() -> int:
    json.dump(build_responses(), sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
