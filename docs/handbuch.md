# Frigate Face Bridge - Bedien- und technisches Handbuch

Stand: Version 2026.07.002, Audit-Basis `0cdb2058ac5468ba5395988c41aaf8016935f7ce`, fachlich und technisch abgeglichen am 2026-07-15. Der maschinenlesbare Katalog `docs/functions.yaml` ist die kanonische Inventarquelle. Die dortigen IDs bleiben stabil; dieses Handbuch erklaert Bedienung und Betrieb.

## Schnellstart

1. Das Add-on installieren oder den Compose-Dienst starten.
2. Unter **Konfiguration** MQTT und optional Frigate, Face-Import, Ansagen, Terrassentuer und Kamera einstellen.
3. MQTT, Frigate, RTSP und Snapshot mit den jeweiligen Testbuttons pruefen.
4. **Ueberblick**, **Live**, **MQTT**, **Erkennungen**, **Ansagen** und **Verlauf** beobachten.

Die Bridge muss auch ohne Kamera und ohne MQTT starten. `demo_mode` wird nie automatisch aktiviert. Fehlende Optionen erhalten nur einen Runtime-Fallback; die gespeicherte `options.json` wird erst durch ausdrueckliches Speichern veraendert.

<a id="betrieb"></a>
## Betrieb und Hintergrundprozesse


Beim Start liest die Bridge Add-on-Defaults und gespeicherte Optionen, validiert sie nur fuer die Laufzeit, richtet Logging, Detektor, Ansagemanager und MQTT ein und startet zwei Hintergrundschleifen:

- `event_loop`: Im Demo-Modus erzeugt sie simulierte Ereignisse. Andernfalls ruft sie den Snapshot-Detektor auf, ausser eine aktivierte Frigate-API-Zaehlschleife ist fuer echte Daten zustaendig.
- `frigate_person_count_loop`: Fragt bei aktivierter Frigate-Integration periodisch aktive Personen und Hunde ab.

Jedes angenommene Ereignis aktualisiert den letzten Status, Zaehler und zwei auf 500 Eintraege begrenzte RAM-Verlaeufe. Ansage- und Terrassentuerdaten werden angereichert und danach per MQTT publiziert. Die API liefert jeweils hoechstens die letzten 50 Status-/Ansageeintraege; `/api/history` liefert den aktuellen In-Memory-Verlauf. Nach Neustart sind diese Verlaeufe leer.

SIGTERM und SIGINT setzen den Laufzustand auf beendet, publizieren nach Moeglichkeit MQTT `offline` und stoppen den MQTT-Netzwerkloop. Integrationsfehler werden protokolliert; die periodische Frigate-Schleife versucht es nach ihrem Intervall erneut.

<a id="konfiguration"></a>
## Konfigurationsverwaltung


Es gelten drei getrennte Ebenen:

- `config.yaml`: Schema und Erstinstallationsvorschlag.
- the add-on options file: gespeicherte Nutzerwerte; nur explizite API-/UI-Speicheraktionen schreiben diese Datei.
- Runtime-Konfiguration: Defaults und gespeicherte Werte werden im Speicher verschmolzen und validiert.

GET `/api/config` liefert eine maskierte Runtime-Konfiguration, maskierte gespeicherte Rohwerte und reine Gesetzt-/Nicht-gesetzt-Indikatoren. MQTT-Passwort und sensible Kamera-URLs werden nicht im Klartext ausgegeben. Ein Passwortfeld mit `***` wird beim Speichern ignoriert, damit es kein echtes Secret ersetzt. Teilupdates erhalten alle nicht uebermittelten Nutzerwerte.

Validiert werden unter anderem Log-Level, Mindestwerte fuer Intervalle/Dimensionen, MQTT-Topics, Hostzeichen, Kamera-/Frigate-Namen, HTTP-/RTSP-Schemas und Confidence im Bereich 0 bis 1. Warnungen koennen Runtime-Fallbacks setzen, schreiben diese aber nicht automatisch zurueck.

