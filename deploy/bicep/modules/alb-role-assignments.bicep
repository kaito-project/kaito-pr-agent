@description('The ALB managed identity principal ID')
param albIdentityPrincipalId string

@description('The ALB managed identity resource ID')
param albIdentityResourceId string

// Reader role assignment on node resource group
resource albIdentityReaderRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, albIdentityResourceId, 'acdd72a7-3385-48ef-bd42-f606fba81ae7')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'acdd72a7-3385-48ef-bd42-f606fba81ae7') // Reader Role
    principalId: albIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// AppGw for Containers Configuration Manager role assignment on node resource group
resource albIdentityAppGwConfigManagerRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, albIdentityResourceId, 'fbc52c3f-28ad-4303-a892-8a056630b8f1')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'fbc52c3f-28ad-4303-a892-8a056630b8f1') // AppGw for Containers Configuration Manager role
    principalId: albIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

@description('Role assignment IDs')
output albIdentityReaderRoleAssignmentId string = albIdentityReaderRoleAssignment.id
output albIdentityAppGwConfigManagerRoleAssignmentId string = albIdentityAppGwConfigManagerRoleAssignment.id