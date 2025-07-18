#!/bin/bash

# FOGIS Credential-Only Backup Script
# Preserves only essential credentials for clean installation testing

set -e

TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Determine correct source and backup directories based on execution context
if [[ -f "manage_fogis_system.sh" && -f "setup_fogis_system.sh" ]]; then
    # Running from within fogis-deployment directory
    SOURCE_DIR="."
    BACKUP_DIR="../fogis-credentials-backup-$TIMESTAMP"
elif [[ -d "fogis-deployment" && -f "fogis-deployment/manage_fogis_system.sh" ]]; then
    # Running from parent directory (web installer context)
    SOURCE_DIR="fogis-deployment"
    BACKUP_DIR="fogis-credentials-backup-$TIMESTAMP"
else
    echo "ERROR: Cannot determine FOGIS deployment directory structure"
    echo "Please run this script from either:"
    echo "  1. Within the fogis-deployment directory, or"
    echo "  2. From the parent directory containing fogis-deployment/"
    exit 1
fi

echo "=== FOGIS Credential-Only Backup Script ==="
echo "Timestamp: $TIMESTAMP"
echo "Backup Directory: $BACKUP_DIR"
echo "Source Directory: $SOURCE_DIR"
echo

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "ERROR: Source directory '$SOURCE_DIR' not found!"
    exit 1
fi

echo "1. Backing up Google OAuth credentials..."
# Backup main Google credentials
if [ -f "$SOURCE_DIR/credentials/google-credentials.json" ]; then
    mkdir -p "$BACKUP_DIR/credentials"
    cp "$SOURCE_DIR/credentials/google-credentials.json" "$BACKUP_DIR/credentials/"
    echo "   ✓ google-credentials.json backed up"
else
    echo "   ⚠ No google-credentials.json found"
fi

echo "2. Backing up OAuth token files..."
TOKENS_BACKED_UP=0

# Backup calendar sync token
if [ -f "$SOURCE_DIR/data/fogis-calendar-phonebook-sync/token.json" ]; then
    mkdir -p "$BACKUP_DIR/tokens/calendar"
    cp "$SOURCE_DIR/data/fogis-calendar-phonebook-sync/token.json" "$BACKUP_DIR/tokens/calendar/"
    echo "   ✓ Calendar sync token backed up"
    TOKENS_BACKED_UP=$((TOKENS_BACKED_UP + 1))
else
    echo "   ⚠ No calendar sync token found"
fi

# Backup Google Drive tokens (these can be used by calendar service if needed)
if [ -f "$SOURCE_DIR/data/google-drive-service/google-drive-token.json" ]; then
    mkdir -p "$BACKUP_DIR/tokens/drive"
    cp "$SOURCE_DIR/data/google-drive-service/google-drive-token.json" "$BACKUP_DIR/tokens/drive/"
    echo "   ✓ Google Drive token backed up"
    TOKENS_BACKED_UP=$((TOKENS_BACKED_UP + 1))

    # Also backup to calendar location as fallback (both services use Google OAuth)
    mkdir -p "$BACKUP_DIR/tokens/calendar"
    cp "$SOURCE_DIR/data/google-drive-service/google-drive-token.json" "$BACKUP_DIR/tokens/calendar/google-drive-token.json"
    echo "   ✓ Google Drive token also backed up for calendar service use"
fi

if [ -f "$SOURCE_DIR/data/google-drive-service/token.json" ]; then
    mkdir -p "$BACKUP_DIR/tokens/drive"
    cp "$SOURCE_DIR/data/google-drive-service/token.json" "$BACKUP_DIR/tokens/drive/token.json"
    echo "   ✓ Google Drive service token backed up"
    TOKENS_BACKED_UP=$((TOKENS_BACKED_UP + 1))
fi

if [ $TOKENS_BACKED_UP -eq 0 ]; then
    echo "   ⚠ No OAuth tokens found - services will require re-authentication"
else
    echo "   ℹ Note: Google OAuth tokens can be shared between calendar and drive services"
fi

echo "3. Backing up FOGIS credentials (.env file)..."
# Search for .env files in multiple locations
ENV_FOUND=false
ENV_BACKUP_PATH="$BACKUP_DIR/env"
mkdir -p "$ENV_BACKUP_PATH"

# Check multiple possible locations for .env file
ENV_LOCATIONS=(
    "$SOURCE_DIR/.env"
    ".env"
    "../.env"
    "$(pwd)/.env"
    "$(dirname "$(pwd)")/.env"
)

for env_path in "${ENV_LOCATIONS[@]}"; do
    if [ -f "$env_path" ]; then
        echo "   ✓ Found .env file at: $env_path"
        cp "$env_path" "$ENV_BACKUP_PATH/fogis.env"
        ENV_FOUND=true

        # Extract and document FOGIS credentials
        echo "FOGIS Authentication Credentials:" > "$BACKUP_DIR/FOGIS_CREDENTIALS.txt"
        echo "=================================" >> "$BACKUP_DIR/FOGIS_CREDENTIALS.txt"
        echo "" >> "$BACKUP_DIR/FOGIS_CREDENTIALS.txt"
        echo "Backed up from: $env_path" >> "$BACKUP_DIR/FOGIS_CREDENTIALS.txt"
        echo "" >> "$BACKUP_DIR/FOGIS_CREDENTIALS.txt"

        # Extract FOGIS credentials
        if grep -E "FOGIS_USERNAME|FOGIS_PASSWORD|USER_REFEREE_NUMBER" "$env_path" >> "$BACKUP_DIR/FOGIS_CREDENTIALS.txt" 2>/dev/null; then
            echo "   ✓ FOGIS credentials extracted and backed up"
        else
            echo "   ⚠ No FOGIS credentials found in .env file"
        fi
        break
    fi
