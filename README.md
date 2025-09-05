# 🚀 FOGIS Deployment - Complete Automated Solution

## **🎉 Latest Deployment: v2.1.0 - Enhanced Error Handling & Logging**

**Deployed**: September 2, 2025
**Status**: ✅ **PRODUCTION READY**

### **🔧 New v2.1.0 Features**
- **✅ Centralized logging configuration** with contextual formatting
- **✅ Advanced retry utilities** with circuit breaker patterns
- **✅ Enhanced API client error handling** with monitoring integration
- **✅ Comprehensive test suite** with 17 test cases (100% pass rate)
- **✅ Structured logging** with sensitive data protection
- **✅ Production-ready error handling** for all external service calls

### **📊 Enhanced Logging Format**
```
2025-09-02T18:35:33.479550 - match-list-processor - storage_service - INFO - src.services.storage_service:57 - File uploaded to Google Drive...
```

**Container Image**: `ghcr.io/pitchconnect/match-list-processor:latest` (v2.1.0)

---

## **🎯 What This Repository Provides**

This repository contains a **complete automated deployment solution** for the FOGIS containerized system, including:

- ✅ **One-click setup** with automated dependency checking
- ✅ **Cron automation** for hourly match processing
- ✅ **Easy management commands** for system control
- ✅ **Comprehensive documentation** for non-technical users
- ✅ **Health monitoring** and troubleshooting tools

## **🚀 Quick Start (4 Commands)**

```bash
# 1. Set up credentials (enhanced 5-8 min OAuth wizard)
./manage_fogis_system.sh setup-auth

# 2. Check system status
./show_system_status.sh

# 3. Start the system (if needed)
./manage_fogis_system.sh start

# 4. Add automation
./manage_fogis_system.sh cron-add
```

**That's it! Your FOGIS system is now fully automated.** 🎉

## **📦 Container Image Deployment**

### **Production GHCR Images**

This deployment now uses **official published container images** from GitHub Container Registry (GHCR):

- **✅ fogis-api-client-service**: `ghcr.io/pitchconnect/fogis-api-client-python:latest`
- **✅ match-list-processor**: `ghcr.io/pitchconnect/match-list-processor:latest`
- **✅ google-drive-service**: `ghcr.io/pitchconnect/google-drive-service:latest`
- **✅ All other services**: Official GHCR images

### **Critical Fixes Included**

The latest GHCR images include these production-ready fixes:

1. **🔧 HTTP Wrapper Parameter Fix**:
   - Fixed parameter name from `filter` to `filter_params`
   - Resolves match-list-processor communication issues
   - Enables proper Google Drive asset upload pipeline

2. **🔧 PyPI Workflow Version Detection Fix**:
   - Corrected package name in publishing workflow
   - Robust regex-based version extraction
   - Ensures reliable future releases

### **No Local Patches Required**

- **❌ No local builds**: All services use published images
- **❌ No temporary fixes**: All fixes are in official releases
- **✅ Production ready**: Fully tested and verified deployment

## **🔐 OAuth Authentication During Startup**

### **Expected Behavior - No Action Required**

When starting FOGIS services, you may see OAuth-related messages during the first 30-60 seconds. **This is normal and expected behavior.**

#### **What You'll See:**
- 🔐 **Initial OAuth messages**: Services may log "OAuth authentication in progress..." or similar messages
- ⚠️ **Temporary warnings**: Brief OAuth errors during service initialization (first 30-60 seconds)
- ✅ **Self-healing**: Services automatically restore OAuth authentication using refresh tokens
- 🎯 **Final success**: All services report "authenticated" status within 60 seconds

#### **Timing Expectations:**
- **OAuth initialization**: 15-30 seconds after service startup
- **Token refresh**: Automatic when tokens are expired
- **Full authentication**: Typically completes within 60 seconds
- **No manual intervention required**: Services self-heal OAuth authentication

#### **Health Check Integration:**
```bash
# Check OAuth status for all services
./manage_fogis_system.sh health

# Individual service OAuth status
curl http://localhost:9085/health  # Google Drive service
curl http://localhost:9083/health  # Calendar service
```

#### **Normal Startup Log Examples:**
```
🔐 OAuth authentication in progress...
⚠️ Failed to obtain Google Calendar Credentials (temporary)
🔄 Refreshing expired Google token...
✅ OAuth authentication established
✅ Successfully authenticated in headless mode
```

