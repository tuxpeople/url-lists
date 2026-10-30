# Firewall-Domainlisten

Eigene und aus externen Quellen erstellte Allow- und Blocklisten. Python 3.10+
genügt; es sind keine zusätzlichen Pakete erforderlich.

Für die Weiterarbeit: [Projektstand und offene Punkte](docs/projektstand.md).

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

In den Quelldateien bleiben Wildcards als `*.example.com` erhalten. Der Pi-hole-
Allow-Export wandelt sie in `@@||example.com^` um und erlaubt damit bewusst die
Hauptdomain samt allen Subdomains. Die Gesamtliste umfasst auch optionale Dienste; die passende Auswahl
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
URL-Formate führen zum Abbruch. Mögliche künftige normale `*.`-Wildcards werden
als ABP-Allow-Regeln in die abonnierbare Liste aufgenommen.

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
Wildcard-Einträge. Konkrete Hosts und normale Wildcards stehen gemeinsam in der
abonnierbaren Allowlist. Insbesondere die Cloud-Wildcards umfassen viele Dienste;
die Gesamtliste enthält sie einschließlich ihrer Hauptdomains. Wildcard-Vorschläge
aus dem Fließtext werden nicht zusätzlich übernommen.

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

## Microsoft-365-Endpunkte

Die [offizielle Übersicht](https://learn.microsoft.com/en-us/microsoft-365/enterprise/urls-and-ip-address-ranges)
wird aus dem [Microsoft-Endpunkt-Webservice](https://learn.microsoft.com/en-us/microsoft-365/enterprise/microsoft-365-ip-web-service)
gespeist. Wir verwenden dessen JSON-Daten für **Worldwide einschließlich GCC**;
China, DoD und GCC High sind nicht enthalten. Required und Optional werden
gemeinsam aufgenommen.

```text
https://raw.githubusercontent.com/tuxpeople/url-lists/main/pihole/microsoft365-allow-exact.txt
```

[metadata/microsoft365.csv](metadata/microsoft365.csv) erhält pro Ziel und
Endpoint-Set die Überschrift als `category`, `Required`/`Optional` als
`requirement`, die separate Netzwerkklassifikation `Optimize`/`Allow`/`Default`,
Service-Area, ID, TCP-/UDP-Ports, ExpressRoute und Hinweise. Die Überschriften sind
Exchange Online, SharePoint Online and OneDrive for Business, Microsoft Teams,
Microsoft 365 Common and Office Online sowie Microsoft 365 Unified Domains
(Endpoint-Set 184). Wiederholte Ziele behalten alle Zuordnungen; ein Ziel kann
in einem Set Required und in einem anderen Optional sein.

Die vollständige API-Antwort einschließlich IP-Netzen bleibt in
[metadata/microsoft365.json](metadata/microsoft365.json). IP-Netze werden nicht
in Pi-hole-Domainlisten aufgenommen. [lists/allow/microsoft365.txt](lists/allow/microsoft365.txt)
enthält konkrete Hosts und normale `*.`-Wildcards. Die Sondermuster
`autodiscover.*.onmicrosoft.com` und `*cdn.onenote.net` bleiben in den Metadaten
und werden zusätzlich in `pihole/microsoft365-allow-regex.txt` und der gemeinsamen
Regex-Liste exportiert. Die Tenant-Wildcard entspricht einem DNS-Label, die
Suffix-Wildcard beliebigen Zeichen vor `cdn.onenote.net`. Unbekannte Muster
brechen die Aktualisierung zur Prüfung ab.

Normale `*.`-Wildcards sind als ABP-Regeln im Abo enthalten. Nur die beiden
Sondermuster benötigen weiterhin Regex-Regeln. Es gibt vorerst keine Aufteilung nach
Dienst oder Required/Optional. Die Überschriften werden aus den Service-Areas
zugeordnet; neue Service-Areas müssen im Parser ergänzt werden.

```sh
python3 scripts/update_microsoft365.py
python3 scripts/build_lists.py
```

Der tägliche Abruf verwendet eine neu erzeugte ClientRequestId. Manuelle Abrufe
nicht in kurzen Abständen wiederholen; Microsoft kann sie begrenzen.

## Pi-hole-Forum: Commonly Whitelisted Domains

[lists/allow/pihole-forum.txt](lists/allow/pihole-forum.txt) enthält die
Domain-Empfehlungen aus dem [Wiki-Hauptbeitrag](https://discourse.pi-hole.net/t/commonly-whitelisted-domains/212).
Importiert wird ausschließlich Post 1 über die Discourse-JSON-Schnittstelle,
keine Antworten und keine verlinkten Seiten. Der erste Abruf ergibt 254 konkrete
Hosts und eine Wildcard (`*.rmbl.ws`). Diese Community-Sammlung ist eine Liste
von möglichen Ausnahmen bei konkreten Problemen, keine notwendige Grundfreigabe;
sie enthält auch Werbung, Tracking und Telemetrie sowie ältere Empfehlungen.

```text
https://raw.githubusercontent.com/tuxpeople/url-lists/main/pihole/pihole-forum-allow-exact.txt
```

[metadata/pihole-forum.csv](metadata/pihole-forum.csv) erhält alle drei
Überschriftenebenen als `category`, `subcategory` und `detail`, dazu Zieltyp,
Ziel, Importstatus und ursprünglichen Befehl. Mehrfachzuordnungen bleiben
erhalten. Nur Domain-Argumente aus Allow-Befehlen werden extrahiert; Shell-Befehle
werden niemals ausgeführt. `s{1..5}.symcb.com` wird kontrolliert in fünf Hosts
aufgelöst. Die redundante Google-Sammelzeile wird mit Status
`excluded-duplicate-summary` dokumentiert und übersprungen, da sie in der Quelle
ein umgebrochenes Domainwort enthält. Die Einzelabschnitte bleiben maßgeblich.
Die ausdrücklich im Rumble-Fließtext empfohlene Wildcard wird ebenfalls übernommen.

Die sieben im Beitrag genannten freien Regex-Ausdrücke bleiben **nur in den
Metadaten**, zusätzlich in [pihole-forum-regex.txt](metadata/pihole-forum-regex.txt).
Sie sind keine konkreten Domains und werden nicht automatisch in die laufende
Regex-Synchronisation übernommen. Die Rumble-Wildcard steht als `@@||rmbl.ws^`
in der abonnierbaren Liste und gibt damit `rmbl.ws` samt Subdomains frei.
Konkrete Domains und diese ABP-Regel fließen auch in den gemeinsamen Allow-Export
ein. Die Forum-Allow-Regex-Datei ist leer.

```sh
python3 scripts/update_pihole_forum.py
python3 scripts/build_lists.py
```

Der Workflow aktualisiert diese Quelle täglich wie die anderen Listen. Der
Parser bricht bei unerwarteten Befehlen, ungültigen Domains oder auffällig
unvollständigem Inhalt ab.

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
| [microsoft365-allow-exact.txt](pihole/microsoft365-allow-exact.txt) | Microsoft-365-Allowlist, Required und Optional |
| [pihole-forum-allow-exact.txt](pihole/pihole-forum-allow-exact.txt) | Community-Domainempfehlungen aus dem Wiki |
| [pihole-forum-allow-regex.txt](pihole/pihole-forum-allow-regex.txt) | Leer; freie Regex des Wikis nur in Metadaten |
| [microsoft365-allow-regex.txt](pihole/microsoft365-allow-regex.txt) | Nur die beiden Microsoft-365-Sondermuster |
| [openshift-allow-regex.txt](pihole/openshift-allow-regex.txt) | Leer; normale Wildcards im Listenabo |
| [docker-allow-regex.txt](pihole/docker-allow-regex.txt) | Leer |
| [allow-exact.txt](pihole/allow-exact.txt) | Gesamte Allowlist zum Abonnieren |
| [block-exact.txt](pihole/block-exact.txt) | Gesamte Blocklist zum Abonnieren; anfangs leer |
| [apple-allow-regex.txt](pihole/apple-allow-regex.txt) | Leer; normale Wildcards im Listenabo |
| [allow-regex.txt](pihole/allow-regex.txt), [block-regex.txt](pihole/block-regex.txt) | Allow: Sondermuster; Block: normale Wildcard-Regex |

Für die anderen abonnierbaren Dateien den Dateinamen in der Raw-URL ersetzen.
Apple, Docker, OpenShift, Microsoft 365 und die Forumsliste sind bereits in der gesamten Allowlist enthalten. Entweder die
gewünschten Einzellisten oder die gesamte Allowlist abonnieren.

Die bisherigen Allow-Dateinamen `*-exact.txt` bleiben für bereits eingerichtete
Abonnements erhalten. **Sie enthalten jetzt konkrete Domains und ABP-Regeln**:

```text
login.microsoftonline.com
@@||microsoft.com^
```

Ein konkreter Host bleibt exakt; `@@||microsoft.com^` erlaubt dagegen sowohl
`microsoft.com` als auch beliebig tiefe Subdomains. Diese Regeln werden als
**Allowlist abonniert**, nicht unter Domains als Regex eingetragen. Aus dem
Quelldomain-Eintrag `*.example.com` entsteht bewusst eine Freigabe einschließlich
der Hauptdomain. In Quellen und Metadaten bleibt die ursprüngliche Schreibweise
mit allen Kategoriezuordnungen vollständig erhalten.

Individuelle exakte Deny-Regeln haben Vorrang vor abonnierten Allowlisten.
Damit können einzelne Hosts trotz einer breiten Domainfreigabe gesperrt werden.
Individuelle Regex-Allow-Regeln haben dagegen Vorrang vor exakten Deny-Regeln;
das gilt weiterhin für die beiden verbliebenen Microsoft-Sondermuster.

Redundante normale Wildcards werden pro Export entfernt: Neben `*.microsoft.com`
wird `*.security.microsoft.com` nicht zusätzlich ausgegeben. DNS-Labelgrenzen
werden berücksichtigt; `*.notmicrosoft.com` bleibt eigenständig. Gefilterte
Exporte werden aus den vollständigen Quelldaten neu bereinigt. Exakte Hosts
bleiben erhalten. Block-Exporte verwenden weiterhin exakte Domains und separate
Subdomain-Regex-Regeln; ihre Semantik wird nicht verändert.

### Umstellung bestehender Installationen

1. Die Änderungen nach GitHub veröffentlichen. Die bestehenden Allow-Abonnement-
   URLs bleiben gleich; für die Gesamtliste ist es
   `https://raw.githubusercontent.com/tuxpeople/url-lists/main/pihole/allow-exact.txt`.
2. In Pi-hole Gravity aktualisieren und prüfen, dass die aktualisierte Allowlist
   samt ABP-Einträgen erfolgreich übernommen und der gewünschten Gruppe zugeordnet ist.
3. `bash scripts/regex_import.sh --dry-run` ausführen. Die normalen eigenen
   Wildcard-Regex-Regeln sollten als zu entfernen erscheinen; nur Sondermuster bleiben.
4. Mit `bash scripts/regex_import.sh` die veralteten skriptverwalteten Regeln entfernen.
   Manuelle Regex-Regeln werden nicht gelöscht. Eventuell manuell angelegte breite
   Regex-Allow-Regeln müssen separat geprüft werden, da sie exakte Sperren weiter überstimmen.

Die Allow-Regex-Dateien bleiben verfügbar, auch wenn sie leer sind, damit bestehende
Synchronisationen entfernte Regeln erkennen und aufräumen können. Die beiden
Microsoft-Sondermuster können weiterhin über den Regex-Abgleich verwaltet werden.
Regex-Dateien sind weiterhin keine abonnierbaren Domainlisten.

Pi-hole filtert DNS-Namen. Die Ports und Protokolle aus der Apple-CSV bleiben
Informationen für eine zusätzliche Firewall-Konfiguration.

Referenz: [CLI](https://docs.pi-hole.net/core/pihole-command/),
[Import und Gruppen](https://docs.pi-hole.net/guides/whitelist-blacklist/),
[abonnierte Allowlisten und Prioritäten](https://docs.pi-hole.net/database/domain-database/).

## Regex-Synchronisation mit Pi-hole

`scripts/regex_import.sh` vergleicht heruntergeladene Regex-Listen mit dem
**aktuellen Pi-hole-Zustand über die JSON-API**. Es liest die Regeln mit
`docker exec CONTAINER pihole api domains/allow/regex` bzw. `domains/deny/regex`
aus, ohne `-i`/`-t`. Die Authentifizierung übernimmt die Pi-hole-CLI im Container;
sie muss dort ohne interaktive Passwortabfrage funktionieren. Auf dem Host werden
Bash, curl, Docker, jq sowie die üblichen Unix-Werkzeuge benötigt.

**Der normale Aufruf führt Änderungen aus.** `--dry-run` zeigt ausschließlich
geplante Änderungen und Befehle an. Standardquelle für Allow ist die gemeinsame
`pihole/allow-regex.txt` mit den verbliebenen Sondermustern; für Deny `pihole/block-regex.txt`.
Die protokollierten Befehle enthalten einzeln für Bash quotierte Argumente;
ausgeführt wird direkt mit Argument-Arrays, ohne `eval`. Pro Befehl werden
höchstens 100 Regeln verarbeitet. Erst nach erfolgreich geprüften Ergänzungen
beginnen Löschungen. Die gesamte Ausgabe enthält auch Überschriften und
Statusmeldungen und ist nicht als Shellskript gedacht.

```sh
# Vorschau ohne Änderungen
bash scripts/regex_import.sh --dry-run

# Gesamte Allow-Regex-Liste im Container pihole synchronisieren
bash scripts/regex_import.sh

# Anderer Containername
bash scripts/regex_import.sh --container dns

# Deny-Regeln synchronisieren
bash scripts/regex_import.sh --type deny
```

`--url` ist wiederholbar und ersetzt die Standardquellen. Alle ausgewählten Listen
werden vor dem Vergleich zusammengeführt. Standardmäßig gelten ausschließlich
Regeln mit dem **exakten Kommentar** `managed by script` als skriptverwaltet;
mit `--comment TEXT` kann eine andere eindeutige Markierung verwendet werden.
Diese Markierung beschreibt den gesamten ausgewählten Regelsatz, nicht einzelne
Quellen. Unterschiedliche unabhängige Abgleiche desselben Regeltyps müssen
unterschiedliche Markierungen verwenden, sonst würden sie gegenseitig Regeln
als veraltet einstufen.

Der Abgleich verarbeitet folgende Änderungen:

- Gewünschte Regeln, die in Pi-hole fehlen: hinzufügen, mit unserer Markierung.
- Eigene Regeln, die nicht mehr in den Quellen stehen: entfernen.
- Bereits vorhandene Regeln mit anderen oder ohne Kommentare: unverändert lassen,
  auch wenn dieselbe Regex gewünscht ist. Alle nicht verwalteten Regeln werden
  separat angezeigt, auch wenn sie in keiner abonnierten Liste vorkommen.
- Deaktivierte eigene Regeln, die weiterhin gewünscht sind: deaktiviert lassen und
  gesondert anzeigen. Gruppen und Aktivierungszustand vorhandener Regeln werden
  nicht verändert. Neue Regeln werden durch die CLI der Default Group zugeordnet.

Es gibt keine lokale Vergleichsdatei mehr. `--state-dir` und `--accept-baseline`
entfallen; alte Vergleichsdateien werden weder gelesen noch gelöscht. Jeder Lauf
liest den tatsächlichen Pi-hole-Zustand neu. Bei `--dry-run` zeigt der nächste Lauf daher dieselben geplanten Änderungen
erneut, solange sich Listen und Istzustand nicht ändern.

Downloads werden mit HTTPS, HTTP-Fehlerprüfung sowie Zeit-/Größenbegrenzung geladen.
Das Skript normalisiert CRLF/Leerzeilen, validiert das erwartete verankerte
POSIX-Regex-Format und entfernt Duplikate. Erfolgreiche leere Listen sind zulässig
und können Löschungen eigener Regeln auslösen. Bei Downloadfehlern oder ungültigen
API-Antworten wird vor Änderungen abgebrochen. Die API-Antwort muss genau
ein JSON-Objekt mit einem gültigen `domains`-Array sein; Fehlermeldungen oder
unvollständige Datensätze werden nicht als leere Liste interpretiert.

Vor jedem Paket wird geprüft, ob sich Regeln, Kommentare, Gruppen oder
Aktivierungszustände seit der Planung geändert haben. Nach jedem Paket und
abschließend wird der tatsächliche Zustand erneut abgefragt. Der CLI-Rückgabecode
allein genügt nicht: Auch ein scheinbar erfolgreicher Befehl mit unvollständigem
Ergebnis führt zum Abbruch mit Fehlerstatus. Bereits erfolgreiche Änderungen
werden nicht zurückgerollt; ein erneuter Lauf plant vom tatsächlichen Zustand aus.
Ein neu hinzugefügter Eintrag muss aktiviert, mit unserer Markierung und der
Default Group `[0]` vorhanden sein. Andere Zustände gelten als Abweichung.

Eine lokale Verzeichnissperre unter
`${XDG_STATE_HOME:-$HOME/.local/state}/url-lists/` verhindert parallele schreibende
Läufe für denselben Container und Regeltyp unter demselben Zustandsverzeichnis.
Verschiedene Benutzer sollten hierfür dasselbe `XDG_STATE_HOME` verwenden.
Nach einem harten Prozessabbruch kann ein `regex-sync-*.lock`-Verzeichnis
zurückbleiben; nur entfernen, wenn kein zugehöriger Lauf aktiv ist. Andere
Pi-hole-Verwaltungswerkzeuge werden nicht gesperrt. Bei erkannten parallelen
Änderungen stoppt der Abgleich; die Prüfung und ein CLI-Schreibzugriff sind keine
atomare Transaktion. Es wird nicht direkt auf die Datenbank zugegriffen.

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
Listen. Die anderen Läufe aktualisieren zunächst Apple, Docker, OpenShift, Microsoft 365 und das Pi-hole-Wiki und laden danach weitere
aktivierte Quellen. Ein erfolgreicher Lauf stellt `domain-lists` für 30 Tage unter
**Actions → Workflow-Lauf → Artifacts** bereit.

Auf dem Default-Branch committet die Action geänderte Quelldaten und die
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
