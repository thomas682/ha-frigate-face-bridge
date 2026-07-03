# projekt-agents.md

# AGENTS - Frigate Face Bridge

Sprache: Deutsch. Repository-Typ: Home Assistant Add-on.

## Globale Regeln

- Die projektuebergreifenden Agent-Regeln in `/Users/thomasschatz/git/global/global-agents.md` sind verbindlich zu lesen und zu beachten.
- Projektspezifische Regeln in dieser Datei ergaenzen oder verschaerfen die globalen Regeln, duerfen sie aber nicht abschwaechen.
- `/Users/thomasschatz/git/global/global-registry-workflow.md` ist fuer Docker-/Registry-/Portainer-/Deployment-Arbeiten zwingend vorher zu lesen und zu beachten.

## Global Rule Drift

- Der zuletzt gepruefte globale Regelstand wird in `docs/rules/global-rule-baseline.json` dokumentiert.
- Vor nicht-trivialen Arbeiten den Drift-Status mit `python3 /Users/thomasschatz/git/global/scripts/check-global-rule-drift.py /Users/thomasschatz/git/facebri` pruefen.
- Wenn der Baseline-Marker fehlt oder Drift meldet, muss ein Global-Rule-Audit angeboten werden, bevor bestehende Projektlogik an neue globale Regeln angepasst wird.
- `docs/rules/global-rule-baseline.json` wird erst nach abgeschlossenem Audit bzw. bewusster Pruefung mit `--write-baseline` aktualisiert.

## Projektregeln

- Vor der ersten Arbeit pruefen, ob der Repository-Root `frigate-face-bridge/`, `AGENTS.md` und `repository.yaml` enthaelt; bei falschem Root stoppen und melden.
- Das fruehere InfluxBro-Projekt dient nur als Struktur- und Stilvorlage. Inhalte nicht blind kopieren.
- Projektbezogene Secret-Hinweise stehen lokal in `secrets.md`; echte Werte stehen zentral in `/Users/thomasschatz/git/global/globalsecrets.md`. Vor Zugriffen auf Frigate, MQTT, Home Assistant, UniFi/RTSP, NAS, Proxmox, Portainer, Docker/Stack oder externe Face-Recognition-Dienste dort nachsehen und keine Werte in Chat, Issues, Logs oder Commits kopieren.
- Add-on muss ohne Kamera und ohne MQTT starten koennen.
- `demo_mode` darf nicht automatisch aktiviert werden. Bestehende Nutzerwerte fuer `demo_mode` und andere Parameter duerfen bei Start, Neustart oder Update niemals automatisch ueberschrieben, normalisiert oder als Defaults persistiert werden.
- Die Parameterverwaltungsregel in `docs/projekt-parameter-management.md` ist fuer neue Optionen und Config-Migrationen zu beachten.
- Jede freigegebene Aenderung benoetigt eine Versionsanpassung in `frigate-face-bridge/config.yaml` und einen Changelog-Eintrag, sofern der Nutzer nichts anderes explizit sagt.
- Vor Aenderungen ein GitHub-Issue mit Ziel, Umfang und Akzeptanzkriterien erstellen und die Arbeit gegen dieses Issue abschliessen.
- Ein aktives Issue bleibt Arbeitskontext, bis Umsetzung, Pruefung, Version/Changelog, Commit, Push und Issue-Abschluss erledigt sind. Nicht auf andere Issues umschalten, solange das aktive Issue offen ist.
- Nach freigegebenen Aenderungen gehoeren Versionsanpassung, Commit und Push zum Abschluss, sofern der Nutzer nichts anderes sagt und keine hoeher priorisierte Regel blockiert.
- Nach Push bei Versionsaenderung Home Assistant Update/Restart versuchen und Live-Version verifizieren, soweit Zugriff vorhanden ist. Wenn Zugriff fehlt oder der Updatepfad scheitert, den offenen Rest klar melden.
- `projekt-oc-agents.md` ist keine aktive Regelquelle fuer dieses Repository. Falls Inhalte daraus benoetigt werden, werden sie nach `AGENTS.md` ueberfuehrt; ansonsten wird die Datei entfernt.

