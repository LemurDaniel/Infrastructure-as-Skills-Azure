# Entscheidungen für „invoicing“

Was gebaut wird, entschieden aus euren Antworten und den Regeln hinter den Vorgaben. Jede Zeile ist eine Entscheidung; der Schlüssel im Anhang ist, wo ein Engineer sie in der Spezifikation findet.

Stand 2026-10-18. Spezifikation: `infra-spec.yaml`.

## Das System

- Das System wird in diesen Stufen ausgerollt: Entwicklung, Test, Echtbetrieb.
- Alles läuft in der Azure-Region westeurope.
- „invoicing“ ist der Name, den jeder Teil des Systems trägt.
- Jede Stufe liegt in einer eigenen Subscription; die Stufen können sich gegenseitig weder Ressourcen noch Budgets noch Berechtigungen anfassen.

## Was sich zwischen den Stufen unterscheidet

Ein Code wird durch diese Stufen ausgerollt; alles, was hier nicht steht, ist in jeder Stufe gleich.

- Das System wird in die Subscription Echtbetrieb: 11111111-2222-3333-4444-555555555555 ausgerollt.
- Alle Teile liegen in der bestehenden Ressourcengruppe Echtbetrieb: rg-invoicing-prod-we.
- Das bestehende Netz Echtbetrieb: vnet-hub-prod-we (rg-network-prod-we) wird genutzt.
- Private Anbindungen landen im bestehenden Subnetz Echtbetrieb: snet-privatelink.
- Protokolle werden in Echtbetrieb: log-platform-prod-we (rg-observability-prod-we) gesammelt.
- Azure Storage Account: Seine private Anbindung landet im Subnetz Echtbetrieb: snet-privatelink.
- Azure Storage Account: Die Daten liegen Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Echtbetrieb: in drei Rechenzentren der Region, eines darf ausfallen. _(außerhalb der Produktion günstiger)_
- Azure Storage Account: Seine Protokolle gehen in Echtbetrieb: log-platform-prod-we (rg-observability-prod-we).

## Was aus euren Antworten folgt

- **Das System wird durch eine GitLab-CI-Pipeline ausgerollt.** _(aus eurer Beschreibung)_
- **Ein Tag Ausfall wäre störend.** _(nicht gesagt, daher gilt die übliche Antwort)_
  - daher, Azure Storage Account: Die Daten liegen Entwicklung: dreifach in einem Rechenzentrum; Test: dreifach in einem Rechenzentrum; Echtbetrieb: in drei Rechenzentren der Region, eines darf ausfallen.
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
- **Einzuhaltende Vorgaben: BSI C5.** _(aus eurer Beschreibung)_

## Nach den Vorgaben gesetzt

Nichts davon wurde gefragt; jede Zeile folgt einer Regel oder einer der Antworten oben. Sagt Bescheid, wenn eine nicht passt.

### Für das ganze System

- Die Pipeline meldet sich mit einem kurzlebigen Token pro Lauf, ohne irgendwo gespeichertes Passwort bei Azure an.
- Eine Person gibt die Änderung frei, bevor sie ausgerollt wird: nur im Echtbetrieb.
- Nutzungstelemetrie an Microsoft ist eingeschaltet: eine Zählung pro Ausrollen, keine eurer Daten.
- Das System landet in dem internen Teil der Firmenplattform, verbunden mit dem Firmennetz. — weil: Das Netz wird das bestehende, hier genutzt und nie verändert.
- Passwörter und Zugriffsschlüssel sind abgeschaltet; der Zugriff läuft über Firmenkonten, damit jede Aktion zuordenbar ist.
- Verschlüsselungsschlüssel sind in Software geschützt, der Standard, ausreichend ohne Vorgabe für Hardware.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Das Netz wird das bestehende, hier genutzt und nie verändert.
- Das bestehende Netz Echtbetrieb: vnet-hub-prod-we (rg-network-prod-we) wird genutzt.
- Private Anbindungen landen im bestehenden Subnetz Echtbetrieb: snet-privatelink.
- Die Namensauflösung für private Anbindungen übernimmt die Firmenplattform.
- Die Namenseinträge für private Anbindungen schreibt eine Plattformregel, automatisch.
- Protokolle gehen in den zentralen Protokoll-Arbeitsbereich der Firma.
- Protokolle werden in Echtbetrieb: log-platform-prod-we (rg-observability-prod-we) gesammelt.

### Azure Storage Account

