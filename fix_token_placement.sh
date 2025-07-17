#!/bin/bash

# Fix OAuth token placement for FOGIS services
# This script ensures tokens are in the correct directories for each service

set -e

echo "🔧 FIXING OAUTH TOKEN PLACEMENT"
echo "==============================="

# Function to safely move tokens
move_token_safely() {
    local source="$1"
    local destination="$2"
    local service_name="$3"
    
    if [ -f "$source" ]; then
        echo "📁 Moving $service_name token: $source → $destination"
        mkdir -p "$(dirname "$destination")"
        cp "$source" "$destination"
        echo "   ✅ Token moved successfully"
    else
        echo "   ⚠️  Source token not found: $source"
    fi
}

# Fix calendar sync token placement
echo ""
echo "1. Fixing calendar sync token placement..."
move_token_safely \
    "data/calendar-sync/calendar-token.json" \
    "data/fogis-calendar-phonebook-sync/token.json" \
    "calendar sync"

# Fix Google Drive token placement (use the real token, not the test one)
echo ""
echo "2. Fixing Google Drive token placement..."
if [ -f "data/google-drive-service/token.json" ]; then
    echo "📁 Real OAuth token found in data/google-drive-service/token.json"
    echo "📁 Replacing test token in google-drive-token.json with real token"
    cp "data/google-drive-service/token.json" "data/google-drive-service/google-drive-token.json"
    echo "   ✅ Google Drive token fixed"
else
    echo "   ⚠️  Real Google Drive token not found"
fi

# Verify token placement
echo ""
echo "3. Verifying token placement..."
echo "Calendar sync token:"
ls -la data/fogis-calendar-phonebook-sync/token.json 2>/dev/null && echo "   ✅ Found" || echo "   ❌ Missing"

echo "Google Drive tokens:"
ls -la data/google-drive-service/google-drive-token.json 2>/dev/null && echo "   ✅ google-drive-token.json found" || echo "   ❌ Missing"
ls -la data/google-drive-service/token.json 2>/dev/null && echo "   ✅ token.json found" || echo "   ❌ Missing"

echo ""
echo "✅ Token placement fix completed!"
echo ""
echo "🔄 Restart services to pick up the corrected tokens:"
echo "   docker-compose -f docker-compose-master.yml restart google-drive-service fogis-calendar-phonebook-sync"
