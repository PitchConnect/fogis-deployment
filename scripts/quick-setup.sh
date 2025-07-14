#!/bin/bash
# FOGIS Quick Setup Script
# Lightning-fast deployment targeting 5-10 minute setup times
#
# This script provides rapid deployment for FOGIS systems with:
# - Automated dependency installation
# - Pre-configured templates and defaults
# - Parallel service initialization
# - Optimized Docker image pulling
# - Streamlined OAuth setup

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/quick-setup.log"
SETUP_START_TIME=$(date +%s)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌ $1${NC}" | tee -a "$LOG_FILE"
}

# Progress tracking
show_progress() {
    local current=$1
    local total=$2
    local description=$3
    local percent=$((current * 100 / total))
    local bar_length=50
    local filled_length=$((percent * bar_length / 100))

    printf "\r${BLUE}Progress: ["
    printf "%*s" $filled_length | tr ' ' '='
    printf "%*s" $((bar_length - filled_length)) | tr ' ' '-'
    printf "] %d%% - %s${NC}" $percent "$description"

    if [ $current -eq $total ]; then
        echo ""
    fi
}

# Error handling
cleanup_on_error() {
    log_error "Setup failed. Cleaning up..."
    # Stop any running containers
    docker compose down --remove-orphans 2>/dev/null || true
    exit 1
}

trap cleanup_on_error ERR

# Main setup function
main() {
    echo "🚀 FOGIS Quick Setup - Lightning Fast Deployment"
    echo "================================================"
    echo "Target: 5-10 minute deployment time"
    echo ""

    # Create logs directory
    mkdir -p "$PROJECT_ROOT/logs"

    # Initialize log file
    echo "FOGIS Quick Setup Log - $(date)" > "$LOG_FILE"

    # Setup steps
    local total_steps=12
    local current_step=0

    # Step 1: System requirements check
    ((current_step++))
    show_progress $current_step $total_steps "Checking system requirements"
    check_system_requirements

    # Step 2: Install dependencies (parallel where possible)
    ((current_step++))
    show_progress $current_step $total_steps "Installing dependencies"
    install_dependencies

    # Step 3: Setup Docker environment
    ((current_step++))
    show_progress $current_step $total_steps "Setting up Docker environment"
    setup_docker_environment

    # Step 4: Pre-pull Docker images (parallel)
    ((current_step++))
    show_progress $current_step $total_steps "Pre-pulling Docker images"
    prepull_docker_images

    # Step 5: Initialize configuration
    ((current_step++))
    show_progress $current_step $total_steps "Initializing configuration"
    initialize_configuration

    # Step 6: Quick OAuth setup (if credentials provided)
    ((current_step++))
    show_progress $current_step $total_steps "Setting up OAuth authentication"
    setup_oauth_quick

    # Step 7: Generate configuration files
    ((current_step++))
    show_progress $current_step $total_steps "Generating configuration files"
    generate_configurations

    # Step 8: Start core services
    ((current_step++))
    show_progress $current_step $total_steps "Starting core services"
    start_core_services

    # Step 9: Health check and validation
    ((current_step++))
    show_progress $current_step $total_steps "Running health checks"
    run_health_checks

    # Step 10: Setup monitoring
    ((current_step++))
    show_progress $current_step $total_steps "Setting up monitoring"
    setup_monitoring

    # Step 11: Create initial backup
    ((current_step++))
    show_progress $current_step $total_steps "Creating initial backup"
    create_initial_backup

    # Step 12: Final validation
    ((current_step++))
    show_progress $current_step $total_steps "Final validation"
    final_validation

    # Calculate setup time
    local setup_end_time=$(date +%s)
    local setup_duration=$((setup_end_time - SETUP_START_TIME))
    local setup_minutes=$((setup_duration / 60))
    local setup_seconds=$((setup_duration % 60))

    echo ""
    echo "🎉 FOGIS Quick Setup Completed Successfully!"
    echo "=============================================="
    echo "Setup time: ${setup_minutes}m ${setup_seconds}s"
    echo ""

    if [ $setup_duration -le 600 ]; then  # 10 minutes
        log_success "✅ Target deployment time achieved (≤10 minutes)"
    else
        log_warning "⚠️  Setup took longer than target (>10 minutes)"
    fi

    show_next_steps
}

check_system_requirements() {
    log "Checking system requirements..."

    # Check OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        log "Detected macOS"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log "Detected Linux"
    else
        log_warning "Unsupported OS: $OSTYPE"
    fi

    # Check required commands
    local required_commands=("docker" "python3" "git" "curl")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command not found: $cmd"
            exit 1
        fi
    done

    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    # Check available disk space (minimum 5GB)
    local available_space=$(df . | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5242880 ]; then  # 5GB in KB
        log_warning "Low disk space. Minimum 5GB recommended."
    fi

    log_success "System requirements check passed"
}

install_dependencies() {
    log "Installing Python dependencies..."

    # Create virtual environment if it doesn't exist
    if [ ! -d "$PROJECT_ROOT/venv" ]; then
        python3 -m venv "$PROJECT_ROOT/venv"
    fi

    # Activate virtual environment
    source "$PROJECT_ROOT/venv/bin/activate"

    # Install requirements
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        pip install -r "$PROJECT_ROOT/requirements.txt" --quiet
    fi

    # Install additional monitoring dependencies
    pip install psutil requests --quiet

    log_success "Dependencies installed"
}

