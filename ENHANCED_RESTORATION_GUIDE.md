# Enhanced FOGIS Credential Restoration Guide

This guide documents the enhanced OAuth token restoration process that enables immediate operational resumption without manual intervention.

## OAuth Token Architecture

### Service-Specific Token Locations

#### Calendar Service (fogis-calendar-phonebook-sync)
- **Primary Location**: `credentials/tokens/calendar/token.json`
- **Legacy Location**: `data/fogis-calendar-phonebook-sync/token.json`
- **Environment Variable**: `GOOGLE_CALENDAR_TOKEN_FILE=/app/credentials/tokens/calendar/token.json`

#### Google Drive Service (google-drive-service)
- **Required Location**: `data/google-drive-service/google-drive-token.json`
- **Environment Variable**: `GOOGLE_CREDENTIALS_PATH=/app/credentials/google-credentials.json`

### Backup Structure
```
backup-directory/
├── credentials/
│   └── google-credentials.json
├── tokens/
│   ├── calendar/
│   │   ├── token.json
│   │   └── google-drive-token.json
│   └── drive/
│       └── google-drive-token.json
└── env/
    └── .env
```

## Enhanced Restoration Process

### 1. Automatic Restoration (Recommended)
```bash
# Enhanced restoration with OAuth validation
./restore_fogis_credentials.sh /path/to/backup --auto --validate

# The script automatically:
# - Places tokens in correct service-specific locations
# - Validates token integrity and format
# - Creates multi-location compatibility mappings
# - Provides comprehensive validation feedback
```

### 2. Validation Results
The enhanced script provides detailed validation:
- ✅ Environment file validation
- ✅ Google credentials validation  
- ✅ OAuth token placement verification
- ✅ Token integrity validation
- ✅ Service-specific location mapping

### 3. Expected OAuth Status
After successful restoration:

**Calendar Service** (port 9083):
```json
{
  "auth_status": "authenticated",
  "status": "healthy",
  "token_location": "/app/credentials/tokens/calendar/token.json"
}
```

**Google Drive Service** (port 9085):
```json
{
  "auth_status": "authenticated",
  "status": "healthy", 
  "api_connectivity": true
}
```

## Troubleshooting OAuth Issues

### Issue 1: Calendar Service "OAuth token not found"
**Symptoms**: Service shows warning status, requests authentication
**Solution**:
```bash
# Check primary token location
ls -la credentials/tokens/calendar/token.json

# If missing, manually copy from backup
cp backup/tokens/calendar/token.json credentials/tokens/calendar/

# Restart service
docker-compose restart fogis-calendar-phonebook-sync
```

### Issue 2: Google Drive Service "Authentication required"
**Symptoms**: Service shows degraded status, auth_status: unauthenticated
**Solution**:
```bash
# Check required token location
ls -la data/google-drive-service/google-drive-token.json

# If missing, copy from backup
cp backup/tokens/drive/google-drive-token.json data/google-drive-service/

# Restart service
docker-compose restart google-drive-service
```

### Issue 3: Token Validation Failures
**Symptoms**: Restoration script reports token validation failed
**Solution**:
```bash
# Check token integrity with jq
jq empty credentials/tokens/calendar/token.json
jq '.access_token' credentials/tokens/calendar/token.json

# If corrupted, try alternative backup locations
cp backup/tokens/calendar/google-drive-token.json credentials/tokens/calendar/token.json
```

## Manual Token Placement (Emergency)

If automatic restoration fails, manually place tokens:

```bash
# Create directory structure
mkdir -p credentials/tokens/calendar
mkdir -p data/google-drive-service
mkdir -p data/fogis-calendar-phonebook-sync

# Copy calendar tokens (both locations for compatibility)
cp backup/tokens/calendar/token.json credentials/tokens/calendar/
cp backup/tokens/calendar/token.json data/fogis-calendar-phonebook-sync/

# Copy Google Drive token
cp backup/tokens/drive/google-drive-token.json data/google-drive-service/

# Copy Google credentials
cp backup/credentials/google-credentials.json credentials/

# Restart services
docker-compose restart fogis-calendar-phonebook-sync google-drive-service
```

## Validation Commands

### Check Service OAuth Status
```bash
# Calendar service
curl -s http://localhost:9083/health | jq '.auth_status'

# Google Drive service  
curl -s http://localhost:9085/health | jq '.auth_status'

# Expected result: "authenticated"
```

### Verify Token Files
```bash
# Check all token locations
find . -name "*token*.json" -exec echo "Found: {}" \;

# Validate token structure
jq '.access_token // .refresh_token' credentials/tokens/calendar/token.json
```

## Integration with PR #56 Validation

This enhanced restoration process enables:
- ✅ **Immediate Operational Resumption**: No manual OAuth re-authorization required
- ✅ **Comprehensive Validation**: All tokens verified and properly placed
- ✅ **Service Integration**: Perfect inter-service communication maintained
- ✅ **Production Readiness**: Complete backup/restoration workflow validated

The restoration process is critical for proving that the FOGIS backup/restoration workflow truly enables immediate operational resumption as claimed in PR #56 validation testing.
