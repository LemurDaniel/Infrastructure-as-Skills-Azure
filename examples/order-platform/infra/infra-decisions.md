# Entscheidungen für „orders“

Was gebaut wird, entschieden aus euren Antworten und den Regeln hinter den Vorgaben. Jede Zeile ist eine Entscheidung; der Schlüssel im Anhang ist, wo ein Engineer sie in der Spezifikation findet.

Stand 2026-10-26. Spezifikation: `infra-spec.yaml`.

## Das System

- Das System wird in diesen Stufen ausgerollt: Entwicklung, Test, Echtbetrieb.
- Alles läuft in der Azure-Region germanywestcentral.
- „orders“ ist der Name, den jeder Teil des Systems trägt.
- Das System wird in die Subscription parameterized ausgerollt.
- Alle Teile liegen in der bestehenden Ressourcengruppe parameterized.
- Jede Stufe liegt in einer eigenen Subscription; die Stufen können sich gegenseitig weder Ressourcen noch Budgets noch Berechtigungen anfassen.

## Ressourcengruppen

Eine Ressourcengruppe wird als Ganzes gelöscht, berechtigt und abgerechnet. Jede Gruppe wird entweder mit dem System angelegt oder existiert bereits und wird nur verwendet.

| Gruppe | Zustand | Name | Enthält |
|---|---|---|---|
| Haupt | wird mit dem System angelegt | nach der Namenskonvention benannt | Azure Private DNS Zone, Azure Public IP Address (appgw), Azure Storage blob container, Azure Virtual Machine, Azure user-assigned managed identity (appgw), Azure user-assigned managed identity (function) |
| Netzwerk | wird mit dem System angelegt | nach der Namenskonvention benannt | Azure Application Gateway (v2) with web application firewall, Azure Front Door (Standard / Premium), Azure Network Security Group (apim), Azure Network Security Group (appgw), Azure Network Security Group (pe), Azure Network Security Group (workload), Azure Virtual Network |
| Daten | wird mit dem System angelegt | nach der Namenskonvention benannt | Azure Backup vault, Azure Recovery Services vault, Azure Storage Account (datalake), Azure Storage Account (host) |
| Anwendung | wird mit dem System angelegt | nach der Namenskonvention benannt | Azure API Management service, Azure Event Grid system topic, Azure Event Hubs namespace, Azure Functions (function app on Flex Consumption or Elastic Premium), Azure Service Bus namespace |
| Überwachung | wird mit dem System angelegt | nach der Namenskonvention benannt | Azure Log Analytics Workspace |

## Was sich zwischen den Stufen unterscheidet

Ein Code wird durch diese Stufen ausgerollt; alles, was hier nicht steht, ist in jeder Stufe gleich.

- Das neue Netz nutzt den Adressbereich Entwicklung: 10.100.0.0/23; Test: 10.101.0.0/23; Echtbetrieb: 10.102.0.0/23.

## Was aus euren Antworten folgt

- **Diese Bereiche erhalten eine eigene Ressourcengruppe: Netzwerk, Daten, Anwendung, Überwachung. Alles andere liegt in der Hauptgruppe.** _(eure Antwort)_
- **Die Hauptressourcengruppe wird zusammen mit dem System angelegt.** _(eure Antwort)_
- **Die Ressourcengruppe für das Netzwerk wird zusammen mit dem System angelegt.** _(eure Antwort)_
- **Die Ressourcengruppe für die Daten wird zusammen mit dem System angelegt.** _(eure Antwort)_
- **Die Ressourcengruppe für die Anwendung wird zusammen mit dem System angelegt.** _(eure Antwort)_
- **Die Ressourcengruppe für die Überwachung wird zusammen mit dem System angelegt.** _(eure Antwort)_
- **Ressourcen, die Daten halten, tragen in der Produktion eine Löschsperre.** _(nicht gesagt, daher gilt die übliche Antwort)_
- **Das System wird durch GitHub Actions ausgerollt.** _(eure Antwort)_
- **Das Netz wird von diesem Ausrollen frei gewählt, ohne Verbindung zum Firmennetz und ohne VPN.** _(eure Antwort)_
- **Ein Tag Ausfall wäre verkraftbar.** _(eure Antwort)_
  - daher, Azure Application Gateway (v2) with web application firewall: Mindestens 1 Instanz(en) laufen immer.
  - daher, Azure Application Gateway (v2) with web application firewall: Das Gateway übersteht den Ausfall eines Rechenzentrums: überstehen nicht.
  - daher, Azure API Management service: Das Gateway ist die Stufe eine Teststufe ohne Verfügbarkeitszusage.
  - daher, Azure Functions (function app on Flex Consumption or Elastic Premium): Die Function App übersteht nicht den Ausfall eines Rechenzentrums der Region.
  - daher, Azure Functions (function app on Flex Consumption or Elastic Premium): 0 Instanz(en) werden vorgewärmt gehalten, damit der erste Aufruf nicht wartet.
  - daher, Azure Storage Account (datalake): Die Daten liegen dreifach in einem Rechenzentrum.
  - daher, Azure Storage Account (host): Die Daten liegen dreifach in einem Rechenzentrum.
  - daher, Azure Service Bus namespace: Die Nachrichtenverarbeitung übersteht den Ausfall eines Rechenzentrums: überstehen nicht.
  - daher, Azure Event Hubs namespace: Der Datenstrom übersteht den Ausfall eines Rechenzentrums: überstehen nicht.
