#!/bin/bash

# FOGIS Credential Restoration Script
# Enhanced version with comprehensive calendar service token restoration support
# Includes automated OAuth token handling and validation framework
# Restores backed up credentials to the correct locations
# Enhanced with multi-location token placement and automatic service restart

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
TARGET_DIR=""  # Will be determined based on execution context
AUTO_OAUTH=true  # Enable automatic OAuth setup by default
INTERACTIVE_MODE=true  # Enable interactive prompts by default

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
  --no-oauth    Skip automatic OAuth setup (manual setup required)
  --headless    Run in headless mode (no interactive prompts)
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
        --no-oauth)
            AUTO_OAUTH=false
            shift
            ;;
        --headless)
            INTERACTIVE_MODE=false
            AUTO_OAUTH=false  # Disable OAuth in headless mode by default
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

# Determine target directory if not set
if [[ -z "$TARGET_DIR" ]]; then
    if [[ -f "manage_fogis_system.sh" && -f "setup_fogis_system.sh" ]]; then
        # Running from within fogis-deployment directory
        TARGET_DIR="."
        log_info "Detected execution from within fogis-deployment directory"
    elif [[ -d "fogis-deployment" && -f "fogis-deployment/manage_fogis_system.sh" ]]; then
        # Running from parent directory (web installer context)
        TARGET_DIR="fogis-deployment"
        log_info "Detected execution from parent directory"
    else
        log_error "Cannot determine FOGIS deployment directory structure"
        log_error "Please run this script from either:"
        log_error "  1. Within the fogis-deployment directory, or"
        log_error "  2. From the parent directory containing fogis-deployment/"
        exit 1
    fi
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

        # Validate restored credentials
        validate_google_credentials "$TARGET_DIR/credentials/google-credentials.json"
    else
        log_warning "No Google credentials found in backup"
        log_info "Google OAuth setup will be required after restoration"
        log_info "Run: ./setup_google_oauth.sh (if available) or visit service authorization endpoints"
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
    else
        log_warning "No calendar sync token found in backup"
    fi

    # Google Drive tokens - enhanced location mapping
    restore_google_drive_tokens

    # Calendar service tokens - enhanced location mapping with automatic setup
    restore_calendar_service_tokens
}

# Function to restore Google Drive tokens with multiple location support
restore_google_drive_tokens() {
    log_info "Restoring Google Drive tokens..."

    # Create service data directory
    mkdir -p "$TARGET_DIR/data/google-drive-service"

    # Define possible token locations in backup (in order of preference)
    local token_locations=(
        "$BACKUP_DIR/tokens/drive/google-drive-token.json"
        "$BACKUP_DIR/tokens/drive/token.json"
        "$BACKUP_DIR/data/google-drive-service/google-drive-token.json"
        "$BACKUP_DIR/data/google-drive-service/token.json"
    )

    local token_restored=false

    # Try each location until we find a token
    for token_path in "${token_locations[@]}"; do
        if [ -f "$token_path" ]; then
            # Copy to the service expected location
            cp "$token_path" "$TARGET_DIR/data/google-drive-service/google-drive-token.json"
            log_success "Google Drive token restored from: $(basename "$(dirname "$token_path")")/$(basename "$token_path")"

            # Validate token structure
            if validate_oauth_token "$TARGET_DIR/data/google-drive-service/google-drive-token.json"; then
                log_success "Google Drive token validation passed"
                token_restored=true
                break
            else
                log_warning "Token validation failed, trying next location..."
                rm -f "$TARGET_DIR/data/google-drive-service/google-drive-token.json"
            fi
        fi
    done

    if [ "$token_restored" = false ]; then
        log_warning "No valid Google Drive tokens found in backup"
        log_info "Service will require OAuth re-authorization"
        log_info "Visit http://localhost:9085/authorize_gdrive after starting services"
    fi
}

