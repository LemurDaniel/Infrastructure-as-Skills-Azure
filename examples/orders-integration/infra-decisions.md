# Entscheidungen für „orders“

Was gebaut wird, entschieden aus euren Antworten und den Regeln hinter den Vorgaben. Jede Zeile ist eine Entscheidung; der Schlüssel im Anhang zeigt, wo sie in der Spezifikation steht.

Stand 2026-10-25. Spezifikation: `infra-spec.yaml`.

## Das System

- Das System wird in diesen Stufen ausgerollt: Entwicklung, Test, Echtbetrieb.
- Alles läuft in der Azure-Region germanywestcentral.
- „orders“ ist der Name, den jeder Teil des Systems trägt.

## Ressourcengruppen

Eine Ressourcengruppe wird als Ganzes gelöscht, berechtigt und abgerechnet. Jede Gruppe wird entweder mit dem System angelegt oder existiert bereits und wird nur verwendet.

| Gruppe | Zustand | Name | Enthält |
|---|---|---|---|
| Haupt | wird mit dem System angelegt | nach der Namenskonvention benannt | Azure API Management service, Azure Event Grid custom topic, Azure Event Hubs namespace, Azure Functions (function app on Flex Consumption or Elastic Premium), Azure Key Vault, Azure Service Bus namespace |
| Netzwerk | wird mit dem System angelegt | nach der Namenskonvention benannt | Azure Application Gateway (v2) with web application firewall, Azure Front Door (Standard / Premium), Azure Virtual Network |
| Daten | wird mit dem System angelegt | nach der Namenskonvention benannt | Azure Backup vault, Azure Recovery Services vault, Azure Storage Account |
| Überwachung | wird mit dem System angelegt | nach der Namenskonvention benannt | Azure Log Analytics Workspace |

## Was sich zwischen den Stufen unterscheidet

Ein Code wird durch diese Stufen ausgerollt; alles, was hier nicht steht, ist in jeder Stufe gleich.

- Gegen absichtliche Zerstörung sind die Daten Entwicklung: zusätzlich in einem getrennten Backup-Speicher, den die Administratoren des Systems nicht löschen können; Test: zusätzlich in einem getrennten Backup-Speicher, den die Administratoren des Systems nicht löschen können; Echtbetrieb: zusätzlich in einem getrennten Backup-Speicher, in dem niemand eine Kopie vor ihrem Ablauf ändern oder löschen kann.
- Logs werden Entwicklung: 30; Test: 30; Echtbetrieb: 90 Tage aufbewahrt.
- Azure API Management service: Das Gateway ist die Stufe Entwicklung: eine Teststufe ohne Verfügbarkeitszusage; Test: eine Teststufe ohne Verfügbarkeitszusage; Echtbetrieb: Premium, mit Zonen, mehreren Regionen und Netzwerkeinbindung.
- Azure Service Bus namespace: Der Namensraum ist die Stufe Entwicklung: Standard, Warteschlangen und Themen auf geteilter Kapazität; Test: Standard, Warteschlangen und Themen auf geteilter Kapazität; Echtbetrieb: Premium, dedizierte Kapazität mit privaten Anbindungen.
- Azure Service Bus namespace: Der Dienst (namespace) ist Entwicklung: firewalled; Test: firewalled; Echtbetrieb: aus dem Internet überhaupt nicht erreichbar.
- Azure Backup vault: `{"development": "LRS", "test": "LRS", "production": "GRS"}`
- Azure Backup vault: Wiederherstellung in der Partnerregion ist Entwicklung: nicht möglich; Test: nicht möglich; Echtbetrieb: möglich.
- Azure Recovery Services vault: `{"development": "LRS", "test": "LRS", "production": "GRS"}`
- Azure Recovery Services vault: Wiederherstellung in der Partnerregion ist Entwicklung: nicht möglich; Test: nicht möglich; Echtbetrieb: möglich.
- Azure Log Analytics Workspace: Logs werden Entwicklung: 30; Test: 30; Echtbetrieb: 90 Tage aufbewahrt.
- Azure Virtual Network: Das Netz nutzt den Adressbereich Entwicklung: 10.100.0.0/22; Test: 10.100.4.0/22; Echtbetrieb: 10.100.8.0/22.