setup_docker_environment() {
    log "Setting up Docker environment..."

    # Ensure Docker Compose is available
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose not available"
        exit 1
    fi

    # Create Docker networks if they don't exist
    docker network create fogis-network 2>/dev/null || true

    # Set up Docker Compose override for quick setup
    cat > "$PROJECT_ROOT/docker-compose.quick.yml" << 'EOF'
version: '3.8'
services:
  # Quick setup optimizations
  calendar-sync:
    restart: unless-stopped
    healthcheck:
      interval: 10s
      timeout: 5s
      retries: 3

  google-drive:
    restart: unless-stopped
    healthcheck:
      interval: 10s
      timeout: 5s
      retries: 3

networks:
  default:
    external:
      name: fogis-network
EOF

    log_success "Docker environment configured"
}

prepull_docker_images() {
    log "Pre-pulling Docker images (parallel)..."

    # List of images to pre-pull
    local images=(
        "ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest"
        "ghcr.io/pitchconnect/google-drive-service:latest"
        "ghcr.io/pitchconnect/match-list-processor:latest"
        "ghcr.io/pitchconnect/team-logo-combiner:latest"
        "ghcr.io/pitchconnect/whatsapp-avatar-automation:latest"
        "ghcr.io/pitchconnect/match-list-change-detector:latest"
    )

    # Pull images in parallel
    for image in "${images[@]}"; do
        {
            docker pull "$image" &> /dev/null && log "Pulled $image"
        } &
    done

    # Wait for all pulls to complete
    wait

    log_success "Docker images pre-pulled"
}

initialize_configuration() {
    log "Initializing configuration..."

    cd "$PROJECT_ROOT"

    # Initialize portable configuration if it doesn't exist
    if [ ! -f "fogis-config.yaml" ]; then
        ./manage_fogis_system.sh config-init --quick
    fi

    log_success "Configuration initialized"
}

setup_oauth_quick() {
    log "Setting up OAuth authentication..."

    # Check if credentials.json exists
    if [ -f "$PROJECT_ROOT/credentials.json" ]; then
        log "Found existing OAuth credentials"

        # Quick OAuth validation
        if python3 -c "
import json
try:
    with open('credentials.json', 'r') as f:
        creds = json.load(f)
    if 'web' in creds or 'installed' in creds:
        print('valid')
    else:
        print('invalid')
except:
    print('invalid')
" | grep -q "valid"; then
            log_success "OAuth credentials validated"
        else
            log_warning "OAuth credentials appear invalid"
        fi
    else
        log_warning "No OAuth credentials found. Manual setup required."
        echo "  To complete OAuth setup later, run:"
        echo "  ./manage_fogis_system.sh setup-oauth"
    fi
}

generate_configurations() {
    log "Generating configuration files..."

    cd "$PROJECT_ROOT"

    # Generate all configuration files
    ./manage_fogis_system.sh config-generate --quiet

    log_success "Configuration files generated"
}

start_core_services() {
    log "Starting core services..."

    cd "$PROJECT_ROOT"

    # Start services with quick setup optimizations
    docker compose -f docker-compose.yml -f docker-compose.quick.yml up -d

    # Wait for services to be ready (with timeout)
    local timeout=120  # 2 minutes
    local elapsed=0
    local interval=5

    while [ $elapsed -lt $timeout ]; do
        if docker compose ps | grep -q "Up"; then
            log_success "Core services started"
            return 0
        fi
        sleep $interval
        elapsed=$((elapsed + interval))
    done

    log_warning "Services took longer than expected to start"
}

run_health_checks() {
    log "Running health checks..."

    cd "$PROJECT_ROOT"

    # Run quick health check
    if python3 lib/monitoring_setup.py health-check > /dev/null 2>&1; then
        log_success "Health checks passed"
    else
        log_warning "Some health checks failed. System may still be starting."
    fi
}

setup_monitoring() {
    log "Setting up monitoring..."

    cd "$PROJECT_ROOT"

    # Initialize monitoring
    python3 lib/monitoring_setup.py setup > /dev/null 2>&1

    log_success "Monitoring configured"
}

create_initial_backup() {
    log "Creating initial backup..."

    cd "$PROJECT_ROOT"

    # Create initial configuration backup
    python3 lib/backup_manager.py create config > /dev/null 2>&1

    log_success "Initial backup created"
}

final_validation() {
    log "Running final validation..."

    cd "$PROJECT_ROOT"

    # Validate configuration
    if ./manage_fogis_system.sh config-validate --quiet; then
        log_success "Configuration validation passed"
    else
        log_warning "Configuration validation issues detected"
    fi

    # Check service availability
    local healthy_services=0
    local total_services=6

    for port in 8080 8081 8082 8083 8084 8085; do
        if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
            ((healthy_services++))
        fi
    done

    if [ $healthy_services -eq $total_services ]; then
        log_success "All services are healthy"
    else
        log_warning "$healthy_services/$total_services services are healthy"
    fi
}

show_next_steps() {
    echo "🎯 Next Steps:"
    echo "=============="
    echo "1. Access FOGIS services:"
    echo "   • Calendar Sync: http://localhost:8080"
    echo "   • Google Drive: http://localhost:8081"
    echo "   • Match List Processor: http://localhost:8082"
    echo ""
    echo "2. Complete OAuth setup (if not done):"
    echo "   ./manage_fogis_system.sh setup-oauth"
    echo ""
    echo "3. Monitor system health:"
    echo "   ./manage_fogis_system.sh health-check"
    echo ""
    echo "4. View logs:"
    echo "   tail -f logs/quick-setup.log"
    echo ""
    echo "5. Create backups:"
    echo "   ./manage_fogis_system.sh backup-create"
    echo ""
    echo "📚 Documentation: docs/QUICK_START.md"
    echo "🆘 Support: https://github.com/PitchConnect/fogis-deployment/issues"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
