# OAuth Automation Guide

## 🔐 Overview

The FOGIS deployment now includes automatic OAuth re-authorization capabilities that streamline the credential restoration process. This guide covers the new OAuth automation features, usage scenarios, and troubleshooting.

## ✨ Features

### **Automatic OAuth Detection**
- Monitors service health endpoints to detect OAuth authentication needs
- Checks both `fogis-calendar-phonebook-sync` and `google-drive-service` status
- Only triggers when services actually need OAuth re-authorization

### **Enhanced Health Check Endpoints**
- **Calendar Service**: Now properly detects OAuth tokens using `GOOGLE_CALENDAR_TOKEN_FILE` environment variable
- **Multi-Location Token Detection**: Checks preferred, legacy, and working directory locations
- **Detailed Status Reporting**: Includes `auth_status`, `token_location`, and `checked_locations`
- **Accurate Monitoring**: Eliminates false negative health checks

### **User Consent & Security**
- Interactive prompts with clear opt-out mechanisms
- No automatic token generation without explicit user consent
- Comprehensive prerequisite validation before attempting OAuth flows
- Graceful fallback to manual setup when automation fails

### **Deployment Flexibility**
- **Interactive Mode**: Full user prompts and guidance (default)
- **Headless Mode**: No interactive prompts for automated deployments
- **Manual Override**: Option to skip OAuth automation entirely

## 🚀 Usage Examples

### **Standard Restoration with OAuth Automation**
```bash
# Default behavior - includes OAuth automation with user consent
./restore_fogis_credentials.sh backup-directory --auto --validate
```

### **Skip OAuth Automation**
```bash
# Manual OAuth setup required after restoration
./restore_fogis_credentials.sh backup-directory --auto --no-oauth
```

### **Headless Deployment**
```bash
# No interactive prompts - suitable for CI/CD pipelines
./restore_fogis_credentials.sh backup-directory --headless
```

### **Interactive Restoration**
```bash
# Full interactive experience with OAuth automation
./restore_fogis_credentials.sh backup-directory --validate
```

## 🔧 Command Line Options

| Option | Description | OAuth Behavior |
|--------|-------------|----------------|
| `--auto` | Automatic mode with minimal prompts | ✅ Enabled with user consent |
| `--no-oauth` | Skip automatic OAuth setup | ❌ Disabled - manual setup required |
| `--headless` | No interactive prompts | ❌ Disabled - suitable for automation |
| `--validate` | Validate restored credentials | ✅ Enabled with user consent |

## 🔍 OAuth Status Detection

The automation system checks service health endpoints to determine OAuth needs:

### **Calendar Service Detection**
```bash
# Checks for "warning" status indicating missing tokens
curl -s http://localhost:9083/health | jq '.status'
# Expected: "warning" = needs OAuth, "healthy" = authenticated
```

### **Google Drive Service Detection**
```bash
# Checks for "unauthenticated" auth_status
curl -s http://localhost:9085/health | jq '.auth_status'
# Expected: "unauthenticated" = needs OAuth, "authenticated" = ready
```

## ⚙️ Prerequisites

The OAuth automation system validates these prerequisites before attempting setup:

1. **Google OAuth Credentials**
   - File: `credentials.json` or `credentials/google-credentials.json`
   - Create at: https://console.cloud.google.com/

2. **Python Dependencies**
   - `google-auth-oauthlib`
   - `requests`
   - Install: `pip3 install google-auth-oauthlib requests`

3. **Authentication Script**
   - File: `authenticate_all_services.py`
   - Should be present in deployment directory

4. **Running Services**
   - `fogis-calendar-phonebook-sync`
   - `google-drive-service`
   - Start: `docker-compose up -d`

## 🔄 Workflow Process

### **1. Credential Restoration**
- Restores backed up credentials and tokens
- Places tokens in correct service locations
- Restarts services to pick up restored tokens

### **2. OAuth Status Check**
- Queries service health endpoints
- Determines if OAuth re-authorization is needed
- Skips automation if services are already authenticated

