#!/bin/bash

# Fix fogis-api-client version dependencies
echo "🔄 Fixing fogis-api-client version dependencies..."

for service in "match-list-change-detector" "fogis-calendar-phonebook-sync"; do
    if [ -f "$service/requirements.txt" ]; then
        if grep -q "fogis-api-client-timmyBird==0.0.5" "$service/requirements.txt"; then
            sed -i.bak 's/fogis-api-client-timmyBird==0.0.5/fogis-api-client-timmyBird==0.5.1/' "$service/requirements.txt"
            echo "✅ Updated $service to use fogis-api-client v0.5.1"
        else
            echo "✅ $service already using correct version"
        fi
    else
        echo "⚠️  $service/requirements.txt not found"
    fi
done

echo "✅ Version dependency fix completed"
