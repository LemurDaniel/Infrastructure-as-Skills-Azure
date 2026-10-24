# Entscheidungen für „chatrag“

Was gebaut wird, entschieden aus euren Antworten und den Regeln hinter den Vorgaben. Jede Zeile ist eine Entscheidung; der Schlüssel im Anhang ist, wo ein Engineer sie in der Spezifikation findet.

Stand 2026-10-24. Spezifikation: `infra-spec.yaml`.

## Das System

- Das System wird in diesen Stufen ausgerollt: Entwicklung, Test, Echtbetrieb.
- Alles läuft in der Azure-Region westeurope.
- „chatrag“ ist der Name, den jeder Teil des Systems trägt.
- Jede Stufe liegt in einer eigenen Subscription; die Stufen können sich gegenseitig weder Ressourcen noch Budgets noch Berechtigungen anfassen.

## Was sich zwischen den Stufen unterscheidet

Ein Code wird durch diese Stufen ausgerollt; alles, was hier nicht steht, ist in jeder Stufe gleich.

- Protokolle werden in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace gesammelt.
- Azure Virtual Network: Eigene Namensserver: Entwicklung: keine; Test: keine; Echtbetrieb: keine (keine: Azures eigene).
- Azure Virtual Network: Subnetze, die eine Sicherheitsgruppe bekommen: Entwicklung: snet-endpoints, snet-web; Test: snet-endpoints, snet-web; Echtbetrieb: snet-endpoints, snet-web.
- Azure Virtual Network: Netzwerkprotokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Network Security Group (endpoints): Ausdrücklich erlaubter Verkehr: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Azure Network Security Group (endpoints): Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Network Security Group (integration): Ausdrücklich erlaubter Verkehr: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Azure Network Security Group (integration): Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Application Insights (workspace-based): Seine Telemetrie wird in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace gespeichert.
- Azure Application Insights (workspace-based): Zugriffsrechte auf die Komponente vergeben an: Entwicklung: app-service (Monitoring Metrics Publisher); Test: app-service (Monitoring Metrics Publisher); Echtbetrieb: app-service (Monitoring Metrics Publisher).
- Azure Key Vault: Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure Key Vault: Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Storage Account: Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure Storage Account: Zugriffsrechte vergeben an: Entwicklung: search-service (Storage Blob Data Reader); Test: search-service (Storage Blob Data Reader); Echtbetrieb: search-service (Storage Blob Data Reader).
- Azure Storage Account: Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure AI Foundry (AI Services account with projects and model deployments): Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure AI Foundry (AI Services account with projects and model deployments): Zugriffsrechte auf das Konto vergeben an: Entwicklung: app-service (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User); Test: app-service (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User); Echtbetrieb: app-service (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User).
- Azure AI Foundry (AI Services account with projects and model deployments): Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure AI Search service: Der Suchdienst hat die Stufe Entwicklung: Basic, klein und günstig, eine Partition; Test: Basic, klein und günstig, eine Partition; Echtbetrieb: Standard, die übliche Produktionsstufe. _(außerhalb der Produktion günstiger)_
- Azure AI Search service: Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure AI Search service: Zugriffsrechte auf den Suchdienst vergeben an: Entwicklung: app-service (Search Index Data Reader); Test: app-service (Search Index Data Reader); Echtbetrieb: app-service (Search Index Data Reader).
- Azure AI Search service: Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure App Service (web app on an App Service plan): Der Hosting-Plan hat die Größe Entwicklung: B1, klein und günstig, ohne Zonenredundanz, für Stufen von denen niemand abhängt; Test: B1, klein und günstig, ohne Zonenredundanz, für Stufen von denen niemand abhängt; Echtbetrieb: P1v3, Premium, die übliche Produktionsgröße. _(außerhalb der Produktion günstiger)_
- Azure App Service (web app on an App Service plan): Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure App Service (web app on an App Service plan): Ausgehender Verkehr verlässt das Netz über das Subnetz Entwicklung: snet-web; Test: snet-web; Echtbetrieb: snet-web.
- Azure App Service (web app on an App Service plan): Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.

## Was aus euren Antworten folgt

