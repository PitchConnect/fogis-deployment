#!/bin/bash

# FOGIS Containerized System - Complete Setup Script
# This script sets up the entire FOGIS system from scratch

set -e  # Exit on any error

echo "🚀 FOGIS CONTAINERIZED SYSTEM SETUP"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    if ! command -v git &> /dev/null; then
        log_error "Git is not installed. Please install Git first."
        exit 1
    fi

    log_success "All prerequisites are installed"
}

# Clean up existing setup
cleanup_existing() {
    log_info "Cleaning up existing setup..."

    # Stop and remove containers
    if docker-compose -f docker-compose-master.yml ps -q 2>/dev/null | grep -q .; then
        log_info "Stopping existing containers..."
        docker-compose -f docker-compose-master.yml down --remove-orphans || true
    fi

    # Remove existing repositories
    for repo in fogis-api-client-python team-logo-combiner match-list-processor match-list-change-detector fogis-calendar-phonebook-sync google-drive-service; do
        if [ -d "$repo" ]; then
            log_info "Removing existing $repo directory..."
            rm -rf "$repo"
        fi
    done

    # Clean up data directories
    if [ -d "data" ]; then
        log_warning "Removing existing data directory..."
        rm -rf data
    fi

    # Clean up logs
    if [ -d "logs" ]; then
        log_info "Removing existing logs..."
        rm -rf logs
    fi

    log_success "Cleanup completed"
}

# Clone all repositories
clone_repositories() {
    log_info "Cloning all required repositories..."

    local repos=(
        "https://github.com/PitchConnect/fogis-api-client-python.git"
        "https://github.com/PitchConnect/team-logo-combiner.git"
        "https://github.com/PitchConnect/match-list-processor.git"
        "https://github.com/PitchConnect/match-list-change-detector.git"
        "https://github.com/PitchConnect/fogis-calendar-phonebook-sync.git"
        "https://github.com/PitchConnect/google-drive-service.git"
    )

    for repo in "${repos[@]}"; do
        local repo_name=$(basename "$repo" .git)
        log_info "Cloning $repo_name..."
        git clone "$repo" || {
            log_error "Failed to clone $repo"
            exit 1
        }
    done

    log_success "All repositories cloned successfully"
}

# Apply critical fixes
apply_fixes() {
    log_info "Applying critical deployment fixes..."

    if [ -f "./apply_deployment_fixes.sh" ]; then
        ./apply_deployment_fixes.sh
        log_success "Critical fixes applied successfully"
    else
        log_warning "apply_deployment_fixes.sh not found, skipping fixes"
    fi
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."

    # Build FOGIS API Client (core service)
    log_info "Building fogis-api-client..."
    docker build -t fogis-api-client:latest ./fogis-api-client-python/

    # Build team-logo-combiner (needs Dockerfile fix)
    log_info "Building team-logo-combiner..."
    docker build -t team-logo-combiner:latest ./team-logo-combiner/

    # Build other services
    local services=("match-list-processor" "match-list-change-detector" "fogis-calendar-phonebook-sync" "google-drive-service")

    for service in "${services[@]}"; do
        if [ -f "$service/Dockerfile" ]; then
            log_info "Building $service..."
            docker build -t "$service:latest" "./$service/"
        else
            log_warning "$service/Dockerfile not found, skipping..."
        fi
    done

    log_success "All Docker images built successfully"
}

# Create directory structure
create_directories() {
    log_info "Creating directory structure..."

    # Create data directories
    mkdir -p data/{fogis-api-client,match-list-change-detector,match-list-processor,fogis-calendar-phonebook-sync,team-logo-combiner,google-drive-service}

    # Create logs directories
    mkdir -p logs/{fogis-api-client,match-list-change-detector,match-list-processor,fogis-calendar-phonebook-sync,team-logo-combiner,google-drive-service}

    # Create credentials directory
    mkdir -p credentials

    log_success "Directory structure created"
}

