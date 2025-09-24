@description('The name of the resource group')
param resourceGroupName string

@description('The name of the AKS cluster')
param clusterName string

@description('The Azure region where the resources will be deployed')
param location string = resourceGroup().location

@description('The Kubernetes version for the cluster')
param kubernetesVersion string = '1.32.6'

@description('The DNS prefix for the cluster')
param dnsPrefix string = '${clusterName}-dns'

@description('Enable Azure RBAC for the cluster')
param enableRBAC bool = true

@description('The SKU tier for the cluster')
@allowed(['Free', 'Standard', 'Premium'])
param skuTier string = 'Standard'

@description('Enable workload identity')
param enableWorkloadIdentity bool = true

@description('Enable OIDC issuer')
param enableOIDCIssuer bool = true

@description('Enable Azure Policy add-on')
param enableAzurePolicy bool = true

@description('Enable OMS Agent (Azure Monitor)')
param enableOmsAgent bool = true

@description('Name for the Azure ALB managed identity')
param albIdentityName string = 'azure-alb-identity'

@description('Name for the Kaito provisioner managed identity')
param kaitoProvisionerIdentityName string = 'kaitoprovisioner'

@description('Kubernetes service account namespace for Kaito provisioner')
param kaitoServiceAccountNamespace string = 'gpu-provisioner'

@description('Kubernetes service account name for Kaito provisioner')
param kaitoServiceAccountName string = 'gpu-provisioner'

@description('System node pool configuration')
param systemNodePool object = {
  name: 'agentpool'
  count: 2
  minCount: 2
  maxCount: 5
  vmSize: 'Standard_D8ds_v5'
  osDiskSizeGB: 300
  osDiskType: 'Ephemeral'
  enableAutoScaling: true
  availabilityZones: ['1', '2', '3']
  nodeTaints: ['CriticalAddonsOnly=true:NoSchedule']
  maxPods: 110
}

@description('User node pool configuration')
param userNodePool object = {
  name: 'userpool'
  count: 2
  minCount: 2
  maxCount: 5
  vmSize: 'Standard_D8ds_v5'
  osDiskSizeGB: 300
  osDiskType: 'Ephemeral'
  enableAutoScaling: true
  availabilityZones: ['1', '2', '3']
  maxPods: 110
}

@description('ALB subnet address prefix')
param albSubnetAddressPrefix string = '10.245.0.0/24'

@description('Network configuration')
param networkProfile object = {
  networkPlugin: 'azure'
  networkPluginMode: 'overlay'
  networkPolicy: 'none'
  networkDataplane: 'azure'
  loadBalancerSku: 'Standard'
  podCidr: '10.244.0.0/16'
  serviceCidr: '10.0.0.0/16'
  dnsServiceIP: '10.0.0.10'
  outboundType: 'loadBalancer'
}

@description('Auto-scaler profile configuration')
param autoScalerProfile object = {
  'balance-similar-node-groups': 'false'
  expander: 'random'
  'max-empty-bulk-delete': '10'
  'max-graceful-termination-sec': '600'
  'max-node-provision-time': '15m'
  'max-total-unready-percentage': '45'
  'new-pod-scale-up-delay': '0s'
  'ok-total-unready-count': '3'
  'scale-down-delay-after-add': '10m'
  'scale-down-delay-after-delete': '10s'
  'scale-down-delay-after-failure': '3m'
  'scale-down-unneeded-time': '10m'
  'scale-down-unready-time': '20m'
  'scale-down-utilization-threshold': '0.5'
  'scan-interval': '10s'
  'skip-nodes-with-local-storage': 'false'
  'skip-nodes-with-system-pods': 'true'
}

// Azure ALB managed identity
resource albIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: albIdentityName
  location: location
}

// Kaito provisioner managed identity
resource kaitoProvisionerIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: kaitoProvisionerIdentityName
  location: location
}

