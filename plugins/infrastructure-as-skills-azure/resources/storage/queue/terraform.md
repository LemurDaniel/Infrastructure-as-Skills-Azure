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

What each decision renders to - the input and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

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

What each decision renders to - the argument and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.
