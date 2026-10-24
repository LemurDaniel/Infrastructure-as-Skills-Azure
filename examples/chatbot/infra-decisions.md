# Entscheidungen für „chatbot“

Was gebaut wird, entschieden aus euren Antworten und den Regeln hinter den Vorgaben. Jede Zeile ist eine Entscheidung; der Schlüssel im Anhang ist, wo ein Engineer sie in der Spezifikation findet.

Stand 2026-10-23. Spezifikation: `infra-spec.yaml`.

## Das System

- Das System wird in diesen Stufen ausgerollt: Echtbetrieb.
- Alles läuft in der Azure-Region westeurope.
- „chatbot“ ist der Name, den jeder Teil des Systems trägt.
- Jede Stufe liegt in einer eigenen Subscription; die Stufen können sich gegenseitig weder Ressourcen noch Budgets noch Berechtigungen anfassen.

## Was aus euren Antworten folgt

- **Ein Tag Ausfall wäre störend.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure Storage Account (uploads): Die Daten liegen in drei Rechenzentren der Region, eines darf ausfallen.
  - daher, Azure Storage Account (host): Die Daten liegen in drei Rechenzentren der Region, eines darf ausfallen.
  - daher, Azure Cosmos DB account (API for NoSQL): Die Daten überstehen den Ausfall eines Rechenzentrums der Region.
  - daher, Azure AI Search service: 2 Kopien des Index beantworten Anfragen.
  - daher, Azure Container Registry: Die Registry übersteht den Ausfall eines Rechenzentrums der Region.
  - daher, Azure Container Apps (environment and one container app): Die Umgebung übersteht den Ausfall eines Rechenzentrums der Region.
  - daher, Azure Container Apps (environment and one container app): Mindestens 2 Kopien der App laufen immer.
  - daher, Azure Functions (function app on Flex Consumption or Elastic Premium): Die Function App übersteht den Ausfall eines Rechenzentrums der Region.
  - daher, Azure Functions (function app on Flex Consumption or Elastic Premium): 1 Instanz(en) werden vorgewärmt gehalten, damit der erste Aufruf nicht wartet.
  - daher, Azure App Service (web app on an App Service plan) (web): Die App übersteht den Ausfall eines Rechenzentrums der Region.
  - daher, Azure App Service (web app on an App Service plan) (web): 2 Kopien der App laufen gleichzeitig.
  - daher, Azure App Service (web app on an App Service plan) (mcp): Die App übersteht den Ausfall eines Rechenzentrums der Region.
  - daher, Azure App Service (web app on an App Service plan) (mcp): 2 Kopien der App laufen gleichzeitig.
- **Nach einem versehentlichen Löschen müsst ihr eine Woche zurückkommen.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure Storage Account (uploads): Gelöschte Dateien sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account (uploads): Gelöschte Ordner sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account (uploads): Frühere Versionen überschriebener Dateien werden aufgehoben.
  - daher, Azure Storage Account (host): Gelöschte Dateien sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account (host): Gelöschte Ordner sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account (host): Frühere Versionen überschriebener Dateien werden aufgehoben.
  - daher, Azure Cosmos DB account (API for NoSQL): Backups erlauben den Rückgang auf jede Sekunde der letzten sieben Tage.
- **Die Daten werden laufend genutzt.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure Storage Account (uploads): Gespeichert in der Klasse Standard: günstig beim Lesen, für Daten in Nutzung.
  - daher, Azure Storage Account (host): Gespeichert in der Klasse Standard: günstig beim Lesen, für Daten in Nutzung.
- **Gegen absichtliche Zerstörung sind die Daten nur innerhalb des Systems selbst geschützt; wer das System löschen kann, kann auch die Kopien löschen.** _(nicht gesagt, daher gilt die übliche Antwort)_
- **Die Daten werden nur innerhalb des Wirtschaftsraums der Region, zum Beispiel der EU gespeichert und verarbeitet.** _(aus eurer Beschreibung)_
  - daher, Azure AI Foundry (AI Services account with projects and model deployments): Anfragen an die Modelle werden überall innerhalb derselben Datenzone (zum Beispiel der EU) verarbeitet.
- **Der Code wird aus Microsofts geprüften, getesteten Bausteinen (Azure Verified Modules) gebaut.** _(nicht gesagt, daher gilt die übliche Antwort)_
- **Der Zugang ist nur privat, nichts ist aus dem Internet erreichbar.** _(aus eurer Beschreibung)_
- **Einzuhaltende Vorgaben: Datenverarbeitung nur in der EU.** _(aus eurer Beschreibung)_
- **Protokolle werden 30 Tage aufbewahrt.** _(aus eurer Beschreibung)_

## Nach den Vorgaben gesetzt

Nichts davon wurde gefragt; jede Zeile folgt einer Regel oder einer der Antworten oben. Sagt Bescheid, wenn eine nicht passt.

### Für das ganze System

- Nutzungstelemetrie an Microsoft ist eingeschaltet: eine Zählung pro Ausrollen, keine eurer Daten.
- Das System landet in dem internen Teil der Firmenplattform, verbunden mit dem Firmennetz.
- Passwörter und Zugriffsschlüssel sind abgeschaltet; der Zugriff läuft über Firmenkonten, damit jede Aktion zuordenbar ist.
- Verschlüsselungsschlüssel sind in Software geschützt, der Standard, ausreichend ohne Vorgabe für Hardware.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Das Netz wird von diesem Ausrollen selbst gebaut.
- Das neue Netz nutzt den Adressbereich 10.20.0.0/16, zugewiesen von der Adressverwaltung.
- Private Anbindungen bekommen ein eigenes Subnetz, 10.20.0.0/27.
- Die Namensauflösung für private Anbindungen übernimmt die Firmenplattform.
- Die Namenseinträge für private Anbindungen schreibt eine Plattformregel, automatisch.
- Protokolle gehen in einen Arbeitsbereich, den dieses Ausrollen anlegt und bezahlt.
- Protokolle werden in log-analytics-workspace gesammelt. — weil: Protokolle gehen in einen Arbeitsbereich, den dieses Ausrollen anlegt und bezahlt.
- Tägliche Obergrenze für Protokolle: -1 GB (-1: keine).

### Azure Virtual Network