resource aksCluster 'Microsoft.ContainerService/managedClusters@2025-02-01' = {
  name: clusterName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Base'
    tier: skuTier
  }
  properties: {
    kubernetesVersion: kubernetesVersion
    dnsPrefix: dnsPrefix
    enableRBAC: enableRBAC
    supportPlan: 'KubernetesOfficial'
    
    // System node pool (required)
    agentPoolProfiles: [
      {
        name: systemNodePool.name
        count: systemNodePool.count
        vmSize: systemNodePool.vmSize
        osDiskSizeGB: systemNodePool.osDiskSizeGB
        osDiskType: systemNodePool.osDiskType
        kubeletDiskType: 'OS'
        maxPods: systemNodePool.maxPods
        type: 'VirtualMachineScaleSets'
        availabilityZones: systemNodePool.availabilityZones
        maxCount: systemNodePool.maxCount
        minCount: systemNodePool.minCount
        enableAutoScaling: systemNodePool.enableAutoScaling
        scaleDownMode: 'Delete'
        enableNodePublicIP: false
        nodeTaints: systemNodePool.nodeTaints
        mode: 'System'
        osType: 'Linux'
        osSKU: 'Ubuntu'
        upgradeSettings: {
          maxSurge: '10%'
        }
        enableFIPS: false
      }
    ]

    // Network configuration
    networkProfile: {
      networkPlugin: networkProfile.networkPlugin
      networkPluginMode: networkProfile.networkPluginMode
      networkPolicy: networkProfile.networkPolicy
      networkDataplane: networkProfile.networkDataplane
      loadBalancerSku: networkProfile.loadBalancerSku
      loadBalancerProfile: {
        managedOutboundIPs: {
          count: 1
        }
        backendPoolType: 'nodeIPConfiguration'
      }
      podCidr: networkProfile.podCidr
      serviceCidr: networkProfile.serviceCidr
      dnsServiceIP: networkProfile.dnsServiceIP
      outboundType: networkProfile.outboundType
      podCidrs: [networkProfile.podCidr]
      serviceCidrs: [networkProfile.serviceCidr]
      ipFamilies: ['IPv4']
    }

    // Auto-scaler profile
    autoScalerProfile: autoScalerProfile

    // Auto-upgrade profile
    autoUpgradeProfile: {
      upgradeChannel: 'patch'
      nodeOSUpgradeChannel: 'NodeImage'
    }

    // Security profile
    securityProfile: {
      imageCleaner: {
        enabled: true
        intervalHours: 168
      }
      workloadIdentity: {
        enabled: enableWorkloadIdentity
      }
    }

    // Storage profile
    storageProfile: {
      diskCSIDriver: {
        enabled: true
      }
      fileCSIDriver: {
        enabled: true
      }
      snapshotController: {
        enabled: true
      }
    }

    // OIDC issuer profile
    oidcIssuerProfile: {
      enabled: enableOIDCIssuer
    }

    // Workload auto-scaler profile
    workloadAutoScalerProfile: {}

    // Azure Monitor profile
    azureMonitorProfile: {
      metrics: {
        enabled: true
        kubeStateMetrics: {
          metricLabelsAllowlist: ''
          metricAnnotationsAllowList: ''
        }
      }
    }

    // Metrics profile
    metricsProfile: {
      costAnalysis: {
        enabled: false
      }
    }

    // Service principal profile
    servicePrincipalProfile: {
      clientId: 'msi'
    }

    // Add-on profiles
    addonProfiles: {
      azureKeyvaultSecretsProvider: {
        enabled: false
      }
      azurepolicy: {
        enabled: enableAzurePolicy
      }
    }

    disableLocalAccounts: false
  }
}

// Note: Role assignments should be created after cluster deployment using separate templates or scripts
// due to cross-scope dependencies and runtime property requirements

// Federated identity credential for Azure ALB workload identity
resource albIdentityFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: albIdentity
  name: 'azure-alb-federated-credential'
  properties: {
    audiences: ['api://AzureADTokenExchange']
    issuer: aksCluster.properties.oidcIssuerProfile.issuerURL
    subject: 'system:serviceaccount:azure-alb-system:alb-controller-sa'
  }
}

