# Entscheidungen für „telemetry“

Was gebaut wird, entschieden aus euren Antworten und den Regeln hinter den Vorgaben. Jede Zeile ist eine Entscheidung; der Schlüssel im Anhang ist, wo ein Engineer sie in der Spezifikation findet.

Stand 2026-10-18. Spezifikation: `infra-spec.yaml`.

## Das System

- Das System wird in diesen Stufen ausgerollt: Entwicklung, Test, Vorproduktion, Echtbetrieb.
- Alles läuft in der Azure-Region germanywestcentral.
- „telemetry“ ist der Name, den jeder Teil des Systems trägt.
- Jede Stufe liegt in einer eigenen Subscription; die Stufen können sich gegenseitig weder Ressourcen noch Budgets noch Berechtigungen anfassen.

## Was sich zwischen den Stufen unterscheidet

Ein Code wird durch diese Stufen ausgerollt; alles, was hier nicht steht, ist in jeder Stufe gleich.

- Das System wird in die Subscription Vorproduktion: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee ausgerollt.
- Alle Teile liegen in der bestehenden Ressourcengruppe Vorproduktion: rg-telemetry-stg-gwc.
- Das neue Netz nutzt den Adressbereich Vorproduktion: 10.20.0.0/16, zugewiesen von der Adressverwaltung.
- Private Anbindungen bekommen ein eigenes Subnetz, Vorproduktion: 10.20.1.0/27.
- Azure Virtual Network: Das Netz nutzt den Adressbereich Vorproduktion: 10.20.0.0/16.
- Azure Virtual Network: Subnetze: Vorproduktion: snet-stg-privatelink-01 (10.20.1.0/27), snet-app (10.20.2.0/24).
- Azure Virtual Network: Private Anbindungen bekommen das Subnetz Vorproduktion: 10.20.1.0/27.
- Azure Storage Account: Die Daten liegen Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Vorproduktion: dreifach in einem Rechenzentrum; Echtbetrieb: in drei Rechenzentren der Region, eines darf ausfallen. _(außerhalb der Produktion günstiger)_

## Was aus euren Antworten folgt

- **Das System wird durch eine Azure-DevOps-Pipeline ausgerollt.** _(aus eurer Beschreibung)_
- **Ein Tag Ausfall wäre störend.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure Storage Account: Die Daten liegen Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Vorproduktion: dreifach in einem Rechenzentrum; Echtbetrieb: in drei Rechenzentren der Region, eines darf ausfallen.
- **Nach einem versehentlichen Löschen müsst ihr eine Woche zurückkommen.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure Storage Account: Gelöschte Dateien sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account: Gelöschte Ordner sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account: Frühere Versionen überschriebener Dateien werden aufgehoben.
- **Die Daten werden laufend genutzt.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure Storage Account: Gespeichert in der Klasse Standard: günstig beim Lesen, für Daten in Nutzung.
- **Gegen absichtliche Zerstörung sind die Daten nur innerhalb des Systems selbst geschützt; wer das System löschen kann, kann auch die Kopien löschen.** _(nicht gesagt, daher gilt die übliche Antwort)_
- **Die Daten werden nur innerhalb des Wirtschaftsraums der Region, zum Beispiel der EU gespeichert und verarbeitet.** _(nicht gesagt, daher gilt die übliche Antwort)_
- **Der Code wird aus Microsofts geprüften, getesteten Bausteinen (Azure Verified Modules) gebaut.** _(nicht gesagt, daher gilt die übliche Antwort)_
- **Der Zugang ist nur privat, nichts ist aus dem Internet erreichbar.** _(aus eurer Beschreibung)_
- **Einzuhaltende Vorgaben: keine.** _(nicht gesagt, daher gilt die übliche Antwort)_
- **Protokolle werden 90 Tage aufbewahrt.** _(aus eurer Beschreibung)_

## Nach den Vorgaben gesetzt

Nichts davon wurde gefragt; jede Zeile folgt einer Regel oder einer der Antworten oben. Sagt Bescheid, wenn eine nicht passt.

### Für das ganze System

- Die Pipeline meldet sich mit einem kurzlebigen Token pro Lauf, ohne irgendwo gespeichertes Passwort bei Azure an.
- Eine Person gibt die Änderung frei, bevor sie ausgerollt wird: nur im Echtbetrieb.
- Nutzungstelemetrie an Microsoft ist eingeschaltet: eine Zählung pro Ausrollen, keine eurer Daten.
- Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Protokollierung selbst mit.
- Passwörter und Zugriffsschlüssel sind abgeschaltet; der Zugriff läuft über Firmenkonten, damit jede Aktion zuordenbar ist.
- Verschlüsselungsschlüssel sind in Software geschützt, der Standard, ausreichend ohne Vorgabe für Hardware.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Das Netz wird von diesem Ausrollen selbst gebaut.
- Das neue Netz nutzt den Adressbereich Vorproduktion: 10.20.0.0/16, zugewiesen von der Adressverwaltung.
- Private Anbindungen bekommen ein eigenes Subnetz, Vorproduktion: 10.20.1.0/27.
- Die Namensauflösung für private Anbindungen übernimmt dieses Ausrollen selbst. — weil: Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Protokollierung selbst mit.
- Protokolle gehen in einen Arbeitsbereich, den dieses Ausrollen anlegt und bezahlt.
- Tägliche Obergrenze für Protokolle: -1 GB (-1: keine).