- Der Speicher ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz Echtbetrieb: snet-privatelink.
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
- Seine Protokolle gehen in Echtbetrieb: log-platform-prod-we (rg-observability-prod-we).
- Protokolliert wird: wer worauf zugegriffen hat.
- Nutzungs- und Leistungswerte werden erfasst.

## Noch offen

Solange diese Punkte offen sind, wird nichts ausgerollt.

- Which subscriptions do the development and test stages deploy into? The request named production's; the stack is one subscription per stage. [Entwicklung, Test] _(gebraucht von: platform team)_ — blockiert: apply
- Which resource group does each of the other stages deploy into? [Entwicklung, Test] _(gebraucht von: platform team)_ — blockiert: apply
- Which hub network do the development and test stages attach to? [Entwicklung, Test] _(gebraucht von: platform team)_ — blockiert: apply
- Which subnet carries the private endpoints in the development and test hubs? [Entwicklung, Test] _(gebraucht von: platform team)_ — blockiert: apply
- Which workspace receives the development and test stages' diagnostics? [Entwicklung, Test] _(gebraucht von: platform team)_ — blockiert: apply
- Follows deployment.private_endpoint_subnet per stage. [Entwicklung, Test] _(gebraucht von: platform team)_ — blockiert: apply
- Follows deployment.diagnostics_destination per stage. [Entwicklung, Test] _(gebraucht von: platform team)_ — blockiert: apply
- Which tag set does the organisation apply? Nothing in the request, no repository to read it from. _(gebraucht von: workload owner)_ — blockiert: apply
- Which principal reads and writes the invoices, and which data-plane role does it need? Shared-key auth is off, so an account with no assignment is working as specified and unusable. _(gebraucht von: workload owner)_ — blockiert: apply

## Anhang: alle Entscheidungen

| Schlüssel | Wert | Quelle |
|---|---|---|
| `deployment.naming_convention` | default | Regel |
| `deployment.module_source` | avm | Regel |
| `deployment.module_telemetry` | enabled | Regel |
| `deployment.deploy_mechanism` | gitlab | eure Beschreibung |
| `deployment.pipeline_auth` | workload_identity | Regel |
| `deployment.pipeline_approvals` | production | Regel |
| `deployment.stage_isolation` | subscription | Regel |
| `deployment.non_production_savings` | enabled | Regel |
| `deployment.outage_impact` | disruptive | Regel |
| `deployment.data_loss_tolerance` | one_week | Regel |
| `deployment.data_access_pattern` | active | Regel |
| `deployment.backup_isolation` | operational | Regel |
| `deployment.data_residency` | data_zone | Regel |
| `deployment.landing_zone` | corp | erzwungen |
| `deployment.network_exposure` | private | eure Beschreibung |
| `deployment.local_auth` | disabled | Regel |
| `deployment.mandates` | ["BSI C5"] | eure Beschreibung |
| `deployment.key_protection` | software | Regel |
| `deployment.key_management` | platform_managed | Regel |
| `deployment.network_ownership` | reference | eure Beschreibung |
| `deployment.existing_vnet` | {"production": {"name": "vnet-hub-prod-we", "resource_group_name": "rg-network-prod-we"}} | eure Beschreibung |
| `deployment.private_endpoint_subnet` | {"production": "snet-privatelink"} | eure Beschreibung |
| `deployment.private_dns_ownership` | platform | Regel |
| `deployment.private_dns_records` | policy | Regel |
| `deployment.observability_ownership` | reference | eure Beschreibung |
| `deployment.diagnostics_destination` | {"production": {"name": "log-platform-prod-we", "resource_group_name": "rg-observability-prod-we"}} | eure Beschreibung |
| `storage-account.networking.public_network_access` | disabled | übernommen |
| `storage-account.networking.private_endpoint_subnet` | {"production": "snet-privatelink"} | übernommen |
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
| `storage-account.data_protection.replication` | {"development": "LRS", "test": "LRS", "production": "ZRS"} | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.access_tier` | Hot | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.blob_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.container_soft_delete_days` | 7 | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.versioning_enabled` | true | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.change_feed_enabled` | false | Regel |
| `storage-account.data_protection.point_in_time_restore_days` | 0 | Regel |
| `storage-account.data_protection.immutability` | none | Regel |
| `storage-account.observability.diagnostic_workspace` | {"production": {"name": "log-platform-prod-we", "resource_group_name": "rg-observability-prod-we"}} | übernommen |
| `storage-account.observability.diagnostic_categories` | ["audit"] | Regel |
| `storage-account.observability.metrics_enabled` | true | Regel |
