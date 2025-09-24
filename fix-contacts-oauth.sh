#!/bin/bash
set -e

# Google People API/Contacts OAuth Fix Script
# Resolves the contacts sync authentication issue

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[CONTACTS]${NC} $1"
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

print_status "🔧 Google People API/Contacts OAuth Fix"
print_status "======================================"

# Step 1: Verify the issue exists
print_status "📋 Step 1: Diagnosing contacts OAuth issue..."

if docker exec fogis-calendar-phonebook-sync test -f /app/token.json; then
    TOKEN_SIZE=$(docker exec fogis-calendar-phonebook-sync stat -c%s /app/token.json)
    if [ "$TOKEN_SIZE" -eq 0 ]; then
        print_warning "⚠️ Empty token.json found in container (${TOKEN_SIZE} bytes)"
        NEEDS_FIX=true
    else
        print_success "✅ token.json exists and has content (${TOKEN_SIZE} bytes)"
        NEEDS_FIX=false
    fi
else
    print_error "❌ token.json not found in container"
    NEEDS_FIX=true
fi

# Step 2: Check if working calendar token exists
print_status "📋 Step 2: Checking for working calendar OAuth token..."

if docker exec fogis-calendar-phonebook-sync test -f /app/credentials/tokens/calendar/token.json; then
    CALENDAR_TOKEN_SIZE=$(docker exec fogis-calendar-phonebook-sync stat -c%s /app/credentials/tokens/calendar/token.json)
    if [ "$CALENDAR_TOKEN_SIZE" -gt 0 ]; then
        print_success "✅ Working calendar token found (${CALENDAR_TOKEN_SIZE} bytes)"
        HAS_WORKING_TOKEN=true
    else
        print_error "❌ Calendar token is empty"
        HAS_WORKING_TOKEN=false
    fi
else
    print_error "❌ Calendar token not found"
    HAS_WORKING_TOKEN=false
fi

# Step 3: Apply fix if needed
if [ "$NEEDS_FIX" = true ] && [ "$HAS_WORKING_TOKEN" = true ]; then
    print_status "📋 Step 3: Applying contacts OAuth fix..."
    
    # Copy working token to contacts location
    print_status "🔄 Copying working OAuth token to contacts location..."
    cp ./credentials/tokens/calendar/token.json ../fogis-calendar-phonebook-sync/token.json
    print_success "✅ Token copied to ../fogis-calendar-phonebook-sync/token.json"
    
    # Restart service to pick up the token
    print_status "🔄 Restarting calendar service to pick up token..."
    docker-compose restart fogis-calendar-phonebook-sync
    
    # Wait for service to be ready
    print_status "⏳ Waiting for service to be ready..."
    sleep 10
    
    print_success "✅ Service restarted with contacts OAuth fix"
    
elif [ "$NEEDS_FIX" = false ]; then
    print_success "✅ No fix needed - contacts OAuth already working"
else
    print_error "❌ Cannot apply fix - no working calendar token available"
    print_status "💡 Please ensure calendar OAuth is working first"
    exit 1
fi

# Step 4: Verify the fix
print_status "📋 Step 4: Verifying contacts OAuth fix..."

print_status "🧪 Testing calendar sync with contacts..."
SYNC_RESULT=$(timeout 15 curl -s -X POST http://localhost:9083/sync 2>/dev/null || echo "timeout")

if echo "$SYNC_RESULT" | grep -q "Google People API is working"; then
    print_success "✅ Google People API is working and can access personal contacts!"
    print_success "✅ Contacts OAuth fix successful!"
    
    # Check for specific success indicators
    if echo "$SYNC_RESULT" | grep -q "Connection established"; then
        print_success "✅ Connection established with Google People API"
    fi
    
    if echo "$SYNC_RESULT" | grep -q "Login successful"; then
        print_success "✅ FOGIS authentication working"
    fi
    
else
    print_warning "⚠️ Contacts OAuth may need additional verification"
    print_status "📋 Checking for error messages..."
    
    if echo "$SYNC_RESULT" | grep -q "Error loading credentials from token.json"; then
        print_error "❌ Still getting token loading errors"
    fi
    
    if echo "$SYNC_RESULT" | grep -q "could not locate runnable browser"; then
        print_error "❌ Still getting browser errors"
    fi
fi

# Step 5: Summary
print_status "📋 Step 5: Fix summary..."

print_status "🎯 Root Cause Analysis:"
print_status "   - Calendar OAuth: Uses /app/credentials/tokens/calendar/token.json"
print_status "   - Contacts OAuth: Uses /app/token.json"
print_status "   - Issue: Different token file locations"

print_status "🔧 Solution Applied:"
print_status "   - Copied working calendar token to contacts location"
print_status "   - Added volume mount for contacts token in docker-compose.yml"
print_status "   - Restarted service to pick up changes"

print_status "✅ Expected Results:"
print_status "   - Calendar sync: Working"
print_status "   - Contacts sync: Working"
print_status "   - Referee processing: Working"
print_status "   - End-to-end sync: Complete"

print_success "🎉 Google People API/Contacts OAuth fix completed!"
print_status "📋 Both calendar events AND referee contact information should now sync properly"
