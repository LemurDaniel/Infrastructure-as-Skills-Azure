# Stage: sandbox - the only stage of chat-sandbox (infra-spec.yaml).
#
# Placeholders: this file cannot deploy while it holds the all-zero GUID or an OPEN-
# value (deploy.ps1 refuses it before init). The spec's open: entries for this stage,
# and who answers them:
#   - context.location, context.subscription_id, context.resource_group_name (Workload-Team):
#     location, subscription_id and resource_group_name below - never asked, nobody named them
#   - resources.app-service.runtime.container_image  (Workload-Team): container_image and
#     container_registry_url below
#   - resources.foundry.models.model_deployments       (Workload-Team): model_deployments
#     below - model and version looked up in the region's catalogue as DataZoneStandard
#   - wiring.entra_app_registration                    (Identity-Team): a directory object,
#     not a resource; its client secret is written into the vault's placeholder
#     entra-client-secret after deployment, by hand, never through this file

environment = "sandbox"
location    = "OPEN-location"
workload    = "chat"

subscription_id     = "00000000-0000-0000-0000-000000000000"
resource_group_name = "OPEN-resource-group"

tags = {}

# resources.app-service.runtime.container_image (open)
container_image        = "OPEN-container-image:OPEN-tag"
container_registry_url = "https://OPEN-container-registry"

# resources.foundry.models.model_deployments (open) - one entry per model the chat
# application calls; the key is the deployment name the application uses.
model_deployments = {
  chat = {
    model_format  = "OpenAI"
    model_name    = "OPEN-chat-model"
    model_version = "OPEN-model-version"
  }
  embedding = {
    model_format  = "OpenAI"
    model_name    = "OPEN-embedding-model"
    model_version = "OPEN-model-version"
  }
}

# resources.<resource>.identity.role_assignments, sandbox
role_assignments = {
  foundry = [
    { principal = "app-service", role = "Cognitive Services OpenAI User" },
    { principal = "search-service", role = "Cognitive Services OpenAI User" },
  ]
  search-service = [
    { principal = "app-service", role = "Search Index Data Reader" },
  ]
  storage-account = [
    { principal = "app-service", role = "Storage Blob Data Contributor" },
    { principal = "search-service", role = "Storage Blob Data Reader" },
  ]
  key-vault = [
    { principal = "app-service", role = "Key Vault Secrets User" },
  ]
}
