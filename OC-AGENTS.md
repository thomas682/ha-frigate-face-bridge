# OpenCode Agenten und AoE Sessions

Diese Datei beschreibt die geplanten Rollen fuer mehrere OpenCode/AoE-Sessions.

Die projektlokalen Agenten liegen unter `.opencode/agents/` und koennen fuer neue OpenCode-Sessions genutzt werden. Nach Aenderungen an diesen Dateien muss OpenCode neu gestartet werden, damit die Konfiguration geladen wird.

## Startrollen

- `oc-orchestrator`: Koordination, Issues, Handoffs, GO-Abfragen.
- `oc-ha-dashboard`: Home Assistant Dashboards, Lovelace, Mobile Views.
- `oc-ha-addon`: Home Assistant Add-ons, `config.yaml`, Docker, Ingress, Tests.
- `oc-facebridge`: Frigate Face Bridge, Frigate, go2rtc, MQTT, Runtime.
- `oc-infra`: Docker, Portainer, Homepage, Netzwerk, lokale Dienste.
- `oc-review`: Review, Tests, Security, Versionen, Commit-/Push-Pruefung.

## Erweiterte Rollen

- `oc-docs`: README, ROADMAP, Changelog, Runbooks, GitHub Issues.
- `oc-holidayplanner`: Holiday Planner Domain, Kalender, Reisen, Packlisten.
- `oc-iphone-ui`: iPhone/iPad UI, PWA, Touch-Layouts.
- `oc-imac-apps`: macOS/iMac Apps, LaunchAgents, lokale Webdienste.

## Gemeinsame Regeln

- Deutsch als Arbeitssprache.
- Keine Secrets, Tokens, Passwoerter oder vollstaendige RTSP-URLs committen.
- Lokale Zugangsdaten nur in der ignorierten `ACCESS.md` oder im Passwortmanager speichern.
- App- oder Add-on-relevante Aenderungen brauchen Version, Changelog und Doku.
- Nach freigegebenen Aenderungen: Tests ausfuehren, Commit erstellen und pushen, sofern der Nutzer nichts anderes sagt.
- Neue Docker-/Webdienste sollen nach Moeglichkeit in `homepage.localdomain` sichtbar oder dokumentiert sein.
- Live-only Aenderungen klar als solche markieren und lokal dokumentieren.

## Empfohlene AoE Nutzung

1. AoE installieren und starten.
2. Sessions mit den Rollen `oc-orchestrator`, `oc-ha-dashboard`, `oc-ha-addon`, `oc-infra` und `oc-review` anlegen.
3. Aufgaben ueber GitHub Issues oder Handoff-Dateien koordinieren.
4. Spezialagenten liefern Ergebnisse an `oc-orchestrator` zurueck.
5. `oc-review` prueft vor Commit/Push oder Deployment.

## Repository-spezifische Pflichtchecks

- `python -m py_compile frigate-face-bridge/app/*.py`
- `pytest`
- `git diff --check`
- Secret-/Credential-Pruefung vor Commit.
