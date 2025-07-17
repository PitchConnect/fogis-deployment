#!/bin/bash

# FOGIS Credential Restoration Script
# Automatically restores FOGIS credentials from backup files during fresh installations
# Part of the credential preservation improvement initiative

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Function to show usage
show_usage() {
    echo "🔐 FOGIS Credential Restoration Tool"
    echo "===================================="
    echo ""
    echo "Usage: $0 [backup_directory] [options]"
    echo ""
    echo "Arguments:"
    echo "  backup_directory    Path to FOGIS credential backup directory"
    echo ""
    echo "Options:"
    echo "  --auto             Run in automatic mode (no prompts)"
    echo "  --validate         Validate credentials after restoration"
    echo "  --dry-run          Show what would be restored without making changes"
    echo "  --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 fogis-credentials-backup-20250717-140734"
    echo "  $0 /path/to/backup --auto --validate"
    echo "  $0 backup-dir --dry-run"
    echo ""
}

# Function to detect backup directories automatically
detect_backup_directories() {
    log_info "Scanning for FOGIS credential backup directories..."
    
    local backup_dirs=()
    
    # Look for backup directories in common locations
    for pattern in "fogis-credentials-backup-*" "../fogis-credentials-backup-*" "*/fogis-credentials-backup-*"; do
        for dir in $pattern; do
            if [[ -d "$dir" && -f "$dir/FOGIS_CREDENTIALS.txt" ]]; then
                backup_dirs+=("$dir")
            fi
        done
    done
    
    if [[ ${#backup_dirs[@]} -eq 0 ]]; then
        log_warning "No FOGIS credential backup directories found"
        return 1
    fi
    
    log_success "Found ${#backup_dirs[@]} backup director(ies):"
    for dir in "${backup_dirs[@]}"; do
        local timestamp=$(basename "$dir" | sed 's/fogis-credentials-backup-//')
        echo "  📁 $dir (created: $timestamp)"
    done
    
    # Return the most recent backup directory
    printf '%s\n' "${backup_dirs[@]}" | sort -r | head -n1
}

# Function to extract credentials from backup file
extract_credentials_from_backup() {
    local backup_dir="$1"
    local credentials_file="$backup_dir/FOGIS_CREDENTIALS.txt"
    
    if [[ ! -f "$credentials_file" ]]; then
        log_error "Credentials file not found: $credentials_file"
        return 1
    fi
    
    log_info "Extracting credentials from backup..."
    
    # Extract FOGIS credentials using more robust parsing
    local username=$(grep "^FOGIS_USERNAME=" "$credentials_file" 2>/dev/null | head -n1 | cut -d'=' -f2- | sed 's/^["'\'']*//;s/["'\'']*$//')
    local password=$(grep "^FOGIS_PASSWORD=" "$credentials_file" 2>/dev/null | head -n1 | cut -d'=' -f2- | sed 's/^["'\'']*//;s/["'\'']*$//')
    local referee_number=$(grep "^USER_REFEREE_NUMBER=" "$credentials_file" 2>/dev/null | head -n1 | cut -d'=' -f2- | sed 's/^["'\'']*//;s/["'\'']*$//')
    
    if [[ -z "$username" || -z "$password" ]]; then
        log_error "Could not extract FOGIS credentials from backup file"
        log_info "Expected format: FOGIS_USERNAME=value and FOGIS_PASSWORD=value"
        return 1
    fi
    
    log_success "Successfully extracted credentials:"
    echo "  👤 Username: $username"
    echo "  🔑 Password: [REDACTED]"
    if [[ -n "$referee_number" ]]; then
        echo "  🏆 Referee Number: $referee_number"
    fi
    
    # Export for use by other functions
    export RESTORED_FOGIS_USERNAME="$username"
    export RESTORED_FOGIS_PASSWORD="$password"
    export RESTORED_REFEREE_NUMBER="$referee_number"
    
    return 0
}

# Function to update .env file with restored credentials
update_env_file() {
    local env_file="${1:-.env}"
    local dry_run="${2:-false}"
    
    if [[ "$dry_run" == "true" ]]; then
        log_info "DRY RUN: Would update $env_file with:"
        echo "  FOGIS_USERNAME=$RESTORED_FOGIS_USERNAME"
        echo "  FOGIS_PASSWORD=[REDACTED]"
        if [[ -n "$RESTORED_REFEREE_NUMBER" ]]; then
            echo "  USER_REFEREE_NUMBER=$RESTORED_REFEREE_NUMBER"
        fi
        return 0
    fi
    
    log_info "Updating $env_file with restored credentials..."
    
    # Create backup of existing .env file
    if [[ -f "$env_file" ]]; then
        cp "$env_file" "$env_file.backup.$(date +%Y%m%d-%H%M%S)"
        log_info "Created backup: $env_file.backup.$(date +%Y%m%d-%H%M%S)"
    fi
    
    # Create or update .env file
    local temp_file=$(mktemp)
    local updated_username=false
    local updated_password=false
    local updated_referee=false
    
    # Process existing .env file if it exists
    if [[ -f "$env_file" ]]; then
        while IFS= read -r line; do
            if [[ "$line" =~ ^FOGIS_USERNAME= ]]; then
                echo "FOGIS_USERNAME=$RESTORED_FOGIS_USERNAME" >> "$temp_file"
                updated_username=true
            elif [[ "$line" =~ ^FOGIS_PASSWORD= ]]; then
                echo "FOGIS_PASSWORD=$RESTORED_FOGIS_PASSWORD" >> "$temp_file"
                updated_password=true
            elif [[ "$line" =~ ^USER_REFEREE_NUMBER= ]] && [[ -n "$RESTORED_REFEREE_NUMBER" ]]; then
                echo "USER_REFEREE_NUMBER=$RESTORED_REFEREE_NUMBER" >> "$temp_file"
                updated_referee=true
            else
                echo "$line" >> "$temp_file"
            fi
        done < "$env_file"
    fi
    
    # Add missing credentials
    if [[ "$updated_username" == "false" ]]; then
        echo "FOGIS_USERNAME=$RESTORED_FOGIS_USERNAME" >> "$temp_file"
    fi
    if [[ "$updated_password" == "false" ]]; then
        echo "FOGIS_PASSWORD=$RESTORED_FOGIS_PASSWORD" >> "$temp_file"
    fi
    if [[ "$updated_referee" == "false" && -n "$RESTORED_REFEREE_NUMBER" ]]; then
        echo "USER_REFEREE_NUMBER=$RESTORED_REFEREE_NUMBER" >> "$temp_file"
    fi
    
    # Replace original file
    mv "$temp_file" "$env_file"
    chmod 600 "$env_file"  # Secure permissions
    
    log_success "Successfully updated $env_file with restored credentials"
    return 0
}

# Function to validate restored credentials
validate_credentials() {
    log_info "Validating restored FOGIS credentials..."
    
    # Check if validation script exists
    if [[ -f "scripts/validate_fogis_credentials.py" ]]; then
        log_info "Using credential validation script..."
        if python3 scripts/validate_fogis_credentials.py; then
            log_success "FOGIS credentials validated successfully"
            return 0
        else
            log_warning "FOGIS credential validation failed"
            log_info "This may be due to network issues or incorrect credentials"
            return 1
        fi
    else
        log_warning "Credential validation script not found"
        log_info "Skipping credential validation"
        return 0
    fi
}

# Main restoration function
restore_credentials() {
    local backup_dir="$1"
    local auto_mode="$2"
    local validate="$3"
    local dry_run="$4"
    
    log_info "Starting FOGIS credential restoration..."
    echo "📁 Backup directory: $backup_dir"
    echo "🤖 Auto mode: $auto_mode"
    echo "✅ Validate: $validate"
    echo "🔍 Dry run: $dry_run"
    echo ""
    
    # Extract credentials from backup
    if ! extract_credentials_from_backup "$backup_dir"; then
        return 1
    fi
    
    # Confirm restoration unless in auto mode
    if [[ "$auto_mode" != "true" && "$dry_run" != "true" ]]; then
        echo ""
        read -p "Proceed with credential restoration? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            log_info "Credential restoration cancelled by user"
            return 0
        fi
    fi
    
    # Update .env file
    if ! update_env_file ".env" "$dry_run"; then
        return 1
    fi
    
    # Validate credentials if requested and not in dry run mode
    if [[ "$validate" == "true" && "$dry_run" != "true" ]]; then
        validate_credentials
    fi
    
    if [[ "$dry_run" != "true" ]]; then
        log_success "FOGIS credential restoration completed successfully!"
        echo ""
        echo "📋 Next steps:"
        echo "  • Restart FOGIS services: ./manage_fogis_system.sh restart"
        echo "  • Check service status: ./manage_fogis_system.sh status"
        echo "  • Test system: ./manage_fogis_system.sh test"
    else
        log_info "Dry run completed - no changes made"
    fi
    
    return 0
}

# Parse command line arguments
BACKUP_DIR=""
AUTO_MODE="false"
VALIDATE="false"
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --auto)
            AUTO_MODE="true"
            shift
            ;;
        --validate)
            VALIDATE="true"
            shift
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        -*)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            if [[ -z "$BACKUP_DIR" ]]; then
                BACKUP_DIR="$1"
            else
                log_error "Multiple backup directories specified"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Main execution
main() {
    echo "🔐 FOGIS Credential Restoration Tool"
    echo "===================================="
    echo ""
    
    # Auto-detect backup directory if not provided
    if [[ -z "$BACKUP_DIR" ]]; then
        log_info "No backup directory specified, attempting auto-detection..."
        BACKUP_DIR=$(detect_backup_directories)
        if [[ $? -ne 0 ]]; then
            log_error "No backup directory found and none specified"
            echo ""
            show_usage
            exit 1
        fi
        log_success "Auto-detected backup directory: $BACKUP_DIR"
        echo ""
    fi
    
    # Validate backup directory
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_error "Backup directory not found: $BACKUP_DIR"
        exit 1
    fi
    
    if [[ ! -f "$BACKUP_DIR/FOGIS_CREDENTIALS.txt" ]]; then
        log_error "FOGIS credentials file not found in backup directory"
        log_info "Expected: $BACKUP_DIR/FOGIS_CREDENTIALS.txt"
        exit 1
    fi
    
    # Perform credential restoration
    if restore_credentials "$BACKUP_DIR" "$AUTO_MODE" "$VALIDATE" "$DRY_RUN"; then
        exit 0
    else
        log_error "Credential restoration failed"
        exit 1
    fi
}

# Run main function
main "$@"
