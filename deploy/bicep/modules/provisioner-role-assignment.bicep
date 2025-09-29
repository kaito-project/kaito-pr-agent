// AKS Contributor role assignment for Kaito provisioner identity (if provided)
@description('The Kaito provisioner managed identity principal ID (optional)')
param kaitoProvisionerIdentityPrincipalId string = ''

@description('The Kaito provisioner managed identity resource ID (optional)')
param kaitoProvisionerIdentityResourceId string = ''

@description('The AKS cluster resource ID')
param clusterResourceId string

resource kaitoProvisionerRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (kaitoProvisionerIdentityPrincipalId != '') {
  name: guid(clusterResourceId, kaitoProvisionerIdentityResourceId, 'b24988ac-6180-42a0-ab88-20f7382dd24c')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c') // AKS Contributor
    principalId: kaitoProvisionerIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

@description('The Kaito provisioner role assignment ID')
output kaitoProvisionerRoleAssignmentId string = kaitoProvisionerIdentityPrincipalId != '' ? kaitoProvisionerRoleAssignment.id : ''