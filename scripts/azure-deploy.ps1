# Azure Container Registry & AKS Deployment Script (Windows PowerShell)
# Complete setup from local images to AKS deployment

param(
    [string]$ResourceGroup = "vision-rg",
    [string]$AcrName = "realtime-vision",
    [string]$AksName = "vision-aks",
    [string]$Location = "eastus",
    [int]$NodeCount = 3
)

# Helper functions
function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    $colors = @{
        "Info" = "Cyan"
        "Success" = "Green"
        "Warning" = "Yellow"
        "Error" = "Red"
    }
    Write-Host $Message -ForegroundColor $colors[$Type]
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=" * 50 -ForegroundColor Blue
    Write-Host $Title -ForegroundColor Blue
    Write-Host "=" * 50 -ForegroundColor Blue
    Write-Host ""
}

# Main script
Write-Section "Azure Container Registry & AKS Setup"

# Check prerequisites
Write-Status "[1/8] Checking prerequisites..." "Warning"
$prerequisites = @("az", "docker", "kubectl")
foreach ($cmd in $prerequisites) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Status "✗ $cmd is not installed" "Error"
        exit 1
    }
}
Write-Status "✓ All prerequisites found" "Success"

# Login to Azure
Write-Host ""
Write-Status "[2/8] Logging in to Azure..." "Warning"
az login
$account = az account show --query '{Name:name, ID:id}' | ConvertFrom-Json
Write-Status "✓ Logged in as: $($account.Name)" "Success"

# Create Resource Group
Write-Host ""
Write-Status "[3/8] Creating resource group..." "Warning"
az group create --name $ResourceGroup --location $Location 2>&1 | Out-Null
Write-Status "✓ Resource group ready" "Success"

# Create ACR
Write-Host ""
Write-Status "[4/8] Creating Azure Container Registry..." "Warning"
az acr create `
    --resource-group $ResourceGroup `
    --name $AcrName `
    --sku Basic 2>&1 | Out-Null
Write-Status "✓ ACR created" "Success"

# Get ACR login server
$AcrRegistry = az acr show --resource-group $ResourceGroup --name $AcrName --query loginServer -o tsv
Write-Host "ACR Login Server: $AcrRegistry"

# Login to ACR
Write-Host ""
Write-Status "[5/8] Logging in to ACR..." "Warning"
az acr login --name $AcrName
Write-Status "✓ Logged in to ACR" "Success"

# Build and push images
Write-Host ""
Write-Status "[6/8] Building and pushing Docker images..." "Warning"

$services = @(
    @{ Name = "yolo-inference"; Dockerfile = "docker/Dockerfile.yolo" },
    @{ Name = "logging-service"; Dockerfile = "docker/Dockerfile.logging" },
    @{ Name = "mlflow-server"; Dockerfile = "docker/Dockerfile.mlflow" },
    @{ Name = "camera-stream"; Dockerfile = "docker/Dockerfile.camera" },
    @{ Name = "preprocessing-service"; Dockerfile = "docker/Dockerfile.preprocessing" }
)

foreach ($service in $services) {
    Write-Host ""
    Write-Status "Building $($service.Name)..." "Warning"
    
    # Build
    docker build --file $service.Dockerfile --tag "$($service.Name):latest" .
    if ($LASTEXITCODE -ne 0) {
        Write-Status "✗ Failed to build $($service.Name)" "Error"
        exit 1
    }
    
    # Tag for ACR
    docker tag "$($service.Name):latest" "$AcrRegistry/$($service.Name):latest"
    docker tag "$($service.Name):latest" "$AcrRegistry/$($service.Name):v1.0"
    
    # Push
    docker push "$AcrRegistry/$($service.Name):latest"
    docker push "$AcrRegistry/$($service.Name):v1.0"
    
    Write-Status "✓ Pushed $($service.Name)" "Success"
}

# Create AKS cluster
Write-Host ""
Write-Status "[7/8] Creating AKS cluster..." "Warning"
az aks create `
    --resource-group $ResourceGroup `
    --name $AksName `
    --node-count $NodeCount `
    --enable-managed-identity `
    --vm-set-type VirtualMachineScaleSets `
    --load-balancer-sku standard `
    --enable-cluster-autoscaler `
    --min-count 1 `
    --max-count 5 `
    --enable-addons monitoring `
    --generate-ssh-keys 2>&1 | Out-Null
Write-Status "✓ AKS cluster created/updated" "Success"

# Attach ACR to AKS
Write-Host ""
Write-Status "[8/8] Attaching ACR to AKS..." "Warning"
az aks update `
    --resource-group $ResourceGroup `
    --name $AksName `
    --attach-acr $AcrName 2>&1 | Out-Null
Write-Status "✓ ACR attached to AKS" "Success"

# Get AKS credentials
Write-Host ""
Write-Status "Getting AKS credentials..." "Warning"
az aks get-credentials `
    --resource-group $ResourceGroup `
    --name $AksName `
    --overwrite-existing
Write-Status "✓ Credentials configured" "Success"

# Verify connection
Write-Host ""
Write-Status "Verifying connection..." "Warning"
kubectl cluster-info
Write-Status "✓ Connected to AKS" "Success"

# Update Kubernetes manifests
Write-Host ""
Write-Status "Updating Kubernetes manifests with ACR registry..." "Warning"

$deploymentPath = "k8s/deployments.yaml"
$content = Get-Content $deploymentPath -Raw
$content = $content -replace "realtime-vision-system:yolo-latest", "$AcrRegistry/yolo-inference:latest"
$content = $content -replace "realtime-vision-system:logging-latest", "$AcrRegistry/logging-service:latest"
Set-Content $deploymentPath -Value $content -Encoding UTF8

Write-Status "✓ Manifests updated" "Success"

# Deploy to AKS
Write-Host ""
Write-Status "Deploying to AKS..." "Warning"
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmaps.yaml
kubectl apply -f k8s/persistent-volumes.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/deployments.yaml
kubectl apply -f k8s/services.yaml
kubectl apply -f k8s/autoscaling.yaml
Write-Status "✓ Deployed to AKS" "Success"

# Show summary
Write-Section "Deployment Summary"

Write-Status "Azure Resources:" "Warning"
Write-Host "  Resource Group: $ResourceGroup"
Write-Host "  ACR: $AcrRegistry"
Write-Host "  AKS Cluster: $AksName"

Write-Host ""
Write-Status "Next Steps:" "Warning"
Write-Host "  1. Monitor pods:"
Write-Host "     kubectl get pods -n vision-system -w"
Write-Host ""
Write-Host "  2. View logs:"
Write-Host "     kubectl logs -n vision-system -l app=yolo -f"
Write-Host ""
Write-Host "  3. Check services:"
Write-Host "     kubectl get svc -n vision-system"
Write-Host ""
Write-Host "  4. Access MLflow:"
Write-Host "     kubectl port-forward -n vision-system svc/mlflow-service 5000:5000"
Write-Host ""

Write-Section "Setup Complete!"
