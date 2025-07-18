#!/bin/bash

# FOGIS Credential Restoration Script
# Restores backed up credentials to the correct locations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
AUTO_MODE=false
VALIDATE_MODE=false
BACKUP_DIR=""
TARGET_DIR="fogis-deployment"

# Function to print colored output
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
    cat << EOF
FOGIS Credential Restoration Script

Usage: $0 [BACKUP_DIR] [OPTIONS]

Arguments:
  BACKUP_DIR    Path to the credential backup directory (optional if auto-detect)

Options:
  --auto        Run in automatic mode (no prompts)
  --validate    Validate restored credentials
  --target DIR  Target directory (default: fogis-deployment)
  --help        Show this help message

Examples:
  # Auto-detect latest backup and restore automatically
  $0 --auto --validate

  # Restore specific backup
  $0 fogis-credentials-backup-20250718-114747 --auto

  # Interactive restoration with validation
  $0 --validate

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --auto)
            AUTO_MODE=true
            shift
            ;;
        --validate)
            VALIDATE_MODE=true
            shift
            ;;
        --target)
            TARGET_DIR="$2"
            shift 2
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
            if [ -z "$BACKUP_DIR" ]; then
                BACKUP_DIR="$1"
            else
                log_error "Multiple backup directories specified"
                exit 1
            fi
            shift
            ;;
    esac
done

# Function to find latest backup if not specified
find_latest_backup() {
    local latest_backup=""
    local latest_timestamp=0
    
    for backup in fogis-credentials-backup-*; do
        if [ -d "$backup" ]; then
            # Extract timestamp from directory name
            timestamp=$(echo "$backup" | sed 's/fogis-credentials-backup-//' | sed 's/-//')
            if [ "$timestamp" -gt "$latest_timestamp" ]; then
                latest_timestamp="$timestamp"
                latest_backup="$backup"
            fi
        fi
    done
    
    echo "$latest_backup"
}

# Auto-detect backup directory if not provided
if [ -z "$BACKUP_DIR" ]; then
    log_info "Auto-detecting latest credential backup..."
    BACKUP_DIR=$(find_latest_backup)
    if [ -z "$BACKUP_DIR" ]; then
        log_error "No credential backup directories found"
        log_info "Looking for directories matching: fogis-credentials-backup-*"
        exit 1
    fi
    log_success "Found latest backup: $BACKUP_DIR"
fi

# Validate backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    log_error "Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Validate target directory exists
if [ ! -d "$TARGET_DIR" ]; then
    log_error "Target directory not found: $TARGET_DIR"
    log_info "Please ensure you're running this from the correct location"
    exit 1
fi

log_info "Starting FOGIS credential restoration..."
log_info "Backup source: $BACKUP_DIR"
log_info "Target directory: $TARGET_DIR"
echo

# Function to restore .env file
restore_env_file() {
    log_info "Restoring .env file..."
    
    if [ -f "$BACKUP_DIR/env/fogis.env" ]; then
        cp "$BACKUP_DIR/env/fogis.env" "$TARGET_DIR/.env"
        log_success ".env file restored to $TARGET_DIR/.env"
        
        # Validate credentials are present
        if grep -q "FOGIS_USERNAME" "$TARGET_DIR/.env" && grep -q "FOGIS_PASSWORD" "$TARGET_DIR/.env"; then
            log_success "FOGIS credentials found in restored .env file"
        else
            log_warning "FOGIS credentials not found in restored .env file"
        fi
    else
        log_warning "No .env backup found at $BACKUP_DIR/env/fogis.env"
        
        # Try to create .env from FOGIS_CREDENTIALS.txt
        if [ -f "$BACKUP_DIR/FOGIS_CREDENTIALS.txt" ]; then
            log_info "Attempting to create .env from FOGIS_CREDENTIALS.txt..."
            
            # Extract credentials
            username=$(grep "FOGIS_USERNAME=" "$BACKUP_DIR/FOGIS_CREDENTIALS.txt" 2>/dev/null || echo "")
            password=$(grep "FOGIS_PASSWORD=" "$BACKUP_DIR/FOGIS_CREDENTIALS.txt" 2>/dev/null || echo "")
            referee_num=$(grep "USER_REFEREE_NUMBER=" "$BACKUP_DIR/FOGIS_CREDENTIALS.txt" 2>/dev/null || echo "")
            
            if [ -n "$username" ] && [ -n "$password" ]; then
                cat > "$TARGET_DIR/.env" << EOF
# FOGIS Credentials (restored from backup)
$username
$password
$referee_num

# Google OAuth Configuration
GOOGLE_CREDENTIALS_FILE=/app/credentials/google-credentials.json
GOOGLE_CALENDAR_TOKEN_FILE=/app/credentials/tokens/calendar/token.json
GOOGLE_DRIVE_TOKEN_FILE=/app/credentials/tokens/drive/token.json

# Service Configuration
FOGIS_API_CLIENT_PORT=9086
TEAM_LOGO_COMBINER_PORT=9088
GOOGLE_DRIVE_SERVICE_PORT=9085
CALENDAR_SYNC_PORT=9084
MATCH_CHANGE_DETECTOR_PORT=9080

# Logging
LOG_LEVEL=INFO
EOF
                log_success ".env file created from backup credentials"
            else
                log_warning "Could not extract valid credentials from backup"
            fi
        fi
    fi
}