- Das Netz nutzt den Adressbereich 10.20.0.0/16.
- Subnetze: snet-endpoints (10.20.0.0/27), snet-web (10.20.0.64/26), snet-mcp (10.20.0.128/26), snet-func (10.20.0.192/26), snet-aca (10.20.1.0/27).
- Private Anbindungen bekommen das Subnetz 10.20.0.0/27.
- Eigene Namensserver: keine (keine: Azures eigene).
- Netzwerkregeln gelten für private Anbindungen in ihrem Subnetz.
- Abkürzungen zu Azure-Diensten aus den Subnetzen: keine.
- An einen Dienst übergebene Subnetze: snet-web (Microsoft.Web/serverFarms), snet-mcp (Microsoft.Web/serverFarms), snet-func (Microsoft.App/environments), snet-aca (Microsoft.App/environments). — weil: `resources.app-service__web.networking.integration_subnet`
- Ein kostenpflichtiger DDoS-Schutzplan wird nicht genutzt; Azures Basisschutz gilt ohnehin.
- Subnetze, die eine Sicherheitsgruppe bekommen: snet-endpoints, snet-web, snet-mcp, snet-func, snet-aca.
- Netzwerkprotokolle gehen in log-analytics-workspace.
- Eine Aufzeichnung erlaubten und abgewiesenen Verkehrs wird nicht geführt.

### Azure Network Security Group (endpoints)

- Die Gruppe schützt ein Subnetz für private Anbindungen an Azure-Dienste.
- Eingehender Verkehr, den keine Regel erlaubt, wird abgelehnt, auch von anderen Maschinen im selben Netz.
- Ausgehender Verkehr ins Internet, den keine Regel erlaubt, wird abgelehnt; was hinaus muss, läuft über die Firmen-Firewall. — weil: `resources.network-security-group__endpoints.rules.subnet_purpose`
- Ausdrücklich erlaubter Verkehr: keine.
- Seine Protokolle gehen in log-analytics-workspace.
- Protokolliert wird: welche Regel auf welche Maschine angewendet wurde, wie oft jede Regel gegriffen hat.

### Azure Network Security Group (integration)

- Die Gruppe schützt ein Subnetz für den ausgehenden Verkehr von Web- und Function-Apps.
- Eingehender Verkehr, den keine Regel erlaubt, wird abgelehnt, auch von anderen Maschinen im selben Netz.
- Ausgehender Verkehr ins Internet, den keine Regel erlaubt, wird den eingebauten Azure-Regeln überlassen, die ihn hinauslassen.
- Ausdrücklich erlaubter Verkehr: keine.
- Seine Protokolle gehen in log-analytics-workspace.
- Protokolliert wird: welche Regel auf welche Maschine angewendet wurde, wie oft jede Regel gegriffen hat.

### Azure Network Security Group (containerapps)

- Die Gruppe schützt ein Subnetz für die Infrastruktur einer Container-Umgebung.
- Eingehender Verkehr, den keine Regel erlaubt, wird abgelehnt, auch von anderen Maschinen im selben Netz.
- Ausgehender Verkehr ins Internet, den keine Regel erlaubt, wird den eingebauten Azure-Regeln überlassen, die ihn hinauslassen.
- Ausdrücklich erlaubter Verkehr: keine.
- Seine Protokolle gehen in log-analytics-workspace.
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

- Seine Telemetrie wird in log-analytics-workspace gespeichert.
- Die Komponente ist eingerichtet für eine Webanwendung oder einen Dienst.
- 100 Prozent der Telemetrie werden behalten.
- Tägliche Obergrenze für die Telemetrie dieser Komponente: 0 GB (0: keine).
- IP-Adressen von Besuchern werden maskiert und nicht gespeichert.
- Die Komponente ist nur über die private Überwachungsanbindung erreichbar, zum Senden und zum Lesen.
- Zugriffsrechte auf die Komponente vergeben an: user-assigned-identity__connector (Monitoring Metrics Publisher).
- Das Senden von Telemetrie nur mit einem Schlüssel ist abgeschaltet; Anwendungen melden sich mit Firmenidentitäten an.

### Azure Key Vault

- Der Tresor ist die Stufe Standard, Schlüssel in Software geschützt.
- Ein gelöschter Tresor oder ein gelöschtes Geheimnis lässt sich nicht endgültig löschen, auch nicht von einem Administrator, bevor die Aufbewahrungszeit endet.
- Gelöschte Inhalte des Tresors lassen sich 90 Tage lang wiederherstellen.
- Der Zugriff auf den Inhalt des Tresors wird über Rollenzuweisungen, wie alles andere in Azure gesteuert.
- Der Tresor ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Vertrauenswürdige Azure-Dienste dürfen nicht an der Firewall des Tresors vorbei.
- Zugriffsrechte auf den Tresor vergeben an: user-assigned-identity__web (Key Vault Secrets User), user-assigned-identity__connector (Key Vault Secrets User).
- Plattformdienste, die aus dem Tresor lesen dürfen: keine (leer: keine).
- Für die Geheimnisse entra-client-secret werden leere Plätze angelegt; die Werte werden danach von Hand oder von der Anwendung eingetragen.
- Verschlüsselungsschlüssel sind von Azure verwaltet - der Tresor hält dafür keine.
- Seine Protokolle gehen in log-analytics-workspace.
- Protokolliert wird: jeder Lese-, Schreib- und fehlgeschlagene Zugriff auf den Tresor, wie Richtlinien den Tresor bewertet haben.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure user-assigned managed identity (web)

- Diese Identität gibt es für the web app and the MCP server, to reach models, search, data and secrets.
- Externe Systeme, die als diese Identität handeln dürfen: keine (leer: keine).
- Die Identität kann von Ressourcen in jeder Region aus genutzt werden.
- Rechte an der Identität selbst vergeben an: keine.

### Azure user-assigned managed identity (connector)

- Diese Identität gibt es für the document connector function, to index documents and keep its own state.
- Externe Systeme, die als diese Identität handeln dürfen: keine (leer: keine).
- Die Identität kann von Ressourcen in jeder Region aus genutzt werden.
- Rechte an der Identität selbst vergeben an: keine.

### Azure user-assigned managed identity (runner)

- Diese Identität gibt es für the code interpreter container app, to pull its image.
- Externe Systeme, die als diese Identität handeln dürfen: keine (leer: keine).
- Die Identität kann von Ressourcen in jeder Region aus genutzt werden.
- Rechte an der Identität selbst vergeben an: keine.

### Azure Storage Account (uploads)

- Der Speicher ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Private Anbindungen gibt es für: Dateien (Blob).
- Azures eigene Dienste (Backup, Überwachung) dürfen am Firewall vorbei auf den Speicher zugreifen.
- Der Speicher hat eine eigene Identität, um andere Dienste zu erreichen.
- Zugriffsrechte vergeben an: user-assigned-identity__web (Storage Blob Data Contributor), search-service (Storage Blob Data Reader).
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
- Seine Protokolle gehen in log-analytics-workspace.
- Protokolliert wird: wer worauf zugegriffen hat.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Storage Account (host)

