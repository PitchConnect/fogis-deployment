#!/bin/bash

# FOGIS One-Line Web Installer
# Usage: curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Parse command line arguments for headless mode
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --headless)
                HEADLESS_MODE=true
                shift
                ;;
            --mode=*)
                INSTALL_MODE="${1#*=}"
                shift
                ;;
            --auto-confirm)
                AUTO_CONFIRM=true
                shift
                ;;
            --backup-retention=*)
                BACKUP_RETENTION_DAYS="${1#*=}"
                shift
                ;;
            --timeout=*)
                TIMEOUT_SECONDS="${1#*=}"
                shift
                ;;
            --operation-id=*)
                OPERATION_ID="${1#*=}"
                shift
                ;;
            --install-dir=*)
                INSTALL_DIR="${1#*=}"
                shift
                ;;
            --branch=*)
                BRANCH="${1#*=}"
                shift
                ;;
            --help)
                show_headless_usage
                exit 0
                ;;
            *)
                if [[ "$HEADLESS_MODE" == "true" ]]; then
                    log_error "Unknown option: $1"
                    show_headless_usage
                    exit $EXIT_INVALID_CONFIG
                fi
                shift
                ;;
        esac
    done

    # Validate headless configuration
    if [[ "$HEADLESS_MODE" == "true" ]]; then
        validate_headless_config
    fi
}

# Show usage for headless mode
show_headless_usage() {
    cat << EOF
🤖 FOGIS Headless Installation

Usage: bash -s -- [options] < <(curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh)

Headless Options:
  --headless                    Enable headless mode (non-interactive)
  --mode=MODE                   Installation mode: fresh|upgrade|force|check
  --auto-confirm                Automatically confirm all prompts
  --backup-retention=DAYS       Backup retention period (default: 30)
  --timeout=SECONDS             Operation timeout (default: 300)
  --operation-id=ID             Unique operation identifier
  --install-dir=PATH            Installation directory (default: ~/fogis-deployment)
  --branch=BRANCH               Git branch to use (default: main)
  --help                        Show this help message

Installation Modes:
  fresh     - Clean installation (default for empty systems)
  upgrade   - Safe upgrade preserving data (default for existing installations)
  force     - Force clean install with backup (destructive)
  check     - Conflict check only (diagnostic mode)

Environment Variables:
  FOGIS_INSTALL_MODE           Override installation mode
  FOGIS_AUTO_CONFIRM           Auto-confirm prompts (true/false)
  FOGIS_BACKUP_RETENTION       Backup retention days
  FOGIS_TIMEOUT                Operation timeout seconds
  FOGIS_INSTALL_DIR            Installation directory
  FOGIS_BRANCH                 Git branch

Examples:
  # Basic headless installation
  curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless

  # Headless upgrade with auto-confirm
  curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless --mode=upgrade --auto-confirm

  # CI/CD with custom settings
  curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless --mode=fresh --timeout=600 --operation-id=ci-build-123

Exit Codes:
  0   - Success
  1   - General error
  10  - Backup failure
  20  - Rollback required
  30  - Conflicts detected (check mode)
  40  - Operation timeout
  50  - Invalid configuration

EOF
}

