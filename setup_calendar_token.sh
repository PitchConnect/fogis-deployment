#!/bin/bash
# Calendar service token location fix
# This script ensures the calendar service can find its OAuth token

if [ -f "data/fogis-calendar-phonebook-sync/token.json" ]; then
    echo "Setting up calendar service token location..."

    # Wait for calendar service to be running
    for i in {1..30}; do
        if docker ps | grep -q "fogis-calendar-phonebook-sync"; then
            echo "Calendar service detected, copying token to working directory..."
            docker exec fogis-calendar-phonebook-sync cp /app/data/token.json /app/token.json 2>/dev/null || true
            echo "✅ Calendar service token setup completed"
            break
        fi
        sleep 2
    done
else
    echo "No calendar service token found to set up"
fi
