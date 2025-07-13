#!/bin/bash

# FOGIS Containerized System - Complete Auto-Setup Script
# This script handles EVERYTHING needed for FOGIS deployment with zero user configuration required
# Implements GitHub Issue #1: One-Click Setup Script - Complete Auto-Configuration

set -e  # Exit on any error

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTO_MODE=false
VERBOSE_MODE=false
QUIET_MODE=false
RESUME_MODE=false
ROLLBACK_MODE=false
PROGRESS_FILE="$SCRIPT_DIR/.setup_progress"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --auto)
            AUTO_MODE=true
            shift
            ;;
        --verbose)
            VERBOSE_MODE=true
            shift
            ;;
        --quiet)
            QUIET_MODE=true
            shift
            ;;
        --resume)
            RESUME_MODE=true
            shift
            ;;
        --rollback)
            ROLLBACK_MODE=true
            shift
            ;;
        --help)
            # show_usage will be called later after function is defined
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🚀 FOGIS ONE-CLICK SETUP SYSTEM"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    if [[ "$QUIET_MODE" != "true" ]]; then
        echo -e "${BLUE}ℹ️  $1${NC}"
    fi
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

log_progress() {
    echo -e "${PURPLE}🔄 $1${NC}"
}

log_step() {
    echo -e "${CYAN}📋 Step $1${NC}"
}

# Progress tracking functions
save_progress() {
    echo "$1" > "$PROGRESS_FILE"
    if [[ "$VERBOSE_MODE" == "true" ]]; then
        log_info "Progress saved: $1"
    fi
}

get_progress() {
    if [[ -f "$PROGRESS_FILE" ]]; then
        cat "$PROGRESS_FILE"
    else
        echo "start"
    fi
}

clear_progress() {
    rm -f "$PROGRESS_FILE"
}

# Usage function
show_usage() {
    echo "🔧 FOGIS One-Click Setup System"
    echo "==============================="
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --auto      Fully automated setup (no prompts)"
    echo "  --verbose   Enable verbose output"
    echo "  --quiet     Minimal output mode"
    echo "  --resume    Resume from last checkpoint"
    echo "  --rollback  Rollback changes and cleanup"
    echo "  --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --auto              # Fully automated setup"
    echo "  $0 --auto --verbose    # Automated with detailed output"
    echo "  $0 --resume            # Resume interrupted setup"
    echo "  $0 --rollback          # Cleanup and rollback"
    echo ""
    echo "Features:"
    echo "  ✅ Auto-detect and install Docker if missing"
    echo "  ✅ Auto-clone all required repositories"
    echo "  ✅ Build Docker images with progress indicators"
    echo "  ✅ Interactive credential setup wizard"
    echo "  ✅ Health checks with automatic retry/fix"
    echo "  ✅ Configure cron jobs automatically"
    echo "  ✅ Resume capability for interrupted setups"
    echo "  ✅ Rollback capability for failed setups"
}

# Enhanced prerequisite checking with auto-installation
check_prerequisites() {
    log_step "1/8: Checking Prerequisites"

    # Use the multi-platform installation system
    if [[ -f "../install-fogis.py" ]]; then
        log_info "Using multi-platform installation system..."

        if [[ "$AUTO_MODE" == "true" ]]; then
            log_progress "Auto-installing missing prerequisites..."
            if python3 ../install-fogis.py --install-prereqs --verbose; then
                log_success "Prerequisites installed successfully"
                save_progress "prerequisites_checked"
                return 0
            else
                log_error "Failed to install prerequisites automatically"
                if [[ "$AUTO_MODE" != "true" ]]; then
                    echo ""
                    read -p "Continue with manual prerequisite checking? (y/N): " -n 1 -r
                    echo
                    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                        exit 1
                    fi
                else
                    exit 1
                fi
            fi
        else
            # Interactive mode - show status and offer to install
            python3 ../install-fogis.py --verbose
            echo ""
            read -p "Install missing prerequisites automatically? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                python3 ../install-fogis.py --install-prereqs --verbose
            fi
        fi
    fi

    # Fallback to manual checking
    log_info "Performing manual prerequisite verification..."

    local missing_prereqs=()

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_warning "Docker is not installed"
        missing_prereqs+=("docker")
    else
        log_success "Docker is installed"
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_warning "Docker Compose is not installed"
        missing_prereqs+=("docker-compose")
    else
        log_success "Docker Compose is installed"
    fi

    # Check Git
    if ! command -v git &> /dev/null; then
        log_warning "Git is not installed"
        missing_prereqs+=("git")
    else
        log_success "Git is installed"
    fi

    # Check Python3
    if ! command -v python3 &> /dev/null; then
        log_warning "Python3 is not installed"
        missing_prereqs+=("python3")
    else
        log_success "Python3 is installed"
    fi

    if [[ ${#missing_prereqs[@]} -gt 0 ]]; then
        log_error "Missing prerequisites: ${missing_prereqs[*]}"
        echo ""
        echo "📋 Installation Instructions:"
        echo ""

        # Detect platform and provide specific instructions
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "macOS detected. Install missing prerequisites with:"
            for prereq in "${missing_prereqs[@]}"; do
                case $prereq in
                    docker)
                        echo "  • Docker: Download from https://docker.com/products/docker-desktop"
                        ;;
                    git)
                        echo "  • Git: brew install git"
                        ;;
                    python3)
                        echo "  • Python3: brew install python@3.11"
                        ;;
                esac
            done
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo "Linux detected. Install missing prerequisites with:"
            for prereq in "${missing_prereqs[@]}"; do
                case $prereq in
                    docker)
                        echo "  • Docker: sudo apt install docker.io (Ubuntu/Debian)"
                        echo "           sudo yum install docker (CentOS/RHEL)"
                        ;;
                    git)
                        echo "  • Git: sudo apt install git (Ubuntu/Debian)"
                        echo "        sudo yum install git (CentOS/RHEL)"
                        ;;
                    python3)
                        echo "  • Python3: sudo apt install python3 (Ubuntu/Debian)"
                        echo "            sudo yum install python3 (CentOS/RHEL)"
                        ;;
                esac
            done
        fi

        if [[ "$AUTO_MODE" == "true" ]]; then
            log_error "Auto-mode enabled but prerequisites missing. Cannot continue."
            exit 1
        else
            echo ""
            read -p "Install prerequisites and press Enter to continue, or Ctrl+C to exit..."
            # Re-run the check
            check_prerequisites
            return
        fi
    fi

    log_success "All prerequisites are satisfied"
    save_progress "prerequisites_checked"
}

