# Frigate Face Bridge

Lokale Personenzaehlung und vorbereitete Gesichtserkennung fuer UniFi-Kameras mit MQTT-Anbindung an Home Assistant.

## Zweck

Dieses Add-on ist die Home-Assistant-nahe Bruecke fuer Kamera-Status, Detection-Events, MQTT-Ausgabe, REST-API und eine einfache Web-UI. Es ist als Grundlage fuer spaetere Integrationen mit Frigate, Double Take, CompreFace oder einer lokalen Face-Recognition-Engine gedacht.

## Funktionsumfang 0.10.0

- Startfaehig ohne Kamera
- Startfaehig ohne MQTT
- Demo-Modus mit simulierten Events
- REST-API fuer Health, Status, Kameras, letztes Event und maskierte Konfiguration
- Ingress-Web-UI auf Port `8099`
- MQTT-Publisher fuer Status und Event-Topics
- Konfiguration ueber `/data/options.json`
- Kamera-Parameter ueber Web-UI speichern
- Snapshot-Vorschau fuer HTTP/HTTPS-Kamerabilder
- REST-Endpunkte fuer Kamera-Konfiguration und Snapshot-Abruf
- Snapshot-Erfassung im Nicht-Demo-Modus mit Status-Events
- optionaler Frigate-MQTT-Event-Import fuer reale Personenzaehlung
- aktiver Frigate-Personenzaehler ueber die Frigate-API fuer aktuelle Personen im Bild
- aktiver Hund-Zaehler fuer Frigate-Objekt `dog` mit `Maja`-Status
- History und Graph fuer Personen gleichzeitig im Wohnzimmer
- lokale Face-Registry fuer bekannte Personen unter `/data/faces.json`
- API zum Anlegen, Aktivieren und Deaktivieren bekannter Personen
- Import externer Face-Matching-Events per MQTT oder REST
- Filter fuer bekannte Personen und Confidence-Schwellwert
- MQTT Discovery fuer Home-Assistant-Sensoren
- Web-UI fuer Demo-Modus, MQTT, Discovery, Frigate-Import und Face-Import
- helles Standard-Theme mit optionalem System-Dark-Mode
- Konfigurationsfehler und Event-Zaehler in der Web-UI sichtbar
- Logs ueber stdout/stderr
- konservativ maskierte Kamera-URLs in API-Ausgaben

## Konfiguration

```yaml
demo_mode: true
log_level: info
event_interval_seconds: 10
mqtt:
  enabled: true
  host: core-mosquitto
  port: 1883
  username: ""
  password: ""
  topic_prefix: ha/frigate_face_bridge
  discovery: true
  discovery_prefix: homeassistant
frigate:
  enabled: false
  events_topic: frigate/events
  camera_name: ""
  api_url: ""
  person_count_enabled: true
  person_count_interval_seconds: 5
  dog_name: Maja
face_recognition:
  enabled: false
  events_topic: face_recognition/events
  min_confidence: 0.7
camera:
  name: garage_g3_flex
  host: 192.168.2.241
  rtsp_url: ""
  snapshot_url: ""
  detect_width: 640
  detect_height: 360
  detect_fps: 5
known_faces:
  - name: Thomas
    enabled: true
  - name: Birgit
    enabled: true
  - name: Marie
    enabled: true
```

## REST-API

- `GET /health`
- `GET /api/status`
- `GET /api/cameras`
- `GET /api/last-event`
- `GET /api/history`
- `GET /api/config`
- `POST /api/config`
- `POST /api/config/camera`
- `GET /api/camera/snapshot`
- `GET /api/faces`
- `POST /api/faces`
- `PATCH /api/faces/<name>`
- `POST /api/face-events`

## MQTT-Topics

- `ha/frigate_face_bridge/status`
- `ha/frigate_face_bridge/<camera>/person_count`
- `ha/frigate_face_bridge/<camera>/dog_count`
- `ha/frigate_face_bridge/<camera>/maja_present`
- `ha/frigate_face_bridge/<camera>/known_faces`
- `ha/frigate_face_bridge/<camera>/recognized_entities`
- `ha/frigate_face_bridge/<camera>/unknown_faces`
- `ha/frigate_face_bridge/<camera>/last_event`
- optionaler Import: `face_recognition/events`

## MQTT Discovery

- `homeassistant/sensor/frigate_face_bridge_<camera>_bridge_status/config`
- `homeassistant/sensor/frigate_face_bridge_<camera>_person_count/config`
- `homeassistant/sensor/frigate_face_bridge_<camera>_dog_count/config`
- `homeassistant/sensor/frigate_face_bridge_<camera>_maja_present/config`
- `homeassistant/sensor/frigate_face_bridge_<camera>_known_faces/config`
- `homeassistant/sensor/frigate_face_bridge_<camera>_recognized_entities/config`
- `homeassistant/sensor/frigate_face_bridge_<camera>_unknown_faces/config`
- `homeassistant/sensor/frigate_face_bridge_<camera>_last_event_source/config`

Die Discovery-Payloads werden retained veroeffentlicht. Availability nutzt `ha/frigate_face_bridge/status` mit `online` und `offline`.

## Demo-Modus

Wenn `demo_mode: true` gesetzt ist, erzeugt das Add-on simulierte Events:

- `person_count`: 0 bis 3
- `known_faces`: zufaellige Auswahl aus aktivierten bekannten Personen
- `unknown_faces`: 0 oder 1
- MQTT-Ausgabe, falls MQTT aktiviert ist
- Web-UI zeigt die simulierten Werte

## Aktive Frigate-Objektzaehlung

Fuer eine echte aktuelle Personen- und Hund-Anzahl muss Frigate laufen und `person` sowie `dog` erkennen. Face Bridge kann dann regelmaessig die aktiven Frigate-Events abfragen:

```yaml
demo_mode: false
frigate:
  enabled: true
  events_topic: frigate/events
  camera_name: wohnzimmer_g3_flex
  api_url: http://fossflow.localdomain:5000
  person_count_enabled: true
  person_count_interval_seconds: 5
  dog_name: Maja
```

Der Zaehler nutzt Frigates aktive Events (`in_progress=1`) und veroeffentlicht die Anzahl auf `person_count`, `dog_count`, `maja_present`, `recognized_entities` und `last_event`.

## Abgrenzung

Frigate Face Bridge ersetzt Frigate nicht. Frigate kann spaeter Personendetektionen liefern. Double Take oder CompreFace koennen spaeter Gesichtserkennung liefern. Dieses Add-on stellt Konfiguration, Statuslogik, API, Web-UI und Home-Assistant-MQTT-Anbindung bereit.

Lokale Bild-Personendetektion und lokale Face-Embedding-Berechnung sind in Version `0.10.0` noch nicht implementiert. Frigate-MQTT-Events und die Frigate-API koennen bereits fuer reale Personen-/Hund-Zaehler genutzt werden. Face-Matching-Ergebnisse koennen von einer externen lokalen Engine importiert werden. Die Face-Registry speichert nur lokale Metadaten bekannter Personen. Die naechsten Ausbaustufen sind in `../ROADMAP.md` dokumentiert.
