#!/bin/bash

# FOGIS Logging Gap Diagnostic Script
# Diagnoses logging gaps between midnight (00:00) and 05:15

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
SEARCH="🔍"
TIME="⏰"
LOG="📋"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

print_status() {
    local level=$1
    local message=$2
    
    case $level in
        "SUCCESS")
            echo -e "${GREEN}${SUCCESS} ${message}${NC}"
            ;;
        "ERROR")
            echo -e "${RED}${ERROR} ${message}${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}${WARNING} ${message}${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}${INFO} ${message}${NC}"
            ;;
        "SEARCH")
            echo -e "${CYAN}${SEARCH} ${message}${NC}"
            ;;
        "TIME")
            echo -e "${PURPLE}${TIME} ${message}${NC}"
            ;;
        "LOG")
            echo -e "${BLUE}${LOG} ${message}${NC}"
            ;;
    esac
}

print_header() {
    echo
    echo "============================================================"
    echo "🔍 FOGIS Logging Gap Diagnostic Tool"
    echo "============================================================"
    echo "Investigating logging gap between 00:00 and 05:15"
    echo
}

check_prerequisites() {
    print_status "INFO" "Checking prerequisites..."
    
    # Check if we're in the deployment directory
    if [ ! -f "docker-compose.yml" ]; then
        print_status "ERROR" "docker-compose.yml not found. Please run from FOGIS deployment directory."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_status "ERROR" "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check if logging services are running
    if ! docker ps | grep -q "fogis-loki"; then
        print_status "ERROR" "Loki container not running. Please start the logging stack."
        exit 1
    fi
    
    if ! docker ps | grep -q "fogis-promtail"; then
        print_status "ERROR" "Promtail container not running. Please start the logging stack."
        exit 1
    fi
    
    print_status "SUCCESS" "Prerequisites check completed"
}

check_timezone_configuration() {
    print_status "TIME" "Checking timezone configuration..."
    
    echo
    echo "=== Container Timezone Information ==="
    
    # Check Loki timezone
    print_status "INFO" "Loki container timezone:"
    docker exec fogis-loki date || print_status "WARNING" "Could not get Loki timezone"
    
    # Check Promtail timezone
    print_status "INFO" "Promtail container timezone:"
    docker exec fogis-promtail date || print_status "WARNING" "Could not get Promtail timezone"
    
    # Check Grafana timezone
    print_status "INFO" "Grafana container timezone:"
    docker exec fogis-grafana date || print_status "WARNING" "Could not get Grafana timezone"
    
    # Check FOGIS services timezone
    print_status "INFO" "Process-matches-service timezone:"
    docker exec process-matches-service date || print_status "WARNING" "Could not get service timezone"
    
    # Check host timezone
    print_status "INFO" "Host system timezone:"
    date
    echo "Host timezone: $(timedatectl show --property=Timezone --value 2>/dev/null || echo 'Unknown')"
    
    echo
}

check_loki_data_ingestion() {
    print_status "SEARCH" "Checking Loki data ingestion..."
    
    # Get current time and calculate time range for investigation
    local current_time=$(date +%s)
    local yesterday_midnight=$((current_time - 86400))  # 24 hours ago
    local today_morning=$((current_time - 43200))       # 12 hours ago
    
    # Convert to RFC3339 format for Loki API
    local start_time=$(date -d "@$yesterday_midnight" -Iseconds)
    local end_time=$(date -d "@$today_morning" -Iseconds)
    
    print_status "INFO" "Querying Loki for logs between $start_time and $end_time"
    
    # Query Loki API directly for log entries in the gap period
    local loki_url="http://localhost:3100"
    local query='{service_name=~"fogis-.*|match-list-.*|process-matches-service"}'
    
    echo
    echo "=== Loki API Query Results ==="
    
    # Check if Loki is responding
    if curl -s "$loki_url/ready" >/dev/null; then
        print_status "SUCCESS" "Loki is responding"
        
        # Query for logs in the gap period
        local api_response=$(curl -s -G "$loki_url/loki/api/v1/query_range" \
            --data-urlencode "query=$query" \
            --data-urlencode "start=$start_time" \
            --data-urlencode "end=$end_time" \
            --data-urlencode "limit=100")
        
        if echo "$api_response" | jq -e '.data.result | length' >/dev/null 2>&1; then
            local result_count=$(echo "$api_response" | jq '.data.result | length')
            print_status "INFO" "Found $result_count log streams in Loki for the time period"
            
            if [ "$result_count" -gt 0 ]; then
                echo "Sample log entries:"
                echo "$api_response" | jq -r '.data.result[0].values[0:3][] | .[1]' 2>/dev/null || echo "No log values found"
            else
                print_status "WARNING" "No logs found in Loki for the specified time period"
            fi
        else
            print_status "ERROR" "Failed to parse Loki API response"
            echo "Raw response: $api_response"
        fi
    else
        print_status "ERROR" "Loki is not responding at $loki_url"
    fi
    
    echo
}

