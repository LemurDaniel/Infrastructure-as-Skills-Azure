terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.0"
    }
    naming = {
      source  = "LemurDaniel/naming"
      version = "~> 1.0"
    }
  }

  # One state per stage, chosen at init by the backend key and never by a workspace:
  #   terraform init -backend-config="key=<workload>/<stage>.tfstate"
  # The state account's subscription, resource group, storage account and container are
  # the consuming repository's and arrive the same way (deploy.ps1 passes every value as
  # -backend-config), which is why the block is empty on purpose. A local run without a
  # state uses `terraform init -backend=false`.
  backend "azurerm" {}
}

provider "azurerm" {
  subscription_id = var.subscription_id

  # Shared keys are off on the storage account; the provider's own data-plane reads
  # (blob properties) authenticate with Entra ID instead of a key.
  storage_use_azuread = true

  features {
    log_analytics_workspace {
      # decision: log-analytics-workspace.data_protection.immediate_purge_protection -
      # false keeps Azure's 14-day soft delete on destroy, so a deleted workspace can
      # be recovered with its data.
      permanently_delete_on_destroy = false
    }
  }
}

# The convention is declared once, for the whole configuration. `naming` points at the
# repository's own copy, so a provider upgrade cannot change a name.
provider "naming" {
  convention = "default"
  naming     = "${path.module}/naming.yaml"
  # Read only by <UNIQUE_ID_4> - the key vault, search and AI account patterns. Those
  # names are global, so the seed carries the deployment scope, not just the workload.
  random_seed = "${var.subscription_id}/${var.resource_group_name}"

  parameters = {
    location    = var.location
    environment = var.environment
    name        = var.workload
  }
}
