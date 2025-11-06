#!/bin/bash
# Apply referee hash fix to fogis-calendar-phonebook-sync service
# This script applies the fix for the calendar sync referee detection bug

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PATCH_FILE="$REPO_ROOT/patches/fogis_calendar_sync_referee_hash.patch"
CONTAINER_NAME="fogis-calendar-phonebook-sync"

echo "🔧 Applying Referee Hash Fix to Calendar Sync Service"
echo "=================================================="
echo ""

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Error: Container ${CONTAINER_NAME} is not running"
    exit 1
fi

echo "✅ Container ${CONTAINER_NAME} is running"
echo ""

# Extract current file
echo "📥 Extracting current fogis_calendar_sync.py from container..."
docker exec "$CONTAINER_NAME" cat /app/fogis_calendar_sync.py > /tmp/fogis_calendar_sync_current.py

# Check if already patched
if grep -q '"domaruppdraglista": match.get("domaruppdraglista", \[\])' /tmp/fogis_calendar_sync_current.py; then
    echo "✅ Fix already applied! No action needed."
    exit 0
fi

echo "⚠️  Fix not yet applied. Applying patch..."
echo ""

# Apply the fix using Python
python3 << 'EOFPYTHON'
import sys

# Read the file
with open('/tmp/fogis_calendar_sync_current.py', 'r') as f:
    content = f.read()

# Find and replace the generate_calendar_hash function
old_function = '''def generate_calendar_hash(match):
    """Generates a hash for calendar-specific match data (excluding referee information)."""
    data = {
        "lag1namn": match["lag1namn"],
        "lag2namn": match["lag2namn"],
        "anlaggningnamn": match["anlaggningnamn"],
        "tid": match["tid"],
        "tavlingnamn": match["tavlingnamn"],
        "kontaktpersoner": match.get("kontaktpersoner", []),  # Handle missing key
    }

    data_string = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data_string).hexdigest()'''

new_function = '''def generate_calendar_hash(match):
    """Generates a hash for calendar-specific match data (INCLUDING referee information).

    FIXED: Now includes domaruppdraglista to detect referee changes.
    This ensures that when referees are added, removed, or changed in FOGIS,
    the calendar event is properly updated.
    """
    data = {
        "lag1namn": match["lag1namn"],
        "lag2namn": match["lag2namn"],
        "anlaggningnamn": match["anlaggningnamn"],
        "tid": match["tid"],
        "tavlingnamn": match["tavlingnamn"],
        "kontaktpersoner": match.get("kontaktpersoner", []),  # Handle missing key
        "domaruppdraglista": match.get("domaruppdraglista", []),  # ✅ FIXED: Include referee data
    }

    data_string = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(data_string).hexdigest()'''

if old_function in content:
    content = content.replace(old_function, new_function)
    print("✅ Successfully patched generate_calendar_hash function")

    # Write the fixed content
    with open('/tmp/fogis_calendar_sync_fixed.py', 'w') as f:
        f.write(content)

    print("✅ Fixed file written to /tmp/fogis_calendar_sync_fixed.py")
    sys.exit(0)
else:
    print("❌ Could not find the function to patch")
    print("⚠️  The file may have been modified or the fix already applied")
    sys.exit(1)
EOFPYTHON

if [ $? -ne 0 ]; then
    echo "❌ Failed to apply patch"
    exit 1
fi

echo ""
echo "📤 Copying fixed file to container..."
docker cp /tmp/fogis_calendar_sync_fixed.py "$CONTAINER_NAME:/app/fogis_calendar_sync.py"

echo ""
echo "🔄 Restarting container to apply changes..."
docker restart "$CONTAINER_NAME"

echo ""
echo "⏳ Waiting for container to be healthy..."
sleep 10

# Check if container is healthy
if docker ps --format '{{.Names}}\t{{.Status}}' | grep "$CONTAINER_NAME" | grep -q "healthy"; then
    echo "✅ Container is healthy"
else
    echo "⚠️  Container is running but health check pending..."
fi

echo ""
echo "✅ Fix applied successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Monitor logs: docker logs -f $CONTAINER_NAME"
echo "   2. Verify calendar updates are working"
echo "   3. Update source repository with this fix"
echo ""
echo "📄 Documentation: CALENDAR_SYNC_REFEREE_HASH_FIX.md"
