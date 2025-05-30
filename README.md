# 🚀 FOGIS Deployment - Complete Automated Solution

## **🎯 What This Repository Provides**

This repository contains a **complete automated deployment solution** for the FOGIS containerized system, including:

- ✅ **One-click setup** with automated dependency checking
- ✅ **Cron automation** for hourly match processing  
- ✅ **Easy management commands** for system control
- ✅ **Comprehensive documentation** for non-technical users
- ✅ **Health monitoring** and troubleshooting tools

## **🚀 Quick Start (3 Commands)**

```bash
# 1. Check system status
./show_system_status.sh

# 2. Start the system (if needed)
./manage_fogis_system.sh start

# 3. Add automation
./manage_fogis_system.sh cron-add
```

**That's it! Your FOGIS system is now fully automated.** 🎉

## **📋 What This System Does**

- 🔄 **Automatically fetches** your FOGIS match assignments every hour
- 📱 **Creates WhatsApp group descriptions and avatars** for each match
- ☁️ **Uploads everything to Google Drive** with organized filenames
- 📅 **Syncs matches to your Google Calendar**
- 📞 **Manages referee contact information**
- 📊 **Logs all activity** for monitoring and troubleshooting

## **🔧 Management Commands**

### **System Control:**
```bash
./manage_fogis_system.sh start      # Start all services
./manage_fogis_system.sh stop       # Stop all services  
./manage_fogis_system.sh restart    # Restart all services
./manage_fogis_system.sh status     # Show detailed status
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

| Service | Purpose | Port |
|---------|---------|------|
| **FOGIS API Client** | Connects to FOGIS, serves match data | 9086 |
| **Team Logo Combiner** | Creates WhatsApp group avatars | 9088 |
| **Calendar/Phonebook Sync** | Syncs to Google Calendar | 9084 |
| **Google Drive Service** | Uploads files to Google Drive | 9085 |
| **Match Processor** | Main processing engine | (triggered) |

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

**🎯 This repository provides everything needed for a complete, automated FOGIS deployment with zero technical knowledge required.**
