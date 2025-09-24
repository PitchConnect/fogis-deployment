#!/bin/bash

# FOGIS Health Check Pattern Diagnostic Script
# Analyzes health check logging patterns and service availability

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Emojis for better visual feedback
SUCCESS="✅"
ERROR="❌"
WARNING="⚠️"
INFO="ℹ️"
HEALTH="🏥"
SEARCH="🔍"
TIME="⏰"

# Configuration
LOKI_URL="http://localhost:3100"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# FOGIS services to check
FOGIS_SERVICES=(
    "process-matches-service"
    "fogis-calendar-phonebook-sync"
    "match-list-change-detector"
    "fogis-api-client-service"
    "team-logo-combiner"
    "google-drive-service"
)

print_status() {
    local level=$1
    local message=$2
    
    case $level in
        "SUCCESS") echo -e "${GREEN}${SUCCESS} ${message}${NC}" ;;
        "ERROR") echo -e "${RED}${ERROR} ${message}${NC}" ;;
        "WARNING") echo -e "${YELLOW}${WARNING} ${message}${NC}" ;;
        "INFO") echo -e "${BLUE}${INFO} ${message}${NC}" ;;
        "HEALTH") echo -e "${PURPLE}${HEALTH} ${message}${NC}" ;;
        "SEARCH") echo -e "${CYAN}${SEARCH} ${message}${NC}" ;;
        "TIME") echo -e "${PURPLE}${TIME} ${message}${NC}" ;;
    esac
}

print_header() {
    echo
    echo "============================================================"
    echo "🏥 FOGIS Health Check Pattern Diagnostic"
    echo "============================================================"
    echo "Analyzing health check patterns during 7:15-7:25 timeframe"
    echo
}

check_prerequisites() {
    print_status "INFO" "Checking prerequisites..."
    
    cd "$DEPLOYMENT_ROOT"
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_status "ERROR" "Docker is not running"
        exit 1
    fi
    
    # Check if Loki is responding
    if ! curl -s "$LOKI_URL/ready" >/dev/null; then
        print_status "ERROR" "Loki is not responding at $LOKI_URL"
        exit 1
    fi
    
    print_status "SUCCESS" "Prerequisites check completed"
}

get_time_range() {
    local target_date="${1:-today}"
    
    if [ "$target_date" = "today" ]; then
        local base_date=$(date +%Y-%m-%d)
    else
        local base_date="$target_date"
    fi
    
    local start_time="${base_date}T07:15:00"
    local end_time="${base_date}T07:25:00"
    
    # Convert to RFC3339 with timezone
    START_TIME=$(date -d "$start_time" -Iseconds 2>/dev/null || echo "${start_time}+01:00")
    END_TIME=$(date -d "$end_time" -Iseconds 2>/dev/null || echo "${end_time}+01:00")
    
    print_status "TIME" "Analyzing time range: $START_TIME to $END_TIME"
}

check_container_status() {
    print_status "SEARCH" "Checking Docker container status during analysis period..."
    
    echo
    echo "=== Current Container Status ==="
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(fogis|process-matches|team-logo|google-drive)" || echo "No FOGIS containers found"
    
    echo
    echo "=== Container Health Status ==="
    for service in "${FOGIS_SERVICES[@]}"; do
        if docker ps | grep -q "$service"; then
            local health_status=$(docker inspect "$service" --format='{{.State.Health.Status}}' 2>/dev/null || echo "no-healthcheck")
            local container_status=$(docker inspect "$service" --format='{{.State.Status}}' 2>/dev/null || echo "unknown")
            
            if [ "$health_status" = "healthy" ]; then
                print_status "SUCCESS" "$service: Container=$container_status, Health=$health_status"
            elif [ "$health_status" = "no-healthcheck" ]; then
                print_status "WARNING" "$service: Container=$container_status, Health=no-healthcheck-configured"
            else
                print_status "ERROR" "$service: Container=$container_status, Health=$health_status"
            fi
        else
            print_status "ERROR" "$service: Container not running"
        fi
    done
    
    echo
}

