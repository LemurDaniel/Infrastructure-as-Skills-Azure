// Stage file: production
//
// Placeholder values (a capitalised word for open plus a hyphen and a name, or an id made only
// of zeros) stand in for answers the spec does not
// have yet (spec 'open:' entries and the parameterized context values). A placeholder never
// deploys: the pipeline refuses it. Replace each one, then the stage can be deployed.
//
//   location, workload, subscriptionId, resourceGroupName  parameterized in the spec, never asked
//   containerImage                                        open: resources.app-service.runtime.container_image
//   modelDeployments                                      open: resources.foundry.models.model_deployments
//   pluginSource                                          open: application.plugin_source
//   entraClientId, entraTenantId                          existing app registration, open: resources.app-service.identity.entra_sign_in

using './main.bicep'

// ---- context (parameterized) ----
param location = 'OPEN-location'
param workload = 'OPEN-workload'
param environment = 'production'
param subscriptionId = '00000000-0000-0000-0000-000000000000'
param resourceGroupName = 'OPEN-resource-group-name'

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
// Name and tag of the image, without the registry; not latest.
param containerImage = 'OPEN-container-image'
// Models of the Foundry account, e.g. { name: 'chat', model: { format: 'OpenAI', name: '<model>', version: '<version>' } }.
// Empty until the workload owner names them; no deployment is created from an empty list.
param modelDeployments = []
param pluginSource = 'OPEN-plugin-source'
// Client id of the existing Entra app registration and the tenant id (all-zero GUID until known).
param entraClientId = '00000000-0000-0000-0000-000000000000'
param entraTenantId = '00000000-0000-0000-0000-000000000000'
