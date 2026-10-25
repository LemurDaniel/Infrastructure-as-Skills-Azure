# The request

A multi-resource-group example: the order platform of the edge, messaging and recovery sets, split
over four resource groups (`resource_group_split`). Written for this example; nothing here has been
applied. The request is the user's words verbatim.

> Ich brauche Terraform für eine Bestellabwicklungs-Plattform in Azure
> (development, test, production), Region Germany West Central.
>
> Eingang:
> - Front Door (Premium) mit WAF-Policy vor einem Application Gateway (WAF_v2),
>   das intern auf API Management verweist. Front Door darf nur das Gateway
>   erreichen, das Gateway nur APIM.
> - API Management im internen VNet-Modus, SKU Premium in prod, Developer in dev/test,
>   mit System-assigned Identity. Policies: JWT-Validierung gegen Entra ID, Rate Limiting
>   pro Subscription, Backend-Routing auf eine Function App.
>
> Messaging:
> - Service Bus Namespace (Premium in prod, Standard sonst) ohne öffentlichen Zugriff,
>   Private Endpoint, nur Entra-ID-Auth (keine SAS-Keys).
>   Topic "orders" mit Subscriptions "billing", "shipping", "audit" (Filter auf Order-Typ),
>   Queue "payments" mit Dead-Lettering und Duplicate Detection.
> - Event Hubs Namespace für Telemetrie (4 Partitionen, 7 Tage Retention, Capture in ein
>   ADLS-Gen2-Storage), ebenfalls per Private Endpoint.
> - Event Grid Custom Topic, das Blob-Events des Storage Accounts an die Function App
>   zustellt, Auth über Managed Identity.
>
> Backup / Resilienz:
> - Backup Vault für Blob-Backups des Storage Accounts und Recovery Services Vault
>   für die VMs. In prod unveränderlich (Soft Delete, GRS, Cross-Region Restore),
>   in dev/test isoliert.
>
> Ressourcengruppen (mehrere, nicht alles in eine):
> - Das Netzwerk (Virtual Network, Front Door, Application Gateway) in eine eigene Gruppe,
>   die Daten (Storage, Backup Vault, Recovery Services Vault) in eine eigene und die
>   Überwachung (Log Analytics) in eine eigene. Alles andere in die Hauptgruppe.
>   Alle Gruppen legt ihr an.
>
> Querschnitt:
> - Diagnostics aller Ressourcen in einen zentralen Log Analytics Workspace
>   (90 Tage prod, 30 sonst), Secrets in Key Vault.

What the spec records beyond the words:

- **Resource groups:** `resource_group_split: [network, data, observability]`, the main group and
  the three others all `create`. Key Vault, API Management, Function App, Service Bus, Event Hubs
  and Event Grid stay in the main group.
- **Service Bus Standard in development and test has no private endpoint.** The request asks for
  Standard there and for no public access with a private endpoint. Standard stays, those two
  stages keep a firewalled endpoint (`public_network_access`, `source: overridden`); production is
  Premium and closed.
- **Front Door cannot reach a gateway over Private Link.** `origin_connection: public`, the
  gateway's frontend public, both `overridden`; the gateway admits only the `AzureFrontDoor.Backend`
  tag and the `X-Azure-FDID` header. `network_exposure` is `private_with_exceptions` for that reason.
- **Backup isolation is per stage:** `backup_isolation` is `immutable` in production and `isolated`
  in development and test (`overridden`, the request names the split); GRS and cross-region restore
  in production only.
- **One storage account** with hierarchical namespace holds the capture, the blob events and the
  backed-up blobs. Blob backup may not support a hierarchical namespace - not checked here, and a
  reason to split the account when it is rendered.
- **Outage impact `tolerable`**: no zone redundancy anywhere; the request names none.
- **Open:** who owns the private DNS zones (`deployment.private_dns_ownership`). Subnets,
  certificates, runtime, publisher data and the order types of the topic filters are not in the
  spec yet and are decided with the render.
