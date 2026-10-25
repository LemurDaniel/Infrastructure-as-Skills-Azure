// Stage file: production
//
// Placeholder values (a capitalised word for open plus a hyphen and a name, or an id made only
// of zeros) stand in for answers the spec does not
// have yet (spec 'open:' entries and the parameterized context values). A placeholder never
// deploys: the pipeline refuses it. Replace each one, then the stage can be deployed.
//
//   location, workload, subscriptionId, resourceGroupName  parameterized in the spec, never asked
//   dashboardContainerImage, agentContainerImage          open: resources.app-service__*.runtime.container_image
//   modelDeployments                                      open: resources.foundry.models.model_deployments
//   pluginSource                                          open: application.plugin_source
//   entraClientId, entraTenantId                          existing app registration, open: resources.app-service__dashboard.identity.entra_sign_in

using './main.bicep'

// ---- context (parameterized) ----
param location = 'westeurope'
param workload = 'evalagent'
param environment = 'production'
param subscriptionId = '6ad43a20-9532-41c0-ad61-885a26bef90f'
param resourceGroupName = 'rg-evalagent-prod-001'
// Instance number in the names (vnet-we-prod-evalagent-02).
param index = 2

// ---- per-stage decisions (known) ----
// deployment.address_space / resources.virtual-network.addressing.address_space
param addressSpace = '10.100.0.0/24'
// resources.virtual-network.addressing.subnets
param subnets = [
  { name: 'pe', prefix: '10.100.0.0/27' }
  { name: 'app-integration', prefix: '10.100.0.64/26' }
]
// deployment.private_endpoint_subnet_prefix
param privateEndpointSubnetPrefix = '10.100.0.0/27'
// resources.container-registry.registry.geo_replicas
param registryGeoReplicas = []
// resources.<resource>.identity.role_assignments - none on the resources themselves; the roles
// of the app identity are wiring.role_assignments and live in main.bicep.
param identityRoleAssignments = []
param registryRoleAssignments = []
param foundryRoleAssignments = []
param storageRoleAssignments = []
param vaultRoleAssignments = []

// ---- open points (placeholders) ----
// Bootstrap image (name:tag, without the registry; not latest), used only while the web app has
// no image. The separate image pipeline owns the image afterwards; the pipeline keeps what runs.
param dashboardContainerImage = 'eval-dashboard:0.0.1'
param agentContainerImage = 'eval-agent:0.0.1'
// Models of the Foundry account, e.g. { name: 'chat', model: { format: 'OpenAI', name: '<model>', version: '<version>' } }.
// Empty until the workload owner names them; no deployment is created from an empty list.
param modelDeployments = []
param pluginSource = 'https://github.com/LemurDaniel/Infrastructure-as-Skills-Azure'
// Client id of the existing Entra app registration and the tenant id (all-zero GUID until known).
param entraClientId = '2a1028db-7ae1-4eff-b842-3d639a9afcf1'
param entraTenantId = 'a910deee-8c06-4a0a-a458-8b347c88c614'
