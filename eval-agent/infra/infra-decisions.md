# Entscheidungen für „claude-plugin-eval-agent“

Was gebaut wird, entschieden aus euren Antworten und den Regeln hinter den Vorgaben. Jede Zeile ist eine Entscheidung; der Schlüssel im Anhang ist, wo ein Engineer sie in der Spezifikation findet.

Stand 2026-10-24. Spezifikation: `infra-spec.yaml`.

## Das System

- Das System wird in diesen Stufen ausgerollt: Echtbetrieb.
- Jede Stufe liegt in einer eigenen Subscription; die Stufen können sich gegenseitig weder Ressourcen noch Budgets noch Berechtigungen anfassen.

## Was aus euren Antworten folgt

- **Das System wird durch GitHub Actions ausgerollt.** _(eure Antwort)_
- **Das Netz wird von diesem Ausrollen frei gewählt, ohne Verbindung zum Firmennetz und ohne VPN.** _(eure Antwort)_
- **Ein Tag Ausfall wäre verkraftbar.** _(eure Antwort)_
  - daher, Azure Container Registry: Die Registry übersteht nicht den Ausfall eines Rechenzentrums der Region.
  - daher, Azure Storage Account: Die Daten liegen dreifach in einem Rechenzentrum.
  - daher, Azure App Service (web app on an App Service plan) (dashboard): Die App übersteht nicht den Ausfall eines Rechenzentrums der Region.
  - daher, Azure App Service (web app on an App Service plan) (dashboard): Gleichzeitig laufende Kopien der App: 1.
- **Nach einem versehentlichen Löschen müsst ihr gar nicht, die Daten lassen sich neu erzeugen zurückkommen.** _(eure Antwort)_
  - daher, Azure Storage Account: Gelöschte Dateien sind 0 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account: Gelöschte Ordner sind 0 Tage wiederherstellbar (0: gar nicht).
  - daher, Azure Storage Account: Frühere Versionen überschriebener Dateien werden nicht aufgehoben.
- **Die Daten werden laufend genutzt.** _(eure Antwort)_
  - daher, Azure Storage Account: Gespeichert in der Klasse Standard: günstig beim Lesen, für Daten in Nutzung.
- **Gegen absichtliche Zerstörung sind die Daten nur innerhalb des Systems selbst geschützt; wer das System löschen kann, kann auch die Kopien löschen.** _(eure Antwort)_
- **Die Daten werden nur innerhalb des Wirtschaftsraums der Region, zum Beispiel der EU gespeichert und verarbeitet.** _(eure Antwort)_
  - daher, Azure AI Foundry (AI Services account with projects and model deployments): Anfragen an die Modelle werden überall innerhalb derselben Datenzone (zum Beispiel der EU) verarbeitet.
- **Der Code wird aus einzeln ausgeschriebenen Ressourcen gebaut.** _(eure Antwort)_
- **Der Zugang ist privat, mit benannten Ausnahmen hinter einer Firewall aus dem Internet erreichbar.** _(eure Antwort)_
- **Einzuhaltende Vorgaben: keine.** _(eure Antwort)_
- **Logs werden 30 Tage aufbewahrt.** _(eure Antwort)_

## Nach den Vorgaben gesetzt

Nichts davon wurde gefragt; jede Zeile folgt einer Regel oder einer der Antworten oben. Sagt Bescheid, wenn eine nicht passt.

### Für das ganze System

- Die Pipeline meldet sich mit einem kurzlebigen Token pro Lauf, ohne irgendwo gespeichertes Passwort bei Azure an.
- Eine Person gibt die Änderung frei, bevor sie ausgerollt wird: nur im Echtbetrieb.
- Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Logging selbst mit. — weil: Das Netz wird von diesem Ausrollen frei gewählt, ohne Verbindung zum Firmennetz und ohne VPN.
- Passwörter und Zugriffsschlüssel sind abgeschaltet; der Zugriff läuft über Firmenkonten, damit jede Aktion zuordenbar ist.
- Verschlüsselungsschlüssel sind in Software geschützt, der Standard, ausreichend ohne Vorgabe für Hardware.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Das Netz wird von diesem Ausrollen selbst gebaut. — weil: Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Logging selbst mit.
- Das neue Netz nutzt den Adressbereich 10.100.0.0/24.
- Private Anbindungen bekommen ein eigenes Subnetz, 10.100.0.0/27. — weil: Das Netz wird von diesem Ausrollen frei gewählt, ohne Verbindung zum Firmennetz und ohne VPN.
- Die Namensauflösung für private Anbindungen übernimmt dieses Ausrollen selbst. — weil: Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Logging selbst mit.
- Logs gehen in einen Arbeitsbereich, den dieses Ausrollen anlegt und bezahlt. — weil: Das System landet in einer eigenen Umgebung: es gibt keine gemeinsame Plattform, also bringt es Netz, Namensauflösung und Logging selbst mit.
- Logs werden in log-analytics-workspace gesammelt. — weil: Logs gehen in einen Arbeitsbereich, den dieses Ausrollen anlegt und bezahlt.
- Tägliche Obergrenze für Logs: -1 GB (-1: keine).

