# identity.role_assignments of the resources: the principal is the system-assigned identity of
# app-service or search-service, the scope the resource that grants the role. Data-plane roles
# only; Contributor and Owner would grant no data access. The list is var.role_assignments, so a
# stage file adds the open ones (key vault readers, the document uploader) without a code change.
resource "azurerm_role_assignment" "this" {
  for_each = { for ra in var.role_assignments : "${ra.resource}/${ra.principal}/${ra.role}" => ra }

  scope                = local.role_scopes[each.value.resource]
  role_definition_name = each.value.role
  principal_id         = local.principal_ids[each.value.principal]
  principal_type       = "ServicePrincipal" # skips the Entra lookup that races a new identity
}