<a id="erkennung"></a>
## Demo- und Snapshot-Erkennung


Im Demo-Modus werden zufaellige Personenanzahl, bis zu zwei aktivierte bekannte Namen, unbekannte Personen und eine Confidence erzeugt. Dies dient ausschliesslich Tests und darf nicht automatisch eingeschaltet werden.

Im Nicht-Demo-Betrieb kann der Snapshot-Detektor ein HTTP(S)-Bild bis 5 MiB laden. Er prueft URL, Content-Type und Groesse. Der veroeffentlichte Stand fuehrt **noch keine echte Erkennung im Snapshot** durch; ein erfolgreicher Abruf meldet deshalb `snapshot captured; detection is not implemented yet` bei Personenanzahl 0. Fehlende URL, Netzwerk-, Content-Type- oder Groessenfehler werden als erklaerendes Nullereignis geliefert.

<a id="frigate-events"></a>
## Frigate-Events und aktive Objekte


Der MQTT-Import verarbeitet nur Objekte mit `label=person`, verwirft `false_positive=true` und kann exakt auf `frigate.camera_name` filtern. `new`/`update` ergibt eine aktive Person; `end`/`deleted` beendet sie. Quelle ist `frigate_mqtt`.

Der aktive Zaehler ruft fuer dieselbe Kamera Frigate `/api/events` getrennt fuer `person` und `dog` mit `in_progress=1` auf. Beendete, falsche oder anders beschriftete Ereignisse werden ausgeschlossen. Bekannte Namen koennen aus `sub_label` oder Attributdaten stammen. Der konfigurierte Hundename wird bei mindestens einem Hund zu den erkannten Entitaeten ergaenzt. Diese zyklischen Zustandszeilen sind keine Garantie fuer ein neues Betreten des Bilds.

Erforderlich sind aktiviertes Frigate, MQTT fuer Eventimport und eine HTTP(S)-API-URL fuer aktive Zaehler. Der REST-Abruf hat acht Sekunden Timeout und liest maximal 512 KiB je Antwort.

<a id="gesichter"></a>
## Bekannte Gesichter und Face-Import


Das Register kombiniert `known_faces` aus der Konfiguration mit the add-on face registry; lokale Eintraege gewinnen bei gleichem Namen. Namen sind 1 bis 80 Zeichen lang und duerfen Buchstaben, Ziffern, Leerzeichen, Punkt, Unterstrich und Bindestrich enthalten. **Person anlegen** erstellt oder aktualisiert einen Eintrag. Der dynamische Button je Person schaltet `enabled` um. Bilder werden im aktuellen Stand nicht hochgeladen; `image_count` bleibt eine Metadatenanzeige.

Externe Face-Events kommen ueber das konfigurierte MQTT-Topic oder POST `/api/face-events`. Nur aktivierte Registereintraege mit Confidence mindestens `face_recognition.min_confidence` werden als bekannte Namen uebernommen. Nicht registrierte Namen werden nicht automatisch angelegt. `unknown_faces` wird separat gezaehlt. Ohne bekannten oder unbekannten Treffer wird das Ereignis ignoriert.

<a id="ansagen"></a>
## Ansagen und Cooldowns


Die Bridge erzeugt Text und MQTT-Signale, spricht aber nicht selbst. Home Assistant oder ein anderer Verbraucher entscheidet ueber die eigentliche TTS-Ausgabe.

- Kategorien fuer bekannte, unbekannte Personen und Hund lassen sich einzeln schalten.
- `disabled_entities` ist eine kommagetrennte, case-insensitive Sperrliste; `unknown` oder `unbekannt` sperrt Unbekannte.
- Der globale Cooldown sperrt alle weiteren Ansagen fuer die konfigurierte Zeit.
- Der Entitaets-Cooldown sperrt denselben Namen, Hund oder `unknown` fuer die konfigurierte Zeit.
- Eigene Texte haben das Format `Schluessel=Text`, eine Zeile pro Regel. Schluessel koennen ein Name, `known`, `dog`, `unknown`, `multiple` oder `default` sein. `{name}` und `{names}` werden ersetzt.
- Ohne eigene Vorlage werden Zufallstexte oder der feste Text `{names} wurde erkannt.` verwendet.

