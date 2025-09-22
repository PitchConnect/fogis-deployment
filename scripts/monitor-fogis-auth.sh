#!/bin/bash

# FOGIS Authentication Monitoring Script
# This script monitors the authentication status of the FOGIS API client service
# and can be used for alerting when authentication issues occur.

set -euo pipefail

# Configuration
FOGIS_API_URL="${FOGIS_API_URL:-http://localhost:9086}"
LOG_FILE="${LOG_FILE:-/tmp/fogis-auth-monitor.log}"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
CHECK_INTERVAL="${CHECK_INTERVAL:-300}"  # 5 minutes - less frequent checks
MAX_FAILURES="${MAX_FAILURES:-2}"        # Reduced threshold since we have loud alerting

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

# Check if service is reachable
check_service_health() {
    local response
    local status_code
    
    response=$(curl -s -w "%{http_code}" "$FOGIS_API_URL/health" 2>/dev/null || echo "000")
    status_code="${response: -3}"
    
    if [[ "$status_code" == "200" ]]; then
        return 0
    else
        log "ERROR" "Service health check failed with status code: $status_code"
        return 1
    fi
}

# Check OAuth failure state (lightweight check)
check_oauth_failure_state() {
    local response
    local status_code
    local has_failures

    response=$(curl -s -w "%{http_code}" "$FOGIS_API_URL/oauth/failure-state" 2>/dev/null || echo "000")
    status_code="${response: -3}"

    if [[ "$status_code" == "200" ]]; then
        # Extract failure state from JSON response
        has_failures=$(echo "${response%???}" | jq -r '.has_active_failures // false' 2>/dev/null || echo "false")

        if [[ "$has_failures" == "false" ]]; then
            return 0
        else
            local failure_count=$(echo "${response%???}" | jq -r '.oauth_failure_state.failure_count // 0' 2>/dev/null || echo "0")
            local last_error=$(echo "${response%???}" | jq -r '.oauth_failure_state.last_error_message // "unknown"' 2>/dev/null || echo "unknown")
            log "ERROR" "OAuth failures detected: $failure_count failures, last error: $last_error"
            return 1
        fi
    else
        log "ERROR" "OAuth failure state check failed with status code: $status_code"
        return 2
    fi
}

# Test matches endpoint (lightweight - only during hourly sync or on-demand)
test_matches_endpoint() {
    local response
    local status_code
    local skip_test="${1:-false}"

    # Skip the actual matches test during regular monitoring to reduce load
    if [[ "$skip_test" == "true" ]]; then
        log "INFO" "Skipping matches endpoint test to reduce server load"
        return 0
    fi

    response=$(curl -s -w "%{http_code}" "$FOGIS_API_URL/matches" 2>/dev/null || echo "000")
    status_code="${response: -3}"

    if [[ "$status_code" == "200" ]]; then
        # Check if response contains matches data
        local match_count
        match_count=$(echo "${response%???}" | jq 'length // 0' 2>/dev/null || echo "0")
        log "INFO" "Matches endpoint working - returned $match_count matches"
        return 0
    elif [[ "$status_code" == "401" ]]; then
        log "ERROR" "Authentication error when accessing matches endpoint"
        return 1
    elif [[ "$status_code" == "500" ]]; then
        log "ERROR" "Internal server error when accessing matches endpoint"
        return 2
    else
        log "ERROR" "Matches endpoint failed with status code: $status_code"
        return 3
    fi
}

# Send alert (webhook or email)
send_alert() {
    local alert_type="$1"
    local message="$2"
    
    log "ALERT" "$alert_type: $message"
    
    if [[ -n "$ALERT_WEBHOOK" ]]; then
        local payload
        payload=$(jq -n \
            --arg type "$alert_type" \
            --arg message "$message" \
            --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            --arg service "fogis-api-client" \
            '{
                alert_type: $type,
                message: $message,
                timestamp: $timestamp,
                service: $service
            }')
        
        curl -s -X POST \
            -H "Content-Type: application/json" \
            -d "$payload" \
            "$ALERT_WEBHOOK" >/dev/null 2>&1 || \
            log "ERROR" "Failed to send webhook alert"
    fi
}

