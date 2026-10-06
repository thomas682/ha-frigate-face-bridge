# AGENTS.md — Frigate Face Bridge

Diese Datei ist die Regelquelle dieses Repositories. opencode liest sie direkt,
Claude Code ueber den Import in `CLAUDE.md`. Was hier steht, gilt fuer beide.

Wer welche Datei liest:

| Werkzeug | liest automatisch | zusaetzlich |
|---|---|---|
| opencode | `AGENTS.md` (Projektroot, aufwaerts traversiert) | `instructions` in `opencode.json` |
| Claude Code | `CLAUDE.md` | `@AGENTS.md` als Import darin |

`AGENTS.md` ist deshalb die vollstaendige Quelle und nicht `CLAUDE.md`: opencode
kennt kein `@`-Import in der Datei. Die Dateien der Nachschlagetabelle am Ende
werden bei Bedarf mit dem Read-Werkzeug geoeffnet.

## Harte Regeln

Diese vier gelten in jeder Sitzung, ohne Rueckfrage und ohne fachliche Ausnahme.
Sie stehen vollstaendig hier, damit sie nicht erst in einer anderen Datei
nachgelesen werden muessen.

1. **Issue vor Umsetzung.** Jede umsetzbare Aufgabe aus dem Chat wird vor der
   ersten Dateiaenderung als GitHub-Issue in diesem Repository erfasst, mit dem
   vollstaendigen Aufgabentext unter `## Vorgaben Chat` in Originalsprache und
   chronologischer Reihenfolge. Eine reine Auskunft ohne Dateiaenderung braucht
   kein Issue. Der Abschlusskommentar endet mit der ausgelieferten Version.
2. **VERSION erhoehen.** Jede Aenderung an Quellcode, Skripten,
   Laufzeitkonfiguration oder produktiver Logik erhoeht im selben Arbeitsblock
   die Datei `VERSION` nach dem Schema `YYYY.MM.NNN`. Ausnahmslos.
3. **Keine Secrets im Repository.** Keine Passwoerter, Tokens, privaten
   Schluessel, Exporte oder produktiven Konfigurationen committen. Benoetigte
   Werte kommen ausschliesslich ueber den freigegebenen Reader
   `/Users/thomasschatz/git/global/scripts/secrets-get.sh`, der keinen Modus
   hat, der etwas auf die Ausgabe schreibt. Beim Beschreiben von Ablaeufen nur
   die Art des Secrets nennen, nie den Wert.
4. **Vor jedem Commit pruefen.** `./scripts/run-local-checks.sh` ausfuehren und
   gruen sehen. Ein fehlendes Werkzeug ist ein Abbruch, kein uebersprungener
   Schritt.

## Projekt

- Name: Frigate Face Bridge
- Zweck: Lokale Bruecke fuer UniFi-Kameras, Personen-/Hund-Erkennung,
  vorbereitete Gesichtserkennung und MQTT-Ausgabe an Home Assistant.
- Repository: https://github.com/thomas682/ha-frigate-face-bridge (auf GitHub
  als `ha-frigate-face-bridge` benannt; das lokale Verzeichnis heisst `facebri`,
  README und Regeldateien verwenden weiterhin den Projektnamen
  "Frigate Face Bridge")
- Root: `/Users/thomasschatz/git/facebri`
- Repository-Typ: Home Assistant Add-on
- Status: siehe `VERSION` und `README.md`
- Verantwortlich: Thomas Schatz
- Sprache fuer Nutzerkommunikation: Deutsch, sofern der Nutzer nichts anderes verlangt.

## Befehle

```sh
# einmalig einrichten
python3 -m venv .venv
.venv/bin/pip install -r frigate-face-bridge/requirements.txt -r requirements-dev.txt
npm install
brew install shellcheck gitleaks

# vor jedem Commit
./scripts/run-local-checks.sh

# nach Quellaenderungen: Funktionskatalog und Handbuch neu erzeugen
.venv/bin/python scripts/build_function_docs.py
```

- `scripts/run-local-checks.sh` ist der verbindliche Ort fuer die Frage, was
  "geprueft" bedeutet: Ruff (Lint und Format), ShellCheck, Biome, yamllint,
  gitleaks, Oberflaechen-Pruefung unter DOM-Ersatz, pytest und
  Funktionskatalog, nach Laufzeit sortiert. Es installiert nichts, startet
  weder einen Stack noch veroeffentlicht ein Release.