Ansagenansicht und MQTT `recognition_log` zeigen Text, Entitaeten, `spoken` und einen Sperrgrund wie `announcements_disabled`, `global_cooldown` oder `entity_cooldown`.

<a id="mqtt"></a>
## MQTT und Home Assistant


Nach erfolgreicher Verbindung publiziert die Bridge retained `online`, Home-Assistant-Discovery und abonniert aktivierte Frigate-/Face-Topics. Beim kontrollierten Stopp wird retained `offline` versucht. Eingehende Nachrichten ueber 256 KiB werden verworfen. Das UI-Nachrichtenlog speichert maximal 200 Eintraege im RAM, kuerzt Payloads auf 4096 Zeichen und maskiert Passwort-, Token-, Secret- und sensible URL-Werte.

Unter `<topic_prefix>/<camera>/` werden publiziert:

| Topic-Suffix | Inhalt |
|---|---|
| `person_count`, `dog_count`, `maja_present` | Objektzaehler und Hundeanwesenheit |
| `known_faces`, `recognized_entities`, `unknown_faces` | Namen und unbekannte Anzahl |
| `announcement_text`, `announcement_should_speak`, `announcement_entities` | Ansagesteuerung |
| `recognition_log` | Text, gesprochen, Entitaeten und Sperrgrund |
| `terrace_door_open`, `terrace_door_confidence`, `terrace_door_last_changed` | Tuerstatus |
| `last_event` | Vollstaendiges angereichertes Ereignis |

`<topic_prefix>/status` liefert den Bridge-Status. Bei Discovery entstehen 15 Sensor-Konfigurationen unter `<discovery_prefix>/sensor/<unique_id>/config`, passend zu den genannten Zustandswerten. Die Terrassentuer-Option ist ein Bridge-Fallback/Entity-Wert und kein automatischer Home-Assistant-Tuerkontaktimport.

<a id="api"></a>
## HTTP-API


Die API hat keine eigene Login-Schicht. Im Add-on-Betrieb ist Home-Assistant-Ingress der vorgesehene Schutz. Der optionale Direktport oder die Compose-Portfreigabe muessen netzseitig geschuetzt werden.

| Methode und Route | Eingabe | Erfolg/Ausgabe | Fehler und Seiteneffekt |
|---|---|---|---|
| `GET /` | keine | Web-UI | Statische Datei |
| `GET /health` | keine | `ok`, `healthy`, UTC-Startzeit | Nur Bereitschaft, keine Integrationsgarantie |
| `GET /api/status` | keine | Gesamtstatus, letzte 50 Verlaeufe, MQTT, Kommunikation | Kann kurze go2rtc-Netzpruefung ausfuehren |
| `GET /api/cameras` | keine | Ein maskierter Kamerastatus | Keine Aenderung |
| `GET /api/last-event` | keine | Letztes Event oder `null` | Keine Aenderung |
| `GET /api/history` | keine | RAM-Verlauf und Frigate-Zaehlerreihe | Nach Neustart leer |
| `GET /api/config` | keine | Maskierte Runtime-/Rohkonfiguration und Gesetzt-Status | Keine Secrets im Klartext |
| `POST /api/config` | partielles JSON | Aktualisierte Konfiguration und Status | 400 Validierung, 500 Speichern; schreibt Optionen und startet Detektor/MQTT neu |
| `GET /api/faces` | keine | Gesichtsregister | Keine Aenderung |
| `POST /api/faces` | `name`, optional `enabled` | Gespeicherte Person und Register | 400 Name/Payload, 500 Speichern; schreibt faces.json |
| `PATCH /api/faces/<name>` | `enabled` erforderlich | Aktualisierte Person | 400/404/500; schreibt faces.json |
| `POST /api/face-events` | Face-Event JSON | Normalisiertes Ereignis | 400 ohne verwertbaren Treffer; aktualisiert Verlauf/MQTT |
| `POST /api/config/camera` | Kamera-Teilobjekt | Kamerastatus | 400/500; schreibt Optionen und erstellt Detektor neu |
| `POST /api/test/mqtt` | optional `mqtt` | Login-/Verbindungsstatus | 502 bei Fehler; temporaere Brokerverbindung |
| `POST /api/test/frigate` | optional `frigate.api_url` | Erreichbarer Pfad und HTTP-Status | 502 bei Fehler; prueft stats, config, dann `/` |
| `POST /api/test/rtsp` | optional `camera.rtsp_url` | TCP-Erreichbarkeit, maskierte URL | 502 bei Fehler; keine Stream-Decodierung |
| `POST /api/test/snapshot` | optional `camera.snapshot_url` | Bild-Content-Type und maskierte URL | 400 URL, 502 Netz; prueft noch keine Groesse |
| `GET /api/camera/snapshot` | konfigurierte URL | Bild bis 5 MiB, `Cache-Control: no-store` | 400 Konfiguration, 502 Abruf/Typ/Groesse |