# Auto-detect and install Docker if needed
auto_install_docker() {
    log_step "2/8: Docker Installation Check"

    if command -v docker &> /dev/null; then
        log_success "Docker is already installed"

        # Check if Docker is running
        if ! docker info &> /dev/null; then
            log_warning "Docker is installed but not running"

            if [[ "$OSTYPE" == "darwin"* ]]; then
                log_info "Starting Docker Desktop..."
                open -a Docker

                # Wait for Docker to start
                log_progress "Waiting for Docker to start..."
                for i in {1..30}; do
                    if docker info &> /dev/null; then
                        log_success "Docker is now running"
                        break
                    fi
                    sleep 2
                    if [[ $i -eq 30 ]]; then
                        log_error "Docker failed to start after 60 seconds"
                        if [[ "$AUTO_MODE" != "true" ]]; then
                            echo ""
                            echo "Please start Docker Desktop manually and press Enter to continue..."
                            read
                        else
                            exit 1
                        fi
                    fi
                done
            elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
                log_info "Starting Docker service..."
                if sudo systemctl start docker; then
                    log_success "Docker service started"
                else
                    log_error "Failed to start Docker service"
                    exit 1
                fi
            fi
        else
            log_success "Docker is running"
        fi

        save_progress "docker_checked"
        return 0
    fi

    log_warning "Docker is not installed"

    if [[ "$AUTO_MODE" == "true" ]]; then
        log_progress "Auto-installing Docker..."

        if [[ "$OSTYPE" == "darwin"* ]]; then
            log_info "macOS detected - Docker Desktop installation required"
            log_error "Docker Desktop must be installed manually on macOS"
            echo ""
            echo "📋 Please install Docker Desktop:"
            echo "1. Go to https://docker.com/products/docker-desktop"
            echo "2. Download Docker Desktop for Mac"
            echo "3. Install and start Docker Desktop"
            echo "4. Re-run this script"
            exit 1

        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            log_info "Linux detected - installing Docker..."

            # Detect Linux distribution
            if command -v apt &> /dev/null; then
                # Ubuntu/Debian
                log_info "Installing Docker on Ubuntu/Debian..."
                sudo apt update
                sudo apt install -y docker.io
                sudo systemctl enable docker
                sudo systemctl start docker
                sudo usermod -aG docker $USER
                log_success "Docker installed successfully"
                log_warning "Please log out and back in for Docker group membership to take effect"

            elif command -v yum &> /dev/null; then
                # CentOS/RHEL
                log_info "Installing Docker on CentOS/RHEL..."
                sudo yum install -y docker
                sudo systemctl enable docker
                sudo systemctl start docker
                sudo usermod -aG docker $USER
                log_success "Docker installed successfully"
                log_warning "Please log out and back in for Docker group membership to take effect"

            else
                log_error "Unsupported Linux distribution for auto-installation"
                exit 1
            fi
        fi
    else
        echo ""
        echo "📋 Docker Installation Required"
        echo "Docker is required for FOGIS deployment."
        echo ""
        read -p "Install Docker automatically? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            AUTO_MODE=true
            auto_install_docker
            AUTO_MODE=false
        else
            echo ""
            echo "Please install Docker manually and re-run this script."
            exit 1
        fi
    fi

    save_progress "docker_checked"
}

