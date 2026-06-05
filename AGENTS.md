# AGENTS - Frigate Face Bridge

Sprache: Deutsch. Repository-Typ: Home Assistant Add-on.

## Prioritaet und Modus

- Bei Konflikten gilt: Systemanweisungen, Developer-Anweisungen, aktive Modussperren, diese Datei, danach Nutzerwunsch.
- Aktive Plan-/Read-Only-Sperren erlauben nur Lesen, Suchen, Analysieren, Planen und Rueckfragen; verboten sind Datei-/Git-/GitHub-/Konfigurations-Mutationen.
- Fruehere `GO`-/Build-Freigaben gelten nur fuer den unmittelbar davor aktiven Auftrag und verfallen bei neuem Ziel, neuem Scope, Plan-/Analyseauftrag oder Read-Only-Kontext.
- Vor der ersten Arbeit pruefen, ob der Repository-Root `frigate-face-bridge/`, `AGENTS.md` und `repository.yaml` enthaelt; bei falschem Root stoppen und melden.

## Arbeitsregeln

- System- und Developer-Anweisungen haben Vorrang vor dieser Datei.
- Aendere nur dieses Repository, sofern der Nutzer nichts anderes explizit freigibt.
- Das fruehere InfluxBro-Projekt dient nur als Struktur- und Stilvorlage. Inhalte nicht blind kopieren.
- Keine Secrets, Tokens, Passwoerter oder vollstaendige RTSP-URLs mit Credentials committen.
- Add-on muss ohne Kamera und ohne MQTT starten koennen.
- `demo_mode: true` darf beim ersten Installieren der sichere Standard sein. Bei Updates darf ein bestehender Nutzerwert fuer `demo_mode` niemals automatisch ueberschrieben werden.
- Jede freigegebene Aenderung benoetigt eine Versionsanpassung in `frigate-face-bridge/config.yaml` und einen Changelog-Eintrag, sofern der Nutzer nichts anderes explizit sagt.
- Vor Aenderungen ein GitHub-Issue mit Ziel, Umfang und Akzeptanzkriterien erstellen und die Arbeit gegen dieses Issue abschliessen.
- Issue-Bodies muessen den Abschnitt `## Urspruengliche Nutzeranweisung` enthalten; relevante Nutzeranweisungen dort moeglichst wortgetreu, chronologisch und in Originalsprache erfassen. Sensible Daten vorher maskieren.
- Ein aktives Issue bleibt Arbeitskontext, bis Umsetzung, Pruefung, Version/Changelog, Commit, Push und Issue-Abschluss erledigt sind. Nicht auf andere Issues umschalten, solange das aktive Issue offen ist.
- Bei nicht-trivialen Aufgaben eine ToDo-Liste fuehren; genau ein Eintrag ist `in_progress`.
- Nach freigegebenen Aenderungen gehoeren Versionsanpassung, Commit und Push zum Abschluss, sofern der Nutzer nichts anderes sagt.
- Vor Commit immer `git status`, `git diff` und `git log --oneline -10` pruefen; nur beabsichtigte Dateien stagen.
- Nach Push bei Versionsaenderung Home Assistant Update/Restart versuchen und Live-Version verifizieren, soweit Zugriff vorhanden ist. Wenn Zugriff fehlt oder der Updatepfad scheitert, den offenen Rest klar melden.
- `OC-AGENTS.md` ist keine aktive Regelquelle fuer dieses Repository. Falls Inhalte daraus benoetigt werden, werden sie nach `AGENTS.md` ueberfuehrt; ansonsten wird die Datei entfernt.

## Umsetzung

- Aenderungen minimal halten und bestehende Repository-Muster beibehalten.
- Dateiinhalte vor Aenderungen neu lesen; nicht auf alte Annahmen verlassen.
- Wenn `apply_patch` fehlschlaegt: betroffene Datei neu lesen, Zielstelle neu bestimmen und mit robusteren Ankern erneut patchen.
- Identische fehlgeschlagene Befehle nicht mehrfach blind wiederholen; zuerst Fehlerausgabe oder Logs auswerten und Ursache klassifizieren.
- Schreiboperationen strikt sequenziell ausfuehren. Unabhaengige Lese-/Suchoperationen duerfen parallel laufen.
- Keine neuen Abhaengigkeiten ohne klare Begruendung. Werden Abhaengigkeiten geaendert, passende Abhaengigkeitsdateien im selben Auftrag aktualisieren.
- Bei Scope-Erweiterungen waehrend aktiver Arbeit den neuen Punkt als Folgepunkt aufnehmen; nur explizite Abbruchsignale wie `abbrechen`, `stop`, `halt`, `lass das`, `nicht weiter damit`, `stattdessen mache jetzt X` oder `verwirf den aktuellen Ablauf` unterbrechen den Auftrag.

## Pflichtpruefungen