- **Das System wird durch GitHub Actions ausgerollt.** _(aus eurer Beschreibung)_
- **Ein Tag Ausfall wäre verkraftbar.** _(aus eurer Beschreibung)_
  - daher, Azure Storage Account: Die Daten liegen dreifach in einem Rechenzentrum.
  - daher, Azure AI Search service: 1 Kopien des Index beantworten Anfragen.
  - daher, Azure App Service (web app on an App Service plan): Die App übersteht nicht den Ausfall eines Rechenzentrums der Region.
  - daher, Azure App Service (web app on an App Service plan): 1 Kopien der App laufen gleichzeitig.
- **Nach einem versehentlichen Löschen müsst ihr eine Woche zurückkommen.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure Storage Account: Gelöschte Dateien sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account: Gelöschte Ordner sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account: Frühere Versionen überschriebener Dateien werden aufgehoben.
- **Die Daten werden laufend genutzt.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure Storage Account: Gespeichert in der Klasse Standard: günstig beim Lesen, für Daten in Nutzung.
- **Gegen absichtliche Zerstörung sind die Daten nur innerhalb des Systems selbst geschützt; wer das System löschen kann, kann auch die Kopien löschen.** _(nicht gesagt, daher gilt die übliche Antwort)_
- **Die Daten werden nur innerhalb des Wirtschaftsraums der Region, zum Beispiel der EU gespeichert und verarbeitet.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure AI Foundry (AI Services account with projects and model deployments): Anfragen an die Modelle werden überall innerhalb derselben Datenzone (zum Beispiel der EU) verarbeitet.
- **Der Code wird aus einzeln ausgeschriebenen Ressourcen gebaut.** _(eure Antwort)_
- **Der Zugang ist nur privat, nichts ist aus dem Internet erreichbar.** _(aus eurer Beschreibung)_
- **Einzuhaltende Vorgaben: keine.** _(aus eurer Beschreibung)_
- **Protokolle werden 30 Tage aufbewahrt.** _(nicht gesagt, daher gilt die übliche Antwort)_

## Nach den Vorgaben gesetzt

Nichts davon wurde gefragt; jede Zeile folgt einer Regel oder einer der Antworten oben. Sagt Bescheid, wenn eine nicht passt.

### Für das ganze System

- Die Pipeline meldet sich mit einem kurzlebigen Token pro Lauf, ohne irgendwo gespeichertes Passwort bei Azure an.
- Eine Person gibt die Änderung frei, bevor sie ausgerollt wird: nur im Echtbetrieb.
- Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Protokollierung selbst mit.
- Passwörter und Zugriffsschlüssel sind abgeschaltet; der Zugriff läuft über Firmenkonten, damit jede Aktion zuordenbar ist.
- Verschlüsselungsschlüssel sind in Software geschützt, der Standard, ausreichend ohne Vorgabe für Hardware.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Das Netz wird von diesem Ausrollen selbst gebaut.
- Die Namensauflösung für private Anbindungen übernimmt dieses Ausrollen selbst. — weil: Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Protokollierung selbst mit.
- Protokolle gehen in einen Arbeitsbereich, den dieses Ausrollen anlegt und bezahlt. — weil: Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Protokollierung selbst mit.
- Protokolle werden in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace gesammelt. — weil: Protokolle gehen in einen Arbeitsbereich, den dieses Ausrollen anlegt und bezahlt.
- Tägliche Obergrenze für Protokolle: -1 GB (-1: keine).

### Azure Virtual Network

- Eigene Namensserver: Entwicklung: keine; Test: keine; Echtbetrieb: keine (keine: Azures eigene).
- Netzwerkregeln gelten für private Anbindungen in ihrem Subnetz.
- Abkürzungen zu Azure-Diensten aus den Subnetzen: keine.
- An einen Dienst übergebene Subnetze: snet-web (Microsoft.Web/serverFarms). — weil: `resources.app-service.networking.integration_subnet`
- Ein kostenpflichtiger DDoS-Schutzplan wird nicht genutzt; Azures Basisschutz gilt ohnehin.
- Subnetze, die eine Sicherheitsgruppe bekommen: Entwicklung: snet-endpoints, snet-web; Test: snet-endpoints, snet-web; Echtbetrieb: snet-endpoints, snet-web. — weil: `resources.network-security-group__endpoints.rules.subnet_purpose`
- Netzwerkprotokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Eine Aufzeichnung erlaubten und abgewiesenen Verkehrs wird nicht geführt.