### Azure Virtual Network

- Das Netz nutzt den Adressbereich Vorproduktion: 10.20.0.0/16.
- Subnetze: Vorproduktion: snet-stg-privatelink-01 (10.20.1.0/27), snet-app (10.20.2.0/24).
- Private Anbindungen bekommen das Subnetz Vorproduktion: 10.20.1.0/27.
- Eigene Namensserver: keine (keine: Azures eigene).
- Netzwerkregeln gelten für private Anbindungen in ihrem Subnetz.
- Abkürzungen zu Azure-Diensten aus den Subnetzen: keine.
- An einen Dienst übergebene Subnetze: keine.
- Ein kostenpflichtiger DDoS-Schutzplan wird nicht genutzt; Azures Basisschutz gilt ohnehin.
- Subnetze, die eine Sicherheitsgruppe bekommen: keine.
- Netzwerkprotokolle gehen in log-gwc-stg-telemetry-01 (rg-telemetry-stg-gwc).
- Eine Aufzeichnung erlaubten und abgewiesenen Verkehrs wird nicht geführt.

### Azure Log Analytics Workspace

- Protokolle werden 90 Tage aufbewahrt.
- Tägliche Obergrenze für Protokolle: -1 GB (-1: keine).
- Abgerechnet pro Gigabyte, nach Verbrauch.
- Der Protokoll-Arbeitsbereich ist aus dem Internet erreichbar, mit Firmenkonten und Verschlüsselung; einen privaten Zugang dafür gibt es nicht.
- Protokolle mit dem Arbeitsbereichs-Schlüssel zu senden ist nicht möglich, Agenten nutzen Firmenidentitäten.
- Wer Protokolle lesen darf, entscheiden die Berechtigungen des Arbeitsbereichs selbst.
- Ein gelöschter Arbeitsbereich kann 14 Tage lang wiederhergestellt werden.
- Langzeitarchivierung in günstigen Speicher ist ausgeschaltet.

### Azure Storage Account

- Der Speicher ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz snet-stg-privatelink-01.
- Private Anbindungen gibt es für: Dateien (Blob).
- Azures eigene Dienste (Backup, Überwachung) dürfen am Firewall vorbei auf den Speicher zugreifen.
- Der Speicher hat eine eigene Identität, um andere Dienste zu erreichen.
- Zugriffsrechte vergeben an: keine.
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
- Seine Protokolle gehen in log-gwc-stg-telemetry-01 (rg-telemetry-stg-gwc).
- Protokolliert wird: wer worauf zugegriffen hat.
- Nutzungs- und Leistungswerte werden erfasst.

## Noch offen

Solange diese Punkte offen sind, wird nichts ausgerollt.

- Which subscriptions do the development, test and production stages deploy into? The request named staging's only; the stack is one subscription per stage. [Entwicklung, Test, Echtbetrieb] _(gebraucht von: platform team)_ — blockiert: apply
- Which resource group does each of the other stages deploy into? [Entwicklung, Test, Echtbetrieb] _(gebraucht von: platform team)_ — blockiert: apply
- Which address ranges are assigned to the development, test and production networks? Staging's is 10.20.0.0/16; the others cannot overlap it. [Entwicklung, Test, Echtbetrieb] _(gebraucht von: network / IPAM owner)_ — blockiert: apply
- Which prefix out of each stage's range carries its private endpoints? [Entwicklung, Test, Echtbetrieb] _(gebraucht von: network / IPAM owner)_ — blockiert: apply
- Follows deployment.address_space per stage. [Entwicklung, Test, Echtbetrieb] _(gebraucht von: network / IPAM owner)_ — blockiert: apply
- Each stage's subnets follow its range; the app subnet keeps its name and size. [Entwicklung, Test, Echtbetrieb] _(gebraucht von: network / IPAM owner)_ — blockiert: apply
- Follows deployment.private_endpoint_subnet_prefix per stage. [Entwicklung, Test, Echtbetrieb] _(gebraucht von: network / IPAM owner)_ — blockiert: apply
- Which tag set does the organisation apply? Nothing in the request, no repository to read it from. _(gebraucht von: workload owner)_ — blockiert: apply
- Which principal writes and reads the raw data, and which data-plane role does it need? Shared-key auth is off, so an account with no assignment is working as specified and unusable. _(gebraucht von: workload owner)_ — blockiert: apply

## Anhang: alle Entscheidungen

