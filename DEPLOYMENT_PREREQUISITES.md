# FOGIS Deployment Prerequisites

## 📋 System Requirements

### **Operating System**
- **macOS**: 10.15+ (Catalina or newer)
- **Linux**: Ubuntu 18.04+, CentOS 7+, or equivalent
- **Windows**: Windows 10 with WSL2 enabled

### **Hardware Requirements**
- **RAM**: Minimum 4GB, Recommended 8GB+
- **Storage**: 10GB free space for containers and data
- **CPU**: 2+ cores recommended
- **Network**: Stable internet connection (for GHCR pulls and API calls)

## 🛠️ Required Software

### **1. Docker & Docker Compose**

#### **macOS Installation:**
```bash
# Install Docker Desktop
brew install --cask docker
# Or download from: https://docs.docker.com/desktop/mac/install/

# Verify installation
docker --version
docker-compose --version
```

#### **Linux Installation:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose

# CentOS/RHEL
sudo yum install docker docker-compose

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

#### **Windows Installation:**
1. Install Docker Desktop for Windows
2. Enable WSL2 integration
3. Verify in PowerShell: `docker --version`

### **2. Python 3.8+ (for configuration scripts)**
```bash
# macOS
brew install python3

# Ubuntu/Debian
sudo apt install python3 python3-pip

# CentOS/RHEL
sudo yum install python3 python3-pip
```

### **3. Required Python Packages**
```bash
pip3 install google-auth-oauthlib requests python-dotenv
```

## 🔑 Required Accounts & Credentials

### **1. FOGIS Account**
- **Username**: Your FOGIS login username
- **Password**: Your FOGIS login password
- **Referee Number**: Found in your FOGIS profile (e.g., 61318)

### **2. Google Cloud Project**

#### **🚀 Enhanced Setup (5-8 minutes with automation):**
The FOGIS deployment now includes an **enhanced OAuth wizard** that automates most of the Google Cloud setup:

```bash
./manage_fogis_system.sh setup-auth
```

**Features:**
- ✅ **Browser automation** - Auto-opens correct Google Cloud Console pages
- ✅ **Real-time validation** - Immediate feedback on credential files
- ✅ **Intelligent detection** - Finds and reuses existing valid credentials
- ✅ **Copy-paste commands** - Ready-to-use values for all fields
- ✅ **Reduced setup time** - From 15-20 minutes to 5-8 minutes

#### **Manual Setup Steps (if needed):**
1. **Create Google Cloud Project**
   - Go to: https://console.cloud.google.com/
   - Click "New Project"
   - Name: "FOGIS Integration" (or similar)

2. **Enable Required APIs**
   ```
   - Google Calendar API
   - Google People API (Contacts)
   - Google Drive API
   ```

3. **Create OAuth Credentials**
   - Go to: APIs & Services → Credentials
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: "Web application" ⚠️ **IMPORTANT: NOT Desktop**
   - Name: "FOGIS Web Client"
   - Authorized redirect URIs: Add both:
     - `http://localhost:8080/callback`
     - `http://127.0.0.1:8080/callback`
   - Download JSON file as `credentials.json`

4. **Configure OAuth Consent Screen**
   - Go to: APIs & Services → OAuth consent screen
   - User Type: External (for personal use)
   - Add your email as test user
   - Scopes: Add Calendar, Contacts, Drive scopes

## 🌐 Network Requirements

### **Internet Connectivity**
- **GHCR Access**: Pull container images from ghcr.io
- **FOGIS API**: Access to FOGIS web services
- **Google APIs**: Calendar, Contacts, Drive API access

### **Firewall Considerations**
- **Outbound HTTPS (443)**: Required for all API calls
- **Outbound HTTP (80)**: For health checks and webhooks
- **Local Ports**: 9080-9088 for service health endpoints

### **Docker Network**
- The system creates its own Docker network: `fogis-network`
- No external network dependencies

## 📁 Directory Structure

### **Required Directories** (auto-created)
```
fogis-deployment/
├── credentials/              # Google OAuth credentials
├── data/                    # Persistent service data
│   ├── fogis-api-client/
│   ├── match-list-change-detector/
│   ├── fogis-calendar-phonebook-sync/
│   ├── team-logo-combiner/
│   ├── google-drive-service/
│   └── match-list-processor/
└── logs/                    # Service logs
    ├── fogis-api-client/
    ├── match-list-change-detector/
    ├── fogis-calendar-phonebook-sync/
    ├── team-logo-combiner/
    ├── google-drive-service/
    └── match-list-processor/
```

## ✅ Pre-Deployment Checklist

### **Before Running configure_system.py:**

- [ ] Docker and Docker Compose installed and working
- [ ] Python 3.8+ installed
- [ ] Required Python packages installed (`pip3 install google-auth-oauthlib requests python-dotenv`)
- [ ] FOGIS account credentials available
- [ ] Google Cloud project created with APIs enabled
- [ ] Google OAuth credentials JSON file downloaded
- [ ] Stable internet connection
- [ ] 10GB+ free disk space

### **Verification Commands:**
```bash
# Check Docker
docker --version
docker-compose --version
docker run hello-world

# Check Python
python3 --version
pip3 list | grep -E "(google-auth-oauthlib|requests|python-dotenv)"

# Check internet connectivity
curl -I https://ghcr.io
curl -I https://www.googleapis.com
```

## 🚨 Common Issues & Solutions

### **Docker Permission Issues (Linux)**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in
```

### **Python Package Installation Issues**
```bash
# Use user installation if system-wide fails
pip3 install --user google-auth-oauthlib requests python-dotenv
```

### **Google API Quota Issues**
- Ensure APIs are enabled in Google Cloud Console
- Check quota limits in APIs & Services → Quotas
- Verify OAuth consent screen is configured

### **Network Connectivity Issues**
```bash
# Test GHCR connectivity
docker pull hello-world

# Test Google API connectivity
curl https://www.googleapis.com/calendar/v3/users/me/calendarList
```

## 📞 Support

If you encounter issues during setup:

1. **Check Prerequisites**: Verify all requirements above
2. **Review Error Messages**: Most issues are clearly indicated
3. **Check Logs**: Use `./manage_fogis_system.sh logs` for service logs
4. **Verify Credentials**: Ensure FOGIS and Google credentials are correct
5. **Network Issues**: Verify internet connectivity and firewall settings

---

## 🚀 Quick Start Guide

### **Step 1: Prerequisites Check**
```bash
# Verify Docker installation
docker --version && docker-compose --version

# Install Python dependencies
pip3 install -r requirements.txt

# Test GHCR connectivity
docker pull ghcr.io/pitchconnect/team-logo-combiner:latest
```

### **Step 2: Interactive Configuration**
```bash
# Run the configuration wizard
python3 configure_system.py
```

### **Step 3: Start the System**
```bash
# Start all services (30-60 second boot time)
./manage_fogis_system.sh start

# Authenticate Google services
python3 authenticate_all_services.py

# Check system status
./show_system_status.sh
```

### **Step 4: Verify Deployment**
```bash
# Test health endpoints
curl http://localhost:9086/health  # FOGIS API Client
curl http://localhost:9085/health  # Google Drive Service
curl http://localhost:9088/health  # Team Logo Combiner
```

**Expected Boot Time**: 30-60 seconds (vs 5-8 minutes with local builds)

---

**Next Step**: Once all prerequisites are met, run `python3 configure_system.py` to begin the interactive setup process.