# Validate headless configuration
validate_headless_config() {
    local errors=()

    # Validate installation mode
    if [[ -n "$INSTALL_MODE" ]]; then
        case "$INSTALL_MODE" in
            fresh|upgrade|force|check)
                ;;
            *)
                errors+=("Invalid installation mode: $INSTALL_MODE")
                ;;
        esac
    fi

    # Validate numeric parameters
    if ! [[ "$BACKUP_RETENTION_DAYS" =~ ^[0-9]+$ ]] || [[ "$BACKUP_RETENTION_DAYS" -lt 1 ]]; then
        errors+=("Invalid backup retention days: $BACKUP_RETENTION_DAYS")
    fi

    if ! [[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || [[ "$TIMEOUT_SECONDS" -lt 60 ]]; then
        errors+=("Invalid timeout seconds: $TIMEOUT_SECONDS (minimum 60)")
    fi

    # Validate paths
    if [[ ! "$INSTALL_DIR" =~ ^/ ]] && [[ ! "$INSTALL_DIR" =~ ^\~ ]]; then
        errors+=("Install directory must be absolute path or start with ~: $INSTALL_DIR")
    fi

    # Report validation errors
    if [[ ${#errors[@]} -gt 0 ]]; then
        log_error "Configuration validation failed:"
        for error in "${errors[@]}"; do
            echo "  - $error"
        done
        exit $EXIT_INVALID_CONFIG
    fi

    log_info "Headless configuration validated successfully"
} # No Color

# Configuration
REPO_URL="https://github.com/PitchConnect/fogis-deployment.git"
INSTALL_DIR="$HOME/fogis-deployment"

# Headless mode configuration
HEADLESS_MODE=false
INSTALL_MODE=""
AUTO_CONFIRM=false
BACKUP_RETENTION_DAYS=30
TIMEOUT_SECONDS=300
OPERATION_ID="fogis-install-$(date +%s)"

# Exit codes for different scenarios
EXIT_SUCCESS=0
EXIT_GENERAL_ERROR=1
EXIT_BACKUP_FAILURE=10
EXIT_ROLLBACK_REQUIRED=20
EXIT_CONFLICT_DETECTED=30
EXIT_TIMEOUT=40
EXIT_INVALID_CONFIG=50
BRANCH="main"

# Load environment variables for headless mode
load_environment_config() {
    # Override with environment variables if set
    [[ -n "$FOGIS_INSTALL_MODE" ]] && INSTALL_MODE="$FOGIS_INSTALL_MODE"
    [[ -n "$FOGIS_AUTO_CONFIRM" ]] && AUTO_CONFIRM="$FOGIS_AUTO_CONFIRM"
    [[ -n "$FOGIS_BACKUP_RETENTION" ]] && BACKUP_RETENTION_DAYS="$FOGIS_BACKUP_RETENTION"
    [[ -n "$FOGIS_TIMEOUT" ]] && TIMEOUT_SECONDS="$FOGIS_TIMEOUT"
    [[ -n "$FOGIS_INSTALL_DIR" ]] && INSTALL_DIR="$FOGIS_INSTALL_DIR"
    [[ -n "$FOGIS_BRANCH" ]] && BRANCH="$FOGIS_BRANCH"
    [[ -n "$FOGIS_HEADLESS" ]] && HEADLESS_MODE="$FOGIS_HEADLESS"

    # Auto-detect headless mode from environment
    if [[ "$CI" == "true" ]] || [[ "$GITHUB_ACTIONS" == "true" ]] || [[ "$JENKINS_URL" != "" ]] || [[ "$GITLAB_CI" == "true" ]]; then
        HEADLESS_MODE=true
        log_info "CI/CD environment detected - enabling headless mode"
    fi
}

# Progress reporting for monitoring systems
report_progress() {
    local phase="$1"
    local step="$2"
    local total_steps="$3"
    local message="$4"

    if [[ "$HEADLESS_MODE" == "true" ]]; then
        local progress_percent=$((step * 100 / total_steps))
        echo "{\"timestamp\":\"$(date -Iseconds)\",\"level\":\"progress\",\"operation_id\":\"$OPERATION_ID\",\"phase\":\"$phase\",\"step\":$step,\"total_steps\":$total_steps,\"progress_percent\":$progress_percent,\"message\":\"$message\"}"
    else
        log_progress "$message ($step/$total_steps)"
    fi
}

# Helper functions with headless mode support
log_info() {
    if [[ "$HEADLESS_MODE" == "true" ]]; then
        echo "{\"timestamp\":\"$(date -Iseconds)\",\"level\":\"info\",\"operation_id\":\"$OPERATION_ID\",\"message\":\"$1\"}"
    else
        echo -e "${BLUE}ℹ️  $1${NC}"
    fi
}

log_success() {
    if [[ "$HEADLESS_MODE" == "true" ]]; then
        echo "{\"timestamp\":\"$(date -Iseconds)\",\"level\":\"success\",\"operation_id\":\"$OPERATION_ID\",\"message\":\"$1\"}"
    else
        echo -e "${GREEN}✅ $1${NC}"
    fi
}

log_warning() {
    if [[ "$HEADLESS_MODE" == "true" ]]; then
        echo "{\"timestamp\":\"$(date -Iseconds)\",\"level\":\"warning\",\"operation_id\":\"$OPERATION_ID\",\"message\":\"$1\"}"
    else
        echo -e "${YELLOW}⚠️  $1${NC}"
    fi
}

log_error() {
    if [[ "$HEADLESS_MODE" == "true" ]]; then
        echo "{\"timestamp\":\"$(date -Iseconds)\",\"level\":\"error\",\"operation_id\":\"$OPERATION_ID\",\"message\":\"$1\"}" >&2
    else
        echo -e "${RED}❌ $1${NC}" >&2
    fi
}

log_progress() {
    if [[ "$HEADLESS_MODE" == "true" ]]; then
        echo "{\"timestamp\":\"$(date -Iseconds)\",\"level\":\"progress\",\"operation_id\":\"$OPERATION_ID\",\"message\":\"$1\"}"
    else
        echo -e "${PURPLE}🔄 $1${NC}"
    fi
}

log_header() {
    if [[ "$HEADLESS_MODE" == "true" ]]; then
        echo "{\"timestamp\":\"$(date -Iseconds)\",\"level\":\"header\",\"operation_id\":\"$OPERATION_ID\",\"message\":\"$1\"}"
    else
        echo -e "${CYAN}$1${NC}"
    fi
}

# Show header
show_header() {
    echo ""
    log_header "🚀 FOGIS ONE-LINE INSTALLER"
    log_header "============================"
    echo ""
    echo "This installer will:"
    echo "  ✅ Download the FOGIS deployment system"
    echo "  ✅ Install prerequisites automatically"
    echo "  ✅ Set up the complete FOGIS environment"
    echo "  ✅ Configure all services and automation"
    echo ""
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        echo "Please run as a regular user with sudo privileges"
        exit 1
    fi
}

# Detect platform
detect_platform() {
    local os_type=$(uname -s)
    local arch=$(uname -m)
    
    log_info "Detecting platform..."
    
    case $os_type in
        "Darwin")
            echo "macOS detected ($arch)"
            ;;
        "Linux")
            if [[ -f /etc/os-release ]]; then
                local distro=$(grep '^NAME=' /etc/os-release | cut -d'"' -f2)
                echo "Linux detected: $distro ($arch)"
            else
                echo "Linux detected ($arch)"
            fi
            ;;
        *)
            log_warning "Unknown platform: $os_type"
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing=()
    
    # Check Git
    if ! command -v git &> /dev/null; then
        missing+=("git")
    fi
    
    # Check Python3
    if ! command -v python3 &> /dev/null; then
        missing+=("python3")
    fi
    
    # Check curl
    if ! command -v curl &> /dev/null; then
        missing+=("curl")
    fi
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_warning "Missing prerequisites: ${missing[*]}"
        
        # Try to install missing prerequisites
        if command -v apt &> /dev/null; then
            log_info "Installing prerequisites with apt..."
            sudo apt update
            for pkg in "${missing[@]}"; do
                sudo apt install -y "$pkg"
            done
        elif command -v yum &> /dev/null; then
            log_info "Installing prerequisites with yum..."
            for pkg in "${missing[@]}"; do
                sudo yum install -y "$pkg"
            done
        elif command -v brew &> /dev/null; then
            log_info "Installing prerequisites with brew..."
            for pkg in "${missing[@]}"; do
                brew install "$pkg"
            done
        else
            log_error "Cannot install prerequisites automatically"
            echo "Please install: ${missing[*]}"
            exit 1
        fi
    fi
    
    log_success "Prerequisites satisfied"
}

# Handle conflicts in headless mode with intelligent defaults
handle_headless_conflicts() {
    local temp_dir="$1"

    log_info "Conflicts detected - analyzing for headless mode..."

    # If mode is explicitly set, validate and use it
    if [[ -n "$INSTALL_MODE" ]]; then
        case "$INSTALL_MODE" in
            fresh)
                log_warning "Fresh installation requested but conflicts exist - this will fail"
                log_error "Cannot proceed with fresh installation when conflicts exist"
                rm -rf "$temp_dir"
                exit $EXIT_CONFLICT_DETECTED
                ;;
            upgrade|force|check)
                log_info "Using explicitly set mode: $INSTALL_MODE"
                return 0
                ;;
            *)
                log_error "Invalid installation mode for headless operation: $INSTALL_MODE"
                rm -rf "$temp_dir"
                exit $EXIT_INVALID_CONFIG
                ;;
        esac
    fi

    # Intelligent default selection based on conflict analysis
    log_info "Analyzing installation health for intelligent mode selection..."

    # Check if this looks like a healthy installation
    local healthy_installation=true

    # Check for running containers
    local running_containers=$(docker ps --filter "name=fogis" --filter "name=team-logo" --filter "name=match-list" --format "{{.Names}}" 2>/dev/null | wc -l || echo "0")

    # Check for credential files
    local credential_files=0
    if [[ -d "$INSTALL_DIR/credentials" ]]; then
        credential_files=$(find "$INSTALL_DIR/credentials" -name "*.json" 2>/dev/null | wc -l || echo "0")
    fi

    # Check for configuration files
    local has_config=false
    if [[ -f "$INSTALL_DIR/.env" ]] || [[ -f "$INSTALL_DIR/docker-compose-master.yml" ]]; then
        has_config=true
    fi

    # Decision matrix for intelligent defaults
    if [[ $running_containers -gt 0 ]] && [[ $credential_files -gt 0 ]] && [[ "$has_config" == "true" ]]; then
        # Healthy installation detected
        INSTALL_MODE="upgrade"
        log_info "Healthy installation detected - defaulting to safe upgrade mode"
    elif [[ $credential_files -gt 0 ]] || [[ "$has_config" == "true" ]]; then
        # Partial installation with important data
        INSTALL_MODE="upgrade"
        log_info "Partial installation with data detected - defaulting to safe upgrade mode"
    else
        # Broken or minimal installation
        INSTALL_MODE="force"
        log_warning "Broken or minimal installation detected - defaulting to force clean install mode"
    fi

    log_info "Selected installation mode: $INSTALL_MODE"

    # Log decision rationale for troubleshooting
    if [[ "$HEADLESS_MODE" == "true" ]]; then
        echo "{\"timestamp\":\"$(date -Iseconds)\",\"level\":\"decision\",\"operation_id\":\"$OPERATION_ID\",\"selected_mode\":\"$INSTALL_MODE\",\"running_containers\":$running_containers,\"credential_files\":$credential_files,\"has_config\":$has_config}"
    fi
}