- Reine Dokumentations- oder Regelaenderungen brauchen mindestens
  Plausibilitaetspruefung, Diff-Review und Secret-Check.
- Eine nicht moegliche oder nicht sinnvolle Pruefung im Abschluss benennen und
  begruenden, statt sie stillschweigend zu lassen.
- Bei Docker-/Runtime-Aenderungen zusaetzlich Docker-Builds,
  Docker-Compose-/Stack-Konfigurationen und Container-Neustarts pruefen.

## Struktur

- `AGENTS.md`: diese Datei, von opencode direkt gelesen.
- `CLAUDE.md`: Startpunkt fuer Claude Code, importiert diese Datei.
- `opencode.json`: laedt fuer opencode `global-secrets-rules.md` zusaetzlich zu
  dieser Datei.
- `VERSION`: kanonische Runtime- und UI-Version; das Add-on-Metadatenfeld wird
  auf denselben Wert geprueft.
- `repository.yaml`: Home-Assistant-Add-on-Repository-Deklaration.
- `frigate-face-bridge/`: Add-on-Quellcode (`app/`, `Dockerfile`, `config.yaml`,
  `run.sh`, `translations/`, `DOCS.md`, `CHANGELOG.md`).
- `docs/functions.yaml`, `docs/function-id-baseline.json`: Funktionskatalog und
  Review-Baseline.
- `docs/handbuch.md`, `docs/local-checks.md`,
  `docs/projekt-parameter-management.md`: Handbuch, lokale Pruefungen,
  Parameterverwaltungsregel.
- `docs/templates/AGENT_PARAMETER_UI_CHANGE_TEMPLATE.md`: Vorlage fuer sichere
  Parameter- und UI-Aenderungen.
- `docs/rules/global-rule-baseline.json`: zuletzt gepruefter globaler Regelstand.
- `deploy/`: Compose-Vorlage und Homepage-Eintrag fuer den Betrieb ausserhalb
  von Home Assistant.
- `scripts/run-local-checks.sh`, `scripts/build_function_docs.py`,
  `scripts/validate_function_docs.py`.
- `tests/test_api.py`, `tests/test_function_docs_validator.py`.
- `ROADMAP.md`: weitere Ausbaustufen.
- `pyproject.toml`, `requirements-dev.txt`: Ruff- und pytest-Konfiguration,
  Entwicklungswerkzeuge fuer die `.venv`.
- `package.json`, `biome.jsonc`: Biome fuer `app.js`, `style.css` und `.mjs`.
- `.yamllint`, `.gitleaks.toml`: Regeln fuer die YAML- und die Secret-Pruefung,
  damit Kommandozeile und Pruefskript dasselbe pruefen.
- `scripts/pruefung-oberflaeche.mjs`, `scripts/oberflaeche_daten.py`:
  Oberflaechen-Pruefung, die `app.js` mit echten API-Antworten unter einem
  DOM-Ersatz ausfuehrt.

## Projektregeln

Diese Regeln sind aus der Arbeit an diesem Projekt entstanden und gelten
weiterhin. Sie ergaenzen oder verschaerfen die globalen Regeln, duerfen sie
aber nicht abschwaechen.

- **Root-Erkennung vor jeder Arbeit.** Pruefen, ob der Repository-Root
  `frigate-face-bridge/`, `AGENTS.md` und `repository.yaml` enthaelt; bei
  falschem Root stoppen und melden.
- **InfluxBro ist nur Stilvorlage.** Das fruehere InfluxBro-Projekt dient nur
  als Struktur- und Stilvorlage. Inhalte nicht blind kopieren.
- **Secret-Zugriff.** Projektbezogene Secret-Hinweise stehen lokal in
  `secrets.md` (gitignored). Die echten Werte liegen zentral verschluesselt in
  `/Users/thomasschatz/git/global/secrets/globalsecrets.enc.yaml` und werden
  ausschliesslich ueber `/Users/thomasschatz/git/global/scripts/secrets-get.sh`
  gelesen. Vor Zugriffen auf Frigate, MQTT, Home Assistant, UniFi/RTSP, NAS,
  Proxmox, Portainer, Docker/Stack oder externe Face-Recognition-Dienste dort
  nachsehen und keine Werte in Chat, Issues, Logs oder Commits kopieren.
- **Start ohne Kamera und ohne MQTT.** Das Add-on muss ohne Kamera und ohne
  MQTT starten koennen.