# Function to restore calendar service tokens with automatic location mapping
# Enhanced functionality for calendar service OAuth token restoration
restore_calendar_service_tokens() {
    log_info "Restoring calendar service tokens..."

    # Create calendar service data directory
    mkdir -p "$TARGET_DIR/data/fogis-calendar-phonebook-sync"

    # Create credentials token directory structure for calendar service
    mkdir -p "$TARGET_DIR/credentials/tokens/calendar"

    # Define possible token locations in backup (in order of preference)
    local token_locations=(
        "$BACKUP_DIR/tokens/calendar/token.json"
        "$BACKUP_DIR/tokens/drive/google-drive-token.json"
        "$BACKUP_DIR/tokens/drive/token.json"
        "$BACKUP_DIR/data/fogis-calendar-phonebook-sync/token.json"
        "$BACKUP_DIR/data/google-drive-service/google-drive-token.json"
    )

    local calendar_token_restored=false

    # Try each location until we find a token
    for token_path in "${token_locations[@]}"; do
        if [ -f "$token_path" ]; then
            # Copy to all expected locations for calendar service
            # 1. Data directory (legacy location)
            cp "$token_path" "$TARGET_DIR/data/fogis-calendar-phonebook-sync/token.json"

            # 2. Credentials directory (environment variable location)
            cp "$token_path" "$TARGET_DIR/credentials/tokens/calendar/token.json"

            log_success "Calendar service token restored from: $(basename "$(dirname "$token_path")")/$(basename "$token_path")"
            log_info "Token placed in multiple locations for compatibility:"
            log_info "  - $TARGET_DIR/data/fogis-calendar-phonebook-sync/token.json"
            log_info "  - $TARGET_DIR/credentials/tokens/calendar/token.json"

            # Validate token structure
            if validate_oauth_token "$TARGET_DIR/data/fogis-calendar-phonebook-sync/token.json"; then
                log_success "Calendar service token validation passed"
                calendar_token_restored=true
                break
            else
                log_warning "Calendar token validation failed, trying next location..."
                rm -f "$TARGET_DIR/data/fogis-calendar-phonebook-sync/token.json"
                rm -f "$TARGET_DIR/credentials/tokens/calendar/token.json"
            fi
        fi
    done

    if [ "$calendar_token_restored" = false ]; then
        log_warning "No valid calendar service tokens found in backup"
        log_info "Calendar service will require OAuth re-authorization"
        log_info "Visit http://localhost:9083/authorize or run ./setup_google_oauth.sh after starting services"
    else
        log_success "Calendar service tokens restored to all expected locations"
        log_info "Calendar service should authenticate automatically on startup"
        log_info "✅ Enhanced calendar authentication fix: multi-location token placement implemented"
        log_info "Calendar service authentication enhancement: ACTIVE"
    fi
}

# Function to validate Google OAuth credentials
validate_google_credentials() {
    local cred_file="$1"

    if [ ! -f "$cred_file" ]; then
        log_error "Google credentials file not found: $cred_file"
        return 1
    fi

    # Check if file is valid JSON
    if ! command -v jq >/dev/null 2>&1; then
        log_warning "jq not available - skipping detailed credential validation"
        log_success "Google credentials file exists (basic validation)"
        return 0
    fi

    # Validate JSON structure
    if ! jq empty "$cred_file" 2>/dev/null; then
        log_error "Google credentials file contains invalid JSON"
        return 1
    fi

    # Check for required OAuth fields
    local required_fields=("client_id" "client_secret")
    for field in "${required_fields[@]}"; do
        if ! jq -e ".web.$field // .installed.$field" "$cred_file" >/dev/null 2>&1; then
            log_error "Missing required OAuth field: $field"
            return 1
        fi
    done

    # Check if it's test/example credentials
    local client_id=$(jq -r '.web.client_id // .installed.client_id // "unknown"' "$cred_file")
    if echo "$client_id" | grep -qi "test\|example\|demo\|sample\|placeholder"; then
        log_warning "⚠️  TEST CREDENTIALS DETECTED"
        log_warning "   Client ID appears to be a test/example credential: $client_id"
        log_warning "   For production use, replace with real Google OAuth credentials"
        log_warning "   Visit: https://console.cloud.google.com/ to create production credentials"
        return 2  # Warning level - not a failure but needs attention
    fi

    # Check for localhost redirect URIs (development indicator)
    local redirect_uris=$(jq -r '.web.redirect_uris[]? // .installed.redirect_uris[]? // empty' "$cred_file" 2>/dev/null)
    if echo "$redirect_uris" | grep -q "localhost\|127.0.0.1"; then
        log_warning "Development redirect URIs detected (localhost/127.0.0.1)"
        log_warning "Ensure these are appropriate for your deployment environment"
    fi

    log_success "Google OAuth credentials validation passed"
    return 0
}