check_promtail_collection() {
    print_status "SEARCH" "Checking Promtail log collection..."
    
    echo
    echo "=== Promtail Status and Configuration ==="
    
    # Check Promtail metrics
    local promtail_url="http://localhost:9080"
    
    if curl -s "$promtail_url/metrics" >/dev/null; then
        print_status "SUCCESS" "Promtail metrics endpoint is responding"
        
        # Get Promtail metrics
        echo "Promtail log entries read:"
        curl -s "$promtail_url/metrics" | grep "promtail_read_lines_total" | head -5
        
        echo
        echo "Promtail files being watched:"
        curl -s "$promtail_url/metrics" | grep "promtail_files_active_total"
        
        echo
        echo "Promtail targets:"
        curl -s "$promtail_url/api/v1/targets" | jq '.data[] | {job: .labels.job, health: .health, lastScrape: .lastScrape}' 2>/dev/null || echo "Could not parse targets"
        
    else
        print_status "ERROR" "Promtail metrics endpoint not responding at $promtail_url"
    fi
    
    # Check Promtail logs
    print_status "INFO" "Recent Promtail container logs:"
    docker logs fogis-promtail --tail 20 --since 1h
    
    echo
}

check_service_activity() {
    print_status "SEARCH" "Checking FOGIS service activity during gap period..."
    
    echo
    echo "=== Service Log File Analysis ==="
    
    # Check log files in the logs directory
    local services=("process-matches-service" "fogis-calendar-phonebook-sync" "team-logo-combiner" "google-drive-service")
    
    for service in "${services[@]}"; do
        print_status "INFO" "Checking $service logs..."
        
        local log_dir="./logs/$service"
        if [ -d "$log_dir" ]; then
            # Find log files
            local log_files=$(find "$log_dir" -name "*.log" -type f 2>/dev/null)
            
            if [ -n "$log_files" ]; then
                echo "Log files found for $service:"
                ls -la "$log_dir"/*.log 2>/dev/null || echo "No .log files found"
                
                # Check for entries in the gap period (last 24 hours)
                echo "Recent log entries (last 50 lines):"
                for log_file in $log_files; do
                    if [ -f "$log_file" ]; then
                        echo "--- $log_file ---"
                        tail -50 "$log_file" | head -10
                        echo
                    fi
                done
            else
                print_status "WARNING" "No log files found for $service"
            fi
        else
            print_status "WARNING" "Log directory not found for $service: $log_dir"
        fi
        
        # Check container logs
        print_status "INFO" "Container logs for $service (last 1 hour):"
        if docker ps | grep -q "$service"; then
            docker logs "$service" --since 1h --tail 10 2>/dev/null || print_status "WARNING" "Could not get container logs for $service"
        else
            print_status "WARNING" "Container $service is not running"
        fi
        
        echo "----------------------------------------"
    done
    
    echo
}

check_log_retention() {
    print_status "SEARCH" "Checking log retention policies..."
    
    echo
    echo "=== Log Retention Configuration ==="
    
    # Check Loki retention settings
    print_status "INFO" "Loki retention configuration:"
    grep -A 5 -B 5 "retention" monitoring/loki-config.yaml || print_status "WARNING" "Could not find retention config"
    
    echo
    
    # Check disk space
    print_status "INFO" "Disk space usage:"
    df -h ./monitoring/loki/ 2>/dev/null || print_status "WARNING" "Could not check Loki disk usage"
    df -h ./logs/ 2>/dev/null || print_status "WARNING" "Could not check logs disk usage"
    
    echo
    
    # Check Loki data directory
    print_status "INFO" "Loki data directory contents:"
    ls -la ./monitoring/loki/ 2>/dev/null || print_status "WARNING" "Could not list Loki directory"
    
    echo
}

check_grafana_dashboard() {
    print_status "SEARCH" "Checking Grafana dashboard configuration..."
    
    echo
    echo "=== Grafana Dashboard Analysis ==="
    
    # Check if Grafana is responding
    local grafana_url="http://localhost:3000"
    
    if curl -s "$grafana_url/api/health" >/dev/null; then
        print_status "SUCCESS" "Grafana is responding"
        
        # Check dashboard queries
        print_status "INFO" "Analyzing dashboard queries in fogis-logs-working.json..."
        
        if [ -f "monitoring/grafana/dashboards/fogis-logs-working.json" ]; then
            # Extract time range settings
            echo "Dashboard time range settings:"
            jq -r '.time // "No time settings found"' monitoring/grafana/dashboards/fogis-logs-working.json
            
            echo
            echo "Dashboard refresh settings:"
            jq -r '.refresh // "No refresh settings found"' monitoring/grafana/dashboards/fogis-logs-working.json
            
            echo
            echo "Sample query expressions:"
            jq -r '.panels[].targets[]?.expr // empty' monitoring/grafana/dashboards/fogis-logs-working.json | head -5
            
        else
            print_status "WARNING" "Dashboard file not found"
        fi
        
    else
        print_status "ERROR" "Grafana is not responding at $grafana_url"
    fi
    
    echo
}

generate_test_logs() {
    print_status "INFO" "Generating test logs to verify pipeline..."
    
    echo
    echo "=== Test Log Generation ==="
    
    # Generate test logs in running services
    local services=("process-matches-service" "fogis-calendar-phonebook-sync")
    
    for service in "${services[@]}"; do
        if docker ps | grep -q "$service"; then
            print_status "INFO" "Generating test log in $service..."
            
            # Generate a test log entry
            docker exec "$service" sh -c "echo '$(date -Iseconds) INFO DIAGNOSTIC: Test log entry for gap analysis - $(date)' >> /app/logs/*.log" 2>/dev/null || \
            docker exec "$service" sh -c "echo '$(date -Iseconds) INFO DIAGNOSTIC: Test log entry for gap analysis - $(date)'" || \
            print_status "WARNING" "Could not generate test log for $service"
        else
            print_status "WARNING" "Service $service is not running"
        fi
    done
    
    echo
    print_status "INFO" "Wait 30 seconds for logs to be processed..."
    sleep 30
    
    # Check if test logs appear in Loki
    print_status "INFO" "Checking if test logs appear in Loki..."
    local test_query='{service_name=~".*"} |= "DIAGNOSTIC"'
    local current_time=$(date -Iseconds)
    local five_minutes_ago=$(date -d "5 minutes ago" -Iseconds)
    
    local test_response=$(curl -s -G "http://localhost:3100/loki/api/v1/query_range" \
        --data-urlencode "query=$test_query" \
        --data-urlencode "start=$five_minutes_ago" \
        --data-urlencode "end=$current_time" \
        --data-urlencode "limit=10")
    
    if echo "$test_response" | jq -e '.data.result | length' >/dev/null 2>&1; then
        local test_result_count=$(echo "$test_response" | jq '.data.result | length')
        if [ "$test_result_count" -gt 0 ]; then
            print_status "SUCCESS" "Test logs found in Loki - pipeline is working"
        else
            print_status "WARNING" "Test logs not found in Loki - pipeline may have issues"
        fi
    else
        print_status "ERROR" "Could not query Loki for test logs"
    fi
    
    echo
}

print_recommendations() {
    print_status "INFO" "Diagnostic recommendations based on findings:"
    
    echo
    echo "=== Troubleshooting Steps ==="
    echo
    echo "1. 🕐 **Timezone Issues**:"
    echo "   - Ensure all containers use the same timezone"
    echo "   - Add TZ environment variable to docker-compose.yml:"
    echo "     environment:"
    echo "       - TZ=Europe/Stockholm"
    echo
    echo "2. 📋 **Service Activity**:"
    echo "   - Check if services are actually running during 00:00-05:15"
    echo "   - Verify service scheduling and cron jobs"
    echo "   - Check if services are in maintenance mode"
    echo
    echo "3. 🔧 **Promtail Configuration**:"
    echo "   - Verify Promtail is reading from correct log paths"
    echo "   - Check Promtail timestamp parsing"
    echo "   - Ensure Docker socket permissions are correct"
    echo
    echo "4. 💾 **Loki Retention**:"
    echo "   - Check if logs are being deleted too early"
    echo "   - Verify retention_period setting in loki-config.yaml"
    echo "   - Check disk space availability"
    echo
    echo "5. 📊 **Grafana Dashboard**:"
    echo "   - Verify dashboard time range settings"
    echo "   - Check query time filters"
    echo "   - Ensure correct timezone in Grafana settings"
    echo
    echo "=== Immediate Actions ==="
    echo
    echo "• Monitor logs in real-time:"
    echo "  docker logs -f fogis-promtail"
    echo
    echo "• Query Loki directly for specific time:"
    echo "  curl -G 'http://localhost:3100/loki/api/v1/query_range' \\"
    echo "    --data-urlencode 'query={service_name=~\".*\"}' \\"
    echo "    --data-urlencode 'start=2025-01-01T00:00:00Z' \\"
    echo "    --data-urlencode 'end=2025-01-01T05:15:00Z'"
    echo
    echo "• Check service logs directly:"
    echo "  tail -f logs/process-matches-service/*.log"
    echo
    echo "• Restart logging stack if needed:"
    echo "  docker-compose restart loki promtail grafana"
    echo
}

main() {
    print_header
    
    cd "$DEPLOYMENT_ROOT"
    
    print_status "INFO" "Starting logging gap diagnostic..."
    print_status "INFO" "Deployment directory: $(pwd)"
    print_status "INFO" "Current time: $(date)"
    
    # Run diagnostic steps
    check_prerequisites
    check_timezone_configuration
    check_loki_data_ingestion
    check_promtail_collection
    check_service_activity
    check_log_retention
    check_grafana_dashboard
    generate_test_logs
    
    echo
    print_status "SUCCESS" "Diagnostic completed!"
    
    print_recommendations
}

# Run main function
main "$@"
