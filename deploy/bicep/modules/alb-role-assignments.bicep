@description('The ALB managed identity principal ID')
param albIdentityPrincipalId string

@description('The ALB managed identity resource ID')
param albIdentityResourceId string

// Network Contributor role assignment on node resource group (ALB subnet)
resource albNetworkContributorNodeRG 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, albIdentityResourceId, '4d97b98b-1d4f-4787-a291-c67834d212e7')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4d97b98b-1d4f-4787-a291-c67834d212e7') // Network Contributor
    principalId: albIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

@description('Role assignment IDs')
output albNetworkContributorRoleAssignmentId string = albNetworkContributorNodeRG.id