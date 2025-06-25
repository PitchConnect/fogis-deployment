# 🔧 FOGIS Calendar Sync Resolution Guide

## 🎯 Issue Summary

**Problem**: June 28th match referee assignment change not reflected in Google Calendar

**Root Cause**: Missing FOGIS authentication credentials preventing the system from fetching updated match data

**Secondary Issue**: OAuth authentication method change from desktop to web application OAuth

**Impact**: Complete calendar synchronization failure - no match updates are being processed

## 🔄 **IMPORTANT: OAuth Authentication Method Change**

**The fogis-calendar-phonebook-sync service has been updated to use web application OAuth instead of desktop OAuth.** This change affects how Google Calendar authentication is set up:

### **What Changed:**
- **Before**: Desktop application OAuth with `InstalledAppFlow` (manual code entry)
- **After**: Web application OAuth with `Flow` (browser-based authentication)
- **Redirect URI**: Now uses `http://localhost:9084/callback` instead of `http://127.0.0.1`
- **Authentication Interface**: New web interface available at `http://localhost:9087`

### **Why This Matters:**
- Old desktop OAuth credentials will not work with the new system
- The authentication process now requires web application OAuth credentials
- Setup process has changed to use the web interface instead of command-line prompts

### **Impact on Resolution:**
- You'll need to create **web application** OAuth credentials (not desktop)
- Authentication is completed through a web browser interface
- The process is more user-friendly but requires different credential setup

## 📊 Current System Status

✅ **Working Components**:
- Docker containers are running
- Calendar sync service is operational
- Team logo combiner is healthy
- Google Drive service is healthy

❌ **Failing Components**:
- FOGIS API Client (missing credentials)
- Match data retrieval (500 errors)
- Google Calendar authentication (missing token)
- Match change detection (not starting)

## 🛠️ Step-by-Step Resolution

### Phase 1: FOGIS Authentication Setup

#### Step 1: Create FOGIS Credentials File

```bash
# Navigate to the FOGIS deployment directory
cd /path/to/fogis-deployment

# Create .env file with your FOGIS credentials
cat > .env << 'EOF'
FOGIS_USERNAME=your_actual_fogis_username
FOGIS_PASSWORD=your_actual_fogis_password
EOF

# Secure the credentials file
chmod 600 .env
```

**⚠️ Important**: Replace `your_actual_fogis_username` and `your_actual_fogis_password` with your real FOGIS login credentials.

#### Step 2: Restart Services with New Credentials

```bash
# Stop all services
./manage_fogis_system.sh stop

# Start services with new credentials
./manage_fogis_system.sh start

# Wait 30 seconds for services to initialize
sleep 30
```

#### Step 3: Verify FOGIS API Connection

```bash
# Check FOGIS API health (should show "healthy" instead of "degraded")
curl http://localhost:9086/health

# Test match data access (should return JSON instead of 500 error)
curl http://localhost:9086/matches
```

**Expected Result**: FOGIS API should return `"status": "healthy"` and match data should be accessible.

### Phase 2: Google Calendar Authentication

**⚠️ IMPORTANT: OAuth Method Change**

The fogis-calendar-phonebook-sync service has been updated to use **web application OAuth** instead of desktop OAuth. This requires a different setup process.

#### Step 4: Set Up Google OAuth (New Web-Based Method)

**Option A: Use the Web Authentication Interface (Recommended)**

```bash
# First, ensure the web authentication interface is running
./start_web_auth_interface.sh

# Access the web authentication manager
open http://localhost:9087
# Or visit manually: http://localhost:9087
```

**In the web interface:**
1. Click "🚀 Start New Authentication"
2. Check your email for the authentication link
3. Complete authentication within 10 minutes
4. Return to verify the token status shows "Valid"

**Option B: Alternative Setup Method**

If the web interface doesn't work, you can set up credentials manually:

1. **Create Web Application OAuth Credentials**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create or select a project
   - Enable Calendar, Contacts, and Drive APIs
   - Create OAuth 2.0 credentials for **Web Application** (not Desktop)
   - Add authorized redirect URI: `http://localhost:9084/callback`
   - Download the credentials as `credentials.json`

2. **Place Credentials in Container**:
   ```bash
   # Copy credentials to the container
   docker cp credentials.json fogis-calendar-phonebook-sync:/app/credentials.json

   # Restart the calendar sync service
   docker restart fogis-calendar-phonebook-sync
   ```

3. **Complete Authentication**:
   ```bash
   # Access the authentication interface
   open http://localhost:9087
   ```

#### Step 5: Verify Calendar Sync Service

```bash
# Check calendar sync health (should not show token warnings)
curl http://localhost:9083/health

# Check web authentication interface status
curl http://localhost:9087/status
```

**Expected Results**:
- No "token.json not found" warnings in health check
- Web interface shows token as "Valid" and not expired
- Authentication status shows successful completion

### Phase 3: Validate and Test

#### Step 6: Run System Health Check

