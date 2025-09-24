#!/bin/bash

# FOGIS Logging Gap Fix Script
# Applies common fixes for logging gaps between midnight and 05:15

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SUCCESS="✅"
ERROR="❌"
WARNING="⚠️"
INFO="ℹ️"
FIX="🔧"

print_status() {
    local level=$1
    local message=$2
    
    case $level in
        "SUCCESS") echo -e "${GREEN}${SUCCESS} ${message}${NC}" ;;
        "ERROR") echo -e "${RED}${ERROR} ${message}${NC}" ;;
        "WARNING") echo -e "${YELLOW}${WARNING} ${message}${NC}" ;;
        "INFO") echo -e "${BLUE}${INFO} ${message}${NC}" ;;
        "FIX") echo -e "${BLUE}${FIX} ${message}${NC}" ;;
    esac
}

print_header() {
    echo
    echo "============================================================"
    echo "🔧 FOGIS Logging Gap Fix Tool"
    echo "============================================================"
    echo "Applying fixes for logging gaps between 00:00 and 05:15"
    echo
}

backup_configs() {
    print_status "FIX" "Creating backup of current configurations..."
    
    local backup_dir="./backups/logging-fix-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup configuration files
    cp docker-compose.yml "$backup_dir/" 2>/dev/null || true
    cp monitoring/loki-config.yaml "$backup_dir/" 2>/dev/null || true
    cp monitoring/promtail-config.yaml "$backup_dir/" 2>/dev/null || true
    
    print_status "SUCCESS" "Backup created at $backup_dir"
}

fix_timezone_configuration() {
    print_status "FIX" "Fixing timezone configuration..."
    
    # Create a temporary docker-compose override for timezone
    cat > docker-compose.timezone.yml << 'EOF'
version: '3.8'

services:
  loki:
    environment:
      - TZ=Europe/Stockholm
      
  promtail:
    environment:
      - TZ=Europe/Stockholm
      
  grafana:
    environment:
      - TZ=Europe/Stockholm
      - GF_DATE_FORMATS_DEFAULT_TIMEZONE=Europe/Stockholm
      
  process-matches-service:
    environment:
      - TZ=Europe/Stockholm
      
  fogis-calendar-phonebook-sync:
    environment:
      - TZ=Europe/Stockholm
      
  team-logo-combiner:
    environment:
      - TZ=Europe/Stockholm
      
  google-drive-service:
    environment:
      - TZ=Europe/Stockholm
EOF

    print_status "SUCCESS" "Created timezone override file: docker-compose.timezone.yml"
    print_status "INFO" "Apply with: docker-compose -f docker-compose.yml -f docker-compose.timezone.yml up -d"
}

fix_loki_configuration() {
    print_status "FIX" "Optimizing Loki configuration for gap prevention..."
    
    # Create an improved Loki configuration
    cat > monitoring/loki-config-improved.yaml << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096
  log_level: info

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 100

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

ruler:
  alertmanager_url: http://localhost:9093

# Enhanced limits configuration to prevent gaps
limits_config:
  enforce_metric_name: false
  reject_old_samples: false
  reject_old_samples_max_age: 168h  # 7 days - very generous
  creation_grace_period: 10m       # Allow logs up to 10 minutes in future
  ingestion_rate_mb: 32            # Increased ingestion rate
  ingestion_burst_size_mb: 64      # Increased burst size
  per_stream_rate_limit: 5MB       # Increased per-stream limit
  per_stream_rate_limit_burst: 25MB
  max_streams_per_user: 20000      # Increased stream limit
  max_line_size: 512000            # Increased line size limit
  retention_period: 720h           # 30 days retention
  max_query_length: 721h           # Allow queries slightly longer than retention
  max_query_parallelism: 32        # Increased parallelism
  max_query_series: 10000          # Increased series limit

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: true
  retention_period: 720h

compactor:
  working_directory: /loki/boltdb-shipper-compactor
  shared_store: filesystem
  compaction_interval: 5m          # More frequent compaction
  retention_enabled: true
  retention_delete_delay: 1h       # Shorter delete delay
  retention_delete_worker_count: 150

# Enhanced ingester configuration
ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 5m            # Shorter idle period
  chunk_retain_period: 30s         # Shorter retain period
  max_transfer_retries: 0
  wal:
    enabled: true
    dir: /loki/wal
    checkpoint_duration: 5m        # More frequent checkpoints
    flush_on_shutdown: true

analytics:
  reporting_enabled: false
EOF

    print_status "SUCCESS" "Created improved Loki configuration: monitoring/loki-config-improved.yaml"
    print_status "INFO" "To apply: cp monitoring/loki-config-improved.yaml monitoring/loki-config.yaml && docker-compose restart loki"
}

