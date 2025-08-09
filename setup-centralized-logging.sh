#!/bin/bash
set -e

# FOGIS Centralized Logging and Monitoring Setup Script
# Implements comprehensive logging, monitoring, and alerting solution

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[SETUP]${NC} $1"
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

print_status "🚀 FOGIS CENTRALIZED LOGGING AND MONITORING SETUP"
print_status "=================================================="

# Phase 1: Fix and Stabilize Monitoring Infrastructure
print_status ""
print_status "📋 Phase 1: Fixing and stabilizing monitoring infrastructure"

print_status "1. Stopping existing monitoring services..."
docker-compose stop loki grafana promtail 2>/dev/null || true

print_status "2. Removing failed containers..."
docker rm fogis-loki fogis-grafana fogis-promtail 2>/dev/null || true

print_status "3. Creating monitoring directories..."
mkdir -p ./monitoring/loki/chunks
mkdir -p ./monitoring/loki/rules
mkdir -p ./monitoring/grafana/dashboards
mkdir -p ./monitoring/grafana/datasources
mkdir -p ./monitoring/grafana/alerting
chmod -R 755 ./monitoring/

print_status "4. Starting monitoring stack..."
docker-compose up -d loki
sleep 10

# Wait for Loki to be healthy
print_status "5. Waiting for Loki to be healthy..."
for i in {1..30}; do
    if docker-compose ps loki | grep -q "healthy"; then
        print_success "✅ Loki is healthy"
        break
    elif [ $i -eq 30 ]; then
        print_error "❌ Loki failed to start properly"
        docker logs fogis-loki --tail 20
        exit 1
    else
        echo -n "."
        sleep 2
    fi
done

print_status "6. Starting Promtail and Grafana..."
docker-compose up -d promtail grafana

# Wait for services to be ready
sleep 15

# Phase 2: Verify Service Health
print_status ""
print_status "📋 Phase 2: Verifying service health"

print_status "7. Checking service status..."
LOKI_STATUS=$(docker-compose ps loki | grep "healthy" | wc -l)
GRAFANA_STATUS=$(docker-compose ps grafana | grep "healthy" | wc -l)
PROMTAIL_STATUS=$(docker-compose ps promtail | grep "Up" | wc -l)

if [ "$LOKI_STATUS" -eq 1 ]; then
    print_success "✅ Loki: Healthy"
else
    print_error "❌ Loki: Not healthy"
    docker logs fogis-loki --tail 10
fi

if [ "$GRAFANA_STATUS" -eq 1 ]; then
    print_success "✅ Grafana: Healthy"
else
    print_warning "⚠️ Grafana: Starting up..."
fi

if [ "$PROMTAIL_STATUS" -eq 1 ]; then
    print_success "✅ Promtail: Running"
else
    print_error "❌ Promtail: Not running"
    docker logs fogis-promtail --tail 10
fi

# Phase 3: Test Log Ingestion
print_status ""
print_status "📋 Phase 3: Testing log ingestion"

print_status "8. Testing Loki API..."
if curl -s http://localhost:3100/ready | grep -q "ready"; then
    print_success "✅ Loki API is responding"
else
    print_error "❌ Loki API is not responding"
    exit 1
fi

print_status "9. Testing log ingestion..."
# Generate a test log entry
docker exec match-list-processor echo "$(date '+%Y-%m-%d %H:%M:%S') - INFO - Centralized logging test message" || true

sleep 5

# Test if logs are being ingested
LOGS_INGESTED=$(curl -s "http://localhost:3100/loki/api/v1/query_range?query={service_name=~\".*\"}&start=$(date -d '1 minute ago' +%s)000000000&end=$(date +%s)000000000" | jq -r '.data.result | length' 2>/dev/null || echo "0")

if [ "$LOGS_INGESTED" -gt 0 ]; then
    print_success "✅ Logs are being ingested successfully"
else
    print_warning "⚠️ No logs detected yet (this may be normal for new setup)"
fi

# Phase 4: Configure Grafana
print_status ""
print_status "📋 Phase 4: Configuring Grafana"

print_status "10. Waiting for Grafana to be fully ready..."
for i in {1..30}; do
    if curl -s http://localhost:3000/api/health | grep -q "ok"; then
        print_success "✅ Grafana is ready"
        break
    elif [ $i -eq 30 ]; then
        print_warning "⚠️ Grafana may still be starting up"
        break
    else
        echo -n "."
        sleep 2
    fi
done

print_status "11. Grafana setup information:"
echo "   URL: http://localhost:3000"
echo "   Username: admin"
echo "   Password: ${GRAFANA_ADMIN_PASSWORD:-admin}"
echo ""
echo "   Dashboards available:"
echo "   - FOGIS Service Health Dashboard"
echo "   - FOGIS Operations Dashboard"

# Phase 5: Display Setup Summary
print_status ""
print_status "📋 Phase 5: Setup summary and next steps"

print_status "12. Service endpoints:"
echo "   🔍 Loki (Logs):     http://localhost:3100"
echo "   📊 Grafana (UI):    http://localhost:3000"
echo "   📡 Promtail:        Running (no direct UI)"

print_status "13. Useful commands:"
echo "   View service status:    docker-compose ps loki grafana promtail"
echo "   View Loki logs:         docker logs fogis-loki"
echo "   View Grafana logs:      docker logs fogis-grafana"
echo "   View Promtail logs:     docker logs fogis-promtail"
echo "   Query logs directly:    curl 'http://localhost:3100/loki/api/v1/query?query={service_name=~\".*\"}'"

print_status "14. Dashboard access:"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Login with admin/${GRAFANA_ADMIN_PASSWORD:-admin}"
echo "   3. Navigate to Dashboards > Browse"
echo "   4. Select 'FOGIS Service Health Dashboard' or 'FOGIS Operations Dashboard'"

print_status "15. Log analysis examples:"
echo "   View all errors:        {level=\"ERROR\"}"
echo "   View OAuth events:      {oauth_event=\"true\"}"
echo "   View match events:      {match_event=\"true\"}"
echo "   View specific service:  {service_name=\"match-list-processor\"}"
echo "   View API errors:        {service_name=~\".*\"} |~ \"500 Server Error\""

# Final verification
print_status ""
print_status "📋 Final verification"

MONITORING_SERVICES=$(docker-compose ps loki grafana promtail | grep -c "Up\|healthy" || echo "0")
if [ "$MONITORING_SERVICES" -ge 2 ]; then
    print_success "🎉 Centralized logging setup completed successfully!"
    print_success "📊 Monitoring services are running and ready for use"
    print_success "🔍 You can now monitor all FOGIS services from a single interface"
else
    print_warning "⚠️ Setup completed but some services may need additional time to start"
    print_warning "📋 Check service status with: docker-compose ps loki grafana promtail"
fi

print_status ""
print_status "📚 For troubleshooting and advanced configuration, see:"
print_status "   - CENTRALIZED-LOGGING-IMPLEMENTATION.md"
print_status "   - monitoring/grafana/dashboards/"
print_status "   - monitoring/grafana/alerting/"

print_status ""
print_status "✅ Setup complete! Happy monitoring! 🚀"