- Der Speicher ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Private Anbindungen gibt es für: Dateien (Blob), Warteschlangen, Tabellen. — weil: `resources.function-app.storage.host_storage_account`
- Azures eigene Dienste (Backup, Überwachung) dürfen am Firewall vorbei auf den Speicher zugreifen.
- Der Speicher hat eine eigene Identität, um andere Dienste zu erreichen.
- Zugriffsrechte vergeben an: user-assigned-identity__connector (Storage Blob Data Owner), user-assigned-identity__connector (Storage Table Data Contributor), user-assigned-identity__connector (Storage Queue Data Contributor).
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
- Seine Protokolle gehen in log-analytics-workspace.
- Protokolliert wird: wer worauf zugegriffen hat.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Cosmos DB account (API for NoSQL)

- Die Kapazität ist vorab reserviert und stundenweise berechnet, mit garantierter Rate.
- Der Durchsatz folgt der Last zwischen einem Zehntel der Obergrenze und der Obergrenze.
- Der Durchsatz ist auf 1000 Anfrageeinheiten pro Sekunde je Container begrenzt.
- Das gesamte Konto darf höchstens -1 Anfrageeinheiten pro Sekunde nutzen (-1: keine Grenze).
- Das monatliche Freikontingent an Durchsatz und Speicher ist nicht genutzt.
- Die Daten liegen zusätzlich in keine (leer: nur in der Hauptregion).
- Fällt die Hauptregion aus, wechselt das Konto.
- Eine Leseanfrage sieht die eigenen Schreibvorgänge sofort, bei anderen einen leicht älteren Stand.
- Das Konto ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Vertrauenswürdige Azure-Dienste dürfen nicht an der Firewall des Kontos vorbei.
- Das Konto hat keine eigene Identität.
- Zugriff auf die Daten selbst vergeben an: user-assigned-identity__web (Cosmos DB Built-in Data Contributor).
- Verwaltungsrechte am Konto vergeben an: keine.
- Die Anmeldung mit Kontoschlüsseln ist abgeschaltet; der Zugriff läuft über Firmenkonten.
- Das Anlegen oder Ändern von Datenbanken, Containern und Durchsatz mit Kontoschlüsseln ist abgeschaltet.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Ein Spaltenspeicher für Analysen neben den Daten ist nicht vorhanden.
- Das Konto enthält die Datenbanken und Container chatbot containers [{'name': 'conversations', 'partition_key_paths': ['/userId']}].
- Seine Protokolle gehen in log-analytics-workspace.
- Protokolliert wird: jede Änderung am Konto, an Datenbanken und Containern, jede Anfrage an die Daten mit Kosten und Ergebnis.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure AI Foundry (AI Services account with projects and model deployments)

- Das Konto ist eine AI-Foundry-Ressource, die auch Projekte, Agenten und die weiteren KI-Dienste bietet.
- Das Konto nutzt die Preisstufe S0, die bezahlte Standardstufe.
- Das Konto enthält Foundry-Projekte als Behälter für Zugriff, Daten und Kosten.
- Das Konto enthält die Projekte chatbot.
- Das Konto stellt die Modelle chat format OpenAI, model gpt-4.1, version 2025-04-14, embeddings format OpenAI, model text-embedding-3-large, version 1 bereit.
- Jedes Modell darf bis zu 10 Tausend Token pro Minute verarbeiten.
- Läuft die Modellversion aus, wechselt sie an diesem Tag auf die neue Standardversion.
- Anfragen und Antworten werden vom Inhaltsfilter Microsoft.DefaultV2 geprüft.
- Das Konto ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Das Konto darf nur Adressen aufrufen, die ausdrücklich erlaubt sind.
- Das Konto hat eine eigene Identität.
- Zugriffsrechte auf das Konto vergeben an: user-assigned-identity__web (Cognitive Services OpenAI User), user-assigned-identity__connector (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User).
- Die Anmeldung mit Kontoschlüsseln ist abgeschaltet; der Zugriff läuft über Firmenkonten.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Seine Protokolle gehen in log-analytics-workspace.
- Protokolliert wird: Änderungen am Konto und wer sie gemacht hat, jede Anfrage an die Modelle mit Aufrufer, Größe und Ergebnis (nicht der Text), die von jedem Aufruf verbrauchten Token.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure AI Search service

- Der Suchdienst hat die Stufe Standard, die übliche Produktionsstufe.
- Die Indexdaten sind auf 1 Partition(en) verteilt.
- Die Neubewertung der Ergebnisse nach Bedeutung ist an, im Rahmen eines kleinen kostenlosen Monatskontingents.
- Der Suchdienst ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Vertrauenswürdige Azure-Dienste dürfen nicht an der Firewall des Suchdienstes vorbei.
- Der Suchdienst hat eine eigene Identität.
- Zugriffsrechte auf den Suchdienst vergeben an: user-assigned-identity__web (Search Index Data Reader), user-assigned-identity__connector (Search Index Data Contributor).
- Die Anmeldung mit API-Schlüsseln ist abgeschaltet; der Zugriff läuft über Firmenkonten.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Seine Protokolle gehen in log-analytics-workspace.
- Protokolliert wird: jede Abfrage und jede Änderung an Indizes und Indexern.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Container Registry

- Die Registry hat die Stufe Premium, die als einzige per privater Anbindung abgeschottet und auf mehrere Regionen verteilt werden kann. — weil: Der Zugang ist nur privat, nichts ist aus dem Internet erreichbar.
- Die Images liegen zusätzlich in keine (leer: nur in der Hauptregion).
- Images ohne Tag werden nach 7 Tagen gelöscht.
- Die Registry ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Vertrauenswürdige Azure-Dienste dürfen nicht an der Firewall der Registry vorbei.
- Das Herauskopieren von Images aus der Registry ist gesperrt.
- Die Registry hat keine eigene Identität.
- Zugriffsrechte auf die Registry vergeben an: user-assigned-identity__runner (AcrPull).
- Das gemeinsame Admin-Konto ist abgeschaltet; der Zugriff läuft über Firmenkonten.
- Das Herunterladen von Images ohne Anmeldung ist nicht erlaubt.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Seine Protokolle gehen in log-analytics-workspace.
- Protokolliert wird: jedes Hochladen, Herunterladen und Löschen eines Images, jede Anmeldung an der Registry.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Container Apps (environment and one container app)

- Die App läuft auf geteilter Kapazität, nach Nutzung abgerechnet und bis auf null skalierbar.
- Die Umgebung ist nur aus dem Firmennetz erreichbar, über einen internen Lastverteiler.
- Die Infrastruktur der Umgebung liegt im Subnetz snet-aca. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Die Umgebung ist für jeden öffentlichen Verkehr gesperrt.
- Der Verkehr zwischen den Apps innerhalb der Umgebung wird verschlüsselt.
- Die App führt das Container-Image container-registry/code-runner:1.0.0 aus.
- Jede Kopie der App bekommt einen halben Kern und ein Gigabyte.
- Die App darf auf höchstens 10 Kopien skalieren.
- Nur die neueste Version der App läuft; eine neue ersetzt sie.
- Die App ist nur von anderen Apps ihrer Umgebung aufrufbar.
- Die App lauscht auf Port 8080.
- Unverschlüsselte Verbindungen zur App werden auf die verschlüsselte Adresse umgeleitet.
- Die App hat eine gemeinsame, separat verwaltete Identität, um andere Dienste zu erreichen.
- Es nutzt die Identität user-assigned-identity__runner.
- Die App liest die Geheimnisse keine aus dem Schlüsseltresor.
- Verwaltungsrechte an der App vergeben an: keine.
- Seine Protokolle gehen in log-analytics-workspace.
- Protokolliert wird: was die App auf ihre Konsole schreibt, die eigenen Meldungen der Plattform zur App und ihren Revisionen.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Functions (function app on Flex Consumption or Elastic Premium)

