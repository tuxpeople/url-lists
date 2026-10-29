# Firewall-Domainlisten

Eigene und aus externen Quellen erstellte Allow- und Blocklisten. Python 3.10+
genügt; es sind keine zusätzlichen Pakete erforderlich.

## Apple-Endpunkte

[lists/allow/apple.txt](lists/allow/apple.txt) enthält die eindeutigen Hosts aus
den Tabellen der offiziellen Quelle [Apple: Use Apple products on enterprise networks](https://support.apple.com/en-us/101555).
Der erste Abruf enthält 134 eindeutige Einträge aus 148 Tabellenzeilen.
[metadata/apple.csv](metadata/apple.csv) bewahrt die Tabellenangaben einschließlich
Kategorien und Unterkategorien aus den Abschnittsüberschriften sowie Ports,
Protokollen, Betriebssystemen und Beschreibungen. Ein Host kann in mehreren
Kategorien vorkommen; diese Zuordnungen bleiben in der CSV erhalten, während die
Allowlist Duplikate entfernt. Damit kann die Liste später nach Diensten aufgeteilt
werden. Auch dort genannte
Drittanbieter sind enthalten. Verlinkte weiterführende Artikel werden nicht importiert.

Wildcards bleiben als `*.example.com` erhalten. Sie werden weder aufgelöst noch
in eine Freigabe der Hauptdomain umgewandelt. Das Zielsystem muss dieses Format
unterstützen. Die Gesamtliste umfasst auch optionale Dienste; die passende Auswahl
hängt von der eigenen Umgebung ab. Die Textdatei allein enthält keine Portregeln.
Apple weist außerdem darauf hin, dass HTTPS-Interception für diese Dienste
Verbindungsfehler verursachen kann (siehe Originalquelle).

```sh
python3 scripts/update_apple.py
python3 scripts/build_lists.py
python3 -m unittest discover -s tests -v
```

## Docker-Desktop-Endpunkte

[lists/allow/docker.txt](lists/allow/docker.txt) enthält die Hosts aus der
offiziellen [Docker-Desktop-Allowlist](https://docs.docker.com/desktop/enterprise/allow-list.md).
Der erste Abruf enthält 17 konkrete Hosts und keine Wildcards. Alle Tabellenzeilen
werden übernommen, einschließlich Fehlerberichten, Docker Scout, Docker Offload
und Gordon. Diese Liste beschreibt Docker Desktop; zusätzliche Registries oder
Dienste aus eigenen Containern sind damit nicht automatisch abgedeckt.
[metadata/docker.csv](metadata/docker.csv) erhält die URLs und Beschreibungen.

Für Pi-hole 6 diese URL als **Allowlist** abonnieren:

```text
https://raw.githubusercontent.com/tuxpeople/url-lists/main/pihole/docker-allow-exact.txt
```

Manuell aktualisieren und Exporte erzeugen:

```sh
python3 scripts/update_docker.py
python3 scripts/build_lists.py
```

Der Parser übernimmt nur die Domain-Tabelle. Fehlende Tabellen, weniger als zehn
Hosts, fehlende zentrale Registry-/Authentifizierungs-Hosts sowie unerwartete
URL-Formate führen zum Abbruch. Mögliche künftige Wildcards werden separat als
Regex exportiert und sind nicht Teil der abonnierbaren Domainliste.

## OpenShift-Endpunkte

[lists/allow/openshift.txt](lists/allow/openshift.txt) übernimmt die Tabellen der
[OpenShift-Firewall-Dokumentation auf `main`](https://github.com/openshift/openshift-docs/raw/refs/heads/main/modules/configuring-firewall-module.adoc).
Vorerst gibt es **eine gemeinsame Liste**: Cluster-Registries, Zugriff und Updates,
Telemetrie, OCI-spezifische Einträge, Cloud-Anbieter, optionale Inhalte und NTP.
Die Quelle ist nicht auf eine bestimmte OpenShift-Version festgelegt.

```text
https://raw.githubusercontent.com/tuxpeople/url-lists/main/pihole/openshift-allow-exact.txt
```

Der erste Abruf enthält 59 Tabellenzeilen und ergibt 47 eindeutige Hosts bzw.
Wildcard-Einträge. Die konkreten Hosts sind abonnierbar; Wildcards stehen separat
in [openshift-allow-regex.txt](pihole/openshift-allow-regex.txt). Insbesondere die
Cloud-Wildcards sind weitreichend und sollten nur nach Bedarf als Regeln ergänzt
werden. Wildcard-Vorschläge aus dem Fließtext werden nicht zusätzlich übernommen.

[metadata/openshift.csv](metadata/openshift.csv) erhält Kategorie, Cloud-Anbieter,
AsciiDoc-Bedingungen, Originalziel, Port und Beschreibung für eine spätere
Aufteilung. Alle bedingten Tabellen werden einbezogen; die Bedingungen werden
nicht für eine bestimmte Installationsvariante ausgewertet. Ziele mit
`<cluster_name>`, `<base_domain>` oder `<aws_region>` erhalten den Status
`requires-substitution` und werden nicht exportiert. Sie müssen für die eigene
Umgebung konkretisiert werden. Bei `storage.googleapis.com/openshift-release`
erlaubt Pi-hole den gesamten Host `storage.googleapis.com`, da DNS keine Pfade
unterscheiden kann. Externe Links in Beschreibungen werden nicht importiert.

Manuell aktualisieren:

```sh
python3 scripts/update_openshift.py
python3 scripts/build_lists.py
```

## Pi-hole 6

Die Dateien unter [`pihole/`](pihole/) werden eingecheckt und von GitHub Actions
aktualisiert. Für Apple diese Raw-URL in Pi-hole unter **Lists** hinzufügen und
als **Allow** (Allowlist) auswählen:

```text
https://raw.githubusercontent.com/tuxpeople/url-lists/main/pihole/apple-allow-exact.txt
```

Anschließend unter **Tools → Update Gravity** die Listen aktualisieren. Danach
übernimmt Pi-hole Änderungen bei seinen regelmäßigen Gravity-Aktualisierungen.
Das Repository muss für einen Zugriff ohne Anmeldung öffentlich sein. Die URL
steht zur Verfügung, sobald diese Änderungen auf GitHub im Branch `main` liegen.

| Datei | Verwendung |
| --- | --- |
| [apple-allow-exact.txt](pihole/apple-allow-exact.txt) | Apple-Allowlist zum Abonnieren |
| [docker-allow-exact.txt](pihole/docker-allow-exact.txt) | Docker-Desktop-Allowlist zum Abonnieren |
| [openshift-allow-exact.txt](pihole/openshift-allow-exact.txt) | Gemeinsame OpenShift-Allowlist zum Abonnieren |
| [openshift-allow-regex.txt](pihole/openshift-allow-regex.txt) | OpenShift-Wildcards als separate Regex-Regeln |
| [docker-allow-regex.txt](pihole/docker-allow-regex.txt) | Docker-Wildcards als separate Regex-Regeln; derzeit leer |
| [allow-exact.txt](pihole/allow-exact.txt) | Gesamte Allowlist zum Abonnieren |
| [block-exact.txt](pihole/block-exact.txt) | Gesamte Blocklist zum Abonnieren; anfangs leer |
| [apple-allow-regex.txt](pihole/apple-allow-regex.txt) | Apples Wildcards als separate Regex-Allow-Regeln |
| [allow-regex.txt](pihole/allow-regex.txt), [block-regex.txt](pihole/block-regex.txt) | Alle Wildcards als separate Regex-Regeln |

Für die anderen abonnierbaren Dateien den Dateinamen in der Raw-URL ersetzen.
Apple, Docker und OpenShift sind bereits in der gesamten Allowlist enthalten. Entweder die
gewünschten Einzellisten oder die gesamte Allowlist abonnieren.

**Das Apple-Abo enthält nur konkrete Hosts und deckt die Wildcards nicht ab.**
Die Zeilen aus `apple-allow-regex.txt` bei Bedarf im Webinterface unter
**Domains** als erlaubte Regex-Regeln hinzufügen. Diese Regeln werden durch das
Listenabo nicht aktualisiert. Regex-Dateien dürfen nicht als Liste abonniert
werden. Importskripte werden nicht benötigt und nicht mehr erzeugt.

Die Regex `^([^.]+\.)+push\.apple\.com$` erlaubt beispielsweise
`a.push.apple.com` und `a.b.push.apple.com`, aber nicht `push.apple.com` selbst.
Die Exportdateien enthalten keine `*.`-Einträge mehr.

Pi-hole filtert DNS-Namen. Die Ports und Protokolle aus der Apple-CSV bleiben
Informationen für eine zusätzliche Firewall-Konfiguration.

Referenz: [CLI](https://docs.pi-hole.net/core/pihole-command/),
[Import und Gruppen](https://docs.pi-hole.net/guides/whitelist-blacklist/),
[abonnierte Allowlisten und Prioritäten](https://docs.pi-hole.net/database/domain-database/).

## Eigene Listen und weitere Quellen

Unter `lists/allow/` und `lists/block/` können beliebige `.txt`-Dateien ergänzt
werden: ein Host pro Zeile, Kommentare ab `#`, optional ein führendes `*.`.
URLs, Pfade, IP-Adressen, Netzbereiche und Hosts-Dateien werden zurückgewiesen.
Der Build normalisiert Groß-/Kleinschreibung und IDNs, entfernt Duplikate und
schreibt sortierte Listen nach `dist/allow.txt` und `dist/block.txt`.
Identische Einträge auf beiden Seiten führen zum Abbruch; es gibt keinen
automatischen Vorrang. Überschneidungen zwischen Wildcards und Einzelhosts werden
nicht erkannt und müssen bei der Regelplanung berücksichtigt werden.

Weitere reine Domainlisten können in `sources.json` eingetragen werden:

```json
{
  "sources": [
    {
      "name": "example-source",
      "type": "block",
      "url": "https://example.org/domains.txt",
      "homepage": "https://example.org/",
      "license": "Lizenz und Weiterverteilungsrecht der Quelle prüfen",
      "enabled": false
    }
  ]
}
```

Dieses Beispiel ist deaktiviert. Quellen müssen UTF-8 und HTTPS verwenden.
Fehlerhafte, leere oder zu große Downloads brechen den Build ab. Für Apple wird
ein eigener HTML-Parser verwendet; auffällige Strukturänderungen oder weniger als
80 extrahierte Hosts führen zum Abbruch. Inhaltliche Änderungen oberhalb dieser
Schwelle werden nicht automatisch bewertet.

Mit `python3 scripts/build_lists.py --offline` werden nur die eingecheckten
Listen geprüft und gebaut.

## GitHub Actions

Der Workflow prüft Pushes und Pull Requests und läuft zusätzlich täglich um
05:23 UTC sowie auf manuellen Aufruf. Pull Requests verwenden ausschließlich lokale
Listen. Die anderen Läufe aktualisieren zunächst Apple, Docker und OpenShift und laden danach weitere
aktivierte Quellen. Ein erfolgreicher Lauf stellt `domain-lists` für 30 Tage unter
**Actions → Workflow-Lauf → Artifacts** bereit.

Auf dem Default-Branch committet die Action geänderte Apple-/Docker-/OpenShift-Quelldaten und die
Exporte unter `pihole/` automatisch. Ohne Änderungen entsteht kein Commit.
Erst nach erfolgreichem Abruf, Validierung und Build wird veröffentlicht.
Pull Requests und andere Branches veröffentlichen keine Änderungen.
Die Action verwendet den integrierten `GITHUB_TOKEN` mit `contents: write`;
ein eigener Token ist nicht erforderlich. Branch-Regeln müssen Pushes durch
GitHub Actions zulassen. Falls sie den Push verhindern, schlägt der Lauf fehl
und die bisher veröffentlichten Listen bleiben erhalten.

Lokal werden dieselben Exporte mit `python3 scripts/build_lists.py --offline`
erzeugt. `dist/` enthält weiterhin die allgemeinen Listen und bleibt ignoriert;
`pihole/` wird versioniert. Änderungen aus diesem Arbeitsverzeichnis müssen
zunächst auf GitHub gepusht werden, bevor die Raw-URLs und die Action nutzbar sind.
