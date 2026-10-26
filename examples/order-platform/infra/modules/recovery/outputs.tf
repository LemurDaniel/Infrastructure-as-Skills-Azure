output "backup_vault_id" {
  description = "Resource id of the Backup vault."
  value       = module.backup_vault.resource_id
}

output "recovery_vault_id" {
  description = "Resource id of the Recovery Services vault."
  value       = module.recovery_vault.resource_id
}