# Clean up existing setup with rollback capability
cleanup_existing() {
    log_step "3/8: Cleanup Existing Setup"

    # Create backup if requested
    if [[ "$ROLLBACK_MODE" == "true" ]]; then
        log_info "Rollback mode - performing complete cleanup..."

        # Stop and remove containers
        if docker-compose -f docker-compose-master.yml ps -q 2>/dev/null | grep -q .; then
            log_info "Stopping and removing containers..."
            docker-compose -f docker-compose-master.yml down --remove-orphans --volumes || true
        fi

        # Remove Docker images
        log_info "Removing FOGIS Docker images..."
        docker images | grep -E "(fogis|team-logo|match-list|google-drive)" | awk '{print $3}' | xargs -r docker rmi -f || true

        # Remove all setup files
        log_info "Removing setup files and directories..."
        rm -rf fogis-api-client-python team-logo-combiner match-list-processor match-list-change-detector fogis-calendar-phonebook-sync google-drive-service
        rm -rf data logs credentials .env
        rm -f "$PROGRESS_FILE"

        log_success "Rollback completed"
        exit 0
    fi

    # Normal cleanup for fresh installation
    log_info "Preparing for fresh installation..."

    # Stop containers gracefully
    if docker-compose -f docker-compose-master.yml ps -q 2>/dev/null | grep -q .; then
        log_info "Stopping existing containers..."
        docker-compose -f docker-compose-master.yml down --remove-orphans || true
    fi

    # Backup existing data if it exists
    if [[ -d "data" && "$AUTO_MODE" != "true" ]]; then
        log_warning "Existing data directory found"
        read -p "Backup existing data? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            backup_dir="data_backup_$(date +%Y%m%d_%H%M%S)"
            log_info "Backing up data to $backup_dir..."
            cp -r data "$backup_dir"
            log_success "Data backed up to $backup_dir"
        fi
    fi

    # Remove existing repositories for fresh clone
    local repos=("fogis-api-client-python" "team-logo-combiner" "match-list-processor" "match-list-change-detector" "fogis-calendar-phonebook-sync" "google-drive-service")

    for repo in "${repos[@]}"; do
        if [[ -d "$repo" ]]; then
            log_info "Removing existing $repo directory..."
            rm -rf "$repo"
        fi
    done

    # Clean up old logs but preserve structure
    if [[ -d "logs" ]]; then
        log_info "Cleaning old logs..."
        find logs -name "*.log" -type f -delete 2>/dev/null || true
    fi

    log_success "Cleanup completed"
    save_progress "cleanup_completed"
}