### Azure Network Security Group (endpoints)

- Die Gruppe schützt ein Subnetz für private Anbindungen an Azure-Dienste.
- Eingehender Verkehr, den keine Regel erlaubt, wird abgelehnt, auch von anderen Maschinen im selben Netz.
- Ausgehender Verkehr ins Internet, den keine Regel erlaubt, wird abgelehnt; was hinaus muss, läuft über die Firmen-Firewall. — weil: `resources.network-security-group__endpoints.rules.subnet_purpose`
- Ausdrücklich erlaubter Verkehr: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Protokolliert wird: welche Regel auf welche Maschine angewendet wurde, wie oft jede Regel gegriffen hat.

### Azure Network Security Group (integration)

- Die Gruppe schützt ein Subnetz für den ausgehenden Verkehr von Web- und Function-Apps.
- Eingehender Verkehr, den keine Regel erlaubt, wird abgelehnt, auch von anderen Maschinen im selben Netz.
- Ausgehender Verkehr ins Internet, den keine Regel erlaubt, wird den eingebauten Azure-Regeln überlassen, die ihn hinauslassen.
- Ausdrücklich erlaubter Verkehr: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Protokolliert wird: welche Regel auf welche Maschine angewendet wurde, wie oft jede Regel gegriffen hat.

### Azure Log Analytics Workspace

- Protokolle werden 30 Tage aufbewahrt.
- Tägliche Obergrenze für Protokolle: -1 GB (-1: keine).
- Abgerechnet pro Gigabyte, nach Verbrauch.
- Der Protokoll-Arbeitsbereich ist aus dem Internet erreichbar, mit Firmenkonten und Verschlüsselung; einen privaten Zugang dafür gibt es nicht.
- Protokolle mit dem Arbeitsbereichs-Schlüssel zu senden ist nicht möglich, Agenten nutzen Firmenidentitäten.
- Wer Protokolle lesen darf, entscheiden die Berechtigungen des Arbeitsbereichs selbst.
- Ein gelöschter Arbeitsbereich kann 14 Tage lang wiederhergestellt werden.
- Langzeitarchivierung in günstigen Speicher ist ausgeschaltet.

### Azure Application Insights (workspace-based)

- Seine Telemetrie wird in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace gespeichert.
- Die Komponente ist eingerichtet für eine Webanwendung oder einen Dienst.
- 100 Prozent der Telemetrie werden behalten.
- Tägliche Obergrenze für die Telemetrie dieser Komponente: 0 GB (0: keine).
- IP-Adressen von Besuchern werden maskiert und nicht gespeichert.
- Die Komponente ist nur über die private Überwachungsanbindung erreichbar, zum Senden und zum Lesen.
- Das Senden von Telemetrie nur mit einem Schlüssel ist abgeschaltet; Anwendungen melden sich mit Firmenidentitäten an.

### Azure Key Vault

- Der Tresor ist die Stufe Standard, Schlüssel in Software geschützt.
- Ein gelöschter Tresor oder ein gelöschtes Geheimnis lässt sich nicht endgültig löschen, auch nicht von einem Administrator, bevor die Aufbewahrungszeit endet.
- Gelöschte Inhalte des Tresors lassen sich 90 Tage lang wiederherstellen.
- Der Zugriff auf den Inhalt des Tresors wird über Rollenzuweisungen, wie alles andere in Azure gesteuert.
- Der Tresor ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Vertrauenswürdige Azure-Dienste dürfen nicht an der Firewall des Tresors vorbei.
- Plattformdienste, die aus dem Tresor lesen dürfen: keine (leer: keine).
- Für die Geheimnisse keine werden leere Plätze angelegt; die Werte werden danach von Hand oder von der Anwendung eingetragen.
- Verschlüsselungsschlüssel sind von Azure verwaltet - der Tresor hält dafür keine.
- Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Protokolliert wird: jeder Lese-, Schreib- und fehlgeschlagene Zugriff auf den Tresor, wie Richtlinien den Tresor bewertet haben.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Storage Account