- **Nach einem versehentlichen Löschen müsst ihr gar nicht, die Daten lassen sich neu erzeugen zurückkommen.** _(eure Antwort)_
  - daher, Azure Storage Account (datalake): Gelöschte Dateien sind 0 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account (datalake): Gelöschte Ordner sind 0 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account (datalake): Frühere Versionen überschriebener Dateien werden nicht aufgehoben.
- **Die Daten werden laufend genutzt.** _(eure Antwort)_
  - daher, Azure Storage Account (datalake): Gespeichert in der Klasse Standard: günstig beim Lesen, für Daten in Nutzung.
- **Gegen absichtliche Zerstörung sind die Daten nur innerhalb des Systems selbst geschützt; wer das System löschen kann, kann auch die Kopien löschen.** _(eure Antwort)_
  - daher, Azure Backup vault: Sicherungen sind gewöhnlich: ein Administrator kann sie löschen.
  - daher, Azure Backup vault: Das Löschen von Sicherungen braucht keine zweite Freigabe.
  - daher, Azure Recovery Services vault: Gelöschte Sicherungen werden eine Zeit lang aufbewahrt und wiederherstellbar, Administratoren können das aber abschalten.
- **Die Daten werden nur innerhalb des Wirtschaftsraums der Region, zum Beispiel der EU gespeichert und verarbeitet.** _(eure Antwort)_
- **Das System wird mit Ausgewogenheit zwischen Kosten und Schutz gebaut.** _(eure Antwort)_
- **Der Code wird aus Microsofts geprüften, getesteten Bausteinen (Azure Verified Modules) gebaut.** _(eure Antwort)_
- **Die Ressourcennamen erzeugt Microsofts fertiges Naming-Modul.** _(eure Antwort)_
- **Der Zugang ist privat, mit benannten Ausnahmen hinter einer Firewall aus dem Internet erreichbar.** _(eure Antwort)_
- **Einzuhaltende Vorgaben: DSGVO.** _(eure Antwort)_
- **Logs werden 30 Tage aufbewahrt.** _(nicht gesagt, daher gilt die übliche Antwort)_

## Nach den Vorgaben gesetzt

Nichts davon wurde gefragt; jede Zeile folgt einer Regel oder einer der Antworten oben. Sagt Bescheid, wenn eine nicht passt.

### Für das ganze System

- Angelegte Ressourcengruppen tragen in der Produktion eine Löschsperre.
- Die Pipeline meldet sich mit einem kurzlebigen Token pro Lauf, ohne irgendwo gespeichertes Passwort bei Azure an.
- Eine Person gibt die Änderung frei, bevor sie ausgerollt wird: nur im Echtbetrieb.
- Nutzungstelemetrie an Microsoft ist ausgeschaltet: eine Zählung pro Ausrollen, keine eurer Daten.
- Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Logging selbst mit. _(bitte bestätigen)_
- Passwörter und Zugriffsschlüssel sind abgeschaltet; der Zugriff läuft über Firmenkonten, damit jede Aktion zuordenbar ist. _(bitte bestätigen)_
- Verschlüsselungsschlüssel sind in Software geschützt, der Standard, ausreichend ohne Vorgabe für Hardware.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch. _(bitte bestätigen)_
- Das Netz wird von diesem Ausrollen selbst gebaut. — weil: Der Zugang ist privat, mit benannten Ausnahmen hinter einer Firewall aus dem Internet erreichbar.
- Das neue Netz nutzt den Adressbereich Entwicklung: 10.100.0.0/23; Test: 10.101.0.0/23; Echtbetrieb: 10.102.0.0/23.
- Die Namensauflösung für private Anbindungen übernimmt dieses Ausrollen selbst. — weil: Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Logging selbst mit.
- Logs gehen in einen Arbeitsbereich, den dieses Ausrollen anlegt und bezahlt. — weil: Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Logging selbst mit.
- Tägliche Obergrenze für Logs: -1 GB (-1: keine). _(bitte bestätigen)_

