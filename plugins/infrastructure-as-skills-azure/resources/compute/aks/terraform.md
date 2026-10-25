# Rendering AKS as Terraform

Mapping from the question set to the cluster and its two node pools. General layout, variables
and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-containerservice-managedcluster/azurerm` | **v0.8.5** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.8.0`.

**AzAPI only.** The module requires `azapi ~> 2.12`, `modtm ~> 0.3`, `random >= 3.5, < 4.0` and
Terraform `>= 1.11` - **no `azurerm`** - and takes the resource group as `parent_id` (its id).
Its inputs mirror the ARM properties in snake case (`api_server_access_profile.enable_private_cluster`
is `apiServerAccessProfile.enablePrivateCluster`), and the node pools are `default_agent_pool`
(the system pool; `mode` and `os_type` are set by the module) and `agent_pools` (a map, one entry
per user pool, in a submodule). A root calling it may stay on `azurerm 5.x`, which the other
modules in the deployment may not allow; the union of the requirements decides.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `sku_tier` | `sku = { name = "Base", tier }` | Bicep defaults `Standard`, Terraform unset (`Free`); written |
| `kubernetes_version` | `kubernetes_version` | A minor (`"1.33"`) takes the newest patch; looked up, never recalled |
| `upgrade_channel`, `node_os_upgrade_channel` | `auto_upgrade_profile = { upgrade_channel, node_os_upgrade_channel }` | Module defaults `"none"` (Bicep `stable`) and `"NodeImage"`; written |
| `zone_redundant` | `availability_zones = ["1", "2", "3"]` on both pools | Strings in Terraform, integers in Bicep. Set when a pool is created |
| `public_network_access` | `public_network_access` (`"Disabled"` / `"Enabled"`) and `api_server_access_profile.enable_private_cluster` | `disabled` is both; `enabled_with_firewall` is `Enabled` with `authorized_ip_ranges`; module default unset |
| `authorized_ip_ranges` | `api_server_access_profile.authorized_ip_ranges` | Never rendered empty |
| `private_dns_zone`, `private_dns_zone_id` | `api_server_access_profile.private_dns_zone` | `"system"`, or the zone's resource id; `"none"` is not offered |
| `node_subnet` | `vnet_subnet_id` on `default_agent_pool` and each `agent_pools` entry | |
| `network_plugin_mode` | `network_profile.network_plugin = "azure"`, `network_plugin_mode` | `"overlay"` or unset for `vnet` |
| `network_dataplane`, `network_policy` | `network_profile.network_dataplane`, `network_policy` | `"cilium"` / `"azure"`; policy `"cilium"`, `"calico"`, `"azure"` or unset for `none` |
| `pod_cidr`, `service_cidr`, `dns_service_ip` | `network_profile.pod_cidr`, `service_cidr`, `dns_service_ip` | `pod_cidr` only with overlay |
| `outbound_type` | `network_profile.outbound_type` | `"loadBalancer"`, `"managedNATGateway"`, `"userDefinedRouting"` |
| `system_pool_vm_size`, `_min_count`, `_max_count` | `default_agent_pool = { vm_size, enable_auto_scaling = true, count_of, min_count, max_count }` | `count_of` is written equal to `min_count`: it is the initial size |
| `system_pool_dedicated` | `default_agent_pool.node_taints = ["CriticalAddonsOnly=true:NoSchedule"]` | |
| `user_pool_*` | `agent_pools = { user = { name, mode = "User", vm_size, enable_auto_scaling, count_of, min_count, max_count } }` | |
| `os_sku`, `os_disk_type` | `os_sku`, `os_disk_type` on both pools | Release names (`AzureLinux3`, ...) from the README |
| `encryption_at_host` | `enable_encryption_at_host` on both pools | |
| `managed_identity`, `user_assigned_identity_ids` | `managed_identities = { system_assigned, user_assigned_resource_ids }` | One kind only |
| `entra_integration`, `azure_rbac_enabled`, `admin_group_object_ids` | `aad_profile = { managed, enable_azure_rbac, admin_group_object_ids }` | `enable_rbac = true` written beside it |
| `local_accounts_disabled` | `disable_local_accounts` | Inverse reading of `local_auth`; module default `false`; written |
| `oidc_issuer_enabled` | `oidc_issuer_profile = { enabled }` | Module default unset; written |
| `workload_identity_enabled` | `security_profile.workload_identity = { enabled }` | |
| `defender_enabled` | `security_profile.defender = { log_analytics_workspace_resource_id, security_monitoring = { enabled } }` | The workspace id is `diagnostic_workspace` |
| `image_cleaner_enabled` | `security_profile.image_cleaner = { enabled, interval_hours = 168 }` | |
| `azure_policy_enabled` | `addon_profile_azure_policy = { enabled }` | |
| `keyvault_secrets_provider_enabled` | `addon_profile_key_vault_secrets_provider = { enabled, config = { enable_secret_rotation = true } }` | |
| `key_management`, `disk_encryption_set_id` | `disk_encryption_set_id` | |
| `container_insights_enabled` | `addon_profile_oms_agent = { enabled, config = { log_analytics_workspace_resource_id, use_aad_auth = true } }` and `onboard_monitoring = true` | `onboard_monitoring` also creates the data collection rule; the validation needs the workspace id |
| `diagnostic_*`, `metrics_enabled` | `diagnostic_settings = { workspace = { workspace_resource_id, log_categories = [...], log_groups = [], metric_categories = ["AllMetrics"] } }` | `log_groups` defaults to `["allLogs"]`: set it empty when `log_categories` names the categories, or every log is collected beside them |
| `role_assignments` | `role_assignments` | `role_definition_id_or_name`, `principal_id` |
| `acr_pull_registry_ids` | *(root)* a role assignment per registry for `module.aks.kubelet_identity.objectId` | Not a module input; `AcrPull` on the registry |
| `deployment.resource_lock` | none | AKS is not in the locked set |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "aks" {
  source  = "Azure/avm-res-containerservice-managedcluster/azurerm"
  version = "~> 0.8.0"

  name      = data.naming_name.aks.name
  location  = var.location
  parent_id = var.resource_group_id

  # decision: aks.cluster.sku_tier - Bicep's default is Standard, Terraform's is Free
  sku = { name = "Base", tier = "Standard" }
  # decision: aks.cluster.kubernetes_version - a supported minor, looked up
  kubernetes_version = var.kubernetes_version
  # decision: aks.cluster.upgrade_channel - the modules disagree on the default
  auto_upgrade_profile = {
    upgrade_channel         = "patch"
    node_os_upgrade_channel = "NodeImage"
  }

  # decision: aks.networking.public_network_access - a private cluster
  public_network_access = "Disabled"
  api_server_access_profile = {
    enable_private_cluster = true
    private_dns_zone       = var.private_dns_zone_id # or "system"
  }
  network_profile = {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    network_dataplane   = "cilium"
    network_policy      = "cilium"
    pod_cidr            = "10.244.0.0/16"
    service_cidr        = var.service_cidr
    dns_service_ip      = var.dns_service_ip
    outbound_type       = "userDefinedRouting"
    load_balancer_sku   = "standard"
  }

  default_agent_pool = {
    name                      = data.naming_name.aks_system_pool.name
    vm_size                   = "Standard_D4ds_v5"
    enable_auto_scaling       = true
    count_of                  = 3
    min_count                 = 3
    max_count                 = 5
    # decision: aks.cluster.zone_redundant - fixed when the pool is created
    availability_zones        = ["1", "2", "3"]
    node_taints               = ["CriticalAddonsOnly=true:NoSchedule"]
    os_sku                    = "AzureLinux"
    os_disk_type              = "Ephemeral"
    enable_encryption_at_host = true
    vnet_subnet_id            = var.node_subnet_id
  }
  agent_pools = {
    user = {
      name                      = data.naming_name.aks_user_pool.name
      mode                      = "User"
      vm_size                   = "Standard_D4ds_v5"
      enable_auto_scaling       = true
      count_of                  = 3
      min_count                 = 3
      max_count                 = 10
      availability_zones        = ["1", "2", "3"]
      os_sku                    = "AzureLinux"
      os_disk_type              = "Ephemeral"
      enable_encryption_at_host = true
      vnet_subnet_id            = var.node_subnet_id
    }
  }

  # decision: aks.identity.managed_identity - roles on the subnet and the zone exist first
  managed_identities = { system_assigned = false, user_assigned_resource_ids = [var.user_assigned_identity_id] }
  aad_profile = {
    managed                = true
    enable_azure_rbac      = true
    admin_group_object_ids = var.admin_group_object_ids
  }
  enable_rbac = true
  # decision: aks.identity.local_accounts_disabled - inverse of local_auth; the module default is false
  disable_local_accounts = true
  oidc_issuer_profile    = { enabled = true }
  security_profile = {
    workload_identity = { enabled = true }
    image_cleaner     = { enabled = true, interval_hours = 168 }
    defender = {
      log_analytics_workspace_resource_id = var.diagnostic_workspace_id
      security_monitoring                 = { enabled = true }
    }
  }
  addon_profile_azure_policy = { enabled = true }
  addon_profile_key_vault_secrets_provider = {
    enabled = true
    config  = { enable_secret_rotation = true }
  }
  addon_profile_oms_agent = {
    enabled = true
    config = {
      log_analytics_workspace_resource_id = var.diagnostic_workspace_id
      use_aad_auth                        = true
    }
  }
  onboard_monitoring = true

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
    }
  }
  diagnostic_settings = {
    workspace = {
      workspace_resource_id = var.diagnostic_workspace_id
      log_categories        = ["kube-audit-admin", "guard", "cluster-autoscaler"]
      log_groups            = []
      metric_categories     = ["AllMetrics"]
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

# wiring in the root: the kubelet identity pulls from each registry
resource "azurerm_role_assignment" "acr_pull" {
  for_each = toset(var.acr_pull_registry_ids)

  scope                = each.value
  role_definition_name = "AcrPull"
  principal_id         = module.aks.kubelet_identity.objectId
  principal_type       = "ServicePrincipal"
}

output "id" { value = module.aks.resource_id }
output "oidc_issuer_url" { value = module.aks.oidc_issuer_profile_issuer_url }
```

Member names of the nested objects and the output names are read from the README of the pinned
version. The module's `kubelet_identity` output is the raw ARM object, so its members are
`clientId`, `objectId` and `resourceId`. Validated with `terraform validate` against v0.8.5.

### Tests

With `azapi` and `modtm` mocked, the module exposes **no `resource` output** - only `resource_id`,
`name`, `fqdn`, `oidc_issuer_profile_issuer_url`, `kubelet_identity` and a few more, all read from
the created resource - so a plan observes nothing of the request body. Every decision is marked
`# not-testable: <key> - set through the module's <input>; the module's own tests cover the
mapping`, and the call is the review; the handover says so
([avm.md](../../../core/iac-rendering/references/avm.md#tests-with-a-module-in-the-middle)). The
root can still assert what it computes itself: the zone list built from `zone_redundant`, the
pool names from the naming provider and the `AcrPull` assignments per registry.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Resource and argument |
|---|---|
| the cluster | `azurerm_kubernetes_cluster` (`public_network_access` is not an argument in 5.x: the private cluster is the control) with `sku_tier`, `kubernetes_version`, `automatic_upgrade_channel`, `node_os_upgrade_channel`, `private_cluster_enabled`, `private_dns_zone_id`, `api_server_access_profile { authorized_ip_ranges }`, `local_account_disabled`, `oidc_issuer_enabled`, `workload_identity_enabled`, `image_cleaner_enabled`, `azure_policy_enabled`, `disk_encryption_set_id` |
| the system pool | `default_node_pool { vm_size, min_count, max_count, auto_scaling_enabled, zones, vnet_subnet_id, only_critical_addons_enabled, os_sku, os_disk_type, host_encryption_enabled }` |
| the user pool | `azurerm_kubernetes_cluster_node_pool` with `mode = "User"` and the same arguments |
| `network_*`, CIDRs, outbound | `network_profile { network_plugin, network_plugin_mode, network_data_plane, network_policy, pod_cidr, service_cidr, dns_service_ip, outbound_type }` |
| Entra and Azure RBAC | `azure_active_directory_role_based_access_control { azure_rbac_enabled, admin_group_object_ids }` |
| identity | `identity { type, identity_ids }` |
| Defender, Container insights, secrets provider | `microsoft_defender { log_analytics_workspace_id }`, `oms_agent { log_analytics_workspace_id, msi_auth_for_monitoring_enabled }`, `key_vault_secrets_provider { secret_rotation_enabled }` |
| diagnostics | `azurerm_monitor_diagnostic_setting` with `enabled_log { category }` |