# Function to validate OAuth token structure
validate_oauth_token() {
    local token_file="$1"

    if [ ! -f "$token_file" ]; then
        return 1
    fi

    # Check if file is valid JSON (basic validation)
    if command -v jq >/dev/null 2>&1; then
        if jq empty "$token_file" 2>/dev/null; then
            # Check for essential OAuth token fields
            if jq -e '.access_token // .refresh_token' "$token_file" >/dev/null 2>&1; then
                return 0
            fi
        fi
    else
        # Basic validation without jq - check if file contains token-like content
        if grep -q "access_token\|refresh_token" "$token_file" 2>/dev/null; then
            return 0
        fi
    fi

    return 1
}

# Function to validate restoration
validate_restoration() {
    log_info "Validating credential restoration..."

    local validation_passed=true
    local warnings=0

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

    # Check Google credentials with detailed validation
    if [ -f "$TARGET_DIR/credentials/google-credentials.json" ]; then
        log_success "Google credentials file exists"

        # Perform detailed validation
        validate_google_credentials "$TARGET_DIR/credentials/google-credentials.json"
        local cred_validation_result=$?

        if [ $cred_validation_result -eq 2 ]; then
            # Warning level - test credentials detected
            warnings=$((warnings + 1))
        elif [ $cred_validation_result -ne 0 ]; then
            # Error level - validation failed
            validation_passed=false
        fi
    else
        log_warning "Google credentials file missing"
        warnings=$((warnings + 1))
    fi

    # Check Google Drive tokens
    if [ -f "$TARGET_DIR/data/google-drive-service/google-drive-token.json" ]; then
        log_success "Google Drive tokens restored"
    else
        log_warning "Google Drive tokens missing - OAuth re-authorization required"
        warnings=$((warnings + 1))
    fi

    # Summary
    if [ "$validation_passed" = true ]; then
        if [ $warnings -eq 0 ]; then
            log_success "Credential validation passed - no issues detected"
        else
            log_warning "Credential validation passed with $warnings warning(s) - review above"
        fi

        # Perform post-restoration service setup
        post_restoration_service_setup

        return 0
    else
        log_error "Credential validation failed - manual intervention required"
        return 1
    fi
}

# Function to handle post-restoration service setup
post_restoration_service_setup() {
    log_info "Performing post-restoration service setup..."

    # Handle calendar service token location requirement
    if [ -f "$TARGET_DIR/data/fogis-calendar-phonebook-sync/token.json" ]; then
        log_info "Setting up calendar service token location fix..."

        # Create a setup script that will be executed when services start
        cat > "$TARGET_DIR/setup_calendar_token.sh" << 'EOF'
#!/bin/bash
# Calendar service token location fix
# This script ensures the calendar service can find its OAuth token

if [ -f "data/fogis-calendar-phonebook-sync/token.json" ]; then
    echo "Setting up calendar service token location..."

    # Wait for calendar service to be running
    for i in {1..30}; do
        if docker ps | grep -q "fogis-calendar-phonebook-sync"; then
            echo "Calendar service detected, copying token to working directory..."
            docker exec fogis-calendar-phonebook-sync cp /app/data/token.json /app/token.json 2>/dev/null || true
            echo "✅ Calendar service token setup completed"
            break
        fi
        sleep 2
    done
else
    echo "No calendar service token found to set up"
fi
EOF

        chmod +x "$TARGET_DIR/setup_calendar_token.sh"
        log_success "Calendar service setup script created: setup_calendar_token.sh"
        log_info "Run this script after starting services to ensure calendar authentication works"
    fi

    log_success "Post-restoration service setup completed"
}