- Die Function App läuft auf Kapazität, die von null aus skaliert und nach Nutzung abgerechnet wird, mit privatem Netz und optional vorgewärmten Instanzen.
- Die Function App ist geschrieben für Python.
- Laufzeit-Version 3.12.
- Die Function App darf auf höchstens 20 Instanzen skalieren.
- Jede Instanz bekommt 2048 MB Arbeitsspeicher.
- Die Function App hält ihren eigenen Zustand im Speicherkonto storage-account__host.
- Die Function App meldet sich an ihrem Speicher an mit ihrer verwalteten Identität, ohne gespeichertes Geheimnis.
- Der ausgerollte Code liegt im Container app-package.
- Die Function App ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Der ausgehende Verkehr der Function App läuft durch das Firmennetz, so erreicht sie private Dienste.
- Ausgehender Verkehr verlässt das Netz über das Subnetz snet-func. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Ausgehender Verkehr wird komplett durch das Firmennetz geleitet, auch ins Internet geleitet.
- Die Function App hat eine gemeinsame, separat verwaltete Identität, um andere Dienste zu erreichen.
- Es nutzt die Identität user-assigned-identity__connector.
- Verwaltungsrechte an der Function App vergeben an: keine.
- Unverschlüsselte Verbindungen werden auf die verschlüsselte Adresse umgeleitet.
- Verbindungen müssen mindestens TLS 1.2-Verschlüsselung nutzen.
- Das Ausrollen mit Benutzername und Passwort ist nicht möglich; Rollouts laufen über Firmenkonten.
- Seine Anwendungstelemetrie geht an application-insights (leer: keine).
- Seine Protokolle gehen in log-analytics-workspace.
- Protokolliert wird: was die Funktionen in ihr Protokoll schreiben, wer sich zum Ausrollen oder Verwalten angemeldet hat.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure App Service (web app on an App Service plan) (web)

- Die App läuft auf Linux.
- Der Hosting-Plan hat die Größe P1v3, Premium, die übliche Produktionsgröße.
- Die App ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Der ausgehende Verkehr der App läuft durch das Firmennetz, so erreicht sie private Dienste.
- Ausgehender Verkehr verlässt das Netz über das Subnetz snet-web. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Ausgehender Verkehr wird komplett durch das Firmennetz geleitet, auch ins Internet geleitet.
- Die App hat eine gemeinsame, separat verwaltete Identität, um andere Dienste zu erreichen.
- Sie nutzt die Identitäten user-assigned-identity__web.
- Unverschlüsselte Verbindungen werden auf die verschlüsselte Adresse umgeleitet.
- Verbindungen müssen mindestens TLS 1.2-Verschlüsselung nutzen.
- Dateiupload per FTP ist abgeschaltet.
- Das Ausrollen mit Benutzername und Passwort ist nicht möglich; Rollouts laufen über Firmenkonten.
- Die App ist geschrieben für Python.
- Laufzeit-Version 3.12.
- Die App bleibt geladen und antwortet sofort auf die erste Anfrage, wenn kein Verkehr anliegt.
- Die Plattform prüft die Gesundheit der App unter dem Pfad  (leer: keine Prüfung).
- HTTP/2 ist eingeschaltet.
- Seine Protokolle gehen in log-analytics-workspace.
- Protokolliert wird: jede Web-Anfrage, die eigenen Log-Meldungen der App, wer sich zum Ausrollen oder Verwalten angemeldet hat, Änderungen an den Zugriffsbeschränkungen, die eigenen Meldungen der Plattform zur App.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure App Service (web app on an App Service plan) (mcp)

- Die App läuft auf Linux.
- Der Hosting-Plan hat die Größe P1v3, Premium, die übliche Produktionsgröße.
- Die App ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Der ausgehende Verkehr der App läuft durch das Firmennetz, so erreicht sie private Dienste.
- Ausgehender Verkehr verlässt das Netz über das Subnetz snet-mcp. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Ausgehender Verkehr wird komplett durch das Firmennetz geleitet, auch ins Internet geleitet.
- Die App hat eine gemeinsame, separat verwaltete Identität, um andere Dienste zu erreichen.
- Sie nutzt die Identitäten user-assigned-identity__web.
- Unverschlüsselte Verbindungen werden auf die verschlüsselte Adresse umgeleitet.
- Verbindungen müssen mindestens TLS 1.2-Verschlüsselung nutzen.
- Dateiupload per FTP ist abgeschaltet.
- Das Ausrollen mit Benutzername und Passwort ist nicht möglich; Rollouts laufen über Firmenkonten.
- Die App ist geschrieben für Node.js.
- Laufzeit-Version 22-lts.
- Die App bleibt geladen und antwortet sofort auf die erste Anfrage, wenn kein Verkehr anliegt.
- Die Plattform prüft die Gesundheit der App unter dem Pfad  (leer: keine Prüfung).
- HTTP/2 ist eingeschaltet.
- Seine Protokolle gehen in log-analytics-workspace.
- Protokolliert wird: jede Web-Anfrage, die eigenen Log-Meldungen der App, wer sich zum Ausrollen oder Verwalten angemeldet hat, Änderungen an den Zugriffsbeschränkungen, die eigenen Meldungen der Plattform zur App.
- Nutzungs- und Leistungswerte werden erfasst.

## Noch offen

Solange diese Punkte offen sind, wird nichts ausgerollt.

- Which private monitoring connection should the component belong to? _(gebraucht von: platform team)_ — blockiert: apply
- Where does the code live, and which system deploys it? The request names none, so no pipeline is rendered. _(gebraucht von: workload owner)_ — blockiert: apply
- Which tag set does the organisation apply? Nothing in the request, no repository to read it from. _(gebraucht von: workload owner)_ — blockiert: apply
- The Entra app registration and its client secret. A directory object, not an Azure resource - the identity team creates it; the secret goes into the key vault placeholder `entra-client-secret`. _(gebraucht von: identity team)_ — blockiert: apply
- The search service indexes the uploads over a shared private link, approved on the storage account. Not rendered: wiring between two resources that no question set owns. _(gebraucht von: workload owner)_ — blockiert: apply
- Is there quota for gpt-4.1 and text-embedding-3-large as DataZoneStandard in West Europe, for 10,000 tokens per minute each? Not checked; a deployment beyond the quota fails at apply. _(gebraucht von: workload owner)_ — blockiert: apply
- Is code-runner:1.0.0 pushed to the registry? The first revision pulls it while it is created, so the registry has to hold it before the app does. _(gebraucht von: workload owner)_ — blockiert: apply

