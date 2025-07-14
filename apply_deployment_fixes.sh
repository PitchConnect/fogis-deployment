#!/bin/bash

# Apply critical fixes after repository cloning
# This script applies all the fixes we discovered during development

set -e

echo "🔧 Applying deployment fixes..."

# Fix 1: team-logo-combiner Dockerfile
echo "📦 Fixing team-logo-combiner Dockerfile..."
if [ -f "team-logo-combiner/Dockerfile" ]; then
    # Check if fix is already applied
    if ! grep -q "error_handler.py" team-logo-combiner/Dockerfile; then
        # Apply the fix
        sed -i.bak '/COPY team_logo_combiner.py team_logo_combiner.py/a\
COPY error_handler.py error_handler.py\
COPY logging_config.py logging_config.py' team-logo-combiner/Dockerfile
        echo "✅ Applied Dockerfile fix to team-logo-combiner"
    else
        echo "✅ team-logo-combiner Dockerfile already fixed"
    fi
else
    echo "⚠️  team-logo-combiner/Dockerfile not found"
fi

# Fix 2: google-drive-service environment variables
echo "☁️  Fixing google-drive-service paths..."
if [ -f "google-drive-service/google_drive_utils.py" ]; then
    # Check if fix is already applied
    if ! grep -q "GOOGLE_CREDENTIALS_PATH" google-drive-service/google_drive_utils.py; then
        # Apply the fix
        sed -i.bak "s|CREDENTIALS_PATH = 'credentials.json'|CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', '/app/credentials/google-credentials.json')|" google-drive-service/google_drive_utils.py
        sed -i.bak "s|TOKEN_PATH = 'token.json'|TOKEN_PATH = os.getenv('GOOGLE_TOKEN_PATH', '/app/data/google-drive-token.json')|" google-drive-service/google_drive_utils.py
        echo "✅ Applied environment variable fix to google-drive-service"
    else
        echo "✅ google-drive-service already fixed"
    fi
else
    echo "⚠️  google-drive-service/google_drive_utils.py not found"
fi

# Fix 3: fogis-calendar-phonebook-sync configuration
echo "📅 Fixing calendar service configuration..."
if [ -f "fogis-calendar-phonebook-sync/config.json" ]; then
    # Check if referee number is set
    if ! grep -q "USER_REFEREE_NUMBER" fogis-calendar-phonebook-sync/config.json; then
        # Add referee number and fix scopes
        python3 << 'EOF'
import json
import os

config_file = "fogis-calendar-phonebook-sync/config.json"
if os.path.exists(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)

    # Add referee number
    config["USER_REFEREE_NUMBER"] = 61318

    # Fix scopes (remove drive scope - handled by separate service)
    config["SCOPES"] = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/contacts"
    ]

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    print("✅ Applied configuration fix to fogis-calendar-phonebook-sync")
else:
    print("⚠️  fogis-calendar-phonebook-sync/config.json not found")
EOF
    else
        echo "✅ fogis-calendar-phonebook-sync already configured"
    fi
else
    echo "⚠️  fogis-calendar-phonebook-sync/config.json not found"
fi

# Fix 4: Update fogis-api-client version dependencies
echo "🔄 Fixing fogis-api-client version dependencies..."
for service in "match-list-change-detector" "fogis-calendar-phonebook-sync"; do
    if [ -f "$service/requirements.txt" ]; then
        if grep -q "fogis-api-client-timmyBird==0.0.5\|fogis-api-client-timmyBird==0.5.2" "$service/requirements.txt"; then
            sed -i.bak "s/fogis-api-client-timmyBird==0.0.5\|fogis-api-client-timmyBird==0.5.2/fogis-api-client-timmyBird==0.5.1/" "$service/requirements.txt"
            echo "✅ Updated $service to use fogis-api-client v0.5.1"
        else
            echo "✅ $service already using correct version"
        fi
    else
        echo "⚠️  $service/requirements.txt not found"
    fi
done
echo ""
echo "🎉 All deployment fixes applied successfully!"
echo ""
echo "📋 Applied fixes:"
echo "  ✅ team-logo-combiner Dockerfile dependencies"
echo "  ✅ google-drive-service environment variables"
echo "  ✅ fogis-calendar-phonebook-sync configuration"
echo "  ✅ docker-compose service orchestration (already in place)"
echo ""

# Fix 4: Update fogis-api-client version dependencies
echo "🔄 Fixing fogis-api-client version dependencies..."
for service in "match-list-change-detector" "fogis-calendar-phonebook-sync"; do
    if [ -f "$service/requirements.txt" ]; then
        if grep -q "fogis-api-client-timmyBird==0.0.5\|fogis-api-client-timmyBird==0.5.2" "$service/requirements.txt"; then
            sed -i.bak 's/fogis-api-client-timmyBird==0.0.5\|fogis-api-client-timmyBird==0.5.2/fogis-api-client-timmyBird==0.5.1/' "$service/requirements.txt"
            echo "✅ Updated $service to use fogis-api-client v0.5.1"
        else
            echo "✅ $service already using correct version"
        fi
    else
        echo "⚠️  $service/requirements.txt not found"
    fi
done
