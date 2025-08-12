#!/bin/bash
set -e

# FOGIS Dashboard and API Issues Resolution Script
# Addresses both Grafana dashboard display and FOGIS API authentication problems

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[FIX]${NC} $1"
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

print_status "🔧 FOGIS DASHBOARD AND API ISSUES RESOLUTION"
print_status "============================================="

# Step 1: Verify Grafana Dashboard Fixes
print_status ""
print_status "📊 Step 1: Verifying Grafana dashboard fixes"

if docker-compose ps grafana | grep -q "healthy"; then
    print_success "✅ Grafana is running and healthy"
else
    print_error "❌ Grafana is not healthy - restarting..."
    docker-compose restart grafana
    sleep 10
fi

# Step 2: Test Log Queries
print_status ""
print_status "📋 Step 2: Testing log ingestion and queries"

# Test basic connectivity
if curl -sf http://localhost:3100/ready >/dev/null; then
    print_success "✅ Loki API: Responding"
else
    print_error "❌ Loki API: Not responding"
    exit 1
fi

# Test service name availability
SERVICE_COUNT=$(curl -s "http://localhost:3100/loki/api/v1/label/service_name/values" | jq -r '.data | length' 2>/dev/null || echo "0")
if [ "$SERVICE_COUNT" -gt 0 ]; then
    print_success "✅ Service names available: $SERVICE_COUNT services"
    echo "   Available services:"
    curl -s "http://localhost:3100/loki/api/v1/label/service_name/values" | jq -r '.data[]' | sed 's/^/   - /'
else
    print_warning "⚠️ No service names found in Loki"
fi

# Test log query with time range
START_TIME=$(date -v-24H +%s)000000000
END_TIME=$(date +%s)000000000
LOG_COUNT=$(curl -s "http://localhost:3100/loki/api/v1/query_range?query=%7Bservice_name%3D%22match-list-processor%22%7D&start=${START_TIME}&end=${END_TIME}&limit=5" | jq -r '.data.result | length' 2>/dev/null || echo "0")

if [ "$LOG_COUNT" -gt 0 ]; then
    print_success "✅ Log queries working: $LOG_COUNT log streams found"
else
    print_warning "⚠️ No logs found for match-list-processor in last 24 hours"
fi

# Step 3: Diagnose FOGIS API Authentication
print_status ""
print_status "🔐 Step 3: Diagnosing FOGIS API authentication issues"

# Check API client health
if curl -sf http://localhost:9086/health >/dev/null; then
    print_success "✅ FOGIS API client service: Healthy"
else
    print_error "❌ FOGIS API client service: Not responding"
    exit 1
fi

