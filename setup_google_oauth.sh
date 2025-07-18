#!/bin/bash

# Google OAuth Setup Script for FOGIS Deployment
# Guides users through setting up Google OAuth credentials and completing the authorization flow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
CREDENTIALS_FILE="credentials/google-credentials.json"
GOOGLE_DRIVE_SERVICE_PORT=9085
CALENDAR_SYNC_SERVICE_PORT=9084

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

log_step() {
    echo -e "${CYAN}🔧 $1${NC}"
}

# Function to show usage
show_usage() {
    cat << EOF
Google OAuth Setup Script for FOGIS

Usage: $0 [OPTIONS]

Options:
  --check-only    Only check current OAuth status, don't setup
  --auto-start    Automatically start services if not running
  --help          Show this help message

This script will:
1. Check for existing Google OAuth credentials
2. Guide you through creating credentials if missing
3. Start necessary services
4. Walk you through the OAuth authorization flow
5. Verify successful authentication

EOF
}

# Parse command line arguments
CHECK_ONLY=false
AUTO_START=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        --auto-start)
            AUTO_START=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Function to check if services are running
check_service_status() {
    local service_name="$1"
    local port="$2"
    
    if docker ps --format "table {{.Names}}" | grep -q "^$service_name$"; then
        if curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
            return 0  # Service running and responding
        else
            return 1  # Service running but not responding
        fi
    else
        return 2  # Service not running
    fi
}

# Function to check OAuth status
check_oauth_status() {
    log_step "Checking current OAuth status..."
    
    # Check Google Drive service
    if check_service_status "google-drive-service" "$GOOGLE_DRIVE_SERVICE_PORT"; then
        local auth_status=$(curl -s "http://localhost:$GOOGLE_DRIVE_SERVICE_PORT/health" | jq -r '.auth_status // "unknown"' 2>/dev/null || echo "unknown")
        
        case $auth_status in
            "authenticated")
                log_success "Google Drive service: OAuth authenticated ✓"
                return 0
                ;;
            "unauthenticated")
                log_warning "Google Drive service: OAuth authentication required"
                return 1
                ;;
            *)
                log_warning "Google Drive service: OAuth status unknown"
                return 1
                ;;
        esac
    else
        log_warning "Google Drive service: Not running or not responding"
        return 2
    fi
}

# Function to validate Google credentials
validate_credentials() {
    log_step "Validating Google OAuth credentials..."
    
    if [ ! -f "$CREDENTIALS_FILE" ]; then
        log_error "Google credentials file missing: $CREDENTIALS_FILE"
        return 1
    fi
    
    # Check if jq is available for validation
    if ! command -v jq >/dev/null 2>&1; then
        log_warning "jq not available - performing basic validation only"
        log_success "Google credentials file exists"
        return 0
    fi
    
    # Validate JSON structure
    if ! jq empty "$CREDENTIALS_FILE" 2>/dev/null; then
        log_error "Google credentials file contains invalid JSON"
        return 1
    fi
    
    # Check for required fields
    local client_id=$(jq -r '.web.client_id // .installed.client_id // "missing"' "$CREDENTIALS_FILE")
    local client_secret=$(jq -r '.web.client_secret // .installed.client_secret // "missing"' "$CREDENTIALS_FILE")
    
    if [ "$client_id" = "missing" ] || [ "$client_secret" = "missing" ]; then
        log_error "Missing required OAuth fields (client_id or client_secret)"
        return 1
    fi
    
    # Check for test credentials
    if echo "$client_id" | grep -qi "test\|example\|demo\|sample"; then
        log_warning "Test/example credentials detected"
        log_warning "For production use, create real Google OAuth credentials"
        return 2  # Warning level
    fi
    
    log_success "Google OAuth credentials validation passed"
    return 0
}

# Function to guide credential creation
guide_credential_creation() {
    log_step "Setting up Google OAuth credentials..."
    echo
    echo "To set up Google OAuth for FOGIS, you need to:"
    echo
    echo "1. 🌐 Visit Google Cloud Console:"
    echo "   https://console.cloud.google.com/"
    echo
    echo "2. 📁 Create or select a project:"
    echo "   - Click 'Select a project' → 'New Project'"
    echo "   - Name: 'FOGIS-OAuth' (or your preferred name)"
    echo "   - Click 'Create'"
    echo
    echo "3. 🔌 Enable required APIs:"
    echo "   - Go to 'APIs & Services' → 'Library'"
    echo "   - Search and enable: 'Google Drive API'"
    echo "   - Search and enable: 'Google Calendar API'"
    echo "   - Search and enable: 'People API' (for contacts)"
    echo
    echo "4. 🔑 Create OAuth 2.0 credentials:"
    echo "   - Go to 'APIs & Services' → 'Credentials'"
    echo "   - Click '+ CREATE CREDENTIALS' → 'OAuth client ID'"
    echo "   - Application type: 'Web application'"
    echo "   - Name: 'FOGIS Services'"
    echo "   - Authorized redirect URIs:"
    echo "     - http://localhost:$GOOGLE_DRIVE_SERVICE_PORT/oauth2callback"
    echo "     - http://localhost:$CALENDAR_SYNC_SERVICE_PORT/oauth2callback"
    echo "   - Click 'Create'"
    echo
    echo "5. 💾 Download credentials:"
    echo "   - Click the download button (⬇️) next to your new OAuth client"
    echo "   - Save the file as: $CREDENTIALS_FILE"
    echo
    
    read -p "Press Enter when you have completed these steps and saved the credentials file..."
    
    if [ -f "$CREDENTIALS_FILE" ]; then
        log_success "Credentials file detected!"
        validate_credentials
        return $?
    else
        log_error "Credentials file not found: $CREDENTIALS_FILE"
        log_info "Please ensure you've saved the downloaded file to the correct location"
        return 1
    fi
}

