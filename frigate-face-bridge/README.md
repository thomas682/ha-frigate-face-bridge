# Frigate Face Bridge

Lokale Personenzaehlung und vorbereitete Gesichtserkennung fuer UniFi-Kameras mit MQTT-Anbindung an Home Assistant.

## Zweck

Dieses Add-on ist die Home-Assistant-nahe Bruecke fuer Kamera-Status, Detection-Events, MQTT-Ausgabe, REST-API und eine einfache Web-UI. Es ist als Grundlage fuer spaetere Integrationen mit Frigate, Double Take, CompreFace oder einer lokalen Face-Recognition-Engine gedacht.

## Funktionsumfang 0.15.2

- Startfaehig ohne Kamera
- Startfaehig ohne MQTT
- Demo-Modus mit simulierten Events
- REST-API fuer Health, Status, Kameras, letztes Event und maskierte Konfiguration
- Ingress-Web-UI auf Port `8099` mit Menuefuehrung fuer Ueberblick, Live-Daten, MQTT, Erkennungen, Ansagen, Verlauf, Konfiguration und Debug
- vollbreite, iPhone-taugliche Web-UI mit filterbaren, scrollbareren Listen
- Konfigurationsspeicherung als Teilupdate, damit leere Formularfelder bestehende Nutzerwerte nicht ueberschreiben
- Statusanzeigen fuer gesetzten MQTT-Benutzer, gesetztes MQTT-Passwort sowie gesetzte RTSP-/Snapshot-URLs
- Testbuttons fuer MQTT-Verbindung, RTSP-Erreichbarkeit und Snapshot-Erreichbarkeit
- Testbutton fuer die Frigate API und direkte Tests mit den aktuell eingegebenen Formularwerten
- Links-Sicht fuer Bridge-API, Frigate, go2rtc und GitHub-Projektseiten
- Ueberblick-Schemazeichnung fuer Datenfluss von Kamera/UniFi Protect ueber Frigate/go2rtc und MQTT bis Home Assistant
- konkrete Hilfetexte direkt an den Konfigurationsparametern sowie kurze Erklaerungen fuer Erkennungs-, MQTT-, Ansage- und Verlaufslogs
- RTSP- und Snapshot-Beispielbuttons fuer `wohnzimmer_g3_flex`-Beispiele und sichtbare gespeicherte RTSP-/Snapshot-URLs ohne Credential-Offenlegung
- maskierte Live-MQTT-History fuer ein- und ausgehende Nachrichten in API und Web-UI
- MQTT-Publisher fuer Status und Event-Topics
- Konfiguration ueber `/data/options.json`
- Parameterverwaltung trennt gespeicherte Rohwerte von Runtime-Fallbacks, damit Updates keine Nutzerwerte ueberschreiben
- Kamera-Parameter ueber Web-UI speichern
- Snapshot-Vorschau fuer HTTP/HTTPS-Kamerabilder
- REST-Endpunkte fuer Kamera-Konfiguration und Snapshot-Abruf
- Snapshot-Erfassung im Nicht-Demo-Modus mit Status-Events
- optionaler Frigate-MQTT-Event-Import fuer reale Personenzaehlung
- aktiver Frigate-Personenzaehler ueber die Frigate-API fuer aktuelle Personen im Bild
- aktiver Hund-Zaehler fuer Frigate-Objekt `dog` mit `Maja`-Status
- History und Zeitreihen-Kurvendiagramm fuer Personen gleichzeitig im Wohnzimmer
- konfigurierbare Ansageereignisse fuer bekannte Personen, unbekannte Personen und Hund
- Anti-Spam-Cooldowns, Zufallstexte, eigene Texte und Sperrliste fuer Ansagen
- Erkennungslog mit Zeitpunkt, Text, Entitaeten und Sperrgrund
- Terrassentuer-Statusfelder fuer MQTT/API/UI: offen, Confidence und letzte Aenderung
- lokale Face-Registry fuer bekannte Personen unter `/data/faces.json`
- API zum Anlegen, Aktivieren und Deaktivieren bekannter Personen
- Import externer Face-Matching-Events per MQTT oder REST
- Filter fuer bekannte Personen und Confidence-Schwellwert
- MQTT Discovery fuer Home-Assistant-Sensoren
- Web-UI fuer Demo-Modus, MQTT, Discovery, Frigate-Import, Face-Import, erkannte Namen und Ansagen
- helles Home-Assistant-lesbares Ingress-Theme ohne ungewollte Dark-Mode-Abdunklung
- ueberarbeitete Ingress-Oberflaeche nach `ffb_ui_concepts.html` mit Command Center, Eventkarte und Timeline
- Konfigurationsfehler und Event-Zaehler in der Web-UI sichtbar
- Logs ueber stdout/stderr
- konservativ maskierte Kamera-URLs in API-Ausgaben

## Konfiguration

