# Entscheidungen für „orders“

Was gebaut wird, entschieden aus euren Antworten und den Regeln hinter den Vorgaben. Jede Zeile ist eine Entscheidung; der Schlüssel im Anhang ist, wo ein Engineer sie in der Spezifikation findet.

Stand 2026-10-25. Spezifikation: `infra-spec.yaml`.

## Das System

- Das System wird in diesen Stufen ausgerollt: Entwicklung, Test, Echtbetrieb.
- Alles läuft in der Azure-Region germanywestcentral.
- „orders“ ist der Name, den jeder Teil des Systems trägt.
- Jede Stufe liegt in einer eigenen Subscription; die Stufen können sich gegenseitig weder Ressourcen noch Budgets noch Berechtigungen anfassen.

## Was sich zwischen den Stufen unterscheidet

Ein Code wird durch diese Stufen ausgerollt; alles, was hier nicht steht, ist in jeder Stufe gleich.

- Das System wird in die Subscription Entwicklung: 00000000-0000-0000-0000-00000000dev1; Test: 00000000-0000-0000-0000-00000000tst1; Echtbetrieb: 00000000-0000-0000-0000-00000000prd1 ausgerollt.
- Alle Teile liegen in der bestehenden Ressourcengruppe Entwicklung: rg-orders-dev-gwc; Test: rg-orders-test-gwc; Echtbetrieb: rg-orders-prod-gwc.
- Das neue Netz nutzt den Adressbereich Entwicklung: 10.100.0.0/23; Test: 10.101.0.0/23; Echtbetrieb: 10.102.0.0/23.
- Private Anbindungen bekommen ein eigenes Subnetz, Entwicklung: 10.100.0.0/27; Test: 10.101.0.0/27; Echtbetrieb: 10.102.0.0/27.
- Logs werden in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace gesammelt.
- Logs werden Entwicklung: 30; Test: 30; Echtbetrieb: 90 Tage aufbewahrt.
- Azure Log Analytics Workspace: Logs werden Entwicklung: 30; Test: 30; Echtbetrieb: 90 Tage aufbewahrt.
- Azure Virtual Network: Das Netz nutzt den Adressbereich Entwicklung: 10.100.0.0/23; Test: 10.101.0.0/23; Echtbetrieb: 10.102.0.0/23.
- Azure Virtual Network: Subnetze: Entwicklung: snet-endpoints (10.100.0.0/27), snet-apim (10.100.0.32/27), snet-func (10.100.0.64/26), snet-gateway (10.100.1.0/24); Test: snet-endpoints (10.101.0.0/27), snet-apim (10.101.0.32/27), snet-func (10.101.0.64/26), snet-gateway (10.101.1.0/24); Echtbetrieb: snet-endpoints (10.102.0.0/27), snet-apim (10.102.0.32/27), snet-func (10.102.0.64/26), snet-gateway (10.102.1.0/24).
- Azure Virtual Network: Private Anbindungen bekommen das Subnetz Entwicklung: 10.100.0.0/27; Test: 10.101.0.0/27; Echtbetrieb: 10.102.0.0/27.
- Azure Virtual Network: Eigene Namensserver: Entwicklung: keine; Test: keine; Echtbetrieb: keine (keine: Azures eigene).
- Azure Virtual Network: Subnetze, die eine Sicherheitsgruppe bekommen: Entwicklung: snet-endpoints, snet-apim, snet-func, snet-gateway; Test: snet-endpoints, snet-apim, snet-func, snet-gateway; Echtbetrieb: snet-endpoints, snet-apim, snet-func, snet-gateway.
- Azure Virtual Network: Netzwerk-Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Network Security Group (endpoints): Ausdrücklich erlaubter Verkehr: Entwicklung: allow-apim-https priority 100, direction Inbound, protocol Tcp, source 10.100.0.32/27, destination 10.100.0.0/27, port 443, access Allow, allow-function-https priority 110, direction Inbound, protocol Tcp, source 10.100.0.64/26, destination 10.100.0.0/27, port 443, access Allow, allow-function-amqp priority 120, direction Inbound, protocol Tcp, source 10.100.0.64/26, destination 10.100.0.0/27, port 5671-5672, access Allow; Test: allow-apim-https priority 100, direction Inbound, protocol Tcp, source 10.101.0.32/27, destination 10.101.0.0/27, port 443, access Allow, allow-function-https priority 110, direction Inbound, protocol Tcp, source 10.101.0.64/26, destination 10.101.0.0/27, port 443, access Allow, allow-function-amqp priority 120, direction Inbound, protocol Tcp, source 10.101.0.64/26, destination 10.101.0.0/27, port 5671-5672, access Allow; Echtbetrieb: allow-apim-https priority 100, direction Inbound, protocol Tcp, source 10.102.0.32/27, destination 10.102.0.0/27, port 443, access Allow, allow-function-https priority 110, direction Inbound, protocol Tcp, source 10.102.0.64/26, destination 10.102.0.0/27, port 443, access Allow, allow-function-amqp priority 120, direction Inbound, protocol Tcp, source 10.102.0.64/26, destination 10.102.0.0/27, port 5671-5672, access Allow.
- Azure Network Security Group (endpoints): Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Network Security Group (func): Ausdrücklich erlaubter Verkehr: Entwicklung: allow-endpoints-https priority 100, direction Outbound, protocol Tcp, source 10.100.0.64/26, destination 10.100.0.0/27, port 443, access Allow, allow-endpoints-amqp priority 110, direction Outbound, protocol Tcp, source 10.100.0.64/26, destination 10.100.0.0/27, port 5671-5672, access Allow; Test: allow-endpoints-https priority 100, direction Outbound, protocol Tcp, source 10.101.0.64/26, destination 10.101.0.0/27, port 443, access Allow, allow-endpoints-amqp priority 110, direction Outbound, protocol Tcp, source 10.101.0.64/26, destination 10.101.0.0/27, port 5671-5672, access Allow; Echtbetrieb: allow-endpoints-https priority 100, direction Outbound, protocol Tcp, source 10.102.0.64/26, destination 10.102.0.0/27, port 443, access Allow, allow-endpoints-amqp priority 110, direction Outbound, protocol Tcp, source 10.102.0.64/26, destination 10.102.0.0/27, port 5671-5672, access Allow.
- Azure Network Security Group (func): Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Network Security Group (gateway): Ausdrücklich erlaubter Verkehr: Entwicklung: allow-front-door-https priority 100, direction Inbound, protocol Tcp, source AzureFrontDoor.Backend, destination 10.100.1.0/24, port 443, access Allow, allow-gateway-manager priority 110, direction Inbound, protocol Tcp, source GatewayManager, destination 10.100.1.0/24, port 65200-65535, access Allow, allow-load-balancer-probe priority 120, direction Inbound, protocol *, source AzureLoadBalancer, destination 10.100.1.0/24, port *, access Allow, allow-apim-https priority 100, direction Outbound, protocol Tcp, source 10.100.1.0/24, destination 10.100.0.32/27, port 443, access Allow, allow-key-vault-https priority 110, direction Outbound, protocol Tcp, source 10.100.1.0/24, destination AzureKeyVault, port 443, access Allow; Test: allow-front-door-https priority 100, direction Inbound, protocol Tcp, source AzureFrontDoor.Backend, destination 10.101.1.0/24, port 443, access Allow, allow-gateway-manager priority 110, direction Inbound, protocol Tcp, source GatewayManager, destination 10.101.1.0/24, port 65200-65535, access Allow, allow-load-balancer-probe priority 120, direction Inbound, protocol *, source AzureLoadBalancer, destination 10.101.1.0/24, port *, access Allow, allow-apim-https priority 100, direction Outbound, protocol Tcp, source 10.101.1.0/24, destination 10.101.0.32/27, port 443, access Allow, allow-key-vault-https priority 110, direction Outbound, protocol Tcp, source 10.101.1.0/24, destination AzureKeyVault, port 443, access Allow; Echtbetrieb: allow-front-door-https priority 100, direction Inbound, protocol Tcp, source AzureFrontDoor.Backend, destination 10.102.1.0/24, port 443, access Allow, allow-gateway-manager priority 110, direction Inbound, protocol Tcp, source GatewayManager, destination 10.102.1.0/24, port 65200-65535, access Allow, allow-load-balancer-probe priority 120, direction Inbound, protocol *, source AzureLoadBalancer, destination 10.102.1.0/24, port *, access Allow, allow-apim-https priority 100, direction Outbound, protocol Tcp, source 10.102.1.0/24, destination 10.102.0.32/27, port 443, access Allow, allow-key-vault-https priority 110, direction Outbound, protocol Tcp, source 10.102.1.0/24, destination AzureKeyVault, port 443, access Allow.
- Azure Network Security Group (gateway): Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Network Security Group (apim): Ausdrücklich erlaubter Verkehr: Entwicklung: allow-gateway-https priority 100, direction Inbound, protocol Tcp, source 10.100.1.0/24, destination 10.100.0.32/27, port 443, access Allow, allow-apim-management priority 110, direction Inbound, protocol Tcp, source ApiManagement, destination 10.100.0.32/27, port 3443, access Allow, allow-load-balancer priority 120, direction Inbound, protocol Tcp, source AzureLoadBalancer, destination 10.100.0.32/27, port 6390, access Allow, allow-endpoints-https priority 100, direction Outbound, protocol Tcp, source 10.100.0.32/27, destination 10.100.0.0/27, port 443, access Allow, allow-storage priority 110, direction Outbound, protocol Tcp, source 10.100.0.32/27, destination Storage, port 443, access Allow, allow-sql priority 120, direction Outbound, protocol Tcp, source 10.100.0.32/27, destination Sql, port 1433, access Allow, allow-key-vault priority 130, direction Outbound, protocol Tcp, source 10.100.0.32/27, destination AzureKeyVault, port 443, access Allow, allow-monitor priority 140, direction Outbound, protocol Tcp, source 10.100.0.32/27, destination AzureMonitor, port 443,1886, access Allow; Test: allow-gateway-https priority 100, direction Inbound, protocol Tcp, source 10.101.1.0/24, destination 10.101.0.32/27, port 443, access Allow, allow-apim-management priority 110, direction Inbound, protocol Tcp, source ApiManagement, destination 10.101.0.32/27, port 3443, access Allow, allow-load-balancer priority 120, direction Inbound, protocol Tcp, source AzureLoadBalancer, destination 10.101.0.32/27, port 6390, access Allow, allow-endpoints-https priority 100, direction Outbound, protocol Tcp, source 10.101.0.32/27, destination 10.101.0.0/27, port 443, access Allow, allow-storage priority 110, direction Outbound, protocol Tcp, source 10.101.0.32/27, destination Storage, port 443, access Allow, allow-sql priority 120, direction Outbound, protocol Tcp, source 10.101.0.32/27, destination Sql, port 1433, access Allow, allow-key-vault priority 130, direction Outbound, protocol Tcp, source 10.101.0.32/27, destination AzureKeyVault, port 443, access Allow, allow-monitor priority 140, direction Outbound, protocol Tcp, source 10.101.0.32/27, destination AzureMonitor, port 443,1886, access Allow; Echtbetrieb: allow-gateway-https priority 100, direction Inbound, protocol Tcp, source 10.102.1.0/24, destination 10.102.0.32/27, port 443, access Allow, allow-apim-management priority 110, direction Inbound, protocol Tcp, source ApiManagement, destination 10.102.0.32/27, port 3443, access Allow, allow-load-balancer priority 120, direction Inbound, protocol Tcp, source AzureLoadBalancer, destination 10.102.0.32/27, port 6390, access Allow, allow-endpoints-https priority 100, direction Outbound, protocol Tcp, source 10.102.0.32/27, destination 10.102.0.0/27, port 443, access Allow, allow-storage priority 110, direction Outbound, protocol Tcp, source 10.102.0.32/27, destination Storage, port 443, access Allow, allow-sql priority 120, direction Outbound, protocol Tcp, source 10.102.0.32/27, destination Sql, port 1433, access Allow, allow-key-vault priority 130, direction Outbound, protocol Tcp, source 10.102.0.32/27, destination AzureKeyVault, port 443, access Allow, allow-monitor priority 140, direction Outbound, protocol Tcp, source 10.102.0.32/27, destination AzureMonitor, port 443,1886, access Allow.
- Azure Network Security Group (apim): Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure user-assigned managed identity (func): Rechte an der Identität selbst vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Azure user-assigned managed identity (gateway): Rechte an der Identität selbst vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Azure Key Vault: Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure Key Vault: Zugriffsrechte auf den Tresor vergeben an: Entwicklung: user-assigned-identity__gateway (Key Vault Secrets User), user-assigned-identity__func (Key Vault Secrets User), api-management (Key Vault Secrets User); Test: user-assigned-identity__gateway (Key Vault Secrets User), user-assigned-identity__func (Key Vault Secrets User), api-management (Key Vault Secrets User); Echtbetrieb: user-assigned-identity__gateway (Key Vault Secrets User), user-assigned-identity__func (Key Vault Secrets User), api-management (Key Vault Secrets User).
- Azure Key Vault: Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Storage Account (orders): Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure Storage Account (orders): Zugriffsrechte vergeben an: Entwicklung: backup-vault (Storage Account Backup Contributor), event-grid-topic (Storage Blob Data Contributor); Test: backup-vault (Storage Account Backup Contributor), event-grid-topic (Storage Blob Data Contributor); Echtbetrieb: backup-vault (Storage Account Backup Contributor), event-grid-topic (Storage Blob Data Contributor).
- Azure Storage Account (orders): Die Daten liegen Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Echtbetrieb: in drei Rechenzentren der Region, eines darf ausfallen. _(außerhalb der Produktion günstiger)_
- Azure Storage Account (orders): Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Storage Account (lake): Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure Storage Account (lake): Zugriffsrechte vergeben an: Entwicklung: event-hubs (Storage Blob Data Contributor); Test: event-hubs (Storage Blob Data Contributor); Echtbetrieb: event-hubs (Storage Blob Data Contributor).
- Azure Storage Account (lake): Die Daten liegen Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Echtbetrieb: in drei Rechenzentren der Region, eines darf ausfallen. _(außerhalb der Produktion günstiger)_
- Azure Storage Account (lake): Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Storage Account (host): Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure Storage Account (host): Zugriffsrechte vergeben an: Entwicklung: user-assigned-identity__func (Storage Blob Data Owner); Test: user-assigned-identity__func (Storage Blob Data Owner); Echtbetrieb: user-assigned-identity__func (Storage Blob Data Owner).
- Azure Storage Account (host): Die Daten liegen Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Echtbetrieb: in drei Rechenzentren der Region, eines darf ausfallen. _(außerhalb der Produktion günstiger)_
- Azure Storage Account (host): Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Storage blob container (orders): Gespeicherte Dateien sind Entwicklung: wie jede andere Datei änderbar; Test: wie jede andere Datei änderbar; Echtbetrieb: gegen Änderung und Löschen gesperrt. _(außerhalb der Produktion günstiger)_
- Azure Storage blob container (orders): Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Azure Storage blob container (lake): Gespeicherte Dateien sind Entwicklung: wie jede andere Datei änderbar; Test: wie jede andere Datei änderbar; Echtbetrieb: gegen Änderung und Löschen gesperrt. _(außerhalb der Produktion günstiger)_
- Azure Storage blob container (lake): Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Azure Functions (function app on Flex Consumption or Elastic Premium): Die Function App Entwicklung: übersteht nicht; Test: übersteht nicht; Echtbetrieb: übersteht den Ausfall eines Rechenzentrums der Region. _(außerhalb der Produktion günstiger)_
- Azure Functions (function app on Flex Consumption or Elastic Premium): Entwicklung: 0; Test: 0; Echtbetrieb: 1 Instanz(en) werden vorgewärmt gehalten, damit der erste Aufruf nicht wartet. _(außerhalb der Produktion günstiger)_
- Azure Functions (function app on Flex Consumption or Elastic Premium): Die Function App hält ihren eigenen Zustand im Speicherkonto Entwicklung: storage-account__host; Test: storage-account__host; Echtbetrieb: storage-account__host.
- Azure Functions (function app on Flex Consumption or Elastic Premium): Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure Functions (function app on Flex Consumption or Elastic Premium): Ausgehender Verkehr verlässt das Netz über das Subnetz Entwicklung: snet-func; Test: snet-func; Echtbetrieb: snet-func.
- Azure Functions (function app on Flex Consumption or Elastic Premium): Öffentliche Adressen, die die Function App erreichen dürfen: Entwicklung: service_tag: AzureEventGrid; Test: service_tag: AzureEventGrid; Echtbetrieb: service_tag: AzureEventGrid.
- Azure Functions (function app on Flex Consumption or Elastic Premium): Es nutzt die Identität Entwicklung: user-assigned-identity__func; Test: user-assigned-identity__func; Echtbetrieb: user-assigned-identity__func.
- Azure Functions (function app on Flex Consumption or Elastic Premium): Verwaltungsrechte an der Function App vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Azure Functions (function app on Flex Consumption or Elastic Premium): Seine Anwendungstelemetrie geht an Entwicklung: ; Test: ; Echtbetrieb:  (leer: keine).
- Azure Functions (function app on Flex Consumption or Elastic Premium): Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure API Management service: Das Gateway ist die Stufe Entwicklung: eine Teststufe ohne Verfügbarkeitszusage; Test: eine Teststufe ohne Verfügbarkeitszusage; Echtbetrieb: Premium, mit Zonen, mehreren Regionen und Netzwerkeinbindung.
- Azure API Management service: Läuft zusätzlich in den Regionen Entwicklung: keine; Test: keine; Echtbetrieb: keine (leer: keine).
- Azure API Management service: Das Gateway liegt im Subnetz Entwicklung: snet-apim; Test: snet-apim; Echtbetrieb: snet-apim.
- Azure API Management service: Das Gateway nutzt die öffentliche Adresse Entwicklung: pip-apim; Test: pip-apim; Echtbetrieb: pip-apim.
- Azure API Management service: Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure API Management service: Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Azure API Management service: Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Service Bus namespace: Der Namensraum ist die Stufe Entwicklung: Standard, Warteschlangen und Themen auf geteilter Kapazität; Test: Standard, Warteschlangen und Themen auf geteilter Kapazität; Echtbetrieb: Premium, dedizierte Kapazität mit privaten Anbindungen.
- Azure Service Bus namespace: Die Nachrichtenverarbeitung übersteht den Ausfall eines Rechenzentrums: Entwicklung: überstehen nicht; Test: überstehen nicht; Echtbetrieb: überstehen. _(außerhalb der Produktion günstiger)_
- Azure Service Bus namespace: Der Dienst (namespace) ist Entwicklung: aus dem Internet nur von gelisteten Adressen erreichbar; Test: aus dem Internet nur von gelisteten Adressen erreichbar; Echtbetrieb: aus dem Internet überhaupt nicht erreichbar.
- Azure Service Bus namespace: Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure Service Bus namespace: Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Azure Service Bus namespace: Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Event Hubs namespace: Das Archiv geht in das Speicherkonto Entwicklung: storage-account__lake; Test: storage-account__lake; Echtbetrieb: storage-account__lake.
- Azure Event Hubs namespace: Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure Event Hubs namespace: Der Datenstrom übersteht den Ausfall eines Rechenzentrums: Entwicklung: überstehen nicht; Test: überstehen nicht; Echtbetrieb: überstehen. _(außerhalb der Produktion günstiger)_
- Azure Event Hubs namespace: Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Azure Event Hubs namespace: Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Event Grid custom topic: Nicht zustellbare Ereignisse gehen in das Speicherkonto Entwicklung: storage-account__orders; Test: storage-account__orders; Echtbetrieb: storage-account__orders.
- Azure Event Grid custom topic: Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure Event Grid custom topic: Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Azure Event Grid custom topic: Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Backup vault: Die Sicherungen werden Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Echtbetrieb: zusätzlich in einer zweiten Region aufbewahrt. _(außerhalb der Produktion günstiger)_
- Azure Backup vault: Sicherungen sind Entwicklung: vor Änderung geschützt, der Schutz lässt sich aber noch abschalten; Test: vor Änderung geschützt, der Schutz lässt sich aber noch abschalten; Echtbetrieb: bis zum Ablauf für alle endgültig geschützt. _(außerhalb der Produktion günstiger)_
- Azure Backup vault: Das Löschen von Sicherungen Entwicklung: braucht keine zweite Freigabe; Test: braucht keine zweite Freigabe; Echtbetrieb: braucht die Freigabe eines zweiten Teams. _(außerhalb der Produktion günstiger)_
- Azure Backup vault: Eine Sicherung wird Entwicklung: 7; Test: 7; Echtbetrieb: 30 Tage aufbewahrt. _(außerhalb der Produktion günstiger)_
- Azure Backup vault: Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Azure Backup vault: Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Recovery Services vault: Die Sicherungen werden Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Echtbetrieb: zusätzlich in einer zweiten Region aufbewahrt. _(außerhalb der Produktion günstiger)_
- Azure Recovery Services vault: Sicherungen sind Entwicklung: vor Änderung geschützt, der Schutz lässt sich aber noch abschalten; Test: vor Änderung geschützt, der Schutz lässt sich aber noch abschalten; Echtbetrieb: bis zum Ablauf für alle endgültig geschützt. _(außerhalb der Produktion günstiger)_
- Azure Recovery Services vault: Das Löschen von Sicherungen Entwicklung: braucht keine zweite Freigabe; Test: braucht keine zweite Freigabe; Echtbetrieb: braucht die Freigabe eines zweiten Teams. _(außerhalb der Produktion günstiger)_
- Azure Recovery Services vault: Eine Sicherung wird Entwicklung: 7; Test: 7; Echtbetrieb: 30 Tage aufbewahrt. _(außerhalb der Produktion günstiger)_
- Azure Recovery Services vault: Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints.
- Azure Recovery Services vault: Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Azure Recovery Services vault: Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Front Door (Standard / Premium): Backends: Entwicklung: origin: application-gateway, route: /*; Test: origin: application-gateway, route: /*; Echtbetrieb: origin: application-gateway, route: /*.
- Azure Front Door (Standard / Premium): Hostnamen: Entwicklung: keine; Test: keine; Echtbetrieb: keine (leer: nur der erzeugte *.azurefd.net-Name).
- Azure Front Door (Standard / Premium): Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Azure Application Gateway (v2) with web application firewall: Mindestens Entwicklung: 1; Test: 1; Echtbetrieb: 2 Instanz(en) laufen immer. _(außerhalb der Produktion günstiger)_
- Azure Application Gateway (v2) with web application firewall: Es wächst auf höchstens Entwicklung: 2; Test: 2; Echtbetrieb: 10 Instanzen. _(außerhalb der Produktion günstiger)_
- Azure Application Gateway (v2) with web application firewall: Das Gateway übersteht den Ausfall eines Rechenzentrums: Entwicklung: überstehen nicht; Test: überstehen nicht; Echtbetrieb: überstehen. _(außerhalb der Produktion günstiger)_
- Azure Application Gateway (v2) with web application firewall: Das Gateway nutzt das Subnetz Entwicklung: snet-gateway; Test: snet-gateway; Echtbetrieb: snet-gateway.
- Azure Application Gateway (v2) with web application firewall: Es nutzt die Identität Entwicklung: user-assigned-identity__gateway; Test: user-assigned-identity__gateway; Echtbetrieb: user-assigned-identity__gateway.
- Azure Application Gateway (v2) with web application firewall: Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.

## Was aus euren Antworten folgt

- **Ressourcen, die Daten halten, tragen in der Produktion eine Löschsperre.** _(nicht gesagt, daher gilt die übliche Antwort)_
- **Das Netz wird von diesem Ausrollen frei gewählt, ohne Verbindung zum Firmennetz und ohne VPN.** _(nicht gesagt, daher gilt die übliche Antwort)_
- **Ein Tag Ausfall wäre störend.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure Storage Account (orders): Die Daten liegen Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Echtbetrieb: in drei Rechenzentren der Region, eines darf ausfallen.
  - daher, Azure Storage Account (lake): Die Daten liegen Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Echtbetrieb: in drei Rechenzentren der Region, eines darf ausfallen.
  - daher, Azure Storage Account (host): Die Daten liegen Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Echtbetrieb: in drei Rechenzentren der Region, eines darf ausfallen.
  - daher, Azure Functions (function app on Flex Consumption or Elastic Premium): Die Function App Entwicklung: übersteht nicht; Test: übersteht nicht; Echtbetrieb: übersteht den Ausfall eines Rechenzentrums der Region.
  - daher, Azure Functions (function app on Flex Consumption or Elastic Premium): Entwicklung: 0; Test: 0; Echtbetrieb: 1 Instanz(en) werden vorgewärmt gehalten, damit der erste Aufruf nicht wartet.
  - daher, Azure Service Bus namespace: Die Nachrichtenverarbeitung übersteht den Ausfall eines Rechenzentrums: Entwicklung: überstehen nicht; Test: überstehen nicht; Echtbetrieb: überstehen.
  - daher, Azure Service Bus namespace: Für den Ausfall einer ganzen Region gibt es keine Ausweichregion.
  - daher, Azure Event Hubs namespace: Der Datenstrom übersteht den Ausfall eines Rechenzentrums: Entwicklung: überstehen nicht; Test: überstehen nicht; Echtbetrieb: überstehen.
  - daher, Azure Event Hubs namespace: Für den Ausfall einer ganzen Region gibt es keine Ausweichregion.
  - daher, Azure Application Gateway (v2) with web application firewall: Mindestens Entwicklung: 1; Test: 1; Echtbetrieb: 2 Instanz(en) laufen immer.
  - daher, Azure Application Gateway (v2) with web application firewall: Das Gateway übersteht den Ausfall eines Rechenzentrums: Entwicklung: überstehen nicht; Test: überstehen nicht; Echtbetrieb: überstehen.
- **Nach einem versehentlichen Löschen müsst ihr eine Woche zurückkommen.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure Storage Account (orders): Gelöschte Dateien sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account (orders): Gelöschte Ordner sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account (orders): Frühere Versionen überschriebener Dateien werden aufgehoben.
  - daher, Azure Storage Account (lake): Gelöschte Dateien sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account (lake): Gelöschte Ordner sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account (lake): Frühere Versionen überschriebener Dateien werden aufgehoben.
  - daher, Azure Storage Account (host): Gelöschte Dateien sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account (host): Gelöschte Ordner sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account (host): Frühere Versionen überschriebener Dateien werden aufgehoben.
  - daher, Azure Backup vault: Eine gelöschte Sicherung lässt sich 14 Tage lang wiederherstellen.
  - daher, Azure Backup vault: Eine Sicherung wird Entwicklung: 7; Test: 7; Echtbetrieb: 30 Tage aufbewahrt.
  - daher, Azure Recovery Services vault: Eine gelöschte Sicherung lässt sich 14 Tage lang wiederherstellen.
  - daher, Azure Recovery Services vault: Eine Sicherung wird Entwicklung: 7; Test: 7; Echtbetrieb: 30 Tage aufbewahrt.
- **Die Daten werden laufend genutzt.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure Storage Account (orders): Gespeichert in der Klasse Standard: günstig beim Lesen, für Daten in Nutzung.
  - daher, Azure Storage Account (lake): Gespeichert in der Klasse Standard: günstig beim Lesen, für Daten in Nutzung.
  - daher, Azure Storage Account (host): Gespeichert in der Klasse Standard: günstig beim Lesen, für Daten in Nutzung.
- **Gegen absichtliche Zerstörung sind die Daten zusätzlich in einem getrennten Backup-Speicher, in dem niemand eine Kopie vor ihrem Ablauf ändern oder löschen kann.** _(aus eurer Beschreibung)_
  - daher, Azure Storage blob container (orders): Gespeicherte Dateien sind Entwicklung: wie jede andere Datei änderbar; Test: wie jede andere Datei änderbar; Echtbetrieb: gegen Änderung und Löschen gesperrt.
  - daher, Azure Storage blob container (lake): Gespeicherte Dateien sind Entwicklung: wie jede andere Datei änderbar; Test: wie jede andere Datei änderbar; Echtbetrieb: gegen Änderung und Löschen gesperrt.
  - daher, Azure Backup vault: Sicherungen sind Entwicklung: vor Änderung geschützt, der Schutz lässt sich aber noch abschalten; Test: vor Änderung geschützt, der Schutz lässt sich aber noch abschalten; Echtbetrieb: bis zum Ablauf für alle endgültig geschützt.
  - daher, Azure Backup vault: Das Löschen von Sicherungen Entwicklung: braucht keine zweite Freigabe; Test: braucht keine zweite Freigabe; Echtbetrieb: braucht die Freigabe eines zweiten Teams.
  - daher, Azure Recovery Services vault: Gelöschte Sicherungen werden eine Zeit lang aufbewahrt und wiederherstellbar, und niemand kann das abschalten.
  - daher, Azure Recovery Services vault: Sicherungen sind Entwicklung: vor Änderung geschützt, der Schutz lässt sich aber noch abschalten; Test: vor Änderung geschützt, der Schutz lässt sich aber noch abschalten; Echtbetrieb: bis zum Ablauf für alle endgültig geschützt.
  - daher, Azure Recovery Services vault: Das Löschen von Sicherungen Entwicklung: braucht keine zweite Freigabe; Test: braucht keine zweite Freigabe; Echtbetrieb: braucht die Freigabe eines zweiten Teams.
- **Die Daten werden nur innerhalb des Wirtschaftsraums der Region, zum Beispiel der EU gespeichert und verarbeitet.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure Event Grid custom topic: Ereignisse bleiben innerhalb der Region und ihrer Partnerregion.
- **Der Code wird aus Microsofts geprüften, getesteten Bausteinen (Azure Verified Modules) gebaut.** _(nicht gesagt, daher gilt die übliche Antwort)_
- **Die Ressourcennamen erzeugt das Naming-Werkzeug des Plugins, gesteuert über eine Namensdatei, die ihr anpassen könnt.** _(nicht gesagt, daher gilt die übliche Antwort)_
- **Der Zugang ist privat, mit benannten Ausnahmen hinter einer Firewall aus dem Internet erreichbar.** _(aus eurer Beschreibung)_
- **Einzuhaltende Vorgaben: keine.** _(nicht gesagt, daher gilt die übliche Antwort)_
- **Logs werden Entwicklung: 30; Test: 30; Echtbetrieb: 90 Tage aufbewahrt.** _(aus eurer Beschreibung)_

## Nach den Vorgaben gesetzt

Nichts davon wurde gefragt; jede Zeile folgt einer Regel oder einer der Antworten oben. Sagt Bescheid, wenn eine nicht passt.

### Für das ganze System

- Nutzungstelemetrie an Microsoft ist ausgeschaltet: eine Zählung pro Ausrollen, keine eurer Daten.
- Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Logging selbst mit.
- Passwörter und Zugriffsschlüssel sind abgeschaltet; der Zugriff läuft über Firmenkonten, damit jede Aktion zuordenbar ist.
- Verschlüsselungsschlüssel sind in Software geschützt, der Standard, ausreichend ohne Vorgabe für Hardware.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Das Netz wird von diesem Ausrollen selbst gebaut.
- Das neue Netz nutzt den Adressbereich Entwicklung: 10.100.0.0/23; Test: 10.101.0.0/23; Echtbetrieb: 10.102.0.0/23.
- Private Anbindungen bekommen ein eigenes Subnetz, Entwicklung: 10.100.0.0/27; Test: 10.101.0.0/27; Echtbetrieb: 10.102.0.0/27.
- Die Namensauflösung für private Anbindungen übernimmt dieses Ausrollen selbst. — weil: Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Logging selbst mit.
- Logs gehen in einen Arbeitsbereich, den dieses Ausrollen anlegt und bezahlt. — weil: Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Logging selbst mit.
- Logs werden in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace gesammelt. — weil: Logs gehen in einen Arbeitsbereich, den dieses Ausrollen anlegt und bezahlt.
- Tägliche Obergrenze für Logs: -1 GB (-1: keine).

### Azure Log Analytics Workspace

- Logs werden Entwicklung: 30; Test: 30; Echtbetrieb: 90 Tage aufbewahrt.
- Tägliche Obergrenze für Logs: -1 GB (-1: keine).
- Abgerechnet pro Gigabyte, nach Verbrauch.
- Der Log-Arbeitsbereich ist aus dem Internet erreichbar, mit Firmenkonten und Verschlüsselung; einen privaten Zugang dafür gibt es nicht.
- Logs mit dem Arbeitsbereichs-Schlüssel zu senden ist nicht möglich, Agenten nutzen Firmenidentitäten.
- Wer Logs lesen darf, entscheiden die Berechtigungen des Arbeitsbereichs selbst.
- Ein gelöschter Arbeitsbereich kann 14 Tage lang wiederhergestellt werden.
- Langzeitarchivierung in günstigen Speicher ist ausgeschaltet.

### Azure Virtual Network

- Das Netz nutzt den Adressbereich Entwicklung: 10.100.0.0/23; Test: 10.101.0.0/23; Echtbetrieb: 10.102.0.0/23.
- Subnetze: Entwicklung: snet-endpoints (10.100.0.0/27), snet-apim (10.100.0.32/27), snet-func (10.100.0.64/26), snet-gateway (10.100.1.0/24); Test: snet-endpoints (10.101.0.0/27), snet-apim (10.101.0.32/27), snet-func (10.101.0.64/26), snet-gateway (10.101.1.0/24); Echtbetrieb: snet-endpoints (10.102.0.0/27), snet-apim (10.102.0.32/27), snet-func (10.102.0.64/26), snet-gateway (10.102.1.0/24).
- Private Anbindungen bekommen das Subnetz Entwicklung: 10.100.0.0/27; Test: 10.101.0.0/27; Echtbetrieb: 10.102.0.0/27.
- Eigene Namensserver: Entwicklung: keine; Test: keine; Echtbetrieb: keine (keine: Azures eigene).
- Netzwerkregeln gelten für private Anbindungen in ihrem Subnetz.
- Abkürzungen zu Azure-Diensten aus den Subnetzen: keine.
- An einen Dienst übergebene Subnetze: snet-func (Microsoft.App/environments). — weil: `resources.function-app.networking.integration_subnet`
- Ein kostenpflichtiger DDoS-Schutzplan wird nicht genutzt; Azures Basisschutz gilt ohnehin.
- Subnetze, die eine Sicherheitsgruppe bekommen: Entwicklung: snet-endpoints, snet-apim, snet-func, snet-gateway; Test: snet-endpoints, snet-apim, snet-func, snet-gateway; Echtbetrieb: snet-endpoints, snet-apim, snet-func, snet-gateway.
- Netzwerk-Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Eine Aufzeichnung erlaubten und abgewiesenen Verkehrs wird nicht geführt.

### Azure Network Security Group (endpoints)

- Die Gruppe schützt ein Subnetz für private Anbindungen an Azure-Dienste.
- Eingehender Verkehr, den keine Regel erlaubt, wird abgelehnt, auch von anderen Maschinen im selben Netz.
- Ausgehender Verkehr ins Internet, den keine Regel erlaubt, wird abgelehnt; was hinaus muss, läuft über die Firmen-Firewall. — weil: `resources.network-security-group__endpoints.rules.subnet_purpose`
- Ausdrücklich erlaubter Verkehr: Entwicklung: allow-apim-https priority 100, direction Inbound, protocol Tcp, source 10.100.0.32/27, destination 10.100.0.0/27, port 443, access Allow, allow-function-https priority 110, direction Inbound, protocol Tcp, source 10.100.0.64/26, destination 10.100.0.0/27, port 443, access Allow, allow-function-amqp priority 120, direction Inbound, protocol Tcp, source 10.100.0.64/26, destination 10.100.0.0/27, port 5671-5672, access Allow; Test: allow-apim-https priority 100, direction Inbound, protocol Tcp, source 10.101.0.32/27, destination 10.101.0.0/27, port 443, access Allow, allow-function-https priority 110, direction Inbound, protocol Tcp, source 10.101.0.64/26, destination 10.101.0.0/27, port 443, access Allow, allow-function-amqp priority 120, direction Inbound, protocol Tcp, source 10.101.0.64/26, destination 10.101.0.0/27, port 5671-5672, access Allow; Echtbetrieb: allow-apim-https priority 100, direction Inbound, protocol Tcp, source 10.102.0.32/27, destination 10.102.0.0/27, port 443, access Allow, allow-function-https priority 110, direction Inbound, protocol Tcp, source 10.102.0.64/26, destination 10.102.0.0/27, port 443, access Allow, allow-function-amqp priority 120, direction Inbound, protocol Tcp, source 10.102.0.64/26, destination 10.102.0.0/27, port 5671-5672, access Allow.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: welche Regel auf welche Maschine angewendet wurde, wie oft jede Regel gegriffen hat.

### Azure Network Security Group (func)

- Die Gruppe schützt ein Subnetz für den ausgehenden Verkehr von Web- und Function-Apps.
- Eingehender Verkehr, den keine Regel erlaubt, wird abgelehnt, auch von anderen Maschinen im selben Netz.
- Ausgehender Verkehr ins Internet, den keine Regel erlaubt, wird den eingebauten Azure-Regeln überlassen, die ihn hinauslassen.
- Ausdrücklich erlaubter Verkehr: Entwicklung: allow-endpoints-https priority 100, direction Outbound, protocol Tcp, source 10.100.0.64/26, destination 10.100.0.0/27, port 443, access Allow, allow-endpoints-amqp priority 110, direction Outbound, protocol Tcp, source 10.100.0.64/26, destination 10.100.0.0/27, port 5671-5672, access Allow; Test: allow-endpoints-https priority 100, direction Outbound, protocol Tcp, source 10.101.0.64/26, destination 10.101.0.0/27, port 443, access Allow, allow-endpoints-amqp priority 110, direction Outbound, protocol Tcp, source 10.101.0.64/26, destination 10.101.0.0/27, port 5671-5672, access Allow; Echtbetrieb: allow-endpoints-https priority 100, direction Outbound, protocol Tcp, source 10.102.0.64/26, destination 10.102.0.0/27, port 443, access Allow, allow-endpoints-amqp priority 110, direction Outbound, protocol Tcp, source 10.102.0.64/26, destination 10.102.0.0/27, port 5671-5672, access Allow.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: welche Regel auf welche Maschine angewendet wurde, wie oft jede Regel gegriffen hat.

### Azure Network Security Group (gateway)

- Die Gruppe schützt ein Subnetz für Workload-Maschinen oder -Dienste.
- Eingehender Verkehr, den keine Regel erlaubt, wird abgelehnt, auch von anderen Maschinen im selben Netz.
- Ausgehender Verkehr ins Internet, den keine Regel erlaubt, wird abgelehnt; was hinaus muss, läuft über die Firmen-Firewall.
- Ausdrücklich erlaubter Verkehr: Entwicklung: allow-front-door-https priority 100, direction Inbound, protocol Tcp, source AzureFrontDoor.Backend, destination 10.100.1.0/24, port 443, access Allow, allow-gateway-manager priority 110, direction Inbound, protocol Tcp, source GatewayManager, destination 10.100.1.0/24, port 65200-65535, access Allow, allow-load-balancer-probe priority 120, direction Inbound, protocol *, source AzureLoadBalancer, destination 10.100.1.0/24, port *, access Allow, allow-apim-https priority 100, direction Outbound, protocol Tcp, source 10.100.1.0/24, destination 10.100.0.32/27, port 443, access Allow, allow-key-vault-https priority 110, direction Outbound, protocol Tcp, source 10.100.1.0/24, destination AzureKeyVault, port 443, access Allow; Test: allow-front-door-https priority 100, direction Inbound, protocol Tcp, source AzureFrontDoor.Backend, destination 10.101.1.0/24, port 443, access Allow, allow-gateway-manager priority 110, direction Inbound, protocol Tcp, source GatewayManager, destination 10.101.1.0/24, port 65200-65535, access Allow, allow-load-balancer-probe priority 120, direction Inbound, protocol *, source AzureLoadBalancer, destination 10.101.1.0/24, port *, access Allow, allow-apim-https priority 100, direction Outbound, protocol Tcp, source 10.101.1.0/24, destination 10.101.0.32/27, port 443, access Allow, allow-key-vault-https priority 110, direction Outbound, protocol Tcp, source 10.101.1.0/24, destination AzureKeyVault, port 443, access Allow; Echtbetrieb: allow-front-door-https priority 100, direction Inbound, protocol Tcp, source AzureFrontDoor.Backend, destination 10.102.1.0/24, port 443, access Allow, allow-gateway-manager priority 110, direction Inbound, protocol Tcp, source GatewayManager, destination 10.102.1.0/24, port 65200-65535, access Allow, allow-load-balancer-probe priority 120, direction Inbound, protocol *, source AzureLoadBalancer, destination 10.102.1.0/24, port *, access Allow, allow-apim-https priority 100, direction Outbound, protocol Tcp, source 10.102.1.0/24, destination 10.102.0.32/27, port 443, access Allow, allow-key-vault-https priority 110, direction Outbound, protocol Tcp, source 10.102.1.0/24, destination AzureKeyVault, port 443, access Allow.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: welche Regel auf welche Maschine angewendet wurde, wie oft jede Regel gegriffen hat.

### Azure Network Security Group (apim)

- Die Gruppe schützt ein Subnetz für Workload-Maschinen oder -Dienste.
- Eingehender Verkehr, den keine Regel erlaubt, wird abgelehnt, auch von anderen Maschinen im selben Netz.
- Ausgehender Verkehr ins Internet, den keine Regel erlaubt, wird abgelehnt; was hinaus muss, läuft über die Firmen-Firewall.
- Ausdrücklich erlaubter Verkehr: Entwicklung: allow-gateway-https priority 100, direction Inbound, protocol Tcp, source 10.100.1.0/24, destination 10.100.0.32/27, port 443, access Allow, allow-apim-management priority 110, direction Inbound, protocol Tcp, source ApiManagement, destination 10.100.0.32/27, port 3443, access Allow, allow-load-balancer priority 120, direction Inbound, protocol Tcp, source AzureLoadBalancer, destination 10.100.0.32/27, port 6390, access Allow, allow-endpoints-https priority 100, direction Outbound, protocol Tcp, source 10.100.0.32/27, destination 10.100.0.0/27, port 443, access Allow, allow-storage priority 110, direction Outbound, protocol Tcp, source 10.100.0.32/27, destination Storage, port 443, access Allow, allow-sql priority 120, direction Outbound, protocol Tcp, source 10.100.0.32/27, destination Sql, port 1433, access Allow, allow-key-vault priority 130, direction Outbound, protocol Tcp, source 10.100.0.32/27, destination AzureKeyVault, port 443, access Allow, allow-monitor priority 140, direction Outbound, protocol Tcp, source 10.100.0.32/27, destination AzureMonitor, port 443,1886, access Allow; Test: allow-gateway-https priority 100, direction Inbound, protocol Tcp, source 10.101.1.0/24, destination 10.101.0.32/27, port 443, access Allow, allow-apim-management priority 110, direction Inbound, protocol Tcp, source ApiManagement, destination 10.101.0.32/27, port 3443, access Allow, allow-load-balancer priority 120, direction Inbound, protocol Tcp, source AzureLoadBalancer, destination 10.101.0.32/27, port 6390, access Allow, allow-endpoints-https priority 100, direction Outbound, protocol Tcp, source 10.101.0.32/27, destination 10.101.0.0/27, port 443, access Allow, allow-storage priority 110, direction Outbound, protocol Tcp, source 10.101.0.32/27, destination Storage, port 443, access Allow, allow-sql priority 120, direction Outbound, protocol Tcp, source 10.101.0.32/27, destination Sql, port 1433, access Allow, allow-key-vault priority 130, direction Outbound, protocol Tcp, source 10.101.0.32/27, destination AzureKeyVault, port 443, access Allow, allow-monitor priority 140, direction Outbound, protocol Tcp, source 10.101.0.32/27, destination AzureMonitor, port 443,1886, access Allow; Echtbetrieb: allow-gateway-https priority 100, direction Inbound, protocol Tcp, source 10.102.1.0/24, destination 10.102.0.32/27, port 443, access Allow, allow-apim-management priority 110, direction Inbound, protocol Tcp, source ApiManagement, destination 10.102.0.32/27, port 3443, access Allow, allow-load-balancer priority 120, direction Inbound, protocol Tcp, source AzureLoadBalancer, destination 10.102.0.32/27, port 6390, access Allow, allow-endpoints-https priority 100, direction Outbound, protocol Tcp, source 10.102.0.32/27, destination 10.102.0.0/27, port 443, access Allow, allow-storage priority 110, direction Outbound, protocol Tcp, source 10.102.0.32/27, destination Storage, port 443, access Allow, allow-sql priority 120, direction Outbound, protocol Tcp, source 10.102.0.32/27, destination Sql, port 1433, access Allow, allow-key-vault priority 130, direction Outbound, protocol Tcp, source 10.102.0.32/27, destination AzureKeyVault, port 443, access Allow, allow-monitor priority 140, direction Outbound, protocol Tcp, source 10.102.0.32/27, destination AzureMonitor, port 443,1886, access Allow.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: welche Regel auf welche Maschine angewendet wurde, wie oft jede Regel gegriffen hat.

### Azure user-assigned managed identity (func)

- Diese Identität gibt es für the function app, to keep its own state in the host storage account and to read secrets.
- Externe Systeme, die als diese Identität handeln dürfen: keine (leer: keine).
- Die Identität kann von Ressourcen in jeder Region aus genutzt werden.
- Rechte an der Identität selbst vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.

### Azure user-assigned managed identity (gateway)

- Diese Identität gibt es für the application gateway, to read its TLS certificates from the key vault.
- Externe Systeme, die als diese Identität handeln dürfen: keine (leer: keine).
- Die Identität kann von Ressourcen in jeder Region aus genutzt werden.
- Rechte an der Identität selbst vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.

### Azure Key Vault

- Der Tresor ist die Stufe Standard, Schlüssel in Software geschützt.
- Ein gelöschter Tresor oder ein gelöschtes Geheimnis lässt sich nicht endgültig löschen, auch nicht von einem Administrator, bevor die Aufbewahrungszeit endet.
- Gelöschte Inhalte des Tresors lassen sich 90 Tage lang wiederherstellen.
- Der Zugriff auf den Inhalt des Tresors wird über Rollenzuweisungen, wie alles andere in Azure gesteuert.
- Der Tresor ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Vertrauenswürdige Azure-Dienste dürfen nicht an der Firewall des Tresors vorbei.
- Zugriffsrechte auf den Tresor vergeben an: Entwicklung: user-assigned-identity__gateway (Key Vault Secrets User), user-assigned-identity__func (Key Vault Secrets User), api-management (Key Vault Secrets User); Test: user-assigned-identity__gateway (Key Vault Secrets User), user-assigned-identity__func (Key Vault Secrets User), api-management (Key Vault Secrets User); Echtbetrieb: user-assigned-identity__gateway (Key Vault Secrets User), user-assigned-identity__func (Key Vault Secrets User), api-management (Key Vault Secrets User).
- Plattformdienste, die aus dem Tresor lesen dürfen: keine (leer: keine).
- Für die Geheimnisse keine werden leere Plätze angelegt; die Werte werden danach von Hand oder von der Anwendung eingetragen.
- Verschlüsselungsschlüssel sind von Azure verwaltet - der Tresor hält dafür keine.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: jeder Lese-, Schreib- und fehlgeschlagene Zugriff auf den Tresor, wie Richtlinien den Tresor bewertet haben.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Storage Account (orders)

- Der Speicher ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Private Anbindungen gibt es für: Dateien (Blob).
- Azures eigene Dienste (Backup, Überwachung) dürfen am Firewall vorbei auf den Speicher zugreifen.
- Der Speicher hat eine eigene Identität, um andere Dienste zu erreichen.
- Zugriffsrechte vergeben an: Entwicklung: backup-vault (Storage Account Backup Contributor), event-grid-topic (Storage Blob Data Contributor); Test: backup-vault (Storage Account Backup Contributor), event-grid-topic (Storage Blob Data Contributor); Echtbetrieb: backup-vault (Storage Account Backup Contributor), event-grid-topic (Storage Blob Data Contributor).
- Zugriff mit einem geteilten Schlüssel ist nicht möglich; der Zugriff läuft über Firmenkonten.
- Verbindungen müssen mindestens TLS 1.2-Verschlüsselung nutzen.
- Unverschlüsselte Verbindungen werden abgewiesen.
- Einzelne Ordner öffentlich lesbar zu machen ist nicht möglich.
- Eine zweite Verschlüsselungsschicht unterhalb des Dienstes ist eingeschaltet.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Dateiübertragung per SFTP ist ausgeschaltet.
- Ein Log jeder Änderung wird nicht geführt.
- Der ganze Speicher lässt sich 0 Tage zurückdrehen (0: gar nicht).
- Löschschutz per Gesetz oder Richtlinie: keiner.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: wer worauf zugegriffen hat.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Storage Account (lake)

- Der Speicher ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Private Anbindungen gibt es für: Dateien (Blob), den Data Lake.
- Azures eigene Dienste (Backup, Überwachung) dürfen am Firewall vorbei auf den Speicher zugreifen.
- Der Speicher hat eine eigene Identität, um andere Dienste zu erreichen.
- Zugriffsrechte vergeben an: Entwicklung: event-hubs (Storage Blob Data Contributor); Test: event-hubs (Storage Blob Data Contributor); Echtbetrieb: event-hubs (Storage Blob Data Contributor).
- Zugriff mit einem geteilten Schlüssel ist nicht möglich; der Zugriff läuft über Firmenkonten.
- Verbindungen müssen mindestens TLS 1.2-Verschlüsselung nutzen.
- Unverschlüsselte Verbindungen werden abgewiesen.
- Einzelne Ordner öffentlich lesbar zu machen ist nicht möglich.
- Eine zweite Verschlüsselungsschicht unterhalb des Dienstes ist eingeschaltet.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Dateiübertragung per SFTP ist ausgeschaltet.
- Ein Log jeder Änderung wird nicht geführt.
- Der ganze Speicher lässt sich 0 Tage zurückdrehen (0: gar nicht).
- Löschschutz per Gesetz oder Richtlinie: keiner.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: wer worauf zugegriffen hat.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Storage Account (host)

- Der Speicher ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Private Anbindungen gibt es für: Dateien (Blob).
- Azures eigene Dienste (Backup, Überwachung) dürfen am Firewall vorbei auf den Speicher zugreifen.
- Der Speicher hat eine eigene Identität, um andere Dienste zu erreichen.
- Zugriffsrechte vergeben an: Entwicklung: user-assigned-identity__func (Storage Blob Data Owner); Test: user-assigned-identity__func (Storage Blob Data Owner); Echtbetrieb: user-assigned-identity__func (Storage Blob Data Owner).
- Zugriff mit einem geteilten Schlüssel ist nicht möglich; der Zugriff läuft über Firmenkonten.
- Verbindungen müssen mindestens TLS 1.2-Verschlüsselung nutzen.
- Unverschlüsselte Verbindungen werden abgewiesen.
- Einzelne Ordner öffentlich lesbar zu machen ist nicht möglich.
- Eine zweite Verschlüsselungsschicht unterhalb des Dienstes ist eingeschaltet.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Dateiübertragung per SFTP ist ausgeschaltet.
- Ein Log jeder Änderung wird nicht geführt.
- Der ganze Speicher lässt sich 0 Tage zurückdrehen (0: gar nicht).
- Löschschutz per Gesetz oder Richtlinie: keiner.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: wer worauf zugegriffen hat.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Storage blob container (orders)

- Container: eventgrid-deadletter.
- Anonymes Lesen ist nicht erlaubt, jeder meldet sich an.
- Absender, die einen anderen Schlüsselbereich wählen, werden erlaubt.
- Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.

### Azure Storage blob container (lake)

- Container: eventhub-capture. — weil: `resources.event-hubs.entities.event_archive`
- Anonymes Lesen ist nicht erlaubt, jeder meldet sich an.
- Absender, die einen anderen Schlüsselbereich wählen, werden erlaubt.
- Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.

### Azure Functions (function app on Flex Consumption or Elastic Premium)

- Die Function App läuft auf Kapazität, die von null aus skaliert und nach Nutzung abgerechnet wird, mit privatem Netz und optional vorgewärmten Instanzen.
- Die Function App darf auf höchstens 20 Instanzen skalieren.
- Jede Instanz bekommt 2048 MB Arbeitsspeicher.
- Die Function App hält ihren eigenen Zustand im Speicherkonto Entwicklung: storage-account__host; Test: storage-account__host; Echtbetrieb: storage-account__host.
- Die Function App meldet sich an ihrem Speicher an mit ihrer verwalteten Identität, ohne gespeichertes Geheimnis.
- Der ausgerollte Code liegt im Container app-package.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Der ausgehende Verkehr der Function App läuft durch das Firmennetz, so erreicht sie private Dienste.
- Ausgehender Verkehr verlässt das Netz über das Subnetz Entwicklung: snet-func; Test: snet-func; Echtbetrieb: snet-func. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Ausgehender Verkehr wird komplett durch das Firmennetz geleitet, auch ins Internet geleitet.
- Öffentliche Adressen, die die Function App erreichen dürfen: Entwicklung: service_tag: AzureEventGrid; Test: service_tag: AzureEventGrid; Echtbetrieb: service_tag: AzureEventGrid.
- Die Function App hat eine gemeinsame, separat verwaltete Identität, um andere Dienste zu erreichen.
- Es nutzt die Identität Entwicklung: user-assigned-identity__func; Test: user-assigned-identity__func; Echtbetrieb: user-assigned-identity__func.
- Verwaltungsrechte an der Function App vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Unverschlüsselte Verbindungen werden auf die verschlüsselte Adresse umgeleitet.
- Verbindungen müssen mindestens TLS 1.2-Verschlüsselung nutzen.
- Das Ausrollen mit Benutzername und Passwort ist nicht möglich; Rollouts laufen über Firmenkonten.
- Seine Anwendungstelemetrie geht an Entwicklung: ; Test: ; Echtbetrieb:  (leer: keine).
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: was die Funktionen in ihr Log schreiben, wer sich zum Ausrollen oder Verwalten angemeldet hat.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure API Management service

- Das Gateway ist die Stufe Entwicklung: eine Teststufe ohne Verfügbarkeitszusage; Test: eine Teststufe ohne Verfügbarkeitszusage; Echtbetrieb: Premium, mit Zonen, mehreren Regionen und Netzwerkeinbindung.
- Die Instanz reserviert 1 Skalierungseinheit(en).
- Das Gateway übersteht den Ausfall eines Rechenzentrums: überstehen nicht.
- Läuft zusätzlich in den Regionen Entwicklung: keine; Test: keine; Echtbetrieb: keine (leer: keine).
- Die Instanz hat eine eigene Identität.
- Ein Aufrufer darf 600 Aufrufe pro Minute machen (0: keine Grenze).
- Ein Entwicklerportal ist nicht bereitgestellt.
- APIs: orders path orders, backend function-app (leer: noch keine).
- Konsumentengruppen: keine (leer: keine).
- Das Gateway ist nur im privaten Netz.
- Das Gateway liegt im Subnetz Entwicklung: snet-apim; Test: snet-apim; Echtbetrieb: snet-apim. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Das Gateway nutzt die öffentliche Adresse Entwicklung: pip-apim; Test: pip-apim; Echtbetrieb: pip-apim. — weil: `resources.api-management.networking.network_integration`
- Das Gateway ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Alte Verschlüsselungsprotokolle sind abgewiesen.
- Clientzertifikate sind nicht verlangt.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: jeder Aufruf durch das Gateway: Aufrufer, API, Status, Dauer.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Service Bus namespace

- Der Namensraum reserviert 1 Messaging-Einheit(en).
- Entitäten werden auf 1 Partition(en) verteilt.
- Clients müssen mindestens TLS 1.2 verwenden.
- Zugriffsschlüssel und Verbindungszeichenfolgen sind abgeschaltet.
- Der Namensraum hat keine eigene Identität.
- Warteschlangen: payments (leer: keine).
- Themen und ihre Abonnenten: orders subscriptions [{'name': 'billing', 'filter': 'order type'}, {'name': 'shipping', 'filter': 'order type'}, {'name': 'audit', 'filter': 'order type'}] (leer: keine).
- Zusammengehörige Nachrichten müssen nicht der Reihenfolge nach bearbeitet werden.
- Doppelt gesendete Nachrichten werden vom Broker verworfen.
- Eine Nachricht, die nicht innerhalb von 14 Tagen bearbeitet wird, verfällt.
- Eine abgelaufene Nachricht wird in einer Ablage zur Prüfung aufbewahrt.
- Eine Nachricht wird nach 10 fehlgeschlagenen Versuchen beiseitegelegt.
- Ein Empfänger hat 60 Sekunden pro Nachricht.
- Eine Warteschlange oder ein Thema fasst höchstens 1024 MB.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: Verwaltungsvorgänge am Namensraum, durch die Firewall blockierte oder erlaubte Verbindungen.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Event Hubs namespace

- Der Namensraum ist die Stufe Standard, mehrere Lesergruppen, bis zu einer Woche Historie und private Anbindung.
- Der Namensraum reserviert 1 Kapazitätseinheit(en).
- Die Kapazität bleibt wie reserviert, wenn die Last wächst.
- Clients müssen mindestens TLS 1.2 verwenden.
- Zugriffsschlüssel und Verbindungszeichenfolgen sind abgeschaltet.
- Der Namensraum hat eine eigene Identität. — weil: `resources.event-hubs.entities.event_archive`
- Event Hubs: telemetry.
- Der Datenstrom kann von bis zu 4 Lesern gleichzeitig verarbeitet werden.
- Ereignisse bleiben 7 Tag(e) lesbar.
- Lesergruppen: keine (leer: nur die Standardgruppe).
- Jedes Ereignis wird zusätzlich als Dateien im Speicher archiviert.
- Das Archiv geht in das Speicherkonto Entwicklung: storage-account__lake; Test: storage-account__lake; Echtbetrieb: storage-account__lake.
- Archivdateien gehen in den Container eventhub-capture.
- Alle 300 Sekunden wird eine Datei geschrieben.
- Der Dienst (namespace) ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: Verwaltungsvorgänge am Namensraum, von der Firewall angenommene oder blockierte Verbindungen.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Event Grid custom topic

- Absender senden Ereignisse im Format dem offenen CloudEvents-Standard.
- Absender müssen mindestens TLS 1.2 verwenden.
- Zugriffsschlüssel sind abgeschaltet.
- Das Thema hat eine eigene Identität.
- Abonnenten: blob-created-to-function target function-app, filter Microsoft.Storage.BlobCreated, delivery managed_identity (leer: noch keine).
- Eine fehlgeschlagene Zustellung wird bis zu 30 Mal wiederholt.
- Ein nicht zugestelltes Ereignis verfällt nach 1440 Minuten.
- Ein Ereignis, das nicht zugestellt werden kann, wird zur Prüfung im Speicher aufbewahrt.
- Nicht zustellbare Ereignisse gehen in das Speicherkonto Entwicklung: storage-account__orders; Test: storage-account__orders; Echtbetrieb: storage-account__orders.
- Die Dateien gehen in den Container eventgrid-deadletter.
- Der Dienst (topic) ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: Ereignisse, die nicht zugestellt werden konnten, und warum, abgewiesene Ereignisse von Absendern.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Backup vault

- Die Sicherungen werden Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Echtbetrieb: zusätzlich in einer zweiten Region aufbewahrt.
- Wiederherstellung in der Partnerregion ist möglich.
- Doppelte Verschlüsselung ist eingeschaltet.
- Eine fehlgeschlagene Sicherung löst eine Warnung aus.
- Gesichert werden: resource: storage-account__orders, kind: storage_blobs (leer: noch nichts).
- Eine Sicherung wird täglich erstellt.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Der Tresor hat eine eigene Identität.
- Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: Sicherungselemente, Aufträge und Richtlinien als Berichtstabelle, jeder Sicherungs- und Wiederherstellungsauftrag und sein Ergebnis, welche Ressourcen geschützt sind und in welchem Zustand.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Recovery Services vault

- Die Sicherungen werden Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Echtbetrieb: zusätzlich in einer zweiten Region aufbewahrt.
- Wiederherstellung in der Partnerregion ist möglich.
- Eine fehlgeschlagene Sicherung löst eine Warnung aus.
- Gesichert werden: keine (leer: noch nichts).
- Eine Sicherung wird täglich erstellt.
- Der Dienst (vault) ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Entwicklung: snet-endpoints; Test: snet-endpoints; Echtbetrieb: snet-endpoints. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Der Tresor hat eine eigene Identität.
- Zugriffsrechte vergeben an: Entwicklung: keine; Test: keine; Echtbetrieb: keine.
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: Sicherungselemente, Aufträge und Richtlinien als Berichtstabelle, jeder Sicherungs- und Wiederherstellungsauftrag und sein Ergebnis, vom Dienst ausgelöste Warnungen, welche Ressourcen geschützt sind und in welchem Zustand.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Front Door (Standard / Premium)

- Front Door ist die Stufe Premium, mit verwalteten Firewall-Regeln und privaten Verbindungen zu den Backends.
- Der Rand wartet höchstens 60 Sekunden auf ein Backend.
- Das Profil hat keine eigene Identität.
- Backends: Entwicklung: origin: application-gateway, route: /*; Test: origin: application-gateway, route: /*; Echtbetrieb: origin: application-gateway, route: /*.
- Front Door spricht mit den Backends über nur eine verschlüsselte Verbindung.
- Unverschlüsselte HTTP-Anfragen werden auf die verschlüsselte Adresse umgeleitet.
- Antworten werden am Rand nicht zwischengespeichert.
- Hostnamen: Entwicklung: keine; Test: keine; Echtbetrieb: keine (leer: nur der erzeugte *.azurefd.net-Name).
- Eine Web Application Firewall am Rand ist von einer Web Application Firewall geprüft.
- Die Firewall blockiert Anfragen, die es für bösartig hält.
- Gepflegte Firewall-Regeln sind angewandt.
- Eine Adresse darf 1000 Anfragen pro Minute stellen (0: keine Grenze).
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: jede Anfrage: Client, Host, Route, Status, Cache-Ergebnis, die Gesundheitsprüfungen je Backend und ihr Ergebnis, was die Firewall erkannt, blockiert oder durchgelassen hat.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Application Gateway (v2) with web application firewall

- Eine Web Application Firewall ist von einer Web Application Firewall geprüft.
- Die Firewall blockiert Anfragen, die es für bösartig hält.
- Die Firewall wendet das Regelwerk die gepflegten Standardregeln von Microsoft an.
- Bekannte bösartige Bots werden blockiert.
- Es wächst auf höchstens Entwicklung: 2; Test: 2; Echtbetrieb: 10 Instanzen.
- Das Gateway nutzt das Subnetz Entwicklung: snet-gateway; Test: snet-gateway; Echtbetrieb: snet-gateway. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Das Gateway hat eine separat verwaltete Identität.
- Es nutzt die Identität Entwicklung: user-assigned-identity__gateway; Test: user-assigned-identity__gateway; Echtbetrieb: user-assigned-identity__gateway.
- Die öffentliche Adresse ist zonenredundant: ja.
- Clients verbinden sich mit der Richtlinie TLS 1.2 oder neuer nur mit starken Chiffren.
- Das Gateway spricht mit den dahinterliegenden Diensten über eine verschlüsselte Verbindung.
- Unverschlüsselte HTTP-Anfragen werden auf die verschlüsselte Adresse umgeleitet.
- HTTP/2 ist angeboten.
- Von der Prüfung ausgenommen: keine (leer: nichts).
- Seine Logs gehen in Entwicklung: log-analytics-workspace; Test: log-analytics-workspace; Echtbetrieb: log-analytics-workspace.
- Geloggt wird: jede Anfrage: Client, Host, Status, Dauer, was die Firewall erkannt, blockiert oder durchgelassen hat.
- Nutzungs- und Leistungswerte werden erfasst.

## Von euch anders entschieden

- Azure Functions (function app on Flex Consumption or Elastic Premium): Die Function App ist aus dem Internet nur von gelisteten Adressen erreichbar. _(Grund: Event Grid delivers the blob events over the public path; the app admits the AzureEventGrid service tag and nothing else, and its private endpoint serves the API Management backend route.)_
- Azure API Management service: Aufrufer melden sich an mit ihrem Firmenkonto und einem Zugriffsschlüssel. _(Grund: Rate limiting per subscription needs the subscription as the caller key, so the gateway requires the Entra token and the subscription key. The key is an API Management subscription key, not a resource key: deployment.local_auth is about Azure resources.)_
- Azure Service Bus namespace: Der Namensraum ist die Stufe Entwicklung: Standard, Warteschlangen und Themen auf geteilter Kapazität; Test: Standard, Warteschlangen und Themen auf geteilter Kapazität; Echtbetrieb: Premium, dedizierte Kapazität mit privaten Anbindungen. _(Grund: Premium in production as stated and as a closed namespace requires. The request names Standard for development and test; Standard has no private endpoint, so those two stages are reached through the firewall (public_network_access, overridden) instead of being raised to Premium.)_
- Azure Service Bus namespace: Der Dienst (namespace) ist Entwicklung: aus dem Internet nur von gelisteten Adressen erreichbar; Test: aus dem Internet nur von gelisteten Adressen erreichbar; Echtbetrieb: aus dem Internet überhaupt nicht erreichbar. _(Grund: Standard (development, test) cannot hold a private endpoint, so these stages keep a firewalled public endpoint with the allowed addresses open. Production is closed.)_
- Azure Front Door (Standard / Premium): Front Door erreicht die Backends über die öffentlichen Adressen der Backends. _(Grund: An Application Gateway cannot be a Private Link origin of Front Door. The gateway admits only the AzureFrontDoor.Backend service tag and the render checks the X-Azure-FDID header against this profile.)_
- Azure Application Gateway (v2) with web application firewall: Das Gateway nimmt Anfragen aus dem Internet entgegen. _(Grund: Front Door reaches the gateway over its public frontend (no Private Link to a gateway); its network security group admits only the AzureFrontDoor.Backend service tag.)_

## Noch offen

Solange diese Punkte offen sind, wird nichts ausgerollt.

- Where does the code live, and which system deploys it? The request names none, so no pipeline is rendered. _(gebraucht von: workload owner)_ — blockiert: apply
- Which tag set does the organisation apply? Nothing in the request, no repository to read it from. _(gebraucht von: workload owner)_ — blockiert: apply
- Which runtime stack and version does the order function run (runtime_stack and runtime_version)? _(gebraucht von: workload owner)_ — blockiert: apply
- Publisher name and e-mail of the API Management instance (publisher_name, publisher_email): the organisation, not the project. _(gebraucht von: workload owner)_ — blockiert: apply
- Entra tenant and the app registration (audience) that validate-jwt checks the token against. A directory object, not an Azure resource - the identity team creates it. _(gebraucht von: identity team)_ — blockiert: apply
- Host name and TLS certificate of the listener, and the API Management gateway host name it forwards to. The certificate is a key vault secret the gateway identity reads. _(gebraucht von: workload owner)_ — blockiert: apply
- Which order types do the subscriptions billing, shipping and audit filter on? The filter rule is rendered from the values. _(gebraucht von: workload owner)_ — blockiert: apply
- Which addresses may reach the firewalled namespaces of development and test? Empty denies every public caller. [Entwicklung, Test] _(gebraucht von: workload owner)_ — blockiert: apply
- Which identities send to and receive from the topic orders, the queue payments and the event hub telemetry? Data Sender / Data Receiver per party; Owner is never granted. _(gebraucht von: workload owner)_ — blockiert: apply
- Blob events are emitted by a system topic on the storage account, which has no question set; the custom topic requested receives them only from a forwarding publisher. Which path is meant? Not rendered. _(gebraucht von: workload owner)_ — blockiert: apply
- Delivery of events to the function with a managed identity needs the Entra application settings on the function app (audience of the event subscription). Not rendered. _(gebraucht von: identity team)_ — blockiert: apply
- Storage account with hierarchical namespace (Data Lake Gen2) - not a question in the storage account set, and not convertible after creation. Decided with the render. _(gebraucht von: engineer)_ — blockiert: apply
- Which containers hold the order blobs? Only the dead-letter container is known. _(gebraucht von: workload owner)_ — blockiert: apply
- Resource Guard for the production backup vault (multi-user authorization): the id of a guard in another subscription, held by the security team. [Echtbetrieb] _(gebraucht von: security team)_ — blockiert: apply
- Resource Guard for the production recovery services vault. [Echtbetrieb] _(gebraucht von: security team)_ — blockiert: apply
- Which virtual machines does the vault protect? The request names no machine and the deployment has none. _(gebraucht von: workload owner)_ — blockiert: apply
- Front Door is a global service and cannot keep requests in the data zone. Does the data owner accept the edge locations? _(gebraucht von: data owner)_ — blockiert: apply

## Anhang: alle Entscheidungen

| Schlüssel | Wert | Quelle |
|---|---|---|
| `deployment.naming_convention` | default | Regel |
| `deployment.naming_source` | provider | Regel |
| `deployment.module_source` | avm | Regel |
| `deployment.module_telemetry` | disabled | Regel |
| `deployment.stage_isolation` | subscription | Regel |
| `deployment.non_production_savings` | enabled | Regel |
| `deployment.network_requirements` | free | Regel |
| `deployment.outage_impact` | disruptive | Regel |
| `deployment.data_loss_tolerance` | one_week | Regel |
| `deployment.data_access_pattern` | active | Regel |
| `deployment.backup_isolation` | immutable | eure Beschreibung |
| `deployment.data_residency` | data_zone | Regel |
| `deployment.landing_zone` | standalone | Regel |
| `deployment.network_exposure` | private_with_exceptions | eure Beschreibung |
| `deployment.local_auth` | disabled | eure Beschreibung |
| `deployment.mandates` | [] | Regel |
| `deployment.key_protection` | software | Regel |
| `deployment.key_management` | platform_managed | Regel |
| `deployment.resource_lock` | production | Regel |
| `deployment.network_ownership` | create | Regel |
| `deployment.address_space` | {"development": "10.100.0.0/23", "test": "10.101.0.0/23", "production": "10.102.0.0/23"} | eure Antwort |
| `deployment.private_endpoint_subnet_prefix` | {"development": "10.100.0.0/27", "test": "10.101.0.0/27", "production": "10.102.0.0/27"} | Regel |
| `deployment.private_dns_ownership` | deployment | erzwungen |
| `deployment.observability_ownership` | create | erzwungen |
| `deployment.diagnostics_destination` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | erzwungen |
| `deployment.log_retention_days` | {"development": 30, "test": 30, "production": 90} | eure Beschreibung |
| `deployment.daily_quota_gb` | -1 | Regel |
| `log-analytics-workspace.cost.retention_days` | {"development": 30, "test": 30, "production": 90} | übernommen |
| `log-analytics-workspace.cost.daily_quota_gb` | -1 | übernommen |
| `log-analytics-workspace.cost.sku` | PerGB2018 | Regel |
| `log-analytics-workspace.access.public_network_access` | enabled | Regel |
| `log-analytics-workspace.access.local_auth` | false | übernommen |
| `log-analytics-workspace.access.rbac_only_access` | true | Regel |
| `log-analytics-workspace.data_protection.immediate_purge_protection` | true | Regel |
| `log-analytics-workspace.data_protection.archive_to_storage` | false | Regel |
| `virtual-network.addressing.address_space` | {"development": "10.100.0.0/23", "test": "10.101.0.0/23", "production": "10.102.0.0/23"} | übernommen |
| `virtual-network.addressing.subnets` | {"development": [{"name": "snet-endpoints", "prefix": "10.100.0.0/27"}, {"name": "snet-apim", "prefix": "10.100.0.32/27"}, {"name": "snet-func", "prefix": "10.100.0.64/26"}, {"name": "snet-gateway", "prefix": "10.100.1.0/24"}], "test": [{"name": "snet-endpoints", "prefix": "10.101.0.0/27"}, {"name": "snet-apim", "prefix": "10.101.0.32/27"}, {"name": "snet-func", "prefix": "10.101.0.64/26"}, {"name": "snet-gateway", "prefix": "10.101.1.0/24"}], "production": [{"name": "snet-endpoints", "prefix": "10.102.0.0/27"}, {"name": "snet-apim", "prefix": "10.102.0.32/27"}, {"name": "snet-func", "prefix": "10.102.0.64/26"}, {"name": "snet-gateway", "prefix": "10.102.1.0/24"}]} | eure Beschreibung |
| `virtual-network.addressing.private_endpoint_subnet_prefix` | {"development": "10.100.0.0/27", "test": "10.101.0.0/27", "production": "10.102.0.0/27"} | übernommen |
| `virtual-network.addressing.dns_servers` | {"development": [], "test": [], "production": []} | Regel |
| `virtual-network.subnet_policy.private_endpoint_network_policies` | Enabled | Regel |
| `virtual-network.subnet_policy.service_endpoints` | [] | Regel |
| `virtual-network.subnet_policy.subnet_delegations` | [{"subnet": "snet-func", "service": "Microsoft.App/environments"}] | erzwungen |
| `virtual-network.security.ddos_protection` | false | Regel |
| `virtual-network.security.subnets_expecting_nsg` | {"development": ["snet-endpoints", "snet-apim", "snet-func", "snet-gateway"], "test": ["snet-endpoints", "snet-apim", "snet-func", "snet-gateway"], "production": ["snet-endpoints", "snet-apim", "snet-func", "snet-gateway"]} | eure Beschreibung |
| `virtual-network.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `virtual-network.observability.flow_logs_enabled` | false | Regel |
| `network-security-group__endpoints.rules.subnet_purpose` | private_endpoints | eure Beschreibung |
| `network-security-group__endpoints.rules.default_inbound` | deny_all | Regel |
| `network-security-group__endpoints.rules.default_outbound` | deny_internet | erzwungen |
| `network-security-group__endpoints.rules.rules` | {"development": [{"name": "allow-apim-https", "priority": 100, "direction": "Inbound", "protocol": "Tcp", "source": "10.100.0.32/27", "destination": "10.100.0.0/27", "port": "443", "access": "Allow"}, {"name": "allow-function-https", "priority": 110, "direction": "Inbound", "protocol": "Tcp", "source": "10.100.0.64/26", "destination": "10.100.0.0/27", "port": "443", "access": "Allow"}, {"name": "allow-function-amqp", "priority": 120, "direction": "Inbound", "protocol": "Tcp", "source": "10.100.0.64/26", "destination": "10.100.0.0/27", "port": "5671-5672", "access": "Allow"}], "test": [{"name": "allow-apim-https", "priority": 100, "direction": "Inbound", "protocol": "Tcp", "source": "10.101.0.32/27", "destination": "10.101.0.0/27", "port": "443", "access": "Allow"}, {"name": "allow-function-https", "priority": 110, "direction": "Inbound", "protocol": "Tcp", "source": "10.101.0.64/26", "destination": "10.101.0.0/27", "port": "443", "access": "Allow"}, {"name": "allow-function-amqp", "priority": 120, "direction": "Inbound", "protocol": "Tcp", "source": "10.101.0.64/26", "destination": "10.101.0.0/27", "port": "5671-5672", "access": "Allow"}], "production": [{"name": "allow-apim-https", "priority": 100, "direction": "Inbound", "protocol": "Tcp", "source": "10.102.0.32/27", "destination": "10.102.0.0/27", "port": "443", "access": "Allow"}, {"name": "allow-function-https", "priority": 110, "direction": "Inbound", "protocol": "Tcp", "source": "10.102.0.64/26", "destination": "10.102.0.0/27", "port": "443", "access": "Allow"}, {"name": "allow-function-amqp", "priority": 120, "direction": "Inbound", "protocol": "Tcp", "source": "10.102.0.64/26", "destination": "10.102.0.0/27", "port": "5671-5672", "access": "Allow"}]} | eure Beschreibung |
| `network-security-group__endpoints.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `network-security-group__endpoints.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | Regel |
| `network-security-group__func.rules.subnet_purpose` | app_integration | eure Beschreibung |
| `network-security-group__func.rules.default_inbound` | deny_all | Regel |
| `network-security-group__func.rules.default_outbound` | azure_default | Regel |
| `network-security-group__func.rules.rules` | {"development": [{"name": "allow-endpoints-https", "priority": 100, "direction": "Outbound", "protocol": "Tcp", "source": "10.100.0.64/26", "destination": "10.100.0.0/27", "port": "443", "access": "Allow"}, {"name": "allow-endpoints-amqp", "priority": 110, "direction": "Outbound", "protocol": "Tcp", "source": "10.100.0.64/26", "destination": "10.100.0.0/27", "port": "5671-5672", "access": "Allow"}], "test": [{"name": "allow-endpoints-https", "priority": 100, "direction": "Outbound", "protocol": "Tcp", "source": "10.101.0.64/26", "destination": "10.101.0.0/27", "port": "443", "access": "Allow"}, {"name": "allow-endpoints-amqp", "priority": 110, "direction": "Outbound", "protocol": "Tcp", "source": "10.101.0.64/26", "destination": "10.101.0.0/27", "port": "5671-5672", "access": "Allow"}], "production": [{"name": "allow-endpoints-https", "priority": 100, "direction": "Outbound", "protocol": "Tcp", "source": "10.102.0.64/26", "destination": "10.102.0.0/27", "port": "443", "access": "Allow"}, {"name": "allow-endpoints-amqp", "priority": 110, "direction": "Outbound", "protocol": "Tcp", "source": "10.102.0.64/26", "destination": "10.102.0.0/27", "port": "5671-5672", "access": "Allow"}]} | eure Beschreibung |
| `network-security-group__func.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `network-security-group__func.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | Regel |
| `network-security-group__gateway.rules.subnet_purpose` | workload | eure Beschreibung |
| `network-security-group__gateway.rules.default_inbound` | deny_all | Regel |
| `network-security-group__gateway.rules.default_outbound` | deny_internet | eure Beschreibung |
| `network-security-group__gateway.rules.rules` | {"development": [{"name": "allow-front-door-https", "priority": 100, "direction": "Inbound", "protocol": "Tcp", "source": "AzureFrontDoor.Backend", "destination": "10.100.1.0/24", "port": "443", "access": "Allow"}, {"name": "allow-gateway-manager", "priority": 110, "direction": "Inbound", "protocol": "Tcp", "source": "GatewayManager", "destination": "10.100.1.0/24", "port": "65200-65535", "access": "Allow"}, {"name": "allow-load-balancer-probe", "priority": 120, "direction": "Inbound", "protocol": "*", "source": "AzureLoadBalancer", "destination": "10.100.1.0/24", "port": "*", "access": "Allow"}, {"name": "allow-apim-https", "priority": 100, "direction": "Outbound", "protocol": "Tcp", "source": "10.100.1.0/24", "destination": "10.100.0.32/27", "port": "443", "access": "Allow"}, {"name": "allow-key-vault-https", "priority": 110, "direction": "Outbound", "protocol": "Tcp", "source": "10.100.1.0/24", "destination": "AzureKeyVault", "port": "443", "access": "Allow"}], "test": [{"name": "allow-front-door-https", "priority": 100, "direction": "Inbound", "protocol": "Tcp", "source": "AzureFrontDoor.Backend", "destination": "10.101.1.0/24", "port": "443", "access": "Allow"}, {"name": "allow-gateway-manager", "priority": 110, "direction": "Inbound", "protocol": "Tcp", "source": "GatewayManager", "destination": "10.101.1.0/24", "port": "65200-65535", "access": "Allow"}, {"name": "allow-load-balancer-probe", "priority": 120, "direction": "Inbound", "protocol": "*", "source": "AzureLoadBalancer", "destination": "10.101.1.0/24", "port": "*", "access": "Allow"}, {"name": "allow-apim-https", "priority": 100, "direction": "Outbound", "protocol": "Tcp", "source": "10.101.1.0/24", "destination": "10.101.0.32/27", "port": "443", "access": "Allow"}, {"name": "allow-key-vault-https", "priority": 110, "direction": "Outbound", "protocol": "Tcp", "source": "10.101.1.0/24", "destination": "AzureKeyVault", "port": "443", "access": "Allow"}], "production": [{"name": "allow-front-door-https", "priority": 100, "direction": "Inbound", "protocol": "Tcp", "source": "AzureFrontDoor.Backend", "destination": "10.102.1.0/24", "port": "443", "access": "Allow"}, {"name": "allow-gateway-manager", "priority": 110, "direction": "Inbound", "protocol": "Tcp", "source": "GatewayManager", "destination": "10.102.1.0/24", "port": "65200-65535", "access": "Allow"}, {"name": "allow-load-balancer-probe", "priority": 120, "direction": "Inbound", "protocol": "*", "source": "AzureLoadBalancer", "destination": "10.102.1.0/24", "port": "*", "access": "Allow"}, {"name": "allow-apim-https", "priority": 100, "direction": "Outbound", "protocol": "Tcp", "source": "10.102.1.0/24", "destination": "10.102.0.32/27", "port": "443", "access": "Allow"}, {"name": "allow-key-vault-https", "priority": 110, "direction": "Outbound", "protocol": "Tcp", "source": "10.102.1.0/24", "destination": "AzureKeyVault", "port": "443", "access": "Allow"}]} | eure Beschreibung |
| `network-security-group__gateway.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `network-security-group__gateway.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | Regel |
| `network-security-group__apim.rules.subnet_purpose` | workload | eure Beschreibung |
| `network-security-group__apim.rules.default_inbound` | deny_all | Regel |
| `network-security-group__apim.rules.default_outbound` | deny_internet | eure Beschreibung |
| `network-security-group__apim.rules.rules` | {"development": [{"name": "allow-gateway-https", "priority": 100, "direction": "Inbound", "protocol": "Tcp", "source": "10.100.1.0/24", "destination": "10.100.0.32/27", "port": "443", "access": "Allow"}, {"name": "allow-apim-management", "priority": 110, "direction": "Inbound", "protocol": "Tcp", "source": "ApiManagement", "destination": "10.100.0.32/27", "port": "3443", "access": "Allow"}, {"name": "allow-load-balancer", "priority": 120, "direction": "Inbound", "protocol": "Tcp", "source": "AzureLoadBalancer", "destination": "10.100.0.32/27", "port": "6390", "access": "Allow"}, {"name": "allow-endpoints-https", "priority": 100, "direction": "Outbound", "protocol": "Tcp", "source": "10.100.0.32/27", "destination": "10.100.0.0/27", "port": "443", "access": "Allow"}, {"name": "allow-storage", "priority": 110, "direction": "Outbound", "protocol": "Tcp", "source": "10.100.0.32/27", "destination": "Storage", "port": "443", "access": "Allow"}, {"name": "allow-sql", "priority": 120, "direction": "Outbound", "protocol": "Tcp", "source": "10.100.0.32/27", "destination": "Sql", "port": "1433", "access": "Allow"}, {"name": "allow-key-vault", "priority": 130, "direction": "Outbound", "protocol": "Tcp", "source": "10.100.0.32/27", "destination": "AzureKeyVault", "port": "443", "access": "Allow"}, {"name": "allow-monitor", "priority": 140, "direction": "Outbound", "protocol": "Tcp", "source": "10.100.0.32/27", "destination": "AzureMonitor", "port": "443,1886", "access": "Allow"}], "test": [{"name": "allow-gateway-https", "priority": 100, "direction": "Inbound", "protocol": "Tcp", "source": "10.101.1.0/24", "destination": "10.101.0.32/27", "port": "443", "access": "Allow"}, {"name": "allow-apim-management", "priority": 110, "direction": "Inbound", "protocol": "Tcp", "source": "ApiManagement", "destination": "10.101.0.32/27", "port": "3443", "access": "Allow"}, {"name": "allow-load-balancer", "priority": 120, "direction": "Inbound", "protocol": "Tcp", "source": "AzureLoadBalancer", "destination": "10.101.0.32/27", "port": "6390", "access": "Allow"}, {"name": "allow-endpoints-https", "priority": 100, "direction": "Outbound", "protocol": "Tcp", "source": "10.101.0.32/27", "destination": "10.101.0.0/27", "port": "443", "access": "Allow"}, {"name": "allow-storage", "priority": 110, "direction": "Outbound", "protocol": "Tcp", "source": "10.101.0.32/27", "destination": "Storage", "port": "443", "access": "Allow"}, {"name": "allow-sql", "priority": 120, "direction": "Outbound", "protocol": "Tcp", "source": "10.101.0.32/27", "destination": "Sql", "port": "1433", "access": "Allow"}, {"name": "allow-key-vault", "priority": 130, "direction": "Outbound", "protocol": "Tcp", "source": "10.101.0.32/27", "destination": "AzureKeyVault", "port": "443", "access": "Allow"}, {"name": "allow-monitor", "priority": 140, "direction": "Outbound", "protocol": "Tcp", "source": "10.101.0.32/27", "destination": "AzureMonitor", "port": "443,1886", "access": "Allow"}], "production": [{"name": "allow-gateway-https", "priority": 100, "direction": "Inbound", "protocol": "Tcp", "source": "10.102.1.0/24", "destination": "10.102.0.32/27", "port": "443", "access": "Allow"}, {"name": "allow-apim-management", "priority": 110, "direction": "Inbound", "protocol": "Tcp", "source": "ApiManagement", "destination": "10.102.0.32/27", "port": "3443", "access": "Allow"}, {"name": "allow-load-balancer", "priority": 120, "direction": "Inbound", "protocol": "Tcp", "source": "AzureLoadBalancer", "destination": "10.102.0.32/27", "port": "6390", "access": "Allow"}, {"name": "allow-endpoints-https", "priority": 100, "direction": "Outbound", "protocol": "Tcp", "source": "10.102.0.32/27", "destination": "10.102.0.0/27", "port": "443", "access": "Allow"}, {"name": "allow-storage", "priority": 110, "direction": "Outbound", "protocol": "Tcp", "source": "10.102.0.32/27", "destination": "Storage", "port": "443", "access": "Allow"}, {"name": "allow-sql", "priority": 120, "direction": "Outbound", "protocol": "Tcp", "source": "10.102.0.32/27", "destination": "Sql", "port": "1433", "access": "Allow"}, {"name": "allow-key-vault", "priority": 130, "direction": "Outbound", "protocol": "Tcp", "source": "10.102.0.32/27", "destination": "AzureKeyVault", "port": "443", "access": "Allow"}, {"name": "allow-monitor", "priority": 140, "direction": "Outbound", "protocol": "Tcp", "source": "10.102.0.32/27", "destination": "AzureMonitor", "port": "443,1886", "access": "Allow"}]} | eure Beschreibung |
| `network-security-group__apim.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `network-security-group__apim.observability.diagnostic_categories` | ["NetworkSecurityGroupEvent", "NetworkSecurityGroupRuleCounter"] | Regel |
| `user-assigned-identity__func.identity.purpose` | the function app, to keep its own state in the host storage account and to read secrets | eure Beschreibung |
| `user-assigned-identity__func.identity.federated_credentials` | [] | Regel |
| `user-assigned-identity__func.identity.isolation_scope` | None | Regel |
| `user-assigned-identity__func.identity.role_assignments` | {"development": [], "test": [], "production": []} | Regel |
| `user-assigned-identity__gateway.identity.purpose` | the application gateway, to read its TLS certificates from the key vault | eure Beschreibung |
| `user-assigned-identity__gateway.identity.federated_credentials` | [] | Regel |
| `user-assigned-identity__gateway.identity.isolation_scope` | None | Regel |
| `user-assigned-identity__gateway.identity.role_assignments` | {"development": [], "test": [], "production": []} | Regel |
| `key-vault.vault.sku` | standard | Regel |
| `key-vault.vault.purge_protection` | true | Regel |
| `key-vault.vault.soft_delete_retention_days` | 90 | Regel |
| `key-vault.vault.rbac_authorization` | true | übernommen |
| `key-vault.networking.public_network_access` | disabled | übernommen |
| `key-vault.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `key-vault.networking.network_acl_bypass` | None | Regel |
| `key-vault.identity.role_assignments` | {"development": [{"principal": "user-assigned-identity__gateway", "role": "Key Vault Secrets User"}, {"principal": "user-assigned-identity__func", "role": "Key Vault Secrets User"}, {"principal": "api-management", "role": "Key Vault Secrets User"}], "test": [{"principal": "user-assigned-identity__gateway", "role": "Key Vault Secrets User"}, {"principal": "user-assigned-identity__func", "role": "Key Vault Secrets User"}, {"principal": "api-management", "role": "Key Vault Secrets User"}], "production": [{"principal": "user-assigned-identity__gateway", "role": "Key Vault Secrets User"}, {"principal": "user-assigned-identity__func", "role": "Key Vault Secrets User"}, {"principal": "api-management", "role": "Key Vault Secrets User"}]} | eure Beschreibung |
| `key-vault.security.enabled_for_services` | [] | Regel |
| `key-vault.security.secret_placeholders` | [] | Regel |
| `key-vault.keys.key_management` | platform_managed | übernommen |
| `key-vault.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `key-vault.observability.diagnostic_categories` | ["AuditEvent", "AzurePolicyEvaluationDetails"] | Regel |
| `key-vault.observability.metrics_enabled` | true | Regel |
| `storage-account__orders.networking.public_network_access` | disabled | übernommen |
| `storage-account__orders.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `storage-account__orders.networking.private_endpoint_subresources` | ["blob"] | Regel |
| `storage-account__orders.networking.allow_azure_services_bypass` | true | Regel |
| `storage-account__orders.identity.managed_identity` | system_assigned | Regel |
| `storage-account__orders.identity.role_assignments` | {"development": [{"principal": "backup-vault", "role": "Storage Account Backup Contributor"}, {"principal": "event-grid-topic", "role": "Storage Blob Data Contributor"}], "test": [{"principal": "backup-vault", "role": "Storage Account Backup Contributor"}, {"principal": "event-grid-topic", "role": "Storage Blob Data Contributor"}], "production": [{"principal": "backup-vault", "role": "Storage Account Backup Contributor"}, {"principal": "event-grid-topic", "role": "Storage Blob Data Contributor"}]} | eure Beschreibung |
| `storage-account__orders.security.shared_access_key_enabled` | false | übernommen |
| `storage-account__orders.security.min_tls_version` | TLS1_2 | Regel |
| `storage-account__orders.security.https_traffic_only` | true | Regel |
| `storage-account__orders.security.allow_blob_public_access` | false | Regel |
| `storage-account__orders.security.infrastructure_encryption_enabled` | true | Regel |
| `storage-account__orders.security.key_management` | platform_managed | übernommen |
| `storage-account__orders.security.sftp_enabled` | false | Regel |
| `storage-account__orders.data_protection.replication` | {"development": "LRS", "test": "LRS", "production": "ZRS"} | abgeleitet aus eurer Antwort |
| `storage-account__orders.data_protection.access_tier` | Hot | abgeleitet aus eurer Antwort |
| `storage-account__orders.data_protection.blob_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account__orders.data_protection.container_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account__orders.data_protection.versioning_enabled` | true | abgeleitet aus eurer Antwort |
| `storage-account__orders.data_protection.change_feed_enabled` | false | Regel |
| `storage-account__orders.data_protection.point_in_time_restore_days` | 0 | Regel |
| `storage-account__orders.data_protection.immutability` | none | Regel |
| `storage-account__orders.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `storage-account__orders.observability.diagnostic_categories` | ["audit"] | Regel |
| `storage-account__orders.observability.metrics_enabled` | true | Regel |
| `storage-account__lake.networking.public_network_access` | disabled | übernommen |
| `storage-account__lake.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `storage-account__lake.networking.private_endpoint_subresources` | ["blob", "dfs"] | eure Beschreibung |
| `storage-account__lake.networking.allow_azure_services_bypass` | true | Regel |
| `storage-account__lake.identity.managed_identity` | system_assigned | Regel |
| `storage-account__lake.identity.role_assignments` | {"development": [{"principal": "event-hubs", "role": "Storage Blob Data Contributor"}], "test": [{"principal": "event-hubs", "role": "Storage Blob Data Contributor"}], "production": [{"principal": "event-hubs", "role": "Storage Blob Data Contributor"}]} | eure Beschreibung |
| `storage-account__lake.security.shared_access_key_enabled` | false | übernommen |
| `storage-account__lake.security.min_tls_version` | TLS1_2 | Regel |
| `storage-account__lake.security.https_traffic_only` | true | Regel |
| `storage-account__lake.security.allow_blob_public_access` | false | Regel |
| `storage-account__lake.security.infrastructure_encryption_enabled` | true | Regel |
| `storage-account__lake.security.key_management` | platform_managed | übernommen |
| `storage-account__lake.security.sftp_enabled` | false | Regel |
| `storage-account__lake.data_protection.replication` | {"development": "LRS", "test": "LRS", "production": "ZRS"} | abgeleitet aus eurer Antwort |
| `storage-account__lake.data_protection.access_tier` | Hot | abgeleitet aus eurer Antwort |
| `storage-account__lake.data_protection.blob_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account__lake.data_protection.container_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account__lake.data_protection.versioning_enabled` | true | abgeleitet aus eurer Antwort |
| `storage-account__lake.data_protection.change_feed_enabled` | false | Regel |
| `storage-account__lake.data_protection.point_in_time_restore_days` | 0 | Regel |
| `storage-account__lake.data_protection.immutability` | none | Regel |
| `storage-account__lake.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `storage-account__lake.observability.diagnostic_categories` | ["audit"] | Regel |
| `storage-account__lake.observability.metrics_enabled` | true | Regel |
| `storage-account__host.networking.public_network_access` | disabled | übernommen |
| `storage-account__host.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `storage-account__host.networking.private_endpoint_subresources` | ["blob"] | Regel |
| `storage-account__host.networking.allow_azure_services_bypass` | true | Regel |
| `storage-account__host.identity.managed_identity` | system_assigned | Regel |
| `storage-account__host.identity.role_assignments` | {"development": [{"principal": "user-assigned-identity__func", "role": "Storage Blob Data Owner"}], "test": [{"principal": "user-assigned-identity__func", "role": "Storage Blob Data Owner"}], "production": [{"principal": "user-assigned-identity__func", "role": "Storage Blob Data Owner"}]} | eure Beschreibung |
| `storage-account__host.security.shared_access_key_enabled` | false | übernommen |
| `storage-account__host.security.min_tls_version` | TLS1_2 | Regel |
| `storage-account__host.security.https_traffic_only` | true | Regel |
| `storage-account__host.security.allow_blob_public_access` | false | Regel |
| `storage-account__host.security.infrastructure_encryption_enabled` | true | Regel |
| `storage-account__host.security.key_management` | platform_managed | übernommen |
| `storage-account__host.security.sftp_enabled` | false | Regel |
| `storage-account__host.data_protection.replication` | {"development": "LRS", "test": "LRS", "production": "ZRS"} | abgeleitet aus eurer Antwort |
| `storage-account__host.data_protection.access_tier` | Hot | abgeleitet aus eurer Antwort |
| `storage-account__host.data_protection.blob_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account__host.data_protection.container_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account__host.data_protection.versioning_enabled` | true | abgeleitet aus eurer Antwort |
| `storage-account__host.data_protection.change_feed_enabled` | false | Regel |
| `storage-account__host.data_protection.point_in_time_restore_days` | 0 | Regel |
| `storage-account__host.data_protection.immutability` | none | Regel |
| `storage-account__host.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `storage-account__host.observability.diagnostic_categories` | ["audit"] | Regel |
| `storage-account__host.observability.metrics_enabled` | true | Regel |
| `blob-container__orders.containers.container_names` | ["eventgrid-deadletter"] | Regel |
| `blob-container__orders.containers.public_access` | None | Regel |
| `blob-container__orders.containers.immutable_storage` | {"development": false, "test": false, "production": true} | abgeleitet aus eurer Antwort |
| `blob-container__orders.containers.encryption_scope_locked` | false | Regel |
| `blob-container__orders.identity.role_assignments` | {"development": [], "test": [], "production": []} | Regel |
| `blob-container__lake.containers.container_names` | ["eventhub-capture"] | erzwungen |
| `blob-container__lake.containers.public_access` | None | Regel |
| `blob-container__lake.containers.immutable_storage` | {"development": false, "test": false, "production": true} | abgeleitet aus eurer Antwort |
| `blob-container__lake.containers.encryption_scope_locked` | false | Regel |
| `blob-container__lake.identity.role_assignments` | {"development": [], "test": [], "production": []} | Regel |
| `function-app.hosting.plan_type` | flex_consumption | Regel |
| `function-app.hosting.zone_redundant` | {"development": false, "test": false, "production": true} | abgeleitet aus eurer Antwort |
| `function-app.hosting.max_instance_count` | 20 | Regel |
| `function-app.hosting.always_ready_instances` | {"development": 0, "test": 0, "production": 1} | abgeleitet aus eurer Antwort |
| `function-app.hosting.instance_memory_mb` | 2048 | Regel |
| `function-app.storage.host_storage_account` | {"development": "storage-account__host", "test": "storage-account__host", "production": "storage-account__host"} | eure Beschreibung |
| `function-app.storage.host_storage_auth` | identity | übernommen |
| `function-app.storage.deployment_container` | app-package | Regel |
| `function-app.networking.public_network_access` | enabled_with_firewall | eure Abweichung |
| `function-app.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `function-app.networking.vnet_integration` | true | Regel |
| `function-app.networking.integration_subnet` | {"development": "snet-func", "test": "snet-func", "production": "snet-func"} | erzwungen |
| `function-app.networking.vnet_route_all` | true | Regel |
| `function-app.networking.ip_restrictions` | {"development": [{"service_tag": "AzureEventGrid"}], "test": [{"service_tag": "AzureEventGrid"}], "production": [{"service_tag": "AzureEventGrid"}]} | eure Beschreibung |
| `function-app.identity.managed_identity` | user_assigned | Regel |
| `function-app.identity.user_assigned_identity_ids` | {"development": ["user-assigned-identity__func"], "test": ["user-assigned-identity__func"], "production": ["user-assigned-identity__func"]} | eure Beschreibung |
| `function-app.identity.role_assignments` | {"development": [], "test": [], "production": []} | Regel |
| `function-app.security.https_only` | true | Regel |
| `function-app.security.min_tls_version` | 1.2 | Regel |
| `function-app.security.basic_auth_enabled` | false | übernommen |
| `function-app.security.application_insights` | {"development": "", "test": "", "production": ""} | Regel |
| `function-app.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `function-app.observability.diagnostic_categories` | ["FunctionAppLogs", "AppServiceAuditLogs"] | Regel |
| `function-app.observability.metrics_enabled` | true | Regel |
| `api-management.service.sku` | {"development": "Developer", "test": "Developer", "production": "Premium"} | eure Beschreibung |
| `api-management.service.capacity` | 1 | Regel |
| `api-management.service.zone_redundant` | false | Regel |
| `api-management.service.additional_regions` | {"development": [], "test": [], "production": []} | Regel |
| `api-management.service.managed_identity` | system_assigned | eure Beschreibung |
| `api-management.access.caller_authentication` | entra_id_and_key | eure Abweichung |
| `api-management.access.rate_limit_calls_per_minute` | 600 | Regel |
| `api-management.access.developer_portal` | false | Regel |
| `api-management.access.apis` | [{"name": "orders", "path": "orders", "backend": "function-app"}] | eure Beschreibung |
| `api-management.access.products` | [] | Regel |
| `api-management.networking.network_integration` | internal | eure Beschreibung |
| `api-management.networking.apim_subnet` | {"development": "snet-apim", "test": "snet-apim", "production": "snet-apim"} | erzwungen |
| `api-management.networking.public_ip_address` | {"development": "pip-apim", "test": "pip-apim", "production": "pip-apim"} | erzwungen |
| `api-management.networking.public_network_access` | disabled | übernommen |
| `api-management.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `api-management.identity.role_assignments` | {"development": [], "test": [], "production": []} | Regel |
| `api-management.security.legacy_protocols_disabled` | true | Regel |
| `api-management.security.client_certificate_required` | false | Regel |
| `api-management.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `api-management.observability.diagnostic_categories` | ["GatewayLogs"] | Regel |
| `api-management.observability.metrics_enabled` | true | Regel |
| `service-bus.namespace.sku` | {"development": "Standard", "test": "Standard", "production": "Premium"} | eure Abweichung |
| `service-bus.namespace.capacity` | 1 | Regel |
| `service-bus.namespace.zone_redundant` | {"development": false, "test": false, "production": true} | abgeleitet aus eurer Antwort |
| `service-bus.namespace.premium_messaging_partitions` | 1 | Regel |
| `service-bus.namespace.minimum_tls_version` | 1.2 | Regel |
| `service-bus.namespace.local_auth` | disabled | übernommen |
| `service-bus.namespace.managed_identity` | none | Regel |
| `service-bus.entities.queues` | [{"name": "payments"}] | eure Beschreibung |
| `service-bus.entities.topics` | [{"name": "orders", "subscriptions": [{"name": "billing", "filter": "order type"}, {"name": "shipping", "filter": "order type"}, {"name": "audit", "filter": "order type"}]}] | eure Beschreibung |
| `service-bus.entities.message_ordering` | false | Regel |
| `service-bus.entities.duplicate_protection` | true | eure Beschreibung |
| `service-bus.entities.message_retention_days` | 14 | Regel |
| `service-bus.entities.dead_letter_on_expiry` | true | Regel |
| `service-bus.entities.max_delivery_count` | 10 | Regel |
| `service-bus.entities.lock_duration_seconds` | 60 | Regel |
| `service-bus.entities.max_size_megabytes` | 1024 | Regel |
| `service-bus.networking.public_network_access` | {"development": "enabled_with_firewall", "test": "enabled_with_firewall", "production": "disabled"} | eure Abweichung |
| `service-bus.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `service-bus.encryption.key_management` | platform_managed | übernommen |
| `service-bus.recovery.geo_recovery` | none | abgeleitet aus eurer Antwort |
| `service-bus.identity.role_assignments` | {"development": [], "test": [], "production": []} | Regel |
| `service-bus.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `service-bus.observability.diagnostic_categories` | ["OperationalLogs", "VNetAndIPFilteringLogs"] | Regel |
| `service-bus.observability.metrics_enabled` | true | Regel |
| `event-hubs.namespace.sku` | Standard | Regel |
| `event-hubs.namespace.capacity` | 1 | Regel |
| `event-hubs.namespace.auto_inflate` | false | Regel |
| `event-hubs.namespace.minimum_tls_version` | 1.2 | Regel |
| `event-hubs.namespace.local_auth` | disabled | übernommen |
| `event-hubs.namespace.managed_identity` | system_assigned | erzwungen |
| `event-hubs.entities.event_hubs` | ["telemetry"] | eure Beschreibung |
| `event-hubs.entities.partition_count` | 4 | eure Beschreibung |
| `event-hubs.entities.message_retention_days` | 7 | eure Beschreibung |
| `event-hubs.entities.consumer_groups` | [] | Regel |
| `event-hubs.entities.event_archive` | true | eure Beschreibung |
| `event-hubs.entities.archive_storage_account` | {"development": "storage-account__lake", "test": "storage-account__lake", "production": "storage-account__lake"} | eure Beschreibung |
| `event-hubs.entities.archive_container` | eventhub-capture | Regel |
| `event-hubs.entities.archive_interval_seconds` | 300 | Regel |
| `event-hubs.networking.public_network_access` | disabled | übernommen |
| `event-hubs.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `event-hubs.encryption.key_management` | platform_managed | übernommen |
| `event-hubs.recovery.zone_redundant` | {"development": false, "test": false, "production": true} | abgeleitet aus eurer Antwort |
| `event-hubs.recovery.geo_recovery` | none | abgeleitet aus eurer Antwort |
| `event-hubs.identity.role_assignments` | {"development": [], "test": [], "production": []} | Regel |
| `event-hubs.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `event-hubs.observability.diagnostic_categories` | ["OperationalLogs", "EventHubVNetConnectionEvent"] | Regel |
| `event-hubs.observability.metrics_enabled` | true | Regel |
| `event-grid-topic.topic.input_schema` | CloudEventSchemaV1_0 | Regel |
| `event-grid-topic.topic.minimum_tls_version` | 1.2 | Regel |
| `event-grid-topic.topic.local_auth` | disabled | übernommen |
| `event-grid-topic.topic.data_residency_boundary` | WithinGeopair | abgeleitet aus eurer Antwort |
| `event-grid-topic.topic.managed_identity` | system_assigned | eure Beschreibung |
| `event-grid-topic.delivery.event_subscriptions` | [{"name": "blob-created-to-function", "target": "function-app", "filter": "Microsoft.Storage.BlobCreated", "delivery": "managed_identity"}] | eure Beschreibung |
| `event-grid-topic.delivery.max_delivery_attempts` | 30 | Regel |
| `event-grid-topic.delivery.event_ttl_minutes` | 1440 | Regel |
| `event-grid-topic.delivery.keep_undeliverable_events` | true | Regel |
| `event-grid-topic.delivery.dead_letter_storage_account` | {"development": "storage-account__orders", "test": "storage-account__orders", "production": "storage-account__orders"} | Regel |
| `event-grid-topic.delivery.dead_letter_container` | eventgrid-deadletter | Regel |
| `event-grid-topic.networking.public_network_access` | disabled | übernommen |
| `event-grid-topic.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `event-grid-topic.identity.role_assignments` | {"development": [], "test": [], "production": []} | Regel |
| `event-grid-topic.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `event-grid-topic.observability.diagnostic_categories` | ["DeliveryFailures", "PublishFailures"] | Regel |
| `event-grid-topic.observability.metrics_enabled` | true | Regel |
| `backup-vault.vault.storage_redundancy` | {"development": "LocallyRedundant", "test": "LocallyRedundant", "production": "GeoRedundant"} | eure Beschreibung |
| `backup-vault.vault.cross_region_restore` | true | eure Beschreibung |
| `backup-vault.vault.immutability` | {"development": "Unlocked", "test": "Unlocked", "production": "Locked"} | abgeleitet aus eurer Antwort |
| `backup-vault.vault.soft_delete_retention_days` | 14 | abgeleitet aus eurer Antwort |
| `backup-vault.vault.multi_user_authorization` | {"development": false, "test": false, "production": true} | abgeleitet aus eurer Antwort |
| `backup-vault.vault.infrastructure_encryption` | true | Regel |
| `backup-vault.vault.job_failure_alerts` | true | Regel |
| `backup-vault.protection.protected_resources` | [{"resource": "storage-account__orders", "kind": "storage_blobs"}] | eure Beschreibung |
| `backup-vault.protection.backup_schedule` | daily | Regel |
| `backup-vault.protection.retention_days` | {"development": 7, "test": 7, "production": 30} | abgeleitet aus eurer Antwort |
| `backup-vault.encryption.key_management` | platform_managed | übernommen |
| `backup-vault.encryption.managed_identity` | system_assigned | Regel |
| `backup-vault.identity.role_assignments` | {"development": [], "test": [], "production": []} | Regel |
| `backup-vault.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `backup-vault.observability.diagnostic_categories` | ["CoreAzureBackup", "AddonAzureBackupJobs", "AddonAzureBackupProtectedInstance"] | Regel |
| `backup-vault.observability.metrics_enabled` | true | Regel |
| `recovery-services-vault.vault.storage_redundancy` | {"development": "LocallyRedundant", "test": "LocallyRedundant", "production": "GeoRedundant"} | eure Beschreibung |
| `recovery-services-vault.vault.cross_region_restore` | true | eure Beschreibung |
| `recovery-services-vault.vault.soft_delete` | AlwaysOn | abgeleitet aus eurer Antwort |
| `recovery-services-vault.vault.soft_delete_retention_days` | 14 | abgeleitet aus eurer Antwort |
| `recovery-services-vault.vault.immutability` | {"development": "Unlocked", "test": "Unlocked", "production": "Locked"} | abgeleitet aus eurer Antwort |
| `recovery-services-vault.vault.multi_user_authorization` | {"development": false, "test": false, "production": true} | abgeleitet aus eurer Antwort |
| `recovery-services-vault.vault.job_failure_alerts` | true | Regel |
| `recovery-services-vault.protection.protected_resources` | [] | Regel |
| `recovery-services-vault.protection.backup_schedule` | daily | Regel |
| `recovery-services-vault.protection.retention_days` | {"development": 7, "test": 7, "production": 30} | abgeleitet aus eurer Antwort |
| `recovery-services-vault.networking.public_network_access` | disabled | übernommen |
| `recovery-services-vault.networking.private_endpoint_subnet` | {"development": "snet-endpoints", "test": "snet-endpoints", "production": "snet-endpoints"} | erzwungen |
| `recovery-services-vault.encryption.key_management` | platform_managed | übernommen |
| `recovery-services-vault.encryption.managed_identity` | system_assigned | Regel |
| `recovery-services-vault.identity.role_assignments` | {"development": [], "test": [], "production": []} | Regel |
| `recovery-services-vault.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `recovery-services-vault.observability.diagnostic_categories` | ["CoreAzureBackup", "AddonAzureBackupJobs", "AddonAzureBackupAlerts", "AddonAzureBackupProtectedInstance"] | Regel |
| `recovery-services-vault.observability.metrics_enabled` | true | Regel |
| `front-door.profile.sku` | Premium_AzureFrontDoor | eure Beschreibung |
| `front-door.profile.response_timeout_seconds` | 60 | Regel |
| `front-door.profile.managed_identity` | none | Regel |
| `front-door.delivery.origins` | {"development": [{"origin": "application-gateway", "route": "/*"}], "test": [{"origin": "application-gateway", "route": "/*"}], "production": [{"origin": "application-gateway", "route": "/*"}]} | eure Beschreibung |
| `front-door.delivery.origin_connection` | public | eure Abweichung |
| `front-door.delivery.forwarding_protocol` | HttpsOnly | Regel |
| `front-door.delivery.https_redirect` | true | Regel |
| `front-door.delivery.caching` | false | Regel |
| `front-door.delivery.custom_domains` | {"development": [], "test": [], "production": []} | Regel |
| `front-door.security.waf_enabled` | true | Regel |
| `front-door.security.waf_mode` | Prevention | Regel |
| `front-door.security.waf_managed_rules` | true | Regel |
| `front-door.security.waf_rate_limit_per_minute` | 1000 | Regel |
| `front-door.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `front-door.observability.diagnostic_categories` | ["FrontDoorAccessLog", "FrontDoorHealthProbeLog", "FrontDoorWebApplicationFirewallLog"] | Regel |
| `front-door.observability.metrics_enabled` | true | Regel |
| `application-gateway.gateway.waf_enabled` | true | Regel |
| `application-gateway.gateway.waf_mode` | Prevention | Regel |
| `application-gateway.gateway.waf_rule_set` | Microsoft_DefaultRuleSet_2.1 | Regel |
| `application-gateway.gateway.waf_bot_protection` | true | Regel |
| `application-gateway.gateway.capacity_min` | {"development": 1, "test": 1, "production": 2} | abgeleitet aus eurer Antwort |
| `application-gateway.gateway.capacity_max` | {"development": 2, "test": 2, "production": 10} | Regel |
| `application-gateway.gateway.zone_redundant` | {"development": false, "test": false, "production": true} | abgeleitet aus eurer Antwort |
| `application-gateway.gateway.gateway_subnet` | {"development": "snet-gateway", "test": "snet-gateway", "production": "snet-gateway"} | erzwungen |
| `application-gateway.gateway.managed_identity` | user_assigned | Regel |
| `application-gateway.gateway.user_assigned_identity_ids` | {"development": ["user-assigned-identity__gateway"], "test": ["user-assigned-identity__gateway"], "production": ["user-assigned-identity__gateway"]} | eure Beschreibung |
| `application-gateway.networking.frontend_exposure` | public | eure Abweichung |
| `application-gateway.networking.public_ip_zone_redundant` | true | Regel |
| `application-gateway.networking.tls_policy` | AppGwSslPolicy20220101S | Regel |
| `application-gateway.networking.backend_protocol` | Https | Regel |
| `application-gateway.networking.redirect_http_to_https` | true | Regel |
| `application-gateway.networking.http2_enabled` | true | Regel |
| `application-gateway.security.waf_exclusions` | [] | Regel |
| `application-gateway.observability.diagnostic_workspace` | {"development": "log-analytics-workspace", "test": "log-analytics-workspace", "production": "log-analytics-workspace"} | übernommen |
| `application-gateway.observability.diagnostic_categories` | ["ApplicationGatewayAccessLog", "ApplicationGatewayFirewallLog"] | Regel |
| `application-gateway.observability.metrics_enabled` | true | Regel |
| `wiring.private_dns_zones` | ["privatelink.blob.core.windows.net", "privatelink.dfs.core.windows.net", "privatelink.queue.core.windows.net", "privatelink.vaultcore.azure.net", "privatelink.azurewebsites.net", "scm.privatelink.azurewebsites.net", "privatelink.servicebus.windows.net", "privatelink.eventgrid.azure.net", "privatelink.gwc.backup.windowsazure.com", "azure-api.net"] | erzwungen |
| `wiring.access` | [{"from": "users", "to": "front-door", "label": "HTTPS 443"}, {"from": "front-door", "to": "application-gateway", "label": "AzureFrontDoor.Backend, X-Azure-FDID"}, {"from": "application-gateway", "to": "api-management", "label": "HTTPS 443"}, {"from": "api-management", "to": "external:entra-id", "label": "validate-jwt"}, {"from": "api-management", "to": "function-app", "label": "backend"}, {"from": "api-management", "to": "key-vault"}, {"from": "application-gateway", "to": "key-vault", "label": "TLS certificates"}, {"from": "function-app", "to": "storage-account__host"}, {"from": "storage-account__orders", "to": "event-grid-topic", "label": "blob events"}, {"from": "event-grid-topic", "to": "function-app", "label": "delivery as managed identity"}, {"from": "event-grid-topic", "to": "storage-account__orders", "label": "dead letters"}, {"from": "event-hubs", "to": "storage-account__lake", "label": "capture"}, {"from": "backup-vault", "to": "storage-account__orders", "label": "blob backup"}] | eure Beschreibung |
| `wiring.purposes` | {"front-door": "Entry point with web application firewall", "application-gateway": "Second firewall stage; reachable from Front Door only", "api-management": "API gateway: JWT validation, rate limit per subscription, routing", "function-app": "Order API backend; receives the blob events", "service-bus": "Order messaging: topic orders, queue payments", "event-hubs": "Telemetry stream, captured to the data lake", "event-grid-topic": "Delivers blob events to the function app", "storage-account__orders": "Order blobs; backed up. Kept apart from the data lake - blob backup does not take a hierarchical namespace", "storage-account__lake": "Data lake (Data Lake Gen2) for the telemetry capture", "storage-account__host": "State of the function app", "backup-vault": "Blob backup of the orders account", "recovery-services-vault": "Backup of virtual machines", "key-vault": "Secrets and TLS certificates", "log-analytics-workspace": "Central workspace for every diagnostic setting", "user-assigned-identity__func": "Function app", "user-assigned-identity__gateway": "Application gateway", "network-security-group__endpoints": "Private endpoints subnet", "network-security-group__func": "Function integration subnet", "network-security-group__gateway": "Gateway subnet; Front Door in, API Management out", "network-security-group__apim": "API Management subnet"} | eure Beschreibung |
| `wiring.optional` | [] | Regel |
