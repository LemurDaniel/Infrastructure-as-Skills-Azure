# Rendering an Azure Bot as Bicep

Mapping from the question set to the bot. General layout, parameters and naming are in
[../../../core/iac-rendering/references/bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md).

```bash
bicep build --stdout modules/bot-service.bicep
```

## No AVM module - authored is the primary

| Module | Status | Resolved |
|---|---|---|
| `br/public:avm/res/bot-service/bot-service` | **Proposed** in the index, not published (no tags on MCR) | 2026-10-26 |

Per [avm.md](../../../core/iac-rendering/references/avm.md), a `Proposed` module renders authored
code and the spec records `implementation: authored`, `source: { forced_by: no AVM module
for Microsoft.BotService/botServices }`. Check the index before a render; when the module is
`Available`, this reference is rewritten against it.

### Decision -> ARM property

`Microsoft.BotService/botServices@2022-09-15` (the current stable version; check
`az provider show -n Microsoft.BotService` before a render), `kind: 'azurebot'`, `location: 'global'`.

What each decision renders to - the property and the literal of every answer - is in [render-map.yaml](render-map.yaml); the render digest prints it for a spec.

### Deployment-wide properties

| Input | Property | Note |
|---|---|---|
| `context.tags` | `tags` | |

### The template

```bicep
resource bot 'Microsoft.BotService/botServices@2022-09-15' = {
  name: botName
  location: 'global'
  tags: tags
  kind: 'azurebot'
  sku: { name: 'S1' } // decision: bot-service.bot.sku
  properties: {
    displayName: empty(displayName) ? botName : displayName // decision: bot-service.bot.display_name
    endpoint: messagingEndpoint // decision: bot-service.bot.messaging_endpoint
    // decision: bot-service.bot.app_identity_type, bot_identity
    msaAppType: 'UserAssignedMSI'
    msaAppId: botIdentityClientId
    msaAppMSIResourceId: botIdentityId
    msaAppTenantId: tenant().tenantId
    isStreamingSupported: false // decision: bot-service.bot.streaming_endpoint
    publicNetworkAccess: 'Disabled' // decision: bot-service.networking.public_network_access
    disableLocalAuth: true // decision: bot-service.security.local_authentication_disabled
    isCmekEnabled: false // decision: bot-service.security.key_management
  }
}

// decision: bot-service.bot.channels - one child per entry, the settings are content
resource botChannels 'Microsoft.BotService/botServices/channels@2022-09-15' = [for channel in channels: {
  parent: bot
  name: channel
  location: 'global'
  properties: {
    channelName: channel
  }
}]

// decision: bot-service.networking.private_endpoint_subnet, private_endpoint_subresources
resource botPrivateEndpoints 'Microsoft.Network/privateEndpoints@2024-05-01' = [for sub in privateEndpointSubresources: {
  name: 'pep-${botName}-${toLower(sub)}'
  location: location
  tags: tags
  properties: {
    subnet: { id: privateEndpointSubnetId }
    privateLinkServiceConnections: [
      {
        name: 'pep-${botName}-${toLower(sub)}'
        properties: {
          privateLinkServiceId: bot.id
          groupIds: [ sub ]
        }
      }
    ]
    // private_dns_records: policy - no privateDnsZoneGroup, the platform policy writes the record
  }
}]

resource botRoleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for ra in roleAssignments: {
  name: guid(bot.id, ra.principalId, ra.roleDefinitionId)
  scope: bot
  properties: {
    principalId: ra.principalId
    roleDefinitionId: ra.roleDefinitionId
    principalType: ra.?principalType
  }
}]

resource botDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag'
  scope: bot
  properties: {
    workspaceId: diagnosticWorkspaceId
    logs: [ { category: 'BotRequest', enabled: true } ] // decision: bot-service.observability.diagnostic_categories
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

output id string = bot.id
```

`location` on the private endpoints is the deployment's region (the endpoint is regional even
though the bot is global). The private endpoint names follow the naming convention in a real
render (`naming.md`), not the interpolation above. For `single_tenant` the properties are
`msaAppType: 'SingleTenant'`, `msaAppId: appRegistrationClientId`, `msaAppTenantId`, and no MSI
id. Role assignments take the role definition id here (no module resolves names), so the render
keeps the name-to-id table of the authored idiom.

### Tests

Authored resources compile to top-level resources, so every property above is observable in
`tests/*.armtest.yaml` ([bicep-idiom.md](../../../core/iac-rendering/references/bicep-idiom.md#tests))
on `resources.bot.properties.*`, `resources.bot.sku.name`, and the loops as `copy` expressions
matched on their text.