### Sicherheit

Die Sicherheitsvorgaben aller Teile an einer Stelle. Sie wurden nicht gefragt und sind in jeder Stufe gleich; sagt Bescheid, wenn eine nicht passt.

- **Azure Virtual Network**
  - Subnetze, die eine Sicherheitsgruppe bekommen: appgw, apim, function-integration, workload, private-endpoints.
- **Azure Front Door (Standard / Premium)**
  - Eine Web Application Firewall am Rand ist von einer Web Application Firewall geprüft. _(bitte bestätigen)_
  - Die Firewall blockiert Anfragen, die es für bösartig hält. _(bitte bestätigen)_

### Azure Virtual Network

- Subnetze: appgw, apim, function-integration, workload, private-endpoints.
- Private Anbindungen bekommen das Subnetz first /27 of each stage's range.

### Azure Network Security Group (appgw)

- Die Gruppe schützt ein Subnetz für Workload-Maschinen oder -Dienste.

### Azure Network Security Group (apim)

- Die Gruppe schützt ein Subnetz für Workload-Maschinen oder -Dienste.

### Azure Network Security Group (workload)

- Die Gruppe schützt ein Subnetz für Workload-Maschinen oder -Dienste.

### Azure Network Security Group (pe)

- Die Gruppe schützt ein Subnetz für private Anbindungen an Azure-Dienste.

### Azure Public IP Address (appgw)

- Die Adresse ist für den Eingang eines Web-Gateways.

### Azure Application Gateway (v2) with web application firewall

- Eine Web Application Firewall ist von einer Web Application Firewall geprüft. _(bitte bestätigen)_
- Die Firewall blockiert Anfragen, die es für bösartig hält. _(bitte bestätigen)_
- Seiten: keine.

### Azure Front Door (Standard / Premium)

- Front Door ist die Stufe Premium, mit verwalteten Firewall-Regeln und privaten Verbindungen zu den Backends. _(bitte bestätigen)_
- Antworten werden am Rand zwischengespeichert.

### Azure Log Analytics Workspace

- Logs werden 30 Tage aufbewahrt.

### Azure API Management service

- Aufrufer melden sich an mit einem persönlichen Zugriffsschlüssel. _(bitte bestätigen)_
- Ein Aufrufer darf 600 Aufrufe pro Minute machen (0: keine Grenze).
- Ein Entwicklerportal ist nicht bereitgestellt.
- Das Gateway ist nur im privaten Netz. _(bitte bestätigen)_

### Azure Functions (function app on Flex Consumption or Elastic Premium)

- Die Function App läuft auf Kapazität, die von null aus skaliert und nach Nutzung abgerechnet wird, mit privatem Netz und optional vorgewärmten Instanzen.

### Azure Storage Account (datalake)

- Private Anbindungen gibt es für: Dateien (Blob), den Data Lake. — weil: Der Zugang ist privat, mit benannten Ausnahmen hinter einer Firewall aus dem Internet erreichbar.

### Azure Storage Account (host)

- Private Anbindungen gibt es für: Dateien (Blob), Warteschlangen. — weil: Der Zugang ist privat, mit benannten Ausnahmen hinter einer Firewall aus dem Internet erreichbar.

### Azure Service Bus namespace

- Der Namensraum ist die Stufe Premium, dedizierte Kapazität mit privaten Anbindungen. — weil: Der Zugang ist privat, mit benannten Ausnahmen hinter einer Firewall aus dem Internet erreichbar. _(bitte bestätigen)_
- Themen und ihre Abonnenten: orders subscriptions ['billing', 'shipping', 'audit'] (leer: keine).
- Warteschlangen: payments (leer: keine).
- Zusammengehörige Nachrichten müssen nicht der Reihenfolge nach bearbeitet werden.
- Doppelt gesendete Nachrichten werden vom Broker verworfen.

