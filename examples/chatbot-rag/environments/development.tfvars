# Stage: development
#
# Placeholders stand in for values nobody has given (infra-spec.yaml, open:). A file holding
# 00000000-0000-0000-0000-000000000000 or OPEN-... never deploys: the pipeline refuses it and the
# spec's open: entries keep blocking apply. Fill the values in, structure stays.
#
# Open entries for this stage - owner in brackets:
#   context.location                                             [workload owner]
#   context.subscription_id                                      [workload owner]
#   context.resource_group_name                                  [workload owner]
#   context.tags                                                 [workload owner]
#   deployment.address_space                                     [network / IPAM owner]
#   deployment.private_endpoint_subnet_prefix                    [network / IPAM owner]
#   resources.virtual-network.addressing.subnets                 [network / IPAM owner]
#   resources.foundry.models.model_deployments (+ deployment_capacity quota) [workload owner]
#   resources.app-service.runtime.runtime_stack / runtime_version [workload owner]
#   resources.key-vault.identity.role_assignments                [workload owner] - none rendered
#   resources.storage-account.identity.role_assignments          [workload owner] - the uploader, none rendered
#   resources.application-insights.networking.private_link_scope [workload owner] - not rendered
#   wiring.search_shared_private_link                            [workload owner] - not rendered

# Context
subscription_id     = "00000000-0000-0000-0000-000000000000"
resource_group_name = "OPEN-resource-group"
location            = "OPEN-location"
workload            = "chatrag"
environment         = "development"
tags                = {} # OPEN: context.tags - the organisation's tag set

# Network
address_space = "OPEN-address-space"
subnets = {
  "snet-endpoints" = { prefix = "OPEN-snet-endpoints-prefix" }
  "snet-web"       = { prefix = "OPEN-snet-web-prefix" }
}
dns_servers            = []
subnets_expecting_nsg  = ["snet-endpoints", "snet-web"]
app_integration_subnet = "snet-web"
private_endpoint_subnets = {
  key_vault       = "snet-endpoints"
  storage_account = "snet-endpoints"
  foundry         = "snet-endpoints"
  search_service  = "snet-endpoints"
  app_service     = "snet-endpoints"
}
endpoints_nsg_rules   = []
integration_nsg_rules = []

# Identity: the key vault readers and the document uploader are open and not listed.
role_assignments = [
  { resource = "application-insights", principal = "app-service", role = "Monitoring Metrics Publisher" }, # assumed in the spec
  { resource = "storage-account", principal = "search-service", role = "Storage Blob Data Reader" },
  { resource = "foundry", principal = "app-service", role = "Cognitive Services OpenAI User" },
  { resource = "foundry", principal = "search-service", role = "Cognitive Services OpenAI User" },
  { resource = "search-service", principal = "app-service", role = "Search Index Data Reader" },
]

# Per-stage cost knobs
search_sku      = "basic"
app_service_sku = "B1"

# Open: models (name and version are looked up against the region's catalogue) and runtime
model_deployments = {
  chat = {
    name    = "OPEN-chat-model"
    version = "OPEN-chat-model-version"
  }
  embedding = {
    name    = "OPEN-embedding-model"
    version = "OPEN-embedding-model-version"
  }
}
runtime_stack   = "OPEN-runtime-stack"
runtime_version = "OPEN-runtime-version"