- `python -m py_compile frigate-face-bridge/app/*.py`
- `pytest` fuer vorhandene Tests
- Bei Docker-/Runtime-Aenderungen Docker-Builds, Docker-Compose-/Stack-Konfigurationen und Container-Neustarts pruefen. Falls erforderlich Docker-Builds patchen, neu bauen und betroffene Container, Docker-Compose-Services, Portainer-Stacks oder Home-Assistant-Add-ons neu starten.
- Wenn eine Aenderung erst nach Neustart wirksam wird, den betroffenen Docker-Container, Stack oder das Add-on neu starten, soweit Zugriff vorhanden ist. Falls Zugriff fehlt, offenen Neustart klar melden.
- Nach Docker-/Runtime-Neustarts Runtime-Status, Logs und relevante Health-/API-Endpunkte verifizieren. Port-Listening allein reicht nicht; ein Dienst gilt erst als bereit, wenn ein Health-/API-Endpunkt erfolgreich und mit gueltigem JSON antwortet.
- Bei Aenderungen an `frigate-face-bridge/app/static/index.html` explizit HTML-Struktur pruefen: Tag-Balance, korrekte Verschachtelung, Tabellen und Section-Grenzen.
- Bei UI-Entfernungen HTML, JS, CSS, API-Aufrufe, Backend-Routen und Doku auf Abhaengigkeiten pruefen; UI-Elemente nicht ohne Ersatz-/Migrationspfad oder klare Begruendung entfernen.
- Sicherheitspruefung auf Secrets, Log-Leaks, unsichere Eingaben, offene Ports und Container-Rechte
- Bei fehlgeschlagener Pflichtpruefung Arbeit nicht als abgeschlossen melden; Fehler beheben oder blockierenden Rest klar benennen.

## Tool-Hinweise

- Bei `rtk git diff` Pfadtrenner doppelt uebergeben: `rtk git diff -- -- <pfade>`. Das erste `--` wird von RTK verbraucht, das zweite erreicht Git.

## Sicherheit

- MQTT-Passwoerter maskieren.
- RTSP- und Snapshot-URLs vor Logging/API-Ausgabe maskieren.
- Keine Shell-Aufrufe mit nutzerkontrollierten Werten ohne strikte Validierung.
- Keine Dateizugriffe ausserhalb der Add-on-Konfigurations-/Datenpfade einfuehren.
- Externe Eingaben immer als nicht vertrauenswuerdig behandeln: Query-Parameter, JSON-Bodies, Formularfelder, HA-Optionswerte, URLs, Hosts, IDs, Umgebungsvariablen und Tokens.
- Flask-Routen sind Vertrauensgrenzen: Eingaben validieren/normalisieren und klare Fehler ohne Secret-Leaks zurueckgeben.
- API-/JSON-Payloads an Grenzen validieren und normalisieren.
- Frontend-Aenderungen auf XSS/DOM-Injection pruefen; nutzerkontrollierte Werte nicht unsicher in HTML schreiben.
- Nutzerkontrollierte URLs/Hosts auf SSRF-Risiken pruefen.
- Schreib-/Loeschaktionen auf CSRF-relevante Risiken pruefen.
- Fehlermeldungen duerfen keine Secrets, internen URLs mit Credentials oder unnoetigen Systemdetails leaken.
- Add-on-Rechte nach Least Privilege pruefen: `host_network`, `privileged`, `full_access`, `homeassistant_api`, `ingress`, `ports`, Mounts und Geraetezugriffe.

## Code-Stil

- Python-Imports gruppieren: Standardbibliothek, Drittanbieter, lokale Imports. Ein Import pro Zeile; unbenutzte Imports vermeiden.
- Neue oder geaenderte Python-Funktionen mit Type-Hints versehen, wo sinnvoll.
- Fuer JSON-aehnliche Payloads `dict[str, Any]` verwenden, wenn es zur bestehenden Python-Version passt.
- Keine breiten `except Exception` in reinen Hilfsfunktionen; an HTTP-, Thread- oder Integrationsgrenzen nur bewusst und mit nuetzlicher Fehlermeldung.
- Funktionalen serverseitigen Zustand von reinem UI-/Layout-Zustand trennen. Browser-lokaler UI-Zustand darf funktionale Add-on-Konfiguration nicht ueberschreiben.

## Kontext und Ausgabe

- Nie alle Dateien gleichzeitig laden; grosse Analysen in kleinen Stapeln durchfuehren.
- Vollstaendige Dateiinhalte, grosse Diffs, Testlogs und Tool-Rohdaten nur auf explizite Anforderung ausgeben oder wenn sie fuer Fehler, Sicherheitsbefunde oder Entscheidungen noetig sind.
- Abschlussberichte kompakt halten: Issue, Version, Commit/Push, QA, Sicherheit und offene Restpunkte.