# Function to start services
start_services() {
    log_step "Starting FOGIS services..."
    
    # Check if docker-compose is available
    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "docker-compose not found"
        log_info "Please install docker-compose or start services manually"
        return 1
    fi
    
    # Start Google Drive service
    docker-compose up -d google-drive-service
    
    # Wait for service to be ready
    log_info "Waiting for Google Drive service to start..."
    local attempts=0
    while [ $attempts -lt 30 ]; do
        if check_service_status "google-drive-service" "$GOOGLE_DRIVE_SERVICE_PORT"; then
            log_success "Google Drive service is running"
            break
        fi
        sleep 2
        attempts=$((attempts + 1))
    done
    
    if [ $attempts -eq 30 ]; then
        log_error "Google Drive service failed to start within 60 seconds"
        log_info "Check service logs: docker logs google-drive-service"
        return 1
    fi
    
    return 0
}

# Function to perform OAuth authorization
perform_oauth_authorization() {
    log_step "Starting OAuth authorization flow..."
    echo
    echo "🌐 OAuth Authorization Required"
    echo "================================"
    echo
    echo "1. Open your web browser and visit:"
    echo "   ${CYAN}http://localhost:$GOOGLE_DRIVE_SERVICE_PORT/authorize_gdrive${NC}"
    echo
    echo "2. You will be redirected to Google's authorization page"
    echo "3. Sign in with your Google account"
    echo "4. Grant the requested permissions:"
    echo "   - View and manage your Google Drive files"
    echo "   - View and edit your Google Calendar"
    echo "   - View your contacts"
    echo "5. You will be redirected back to the FOGIS service"
    echo "6. Look for a success message"
    echo
    
    if command -v open >/dev/null 2>&1; then
        read -p "Press Enter to open the authorization URL automatically, or Ctrl+C to open manually: "
        open "http://localhost:$GOOGLE_DRIVE_SERVICE_PORT/authorize_gdrive"
    else
        read -p "Press Enter after completing the OAuth authorization in your browser..."
    fi
    
    # Wait for authentication to complete
    log_info "Waiting for OAuth authorization to complete..."
    local attempts=0
    while [ $attempts -lt 60 ]; do  # Wait up to 2 minutes
        local auth_status=$(curl -s "http://localhost:$GOOGLE_DRIVE_SERVICE_PORT/health" | jq -r '.auth_status // "unknown"' 2>/dev/null || echo "unknown")
        
        if [ "$auth_status" = "authenticated" ]; then
            log_success "OAuth authorization completed successfully!"
            return 0
        fi
        
        sleep 2
        attempts=$((attempts + 1))
        
        # Show progress every 10 attempts (20 seconds)
        if [ $((attempts % 10)) -eq 0 ]; then
            log_info "Still waiting for authorization... ($((attempts * 2)) seconds elapsed)"
        fi
    done
    
    log_error "OAuth authorization timed out after 2 minutes"
    log_info "Please check that you completed the authorization flow in your browser"
    return 1
}

# Main setup function
main() {
    echo "=== Google OAuth Setup for FOGIS ==="
    echo
    
    # Check if we're in the right directory
    if [ ! -f "docker-compose.yml" ]; then
        log_error "docker-compose.yml not found"
        log_info "Please run this script from the FOGIS deployment directory"
        exit 1
    fi
    
    # Create credentials directory if it doesn't exist
    mkdir -p "$(dirname "$CREDENTIALS_FILE")"
    
    # If check-only mode, just check status and exit
    if [ "$CHECK_ONLY" = true ]; then
        check_oauth_status
        exit $?
    fi
    
    # Step 1: Check existing credentials
    if validate_credentials; then
        log_success "Google OAuth credentials are valid"
    else
        local validation_result=$?
        if [ $validation_result -eq 1 ]; then
            # Missing or invalid credentials
            guide_credential_creation || exit 1
        elif [ $validation_result -eq 2 ]; then
            # Test credentials detected
            log_warning "Test credentials detected - consider updating for production use"
        fi
    fi
    
    # Step 2: Check service status
    local oauth_status_result=0
    check_oauth_status || oauth_status_result=$?
    
    if [ $oauth_status_result -eq 0 ]; then
        log_success "OAuth is already configured and working!"
        log_info "No further setup required"
        exit 0
    elif [ $oauth_status_result -eq 2 ] || [ "$AUTO_START" = true ]; then
        # Service not running or auto-start requested
        start_services || exit 1
    fi
    
    # Step 3: Perform OAuth authorization if needed
    check_oauth_status || {
        perform_oauth_authorization || exit 1
    }
    
    # Step 4: Final verification
    echo
    log_step "Performing final verification..."
    if check_oauth_status; then
        echo
        log_success "🎉 Google OAuth setup completed successfully!"
        echo
        log_info "Next steps:"
        echo "  • Start all FOGIS services: ./manage_fogis_system.sh start"
        echo "  • Check system status: ./manage_fogis_system.sh status"
        echo "  • Test functionality: ./manage_fogis_system.sh test"
    else
        echo
        log_error "OAuth setup verification failed"
        log_info "Please check service logs and try again:"
        echo "  • Google Drive service logs: docker logs google-drive-service"
        echo "  • Retry setup: $0"
        exit 1
    fi
}

# Run main function
main "$@"
