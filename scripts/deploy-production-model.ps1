# Deployment Script for Production Model (PowerShell)
# 
# Pulls latest Production model from MLflow and updates inference service container
#
# Usage:
#   .\deploy-production-model.ps1 -Deployment docker
#   .\deploy-production-model.ps1 -Deployment docker -DryRun
#   .\deploy-production-model.ps1 -Deployment k8s -Namespace production

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("docker", "k8s")]
    [string]$Deployment,
    
    [Parameter(Mandatory=$false)]
    [string]$MlflowUri = $env:MLFLOW_TRACKING_URI -replace '\s','' ,
    
    [Parameter(Mandatory=$false)]
    [string]$ModelName = $env:MODEL_NAME -replace '\s','' ,
    
    [Parameter(Mandatory=$false)]
    [string]$ModelStage = "Production",
    
    [Parameter(Mandatory=$false)]
    [string]$ServiceName = "inference-service",
    
    [Parameter(Mandatory=$false)]
    [string]$Namespace = "default",
    
    [Parameter(Mandatory=$false)]
    [string]$Registry = $null,
    
    [Parameter(Mandatory=$false)]
    [string]$ImageTag = "latest",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBuild = $false,
    
    [Parameter(Mandatory=$false)]
    [int]$Timeout = 300,
    
    [Parameter(Mandatory=$false)]
    [switch]$NoRollback = $false
)

# Set defaults if not provided
if (-not $MlflowUri) {
    $MlflowUri = "http://127.0.0.1:5000"
}
if (-not $ModelName) {
    $ModelName = "simple-cnn-demo"
}
if (-not $Registry) {
    $Registry = "localhost"
}

# Configuration
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir

Write-Host "==================== DEPLOYMENT CONFIGURATION ====================" -ForegroundColor Cyan
Write-Host "Deployment Type: $Deployment"
Write-Host "MLflow URI: $MlflowUri"
Write-Host "Model Name: $ModelName"
Write-Host "Model Stage: $ModelStage"
Write-Host "Service Name: $ServiceName"
if ($Deployment -eq "k8s") {
    Write-Host "Namespace: $Namespace"
}
Write-Host "Registry: $Registry"
Write-Host "Image Tag: $ImageTag"
Write-Host "Dry Run: $DryRun"
Write-Host "===================================================================" -ForegroundColor Cyan

# Helper function to log messages
function Write-Log {
    param(
        [string]$Message,
        [ValidateSet("Info", "Success", "Warning", "Error")]
        [string]$Level = "Info"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    switch ($Level) {
        "Info" { Write-Host "[$timestamp] INFO: $Message" -ForegroundColor White }
        "Success" { Write-Host "[$timestamp] ✓ $Message" -ForegroundColor Green }
        "Warning" { Write-Host "[$timestamp] ⚠ $Message" -ForegroundColor Yellow }
        "Error" { Write-Host "[$timestamp] ✗ $Message" -ForegroundColor Red }
    }
}

# Helper function to execute commands
function Invoke-Command {
    param(
        [string[]]$Command,
        [string]$ErrorMessage = "Command failed",
        [bool]$AllowFailure = $false
    )
    
    $commandStr = $Command -join " "
    Write-Log "Executing: $commandStr"
    
    if ($DryRun) {
        Write-Log "[DRY-RUN] Would execute: $commandStr" "Info"
        return $true
    }
    
    try {
        & @Command 2>&1 | Tee-Object -Variable output | Write-Host
        if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
            if (-not $AllowFailure) {
                Write-Log "$ErrorMessage (exit code: $LASTEXITCODE)" "Error"
                return $false
            }
        }
        return $true
    }
    catch {
        Write-Log "$ErrorMessage: $_" "Error"
        return $false
    }
}

# Function to validate MLflow model
function Test-MLflowModel {
    Write-Log "Validating MLflow model..."
    
    $pythonScript = @"
import sys
import mlflow
import json

mlflow.set_tracking_uri('$MlflowUri')
client = mlflow.tracking.MlflowClient(tracking_uri='$MlflowUri')

try:
    model_version = client.get_model_version_by_stage(name='$ModelName', stage='$ModelStage')
    model_info = {
        'name': '$ModelName',
        'version': model_version.version,
        'stage': '$ModelStage',
        'uri': f'models:/$ModelName/$ModelStage',
        'status': model_version.status
    }
    print(json.dumps(model_info))
    sys.exit(0)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
"@

    try {
        $result = python -c $pythonScript 2>&1
        if ($LASTEXITCODE -eq 0) {
            $modelInfo = $result | ConvertFrom-Json
            Write-Log "Model found: $($modelInfo.uri)" "Success"
            Write-Log "  Version: $($modelInfo.version)" "Info"
            Write-Log "  Status: $($modelInfo.status)" "Info"
            return $true
        }
        else {
            Write-Log "Model validation failed: $result" "Error"
            return $false
        }
    }
    catch {
        Write-Log "Failed to validate model: $_" "Error"
        return $false
    }
}

