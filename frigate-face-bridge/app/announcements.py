from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from typing import Any


RANDOM_TEXTS = [
    "{names} wurde erkannt.",
    "{names} ist im Haus.",
    "Willkommen, {names}.",
    "Achtung, {names} wurde gesichtet.",
    "{names} ist angekommen.",
    "Ich sehe {names}.",
    "{names} ist jetzt im Bild.",
    "Da ist {names}.",
    "{names} betritt die Szene.",
    "Gute Nachrichten: {names} wurde erkannt.",
    "Hausmeldung: {names} ist da.",
    "Kamera meldet {names}.",
    "{names} wurde gerade entdeckt.",
    "Auftritt von {names}.",
    "{names} schaut vorbei.",
    "System sagt: {names} ist anwesend.",
    "Die Bridge hat {names} erkannt.",
    "{names} ist wieder im Blickfeld.",
    "Erkennung erfolgreich: {names}.",
    "Kurze Info: {names} ist da.",
]


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _csv_set(value: Any) -> set[str]:
    return {item.strip().lower() for item in str(value or "").replace("\n", ",").split(",") if item.strip()}


def _custom_texts(value: Any) -> dict[str, str]:
    texts: dict[str, str] = {}
    for line in str(value or "").splitlines():
        if "=" not in line:
            continue
        key, text = line.split("=", 1)
        key = key.strip().lower()
        text = text.strip()
        if key and text:
            texts[key] = text
    return texts


def _join_names(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " und " + names[-1]


class AnnouncementManager:
    def __init__(self) -> None:
        self.last_global_at = 0.0
        self.last_entity_at: dict[str, float] = {}

    def build(self, event: dict[str, Any], config: dict[str, Any], now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else now
        settings = config.get("announcements", {}) if isinstance(config.get("announcements"), dict) else {}
        enabled = bool(settings.get("enabled", True))
        dog_name = str((config.get("frigate") or {}).get("dog_name") or "Maja").strip() or "Maja"
        disabled = _csv_set(settings.get("disabled_entities"))
        custom = _custom_texts(settings.get("custom_texts"))

        entities: list[dict[str, str]] = []
        if bool(settings.get("announce_known", True)):
            for name in _as_list(event.get("known_faces")):
                if name.lower() not in disabled:
                    entities.append({"key": name.lower(), "name": name, "type": "known"})
        if bool(settings.get("announce_dog", True)) and int(event.get("dog_count") or 0) > 0 and dog_name.lower() not in disabled:
            entities.append({"key": dog_name.lower(), "name": dog_name, "type": "dog"})
        unknown_count = int(event.get("unknown_faces") or 0)
        if bool(settings.get("announce_unknown", True)) and unknown_count > 0 and "unknown" not in disabled and "unbekannt" not in disabled:
            name = "eine unbekannte Person" if unknown_count == 1 else f"{unknown_count} unbekannte Personen"
            entities.append({"key": "unknown", "name": name, "type": "unknown"})

        global_cooldown = max(0, int(settings.get("global_cooldown_seconds") or 0))
        entity_cooldown = max(0, int(settings.get("entity_cooldown_seconds") or 0))
        global_blocked = bool(global_cooldown and now - self.last_global_at < global_cooldown)
        speak_entities = [] if global_blocked else [item for item in entities if not (entity_cooldown and now - self.last_entity_at.get(item["key"], 0.0) < entity_cooldown)]

        names = [item["name"] for item in speak_entities]
        text = self._text(names, speak_entities, custom, bool(settings.get("random_texts_enabled", True))) if enabled and names else ""
        should_speak = bool(enabled and text)
        if should_speak:
            self.last_global_at = now
            for item in speak_entities:
                self.last_entity_at[item["key"]] = now

        all_names = [item["name"] for item in entities]
        log_text = text or (f"Erkannt: {_join_names(all_names)}" if all_names else "Keine ansagefaehige Erkennung")
        suppressed_reason = ""
        if not enabled and entities:
            suppressed_reason = "announcements_disabled"
        elif global_blocked and entities:
            suppressed_reason = "global_cooldown"
        elif entities and not speak_entities:
            suppressed_reason = "entity_cooldown"

        return {
            "timestamp": event.get("timestamp") or _timestamp(),
            "should_speak": should_speak,
            "text": text,
            "entities": all_names,
            "spoken_entities": names,
            "known_faces": _as_list(event.get("known_faces")),
            "dog_count": int(event.get("dog_count") or 0),
            "unknown_faces": unknown_count,
            "suppressed_reason": suppressed_reason,
            "log_text": log_text,
        }

    def _text(self, names: list[str], entities: list[dict[str, str]], custom: dict[str, str], random_enabled: bool) -> str:
        if len(entities) == 1:
            item = entities[0]
            template = custom.get(item["key"]) or custom.get(item["type"]) or custom.get("default")
            if template:
                return template.format(name=item["name"], names=item["name"])
        else:
            template = custom.get("multiple") or custom.get("default")
            if template:
                return template.format(name=_join_names(names), names=_join_names(names))
        template = random.choice(RANDOM_TEXTS) if random_enabled else "{names} wurde erkannt."
        return template.format(name=_join_names(names), names=_join_names(names))
