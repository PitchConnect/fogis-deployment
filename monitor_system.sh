#!/bin/bash

# FOGIS System Monitoring Script
# Checks system health and sends alerts if issues are detected

set -e

# Configuration
ALERT_EMAIL=""  # Set this to receive email alerts
CHECK_INTERVAL=300  # 5 minutes
LOG_FILE="./logs/system-monitor.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_with_timestamp() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_service_health() {
    local service=$1
    local port=$2

    if curl -f "http://localhost:$port/health" &>/dev/null; then
        return 0
    else
        return 1
    fi
}

check_all_services() {
    local services=(
        "fogis-api-client-service:9086"
        "match-list-change-detector:9082"
        "match-list-processor:9081"
        "team-logo-combiner:9088"
        "google-drive-service:9085"
        "fogis-calendar-phonebook-sync:9083"
    )

    local failed_services=()

    for service_port in "${services[@]}"; do
        local service=$(echo "$service_port" | cut -d: -f1)
        local port=$(echo "$service_port" | cut -d: -f2)

        if ! check_service_health "$service" "$port"; then
            failed_services+=("$service")
        fi
    done

    if [ ${#failed_services[@]} -gt 0 ]; then
        log_with_timestamp "❌ UNHEALTHY SERVICES: ${failed_services[*]}"
        return 1
    else
        log_with_timestamp "✅ All services healthy"
        return 0
    fi
}

check_token_expiry() {
    local token_file="data/fogis-calendar-phonebook-sync/token.json"

    if [ -f "$token_file" ]; then
        # Extract expiry date from token (this is a simplified check)
        local expiry=$(python3 -c "
import json, datetime
try:
    with open('$token_file', 'r') as f:
        token = json.load(f)
    expiry = datetime.datetime.fromisoformat(token['expiry'].replace('Z', '+00:00'))
    now = datetime.datetime.now(datetime.timezone.utc)
    days_left = (expiry - now).days
    print(days_left)
except:
    print(-1)
" 2>/dev/null)

        if [ "$expiry" -lt 2 ]; then
            log_with_timestamp "⚠️  Google tokens expire in $expiry days"
            return 1
        fi
    else
        log_with_timestamp "❌ Token file missing"
        return 1
    fi

    return 0
}

send_alert() {
    local message=$1

    log_with_timestamp "🚨 ALERT: $message"

    if [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "FOGIS System Alert" "$ALERT_EMAIL" 2>/dev/null || true
    fi
}

monitor_once() {
    if ! check_all_services; then
        send_alert "FOGIS services are unhealthy. Run ./recover_system.sh"
        return 1
    fi

    if ! check_token_expiry; then
        send_alert "FOGIS authentication tokens need renewal. Run python authenticate_all_services.py"
    fi

    return 0
}

monitor_continuous() {
    log_with_timestamp "🔍 Starting continuous monitoring (interval: ${CHECK_INTERVAL}s)"

    while true; do
        monitor_once
        sleep "$CHECK_INTERVAL"
    done
}

show_status() {
    echo "🔍 FOGIS SYSTEM STATUS"
    echo "===================="

    echo ""
    echo "📊 Service Health:"
    local services=(
        "fogis-api-client-service:9086"
        "match-list-change-detector:9082"
        "match-list-processor:9081"
        "team-logo-combiner:9088"
        "google-drive-service:9085"
        "fogis-calendar-phonebook-sync:9083"
    )

    for service_port in "${services[@]}"; do
        local service=$(echo "$service_port" | cut -d: -f1)
        local port=$(echo "$service_port" | cut -d: -f2)

        if check_service_health "$service" "$port"; then
            echo -e "  ✅ $service"
        else
            echo -e "  ❌ $service"
        fi
    done

    echo ""
    echo "🔐 Authentication Status:"
    if [ -f "data/fogis-calendar-phonebook-sync/token.json" ]; then
        echo "  ✅ Calendar/Contacts token present"
    else
        echo "  ❌ Calendar/Contacts token missing"
    fi

    if [ -f "data/google-drive-service/google-drive-token.json" ]; then
        echo "  ✅ Google Drive token present"
    else
        echo "  ❌ Google Drive token missing"
    fi

    echo ""
    echo "📁 Data Persistence:"
    if [ -f "data/match-list-change-detector/previous_matches.json" ]; then
        local match_count=$(jq length data/match-list-change-detector/previous_matches.json 2>/dev/null || echo "unknown")
        echo "  ✅ Match history: $match_count matches tracked"
    else
        echo "  ❌ Match history missing"
    fi
}

case "${1:-status}" in
    "status")
        show_status
        ;;
    "check")
        monitor_once
        ;;
    "monitor")
        monitor_continuous
        ;;
    *)
        echo "Usage: $0 [status|check|monitor]"
        echo ""
        echo "Commands:"
        echo "  status  - Show current system status"
        echo "  check   - Run single health check"
        echo "  monitor - Start continuous monitoring"
        exit 1
        ;;
esac
