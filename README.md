# Frigate Face Bridge Add-on Repository

Dieses Repository stellt das Home-Assistant-Add-on `Frigate Face Bridge` bereit.

## Zweck

Frigate Face Bridge ist eine lokale Bruecke fuer UniFi-Kameras, Personen-/Hund-Erkennung, vorbereitete Gesichtserkennung und MQTT-Ausgabe an Home Assistant. Version `0.15.2` liefert eine stabile Add-on-Basis mit sicherer Parameterverwaltung, vollbreiter iPhone-tauglicher Web-UI, Links-Sicht, Schemazeichnung, Testfunktionen fuer MQTT/Frigate/RTSP/Snapshot, Demo-Modus, REST-API, Live-MQTT-Nachrichten, MQTT-Publisher, Kamera-Konfiguration, Snapshot-Vorschau, realer Snapshot-Erfassung, optionalem Frigate-Event-Import, aktivem Frigate-Objektzaehler fuer Personen und Hund, konfigurierbaren Ansagetexten mit Cooldowns, Terrassentuer-Statusfeldern, lokaler Face-Registry, externem Face-Matching-Import, MQTT Discovery und konservativ maskierten Kamera-URLs in API-Ausgaben.

## Architektur

```text
UniFi G3 Flex / UniFi Protect
        -> RTSP / Snapshot
        -> Frigate Face Bridge
        -> MQTT / REST API
        -> Home Assistant
```

Das Add-on ersetzt Frigate nicht. Frigate, Double Take, CompreFace oder eine lokale Face-Recognition-Engine koennen spaeter angebunden werden.

## Installation

1. Home Assistant: `Einstellungen -> Add-ons -> Add-on Store`.
2. Oben rechts `... -> Repositories` oeffnen.
3. Repository-URL eintragen: `https://github.com/thomas682/ha-frigate-face-bridge`.
4. Add-on `Frigate Face Bridge` installieren und starten.
5. Web UI ueber `Open Web UI` oeffnen.

## Aktueller Stand

Aktuelle Add-on-Version: `0.15.2`.

Lokale Bild-Personendetektion und lokale Face-Embedding-Berechnung sind noch nicht implementiert. Externe Matching-Events koennen bereits importiert werden. `demo_mode` ist fuer fehlende/neue Werte nicht automatisch aktiv; bestehende Nutzerwerte werden bei Start, Neustart und Update nicht automatisch ueberschrieben.

Die weiteren Ausbaustufen stehen in `ROADMAP.md`.

## Version 0.15.2

- Ueberblick zeigt eine Schemazeichnung vom Kamera-/UniFi-/Frigate-Datenfluss bis Home Assistant und zurueck zur Bridge-Konfiguration
- Neue Links-Sicht mit anklickbaren Bridge-, Frigate-, go2rtc- und GitHub-Links
- Snapshot-Beispielbutton ergaenzt; Kamera-Name und Host/IP sind fuer neue Installationen neutral leer statt alter Beispielwerte

## Version 0.15.0

- Template fuer sichere Parameter- und UI-Aenderungen in `docs/templates/AGENT_PARAMETER_UI_CHANGE_TEMPLATE.md`
- Web-UI speichert Betriebs- und Kamerakonfiguration als Teilupdate, damit leere Formularfelder keine bestehenden Werte ueberschreiben
- Vollbreite, mobil bedienbare UI mit Statusanzeigen fuer gesetzte MQTT-/Kamera-Secrets, Testbuttons und filterbaren Listen

## Version 0.14.1

- Parameterverwaltungsregel in `docs/PARAMETER_MANAGEMENT.md` dokumentiert
- Gespeicherte Rohoptionen und Runtime-Konfiguration getrennt
- `demo_mode` ist fuer fehlende/neue Werte standardmaessig aus, ohne bestehende Nutzerwerte zu ueberschreiben

## Version 0.14.0

- Navigierbare Web-UI mit Sichten fuer Ueberblick, Live-Daten, MQTT, Erkennungen, Ansagen, Verlauf, Konfiguration und Debug
- Live-MQTT-Nachrichten und Bridge-Ausgabe-Topics sichtbar
- Erkannte Namen, unbekannte Personen, Hunde und Ansagezustand in eigenen Live-Sichten sichtbar

## Version 0.13.0

- Konfigurierbare Sprachausgabe-Ereignisse fuer bekannte Personen, unbekannte Personen und Hund
- Globale und entitaetsbezogene Cooldowns verhindern Daueransagen
- Zufallstexte, eigene Texte und Sperrliste fuer Ansagen in der Web-UI konfigurierbar
- Neue MQTT-/HA-Sensoren fuer Ansagetext, Ansageausloeser, Ansage-Entitaeten und Erkennungslog

## Version 0.12.1

- Personen-Verlauf in der Web-UI als Zeitreihen-Kurvendiagramm statt Balkendiagramm

## Version 0.12.0

- Web-UI im Home-Assistant-Ingress auf helles HA-aehnliches Kartendesign umgestellt
- Kontraste, Schriftgroessen, Formulare, Buttons und Tabellen fuer bessere Lesbarkeit angepasst
- Dark-Mode-Abdunklung entfernt, damit die Seitenleistenansicht stabil hell bleibt

## Version 0.11.0

