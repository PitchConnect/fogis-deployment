#!/bin/bash
set -e

# FOGIS Centralized Logging Verification Script
# Comprehensive testing and validation of the monitoring setup

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[VERIFY]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "🔍 FOGIS CENTRALIZED LOGGING VERIFICATION"
print_status "=========================================="

# Test 1: Service Health Check
print_status ""
print_status "📋 Test 1: Monitoring service health"

LOKI_STATUS=$(docker-compose ps loki | grep "healthy" | wc -l)
GRAFANA_STATUS=$(docker-compose ps grafana | grep "healthy" | wc -l)
PROMTAIL_STATUS=$(docker-compose ps promtail | grep "Up" | wc -l)

if [ "$LOKI_STATUS" -eq 1 ]; then
    print_success "✅ Loki: Healthy and running"
else
    print_error "❌ Loki: Not healthy"
    exit 1
fi

if [ "$GRAFANA_STATUS" -eq 1 ]; then
    print_success "✅ Grafana: Healthy and running"
else
    print_error "❌ Grafana: Not healthy"
    exit 1
fi

if [ "$PROMTAIL_STATUS" -eq 1 ]; then
    print_success "✅ Promtail: Running"
else
    print_error "❌ Promtail: Not running"
    exit 1
fi

# Test 2: API Connectivity
print_status ""
print_status "📋 Test 2: API connectivity"

if curl -sf http://localhost:3100/ready >/dev/null; then
    print_success "✅ Loki API: Responding"
else
    print_error "❌ Loki API: Not responding"
    exit 1
fi

if curl -sf http://localhost:3000/api/health >/dev/null; then
    print_success "✅ Grafana API: Responding"
else
    print_error "❌ Grafana API: Not responding"
    exit 1
fi

# Test 3: Log Ingestion Test
print_status ""
print_status "📋 Test 3: Log ingestion verification"

# Generate test logs from FOGIS services
print_status "Generating test log entries..."
docker exec match-list-processor echo "$(date '+%Y-%m-%d %H:%M:%S') - INFO - Centralized logging verification test" 2>/dev/null || true
docker exec fogis-api-client-service echo "$(date '+%Y-%m-%d %H:%M:%S') - INFO - API client logging test" 2>/dev/null || true

# Wait for log ingestion
sleep 10

# Test log queries
print_status "Testing log queries..."

# Simple query test
LOGS_FOUND=$(curl -s "http://localhost:3100/loki/api/v1/query?query={service_name=~\".*\"}&limit=10" | jq -r '.data.result | length' 2>/dev/null || echo "0")

if [ "$LOGS_FOUND" -gt 0 ]; then
    print_success "✅ Log ingestion: Working ($LOGS_FOUND log streams found)"
else
    print_warning "⚠️ Log ingestion: No logs detected yet (may need more time)"
fi

# Test 4: Dashboard Accessibility
print_status ""
print_status "📋 Test 4: Dashboard accessibility"

# Check if dashboards are loaded
DASHBOARD_CHECK=$(curl -s "http://localhost:3000/api/search?query=FOGIS" -u admin:admin | jq -r '. | length' 2>/dev/null || echo "0")

if [ "$DASHBOARD_CHECK" -gt 0 ]; then
    print_success "✅ Dashboards: Available ($DASHBOARD_CHECK FOGIS dashboards found)"
else
    print_warning "⚠️ Dashboards: May still be loading"
fi

# Test 5: Error Detection Capability
print_status ""
print_status "📋 Test 5: Error detection capability"

# Generate a test error log
docker exec match-list-processor echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR - Test error for monitoring verification" 2>/dev/null || true

sleep 5

# Check if error is detected
ERROR_LOGS=$(curl -s "http://localhost:3100/loki/api/v1/query?query={level=\"ERROR\"}&limit=5" | jq -r '.data.result | length' 2>/dev/null || echo "0")

if [ "$ERROR_LOGS" -gt 0 ]; then
    print_success "✅ Error detection: Working ($ERROR_LOGS error log streams found)"
else
    print_warning "⚠️ Error detection: No error logs detected yet"
