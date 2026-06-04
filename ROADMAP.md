# Roadmap

Diese Roadmap haelt den Projektstand und die naechsten Ausbaustufen fuer `Frigate Face Bridge` fest.

## Status

Aktueller Stand: **Stufe 13 abgeschlossen**.

Aktuelle Add-on-Version: `0.12.0`.

## Stufe 1 - Add-on-Basis

Status: **abgeschlossen**

Ziel: Das Projekt ist als Home-Assistant-Add-on installierbar und startet sicher ohne Kamera und ohne MQTT.

Umgesetzt:

- Home-Assistant-Add-on-Struktur mit `config.yaml`
- Dockerfile und `run.sh`
- Python/Flask-App auf Port `8099`
- Konfiguration ueber `/data/options.json`
- sicherer Standard `demo_mode: true`
- Start ohne Kamera und ohne MQTT moeglich

Abnahme:

- Add-on startet mit Default-Konfiguration.
- `/health` liefert einen erfolgreichen Status.

## Stufe 2 - API, Web-UI und Kamera-Konfiguration

Status: **abgeschlossen**

Ziel: Status, Demo-Events, MQTT-Ausgabe und Kamera-Grundkonfiguration sind nutzbar.

Umgesetzt:

- REST-Endpunkte fuer Health, Status, Kameras, letztes Event und maskierte Konfiguration
- Demo-Events fuer Personenanzahl, bekannte Gesichter und unbekannte Gesichter
- optionale MQTT-Ausgabe fuer Status und Event-Topics
- einfache Ingress-Web-UI
- Kamera-Parameter koennen ueber die Web-UI gespeichert werden
- HTTP/HTTPS-Snapshot-Vorschau
- Maskierung von MQTT-Passwoertern sowie RTSP-/Snapshot-URL-Credentials
- Tests fuer API, Secret-Maskierung, Kamera-Speichern und Snapshot-Pflichtpruefung

Abnahme:

- Web-UI zeigt Status und Demo-Events.
- Kamera-Konfiguration kann gespeichert werden.
- Snapshot-Vorschau funktioniert mit einer gueltigen HTTP/HTTPS-URL.

## Stufe 3 - Dokumentation und Projektstand konsolidieren

Status: **abgeschlossen**

Ziel: Repository-Dokumentation, Add-on-Dokumentation und Roadmap beschreiben denselben Stand.

Aufgaben:

- Root-README auf den aktuellen Stand bringen
- Add-on-README um die aktuellen Funktionen ergaenzen
- Roadmap dauerhaft pflegen
- klare Abgrenzung dokumentieren: echte Detection ist noch nicht implementiert

Abnahme:

- README-Dateien und Changelog widersprechen sich nicht.
- Offene Stufen sind im Repository nachvollziehbar.

## Stufe 4 - Reale Snapshot-Erfassung

Status: **abgeschlossen**

Ziel: Das Add-on kann ohne Demo-Modus regelmaessig ein echtes Kamerabild abrufen und seinen Status melden, noch ohne Personendetektion.

Aufgaben:

- Snapshot-Abruf in den Detector-Pfad integrieren
- Abrufintervall und Fehlerstatus sauber abbilden
- Bildgroesse und Content-Type begrenzen
- URL-Credentials weiterhin nie loggen oder ueber API ausgeben
- Tests fuer erfolgreiche und fehlerhafte Snapshot-Abrufe ergaenzen

Abnahme:

- `demo_mode: false` mit `snapshot_url` erzeugt echte Status-Events statt reiner Platzhalter-Events.
- Fehlerhafte Kamera-URLs bringen das Add-on nicht zum Absturz.

## Stufe 5 - Personendetektion

Status: **abgeschlossen**

Ziel: Aus echten Bildern oder externen Events wird eine reale Personenanzahl erzeugt.

Moegliche Wege:

- lokale OpenCV-/YOLO-basierte Erkennung
- Import von Frigate-Events
- spaetere externe Engine ueber HTTP/MQTT

Umgesetzt:

