# Frigate Face Bridge

Lokale Personenzaehlung und vorbereitete Gesichtserkennung fuer UniFi-Kameras mit MQTT-Anbindung an Home Assistant.

## Zweck

Dieses Add-on ist die Home-Assistant-nahe Bruecke fuer Kamera-Status, Detection-Events, MQTT-Ausgabe, REST-API und eine einfache Web-UI. Es ist als Grundlage fuer spaetere Integrationen mit Frigate, Double Take, CompreFace oder einer lokalen Face-Recognition-Engine gedacht.

## Funktionsumfang 0.1.0

- Startfaehig ohne Kamera
- Startfaehig ohne MQTT
- Demo-Modus mit simulierten Events
- REST-API fuer Health, Status, Kameras, letztes Event und maskierte Konfiguration
- Ingress-Web-UI auf Port `8099`
- MQTT-Publisher fuer Status und Event-Topics
- Konfiguration ueber `/data/options.json`
- Logs ueber stdout/stderr

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
- `GET /api/config`

## MQTT-Topics

- `ha/frigate_face_bridge/status`
- `ha/frigate_face_bridge/<camera>/person_count`
- `ha/frigate_face_bridge/<camera>/known_faces`
- `ha/frigate_face_bridge/<camera>/unknown_faces`
- `ha/frigate_face_bridge/<camera>/last_event`

## Demo-Modus

Wenn `demo_mode: true` gesetzt ist, erzeugt das Add-on simulierte Events:

- `person_count`: 0 bis 3
- `known_faces`: zufaellige Auswahl aus aktivierten bekannten Personen
- `unknown_faces`: 0 oder 1
- MQTT-Ausgabe, falls MQTT aktiviert ist
- Web-UI zeigt die simulierten Werte

## Abgrenzung

Frigate Face Bridge ersetzt Frigate nicht. Frigate kann spaeter Personendetektionen liefern. Double Take oder CompreFace koennen spaeter Gesichtserkennung liefern. Dieses Add-on stellt Konfiguration, Statuslogik, API, Web-UI und Home-Assistant-MQTT-Anbindung bereit.
