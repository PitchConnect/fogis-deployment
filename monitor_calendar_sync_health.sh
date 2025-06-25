#!/bin/bash
# FOGIS Calendar Sync Health Monitor
# Monitors the health of calendar sync components and alerts to issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    local status="$1"
    local message="$2"
    
    case "$status" in
        "OK")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
    esac
}

check_fogis_api_health() {
    print_status "INFO" "Checking FOGIS API Client health..."
    
    local response=$(curl -s "http://localhost:9086/health" 2>/dev/null || echo "")
    
    if [[ -z "$response" ]]; then
        print_status "ERROR" "FOGIS API Client not responding"
        return 1
    fi
    
    local status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    local fogis_client=$(echo "$response" | grep -o '"fogis_client":"[^"]*"' | cut -d'"' -f4)
    
    if [[ "$status" == "healthy" ]]; then
        print_status "OK" "FOGIS API Client is healthy"
        return 0
    elif [[ "$status" == "degraded" ]]; then
        if [[ "$fogis_client" == "unavailable" ]]; then
            print_status "ERROR" "FOGIS API Client degraded - missing credentials"
        else
            print_status "WARNING" "FOGIS API Client degraded - $fogis_client"
        fi
        return 1
    else
        print_status "ERROR" "FOGIS API Client status unknown: $status"
        return 1
    fi
}

check_calendar_sync_health() {
    print_status "INFO" "Checking Calendar Sync service health..."

    local response=$(curl -s "http://localhost:9083/health" 2>/dev/null || echo "")

    if [[ -z "$response" ]]; then
        print_status "ERROR" "Calendar Sync service not responding"
        return 1
    fi

    if echo "$response" | grep -q "token.json not found"; then
        print_status "ERROR" "Calendar Sync missing Google authentication (use web interface at http://localhost:9087)"
        return 1
    elif echo "$response" | grep -q '"status":"ok"'; then
        print_status "OK" "Calendar Sync service is healthy"
        return 0
    else
        print_status "WARNING" "Calendar Sync service responding but status unclear"
        return 1
    fi
}

check_web_auth_interface() {
    print_status "INFO" "Checking Web Authentication Interface..."

    local response=$(curl -s "http://localhost:9087/status" 2>/dev/null || echo "")

    if [[ -z "$response" ]]; then
        print_status "ERROR" "Web Authentication Interface not responding"
        return 1
    fi

    if echo "$response" | grep -q '"valid":true'; then
        print_status "OK" "OAuth token is valid"
        return 0
    elif echo "$response" | grep -q '"valid":false'; then
        print_status "ERROR" "OAuth token is invalid or expired - visit http://localhost:9087 to re-authenticate"
        return 1
    else
        print_status "WARNING" "Web Authentication Interface responding but token status unclear"
        return 1
    fi
}

check_match_data_access() {
    print_status "INFO" "Checking match data access..."
    
    local http_code=$(curl -s -w "%{http_code}" "http://localhost:9086/matches" -o /tmp/matches_check.json 2>/dev/null || echo "000")
    
    case "$http_code" in
        "200")
            print_status "OK" "Match data API is accessible"
            
            # Check for June 28th match specifically
            if grep -q "2025-06-28\|June.*28" /tmp/matches_check.json 2>/dev/null; then
                print_status "OK" "June 28th match found in data"
            else
                print_status "INFO" "June 28th match not found (may be normal if no matches scheduled)"
            fi
            rm -f /tmp/matches_check.json
            return 0
            ;;
        "500")
            print_status "ERROR" "Match data API returning 500 error - likely credential issue"
            ;;
        "000")
            print_status "ERROR" "Cannot connect to match data API"
            ;;
        *)
            print_status "ERROR" "Match data API returned HTTP $http_code"
            ;;
    esac
    
    rm -f /tmp/matches_check.json
    return 1
}