analyze_health_logs_by_service() {
    print_status "SEARCH" "Analyzing health check logs by service..."
    
    echo
    echo "=== Health Check Log Analysis (7:15-7:25) ==="
    
    for service in "${FOGIS_SERVICES[@]}"; do
        print_status "INFO" "Checking health logs for: $service"
        
        # Query for health-related logs
        local health_query="{container_name=\"$service\"} |~ \"(?i)(health|/health|healthcheck|ping|status|ready)\""
        
        local response=$(curl -s -G "$LOKI_URL/loki/api/v1/query_range" \
            --data-urlencode "query=$health_query" \
            --data-urlencode "start=$START_TIME" \
            --data-urlencode "end=$END_TIME" \
            --data-urlencode "limit=50" 2>/dev/null)
        
        if echo "$response" | jq -e '.data.result | length' >/dev/null 2>&1; then
            local result_count=$(echo "$response" | jq '.data.result | length')
            local total_entries=0
            
            if [ "$result_count" -gt 0 ]; then
                # Count total log entries
                for i in $(seq 0 $((result_count - 1))); do
                    local stream_entries=$(echo "$response" | jq ".data.result[$i].values | length")
                    total_entries=$((total_entries + stream_entries))
                done
                
                print_status "SUCCESS" "  Found $total_entries health-related log entries"
                
                # Show sample health logs
                echo "  Sample health logs:"
                echo "$response" | jq -r '.data.result[0].values[0:3][]? | "    " + .[0] + " " + .[1]' 2>/dev/null | head -3 || echo "    No sample entries available"
            else
                print_status "WARNING" "  No health-related logs found"
            fi
        else
            print_status "ERROR" "  Failed to query health logs"
        fi
        
        echo
    done
}

analyze_general_service_activity() {
    print_status "SEARCH" "Analyzing general service activity during 7:15-7:25..."
    
    echo
    echo "=== General Service Activity Analysis ==="
    
    for service in "${FOGIS_SERVICES[@]}"; do
        print_status "INFO" "Checking general activity for: $service"
        
        # Query for any logs from the service
        local general_query="{container_name=\"$service\"}"
        
        local response=$(curl -s -G "$LOKI_URL/loki/api/v1/query_range" \
            --data-urlencode "query=$general_query" \
            --data-urlencode "start=$START_TIME" \
            --data-urlencode "end=$END_TIME" \
            --data-urlencode "limit=20" 2>/dev/null)
        
        if echo "$response" | jq -e '.data.result | length' >/dev/null 2>&1; then
            local result_count=$(echo "$response" | jq '.data.result | length')
            local total_entries=0
            
            if [ "$result_count" -gt 0 ]; then
                # Count total log entries
                for i in $(seq 0 $((result_count - 1))); do
                    local stream_entries=$(echo "$response" | jq ".data.result[$i].values | length")
                    total_entries=$((total_entries + stream_entries))
                done
                
                print_status "SUCCESS" "  Found $total_entries total log entries"
                
                # Analyze log types
                echo "  Recent log entries:"
                echo "$response" | jq -r '.data.result[0].values[0:3][]? | "    " + .[0] + " " + (.[1] | split(" ") | .[0:8] | join(" "))' 2>/dev/null | head -3 || echo "    No entries available"
            else
                print_status "WARNING" "  No logs found - service may be inactive or down"
            fi
        else
            print_status "ERROR" "  Failed to query service logs"
        fi
        
        echo
    done
}

check_health_endpoint_configuration() {
    print_status "SEARCH" "Checking health endpoint configuration..."
    
    echo
    echo "=== Health Endpoint Configuration ==="
    
    # Check docker-compose.yml for health check configuration
    if [ -f "docker-compose.yml" ]; then
        print_status "INFO" "Health check configuration in docker-compose.yml:"
        echo
        
        for service in "${FOGIS_SERVICES[@]}"; do
            echo "--- $service ---"
            
            # Extract health check configuration for this service
            local health_config=$(awk "/^  $service:/,/^  [a-zA-Z]/ {print}" docker-compose.yml | grep -A 10 "healthcheck:" || echo "No healthcheck configured")
            
            if echo "$health_config" | grep -q "healthcheck:"; then
                echo "$health_config"
                print_status "SUCCESS" "Health check configured for $service"
            else
                print_status "WARNING" "No health check configured for $service"
            fi
            echo
        done
    else
        print_status "ERROR" "docker-compose.yml not found"
    fi
}

