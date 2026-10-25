# Rendering a Managed Disk as Terraform

Mapping from the question set to the disk. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

## With the AVM module

| Module | Documented against | Resolved | Status |
|---|---|---|---|
| `Azure/avm-res-compute-disk/azurerm` | **v0.4.1** | 2026-10-25 | Available |

Resolve the current version and re-read the README inputs before rendering, as
[avm.md](../../../core/iac-rendering/references/avm.md) says. The pin is `~> 0.4.0`.

**AzAPI plus `azurerm`**: it takes `resource_group_name` and requires `azurerm ~> 4.0` -
**a root calling it cannot be on 5.x** - plus `azapi ~> 2.12`, `modtm ~> 0.3`, `random`, and
Terraform `>= 1.9`. The root's provider set is the union with the other modules. `zone` is a
**required** input and takes `null`.

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `create_option`, `source_resource_id` | `create_option`, `source_resource_id` | Required `create_option`; `"Empty"` / `"Copy"` |
| `sku` | `storage_account_type` | Required; written |
| `size_gb` | `disk_size_gb` | |
| `zone` | `zone` | Required, a string `"1"`; `null` for a ZRS type |
| `network_access` | `network_access_policy`, `public_network_access_enabled` | **Bool** for the second; `deny_all` is `"DenyAll"` + `false`; module defaults `"AllowPrivate"` + `false`; written |
| `disk_access_id` | `disk_access_id` | `allow_private` only |
| `private_endpoint_subnet` | `private_endpoints = { disks = { subnet_resource_id } }` | Sub-resource `disks`; needs `disk_access_id` |
| `deployment.private_dns_records` | `private_endpoints_manage_dns_zone_group` | `false` under `policy` |
| `key_management`, `disk_encryption_set_id` | `disk_encryption_set_id` | A set the module does not create. `customer_managed_key` is the module's own variant and is left unset |
| `role_assignments` | `role_assignments` | |
| `deployment.module_telemetry` | `enable_telemetry` | |
| `context.tags` | `tags = local.tags` | |

### The call

```hcl
module "disk" {
  source  = "Azure/avm-res-compute-disk/azurerm"
  version = "~> 0.4.0"

  name                = data.naming_name.disk.name # resource = "Azure::Microsoft.Compute/disks::data"
  location            = var.location
  resource_group_name = var.resource_group_name
  # decision: managed-disk.disk.zone - the machine's zone; null for a ZRS type
  zone = "1"

  create_option = "Empty"
  # decision: managed-disk.disk.sku
  storage_account_type = "Premium_LRS"
  disk_size_gb         = 128

  # decision: managed-disk.networking.network_access - the module's default is AllowPrivate; a bool, not the 5.x string
  network_access_policy         = "DenyAll"
  public_network_access_enabled = false

  # decision: managed-disk.security.key_management - customer_managed only
  disk_encryption_set_id = var.disk_encryption_set_id

  role_assignments = {
    for k, v in var.role_assignments : k => {
      role_definition_id_or_name = v.role
      principal_id               = v.principal_id
    }
  }

  enable_telemetry = true
  tags             = local.tags
}

output "id" { value = module.disk.resource_id }
```

For `allow_private` the call adds `network_access_policy = "AllowPrivate"`,
`disk_access_id = var.disk_access_id`, `private_endpoints = { disks = { name = ..., subnet_resource_id = var.private_endpoint_subnet_id } }`
and `private_endpoints_manage_dns_zone_group = false` under a platform that writes the DNS
record. The call and the private variant (a ZRS disk, `zone = null`) were validated with
`terraform validate` against v0.4.1 (azurerm 4.81, azapi 2.13); the attach to a machine is
the machine's `data_disk_existing_disks` or `data_disk_managed_disks`.

### Tests

With `azurerm` mocked, asserts target what the plan shows of the module's `azurerm_managed_disk`:
the SKU, the size, the zone, the network access policy and the public flag, the create option and
the encryption set. The output paths are read off a first `terraform test` run on the pinned
version. The private endpoint and the role assignments are marked `# not-testable:` with a reason
where the plan hides them.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Argument on `azurerm_managed_disk` |
|---|---|
| `create_option`, `source_resource_id` | `create_option`, `source_resource_id` |
| `sku`, `size_gb` | `storage_account_type`, `disk_size_gb` |
| `zone` | `zone` |
| `network_access` | `network_access_policy`, `public_network_access_enabled`, `disk_access_id` |
| `key_management` | `disk_encryption_set_id` |
| private endpoint | `azurerm_private_endpoint` with `subresource_names = ["disks"]` |
| `role_assignments` | `azurerm_role_assignment` |
