#!/bin/bash

# FOGIS Real-time Health Pattern Monitor
# Continuously monitors health check patterns and service availability

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SUCCESS="✅"
ERROR="❌"
WARNING="⚠️"
INFO="ℹ️"
HEALTH="🏥"

# Configuration
MONITOR_INTERVAL=60  # Check every 60 seconds
LOG_FILE="./logs/health-pattern-monitor.log"
ALERT_FILE="./logs/health-alerts.log"

# FOGIS services to monitor
FOGIS_SERVICES=(
    "process-matches-service:9082"
    "fogis-calendar-phonebook-sync:9081"
    "team-logo-combiner:9083"
    "google-drive-service:9084"
    "fogis-api-client-service:9080"
)

print_status() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "SUCCESS") echo -e "${GREEN}${SUCCESS} [$timestamp] ${message}${NC}" ;;
        "ERROR") echo -e "${RED}${ERROR} [$timestamp] ${message}${NC}" ;;
        "WARNING") echo -e "${YELLOW}${WARNING} [$timestamp] ${message}${NC}" ;;
        "INFO") echo -e "${BLUE}${INFO} [$timestamp] ${message}${NC}" ;;
        "HEALTH") echo -e "${BLUE}${HEALTH} [$timestamp] ${message}${NC}" ;;
    esac
    
    # Log to file
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

log_alert() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] ALERT: $message" >> "$ALERT_FILE"
    print_status "ERROR" "ALERT: $message"
}

setup_monitoring() {
    print_status "INFO" "Setting up health pattern monitoring..."
    
    # Create log directories
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$(dirname "$ALERT_FILE")"
    
    # Initialize log files
    echo "FOGIS Health Pattern Monitor Started: $(date)" >> "$LOG_FILE"
    echo "FOGIS Health Alerts Log Started: $(date)" >> "$ALERT_FILE"
    
    print_status "SUCCESS" "Monitoring setup completed"
    print_status "INFO" "Monitor log: $LOG_FILE"
    print_status "INFO" "Alert log: $ALERT_FILE"
    print_status "INFO" "Check interval: ${MONITOR_INTERVAL}s"
}

check_container_status() {
    local service_name="$1"
    
    if docker ps | grep -q "$service_name"; then
        local container_status=$(docker inspect "$service_name" --format='{{.State.Status}}' 2>/dev/null || echo "unknown")
        local health_status=$(docker inspect "$service_name" --format='{{.State.Health.Status}}' 2>/dev/null || echo "no-healthcheck")
        
        echo "$container_status:$health_status"
    else
        echo "not-running:not-running"
    fi
}

test_health_endpoint() {
    local service_name="$1"
    local port="$2"
    
    # Try common health endpoints
    local endpoints=("/health" "/healthcheck" "/ping" "/status" "/ready")
    
    for endpoint in "${endpoints[@]}"; do
        local url="http://localhost:$port$endpoint"
        local response=$(curl -s -w "%{http_code}" --max-time 3 "$url" 2>/dev/null || echo "000")
        local http_code="${response: -3}"
        
        if [ "$http_code" = "200" ]; then
            echo "healthy:$endpoint"
            return 0
        fi
    done
    
    echo "unhealthy:no-endpoint"
    return 1
}

check_service_health() {
    local service_info="$1"
    local service_name="${service_info%:*}"
    local port="${service_info#*:}"
    
    # Check container status
    local container_status=$(check_container_status "$service_name")
    local container_state="${container_status%:*}"
    local health_state="${container_status#*:}"
    
    # Test health endpoint
    local endpoint_result=$(test_health_endpoint "$service_name" "$port")
    local endpoint_status="${endpoint_result%:*}"
    local endpoint_path="${endpoint_result#*:}"
    
    # Determine overall health
    local overall_status="unknown"
    local status_details=""
    
    if [ "$container_state" = "running" ]; then
        if [ "$endpoint_status" = "healthy" ]; then
            overall_status="healthy"
            status_details="Container: $container_state, Docker Health: $health_state, Endpoint: $endpoint_path"
        else
            overall_status="unhealthy"
            status_details="Container: $container_state, Docker Health: $health_state, Endpoint: failed"
        fi
    else
        overall_status="down"
        status_details="Container: $container_state"
    fi
    
    echo "$overall_status:$status_details"
}