# Clone all repositories with progress indicators and retry logic
clone_repositories() {
    log_step "4/8: Repository Management"

    local repos=(
        "https://github.com/PitchConnect/fogis-api-client-python.git"
        "https://github.com/PitchConnect/team-logo-combiner.git"
        "https://github.com/PitchConnect/match-list-processor.git"
        "https://github.com/PitchConnect/match-list-change-detector.git"
        "https://github.com/PitchConnect/fogis-calendar-phonebook-sync.git"
        "https://github.com/PitchConnect/google-drive-service.git"
    )

    local total_repos=${#repos[@]}
    local current_repo=0

    log_info "Cloning $total_repos required repositories..."

    for repo in "${repos[@]}"; do
        current_repo=$((current_repo + 1))
        local repo_name=$(basename "$repo" .git)

        log_progress "[$current_repo/$total_repos] Cloning $repo_name..."

        # Check if repository already exists and is valid
        if [[ -d "$repo_name" ]]; then
            log_info "$repo_name already exists, checking validity..."
            if cd "$repo_name" && git status &>/dev/null; then
                log_info "Updating existing $repo_name..."
                git pull origin main || git pull origin master || {
                    log_warning "Failed to update $repo_name, re-cloning..."
                    cd ..
                    rm -rf "$repo_name"
                }
                cd ..
            else
                log_warning "Invalid repository $repo_name, re-cloning..."
                rm -rf "$repo_name"
            fi
        fi

        # Clone if not exists or was removed
        if [[ ! -d "$repo_name" ]]; then
            local retry_count=0
            local max_retries=3

            while [[ $retry_count -lt $max_retries ]]; do
                if [[ $retry_count -gt 0 ]]; then
                    log_warning "Retry $retry_count/$max_retries for $repo_name..."
                    sleep 2
                fi

                if git clone --progress "$repo" 2>&1 | while IFS= read -r line; do
                    if [[ "$VERBOSE_MODE" == "true" ]]; then
                        echo "  $line"
                    elif [[ "$line" =~ [0-9]+% ]]; then
                        echo -ne "\r  Progress: $line"
                    fi
                done; then
                    echo ""  # New line after progress
                    log_success "Successfully cloned $repo_name"
                    break
                else
                    retry_count=$((retry_count + 1))
                    if [[ $retry_count -eq $max_retries ]]; then
                        log_error "Failed to clone $repo after $max_retries attempts"

                        if [[ "$AUTO_MODE" == "true" ]]; then
                            exit 1
                        else
                            echo ""
                            echo "📋 Manual Clone Instructions:"
                            echo "git clone $repo"
                            echo ""
                            read -p "Clone manually and press Enter to continue, or Ctrl+C to exit..."

                            # Verify manual clone
                            if [[ ! -d "$repo_name" ]]; then
                                log_error "Repository $repo_name still not found"
                                exit 1
                            fi
                        fi
                    fi
                fi
            done
        fi

        # Verify repository is valid
        if [[ -d "$repo_name" ]]; then
            if cd "$repo_name" && git status &>/dev/null; then
                log_success "✓ $repo_name is ready"
                cd ..
            else
                log_error "Repository $repo_name is corrupted"
                exit 1
            fi
        else
            log_error "Repository $repo_name not found after cloning"
            exit 1
        fi
    done

    log_success "All repositories are ready"
    save_progress "repositories_cloned"
}

# Apply critical fixes
apply_fixes() {
    log_step "5/8: Applying Critical Fixes"

    log_info "Applying critical deployment fixes..."

    if [[ -f "./apply_deployment_fixes.sh" ]]; then
        log_progress "Running deployment fixes..."
        if ./apply_deployment_fixes.sh; then
            log_success "Critical fixes applied successfully"
        else
            log_warning "Some fixes may have failed, continuing..."
        fi
    else
        log_warning "apply_deployment_fixes.sh not found, skipping fixes"
    fi

    save_progress "fixes_applied"
}

# Build Docker images with progress indicators and GHCR tagging
build_images() {
    log_step "6/8: Building Docker Images"

    # Check if we should use pre-built images or build locally
    if [[ "$AUTO_MODE" == "true" ]]; then
        log_info "Auto-mode: Attempting to use pre-built GHCR images..."

        local ghcr_images=(
            "ghcr.io/pitchconnect/fogis-api-client-service:latest"
            "ghcr.io/pitchconnect/team-logo-combiner:latest"
            "ghcr.io/pitchconnect/match-list-processor:latest"
            "ghcr.io/pitchconnect/match-list-change-detector:latest"
            "ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest"
            "ghcr.io/pitchconnect/google-drive-service:latest"
        )

        local pull_success=true
        for image in "${ghcr_images[@]}"; do
            log_info "Pulling $image..."
            if ! docker pull "$image" 2>/dev/null; then
                log_warning "Failed to pull $image"
                pull_success=false
                break
            fi
        done

        if [[ "$pull_success" == "true" ]]; then
            log_success "All pre-built images pulled successfully"
            save_progress "images_ready"
            return 0
        else
            log_warning "Pre-built images not available, building locally..."
        fi
    fi

    log_info "Building Docker images locally..."

    # Define services with their build contexts and image names
    local services=(
        "fogis-api-client-python:ghcr.io/pitchconnect/fogis-api-client-service:latest"
        "team-logo-combiner:ghcr.io/pitchconnect/team-logo-combiner:latest"
        "match-list-processor:ghcr.io/pitchconnect/match-list-processor:latest"
        "match-list-change-detector:ghcr.io/pitchconnect/match-list-change-detector:latest"
        "fogis-calendar-phonebook-sync:ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest"
        "google-drive-service:ghcr.io/pitchconnect/google-drive-service:latest"
    )

    local total_services=${#services[@]}
    local current_service=0

    for service_info in "${services[@]}"; do
        current_service=$((current_service + 1))
        local build_context=$(echo "$service_info" | cut -d: -f1)
        local image_name=$(echo "$service_info" | cut -d: -f2-)
        local service_name=$(basename "$build_context")

        log_progress "[$current_service/$total_services] Building $service_name..."

        if [[ -f "$build_context/Dockerfile" ]]; then
            # Build with progress output
            if [[ "$VERBOSE_MODE" == "true" ]]; then
                docker build -t "$image_name" "./$build_context/" || {
                    log_error "Failed to build $service_name"
                    exit 1
                }
            else
                # Build with minimal output
                if docker build -t "$image_name" "./$build_context/" > /tmp/build_${service_name}.log 2>&1; then
                    log_success "✓ $service_name built successfully"
                else
                    log_error "Failed to build $service_name"
                    echo "Build log:"
                    cat /tmp/build_${service_name}.log
                    exit 1
                fi
            fi

            # Also tag with legacy names for compatibility
            local legacy_name="${service_name}:latest"
            docker tag "$image_name" "$legacy_name"

        else
            log_warning "$build_context/Dockerfile not found, skipping $service_name..."
        fi
    done

    log_success "All Docker images built successfully"
    save_progress "images_built"
}

# Create directory structure
create_directories() {
    log_step "7/8: Directory Structure Setup"

    log_info "Creating directory structure..."

    # Create data directories
    mkdir -p data/{fogis-api-client,match-list-change-detector,match-list-processor,fogis-calendar-phonebook-sync,team-logo-combiner,google-drive-service}

    # Create logs directories with cron subdirectory
    mkdir -p logs/{fogis-api-client,match-list-change-detector,match-list-processor,fogis-calendar-phonebook-sync,team-logo-combiner,google-drive-service,cron}

    # Create credentials directory
    mkdir -p credentials

    log_success "Directory structure created"
    save_progress "directories_created"
}

# Configuration mode detection and management functions
detect_config_mode() {
    if [[ -f "fogis-config.yaml" ]]; then
        echo "portable"
    elif [[ -f ".env" ]]; then
        echo "legacy"
    else
        echo "new_installation"
    fi
}

validate_portable_config() {
    log_info "Validating portable configuration..."

    if ! python3 lib/config_validator.py; then
        log_error "Configuration validation failed"
        log_info "Please check your fogis-config.yaml file and fix any errors"
        return 1
    fi

    log_success "Configuration validation passed"
    return 0
}

setup_portable_workflow() {
    log_info "Setting up portable configuration workflow..."

    # Validate YAML configuration
    if ! validate_portable_config; then
        return 1
    fi

    # Generate configuration files
    log_info "Generating configuration files from YAML..."
    if ! python3 lib/config_generator.py; then
        log_error "Failed to generate configuration files"
        return 1
    fi

    log_success "Configuration files generated successfully"
    return 0
}

offer_configuration_choice() {
    # Check if there are legacy files that could be migrated
    local has_legacy_files=false
    if [[ -f ".env" ]] || [[ -f "fogis-calendar-phonebook-sync/config.json" ]]; then
        has_legacy_files=true
    fi

    if [[ "$has_legacy_files" == "true" ]]; then
        log_info "Existing configuration detected. Choose setup mode:"
        echo "1. Migrate to Portable Configuration (Recommended)"
        echo "   ✅ Convert existing .env + config.json to portable format"
        echo "   ✅ Automatic backup and rollback capability"
        echo "   ✅ Preserve all current settings"
        echo ""
        echo "2. New Portable Configuration"
        echo "   ⚠️  Start fresh (existing config will be backed up)"
        echo ""
        echo "3. Keep Legacy Configuration"
        echo "   ⚠️  Continue with current .env + config.json approach"
        echo ""

        while true; do
            read -p "Choose setup mode (1/2/3) [1]: " choice
            choice=${choice:-1}

            case $choice in
                1)
                    log_info "Starting configuration migration..."
                    if python3 lib/migration_tool.py migrate; then
                        log_success "Migration completed successfully!"
                        return 0
                    else
                        log_error "Migration failed"
                        log_info "Falling back to new portable configuration..."
                        setup_new_portable_config
                        return $?
                    fi
                    ;;
                2)
                    setup_new_portable_config
                    return $?
                    ;;
                3)
                    log_info "Using legacy configuration mode"
                    return 0
                    ;;
                *)
                    log_error "Invalid choice. Please enter 1, 2, or 3."
                    ;;
            esac
        done
    else
        log_info "New installation detected. Choose configuration mode:"
        echo "1. Portable Configuration (Recommended)"
        echo "   ✅ Single configuration file"
        echo "   ✅ Easy backup and migration"
        echo "   ✅ Infrastructure as Code support"
        echo "   ✅ Enhanced validation"
        echo ""
        echo "2. Legacy Configuration (Current approach)"
        echo "   ⚠️  Multiple configuration files"
        echo "   ⚠️  Manual backup required"
        echo ""

        while true; do
            read -p "Choose configuration mode (1/2) [1]: " choice
            choice=${choice:-1}

            case $choice in
                1)
                    setup_new_portable_config
                    return $?
                    ;;
                2)
                    log_info "Using legacy configuration mode"
                    return 0
                    ;;
                *)
                    log_error "Invalid choice. Please enter 1 or 2."
                    ;;
            esac
        done
    fi
}

