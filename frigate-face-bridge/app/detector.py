from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


MAX_SNAPSHOT_BYTES = 5 * 1024 * 1024


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


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class SnapshotDetector:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def _base_event(self, status: str) -> dict[str, Any]:
        camera = self.config.get("camera", {})
        return {
            "camera": camera.get("name") or "camera",
            "person_count": 0,
            "known_faces": [],
            "unknown_faces": 0,
            "timestamp": _timestamp(),
            "source": "frigate_face_bridge",
            "demo_mode": False,
            "confidence": 0.0,
            "boxes": [],
            "status": status,
            "snapshot_available": False,
        }

    def detect(self) -> dict[str, Any]:
        camera = self.config.get("camera", {})
        snapshot_url = str(camera.get("snapshot_url") or "").strip()
        if not snapshot_url:
            return self._base_event("snapshot_url is not configured")

        parts = urlsplit(snapshot_url)
        if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
            return self._base_event("snapshot_url must use http or https")

        try:
            req = Request(snapshot_url, headers={"User-Agent": "frigate-face-bridge/0.11"})
            with urlopen(req, timeout=8) as response:
                content_type = response.headers.get("Content-Type", "image/jpeg").split(";", 1)[0].lower()
                if not content_type.startswith("image/"):
                    return self._base_event("snapshot response is not an image")
                data = response.read(MAX_SNAPSHOT_BYTES + 1)
        except (OSError, URLError):
            return self._base_event("snapshot fetch failed")

        if len(data) > MAX_SNAPSHOT_BYTES:
            return self._base_event("snapshot is too large")

        event = self._base_event("snapshot captured; detection is not implemented yet")
        event.update({"snapshot_available": True, "snapshot_content_type": content_type, "snapshot_bytes": len(data)})
        return event


def create_detector(config: dict[str, Any]) -> DemoDetector | SnapshotDetector:
    if config.get("demo_mode", True):
        return DemoDetector(config)
    return SnapshotDetector(config)