done

if [ "$ENV_FOUND" = false ]; then
    echo "   ⚠ No .env file found in any standard location"
    echo "FOGIS Authentication Credentials:" > "$BACKUP_DIR/FOGIS_CREDENTIALS.txt"
    echo "=================================" >> "$BACKUP_DIR/FOGIS_CREDENTIALS.txt"
    echo "" >> "$BACKUP_DIR/FOGIS_CREDENTIALS.txt"
    echo "No .env file found in any of these locations:" >> "$BACKUP_DIR/FOGIS_CREDENTIALS.txt"
    for env_path in "${ENV_LOCATIONS[@]}"; do
        echo "  - $env_path" >> "$BACKUP_DIR/FOGIS_CREDENTIALS.txt"
    done
    echo "" >> "$BACKUP_DIR/FOGIS_CREDENTIALS.txt"
    echo "Note: You may need to manually configure FOGIS credentials after restoration." >> "$BACKUP_DIR/FOGIS_CREDENTIALS.txt"
fi

echo "4. Creating restoration guide..."
cat > "$BACKUP_DIR/RESTORATION_GUIDE.md" << 'EOF'
# FOGIS Credential Restoration Guide

This backup contains ONLY the essential credentials needed for FOGIS deployment.
Processing state files (hashes, change detection data) are intentionally excluded
to ensure fresh processing during clean installation testing.

## Contents

### Google OAuth Credentials
- `credentials/google-credentials.json` - Main Google OAuth client configuration
- `tokens/calendar/token.json` - Calendar sync OAuth token
- `tokens/drive/google-drive-token.json` - Google Drive OAuth token
- `tokens/drive/token.json` - Google Drive service token

### FOGIS Authentication
- `FOGIS_CREDENTIALS.txt` - FOGIS username/password documentation

## Restoration Process

### Automatic Restoration (Recommended)

1. **Use the automated restoration script**:
   ```bash
   # Automatic restoration with validation
   ./restore_fogis_credentials.sh --auto --validate

   # Or specify backup directory explicitly
   ./restore_fogis_credentials.sh fogis-credentials-backup-YYYYMMDD-HHMMSS --auto
   ```

2. **Restart services** to apply restored credentials:
   ```bash
   ./manage_fogis_system.sh restart
   ```

### Manual Restoration (Legacy)

1. **Copy Google credentials**:
   ```bash
   cp credentials/google-credentials.json fogis-deployment/credentials/

   # Copy OAuth tokens
   cp tokens/calendar/token.json fogis-deployment/data/fogis-calendar-phonebook-sync/
   cp tokens/drive/google-drive-token.json fogis-deployment/data/google-drive-service/
   cp tokens/drive/token.json fogis-deployment/data/google-drive-service/
   ```

2. **Restore FOGIS credentials manually**:
   ```bash
   # Extract credentials from backup
   grep "FOGIS_USERNAME=" FOGIS_CREDENTIALS.txt
   grep "FOGIS_PASSWORD=" FOGIS_CREDENTIALS.txt

   # Update .env file or use setup wizard
   ./manage_fogis_system.sh setup-auth
   ```

## What's NOT Included (Intentionally)

- Match processing state files
- Change detection hashes
- Service logs
- Docker containers or images
- Any processing history

This ensures a truly fresh installation test while preserving authentication.
EOF

echo "5. Creating backup manifest..."
cat > "$BACKUP_DIR/BACKUP_MANIFEST.md" << EOF
# FOGIS Credential-Only Backup

**Backup Created:** $TIMESTAMP
**Purpose:** Clean installation testing
**Source Directory:** $SOURCE_DIR
**Backup Directory:** $BACKUP_DIR

## Backup Strategy

This backup contains ONLY essential credentials required for authentication:
- Google OAuth credentials and tokens
- FOGIS authentication documentation

Processing state files are intentionally excluded to ensure fresh processing
during clean installation testing.

## Backup Size
$(du -sh "$BACKUP_DIR" | cut -f1)

## Files Backed Up
$(find "$BACKUP_DIR" -type f | wc -l) files total

## Next Steps
1. Perform complete system cleanup
2. Fresh installation from GitHub
3. Restore credentials using restoration guide
4. Test end-to-end functionality
EOF

echo
echo "=== Credential Backup Complete ==="
echo "Backup location: $(pwd)/$BACKUP_DIR"
echo "Backup size: $(du -sh "$BACKUP_DIR" | cut -f1)"
echo
echo "Backup contents:"
find "$BACKUP_DIR" -type f | sort
echo
echo "✓ Credential backup completed successfully!"
echo "✓ Ready for complete system cleanup and fresh installation testing"