- Neue MQTT-/API-Felder fuer Terrassentuer: `terrace_door_open`, `terrace_door_confidence`, `terrace_door_last_changed`
- MQTT Discovery fuer Terrassentuer-Status, Confidence und letzte Aenderung
- Web-UI-Konfiguration und Statusanzeige fuer Terrassentuer-Felder

## Version 0.10.0

- Aktiver Frigate-Objektzaehler zaehlt jetzt `person` und `dog`
- `dog_count`, `maja_present`, `recognized_entities` und History werden per API/UI/MQTT sichtbar
- Neue History-API und Web-UI-Graph fuer Personen gleichzeitig im Wohnzimmer

## Version 0.9.0

- Aktiver Frigate-Personenzaehler ueber `/api/events?...&in_progress=1`
- Neue Frigate-Konfiguration fuer `api_url`, Live-Zaehler und Poll-Intervall
- `person_count` kann jetzt die aktuelle Anzahl aktiver Personen im Bild abbilden

## Version 0.8.2

- Kamera-URLs in API-Ausgaben maskieren Pfad, Query und Credentials

## Version 0.8.1

- Helles Standard-Theme fuer die Web-UI
- Dunkles Theme nur noch ueber System-Dark-Mode

## Version 0.8.0

- Web-UI fuer Demo-Modus, Event-Intervall, Log-Level, MQTT und Discovery
- Web-UI fuer Frigate-Import und externen Face-Import
- Neuer Endpunkt `POST /api/config` fuer sichere Konfigurationsaenderungen
- Konfigurationsfehler und Event-Zaehler sind in der Web-UI sichtbar

## Version 0.7.0

- MQTT Discovery fuer Home-Assistant-Sensoren
- Sensoren fuer Bridge-Status, Personenanzahl, bekannte Gesichter, unbekannte Gesichter und letzte Event-Quelle
- Discovery ist ueber `mqtt.discovery` und `mqtt.discovery_prefix` konfigurierbar

## Version 0.6.0

- Externe Face-Matching-Events ueber MQTT oder `POST /api/face-events`
- Filter gegen lokale Face-Registry und `face_recognition.min_confidence`
- Events enthalten echte `known_faces`, `unknown_faces` und Confidence aus externer Engine

## Version 0.5.0

- Lokale Face-Registry unter `/data/faces.json`
- REST-API fuer bekannte Personen: `GET /api/faces`, `POST /api/faces`, `PATCH /api/faces/<name>`
- Bekannte Personen koennen angelegt, aktiviert und deaktiviert werden
- Noch keine Speicherung von Gesichtsbildern oder Embeddings

## Version 0.4.0

- Optionaler Import von Frigate-MQTT-Events ueber `frigate.events_topic`
- Frigate-Events mit `label: person` erzeugen reale `person_count`-Events
- Kamera-Filter ueber `frigate.camera_name`

## Version 0.3.0

- Snapshot-Erfassung im Nicht-Demo-Modus in den Detector-Pfad integriert
- Status-Events fuer erfolgreiche und fehlgeschlagene Snapshot-Abrufe
- Tests fuer Snapshot-Detector-Erfolg und Fehlerfall

## Version 0.2.0

- Kamera-Parameter koennen ueber die Weboberflaeche gespeichert werden
- Snapshot-Vorschau fuer HTTP/HTTPS-Kamerabilder
- REST-Endpunkte fuer Kamera-Konfiguration und Snapshot-Abruf
- Secret- und RTSP-/Snapshot-URL-Maskierung

## Version 0.1.0

- Home-Assistant-Add-on-Struktur
- Dockerfile und Startskript
- Python/Flask-App auf Port `8099`
- Lesen von `/data/options.json`
- Demo-Modus mit simulierten Events
- REST-Endpunkte `/health`, `/api/status`, `/api/cameras`, `/api/last-event`, `/api/config`
- einfache Ingress-Web-UI
- optionale MQTT-Ausgabe
- Secret- und RTSP-URL-Maskierung

## MQTT-Topics

- `ha/frigate_face_bridge/status`
- `ha/frigate_face_bridge/<camera>/person_count`
- `ha/frigate_face_bridge/<camera>/known_faces`
- `ha/frigate_face_bridge/<camera>/unknown_faces`
- `ha/frigate_face_bridge/<camera>/last_event`
- Import optional: `face_recognition/events`

## MQTT Discovery

- Standard-Prefix: `homeassistant`
- Konfigurations-Topics: `homeassistant/sensor/frigate_face_bridge_<camera>_<sensor>/config`
- Discovery kann mit `mqtt.discovery: false` deaktiviert werden.

## Datenschutz

- Verarbeitung ist fuer das lokale Netzwerk vorgesehen.
- Keine Cloud-Anbindung ist erforderlich.
- Externe Engines liefern nur Ergebnis-Events; Bild-Uploads werden vom Add-on nicht erzwungen.
- Gesichtsdaten und Face-Registry bleiben lokal; externe Uploads sind nicht vorgesehen.
- Passwoerter und RTSP-Credentials duerfen nicht in Logs ausgegeben werden.
- Betreiber sind fuer rechtliche Zulassung, Kennzeichnung und Einwilligungen verantwortlich.

Weitere Details stehen in `frigate-face-bridge/DOCS.md`.

## Docker-Deployment ausserhalb von Home Assistant

Fuer einen bestehenden Docker-Host liegt unter `deploy/` eine Compose-Vorlage. Vor dem Start `deploy/data/options.json.example` nach `deploy/data/options.json` kopieren und lokal anpassen. Keine echten Passwoerter committen.