- **Bestehende Nutzerwerte sind unantastbar.** `demo_mode` darf nicht
  automatisch aktiviert werden. Bestehende Nutzerwerte fuer `demo_mode` und
  andere Parameter duerfen bei Start, Neustart oder Update niemals automatisch
  ueberschrieben, normalisiert oder als Defaults persistiert werden.
- **Parameterverwaltung.** Die Parameterverwaltungsregel in
  `docs/projekt-parameter-management.md` ist fuer neue Optionen und
  Config-Migrationen zu beachten.
- **Versionsspiegel und Changelog.** Jede Aenderung an Quellcode, Skripten,
  Laufzeitkonfiguration oder produktiver Logik benoetigt zusaetzlich zur
  Root-`VERSION` die projektspezifischen Versionsspiegel und einen
  Changelog-Eintrag in `frigate-face-bridge/CHANGELOG.md`.
- **Issue mit Ziel, Umfang und Akzeptanzkriterien.** Vor jeder umsetzbaren
  Chat-Aufgabe ein GitHub-Issue mit dem vollstaendigen Aufgabentext unter
  `## Vorgaben Chat`, Ziel, Umfang und Akzeptanzkriterien erstellen und die
  Arbeit gegen dieses Issue abschliessen.
- **Ein aktives Issue bleibt Arbeitskontext**, bis Umsetzung, Pruefung,
  Version/Changelog, Commit, Push und Issue-Abschluss erledigt sind. Nicht auf
  andere Issues umschalten, solange das aktive Issue offen ist.
- **Nach Push: Home Assistant verifizieren.** Nach Push bei Versionsaenderung
  Home Assistant Update/Restart versuchen und Live-Version verifizieren, soweit
  Zugriff vorhanden ist. Wenn Zugriff fehlt oder der Updatepfad scheitert, den
  offenen Rest klar melden.

## Pflichtpruefungen

- Bei Docker-/Runtime-Aenderungen Docker-Builds, Docker-Compose-/Stack-
  Konfigurationen und Container-Neustarts pruefen. Falls erforderlich
  Docker-Builds patchen, neu bauen und betroffene Container,
  Docker-Compose-Services, Portainer-Stacks oder Home-Assistant-Add-ons neu
  starten.
- Wenn eine Aenderung erst nach Neustart wirksam wird, den betroffenen
  Docker-Container, Stack oder das Add-on neu starten, soweit Zugriff
  vorhanden ist. Falls Zugriff fehlt, offenen Neustart klar melden.
- Nach Docker-/Runtime-Neustarts Runtime-Status, Logs und relevante
  Health-/API-Endpunkte verifizieren. Port-Listening allein reicht nicht; ein
  Dienst gilt erst als bereit, wenn ein Health-/API-Endpunkt erfolgreich und
  mit gueltigem JSON antwortet.
- Bei Aenderungen an `frigate-face-bridge/app/static/index.html` explizit
  HTML-Struktur pruefen: Tag-Balance, korrekte Verschachtelung, Tabellen und
  Section-Grenzen.
- Bei UI-Entfernungen HTML, JS, CSS, API-Aufrufe, Backend-Routen und Doku auf
  Abhaengigkeiten pruefen; UI-Elemente nicht ohne Ersatz-/Migrationspfad oder
  klare Begruendung entfernen.
- Sicherheitspruefung auf Secrets, Log-Leaks, unsichere Eingaben, offene Ports
  und Container-Rechte.
- Bei fehlgeschlagener Pflichtpruefung Arbeit nicht als abgeschlossen melden;
  Fehler beheben oder blockierenden Rest klar benennen.

## Sicherheit und Datenschutz

Diese Regeln sind aus konkreten Vorfaellen entstanden und besonders
schuetzenswert; sie werden nicht abgeschwaecht.

- MQTT-Passwoerter maskieren.
- RTSP- und Snapshot-URLs vor Logging/API-Ausgabe maskieren.
- Keine Dateizugriffe ausserhalb der Add-on-Konfigurations-/Datenpfade
  einfuehren.
- Flask-Routen sind Vertrauensgrenzen: Eingaben validieren/normalisieren und
  klare Fehler ohne Secret-Leaks zurueckgeben.
- Add-on-Rechte nach Least Privilege pruefen: `host_network`, `privileged`,
  `full_access`, `homeassistant_api`, `ingress`, `ports`, Mounts und
  Geraetezugriffe.

## Code-Stil

- Python-Imports gruppieren: Standardbibliothek, Drittanbieter, lokale
  Imports. Ein Import pro Zeile; unbenutzte Imports vermeiden.