- optionaler Import von Frigate-MQTT-Events ueber `frigate/events`
- Filter fuer `label: person`, False-Positive-Events und optionalen Kameranamen
- reale `person_count`-Events mit Confidence, Box-Daten und Frigate-Event-ID

Abnahme:

- Events enthalten eine reale `person_count` aus Kamera- oder Frigate-Daten.
- Demo- und Realbetrieb sind klar unterscheidbar.

## Stufe 6 - Face-Recognition-Grundlage

Status: **abgeschlossen**

Ziel: Bekannte Personen werden lokal verwaltet und fuer spaeteres Matching vorbereitet.

Aufgaben:

- lokale Ablage fuer bekannte Personen definieren
- Enrollment-Prozess planen und umsetzen
- Datenschutzgrenzen dokumentieren
- API/Web-UI fuer bekannte Personen erweitern

Umgesetzt:

- lokale Face-Registry unter `/data/faces.json`
- API zum Lesen, Anlegen und Aktivieren/Deaktivieren bekannter Personen
- Registry speichert aktuell nur Metadaten, keine Gesichtsbilder und keine Embeddings
- Frigate-Events werden im App-State als reale externe Personendetektion gezaehlt

Abnahme:

- Bekannte Personen koennen lokal angelegt, aktiviert und deaktiviert werden.
- Keine Gesichtsdaten werden extern uebertragen.

## Stufe 7 - Gesichtserkennung und Matching

Status: **abgeschlossen**

Ziel: Bekannte und unbekannte Gesichter werden aus echten Events unterschieden.

Moegliche Wege:

- lokale Face-Recognition-Engine
- Double Take
- CompreFace

Umgesetzt:

- externe Face-Matching-Events koennen per MQTT oder REST importiert werden
- bekannte Namen werden gegen die lokale Face-Registry geprueft
- deaktivierte Personen, unbekannte Namen und Treffer unterhalb `face_recognition.min_confidence` werden verworfen
- Events enthalten `known_faces`, `unknown_faces`, `confidence` und `source: external_face_recognition`

Abgrenzung:

- lokale Bildanalyse und Embedding-Berechnung sind weiterhin nicht implementiert
- Double Take, CompreFace oder eine lokale Engine koennen die Matching-Events liefern

Abnahme:

- Events enthalten echte `known_faces` und `unknown_faces`.
- Confidence-Werte und Fehlerzustaende sind nachvollziehbar.

## Stufe 8 - Home-Assistant-Integration ausbauen

Status: **abgeschlossen**

Ziel: Home Assistant erkennt Sensoren automatisch und kann die Bridge sauber ueberwachen.

Aufgaben:

- MQTT Discovery fuer Sensoren ergaenzen
- Status-, Personen-, bekannte- und unbekannte-Gesichter-Sensoren definieren
- Availability/online/offline sauber setzen

Umgesetzt:

- retained MQTT-Discovery-Payloads unter `homeassistant/sensor/.../config`
- Sensoren fuer Bridge-Status, Personenanzahl, bekannte Gesichter, unbekannte Gesichter und letzte Event-Quelle
- Availability ueber `ha/frigate_face_bridge/status` mit `online`/`offline`
- Discovery kann ueber `mqtt.discovery` deaktiviert und ueber `mqtt.discovery_prefix` umkonfiguriert werden

Abnahme:

- Sensoren erscheinen automatisch in Home Assistant.
- Neustarts erzeugen keine doppelten oder kaputten Entitaeten.

## Stufe 9 - Web-UI-Ausbau

Status: **abgeschlossen**

Ziel: Die wichtigsten Einstellungen sind ohne manuelles Bearbeiten von JSON erreichbar.

Aufgaben:

- Demo-Modus umschaltbar machen
- MQTT-Konfiguration editierbar machen
- bekannte Personen verwaltbar machen
- Detection-/Kamera-Fehler sichtbar machen

Umgesetzt:

- Web-UI-Formular fuer Demo-Modus, Event-Intervall und Log-Level
- Web-UI-Formular fuer MQTT, MQTT Discovery, Frigate-Import und Face-Import
- sichere REST-API `POST /api/config` mit Allowlist, Validierung und Secret-Schutz
- Konfigurationsfehler sowie Frigate- und Face-Event-Zaehler sichtbar in der UI
- bekannte Personen bleiben ueber die Web-UI verwaltbar