### Azure Event Hubs namespace

- Der Namensraum ist die Stufe Standard, mehrere Lesergruppen, bis zu einer Woche Historie und private Anbindung. _(bitte bestätigen)_
- Event Hubs: telemetry.
- Jedes Ereignis wird zusätzlich als Dateien im Speicher archiviert.
- Das Archiv geht in das Speicherkonto storage-account__datalake.

### Azure Event Grid system topic

- Die Quelle ist ein Speicherkonto.
- Meldet, was mit storage-account__datalake geschieht.
- Ereignisse werden an direkt eine Funktion zugestellt.

### Azure Virtual Machine

- Die Maschine läuft mit Linux.

### Azure Backup vault

- Gesichert werden: storage-account__datalake (leer: noch nichts).

### Azure Recovery Services vault

- Gesichert werden: virtual-machine (leer: noch nichts).

## Von euch anders entschieden

- Azure Application Gateway (v2) with web application firewall: Das Gateway nimmt Anfragen aus dem Internet entgegen. _(Grund: Front Door (Premium) cannot reach an Application Gateway through Private Link; the gateway keeps a public IP that only admits the AzureFrontDoor.Backend service tag and the Front Door id header. Default is private.)_
- Azure Front Door (Standard / Premium): Front Door erreicht die Backends über die öffentlichen Adressen der Backends. _(Grund: Origin is the Application Gateway, which Front Door cannot reach over Private Link. Default is private_link.)_
- Azure Functions (function app on Flex Consumption or Elastic Premium): Die Function App ist aus dem Internet nur von gelisteten Adressen erreichbar. _(Grund: Event Grid delivers blob events to the function over its public endpoint; access is restricted to the AzureEventGrid and ApiManagement service tags (the app is otherwise private). Deployment default is disabled.)_
- Azure Virtual Machine: Die Maschine wird gesichert: ja. _(Grund: The customer asked for VM backup; the derived value from data_loss_tolerance "reproducible" would be false.)_

## Noch offen

Solange diese Punkte offen sind, wird nichts ausgerollt.

- Welcher Organisationsname soll in API Management erscheinen? _(gebraucht von: Workload-Verantwortliche)_ — blockiert: apply
- Welche Kontaktadresse erhält die Benachrichtigungen von API Management? _(gebraucht von: Workload-Verantwortliche)_ — blockiert: apply
- Welche Laufzeit und Version nutzt die Function App (z. B. Node 20, .NET isolated)? _(gebraucht von: Entwicklung)_ — blockiert: apply
- Welche Domänen und TLS-Zertifikate gelten für das Application Gateway, und wer erneuert sie? _(gebraucht von: Workload-Verantwortliche)_ — blockiert: apply
- Wofür laufen die VMs, und welche Größe und Anzahl brauchen sie? (Annahme: 3 × Standard_D2ds_v5) _(gebraucht von: Workload-Verantwortliche)_ — blockiert: apply
- Welcher öffentliche SSH-Schlüssel gilt für die VMs? _(gebraucht von: Workload-Verantwortliche)_ — blockiert: apply

## Platzhalter

Werte, die der Lauf angenommen hat, um weiterzukommen. Das sind noch keine Entscheidungen.

- Container: telemetry. (`resources.blob-container.containers.container_names`)
- Zugestellte Ereignisse: Microsoft.Storage.BlobCreated (leer: alle Arten, die die Quelle meldet). (`resources.event-grid-system-topic.delivery.included_event_types`)

## Anhang: alle Entscheidungen