## Was aus euren Antworten folgt

- **Ressourcen, die Daten halten, tragen in der Produktion eine Löschsperre.** _(eure Antwort)_
- **Das System wird durch GitHub Actions ausgerollt.** _(eure Antwort)_
- **Das Netz wird von diesem Ausrollen frei gewählt, ohne Verbindung zum Firmennetz und ohne VPN.** _(eure Antwort)_
- **Ein Tag Ausfall wäre verkraftbar.** _(eure Antwort)_
- **Nach einem versehentlichen Löschen müsst ihr einen Monat zurückkommen.** _(eure Antwort)_
- **Die Daten werden laufend genutzt.** _(eure Antwort)_
- **Gegen absichtliche Zerstörung sind die Daten Entwicklung: zusätzlich in einem getrennten Backup-Speicher, den die Administratoren des Systems nicht löschen können; Test: zusätzlich in einem getrennten Backup-Speicher, den die Administratoren des Systems nicht löschen können; Echtbetrieb: zusätzlich in einem getrennten Backup-Speicher, in dem niemand eine Kopie vor ihrem Ablauf ändern oder löschen kann.** _(eure Abweichung)_
- **Die Daten werden nur innerhalb des Wirtschaftsraums der Region, zum Beispiel der EU gespeichert und verarbeitet.** _(eure Antwort)_
- **Der Code wird aus Microsofts geprüften, getesteten Bausteinen (Azure Verified Modules) gebaut.** _(eure Antwort)_
- **Die Ressourcennamen erzeugt das Naming-Werkzeug des Plugins, gesteuert über eine Namensdatei, die ihr anpassen könnt.** _(eure Antwort)_
- **Der Zugang ist privat; nur die benannten Teile sind hinter einer Firewall aus dem Internet erreichbar, alles dahinter bleibt privat.** _(aus eurer Beschreibung)_
- **Einzuhaltende Vorgaben: keine.** _(eure Antwort)_
- **Logs werden Entwicklung: 30; Test: 30; Echtbetrieb: 90 Tage aufbewahrt.** _(aus eurer Beschreibung)_

## Nach den Vorgaben gesetzt

Nichts davon wurde gefragt; jede Zeile folgt einer Regel oder einer der Antworten oben. Sagt Bescheid, wenn eine nicht passt.

### Für das ganze System

- Diese Bereiche erhalten eine eigene Ressourcengruppe: Netzwerk, Daten, Überwachung. Alles andere liegt in der Hauptgruppe.
- Die Hauptressourcengruppe wird zusammen mit dem System angelegt.
- Die Ressourcengruppe für das Netzwerk wird zusammen mit dem System angelegt.
- Die Ressourcengruppe für die Daten wird zusammen mit dem System angelegt.
- Die Ressourcengruppe für die Überwachung wird zusammen mit dem System angelegt.
- Die Pipeline meldet sich mit einem kurzlebigen Token pro Lauf, ohne irgendwo gespeichertes Passwort bei Azure an.
- Eine Person gibt die Änderung frei, bevor sie ausgerollt wird: nur im Echtbetrieb.
- Wer ausrollt, braucht neben dem Recht, die Ressourcen zu ändern: Contributor (subscription). — weil: Die Hauptressourcengruppe wird zusammen mit dem System angelegt.
- Passwörter und Zugriffsschlüssel sind abgeschaltet; der Zugriff läuft über Firmenkonten, damit jede Aktion zuordenbar ist.

### Sicherheit

Die Sicherheitsvorgaben aller Teile an einer Stelle. Sie wurden nicht gefragt und sind in jeder Stufe gleich; sagt Bescheid, wenn eine nicht passt.

- **Azure Front Door (Standard / Premium)**
  - Gepflegte Firewall-Regeln sind angewandt.
- **Azure API Management service**
  - `true`
