# Roadmap

Diese Roadmap haelt den Projektstand und die naechsten Ausbaustufen fuer `Frigate Face Bridge` fest.

## Status

Aktueller Stand: **Stufe 19 abgeschlossen**.

Aktuelle Add-on-Version: `0.16.0`.

## Stufe 1 - Add-on-Basis

Status: **abgeschlossen**

Ziel: Das Projekt ist als Home-Assistant-Add-on installierbar und startet sicher ohne Kamera und ohne MQTT.

Umgesetzt:

- Home-Assistant-Add-on-Struktur mit `config.yaml`
- Dockerfile und `run.sh`
- Python/Flask-App auf Port `8099`
- Konfiguration ueber `/data/options.json`
- sicherer Standard `demo_mode: false`
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

## Stufe 14 - Ansageereignisse und Erkennungslog

Status: **abgeschlossen**

Ziel: Erkannte Personen, unbekannte Personen und Hund sollen einstellbare Ansageereignisse und ein nachtraegliches Log erzeugen.

Umgesetzt:

- Ansage-Manager mit Zufallstexten, eigenen Texten, Sperrliste und Cooldowns
- MQTT Topics und Discovery fuer Ansagetext, Ansageausloeser, Entitaeten und Erkennungslog
- Web-UI-Konfiguration und History-Erweiterung fuer Ansagen

Abnahme:

- Ansageereignisse werden in API, Web-UI und MQTT sichtbar.
- Wiederholte Ansagen werden ueber Cooldowns begrenzt.

## Stufe 15 - Navigierbare Live-UI und MQTT-Ansicht

Status: **abgeschlossen**

Ziel: Die Face-Bridge-App soll MQTT-Nachrichten, Namen und Live-Daten in sinnvollen Sichten mit Menuefuehrung anzeigen.

Umgesetzt:

- Menue-Sichten fuer Ueberblick, Live, MQTT, Erkennungen, Ansagen, Verlauf, Konfiguration und Debug
- Maskierte Live-History fuer ein- und ausgehende MQTT-Nachrichten
- Eigene Live-Sichten fuer erkannte Namen, unbekannte Personen, Hundestatus, Ansagen und MQTT-Topics

Abnahme:

- Die Web-UI zeigt Live-Daten und MQTT-Nachrichten ohne Secrets.
- Bestehende Konfiguration und Verlauf bleiben erreichbar.

## Stufe 16 - Parameterverwaltung ohne Update-Ueberschreibung

Status: **abgeschlossen**

Ziel: Parametrierte Nutzerwerte sollen bei Start, Neustart und Update nicht automatisch initialisiert, ueberschrieben, normalisiert oder als Defaults persistiert werden.

Umgesetzt:

- Wiederverwendbare Regel in `docs/projekt-parameter-management.md`
- Trennung zwischen gespeicherten Rohoptionen und Runtime-Konfiguration
- `demo_mode` fuer fehlende/neue Werte standardmaessig aus
- `/api/config` liefert `raw_config` zusaetzlich zur Runtime-Konfiguration

Abnahme:

- Fehlende neue Optionen funktionieren zur Laufzeit, ohne automatisch in `/data/options.json` geschrieben zu werden.
- Bestehende Nutzerwerte fuer `demo_mode` bleiben true oder false, wie gespeichert.

## Stufe 17 - Konfigurationspersistenz und responsive Bedien-UI

Status: **abgeschlossen**

Ziel: Die Web-UI soll gespeicherte Werte nicht durch leere Formularfelder ersetzen, gesetzte Secrets/URLs verstaendlich anzeigen, Testfunktionen anbieten und auf iPhone sowie voller Desktop-Breite bedienbar sein.

Umgesetzt:

- Template fuer sichere Parameter- und UI-Aenderungen unter `docs/templates/AGENT_PARAMETER_UI_CHANGE_TEMPLATE.md`
- Teilupdates fuer Betriebs- und Kamerakonfiguration statt Vollformular-Speicherung
- Statusanzeigen fuer gesetzte MQTT-/Kamera-Secrets ohne Offenlegung
- Testbuttons fuer MQTT, RTSP und Snapshot
- Vollbreite, mobile UI mit filterbaren, scrollbareren Listen und lesbaren Debug-/Live-Textlisten

Abnahme:

- Leere Formularfelder ueberschreiben keine gespeicherten Nutzerwerte.
- Listen sind nach Zeitbereich und Volltext filterbar; Treffer werden markiert.
- Debug und Live zeigen lesbare Statuslisten statt JSON-/YAML-Dumps.

## Stufe 18 - Links, Schema und neutrale Kamera-Beispiele

Status: **abgeschlossen**

Ziel: Die Web-UI soll erklaeren, wie die Bridge zwischen Kamera, UniFi Protect, Frigate, MQTT und Home Assistant arbeitet, relevante Links direkt anbieten und keine alten Kamera-Beispielwerte als neue Defaults setzen.

Umgesetzt:

- Schemazeichnung im Ueberblick fuer Hin- und Rueckweg der Daten
- Links-Sicht fuer Bridge-API, Frigate/go2rtc und GitHub-Seiten
- Header mit Add-on-Version und Erstellerhinweis
- Snapshot-Beispielbutton analog zum RTSP-Beispielbutton
- Neue Installationen bekommen leere Kamera-Name-/Host-Felder statt alter Beispielwerte

Abnahme:

- Bestehende gespeicherte Kamera-Werte bleiben bei Updates erhalten.
- Neue Installationen zeigen keine irrefuehrenden Default-Werte `garage_g3_flex` oder `192.168.2.241`.
- Relevante Projekt- und Weboberflaechen sind in der Links-Sicht anklickbar.

## Stufe 19 - Live-Kommunikation und HA-Ingress-Fokus

Status: **abgeschlossen**

Ziel: Die Bridge soll die aktuelle Kommunikation von Kamera/UniFi ueber go2rtc/Frigate und Face Bridge bis Home Assistant live, verstaendlich und mit Status darstellen. Der direkte Port `8099` soll nicht als zweite Detail-Webseite erscheinen.

Umgesetzt:

- Neuer Menuepunkt `Kommunikation` nach Vorlage `docs/templates/ffb_schema_go2rtc_grouped.html`
- Live-Anzeige fuer Status, Host/DNS/IP, Port, go2rtc-Nutzung und ausgetauschte Daten je Element
- Links-Sicht mit HA-Add-on-Aufruflink fuer Homepage und getrenntem Health-/Status-Link fuer direkten `8099`-Zugriff
- Direktzugriff zeigt nur Status und verweist auf die Home-Assistant-Add-on-Webseite

Abnahme:

- Kommunikationsdaten werden aus der aktuellen Runtime-Konfiguration/API abgeleitet und ohne Secrets angezeigt.
- Details werden in der HA-Add-on-Webseite gebuendelt.
- Homepage-Link zeigt auf die HA-Ingress-Webseite statt auf den direkten Port.

## Laufende Sicherheitsregeln

- Keine Secrets, Tokens, Passwoerter oder vollstaendige RTSP-URLs mit Credentials committen.
- MQTT-Passwoerter maskieren.
- RTSP- und Snapshot-URLs vor Logging/API-Ausgabe maskieren.
- Add-on muss ohne Kamera und ohne MQTT starten koennen.
- `demo_mode` wird nicht automatisch aktiviert; gespeicherte Nutzerwerte bleiben erhalten.