setup_new_portable_config() {
    log_info "Setting up portable configuration..."

    # Offer interactive setup wizard
    log_info "Choose setup method:"
    echo "1. Interactive Setup Wizard (Recommended)"
    echo "   ✅ Guided configuration with validation"
    echo "   ✅ Smart defaults and error checking"
    echo "   ✅ Automatic file generation"
    echo ""
    echo "2. Manual Configuration"
    echo "   ⚠️  Copy template and edit manually"
    echo "   ⚠️  Requires manual validation"
    echo ""

    while true; do
        read -p "Choose setup method (1/2) [1]: " choice
        choice=${choice:-1}

        case $choice in
            1)
                log_info "Starting interactive setup wizard..."
                if python3 lib/interactive_setup.py; then
                    log_success "Interactive setup completed successfully!"
                    return 0
                else
                    log_error "Interactive setup failed"
                    log_info "Falling back to manual configuration..."
                    setup_manual_portable_config
                    return $?
                fi
                ;;
            2)
                setup_manual_portable_config
                return $?
                ;;
            *)
                log_error "Invalid choice. Please enter 1 or 2."
                ;;
        esac
    done
}

setup_manual_portable_config() {
    log_info "Setting up manual portable configuration..."

    # Copy template
    if [[ ! -f "templates/fogis-config.template.yaml" ]]; then
        log_error "Configuration template not found: templates/fogis-config.template.yaml"
        return 1
    fi

    cp templates/fogis-config.template.yaml fogis-config.yaml
    log_success "Configuration template copied to fogis-config.yaml"

    log_info "Please edit fogis-config.yaml with your configuration details"
    log_info "Required fields:"
    log_info "  - fogis.username: Your FOGIS login username"
    log_info "  - fogis.password: Your FOGIS login password"
    log_info "  - fogis.referee_number: Your referee number"
    log_info ""
    log_info "After editing, run: ./manage_fogis_system.sh config-generate"

    return 0
}