# Enhanced download with safety system
download_fogis() {
    log_info "Downloading FOGIS deployment system..."

    # First, clone to a temporary location to access safety modules
    local temp_dir="/tmp/fogis-download-$(date +%s)"

    log_progress "Cloning repository to temporary location..."
    if ! git clone --branch "$BRANCH" "$REPO_URL" "$temp_dir"; then
        log_error "Failed to clone repository"
        exit 1
    fi

    # Source the safety system
    if [[ -f "$temp_dir/fogis-deployment/lib/installation_safety.sh" ]]; then
        log_info "Loading installation safety system..."
        source "$temp_dir/fogis-deployment/lib/installation_safety.sh"

        # Run conflict detection and intelligent mode selection
        if detect_all_conflicts; then
            # No conflicts detected
            if [[ -z "$INSTALL_MODE" ]]; then
                INSTALL_MODE="fresh"
            fi
            log_success "No conflicts detected - proceeding with $INSTALL_MODE installation"
        else
            # Conflicts detected - handle based on mode
            if [[ "$HEADLESS_MODE" == "true" ]]; then
                handle_headless_conflicts "$temp_dir"
            else
                # Interactive mode - let user choose
                select_installation_mode
            fi

            # Execute the selected mode
            if ! execute_installation_mode; then
                # Mode execution failed or was conflict-check-only
                if [[ "$INSTALL_MODE" == "check" ]]; then
                    log_info "Conflict check completed. Exiting."
                    rm -rf "$temp_dir"
                    exit $EXIT_CONFLICT_DETECTED
                else
                    log_error "Installation mode execution failed"
                    rm -rf "$temp_dir"
                    exit $EXIT_GENERAL_ERROR
                fi
            fi
        fi
    else
        log_warning "Safety system not available, using legacy behavior"
        # Legacy behavior for backward compatibility
        if [[ -d "$INSTALL_DIR" ]]; then
            log_warning "Existing installation found at $INSTALL_DIR"
            read -p "Remove existing installation? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$INSTALL_DIR"
            else
                log_error "Installation cancelled"
                rm -rf "$temp_dir"
                exit 1
            fi
        fi
    fi

    # Move the cloned repository to the final location
    log_progress "Moving installation to final location..."
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
    fi

    mv "$temp_dir" "$INSTALL_DIR"
    log_success "Repository installed successfully"
}

