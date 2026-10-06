#!/usr/bin/env bash
# Alle Pruefungen, die vor einem Commit laufen muessen -- in einem Aufruf.
#
# Vorgabe: /Users/thomasschatz/git/global/global-project-rules.md ("Lokale Pruefskripte").
# Die Reihenfolge folgt der Laufzeit: Was in Sekunden scheitert, soll nicht erst nach Minuten
# auffallen. Fehlt ein Werkzeug, bricht das Skript ab und nennt den Einrichtungsbefehl -- ein
# uebersprungener Linter meldet gruen, ohne stattgefunden zu haben.
#
# Das Skript installiert nichts. Einmalig einrichten:
#   python3 -m venv .venv
#   .venv/bin/pip install -r frigate-face-bridge/requirements.txt -r requirements-dev.txt
#   npm install
#   brew install shellcheck gitleaks
# Es startet weder einen Stack noch ein Add-on und veroeffentlicht kein Release.
set -euo pipefail
cd "$(dirname "$0")/.."

blau=$'\033[1;34m'; gruen=$'\033[1;32m'; rot=$'\033[1;31m'; aus=$'\033[0m'
schritt() { printf '%s[%s]%s %s\n' "$blau" "$(date +%H:%M:%S)" "$aus" "$1"; }
gut()     { printf '%s  ok%s %s\n' "$gruen" "$aus" "$1"; }
ende()    { printf '%s  FEHLER %s%s\n' "$rot" "$1" "$aus"; exit 1; }

VENV_HILFE="python3 -m venv .venv && .venv/bin/pip install -r frigate-face-bridge/requirements.txt -r requirements-dev.txt"
# Python-Werkzeuge kommen aus der projekteigenen .venv, damit Kommandozeile und Pruefskript
# dieselben Fassungen benutzen. Eine systemweite Installation scheitert unter Homebrew-Python
# ohnehin an PEP 668.
[[ -x .venv/bin/python ]] || ende ".venv fehlt. Einrichten mit: $VENV_HILFE"
PATH="$PWD/.venv/bin:$PATH"
export PATH

schritt "Fassung"
[[ -s VERSION ]] || ende "Datei VERSION fehlt (Schema YYYY.MM.NNN, siehe global-project-rules.md)"
FASSUNG="$(tr -d '[:space:]' <VERSION)"
[[ "$FASSUNG" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{3}$ ]] \
  || ende "VERSION '$FASSUNG' folgt nicht dem Schema YYYY.MM.NNN"
grep -qx "version: \"$FASSUNG\"" frigate-face-bridge/config.yaml \
  || ende "frigate-face-bridge/config.yaml traegt nicht die Fassung $FASSUNG"
gut "$FASSUNG (Add-on-Metadaten gleich)"

schritt "Ruff (Python)"
command -v ruff >/dev/null || ende "Ruff fehlt. Einrichten mit: $VENV_HILFE"
ruff check .
# Den Zeilenumbruch fuehrt der Formatierer; ein Abweichen davon ist ein Befund wie jeder andere.
ruff format --check .
gut "keine Befunde, Formatierung einheitlich"

schritt "ShellCheck (Shell)"
command -v shellcheck >/dev/null \
  || ende "ShellCheck fehlt. Einrichten mit: brew install shellcheck"
shellcheck -x -S style scripts/*.sh frigate-face-bridge/run.sh
gut "keine Befunde"

schritt "Biome (JavaScript, CSS)"
command -v node >/dev/null || ende "Node fehlt. Einrichten mit: brew install node"
[[ -x node_modules/.bin/biome ]] || ende "Biome fehlt. Einrichten mit: npm install"
node_modules/.bin/biome check --error-on-warnings .
gut "keine Befunde"

schritt "yamllint (YAML)"
# Nur wenn es YAML gibt. Existiert welches, ist das Werkzeug Pflicht: eine kaputte
# compose- oder Konfigurationsdatei fiele sonst erst beim Ausrollen auf.
# Kein mapfile: macOS liefert bash 3.2, dort gibt es das nicht.
YAML_LISTE=$(find . \( -path ./.git -o -path ./.venv -o -path ./node_modules \) -prune -o \
  \( -name '*.yml' -o -name '*.yaml' \) -print)
if [[ -n "$YAML_LISTE" ]]; then
  command -v yamllint >/dev/null \
    || ende "yamllint fehlt, aber das Repository enthaelt YAML. Einrichten mit: $VENV_HILFE"
  # Die Regeln stehen in .yamllint im Projektroot, damit Kommandozeile und Pruefskript
  # dasselbe pruefen. docs/functions.yaml ist dort ausgenommen: die Datei ist absichtlich
  # JSON-kompatibles YAML und wird vom Funktionskatalog-Schritt geprueft.
  printf '%s\n' "$YAML_LISTE" | tr '\n' '\0' | xargs -0 yamllint
  gut "$(printf '%s\n' "$YAML_LISTE" | wc -l | tr -d ' ') Datei(en) ohne Befund"
else
  gut "kein YAML vorhanden"
fi

schritt "gitleaks (Secrets)"
# Ein Klartext-Secret im Commit ist der eine Fehler, der sich nicht zurueckholen
# laesst: er ist ab dem Push kompromittiert, egal was danach passiert. --redact
# haelt gefundene Werte aus Ausgabe und Protokoll.
command -v gitleaks >/dev/null \
  || ende "gitleaks fehlt. Einrichten mit: brew install gitleaks"
gitleaks dir . --no-banner --redact --config .gitleaks.toml
gut "keine Klartext-Secrets im Arbeitsbaum"

schritt "Oberflaeche laedt fehlerfrei"
# Eine Syntaxpruefung sagt nur, dass app.js lesbar ist -- nicht, dass die Seite laeuft.
# Dieser Schritt fuehrt das gesamte Skript unter einem DOM-Ersatz aus, gespeist mit echten
# API-Antworten der App (siehe scripts/oberflaeche_daten.py).
ANTWORTEN="$(mktemp)"
trap 'rm -f "$ANTWORTEN"' EXIT
python scripts/oberflaeche_daten.py >"$ANTWORTEN" 2>/dev/null \
  || ende "API-Antworten fuer die Oberflaechen-Pruefung liessen sich nicht erzeugen"
node scripts/pruefung-oberflaeche.mjs "$ANTWORTEN"
gut "laeuft durch"

schritt "Tests (pytest)"
python -m pytest -q
gut "bestanden"

schritt "Funktionskatalog"
python scripts/validate_function_docs.py
gut "Katalog und Handbuch passen zum Quelltext"

printf '\n%s  Alle Pruefungen bestanden -- Fassung %s%s\n' "$gruen" "$FASSUNG" "$aus"