| Schlüssel | Wert | Quelle |
|---|---|---|
| `deployment.naming_convention` | default | Regel |
| `deployment.module_source` | avm | Regel |
| `deployment.module_telemetry` | enabled | Regel |
| `deployment.deploy_mechanism` | azure_devops | eure Beschreibung |
| `deployment.pipeline_auth` | workload_identity | Regel |
| `deployment.pipeline_approvals` | production | Regel |
| `deployment.stage_isolation` | subscription | Regel |
| `deployment.non_production_savings` | enabled | Regel |
| `deployment.outage_impact` | disruptive | Regel |
| `deployment.data_loss_tolerance` | one_week | Regel |
| `deployment.data_access_pattern` | active | Regel |
| `deployment.backup_isolation` | operational | Regel |
| `deployment.data_residency` | data_zone | Regel |
| `deployment.landing_zone` | standalone | Regel |
| `deployment.network_exposure` | private | eure Beschreibung |
| `deployment.local_auth` | disabled | Regel |
| `deployment.mandates` | [] | Regel |
| `deployment.key_protection` | software | Regel |
| `deployment.key_management` | platform_managed | Regel |
| `deployment.network_ownership` | create | eure Beschreibung |
| `deployment.address_space` | {"staging": "10.20.0.0/16"} | eure Beschreibung |
| `deployment.private_endpoint_subnet_prefix` | {"staging": "10.20.1.0/27"} | eure Beschreibung |
| `deployment.private_dns_ownership` | deployment | erzwungen |
| `deployment.observability_ownership` | create | eure Beschreibung |
| `deployment.log_retention_days` | 90 | eure Beschreibung |
| `deployment.daily_quota_gb` | -1 | Regel |
| `virtual-network.addressing.address_space` | {"staging": "10.20.0.0/16"} | übernommen |
| `virtual-network.addressing.subnets` | {"staging": [{"name": "snet-stg-privatelink-01", "prefix": "10.20.1.0/27", "purpose": "private_endpoints"}, {"name": "snet-app", "prefix": "10.20.2.0/24"}]} | eure Beschreibung |
| `virtual-network.addressing.private_endpoint_subnet_prefix` | {"staging": "10.20.1.0/27"} | übernommen |
| `virtual-network.addressing.dns_servers` | [] | Regel |
| `virtual-network.subnet_policy.private_endpoint_network_policies` | Enabled | Regel |
| `virtual-network.subnet_policy.service_endpoints` | [] | Regel |
| `virtual-network.subnet_policy.subnet_delegations` | [] | Regel |
| `virtual-network.security.ddos_protection` | false | Regel |
| `virtual-network.security.subnets_expecting_nsg` | [] | Regel |
| `virtual-network.observability.diagnostic_workspace` | {"name": "log-gwc-stg-telemetry-01", "resource_group_name": "rg-telemetry-stg-gwc"} | übernommen |
| `virtual-network.observability.flow_logs_enabled` | false | Regel |
| `log-analytics-workspace.cost.retention_days` | 90 | übernommen |
| `log-analytics-workspace.cost.daily_quota_gb` | -1 | übernommen |
| `log-analytics-workspace.cost.sku` | PerGB2018 | Regel |
| `log-analytics-workspace.access.public_network_access` | enabled | Regel |
| `log-analytics-workspace.access.local_auth` | false | übernommen |
| `log-analytics-workspace.access.rbac_only_access` | true | Regel |
| `log-analytics-workspace.data_protection.immediate_purge_protection` | true | Regel |
| `log-analytics-workspace.data_protection.archive_to_storage` | false | Regel |
| `storage-account.networking.public_network_access` | disabled | übernommen |
| `storage-account.networking.private_endpoint_subnet` | snet-stg-privatelink-01 | übernommen |
| `storage-account.networking.private_endpoint_subresources` | ["blob"] | Regel |
| `storage-account.networking.allow_azure_services_bypass` | true | Regel |
| `storage-account.identity.managed_identity` | system_assigned | Regel |
| `storage-account.identity.role_assignments` | [] | Regel |
| `storage-account.security.shared_access_key_enabled` | false | übernommen |
| `storage-account.security.min_tls_version` | TLS1_2 | Regel |
| `storage-account.security.https_traffic_only` | true | Regel |
| `storage-account.security.allow_blob_public_access` | false | Regel |
| `storage-account.security.infrastructure_encryption_enabled` | true | Regel |
| `storage-account.security.key_management` | platform_managed | übernommen |
| `storage-account.security.sftp_enabled` | false | Regel |
| `storage-account.data_protection.replication` | {"development": "LRS", "test": "LRS", "staging": "LRS", "production": "ZRS"} | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.access_tier` | Hot | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.blob_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.container_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.versioning_enabled` | true | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.change_feed_enabled` | false | Regel |
| `storage-account.data_protection.point_in_time_restore_days` | 0 | Regel |
| `storage-account.data_protection.immutability` | none | Regel |
| `storage-account.observability.diagnostic_workspace` | {"name": "log-gwc-stg-telemetry-01", "resource_group_name": "rg-telemetry-stg-gwc"} | übernommen |
| `storage-account.observability.diagnostic_categories` | ["audit"] | Regel |
| `storage-account.observability.metrics_enabled` | true | Regel |
| `wiring.private_dns_zones` | ["privatelink.blob.core.windows.net"] | erzwungen |
| `wiring.private_dns_zone_links` | [{"zone": "privatelink.blob.core.windows.net", "network": "virtual-network"}] | erzwungen |
