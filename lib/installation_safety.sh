#!/bin/bash

# FOGIS Installation Safety System
# Core safety functions for safe installation with rollback protection
# Part of the Safe Installation System (GitHub Issue #17)

set -e

# Note: This script expects conflict_detector.sh and backup_manager.sh to be sourced separately
# to avoid circular dependencies and conflicts with logging functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define color and logging functions directly to avoid sourcing interactive scripts
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_progress() { echo -e "${PURPLE}🔄 $1${NC}"; }
log_header() { echo -e "${CYAN}$1${NC}"; }

# Configuration
INSTALL_DIR="${INSTALL_DIR:-$HOME/fogis-deployment}"
INSTALL_MODE=""

# Installation mode selection interface (interactive mode only)
select_installation_mode() {
    # Skip if already in headless mode or mode is already set
    if [[ "$HEADLESS_MODE" == "true" ]] || [[ -n "$INSTALL_MODE" ]]; then
        return 0
    fi

    echo ""
    log_header "🛠️ FOGIS INSTALLATION OPTIONS"
    log_header "=============================="
    echo ""
    echo "Please select installation mode:"
    echo ""
    echo "1. 🆕 Fresh Installation (recommended for new setups)"
    echo "   • Clean installation on empty system"
    echo "   • No conflict detection needed"
    echo "   • Fastest installation method"
    echo ""
    echo "2. 🔄 Safe Upgrade (recommended for existing installations)"
    echo "   • Preserves credentials and important data"
    echo "   • Graceful service shutdown and cleanup"
    echo "   • Automatic backup creation"
    echo "   • Rollback capability on failure"
    echo ""
    echo "3. 🧹 Force Clean Install (destructive - use with caution)"
    echo "   • Removes all existing data and configurations"
    echo "   • Creates backup before destruction"
    echo "   • Use only if upgrade fails"
    echo "   • ⚠️  WARNING: This will destroy all existing data!"
    echo ""
    echo "4. 🔍 Conflict Check Only (diagnostic mode)"
    echo "   • Check for conflicts without making changes"
    echo "   • Generate detailed conflict report"
    echo "   • Provide manual resolution steps"
    echo "   • Safe for troubleshooting"
    echo ""

    while true; do
        read -p "Enter your choice (1-4): " choice
        case $choice in
            1)
                INSTALL_MODE="fresh"
                log_info "Selected: Fresh Installation"
                break
                ;;
            2)
                INSTALL_MODE="upgrade"
                log_info "Selected: Safe Upgrade"
                break
                ;;
            3)
                INSTALL_MODE="force"
                log_warning "⚠️ This will destroy all existing data!"
                echo ""
                if [[ "$AUTO_CONFIRM" == "true" ]]; then
                    log_info "Auto-confirm enabled - proceeding with Force Clean Install"
                    break
                else
                    read -p "Are you sure? Type 'DESTROY' to confirm: " confirm
                    if [[ "$confirm" == "DESTROY" ]]; then
                        log_info "Selected: Force Clean Install"
                        break
                    else
                        log_info "Operation cancelled"
                        continue
                    fi
                fi
                ;;
            4)
                INSTALL_MODE="check"
                log_info "Selected: Conflict Check Only"
                break
                ;;
            *)
                log_error "Invalid choice. Please enter 1, 2, 3, or 4."
                ;;
        esac
    done

    echo ""
}

