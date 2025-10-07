#!/bin/bash

# ARM64 Deployment Verification Script
# This script verifies that ARM64 images are available and deployment is ready

set -e

echo "=========================================="
echo "ARM64 Deployment Verification"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if running on ARM64
check_architecture() {
    echo "1. Checking system architecture..."
    ARCH=$(uname -m)
    echo "   System architecture: $ARCH"

    if [[ "$ARCH" == "arm64" ]] || [[ "$ARCH" == "aarch64" ]]; then
        echo -e "   ${GREEN}✓ Running on ARM64 system${NC}"
        return 0
    else
        echo -e "   ${YELLOW}⚠ Running on $ARCH system (not ARM64)${NC}"
        echo "   Note: ARM64 images will still be pulled if available"
        return 1
    fi
    echo ""
}

# Function to check Docker version
check_docker() {
    echo ""
    echo "2. Checking Docker installation..."

    if ! command -v docker &> /dev/null; then
        echo -e "   ${RED}✗ Docker not found${NC}"
        echo "   Please install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi

    DOCKER_VERSION=$(docker --version)
    echo "   $DOCKER_VERSION"
    echo -e "   ${GREEN}✓ Docker installed${NC}"
}

# Function to check Docker Compose
check_docker_compose() {
    echo ""
    echo "3. Checking Docker Compose..."

    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version)
        echo "   $COMPOSE_VERSION"
        echo -e "   ${GREEN}✓ Docker Compose v2 available${NC}"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version)
        echo "   $COMPOSE_VERSION"
        echo -e "   ${YELLOW}⚠ Using Docker Compose v1 (consider upgrading to v2)${NC}"
    else
        echo -e "   ${RED}✗ Docker Compose not found${NC}"
        echo "   Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
}

# Function to check image manifest for ARM64 support
check_image_manifest() {
    local image=$1
    local service_name=$2

    echo "   Checking $service_name..."

    # Try to inspect the manifest
    if docker manifest inspect "$image" &> /dev/null; then
        # Check if ARM64 is in the manifest
        if docker manifest inspect "$image" | grep -q "arm64\|aarch64"; then
            echo -e "   ${GREEN}✓ $service_name: ARM64 image available${NC}"
            return 0
        else
            echo -e "   ${YELLOW}⚠ $service_name: AMD64 only (will run via emulation on ARM64)${NC}"
            return 1
        fi
    else
        echo -e "   ${YELLOW}⚠ $service_name: Cannot inspect manifest (may need authentication)${NC}"
        return 2
    fi
}

# Function to check all service images
check_service_images() {
    echo ""
    echo "4. Checking service image availability..."

    local arm64_count=0
    local total_count=0

    # List of services from docker-compose.yml
    declare -A services=(
        ["fogis-api-client-python"]="ghcr.io/pitchconnect/fogis-api-client-python:latest"
        ["match-list-processor"]="ghcr.io/pitchconnect/match-list-processor:latest"
        ["fogis-calendar-phonebook-sync"]="ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest"
        ["team-logo-combiner"]="ghcr.io/pitchconnect/team-logo-combiner:latest"
        ["google-drive-service"]="ghcr.io/pitchconnect/google-drive-service:latest"
    )

    for service in "${!services[@]}"; do
        image="${services[$service]}"
        ((total_count++))

        if check_image_manifest "$image" "$service"; then
            ((arm64_count++))
        fi
    done

    echo ""
    echo "   Summary: $arm64_count/$total_count services have ARM64 images"

    if [ $arm64_count -eq $total_count ]; then
        echo -e "   ${GREEN}✓ All services support ARM64${NC}"
    elif [ $arm64_count -gt 0 ]; then
        echo -e "   ${YELLOW}⚠ Some services will run via emulation${NC}"
    else
        echo -e "   ${YELLOW}⚠ Could not verify ARM64 support (may need GHCR authentication)${NC}"
    fi
}

# Function to check GHCR authentication
check_ghcr_auth() {
    echo ""
    echo "5. Checking GitHub Container Registry authentication..."

    # Try to pull a small manifest to test auth
    if docker manifest inspect ghcr.io/pitchconnect/fogis-api-client-python:latest &> /dev/null; then
        echo -e "   ${GREEN}✓ Authenticated to GHCR${NC}"
        return 0
    else
        echo -e "   ${YELLOW}⚠ Not authenticated to GHCR${NC}"
        echo "   To authenticate, run:"
        echo "   docker login ghcr.io -u YOUR_GITHUB_USERNAME"
        echo ""
        echo "   Note: Public images can be pulled without authentication"
        return 1
    fi
}

# Function to verify docker-compose.yml
check_compose_file() {
    echo ""
    echo "6. Verifying docker-compose.yml..."

    if [ ! -f "docker-compose.yml" ]; then
        echo -e "   ${RED}✗ docker-compose.yml not found${NC}"
        echo "   Please run this script from the fogis-deployment directory"
        exit 1
    fi

    echo -e "   ${GREEN}✓ docker-compose.yml found${NC}"

    # Check if using :latest tags
    if grep -q ":latest" docker-compose.yml; then
        echo -e "   ${GREEN}✓ Using :latest tags (will pull ARM64 automatically)${NC}"
    else
        echo -e "   ${YELLOW}⚠ Not using :latest tags (may need manual update)${NC}"
    fi
}

# Function to show deployment commands
show_deployment_commands() {
    echo ""
    echo "=========================================="
    echo "Deployment Commands"
    echo "=========================================="
    echo ""
    echo "To deploy the FOGIS system with ARM64 support:"
    echo ""
    echo "1. Pull latest images:"
    echo "   docker-compose pull"
    echo ""
    echo "2. Start services:"
    echo "   docker-compose up -d"
    echo ""
    echo "3. Verify services are running:"
    echo "   docker-compose ps"
    echo ""
    echo "4. Check service architecture:"
    echo "   docker inspect fogis-api-client-service | grep Architecture"
    echo "   docker inspect process-matches-service | grep Architecture"
    echo "   docker inspect fogis-calendar-phonebook-sync | grep Architecture"
    echo ""
    echo "5. View logs:"
    echo "   docker-compose logs -f"
    echo ""
    echo "For more information, see ARM64_DEPLOYMENT_STATUS.md"
    echo ""
}

# Main execution
main() {
    check_architecture
    check_docker
    check_docker_compose
    check_ghcr_auth
    check_compose_file
    check_service_images

    echo ""
    echo "=========================================="
    echo "Verification Complete"
    echo "=========================================="
    echo ""

    show_deployment_commands
}

# Run main function
main
