#!/bin/bash

# AKS Cluster Deployment Script - Two-stage deployment with ALB support
set -e

# Default values
SUBSCRIPTION_ID=""
LOCATION="westeurope"
DEPLOYMENT_NAME="aks-cluster-deployment-$(date +%Y%m%d-%H%M%S)"
ALB_DEPLOYMENT_NAME="alb-subnet-deployment-$(date +%Y%m%d-%H%M%S)"
TEMPLATE_FILE="aks-cluster.bicep"
PARAMETERS_FILE="aks-cluster.parameters.json"
ALB_TEMPLATE_FILE="alb-subnet.bicep"
SKIP_ALB=false

usage() {
    echo "Usage: $0 -s <subscription-id> [OPTIONS]"
    echo ""
    echo "  -s, --subscription     Azure subscription ID (required)"
    echo "  -l, --location         Azure region (default: westeurope)"
    echo "  --skip-alb             Skip ALB subnet deployment"
    echo "  --what-if              Preview deployment changes"
    echo "  --validate-only        Validate templates only"
    echo "  -h, --help             Show help"
    echo ""
    echo "Examples:"
    echo "  $0 -s 12345678-1234-1234-1234-123456789abc"
    echo "  $0 -s 12345678-1234-1234-1234-123456789abc --what-if"
    echo "  $0 -s 12345678-1234-1234-1234-123456789abc --skip-alb"
}

# Parse arguments
WHAT_IF=false
VALIDATE_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--subscription) SUBSCRIPTION_ID="$2"; shift 2 ;;
        -l|--location) LOCATION="$2"; shift 2 ;;
        --what-if) WHAT_IF=true; shift ;;
        --validate-only) VALIDATE_ONLY=true; shift ;;
        --skip-alb) SKIP_ALB=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# Validation
if [[ -z "$SUBSCRIPTION_ID" ]]; then
    echo "Error: Subscription ID is required"
    usage
    exit 1
fi

for file in "$TEMPLATE_FILE" "$PARAMETERS_FILE"; do
    if [[ ! -f "$file" ]]; then
        echo "Error: File '$file' not found"
        exit 1
    fi
done

if [[ "$SKIP_ALB" == false && ! -f "$ALB_TEMPLATE_FILE" ]]; then
    echo "Error: ALB template file '$ALB_TEMPLATE_FILE' not found"
    exit 1
fi

# Set Azure subscription
echo "Setting Azure subscription to $SUBSCRIPTION_ID..."
az account set --subscription "$SUBSCRIPTION_ID"

# Extract resource group name from parameters file
RESOURCE_GROUP=$(jq -r '.parameters.resourceGroupName.value' "$PARAMETERS_FILE")

# Create resource group if it doesn't exist
echo "Ensuring resource group '$RESOURCE_GROUP' exists..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

# Stage 1: Validate AKS cluster template
echo "Validating AKS cluster Bicep template..."
az deployment group validate \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$TEMPLATE_FILE" \
    --parameters "@$PARAMETERS_FILE" \
    --debug

# Validate ALB template if not skipping
if [[ "$SKIP_ALB" == false ]]; then
    echo "Validating ALB subnet Bicep template..."
    az deployment group validate \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$ALB_TEMPLATE_FILE" \
        --debug \
        --parameters \
            nodeResourceGroup="$RESOURCE_GROUP" \
            albIdentityPrincipalId="00000000-0000-0000-0000-000000000000" \
            albIdentityResourceId="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ManagedIdentity/userAssignedIdentities/dummy" \
            clusterResourceId="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ContainerService/managedClusters/dummy" \
            aksVnetName="dummy-vnet"
fi

if [[ "$VALIDATE_ONLY" == true ]]; then
    echo "Template validation completed successfully."
    exit 0
fi

