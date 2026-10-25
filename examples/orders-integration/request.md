# The request

Written for this example to play through the edge and messaging sets together with the two
vaults; nothing here has been applied. The request is the user's words verbatim.

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
> Querschnitt:
> - Diagnostics aller Ressourcen in einen zentralen Log Analytics Workspace
>   (90 Tage prod, 30 sonst), Secrets in Key Vault.

What the spec records beyond the words, where the request contradicts itself or the sets:

- **Service Bus Standard in development and test has no private endpoint.** The request asks for
  Standard there and for no public access with a private endpoint. Decided with the owner:
  Standard stays, those two stages keep a firewalled endpoint (`public_network_access`,
  `source: overridden`), allowed addresses open. Production is Premium and closed.
- **Front Door cannot reach a gateway over Private Link.** `origin_connection: public`, the
  gateway's frontend public, both `overridden`; the gateway's network security group admits only
  `AzureFrontDoor.Backend`, and the render checks `X-Azure-FDID`. `network_exposure` is
  `private_with_exceptions` for that reason.
- **Rate limiting per subscription needs the subscription key.** `caller_authentication:
  entra_id_and_key`, `overridden`; `local_auth: disabled` is about Azure resources, not API
  Management subscriptions.
- **Blob events come from a system topic**, which has no question set. The custom topic is
  rendered as asked, the path from the account to it is an `open:` entry.
- **Three storage accounts**: the backed-up orders account, the data lake the capture writes to
  (blob backup does not take a hierarchical namespace) and the function app's host storage.
- **The function app admits the `AzureEventGrid` service tag** (`overridden`): Event Grid does not
  deliver to a private endpoint.
- **No machines**: the recovery services vault protects nothing until the VMs are named.
