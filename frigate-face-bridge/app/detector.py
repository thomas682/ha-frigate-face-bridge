from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any


class DemoDetector:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._rng = random.Random()

    def detect(self) -> dict[str, Any]:
        camera = self.config.get("camera", {})
        enabled_faces = [f.get("name") for f in self.config.get("known_faces", []) if f.get("enabled") and f.get("name")]
        selected = self._rng.sample(enabled_faces, k=self._rng.randint(0, min(2, len(enabled_faces)))) if enabled_faces else []
        person_count = self._rng.randint(0, 3)
        unknown_faces = self._rng.randint(0, 1) if person_count else 0
        return {
            "camera": camera.get("name") or "camera",
            "person_count": person_count,
            "known_faces": selected,
            "unknown_faces": unknown_faces,
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "source": "frigate_face_bridge",
            "demo_mode": True,
            "confidence": round(self._rng.uniform(0.72, 0.98), 2) if person_count else 0.0,
            "boxes": [],
        }


class PlaceholderDetector:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def detect(self) -> dict[str, Any]:
        camera = self.config.get("camera", {})
        return {
            "camera": camera.get("name") or "camera",
            "person_count": 0,
            "known_faces": [],
            "unknown_faces": 0,
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "source": "frigate_face_bridge",
            "demo_mode": False,
            "confidence": 0.0,
            "boxes": [],
            "status": "camera detection is not implemented yet",
        }


def create_detector(config: dict[str, Any]) -> DemoDetector | PlaceholderDetector:
    if config.get("demo_mode", True):
        return DemoDetector(config)
    return PlaceholderDetector(config)