### Azure Virtual Network

- Das Netz nutzt den Adressbereich 10.100.0.0/24.
- Subnetze: pe (10.100.0.0/27), app-integration (10.100.0.64/26).
- Private Anbindungen bekommen das Subnetz 10.100.0.0/27.
- Eigene Namensserver: keine (keine: Azures eigene).
- Netzwerkregeln gelten für private Anbindungen in ihrem Subnetz.
- Abkürzungen zu Azure-Diensten aus den Subnetzen: keine.
- An einen Dienst übergebene Subnetze: app-integration (Microsoft.Web/serverFarms). — weil: `resources.app-service__dashboard.networking.vnet_integration`
- Ein kostenpflichtiger DDoS-Schutzplan wird nicht genutzt; Azures Basisschutz gilt ohnehin.
- Subnetze, die eine Sicherheitsgruppe bekommen: keine.
- Netzwerk-Logs gehen in log-analytics-workspace.
- Eine Aufzeichnung erlaubten und abgewiesenen Verkehrs wird nicht geführt.

### Azure Log Analytics Workspace

- Logs werden 30 Tage aufbewahrt.
- Tägliche Obergrenze für Logs: -1 GB (-1: keine).
- Abgerechnet pro Gigabyte, nach Verbrauch.
- Der Log-Arbeitsbereich ist aus dem Internet erreichbar, mit Firmenkonten und Verschlüsselung; einen privaten Zugang dafür gibt es nicht.
- Logs mit dem Arbeitsbereichs-Schlüssel zu senden ist nicht möglich, Agenten nutzen Firmenidentitäten.
- Wer Logs lesen darf, entscheiden die Berechtigungen des Arbeitsbereichs selbst.
- Ein gelöschter Arbeitsbereich kann 14 Tage lang wiederhergestellt werden.
- Langzeitarchivierung in günstigen Speicher ist ausgeschaltet.

### Azure user-assigned managed identity (dashboard)

- Diese Identität gibt es für app-runtime.
- Externe Systeme, die als diese Identität handeln dürfen: keine (leer: keine).
- Die Identität kann von Ressourcen in jeder Region aus genutzt werden.
- Rechte an der Identität selbst vergeben an: keine.

### Azure user-assigned managed identity (agent)

- Diese Identität gibt es für app-runtime.
- Externe Systeme, die als diese Identität handeln dürfen: keine (leer: keine).
- Die Identität kann von Ressourcen in jeder Region aus genutzt werden.
- Rechte an der Identität selbst vergeben an: keine.

### Azure Container Registry

- Die Registry hat die Stufe Premium, die als einzige per privater Anbindung abgeschottet und auf mehrere Regionen verteilt werden kann. — weil: Der Zugang ist privat, mit benannten Ausnahmen hinter einer Firewall aus dem Internet erreichbar.
- Die Images liegen zusätzlich in keine (leer: nur in der Hauptregion).
- Images ohne Tag werden nach 7 Tagen gelöscht.
- Die Registry ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz pe.
- Vertrauenswürdige Azure-Dienste dürfen nicht an der Firewall der Registry vorbei.
- Das Herauskopieren von Images aus der Registry ist gesperrt.
- Die Registry hat keine eigene Identität.
- Zugriffsrechte auf die Registry vergeben an: keine.
- Das gemeinsame Admin-Konto ist abgeschaltet; der Zugriff läuft über Firmenkonten.
- Das Herunterladen von Images ohne Anmeldung ist nicht erlaubt.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Seine Logs gehen in log-analytics-workspace.
- Geloggt wird: jedes Hochladen, Herunterladen und Löschen eines Images, jede Anmeldung an der Registry.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure AI Foundry (AI Services account with projects and model deployments)