test_health_endpoints_directly() {
    print_status "SEARCH" "Testing health endpoints directly..."
    
    echo
    echo "=== Direct Health Endpoint Testing ==="
    
    # Common health endpoint patterns
    local health_endpoints=(
        "/health"
        "/healthcheck"
        "/ping"
        "/status"
        "/ready"
        "/"
    )
    
    # Service port mappings (from docker-compose.yml)
    declare -A service_ports=(
        ["process-matches-service"]="9082"
        ["fogis-calendar-phonebook-sync"]="9081"
        ["team-logo-combiner"]="9083"
        ["google-drive-service"]="9084"
        ["fogis-api-client-service"]="9080"
    )
    
    for service in "${FOGIS_SERVICES[@]}"; do
        local port="${service_ports[$service]:-unknown}"
        
        print_status "INFO" "Testing health endpoints for $service (port $port):"
        
        if [ "$port" != "unknown" ]; then
            for endpoint in "${health_endpoints[@]}"; do
                local url="http://localhost:$port$endpoint"
                
                # Test endpoint with timeout
                local response=$(curl -s -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
                local http_code="${response: -3}"
                local body="${response%???}"
                
                if [ "$http_code" = "200" ]; then
                    print_status "SUCCESS" "  $endpoint: HTTP $http_code - OK"
                    if [ ${#body} -lt 100 ]; then
                        echo "    Response: $body"
                    else
                        echo "    Response: ${body:0:100}..."
                    fi
                elif [ "$http_code" = "000" ]; then
                    print_status "ERROR" "  $endpoint: Connection failed/timeout"
                else
                    print_status "WARNING" "  $endpoint: HTTP $http_code"
                fi
            done
        else
            print_status "WARNING" "  Port unknown for $service"
        fi
        
        echo
    done
}

analyze_docker_health_checks() {
    print_status "SEARCH" "Analyzing Docker health check results..."
    
    echo
    echo "=== Docker Health Check Analysis ==="
    
    for service in "${FOGIS_SERVICES[@]}"; do
        if docker ps | grep -q "$service"; then
            print_status "INFO" "Health check details for $service:"
            
            # Get detailed health check information
            local health_info=$(docker inspect "$service" --format='{{json .State.Health}}' 2>/dev/null)
            
            if [ "$health_info" != "null" ] && [ -n "$health_info" ]; then
                echo "$health_info" | jq -r '
                    "  Status: " + .Status + 
                    "\n  Failing Streak: " + (.FailingStreak | tostring) + 
                    "\n  Last Check: " + (.Log[-1].Start // "never") +
                    "\n  Exit Code: " + (.Log[-1].ExitCode // "unknown" | tostring) +
                    "\n  Output: " + (.Log[-1].Output // "no output")
                ' 2>/dev/null || echo "  Could not parse health check data"
            else
                print_status "WARNING" "  No health check configured"
            fi
        else
            print_status "ERROR" "  Container not running"
        fi
        
        echo
    done
}

check_service_logs_for_errors() {
    print_status "SEARCH" "Checking service logs for errors during 7:15-7:25..."
    
    echo
    echo "=== Service Error Log Analysis ==="
    
    for service in "${FOGIS_SERVICES[@]}"; do
        print_status "INFO" "Checking error logs for: $service"
        
        # Query for error logs
        local error_query="{container_name=\"$service\"} |~ \"(?i)(error|exception|failed|timeout|refused|unavailable)\""
        
        local response=$(curl -s -G "$LOKI_URL/loki/api/v1/query_range" \
            --data-urlencode "query=$error_query" \
            --data-urlencode "start=$START_TIME" \
            --data-urlencode "end=$END_TIME" \
            --data-urlencode "limit=10" 2>/dev/null)
        
        if echo "$response" | jq -e '.data.result | length' >/dev/null 2>&1; then
            local result_count=$(echo "$response" | jq '.data.result | length')
            
            if [ "$result_count" -gt 0 ]; then
                local total_errors=0
                for i in $(seq 0 $((result_count - 1))); do
                    local stream_errors=$(echo "$response" | jq ".data.result[$i].values | length")
                    total_errors=$((total_errors + stream_errors))
                done
                
                print_status "WARNING" "  Found $total_errors error entries"
                
                # Show error samples
                echo "  Sample errors:"
                echo "$response" | jq -r '.data.result[0].values[0:2][]? | "    " + .[0] + " " + .[1]' 2>/dev/null | head -2 || echo "    No error samples available"
            else
                print_status "SUCCESS" "  No errors found"
            fi
        else
            print_status "ERROR" "  Failed to query error logs"
        fi
        
        echo
    done
}

generate_health_check_report() {
    print_status "INFO" "Generating health check pattern analysis report..."
    
    local report_file="./logs/health-check-analysis-$(date +%Y%m%d-%H%M%S).log"
    mkdir -p "$(dirname "$report_file")"
    
    {
        echo "FOGIS Health Check Pattern Analysis Report"
        echo "Generated: $(date)"
        echo "Time Range Analyzed: $START_TIME to $END_TIME"
        echo "=========================================="
        echo
        
        echo "SUMMARY:"
        echo "- Only fogis-calendar-phonebook-sync showing health logs during 7:15-7:25"
        echo "- Other services may be down, misconfigured, or have logging issues"
        echo
        
        echo "RECOMMENDATIONS:"
        echo "1. Check if other services are actually running during this period"
        echo "2. Verify health check endpoint configuration"
        echo "3. Test health endpoints directly"
        echo "4. Check for service startup/restart patterns"
        echo "5. Review service dependencies and startup order"
        echo
        
        echo "NEXT STEPS:"
        echo "- Run: docker logs [service-name] --since 1h"
        echo "- Test: curl http://localhost:[port]/health"
        echo "- Check: docker-compose logs [service-name]"
        echo "- Monitor: ./scripts/monitor_health_patterns.sh"
        
    } > "$report_file"
    
    print_status "SUCCESS" "Report saved to: $report_file"
}

print_recommendations() {
    print_status "INFO" "Health check pattern analysis recommendations:"
    
    echo
    echo "=== Immediate Actions ==="
    echo
    echo "1. 🔍 **Check Service Status**:"
    echo "   docker ps | grep -E '(fogis|process-matches|team-logo|google-drive)'"
    echo
    echo "2. 🏥 **Test Health Endpoints**:"
    echo "   curl http://localhost:9082/health  # process-matches-service"
    echo "   curl http://localhost:9081/health  # calendar-phonebook-sync"
    echo "   curl http://localhost:9083/health  # team-logo-combiner"
    echo
    echo "3. 📋 **Check Service Logs**:"
    echo "   docker logs process-matches-service --since 1h"
    echo "   docker logs team-logo-combiner --since 1h"
    echo
    echo "4. 🔄 **Restart Problematic Services**:"
    echo "   docker-compose restart process-matches-service"
    echo "   docker-compose restart team-logo-combiner"
    echo
    echo "=== Root Cause Analysis ==="
    echo
    echo "• **If services are down**: Check startup dependencies and resource limits"
    echo "• **If services are up but no health logs**: Check health endpoint configuration"
    echo "• **If health endpoints fail**: Check service internal health and dependencies"
    echo "• **If logs missing**: Check Promtail configuration and log collection"
    echo
    echo "=== Monitoring Setup ==="
    echo
    echo "• **Continuous monitoring**: Set up health check alerts"
    echo "• **Service dependencies**: Review startup order and dependencies"
    echo "• **Resource monitoring**: Check CPU, memory, and disk usage"
    echo "• **Network connectivity**: Verify inter-service communication"
}

main() {
    print_header
    
    # Parse command line arguments
    local target_date="${1:-today}"
    
    print_status "INFO" "Starting health check pattern analysis..."
    print_status "INFO" "Target date: $target_date"
    
    check_prerequisites
    get_time_range "$target_date"
    check_container_status
    analyze_health_logs_by_service
    analyze_general_service_activity
    check_health_endpoint_configuration
    test_health_endpoints_directly
    analyze_docker_health_checks
    check_service_logs_for_errors
    generate_health_check_report
    
    echo
    print_status "SUCCESS" "Health check pattern analysis completed!"
    
    print_recommendations
}

# Run main function with arguments
main "$@"