Konfigurierbare Ziel-URLs sind SSRF-relevante Vertrauensgrenzen. Nur vertrauenswuerdige interne Frigate-/Kameraendpunkte eintragen.

<a id="oberflaeche"></a>
## Web-Oberflaeche


Die UI verwendet relative API-URLs und funktioniert dadurch unter Ingress sowie Direktzugriff. Beim Start werden Status und Konfiguration parallel geladen. Danach werden sie alle fuenf Sekunden neu abgefragt. UTC-Zeitwerte werden im Browser lokal formatiert, soweit eine formatierte Anzeige vorgesehen ist. Statuskarten, letzte Ereignisse, MQTT-Log, Erkennungen, Ansagen, Verlauf, Kommunikationsschema, Debug und Links werden mit sicheren DOM-Textknoten aktualisiert.

Formulare senden nur Felder, die vom geladenen Rohwert abweichen. Meldungen zeigen laufende, erfolgreiche und fehlgeschlagene Aktionen. Im aktuellen HEAD werden Buttons waehrend Requests jedoch nicht technisch deaktiviert; schnelle Mehrfachklicks sind daher ein verbleibendes UI-Risiko. Es bestehen keine automatisierten Browser-Tests.

<a id="monitoring"></a>
## Navigation und Monitoring


Die zehn Tabs wechseln ohne Seitenreload. Die letzte Ansicht bleibt in Browser-`localStorage` gespeichert. Die Kommunikationsansicht hat die Stufen Kamera, go2rtc, Frigate, Face Bridge und Home Assistant. Ein Klick zeigt Status, Host, Port, API/Stream, Snapshot, Topic, Filter und Datenfluss. Die Darstellung sagt nur, was konfiguriert beziehungsweise per kurzer Pruefung erreichbar ist.

MQTT-, Erkennungs-, Ansage- und Verlaufstabellen besitzen jeweils Zeitbereich und Volltextsuche. Zeitbereiche reichen von vier Stunden bis alle vorhandenen RAM-Eintraege. Treffer werden markiert, neueste Eintraege stehen zuerst. Leere Tabellen und das Diagramm zeigen ausdrueckliche Leerzustaende. Es gibt keine Sortierbuttons oder Detaildialoge im aktuellen Stand.

<a id="app-formular"></a>
## Betriebsformular bedienen


1. Im Tab **Konfiguration** nur gewuenschte Felder aendern.
2. MQTT und Frigate bei Bedarf mit den Testbuttons gegen die aktuellen Formularwerte pruefen.
3. **Betrieb speichern** waehlen. Ohne erkannte Aenderung wird keine API-Anfrage gesendet.
4. Erfolgs- oder Fehlermeldung unter dem Formular beachten.

