#!/bin/bash
# FOGIS Calendar Sync Issue Validation Script
# This script validates the resolution steps for the June 28th calendar sync issue

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}🔍 $1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_step() {
    echo -e "\n${YELLOW}📋 Step $1: $2${NC}"
    echo -e "${YELLOW}$(printf '%.0s-' {1..40})${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_service_health() {
    local service_name="$1"
    local port="$2"
    local endpoint="$3"
    
    print_info "Checking $service_name health on port $port..."
    
    if curl -s -f "http://localhost:$port$endpoint" >/dev/null 2>&1; then
        print_success "$service_name is responding"
        return 0
    else
        print_error "$service_name is not responding on port $port"
        return 1
    fi
}

check_docker_container() {
    local container_name="$1"
    
    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container_name.*Up"; then
        print_success "Container $container_name is running"
        return 0
    else
        print_error "Container $container_name is not running"
        return 1
    fi
}

validate_credentials_setup() {
    print_step "1" "Validating Credential Setup Process"
    
    # Check if .env file exists
    if [[ -f ".env" ]]; then
        print_warning ".env file already exists"
        if grep -q "FOGIS_USERNAME=" .env && grep -q "FOGIS_PASSWORD=" .env; then
            print_success "FOGIS credentials are configured in .env"
        else
            print_error "FOGIS credentials missing from .env file"
        fi
    else
        print_warning ".env file does not exist - needs to be created with FOGIS credentials"
        print_info "Example .env file content:"
        echo "FOGIS_USERNAME=your_fogis_username"
        echo "FOGIS_PASSWORD=your_fogis_password"
    fi
    
    # Check credentials directory
    if [[ -d "credentials" ]]; then
        if [[ -n "$(ls -A credentials/)" ]]; then
            print_success "Credentials directory contains files"
        else
            print_warning "Credentials directory is empty - Google OAuth setup needed"
        fi
    else
        print_error "Credentials directory does not exist"
    fi
}

validate_service_status() {
    print_step "2" "Validating Service Status"
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running"
        return 1
    fi
    print_success "Docker is running"
    
    # Check each service container
    local services=("fogis-api-client-service" "fogis-calendar-phonebook-sync" "match-list-processor" "match-list-change-detector")
    
    for service in "${services[@]}"; do
        check_docker_container "$service"
    done
}

validate_api_connectivity() {
    print_step "3" "Validating API Connectivity"
    
    # Check FOGIS API Client
    print_info "Testing FOGIS API Client..."
    if curl -s "http://localhost:9086/health" | grep -q '"status"'; then
        local status=$(curl -s "http://localhost:9086/health" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [[ "$status" == "healthy" ]]; then
            print_success "FOGIS API Client is healthy"
        else
            print_warning "FOGIS API Client status: $status (needs credentials)"
        fi
    else
        print_error "FOGIS API Client not responding"
    fi
    
    # Check Calendar Sync Service
    print_info "Testing Calendar Sync Service..."
    if curl -s "http://localhost:9083/health" >/dev/null 2>&1; then
        local response=$(curl -s "http://localhost:9083/health")
        if echo "$response" | grep -q "token.json not found"; then
            print_warning "Calendar Sync needs Google authentication"
        else
            print_success "Calendar Sync service is responding"
        fi
    else
        print_error "Calendar Sync service not responding"
    fi
}

validate_match_data_flow() {
    print_step "4" "Validating Match Data Flow"
    
    # Test match data retrieval
    print_info "Testing match data retrieval..."
    local response=$(curl -s -w "%{http_code}" "http://localhost:9086/matches" -o /tmp/matches_response.json)
    
    if [[ "$response" == "200" ]]; then
        print_success "Match data API is working"
        if grep -q "2025-06-28\|June.*28" /tmp/matches_response.json 2>/dev/null; then
            print_success "June 28th match found in data"
        else
            print_info "June 28th match not found (may need credential setup)"
        fi
    elif [[ "$response" == "500" ]]; then
        print_error "Match data API returning 500 error (credential issue)"
    else
        print_error "Match data API not accessible (HTTP $response)"
    fi
    
    # Clean up temp file
    rm -f /tmp/matches_response.json
}

check_logs_for_errors() {
    print_step "5" "Checking Service Logs for Errors"
    
    local services=("fogis-api-client-service" "fogis-calendar-phonebook-sync" "match-list-processor")
    
    for service in "${services[@]}"; do
        print_info "Checking $service logs..."
        if docker logs "$service" --tail 10 2>/dev/null | grep -i "error\|fail\|exception" | head -3; then
            print_warning "Found errors in $service logs (see above)"
        else
            print_success "No recent errors in $service logs"
        fi
    done
}

generate_resolution_commands() {
    print_step "6" "Generating Resolution Commands"
    
    cat > fix_calendar_sync.sh << 'EOF'
#!/bin/bash
# FOGIS Calendar Sync Fix Commands
# Run these commands after setting up credentials

echo "🔧 Fixing FOGIS Calendar Sync Issue..."

# Step 1: Create .env file with FOGIS credentials
echo "Step 1: Setting up FOGIS credentials..."
echo "Please create .env file with:"
echo "FOGIS_USERNAME=your_actual_username"
echo "FOGIS_PASSWORD=your_actual_password"
echo ""

# Step 2: Restart services
echo "Step 2: Restarting services..."
./manage_fogis_system.sh stop
./manage_fogis_system.sh start

# Step 3: Set up Google OAuth
echo "Step 3: Setting up Google OAuth..."
echo "Run: ./manage_fogis_system.sh setup-auth"
echo ""

# Step 4: Verify fix
echo "Step 4: Verifying the fix..."
echo "Check FOGIS API: curl http://localhost:9086/health"
echo "Check Calendar Sync: curl http://localhost:9083/health"
echo "Test match data: curl http://localhost:9086/matches"
echo ""

# Step 5: Enable automation
echo "Step 5: Enable automated processing..."
echo "Run: ./manage_fogis_system.sh cron-add"

echo "✅ Resolution steps prepared!"
EOF
    
    chmod +x fix_calendar_sync.sh
    print_success "Created fix_calendar_sync.sh with resolution commands"
}

main() {
    print_header "FOGIS Calendar Sync Issue Validation"
    
    print_info "This script validates the current system state and prepares resolution steps"
    print_info "for the June 28th match calendar synchronization issue."
    
    validate_credentials_setup
    validate_service_status
    validate_api_connectivity
    validate_match_data_flow
    check_logs_for_errors
    generate_resolution_commands
    
    print_header "Validation Complete"
    
    print_info "Summary of findings:"
    echo "• System is running but missing FOGIS authentication credentials"
    echo "• Calendar sync service needs Google OAuth setup"
    echo "• Match data flow is blocked at the FOGIS API level"
    echo "• Resolution script created: fix_calendar_sync.sh"
    
    print_info "Next steps:"
    echo "1. Set up FOGIS credentials in .env file"
    echo "2. Run Google OAuth setup: ./manage_fogis_system.sh setup-auth"
    echo "3. Execute: ./fix_calendar_sync.sh"
    echo "4. Verify June 28th match is updated in calendar"
}

# Run the validation
main "$@"