# Run what-if or actual deployment
if [[ "$WHAT_IF" == true ]]; then
    echo "Running what-if deployment for AKS cluster..."
    az deployment group what-if \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DEPLOYMENT_NAME" \
        --template-file "$TEMPLATE_FILE" \
        --parameters "@$PARAMETERS_FILE"
    
    if [[ "$SKIP_ALB" == false ]]; then
        echo "ALB subnet deployment would be run after cluster deployment completes."
        echo "Use --skip-alb flag to skip ALB subnet deployment in what-if mode."
    fi
else
    # Stage 1: Deploy AKS cluster
    echo "Stage 1: Deploying AKS cluster and managed identities..."
    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DEPLOYMENT_NAME" \
        --template-file "$TEMPLATE_FILE" \
        --parameters "@$PARAMETERS_FILE"
    
    echo "Stage 1 deployment completed successfully!"
    
    # Stage 2: Deploy ALB if not skipped
    if [[ "$SKIP_ALB" == false ]]; then
        echo "Stage 2: Setting up ALB subnet and role assignments..."
        
        # Get deployment outputs
        get_output() {
            az deployment group show --resource-group "$RESOURCE_GROUP" --name "$DEPLOYMENT_NAME" \
                --query "properties.outputs.$1.value" --output tsv
        }
        
        CLUSTER_NAME=$(get_output "clusterName")
        NODE_RESOURCE_GROUP=$(get_output "nodeResourceGroup")
        ALB_SUBNET_PREFIX=$(get_output "albSubnetAddressPrefix")
        ALB_IDENTITY_PRINCIPAL_ID=$(get_output "albIdentityPrincipalId")
        ALB_IDENTITY_RESOURCE_ID=$(get_output "albIdentityResourceId")
        KAITO_IDENTITY_PRINCIPAL_ID=$(get_output "kaitoProvisionerIdentityPrincipalId")
        KAITO_IDENTITY_RESOURCE_ID=$(get_output "kaitoProvisionerIdentityResourceId")
        CLUSTER_RESOURCE_ID=$(get_output "clusterResourceId")
        
        # Discover AKS VNet for ALB subnet deployment
        echo "Discovering AKS VNet in resource group: $NODE_RESOURCE_GROUP"
        AKS_VNET_NAME=$(az network vnet list --resource-group "$NODE_RESOURCE_GROUP" --query "[0].name" --output tsv)
        
        if [[ -z "$AKS_VNET_NAME" || "$AKS_VNET_NAME" == "null" ]]; then
            echo "Error: Could not find AKS VNet in resource group: $NODE_RESOURCE_GROUP"
            exit 1
        fi
        
        echo "Found AKS VNet: $AKS_VNET_NAME"
        
        # Deploy ALB subnet and role assignments via Bicep modules
        echo "Deploying ALB subnet and role assignments via Bicep template..."
        az deployment group create \
            --resource-group "$RESOURCE_GROUP" \
            --name "$ALB_DEPLOYMENT_NAME" \
            --template-file "$ALB_TEMPLATE_FILE" \
            --parameters \
                nodeResourceGroup="$NODE_RESOURCE_GROUP" \
                albIdentityPrincipalId="$ALB_IDENTITY_PRINCIPAL_ID" \
                albIdentityResourceId="$ALB_IDENTITY_RESOURCE_ID" \
                kaitoProvisionerIdentityPrincipalId="$KAITO_IDENTITY_PRINCIPAL_ID" \
                kaitoProvisionerIdentityResourceId="$KAITO_IDENTITY_RESOURCE_ID" \
                clusterResourceId="$CLUSTER_RESOURCE_ID" \
                aksVnetName="$AKS_VNET_NAME"
        
        echo "Stage 2 deployment completed successfully!"
    fi
    
    # Summary
    echo ""
    echo "Deployment Summary"
    echo "=================="
    echo "Cluster: $CLUSTER_NAME"
    echo "Resource Group: $RESOURCE_GROUP"
    echo ""
    echo "To get kubectl credentials:"
    echo "az aks get-credentials --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME"
    
    if [[ "$SKIP_ALB" == true ]]; then
        echo ""
        echo "Note: ALB subnet was skipped. Use without --skip-alb to deploy ALB components."
    fi
fi