- **Azure Service Bus namespace**
  - Zugriffsschlüssel und Verbindungszeichenfolgen sind abgeschaltet.
- **Azure Event Grid custom topic**
  - `"managed_identity"`
- **Azure Storage Account**
  - Zugriff mit einem geteilten Schlüssel ist nicht möglich; der Zugriff läuft über Firmenkonten.
- **Azure Key Vault**
  - Der Zugriff auf den Inhalt des Tresors wird über Rollenzuweisungen, wie alles andere in Azure gesteuert.

### Azure Front Door (Standard / Premium)

- Front Door ist die Stufe Premium.
- Backends: application-gateway.

### Azure Application Gateway (v2) with web application firewall

- `"WAF_v2"`
- `["api-management"]`

### Azure API Management service

- Das Gateway ist die Stufe Entwicklung: eine Teststufe ohne Verfügbarkeitszusage; Test: eine Teststufe ohne Verfügbarkeitszusage; Echtbetrieb: Premium, mit Zonen, mehreren Regionen und Netzwerkeinbindung.
- `"Internal"`
- `"entra-id"`
- `"per-subscription"`
- `"function-app"`

### Azure Functions (function app on Flex Consumption or Elastic Premium)

- Die Function App ist aus dem Internet überhaupt nicht erreichbar.

### Azure Service Bus namespace

- `{"subscriptions": ["billing", "shipping", "audit"], "filter": "order-type"}`
- `{"dead_lettering": true, "duplicate_detection": true}`

### Azure Event Hubs namespace

- Der Dienst (namespace) ist aus dem Internet überhaupt nicht erreichbar.
- `4`
- `7`
- `"storage-account"`

### Azure Event Grid custom topic

- `{"source": "storage-account", "destination": "function-app"}`

### Azure Storage Account

- `true`
- Der Speicher ist aus dem Internet überhaupt nicht erreichbar.

### Azure Backup vault

- `{"development": "LRS", "test": "LRS", "production": "GRS"}`
- `true`
- `["storage-account"]`

### Azure Recovery Services vault

- `{"development": "LRS", "test": "LRS", "production": "GRS"}`
- Gelöschte Sicherungen werden ja.

### Azure Log Analytics Workspace

- Logs werden Entwicklung: 30; Test: 30; Echtbetrieb: 90 Tage aufbewahrt.

### Azure Virtual Network

- Das Netz nutzt den Adressbereich Entwicklung: 10.100.0.0/22; Test: 10.100.4.0/22; Echtbetrieb: 10.100.8.0/22.

## Von euch anders entschieden

- Für das ganze System: Gegen absichtliche Zerstörung sind die Daten Entwicklung: zusätzlich in einem getrennten Backup-Speicher, den die Administratoren des Systems nicht löschen können; Test: zusätzlich in einem getrennten Backup-Speicher, den die Administratoren des Systems nicht löschen können; Echtbetrieb: zusätzlich in einem getrennten Backup-Speicher, in dem niemand eine Kopie vor ihrem Ablauf ändern oder löschen kann. _(Grund: Customer named the stage split explicitly - immutable in production, isolated in development and test.)_
- Azure Front Door (Standard / Premium): Front Door erreicht die Backends über die öffentlichen Adressen der Backends. _(Grund: Application Gateway has no Private Link origin; it is locked to the AzureFrontDoor.Backend tag and the X-Azure-FDID header.)_
- Azure Application Gateway (v2) with web application firewall: Das Gateway nimmt Anfragen aus dem Internet entgegen. _(Grund: Reached by Front Door over its public IP, restricted to the AzureFrontDoor.Backend service tag and the X-Azure-FDID header.)_
- Azure Service Bus namespace: Der Namensraum ist die Stufe Entwicklung: Standard, Warteschlangen und Themen auf geteilter Kapazität; Test: Standard, Warteschlangen und Themen auf geteilter Kapazität; Echtbetrieb: Premium, dedizierte Kapazität mit privaten Anbindungen. _(Grund: Customer named the stage split explicitly - Premium in production, Standard otherwise.)_
- Azure Service Bus namespace: Der Dienst (namespace) ist Entwicklung: firewalled; Test: firewalled; Echtbetrieb: aus dem Internet überhaupt nicht erreichbar. _(Grund: Standard has no private endpoint; the customer chose a firewalled public endpoint in development and test.)_
- Azure Backup vault: Wiederherstellung in der Partnerregion ist Entwicklung: nicht möglich; Test: nicht möglich; Echtbetrieb: möglich. _(Grund: Customer asked for cross-region restore in production only.)_
- Azure Recovery Services vault: Wiederherstellung in der Partnerregion ist Entwicklung: nicht möglich; Test: nicht möglich; Echtbetrieb: möglich. _(Grund: Customer asked for cross-region restore in production only.)_

