# Changelog

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
