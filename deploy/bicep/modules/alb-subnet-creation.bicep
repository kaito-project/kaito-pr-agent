@description('The VNet name where the ALB subnet should be created')
param vnetName string

@description('ALB subnet address prefix')
param albSubnetAddressPrefix string = '10.225.0.0/24'

@description('The ALB managed identity principal ID')
param albIdentityPrincipalId string

@description('The ALB managed identity resource ID')
param albIdentityResourceId string

// Reference to existing AKS VNet
resource aksVnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: vnetName
}

// Create ALB subnet in the AKS VNet
resource albSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: aksVnet
  name: 'alb-subnet'
  properties: {
    addressPrefix: albSubnetAddressPrefix
    delegations: [
      {
        name: 'Microsoft.ServiceNetworking.trafficControllers'
        properties: {
          serviceName: 'Microsoft.ServiceNetworking/trafficControllers'
        }
      }
    ]
  }
}

// Network Contributor role assignment on the ALB subnet itself
resource albNetworkContributorSubnetRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: albSubnet
  name: guid(albSubnet.id, albIdentityResourceId, '4d97b98b-1d4f-4787-a291-c67834d212e7')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4d97b98b-1d4f-4787-a291-c67834d212e7') // Network Contributor
    principalId: albIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

@description('ALB subnet resource information')
output albSubnetId string = albSubnet.id
output albSubnetName string = albSubnet.name
output albSubnetAddressPrefix string = albSubnetAddressPrefix

@description('Role assignment information')
output albNetworkContributorSubnetRoleAssignmentId string = albNetworkContributorSubnetRoleAssignment.id