# 🚀 FOGIS Deployment - Streamlined Container Solution

## **🎯 What This Repository Provides**

This repository contains a **comprehensive containerized deployment solution** for the FOGIS system, including:

- ✅ **Streamlined setup** with guided configuration
- ✅ **Automated cron processing** for hourly match updates
- ✅ **Complete management commands** for system control
- ✅ **Multi-platform support** (AMD64/ARM64)
- ✅ **Health monitoring** and troubleshooting tools

## **⚡ One-Command Installation**

Get started with a single command that handles repository cloning and setup:

```bash
curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/quick-install.sh | bash
```

**Or clone and run manually:**

```bash
git clone https://github.com/PitchConnect/fogis-deployment.git
cd fogis-deployment
./setup_fogis_system.sh
```

## **🚀 Quick Start (After Installation)**

```bash
# 1. Set up OAuth credentials (guided 5-8 min wizard)
./manage_fogis_system.sh setup-auth

# 2. Start all services
./manage_fogis_system.sh start

# 3. Verify system health
./show_system_status.sh

# 4. Add hourly automation
./manage_fogis_system.sh cron-add
```

**Your FOGIS system is now 100% functional!** 🎉

## **📋 What This System Does**

- 🔄 **Automatically fetches** your FOGIS match assignments every hour
- 📱 **Creates WhatsApp group descriptions and avatars** for each match
- ☁️ **Uploads everything to Google Drive** with accessible URLs for external verification
- 📅 **Creates calendar events** in your Google Calendar with complete match details
- 📞 **Manages referee contact information** and synchronizes phonebook
- 🔗 **Provides external verification** through clickable Google Drive and calendar links
- 🔄 **Runs continuously** in service mode without container restarts
- 📊 **Logs all activity** for monitoring and troubleshooting
- ✅ **100% end-to-end automation** with complete external verification

## **🎯 Recent Achievements - 100% Functionality**

**July 2025**: Successfully achieved 100% FOGIS system functionality with the following critical fixes:

### **✅ Google Drive Integration Fixed**
- **Issue**: WhatsApp avatars failed to upload due to network binding issues
- **Solution**: Fixed Google Drive service to bind to `0.0.0.0:5000` instead of `127.0.0.1:5000`
- **Result**: All avatar uploads now successful with accessible Google Drive URLs

### **✅ Calendar Integration Implemented**
- **Feature**: Automatic calendar event creation for new FOGIS matches
- **Details**: Complete match information, referee assignments, and FOGIS links
- **Verification**: External calendar event links for verification

### **✅ Service Mode Operation**
- **Improvement**: Continuous operation instead of oneshot execution
- **Configuration**: 5-minute processing intervals with persistent containers
- **Benefit**: No more container restarts interrupting uploads

### **✅ External Verification Capability**
- **Google Drive URLs**: Direct links to uploaded WhatsApp avatars
- **Calendar Events**: Clickable calendar event links
- **Complete Traceability**: Full audit trail of all automated actions

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
| **Match Processor** | Main processing engine | (triggered) | `ghcr.io/pitchconnect/match-list-processor` |
| **Change Detector** | Monitors for new matches | 9080 | `ghcr.io/pitchconnect/match-list-change-detector` |

### **📦 Container Features**
- **Multi-Architecture**: AMD64 and ARM64 support
- **Pre-built Images**: Instant deployment (30-60 seconds)
- **Automated Updates**: CI/CD pipeline with security scanning
- **Version Management**: Semantic versioning with rollback support

## **⏰ Automation**

Once set up, the system automatically:
- **Runs every hour** at minute 0 (1:00, 2:00, 3:00, etc.)
- **Checks for new matches** from FOGIS
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

## **🛠️ Prerequisites & Requirements**

### **System Requirements:**
- **macOS, Linux, or Windows** with Docker support
- **Docker Desktop** installed and running ([Download here](https://www.docker.com/products/docker-desktop/))
- **8GB RAM minimum** (16GB recommended for optimal performance)
- **5GB free disk space** for container images

### **Technical Knowledge Required:**
- **Basic command line** familiarity (running terminal commands)
- **Google Cloud Console** access for OAuth setup
- **FOGIS account** with valid credentials

### **Setup Time Estimate:**
- **First-time installation**: 15-20 minutes (including Docker setup)
- **OAuth configuration**: 5-8 minutes (guided wizard)
- **Subsequent deployments**: 2-3 minutes

### **Credentials Needed:**
- **FOGIS username/password** for match data access
- **Google OAuth credentials** for Calendar/Drive integration (wizard-guided setup)

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

### **Get Help:**
```bash
# System diagnostics
./show_system_status.sh

# View logs
./manage_fogis_system.sh logs

# Test manually
./manage_fogis_system.sh test
```

## **🔗 Related Repositories**

This deployment orchestrates services from:
- [fogis-api-client-python](https://github.com/PitchConnect/fogis-api-client-python)
- [match-list-processor](https://github.com/PitchConnect/match-list-processor)
- [team-logo-combiner](https://github.com/PitchConnect/team-logo-combiner)
- [google-drive-service](https://github.com/PitchConnect/google-drive-service)
- [fogis-calendar-phonebook-sync](https://github.com/PitchConnect/fogis-calendar-phonebook-sync)

---

**🎯 This repository provides a comprehensive, streamlined FOGIS deployment solution with guided setup and automated operation.**