- Das Konto ist eine AI-Foundry-Ressource, die auch Projekte, Agenten und die weiteren KI-Dienste bietet.
- Das Konto nutzt die Preisstufe S0, die bezahlte Standardstufe.
- Das Konto enthält Foundry-Projekte als Behälter für Zugriff, Daten und Kosten.
- Jedes Modell darf bis zu 10 Tausend Token pro Minute verarbeiten.
- Läuft die Modellversion aus, wechselt sie an diesem Tag auf die neue Standardversion.
- Anfragen und Antworten werden vom Inhaltsfilter Microsoft.DefaultV2 geprüft.
- Das Konto ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz pe.
- Das Konto darf nur Adressen aufrufen, die ausdrücklich erlaubt sind.
- Das Konto hat eine eigene Identität.
- Zugriffsrechte auf das Konto vergeben an: keine.
- Die Anmeldung mit Kontoschlüsseln ist abgeschaltet; der Zugriff läuft über Firmenkonten.
- Verschlüsselungsschlüssel sind von Azure verwaltet: verschlüsselt, rotiert, kein Aufwand bei euch.
- Seine Logs gehen in log-analytics-workspace.
- Geloggt wird: Änderungen am Konto und wer sie gemacht hat, jede Anfrage an die Modelle mit Aufrufer, Größe und Ergebnis (nicht der Text), die von jedem Aufruf verbrauchten Token.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Storage Account

- Der Speicher ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz pe.
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
- Ein Log jeder Änderung wird nicht geführt.
- Der ganze Speicher lässt sich 0 Tage zurückdrehen (0: gar nicht).
- Löschschutz per Gesetz oder Richtlinie: keiner.
- Seine Logs gehen in log-analytics-workspace.
- Geloggt wird: wer worauf zugegriffen hat.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure App Service (web app on an App Service plan) (dashboard)

- Die App läuft auf Linux.
- Der ausgehende Verkehr der App läuft durch das Firmennetz, so erreicht sie private Dienste.
- Ausgehender Verkehr verlässt das Netz über das Subnetz app-integration. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Sie nutzt die Identitäten user-assigned-identity__dashboard. — weil: `resources.app-service__dashboard.identity.managed_identity`
- `"existing_app_registration"`
- `"key_vault_reference"`
- Unverschlüsselte Verbindungen werden auf die verschlüsselte Adresse umgeleitet.
- Verbindungen müssen mindestens TLS 1.2-Verschlüsselung nutzen.
- Dateiupload per FTP ist abgeschaltet.
- Das Ausrollen mit Benutzername und Passwort ist nicht möglich; Rollouts laufen über Firmenkonten.
- Die App ist geschrieben für ein Container-Image, das seine Laufzeit selbst mitbringt.
- Die App bleibt geladen und antwortet sofort auf die erste Anfrage, wenn kein Verkehr anliegt.
- Die Plattform prüft die Gesundheit der App unter dem Pfad  (leer: keine Prüfung).
- HTTP/2 ist eingeschaltet.
- Seine Logs gehen in log-analytics-workspace.
- Geloggt wird: jede Web-Anfrage, die eigenen Log-Meldungen der App, wer sich zum Ausrollen oder Verwalten angemeldet hat, Änderungen an den Zugriffsbeschränkungen, die eigenen Meldungen der Plattform zur App.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure App Service (web app on an App Service plan) (agent)

- Die App läuft auf Linux. — weil: `resources.app-service__dashboard.hosting.os_type`
- Der Hosting-Plan hat die Größe B2, Basic, zwei Kerne. — weil: `resources.app-service__dashboard.hosting.sku`
- Die App übersteht nicht den Ausfall eines Rechenzentrums der Region. — weil: `resources.app-service__dashboard.hosting.zone_redundant`
- Gleichzeitig laufende Kopien der App: 1. — weil: `resources.app-service__dashboard.hosting.instance_count`
- Seine private Anbindung landet im Subnetz pe.
- Der ausgehende Verkehr der App läuft durch das Firmennetz, so erreicht sie private Dienste.
- Ausgehender Verkehr verlässt das Netz über das Subnetz app-integration. — weil: Das Netz wird von diesem Ausrollen selbst gebaut.
- Sie nutzt die Identitäten user-assigned-identity__agent. — weil: `resources.app-service__agent.identity.managed_identity`
- Unverschlüsselte Verbindungen werden auf die verschlüsselte Adresse umgeleitet.
- Verbindungen müssen mindestens TLS 1.2-Verschlüsselung nutzen.
- Dateiupload per FTP ist abgeschaltet.
- Das Ausrollen mit Benutzername und Passwort ist nicht möglich; Rollouts laufen über Firmenkonten.
- Die App ist geschrieben für ein Container-Image, das seine Laufzeit selbst mitbringt.
- Die App bleibt geladen und antwortet sofort auf die erste Anfrage, wenn kein Verkehr anliegt.
- Die Plattform prüft die Gesundheit der App unter dem Pfad  (leer: keine Prüfung).
- HTTP/2 ist eingeschaltet.
- Seine Logs gehen in log-analytics-workspace.
- Geloggt wird: jede Web-Anfrage, die eigenen Log-Meldungen der App, wer sich zum Ausrollen oder Verwalten angemeldet hat, Änderungen an den Zugriffsbeschränkungen, die eigenen Meldungen der Plattform zur App.
- Nutzungs- und Leistungswerte werden erfasst.

