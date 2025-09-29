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
    albIdentityPrincipalId: albIdentityPrincipalId
    albIdentityResourceId: albIdentityResourceId
  }
}

// Deploy role assignments using module in node resource group scope
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

// Deploy role assignments using module in cluster resource group scope
module provisionerRoleAssignment 'modules/provisioner-role-assignment.bicep' = {
  scope: resourceGroup(split(clusterResourceId, '/')[2], split(clusterResourceId, '/')[4]) // Extract subscription and RG from cluster resource ID
  name: 'provisionerRoleAssignmentDeployment'
  params: {
    kaitoProvisionerIdentityPrincipalId: kaitoProvisionerIdentityPrincipalId
    kaitoProvisionerIdentityResourceId: kaitoProvisionerIdentityResourceId
    clusterResourceId: clusterResourceId
  }
}

@description('ALB subnet resource information')
output albSubnetId string = albSubnetModule.outputs.albSubnetId
output albSubnetName string = albSubnetModule.outputs.albSubnetName
output albSubnetAddressPrefix string = albSubnetModule.outputs.albSubnetAddressPrefix

@description('Role assignment IDs')
output albIdentityAppGwConfigManagerRoleAssignmentId string = albRoleAssignmentsModule.outputs.albIdentityAppGwConfigManagerRoleAssignmentId
output albIdentityReaderRoleAssignmentId string = albRoleAssignmentsModule.outputs.albIdentityReaderRoleAssignmentId

@description('The Kaito provisioner role assignment ID (if created)')
output kaitoProvisionerRoleAssignmentId string = kaitoProvisionerIdentityPrincipalId != '' ? provisionerRoleAssignment.outputs.kaitoProvisionerRoleAssignmentId : ''

@description('Node resource group')
output nodeResourceGroup string = nodeResourceGroup