## Noch offen

Solange diese Punkte offen sind, wird nichts ausgerollt.

- In welche Subscription wird jede Stufe ausgerollt? [Entwicklung, Test, Echtbetrieb] _(gebraucht von: Workload-Owner)_ — blockiert: apply
- Wem gehören die privaten DNS-Zonen, und gibt es zentrale? _(gebraucht von: Plattform-Team)_ — blockiert: apply

## Anhang: alle Entscheidungen

| Schlüssel | Wert | Quelle |
|---|---|---|
| `deployment.resource_group_split` | ["network", "data", "observability"] | eure Antwort |
| `deployment.resource_group_mode_main` | create | eure Antwort |
| `deployment.resource_group_mode_network` | create | eure Antwort |
| `deployment.resource_group_mode_data` | create | eure Antwort |
| `deployment.resource_group_mode_observability` | create | eure Antwort |
| `deployment.resource_lock` | production | eure Antwort |
| `deployment.deploy_mechanism` | github | eure Antwort |
| `deployment.pipeline_auth` | workload_identity | Regel |
| `deployment.pipeline_approvals` | production | Regel |
| `deployment.deployer_roles` | [{"role": "Contributor", "scope": "subscription", "for": ["deployment.resource_group_mode_main", "deployment.resource_group_mode_network", "deployment.resource_group_mode_data", "deployment.resource_group_mode_observability"]}] | erzwungen |
| `deployment.network_requirements` | free | eure Antwort |
| `deployment.outage_impact` | tolerable | eure Antwort |
| `deployment.data_loss_tolerance` | one_month | eure Antwort |
| `deployment.data_access_pattern` | active | eure Antwort |
| `deployment.backup_isolation` | {"development": "isolated", "test": "isolated", "production": "immutable"} | eure Abweichung |
| `deployment.data_residency` | data_zone | eure Antwort |
| `deployment.module_source` | avm | eure Antwort |
| `deployment.naming_source` | provider | eure Antwort |
| `deployment.network_exposure` | private_with_exceptions | eure Beschreibung |
| `deployment.local_auth` | disabled | eure Beschreibung |
| `deployment.mandates` | [] | eure Antwort |
| `deployment.log_retention_days` | {"development": 30, "test": 30, "production": 90} | eure Beschreibung |
| `front-door.placement.sku` | Premium | eure Beschreibung |
| `front-door.security.waf_managed_rules` | true | eure Beschreibung |
| `front-door.networking.origin_connection` | public | eure Abweichung |
| `front-door.networking.origins` | ["application-gateway"] | eure Beschreibung |
| `application-gateway.placement.sku` | WAF_v2 | eure Beschreibung |
| `application-gateway.networking.frontend_exposure` | public | eure Abweichung |
| `application-gateway.networking.backends` | ["api-management"] | eure Beschreibung |
| `api-management.placement.sku` | {"development": "Developer", "test": "Developer", "production": "Premium"} | eure Beschreibung |
| `api-management.networking.virtual_network_type` | Internal | eure Beschreibung |
| `api-management.identity.system_assigned_identity` | true | eure Beschreibung |
| `api-management.policies.jwt_validation` | entra-id | eure Beschreibung |
| `api-management.policies.rate_limit` | per-subscription | eure Beschreibung |
| `api-management.policies.backend_routing` | function-app | eure Beschreibung |
| `function-app.networking.public_network_access` | disabled | übernommen |
| `service-bus.placement.sku` | {"development": "Standard", "test": "Standard", "production": "Premium"} | eure Abweichung |
| `service-bus.networking.public_network_access` | {"development": "firewalled", "test": "firewalled", "production": "disabled"} | eure Abweichung |
| `service-bus.security.local_auth` | disabled | eure Beschreibung |
| `service-bus.topics.orders` | {"subscriptions": ["billing", "shipping", "audit"], "filter": "order-type"} | eure Beschreibung |
| `service-bus.queues.payments` | {"dead_lettering": true, "duplicate_detection": true} | eure Beschreibung |
| `event-hubs.networking.public_network_access` | disabled | übernommen |
| `event-hubs.data.partitions` | 4 | eure Beschreibung |
| `event-hubs.data.retention_days` | 7 | eure Beschreibung |
| `event-hubs.data.capture` | storage-account | eure Beschreibung |
| `event-grid-topic.identity.delivery_auth` | managed_identity | eure Beschreibung |
| `event-grid-topic.subscriptions.blob-events` | {"source": "storage-account", "destination": "function-app"} | eure Beschreibung |
| `storage-account.placement.hierarchical_namespace` | true | eure Beschreibung |
| `storage-account.networking.public_network_access` | disabled | übernommen |
| `storage-account.security.shared_access_key_enabled` | false | übernommen |
| `backup-vault.data_protection.redundancy` | {"development": "LRS", "test": "LRS", "production": "GRS"} | eure Beschreibung |
| `backup-vault.data_protection.cross_region_restore` | {"development": false, "test": false, "production": true} | eure Abweichung |
| `backup-vault.data_protection.soft_delete` | true | eure Beschreibung |
| `backup-vault.data_protection.protects` | ["storage-account"] | eure Beschreibung |
| `recovery-services-vault.data_protection.redundancy` | {"development": "LRS", "test": "LRS", "production": "GRS"} | eure Beschreibung |
| `recovery-services-vault.data_protection.cross_region_restore` | {"development": false, "test": false, "production": true} | eure Abweichung |
| `recovery-services-vault.data_protection.soft_delete` | true | eure Beschreibung |
| `log-analytics-workspace.data_protection.retention_days` | {"development": 30, "test": 30, "production": 90} | eure Beschreibung |
| `key-vault.security.rbac_authorization` | true | übernommen |
| `virtual-network.networking.address_space` | {"development": "10.100.0.0/22", "test": "10.100.4.0/22", "production": "10.100.8.0/22"} | eure Antwort |
| `wiring.access` | [{"from": "internet", "to": "front-door", "label": "HTTPS 443"}, {"from": "front-door", "to": "application-gateway", "label": "HTTPS, nur Front Door"}, {"from": "application-gateway", "to": "api-management", "label": "HTTPS intern"}, {"from": "api-management", "to": "function-app", "label": "Backend-Routing"}, {"from": "function-app", "to": "service-bus", "label": "Entra-Login"}, {"from": "event-hubs", "to": "storage-account", "label": "Capture"}, {"from": "event-grid-topic", "to": "function-app", "label": "Blob-Events"}, {"from": "storage-account", "to": "event-grid-topic", "label": "Blob-Events"}, {"from": "backup-vault", "to": "storage-account", "label": "Blob-Backup"}] | eure Beschreibung |
| `wiring.purposes` | {"front-door": "Öffentlicher Eingang mit WAF", "application-gateway": "WAF vor APIM", "api-management": "API-Schicht", "function-app": "Bestell-Backend", "service-bus": "Bestellnachrichten", "event-hubs": "Telemetrie", "event-grid-topic": "Blob-Events", "storage-account": "Telemetrie-Ablage", "backup-vault": "Blob-Backup", "recovery-services-vault": "VM-Backup", "log-analytics-workspace": "Zentrale Logs", "key-vault": "Secrets"} | eure Beschreibung |
