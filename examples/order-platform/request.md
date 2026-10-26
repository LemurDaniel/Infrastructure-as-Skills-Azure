# The request

The order platform of the edge, messaging and recovery sets, rendered as a customer
repository. The request is the user's words verbatim; the interview's answers are in
`infra/infra-spec.yaml`.

> I need Terraform for an order processing platform in Azure (development, test, production), region Germany West Central.
>
> Ingress:
> Front Door with a WAF in front of an Application Gateway, which points internally to API Management. The API is backed by a Function App.
>
> Messaging:
> A Service Bus for orders (billing, shipping and audit consume them) and a queue for payments.
> An Event Hubs namespace for telemetry that is archived into a data lake storage account.
> An Event Grid topic that forwards the storage account's blob events to the Function App.
>
> Backup / Resilience:
> Backup for the storage account and for a few VMs.