- Der Speicher ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Private Anbindungen gibt es für: Dateien (Blob).
- Azures eigene Dienste (Backup, Überwachung) dürfen am Firewall vorbei auf den Speicher zugreifen.
- Der Speicher hat eine eigene Identität, um andere Dienste zu erreichen.
- Zugriffsrechte vergeben an: Entwicklung: search-service (Storage Blob Data Reader); Test: search-service (Storage Blob Data Reader); Echtbetrieb: search-service (Storage Blob Data Reader).
- Zugriff mit einem geteilten Schlüssel ist nicht möglich; der Zugriff läuft über Firmenkonten.
- Verbindungen müssen mindestens TLS 1.2-Verschlüsselung nutzen.
- Unverschlüsselte Verbindungen werden abgewiesen.
- Einzelne Ordner öffentlich lesbar zu machen ist nicht möglich.
- Eine zweite Verschlüsselungsschicht unterhalb des Dienstes ist eingeschaltet.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Dateiübertragung per SFTP ist ausgeschaltet.
- Ein Protokoll jeder Änderung wird nicht geführt.
- Der ganze Speicher lässt sich 0 Tage zurückdrehen (0: gar nicht).
- Löschschutz per Gesetz oder Richtlinie: keiner.
- Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Protokolliert wird: wer worauf zugegriffen hat.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure AI Foundry (AI Services account with projects and model deployments)

- Das Konto ist eine AI-Foundry-Ressource, die auch Projekte, Agenten und die weiteren KI-Dienste bietet.
- Das Konto nutzt die Preisstufe S0, die bezahlte Standardstufe.
- Das Konto enthält Foundry-Projekte als Behälter für Zugriff, Daten und Kosten.
- Das Konto enthält die Projekte keine.
- Jedes Modell darf bis zu 10 Tausend Token pro Minute verarbeiten.
- Läuft die Modellversion aus, wechselt sie an diesem Tag auf die neue Standardversion.
- Anfragen und Antworten werden vom Inhaltsfilter Microsoft.DefaultV2 geprüft.
- Das Konto ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Das Konto darf nur Adressen aufrufen, die ausdrücklich erlaubt sind.
- Das Konto hat eine eigene Identität.
- Zugriffsrechte auf das Konto vergeben an: Entwicklung: app-service (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User); Test: app-service (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User); Echtbetrieb: app-service (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User).
- Die Anmeldung mit Kontoschlüsseln ist abgeschaltet; der Zugriff läuft über Firmenkonten.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Protokolliert wird: Änderungen am Konto und wer sie gemacht hat, jede Anfrage an die Modelle mit Aufrufer, Größe und Ergebnis (nicht der Text), die von jedem Aufruf verbrauchten Token.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure AI Search service

- Der Suchdienst hat die Stufe Entwicklung: Basic, klein und günstig, eine Partition; Test: Basic, klein und günstig, eine Partition; Echtbetrieb: Standard, die übliche Produktionsstufe.
- Die Indexdaten sind auf 1 Partition(en) verteilt.
- Die Neubewertung der Ergebnisse nach Bedeutung ist an, im Rahmen eines kleinen kostenlosen Monatskontingents.
- Der Suchdienst ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Vertrauenswürdige Azure-Dienste dürfen nicht an der Firewall des Suchdienstes vorbei.
- Der Suchdienst hat eine eigene Identität.
- Zugriffsrechte auf den Suchdienst vergeben an: Entwicklung: app-service (Search Index Data Reader); Test: app-service (Search Index Data Reader); Echtbetrieb: app-service (Search Index Data Reader).
- Die Anmeldung mit API-Schlüsseln ist abgeschaltet; der Zugriff läuft über Firmenkonten.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Protokolliert wird: jede Abfrage und jede Änderung an Indizes und Indexern.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure App Service (web app on an App Service plan)

