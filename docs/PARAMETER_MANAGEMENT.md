# Parameterverwaltung ohne Update-Ueberschreibung

Diese Regel gilt fuer Face Bridge und kann fuer neue Parameter wiederverwendet werden.

## Grundsatz

Gespeicherte Nutzerwerte sind die Wahrheit. Werte aus `/data/options.json` duerfen bei Start, Neustart oder Update nicht automatisch durch Defaults, Fallbacks, Migrationen oder Normalisierung ueberschrieben werden.

## Ebenen

- `config.yaml`: Schema und Erstinstallationsvorschlag fuer Home Assistant.
- `/data/options.json`: gespeicherte Nutzerwerte. Diese Datei wird nur bei explizitem Speichern geaendert.
- Runtime-Konfiguration: nur im Speicher berechnete Werte, mit denen die App sicher laufen kann.

## Regeln

- Existiert ein Wert in `/data/options.json`, bleibt der gespeicherte Wert unveraendert.
- Fehlende Werte werden nicht automatisch in `/data/options.json` eingetragen.
- Neue Optionen duerfen ueber `config.yaml` und Runtime-Fallbacks eingefuehrt werden.
- Runtime-Fallbacks duerfen intern verwendet werden, werden aber nicht automatisch persistiert.
- Validierung darf Warnungen erzeugen, aber gespeicherte Werte nicht still reparieren.
- Persistente Aenderungen erfolgen nur durch explizites Speichern ueber Home Assistant, Web-UI oder API.
- Maskierte Secrets oder URLs mit `***` duerfen beim Speichern vorhandene echte Werte nicht ersetzen.

## Neue Parameter

Beim Hinzufuegen eines Parameters:

1. Parameter im Schema bzw. in `config.yaml` aufnehmen.
2. Einen sicheren Runtime-Fallback definieren.
3. Sicherstellen, dass fehlende Werte nicht automatisch gespeichert werden.
4. Tests ergaenzen: fehlend, vorhandener Wert, ungueltiger Wert, explizites Speichern.
5. UI klar zwischen gespeichertem Rohwert und Runtime-Wert unterscheiden, wenn relevant.

## Beispiel

Gespeichert:

```json
{
  "mqtt": {
    "topic_prefix": "/ha/frigate_face_bridge/"
  }
}
```

Runtime:

```json
{
  "mqtt": {
    "topic_prefix": "ha/frigate_face_bridge"
  }
}
```

Der gespeicherte Wert bleibt exakt erhalten. Nur die Runtime nutzt den bereinigten Wert.

## Demo-Modus

- Neu oder fehlend: Runtime verwendet `demo_mode: false`.
- Gespeichert `demo_mode: true`: bleibt true.
- Gespeichert `demo_mode: false`: bleibt false.
- Updates duerfen `demo_mode` nicht automatisch setzen oder aendern.
