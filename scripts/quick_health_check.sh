#!/bin/bash

# Quick FOGIS Health Check
# Immediate health status check for all FOGIS services

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SUCCESS="✅"
ERROR="❌"
WARNING="⚠️"
INFO="ℹ️"

# Service configurations
declare -A SERVICES=(
    ["process-matches-service"]="9082"
    ["fogis-calendar-phonebook-sync"]="9081"
    ["team-logo-combiner"]="9083"
    ["google-drive-service"]="9084"
    ["fogis-api-client-service"]="9080"
)

print_status() {
    local level=$1
    local message=$2
    
    case $level in
        "SUCCESS") echo -e "${GREEN}${SUCCESS} ${message}${NC}" ;;
        "ERROR") echo -e "${RED}${ERROR} ${message}${NC}" ;;
        "WARNING") echo -e "${YELLOW}${WARNING} ${message}${NC}" ;;
        "INFO") echo -e "${BLUE}${INFO} ${message}${NC}" ;;
    esac
}

check_docker_status() {
    local service=$1
    
    if docker ps --format "{{.Names}}" | grep -q "^${service}$"; then
        local status=$(docker inspect "$service" --format='{{.State.Status}}' 2>/dev/null)
        local health=$(docker inspect "$service" --format='{{.State.Health.Status}}' 2>/dev/null || echo "no-healthcheck")
        echo "running:$health"
    else
        echo "not-running:not-running"
    fi
}

test_health_endpoints() {
    local service=$1
    local port=$2
    
    local endpoints=("/health" "/healthcheck" "/ping" "/status" "/ready" "/")
    
    for endpoint in "${endpoints[@]}"; do
        local url="http://localhost:$port$endpoint"
        local response=$(curl -s -w "%{http_code}" --max-time 3 "$url" 2>/dev/null || echo "000")
        local http_code="${response: -3}"
        
        if [ "$http_code" = "200" ]; then
            echo "OK:$endpoint:$http_code"
            return 0
        elif [ "$http_code" != "000" ]; then
            echo "PARTIAL:$endpoint:$http_code"
        fi
    done
    
    echo "FAILED:none:000"
    return 1
}

check_recent_logs() {
    local service=$1
    
    if docker ps --format "{{.Names}}" | grep -q "^${service}$"; then
        local recent_logs=$(docker logs "$service" --since 5m 2>/dev/null | wc -l)
        echo "$recent_logs"
    else
        echo "0"
    fi
}

main() {
    echo "🏥 Quick FOGIS Health Check"
    echo "=========================="
    echo "Timestamp: $(date)"
    echo
    
    local healthy_count=0
    local total_count=${#SERVICES[@]}
    local issues=()
    
    printf "%-30s %-15s %-15s %-20s %-10s\n" "SERVICE" "CONTAINER" "HEALTH" "ENDPOINT" "LOGS(5m)"
    echo "--------------------------------------------------------------------------------"
    
    for service in "${!SERVICES[@]}"; do
        local port="${SERVICES[$service]}"
        
        # Check Docker status
        local docker_status=$(check_docker_status "$service")
        local container_state="${docker_status%:*}"
        local health_state="${docker_status#*:}"
        
        # Check health endpoints
        local endpoint_result=$(test_health_endpoints "$service" "$port")
        local endpoint_status="${endpoint_result%%:*}"
        local endpoint_path="${endpoint_result#*:}"
        local endpoint_path="${endpoint_path%:*}"
        local http_code="${endpoint_result##*:}"
        
        # Check recent logs
        local log_count=$(check_recent_logs "$service")
        
        # Determine overall status
        local overall_status=""
        local status_color=""
        
        if [ "$container_state" = "running" ] && [ "$endpoint_status" = "OK" ]; then
            overall_status="HEALTHY"
            status_color="$GREEN"
            ((healthy_count++))
        elif [ "$container_state" = "running" ] && [ "$endpoint_status" = "PARTIAL" ]; then
            overall_status="DEGRADED"
            status_color="$YELLOW"
            issues+=("$service: Partial endpoint response")
        elif [ "$container_state" = "running" ]; then
            overall_status="UNHEALTHY"
            status_color="$RED"
            issues+=("$service: No working health endpoints")
        else
            overall_status="DOWN"
            status_color="$RED"
            issues+=("$service: Container not running")
        fi
        
        # Format endpoint info
        local endpoint_info="$endpoint_path"
        if [ "$http_code" != "000" ] && [ "$http_code" != "200" ]; then
            endpoint_info="$endpoint_path($http_code)"
        fi
        
        # Print status line
        printf "${status_color}%-30s${NC} %-15s %-15s %-20s %-10s\n" \
            "$service" "$container_state" "$health_state" "$endpoint_info" "$log_count"
    done
    
    echo
    echo "Summary:"
    echo "--------"
    
    if [ "$healthy_count" -eq "$total_count" ]; then
        print_status "SUCCESS" "All $total_count services are healthy"
    else
        local unhealthy_count=$((total_count - healthy_count))
        print_status "WARNING" "$healthy_count/$total_count services healthy ($unhealthy_count need attention)"
        
        echo
        echo "Issues found:"
        for issue in "${issues[@]}"; do
            print_status "ERROR" "$issue"
        done
    fi
    
    echo
    echo "Quick Actions:"
    echo "--------------"
    
    if [ ${#issues[@]} -gt 0 ]; then
        echo "• Check service logs: docker logs [service-name] --since 1h"
        echo "• Restart unhealthy services: docker-compose restart [service-name]"
        echo "• Full diagnostic: ./scripts/diagnose_health_check_pattern.sh"
        echo "• Monitor patterns: ./scripts/monitor_health_patterns.sh"
    else
        echo "• Monitor continuously: ./scripts/monitor_health_patterns.sh"
        echo "• Check historical patterns: ./scripts/diagnose_health_check_pattern.sh"
    fi
    
    echo
    echo "Health Endpoints Tested:"
    echo "• /health, /healthcheck, /ping, /status, /ready, /"
    echo
    echo "For detailed analysis of the 7:15-7:25 pattern:"
    echo "• ./scripts/diagnose_health_check_pattern.sh"
}

main "$@"