monitor_health_patterns() {
    local current_time=$(date '+%H:%M')
    local current_hour=$(date '+%H')
    local current_minute=$(date '+%M')
    
    print_status "HEALTH" "Health check cycle - Time: $current_time"
    
    # Track service health status
    local healthy_services=0
    local total_services=${#FOGIS_SERVICES[@]}
    local unhealthy_services=()
    local down_services=()
    
    for service_info in "${FOGIS_SERVICES[@]}"; do
        local service_name="${service_info%:*}"
        local health_result=$(check_service_health "$service_info")
        local health_status="${health_result%:*}"
        local health_details="${health_result#*:}"
        
        case "$health_status" in
            "healthy")
                print_status "SUCCESS" "$service_name: $health_details"
                ((healthy_services++))
                ;;
            "unhealthy")
                print_status "WARNING" "$service_name: $health_details"
                unhealthy_services+=("$service_name")
                ;;
            "down")
                print_status "ERROR" "$service_name: $health_details"
                down_services+=("$service_name")
                ;;
            *)
                print_status "WARNING" "$service_name: Unknown status - $health_details"
                unhealthy_services+=("$service_name")
                ;;
        esac
    done
    
    # Generate alerts for problematic patterns
    if [ ${#down_services[@]} -gt 0 ]; then
        log_alert "Services DOWN: ${down_services[*]}"
    fi
    
    if [ ${#unhealthy_services[@]} -gt 0 ]; then
        log_alert "Services UNHEALTHY: ${unhealthy_services[*]}"
    fi
    
    # Special alert for 7:15-7:25 pattern
    if [ "$current_hour" = "07" ] && [ "$current_minute" -ge "15" ] && [ "$current_minute" -le "25" ]; then
        if [ ${#down_services[@]} -gt 0 ] || [ ${#unhealthy_services[@]} -gt 0 ]; then
            log_alert "CRITICAL PATTERN DETECTED: Services unhealthy during 7:15-7:25 window!"
        fi
    fi
    
    # Summary
    print_status "INFO" "Health Summary: $healthy_services/$total_services services healthy"
    
    if [ "$healthy_services" -eq "$total_services" ]; then
        print_status "SUCCESS" "All services healthy"
    else
        print_status "WARNING" "$((total_services - healthy_services)) services need attention"
    fi
    
    echo "----------------------------------------"
}

check_loki_health_logs() {
    local current_time=$(date -Iseconds)
    local five_minutes_ago=$(date -d "5 minutes ago" -Iseconds)
    
    # Query Loki for recent health logs
    local health_query='{container_name=~"fogis-.*|process-matches-.*|team-logo-.*|google-drive-.*"} |~ "(?i)(health|ping|status)"'
    
    local response=$(curl -s -G "http://localhost:3100/loki/api/v1/query_range" \
        --data-urlencode "query=$health_query" \
        --data-urlencode "start=$five_minutes_ago" \
        --data-urlencode "end=$current_time" \
        --data-urlencode "limit=50" 2>/dev/null)
    
    if echo "$response" | jq -e '.data.result | length' >/dev/null 2>&1; then
        local result_count=$(echo "$response" | jq '.data.result | length')
        local total_entries=0
        
        if [ "$result_count" -gt 0 ]; then
            for i in $(seq 0 $((result_count - 1))); do
                local stream_entries=$(echo "$response" | jq ".data.result[$i].values | length")
                total_entries=$((total_entries + stream_entries))
            done
            
            print_status "INFO" "Loki health logs: $total_entries entries from $result_count services in last 5 minutes"
        else
            print_status "WARNING" "No health logs found in Loki for last 5 minutes"
        fi
    else
        print_status "ERROR" "Failed to query Loki for health logs"
    fi
}

generate_hourly_report() {
    local current_minute=$(date '+%M')
    
    # Generate report at the top of each hour
    if [ "$current_minute" = "00" ]; then
        local report_time=$(date '+%Y-%m-%d %H:00')
        local report_file="./logs/hourly-health-report-$(date '+%Y%m%d-%H').log"
        
        {
            echo "FOGIS Health Report - $report_time"
            echo "=================================="
            echo
            
            # Service status summary
            echo "Service Status Summary:"
            for service_info in "${FOGIS_SERVICES[@]}"; do
                local service_name="${service_info%:*}"
                local health_result=$(check_service_health "$service_info")
                local health_status="${health_result%:*}"
                echo "  $service_name: $health_status"
            done
            
            echo
            echo "Recent Alerts (last hour):"
            tail -20 "$ALERT_FILE" | grep "$(date '+%Y-%m-%d %H')" || echo "  No alerts in last hour"
            
            echo
            echo "Next report: $(date -d '+1 hour' '+%Y-%m-%d %H:00')"
            
        } > "$report_file"
        
        print_status "INFO" "Hourly report generated: $report_file"
    fi
}

cleanup_old_logs() {
    # Clean up logs older than 7 days
    find "$(dirname "$LOG_FILE")" -name "*.log" -mtime +7 -delete 2>/dev/null || true
}

signal_handler() {
    print_status "INFO" "Received signal, shutting down health monitor..."
    echo "FOGIS Health Pattern Monitor Stopped: $(date)" >> "$LOG_FILE"
    exit 0
}

main() {
    echo "🏥 FOGIS Health Pattern Monitor"
    echo "==============================="
    echo "Monitoring health check patterns and service availability"
    echo "Press Ctrl+C to stop"
    echo
    
    # Set up signal handlers
    trap signal_handler SIGINT SIGTERM
    
    # Initialize monitoring
    setup_monitoring
    
    # Main monitoring loop
    while true; do
        monitor_health_patterns
        check_loki_health_logs
        generate_hourly_report
        cleanup_old_logs
        
        # Wait for next cycle
        sleep "$MONITOR_INTERVAL"
    done
}

# Check if running as main script
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