# Docker deployment functions
function Deploy-Docker {
    Write-Log "================================" "Info"
    Write-Log "DOCKER DEPLOYMENT" "Info"
    Write-Log "================================" "Info"
    
    $imageName = "$Registry/$ServiceName"
    if ($ImageTag -and $ImageTag -ne "latest") {
        $imageName = "$imageName`:$ImageTag"
    }
    else {
        $imageName = "$imageName`:latest"
    }
    
    # Build image
    if (-not $SkipBuild) {
        Write-Log "Building Docker image: $imageName"
        if (-not (Invoke-Command @("docker", "build", "-t", $imageName, ".") -ErrorMessage "Docker build failed")) {
            return $false
        }
        Write-Log "Docker image built successfully" "Success"
    }
    
    # Stop existing container
    Write-Log "Checking for existing container..."
    try {
        $containerId = & docker ps -q -f "name=$ServiceName" 2>&1
        if ($containerId) {
            Write-Log "Stopping existing container: $containerId"
            if (-not (Invoke-Command @("docker", "stop", $containerId) -ErrorMessage "Failed to stop container" -AllowFailure)) {
                Write-Log "Continuing despite container stop failure" "Warning"
            }
            Start-Sleep -Seconds 2
        }
    }
    catch {
        Write-Log "Could not check for existing container" "Warning"
    }
    
    # Start new container
    Write-Log "Starting new container..."
    $dockerArgs = @(
        "docker", "run", "-d",
        "--name", $ServiceName,
        "-p", "8000:8000",
        "-e", "MLFLOW_TRACKING_URI=$MlflowUri",
        "-e", "MODEL_NAME=$ModelName",
        "-e", "MODEL_STAGE=$ModelStage",
        $imageName
    )
    
    if (-not (Invoke-Command $dockerArgs -ErrorMessage "Failed to start container")) {
        return $false
    }
    
    # Wait for health check
    Write-Log "Waiting for container to be healthy..."
    $healthCheckAttempts = 10
    $attempt = 0
    while ($attempt -lt $healthCheckAttempts) {
        try {
            $healthCheck = & docker exec $ServiceName curl -f http://localhost:8000/health 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Log "Container is healthy" "Success"
                return $true
            }
        }
        catch {}
        
        $attempt++
        if ($attempt -lt $healthCheckAttempts) {
            Write-Log "  Health check attempt $attempt/$healthCheckAttempts..."
            Start-Sleep -Seconds 3
        }
    }
    
    Write-Log "Container health check failed" "Error"
    return $false
}

# Kubernetes deployment functions
function Deploy-Kubernetes {
    Write-Log "================================" "Info"
    Write-Log "KUBERNETES DEPLOYMENT" "Info"
    Write-Log "================================" "Info"
    Write-Log "Namespace: $Namespace" "Info"
    Write-Log "Deployment: $ServiceName" "Info"
    
    $imageName = "$Registry/$ServiceName"
    if ($ImageTag -and $ImageTag -ne "latest") {
        $imageName = "$imageName`:$ImageTag"
    }
    else {
        $imageName = "$imageName`:latest"
    }
    
    Write-Log "Image: $imageName" "Info"
    
    # Check if deployment exists
    Write-Log "Checking if deployment exists..."
    try {
        $deployment = & kubectl get deployment $ServiceName -n $Namespace -o json 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Deployment '$ServiceName' not found in namespace '$Namespace'" "Error"
            Write-Log "Please create the deployment first" "Info"
            return $false
        }
    }
    catch {
        Write-Log "Failed to check deployment: $_" "Error"
        return $false
    }
    
    # Build and push image
    if (-not $SkipBuild) {
        Write-Log "Building Docker image..."
        if (-not (Invoke-Command @("docker", "build", "-t", $imageName, ".") -ErrorMessage "Docker build failed")) {
            return $false
        }
        Write-Log "Docker image built" "Success"
        
        Write-Log "Pushing image to registry..."
        if (-not (Invoke-Command @("docker", "push", $imageName) -ErrorMessage "Docker push failed")) {
            return $false
        }
        Write-Log "Image pushed" "Success"
    }
    
    # Patch deployment
    Write-Log "Updating deployment image..."
    $patchArgs = @(
        "kubectl", "set", "image",
        "deployment/$ServiceName",
        "$ServiceName=$imageName",
        "-n", $Namespace
    )
    
    if (-not (Invoke-Command $patchArgs -ErrorMessage "Failed to patch deployment")) {
        return $false
    }
    Write-Log "Deployment patched" "Success"
    
    # Wait for rollout
    Write-Log "Waiting for rollout to complete (timeout: ${Timeout}s)..."
    $rolloutArgs = @(
        "kubectl", "rollout", "status",
        "deployment/$ServiceName",
        "-n", $Namespace,
        "--timeout=${Timeout}s"
    )
    
    if (-not (Invoke-Command $rolloutArgs -ErrorMessage "Rollout failed")) {
        if (-not $NoRollback) {
            Write-Log "Rolling back deployment..."
            $rollbackArgs = @(
                "kubectl", "rollout", "undo",
                "deployment/$ServiceName",
                "-n", $Namespace
            )
            Invoke-Command $rollbackArgs -ErrorMessage "Rollback failed" -AllowFailure | Out-Null
        }
        return $false
    }
    
    Write-Log "Rollout completed" "Success"
    return $true
}

# Main execution
try {
    # Validate model
    if (-not (Test-MLflowModel)) {
        Write-Log "Model validation failed" "Error"
        exit 1
    }
    
    # Execute deployment
    if ($Deployment -eq "docker") {
        $success = Deploy-Docker
    }
    elseif ($Deployment -eq "k8s") {
        $success = Deploy-Kubernetes
    }
    
    if ($success) {
        Write-Host ""
        Write-Log "===================================================================" "Info"
        Write-Log "✓ DEPLOYMENT SUCCESSFUL" "Success"
        Write-Log "===================================================================" "Info"
        Write-Log "Model: $ModelName" "Info"
        Write-Log "Stage: $ModelStage" "Info"
        Write-Log "Deployment: $Deployment" "Info"
        exit 0
    }
    else {
        Write-Host ""
        Write-Log "===================================================================" "Info"
        Write-Log "✗ DEPLOYMENT FAILED" "Error"
        Write-Log "===================================================================" "Info"
        exit 1
    }
}
catch {
    Write-Log "Unexpected error: $_" "Error"
    exit 1
}