- Die App läuft auf Linux.
- Der Hosting-Plan hat die Größe Entwicklung: B1, klein und günstig, ohne Zonenredundanz, für Stufen von denen niemand abhängt; Test: B1, klein und günstig, ohne Zonenredundanz, für Stufen von denen niemand abhängt; Echtbetrieb: P1v3, Premium, die übliche Produktionsgröße.
- Die App ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Der ausgehende Verkehr der App läuft durch das Firmennetz, so erreicht sie private Dienste.
- Ausgehender Verkehr verlässt das Netz über das Subnetz Entwicklung: snet-web; Test: snet-web; Echtbetrieb: snet-web. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Ausgehender Verkehr wird komplett durch das Firmennetz geleitet, auch ins Internet geleitet.
- Die App hat eine eigene Identität, um andere Dienste zu erreichen.
- Unverschlüsselte Verbindungen werden auf die verschlüsselte Adresse umgeleitet.
- Verbindungen müssen mindestens TLS 1.2-Verschlüsselung nutzen.
- Dateiupload per FTP ist abgeschaltet.
- Das Ausrollen mit Benutzername und Passwort ist nicht möglich; Rollouts laufen über Firmenkonten.
- Die App bleibt geladen und antwortet sofort auf die erste Anfrage, wenn kein Verkehr anliegt.
- Die Plattform prüft die Gesundheit der App unter dem Pfad  (leer: keine Prüfung).
- HTTP/2 ist eingeschaltet.
- Seine Protokolle gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Protokolliert wird: jede Web-Anfrage, die eigenen Log-Meldungen der App, wer sich zum Ausrollen oder Verwalten angemeldet hat, Änderungen an den Zugriffsbeschränkungen, die eigenen Meldungen der Plattform zur App.
- Nutzungs- und Leistungswerte werden erfasst.

## Noch offen

Solange diese Punkte offen sind, wird nichts ausgerollt.

- Which subscription does each stage deploy into? One per stage (stage_isolation: subscription). [Entwicklung, Test, Echtbetrieb] _(gebraucht von: workload owner)_ — blockiert: apply
- Which resource group does each stage deploy into? [Entwicklung, Test, Echtbetrieb] _(gebraucht von: workload owner)_ — blockiert: apply
- Which tag set does the organisation apply? Nothing stated, no repository to read it from. _(gebraucht von: workload owner)_ — blockiert: apply
- Which address range does each stage's new virtual network get? [Entwicklung, Test, Echtbetrieb] _(gebraucht von: network / IPAM owner)_ — blockiert: apply
- Which prefix inside that range is the private endpoint subnet (snet-endpoints)? [Entwicklung, Test, Echtbetrieb] _(gebraucht von: network / IPAM owner)_ — blockiert: apply
- Prefixes of the subnets snet-endpoints (private endpoints) and snet-web (App Service integration, delegated to Microsoft.Web/serverFarms), per stage. [Entwicklung, Test, Echtbetrieb] _(gebraucht von: network / IPAM owner)_ — blockiert: apply
- Which chat model and which embedding model (name and version)? Regional, with quota - looked up at render time, never recalled. _(gebraucht von: workload owner)_ — blockiert: apply
- Is there quota for the chosen models as DataZoneStandard in West Europe at 10,000 tokens per minute each? Not checked; a deployment beyond the quota fails at apply. _(gebraucht von: workload owner)_ — blockiert: apply
- Which runtime stack and version does the web app run (runtime_stack and runtime_version)? _(gebraucht von: workload owner)_ — blockiert: apply
- Which Azure Monitor Private Link Scope should the component belong to? Standalone: none exists, so it is built or the component stays open. _(gebraucht von: workload owner)_ — blockiert: apply
- Which principal reads which secrets? Nothing stated; with RBAC-only access a vault without assignment is working as specified and unusable. _(gebraucht von: workload owner)_ — blockiert: apply
- Who uploads the documents, and which data-plane role does that principal need? Only the search service (reader) is assigned. _(gebraucht von: workload owner)_ — blockiert: apply
- The search indexer reaches the storage account over a shared private link, approved on the account. Not rendered: wiring between two resources that no question set owns. _(gebraucht von: workload owner)_ — blockiert: apply

## Platzhalter

Werte, die der Lauf angenommen hat, um weiterzukommen. Das sind noch keine Entscheidungen.

- Zugriffsrechte auf die Komponente vergeben an: Entwicklung: app-service (Monitoring Metrics Publisher); Test: app-service (Monitoring Metrics Publisher); Echtbetrieb: app-service (Monitoring Metrics Publisher). (`resources.application-insights.identity.role_assignments`)