# Function to restore Google credentials
restore_google_credentials() {
    log_info "Restoring Google OAuth credentials..."
    
    # Create credentials directory if it doesn't exist
    mkdir -p "$TARGET_DIR/credentials"
    
    if [ -f "$BACKUP_DIR/credentials/google-credentials.json" ]; then
        cp "$BACKUP_DIR/credentials/google-credentials.json" "$TARGET_DIR/credentials/"
        log_success "Google credentials restored"
    else
        log_warning "No Google credentials found in backup"
    fi
}

# Function to restore OAuth tokens
restore_oauth_tokens() {
    log_info "Restoring OAuth tokens..."
    
    # Calendar sync token
    if [ -f "$BACKUP_DIR/tokens/calendar/token.json" ]; then
        mkdir -p "$TARGET_DIR/data/fogis-calendar-phonebook-sync"
        cp "$BACKUP_DIR/tokens/calendar/token.json" "$TARGET_DIR/data/fogis-calendar-phonebook-sync/"
        log_success "Calendar sync token restored"
    fi
    
    # Google Drive tokens
    if [ -f "$BACKUP_DIR/tokens/drive/google-drive-token.json" ]; then
        mkdir -p "$TARGET_DIR/data/google-drive-service"
        cp "$BACKUP_DIR/tokens/drive/google-drive-token.json" "$TARGET_DIR/data/google-drive-service/"
        log_success "Google Drive token restored"
    fi
    
    if [ -f "$BACKUP_DIR/tokens/drive/token.json" ]; then
        mkdir -p "$TARGET_DIR/data/google-drive-service"
        cp "$BACKUP_DIR/tokens/drive/token.json" "$TARGET_DIR/data/google-drive-service/"
        log_success "Google Drive service token restored"
    fi
}

# Function to validate restoration
validate_restoration() {
    log_info "Validating credential restoration..."
    
    local validation_passed=true
    
    # Check .env file
    if [ -f "$TARGET_DIR/.env" ]; then
        log_success ".env file exists"
        
        if grep -q "FOGIS_USERNAME" "$TARGET_DIR/.env" && grep -q "FOGIS_PASSWORD" "$TARGET_DIR/.env"; then
            log_success "FOGIS credentials present in .env"
        else
            log_warning "FOGIS credentials missing from .env"
            validation_passed=false
        fi
    else
        log_error ".env file missing"
        validation_passed=false
    fi
    
    # Check Google credentials
    if [ -f "$TARGET_DIR/credentials/google-credentials.json" ]; then
        log_success "Google credentials file exists"
    else
        log_warning "Google credentials file missing"
    fi
    
    # Test if services can start (if requested)
    if [ "$validation_passed" = true ]; then
        log_success "Credential validation passed"
        return 0
    else
        log_warning "Credential validation failed"
        return 1
    fi
}

# Main restoration process
echo "=== FOGIS Credential Restoration ==="
echo "Backup: $BACKUP_DIR"
echo "Target: $TARGET_DIR"
echo

# Confirm restoration in interactive mode
if [ "$AUTO_MODE" = false ]; then
    echo "This will restore credentials to $TARGET_DIR"
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restoration cancelled"
        exit 0
    fi
fi

# Perform restoration
restore_env_file
restore_google_credentials
restore_oauth_tokens

echo
log_success "Credential restoration completed!"

# Validate if requested
if [ "$VALIDATE_MODE" = true ]; then
    echo
    validate_restoration
fi

echo
log_info "Next steps:"
echo "1. Start FOGIS services: ./manage_fogis_system.sh start"
echo "2. Check service status: ./manage_fogis_system.sh status"
echo "3. Test functionality: ./manage_fogis_system.sh test"