- Neue oder geaenderte Python-Funktionen mit Type-Hints versehen, wo sinnvoll.
- Fuer JSON-aehnliche Payloads `dict[str, Any]` verwenden, wenn es zur
  bestehenden Python-Version passt.
- Keine breiten `except Exception` in reinen Hilfsfunktionen; an HTTP-,
  Thread- oder Integrationsgrenzen nur bewusst und mit nuetzlicher
  Fehlermeldung.
- Funktionalen serverseitigen Zustand von reinem UI-/Layout-Zustand trennen.
  Browser-lokaler UI-Zustand darf funktionale Add-on-Konfiguration nicht
  ueberschreiben.

## Arbeitsweise

- Vor einer Aenderung die betroffenen Dateien frisch lesen; Index- und
  Memory-Daten sind Orientierung, keine aktuelle Dateiquelle.
- Kleine, nachvollziehbare Aenderungen. Bestehende Muster und Namen beibehalten.
- Keine unangeforderten Umbauten, Formatierungen oder Umbenennungen. Fremde
  lokale Aenderungen nicht zuruecksetzen und nicht mitcommitten.
- Bei `rtk git diff` Pfadtrenner doppelt uebergeben: `rtk git diff -- --
  <pfade>`. Das erste `--` wird von RTK verbraucht, das zweite erreicht Git.
- Neue oder geaenderte Funktionen, Eingaben und GUI-Elemente im selben
  Arbeitsblock in `docs/functions.yaml` und `docs/handbuch.md` nachziehen.
- `.github/workflows/` bleibt leer: Remote-CI ist ohne ausdrueckliche
  Nutzerfreigabe untersagt, Pruefungen laufen lokal.

## Globale Regeln nachschlagen

Die verbindlichen projektuebergreifenden Regeln liegen unter
`/Users/thomasschatz/git/global/`. Die vier harten Regeln oben sind daraus
bereits hier vollstaendig wiedergegeben. Die uebrigen Dateien werden gelesen,
wenn die Aufgabe das jeweilige Thema beruehrt -- nicht vorsorglich alle:

| Thema der Aufgabe | Datei |
|---|---|
| Arbeitsweise, Scope, Abschluss, Git-Hygiene | `global-workflow-rules.md` |
| Grundregeln fuer Agenten, Freigaben, Prioritaet | `global-agents.md` |
| Version, Linter je Sprache, Pruefskripte, lokale Workflows | `global-project-rules.md` |
| Secrets, Maskierung, Vorfaelle | `global-secrets-rules.md` |
| Security-Baseline, destruktive Aktionen | `global-security-rules.md` |
| Funktionskatalog, Handbuch, Kurzbeschreibungen | `global-documentation-rules.md` |
| Installation, Setup-Scripts, Distribution, Releases | `global-installation-rules.md` |
| Web- und GUI-Verhalten, Ladezustaende, Sichtposition | `global-gui-rules.md` |
| MCP- und Werkzeugnutzung | `global-mcp-rules.md` |
| Logs und Protokolle | `global-log-rules.md` |
| Docker, Registry, Portainer, Deployment | `global-registry-workflow.md` |
| `homepage.localdomain`-Eintrag | `global-homepage-rules.md` |
| DNS, Netzwerk, UDM | `global-dns-rules.md`, `global-udm-rules.md` |

Der zuletzt gepruefte Stand steht in `docs/rules/global-rule-baseline.json`.
Vor nicht-trivialen Arbeiten den Drift-Status pruefen:

```sh
python3 /Users/thomasschatz/git/global/scripts/check-global-rule-drift.py /Users/thomasschatz/git/facebri
```

Meldet der Check Drift oder fehlt der Marker, zuerst einen Global-Rule-Audit
anbieten; die Baseline erst nach abgeschlossenem Audit mit `--write-baseline`
erneuern.

## Abschluss

Eine Aufgabe ist erst fertig, wenn Umsetzung, Pruefung, Version/Changelog,
Funktionskatalog und Handbuch synchron, Commit, Push und Issue-Abschluss
erledigt sind, oder ein blockierender Rest konkret benannt ist. Der
Abschlussbericht bleibt kompakt: Issue, Version, Commit/Push, QA, Sicherheit
und offene Restpunkte; Pruefungen, die nur der Nutzer an seiner Hardware
ausfuehren kann, stehen dort unter `Offene Benutzerpruefungen`.