Das MQTT-Passwort bleibt bei leerem Feld unveraendert. Ein neuer Wert wird gespeichert, aber anschliessend nur maskiert beziehungsweise als gesetzt angezeigt. Ein erfolgreicher MQTT-Test bedeutet einen erfolgreichen temporaeren Login; der separate Laufzeitstatus zeigt, ob der aktive Publisher verbunden ist. Der RTSP-Test prueft nur TCP-Erreichbarkeit, nicht Decodierbarkeit oder Bildinhalt.

<a id="kamera-formular"></a>
## Kameraformular bedienen


- **Kameraname** wird auf Buchstaben, Ziffern, Unterstrich und Bindestrich normalisiert.
- **IP-Adresse / Host** erlaubt Host-, IP-, Doppelpunkt- und Bindestrichzeichen.
- **RTSP URL** akzeptiert RTSP, RTSPS, HTTP oder HTTPS. **Beispiel uebernehmen** setzt einen nicht geheimen go2rtc-Beispielwert, der angepasst werden muss.
- **Snapshot URL** akzeptiert HTTP oder HTTPS. Der zweite Beispielbutton setzt eine anpassbare Frigate-Beispieladresse.
- **Speichern** persistiert nur geaenderte, nicht maskierte Werte.
- **RTSP testen** prueft den Zielport. **Snapshot testen** prueft, ob die Antwort ein Bild ist. **Vorschau laden** ruft den auf 5 MiB begrenzten Bridge-Proxy auf.

URLs mit Zugangsdaten werden in API und UI maskiert. Ein maskierter Wert wird nicht zurueckgespeichert. Fuer eine Aenderung muss die vollstaendige neue URL eingegeben werden.

<a id="links"></a>
## Ingress, Direktzugriff und Links


Die vollstaendige UI ist fuer Home-Assistant-Ingress vorgesehen. Wenn die Seite direkt auf Port 8099 geoeffnet wird, erscheint ein Hinweis mit Link zur Add-on-Webseite. Der Tab **Links** enthaelt Home Assistant, Add-on/Ingress, Homepage-Aufruf, Health, Status-/Konfigurations-API, Frigate, go2rtc, Repository, Issues und Changelog. Frigate/go2rtc bleiben ohne konfigurierte API-URL deaktiviert. Externe Links oeffnen mit `noreferrer`.

<a id="konfigurationsfelder"></a>
## Konfigurationsfelder


