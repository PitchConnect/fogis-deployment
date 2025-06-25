#!/bin/bash
# Start Web Authentication Interface for FOGIS Calendar Sync
# This script ensures the web authentication interface is running

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo "🌐 Starting FOGIS Web Authentication Interface"
echo "============================================="

# Check if calendar sync container is running
if ! docker ps --format "table {{.Names}}" | grep -q "fogis-calendar-phonebook-sync"; then
    print_error "fogis-calendar-phonebook-sync container is not running"
    echo "Please start the FOGIS system first:"
    echo "  ./manage_fogis_system.sh start"
    exit 1
fi

print_status "Calendar sync container is running"

# Check if web interface is already accessible
if curl -s http://localhost:9087/status >/dev/null 2>&1; then
    print_warning "Web interface is already running at http://localhost:9087"
    echo "🌐 Access it at: http://localhost:9087"
    exit 0
fi

# Start the web authentication interface
print_status "Starting web authentication interface..."
docker exec -d fogis-calendar-phonebook-sync python3 /app/auth_web_trigger.py

# Wait a moment for it to start
sleep 3

# Verify it's accessible
if curl -s http://localhost:9087/status >/dev/null 2>&1; then
    print_status "Web authentication interface started successfully!"
    echo ""
    echo "🌐 Access the interface at: http://localhost:9087"
    echo "📋 Use this interface to:"
    echo "   • Check OAuth token status"
    echo "   • Start new authentication process"
    echo "   • Monitor authentication health"
    echo ""
    echo "🔖 Bookmark this URL for easy access: http://localhost:9087"
else
    print_error "Failed to start web authentication interface"
    echo "Please check container logs:"
    echo "  docker logs fogis-calendar-phonebook-sync --tail 20"
    exit 1
fi