# Main monitoring function
monitor_authentication() {
    local failure_count=0
    local last_status="unknown"
    local cycle_count=0

    log "INFO" "Starting FOGIS lightweight monitoring (interval: ${CHECK_INTERVAL}s)"
    log "INFO" "Using OAuth failure state monitoring instead of frequent authentication checks"

    while true; do
        local current_status="healthy"
        local error_details=""
        cycle_count=$((cycle_count + 1))

        # Check service health (always)
        if ! check_service_health; then
            current_status="service_down"
            error_details="Service health check failed"
        # Check OAuth failure state (lightweight)
        elif ! check_oauth_failure_state; then
            current_status="oauth_failed"
            error_details="OAuth failure state detected"
        # Test matches endpoint only occasionally to reduce load
        elif [[ $((cycle_count % 12)) -eq 0 ]] && ! test_matches_endpoint "false"; then
            current_status="endpoint_failed"
            error_details="Matches endpoint test failed"
        else
            # Skip matches endpoint test most of the time
            test_matches_endpoint "true" >/dev/null 2>&1
        fi
        
        # Handle status changes
        if [[ "$current_status" != "healthy" ]]; then
            ((failure_count++))
            
            if [[ "$last_status" == "healthy" ]]; then
                log "WARN" "Authentication issue detected: $error_details (failure #$failure_count)"
            fi
            
            if [[ "$failure_count" -ge "$MAX_FAILURES" ]]; then
                send_alert "CRITICAL" "FOGIS authentication has failed $failure_count consecutive times: $error_details"
                failure_count=0  # Reset to avoid spam
            fi
        else
            if [[ "$last_status" != "healthy" && "$failure_count" -gt 0 ]]; then
                log "INFO" "Authentication recovered after $failure_count failures"
                send_alert "RECOVERY" "FOGIS authentication has recovered"
            fi
            failure_count=0
        fi
        
        last_status="$current_status"
        sleep "$CHECK_INTERVAL"
    done
}

# Handle script termination
cleanup() {
    log "INFO" "Monitoring stopped"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Main execution
case "${1:-monitor}" in
    "monitor")
        monitor_authentication
        ;;
    "check")
        echo "Checking FOGIS API authentication status..."
        if check_service_health && check_oauth_failure_state && test_matches_endpoint "false"; then
            echo -e "${GREEN}✅ All checks passed${NC}"
            exit 0
        else
            echo -e "${RED}❌ One or more checks failed${NC}"
            exit 1
        fi
        ;;
    "status")
        echo "FOGIS API Service Status:"
        echo "========================"

        if check_service_health; then
            echo -e "Service Health: ${GREEN}✅ OK${NC}"
        else
            echo -e "Service Health: ${RED}❌ FAILED${NC}"
        fi

        if check_oauth_failure_state; then
            echo -e "OAuth Status: ${GREEN}✅ OK${NC}"
        else
            echo -e "OAuth Status: ${RED}❌ FAILURES DETECTED${NC}"
        fi

        if test_matches_endpoint "false"; then
            echo -e "Matches Endpoint: ${GREEN}✅ OK${NC}"
        else
            echo -e "Matches Endpoint: ${RED}❌ FAILED${NC}"
        fi
        ;;
    *)
        echo "Usage: $0 [monitor|check|status]"
        echo ""
        echo "Commands:"
        echo "  monitor  - Start continuous monitoring (default)"
        echo "  check    - Run a single check and exit"
        echo "  status   - Show current status"
        echo ""
        echo "Environment variables:"
        echo "  FOGIS_API_URL     - API URL (default: http://localhost:9086)"
        echo "  LOG_FILE          - Log file path (default: /tmp/fogis-auth-monitor.log)"
        echo "  ALERT_WEBHOOK     - Webhook URL for alerts"
        echo "  CHECK_INTERVAL    - Check interval in seconds (default: 300)"
        echo "  MAX_FAILURES      - Max failures before alert (default: 2)"
        echo ""
        echo "Note: This monitoring script uses lightweight OAuth failure state"
        echo "monitoring instead of frequent authentication checks to reduce"
        echo "server load. OAuth failures are detected during normal operations"
        echo "and reported loudly through the built-in alerting system."
        exit 1
        ;;
esac
