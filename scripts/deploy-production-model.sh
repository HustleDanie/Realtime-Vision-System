#!/bin/bash

# Deployment Script for Production Model (Bash)
#
# Pulls latest Production model from MLflow and updates inference service container
#
# Usage:
#   ./scripts/deploy-production-model.sh docker
#   ./scripts/deploy-production-model.sh docker --dry-run
#   ./scripts/deploy-production-model.sh k8s --namespace production

set -euo pipefail

# Configuration
DEPLOYMENT_TYPE="${1:-}"
MLFLOW_URI="${MLFLOW_TRACKING_URI:-http://127.0.0.1:5000}"
MODEL_NAME="${MODEL_NAME:-simple-cnn-demo}"
MODEL_STAGE="Production"
SERVICE_NAME="inference-service"
REGISTRY="${REGISTRY:-localhost}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
NAMESPACE="default"
DRY_RUN=false
SKIP_BUILD=false
TIMEOUT=300
ROLLBACK_ON_FAILURE=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}========================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================================${NC}"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        docker|k8s)
            DEPLOYMENT_TYPE="$1"
            shift
            ;;
        --mlflow-uri)
            MLFLOW_URI="$2"
            shift 2
            ;;
        --model-name)
            MODEL_NAME="$2"
            shift 2
            ;;
        --service-name)
            SERVICE_NAME="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --image-tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --no-rollback)
            ROLLBACK_ON_FAILURE=false
            shift
            ;;
        --help)
            echo "Usage: $0 [docker|k8s] [options]"
            echo ""
            echo "Options:"
            echo "  --mlflow-uri URI            MLflow tracking URI"
            echo "  --model-name NAME           MLflow model name"
            echo "  --service-name NAME         Service/deployment name"
            echo "  --namespace NS              Kubernetes namespace"
            echo "  --registry REGISTRY         Docker/K8s registry URL"
            echo "  --image-tag TAG             Docker image tag"
            echo "  --dry-run                   Simulate without changes"
            echo "  --skip-build                Skip image build step"
            echo "  --timeout SECONDS           Deployment timeout"
            echo "  --no-rollback               Don't rollback on failure"
            echo "  --help                      Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate inputs
if [[ -z "$DEPLOYMENT_TYPE" ]]; then
    print_error "Deployment type required (docker or k8s)"
    exit 1
fi

if [[ ! "$DEPLOYMENT_TYPE" =~ ^(docker|k8s)$ ]]; then
    print_error "Invalid deployment type: $DEPLOYMENT_TYPE"
    exit 1
fi

# Print configuration
print_header "DEPLOYMENT CONFIGURATION"
echo "Deployment Type: $DEPLOYMENT_TYPE"
echo "MLflow URI: $MLFLOW_URI"
echo "Model Name: $MODEL_NAME"
echo "Model Stage: $MODEL_STAGE"
echo "Service Name: $SERVICE_NAME"
if [[ "$DEPLOYMENT_TYPE" == "k8s" ]]; then
    echo "Namespace: $NAMESPACE"
fi
echo "Registry: $REGISTRY"
echo "Image Tag: $IMAGE_TAG"
echo "Dry Run: $DRY_RUN"

# Function to validate MLflow model
validate_mlflow_model() {
    print_info "Validating MLflow model..."
    
    python3 << EOF
import sys
import mlflow
import json
from datetime import datetime

mlflow.set_tracking_uri('$MLFLOW_URI')
client = mlflow.tracking.MlflowClient(tracking_uri='$MLFLOW_URI')

try:
    model_version = client.get_model_version_by_stage(name='$MODEL_NAME', stage='$MODEL_STAGE')
    model_info = {
        'name': '$MODEL_NAME',
        'version': model_version.version,
        'stage': '$MODEL_STAGE',
        'uri': f'models:/$MODEL_NAME/$MODEL_STAGE',
        'status': model_version.status,
        'created_at': datetime.fromtimestamp(model_version.creation_timestamp / 1000).isoformat()
    }
    
    print(json.dumps(model_info, indent=2))
    print(f"\nModel URI: models:/$MODEL_NAME/$MODEL_STAGE")
    print(f"Version: {model_version.version}")
    print(f"Status: {model_version.status}")
    print(f"Created: {model_info['created_at']}")
    
    sys.exit(0)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
EOF

    if [[ $? -eq 0 ]]; then
        print_success "MLflow model validation passed"
        return 0
    else
        print_error "MLflow model validation failed"
        return 1
    fi
}

