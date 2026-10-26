# Entscheidungen für „chat“

Was gebaut wird, entschieden aus euren Antworten und den Regeln hinter den Vorgaben. Jede Zeile ist eine Entscheidung; der Schlüssel im Anhang ist, wo ein Engineer sie in der Spezifikation findet.

Stand 2026-10-24. Spezifikation: `infra-spec.yaml`.

## Das System

- Das System wird in diesen Stufen ausgerollt: Sandbox, eine Wegwerf-Umgebung.
- Alles läuft in der Azure-Region germanywestcentral.
- „chat“ ist der Name, den jeder Teil des Systems trägt.

## Was aus euren Antworten folgt

- **Das System wird von Hand von einem Arbeitsplatz, ohne Pipeline ausgerollt.** _(eure Antwort)_
- **Ein Tag Ausfall wäre verkraftbar.** _(eure Antwort)_
  - daher, Azure App Service (web app on an App Service plan): Die App übersteht nicht den Ausfall eines Rechenzentrums der Region.
  - daher, Azure App Service (web app on an App Service plan): Gleichzeitig laufende Kopien der App: 1.
  - daher, Azure AI Search service: 1 Kopien des Index beantworten Anfragen.
  - daher, Azure Storage Account: Die Daten liegen dreifach in einem Rechenzentrum.
- **Nach einem versehentlichen Löschen müsst ihr eine Woche zurückkommen.** _(eure Antwort)_
  - daher, Azure Storage Account: Gelöschte Dateien sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account: Gelöschte Ordner sind 7 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account: Frühere Versionen überschriebener Dateien werden aufgehoben.
- **Die Daten werden laufend genutzt.** _(eure Antwort)_
  - daher, Azure Storage Account: Gespeichert in der Klasse Standard: günstig beim Lesen, für Daten in Nutzung.
- **Gegen absichtliche Zerstörung sind die Daten nur innerhalb des Systems selbst geschützt; wer das System löschen kann, kann auch die Kopien löschen.** _(eure Antwort)_
- **Die Daten werden nur innerhalb des Wirtschaftsraums der Region, zum Beispiel der EU gespeichert und verarbeitet.** _(eure Antwort)_
  - daher, Azure AI Foundry (AI Services account with projects and model deployments): Anfragen an die Modelle werden überall innerhalb derselben Datenzone (zum Beispiel der EU) verarbeitet.
- **Der Code wird aus einzeln ausgeschriebenen Ressourcen gebaut.** _(eure Antwort)_
- **Die Ressourcennamen erzeugt das Naming-Werkzeug des Plugins, gesteuert über eine Namensdatei, die ihr anpassen könnt.** _(eure Antwort)_
- **Der Zugang ist öffentlich: jeder Teil, auch die Datenbanken, ist absichtlich aus dem Internet erreichbar.** _(eure Antwort)_
- **Einzuhaltende Vorgaben: keine.** _(eure Antwort)_
- **Logs werden 30 Tage aufbewahrt.** _(eure Antwort)_

## Nach den Vorgaben gesetzt

Nichts davon wurde gefragt; jede Zeile folgt einer Regel oder einer der Antworten oben. Sagt Bescheid, wenn eine nicht passt.

### Für das ganze System

- Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Logging selbst mit.
- Passwörter und Zugriffsschlüssel sind abgeschaltet; der Zugriff läuft über Firmenkonten, damit jede Aktion zuordenbar ist.
- Verschlüsselungsschlüssel sind in Software geschützt, der Standard, ausreichend ohne Vorgabe für Hardware.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Das Netz wird nicht gebraucht, alles wird über öffentliche Endpunkte erreicht. — weil: Der Zugang ist öffentlich: jeder Teil, auch die Datenbanken, ist absichtlich aus dem Internet erreichbar.
- Die Namensauflösung für private Anbindungen übernimmt dieses Ausrollen selbst. — weil: Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Logging selbst mit.
- Logs gehen in einen Arbeitsbereich, den dieses Ausrollen anlegt und bezahlt. — weil: Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Logging selbst mit.
- Logs werden in log-analytics-workspace gesammelt. — weil: Logs gehen in einen Arbeitsbereich, den dieses Ausrollen anlegt und bezahlt.
- Tägliche Obergrenze für Logs: -1 GB (-1: keine).

