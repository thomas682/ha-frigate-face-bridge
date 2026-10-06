# Lokale Pruefungen

Alle Pruefungen vor Commit und Push laufen ueber einen Aufruf:

```sh
./scripts/run-local-checks.sh
```

Einmalig einrichten (das Skript selbst installiert nichts):

```sh
python3 -m venv .venv
.venv/bin/pip install -r frigate-face-bridge/requirements.txt -r requirements-dev.txt
npm install
brew install shellcheck gitleaks
```

Reihenfolge nach Laufzeit:

| Schritt | Werkzeug | Konfiguration |
|---|---|---|
| Fassung | `VERSION` gegen `frigate-face-bridge/config.yaml` | - |
| Python | Ruff (`check` und `format --check`) | `pyproject.toml` |
| Shell | ShellCheck | - |
| JavaScript, CSS | Biome | `biome.jsonc` |
| YAML | yamllint | `.yamllint` |
| Secrets | gitleaks | `.gitleaks.toml` |
| Oberflaeche | `scripts/pruefung-oberflaeche.mjs` mit echten API-Antworten aus `scripts/oberflaeche_daten.py` | - |
| Tests | pytest | `pyproject.toml` |
| Funktionskatalog | `scripts/validate_function_docs.py` | `docs/functions.yaml` |

Fehlt ein Werkzeug, bricht das Skript mit dem Einrichtungsbefehl ab, statt den
Schritt zu ueberspringen. Es startet weder einen Docker-Stack noch ein
Home-Assistant-Add-on und veroeffentlicht kein Release.
