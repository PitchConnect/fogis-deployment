#!/bin/bash
# Validation script for the persistent match-list-change-detector service
# Tests all endpoints and validates the implementation

set -e

BASE_URL="http://localhost:9080"
PASSED=0
FAILED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_test() {
    echo -e "${YELLOW}Testing: $1${NC}"
}

print_pass() {
    echo -e "${GREEN}✅ PASS: $1${NC}"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}❌ FAIL: $1${NC}"
    ((FAILED++))
}

print_info() {
    echo -e "   $1"
}

echo "🔍 Validating Persistent Service Implementation"
echo "=============================================="

# Test 1: Health endpoint accessibility
print_test "Health endpoint accessibility"
if curl -s -f "$BASE_URL/health" > /dev/null; then
    print_pass "Health endpoint is accessible"
else
    print_fail "Health endpoint is not accessible"
fi

# Test 2: Health endpoint returns valid JSON
print_test "Health endpoint JSON structure"
HEALTH_RESPONSE=$(curl -s "$BASE_URL/health")
if echo "$HEALTH_RESPONSE" | python3 -m json.tool > /dev/null 2>&1; then
    print_pass "Health endpoint returns valid JSON"
    
    # Extract key fields
    SERVICE_NAME=$(echo "$HEALTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('service_name', ''))")
    STATUS=$(echo "$HEALTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))")
    RUN_MODE=$(echo "$HEALTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('run_mode', ''))")
    CRON_SCHEDULE=$(echo "$HEALTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('cron_schedule', ''))")
    
    print_info "Service: $SERVICE_NAME"
    print_info "Status: $STATUS"
    print_info "Mode: $RUN_MODE"
    print_info "Schedule: $CRON_SCHEDULE"
    
    # Validate fields
    if [ "$SERVICE_NAME" = "match-list-change-detector" ]; then
        print_pass "Service name is correct"
    else
        print_fail "Service name is incorrect: $SERVICE_NAME"
    fi
    
    if [ "$STATUS" = "healthy" ]; then
        print_pass "Service status is healthy"
    else
        print_fail "Service status is not healthy: $STATUS"
    fi
    
    if [ "$RUN_MODE" = "service" ]; then
        print_pass "Service is running in service mode"
    else
        print_fail "Service is not in service mode: $RUN_MODE"
    fi
    
    if [ -n "$CRON_SCHEDULE" ]; then
        print_pass "Cron schedule is configured: $CRON_SCHEDULE"
    else
        print_fail "Cron schedule is not configured"
    fi
else
    print_fail "Health endpoint does not return valid JSON"
fi

# Test 3: Status endpoint
print_test "Status endpoint accessibility"
if curl -s -f "$BASE_URL/status" > /dev/null; then
    print_pass "Status endpoint is accessible"
else
    print_fail "Status endpoint is not accessible"
fi

# Test 4: Manual trigger endpoint
print_test "Manual trigger functionality"
TRIGGER_RESPONSE=$(curl -s -X POST "$BASE_URL/trigger")
if echo "$TRIGGER_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); exit(0 if data.get('status')=='success' else 1)" 2>/dev/null; then
    print_pass "Manual trigger works correctly"
    
    # Check if execution count increased
    sleep 1
    NEW_HEALTH_RESPONSE=$(curl -s "$BASE_URL/health")
    NEW_EXEC_COUNT=$(echo "$NEW_HEALTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('execution_count', 0))")
    print_info "Execution count after trigger: $NEW_EXEC_COUNT"
    
    if [ "$NEW_EXEC_COUNT" -gt 0 ]; then
        print_pass "Execution count is tracking correctly"
    else
        print_fail "Execution count is not tracking"
    fi
else
    print_fail "Manual trigger failed"
fi

# Test 5: Service persistence (check it's not restarting)
print_test "Service persistence (no restart loops)"
echo "   Checking service status over 30 seconds..."
RESTART_COUNT=0
for i in {1..6}; do
    sleep 5
    if docker compose -f ../../docker-compose-master.yml ps match-list-change-detector | grep -q "Restarting"; then
        ((RESTART_COUNT++))
    fi
done

if [ "$RESTART_COUNT" -eq 0 ]; then
    print_pass "Service is running persistently (no restarts detected)"
else
    print_fail "Service is still restarting ($RESTART_COUNT restarts detected)"
fi

# Test 6: Docker health check
print_test "Docker health check status"
DOCKER_STATUS=$(docker compose -f ../../docker-compose-master.yml ps match-list-change-detector --format "table {{.Status}}" | tail -n 1)
if echo "$DOCKER_STATUS" | grep -q "healthy\|starting"; then
    print_pass "Docker reports service as healthy"
    print_info "Docker status: $DOCKER_STATUS"
else
    print_fail "Docker reports service as unhealthy: $DOCKER_STATUS"
fi

# Test 7: Port accessibility
print_test "Port configuration"
if netstat -an 2>/dev/null | grep -q ":9080.*LISTEN" || ss -an 2>/dev/null | grep -q ":9080.*LISTEN"; then
    print_pass "Service is listening on port 9080"
else
    print_fail "Service is not listening on port 9080"
fi

# Test 8: Environment variable configuration
print_test "Environment variable configuration"
ENV_CRON=$(docker exec match-list-change-detector env | grep "CRON_SCHEDULE" | cut -d'=' -f2)
if [ -n "$ENV_CRON" ]; then
    print_pass "CRON_SCHEDULE environment variable is set: $ENV_CRON"
else
    print_fail "CRON_SCHEDULE environment variable is not set"
fi

ENV_RUN_MODE=$(docker exec match-list-change-detector env | grep "RUN_MODE" | cut -d'=' -f2)
if [ "$ENV_RUN_MODE" = "service" ]; then
    print_pass "RUN_MODE environment variable is correctly set to 'service'"
else
    print_fail "RUN_MODE environment variable is not set to 'service': $ENV_RUN_MODE"
fi

# Summary
echo ""
echo "=============================================="
echo "🎯 Validation Summary"
echo "=============================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! The persistent service implementation is working correctly.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review the implementation.${NC}"
    exit 1
fi
