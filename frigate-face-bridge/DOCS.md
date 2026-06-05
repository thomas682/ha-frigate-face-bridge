# Dokumentation

## Add-on-Start

Das Add-on startet im Standardzustand ohne automatisch aktivierten Demo-Modus. `demo_mode` muss bewusst aktiviert werden, wenn simulierte Events gewuenscht sind. Bereits gespeicherte Parameterwerte werden bei Start, Neustart oder Update nicht automatisch ueberschrieben.

## Kamera 192.168.2.241 vorbereiten

Die Kamera-IP ist als `camera.host: 192.168.2.241` vorbereitet. Eine echte RTSP-URL wird bewusst nicht hart codiert.

Vorgehensweise fuer UniFi Protect / G3 Flex:

1. UniFi Protect oeffnen.
2. Kamera `G3 Flex` mit IP `192.168.2.241` auswaehlen.
3. RTSP oder RTSPS fuer die gewuenschte Stream-Qualitaet aktivieren.
4. Falls UniFi Protect Zugangsdaten verlangt, einen dedizierten Nutzer mit minimalen Leserechten erstellen.
5. RTSP-URL in VLC, `ffprobe` oder `ffmpeg` testen.
6. Erst danach die URL in der Add-on-Konfiguration unter `camera.rtsp_url` eintragen.
7. `demo_mode` nur bewusst aktivieren, wenn simulierte Events zum Testen gewuenscht sind.

Beispiel ohne Zugangsdaten:

```yaml
camera:
  name: garage_g3_flex
  host: 192.168.2.241
  rtsp_url: rtsp://192.168.2.241:7447/STREAM_ID
```

Passwoerter gehoeren nicht in Logs, Issues, Screenshots oder Commits.

## REST-API

`GET /health` liefert einen einfachen Healthcheck mit HTTP 200.

`GET /api/status` liefert Status, Kamera, MQTT, bekannte Personen und letztes Event.

`GET /api/cameras` liefert die konfigurierte Kamera mit maskierten Stream-URLs.

`GET /api/last-event` liefert das letzte Detection-Event.

`GET /api/config` liefert die wirksame Konfiguration ohne Klartext-MQTT-Passwort und ohne Klartext-Credentials in URLs.

## MQTT

Wenn `mqtt.enabled: true` gesetzt ist, verbindet sich das Add-on mit dem Broker und veroeffentlicht Events unter `mqtt.topic_prefix`.

Payload fuer `person_count`:

```json
{
  "camera": "garage_g3_flex",
  "person_count": 2,
  "timestamp": "2026-06-01T18:30:00Z",
  "source": "frigate_face_bridge"
}
```

## Datenschutz und Sicherheit

- Verarbeitung findet lokal im eigenen Netzwerk statt.
- Keine Cloud ist erforderlich.
- Keine externen Uploads sind implementiert.
- Gesichtsdaten duerfen spaeter nur lokal gespeichert werden.
- Zugriff auf die Web-UI sollte ueber Home Assistant Ingress oder das lokale Netzwerk erfolgen.
- MQTT-Passwort wird in `/api/config` maskiert.
- RTSP-URLs mit Credentials werden in Status/API-Ausgaben maskiert.
- Betreiber sind fuer rechtliche Verantwortung, Einwilligung, Hinweispflichten und lokale Gesetze verantwortlich.

## Roadmap

- Frigate-Integration
- Double-Take-Integration
- CompreFace-Integration
- lokale Face-Recognition-Engine
- Home-Assistant-MQTT-Auto-Discovery
- Kamera-Testfunktion
- Snapshot-Anzeige in der Web-UI
- Event-Historie
- Datenschutzmodus
- Speicherung bekannter Gesichter
- Import von Trainingsbildern
- Erkennungszonen
- Erkennungszeitfenster
- Maskierung von Bereichen
- Performance-Anzeige CPU/RAM/FPS
