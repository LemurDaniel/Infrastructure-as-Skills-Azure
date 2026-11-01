# Rendering Azure Managed Redis as Terraform

Mapping from the question set to the cluster and its database. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-cache-redisenterprise/azurerm` | **v0.2.0** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.2.0`.

**`azapi`-only**: it takes the resource group as `parent_id` (an id, not a name) and requires `azapi ~> 2.4`,
`modtm ~> 0.3`, `random ~> 3.5` and Terraform `~> 1.9` - **no `azurerm`**, so a root that calls only this module
needs none, and may be on `azurerm` 5.x. The root's provider set is the union with the other modules in the
deployment. The module builds the cluster and its one database `default` with TLS, eviction and clustering, private
endpoints, Entra access-policy assignments and role assignments. It does **not** build the database's persistence
or its access-key switch, the diagnostic setting, or geo-replication.

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide inputs

| Input | Module input | Note |
|---|---|---|
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "redis" {
  source  = "Azure/avm-res-cache-redisenterprise/azurerm"
  version = "~> 0.2.0"

  name      = data.naming_name.redis.name
  location  = var.location
  parent_id = var.resource_group_id

  # decision: redis-cache.cache.sku_name
  sku_name = "Balanced_B1"
  # decision: redis-cache.cache.clustering_policy / eviction_policy / redis_modules
  clustering_policy = "EnterpriseCluster"
  eviction_policy   = "AllKeysLRU"
  redis_modules     = []

  # decision: redis-cache.resilience.high_availability
  high_availability = "Enabled"

  # decision: redis-cache.networking.public_network_access - a string
  public_network_access = "Disabled"
  private_endpoints = {
    redis = {
      name               = data.naming_name.redis_private_endpoint.name
      subnet_resource_id = var.private_endpoint_subnet_id
      subresource_name   = "redisEnterprise"
    }
  }
  # private_dns_records: policy - the platform policy writes the record
  private_endpoints_manage_dns_zone_group = false

  # decision: redis-cache.security.encrypted_connections_only
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  # decision: redis-cache.identity.data_access_assignments - the database's one access policy
  access_policy_assignments = {
    app = { object_id = var.app_identity_principal_id, access_policy_name = "default" }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.redis.resource_id }
output "hostname" { value = module.redis.hostname }
```

A cache that is not highly available sets `high_availability = "Disabled"`. A
customer-managed key adds `managed_identities` and `customer_managed_key_encryption`.

### Access keys, persistence and diagnostics

The module has no input for the database's access-key switch or its persistence, and builds no diagnostic
setting; the first two are one update of the database it created, the third a resource on its id:

```hcl
# decision: redis-cache.security.access_keys_authentication_disabled
# decision: redis-cache.data_protection.persistence - disabled: a cache is rebuilt from its source
resource "azapi_update_resource" "database" {
  type        = "Microsoft.Cache/redisEnterprise/databases@2025-07-01"
  resource_id = module.redis.database_id

  body = {
    properties = {
      accessKeysAuthentication = "Disabled"
      persistence              = { rdbEnabled = false, aofEnabled = false }
    }
  }
}

resource "azurerm_monitor_diagnostic_setting" "redis" {
  name                       = "diag-redis"
  target_resource_id         = module.redis.database_id
  log_analytics_workspace_id = var.diagnostic_workspace_id

  enabled_log {
    category = "ConnectionEvents"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
```

Persistence on is `{ rdbEnabled = true, rdbFrequency = "1h" }` (frequencies `1h`, `6h`, `12h`) or
`{ aofEnabled = true, aofFrequency = "1s" }`. The metrics of Azure Managed Redis are on the cluster as well as the
database; the category, and which of the two resources it belongs to, is checked with `az monitor
diagnostic-settings categories list --resource <id>` before a render. The update is applied after the module and
carries the module's api-version; both are re-read from the module source of the pinned version.

### Data access

With access keys off, a client signs in with a Microsoft Entra token; the object id in
`access_policy_assignments` is the identity that is allowed to. The client library must support Entra
authentication and refresh the token before it expires.

### Tests

With the providers mocked, asserts target what the plan shows of the module's resources: the SKU, the high
availability, the public access string, the TLS settings, the clustering and eviction policies, and the
update's body. The output paths are read off a first `terraform test` run on the pinned version, not recalled.
What the module builds in child resources - the private endpoint, the access-policy assignments - is marked
`# not-testable:` with a reason where the plan hides it.

## Authored rendering

The fallback - `implementation: authored`, or a repository that already renders the cache this way. Targets
`azurerm` **5.x**; check against `terraform providers schema -json`. `azurerm` has a resource for Azure Managed
Redis (`azurerm_managed_redis`) which carries what the AVM module does not.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

## Azure Cache for Redis (Basic, Standard, Premium)

Not covered by the question set, and on a retirement path (see [notes.md](notes.md)). A repository that already
renders it keeps the module `Azure/avm-res-cache-redis/azurerm` (**v0.4.0**, `azurerm ~> 4.0`), whose inputs
differ: `sku_name` (`Basic`/`Standard`/`Premium`) with `capacity`, `redis_configuration`
(persistence, `maxmemory_policy`, Entra authentication through `active_directory_authentication_enabled`),
`access_keys_authentication_enabled`, `zones`, `subnet_resource_id` for the injected Premium network, and
`cache_firewall_rules`. Its private-endpoint sub-resource is `redisCache`.
