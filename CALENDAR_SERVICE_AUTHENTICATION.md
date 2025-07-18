# Calendar Service Authentication Guide

## Overview

The `fogis-calendar-phonebook-sync` service requires specific OAuth token placement for proper Google Calendar API authentication. This guide explains the token location requirements and provides solutions for common authentication issues.

## Token Location Requirements

### Standard Token Location
The calendar service expects OAuth tokens in the **working directory** (`/app/token.json`) inside the container, in addition to the standard data directory location.

```bash
# Required token locations:
/app/data/token.json          # Standard data directory (mounted volume)
/app/token.json              # Working directory (required for service)
```

### Why Two Locations?

The calendar service uses a hardcoded token path in its authentication logic:
- **Data directory**: Persistent storage for token backup and restoration
- **Working directory**: Runtime location where the service actually reads the token

## Automatic Token Setup

### Enhanced Restoration Script

The `restore_fogis_credentials.sh` script now automatically handles calendar service token restoration:

```bash
# Automatic restoration with calendar service support
./restore_fogis_credentials.sh backup-directory --auto --validate
```

**Features:**
- ✅ Automatically copies tokens to `data/fogis-calendar-phonebook-sync/token.json`
- ✅ Creates `setup_calendar_token.sh` helper script for runtime token placement
- ✅ Validates token structure and authentication requirements
- ✅ Provides clear guidance for manual intervention if needed

### Post-Restoration Setup

After credential restoration, run the generated setup script:

```bash
# Run after starting services
./setup_calendar_token.sh
```

This script:
1. Waits for the calendar service to start
2. Copies the token from data directory to working directory
3. Verifies the token placement was successful

## Manual Token Setup

### If Automatic Setup Fails

If you need to manually configure calendar service authentication:

```bash
# 1. Ensure token exists in data directory
ls -la data/fogis-calendar-phonebook-sync/token.json

# 2. Start the calendar service
docker-compose up -d fogis-calendar-phonebook-sync

# 3. Copy token to working directory
docker exec fogis-calendar-phonebook-sync cp /app/data/token.json /app/token.json

# 4. Verify authentication
curl -s http://localhost:9083/health | jq '.status'
```

### Expected Result

After proper token setup, the calendar service should show:

```json
{
  "status": "healthy",
  "message": "Service is running normally"
}
```

## Troubleshooting

### Common Issues

**Issue**: `"token.json not found, may need authentication"`
```bash
# Solution: Copy token to working directory
docker exec fogis-calendar-phonebook-sync cp /app/data/token.json /app/token.json
```

**Issue**: `"Failed to obtain Google Calendar Credentials"`
```bash
# Check if token file exists
docker exec fogis-calendar-phonebook-sync ls -la /app/token.json

# If missing, copy from data directory
docker exec fogis-calendar-phonebook-sync cp /app/data/token.json /app/token.json
```

**Issue**: Calendar sync returns authentication errors
```bash
# Restart service after token placement
docker restart fogis-calendar-phonebook-sync

# Wait for service to initialize
sleep 10

# Test authentication
curl -X POST http://localhost:9083/sync
```

### Verification Commands

```bash
# Check service health
curl -s http://localhost:9083/health | jq .

# Test calendar sync
curl -X POST http://localhost:9083/sync | jq '.status'

# Check service logs
docker logs fogis-calendar-phonebook-sync --tail 20
```

## Integration with OAuth Setup

### Using setup_google_oauth.sh

The OAuth setup script automatically handles calendar service authentication:

```bash
# Complete OAuth setup including calendar service
./setup_google_oauth.sh --auto-start
```

### Manual OAuth Flow

If you need to re-authenticate the calendar service:

```bash
# 1. Remove existing token
rm -f data/fogis-calendar-phonebook-sync/token.json

# 2. Start OAuth flow (if service supports it)
# Visit: http://localhost:9083/authorize

# 3. Or copy token from Google Drive service
cp data/google-drive-service/google-drive-token.json data/fogis-calendar-phonebook-sync/token.json

# 4. Apply working directory fix
docker exec fogis-calendar-phonebook-sync cp /app/data/token.json /app/token.json
```

## Calendar Configuration

### Target Calendar

The service creates events in a specific Google Calendar configured in `config.json`:

```json
{
  "CALENDAR_ID": "e8835809c7a887d4b3138f8b1f3ebc196bd3916dcf0b689b7f8b4a399ffc12df@group.calendar.google.com"
}
```

### Verifying Calendar Access

```bash
# Check if calendar is accessible
docker exec fogis-calendar-phonebook-sync python3 -c "
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

with open('config.json', 'r') as f:
    config = json.load(f)
with open('token.json', 'r') as f:
    token_data = json.load(f)

creds = Credentials.from_authorized_user_info(token_data)
service = build('calendar', 'v3', credentials=creds)

try:
    calendar = service.calendars().get(calendarId=config['CALENDAR_ID']).execute()
    print(f'✅ Calendar accessible: {calendar.get(\"summary\", \"Unknown\")}')
except Exception as e:
    print(f'❌ Calendar access failed: {e}')
"
```

## Best Practices

1. **Always use the enhanced restoration script** for automated token handling
2. **Verify authentication** after service startup using health endpoints
3. **Monitor service logs** for authentication-related errors
4. **Keep tokens backed up** in the data directory for persistence
5. **Test calendar sync** after any authentication changes

## Support

If you encounter persistent authentication issues:

1. Check the service logs: `docker logs fogis-calendar-phonebook-sync`
2. Verify token file permissions and content
3. Ensure Google Calendar API is enabled in your Google Cloud project
4. Confirm OAuth scopes include Calendar API access
5. Test with a fresh OAuth token if needed

For additional help, refer to the main FOGIS deployment documentation or the OAuth troubleshooting guide in README.md.