### Azure Key Vault

- Der Tresor ist die Stufe Standard, Schlüssel in Software geschützt.
- Ein gelöschter Tresor oder ein gelöschtes Geheimnis lässt sich nicht endgültig löschen, auch nicht von einem Administrator, bevor die Aufbewahrungszeit endet.
- Gelöschte Inhalte des Tresors lassen sich 90 Tage lang wiederherstellen.
- Der Zugriff auf den Inhalt des Tresors wird über Rollenzuweisungen, wie alles andere in Azure gesteuert.
- Der Tresor ist aus dem Internet überhaupt nicht erreichbar.
- Seine private Anbindung landet im Subnetz pe.
- Vertrauenswürdige Azure-Dienste dürfen nicht an der Firewall des Tresors vorbei.
- Zugriffsrechte auf den Tresor vergeben an: keine.
- Plattformdienste, die aus dem Tresor lesen dürfen: keine (leer: keine).
- Verschlüsselungsschlüssel sind von Azure verwaltet - der Tresor hält dafür keine.
- Seine Logs gehen in log-analytics-workspace.
- Geloggt wird: jeder Lese-, Schreib- und fehlgeschlagene Zugriff auf den Tresor, wie Richtlinien den Tresor bewertet haben.
- Nutzungs- und Leistungswerte werden erfasst.

## Von euch anders entschieden