# Run the setup with rollback protection
run_setup() {
    log_info "Starting FOGIS setup with rollback protection..."

    cd "$INSTALL_DIR"

    # Make scripts executable
    chmod +x *.sh 2>/dev/null || true
    chmod +x fogis-deployment/*.sh 2>/dev/null || true

    # Set up rollback protection
    local backup_location=""
    if [[ -f "/tmp/fogis_backup_location" ]]; then
        backup_location=$(cat /tmp/fogis_backup_location)
    fi

    # Set trap for failure handling
    trap "handle_installation_failure '$backup_location'" ERR

    # Run the enhanced setup script
    report_progress "setup" 1 3 "Running one-click setup"

    if [[ "$HEADLESS_MODE" != "true" ]]; then
        echo ""
    fi

    if ./fogis-deployment/setup_fogis_system.sh --auto; then
        # Installation succeeded
        trap - ERR  # Remove error trap

        report_progress "setup" 2 3 "Restoring preserved data"

        # Restore preserved data if this was an upgrade
        if [[ -f "fogis-deployment/lib/installation_safety.sh" ]]; then
            source fogis-deployment/lib/installation_safety.sh
            restore_preserved_data
        fi

        report_progress "setup" 3 3 "Verifying installation health"

        # Perform health verification for headless mode
        if [[ "$HEADLESS_MODE" == "true" ]]; then
            if ! verify_installation_health; then
                log_warning "Health verification failed but installation completed"
            fi
        fi

        log_success "FOGIS setup completed successfully!"

        # Handle backup cleanup
        if [[ -n "$backup_location" && -f "$backup_location" ]]; then
            if [[ "$HEADLESS_MODE" == "true" ]] || [[ "$AUTO_CONFIRM" == "true" ]]; then
                # Auto-cleanup in headless mode or when auto-confirm is enabled
                rm -f "$backup_location"
                rm -f /tmp/fogis_backup_location
                log_info "Backup automatically removed"
            else
                # Interactive cleanup prompt
                echo ""
                read -p "Installation successful. Remove backup file? (y/N): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    rm -f "$backup_location"
                    rm -f /tmp/fogis_backup_location
                    log_info "Backup removed"
                else
                    log_info "Backup preserved at: $backup_location"
                fi
            fi
        fi
    else
        # This should not be reached due to ERR trap, but kept for safety
        log_error "Setup failed"
        handle_installation_failure "$backup_location"
    fi
}

# Handle installation failure with rollback options
handle_installation_failure() {
    local backup_location="$1"

    log_error "💥 Installation failed!"
    echo ""

    if [[ -n "$backup_location" && -f "$backup_location" ]]; then
        log_warning "🔄 Rollback options available:"
        echo ""
        echo "1. Automatic rollback (restores previous installation)"
        echo "2. Manual recovery (provides backup location)"
        echo "3. Clean up and exit (removes partial installation)"
        echo ""

        read -p "Select option (1-3): " rollback_choice

        case $rollback_choice in
            1)
                perform_automatic_rollback "$backup_location"
                ;;
            2)
                log_info "📁 Backup location: $backup_location"
                log_info "📋 Manual recovery instructions:"
                echo "  1. Extract backup: tar -xzf $backup_location -C /tmp/"
                echo "  2. Review contents: ls -la /tmp/fogis-backup-*/"
                echo "  3. Restore selectively as needed"
                ;;
            3)
                cleanup_partial_installation
                ;;
            *)
                log_warning "Invalid choice, performing cleanup"
                cleanup_partial_installation
                ;;
        esac
    else
        log_error "No backup available for rollback"
        cleanup_partial_installation
    fi

    exit 1
}