**💡 Key Point**: If you see OAuth errors in the first minute after startup, wait 60 seconds before troubleshooting. Most issues resolve automatically.

## **📋 What This System Does**

- 🔄 **Automatically fetches** your FOGIS match assignments every hour
- 📱 **Creates WhatsApp group descriptions and avatars** for each match
- ☁️ **Uploads everything to Google Drive** with organized filenames
- 📅 **Syncs matches to your Google Calendar**
- 📞 **Manages referee contact information**
- 📊 **Logs all activity** for monitoring and troubleshooting

## **🔧 Management Commands**

### **🔐 Enhanced OAuth Setup (5-8 minutes):**
```bash
./manage_fogis_system.sh setup-auth # Enhanced OAuth wizard with browser automation
```

**Features:**
- ✅ **Browser automation** - Auto-opens correct Google Cloud Console pages
- ✅ **Real-time validation** - Immediate feedback on credential files
- ✅ **Intelligent detection** - Finds and reuses existing valid credentials
- ✅ **Copy-paste commands** - Ready-to-use values for all fields
- ✅ **Reduced setup time** - From 15-20 minutes to 5-8 minutes

### **System Control:**
```bash
./manage_fogis_system.sh start      # Start all services
./manage_fogis_system.sh stop       # Stop all services
./manage_fogis_system.sh restart    # Restart all services
./manage_fogis_system.sh status     # Show detailed status
```

### **🔄 Updates & Version Management:**
```bash
./manage_fogis_system.sh check-updates  # Check for image updates
./manage_fogis_system.sh update         # Update all services
./manage_fogis_system.sh version        # Show current versions
./manage_fogis_system.sh rollback       # Rollback information
```

### **🧪 Testing & Validation:**
```bash
# Test management commands
python3 test_management_commands.py

# Benchmark deployment performance
python3 benchmark_deployment.py

# Test multi-platform compatibility
python3 test_multiplatform.py
```

### **Testing & Monitoring:**
```bash
./manage_fogis_system.sh test       # Test the system manually
./manage_fogis_system.sh health     # Check service health
./manage_fogis_system.sh logs       # View all logs
```

### **📧 Notification System Testing:**
```bash
# Test notification system (validates configuration and sends test email)
./test-notifications.sh

# Comprehensive integration test (validates all notification components)
python3 test-notification-integration.py

# Test specific notification channels
docker exec process-matches-service python /tmp/simple-notification-test.py
```

**Notification Testing Features:**
- ✅ **Configuration Validation**: Checks environment variables and SMTP settings
- ✅ **Service Health**: Verifies Docker container access and notification system imports
- ✅ **Email Delivery**: Sends test email to configured SMTP_USERNAME
- ✅ **Integration Testing**: Validates stakeholder configuration and notification channels
- ✅ **Error Debugging**: Detailed logging for troubleshooting SMTP issues

### **Automation:**
```bash
./manage_fogis_system.sh cron-add     # Add hourly automation
./manage_fogis_system.sh cron-remove  # Remove automation
./manage_fogis_system.sh cron-status  # Check automation status
```

## **🌐 Service Architecture**

| Service | Purpose | Port | Image |
|---------|---------|------|-------|
| **FOGIS API Client** | Connects to FOGIS, serves match data | 9086 | `ghcr.io/pitchconnect/fogis-api-client-service` |
| **Team Logo Combiner** | Creates WhatsApp group avatars | 9088 | `ghcr.io/pitchconnect/team-logo-combiner` |
| **Calendar/Phonebook Sync** | Syncs to Google Calendar | 9084 | `ghcr.io/pitchconnect/fogis-calendar-phonebook-sync` |
| **Google Drive Service** | Uploads files to Google Drive | 9085 | `ghcr.io/pitchconnect/google-drive-service` |
| **Match Processor** | Main processing engine with internal scheduling | 9082 | `ghcr.io/pitchconnect/match-list-processor` |

### **📦 Container Features**
- **Multi-Architecture**: AMD64 and ARM64 support
- **Pre-built Images**: Instant deployment (30-60 seconds)
- **Automated Updates**: CI/CD pipeline with security scanning
- **Version Management**: Semantic versioning with rollback support

## **⏰ Automation**