setup_portable_credentials() {
    log_info "Using portable configuration mode..."

    # Setup portable workflow
    if ! setup_portable_workflow; then
        log_error "Portable configuration setup failed"
        return 1
    fi

    # Continue with existing credential setup logic
    setup_legacy_credentials
    return $?
}

setup_legacy_credentials() {
    # This is the existing setup_credentials function content
    # We'll rename the original function to this
    log_info "Using legacy configuration mode..."
}

# Enhanced credential setup using the existing wizard
setup_credentials() {
    log_step "8/8: Credential Configuration"

    log_info "Setting up authentication credentials..."

    # Detect configuration mode
    local config_mode=$(detect_config_mode)
    log_info "Configuration mode: $config_mode"

    case $config_mode in
        "portable")
            setup_portable_credentials
            return $?
            ;;
        "legacy")
            setup_legacy_credentials
            return $?
            ;;
        "new_installation")
            offer_configuration_choice
            if [[ $? -eq 0 ]]; then
                # After choice, detect mode again and proceed
                local new_mode=$(detect_config_mode)
                if [[ "$new_mode" == "portable" ]]; then
                    setup_portable_credentials
                else
                    setup_legacy_credentials
                fi
            else
                return 1
            fi
            ;;
        *)
            log_error "Unknown configuration mode: $config_mode"
            return 1
            ;;
    esac
}

# Legacy credential setup (original setup_credentials content)
setup_legacy_credentials() {
    log_info "Using legacy configuration mode..."

    # Check if credentials are already configured
    if [[ -f ".env" && -f "credentials/google-credentials.json" ]]; then
        log_success "Credentials already configured"

        if [[ "$AUTO_MODE" != "true" ]]; then
            echo ""
            read -p "Reconfigure credentials? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                save_progress "credentials_configured"
                return 0
            fi
        else
            save_progress "credentials_configured"
            return 0
        fi
    fi

    # Use the existing credential wizard
    if [[ -f "lib/credential_wizard.py" ]]; then
        log_info "Using interactive credential setup wizard..."

        if [[ "$AUTO_MODE" == "true" ]]; then
            log_warning "Auto-mode enabled but credentials need interactive setup"
            log_info "Credentials must be configured manually after installation"
            echo ""
            echo "📋 POST-INSTALLATION CREDENTIAL SETUP:"
            echo "Run: ./manage_fogis_system.sh setup-auth"
            echo ""
            save_progress "credentials_pending"
            return 0
        else
            # Interactive credential setup
            echo ""
            echo "🔐 CREDENTIAL SETUP WIZARD"
            echo "=========================="
            echo ""
            echo "This wizard will guide you through setting up:"
            echo "  • Google OAuth credentials"
            echo "  • Google Calendar integration"
            echo "  • FOGIS authentication"
            echo "  • Secure credential storage"
            echo ""
            read -p "Start credential setup wizard? (Y/n): " -n 1 -r
            echo

            if [[ $REPLY =~ ^[Nn]$ ]]; then
                log_warning "Skipping credential setup"
                echo ""
                echo "📋 MANUAL CREDENTIAL SETUP:"
                echo "Run: ./manage_fogis_system.sh setup-auth"
                echo ""
                save_progress "credentials_pending"
                return 0
            fi

            # Run the credential wizard
            if python3 lib/credential_wizard.py 2>/dev/null || python3 lib/minimal_wizard.py; then
                log_success "Credentials configured successfully"
                save_progress "credentials_configured"
            else
                log_error "Credential setup failed"
                echo ""
                echo "📋 MANUAL CREDENTIAL SETUP:"
                echo "Run: ./manage_fogis_system.sh setup-auth"
                echo ""
                save_progress "credentials_pending"
            fi
        fi
    else
        # Fallback to basic credential setup
        log_warning "Credential wizard not found, using basic setup..."

        if [[ ! -f "credentials.json" ]]; then
            log_warning "Google credentials.json not found!"
            echo ""
            echo "📋 REQUIRED: Google Cloud Credentials"
            echo "1. Go to Google Cloud Console"
            echo "2. Create OAuth 2.0 credentials"
            echo "3. Download as 'credentials.json'"
            echo "4. Place it in this directory"
            echo ""

            if [[ "$AUTO_MODE" == "true" ]]; then
                log_error "Auto-mode enabled but credentials.json not found"
                echo "Please provide credentials.json and re-run the script"
                exit 1
            else
                read -p "Press Enter when credentials.json is ready..."

                if [[ ! -f "credentials.json" ]]; then
                    log_error "credentials.json still not found. Exiting."
                    exit 1
                fi
            fi
        fi

        # Copy credentials to services
        cp credentials.json credentials/google-credentials.json
        log_success "Basic credentials setup completed"
        save_progress "credentials_configured"
    fi
}