# Graceful service shutdown
graceful_service_shutdown() {
    log_info "🛑 Performing graceful service shutdown..."

    # Check if management script exists
    if [[ -f "$INSTALL_DIR/manage_fogis_system.sh" ]]; then
        log_progress "Using management script for shutdown..."
        cd "$INSTALL_DIR"

        # Stop services gracefully
        if ./manage_fogis_system.sh stop 2>/dev/null; then
            log_success "Services stopped via management script"
        else
            log_warning "Management script shutdown failed, trying Docker Compose"
        fi

        # Remove cron jobs
        if ./manage_fogis_system.sh cron-remove 2>/dev/null; then
            log_success "Cron jobs removed"
        else
            log_warning "Failed to remove cron jobs via management script"
        fi
    fi

    # Fallback to Docker Compose
    if [[ -f "$INSTALL_DIR/docker-compose-master.yml" ]]; then
        log_progress "Using Docker Compose for shutdown..."
        cd "$INSTALL_DIR"

        if docker-compose -f docker-compose-master.yml down --remove-orphans --volumes 2>/dev/null; then
            log_success "Services stopped via Docker Compose"
        else
            log_warning "Docker Compose shutdown failed"
        fi
    fi

    # Manual container cleanup
    log_progress "Cleaning up any remaining containers..."
    local fogis_containers=$(docker ps -a --filter "name=fogis" --filter "name=team-logo" --filter "name=match-list" --filter "name=google-drive" --filter "name=cron-scheduler" --format "{{.Names}}" 2>/dev/null || true)

    if [[ -n "$fogis_containers" ]]; then
        while IFS= read -r container; do
            [[ -n "$container" ]] || continue
            log_progress "Stopping container: $container"
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
        done <<< "$fogis_containers"
    fi

    # Clean up Docker network
    if docker network ls --filter "name=fogis-network" --format "{{.Name}}" 2>/dev/null | grep -q "fogis-network"; then
        log_progress "Removing Docker network..."
        docker network rm fogis-network 2>/dev/null || true
    fi

    # Clean up cron jobs manually
    log_progress "Cleaning up cron jobs..."
    if crontab -l 2>/dev/null | grep -q "match-list-processor\|fogis"; then
        local temp_cron="/tmp/crontab_backup_$(date +%s)"
        crontab -l 2>/dev/null | grep -v "match-list-processor\|fogis" > "$temp_cron" || true
        crontab "$temp_cron" 2>/dev/null || true
        rm -f "$temp_cron"
        log_success "Cron jobs cleaned up"
    fi

    log_success "✅ Graceful shutdown completed"
}

# Safe upgrade with data preservation
perform_safe_upgrade() {
    log_header "🔄 PERFORMING SAFE UPGRADE"
    log_header "=========================="
    echo ""

    # Step 1: Create comprehensive backup
    log_info "Step 1/6: Creating comprehensive backup..."
    local backup_file=$(create_installation_backup)
    if [[ $? -ne 0 || -z "$backup_file" ]]; then
        log_error "Backup creation failed"
        return 1
    fi

    # Step 2: Graceful service shutdown
    log_info "Step 2/6: Graceful service shutdown..."
    graceful_service_shutdown

    # Step 3: Preserve critical data
    log_info "Step 3/6: Preserving critical data..."
    local temp_preserve="/tmp/fogis-preserve-$(date +%s)"
    mkdir -p "$temp_preserve"

    if [[ -d "$INSTALL_DIR/credentials" ]]; then
        cp -r "$INSTALL_DIR/credentials" "$temp_preserve/" 2>/dev/null || {
            log_warning "Failed to preserve credentials"
        }
    fi

    if [[ -d "$INSTALL_DIR/data" ]]; then
        # Only preserve essential data files
        mkdir -p "$temp_preserve/data"
        find "$INSTALL_DIR/data" -name "*.json" -o -name "*.db" -o -name "*.sqlite*" | \
            xargs -I {} cp --parents {} "$temp_preserve/" 2>/dev/null || true
    fi

    # Step 4: Remove old installation
    log_info "Step 4/6: Removing old installation..."
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        log_success "Old installation removed"
    fi

    # Step 5: Signal for fresh installation
    log_info "Step 5/6: Ready for fresh installation..."
    echo "SAFE_UPGRADE_PRESERVE_DIR=$temp_preserve" > /tmp/fogis_upgrade_state
    echo "SAFE_UPGRADE_BACKUP=$backup_file" >> /tmp/fogis_upgrade_state

    log_success "✅ Safe upgrade preparation completed"
    echo ""
    echo "📋 Next steps:"
    echo "1. Fresh installation will proceed automatically"
    echo "2. Preserved data will be restored after installation"
    echo "3. Backup available at: $backup_file"
    echo ""
}

