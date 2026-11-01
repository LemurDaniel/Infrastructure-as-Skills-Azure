# Rendering blob containers as Terraform

Mapping from the question set to the containers. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

A container is a child of a storage account, and the AVM storage account module takes its
containers as an input. **There is no module call of its own:** the decisions below land in the
`containers` input of the account's call, rendered by [../storage-account/terraform.md](../storage-account/terraform.md).
Module: `Azure/avm-res-storage-storageaccount/azurerm` v0.10.0 (resolved 2026-10-25), pinned and
provider-constrained as there.

## With the AVM module

### Decision -> module input

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

```hcl
  # inside module "storage" - decision: blob-container.containers.*
  containers = {
    for c in var.container_names : c => {
      name          = c
      public_access = "None"
      immutable_storage_with_versioning = { enabled = false }
    }
  }
```

### Tests

The container is a child of the account module, so the assertion target is what the account
module exposes at plan time; the exact paths are read off a first `terraform test` on the
pinned version, and what the plan hides is marked `# not-testable:` with a reason, as for the
account's other children.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

In 5.x the resource takes `storage_account_id` and is managed through the Resource Manager API, so
a runner outside a closed account's network can still create the container; the objects *inside*
it are the data plane. Check this against the provider documentation of the pinned version
before relying on it: the 4.x resource keyed on `storage_account_name` used the data plane and
needed a network path and `storage_use_azuread` with shared keys off.
