@description('The VNet name where the ALB subnet should be created')
param vnetName string

@description('ALB subnet address prefix')
param albSubnetAddressPrefix string = '10.225.0.0/24'

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

@description('ALB subnet resource information')
output albSubnetId string = albSubnet.id
output albSubnetName string = albSubnet.name
output albSubnetAddressPrefix string = albSubnetAddressPrefix