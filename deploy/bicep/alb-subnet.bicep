@description('The node resource group name from AKS cluster output')
param nodeResourceGroup string

@description('ALB subnet address prefix')
param albSubnetAddressPrefix string = '10.225.0.0/24'

@description('The ALB managed identity principal ID')
param albIdentityPrincipalId string

@description('The ALB managed identity resource ID')
param albIdentityResourceId string

@description('The AKS-managed VNet name')
param aksVnetName string

// Deploy ALB subnet using module in node resource group scope
module albSubnetModule 'modules/alb-subnet-creation.bicep' = {
  scope: resourceGroup(subscription().subscriptionId, nodeResourceGroup)
  name: 'albSubnetDeployment'
  params: {
    vnetName: aksVnetName
    albSubnetAddressPrefix: albSubnetAddressPrefix
  }
}

// ALB Identity role assignments

// 1. AppGw for Containers Configuration Manager role assignment for ALB identity (in current resource group)
resource albIdentityAppGwConfigManagerRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, albIdentityResourceId, 'fbc52c3f-28ad-4303-a892-8a056630b8f1')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'fbc52c3f-28ad-4303-a892-8a056630b8f1') // AppGw for Containers Configuration Manager
    principalId: albIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// 2. Reader role assignment for ALB identity (in current resource group)
resource albIdentityReaderRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, albIdentityResourceId, 'acdd72a7-3385-48ef-bd42-f606fba81ae7')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'acdd72a7-3385-48ef-bd42-f606fba81ae7') // Reader
    principalId: albIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// 2. Deploy role assignments using module in node resource group scope
module albRoleAssignmentsModule 'modules/alb-role-assignments.bicep' = {
  scope: resourceGroup(subscription().subscriptionId, nodeResourceGroup)
  name: 'albRoleAssignmentsDeployment'
  params: {
    albIdentityPrincipalId: albIdentityPrincipalId
    albIdentityResourceId: albIdentityResourceId
  }
}

// AKS Contributor role assignment for Kaito provisioner identity (if provided)
@description('The Kaito provisioner managed identity principal ID (optional)')
param kaitoProvisionerIdentityPrincipalId string = ''

@description('The Kaito provisioner managed identity resource ID (optional)')
param kaitoProvisionerIdentityResourceId string = ''

@description('The AKS cluster resource ID')
param clusterResourceId string

resource kaitoProvisionerRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (kaitoProvisionerIdentityPrincipalId != '') {
  scope: resourceGroup()
  name: guid(clusterResourceId, kaitoProvisionerIdentityResourceId, 'b24988ac-6180-42a0-ab88-20f7382dd24c')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c') // AKS Contributor
    principalId: kaitoProvisionerIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

@description('ALB subnet resource information')
output albSubnetId string = albSubnetModule.outputs.albSubnetId
output albSubnetName string = albSubnetModule.outputs.albSubnetName
output albSubnetAddressPrefix string = albSubnetModule.outputs.albSubnetAddressPrefix

@description('Role assignment IDs')
output albIdentityAppGwConfigManagerRoleAssignmentId string = albIdentityAppGwConfigManagerRoleAssignment.id
output albIdentityReaderRoleAssignmentId string = albIdentityReaderRoleAssignment.id
output albNetworkContributorRoleAssignmentId string = albRoleAssignmentsModule.outputs.albNetworkContributorRoleAssignmentId

@description('The Kaito provisioner role assignment ID (if created)')
output kaitoProvisionerRoleAssignmentId string = kaitoProvisionerIdentityPrincipalId != '' ? kaitoProvisionerRoleAssignment.id : ''

@description('Node resource group')
output nodeResourceGroup string = nodeResourceGroup