### Sicherheit

Die Sicherheitsvorgaben aller Teile an einer Stelle. Sie wurden nicht gefragt und sind in jeder Stufe gleich; sagt Bescheid, wenn eine nicht passt.

- **Azure App Service (web app on an App Service plan)**
  - Die App hat eine eigene Identität, um andere Dienste zu erreichen.
  - Unverschlüsselte Verbindungen werden auf die verschlüsselte Adresse umgeleitet.
  - Verbindungen müssen mindestens TLS 1.2-Verschlüsselung nutzen.
  - Dateiupload per FTP ist abgeschaltet.
  - Das Ausrollen mit Benutzername und Passwort ist nicht möglich; Rollouts laufen über Firmenkonten.
- **Azure AI Foundry (AI Services account with projects and model deployments)**
  - Das Konto hat eine eigene Identität.
  - Zugriffsrechte auf das Konto vergeben an: app-service (Cognitive Services OpenAI User), search-service (Cognitive Services OpenAI User). — weil: `wiring.access`
  - Die Anmeldung mit Kontoschlüsseln ist abgeschaltet; der Zugriff läuft über Firmenkonten.
  - Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- **Azure AI Search service**
  - Der Suchdienst hat eine eigene Identität.
  - Zugriffsrechte auf den Suchdienst vergeben an: app-service (Search Index Data Reader). — weil: `wiring.access`
  - Die Anmeldung mit API-Schlüsseln ist abgeschaltet; der Zugriff läuft über Firmenkonten.
  - Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- **Azure Storage Account**
  - Der Speicher hat eine eigene Identität, um andere Dienste zu erreichen.
  - Zugriffsrechte vergeben an: app-service (Storage Blob Data Contributor), search-service (Storage Blob Data Reader). — weil: `wiring.access`
  - Zugriff mit einem geteilten Schlüssel ist nicht möglich; der Zugriff läuft über Firmenkonten.
  - Verbindungen müssen mindestens TLS 1.2-Verschlüsselung nutzen.
  - Unverschlüsselte Verbindungen werden abgewiesen.
  - Einzelne Ordner öffentlich lesbar zu machen ist nicht möglich.
  - Eine zweite Verschlüsselungsschicht unterhalb des Dienstes ist eingeschaltet.
  - Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
  - Dateiübertragung per SFTP ist ausgeschaltet.
- **Azure Key Vault**
  - Zugriffsrechte auf den Tresor vergeben an: app-service (Key Vault Secrets User). — weil: `wiring.access`
  - Plattformdienste, die aus dem Tresor lesen dürfen: keine (leer: keine).
  - Für die Geheimnisse entra-client-secret werden leere Plätze angelegt; die Werte werden danach von Hand oder von der Anwendung eingetragen.

### Azure App Service (web app on an App Service plan)

- Die App läuft auf Linux.
- Der Hosting-Plan hat die Größe B1, klein und günstig, ohne Zonenredundanz, für Stufen von denen niemand abhängt. — weil: `deployment.environments`
- Der ausgehende Verkehr der App geht über das öffentliche Internet raus. — weil: Das Netz wird nicht gebraucht, alles wird über öffentliche Endpunkte erreicht.
- Die App ist geschrieben für ein Container-Image, das seine Laufzeit selbst mitbringt.
- Die App bleibt geladen und antwortet sofort auf die erste Anfrage, wenn kein Verkehr anliegt.
- Die Plattform prüft die Gesundheit der App unter dem Pfad  (leer: keine Prüfung).
- HTTP/2 ist eingeschaltet.
- Seine Logs gehen in log-analytics-workspace.
- Geloggt wird: jede Web-Anfrage, die eigenen Log-Meldungen der App, wer sich zum Ausrollen oder Verwalten angemeldet hat, Änderungen an den Zugriffsbeschränkungen, die eigenen Meldungen der Plattform zur App.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure AI Foundry (AI Services account with projects and model deployments)

