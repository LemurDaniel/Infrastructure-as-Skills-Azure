locals {
  # The set itself is the spec's context.tags (empty - nothing the customer named), merged
  # once and applied everywhere. The derived pair is what the stage file already states.
  derived_tags = {
    environment = var.environment
    workload    = var.workload
  }
  tags = merge(var.tags, local.derived_tags)
}