Once set up, the system automatically:
- **Runs every hour** with internal scheduling (3600-second intervals)
- **Checks for new matches** from FOGIS using integrated change detection
- **Creates WhatsApp assets** for any new assignments
- **Uploads to Google Drive** with proper organization
- **Logs everything** for monitoring

## **🔍 Monitoring**

```bash
# Quick system overview
./show_system_status.sh

# Check if automation is working
./manage_fogis_system.sh cron-status

# View recent activity
tail -f logs/cron/match-processing.log

# Health check all services
./manage_fogis_system.sh health
```

## **🛠️ Prerequisites**

- **Docker Desktop** installed and running
- **Docker Compose** available
- **Google OAuth** configured (for Calendar/Drive access)
- **FOGIS credentials** for match data access

## **🎉 Success Indicators**

**✅ System is working when:**
- All services show "healthy" status
- Cron job runs every hour automatically
- WhatsApp assets are created and uploaded
- Matches appear in Google Calendar
- Logs show successful processing

## **🆘 Troubleshooting**

### **Common Issues:**
- **Services not starting:** `./manage_fogis_system.sh restart`
- **Docker not running:** Start Docker Desktop
- **Permission denied:** `chmod +x *.sh`
- **Cron not working:** Check system cron permissions

### **🔐 Google OAuth Authentication Issues**

#### **Quick OAuth Status Check:**
```bash
# Check current OAuth status
./setup_google_oauth.sh --check-only

# View Google Drive service status
curl -s http://localhost:9085/health | jq .
```

#### **Common OAuth Problems & Solutions:**

**❌ Problem: "Authentication required. Visit /authorize_gdrive to authenticate"**
```bash
# Solution 1: Run OAuth setup wizard
./setup_google_oauth.sh

# Solution 2: Restore from backup with OAuth automation
./restore_fogis_credentials.sh --auto --validate

# Solution 3: Manual authorization
# Visit: http://localhost:9085/authorize_gdrive
```

**❌ Problem: "Google credentials file missing"**
```bash
# Check if credentials exist
ls -la credentials/google-credentials.json

# If missing, run setup
./setup_google_oauth.sh

# Or restore from backup with OAuth automation
./restore_fogis_credentials.sh --auto
```