# Setup credentials
setup_credentials() {
    log_info "Setting up credentials..."

    if [ ! -f "credentials.json" ]; then
        log_warning "Google credentials.json not found!"
        echo ""
        echo "📋 REQUIRED: Google Cloud Credentials"
        echo "1. Go to Google Cloud Console"
        echo "2. Create OAuth 2.0 credentials"
        echo "3. Download as 'credentials.json'"
        echo "4. Place it in this directory"
        echo ""
        read -p "Press Enter when credentials.json is ready..."

        if [ ! -f "credentials.json" ]; then
            log_error "credentials.json still not found. Exiting."
            exit 1
        fi
    fi

    # Copy credentials to services
    cp credentials.json credentials/google-credentials.json

    log_success "Credentials setup completed"
}

# Start services
start_services() {
    log_info "Starting FOGIS services..."

    # Start core services first
    docker-compose -f docker-compose-master.yml up -d fogis-api-client-service
    sleep 10

    # Start processing services
    docker-compose -f docker-compose-master.yml up -d match-list-processor team-logo-combiner google-drive-service
    sleep 15

    # Start sync services
    docker-compose -f docker-compose-master.yml up -d fogis-calendar-phonebook-sync
    sleep 10

    # Start change detector and scheduler
    docker-compose -f docker-compose-master.yml up -d match-list-change-detector cron-scheduler

    log_success "All services started"
}

# Check service health
check_service_health() {
    log_info "Checking service health..."

    local services=(
        "fogis-api-client-service:9086"
        "match-list-change-detector:9082"
        "match-list-processor:9081"
        "team-logo-combiner:9088"
        "google-drive-service:9085"
        "fogis-calendar-phonebook-sync:9083"
    )

    for service_port in "${services[@]}"; do
        local service=$(echo "$service_port" | cut -d: -f1)
        local port=$(echo "$service_port" | cut -d: -f2)

        log_info "Checking $service on port $port..."

        for i in {1..30}; do
            if curl -f "http://localhost:$port/health" &>/dev/null; then
                log_success "$service is healthy"
                break
            fi

            if [ $i -eq 30 ]; then
                log_warning "$service health check failed after 30 attempts"
            else
                sleep 2
            fi
        done
    done
}

# Main execution
main() {
    echo "This script will:"
    echo "1. 🧹 Clean up any existing setup"
    echo "2. 📦 Clone all required repositories"
    echo "3. 🔧 Apply critical deployment fixes"
    echo "4. 🏗️  Build all Docker images"
    echo "5. 📁 Create directory structure"
    echo "6. 🔐 Setup credentials"
    echo "7. 🚀 Start all services"
    echo "8. 🏥 Check service health"
    echo ""

    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Setup cancelled"
        exit 0
    fi

    check_prerequisites
    cleanup_existing
    clone_repositories
    apply_fixes
    build_images
    create_directories
    setup_credentials
    start_services
    check_service_health

    echo ""
    echo "🎉 FOGIS SYSTEM SETUP COMPLETE!"
    echo ""
    echo "📋 NEXT STEPS:"
    echo "1. Run authentication: python authenticate_all_services.py"
    echo "2. Check service status: docker-compose -f docker-compose-master.yml ps"
    echo "3. View logs: docker-compose -f docker-compose-master.yml logs -f"
    echo ""
    echo "🔧 CRITICAL FIXES APPLIED:"
    echo "✅ team-logo-combiner Dockerfile dependencies"
    echo "✅ google-drive-service environment variables"
    echo "✅ fogis-calendar-phonebook-sync configuration"
    echo "✅ fogis-api-client version dependencies (0.0.5 → 0.5.1)"
    echo "✅ All Docker images built with latest fixes"    echo ""
    echo "🌐 Service URLs:"
    echo "- FOGIS API Client: http://localhost:9086/health"
    echo "- Match Change Detector: http://localhost:9082/health"
    echo "- Match Processor: http://localhost:9081/health"
    echo "- Avatar Service: http://localhost:9088/health"
    echo "- Google Drive: http://localhost:9085/health"
    echo "- Calendar Sync: http://localhost:9083/health"
    echo ""
}

# Run main function
main "$@"