### **3. Prerequisite Validation**
- Checks for Google credentials file
- Validates Python dependencies
- Confirms required services are running

### **4. User Consent (Interactive Mode)**
- Explains OAuth process requirements
- Requests user permission to proceed
- Provides clear opt-out option

### **5. OAuth Execution**
- Runs `authenticate_all_services.py` script
- Handles browser-based OAuth flow
- Distributes tokens to both services

### **6. Verification**
- Waits for services to recognize new tokens
- Re-checks service health endpoints
- Reports final authentication status

## 🛠️ Troubleshooting

### **OAuth Automation Prerequisites Not Met**
```bash
# Check Google credentials
ls -la credentials/google-credentials.json

# Check Python dependencies
python3 -c "import google_auth_oauthlib, requests"

# Check services are running
docker ps --filter "name=fogis-calendar-phonebook-sync"
docker ps --filter "name=google-drive-service"
```

### **OAuth Automation Failed**
```bash
# Manual OAuth setup
python3 authenticate_all_services.py

# Check service logs
docker logs fogis-calendar-phonebook-sync --tail 20
docker logs google-drive-service --tail 20

# Verify final status
curl -s http://localhost:9083/health | jq '.status'
curl -s http://localhost:9085/health | jq '.auth_status'
```

### **Headless Deployment Issues**
```bash
# Use headless mode with manual OAuth setup
./restore_fogis_credentials.sh backup-dir --headless --no-oauth

# Then setup OAuth separately
python3 authenticate_all_services.py
```

## 📋 Production Deployment Scenarios

### **Interactive Migration**
- Use default OAuth automation for guided setup
- Suitable for manual migrations with user present
- Provides clear feedback and error handling

### **Automated CI/CD Pipeline**
- Use `--headless --no-oauth` to avoid interactive prompts
- Setup OAuth separately in controlled environment
- Suitable for automated deployment scenarios

### **Hybrid Approach**
- Use `--no-oauth` for credential restoration
- Run OAuth setup as separate step when ready
- Provides maximum control over timing

## 📊 Enhanced Health Check Endpoints

### **Calendar Service Health Check**

**Healthy Response (New Format)**:
```json
{
  "status": "healthy",
  "auth_status": "authenticated",
  "token_location": "/app/credentials/tokens/calendar/token.json",
  "version": "dev",
  "environment": "development"
}
```

**Warning Response (Enhanced)**:
```json
{
  "status": "warning",
  "message": "OAuth token not found, may need authentication",
  "checked_locations": [
    "/app/credentials/tokens/calendar/token.json",
    "/app/data/token.json",
    "/app/token.json"
  ],
  "auth_url": "http://localhost:9083/authorize"
}
```

### **Google Drive Service Health Check**

**Healthy Response**:
```json
{
  "api_connectivity": true,
  "api_response_time_ms": 588.24,
  "auth_status": "authenticated",
  "service": "google-drive-service",
  "status": "healthy",
  "timestamp": 1752940923.3330617,
  "version": "2025.07.0"
}
```

### **Health Check Verification Commands**

```bash
# Check calendar service authentication status
curl -s http://localhost:9083/health | jq '.auth_status'

# Check Google Drive service authentication status
curl -s http://localhost:9085/health | jq '.auth_status'

# Verify token locations
curl -s http://localhost:9083/health | jq '.token_location'

# Check all service health statuses
curl -s http://localhost:9083/health && echo ""
curl -s http://localhost:9085/health
```

## 🔗 Related Documentation

- [OAuth Setup Checklist](OAUTH_SETUP_CHECKLIST.md)
- [Main README](../README.md)
- [Credential Backup Guide](../create_credential_backup.sh)

## 💡 Best Practices

1. **Test OAuth automation** in development before production use
2. **Backup credentials** before attempting OAuth re-authorization
3. **Use headless mode** for automated deployment pipelines
4. **Monitor service logs** during OAuth setup for troubleshooting
5. **Verify authentication status** after restoration completion