**❌ Problem: "Test credentials detected"**
- Your `google-credentials.json` contains test/example credentials
- Visit [Google Cloud Console](https://console.cloud.google.com/) to create production credentials
- Replace the file and restart services: `./manage_fogis_system.sh restart`

**❌ Problem: OAuth tokens expired**
```bash
# Services automatically refresh tokens, but if manual refresh needed:
docker restart google-drive-service

# Check if refresh worked
curl -s http://localhost:9085/health | jq '.auth_status'
```

#### **OAuth Setup from Scratch:**

**Step 1: Create Google Cloud Project**
1. Visit: https://console.cloud.google.com/
2. Create new project: "FOGIS-OAuth"
3. Enable APIs: Google Drive API, Google Calendar API, People API

**Step 2: Create OAuth Credentials**
1. Go to "APIs & Services" → "Credentials"
2. Create "OAuth client ID" → "Web application"
3. Add redirect URIs:
   - `http://localhost:9085/oauth2callback`
   - `http://localhost:9084/oauth2callback`
4. Download as `credentials/google-credentials.json`

**Step 3: Complete Authorization**
```bash
# Start services and run OAuth flow
./setup_google_oauth.sh --auto-start
```

#### **OAuth Troubleshooting Commands:**
```bash
# Comprehensive OAuth diagnosis
./setup_google_oauth.sh --check-only

# Validate credentials file
./restore_fogis_credentials.sh --validate

# Test OAuth automation workflow
./restore_fogis_credentials.sh backup-dir --auto

# Skip OAuth automation for manual setup
./restore_fogis_credentials.sh backup-dir --auto --no-oauth

# Check service logs for OAuth errors
docker logs google-drive-service --tail 20

# Test OAuth connectivity
curl -s http://localhost:9085/health

# Restart OAuth services
docker restart google-drive-service fogis-calendar-phonebook-sync
```

#### **OAuth Automation Troubleshooting:**
```bash
# Check OAuth automation prerequisites
./restore_fogis_credentials.sh --help  # See all options

# Test in headless mode (no prompts)
./restore_fogis_credentials.sh backup-dir --headless

# Manual OAuth setup after failed automation
python3 authenticate_all_services.py

# Verify OAuth status after setup
curl -s http://localhost:9083/health | jq '.status'
curl -s http://localhost:9085/health | jq '.auth_status'
```

#### **OAuth Service Health Indicators:**
- ✅ **Healthy**: `"auth_status": "authenticated"`
- ❌ **Needs Setup**: `"auth_status": "unauthenticated"`
- ⚠️ **Check Logs**: Service not responding

**Enhanced Health Check Features (Latest Update):**
- **Calendar Service**: Now properly detects OAuth tokens using environment variables
- **Multi-Location Detection**: Checks preferred, legacy, and working directory token locations
- **Detailed Status**: Includes `token_location` and `checked_locations` in responses
- **Accurate Monitoring**: Eliminates false negative health checks

### **🔧 Credential Management**

#### **Backup Credentials:**
```bash
# Create comprehensive backup
./create_credential_backup.sh

# Backup location: fogis-credentials-backup-YYYYMMDD-HHMMSS/
```

#### **Restore Credentials with OAuth Automation:**
```bash
# Auto-detect and restore latest backup with OAuth automation (default)
./restore_fogis_credentials.sh --auto --validate

# Restore specific backup with OAuth automation
./restore_fogis_credentials.sh backup-directory --auto

# Skip OAuth automation (manual setup required)
./restore_fogis_credentials.sh backup-directory --auto --no-oauth

# Headless restoration (no interactive prompts)
./restore_fogis_credentials.sh backup-directory --headless

# Interactive restoration with OAuth automation
./restore_fogis_credentials.sh --validate
```

**OAuth Automation Features:**
- ✅ **Automatic Detection**: Checks service health endpoints to determine OAuth needs
- ✅ **User Consent**: Interactive prompts with clear opt-out mechanisms
- ✅ **Prerequisite Validation**: Verifies Google credentials and dependencies
- ✅ **Graceful Fallback**: Provides manual setup instructions when automation fails
- ✅ **Production Ready**: Supports headless deployments with `--headless --no-oauth`

#### **Credential Validation:**
```bash
# Validate all credentials
./restore_fogis_credentials.sh --validate

# Check specific components
ls -la credentials/google-credentials.json
ls -la data/google-drive-service/
grep "FOGIS_USERNAME" .env
```

### **Get Help:**
```bash
# System diagnostics
./show_system_status.sh

# View logs
./manage_fogis_system.sh logs

# Test manually
./manage_fogis_system.sh test

# OAuth-specific help
./setup_google_oauth.sh --help
```

## **📚 Additional Documentation**

### **Service-Specific Guides**
- **[Calendar Service Authentication](CALENDAR_SERVICE_AUTHENTICATION.md)** - Detailed guide for calendar service OAuth token setup and troubleshooting
- **[Match Processor Service Behavior](MATCH_PROCESSOR_SERVICE_BEHAVIOR.md)** - Understanding the match processor's intended restart behavior and monitoring

### **Quick Reference**
- **OAuth Automation**: `./restore_fogis_credentials.sh backup-dir --auto` (includes automatic OAuth setup)
- **Headless Restoration**: `./restore_fogis_credentials.sh backup-dir --headless --no-oauth`
- **Manual OAuth Setup**: `python3 authenticate_all_services.py`
- **Calendar Service Token Fix**: `docker exec fogis-calendar-phonebook-sync cp /app/data/token.json /app/token.json`
- **Enhanced Credential Restoration**: `./restore_fogis_credentials.sh backup-dir --auto --validate`
- **Match Processor Monitoring**: Service restarts are normal behavior - check logs for processing activity

## **🔗 Related Repositories**

This deployment orchestrates services from:
- [fogis-api-client-python](https://github.com/PitchConnect/fogis-api-client-python)
- [match-list-processor](https://github.com/PitchConnect/match-list-processor)
- [team-logo-combiner](https://github.com/PitchConnect/team-logo-combiner)
- [google-drive-service](https://github.com/PitchConnect/google-drive-service)
- [fogis-calendar-phonebook-sync](https://github.com/PitchConnect/fogis-calendar-phonebook-sync)

---

**🎯 This repository provides everything needed for a complete, automated FOGIS deployment with zero technical knowledge required.**
# CI/CD Pipeline Status: Fixed embedded Git repository issues
# CI/CD Pipeline Status: Removed conflicting .github directories