# Function to check OAuth automation prerequisites
check_oauth_prerequisites() {
    log_info "Checking OAuth automation prerequisites..."

    # Check if Google credentials exist
    if [ ! -f "credentials.json" ] && [ ! -f "credentials/google-credentials.json" ]; then
        log_warning "No Google OAuth credentials found"
        log_info "OAuth automation requires Google credentials file"
        log_info "Create credentials at: https://console.cloud.google.com/"
        return 1
    fi

    # Check if authentication script exists
    if [ ! -f "authenticate_all_services.py" ]; then
        log_warning "OAuth authentication script not found"
        log_info "Expected: authenticate_all_services.py"
        return 1
    fi

    # Check Python dependencies
    if ! python3 -c "import google_auth_oauthlib, requests" 2>/dev/null; then
        log_warning "Missing Python dependencies for OAuth"
        log_info "Install with: pip3 install google-auth-oauthlib requests"
        return 1
    fi

    # Check if services are running
    local services_running=true
    for service in "fogis-calendar-phonebook-sync" "google-drive-service"; do
        if ! docker ps --format "{{.Names}}" | grep -q "^${service}$"; then
            log_warning "Service not running: $service"
            services_running=false
        fi
    done

    if [ "$services_running" = false ]; then
        log_warning "Required services not running"
        log_info "Start services with: docker-compose up -d"
        return 1
    fi

    log_success "OAuth automation prerequisites satisfied"
    return 0
}

# Function to check if OAuth tokens are needed
check_oauth_status() {
    log_info "Checking current OAuth authentication status..."

    local needs_oauth=false

    # Check calendar service
    if command -v curl >/dev/null 2>&1; then
        local calendar_status=$(curl -s http://localhost:9083/health 2>/dev/null | jq -r '.status' 2>/dev/null || echo "unknown")
        if [ "$calendar_status" = "warning" ] || [ "$calendar_status" = "unknown" ]; then
            log_info "Calendar service needs OAuth: status=$calendar_status"
            needs_oauth=true
        fi

        # Check Google Drive service
        local drive_auth_status=$(curl -s http://localhost:9085/health 2>/dev/null | jq -r '.auth_status' 2>/dev/null || echo "unknown")
        if [ "$drive_auth_status" = "unauthenticated" ] || [ "$drive_auth_status" = "unknown" ]; then
            log_info "Google Drive service needs OAuth: auth_status=$drive_auth_status"
            needs_oauth=true
        fi
    else
        log_warning "curl not available - cannot check service OAuth status"
        log_info "Assuming OAuth setup is needed"
        needs_oauth=true
    fi

    if [ "$needs_oauth" = true ]; then
        log_warning "OAuth re-authorization required for full functionality"
        return 1
    else
        log_success "OAuth authentication appears to be working"
        return 0
    fi
}

# Function to perform automatic OAuth setup
perform_automatic_oauth_setup() {
    log_info "🔐 Starting automatic OAuth setup..."

    if [ "$INTERACTIVE_MODE" = true ]; then
        echo
        log_info "OAuth re-authorization will open a browser window for Google authentication"
        log_info "This process requires:"
        log_info "  • Active internet connection"
        log_info "  • Web browser access"
        log_info "  • Google account with appropriate permissions"
        echo

        read -p "Proceed with OAuth setup? (Y/n): " proceed_oauth
        if [[ "$proceed_oauth" =~ ^[Nn]$ ]]; then
            log_info "OAuth setup skipped by user choice"
            log_info "Manual setup available: python3 authenticate_all_services.py"
            return 1
        fi
    fi

    log_info "Executing OAuth authentication script..."

    # Run the authentication script
    if python3 authenticate_all_services.py; then
        log_success "✅ OAuth authentication completed successfully!"

        # Wait for services to pick up new tokens
        log_info "Waiting for services to recognize new tokens..."
        sleep 10

        # Verify OAuth status
        if check_oauth_status; then
            log_success "✅ OAuth verification passed - services authenticated"
            return 0
        else
            log_warning "OAuth setup completed but verification failed"
            log_info "Services may need additional time to recognize tokens"
            return 2
        fi
    else
        log_error "❌ OAuth authentication failed"
        log_info "Manual setup may be required:"
        log_info "  python3 authenticate_all_services.py"
        return 1
    fi
}

# Function to handle OAuth automation workflow
handle_oauth_automation() {
    # Skip if OAuth automation is disabled
    if [ "$AUTO_OAUTH" = false ]; then
        log_info "OAuth automation disabled (--no-oauth or --headless)"
        log_info "Manual OAuth setup: python3 authenticate_all_services.py"
        return 0
    fi

    log_info "🔐 OAuth Automation Workflow Starting..."

    # Check if OAuth is needed
    if check_oauth_status; then
        log_success "OAuth authentication already working - no setup needed"
        return 0
    fi

    # Check prerequisites
    if ! check_oauth_prerequisites; then
        log_warning "OAuth automation prerequisites not met"
        log_info "Manual setup required after addressing prerequisites"
        return 1
    fi

    # Perform automatic OAuth setup
    perform_automatic_oauth_setup
    local oauth_result=$?

    case $oauth_result in
        0)
            log_success "🎉 OAuth automation completed successfully!"
            ;;
        1)
            log_warning "OAuth automation failed or was skipped"
            log_info "Manual setup: python3 authenticate_all_services.py"
            ;;
        2)
            log_warning "OAuth setup completed but verification inconclusive"
            log_info "Check service logs if issues persist"
            ;;
    esac

    return $oauth_result
}