```bash
# Run comprehensive health monitoring
./monitor_calendar_sync_health.sh

# Generate detailed health report
./monitor_calendar_sync_health.sh --report
```

**Expected Result**: All components should show as healthy.

#### Step 7: Test June 28th Match Processing

```bash
# Manually trigger match processing
./manage_fogis_system.sh test

# Check for June 28th match in the data
curl http://localhost:9086/matches | grep -i "2025-06-28\|june.*28"

# Force calendar sync for June 28th (if needed)
curl -X POST http://localhost:9083/sync \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-06-28", "force_update": true}'
```

#### Step 8: Enable Automated Processing

```bash
# Add cron job for hourly processing
./manage_fogis_system.sh cron-add

# Verify cron is working
./manage_fogis_system.sh cron-status
```

## 🔍 Verification Checklist

After completing the resolution steps, verify:

- [ ] **FOGIS API Health**: `curl http://localhost:9086/health` returns `"status": "healthy"`
- [ ] **Match Data Access**: `curl http://localhost:9086/matches` returns match list (not 500 error)
- [ ] **Calendar Sync Health**: `curl http://localhost:9083/health` returns success (no token warnings)
- [ ] **June 28th Match**: Match appears in API response with updated referee information
- [ ] **Google Calendar**: June 28th calendar entry is updated with new referee
- [ ] **System Health**: `./monitor_calendar_sync_health.sh` shows all components healthy
- [ ] **Automation**: `./manage_fogis_system.sh cron-status` shows active cron job

## 🚨 Troubleshooting

### If FOGIS API Still Shows "Degraded"

```bash
# Check if credentials are correctly formatted
cat .env

# Verify environment variables are loaded
docker exec fogis-api-client-service env | grep FOGIS

# Check container logs for authentication errors
docker logs fogis-api-client-service --tail 20
```

### If Google Calendar Sync Fails

**For Web OAuth Authentication Issues:**

```bash
# Check if credentials file exists in container
docker exec fogis-calendar-phonebook-sync ls -la /app/credentials.json

# Check web authentication interface
curl http://localhost:9087/status

# Check calendar sync logs for OAuth errors
docker logs fogis-calendar-phonebook-sync --tail 20 | grep -i "oauth\|token\|auth"

# Restart authentication process via web interface
curl -X POST http://localhost:9087/restart-auth
```

**For Credential Setup Issues:**

```bash
# Verify OAuth client type (should be web application)
docker exec fogis-calendar-phonebook-sync cat /app/credentials.json | grep -A 5 -B 5 "web\|installed"

# Check redirect URI configuration
docker exec fogis-calendar-phonebook-sync grep -r "redirect.*uri\|callback" /app/

# Manual credential placement if needed
docker cp credentials.json fogis-calendar-phonebook-sync:/app/credentials.json
docker restart fogis-calendar-phonebook-sync
```

### If June 28th Match Still Not Updated

```bash
# Force a complete system restart
./manage_fogis_system.sh restart

# Wait for initialization
sleep 60

# Manually trigger processing
./manage_fogis_system.sh test

# Check calendar sync logs for the specific date
docker logs fogis-calendar-phonebook-sync | grep -i "june\|28\|2025-06-28"
```

## 📈 Prevention and Monitoring

### Set Up Automated Health Monitoring

```bash
# Add daily health checks to cron
echo "0 8 * * * cd $(pwd) && ./monitor_calendar_sync_health.sh --report" | crontab -

# Create alert script for credential issues
cat > alert_on_credential_issues.sh << 'EOF'
#!/bin/bash
if ! ./monitor_calendar_sync_health.sh | grep -q "Overall system health: GOOD"; then
    echo "ALERT: FOGIS calendar sync has health issues - check credentials"
    # Add your notification method here (email, Slack, etc.)
fi
EOF

chmod +x alert_on_credential_issues.sh
```

### Backup Credentials

```bash
# Create secure backup of working credentials
cp .env .env.backup
cp -r credentials credentials.backup
chmod 600 .env.backup
chmod -R 600 credentials.backup
```

## 🎯 Expected Outcome

Once these steps are completed:

1. **Immediate Fix**: June 28th match will be processed and calendar entry updated with new referee
2. **System Restoration**: All FOGIS services will be fully functional
3. **Future Prevention**: Automated hourly processing will catch referee changes immediately
4. **Monitoring**: Health checks will alert to credential issues before they cause problems

## 📞 Support

If issues persist after following this guide:

1. **Generate Health Report**: `./monitor_calendar_sync_health.sh --report`
2. **Collect Logs**: `./manage_fogis_system.sh logs > system_logs.txt`
3. **Check Service Status**: `./manage_fogis_system.sh status > service_status.txt`
4. **Review Error Messages**: Look for specific error patterns in the logs

The calendar synchronization issue should be resolved, and the system will be more resilient to similar problems in the future.

---

**📝 Note**: This guide was generated based on the comprehensive system analysis performed on 2025-06-25. The resolution steps have been validated against the current system state.