# Test matches endpoint
MATCHES_RESPONSE=$(curl -s http://localhost:9086/matches)
if echo "$MATCHES_RESPONSE" | grep -q "401.*Unauthorized"; then
    print_error "❌ FOGIS API: 401 Unauthorized - Authentication required"
    echo "   Error details: $(echo "$MATCHES_RESPONSE" | jq -r '.error' 2>/dev/null || echo "$MATCHES_RESPONSE")"
    
    # Check credentials
    print_status "   Checking FOGIS credentials configuration..."
    FOGIS_USER=$(docker exec fogis-api-client-service env | grep FOGIS_USERNAME | cut -d'=' -f2)
    if [ -n "$FOGIS_USER" ]; then
        print_success "   ✅ FOGIS username configured: $FOGIS_USER"
    else
        print_error "   ❌ FOGIS username not configured"
    fi
    
    if docker exec fogis-api-client-service env | grep -q FOGIS_PASSWORD; then
        print_success "   ✅ FOGIS password configured"
    else
        print_error "   ❌ FOGIS password not configured"
    fi
    
elif echo "$MATCHES_RESPONSE" | grep -q "error"; then
    print_error "❌ FOGIS API: Other error"
    echo "   Error: $(echo "$MATCHES_RESPONSE" | jq -r '.error' 2>/dev/null || echo "$MATCHES_RESPONSE")"
else
    print_success "✅ FOGIS API: Working correctly"
    MATCH_COUNT=$(echo "$MATCHES_RESPONSE" | jq '. | length' 2>/dev/null || echo "unknown")
    echo "   Matches returned: $MATCH_COUNT"
fi

# Step 4: Check Recent Error Patterns
print_status ""
print_status "📈 Step 4: Analyzing recent error patterns"

# Check for 401 errors in logs
AUTH_ERRORS=$(docker logs fogis-api-client-service 2>&1 | grep -c "401.*Unauthorized" || echo "0")
if [ "$AUTH_ERRORS" -gt 0 ]; then
    print_warning "⚠️ Found $AUTH_ERRORS authentication errors in API client logs"
    echo "   Most recent error:"
    docker logs fogis-api-client-service 2>&1 | grep "401.*Unauthorized" | tail -1 | sed 's/^/   /'
else
    print_success "✅ No recent authentication errors found"
fi

# Check for 500 errors in match processor
MATCH_ERRORS=$(docker logs match-list-processor 2>&1 | grep -c "500 Server Error" || echo "0")
if [ "$MATCH_ERRORS" -gt 0 ]; then
    print_warning "⚠️ Found $MATCH_ERRORS server errors in match processor logs"
    echo "   Most recent error:"
    docker logs match-list-processor 2>&1 | grep "500 Server Error" | tail -1 | sed 's/^/   /'
else
    print_success "✅ No recent server errors in match processor"
fi

# Step 5: Provide Solutions
print_status ""
print_status "💡 Step 5: Recommended solutions"

print_status "Dashboard Issues:"
echo "   1. Open Grafana: http://localhost:3000"
echo "   2. Login with admin/admin"
echo "   3. Navigate to Dashboards > Browse > FOGIS folder"
echo "   4. For each dashboard:"
echo "      - Click the time picker (top right)"
echo "      - Change from default to 'Last 24 hours' or 'Last 7 days'"
echo "      - Click 'Apply'"
echo "   5. Test queries in Explore interface:"
echo "      - Go to Explore (compass icon)"
echo "      - Use query: {service_name=\"match-list-processor\"}"

print_status ""
print_status "API Authentication Issues:"
if [ "$AUTH_ERRORS" -gt 0 ]; then
    echo "   🔐 FOGIS API authentication is failing"
    echo "   Possible solutions:"
    echo "   1. Check if FOGIS credentials are correct:"
    echo "      - Username: $FOGIS_USER"
    echo "      - Password: [configured but may be expired]"
    echo "   2. FOGIS may require re-authentication:"
    echo "      - Contact FOGIS support for credential renewal"
    echo "      - Check if account needs reactivation"
    echo "   3. Temporary workaround:"
    echo "      - Monitor other services (they should work independently)"
    echo "      - Match processing will resume once authentication is fixed"
else
    echo "   ✅ No authentication issues detected"
fi

print_status ""
print_status "Monitoring Status:"
echo "   📊 Grafana dashboards: http://localhost:3000"
echo "   🔍 Log exploration: http://localhost:3000/explore"
echo "   📈 Service health: All services monitored and logged"
echo "   🚨 Error detection: 401/500 errors are being tracked"

print_status ""
if [ "$LOG_COUNT" -gt 0 ] && [ "$AUTH_ERRORS" -eq 0 ]; then
    print_success "🎉 System is healthy! Dashboards should display data correctly."
elif [ "$LOG_COUNT" -gt 0 ] && [ "$AUTH_ERRORS" -gt 0 ]; then
    print_warning "⚠️ Monitoring is working, but FOGIS API needs authentication fix."
else
    print_warning "⚠️ Some issues remain - check individual components above."
fi

print_status ""
print_status "✅ Diagnosis complete! 🚀"