check_container_status() {
    print_status "INFO" "Checking container status..."
    
    local containers=("fogis-api-client-service" "fogis-calendar-phonebook-sync" "match-list-processor" "match-list-change-detector")
    local all_running=true
    
    for container in "${containers[@]}"; do
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container.*Up"; then
            print_status "OK" "Container $container is running"
        else
            print_status "ERROR" "Container $container is not running"
            all_running=false
        fi
    done
    
    if $all_running; then
        return 0
    else
        return 1
    fi
}

check_credentials_configuration() {
    print_status "INFO" "Checking credentials configuration..."
    
    # Check .env file
    if [[ -f ".env" ]]; then
        if grep -q "FOGIS_USERNAME=" .env && grep -q "FOGIS_PASSWORD=" .env; then
            print_status "OK" "FOGIS credentials configured in .env"
        else
            print_status "ERROR" "FOGIS credentials missing from .env file"
            return 1
        fi
    else
        print_status "ERROR" ".env file not found - FOGIS credentials not configured"
        return 1
    fi
    
    # Check Google credentials
    if [[ -d "credentials" ]] && [[ -n "$(ls -A credentials/)" ]]; then
        print_status "OK" "Google credentials directory contains files"
    else
        print_status "ERROR" "Google credentials not configured"
        return 1
    fi
    
    return 0
}

generate_health_report() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "# FOGIS Calendar Sync Health Report"
    echo "Generated: $timestamp"
    echo ""
    
    echo "## System Status"
    check_container_status && echo "- Containers: ✅ All running" || echo "- Containers: ❌ Some not running"
    check_credentials_configuration && echo "- Credentials: ✅ Configured" || echo "- Credentials: ❌ Missing"
    check_fogis_api_health && echo "- FOGIS API: ✅ Healthy" || echo "- FOGIS API: ❌ Issues detected"
    check_calendar_sync_health && echo "- Calendar Sync: ✅ Healthy" || echo "- Calendar Sync: ❌ Issues detected"
    check_match_data_access && echo "- Match Data: ✅ Accessible" || echo "- Match Data: ❌ Not accessible"
    
    echo ""
    echo "## Recommendations"
    
    if ! check_credentials_configuration >/dev/null 2>&1; then
        echo "1. Set up FOGIS credentials: Create .env file with FOGIS_USERNAME and FOGIS_PASSWORD"
        echo "2. Set up Google OAuth: Run ./manage_fogis_system.sh setup-auth"
    fi
    
    if ! check_fogis_api_health >/dev/null 2>&1; then
        echo "3. Restart services after credential setup: ./manage_fogis_system.sh restart"
    fi
    
    if ! check_match_data_access >/dev/null 2>&1; then
        echo "4. Test match processing: ./manage_fogis_system.sh test"
    fi
    
    echo "5. Enable automated processing: ./manage_fogis_system.sh cron-add"
}

main() {
    echo -e "${BLUE}🔍 FOGIS Calendar Sync Health Monitor${NC}"
    echo -e "${BLUE}=====================================${NC}"
    
    local overall_health=true
    
    check_container_status || overall_health=false
    echo ""
    
    check_credentials_configuration || overall_health=false
    echo ""
    
    check_fogis_api_health || overall_health=false
    echo ""
    
    check_calendar_sync_health || overall_health=false
    echo ""

    check_web_auth_interface || overall_health=false
    echo ""

    check_match_data_access || overall_health=false
    echo ""
    
    if $overall_health; then
        print_status "OK" "Overall system health: GOOD"
        print_status "INFO" "June 28th calendar sync should be working correctly"
    else
        print_status "ERROR" "Overall system health: ISSUES DETECTED"
        print_status "INFO" "June 28th calendar sync will not work until issues are resolved"
        echo ""
        print_status "INFO" "Run ./validate_calendar_sync_fix.sh for detailed resolution steps"
    fi
    
    # Generate report if requested
    if [[ "$1" == "--report" ]]; then
        echo ""
        echo -e "${BLUE}📊 Generating detailed report...${NC}"
        generate_health_report > calendar_sync_health_report.md
        print_status "OK" "Health report saved to calendar_sync_health_report.md"
    fi
}

# Run the health check
main "$@"