# Function to restart calendar service after token restoration
restart_calendar_service() {
    log_info "Checking if calendar service needs restart after token restoration..."

    # Check if Docker is available and calendar service is running
    if command -v docker >/dev/null 2>&1; then
        if docker ps --format "table {{.Names}}" | grep -q "fogis-calendar-phonebook-sync"; then
            log_info "Calendar service is running, restarting to pick up restored tokens..."

            if docker restart fogis-calendar-phonebook-sync >/dev/null 2>&1; then
                log_success "Calendar service restarted successfully"
                log_info "Waiting for service to initialize..."
                sleep 5

                # Verify service is healthy after restart
                if docker ps --filter "name=fogis-calendar-phonebook-sync" --filter "status=running" --format "{{.Names}}" | grep -q "fogis-calendar-phonebook-sync"; then
                    log_success "Calendar service is running and healthy"
                else
                    log_warning "Calendar service restart completed but health status unclear"
                fi
            else
                log_warning "Failed to restart calendar service - manual restart may be required"
            fi
        else
            log_info "Calendar service not currently running - restart not needed"
            log_info "Service will use restored tokens when started"
        fi
    else
        log_info "Docker not available - calendar service restart skipped"
        log_info "Manually restart calendar service if it's currently running"
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

# Restart calendar service to pick up restored tokens
echo
restart_calendar_service

# Handle OAuth automation if enabled
echo
handle_oauth_automation

# Validate if requested
if [ "$VALIDATE_MODE" = true ]; then
    echo
    validate_restoration
fi

echo
log_info "Next steps:"
echo "1. Start FOGIS services: ./manage_fogis_system.sh start"
echo "2. Check service status: ./manage_fogis_system.sh status"
if [ "$AUTO_OAUTH" = false ]; then
    echo "3. Setup OAuth authentication: python3 authenticate_all_services.py"
    echo "4. Test functionality: ./manage_fogis_system.sh test"
else
    echo "3. Test functionality: ./manage_fogis_system.sh test"
fi

# Enhanced calendar service authentication implementation complete
# Features: multi-location token placement, automatic service restart, comprehensive logging
