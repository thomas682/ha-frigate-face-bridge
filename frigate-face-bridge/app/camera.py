from __future__ import annotations

from typing import Any

from config_loader import display_url


def camera_status(config: dict[str, Any]) -> dict[str, Any]:
    camera = config.get("camera", {}) if isinstance(config.get("camera"), dict) else {}
    return {
        "name": camera.get("name") or "",
        "host": camera.get("host") or "",
        "rtsp_configured": bool(camera.get("rtsp_url")),
        "snapshot_configured": bool(camera.get("snapshot_url")),
        "rtsp_url": display_url(str(camera.get("rtsp_url") or "")),
        "snapshot_url": display_url(str(camera.get("snapshot_url") or "")),
        "detect_width": camera.get("detect_width"),
        "detect_height": camera.get("detect_height"),
        "detect_fps": camera.get("detect_fps"),
    }