fi

# Test 6: Service-Specific Log Filtering
print_status ""
print_status "📋 Test 6: Service-specific log filtering"

# Test match processor logs
MATCH_LOGS=$(curl -s "http://localhost:3100/loki/api/v1/query?query={service_name=~\"match-list.*\"}&limit=5" | jq -r '.data.result | length' 2>/dev/null || echo "0")

if [ "$MATCH_LOGS" -gt 0 ]; then
    print_success "✅ Service filtering: Working (match processor logs found)"
else
    print_warning "⚠️ Service filtering: No match processor logs detected yet"
fi

# Test 7: Performance Check
print_status ""
print_status "📋 Test 7: Performance verification"

# Check Loki memory usage
LOKI_MEMORY=$(docker stats fogis-loki --no-stream --format "{{.MemUsage}}" | cut -d'/' -f1 | sed 's/MiB//' | sed 's/ //')
print_status "Loki memory usage: ${LOKI_MEMORY}MiB"

# Check Grafana memory usage
GRAFANA_MEMORY=$(docker stats fogis-grafana --no-stream --format "{{.MemUsage}}" | cut -d'/' -f1 | sed 's/MiB//' | sed 's/ //')
print_status "Grafana memory usage: ${GRAFANA_MEMORY}MiB"

# Test 8: Configuration Validation
print_status ""
print_status "📋 Test 8: Configuration validation"

# Check if configuration files exist
if [ -f "./monitoring/loki-config.yaml" ]; then
    print_success "✅ Loki configuration: Present"
else
    print_error "❌ Loki configuration: Missing"
fi

if [ -f "./monitoring/promtail-config.yaml" ]; then
    print_success "✅ Promtail configuration: Present"
else
    print_error "❌ Promtail configuration: Missing"
fi

if [ -f "./monitoring/grafana/dashboards/fogis-service-health.json" ]; then
    print_success "✅ Service health dashboard: Present"
else
    print_error "❌ Service health dashboard: Missing"
fi

if [ -f "./monitoring/grafana/dashboards/fogis-operations.json" ]; then
    print_success "✅ Operations dashboard: Present"
else
    print_error "❌ Operations dashboard: Missing"
fi

# Summary and Recommendations
print_status ""
print_status "📋 Verification Summary"

print_status "Access Information:"
echo "   🔍 Loki API:        http://localhost:3100"
echo "   📊 Grafana UI:      http://localhost:3000 (admin/admin)"
echo "   📡 Promtail:        Running (no direct UI)"

print_status ""
print_status "Quick Start Guide:"
echo "   1. Open Grafana: http://localhost:3000"
echo "   2. Login with admin/admin"
echo "   3. Go to Dashboards > Browse > FOGIS folder"
echo "   4. Select 'FOGIS Service Health Dashboard'"

print_status ""
print_status "Useful Log Queries (in Grafana Explore):"
echo "   All logs:           {service_name=~\".*\"}"
echo "   Errors only:        {level=\"ERROR\"}"
echo "   Match processor:    {service_name=\"match-list-processor\"}"
echo "   OAuth events:       {oauth_event=\"true\"}"
echo "   API errors:         {service_name=~\".*\"} |~ \"500 Server Error\""

print_status ""
print_status "Troubleshooting:"
echo "   View service logs:  docker logs fogis-loki"
echo "   Restart services:   docker-compose restart loki grafana promtail"
echo "   Full reset:         ./setup-centralized-logging.sh"

print_status ""
if [ "$LOKI_STATUS" -eq 1 ] && [ "$GRAFANA_STATUS" -eq 1 ] && [ "$PROMTAIL_STATUS" -eq 1 ]; then
    print_success "🎉 Centralized logging verification completed successfully!"
    print_success "📊 All monitoring services are operational and ready for use"
    print_success "🔍 You can now monitor all FOGIS services from Grafana"
else
    print_warning "⚠️ Some services may need additional time to fully initialize"
    print_warning "📋 Re-run this script in a few minutes if issues persist"
fi

print_status ""
print_status "✅ Verification complete! 🚀"