| Schlüssel | Wert | Quelle |
|---|---|---|
| `deployment.module_source` | avm | eure Antwort |
| `deployment.naming_source` | module | eure Antwort |
| `deployment.module_telemetry` | disabled | Regel |
| `deployment.deploy_mechanism` | github | eure Antwort |
| `deployment.pipeline_auth` | workload_identity | Regel |
| `deployment.pipeline_approvals` | production | Regel |
| `deployment.stage_isolation` | subscription | Regel |
| `deployment.non_production_savings` | enabled | Regel |
| `deployment.priority` | balanced | eure Antwort |
| `deployment.landing_zone` | standalone | abgeleitet aus eurer Antwort |
| `deployment.network_requirements` | free | eure Antwort |
| `deployment.network_exposure` | private_with_exceptions | eure Antwort |
| `deployment.local_auth` | disabled | Regel |
| `deployment.network_ownership` | create | erzwungen |
| `deployment.address_space` | {"development": "10.100.0.0/23", "test": "10.101.0.0/23", "production": "10.102.0.0/23"} | eure Antwort |
| `deployment.private_dns_ownership` | deployment | erzwungen |
| `deployment.observability_ownership` | create | erzwungen |
| `deployment.log_retention_days` | 30 | Regel |
| `deployment.daily_quota_gb` | -1 | Regel |
| `deployment.outage_impact` | tolerable | eure Antwort |
| `deployment.data_loss_tolerance` | reproducible | eure Antwort |
| `deployment.data_access_pattern` | active | eure Antwort |
| `deployment.backup_isolation` | operational | eure Antwort |
| `deployment.data_residency` | data_zone | eure Antwort |
| `deployment.mandates` | ["DSGVO"] | eure Antwort |
| `deployment.key_protection` | software | Regel |
| `deployment.key_management` | platform_managed | Regel |
| `deployment.resource_lock` | production | Regel |
| `deployment.resource_group_lock` | production | Regel |
| `deployment.resource_group_split` | ["network", "data", "application", "observability"] | eure Antwort |
| `deployment.resource_group_mode_main` | create | eure Antwort |
| `deployment.resource_group_mode_network` | create | eure Antwort |
| `deployment.resource_group_mode_data` | create | eure Antwort |
| `deployment.resource_group_mode_application` | create | eure Antwort |
| `deployment.resource_group_mode_observability` | create | eure Antwort |
| `virtual-network.addressing.subnets` | ["appgw", "apim", "function-integration", "workload", "private-endpoints"] | Regel |
| `virtual-network.addressing.private_endpoint_subnet_prefix` | first /27 of each stage's range | Regel |
| `virtual-network.security.subnets_expecting_nsg` | ["appgw", "apim", "function-integration", "workload", "private-endpoints"] | Regel |
| `network-security-group__appgw.rules.subnet_purpose` | workload | Regel |
| `network-security-group__apim.rules.subnet_purpose` | workload | Regel |
| `network-security-group__workload.rules.subnet_purpose` | workload | Regel |
| `network-security-group__pe.rules.subnet_purpose` | private_endpoints | Regel |
| `public-ip-address__appgw.address.purpose` | application_gateway | Regel |
| `application-gateway.gateway.waf_enabled` | true | Regel |
| `application-gateway.gateway.waf_mode` | Prevention | Regel |
| `application-gateway.gateway.capacity_min` | 1 | abgeleitet aus eurer Antwort |
| `application-gateway.gateway.zone_redundant` | false | abgeleitet aus eurer Antwort |
| `application-gateway.networking.frontend_exposure` | public | eure Abweichung |
| `application-gateway.networking.listeners` | [] | Regel |
| `front-door.profile.sku` | Premium_AzureFrontDoor | Regel |
| `front-door.delivery.caching` | true | eure Antwort |
| `front-door.delivery.origin_connection` | public | eure Abweichung |
| `front-door.security.waf_enabled` | true | Regel |
| `front-door.security.waf_mode` | Prevention | Regel |
| `log-analytics-workspace.cost.retention_days` | 30 | übernommen |
| `api-management.service.sku` | Developer | abgeleitet aus eurer Antwort |
| `api-management.access.caller_authentication` | subscription_key | eure Antwort |
| `api-management.access.rate_limit_calls_per_minute` | 600 | Regel |
| `api-management.access.developer_portal` | false | Regel |
| `api-management.networking.network_integration` | internal | Regel |
| `function-app.hosting.plan_type` | flex_consumption | Regel |
| `function-app.hosting.zone_redundant` | false | abgeleitet aus eurer Antwort |
| `function-app.hosting.always_ready_instances` | 0 | abgeleitet aus eurer Antwort |
| `function-app.networking.public_network_access` | enabled_with_firewall | eure Abweichung |
| `storage-account__datalake.data_protection.replication` | LRS | abgeleitet aus eurer Antwort |
| `storage-account__datalake.data_protection.access_tier` | Hot | abgeleitet aus eurer Antwort |
| `storage-account__datalake.data_protection.blob_soft_delete_days` | 0 | abgeleitet aus eurer Antwort |
| `storage-account__datalake.data_protection.container_soft_delete_days` | 0 | abgeleitet aus eurer Antwort |
| `storage-account__datalake.data_protection.versioning_enabled` | false | abgeleitet aus eurer Antwort |
| `storage-account__datalake.networking.private_endpoint_subresources` | ["blob", "dfs"] | erzwungen |
| `storage-account__host.data_protection.replication` | LRS | abgeleitet aus eurer Antwort |
| `storage-account__host.networking.private_endpoint_subresources` | ["blob", "queue"] | erzwungen |
| `blob-container.containers.container_names` | ["telemetry"] | Platzhalter |
| `service-bus.namespace.sku` | Premium | erzwungen |
| `service-bus.namespace.zone_redundant` | false | abgeleitet aus eurer Antwort |
| `service-bus.entities.topics` | [{"name": "orders", "subscriptions": ["billing", "shipping", "audit"]}] | eure Beschreibung |
| `service-bus.entities.queues` | ["payments"] | eure Beschreibung |
| `service-bus.entities.message_ordering` | false | eure Antwort |
| `service-bus.entities.duplicate_protection` | true | eure Antwort |
| `event-hubs.namespace.sku` | Standard | Regel |
| `event-hubs.entities.event_hubs` | ["telemetry"] | eure Beschreibung |
| `event-hubs.entities.event_archive` | true | eure Beschreibung |
| `event-hubs.entities.archive_storage_account` | storage-account__datalake | eure Beschreibung |
| `event-hubs.recovery.zone_redundant` | false | abgeleitet aus eurer Antwort |
| `event-grid-system-topic.source.topic_type` | Microsoft.Storage.StorageAccounts | eure Beschreibung |
| `event-grid-system-topic.source.source_resource` | storage-account__datalake | eure Beschreibung |
| `event-grid-system-topic.delivery.destination_kind` | azure_function | eure Beschreibung |
| `event-grid-system-topic.delivery.included_event_types` | ["Microsoft.Storage.BlobCreated"] | Platzhalter |
| `virtual-machine.machine.os_type` | Linux | eure Antwort |
| `virtual-machine.data_protection.backup_enabled` | true | eure Abweichung |
| `backup-vault.protection.protected_resources` | ["storage-account__datalake"] | eure Beschreibung |
| `backup-vault.vault.immutability` | Disabled | abgeleitet aus eurer Antwort |
| `backup-vault.vault.multi_user_authorization` | false | abgeleitet aus eurer Antwort |
| `recovery-services-vault.protection.protected_resources` | ["virtual-machine"] | eure Beschreibung |
| `recovery-services-vault.vault.soft_delete` | Enabled | abgeleitet aus eurer Antwort |
| `wiring.access` | [{"from": "internet", "to": "front-door", "label": "HTTPS 443"}, {"from": "front-door", "to": "application-gateway", "label": "HTTPS"}, {"from": "application-gateway", "to": "api-management", "label": "HTTPS"}, {"from": "api-management", "to": "function-app", "label": "HTTPS"}, {"from": "function-app", "to": "service-bus", "label": "Bestellungen und Zahlungen senden"}, {"from": "service-bus", "to": "function-app", "label": "Billing, Shipping, Audit verarbeiten"}, {"from": "external:Telemetrie-Quellen", "to": "event-hubs", "label": "Telemetrie senden"}, {"from": "event-hubs", "to": "storage-account__datalake", "label": "Archiv (Capture)"}, {"from": "storage-account__datalake", "to": "event-grid-system-topic", "label": "Blob-Ereignisse"}, {"from": "event-grid-system-topic", "to": "function-app", "label": "Ereignisse zustellen"}, {"from": "backup-vault", "to": "storage-account__datalake", "label": "sichert"}, {"from": "recovery-services-vault", "to": "virtual-machine", "label": "sichert"}] | eure Beschreibung |
| `wiring.purposes` | {"front-door": "Öffentlicher Eingang mit WAF", "application-gateway": "Zweite WAF, nimmt nur Front Door an", "api-management": "Bestell-API", "function-app": "Backend der API", "service-bus": "Bestellungen und Zahlungen", "event-hubs": "Telemetrie", "storage-account__datalake": "Telemetrie-Archiv", "event-grid-system-topic": "Blob-Ereignisse", "virtual-machine": "Virtuelle Maschinen", "backup-vault": "Sicherung Speicher", "recovery-services-vault": "Sicherung VMs"} | eure Beschreibung |
