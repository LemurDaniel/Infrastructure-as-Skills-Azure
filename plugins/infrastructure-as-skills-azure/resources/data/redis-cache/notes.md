# Azure Managed Redis - what the question set cannot express

## Which Redis this is

Azure has two Redis services under `Microsoft.Cache`, and **Microsoft has announced the retirement of the older
one**:

| Service | Resource type | AVM Terraform | AVM Bicep | In this set |
|---|---|---|---|---|
| **Azure Managed Redis** | `Microsoft.Cache/redisEnterprise` | `Azure/avm-res-cache-redisenterprise/azurerm` **v0.2.0**, Available | `avm/res/cache/redis-enterprise` **0.5.1**, Available | **Yes** |
| Azure Cache for Redis (Basic, Standard, Premium) | `Microsoft.Cache/redis` | `Azure/avm-res-cache-redis/azurerm` **v0.4.0**, Available | `avm/res/cache/redis` **0.18.0**, Available | No - the rendering references list its module only |
| Azure Cache for Redis Enterprise (`Enterprise_*`, `EnterpriseFlash_*`) | `Microsoft.Cache/redisEnterprise` | the same module as Managed Redis | the same module | No - older SKUs of the same resource type |

New work targets Managed Redis; the question set is written for it. The retirement dates were not verified
against the announcement while this set was written, and are looked up before they are quoted to a customer. A
repository that already renders `Microsoft.Cache/redis` keeps its module, and the migration is a decision of its
own (the clients, the sizes and the network model all change), not a rendering detail.

## Fixed at creation

- **The clustering policy and the Redis modules.** A different one is a new cache and a data migration.
- **A customer-managed key.** Set at creation; losing the key makes the cache unreadable.
- **The name.** Global, part of the endpoint `<name>.<region>.redis.azure.net`.
- **One database.** A cluster has exactly one, named `default`.

## Ordering

The identity and its role on the Key Vault key (when `key_management: customer_managed`), then the cluster, then the
database, then the access-policy assignments, then the consumers. The workspace before the diagnostic setting,
which sits on the database.

## Pitfalls

**Two permission systems.** Azure RBAC governs the cluster; the database has its own access policy, one named
`default` with full access, assigned to Entra identities. With access keys off, nothing reads the cache until an
identity is assigned - an Azure `Owner` does not. Both modules render the assignments.

**The Terraform module has gaps the Bicep one does not.** It has no input for the access-key switch, for
persistence, for a diagnostic setting or for geo-replication; the render adds an `azapi_update_resource` on the
database and an `azurerm_monitor_diagnostic_setting` beside it. It also takes `NoEviction` where the API says
`NoCluster` for the non-clustered policy and lacks the LFU eviction values, so those cases need the authored form.
The Bicep module covers all of them through its `database` object.

**Persistence is not a backup.** It lives with the cache and cannot go to an earlier day. A cache is rebuilt from its
source; Redis used as a primary store needs its own export, which no template owns.

**Entra tokens expire.** A client with access keys off holds a token for about an hour and must refresh it; a client
library without that support is replaced, not accommodated.

**No IP firewall.** Public access is on or off. A request for "internet, but only from these addresses" is a private
endpoint or a gateway in front, and the question set records `enabled_with_firewall` as `enabled`, overridden.

**Zones are the service's.** For the Managed Redis SKUs the service spreads a highly available cluster across zones
where the region has them; the modules' `zones` input is documented for the Enterprise SKUs.

**Evictions are the signal.** A cache that is too small shows as evicted keys and a falling hit ratio, not as an error;
the metrics are collected for that.

**The diagnostic category was not checked live.** `ConnectionEvents` is checked against `az monitor
diagnostic-settings categories list --resource <database id>` before a render.

## Not covered here, and why

Azure Cache for Redis (all tiers), active geo-replication (recorded as an open entry for `critical`), clustering
tuning, the modules' own configuration, data import and export, and scheduled patching each carry decisions of
their own and have no question set; a request for one is said out loud, not improvised.