| Feld | Typ / Pflicht | Default | Erlaubt und Validierung | Wirkung |
|---|---|---|---|---|
| `demo_mode` | bool / ja | `false` | bool-artig; nie automatisch aktivieren | Simulierte Ereignisse statt echter Quelle |
| `log_level` | Auswahl / ja | `info` | `trace`, `debug`, `info`, `warning`, `error`; trace nutzt DEBUG | Logumfang |
| `event_interval_seconds` | int / ja | `10` | mindestens 1 | Demo-/Snapshot-Schleifenintervall |
| `mqtt.enabled` | bool / ja | `true` im Add-on-Schema | benoetigt Host; Frigate-/Face-MQTT-Import benoetigt MQTT | Brokerverbindung |
| `mqtt.host` | string / ja | `core-mosquitto` | Hostzeichen `[A-Za-z0-9_.:-]` | Brokerziel |
| `mqtt.port` | port / ja | `1883` | mindestens 1 | Brokerport |
| `mqtt.username` | string / nein | leer | beliebiger String | Brokerlogin |
| `mqtt.password` | password / nein | leer | maskierte Werte werden nicht gespeichert | Brokerlogin-Secret |
| `mqtt.topic_prefix` | string / ja | `ha/frigate_face_bridge` | Topiczeichen, Rand-Slashes entfernt | Ausgabe-Basis |
| `mqtt.discovery` | bool / ja | `true` | bool-artig | HA Discovery an/aus |
| `mqtt.discovery_prefix` | string / ja | `homeassistant` | gueltiges Topic | Discovery-Basis |
| `frigate.enabled` | bool / ja | `false` | erfordert MQTT fuer Eventimport | Integration an/aus |
| `frigate.events_topic` | string / ja | `frigate/events` | gueltiges Topic, bei Import nicht leer | MQTT-Eingang |
| `frigate.camera_name` | string / nein | leer | wird zu `[A-Za-z0-9_-]` normalisiert | Exakter Kamera-Filter/API-Kamera |
| `frigate.api_url` | string / nein | leer | HTTP/HTTPS, ohne End-Slash | aktive Objekte und go2rtc |
| `frigate.person_count_enabled` | bool / ja | `true` | bool-artig | periodische aktive Zaehler |
| `frigate.person_count_interval_seconds` | int / ja | `5` | mindestens 1 | REST-Pollingintervall |
| `frigate.dog_name` | string / ja | `Example Dog` | Buchstaben, Ziffern, Leerzeichen, `_` und `-` | Anzeige/Ansage fuer Hunde |
| `face_recognition.enabled` | bool / ja | `false` | erfordert MQTT fuer Topicimport | Face-MQTT-Import |
| `face_recognition.events_topic` | string / ja | `face_recognition/events` | gueltiges Topic | Face-MQTT-Eingang |
| `face_recognition.min_confidence` | float / ja | `0.7` | auf 0 bis 1 begrenzt | Treffer-Schwelle |
| `announcements.enabled` | bool / ja | `true` | bool-artig | Ansagesignale gesamt |
| `announcements.announce_known` | bool / ja | `true` | bool-artig | bekannte Namen |
| `announcements.announce_unknown` | bool / ja | `true` | bool-artig | Unbekannte |
| `announcements.announce_dog` | bool / ja | `true` | bool-artig | Hund |
| `announcements.random_texts_enabled` | bool / ja | `true` | bool-artig | wechselnde Standardtexte |
| `announcements.global_cooldown_seconds` | int / ja | `60` | mindestens 0 | Gesamtsperre |
| `announcements.entity_cooldown_seconds` | int / ja | `300` | mindestens 0 | Sperre je Entitaet |
| `announcements.disabled_entities` | string / nein | leer | maximal 1000 Zeichen, kommagetrennt | Sperrliste |
| `announcements.custom_texts` | string / nein | leer | maximal 5000 Zeichen, `key=text` je Zeile | Vorlagen |
| `terrace_door.enabled` | bool / ja | `false` | bool-artig | dokumentiert Aktivierung; Publikation erfolgt im HEAD dennoch mit jedem Event |
| `terrace_door.open` | bool / ja | `false` | bool-artig | Fallback-Tuerstatus |
| `terrace_door.confidence` | float / ja | `0.0` | auf 0 bis 1 begrenzt | Tuer-Confidence |
| `terrace_door.last_changed` | string / nein | leer | keine Zeitformatvalidierung | letzter bekannter Zeitpunkt |
| `camera.name` | string / ja | leer | normalisierte Kamera-ID | Topic-/Anzeige-Kamera |
| `camera.host` | string / nein | leer | Hostzeichen | Status/Kommunikation |
| `camera.rtsp_url` | string / nein | leer | RTSP, RTSPS, HTTP oder HTTPS | Streamreferenz/Test |
| `camera.snapshot_url` | string / nein | leer | HTTP oder HTTPS | Snapshot/Test/Vorschau |
| `camera.detect_width` | int / ja | `640` | mindestens 1; nicht in Web-UI editierbar | reservierte Detektorbreite |
| `camera.detect_height` | int / ja | `360` | mindestens 1; nicht in Web-UI editierbar | reservierte Detektorhoehe |
| `camera.detect_fps` | int / ja | `5` | mindestens 1; nicht in Web-UI editierbar | reservierte Detektorrate |
| `known_faces[].name` | string / ja | drei Beispielnamen im Add-on-Schema | nicht-leer; Register nutzt strengere Namensvalidierung | initial bekannte Person |
| `known_faces[].enabled` | bool / ja | `true` | bool-artig | Trefferfreigabe |

