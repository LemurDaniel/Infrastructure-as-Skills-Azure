terraform {
  required_version = ">= 1.9"

  # Empty on purpose: the pipeline passes the values as -backend-config. One state per stage,
  # chosen by the key, never by a workspace:
  #   terraform init -backend-config="key=chatrag/<stage>.tfstate" ...
  # A local run without a state: terraform init -backend=false
  backend "azurerm" {}

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
}

provider "azurerm" {
  features {
    log_analytics_workspace {
      # deployment: log_analytics_workspace.data_protection.immediate_purge_protection - keep Azure's
      # 14 days of soft delete instead of purging the workspace on destroy.
      permanently_delete_on_destroy = false
    }
  }

  subscription_id = var.subscription_id

  # The storage account has shared_access_key_enabled = false: the provider's own data-plane
  # reads (blob properties) must use Entra ID, or they fail with a 403 after a successful create.
  storage_use_azuread = true
}

# The convention is the repository's own copy (naming.yaml beside the spec), so a provider upgrade
# cannot rename a resource. The seed is read only by <UNIQUE_ID_n> (key vault, Foundry, search):
# those names are global, so the seed carries the deployment scope, not just the workload.
provider "naming" {
  convention  = "default"
  naming      = "${path.module}/naming.yaml"
  random_seed = "${var.subscription_id}/${var.resource_group_name}"

  parameters = {
    location    = var.location
    environment = var.environment
    name        = var.workload
  }
}