# Enhanced service startup with health monitoring
start_services() {
    log_info "Starting FOGIS services..."

    # Check if docker-compose file exists
    if [[ ! -f "docker-compose-master.yml" ]]; then
        log_error "docker-compose-master.yml not found"
        exit 1
    fi

    log_progress "Starting core services..."

    # Start core services first
    if docker-compose -f docker-compose-master.yml up -d fogis-api-client-service; then
        log_success "Core service started"
        sleep 10
    else
        log_error "Failed to start core service"
        exit 1
    fi

    log_progress "Starting processing services..."

    # Start processing services
    if docker-compose -f docker-compose-master.yml up -d match-list-processor team-logo-combiner google-drive-service; then
        log_success "Processing services started"
        sleep 15
    else
        log_error "Failed to start processing services"
        exit 1
    fi

    log_progress "Starting sync services..."

    # Start sync services
    if docker-compose -f docker-compose-master.yml up -d fogis-calendar-phonebook-sync; then
        log_success "Sync services started"
        sleep 10
    else
        log_error "Failed to start sync services"
        exit 1
    fi

    log_progress "Starting automation services..."

    # Start change detector and scheduler
    if docker-compose -f docker-compose-master.yml up -d match-list-change-detector; then
        log_success "Automation services started"
    else
        log_error "Failed to start automation services"
        exit 1
    fi

    log_success "All services started successfully"
    save_progress "services_started"
}