```yaml
demo_mode: false
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
announcements:
  enabled: true
  announce_known: true
  announce_unknown: true
  announce_dog: true
  random_texts_enabled: true
  global_cooldown_seconds: 60
  entity_cooldown_seconds: 300
  disabled_entities: ""
  custom_texts: ""
terrace_door:
  enabled: false
  open: false
  confidence: 0.0
  last_changed: ""
camera:
  name: ""
  host: ""
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
- `POST /api/test/mqtt`
- `POST /api/test/rtsp`
- `POST /api/test/snapshot`
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
- `ha/frigate_face_bridge/<camera>/announcement_text`
- `ha/frigate_face_bridge/<camera>/announcement_should_speak`
- `ha/frigate_face_bridge/<camera>/announcement_entities`
- `ha/frigate_face_bridge/<camera>/recognition_log`
- `ha/frigate_face_bridge/<camera>/terrace_door_open`
- `ha/frigate_face_bridge/<camera>/terrace_door_confidence`
- `ha/frigate_face_bridge/<camera>/terrace_door_last_changed`
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
- `homeassistant/sensor/frigate_face_bridge_<camera>_announcement_text/config`
- `homeassistant/sensor/frigate_face_bridge_<camera>_announcement_should_speak/config`
- `homeassistant/sensor/frigate_face_bridge_<camera>_announcement_entities/config`
- `homeassistant/sensor/frigate_face_bridge_<camera>_recognition_log/config`
- `homeassistant/sensor/frigate_face_bridge_<camera>_terrace_door_open/config`
- `homeassistant/sensor/frigate_face_bridge_<camera>_terrace_door_confidence/config`
- `homeassistant/sensor/frigate_face_bridge_<camera>_terrace_door_last_changed/config`
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

## Web-UI-Sichten

Die Ingress-Web-UI ist in navigierbare Sichten aufgeteilt:

- `Ueberblick`: Bridge-, Kamera-, MQTT- und letzte Event-Werte.
- `Live`: aktuell erkannte Namen, bekannte Gesichter, unbekannte Personen, Hundestatus und letztes Event.
- `MQTT`: Verbindungsstatus, Import-Topics, Bridge-Ausgabe-Topics und maskierte Live-Nachrichten.
- `Erkennungen`: aktuelle und historische Personen-/Tier-Erkennungen.
- `Ansagen`: aktueller Ansagetext, Ausloesung, Entitaeten, Sperrgrund und Ansage-History.
- `Verlauf`: Personen-Zeitreihe sowie Erkennungs- und Ansagelog.
- `Konfiguration`: System-, MQTT-, Frigate-, Face-, Ansage-, Kamera- und Personen-Konfiguration.
- `Debug`: maskierter technischer Status fuer Diagnose.

Die Konfigurationssicht sendet Teilupdates. Leere Passwort-, RTSP- oder Snapshot-Felder bedeuten `unveraendert lassen`; gesetzte Werte werden als Status angezeigt, nicht im Klartext.

Die MQTT-Live-History wird nur im Speicher gehalten und begrenzt. Secrets, Token, Passwoerter und Kamera-URLs mit Credentials werden vor der API-Ausgabe maskiert.

## Ansageereignisse

Face Bridge erzeugt pro Erkennung ein `announcement`-Objekt mit sprechbarem Text, `should_speak`, erkannten Entitaeten und Sperrgrund. Home Assistant kann `sensor.frigate_face_bridge_ansage_ausloesen` als Trigger/Bedingung und `sensor.frigate_face_bridge_ansagetext` als TTS-Text verwenden. Globale und entitaetsbezogene Cooldowns verhindern wiederholte Ansagen derselben Person im Sekundentakt.

Eigene Texte werden zeilenweise gepflegt:

```text
Thomas=Thomas ist im Wohnzimmer erkannt worden.
Maja=Maja ist im Haus.
unknown=Achtung, unbekannte Person erkannt.
multiple={names} wurden erkannt.
```

Ohne eigenen Text waehlt die Bridge zufaellig aus 20 gespeicherten Ansagetexten.

## Terrassentuer-Felder

Face Bridge stellt vorbereitete Terrassentuer-Felder bereit, damit eine spaetere Frigate-Klassifizierung oder ein anderer lokaler Sensor dieselben MQTT-Entities nutzen kann:

```yaml
terrace_door:
  enabled: true
  open: false
  confidence: 0.0
  last_changed: ""
```

Diese Werte werden auf `terrace_door_open`, `terrace_door_confidence`, `terrace_door_last_changed` und im `last_event` veroeffentlicht. Die aktuelle Version erkennt den Tuerzustand noch nicht selbst aus dem Bild.

## Abgrenzung

Frigate Face Bridge ersetzt Frigate nicht. Frigate kann spaeter Personendetektionen liefern. Double Take oder CompreFace koennen spaeter Gesichtserkennung liefern. Dieses Add-on stellt Konfiguration, Statuslogik, API, Web-UI und Home-Assistant-MQTT-Anbindung bereit.

Lokale Bild-Personendetektion, lokale Face-Embedding-Berechnung und Terrassentuer-Bildklassifizierung sind in Version `0.15.2` noch nicht implementiert. Frigate-MQTT-Events und die Frigate-API koennen bereits fuer reale Personen-/Hund-Zaehler genutzt werden. Face-Matching-Ergebnisse koennen von einer externen lokalen Engine importiert werden. Die Face-Registry speichert nur lokale Metadaten bekannter Personen. Die naechsten Ausbaustufen sind in `../ROADMAP.md` dokumentiert.
