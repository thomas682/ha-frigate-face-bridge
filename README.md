# Frigate Face Bridge Add-on Repository

Dieses Repository stellt das Home-Assistant-Add-on `Frigate Face Bridge` bereit.

## Zweck

Frigate Face Bridge ist eine lokale Bruecke fuer UniFi-Kameras, Personenzaehlung, vorbereitete Gesichtserkennung und MQTT-Ausgabe an Home Assistant. Version `0.1.0` liefert eine stabile Add-on-Basis mit Demo-Modus, REST-API, Web-UI und MQTT-Publisher.

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

## Datenschutz

- Verarbeitung ist fuer das lokale Netzwerk vorgesehen.
- Keine Cloud-Anbindung ist erforderlich.
- Es werden keine externen Uploads implementiert.
- Gesichtsdaten sollen spaeter nur lokal gespeichert werden.
- Passwoerter und RTSP-Credentials duerfen nicht in Logs ausgegeben werden.
- Betreiber sind fuer rechtliche Zulassung, Kennzeichnung und Einwilligungen verantwortlich.

Weitere Details stehen in `frigate-face-bridge/DOCS.md`.
