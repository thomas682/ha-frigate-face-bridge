# Template: Parameter- und UI-Aenderungen

Dieses Template dient Agenten als Vorgehensweise, wenn Parameter, Add-on-Konfiguration oder Bedienoberflaechen geaendert werden.

## Grundregel

- Gespeicherte Nutzerwerte sind die Wahrheit.
- Ein Start, Neustart oder Update darf gespeicherte Werte nicht automatisch ueberschreiben, normalisieren, kuerzen oder durch Defaults ersetzen.
- Defaults duerfen nur als Erstinstallationsvorschlag in `config.yaml` oder als Runtime-Fallback im Speicher verwendet werden.
- Runtime-Fallbacks duerfen nicht automatisch in `/data/options.json` geschrieben werden.
- Maskierte Secrets oder maskierte URLs duerfen niemals als echte Werte gespeichert werden.

## Vor Aenderungen

- Aktuelles Issue mit Ziel, Umfang, Akzeptanzkriterien und `## Urspruengliche Nutzeranweisung` erstellen.
- Betroffene Dateien neu lesen, nicht auf alte Annahmen verlassen.
- Pruefen, ob ein Wert aus `config.yaml`, `/data/options.json`, Registry-Dateien oder UI-Formularen stammt.
- Klaeren, ob ein Feld ein Secret, eine URL mit Credentials oder ein sicherheitsrelevanter Wert ist.

## Parameterverwaltung

- `config.yaml`: Schema und Erstinstallationsvorschlag.
- `/data/options.json`: gespeicherte Nutzerwerte, nur durch explizites Speichern veraendern.
- Runtime-Konfiguration: gemergte, validierte Arbeitskonfiguration im Speicher.
- API sollte `config` fuer Runtime-Werte und `raw_config` fuer gespeicherte Werte liefern.
- UI muss gespeicherte Rohwerte anzeigen, sofern vorhanden, und fehlende Werte als `nicht gesetzt` kennzeichnen.
- UI darf beim Speichern nur geaenderte Felder senden oder muss serverseitig maskierte/leere Platzhalter sicher ignorieren.

## UI-Regeln

- Keine leeren Passwort-/URL-Felder so darstellen, dass Nutzer glauben, der Wert sei verschwunden.
- Fuer Secrets und Kamera-URLs einen Status anzeigen: `gesetzt` oder `nicht gesetzt`.
- Testbuttons muessen erklaeren, was getestet wird, und duerfen keine Secrets ausgeben.
- Eingaben und API-Daten nur mit `textContent` oder gleichwertig sicheren Methoden darstellen.
- Tabellen fuer mobile Geraete scrollbar machen und Bedienelemente gross genug fuer iPhone-Nutzung halten.

## Neue Optionen

- Neue Option in `config.yaml` und Schema ergaenzen.
- Runtime-Fallback ergaenzen, falls die Option fehlt.
- Keine automatische Migration schreiben, die bestehende Nutzerwerte ersetzt.
- Web-UI nur so erweitern, dass fehlende Werte nicht beim naechsten Speichern als Default persistiert werden.
- Tests fuer fehlende, bestehende und explizit geaenderte Werte ergaenzen.

## Abschluss

- Version und Changelog aktualisieren.
- Pflichtpruefungen ausfuehren.
- Sicherheitspruefung auf Secrets, Log-Leaks, XSS, SSRF und offene Ports durchfuehren.
- Vor Commit `git status`, `git diff` und `git log --oneline -10` pruefen.
- Nach Push Add-on-Update/Restart und Live-Status verifizieren, soweit Zugriff vorhanden ist.
