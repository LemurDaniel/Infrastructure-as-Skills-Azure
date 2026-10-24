// Module "observability" (spec composition: observability) - the Log Analytics workspace that
// receives the diagnostics of every other resource.

@description('Finished workspace name, assembled in main.bicep.')
param name string

@description('Azure region.')
param location string

@description('Tags applied to the workspace.')
param tags object

resource workspace 'Microsoft.OperationalInsights/workspaces@2025-02-01' = {
  name: name
  location: location
  tags: tags

  properties: {
    // decision: log-analytics-workspace.cost.sku
    sku: { name: 'PerGB2018' }
    // decision: log-analytics-workspace.cost.retention_days
    retentionInDays: 30

    workspaceCapping: {
      // decision: log-analytics-workspace.cost.daily_quota_gb - -1 is no cap
      dailyQuotaGb: -1
    }

    // decision: log-analytics-workspace.access.public_network_access - ingestion and query
    // are separate switches; both are written.
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'

    features: {
      // decision: log-analytics-workspace.access.local_auth - the workspace key is a
      // non-expiring bearer credential.
      disableLocalAuth: true
      // decision: log-analytics-workspace.access.rbac_only_access - false selects workspace
      // permissions as the deciding ones (not those on the sending resources).
      enableLogAccessUsingOnlyResourcePermissions: false
    }
  }
}

// decision: log-analytics-workspace.data_protection.archive_to_storage - false: no data export
// rule is rendered (a Microsoft.OperationalInsights/workspaces/dataExports resource would be here).

output id string = workspace.id
output name string = workspace.name