Die drei `camera.detect_*` Felder werden validiert und angezeigt, steuern im aktuellen Snapshot-Detektor aber noch keine Bildanalyse. `terrace_door.enabled` wird im Status gefuehrt; `publish_event` publiziert die Tuer-Topics im aktuellen HEAD unabhaengig von diesem Schalter. Diese Abweichungen sind dokumentiertes Ist-Verhalten, keine Zusage fuer gewuenschtes Verhalten.

<a id="betriebspfade"></a>
## Start-, Container- und Pruefpfade


`run.sh` startet `/app/main.py`. Die Anwendung liest die Version aus der kanonischen Root-Datei `VERSION`; das Image erhaelt denselben Wert ueber Home Assistants `BUILD_VERSION`, waehrend das Beispiel-Compose die Root-Datei read-only einbindet. Das Dockerfile verwendet Python 3.12 Alpine, installiert Bash/tzdata und `requirements.txt`, kopiert `config.yaml` als `/app/addon_config.yaml`, Anwendung und Startskript und exponiert Port 8099.

Home Assistant aktiviert Ingress auf 8099; die direkte Portzuordnung ist standardmaessig `null`. Das Beispiel-Compose exponiert dagegen `8099:8099`, bindet `deploy/data` nach `/data` und startet bei Fehlern/Hostneustart erneut. Dieser Port braucht einen vertrauenswuerdigen Netzbereich, weil die App keine eigene Authentifizierung besitzt.

Die CI installiert Anforderungen plus pytest, kompiliert alle App-Python-Dateien und fuehrt `pytest -q` aus. Fuer die Funktionsdokumentation kommt lokal hinzu:

```bash
python3 scripts/validate_function_docs.py
```

Der Validator benoetigt nur die Python-Standardbibliothek. Er prueft Katalogstruktur, stabile IDs, Pflichtfelder, Handbuch-/Datei-/Testreferenzen, alle eigenen Python- und JavaScript-Funktionen, Flask-Routen, Konfigurationsschemafelder, Betriebsdateien und interaktive statische beziehungsweise dynamische UI-Elemente.

## Sicherheit und Datenschutz

- Kamera- und Gesichtsdaten koennen personenbezogen sein. Zugriff auf UI, MQTT, `/data` und Logs begrenzen.
- MQTT-Passwort, URL-Credentials und Tokens nicht in Issues, Logs oder Supporttexte uebernehmen.
- Nur vertrauenswuerdige interne URLs konfigurieren; Frigate-/Snapshot-/RTSP-Tests und Abrufe erzeugen serverseitige Netzwerkverbindungen.
- Ingress bevorzugen. Compose-/Direktport netzseitig authentisieren oder isolieren.
- Das Nachrichtenlog liegt nur im RAM, kann aber Namen und Ereignisdaten enthalten.

## Bekannte Grenzen

- Snapshot-Abruf ist implementiert, echte Snapshot-Personen-/Gesichtserkennung nicht.
- Die Bridge erzeugt Ansagesignale, keine direkte TTS-Ausgabe.
- Historien sind fluechtig und auf RAM-Limits begrenzt.
- Es gibt keine Browser-Automationstests und keinen Mehrfachklickschutz durch deaktivierte Aktionsbuttons.
- `config.yaml.version` bleibt als technisch verpflichtende Home-Assistant-Metadatenkopie bestehen und wird gegen die kanonische Root-Datei `VERSION` getestet.
- Der globale Regelstand ist in `docs/rules/global-rule-baseline.json` festgehalten und muss bei kuenftiger Drift erneut auditiert werden.

<a id="atomic-inventory"></a>
## Technische Funktionsreferenz

