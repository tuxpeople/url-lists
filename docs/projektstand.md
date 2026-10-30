# Projektstand für die Weiterarbeit

Stand: 30. Oktober 2026. Technische Details und Bezugsquellen stehen in der
[README](../README.md); diese Datei hält Entscheidungen und offene Punkte fest.

## Ziel und getroffene Entscheidungen

- Domainlisten für Allow-/Blocklisting sammeln und aus offiziellen Quellen erzeugen.
- Aktuelles Zielsystem ist Pi-hole 6. Exakte Domains werden über öffentliche
  GitHub-Raw-URLs abonniert; keine Importskripte erzeugen.
- Apple, Docker Desktop, OpenShift und Microsoft 365 sind implementiert, jeweils einzeln und in
  der gemeinsamen Allowlist unter `pihole/allow-exact.txt` verfügbar.
- Wildcards bleiben separat als Regex-Regeln erhalten. Sie sind nicht über die
  normalen Pi-hole-Listenabos abgedeckt und werden dort nicht automatisch synchronisiert.
- Pi-hole-Regex-Exporte entfernen pro Liste normale Wildcards, die durch eine
  breitere normale Wildcard abgedeckt sind. Quelldaten/Metadaten bleiben vollständig;
  exakte Hosts und Microsofts Sondermuster werden nicht gekürzt. Bei späteren
  Aufteilungen die Bereinigung immer erst nach der Auswahl anwenden.
- OpenShift bleibt vorerst eine gemeinsame Liste. Eine spätere Aufteilung wird
  noch erwogen; keine Kategorien eigenständig ausschließen.
- Apple-Kategorien und Unterkategorien sowie OpenShift-Kategorien, Cloud-Anbieter
  und Bedingungen bleiben in CSV-Metadaten für spätere Aufteilungen erhalten.
- Platzhalter in OpenShift-Zielen werden dokumentiert, aber nicht exportiert.
  Pi-hole-Exporte reduzieren Ziele mit Pfaden auf den Host.
- Microsoft 365 verwendet den offiziellen Worldwide-JSON-Webservice. Die
  Dienstüberschriften, Required/Optional und Optimize/Allow/Default bleiben pro
  Endpoint-Set in der CSV erhalten; die vollständigen API-Daten inklusive IP-Netzen
  in JSON. Vorerst eine gemeinsame Liste einschließlich Optional. Zwei besondere
  Wildcard-Muster werden ausschließlich in den Regex-Export aufgenommen.

## Umsetzung und Betrieb

Die Daten fließen von `scripts/update_*.py` nach `lists/allow/*.txt` und
`metadata/*.csv`. `scripts/build_lists.py` validiert, dedupliziert und erzeugt die
versionierten Pi-hole-Exporte sowie die ignorierten allgemeinen Listen in `dist/`.
Generierte Dateien über die Skripte aktualisieren, nicht direkt bearbeiten.
Eigene Einträge gehören nach `lists/allow/custom.txt` bzw. `lists/block/custom.txt`.

Der Workflow `.github/workflows/lists.yml` läuft bei Pushes, Pull Requests,
manuell und täglich um 05:23 UTC. Nur auf dem Default-Branch veröffentlicht er
Änderungen per Bot-Commit. Pull Requests bauen offline. Der Nutzer hat den ersten
Push und einen erfolgreichen Workflow-Lauf bestätigt. Die Einrichtung der Abos
auf seinem Pi-hole wurde hier noch nicht bestätigt.

Die vier Renovate-Updates wurden geprüft: Python 3.15, checkout v7,
setup-python v7 und upload-artifact v7. Die einzelnen PR-Checks waren erfolgreich;
alle vier Versionen stehen inzwischen im lokalen Workflow. Für den aktuellen
Zustand auf GitHub bei Bedarf PRs und Actions erneut prüfen.

## Offene Punkte

- Entscheiden, ob OpenShift nach Kernfunktionen, Telemetrie, Cloud-Anbieter,
  OCI-spezifischen oder optionalen Diensten aufgeteilt werden soll.
- Bei Bedarf Apple nach den erhaltenen Kategorien aufteilen.
- Konkrete cluster-/regionsabhängige OpenShift-Ziele nur mit Angaben zur eigenen
  Umgebung erzeugen. Die globale Liste ersetzt diese Konfiguration nicht.
- Die Regex-Synchronisation ist implementiert und mit simulierten Docker-Antworten
  getestet. Der Nutzer hat den ersten echten Allow-Lauf auf `core1` bestätigt:
  87 Regeln hinzugefügt, keine gelöscht, die manuelle Regel für `tdeutsch.ch`
  mit Kommentar `Test` erhalten. Die abschließende API-Prüfung meldete
  `Synchronization verified successfully.` Wiederholung ohne Änderungen und
  echte Löschungen bzw. Deny-Synchronisation sind damit noch nicht auf dem
  Zielsystem bestätigt.
- `scripts/regex_import.sh` verwendet inzwischen den Live-Istzustand über
  `docker exec CONTAINER pihole api domains/allow/regex` bzw. `domains/deny/regex`,
  ohne `-i`/`-t`. Host-Abhängigkeiten: Bash, curl, Docker, jq. Standardquellen:
  gemeinsame Allow- bzw. Block-Regex-Liste. Auswahl über
  wiederholtes `--url`; Container und Regeltyp über `--container`/`--type`.
  Nur Regeln mit exakt passender Kommentar-Markierung (`managed by script`,
  konfigurierbar über `--comment`) werden als eigene Regeln behandelt. Manuelle
  Regeln und vorhandene Gruppen/Aktivierungszustände bleiben erhalten;
  deaktivierte gewünschte Regeln werden gemeldet. API-Fehler brechen den Lauf ab.
  Normaler Aufruf führt Änderungen aus; `--dry-run` liefert nur eine Vorschau.
  Ergänzungen vor Löschungen, maximal 100 Regeln je Befehl. Vor jedem Paket wird
  auf externe Änderungen geprüft, danach und abschließend das Ergebnis per API
  kontrolliert. Bei Teilerfolgen Abbruch; erneuter Lauf plant aus dem Istzustand.
  Eine lokale Verzeichnissperre verhindert parallele Synchronisationen desselben
  Containers/Regeltyps unter demselben XDG-Zustandsverzeichnis. Keine lokalen
  Vergleichsdateien; `--accept-baseline` und `--state-dir` entfallen.

## Einstieg beim nächsten Mal

```sh
git status --short
python3 -m unittest discover -s tests -v
python3 scripts/build_lists.py --offline
git diff --check
```

Für einen vollständigen Abruf alle vier `scripts/update_*.py` einzeln ausführen
und anschließend neu bauen. Microsoft-365-Abrufe nicht in kurzen Abständen wiederholen.
Danach Änderungen an Listen und Metadaten prüfen; Quellen können sich ändern.

Bei einer neuen Quelle: Parser mit Validierung und passenden Tests ergänzen,
Quelldatei und CSV erzeugen, den Einzel-Export in `build_lists.py` aufnehmen und
im Workflow Abruf, Commit-Pfade und Artefakt-Pfade ergänzen. Raw-URL und Grenzen
in der README dokumentieren. Zusätzliche reine Domainlisten können alternativ
über `sources.json` in die gemeinsame Liste einfließen.
