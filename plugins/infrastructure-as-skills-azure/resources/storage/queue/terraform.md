# Rendering storage queues as Terraform

Mapping from the question set to the queues. General layout, variables and tagging are in
[../../../core/iac-rendering/references/terraform-idiom.md](../../../core/iac-rendering/references/terraform-idiom.md).

A queue is a child of a storage account, and the AVM storage account module takes its queues as
an input. **There is no module call of its own:** the decisions below land in the `queues` input
of the account's call, rendered by [../storage-account/terraform.md](../storage-account/terraform.md).
Module: `Azure/avm-res-storage-storageaccount/azurerm` v0.10.0 (resolved 2026-10-25), pinned and
provider-constrained as there.

## With the AVM module

### Decision -> module input

| Decision | Input | Note |
|---|---|---|
| `queue_names` | `queues = { <key> = { name } }` | The map key is arbitrary; the name is the decision |
| `metadata` | `queues.<k>.metadata` | A map of lowercase keys |
| `role_assignments` | `queues.<k>.role_assignments = { <k> = { role_definition_id_or_name, principal_id, principal_type } }` | Scoped to the queue |
| `needs_dead_letter_or_ordering` | - | Not a module input: `true` swaps this set for `service-bus` |

```hcl
  # inside module "storage" - decision: queue.queues.*
  queues = {
    for q in var.queue_names : q => {
      name = q
    }
  }
```

### Tests

The queue is a child of the account module; asserts target what the account module exposes at
plan time (read off a first `terraform test` on the pinned version), and what the plan hides is
marked `# not-testable:` with a reason, as for the account's other children.

## Authored rendering

The fallback. Targets `azurerm` **5.x**; check against `terraform providers schema -json`.

| Decision | Argument on `azurerm_storage_queue` |
|---|---|
| `queue_names` | `name`, `storage_account_id` |
| `metadata` | `metadata` |
| `role_assignments` | `azurerm_role_assignment` with `scope = azurerm_storage_queue.<k>.id` (the Resource Manager id in 5.x) |
