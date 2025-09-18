# AKS Cluster Deployment with Application Load Balancer

Production-ready Bicep templates for deploying AKS clusters with Application Load Balancer support and Kaito AI workload integration.

## Features

✅ **Complete AKS Infrastructure** - Cluster, node pools, networking, monitoring  
✅ **Application Load Balancer Ready** - Dedicated subnet with proper permissions  
✅ **Workload Identity** - Passwordless authentication for ALB and Kaito  
✅ **Auto-scaling** - Multi-zone deployment with intelligent scaling  
✅ **Security Hardened** - RBAC, Azure Policy, managed identities

## Files

- `aks-cluster.bicep` - Main AKS cluster template
- `aks-cluster.parameters.json` - Configuration parameters  
- `alb-subnet.bicep` - ALB subnet and role assignments
- `deploy.sh` - Two-stage deployment script

## Quick Start

**Prerequisites**: Azure CLI, Contributor/Owner permissions, `jq` tool

1. **Configure parameters**: Edit `aks-cluster.parameters.json`
2. **Deploy**: `./deploy.sh -s <subscription-id>`
3. **Get credentials**: Follow the output instructions

## Deployment Options

```bash
# Complete deployment (recommended)
./deploy.sh -s <subscription-id>

# Preview changes first  
./deploy.sh -s <subscription-id> --what-if

# Validate templates only
./deploy.sh -s <subscription-id> --validate-only

# Skip ALB subnet (AKS only)
./deploy.sh -s <subscription-id> --skip-alb
```

## Key Parameters

Edit `aks-cluster.parameters.json` to customize:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `clusterName` | AKS cluster name | `kaito-dogfood` |
| `location` | Azure region | `westeurope` |
| `kubernetesVersion` | Kubernetes version | `1.32.6` |
| `albSubnetAddressPrefix` | ALB subnet CIDR | `10.245.0.0/24` |

## What Gets Deployed

### Stage 1: Core Infrastructure
- **AKS Cluster** - Multi-zone with auto-scaling (2-5 nodes)
- **Managed Identities** - ALB and Kaito provisioner with workload identity
- **Node Pools** - System pool (tainted) + User pool

### Stage 2: ALB Configuration  
- **ALB Subnet** - Dedicated subnet with proper delegations
- **Role Assignments** - Network permissions for ALB identity

## Post-Deployment

```bash
# Get cluster credentials (example)
az aks get-credentials --resource-group kaito-dogfood --name kaito-dogfood

# Verify deployment
kubectl get nodes
```

The cluster includes:
- ✅ Azure Monitor integration
- ✅ Workload Identity for ALB/Kaito  
- ✅ Azure Policy and RBAC
- ✅ Ready for Application Load Balancer deployment

## Troubleshooting

**Common issues:**
- Insufficient VM quota - check subscription limits
- Network conflicts - ensure ALB subnet doesn't overlap
- Permissions - need Contributor/Owner on subscription

**Validate deployment:**
```bash
# Check cluster status
az aks show --resource-group kaito-dogfood --name kaito-dogfood --query "provisioningState"

# Check managed identities  
az identity list --resource-group kaito-dogfood --output table
```