- Azure AI Foundry (AI Services account with projects and model deployments): Das Konto enthält die Projekte eval. _(Grund: Departs from the default []: Foundry evaluations are scoped to a project.)_
- Azure App Service (web app on an App Service plan) (dashboard): Der Hosting-Plan hat die Größe B2, Basic, zwei Kerne. _(Grund: The subscription has no App Service quota in germanywestcentral (SubscriptionIsOverQuotaForSku for P1v3 and B1), so the stack runs in westeurope on B2. B2 is Basic: VNet integration, always on and the container run; no slots, no autoscale, no zone redundancy.)_
- Azure App Service (web app on an App Service plan) (dashboard): Die App ist aus dem Internet erreichbar. _(Grund: The dashboard is the one internet-facing part (customer: reachable from the internet, sign-in with company accounts). Departs from the private baseline, which would map to disabled.)_
- Azure App Service (web app on an App Service plan) (dashboard): Ausgehender Verkehr wird nur für private Adressen durch das Firmennetz geleitet geleitet. _(Grund: The agent needs the internet (plugin source, package installs). With all traffic routed into the VNet there is no outbound path without a NAT gateway; private endpoint addresses are RFC 1918 and still go through the VNet.)_
- Azure App Service (web app on an App Service plan) (dashboard): Die App hat eine gemeinsame, separat verwaltete Identität, um andere Dienste zu erreichen. _(Grund: Departs from system_assigned: AcrPull and the data roles must exist before the container first starts, which a system-assigned identity cannot have.)_
- Azure App Service (web app on an App Service plan) (dashboard): `"image_pipeline"` _(Grund: A separate pipeline builds, pushes and updates the image. This template sets the stage-file image only on the first deployment and keeps the running one afterwards.)_
- Azure App Service (web app on an App Service plan) (agent): Die App ist aus dem Internet überhaupt nicht erreichbar. _(Grund: Nothing outside the VNet calls the agent: the dashboard starts a run from inside the VNet, through the agent's private endpoint.)_
- Azure App Service (web app on an App Service plan) (agent): Ausgehender Verkehr wird nur für private Adressen durch das Firmennetz geleitet geleitet. _(Grund: The agent needs the internet (plugin source, package installs). With all traffic routed into the VNet there is no outbound path without a NAT gateway; private endpoint addresses are RFC 1918 and still go through the VNet.)_
- Azure App Service (web app on an App Service plan) (agent): Die App hat eine gemeinsame, separat verwaltete Identität, um andere Dienste zu erreichen. _(Grund: Departs from system_assigned: AcrPull and the data roles must exist before the container first starts, which a system-assigned identity cannot have.)_
- Azure App Service (web app on an App Service plan) (agent): `"image_pipeline"` _(Grund: A separate pipeline builds, pushes and updates the image. This template sets the stage-file image only on the first deployment and keeps the running one afterwards.)_
- Azure Key Vault: Für die Geheimnisse entra-client-secret, github-token werden leere Plätze angelegt; die Werte werden danach von Hand oder von der Anwendung eingetragen. _(Grund: Departs from the default []: the dashboard reads the sign-in's client secret and the GitHub token (issues:write on this repository only) through Key Vault references and needs both to exist before its first start. The agent reads neither.)_

## Noch offen

Solange diese Punkte offen sind, wird nichts ausgerollt.

- Welche Modelle werden gebraucht (Agent und Bewertung)? Claude-Modelle sind in Foundry womöglich nur weltweit verarbeitet verfügbar, das widerspräche 'nur EU'. [Echtbetrieb] _(gebraucht von: Workload-Owner)_ — blockiert: apply
- Woher holt der Agent das Claude-Plugin (Git-Repo, Speicher)? [Echtbetrieb] _(gebraucht von: Workload-Owner)_ — blockiert: apply
- Wann legt das Dashboard ein Ticket an: automatisch nach jedem Lauf mit fehlgeschlagenen Evals (vermutlich, noch nicht entschieden) oder erst auf Klick? Wer legt das GitHub-Token (issues:write, nur dieses Repo) im Tresor als 'github-token' ab? [Echtbetrieb] _(gebraucht von: Workload-Owner)_ — blockiert: apply
- Die Anmeldung nutzt eure bestehende App-Registrierung samt Client Secret. Wer erzeugt das Secret und trägt es im Tresor ein (der Tresor ist nur aus dem Netz erreichbar), und wer trägt nach dem ersten Ausrollen die Weiterleitungsadresse der App ein (https://<App-Adresse>/.auth/login/aad/callback)? _(gebraucht von: Identitäts-Team)_ — blockiert: apply
- Die Registry ist nur privat erreichbar. Wie kommt das Image hinein (Pipeline-Runner im Netz oder ein Build in der Registry)? _(gebraucht von: Workload-Owner)_ — blockiert: apply

## Anhang: alle Entscheidungen

| Schlüssel | Wert | Quelle |
|---|---|---|
| `deployment.deploy_mechanism` | github | eure Antwort |
| `deployment.pipeline_auth` | workload_identity | Regel |
| `deployment.pipeline_approvals` | production | Regel |
| `deployment.module_source` | authored | eure Antwort |
| `deployment.naming_convention` | default | Regel |
| `deployment.stage_isolation` | subscription | Regel |
| `deployment.non_production_savings` | enabled | Regel |
| `deployment.network_requirements` | free | eure Antwort |
| `deployment.outage_impact` | tolerable | eure Antwort |
| `deployment.data_loss_tolerance` | reproducible | eure Antwort |
| `deployment.data_access_pattern` | active | eure Antwort |
| `deployment.backup_isolation` | operational | eure Antwort |
| `deployment.data_residency` | data_zone | eure Antwort |
| `deployment.landing_zone` | standalone | erzwungen |
| `deployment.network_exposure` | private_with_exceptions | eure Antwort |
| `deployment.local_auth` | disabled | Regel |
| `deployment.mandates` | [] | eure Antwort |
| `deployment.key_protection` | software | Regel |
| `deployment.key_management` | platform_managed | Regel |
| `deployment.network_ownership` | create | erzwungen |
| `deployment.address_space` | {"production": "10.100.0.0/24"} | eure Antwort |
| `deployment.private_endpoint_subnet_prefix` | {"production": "10.100.0.0/27"} | erzwungen |
| `deployment.private_dns_ownership` | deployment | erzwungen |
| `deployment.observability_ownership` | create | erzwungen |
| `deployment.diagnostics_destination` | log-analytics-workspace | erzwungen |
| `deployment.log_retention_days` | 30 | eure Antwort |
| `deployment.daily_quota_gb` | -1 | Regel |
| `virtual-network.addressing.address_space` | {"production": "10.100.0.0/24"} | übernommen |
| `virtual-network.addressing.subnets` | {"production": [{"name": "pe", "prefix": "10.100.0.0/27"}, {"name": "app-integration", "prefix": "10.100.0.64/26"}]} | Regel |
| `virtual-network.addressing.private_endpoint_subnet_prefix` | {"production": "10.100.0.0/27"} | übernommen |
| `virtual-network.addressing.dns_servers` | [] | Regel |
| `virtual-network.subnet_policy.private_endpoint_network_policies` | Enabled | Regel |
| `virtual-network.subnet_policy.service_endpoints` | [] | Regel |
| `virtual-network.subnet_policy.subnet_delegations` | [{"subnet": "app-integration", "service": "Microsoft.Web/serverFarms"}] | erzwungen |
| `virtual-network.security.ddos_protection` | false | Regel |
| `virtual-network.security.subnets_expecting_nsg` | {"production": []} | Regel |
| `virtual-network.observability.diagnostic_workspace` | log-analytics-workspace | übernommen |
| `virtual-network.observability.flow_logs_enabled` | false | Regel |
| `log-analytics-workspace.cost.retention_days` | 30 | übernommen |
| `log-analytics-workspace.cost.daily_quota_gb` | -1 | übernommen |
| `log-analytics-workspace.cost.sku` | PerGB2018 | Regel |
| `log-analytics-workspace.access.public_network_access` | enabled | Regel |
| `log-analytics-workspace.access.local_auth` | false | übernommen |
| `log-analytics-workspace.access.rbac_only_access` | true | Regel |
| `log-analytics-workspace.data_protection.immediate_purge_protection` | true | Regel |
| `log-analytics-workspace.data_protection.archive_to_storage` | false | Regel |
| `user-assigned-identity__dashboard.identity.purpose` | app-runtime | Regel |
| `user-assigned-identity__dashboard.identity.federated_credentials` | [] | Regel |
| `user-assigned-identity__dashboard.identity.isolation_scope` | None | Regel |
| `user-assigned-identity__dashboard.identity.role_assignments` | {"production": []} | Regel |
| `user-assigned-identity__agent.identity.purpose` | app-runtime | Regel |
| `user-assigned-identity__agent.identity.federated_credentials` | [] | Regel |
| `user-assigned-identity__agent.identity.isolation_scope` | None | Regel |
| `user-assigned-identity__agent.identity.role_assignments` | {"production": []} | Regel |
| `container-registry.registry.sku` | Premium | erzwungen |
| `container-registry.registry.zone_redundant` | false | abgeleitet aus eurer Antwort |
| `container-registry.registry.geo_replicas` | {"production": []} | Regel |
| `container-registry.registry.retention_untagged_days` | 7 | Regel |
| `container-registry.networking.public_network_access` | disabled | übernommen |
| `container-registry.networking.private_endpoint_subnet` | pe | übernommen |
| `container-registry.networking.network_rule_bypass` | None | Regel |
| `container-registry.networking.export_policy_enabled` | false | Regel |
| `container-registry.identity.managed_identity` | none | Regel |
| `container-registry.identity.role_assignments` | {"production": []} | Regel |
| `container-registry.security.admin_enabled` | false | übernommen |
| `container-registry.security.anonymous_pull_enabled` | false | Regel |
| `container-registry.security.key_management` | platform_managed | übernommen |
| `container-registry.observability.diagnostic_workspace` | log-analytics-workspace | übernommen |
| `container-registry.observability.diagnostic_categories` | ["ContainerRegistryRepositoryEvents", "ContainerRegistryLoginEvents"] | Regel |
| `container-registry.observability.metrics_enabled` | true | Regel |
| `foundry.account.kind` | AIServices | Regel |
| `foundry.account.sku_name` | S0 | Regel |
| `foundry.account.project_management` | true | Regel |
| `foundry.account.projects` | ["eval"] | eure Abweichung |
| `foundry.models.deployment_sku` | DataZoneStandard | abgeleitet aus eurer Antwort |
| `foundry.models.deployment_capacity` | 10 | Regel |
| `foundry.models.version_upgrade_option` | OnceCurrentVersionExpired | Regel |
| `foundry.models.content_filter` | Microsoft.DefaultV2 | Regel |
| `foundry.networking.public_network_access` | disabled | übernommen |
| `foundry.networking.private_endpoint_subnet` | pe | übernommen |
| `foundry.networking.restrict_outbound` | true | Regel |
| `foundry.identity.managed_identity` | system_assigned | Regel |
| `foundry.identity.role_assignments` | {"production": []} | Regel |
| `foundry.security.local_authentication_disabled` | true | übernommen |
| `foundry.security.key_management` | platform_managed | übernommen |
| `foundry.observability.diagnostic_workspace` | log-analytics-workspace | übernommen |
| `foundry.observability.diagnostic_categories` | ["Audit", "RequestResponse", "AzureOpenAIRequestUsage"] | Regel |
| `foundry.observability.metrics_enabled` | true | Regel |
| `storage-account.networking.public_network_access` | disabled | übernommen |
| `storage-account.networking.private_endpoint_subnet` | pe | übernommen |
| `storage-account.networking.private_endpoint_subresources` | ["blob"] | Regel |
| `storage-account.networking.allow_azure_services_bypass` | true | Regel |
| `storage-account.identity.managed_identity` | system_assigned | Regel |
| `storage-account.identity.role_assignments` | {"production": []} | Regel |
| `storage-account.security.shared_access_key_enabled` | false | übernommen |
| `storage-account.security.min_tls_version` | TLS1_2 | Regel |
| `storage-account.security.https_traffic_only` | true | Regel |
| `storage-account.security.allow_blob_public_access` | false | Regel |
| `storage-account.security.infrastructure_encryption_enabled` | true | Regel |
| `storage-account.security.key_management` | platform_managed | übernommen |
| `storage-account.security.sftp_enabled` | false | Regel |
| `storage-account.data_protection.replication` | LRS | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.access_tier` | Hot | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.blob_soft_delete_days` | 0 | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.container_soft_delete_days` | 0 | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.versioning_enabled` | false | abgeleitet aus eurer Antwort |
| `storage-account.data_protection.change_feed_enabled` | false | Regel |
| `storage-account.data_protection.point_in_time_restore_days` | 0 | Regel |
| `storage-account.data_protection.immutability` | none | Regel |
| `storage-account.observability.diagnostic_workspace` | log-analytics-workspace | übernommen |
| `storage-account.observability.diagnostic_categories` | ["audit"] | Regel |
| `storage-account.observability.metrics_enabled` | true | Regel |
| `app-service__dashboard.hosting.os_type` | Linux | Regel |
| `app-service__dashboard.hosting.sku` | B2 | eure Abweichung |
| `app-service__dashboard.hosting.zone_redundant` | false | abgeleitet aus eurer Antwort |
| `app-service__dashboard.hosting.instance_count` | 1 | abgeleitet aus eurer Antwort |
| `app-service__dashboard.networking.public_network_access` | enabled | eure Abweichung |
| `app-service__dashboard.networking.vnet_integration` | true | Regel |
| `app-service__dashboard.networking.integration_subnet` | app-integration | erzwungen |
| `app-service__dashboard.networking.vnet_route_all` | false | eure Abweichung |
| `app-service__dashboard.identity.managed_identity` | user_assigned | eure Abweichung |
| `app-service__dashboard.identity.user_assigned_identity_ids` | {"production": ["user-assigned-identity__dashboard"]} | erzwungen |
| `app-service__dashboard.identity.entra_sign_in` | existing_app_registration | eure Beschreibung |
| `app-service__dashboard.identity.entra_client_secret` | key_vault_reference | eure Beschreibung |
| `app-service__dashboard.security.https_only` | true | Regel |
| `app-service__dashboard.security.min_tls_version` | 1.2 | Regel |
| `app-service__dashboard.security.ftps_state` | Disabled | Regel |
| `app-service__dashboard.security.basic_auth_enabled` | false | übernommen |
| `app-service__dashboard.runtime.runtime_stack` | container | eure Beschreibung |
| `app-service__dashboard.runtime.always_on` | true | Regel |
| `app-service__dashboard.runtime.health_check_path` |  | Regel |
| `app-service__dashboard.runtime.http2_enabled` | true | Regel |
| `app-service__dashboard.runtime.container_image_owner` | image_pipeline | eure Abweichung |
| `app-service__dashboard.observability.diagnostic_workspace` | log-analytics-workspace | übernommen |
| `app-service__dashboard.observability.diagnostic_categories` | ["AppServiceHTTPLogs", "AppServiceAppLogs", "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs"] | Regel |
| `app-service__dashboard.observability.metrics_enabled` | true | Regel |
| `app-service__agent.hosting.os_type` | Linux | erzwungen |
| `app-service__agent.hosting.sku` | B2 | erzwungen |
| `app-service__agent.hosting.zone_redundant` | false | erzwungen |
| `app-service__agent.hosting.instance_count` | 1 | erzwungen |
| `app-service__agent.networking.public_network_access` | disabled | eure Abweichung |
| `app-service__agent.networking.private_endpoint_subnet` | pe | übernommen |
| `app-service__agent.networking.vnet_integration` | true | Regel |
| `app-service__agent.networking.integration_subnet` | app-integration | erzwungen |
| `app-service__agent.networking.vnet_route_all` | false | eure Abweichung |
| `app-service__agent.identity.managed_identity` | user_assigned | eure Abweichung |
| `app-service__agent.identity.user_assigned_identity_ids` | {"production": ["user-assigned-identity__agent"]} | erzwungen |
| `app-service__agent.security.https_only` | true | Regel |
| `app-service__agent.security.min_tls_version` | 1.2 | Regel |
| `app-service__agent.security.ftps_state` | Disabled | Regel |
| `app-service__agent.security.basic_auth_enabled` | false | übernommen |
| `app-service__agent.runtime.runtime_stack` | container | eure Beschreibung |
| `app-service__agent.runtime.always_on` | true | Regel |
| `app-service__agent.runtime.health_check_path` |  | Regel |
| `app-service__agent.runtime.http2_enabled` | true | Regel |
| `app-service__agent.runtime.container_image_owner` | image_pipeline | eure Abweichung |
| `app-service__agent.observability.diagnostic_workspace` | log-analytics-workspace | übernommen |
| `app-service__agent.observability.diagnostic_categories` | ["AppServiceHTTPLogs", "AppServiceAppLogs", "AppServiceAuditLogs", "AppServiceIPSecAuditLogs", "AppServicePlatformLogs"] | Regel |
| `app-service__agent.observability.metrics_enabled` | true | Regel |
| `key-vault.vault.sku` | standard | Regel |
| `key-vault.vault.purge_protection` | true | Regel |
| `key-vault.vault.soft_delete_retention_days` | 90 | Regel |
| `key-vault.vault.rbac_authorization` | true | übernommen |
| `key-vault.networking.public_network_access` | disabled | übernommen |
| `key-vault.networking.private_endpoint_subnet` | pe | übernommen |
| `key-vault.networking.network_acl_bypass` | None | Regel |
| `key-vault.identity.role_assignments` | {"production": []} | Regel |
| `key-vault.security.enabled_for_services` | [] | Regel |
| `key-vault.security.secret_placeholders` | ["entra-client-secret", "github-token"] | eure Abweichung |
| `key-vault.keys.key_management` | platform_managed | übernommen |
| `key-vault.observability.diagnostic_workspace` | log-analytics-workspace | übernommen |
| `key-vault.observability.diagnostic_categories` | ["AuditEvent", "AzurePolicyEvaluationDetails"] | Regel |
| `key-vault.observability.metrics_enabled` | true | Regel |
| `wiring.private_dns_zones` | ["privatelink.vaultcore.azure.net", "privatelink.blob.core.windows.net", "privatelink.azurecr.io", "privatelink.cognitiveservices.azure.com", "privatelink.openai.azure.com", "privatelink.services.ai.azure.com", "privatelink.azurewebsites.net"] | erzwungen |
| `wiring.role_assignments` | [{"from": "user-assigned-identity__dashboard", "to": "container-registry", "role": "AcrPull"}, {"from": "user-assigned-identity__dashboard", "to": "storage-account", "role": "Storage Blob Data Reader"}, {"from": "user-assigned-identity__dashboard", "to": "key-vault", "role": "Key Vault Secrets User"}, {"from": "user-assigned-identity__agent", "to": "container-registry", "role": "AcrPull"}, {"from": "user-assigned-identity__agent", "to": "storage-account", "role": "Storage Blob Data Contributor"}, {"from": "user-assigned-identity__agent", "to": "foundry", "role": "Azure AI User"}] | Regel |
| `wiring.access` | [{"from": "users", "to": "app-service__dashboard", "label": "HTTPS 443, Anmeldung mit Firmenkonto"}, {"from": "app-service__dashboard", "to": "storage-account", "label": "Ergebnisse lesen"}, {"from": "app-service__dashboard", "to": "key-vault", "label": "Anmelde-Secret und GitHub-Token lesen"}, {"from": "app-service__dashboard", "to": "container-registry", "label": "Image laden"}, {"from": "app-service__dashboard", "to": "app-service__agent", "label": "Lauf starten"}, {"from": "app-service__agent", "to": "foundry", "label": "Modelle aufrufen"}, {"from": "app-service__agent", "to": "storage-account", "label": "Ergebnisse schreiben"}, {"from": "app-service__agent", "to": "container-registry", "label": "Image laden"}] | eure Beschreibung |
| `wiring.purposes` | {"app-service__dashboard": "Dashboard: zeigt Ergebnisse, legt Tickets an", "app-service__agent": "Agent: führt die Evals aus", "container-registry": "Images von Dashboard und Agent", "foundry": "Sprachmodelle für Agent und Bewertung", "storage-account": "Eval-Ergebnisse", "key-vault": "Anmelde-Secret und GitHub-Token des Dashboards", "virtual-network": "Privates Netz", "log-analytics-workspace": "Logs aller Teile", "user-assigned-identity__dashboard": "Zugriff des Dashboards ohne Schlüssel", "user-assigned-identity__agent": "Zugriff des Agents ohne Schlüssel"} | eure Beschreibung |
