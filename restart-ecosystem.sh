#!/bin/bash
set -e

# FOGIS Service Ecosystem Single-Command Restart Script
# Eliminates manual multi-step deployment complexity

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[RESTART]${NC} $1"
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

print_status "🔄 Starting FOGIS Service Ecosystem Restart..."
print_status "Using master orchestration: docker-compose.yml"

# Stop all services cleanly
print_status "🛑 Stopping all services..."
docker-compose down --remove-orphans

# Start all services with proper dependencies
print_status "🚀 Starting all services with dependency management..."
docker-compose up -d

# Wait for services to be ready
print_status "⏳ Waiting for services to become healthy..."
sleep 10

# Verify service health
print_status "🏥 Verifying service health..."

SERVICES=(
    "fogis-calendar-phonebook-sync:9083"
    "match-list-processor:9082"
    "fogis-api-client-service:9086"
    "google-drive-service:9085"
    "team-logo-combiner:9088"
)

ALL_HEALTHY=true

for service in "${SERVICES[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if curl -s -f "http://localhost:$port/health" > /dev/null; then
        print_success "✅ $name (Port $port): Healthy"
    else
        print_warning "⚠️ $name (Port $port): Not responding"
        ALL_HEALTHY=false
    fi
done

if [ "$ALL_HEALTHY" = true ]; then
    print_success "🎉 FOGIS Service Ecosystem restart completed successfully!"
    print_status "📊 All services are healthy and operational"
else
    print_warning "⚠️ Some services may need additional time to start"
    print_status "💡 Check individual service logs: docker-compose logs [service-name]"
fi

print_status "📋 Service Status Summary:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(NAMES|fogis|match-list|google-drive|team-logo)"

print_success "✅ Single-command restart completed!"

# Additional verification for FOGIS credentials
print_status "🔍 Verifying FOGIS authentication..."
if docker exec fogis-calendar-phonebook-sync env | grep -q "FOGIS_USERNAME=Bartek Svaberg"; then
    print_success "✅ FOGIS credentials properly loaded"
else
    print_warning "⚠️ FOGIS credentials may need verification"
fi

print_status "📋 Quick sync test (FOGIS authentication)..."
if timeout 5 curl -s -f "http://localhost:9083/sync" > /dev/null 2>&1; then
    print_success "✅ FOGIS sync endpoint responding"
else
    print_warning "⚠️ FOGIS sync may need OAuth setup for full functionality"
fi
