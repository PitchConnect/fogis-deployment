# OAuth Setup Checklist - Quick Reference

## 🚀 Enhanced OAuth Setup (5-8 minutes)

**Run the enhanced wizard:**
```bash
./manage_fogis_system.sh setup-auth
```

The enhanced wizard provides:
- ✅ **Browser automation** - Auto-opens correct Google Cloud Console pages
- ✅ **Real-time validation** - Immediate feedback on credential files
- ✅ **Intelligent detection** - Finds and reuses existing valid credentials
- ✅ **Copy-paste commands** - Ready-to-use values for all fields

---

## 📋 Manual Setup Checklist (if needed)

### **Step 1: Google Cloud Project**
1. Go to: https://console.cloud.google.com/projectcreate
2. **Project name:** `FOGIS Integration`
3. Click **CREATE**
4. Note your **Project ID** (format: `project-name-123456`)

### **Step 2: Enable APIs**
For each API, go to the URL and click **ENABLE**:

1. **Calendar API:** https://console.cloud.google.com/apis/library/calendar-json.googleapis.com?project=YOUR_PROJECT_ID
2. **Drive API:** https://console.cloud.google.com/apis/library/drive.googleapis.com?project=YOUR_PROJECT_ID  
3. **People API:** https://console.cloud.google.com/apis/library/people.googleapis.com?project=YOUR_PROJECT_ID

### **Step 3: Create OAuth Client**
1. Go to: https://console.cloud.google.com/apis/credentials?project=YOUR_PROJECT_ID
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. **Application type:** `Web application` ⚠️ **IMPORTANT: NOT Desktop**
4. **Name:** `FOGIS Web Client`
5. **Authorized redirect URIs** (add both):
   ```
   http://localhost:8080/callback
   http://127.0.0.1:8080/callback
   ```
6. Click **CREATE**
7. Click **DOWNLOAD JSON**
8. Save as `credentials.json` in the fogis-deployment directory

---

## 🔍 Copy-Paste Ready Values

### **Project Name:**
```
FOGIS Integration
```

### **OAuth Client Name:**
```
FOGIS Web Client
```

### **Redirect URIs (add both):**
```
http://localhost:8080/callback
http://127.0.0.1:8080/callback
```

### **Required API IDs:**
```
calendar-json.googleapis.com
drive.googleapis.com
people.googleapis.com
```

---

## ✅ Validation Checklist

**Your credentials.json should contain:**
- ✅ `"web"` section (not `"installed"`)
- ✅ `client_id` field
- ✅ `client_secret` field
- ✅ Both redirect URIs listed above
- ✅ File saved as `credentials.json` in fogis-deployment directory

**Test your setup:**
```bash
# Validate credentials
python3 lib/enhanced_oauth_wizard.py

# Start FOGIS services
./manage_fogis_system.sh start

# Check system status
./show_system_status.sh
```

---

## 🆘 Common Issues & Solutions

### **"Invalid credential type" error**
- **Problem:** Downloaded "Desktop application" credentials
- **Solution:** Create "Web application" credentials instead

### **"Missing redirect URIs" error**
- **Problem:** Forgot to add redirect URIs or added wrong ones
- **Solution:** Add both URIs exactly as shown above

### **"API not enabled" error**
- **Problem:** Forgot to enable required APIs
- **Solution:** Enable all 3 APIs listed in Step 2

### **"File not found" error**
- **Problem:** credentials.json not in correct location
- **Solution:** Save file as `credentials.json` in fogis-deployment directory

### **Browser doesn't open automatically**
- **Problem:** System doesn't support automatic browser opening
- **Solution:** Manually copy-paste URLs from the wizard output

---

## 🎯 Success Indicators

**OAuth setup is complete when:**
- ✅ Enhanced wizard shows "OAuth setup completed successfully!"
- ✅ `credentials.json` file exists and validates
- ✅ All 3 Google APIs are enabled
- ✅ OAuth client has correct redirect URIs
- ✅ FOGIS services start without authentication errors

**Next steps after successful OAuth setup:**
1. `./manage_fogis_system.sh start` - Start all services
2. `./show_system_status.sh` - Verify system health
3. `./manage_fogis_system.sh cron-add` - Add automation

---

## 📞 Getting Help

**If you encounter issues:**
1. Check this checklist for common solutions
2. Run the enhanced wizard again: `./manage_fogis_system.sh setup-auth`
3. Check system logs: `./manage_fogis_system.sh logs`
4. Verify prerequisites: Review `DEPLOYMENT_PREREQUISITES.md`

**The enhanced OAuth wizard reduces setup time from 15-20 minutes to 5-8 minutes with automated guidance and validation.**