# Docker deployment functions
build_docker_image() {
    local image_name="$REGISTRY/$SERVICE_NAME:$IMAGE_TAG"
    
    print_info "Building Docker image: $image_name"
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY-RUN] Would execute: docker build -t $image_name ."
        return 0
    fi
    
    if docker build -t "$image_name" .; then
        print_success "Docker image built: $image_name"
        return 0
    else
        print_error "Docker build failed"
        return 1
    fi
}

push_docker_image() {
    local image_name="$REGISTRY/$SERVICE_NAME:$IMAGE_TAG"
    
    if [[ "$REGISTRY" == "localhost" ]] || [[ "$REGISTRY" == "127.0.0.1" ]]; then
        print_info "Skipping push (local registry)"
        return 0
    fi
    
    print_info "Pushing image to registry..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY-RUN] Would execute: docker push $image_name"
        return 0
    fi
    
    if docker push "$image_name"; then
        print_success "Image pushed: $image_name"
        return 0
    else
        print_error "Docker push failed"
        return 1
    fi
}

stop_docker_container() {
    print_info "Checking for existing container..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY-RUN] Would stop container $SERVICE_NAME"
        return 0
    fi
    
    local container_id=$(docker ps -q -f "name=$SERVICE_NAME" || echo "")
    
    if [[ -n "$container_id" ]]; then
        print_info "Stopping container: $container_id"
        if docker stop "$container_id"; then
            print_success "Container stopped"
            sleep 2
            return 0
        else
            print_warning "Failed to stop container"
            return 0  # Continue anyway
        fi
    else
        print_info "No running container found"
        return 0
    fi
}

start_docker_container() {
    local image_name="$REGISTRY/$SERVICE_NAME:$IMAGE_TAG"
    
    print_info "Starting new container from $image_name..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY-RUN] Would start container with:"
        print_info "  Image: $image_name"
        print_info "  Name: $SERVICE_NAME"
        print_info "  Port: 8000:8000"
        return 0
    fi
    
    if docker run -d \
        --name "$SERVICE_NAME" \
        -p 8000:8000 \
        -e "MLFLOW_TRACKING_URI=$MLFLOW_URI" \
        -e "MODEL_NAME=$MODEL_NAME" \
        -e "MODEL_STAGE=$MODEL_STAGE" \
        "$image_name"; then
        print_success "Container started"
        
        # Wait for health check
        print_info "Waiting for container to be healthy..."
        local attempts=0
        local max_attempts=10
        
        while [[ $attempts -lt $max_attempts ]]; do
            if docker exec "$SERVICE_NAME" curl -f http://localhost:8000/health > /dev/null 2>&1; then
                print_success "Container is healthy"
                return 0
            fi
            
            attempts=$((attempts + 1))
            if [[ $attempts -lt $max_attempts ]]; then
                print_info "  Health check attempt $attempts/$max_attempts..."
                sleep 3
            fi
        done
        
        print_error "Container health check failed"
        return 1
    else
        print_error "Failed to start container"
        return 1
    fi
}

deploy_docker() {
    print_header "DOCKER DEPLOYMENT"
    
    if [[ "$SKIP_BUILD" != true ]]; then
        build_docker_image || return 1
        push_docker_image || return 1
    fi
    
    stop_docker_container || return 1
    start_docker_container || return 1
    
    return 0
}