- Das Konto ist eine AI-Foundry-Ressource, die auch Projekte, Agenten und die weiteren KI-Dienste bietet.
- Das Konto nutzt die Preisstufe S0, die bezahlte Standardstufe.
- Das Konto enthält Foundry-Projekte als Behälter für Zugriff, Daten und Kosten.
- Das Konto enthält die Projekte chat.
- Jedes Modell darf bis zu 10 Tausend Token pro Minute verarbeiten.
- Läuft die Modellversion aus, wechselt sie an diesem Tag auf die neue Standardversion.
- Anfragen und Antworten werden vom Inhaltsfilter Microsoft.DefaultV2 geprüft.
- Das Konto darf nur Adressen aufrufen, die ausdrücklich erlaubt sind.
- Seine Logs gehen in log-analytics-workspace.
- Geloggt wird: Änderungen am Konto und wer sie gemacht hat, jede Anfrage an die Modelle mit Aufrufer, Größe und Ergebnis (nicht der Text), die von jedem Aufruf verbrauchten Token.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure AI Search service

- Der Suchdienst hat die Stufe Basic, klein und günstig, eine Partition. — weil: `deployment.environments`
- Die Indexdaten sind auf 1 Partition(en) verteilt.
- Die Neubewertung der Ergebnisse nach Bedeutung ist an, im Rahmen eines kleinen kostenlosen Monatskontingents.
- Vertrauenswürdige Azure-Dienste dürfen nicht an der Firewall des Suchdienstes vorbei.
- Seine Logs gehen in log-analytics-workspace.
- Geloggt wird: jede Abfrage und jede Änderung an Indizes und Indexern.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Storage Account

- Private Anbindungen gibt es für: Dateien (Blob).
- Azures eigene Dienste (Backup, Überwachung) dürfen am Firewall vorbei auf den Speicher zugreifen.
- Ein Log jeder Änderung wird nicht geführt.
- Der ganze Speicher lässt sich 0 Tage zurückdrehen (0: gar nicht).
- Löschschutz per Gesetz oder Richtlinie: keiner.
- Seine Logs gehen in log-analytics-workspace.
- Geloggt wird: wer worauf zugegriffen hat.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Key Vault

- Der Tresor ist die Stufe Standard, Schlüssel in Software geschützt.
- Der Zugriff auf den Inhalt des Tresors wird über Rollenzuweisungen, wie alles andere in Azure gesteuert.
- Vertrauenswürdige Azure-Dienste dürfen nicht an der Firewall des Tresors vorbei.
- Verschlüsselungsschlüssel sind von Azure verwaltet - der Tresor hält dafür keine.
- Seine Logs gehen in log-analytics-workspace.
- Geloggt wird: jeder Lese-, Schreib- und fehlgeschlagene Zugriff auf den Tresor, wie Richtlinien den Tresor bewertet haben.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Log Analytics Workspace

- Logs werden 30 Tage aufbewahrt.
- Tägliche Obergrenze für Logs: -1 GB (-1: keine).
- Abgerechnet pro Gigabyte, nach Verbrauch.
- Der Log-Arbeitsbereich ist aus dem Internet erreichbar, mit Firmenkonten und Verschlüsselung; einen privaten Zugang dafür gibt es nicht.
- Logs mit dem Arbeitsbereichs-Schlüssel zu senden ist disabled.
- Wer Logs lesen darf, entscheiden die Berechtigungen des Arbeitsbereichs selbst.
- Ein gelöschter Arbeitsbereich kann 14 Tage lang wiederhergestellt werden.
- Langzeitarchivierung in günstigen Speicher ist ausgeschaltet.

## Von euch anders entschieden