fix_promtail_configuration() {
    print_status "FIX" "Enhancing Promtail configuration for better log collection..."
    
    # Create an improved Promtail configuration
    cat > monitoring/promtail-config-improved.yaml << 'EOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0
  log_level: info

positions:
  filename: /tmp/positions.yaml
  sync_period: 10s

clients:
  - url: http://loki:3100/loki/api/v1/push
    timeout: 30s
    backoff_config:
      min_period: 500ms
      max_period: 5m
      max_retries: 10
    # Enhanced batch configuration
    batchsize: 1048576
    batchwait: 1s

scrape_configs:
  # Enhanced FOGIS Service Logs from Docker containers
  - job_name: fogis-services
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
        filters:
          - name: label
            values: ["com.docker.compose.project=fogis-deployment"]
    relabel_configs:
      - source_labels: ['__meta_docker_container_label_com_docker_compose_service']
        regex: '(fogis-.*|match-list-.*|process-matches-service|team-logo-combiner|google-drive-service|loki|grafana|promtail|fogis-event-collector)'
        target_label: __tmp_docker_service
      - source_labels: ['__tmp_docker_service']
        regex: '(.+)'
        target_label: service_name
      - source_labels: ['__meta_docker_container_name']
        target_label: container_name
      - source_labels: ['__meta_docker_container_log_stream']
        target_label: stream
      - source_labels: ['__meta_docker_container_label_com_docker_compose_project']
        target_label: project
    pipeline_stages:
      # Enhanced timestamp parsing with multiple formats
      - regex:
          expression: '(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.,]\d{3})\s*[-\s]*\s*(?P<level>DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)?\s*[-\s]*\s*(?P<message>.*)'
      - labels:
          level:
      - timestamp:
          source: timestamp
          format: '2006-01-02 15:04:05,000'
          fallback_formats:
            - '2006-01-02T15:04:05.000Z'
            - '2006-01-02T15:04:05.000'
            - '2006-01-02 15:04:05.000'
            - '2006-01-02T15:04:05,000'
          # Enhanced timezone handling
          location: 'Europe/Stockholm'
      
      # Add diagnostic labels for gap analysis
      - match:
          selector: '{service_name=~".*"}'
          stages:
            - regex:
                expression: '.*'
            - labels:
                log_processed_at: '{{ .timestamp }}'
                gap_analysis: 'enabled'
      
      # OAuth Authentication Events
      - match:
          selector: '{service_name=~"fogis-calendar-.*|google-drive-.*"}'
          stages:
            - regex:
                expression: '.*(?P<oauth_indicator>OAuth|authentication|token|credential).*'
            - labels:
                oauth_event: "true"
      
      # Service Health Events
      - match:
          selector: '{service_name=~".*"}'
          stages:
            - regex:
                expression: '.*(?P<health_status>healthy|unhealthy|starting|stopping|degraded).*'
            - labels:
                health_status:
      
      # Match Processing Events
      - match:
          selector: '{service_name=~"match-list-.*|process-matches-service"}'
          stages:
            - regex:
                expression: '.*(?P<match_event>new matches|changes detected|processing complete|match.*uploaded|calendar.*sync).*'
            - labels:
                match_event: "true"
      
      # Error and Exception Tracking
      - match:
          selector: '{level=~"ERROR|CRITICAL|FATAL"}'
          stages:
            - regex:
                expression: '.*(?P<error_type>Exception|Error|Traceback|Failed).*'
            - labels:
                error_event: "true"
                error_type:

  # Enhanced static log files with better timestamp handling
  - job_name: fogis-static-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: fogis-static-logs
          __path__: /var/log/fogis/*.log
    pipeline_stages:
      - regex:
          expression: '(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?P<level>\w+) (?P<service>\w+): (?P<message>.*)'
      - labels:
          level:
          service:
      - timestamp:
          source: timestamp
          format: '2006-01-02 15:04:05'
          location: 'Europe/Stockholm'

  # System logs with timezone awareness
  - job_name: system-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: system-logs
          __path__: /var/log/syslog
    pipeline_stages:
      - regex:
          expression: '(?P<timestamp>\w{3}\s+\d{1,2} \d{2}:\d{2}:\d{2}) (?P<hostname>\S+) (?P<service>\S+): (?P<message>.*)'
      - labels:
          hostname:
          service:
      - timestamp:
          source: timestamp
          format: 'Jan 02 15:04:05'
          location: 'Europe/Stockholm'
EOF

    print_status "SUCCESS" "Created improved Promtail configuration: monitoring/promtail-config-improved.yaml"
    print_status "INFO" "To apply: cp monitoring/promtail-config-improved.yaml monitoring/promtail-config.yaml && docker-compose restart promtail"
}

create_monitoring_script() {
    print_status "FIX" "Creating continuous monitoring script..."
    
    cat > scripts/monitor_logging_gaps.sh << 'EOF'
#!/bin/bash

# Continuous logging gap monitor
# Runs every hour to check for logging gaps

LOGFILE="./logs/gap-monitor.log"
mkdir -p "$(dirname "$LOGFILE")"

log_message() {
    echo "$(date -Iseconds) $1" | tee -a "$LOGFILE"
}

check_recent_logs() {
    local current_time=$(date +%s)
    local one_hour_ago=$((current_time - 3600))
    local start_time=$(date -d "@$one_hour_ago" -Iseconds)
    local end_time=$(date -d "@$current_time" -Iseconds)
    
    local query='{service_name=~"fogis-.*|match-list-.*|process-matches-service"}'
    local response=$(curl -s -G "http://localhost:3100/loki/api/v1/query_range" \
        --data-urlencode "query=$query" \
        --data-urlencode "start=$start_time" \
        --data-urlencode "end=$end_time" \
        --data-urlencode "limit=1")
    
    if echo "$response" | jq -e '.data.result | length' >/dev/null 2>&1; then
        local result_count=$(echo "$response" | jq '.data.result | length')
        if [ "$result_count" -gt 0 ]; then
            log_message "✅ Logs found for last hour: $result_count streams"
        else
            log_message "❌ NO LOGS found for last hour - potential gap detected!"
            # Send alert (implement your alerting mechanism here)
        fi
    else
        log_message "⚠️ Failed to query Loki for gap check"
    fi
}

log_message "🔍 Starting logging gap check..."
check_recent_logs
log_message "✅ Gap check completed"
EOF

    chmod +x scripts/monitor_logging_gaps.sh
    print_status "SUCCESS" "Created monitoring script: scripts/monitor_logging_gaps.sh"
    
    # Create cron job suggestion
    cat > scripts/setup_gap_monitoring_cron.sh << 'EOF'
#!/bin/bash

# Setup cron job for gap monitoring
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/monitor_logging_gaps.sh"

# Add cron job to run every hour
(crontab -l 2>/dev/null; echo "0 * * * * $SCRIPT_PATH") | crontab -

echo "✅ Cron job added to run gap monitoring every hour"
echo "📋 View cron jobs with: crontab -l"
echo "📋 View monitoring logs with: tail -f logs/gap-monitor.log"
EOF

    chmod +x scripts/setup_gap_monitoring_cron.sh
    print_status "SUCCESS" "Created cron setup script: scripts/setup_gap_monitoring_cron.sh"
}

apply_fixes() {
    print_status "FIX" "Applying logging gap fixes..."
    
    echo
    read -p "Apply timezone fixes? (y/N): " apply_timezone
    if [[ $apply_timezone =~ ^[Yy]$ ]]; then
        print_status "INFO" "Applying timezone configuration..."
        docker-compose -f docker-compose.yml -f docker-compose.timezone.yml up -d
        print_status "SUCCESS" "Timezone fixes applied"
    fi
    
    echo
    read -p "Apply improved Loki configuration? (y/N): " apply_loki
    if [[ $apply_loki =~ ^[Yy]$ ]]; then
        print_status "INFO" "Applying improved Loki configuration..."
        cp monitoring/loki-config-improved.yaml monitoring/loki-config.yaml
        docker-compose restart loki
        print_status "SUCCESS" "Loki configuration updated"
    fi
    
    echo
    read -p "Apply improved Promtail configuration? (y/N): " apply_promtail
    if [[ $apply_promtail =~ ^[Yy]$ ]]; then
        print_status "INFO" "Applying improved Promtail configuration..."
        cp monitoring/promtail-config-improved.yaml monitoring/promtail-config.yaml
        docker-compose restart promtail
        print_status "SUCCESS" "Promtail configuration updated"
    fi
    
    echo
    read -p "Setup continuous gap monitoring? (y/N): " setup_monitoring
    if [[ $setup_monitoring =~ ^[Yy]$ ]]; then
        print_status "INFO" "Setting up gap monitoring..."
        ./scripts/setup_gap_monitoring_cron.sh
        print_status "SUCCESS" "Gap monitoring setup completed"
    fi
}

print_next_steps() {
    print_status "INFO" "Next steps after applying fixes:"
    
    echo
    echo "1. 🔍 **Monitor the fixes**:"
    echo "   ./scripts/diagnose_logging_gap.sh"
    echo
    echo "2. 📊 **Check Grafana dashboard**:"
    echo "   http://localhost:3000"
    echo
    echo "3. 🔄 **Verify log ingestion**:"
    echo "   curl -G 'http://localhost:3100/loki/api/v1/query_range' \\"
    echo "     --data-urlencode 'query={service_name=~\".*\"}' \\"
    echo "     --data-urlencode 'start=$(date -d '1 hour ago' -Iseconds)' \\"
    echo "     --data-urlencode 'end=$(date -Iseconds)'"
    echo
    echo "4. 📋 **Monitor gap detection**:"
    echo "   tail -f logs/gap-monitor.log"
    echo
    echo "5. 🔧 **If gaps persist**:"
    echo "   - Check service activity during gap hours"
    echo "   - Verify timezone settings are consistent"
    echo "   - Check disk space and retention policies"
    echo "   - Review Promtail and Loki logs for errors"
    echo
}

main() {
    print_header
    
    cd "$(dirname "$0")/.."
    
    print_status "INFO" "Starting logging gap fix process..."
    print_status "INFO" "Current directory: $(pwd)"
    
    backup_configs
    fix_timezone_configuration
    fix_loki_configuration
    fix_promtail_configuration
    create_monitoring_script
    
    echo
    print_status "SUCCESS" "All fix configurations prepared!"
    
    apply_fixes
    print_next_steps
}

main "$@"
EOF
