# Lokale Pruefungen

Der ehemalige GitHub-Lint-Workflow wird vor Commit und Push manuell ausgefuehrt:

```sh
scripts/run-local-checks.sh
```

Der Ablauf installiert die deklarierten Python-Testabhaengigkeiten, kompiliert die
Bridge, fuehrt die Tests aus und validiert den Funktionskatalog. Er startet weder
einen Docker-Stack noch ein Home-Assistant-Add-on und veroeffentlicht kein Release.
