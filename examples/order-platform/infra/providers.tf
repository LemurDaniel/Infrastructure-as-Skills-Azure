terraform {
  required_version = ">= 1.12"

  # One state per stage, chosen at init by the backend key, never by a workspace:
  #   terraform init -backend-config="key=orders/<stage>.tfstate" ...
  # The backend values (storage account, container) belong to the pipeline; this block stays empty.
  # A local run without state: terraform init -backend=false
  backend "azurerm" {}

  # The union of the requirements of all AVM modules in modules/*/versions.tf.
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.60"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.12"
    }
    modtm = {
      source  = "Azure/modtm"
      version = "~> 0.3"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.13"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}

  subscription_id     = var.subscription_id
  storage_use_azuread = true
}

provider "azapi" {
  subscription_id = var.subscription_id
}

provider "modtm" {}
