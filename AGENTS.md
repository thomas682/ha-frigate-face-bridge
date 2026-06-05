# AGENTS - Frigate Face Bridge

Sprache: Deutsch. Repository-Typ: Home Assistant Add-on.

## Arbeitsregeln

- System- und Developer-Anweisungen haben Vorrang vor dieser Datei.
- Aendere nur dieses Repository, sofern der Nutzer nichts anderes explizit freigibt.
- Das fruehere InfluxBro-Projekt dient nur als Struktur- und Stilvorlage. Inhalte nicht blind kopieren.
- Keine Secrets, Tokens, Passwoerter oder vollstaendige RTSP-URLs mit Credentials committen.
- Add-on muss ohne Kamera und ohne MQTT starten koennen.
- `demo_mode: true` bleibt der sichere Standard, bis echte Detection implementiert ist.
- App-relevante Aenderungen benoetigen Versionsanpassung in `frigate-face-bridge/config.yaml` und Changelog-Eintrag.
- Nach freigegebenen Aenderungen gehoeren Versionsanpassung, Commit und Push zum Abschluss, sofern der Nutzer nichts anderes sagt.
- Projektlokale OpenCode-Agenten liegen unter `.opencode/agents/`; Rollen und gemeinsame Regeln sind in `OC-AGENTS.md` beschrieben.
- Neue Docker-/Webdienste sollen nach Moeglichkeit auch in `homepage.localdomain` sichtbar oder dokumentiert sein.
- Globale Suchen auf dem gesamten Laufwerk oder im kompletten Home-Verzeichnis nur ausfuehren, wenn der Nutzer dies explizit freigibt; solche Suchen dauern lange und koennen wie ein haengendes OpenCode wirken.

## Pflichtpruefungen

- `python -m py_compile frigate-face-bridge/app/*.py`
- `pytest` fuer vorhandene Tests
- Bei Docker-/Runtime-Aenderungen nach Moeglichkeit Docker-Build pruefen
- Sicherheitspruefung auf Secrets, Log-Leaks, unsichere Eingaben, offene Ports und Container-Rechte

## Sicherheit

- MQTT-Passwoerter maskieren.
- RTSP- und Snapshot-URLs vor Logging/API-Ausgabe maskieren.
- Keine Shell-Aufrufe mit nutzerkontrollierten Werten ohne strikte Validierung.
- Keine Dateizugriffe ausserhalb der Add-on-Konfigurations-/Datenpfade einfuehren.