// Federated identity credential for Kaito provisioner workload identity
resource kaitoProvisionerFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: kaitoProvisionerIdentity
  name: 'kaito-provisioner-federated-credential'
  properties: {
    audiences: ['api://AzureADTokenExchange']
    issuer: aksCluster.properties.oidcIssuerProfile.issuerURL
    subject: 'system:serviceaccount:${kaitoServiceAccountNamespace}:${kaitoServiceAccountName}'
  }
}

// User node pool
resource userAgentPool 'Microsoft.ContainerService/managedClusters/agentPools@2025-02-01' = {
  parent: aksCluster
  name: userNodePool.name
  properties: {
    count: userNodePool.count
    vmSize: userNodePool.vmSize
    osDiskSizeGB: userNodePool.osDiskSizeGB
    osDiskType: userNodePool.osDiskType
    kubeletDiskType: 'OS'
    maxPods: userNodePool.maxPods
    type: 'VirtualMachineScaleSets'
    availabilityZones: userNodePool.availabilityZones
    maxCount: userNodePool.maxCount
    minCount: userNodePool.minCount
    enableAutoScaling: userNodePool.enableAutoScaling
    scaleDownMode: 'Delete'
    orchestratorVersion: kubernetesVersion
    enableNodePublicIP: false
    mode: 'User'
    osType: 'Linux'
    osSKU: 'Ubuntu'
    upgradeSettings: {
      maxSurge: '10%'
    }
    enableFIPS: false
  }
}

// Note: ALB subnet and role assignments should be created post-deployment due to cross-scope dependencies

@description('The resource group name')
output resourceGroupName string = resourceGroupName

@description('The resource group resource ID')
output resourceGroupId string = resourceGroup().id

@description('The resource ID of the AKS cluster')
output clusterResourceId string = aksCluster.id

@description('The name of the AKS cluster')
output clusterName string = aksCluster.name

@description('The FQDN of the AKS cluster')
output clusterFQDN string = aksCluster.properties.fqdn

@description('The OIDC issuer URL')
output oidcIssuerUrl string = enableOIDCIssuer ? aksCluster.properties.oidcIssuerProfile.issuerURL : ''

@description('The kubelet identity object ID')
output kubeletIdentityObjectId string = aksCluster.properties.identityProfile.kubeletidentity.objectId

@description('The kubelet identity client ID')
output kubeletIdentityClientId string = aksCluster.properties.identityProfile.kubeletidentity.clientId

@description('The cluster principal ID (system-assigned managed identity)')
output clusterPrincipalId string = aksCluster.identity.principalId

@description('The node resource group name')
output nodeResourceGroup string = aksCluster.properties.nodeResourceGroup

@description('The ALB managed identity resource ID')
output albIdentityResourceId string = albIdentity.id

@description('The ALB managed identity client ID')
output albIdentityClientId string = albIdentity.properties.clientId

@description('The ALB managed identity principal ID')
output albIdentityPrincipalId string = albIdentity.properties.principalId

@description('The ALB identity federated credential name')
output albIdentityFederatedCredentialName string = albIdentityFederatedCredential.name

@description('The ALB service account subject for the federated credential')
output albServiceAccountSubject string = 'system:serviceaccount:azure-alb-system:alb-controller-sa'

@description('The Kaito provisioner managed identity resource ID')
output kaitoProvisionerIdentityResourceId string = kaitoProvisionerIdentity.id

@description('The Kaito provisioner managed identity client ID')
output kaitoProvisionerIdentityClientId string = kaitoProvisionerIdentity.properties.clientId

@description('The Kaito provisioner managed identity principal ID')
output kaitoProvisionerIdentityPrincipalId string = kaitoProvisionerIdentity.properties.principalId

@description('The Kaito provisioner federated credential name')
output kaitoProvisionerFederatedCredentialName string = kaitoProvisionerFederatedCredential.name

@description('The service account subject for the federated credential')
output kaitoProvisionerServiceAccountSubject string = 'system:serviceaccount:${kaitoServiceAccountNamespace}:${kaitoServiceAccountName}'

@description('The ALB subnet address prefix to use for post-deployment subnet creation')
output albSubnetAddressPrefix string = albSubnetAddressPrefix