## Pflichtpruefungen

- `python -m py_compile frigate-face-bridge/app/*.py`
- `pytest` fuer vorhandene Tests
- Bei Docker-/Runtime-Aenderungen Docker-Builds, Docker-Compose-/Stack-Konfigurationen und Container-Neustarts pruefen. Falls erforderlich Docker-Builds patchen, neu bauen und betroffene Container, Docker-Compose-Services, Portainer-Stacks oder Home-Assistant-Add-ons neu starten.
- Wenn eine Aenderung erst nach Neustart wirksam wird, den betroffenen Docker-Container, Stack oder das Add-on neu starten, soweit Zugriff vorhanden ist. Falls Zugriff fehlt, offenen Neustart klar melden.
- Nach Docker-/Runtime-Neustarts Runtime-Status, Logs und relevante Health-/API-Endpunkte verifizieren. Port-Listening allein reicht nicht; ein Dienst gilt erst als bereit, wenn ein Health-/API-Endpunkt erfolgreich und mit gueltigem JSON antwortet.
- Bei Aenderungen an `frigate-face-bridge/app/static/index.html` explizit HTML-Struktur pruefen: Tag-Balance, korrekte Verschachtelung, Tabellen und Section-Grenzen.
- Bei UI-Entfernungen HTML, JS, CSS, API-Aufrufe, Backend-Routen und Doku auf Abhaengigkeiten pruefen; UI-Elemente nicht ohne Ersatz-/Migrationspfad oder klare Begruendung entfernen.
- Sicherheitspruefung auf Secrets, Log-Leaks, unsichere Eingaben, offene Ports und Container-Rechte.
- Bei fehlgeschlagener Pflichtpruefung Arbeit nicht als abgeschlossen melden; Fehler beheben oder blockierenden Rest klar benennen.

## Tool-Hinweise

- Bei `rtk git diff` Pfadtrenner doppelt uebergeben: `rtk git diff -- -- <pfade>`. Das erste `--` wird von RTK verbraucht, das zweite erreicht Git.

## Sicherheit

- MQTT-Passwoerter maskieren.
- RTSP- und Snapshot-URLs vor Logging/API-Ausgabe maskieren.
- Keine Dateizugriffe ausserhalb der Add-on-Konfigurations-/Datenpfade einfuehren.
- Flask-Routen sind Vertrauensgrenzen: Eingaben validieren/normalisieren und klare Fehler ohne Secret-Leaks zurueckgeben.
- Add-on-Rechte nach Least Privilege pruefen: `host_network`, `privileged`, `full_access`, `homeassistant_api`, `ingress`, `ports`, Mounts und Geraetezugriffe.

## Code-Stil

- Python-Imports gruppieren: Standardbibliothek, Drittanbieter, lokale Imports. Ein Import pro Zeile; unbenutzte Imports vermeiden.
- Neue oder geaenderte Python-Funktionen mit Type-Hints versehen, wo sinnvoll.
- Fuer JSON-aehnliche Payloads `dict[str, Any]` verwenden, wenn es zur bestehenden Python-Version passt.
- Keine breiten `except Exception` in reinen Hilfsfunktionen; an HTTP-, Thread- oder Integrationsgrenzen nur bewusst und mit nuetzlicher Fehlermeldung.
- Funktionalen serverseitigen Zustand von reinem UI-/Layout-Zustand trennen. Browser-lokaler UI-Zustand darf funktionale Add-on-Konfiguration nicht ueberschreiben.

## Kontext und Ausgabe

- Abschlussberichte kompakt halten: Issue, Version, Commit/Push, QA, Sicherheit und offene Restpunkte.