## Anhang: alle Entscheidungen

| Schlüssel | Wert | Quelle |
|---|---|---|
| `deployment.naming_convention` | default | Regel |
| `deployment.module_source` | authored | eure Antwort |
| `deployment.deploy_mechanism` | github | eure Beschreibung |
| `deployment.pipeline_auth` | workload_identity | Regel |
| `deployment.pipeline_approvals` | production | Regel |
| `deployment.stage_isolation` | subscription | Regel |
| `deployment.non_production_savings` | enabled | Regel |
| `deployment.outage_impact` | tolerable | eure Beschreibung |
| `deployment.data_loss_tolerance` | one_week | Regel |
| `deployment.data_access_pattern` | active | Regel |
| `deployment.backup_isolation` | operational | Regel |
| `deployment.data_residency` | data_zone | Regel |
| `deployment.landing_zone` | standalone | eure Beschreibung |
| `deployment.network_exposure` | private | eure Beschreibung |
| `deployment.local_auth` | disabled | Regel |
| `deployment.mandates` | [] | eure Beschreibung |
| `deployment.key_protection` | software | Regel |
| `deployment.key_management` | platform_managed | Regel |
| `deployment.network_ownership` | create | eure Beschreibung |
| `deployment.private_dns_ownership` | deployment | erzwungen |
| `deployment.observability_ownership` | create | erzwungen |
| `deployment.diagnostics_destination` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | erzwungen |
| `deployment.log_retention_days` | 30 | Regel |
| `deployment.daily_quota_gb` | -1 | Regel |
| `virtual-network.addressing.dns_servers` | {"development": [], "test": [], "production": []} | Regel |
| `virtual-network.subnet_policy.private_endpoint_network_policies` | Enabled | Regel |
| `virtual-network.subnet_policy.service_endpoints` | [] | Regel |
| `virtual-network.subnet_policy.subnet_delegations` | [{"subnet": "snet-web", "service": "Microsoft.Web/serverFarms"}] | erzwungen |
| `virtual-network.security.ddos_protection` | false | Regel |
| `virtual-network.security.subnets_expecting_nsg` | {"development": ["snet-endpoints", "snet-web"], "test": ["snet-endpoints", "snet-web"], "production": ["snet-endpoints", "snet-web"]} | erzwungen |
| `virtual-network.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `virtual-network.observability.flow_logs_enabled` | false | Regel |
| `network-security-group__endpoints.rules.subnet_purpose` | private_endpoints | eure Beschreibung |
| `network-security-group__endpoints.rules.default_inbound` | deny_all | Regel |
| `network-security-group__endpoints.rules.default_outbound` | deny_internet | erzwungen |
| `network-security-group__endpoints.rules.rules` | {"development": [], "test": [], "production": []} | Regel |
| `network-security-group__endpoints.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `network-security-group__endpoints.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | Regel |
| `network-security-group__integration.rules.subnet_purpose` | app_integration | eure Beschreibung |
| `network-security-group__integration.rules.default_inbound` | deny_all | Regel |
| `network-security-group__integration.rules.default_outbound` | azure_default | Regel |
| `network-security-group__integration.rules.rules` | {"development": [], "test": [], "production": []} | Regel |
| `network-security-group__integration.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `network-security-group__integration.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | Regel |
| `log-analytics-workspace.cost.retention_days` | 30 | übernommen |
| `log-analytics-workspace.cost.daily_quota_gb` | -1 | übernommen |
| `log-analytics-workspace.cost.sku` | PerGB2018 | Regel |
| `log-analytics-workspace.access.public_network_access` | enabled | Regel |
| `log-analytics-workspace.access.local_auth` | false | übernommen |
| `log-analytics-workspace.access.rbac_only_access` | true | Regel |
| `log-analytics-workspace.data_protection.immediate_purge_protection` | true | Regel |
| `log-analytics-workspace.data_protection.archive_to_storage` | false | Regel |
| `application-insights.component.workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `application-insights.component.application_type` | web | Regel |
| `application-insights.component.sampling_percentage` | 100 | Regel |
| `application-insights.component.daily_cap_gb` | 0 | Regel |
| `application-insights.component.store_client_ip` | false | Regel |
| `application-insights.networking.public_network_access` | disabled | übernommen |
| `application-insights.identity.role_assignments` | {"development": [{"principal": "app-service", "role": "Monitoring Metrics Publisher"}], "test": [{"principal": "app-service", "role": "Monitoring Metrics Publisher"}], "production": [{"principal": "app-service", "role": "Monitoring Metrics Publisher"}]} | Platzhalter |
| `application-insights.security.local_authentication_disabled` | true | übernommen |
| `key-vault.vault.sku` | standard | Regel |
| `key-vault.vault.purge_protection` | true | Regel |
| `key-vault.vault.soft_delete_retention_days` | 90 | Regel |
| `key-vault.vault.rbac_authorization` | true | übernommen |
| `key-vault.networking.public_network_access` | disabled | übernommen |
| `key-vault.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `key-vault.networking.network_acl_bypass` | None | Regel |
| `key-vault.security.enabled_for_services` | [] | Regel |
| `key-vault.security.secret_placeholders` | [] | Regel |
| `key-vault.keys.key_management` | platform_managed | übernommen |
| `key-vault.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `key-vault.observability.diagnostic_categories` | ["AuditEvent", "AzurePolicyEvaluationDetails"] | Regel |
| `key-vault.observability.metrics_enabled` | true | Regel |
| `storage-account.networking.public_network_access` | disabled | übernommen |
| `storage-account.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `storage-account.networking.private_endpoint_subresources` | ["blob"] | Regel |
| `storage-account.networking.allow_azure_services_bypass` | true | Regel |
| `storage-account.identity.managed_identity` | system_assigned | Regel |
| `storage-account.identity.role_assignments` | {"development": [{"principal": "search-service", "role": "Storage Blob Data Reader"}], "test": [{"principal": "search-service", "role": "Storage Blob Data Reader"}], "production": [{"principal": "search-service", "role": "Storage Blob Data Reader"}]} | eure Antwort |
| `storage-account.security.shared_access_key_enabled` | false | übernommen |
| `storage-account.security.min_tls_version` | TLS1_2 | Regel |
| `storage-account.security.https_traffic_only` | true | Regel |
| `storage-account.security.allow_blob_public_access` | false | Regel |
| `storage-account.security.infrastructure_encryption_enabled` | true | Regel |
| `storage-account.security.key_management` | platform_managed | übernommen |
| `storage-account.security.sftp_enabled` | false | Regel |
| `storage-account.data_protection.replication` | LRS | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.access_tier` | Hot | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.blob_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.container_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.versioning_enabled` | true | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.change_feed_enabled` | false | Regel |
| `storage-account.data_protection.point_in_time_restore_days` | 0 | Regel |
| `storage-account.data_protection.immutability` | none | Regel |
| `storage-account.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `storage-account.observability.diagnostic_categories` | ["audit"] | Regel |
| `storage-account.observability.metrics_enabled` | true | Regel |
| `foundry.account.kind` | AIServices | Regel |
| `foundry.account.sku_name` | S0 | Regel |
| `foundry.account.project_management` | true | Regel |
| `foundry.account.projects` | [] | Regel |
| `foundry.models.deployment_sku` | DataZoneStandard | abgeleitet aus eurer Antwort |
| `foundry.models.deployment_capacity` | 10 | Regel |
| `foundry.models.version_upgrade_option` | OnceCurrentVersionExpired | Regel |
| `foundry.models.content_filter` | Microsoft.DefaultV2 | Regel |
| `foundry.networking.public_network_access` | disabled | übernommen |
| `foundry.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `foundry.networking.restrict_outbound` | true | Regel |
| `foundry.identity.managed_identity` | system_assigned | Regel |
| `foundry.identity.role_assignments` | {"development": [{"principal": "app-service", "role": "Cognitive Services OpenAI User"}, {"principal": "search-service", "role": "Cognitive Services OpenAI User"}], "test": [{"principal": "app-service", "role": "Cognitive Services OpenAI User"}, {"principal": "search-service", "role": "Cognitive Services OpenAI User"}], "production": [{"principal": "app-service", "role": "Cognitive Services OpenAI User"}, {"principal": "search-service", "role": "Cognitive Services OpenAI User"}]} | eure Beschreibung |
| `foundry.security.local_authentication_disabled` | true | übernommen |
| `foundry.security.key_management` | platform_managed | übernommen |
| `foundry.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `foundry.observability.diagnostic_categories` | ["Audit", "RequestResponse", "AzureOpenAIRequestUsage"] | Regel |
| `foundry.observability.metrics_enabled` | true | Regel |
| `search-service.service.sku` | {"development": "basic", "test": "basic", "production": "standard"} | Regel |
| `search-service.service.replica_count` | 1 | abgeleitet aus eurer Antwort |
| `search-service.service.partition_count` | 1 | Regel |
| `search-service.service.semantic_ranker` | free | Regel |
| `search-service.networking.public_network_access` | disabled | übernommen |
| `search-service.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `search-service.networking.network_rule_bypass` | None | Regel |
| `search-service.identity.managed_identity` | system_assigned | Regel |
| `search-service.identity.role_assignments` | {"development": [{"principal": "app-service", "role": "Search Index Data Reader"}], "test": [{"principal": "app-service", "role": "Search Index Data Reader"}], "production": [{"principal": "app-service", "role": "Search Index Data Reader"}]} | eure Beschreibung |
| `search-service.security.local_authentication_disabled` | true | übernommen |
| `search-service.security.key_management` | platform_managed | übernommen |
| `search-service.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `search-service.observability.diagnostic_categories` | ["OperationLogs"] | Regel |
| `search-service.observability.metrics_enabled` | true | Regel |
| `app-service.hosting.os_type` | Linux | Regel |
| `app-service.hosting.sku` | {"development": "B1", "test": "B1", "production": "P1v3"} | Regel |
| `app-service.hosting.zone_redundant` | false | abgeleitet aus eurer Antwort |
| `app-service.hosting.instance_count` | 1 | abgeleitet aus eurer Antwort |
| `app-service.networking.public_network_access` | disabled | übernommen |
| `app-service.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `app-service.networking.vnet_integration` | true | Regel |
| `app-service.networking.integration_subnet` | {"development": "snet-web", "test": "snet-web", "production": "snet-web"} | erzwungen |
| `app-service.networking.vnet_route_all` | true | Regel |
| `app-service.identity.managed_identity` | system_assigned | Regel |
| `app-service.security.https_only` | true | Regel |
| `app-service.security.min_tls_version` | 1.2 | Regel |
| `app-service.security.ftps_state` | Disabled | Regel |
| `app-service.security.basic_auth_enabled` | false | übernommen |
| `app-service.runtime.always_on` | true | Regel |
| `app-service.runtime.health_check_path` |  | Regel |
| `app-service.runtime.http2_enabled` | true | Regel |
| `app-service.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `app-service.observability.diagnostic_categories` | ["AppServiceHTTPLogs", "AppServiceAppLogs", "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs"] | Regel |
| `app-service.observability.metrics_enabled` | true | Regel |
| `wiring.private_dns_zones` | ["privatelink.blob.core.windows.net", "privatelink.vaultcore.azure.net", "privatelink.cognitiveservices.azure.com", "privatelink.openai.azure.com", "privatelink.services.ai.azure.com", "privatelink.search.windows.net", "privatelink.azurewebsites.net", "privatelink.monitor.azure.com"] | erzwungen |
| `wiring.access` | [{"from": "users", "to": "app-service", "label": "HTTPS 443"}, {"from": "app-service", "to": "foundry"}, {"from": "app-service", "to": "search-service"}, {"from": "search-service", "to": "storage-account", "label": "indexer"}, {"from": "search-service", "to": "foundry", "label": "embeddings"}] | eure Beschreibung |
| `wiring.purposes` | {"app-service": "Chat web app", "foundry": "Chat and embedding models", "search-service": "Retrieval index over the documents", "storage-account": "Source documents", "key-vault": "Secrets of the app", "application-insights": "Application telemetry", "network-security-group__endpoints": "Private endpoints subnet", "network-security-group__integration": "App integration subnet"} | eure Beschreibung |
| `wiring.optional` | [] | Regel |