# Enhanced service health checking with retry and recovery
check_service_health() {
    log_info "Performing comprehensive health checks..."

    local services=(
        "fogis-api-client-service:9086"
        "team-logo-combiner:9088"
        "google-drive-service:9085"
        "fogis-calendar-phonebook-sync:9084"
    )

    local healthy_services=0
    local total_services=${#services[@]}

    for service_port in "${services[@]}"; do
        local service=$(echo "$service_port" | cut -d: -f1)
        local port=$(echo "$service_port" | cut -d: -f2)

        log_progress "Checking $service on port $port..."

        local attempts=0
        local max_attempts=30
        local service_healthy=false

        while [[ $attempts -lt $max_attempts ]]; do
            if curl -f "http://localhost:$port/health" &>/dev/null; then
                log_success "✓ $service is healthy"
                healthy_services=$((healthy_services + 1))
                service_healthy=true
                break
            fi

            attempts=$((attempts + 1))
            if [[ $attempts -eq $max_attempts ]]; then
                log_warning "✗ $service health check failed after $max_attempts attempts"

                # Try to restart the service
                if [[ "$AUTO_MODE" == "true" ]]; then
                    log_info "Auto-restarting $service..."
                    docker-compose -f docker-compose-master.yml restart "$service"
                    sleep 10

                    # Check again after restart
                    if curl -f "http://localhost:$port/health" &>/dev/null; then
                        log_success "✓ $service recovered after restart"
                        healthy_services=$((healthy_services + 1))
                        service_healthy=true
                    else
                        log_error "✗ $service failed to recover"
                    fi
                fi
            else
                sleep 2
            fi
        done

        if [[ "$service_healthy" == "false" ]]; then
            echo ""
            echo "📋 Service $service is not responding"
            echo "Check logs: docker-compose -f docker-compose-master.yml logs $service"
            echo ""
        fi
    done

    echo ""
    log_info "Health Check Summary: $healthy_services/$total_services services healthy"

    if [[ $healthy_services -eq $total_services ]]; then
        log_success "All services are healthy!"
        save_progress "health_check_passed"
        return 0
    elif [[ $healthy_services -gt 0 ]]; then
        log_warning "Some services are not healthy, but system is partially functional"
        save_progress "health_check_partial"
        return 1
    else
        log_error "No services are responding"
        save_progress "health_check_failed"
        return 2
    fi
}

# Setup automation (cron jobs)
setup_automation() {
    log_info "Setting up automation..."

    if [[ "$AUTO_MODE" == "true" ]]; then
        log_progress "Auto-configuring cron jobs..."

        # Use the existing management script to add cron
        if ./manage_fogis_system.sh cron-add; then
            log_success "Automation configured successfully"
        else
            log_warning "Failed to configure automation automatically"
        fi
    else
        echo ""
        echo "🕐 AUTOMATION SETUP"
        echo "=================="
        echo ""
        echo "Would you like to set up automatic match processing?"
        echo "This will run every hour to check for new matches."
        echo ""
        read -p "Enable automation? (Y/n): " -n 1 -r
        echo

        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            if ./manage_fogis_system.sh cron-add; then
                log_success "Automation enabled successfully"
            else
                log_warning "Failed to enable automation"
                echo ""
                echo "📋 Manual automation setup:"
                echo "./manage_fogis_system.sh cron-add"
            fi
        else
            log_info "Automation skipped"
            echo ""
            echo "📋 To enable automation later:"
            echo "./manage_fogis_system.sh cron-add"
        fi
    fi

    save_progress "automation_configured"
}

# Main execution with resume capability
main() {
    # Handle help mode
    if [[ "$SHOW_HELP" == "true" ]]; then
        show_usage
        exit 0
    fi

    # Handle rollback mode
    if [[ "$ROLLBACK_MODE" == "true" ]]; then
        cleanup_existing
        exit 0
    fi

    # Handle resume mode
    local current_progress="start"
    if [[ "$RESUME_MODE" == "true" ]]; then
        current_progress=$(get_progress)
        log_info "Resuming from: $current_progress"
    fi

    # Show setup overview
    if [[ "$current_progress" == "start" ]]; then
        echo ""
        echo "🎯 FOGIS ONE-CLICK SETUP OVERVIEW"
        echo "================================="
        echo ""
        echo "This script will automatically:"
        echo "1. 🔍 Check and install prerequisites"
        echo "2. 🐳 Detect and configure Docker"
        echo "3. 🧹 Clean up existing setup"
        echo "4. 📦 Clone all required repositories"
        echo "5. 🔧 Apply critical deployment fixes"
        echo "6. 🏗️  Build Docker images with progress"
        echo "7. 📁 Create directory structure"
        echo "8. 🔐 Setup credentials (interactive)"
        echo "9. 🚀 Start all services"
        echo "10. 🏥 Perform health checks"
        echo "11. 🕐 Configure automation"
        echo ""

        if [[ "$AUTO_MODE" != "true" ]]; then
            echo "Features enabled:"
            echo "  ✅ Resume capability (--resume)"
            echo "  ✅ Rollback capability (--rollback)"
            echo "  ✅ Progress tracking"
            echo "  ✅ Error recovery"
            echo "  ✅ Health monitoring"
            echo ""
            read -p "Continue with setup? (Y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Nn]$ ]]; then
                log_info "Setup cancelled"
                exit 0
            fi
        else
            log_info "Auto-mode enabled - proceeding automatically..."
        fi

        save_progress "overview_shown"
    fi

    # Execute setup steps with resume capability
    local steps=(
        "prerequisites_checked:check_prerequisites"
        "docker_checked:auto_install_docker"
        "cleanup_completed:cleanup_existing"
        "repositories_cloned:clone_repositories"
        "fixes_applied:apply_fixes"
        "images_built:build_images"
        "directories_created:create_directories"
        "credentials_configured:setup_credentials"
        "services_started:start_services"
        "health_check_passed:check_service_health"
        "automation_configured:setup_automation"
    )

    for step_info in "${steps[@]}"; do
        local step_name=$(echo "$step_info" | cut -d: -f1)
        local step_function=$(echo "$step_info" | cut -d: -f2)

        # Skip completed steps in resume mode
        if [[ "$RESUME_MODE" == "true" ]]; then
            local progress=$(get_progress)
            case $progress in
                "prerequisites_checked"|"docker_checked"|"cleanup_completed"|"repositories_cloned"|"fixes_applied"|"images_built"|"directories_created"|"credentials_configured"|"services_started"|"health_check_passed"|"automation_configured")
                    if [[ "$step_name" == "$progress" ]]; then
                        RESUME_MODE=false  # Start executing from next step
                        continue
                    elif [[ "$RESUME_MODE" == "true" ]]; then
                        log_info "Skipping completed step: $step_function"
                        continue
                    fi
                    ;;
            esac
        fi

        # Execute the step
        if ! $step_function; then
            log_error "Step failed: $step_function"
            echo ""
            echo "📋 Recovery Options:"
            echo "1. Fix the issue and run: $0 --resume"
            echo "2. Rollback changes: $0 --rollback"
            echo "3. Check logs for details"
            exit 1
        fi
    done

    # Final success message
    echo ""
    echo "🎉 FOGIS ONE-CLICK SETUP COMPLETE!"
    echo "=================================="
    echo ""

    # Show completion summary
    local health_status=$(get_progress)
    if [[ "$health_status" == "health_check_passed" || "$health_status" == "automation_configured" ]]; then
        log_success "✅ All services are running and healthy"
        echo ""
        echo "🌐 Service URLs:"
        echo "  • FOGIS API Client: http://localhost:9086/health"
        echo "  • Team Logo Combiner: http://localhost:9088/health"
        echo "  • Google Drive Service: http://localhost:9085/health"
        echo "  • Calendar Sync: http://localhost:9084/health"
        echo ""
        echo "🔧 Management Commands:"
        echo "  • Check status: ./manage_fogis_system.sh status"
        echo "  • View logs: ./manage_fogis_system.sh logs"
        echo "  • Test system: ./manage_fogis_system.sh test"
        echo "  • Setup auth: ./manage_fogis_system.sh setup-auth"
        echo ""

        # Check if credentials still need setup
        local progress=$(get_progress)
        if [[ "$progress" == "credentials_pending" ]]; then
            echo "⚠️  IMPORTANT: Credentials need to be configured"
            echo "   Run: ./manage_fogis_system.sh setup-auth"
            echo ""
        fi

        echo "📊 System Status:"
        ./show_system_status.sh 2>/dev/null || echo "  Run ./show_system_status.sh for detailed status"

    else
        log_warning "⚠️  Setup completed with some issues"
        echo ""
        echo "📋 Troubleshooting:"
        echo "  • Check service health: ./manage_fogis_system.sh health"
        echo "  • View logs: ./manage_fogis_system.sh logs"
        echo "  • Restart services: ./manage_fogis_system.sh restart"
    fi

    # Clean up progress file on successful completion
    clear_progress

    echo ""
    log_success "🚀 FOGIS system is ready for use!"
}

# Run main function
main "$@"
