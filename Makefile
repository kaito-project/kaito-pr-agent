AKS_NAME ?= 'kaito-pr-agent'
RESOURCE_GROUP ?= 'kaito-pr-agent'
SUBNET_ADDRESS_PREFIX ?= '10.225.0.0/24'
ALB_SUBNET_NAME ?= 'subnet-alb' # subnet name can be any non-reserved subnet name (i.e. GatewaySubnet, AzureFirewallSubnet, AzureBastionSubnet would all be invalid)
IDENTITY_RESOURCE_NAME ?= 'azure-alb-identity'
HELM_NAMESPACE ?= 'default'
CONTROLLER_NAMESPACE ?= 'azure-alb-system'

setup-agc: create-alb-identity create-alb-subnet install-alb-controller apply-agc-resources

.PHONY: create-alb-identity
create-alb-identity:
	mcResourceGroup=$(az aks show --resource-group $RESOURCE_GROUP --name $AKS_NAME --query "nodeResourceGroup" -o tsv)
	mcResourceGroupId=$(az group show --name $mcResourceGroup --query id -otsv)

	echo "Creating identity $IDENTITY_RESOURCE_NAME in resource group $RESOURCE_GROUP"
	az identity create --resource-group $RESOURCE_GROUP --name $IDENTITY_RESOURCE_NAME
	principalId="$(az identity show -g $RESOURCE_GROUP -n $IDENTITY_RESOURCE_NAME --query principalId -otsv)"

	echo "Waiting 60 seconds to allow for replication of the identity..."
	sleep 60

	echo "Apply Reader role to the AKS managed cluster resource group for the newly provisioned identity"
	az role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal --scope $mcResourceGroupId --role "acdd72a7-3385-48ef-bd42-f606fba81ae7" # Reader role

	echo "Set up federation with AKS OIDC issuer"
	AKS_OIDC_ISSUER="$(az aks show -n "$AKS_NAME" -g "$RESOURCE_GROUP" --query "oidcIssuerProfile.issuerUrl" -o tsv)"
	az identity federated-credential create --name "azure-alb-identity" --identity-name "$IDENTITY_RESOURCE_NAME" --resource-group $RESOURCE_GROUP --issuer "$AKS_OIDC_ISSUER" --subject "system:serviceaccount:azure-alb-system:alb-controller-sa"

.PHONY: install-alb-controller
install-alb-controller:
	az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_NAME
	helm install alb-controller oci://mcr.microsoft.com/application-lb/charts/alb-controller --namespace $HELM_NAMESPACE --version 1.7.9 --set albController.namespace=$CONTROLLER_NAMESPACE --set albController.podIdentity.clientID=$(az identity show -g $RESOURCE_GROUP -n azure-alb-identity --query clientId -o tsv)

.PHONY: create-alb-subnet
create-alb-subnet:
	MC_RESOURCE_GROUP=$(az aks show --name $AKS_NAME --resource-group $RESOURCE_GROUP --query "nodeResourceGroup" -o tsv)
	CLUSTER_SUBNET_ID=$(az vmss list --resource-group $MC_RESOURCE_GROUP --query '[0].virtualMachineProfile.networkProfile.networkInterfaceConfigurations[0].ipConfigurations[0].subnet.id' -o tsv)
	VNET_NAME=$(az network vnet show --ids $CLUSTER_SUBNET_ID --query 'name' -o tsv)
	VNET_RESOURCE_GROUP=$(az network vnet show --ids $CLUSTER_SUBNET_ID --query 'resourceGroup' -o tsv)
	VNET_ID=$(az network vnet show --ids $CLUSTER_SUBNET_ID --query 'id' -o tsv)

	az network vnet subnet create \
	--resource-group $VNET_RESOURCE_GROUP \
	--vnet-name $VNET_NAME \
	--name $ALB_SUBNET_NAME \
	--address-prefixes $SUBNET_ADDRESS_PREFIX \
	--delegations 'Microsoft.ServiceNetworking/trafficControllers'
	ALB_SUBNET_ID=$(az network vnet subnet show --name $ALB_SUBNET_NAME --resource-group $VNET_RESOURCE_GROUP --vnet-name $VNET_NAME --query '[id]' --output tsv)

	MC_RESOURCE_GROUP=$(az aks show --name $AKS_NAME --resource-group $RESOURCE_GROUP --query "nodeResourceGroup" -otsv | tr -d '\r')

	mcResourceGroupId=$(az group show --name $MC_RESOURCE_GROUP --query id -otsv)
	principalId=$(az identity show -g $RESOURCE_GROUP -n $IDENTITY_RESOURCE_NAME --query principalId -otsv)

	# Delegate AppGw for Containers Configuration Manager role to AKS Managed Cluster RG
	az role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal --scope $mcResourceGroupId --role "fbc52c3f-28ad-4303-a892-8a056630b8f1"

	# Delegate Network Contributor permission for join to association subnet
	az role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal --scope $ALB_SUBNET_ID --role "4d97b98b-1d4f-4787-a291-c67834d212e7"

.PHONY: apply-agc-resources
apply-agc-resources:
	ALB_SUBNET_ID=$(az network vnet subnet show --name $ALB_SUBNET_NAME --resource-group $VNET_RESOURCE_GROUP --vnet-name $VNET_NAME --query '[id]' --output tsv)
	az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_NAME --overwrite-existing
	k apply -f deploy/agc/applicationloadbalancer.yaml
	k apply -f deploy/agc/gateway.yaml
	k apply -f deploy/agc/httproute.yaml