- Azure App Service (web app on an App Service plan): Die App ist aus dem Internet erreichbar. _(Grund: departs from the deployment mapping public -> enabled_with_firewall; network_ownership is none, so the app's outbound addresses are public and change, and a firewall with no rules would lock the app out of its own backends)_
- Azure AI Foundry (AI Services account with projects and model deployments): Das Konto ist aus dem Internet erreichbar. _(Grund: departs from the deployment mapping public -> enabled_with_firewall; network_ownership is none, so the app's outbound addresses are public and change, and a firewall with no rules would lock the app out of its own backends)_
- Azure AI Search service: Der Suchdienst ist aus dem Internet erreichbar. _(Grund: departs from the deployment mapping public -> enabled_with_firewall; network_ownership is none, so the app's outbound addresses are public and change, and a firewall with no rules would lock the app out of its own backends)_
- Azure Storage Account: Der Speicher ist aus dem Internet erreichbar. _(Grund: departs from the deployment mapping public -> enabled_with_firewall; network_ownership is none, so the app's outbound addresses are public and change, and a firewall with no rules would lock the app out of its own backends)_
- Azure Key Vault: Ein gelöschter Tresor oder ein gelöschtes Geheimnis lässt sich von jedem mit dem Recht endgültig löschen, bevor die Aufbewahrungszeit endet. _(Grund: a throwaway sandbox is torn down and rebuilt; purge protection would reserve the vault name for the soft-delete window after every tear-down and cannot be switched off once on)_
- Azure Key Vault: Gelöschte Inhalte des Tresors lassen sich 7 Tage lang wiederherstellen. _(Grund: the shortest window Azure allows, for the same reason - the name comes back after a week instead of a quarter; nothing in this vault is irreplaceable (one placeholder secret))_
- Azure Key Vault: Der Tresor ist aus dem Internet erreichbar. _(Grund: departs from the deployment mapping public -> enabled_with_firewall; network_ownership is none, so the app's outbound addresses are public and change, and a firewall with no rules would lock the app out of its own backends)_

## Noch offen

Solange diese Punkte offen sind, wird nichts ausgerollt.

- Welches Container-Image läuft in der App - Registry, Repository und ein Tag, der nicht "latest" ist? Und aus welcher Registry darf die App es mit ihrer Identität ziehen? [Sandbox, eine Wegwerf-Umgebung] _(gebraucht von: Workload-Team)_ — blockiert: apply
- Welches Chat-Modell und welches Embedding-Modell, in welchen genauen Versionen, mit welchem Kontingent? Wird beim Rendern gegen den Katalog der Region als DataZoneStandard nachgeschlagen, nie aus dem Gedächtnis. [Sandbox, eine Wegwerf-Umgebung] _(gebraucht von: Workload-Team)_ — blockiert: apply
- Die Entra-App-Registrierung und ihr Client Secret. Ein Verzeichnisobjekt, keine Azure-Ressource - das Identity-Team legt sie an; das Secret kommt in den Key-Vault-Platzhalter "entra-client-secret". [Sandbox, eine Wegwerf-Umgebung] _(gebraucht von: Identity-Team)_ — blockiert: apply

## Anhang: alle Entscheidungen

| Schlüssel | Wert | Quelle |
|---|---|---|
| `deployment.non_production_savings` | enabled | erzwungen |
| `deployment.naming_convention` | default | Regel |
| `deployment.deploy_mechanism` | local | eure Antwort |
| `deployment.outage_impact` | tolerable | eure Antwort |
| `deployment.data_loss_tolerance` | one_week | eure Antwort |
| `deployment.data_access_pattern` | active | eure Antwort |
| `deployment.backup_isolation` | operational | eure Antwort |
| `deployment.data_residency` | data_zone | eure Antwort |
| `deployment.module_source` | authored | eure Antwort |
| `deployment.naming_source` | provider | eure Antwort |
| `deployment.landing_zone` | standalone | Regel |
| `deployment.network_exposure` | public | eure Antwort |
| `deployment.local_auth` | disabled | Regel |
| `deployment.mandates` | [] | eure Antwort |
| `deployment.key_protection` | software | Regel |
| `deployment.key_management` | platform_managed | Regel |
| `deployment.network_ownership` | none | erzwungen |
| `deployment.private_dns_ownership` | deployment | erzwungen |
| `deployment.observability_ownership` | create | erzwungen |
| `deployment.diagnostics_destination` | log-analytics-workspace | erzwungen |
| `deployment.log_retention_days` | 30 | eure Antwort |
| `deployment.daily_quota_gb` | -1 | Regel |
| `app-service.hosting.os_type` | Linux | Regel |
| `app-service.hosting.sku` | B1 | erzwungen |
| `app-service.hosting.zone_redundant` | false | abgeleitet aus eurer Antwort |
| `app-service.hosting.instance_count` | 1 | abgeleitet aus eurer Antwort |
| `app-service.networking.public_network_access` | enabled | eure Abweichung |
| `app-service.networking.vnet_integration` | false | erzwungen |
| `app-service.identity.managed_identity` | system_assigned | Regel |
| `app-service.security.https_only` | true | Regel |
| `app-service.security.min_tls_version` | 1.2 | Regel |
| `app-service.security.ftps_state` | Disabled | Regel |
| `app-service.security.basic_auth_enabled` | false | übernommen |
| `app-service.runtime.runtime_stack` | container | eure Beschreibung |
| `app-service.runtime.always_on` | true | Regel |
| `app-service.runtime.health_check_path` |  | Regel |
| `app-service.runtime.http2_enabled` | true | Regel |
| `app-service.observability.diagnostic_workspace` | {"sandbox": "log-analytics-workspace"} | übernommen |
| `app-service.observability.diagnostic_categories` | ["AppServiceHTTPLogs", "AppServiceAppLogs", "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs"] | Regel |
| `app-service.observability.metrics_enabled` | true | Regel |
| `foundry.account.kind` | AIServices | Regel |
| `foundry.account.sku_name` | S0 | Regel |
| `foundry.account.project_management` | true | Regel |
| `foundry.account.projects` | ["chat"] | eure Beschreibung |
| `foundry.models.deployment_sku` | DataZoneStandard | abgeleitet aus eurer Antwort |
| `foundry.models.deployment_capacity` | 10 | Regel |
| `foundry.models.version_upgrade_option` | OnceCurrentVersionExpired | Regel |
| `foundry.models.content_filter` | Microsoft.DefaultV2 | Regel |
| `foundry.networking.public_network_access` | enabled | eure Abweichung |
| `foundry.networking.restrict_outbound` | true | Regel |
| `foundry.identity.managed_identity` | system_assigned | Regel |
| `foundry.identity.role_assignments` | {"sandbox": [{"principal": "app-service", "role": "Cognitive Services OpenAI User"}, {"principal": "search-service", "role": "Cognitive Services OpenAI User"}]} | erzwungen |
| `foundry.security.local_authentication_disabled` | true | übernommen |
| `foundry.security.key_management` | platform_managed | übernommen |
| `foundry.observability.diagnostic_workspace` | {"sandbox": "log-analytics-workspace"} | übernommen |
| `foundry.observability.diagnostic_categories` | ["Audit", "RequestResponse", "AzureOpenAIRequestUsage"] | Regel |
| `foundry.observability.metrics_enabled` | true | Regel |
| `search-service.service.sku` | basic | erzwungen |
| `search-service.service.replica_count` | 1 | abgeleitet aus eurer Antwort |
| `search-service.service.partition_count` | 1 | Regel |
| `search-service.service.semantic_ranker` | free | Regel |
| `search-service.networking.public_network_access` | enabled | eure Abweichung |
| `search-service.networking.network_rule_bypass` | None | Regel |
| `search-service.identity.managed_identity` | system_assigned | Regel |
| `search-service.identity.role_assignments` | {"sandbox": [{"principal": "app-service", "role": "Search Index Data Reader"}]} | erzwungen |
| `search-service.security.local_authentication_disabled` | true | übernommen |
| `search-service.security.key_management` | platform_managed | übernommen |
| `search-service.observability.diagnostic_workspace` | {"sandbox": "log-analytics-workspace"} | übernommen |
| `search-service.observability.diagnostic_categories` | ["OperationLogs"] | Regel |
| `search-service.observability.metrics_enabled` | true | Regel |
| `storage-account.networking.public_network_access` | enabled | eure Abweichung |
| `storage-account.networking.private_endpoint_subresources` | ["blob"] | Regel |
| `storage-account.networking.allow_azure_services_bypass` | true | Regel |
| `storage-account.identity.managed_identity` | system_assigned | Regel |
| `storage-account.identity.role_assignments` | {"sandbox": [{"principal": "app-service", "role": "Storage Blob Data Contributor"}, {"principal": "search-service", "role": "Storage Blob Data Reader"}]} | erzwungen |
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
| `storage-account.observability.diagnostic_workspace` | {"sandbox": "log-analytics-workspace"} | übernommen |
| `storage-account.observability.diagnostic_categories` | ["audit"] | Regel |
| `storage-account.observability.metrics_enabled` | true | Regel |
| `key-vault.vault.sku` | standard | Regel |
| `key-vault.vault.purge_protection` | false | eure Abweichung |
| `key-vault.vault.soft_delete_retention_days` | 7 | eure Abweichung |
| `key-vault.vault.rbac_authorization` | true | übernommen |
| `key-vault.networking.public_network_access` | enabled | eure Abweichung |
| `key-vault.networking.network_acl_bypass` | None | Regel |
| `key-vault.identity.role_assignments` | {"sandbox": [{"principal": "app-service", "role": "Key Vault Secrets User"}]} | erzwungen |
| `key-vault.security.enabled_for_services` | [] | Regel |
| `key-vault.security.secret_placeholders` | ["entra-client-secret"] | eure Beschreibung |
| `key-vault.keys.key_management` | platform_managed | übernommen |
| `key-vault.observability.diagnostic_workspace` | {"sandbox": "log-analytics-workspace"} | übernommen |
| `key-vault.observability.diagnostic_categories` | ["AuditEvent", "AzurePolicyEvaluationDetails"] | Regel |
| `key-vault.observability.metrics_enabled` | true | Regel |
| `log-analytics-workspace.cost.retention_days` | 30 | übernommen |
| `log-analytics-workspace.cost.daily_quota_gb` | -1 | übernommen |
| `log-analytics-workspace.cost.sku` | PerGB2018 | Regel |
| `log-analytics-workspace.access.public_network_access` | enabled | Regel |
| `log-analytics-workspace.access.local_auth` | disabled | übernommen |
| `log-analytics-workspace.access.rbac_only_access` | true | Regel |
| `log-analytics-workspace.data_protection.immediate_purge_protection` | true | Regel |
| `log-analytics-workspace.data_protection.archive_to_storage` | false | Regel |
| `wiring.private_dns_zones` | [] | erzwungen |
| `wiring.access` | [{"from": "users", "to": "app-service", "label": "HTTPS 443"}, {"from": "app-service", "to": "external:entra-id", "label": "Anmeldung (Client Secret)"}, {"from": "app-service", "to": "foundry"}, {"from": "app-service", "to": "search-service", "label": "Suche"}, {"from": "app-service", "to": "storage-account"}, {"from": "search-service", "to": "storage-account", "label": "indexiert die Dokumente"}, {"from": "search-service", "to": "foundry", "label": "Embeddings"}, {"from": "app-service", "to": "key-vault", "label": "liest das Client Secret"}] | eure Beschreibung |
| `wiring.purposes` | {"app-service": "Chat-Anwendung (Docker-Container)", "foundry": "Chat- und Embedding-Modelle", "search-service": "Suchindex über die Dokumente (RAG)", "storage-account": "Persistente Daten der Chat-Anwendung", "key-vault": "Client Secret der Entra-App", "log-analytics-workspace": "Protokolle aller Ressourcen"} | eure Beschreibung |
| `wiring.optional` | [] | Regel |
