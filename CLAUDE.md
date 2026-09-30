# CLAUDE.md

Diese Datei wird von Claude Code beim Start **automatisch** gelesen. `AGENTS.md`
wird es nicht — deshalb steht der Einstieg hier und zieht die Regeln nach.

@AGENTS.md

## Die eine Regel, die vor allem anderen kommt

**Issue vor Umsetzung.** Jede umsetzbare Aufgabe aus dem Chat wird vor der
ersten Dateiaenderung als GitHub-Issue in diesem Repository erfasst, mit dem
vollstaendigen Aufgabentext unter `## Vorgaben Chat` in Originalsprache und
chronologischer Reihenfolge. Eine reine Auskunft ohne Dateiaenderung braucht
kein Issue.

Sie steht hier doppelt, weil sie greifen muss, bevor das erste Werkzeug laeuft.
Die uebrigen harten Regeln -- `VERSION` erhoehen, keine Secrets, vor dem Commit
`./scripts/run-local-checks.sh` -- stehen in `AGENTS.md`.