Der kanonische Katalog enthaelt 546 einzeln an Quellcode gebundene Einheiten. `scripts/validate_function_docs.py` prueft Audit-Basis, Quellfingerprints, stabile IDs, GUI-Bindungen, delegierte JavaScript-Effekte und alle Pflichtfelder. Detailangaben zu Signaturen, Zustandswegen, Seiteneffekten, Sicherheit und Tests stehen strukturiert in `docs/functions.yaml`; dieses Handbuch beschreibt die fuer Betrieb und Wartung relevanten Zusammenhaenge statt generierter Symbolprosa.

<a id="inventory-python"></a>
### Python (169)

Python-Funktionen umfassen Konfigurationsvalidierung und -persistenz, Eventnormalisierung, MQTT-Ausgabe, Netzwerkpruefungen, Hintergrundschleifen sowie die Dokumentationswerkzeuge. Dateischreibvorgaenge wie `config_loader._write_options`, Netzwerkzugriffe und Shared-State-Mutationen werden als Seiteneffekte ausgewiesen.

<a id="inventory-javascript"></a>
### Javascript (95)

JavaScript-Einheiten umfassen benannte Funktionen und Arrow-Callbacks. Der Katalog propagiert Effekte ueber den Call-Graph: Der Klick-Callback in `renderFaces` erbt deshalb den PATCH-Request und die DOM-Aktualisierung von `setFaceEnabled`, statt faelschlich als effektfrei zu gelten.

<a id="inventory-route"></a>
### Route (18)

Jede Flask-Route ist separat mit HTTP-Methode, Pfad, Handler, Statuswegen und den vom Handler geerbten Datei-, Netzwerk-, MQTT- oder Zustandswirkungen dokumentiert. Die API besitzt keine eigene Login-Schicht und bleibt eine Ingress-/Netzwerk-Trust-Boundary.

<a id="inventory-gui"></a>
### Gui (217)

Alle statischen Eingaben, Aktionen und Anzeigen sind ueber `data-doc-id` gebunden. Jede `createElement`- und `createElementNS`-Erzeugungsstelle wird direkt aus dem JavaScript entdeckt und braucht eine eigene source-lokale ID. Dadurch sind Daten- und Leerzustaende fuer History, Erkennung, MQTT, Ansagen, Topics, Chips, Key/Value-Listen, Diagramme und Face-Listen getrennt inventarisiert.

<a id="inventory-config"></a>
### Config (43)

Die Konfigurationsreferenz nennt Schematyp, Pflichtstatus, Installationsdefault und Runtime-Validierung. Persistierte Nutzerwerte werden nur durch explizites Speichern geaendert; maskierte Secrets werden nicht zurueckgeschrieben.

<a id="inventory-operation"></a>
### Operation (4)

CI, Dockerfile, Compose und Startskript sind als Betriebsfunktionen erfasst. Die Lint-CI kompiliert Python, fuehrt pytest aus und blockiert bei einem ungueltigen Funktionskatalog.

### Integritaet und ID-Stabilitaet

`audited_head` ist die vollstaendige Commit-ID des vor Erstellung oder Aktualisierung des Inventars fachlich geprueften Basisstands. Sie muss existieren und Vorfahr des validierten Repository-HEAD sein; eine Gleichheit mit dem Inventar-Commit waere eine unloesbare Selbstreferenz. Der Top-Level-Quelldigest bindet stattdessen den gesamten aktuellen inventarisierten Quellumfang, und jeder Eintrag enthaelt zusaetzlich einen SHA-256-Fingerprint seiner Quelldatei und technischen Referenz. Produktquellenaenderungen nach der Audit-Basis schlagen deshalb weiterhin fehl, bis Katalog und Review aktualisiert werden. `docs/function-id-baseline.json` speichert die dauerhafte Zuordnung aus Einheit und Dokumentations-ID; Umbenennungen oder Wiederverwendung einer ID schlagen im Validator fehl und muessen bewusst migriert werden.
