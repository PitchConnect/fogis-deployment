#!/bin/bash

# Quick Loki Diagnostic Queries
# Provides immediate diagnostic queries for the logging gap issue

set -euo pipefail

LOKI_URL="http://localhost:3100"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}$1${NC}"
    echo "----------------------------------------"
}

query_loki() {
    local query="$1"
    local start="$2"
    local end="$3"
    local description="$4"
    
    echo -e "${YELLOW}Query: $description${NC}"
    echo "Time range: $start to $end"
    echo "LogQL: $query"
    echo
    
    local response=$(curl -s -G "$LOKI_URL/loki/api/v1/query_range" \
        --data-urlencode "query=$query" \
        --data-urlencode "start=$start" \
        --data-urlencode "end=$end" \
        --data-urlencode "limit=100" 2>/dev/null)
    
    if echo "$response" | jq -e '.data.result | length' >/dev/null 2>&1; then
        local result_count=$(echo "$response" | jq '.data.result | length')
        local total_entries=0
        
        if [ "$result_count" -gt 0 ]; then
            # Count total log entries across all streams
            for i in $(seq 0 $((result_count - 1))); do
                local stream_entries=$(echo "$response" | jq ".data.result[$i].values | length")
                total_entries=$((total_entries + stream_entries))
            done
            
            echo -e "${GREEN}✅ Found $result_count streams with $total_entries total log entries${NC}"
            
            # Show sample entries
            echo "Sample log entries:"
            echo "$response" | jq -r '.data.result[0].values[0:3][]? | .[1]' 2>/dev/null | head -3 || echo "No sample entries available"
        else
            echo -e "${YELLOW}⚠️ No log streams found for this time period${NC}"
        fi
    else
        echo -e "${YELLOW}❌ Failed to query Loki or parse response${NC}"
        echo "Raw response: $response" | head -200
    fi
    
    echo
    echo "----------------------------------------"
    echo
}

main() {
    echo "🔍 FOGIS Loki Quick Diagnostic Queries"
    echo "======================================"
    echo
    
    # Check if Loki is responding
    if ! curl -s "$LOKI_URL/ready" >/dev/null; then
        echo "❌ Loki is not responding at $LOKI_URL"
        echo "Please ensure Loki container is running: docker ps | grep loki"
        exit 1
    fi
    
    echo "✅ Loki is responding"
    echo
    
    # Calculate time ranges
    local current_time=$(date +%s)
    local today_midnight=$(date -d "today 00:00" +%s)
    local today_0515=$(date -d "today 05:15" +%s)
    local yesterday_midnight=$(date -d "yesterday 00:00" +%s)
    local yesterday_0515=$(date -d "yesterday 05:15" +%s)
    local last_24h=$((current_time - 86400))
    
    # Convert to RFC3339 format
    local today_midnight_rfc=$(date -d "@$today_midnight" -Iseconds)
    local today_0515_rfc=$(date -d "@$today_0515" -Iseconds)
    local yesterday_midnight_rfc=$(date -d "@$yesterday_midnight" -Iseconds)
    local yesterday_0515_rfc=$(date -d "@$yesterday_0515" -Iseconds)
    local last_24h_rfc=$(date -d "@$last_24h" -Iseconds)
    local current_time_rfc=$(date -d "@$current_time" -Iseconds)
    
    # Query 1: Check today's gap period (00:00-05:15)
    print_header "1. Today's Gap Period (00:00-05:15)"
    query_loki '{service_name=~"fogis-.*|match-list-.*|process-matches-service"}' \
        "$today_midnight_rfc" "$today_0515_rfc" \
        "All FOGIS services during today's gap period"
    
    # Query 2: Check yesterday's gap period (00:00-05:15)
    print_header "2. Yesterday's Gap Period (00:00-05:15)"
    query_loki '{service_name=~"fogis-.*|match-list-.*|process-matches-service"}' \
        "$yesterday_midnight_rfc" "$yesterday_0515_rfc" \
        "All FOGIS services during yesterday's gap period"
    
    # Query 3: Check last 24 hours for comparison
    print_header "3. Last 24 Hours (for comparison)"
    query_loki '{service_name=~"fogis-.*|match-list-.*|process-matches-service"}' \
        "$last_24h_rfc" "$current_time_rfc" \
        "All FOGIS services in last 24 hours"
    
    # Query 4: Check specific services during gap
    print_header "4. Process Matches Service During Gap"
    query_loki '{service_name="process-matches-service"}' \
        "$today_midnight_rfc" "$today_0515_rfc" \
        "Process matches service during gap period"
    
    # Query 5: Check for any logs with timestamps in gap period
    print_header "5. Any Logs with Gap Period Timestamps"
    query_loki '{job=~".*"}' \
        "$today_midnight_rfc" "$today_0515_rfc" \
        "Any logs from any job during gap period"
    
    # Query 6: Check Promtail and Loki internal logs
    print_header "6. Logging Infrastructure Logs"
    query_loki '{container_name=~"fogis-loki|fogis-promtail"}' \
        "$yesterday_midnight_rfc" "$current_time_rfc" \
        "Loki and Promtail container logs"
    
    # Query 7: Check for error logs during gap period
    print_header "7. Error Logs During Gap Period"
    query_loki '{service_name=~".*"} |= "ERROR"' \
        "$today_midnight_rfc" "$today_0515_rfc" \
        "Error logs during gap period"
    
    # Summary and recommendations
    print_header "Summary and Next Steps"
    echo "If no logs are found in queries 1-5 but logs exist in query 3:"
    echo "• Services may not be active during 00:00-05:15"
    echo "• Check service scheduling and cron jobs"
    echo "• Verify if services are in maintenance mode"
    echo
    echo "If query 6 shows errors:"
    echo "• Check Loki and Promtail configuration"
    echo "• Verify disk space and permissions"
    echo "• Check Docker container health"
    echo
    echo "If query 7 shows errors during gap:"
    echo "• Investigate specific error messages"
    echo "• Check service health during gap period"
    echo
    echo "Additional diagnostic commands:"
    echo "• Check container logs: docker logs fogis-promtail --since 24h"
    echo "• Check service activity: docker logs process-matches-service --since 24h"
    echo "• Run full diagnostic: ./scripts/diagnose_logging_gap.sh"
    echo "• Apply fixes: ./scripts/fix_logging_gap.sh"
}

main "$@"
