# Changelog

## 2026.07.004

### Changed

- Die bisherige GitHub-Lint-Automation wurde durch den manuell auszufuehrenden lokalen Pruefeinstieg `scripts/run-local-checks.sh` ersetzt ([#16](https://github.com/thomas682/ha-frigate-face-bridge/issues/16)).
- Die Funktionsreferenz erfasst den lokalen Pruefpfad statt eines GitHub-Workflow-Schritts.

## 2026.07.003

### Fixed

- Die Versionsermittlung startet auch im echten Home-Assistant-Add-on-Layout `/app/main.py` ohne `IndexError` und liefert bei fehlender oder leerer `VERSION` sicher `unbekannt` ([#12](https://github.com/thomas682/ha-frigate-face-bridge/issues/12)).

### Changed

- Funktionskatalog, Review-Fingerprints, Handbuch und globale Regel-Baseline wurden gemeinsam gegen den aktuellen Quell- und Regelstand aktualisiert.

## 2026.07.002

- Die Funktionsinventar-Pruefung bindet Reviews jetzt ohne Selbstreferenz an eine existierende Audit-Basisrevision, die Vorfahr des validierten Commits sein muss ([#13](https://github.com/thomas682/ha-frigate-face-bridge/issues/13)).
- Aktueller Quellbaum-Digest, Einzelfingerprints, kanonische Vertraege und stabile Dokumentations-IDs bleiben unveraendert strikt geprueft.

## 2026.07.001

### Fixed

- Die Hund-Anwesenheitsanzeige aktualisiert wieder das vorhandene Element `dog-present` statt der nicht existierenden ID `maja-present`.

### Changed

- Die kanonische Release-Version liegt im Repository-Root in `VERSION`; Runtime und UI lesen diesen Wert ohne veraltete Code-Fallbacks.
- Das von Home Assistant vorgeschriebene Feld `config.yaml.version` spiegelt dieselbe Version `2026.07.001`.
- Funktionskatalog, Handbuch, stabile UI-Dokumentations-IDs, Review-Versionen und Quellfingerprints wurden auf den auditierten Baseline-Stand aktualisiert.

## 0.16.0

### Added

- Menuepunkt `Kommunikation` mit Live-Schema auf Basis der bereitgestellten go2rtc/Frigate-Vorlage ergaenzt ([#11](https://github.com/thomas682/ha-frigate-face-bridge/issues/11)).
- Kommunikationsstatus zeigt je Element Status, aktuelle Hosts/IPs/Ports, go2rtc-Nutzung und Daten-Austausch ohne Secret-Offenlegung.
- Links-Sicht zeigt den HA-Add-on-Aufruflink fuer Homepage und den direkten `8099`-Zugriff nur noch als optionalen Health-/Status-Link.

### Changed

- Der vereinfachte Ueberblick verweist auf die neue Kommunikationssicht; Detailinformationen werden in der HA-Add-on-Webseite gebuendelt.

## 0.15.2

### Added

- Ueberblick-Schemazeichnung fuer Datenfluss von Kamera/UniFi Protect ueber Frigate/go2rtc und MQTT bis Home Assistant ergaenzt ([#10](https://github.com/thomas682/ha-frigate-face-bridge/issues/10)).
- Links-Sicht mit Bridge-API-, Frigate-/go2rtc- und GitHub-Links ergaenzt.
- Snapshot-Beispielbutton und Headeranzeige fuer Version und Ersteller ergaenzt.

### Changed

- Kamera-Name und Kamera-Host/IP sind fuer neue Installationen neutral leer statt alter Beispielwerte `garage_g3_flex` und `192.168.2.241`; bestehende gespeicherte Nutzerwerte bleiben unveraendert.

## 0.15.1

### Added

- Feldnahe, konkrete Hilfetexte fuer die Konfigurationsparameter in der Ingress-Web-UI ergaenzt.
- Erklaertexte fuer MQTT-, Erkennungs-, Ansage- und Verlaufslogs hinzugefuegt.
- Frigate-API-Testbutton ergaenzt und vorhandene Testbuttons so erweitert, dass sie aktuelle Formulareingaben pruefen.
- RTSP-Beispielbutton und sichtbare gespeicherte RTSP-/Snapshot-URLs ohne Credential-Offenlegung ergaenzt.

## 0.15.0

### Added

- Wiederverwendbares Template fuer sichere Parameter- und UI-Aenderungen ergaenzt ([#8](https://github.com/thomas682/ha-frigate-face-bridge/issues/8)).
- Test-Endpunkte und Web-UI-Testbuttons fuer MQTT, RTSP und Snapshot ergaenzt.
- Statusanzeigen fuer gesetzten MQTT-Benutzer, gesetztes MQTT-Passwort sowie gesetzte RTSP-/Snapshot-URLs hinzugefuegt, ohne Secrets offenzulegen.
- Filterbare und scrollbare Listen mit Zeitbereichsauswahl und Treffer-Markierung fuer Verlauf, Ansagen, Erkennungen und MQTT-Nachrichten ergaenzt.

### Changed

- Web-UI speichert Betriebs- und Kamera-Konfiguration als Teilupdate, damit leere Felder keine bestehenden Nutzerwerte ueberschreiben.
- Web-UI nutzt die volle Fensterbreite und bleibt auf iPhone-Displays besser bedienbar.
- Live- und Debug-Sicht zeigen Textlisten statt JSON-/YAML-Dumps.

## 0.14.1

### Changed

- Parameterverwaltungsregel dokumentiert und gespeicherte Rohoptionen von Runtime-Konfiguration getrennt ([#7](https://github.com/thomas682/ha-frigate-face-bridge/issues/7)).
- `demo_mode` fuer fehlende/neue Werte auf `false` gesetzt, ohne bestehende Nutzerwerte zu ueberschreiben.
- `/api/config` liefert zusaetzlich `raw_config`, damit UI und API gespeicherte Werte von Runtime-Fallbacks unterscheiden koennen.

## 0.14.0

### Added

- Navigierbare Web-UI-Sichten fuer Ueberblick, Live-Daten, MQTT, Erkennungen, Ansagen, Verlauf, Konfiguration und Debug hinzugefuegt ([#6](https://github.com/thomas682/ha-frigate-face-bridge/issues/6)).
- Maskierte Live-History fuer ein- und ausgehende MQTT-Nachrichten in Status-API und Web-UI ergaenzt.
- Erkannte Namen, unbekannte Personen, Hunde, Ansagetexte und MQTT-Ausgabe-Topics als eigene Live-Ansichten sichtbar gemacht.

## 0.13.5

### Changed

- Agent-Regeln aus InfluxBro in FaceBridge-spezifischer Form uebernommen ([#5](https://github.com/thomas682/ha-frigate-face-bridge/issues/5)).
- `demo_mode`-Regel fuer Erstinstallation und Updates praezisiert.
- Versionierungs-, Docker-/Runtime-, Sicherheits-, Issue- und Abschlussregeln erweitert.

## 0.13.4

### Fixed

- Statische Dateien und REST-Aufrufe verwenden relative Pfade, damit die Web-UI unter Home-Assistant-Ingress korrekt laedt.

## 0.13.3

### Fixed

- Sichtbaren Versionshinweis in der Ingress-Weboberflaeche angeglichen.

## 0.13.2

### Fixed

- Runtime-Version fuer die REST-API an die Add-on-Version angeglichen.

### Changed

- Ingress-Weboberflaeche weiter im Command-Center-Design ausgeliefert.

## 0.13.1

### Changed

- Ingress-Weboberflaeche nach der Command-Center-Vorlage ueberarbeitet.
- Status, MQTT, Kamera, Event, Ansagen, Verlauf und Konfiguration optisch gruppiert.

## 0.13.0

### Added

- Konfigurierbare Ansageereignisse fuer bekannte Personen, unbekannte Personen und Hund hinzugefuegt.
- Globale und entitaetsbezogene Cooldowns gegen wiederholte Sprachausgaben ergaenzt.
- 20 gespeicherte Zufallstexte sowie eigene Texte und Sperrliste fuer Ansagen hinzugefuegt.
- MQTT Topics und MQTT Discovery fuer `announcement_text`, `announcement_should_speak`, `announcement_entities` und `recognition_log` ergaenzt.
- Web-UI um Ansage-Konfiguration, Ansagestatus und Ansage-/Erkennungslog erweitert.

## 0.12.1

### Changed

- Personen-Verlauf in der Web-UI von Balken auf ein Zeitreihen-Kurvendiagramm mit Flaeche, Punkten und Start-/Endzeit umgestellt.

## 0.12.0

### Changed

- Web-UI fuer das Home-Assistant-Ingress-Panel auf helles HA-aehnliches Kartendesign umgestellt.
- Kontraste, Formulare, Buttons, Tabellen und Debug-Ausgabe fuer bessere Lesbarkeit angepasst.
- Dark-Mode-Abdunklung entfernt, damit die Seitenleistenansicht stabil hell bleibt.

## 0.11.0

### Added

- Terrassentuer-Felder `terrace_door_open`, `terrace_door_confidence` und `terrace_door_last_changed` ergaenzt.
- MQTT Topics und MQTT Discovery fuer Terrassentuer-Status, Confidence und letzte Aenderung hinzugefuegt.
- Web-UI und `POST /api/config` um Terrassentuer-Konfiguration erweitert.
- Tests fuer Terrassentuer-Konfiguration und MQTT-Ausgabe ergaenzt.

## 0.10.0

### Added

- Frigate-API-Zaehler um Objekt `dog`, `dog_count` und `maja_present` erweitert.
- `recognized_entities` fuer bekannte Personen und Maja hinzugefuegt.
- MQTT Topics und MQTT Discovery fuer Hund, Maja und erkannte Entitaeten ergaenzt.
- Web-UI um History und Personen-Graph fuer das Wohnzimmer erweitert.
- Neuer REST-Endpunkt `GET /api/history`.

## 0.9.0

### Added

- Aktiven Frigate-Personenzaehler ueber die Frigate-API ergaenzt.
- Neue Frigate-Optionen `api_url`, `person_count_enabled` und `person_count_interval_seconds` hinzugefuegt.
- Web-UI um Frigate-API-URL und Polling-Optionen fuer aktive Personen erweitert.
- Tests fuer aktive Frigate-Personenzaehlung und Konfigurationsvalidierung ergaenzt.

## 0.8.2

### Fixed

- Kamera-URLs werden in API-Ausgaben jetzt konservativ maskiert: Pfad, Query und Credentials werden nicht mehr ausgegeben.
- Regressionstest fuer maskierte Kamera-URLs in `/api/status` ergaenzt.

## 0.8.1

### Changed

- Web-UI auf helles Standard-Theme umgestellt.
- Dunkles Theme bleibt ueber die System-Einstellung `prefers-color-scheme: dark` verfuegbar.

## 0.8.0

### Added

- Web-UI um Betriebs-Konfiguration fuer Demo-Modus, Event-Intervall, Log-Level, MQTT, MQTT Discovery, Frigate-Import und Face-Import erweitert.
- Neuer REST-Endpunkt `POST /api/config` fuer sichere UI-basierte Konfigurationsaenderungen ergaenzt.
- Konfigurationsfehler, Frigate-Event-Zaehler und Face-Event-Zaehler werden in der Web-UI angezeigt.
- Tests fuer Konfigurations-API, Topic-Validierung und maskierte MQTT-Passwoerter ergaenzt.

## 0.7.0

### Added

- MQTT Discovery fuer Home-Assistant-Sensoren ergaenzt.
- Discovery-Konfigurationen fuer Bridge-Status, Personenanzahl, bekannte Gesichter, unbekannte Gesichter und letzte Event-Quelle werden retained veroeffentlicht.
- Neue MQTT-Optionen `mqtt.discovery` und `mqtt.discovery_prefix` hinzugefuegt.
- Tests fuer Discovery-Payloads und Abschalten von Discovery ergaenzt.

## 0.6.0

### Added

- Externe Face-Matching-Events ueber MQTT und REST angenommen.
- Neue Konfiguration `face_recognition.enabled`, `face_recognition.events_topic` und `face_recognition.min_confidence` ergaenzt.
- Neuer REST-Endpunkt `POST /api/face-events` fuer erkannte bekannte und unbekannte Gesichter.
- Matching-Events werden gegen die lokale Face-Registry und den Confidence-Schwellwert gefiltert.
- Tests fuer Face-Matching-Parser und REST-Eventannahme hinzugefuegt.

## 0.5.0

### Added

- Lokale Face-Registry unter `/data/faces.json` als Grundlage fuer spaeteres Matching ergaenzt.
- REST-Endpunkte `GET /api/faces`, `POST /api/faces` und `PATCH /api/faces/<name>` hinzugefuegt.
- Frigate-Event-Import im App-State mit eigenem Zaehler verdrahtet.
- Tests fuer Face-Registry-API und Frigate-Handler ergaenzt.

## 0.4.0

### Added

- Optionalen Import von Frigate-MQTT-Events ueber `frigate.events_topic` ergaenzt.
- Person-Events aus Frigate erzeugen reale `person_count`-Events mit Confidence und Box-Daten.
- Tests fuer Frigate-Personen-Events, Nicht-Personen-Events und Kamera-Filter hinzugefuegt.

## 0.3.0

### Added

- Snapshot-Erfassung im Nicht-Demo-Modus in den Detector-Pfad integriert.
- Status-Events fuer erfolgreiche und fehlgeschlagene Snapshot-Abrufe ergaenzt.
- Tests fuer Snapshot-Detector-Erfolg und Fehlerfall hinzugefuegt.

## 0.2.0

### Added

- Kamera-Parameter koennen ueber die Weboberflaeche gespeichert werden.
- Snapshot-Vorschau zum Testen von HTTP/HTTPS-Kamerabildern ergaenzt.
- REST-Endpunkte fuer Kamera-Konfiguration und Snapshot-Abruf hinzugefuegt.

## 0.1.0

### Initial

- Erste lauffaehige Add-on-Basis mit Demo-Modus, REST-API, Web-UI und optionaler MQTT-Ausgabe.
- Kamera `192.168.2.241` als Host vorbereitet, ohne RTSP-Credentials zu speichern.
- Datenschutz- und Sicherheitsdokumentation ergaenzt.