## Anhang: alle Entscheidungen

| Schlüssel | Wert | Quelle |
|---|---|---|
| `deployment.naming_convention` | default | Regel |
| `deployment.module_source` | avm | Regel |
| `deployment.module_telemetry` | enabled | Regel |
| `deployment.stage_isolation` | subscription | Regel |
| `deployment.non_production_savings` | enabled | Regel |
| `deployment.outage_impact` | disruptive | Regel |
| `deployment.data_loss_tolerance` | one_week | Regel |
| `deployment.data_access_pattern` | active | Regel |
| `deployment.backup_isolation` | operational | Regel |
| `deployment.data_residency` | data_zone | eure Beschreibung |
| `deployment.landing_zone` | corp | eure Beschreibung |
| `deployment.network_exposure` | private | eure Beschreibung |
| `deployment.local_auth` | disabled | Regel |
| `deployment.mandates` | ["Datenverarbeitung nur in der EU"] | eure Beschreibung |
| `deployment.key_protection` | software | Regel |
| `deployment.key_management` | platform_managed | Regel |
| `deployment.network_ownership` | create | eure Beschreibung |
| `deployment.address_space` | {"production": "10.20.0.0/16"} | eure Beschreibung |
| `deployment.private_endpoint_subnet_prefix` | {"production": "10.20.0.0/27"} | eure Beschreibung |
| `deployment.private_dns_ownership` | platform | Regel |
| `deployment.private_dns_records` | policy | Regel |
| `deployment.observability_ownership` | create | eure Beschreibung |
| `deployment.diagnostics_destination` | {"production": "log-analytics-workspace"} | erzwungen |
| `deployment.log_retention_days` | 30 | eure Beschreibung |
| `deployment.daily_quota_gb` | -1 | Regel |
| `virtual-network.addressing.address_space` | {"production": "10.20.0.0/16"} | übernommen |
| `virtual-network.addressing.subnets` | {"production": [{"name": "snet-endpoints", "prefix": "10.20.0.0/27"}, {"name": "snet-web", "prefix": "10.20.0.64/26"}, {"name": "snet-mcp", "prefix": "10.20.0.128/26"}, {"name": "snet-func", "prefix": "10.20.0.192/26"}, {"name": "snet-aca", "prefix": "10.20.1.0/27"}]} | eure Beschreibung |
| `virtual-network.addressing.private_endpoint_subnet_prefix` | {"production": "10.20.0.0/27"} | übernommen |
| `virtual-network.addressing.dns_servers` | {"production": []} | Regel |
| `virtual-network.subnet_policy.private_endpoint_network_policies` | Enabled | Regel |
| `virtual-network.subnet_policy.service_endpoints` | [] | Regel |
| `virtual-network.subnet_policy.subnet_delegations` | [{"subnet": "snet-web", "service": "Microsoft.Web/serverFarms"}, {"subnet": "snet-mcp", "service": "Microsoft.Web/serverFarms"}, {"subnet": "snet-func", "service": "Microsoft.App/environments"}, {"subnet": "snet-aca", "service": "Microsoft.App/environments"}] | erzwungen |
| `virtual-network.security.ddos_protection` | false | Regel |
| `virtual-network.security.subnets_expecting_nsg` | {"production": ["snet-endpoints", "snet-web", "snet-mcp", "snet-func", "snet-aca"]} | eure Beschreibung |
| `virtual-network.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `virtual-network.observability.flow_logs_enabled` | false | Regel |
| `network-security-group__endpoints.rules.subnet_purpose` | private_endpoints | eure Beschreibung |
| `network-security-group__endpoints.rules.default_inbound` | deny_all | Regel |
| `network-security-group__endpoints.rules.default_outbound` | deny_internet | erzwungen |
| `network-security-group__endpoints.rules.rules` | {"production": []} | Regel |
| `network-security-group__endpoints.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `network-security-group__endpoints.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | Regel |
| `network-security-group__integration.rules.subnet_purpose` | app_integration | eure Beschreibung |
| `network-security-group__integration.rules.default_inbound` | deny_all | Regel |
| `network-security-group__integration.rules.default_outbound` | azure_default | Regel |
| `network-security-group__integration.rules.rules` | {"production": []} | Regel |
| `network-security-group__integration.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `network-security-group__integration.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | Regel |
| `network-security-group__containerapps.rules.subnet_purpose` | container_apps | eure Beschreibung |
| `network-security-group__containerapps.rules.default_inbound` | deny_all | Regel |
| `network-security-group__containerapps.rules.default_outbound` | azure_default | Regel |
| `network-security-group__containerapps.rules.rules` | {"production": []} | Regel |
| `network-security-group__containerapps.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `network-security-group__containerapps.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | Regel |
| `log-analytics-workspace.cost.retention_days` | 30 | übernommen |
| `log-analytics-workspace.cost.daily_quota_gb` | -1 | übernommen |
| `log-analytics-workspace.cost.sku` | PerGB2018 | Regel |
| `log-analytics-workspace.access.public_network_access` | enabled | Regel |
| `log-analytics-workspace.access.local_auth` | false | übernommen |
| `log-analytics-workspace.access.rbac_only_access` | true | Regel |
| `log-analytics-workspace.data_protection.immediate_purge_protection` | true | Regel |
| `log-analytics-workspace.data_protection.archive_to_storage` | false | Regel |
| `application-insights.component.workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `application-insights.component.application_type` | web | Regel |
| `application-insights.component.sampling_percentage` | 100 | Regel |
| `application-insights.component.daily_cap_gb` | 0 | Regel |
| `application-insights.component.store_client_ip` | false | Regel |
| `application-insights.networking.public_network_access` | disabled | übernommen |
| `application-insights.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__connector", "role": "Monitoring Metrics Publisher"}]} | eure Beschreibung |
| `application-insights.security.local_authentication_disabled` | true | übernommen |
| `key-vault.vault.sku` | standard | Regel |
| `key-vault.vault.purge_protection` | true | Regel |
| `key-vault.vault.soft_delete_retention_days` | 90 | Regel |
| `key-vault.vault.rbac_authorization` | true | übernommen |
| `key-vault.networking.public_network_access` | disabled | übernommen |
| `key-vault.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | erzwungen |
| `key-vault.networking.network_acl_bypass` | None | Regel |
| `key-vault.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__web", "role": "Key Vault Secrets User"}, {"principal": "user-assigned-identity__connector", "role": "Key Vault Secrets User"}]} | eure Beschreibung |
| `key-vault.security.enabled_for_services` | [] | Regel |
| `key-vault.security.secret_placeholders` | ["entra-client-secret"] | eure Beschreibung |
| `key-vault.keys.key_management` | platform_managed | übernommen |
| `key-vault.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `key-vault.observability.diagnostic_categories` | ["AuditEvent", "AzurePolicyEvaluationDetails"] | Regel |
| `key-vault.observability.metrics_enabled` | true | Regel |
| `user-assigned-identity__web.identity.purpose` | the web app and the MCP server, to reach models, search, data and secrets | eure Beschreibung |
| `user-assigned-identity__web.identity.federated_credentials` | [] | Regel |
| `user-assigned-identity__web.identity.isolation_scope` | None | Regel |
| `user-assigned-identity__web.identity.role_assignments` | {"production": []} | Regel |
| `user-assigned-identity__connector.identity.purpose` | the document connector function, to index documents and keep its own state | eure Beschreibung |
| `user-assigned-identity__connector.identity.federated_credentials` | [] | Regel |
| `user-assigned-identity__connector.identity.isolation_scope` | None | Regel |
| `user-assigned-identity__connector.identity.role_assignments` | {"production": []} | Regel |
| `user-assigned-identity__runner.identity.purpose` | the code interpreter container app, to pull its image | eure Beschreibung |
| `user-assigned-identity__runner.identity.federated_credentials` | [] | Regel |
| `user-assigned-identity__runner.identity.isolation_scope` | None | Regel |
| `user-assigned-identity__runner.identity.role_assignments` | {"production": []} | Regel |
| `storage-account__uploads.networking.public_network_access` | disabled | übernommen |
| `storage-account__uploads.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | erzwungen |
| `storage-account__uploads.networking.private_endpoint_subresources` | ["blob"] | Regel |
| `storage-account__uploads.networking.allow_azure_services_bypass` | true | Regel |
| `storage-account__uploads.identity.managed_identity` | system_assigned | Regel |
| `storage-account__uploads.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__web", "role": "Storage Blob Data Contributor"}, {"principal": "search-service", "role": "Storage Blob Data Reader"}]} | eure Beschreibung |
| `storage-account__uploads.security.shared_access_key_enabled` | false | übernommen |
| `storage-account__uploads.security.min_tls_version` | TLS1_2 | Regel |
| `storage-account__uploads.security.https_traffic_only` | true | Regel |
| `storage-account__uploads.security.allow_blob_public_access` | false | Regel |
| `storage-account__uploads.security.infrastructure_encryption_enabled` | true | Regel |
| `storage-account__uploads.security.key_management` | platform_managed | übernommen |
| `storage-account__uploads.security.sftp_enabled` | false | Regel |
| `storage-account__uploads.data_protection.replication` | ZRS | abgeleitet aus eurer Antwort |
| `storage-account__uploads.data_protection.access_tier` | Hot | abgeleitet aus eurer Antwort |
| `storage-account__uploads.data_protection.blob_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account__uploads.data_protection.container_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account__uploads.data_protection.versioning_enabled` | true | abgeleitet aus eurer Antwort |
| `storage-account__uploads.data_protection.change_feed_enabled` | false | Regel |
| `storage-account__uploads.data_protection.point_in_time_restore_days` | 0 | Regel |
| `storage-account__uploads.data_protection.immutability` | none | Regel |
| `storage-account__uploads.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `storage-account__uploads.observability.diagnostic_categories` | ["audit"] | Regel |
| `storage-account__uploads.observability.metrics_enabled` | true | Regel |
| `storage-account__host.networking.public_network_access` | disabled | übernommen |
| `storage-account__host.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | erzwungen |
| `storage-account__host.networking.private_endpoint_subresources` | ["blob", "queue", "table"] | erzwungen |
| `storage-account__host.networking.allow_azure_services_bypass` | true | Regel |
| `storage-account__host.identity.managed_identity` | system_assigned | Regel |
| `storage-account__host.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__connector", "role": "Storage Blob Data Owner"}, {"principal": "user-assigned-identity__connector", "role": "Storage Table Data Contributor"}, {"principal": "user-assigned-identity__connector", "role": "Storage Queue Data Contributor"}]} | eure Beschreibung |
| `storage-account__host.security.shared_access_key_enabled` | false | übernommen |
| `storage-account__host.security.min_tls_version` | TLS1_2 | Regel |
| `storage-account__host.security.https_traffic_only` | true | Regel |
| `storage-account__host.security.allow_blob_public_access` | false | Regel |
| `storage-account__host.security.infrastructure_encryption_enabled` | true | Regel |
| `storage-account__host.security.key_management` | platform_managed | übernommen |
| `storage-account__host.security.sftp_enabled` | false | Regel |
| `storage-account__host.data_protection.replication` | ZRS | abgeleitet aus eurer Antwort |
| `storage-account__host.data_protection.access_tier` | Hot | abgeleitet aus eurer Antwort |
| `storage-account__host.data_protection.blob_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account__host.data_protection.container_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account__host.data_protection.versioning_enabled` | true | abgeleitet aus eurer Antwort |
| `storage-account__host.data_protection.change_feed_enabled` | false | Regel |
| `storage-account__host.data_protection.point_in_time_restore_days` | 0 | Regel |
| `storage-account__host.data_protection.immutability` | none | Regel |
| `storage-account__host.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `storage-account__host.observability.diagnostic_categories` | ["audit"] | Regel |
| `storage-account__host.observability.metrics_enabled` | true | Regel |
| `cosmos-db.account.capacity_mode` | provisioned | Regel |
| `cosmos-db.account.throughput_mode` | autoscale | Regel |
| `cosmos-db.account.max_throughput` | 1000 | Regel |
| `cosmos-db.account.total_throughput_limit` | -1 | Regel |
| `cosmos-db.account.free_tier` | false | Regel |
| `cosmos-db.resilience.zone_redundant` | true | abgeleitet aus eurer Antwort |
| `cosmos-db.resilience.geo_replicas` | {"production": []} | Regel |
| `cosmos-db.resilience.automatic_failover` | true | Regel |
| `cosmos-db.resilience.consistency_level` | Session | Regel |
| `cosmos-db.networking.public_network_access` | disabled | übernommen |
| `cosmos-db.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | erzwungen |
| `cosmos-db.networking.network_acl_bypass` | false | Regel |
| `cosmos-db.identity.managed_identity` | none | Regel |
| `cosmos-db.identity.data_plane_role_assignments` | {"production": [{"principal": "user-assigned-identity__web", "role": "Cosmos DB Built-in Data Contributor", "scope": "account"}]} | eure Beschreibung |
| `cosmos-db.identity.role_assignments` | {"production": []} | Regel |
| `cosmos-db.security.local_authentication_disabled` | true | übernommen |
| `cosmos-db.security.key_based_metadata_writes` | true | übernommen |
| `cosmos-db.security.key_management` | platform_managed | übernommen |
| `cosmos-db.data_protection.backup_policy` | continuous_7_days | abgeleitet aus eurer Antwort |
| `cosmos-db.data_protection.analytical_storage` | false | Regel |
| `cosmos-db.containers.databases` | [{"name": "chatbot", "containers": [{"name": "conversations", "partition_key_paths": ["/userId"]}]}] | eure Beschreibung |
| `cosmos-db.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `cosmos-db.observability.diagnostic_categories` | ["ControlPlaneRequests", "DataPlaneRequests"] | Regel |
| `cosmos-db.observability.metrics_enabled` | true | Regel |
| `foundry.account.kind` | AIServices | Regel |
| `foundry.account.sku_name` | S0 | Regel |
| `foundry.account.project_management` | true | Regel |
| `foundry.account.projects` | ["chatbot"] | eure Beschreibung |
| `foundry.models.model_deployments` | [{"name": "chat", "format": "OpenAI", "model": "gpt-4.1", "version": "2025-04-14"}, {"name": "embeddings", "format": "OpenAI", "model": "text-embedding-3-large", "version": "1"}] | eure Beschreibung |
| `foundry.models.deployment_sku` | DataZoneStandard | abgeleitet aus eurer Antwort |
| `foundry.models.deployment_capacity` | 10 | Regel |
| `foundry.models.version_upgrade_option` | OnceCurrentVersionExpired | Regel |
| `foundry.models.content_filter` | Microsoft.DefaultV2 | Regel |
| `foundry.networking.public_network_access` | disabled | übernommen |
| `foundry.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | erzwungen |
| `foundry.networking.restrict_outbound` | true | Regel |
| `foundry.identity.managed_identity` | system_assigned | Regel |
| `foundry.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__web", "role": "Cognitive Services OpenAI User"}, {"principal": "user-assigned-identity__connector", "role": "Cognitive Services OpenAI User"}, {"principal": "search-service", "role": "Cognitive Services OpenAI User"}]} | eure Beschreibung |
| `foundry.security.local_authentication_disabled` | true | übernommen |
| `foundry.security.key_management` | platform_managed | übernommen |
| `foundry.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `foundry.observability.diagnostic_categories` | ["Audit", "RequestResponse", "AzureOpenAIRequestUsage"] | Regel |
| `foundry.observability.metrics_enabled` | true | Regel |
| `search-service.service.sku` | standard | Regel |
| `search-service.service.replica_count` | 2 | abgeleitet aus eurer Antwort |
| `search-service.service.partition_count` | 1 | Regel |
| `search-service.service.semantic_ranker` | free | Regel |
| `search-service.networking.public_network_access` | disabled | übernommen |
| `search-service.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | erzwungen |
| `search-service.networking.network_rule_bypass` | None | Regel |
| `search-service.identity.managed_identity` | system_assigned | Regel |
| `search-service.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__web", "role": "Search Index Data Reader"}, {"principal": "user-assigned-identity__connector", "role": "Search Index Data Contributor"}]} | eure Beschreibung |
| `search-service.security.local_authentication_disabled` | true | übernommen |
| `search-service.security.key_management` | platform_managed | übernommen |
| `search-service.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `search-service.observability.diagnostic_categories` | ["OperationLogs"] | Regel |
| `search-service.observability.metrics_enabled` | true | Regel |
| `container-registry.registry.sku` | Premium | erzwungen |
| `container-registry.registry.zone_redundant` | true | abgeleitet aus eurer Antwort |
| `container-registry.registry.geo_replicas` | {"production": []} | Regel |
| `container-registry.registry.retention_untagged_days` | 7 | Regel |
| `container-registry.networking.public_network_access` | disabled | übernommen |
| `container-registry.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | erzwungen |
| `container-registry.networking.network_rule_bypass` | None | Regel |
| `container-registry.networking.export_policy_enabled` | false | Regel |
| `container-registry.identity.managed_identity` | none | Regel |
| `container-registry.identity.role_assignments` | {"production": [{"principal": "user-assigned-identity__runner", "role": "AcrPull"}]} | eure Beschreibung |
| `container-registry.security.admin_enabled` | false | übernommen |
| `container-registry.security.anonymous_pull_enabled` | false | Regel |
| `container-registry.security.key_management` | platform_managed | übernommen |
| `container-registry.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `container-registry.observability.diagnostic_categories` | ["ContainerRegistryRepositoryEvents", "ContainerRegistryLoginEvents"] | Regel |
| `container-registry.observability.metrics_enabled` | true | Regel |
| `container-apps.environment.workload_profile` | Consumption | Regel |
| `container-apps.environment.zone_redundant` | true | abgeleitet aus eurer Antwort |
| `container-apps.environment.internal` | true | übernommen |
| `container-apps.environment.infrastructure_subnet` | {"production": "snet-aca"} | erzwungen |
| `container-apps.environment.public_network_access` | disabled | übernommen |
| `container-apps.environment.peer_traffic_encryption` | true | Regel |
| `container-apps.app.container_image` | container-registry/code-runner:1.0.0 | eure Beschreibung |
| `container-apps.app.container_size` | 0.5-1Gi | Regel |
| `container-apps.app.min_replicas` | 2 | abgeleitet aus eurer Antwort |
| `container-apps.app.max_replicas` | 10 | Regel |
| `container-apps.app.revision_mode` | Single | Regel |
| `container-apps.ingress.ingress` | environment | Regel |
| `container-apps.ingress.target_port` | 8080 | eure Beschreibung |
| `container-apps.ingress.allow_insecure` | false | Regel |
| `container-apps.identity.managed_identity` | user_assigned | Regel |
| `container-apps.identity.user_assigned_identity_ids` | {"production": ["user-assigned-identity__runner"]} | eure Beschreibung |
| `container-apps.identity.secret_references` | {"production": []} | Regel |
| `container-apps.identity.role_assignments` | {"production": []} | Regel |
| `container-apps.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `container-apps.observability.diagnostic_categories` | ["ContainerAppConsoleLogs", "ContainerAppSystemLogs"] | Regel |
| `container-apps.observability.metrics_enabled` | true | Regel |
| `function-app.hosting.plan_type` | flex_consumption | Regel |
| `function-app.hosting.runtime_stack` | python | eure Beschreibung |
| `function-app.hosting.runtime_version` | 3.12 | eure Beschreibung |
| `function-app.hosting.zone_redundant` | true | abgeleitet aus eurer Antwort |
| `function-app.hosting.max_instance_count` | 20 | Regel |
| `function-app.hosting.always_ready_instances` | 1 | abgeleitet aus eurer Antwort |
| `function-app.hosting.instance_memory_mb` | 2048 | Regel |
| `function-app.storage.host_storage_account` | {"production": "storage-account__host"} | eure Beschreibung |
| `function-app.storage.host_storage_auth` | identity | übernommen |
| `function-app.storage.deployment_container` | app-package | Regel |
| `function-app.networking.public_network_access` | disabled | übernommen |
| `function-app.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | erzwungen |
| `function-app.networking.vnet_integration` | true | Regel |
| `function-app.networking.integration_subnet` | {"production": "snet-func"} | erzwungen |
| `function-app.networking.vnet_route_all` | true | Regel |
| `function-app.identity.managed_identity` | user_assigned | Regel |
| `function-app.identity.user_assigned_identity_ids` | {"production": ["user-assigned-identity__connector"]} | eure Beschreibung |
| `function-app.identity.role_assignments` | {"production": []} | Regel |
| `function-app.security.https_only` | true | Regel |
| `function-app.security.min_tls_version` | 1.2 | Regel |
| `function-app.security.basic_auth_enabled` | false | übernommen |
| `function-app.security.application_insights` | {"production": "application-insights"} | eure Beschreibung |
| `function-app.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `function-app.observability.diagnostic_categories` | ["FunctionAppLogs", "AppServiceAuditLogs"] | Regel |
| `function-app.observability.metrics_enabled` | true | Regel |
| `app-service__web.hosting.os_type` | Linux | Regel |
| `app-service__web.hosting.sku` | P1v3 | Regel |
| `app-service__web.hosting.zone_redundant` | true | abgeleitet aus eurer Antwort |
| `app-service__web.hosting.instance_count` | 2 | abgeleitet aus eurer Antwort |
| `app-service__web.networking.public_network_access` | disabled | übernommen |
| `app-service__web.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | erzwungen |
| `app-service__web.networking.vnet_integration` | true | Regel |
| `app-service__web.networking.integration_subnet` | {"production": "snet-web"} | erzwungen |
| `app-service__web.networking.vnet_route_all` | true | Regel |
| `app-service__web.identity.managed_identity` | user_assigned | eure Beschreibung |
| `app-service__web.identity.user_assigned_identity_ids` | {"production": ["user-assigned-identity__web"]} | eure Beschreibung |
| `app-service__web.security.https_only` | true | Regel |
| `app-service__web.security.min_tls_version` | 1.2 | Regel |
| `app-service__web.security.ftps_state` | Disabled | Regel |
| `app-service__web.security.basic_auth_enabled` | false | übernommen |
| `app-service__web.runtime.runtime_stack` | python | eure Beschreibung |
| `app-service__web.runtime.runtime_version` | 3.12 | eure Beschreibung |
| `app-service__web.runtime.always_on` | true | Regel |
| `app-service__web.runtime.health_check_path` |  | Regel |
| `app-service__web.runtime.http2_enabled` | true | Regel |
| `app-service__web.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `app-service__web.observability.diagnostic_categories` | ["AppServiceHTTPLogs", "AppServiceAppLogs", "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs"] | Regel |
| `app-service__web.observability.metrics_enabled` | true | Regel |
| `app-service__mcp.hosting.os_type` | Linux | Regel |
| `app-service__mcp.hosting.sku` | P1v3 | Regel |
| `app-service__mcp.hosting.zone_redundant` | true | abgeleitet aus eurer Antwort |
| `app-service__mcp.hosting.instance_count` | 2 | abgeleitet aus eurer Antwort |
| `app-service__mcp.networking.public_network_access` | disabled | übernommen |
| `app-service__mcp.networking.private_endpoint_subnet` | {"production": "snet-endpoints"} | erzwungen |
| `app-service__mcp.networking.vnet_integration` | true | Regel |
| `app-service__mcp.networking.integration_subnet` | {"production": "snet-mcp"} | erzwungen |
| `app-service__mcp.networking.vnet_route_all` | true | Regel |
| `app-service__mcp.identity.managed_identity` | user_assigned | eure Beschreibung |
| `app-service__mcp.identity.user_assigned_identity_ids` | {"production": ["user-assigned-identity__web"]} | eure Beschreibung |
| `app-service__mcp.security.https_only` | true | Regel |
| `app-service__mcp.security.min_tls_version` | 1.2 | Regel |
| `app-service__mcp.security.ftps_state` | Disabled | Regel |
| `app-service__mcp.security.basic_auth_enabled` | false | übernommen |
| `app-service__mcp.runtime.runtime_stack` | node | eure Beschreibung |
| `app-service__mcp.runtime.runtime_version` | 22-lts | eure Beschreibung |
| `app-service__mcp.runtime.always_on` | true | Regel |
| `app-service__mcp.runtime.health_check_path` |  | Regel |
| `app-service__mcp.runtime.http2_enabled` | true | Regel |
| `app-service__mcp.observability.diagnostic_workspace` | {"production": "log-analytics-workspace"} | übernommen |
| `app-service__mcp.observability.diagnostic_categories` | ["AppServiceHTTPLogs", "AppServiceAppLogs", "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs"] | Regel |
| `app-service__mcp.observability.metrics_enabled` | true | Regel |
| `wiring.access` | [{"from": "users", "to": "app-service__web", "label": "HTTPS 443"}, {"from": "app-service__web", "to": "external:entra-id", "label": "sign-in"}, {"from": "app-service__web", "to": "app-service__mcp"}, {"from": "app-service__web", "to": "foundry"}, {"from": "app-service__web", "to": "search-service"}, {"from": "app-service__web", "to": "cosmos-db"}, {"from": "app-service__web", "to": "storage-account__uploads"}, {"from": "app-service__web", "to": "key-vault"}, {"from": "app-service__mcp", "to": "container-apps"}, {"from": "app-service__mcp", "to": "foundry"}, {"from": "function-app", "to": "search-service"}, {"from": "function-app", "to": "foundry"}, {"from": "function-app", "to": "key-vault"}, {"from": "function-app", "to": "storage-account__host"}, {"from": "function-app", "to": "application-insights"}, {"from": "container-apps", "to": "container-registry", "label": "pulls its image"}] | eure Beschreibung |
| `wiring.purposes` | {"app-service__web": "Chat front end and back end", "app-service__mcp": "MCP tool server", "function-app": "Connector to the document store", "container-apps": "Code interpreter", "foundry": "Chat and embedding models", "search-service": "Search; indexes the uploads, embeds with the models", "cosmos-db": "Conversation history", "storage-account__uploads": "Uploaded files", "storage-account__host": "State of the connector function", "key-vault": "Secrets", "user-assigned-identity__web": "Web app and MCP server", "user-assigned-identity__connector": "Connector function", "user-assigned-identity__runner": "Code interpreter", "network-security-group__endpoints": "Private endpoints subnet", "network-security-group__integration": "App integration subnets", "network-security-group__containerapps": "Container Apps subnet", "container-registry": "Images of all apps", "application-insights": "Application telemetry"} | eure Beschreibung |
| `wiring.optional` | [] | Regel |