Abnahme:

- Standardbetrieb kann ueber die Web-UI eingerichtet werden.
- Secrets bleiben auch in der UI maskiert.

## Stufe 10 - Aktive Frigate-Personenzaehlung

Status: **abgeschlossen**

Ziel: Die Personenanzahl soll nicht nur aus einzelnen Frigate-MQTT-Events entstehen, sondern die aktuell aktiven Personen im Kamerabild widerspiegeln.

Umgesetzt:

- Frigate-API-Abfrage fuer aktive `person`-Events mit `in_progress=1`
- Zaehlung aller aktiven Personen fuer den konfigurierten Kamera-Filter
- MQTT-Publish auf den bestehenden `person_count`-Sensor
- Web-UI-Konfiguration fuer `frigate.api_url`, `frigate.person_count_enabled` und Poll-Intervall
- Nicht-Demo-Snapshot-Status ueberschreibt den aktiven Frigate-Zaehler nicht mehr, wenn der API-Zaehler aktiv ist

Abnahme:

- Wenn Frigate mehrere aktive Personen im Bild erkennt, veroeffentlicht Face Bridge diese Anzahl als `person_count`.
- Bei `0` aktiven Personen wird ebenfalls `person_count: 0` veroeffentlicht.

## Stufe 11 - Hund, Maja und History

Status: **abgeschlossen**

Ziel: Neben Personen soll auch der Hund im Wohnzimmer sichtbar werden und die Web-UI soll Verlauf und Personenanzahl als Graph anzeigen.

Umgesetzt:

- Frigate-API-Zaehler fuer aktive `dog`-Events
- MQTT Topics und Discovery fuer `dog_count`, `maja_present` und `recognized_entities`
- History-API `GET /api/history`
- Web-UI mit Verlauf und Personen-Graph

Abnahme:

- `dog_count` und `maja_present` werden per MQTT und API veroeffentlicht.
- Die UI zeigt History und Personenserie an.

## Stufe 12 - Terrassentuer-Felder

Status: **abgeschlossen**

Ziel: Face Bridge soll vorbereitete MQTT-/API-Felder fuer den spaeteren Terrassentuer-Zustand bereitstellen.

Umgesetzt:

- Konfiguration `terrace_door.enabled`, `open`, `confidence`, `last_changed`
- MQTT Topics `terrace_door_open`, `terrace_door_confidence`, `terrace_door_last_changed`
- MQTT Discovery fuer die drei Terrassentuer-Felder
- Web-UI-Konfiguration und Statusanzeige

Abnahme:

- Home Assistant kann die drei Felder als MQTT-Entities anlegen.
- Der Zustand kann ueber `POST /api/config` gesetzt und per `/api/status` gelesen werden.

## Stufe 13 - Home-Assistant-lesbare Ingress-UI

Status: **abgeschlossen**

Ziel: Der Seitenleisten-Eintrag `Face Bridge` soll im Home-Assistant-Ingress besser lesbar sein und sich farblich an Standarddialogen von Home Assistant orientieren.

Umgesetzt:

- Helles HA-aehnliches Kartendesign fuer Status, Panels und Formulare
- Bessere Kontraste, groessere lesbare Typografie und klare Input-Zustaende
- Dunkelmodus-Uebersteuerung entfernt, damit die UI im HA-Ingress nicht ungewollt zu dunkel wird
- Version auf `0.12.0` angehoben

Abnahme:

- Die Web-UI ist im HA-Seitenleistenpanel lesbar.
- Status, Konfiguration, History und Debug bleiben erreichbar.

## Laufende Sicherheitsregeln

- Keine Secrets, Tokens, Passwoerter oder vollstaendige RTSP-URLs mit Credentials committen.
- MQTT-Passwoerter maskieren.
- RTSP- und Snapshot-URLs vor Logging/API-Ausgabe maskieren.
- Add-on muss ohne Kamera und ohne MQTT starten koennen.
- `demo_mode: true` bleibt der sichere Standard, bis echte Detection implementiert ist.
