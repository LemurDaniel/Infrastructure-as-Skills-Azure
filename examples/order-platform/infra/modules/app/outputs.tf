output "apim_gateway_url" {
  description = "Gateway URL of API Management (internal, reachable inside the network)."
  value       = module.apim.apim_gateway_url
}

output "apim_id" {
  description = "Resource id of API Management."
  value       = module.apim.resource_id
}

output "function_app_id" {
  description = "Resource id of the function app."
  value       = module.function_app.resource_id
}

output "vm_ids" {
  description = "Resource ids of the virtual machines by instance number. Built from the subscription, the group name and the rendered name, so they are known at plan (the group's own id is not, on a first deployment): the Recovery Services vault module takes them as for_each input (through try()), which rejects a value that is only known after apply."
  value = {
    for k in local.vm_keys : k => "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${var.resource_groups["main"].name}/providers/Microsoft.Compute/virtualMachines/${module.naming_vm[k].linux_virtual_machine.name}"
  }
}

output "vm_ready_ids" {
  description = "Resource ids as returned by the created machines (known after apply); used only to order the backup protection behind the machines."
  value       = { for k, vm in module.virtual_machine : k => vm.resource_id }
}
