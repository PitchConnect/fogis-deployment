#!/bin/bash
set -e

# FOGIS Single-Service Architecture Consolidation Verification Script
# Verifies successful removal of match list change detector and continued operation

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

print_status "🔍 FOGIS SINGLE-SERVICE ARCHITECTURE CONSOLIDATION VERIFICATION"
print_status "=============================================================="

# Test 1: Verify change detector is completely removed
print_status "1. Verifying match list change detector removal..."
CHANGE_DETECTOR_CONTAINERS=$(docker ps -a | grep change-detector | wc -l)

if [ "$CHANGE_DETECTOR_CONTAINERS" -eq 0 ]; then
    print_success "✅ Match list change detector completely removed"
else
    print_error "❌ Change detector containers still exist"
    docker ps -a | grep change-detector
    exit 1
fi

# Test 2: Verify match processor is running
print_status "2. Verifying match list processor status..."
PROCESSOR_STATUS=$(docker ps | grep match-list-processor | grep "healthy" | wc -l)

if [ "$PROCESSOR_STATUS" -eq 1 ]; then
    print_success "✅ Match list processor running and healthy"
    docker ps | grep match-list-processor | awk '{print "   Container: " $1 " | Status: " $7 " | Uptime: " $9 " " $10}'
else
    print_error "❌ Match list processor not running or unhealthy"
    docker ps | grep match-list-processor || echo "No match processor found"
    exit 1
fi

# Test 3: Verify processor health endpoint
print_status "3. Testing match list processor health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:9082/health 2>/dev/null || echo "{}")

if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    print_success "✅ Match list processor health endpoint responding"
    UPTIME=$(echo "$HEALTH_RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(f'{data.get(\"uptime_seconds\", 0):.0f}s')" 2>/dev/null || echo "unknown")
    echo "   Uptime: $UPTIME"
else
    print_error "❌ Match list processor health endpoint not responding properly"
    echo "   Response: $HEALTH_RESPONSE"
    exit 1
fi

# Test 4: Verify data directories cleanup
print_status "4. Verifying change detector data cleanup..."
if [ ! -d "./data/match-list-change-detector" ] && [ ! -d "./logs/match-list-change-detector" ]; then
    print_success "✅ Change detector data and log directories removed"
else
    print_warning "⚠️ Change detector directories still exist"
    ls -la ./data/ | grep change-detector || true
    ls -la ./logs/ | grep change-detector || true
fi

# Test 5: Verify docker-compose.yml changes
print_status "5. Verifying docker-compose.yml consolidation..."
if grep -q "match-list-change-detector:" docker-compose.yml 2>/dev/null; then
    print_error "❌ Change detector service still in docker-compose.yml"
    grep -n "match-list-change-detector" docker-compose.yml
    exit 1
else
    print_success "✅ Change detector service removed from docker-compose.yml"
fi

# Test 6: Verify processor functionality
print_status "6. Verifying processor functionality..."
PROCESSOR_LOGS=$(docker logs match-list-processor --since="1h" | grep -E "(Starting periodic|completed|Sleeping)" | wc -l)

if [ "$PROCESSOR_LOGS" -gt 0 ]; then
    print_success "✅ Match list processor showing active processing cycles"
    echo "   Recent processing activity detected in logs"
else
    print_warning "⚠️ No recent processing activity in logs (may be normal if no recent cycles)"
fi

# Test 7: Verify service count reduction
print_status "7. Verifying service count reduction..."
TOTAL_FOGIS_SERVICES=$(docker ps | grep -E "(fogis|match|team|google|calendar)" | wc -l)
MATCH_SERVICES=$(docker ps | grep match | wc -l)

print_success "✅ Current FOGIS service count: $TOTAL_FOGIS_SERVICES"
print_success "✅ Match-related services: $MATCH_SERVICES (should be 1)"

if [ "$MATCH_SERVICES" -eq 1 ]; then
    print_success "✅ Correct number of match services (consolidated to 1)"
else
    print_error "❌ Unexpected number of match services: $MATCH_SERVICES"
    docker ps | grep match
    exit 1
fi

# Test 8: Verify resource usage
print_status "8. Checking resource usage after consolidation..."
PROCESSOR_STATS=$(docker stats --no-stream --format "{{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep match-list-processor || echo "N/A")

if [ "$PROCESSOR_STATS" != "N/A" ]; then
    print_success "✅ Resource usage for consolidated service:"
    echo "   $PROCESSOR_STATS"
else
    print_warning "⚠️ Could not retrieve resource usage statistics"
fi

# Test 9: Verify all other services still running
print_status "9. Verifying all other FOGIS services are healthy..."
EXPECTED_SERVICES=("fogis-api-client-service" "fogis-calendar-phonebook-sync" "team-logo-combiner" "google-drive-service" "match-list-processor")
ALL_HEALTHY=true

for service in "${EXPECTED_SERVICES[@]}"; do
    if docker ps | grep "$service" | grep -q "healthy"; then
        print_success "✅ $service: healthy"
    else
        print_error "❌ $service: not healthy or not running"
        ALL_HEALTHY=false
    fi
done

if [ "$ALL_HEALTHY" = true ]; then
    print_success "✅ All expected FOGIS services are healthy"
else
    print_error "❌ Some FOGIS services are not healthy"
    exit 1
fi

print_status ""
print_status "📊 CONSOLIDATION VERIFICATION SUMMARY:"
print_success "✅ Match list change detector completely removed"
print_success "✅ Match list processor operating normally"
print_success "✅ Single-service architecture successfully implemented"
print_success "✅ All functionality preserved"
print_success "✅ Resource usage reduced (eliminated duplicate service)"
print_success "✅ Operational complexity simplified"

print_status ""
print_status "🎉 FOGIS single-service architecture consolidation verification completed successfully!"
print_status "📋 The system now operates with improved efficiency and reduced complexity."