# Kubernetes deployment functions
build_and_push_k8s_image() {
    local image_name="$REGISTRY/$SERVICE_NAME:$IMAGE_TAG"
    
    if [[ "$SKIP_BUILD" == true ]]; then
        print_info "Skipping image build"
        return 0
    fi
    
    print_info "Building Docker image..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY-RUN] Would execute: docker build -t $image_name ."
        print_info "[DRY-RUN] Would execute: docker push $image_name"
        return 0
    fi
    
    if docker build -t "$image_name" .; then
        print_success "Image built: $image_name"
    else
        print_error "Docker build failed"
        return 1
    fi
    
    print_info "Pushing image to registry..."
    
    if docker push "$image_name"; then
        print_success "Image pushed: $image_name"
        return 0
    else
        print_error "Docker push failed"
        return 1
    fi
}

patch_k8s_deployment() {
    local image_name="$REGISTRY/$SERVICE_NAME:$IMAGE_TAG"
    
    print_info "Patching Kubernetes deployment..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY-RUN] Would execute:"
        print_info "  kubectl set image deployment/$SERVICE_NAME"
        print_info "  $SERVICE_NAME=$image_name -n $NAMESPACE"
        return 0
    fi
    
    if kubectl set image "deployment/$SERVICE_NAME" \
        "$SERVICE_NAME=$image_name" \
        -n "$NAMESPACE"; then
        print_success "Deployment patched"
        return 0
    else
        print_error "Failed to patch deployment"
        return 1
    fi
}

wait_k8s_rollout() {
    print_info "Waiting for rollout to complete (timeout: ${TIMEOUT}s)..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY-RUN] Would wait for rollout"
        return 0
    fi
    
    if kubectl rollout status "deployment/$SERVICE_NAME" \
        -n "$NAMESPACE" \
        --timeout="${TIMEOUT}s"; then
        print_success "Rollout completed successfully"
        return 0
    else
        print_error "Rollout failed"
        return 1
    fi
}

rollback_k8s_deployment() {
    if [[ "$ROLLBACK_ON_FAILURE" != true ]]; then
        return 0
    fi
    
    print_warning "Rolling back deployment..."
    
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY-RUN] Would execute: kubectl rollout undo deployment/$SERVICE_NAME -n $NAMESPACE"
        return 0
    fi
    
    if kubectl rollout undo "deployment/$SERVICE_NAME" -n "$NAMESPACE"; then
        print_success "Rollback completed"
        return 0
    else
        print_error "Rollback failed"
        return 1
    fi
}

deploy_k8s() {
    print_header "KUBERNETES DEPLOYMENT"
    echo "Namespace: $NAMESPACE"
    echo "Deployment: $SERVICE_NAME"
    echo "Image: $REGISTRY/$SERVICE_NAME:$IMAGE_TAG"
    
    # Check if deployment exists
    if [[ "$DRY_RUN" != true ]]; then
        if ! kubectl get deployment "$SERVICE_NAME" -n "$NAMESPACE" > /dev/null 2>&1; then
            print_error "Deployment '$SERVICE_NAME' not found in namespace '$NAMESPACE'"
            print_info "Please create the deployment first"
            return 1
        fi
    fi
    
    build_and_push_k8s_image || return 1
    patch_k8s_deployment || return 1
    
    if ! wait_k8s_rollout; then
        rollback_k8s_deployment
        return 1
    fi
    
    return 0
}

# Main execution
main() {
    # Validate model
    if ! validate_mlflow_model; then
        print_error "Model validation failed"
        exit 1
    fi
    
    print_info ""
    
    # Execute deployment
    if [[ "$DEPLOYMENT_TYPE" == "docker" ]]; then
        if deploy_docker; then
            print_header "✓ DEPLOYMENT SUCCESSFUL"
            echo "Model: $MODEL_NAME"
            echo "Stage: $MODEL_STAGE"
            echo "Deployment: $DEPLOYMENT_TYPE"
            exit 0
        else
            print_error "Deployment failed"
            exit 1
        fi
    elif [[ "$DEPLOYMENT_TYPE" == "k8s" ]]; then
        if deploy_k8s; then
            print_header "✓ DEPLOYMENT SUCCESSFUL"
            echo "Model: $MODEL_NAME"
            echo "Stage: $MODEL_STAGE"
            echo "Deployment: $DEPLOYMENT_TYPE"
            exit 0
        else
            print_error "Deployment failed"
            exit 1
        fi
    fi
}

# Execute main
main