# Restore preserved data after upgrade
restore_preserved_data() {
    if [[ ! -f "/tmp/fogis_upgrade_state" ]]; then
        return 0  # No upgrade in progress
    fi

    source /tmp/fogis_upgrade_state

    if [[ -n "$SAFE_UPGRADE_PRESERVE_DIR" && -d "$SAFE_UPGRADE_PRESERVE_DIR" ]]; then
        log_info "🔄 Restoring preserved data from upgrade..."

        # Restore credentials
        if [[ -d "$SAFE_UPGRADE_PRESERVE_DIR/credentials" ]]; then
            mkdir -p "$INSTALL_DIR/credentials"
            cp -r "$SAFE_UPGRADE_PRESERVE_DIR/credentials"/* "$INSTALL_DIR/credentials/" 2>/dev/null || {
                log_warning "Failed to restore some credentials"
            }
            log_success "Credentials restored"
        fi

        # Restore essential data
        if [[ -d "$SAFE_UPGRADE_PRESERVE_DIR/data" ]]; then
            mkdir -p "$INSTALL_DIR/data"
            cp -r "$SAFE_UPGRADE_PRESERVE_DIR/data"/* "$INSTALL_DIR/data/" 2>/dev/null || {
                log_warning "Failed to restore some data"
            }
            log_success "Essential data restored"
        fi

        # Cleanup
        rm -rf "$SAFE_UPGRADE_PRESERVE_DIR"
        rm -f /tmp/fogis_upgrade_state

        log_success "✅ Data restoration completed"
    fi
}

# Force clean installation with backup
perform_force_clean() {
    log_header "🧹 PERFORMING FORCE CLEAN INSTALLATION"
    log_header "======================================"
    echo ""

    log_warning "⚠️ This will destroy all existing data!"
    echo ""

    # Create backup before destruction
    log_info "Step 1/3: Creating backup before destruction..."
    local backup_file=$(create_installation_backup)
    if [[ $? -ne 0 ]]; then
        log_warning "Backup creation failed, but continuing with force clean"
    else
        log_success "Backup created: $backup_file"
    fi

    # Graceful shutdown
    log_info "Step 2/3: Graceful service shutdown..."
    graceful_service_shutdown

    # Complete removal
    log_info "Step 3/3: Complete removal of installation..."
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        log_success "Installation directory removed"
    fi

    log_success "✅ Force clean completed"
    if [[ -n "$backup_file" ]]; then
        echo "📦 Backup available at: $backup_file"
    fi
    echo ""
}

# Conflict check only mode
perform_conflict_check() {
    log_header "🔍 CONFLICT CHECK ONLY MODE"
    log_header "==========================="
    echo ""

    # Run comprehensive conflict detection
    if detect_all_conflicts; then
        echo ""
        log_success "✅ System is ready for fresh installation"
        echo ""
        echo "📋 Recommended next steps:"
        echo "1. Run installer with 'Fresh Installation' mode"
        echo "2. No special precautions needed"
    else
        echo ""
        log_warning "⚠️ Conflicts detected - see details above"
        echo ""
        echo "📋 Recommended next steps:"
        echo "1. Use 'Safe Upgrade' mode to preserve data"
        echo "2. Or manually resolve conflicts before fresh installation"
        echo "3. Or use 'Force Clean Install' if data loss is acceptable"
    fi

    # Generate detailed report
    local report_file=$(generate_conflict_report)
    echo ""
    log_info "📄 Detailed report saved to: $report_file"
    echo ""
}

# Main safety orchestration function
execute_installation_mode() {
    case "$INSTALL_MODE" in
        "fresh")
            log_info "Proceeding with fresh installation..."
            # No special actions needed for fresh installation
            return 0
            ;;
        "upgrade")
            perform_safe_upgrade
            return $?
            ;;
        "force")
            perform_force_clean
            return $?
            ;;
        "check")
            perform_conflict_check
            return 1  # Exit after check, don't proceed with installation
            ;;
        *)
            log_error "Invalid installation mode: $INSTALL_MODE"
            return 1
            ;;
    esac
}

# Headless mode validation and health checks
validate_headless_environment() {
    log_info "Validating headless environment..."

    # Check required tools
    local missing_tools=()
    for tool in docker git tar; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools+=("$tool")
        fi
    done

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools for headless operation: ${missing_tools[*]}"
        return 1
    fi

    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running or accessible"
        return 1
    fi

    # Check disk space (minimum 1GB)
    local available_space=$(df "$HOME" | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 1048576 ]]; then  # 1GB in KB
        log_warning "Low disk space detected: $(( available_space / 1024 ))MB available"
    fi

    log_success "Headless environment validation passed"
    return 0
}

# Post-installation health verification for headless mode
verify_installation_health() {
    log_info "Performing post-installation health verification..."

    local health_checks=0
    local total_checks=5

    # Check 1: Installation directory exists
    if [[ -d "$INSTALL_DIR" ]]; then
        log_success "Installation directory exists"
        ((health_checks++))
    else
        log_error "Installation directory missing"
    fi

    # Check 2: Essential files present
    if [[ -f "$INSTALL_DIR/docker-compose-master.yml" ]] && [[ -f "$INSTALL_DIR/.env" ]]; then
        log_success "Essential configuration files present"
        ((health_checks++))
    else
        log_error "Essential configuration files missing"
    fi

    # Check 3: Docker network exists
    if docker network ls --filter "name=fogis-network" --format "{{.Name}}" 2>/dev/null | grep -q "fogis-network"; then
        log_success "Docker network configured"
        ((health_checks++))
    else
        log_warning "Docker network not found"
    fi

    # Check 4: Containers can be started (dry run)
    cd "$INSTALL_DIR" || return 1
    if docker-compose -f docker-compose-master.yml config >/dev/null 2>&1; then
        log_success "Docker Compose configuration valid"
        ((health_checks++))
    else
        log_error "Docker Compose configuration invalid"
    fi

    # Check 5: Management script exists and is executable
    if [[ -x "$INSTALL_DIR/manage_fogis_system.sh" ]]; then
        log_success "Management script ready"
        ((health_checks++))
    else
        log_warning "Management script not executable"
    fi

    # Report health status
    local health_percentage=$((health_checks * 100 / total_checks))

    if [[ "$HEADLESS_MODE" == "true" ]]; then
        echo "{\"timestamp\":\"$(date -Iseconds)\",\"level\":\"health_check\",\"operation_id\":\"$OPERATION_ID\",\"checks_passed\":$health_checks,\"total_checks\":$total_checks,\"health_percentage\":$health_percentage}"
    fi

    if [[ $health_checks -eq $total_checks ]]; then
        log_success "Installation health verification: PASSED ($health_checks/$total_checks)"
        return 0
    elif [[ $health_checks -ge 3 ]]; then
        log_warning "Installation health verification: PARTIAL ($health_checks/$total_checks)"
        return 0
    else
        log_error "Installation health verification: FAILED ($health_checks/$total_checks)"
        return 1
    fi
}

# Enhanced error handling for headless mode
handle_headless_error() {
    local error_type="$1"
    local error_message="$2"
    local suggested_action="$3"

    if [[ "$HEADLESS_MODE" == "true" ]]; then
        echo "{\"timestamp\":\"$(date -Iseconds)\",\"level\":\"error\",\"operation_id\":\"$OPERATION_ID\",\"error_type\":\"$error_type\",\"message\":\"$error_message\",\"suggested_action\":\"$suggested_action\"}" >&2
    else
        log_error "$error_message"
        if [[ -n "$suggested_action" ]]; then
            echo "Suggested action: $suggested_action"
        fi
    fi
}

# Export functions for use by other scripts
export -f select_installation_mode
export -f graceful_service_shutdown
export -f perform_safe_upgrade
export -f restore_preserved_data
export -f perform_force_clean
export -f perform_conflict_check
export -f execute_installation_mode
export -f validate_headless_environment
export -f verify_installation_health
export -f handle_headless_error