# Perform automatic rollback
perform_automatic_rollback() {
    local backup_location="$1"

    log_info "🔄 Performing automatic rollback..."

    # Clean up partial installation
    if [[ -d "$INSTALL_DIR" ]]; then
        log_progress "Removing partial installation..."
        rm -rf "$INSTALL_DIR"
    fi

    # Restore from backup
    if [[ -f "$backup_location" ]]; then
        log_progress "Restoring from backup..."

        # Source backup manager if available
        local temp_extract="/tmp/fogis_rollback_$(date +%s)"
        mkdir -p "$temp_extract"

        if tar -xzf "$backup_location" -C "$temp_extract" 2>/dev/null; then
            local backup_content=$(find "$temp_extract" -maxdepth 1 -type d ! -path "$temp_extract" | head -1)

            if [[ -d "$backup_content" ]]; then
                mkdir -p "$INSTALL_DIR"

                # Restore directory structure
                if [[ -d "$backup_content/credentials" ]]; then
                    cp -r "$backup_content/credentials" "$INSTALL_DIR/"
                fi

                if [[ -d "$backup_content/configs" ]]; then
                    cp "$backup_content/configs"/*.env "$INSTALL_DIR/" 2>/dev/null || true
                    cp "$backup_content/configs"/*.yml "$INSTALL_DIR/" 2>/dev/null || true
                fi

                if [[ -d "$backup_content/data" ]]; then
                    cp -r "$backup_content/data" "$INSTALL_DIR/"
                fi

                log_success "✅ Rollback completed successfully"
                echo ""
                echo "📋 Previous installation restored from backup"
                echo "📁 Installation directory: $INSTALL_DIR"
            else
                log_error "Invalid backup structure"
            fi
        else
            log_error "Failed to extract backup"
        fi

        rm -rf "$temp_extract"
    else
        log_error "Backup file not found: $backup_location"
    fi
}

# Clean up partial installation
cleanup_partial_installation() {
    log_info "🧹 Cleaning up partial installation..."

    # Stop any running containers
    local fogis_containers=$(docker ps -a --filter "name=fogis" --filter "name=team-logo" --filter "name=match-list" --filter "name=google-drive" --filter "name=cron-scheduler" --format "{{.Names}}" 2>/dev/null || true)

    if [[ -n "$fogis_containers" ]]; then
        log_progress "Stopping containers..."
        while IFS= read -r container; do
            [[ -n "$container" ]] || continue
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
        done <<< "$fogis_containers"
    fi

    # Remove Docker network
    if docker network ls --filter "name=fogis-network" --format "{{.Name}}" 2>/dev/null | grep -q "fogis-network"; then
        log_progress "Removing Docker network..."
        docker network rm fogis-network 2>/dev/null || true
    fi

    # Remove installation directory
    if [[ -d "$INSTALL_DIR" ]]; then
        log_progress "Removing installation directory..."
        rm -rf "$INSTALL_DIR"
    fi

    # Clean up temporary files
    rm -f /tmp/fogis_backup_location
    rm -f /tmp/fogis_upgrade_state

    log_success "Cleanup completed"
}

# Show completion message
show_completion() {
    echo ""
    log_header "🎉 INSTALLATION COMPLETE!"
    log_header "========================="
    echo ""
    log_success "FOGIS has been installed successfully!"
    echo ""
    echo "📁 Installation directory: $INSTALL_DIR"
    echo ""
    echo "🔧 Quick commands:"
    echo "  cd $INSTALL_DIR"
    echo "  ./fogis-deployment/manage_fogis_system.sh status"
    echo "  ./fogis-deployment/manage_fogis_system.sh setup-auth"
    echo "  ./fogis-deployment/show_system_status.sh"
    echo ""
    echo "📖 Documentation:"
    echo "  • README: $INSTALL_DIR/fogis-deployment/README.md"
    echo "  • Prerequisites: $INSTALL_DIR/fogis-deployment/DEPLOYMENT_PREREQUISITES.md"
    echo ""
    echo "🌐 Service URLs (once running):"
    echo "  • FOGIS API: http://localhost:9086/health"
    echo "  • Team Logos: http://localhost:9088/health"
    echo "  • Google Drive: http://localhost:9085/health"
    echo "  • Calendar Sync: http://localhost:9084/health"
    echo ""
    log_success "🚀 FOGIS is ready to use!"
}

# Main execution
main() {
    # Initialize headless mode configuration
    load_environment_config
    parse_arguments "$@"

    # Show header (suppressed in headless mode)
    if [[ "$HEADLESS_MODE" != "true" ]]; then
        show_header
    else
        log_info "Starting FOGIS headless installation (Operation ID: $OPERATION_ID)"
    fi

    # Set up timeout handling for headless mode
    if [[ "$HEADLESS_MODE" == "true" ]]; then
        setup_timeout_handling
    fi

    check_root
    detect_platform
    check_prerequisites
    download_fogis
    run_setup
    show_completion
}

# Setup timeout handling for headless operations
setup_timeout_handling() {
    # Set up a background process to enforce timeout
    (
        sleep "$TIMEOUT_SECONDS"
        log_error "Operation timeout after $TIMEOUT_SECONDS seconds"
        kill -TERM $$ 2>/dev/null
    ) &
    local timeout_pid=$!

    # Store timeout PID for cleanup
    echo "$timeout_pid" > "/tmp/fogis-timeout-$$"

    # Cleanup timeout process on exit
    trap "cleanup_timeout_process $timeout_pid" EXIT
}

# Cleanup timeout process
cleanup_timeout_process() {
    local timeout_pid="$1"
    if kill -0 "$timeout_pid" 2>/dev/null; then
        kill "$timeout_pid" 2>/dev/null
    fi
    rm -f "/tmp/fogis-timeout-$$"
}

# Enhanced interruption handling
handle_interruption() {
    if [[ "$HEADLESS_MODE" == "true" ]]; then
        log_error "Installation interrupted"
        exit $EXIT_GENERAL_ERROR
    else
        echo ""
        log_warning "Installation interrupted"
        exit 1
    fi
}

# Handle interruption
trap 'handle_interruption' INT TERM

# Run main function
main "$@"
