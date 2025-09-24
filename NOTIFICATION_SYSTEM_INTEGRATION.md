# Notification System Integration Guide

## 🔔 **Overview**

The match-list-processor now includes a comprehensive notification system that requires integration with the FOGIS deployment infrastructure. This document outlines the required updates to enable notifications in deployed environments.

## 📋 **Required Deployment Updates**

### **1. Docker Compose Configuration Updates**

The `docker-compose.yml` needs notification environment variables and volume mounts:

```yaml
# Add to process-matches-service environment section:
environment:
  # Existing variables...
  
  # Notification System Configuration
  - NOTIFICATION_SYSTEM_ENABLED=${NOTIFICATION_SYSTEM_ENABLED:-false}
  - NOTIFICATION_BATCH_SIZE=${NOTIFICATION_BATCH_SIZE:-10}
  - NOTIFICATION_BATCH_TIMEOUT=${NOTIFICATION_BATCH_TIMEOUT:-30}
  
  # Email Configuration
  - EMAIL_ENABLED=${EMAIL_ENABLED:-false}
  - SMTP_HOST=${SMTP_HOST:-smtp.gmail.com}
  - SMTP_PORT=${SMTP_PORT:-587}
  - SMTP_USERNAME=${SMTP_USERNAME}
  - SMTP_PASSWORD=${SMTP_PASSWORD}
  - SMTP_FROM=${SMTP_FROM}
  - SMTP_USE_TLS=${SMTP_USE_TLS:-true}
  
  # Discord Configuration
  - DISCORD_ENABLED=${DISCORD_ENABLED:-false}
  - DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}
  - DISCORD_BOT_USERNAME=${DISCORD_BOT_USERNAME:-FOGIS Match Bot}
  
  # Webhook Configuration
  - WEBHOOK_ENABLED=${WEBHOOK_ENABLED:-false}
  - WEBHOOK_URL=${WEBHOOK_URL}
  - WEBHOOK_AUTH_TOKEN=${WEBHOOK_AUTH_TOKEN}
  - WEBHOOK_TIMEOUT=${WEBHOOK_TIMEOUT:-30}
  
  # Security and Monitoring
  - NOTIFICATION_ENCRYPT_DATA=${NOTIFICATION_ENCRYPT_DATA:-false}
  - NOTIFICATION_DEBUG=${NOTIFICATION_DEBUG:-false}
  - NOTIFICATION_TEST_MODE=${NOTIFICATION_TEST_MODE:-false}

# Add to volumes section:
volumes:
  - ./data/process-matches-service:/app/data
  - ./logs/process-matches-service:/app/logs
  - ./config/notifications:/app/config/notifications  # New: notification config
```

### **2. Configuration Template Updates**

Replace the basic notification section in `fogis-config.template.yaml`:

```yaml
# Notification System Configuration (Enhanced)
notifications:
  # Enable notification system
  enabled: false  # Set to true to enable notifications
  
  # Email notifications
  email:
    enabled: false
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    smtp_username: ""           # Your email username
    smtp_password: ""           # Your email password or app password
    smtp_from: ""              # Sender email address
    use_tls: true
    
  # Discord notifications
  discord:
    enabled: false
    webhook_url: ""            # Discord webhook URL
    bot_username: "FOGIS Match Bot"
    
  # Webhook notifications
  webhook:
    enabled: false
    webhook_url: ""            # Generic webhook endpoint
    auth_token: ""             # Authentication token if required
    timeout: 30
    
  # Stakeholder configuration
  stakeholders:
    # Administrator contacts
    administrators:
      - name: "System Administrator"
        email: ""              # Admin email address
        role: "Administrator"
        channels: ["email"]
        
    # Referee coordinator contacts  
    coordinators:
      - name: "Referee Coordinator"
        email: ""              # Coordinator email address
        role: "RefereeCoordinator"
        channels: ["email", "discord"]
        
  # Notification preferences
  preferences:
    # Send notifications for match changes
    match_changes: true
    # Send notifications for referee assignments
    referee_assignments: true
    # Send notifications for system alerts
    system_alerts: true
    # Send notifications for critical errors
    critical_errors: true
    
  # Advanced settings
  advanced:
    batch_size: 10             # Number of notifications to batch together
    batch_timeout: 30          # Seconds to wait before sending batch
    encrypt_data: false        # Encrypt stored notification data
    debug_mode: false          # Enable debug logging
    test_mode: false           # Send all notifications to test recipients
```

### **3. Environment Template Creation**

Create `.env.template` in fogis-deployment root:

```bash
# FOGIS Deployment Environment Configuration
# Copy this file to .env and fill in your values

# =============================================================================
# NOTIFICATION SYSTEM CONFIGURATION
# =============================================================================

# Enable/disable notification system
NOTIFICATION_SYSTEM_ENABLED=false

# Notification batch processing
NOTIFICATION_BATCH_SIZE=10
NOTIFICATION_BATCH_TIMEOUT=30

# =============================================================================
# EMAIL NOTIFICATIONS
# =============================================================================

# Enable email notifications
EMAIL_ENABLED=false

# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_USE_TLS=true

# =============================================================================
# DISCORD NOTIFICATIONS
# =============================================================================

# Enable Discord notifications
DISCORD_ENABLED=false

# Discord Configuration
DISCORD_WEBHOOK_URL=
DISCORD_BOT_USERNAME=FOGIS Match Bot

# =============================================================================
# WEBHOOK NOTIFICATIONS
# =============================================================================

# Enable webhook notifications
WEBHOOK_ENABLED=false

# Webhook Configuration
WEBHOOK_URL=
WEBHOOK_AUTH_TOKEN=
WEBHOOK_TIMEOUT=30

# =============================================================================
# SECURITY AND MONITORING
# =============================================================================

# Security settings
NOTIFICATION_ENCRYPT_DATA=false
NOTIFICATION_DEBUG=false

# Testing settings
NOTIFICATION_TEST_MODE=false
NOTIFICATION_TEST_EMAIL=
```

### **4. Installation Script Updates**

Add notification setup to installation scripts:

```bash
# Add to install_enhanced.sh

setup_notifications() {
    echo "🔔 Setting up notification system..."
    
    # Create notification config directory
    mkdir -p config/notifications
    
    # Copy notification configuration if it doesn't exist
    if [ ! -f "config/notifications/notification_channels.yml" ]; then
        echo "📋 Creating notification configuration..."
        # This would copy from match-list-processor template
        docker run --rm -v $(pwd)/config/notifications:/output \
            ghcr.io/pitchconnect/match-list-processor:latest \
            cp /app/config/notification_channels.yml /output/
    fi
    
    # Copy stakeholder template if it doesn't exist
    if [ ! -f "data/process-matches-service/stakeholders.json" ]; then
        echo "👥 Creating stakeholder database..."
        docker run --rm -v $(pwd)/data/process-matches-service:/output \
            ghcr.io/pitchconnect/match-list-processor:latest \
            cp /app/config/stakeholders_template.json /output/stakeholders.json
    fi
    
    echo "✅ Notification system setup complete"
    echo "📝 Edit config/notifications/notification_channels.yml to configure channels"
    echo "👥 Edit data/process-matches-service/stakeholders.json to add stakeholders"
}

# Add to main installation flow
setup_notifications
```

### **5. Validation Script Updates**

Add notification validation to existing validation scripts:

```bash
# Add to validate_implementation.sh

validate_notifications() {
    echo "🔔 Validating notification system..."
    
    # Check if notification files exist
    if [ -f "config/notifications/notification_channels.yml" ]; then
        echo "✅ Notification configuration found"
    else
        echo "⚠️  Notification configuration missing"
    fi
    
    # Check stakeholder database
    if [ -f "data/process-matches-service/stakeholders.json" ]; then
        echo "✅ Stakeholder database found"
    else
        echo "⚠️  Stakeholder database missing"
    fi
    
    # Test notification system if enabled
    if [ "$NOTIFICATION_SYSTEM_ENABLED" = "true" ]; then
        echo "🧪 Testing notification system..."
        docker exec process-matches-service python scripts/test_notifications.py --dry-run
    else
        echo "ℹ️  Notification system disabled"
    fi
}

# Add to main validation flow
validate_notifications
```

## 🚀 **Implementation Priority**

### **Phase 1: Essential Updates (Required)**
1. **Docker Compose**: Add notification environment variables
2. **Environment Template**: Create `.env.template` with notification variables
3. **Configuration Template**: Update `fogis-config.template.yaml` notification section

### **Phase 2: Integration Updates (Recommended)**
1. **Installation Scripts**: Add notification setup to `install_enhanced.sh`
2. **Validation Scripts**: Add notification validation to existing scripts
3. **Documentation**: Update deployment documentation

### **Phase 3: Advanced Features (Optional)**
1. **Monitoring Integration**: Add notification metrics to monitoring stack
2. **Backup Integration**: Include notification data in backup scripts
3. **Health Checks**: Add notification-specific health checks

## 📋 **Migration Path for Existing Deployments**

### **For Existing FOGIS Deployments:**

1. **Update Docker Compose:**
   ```bash
   # Backup current configuration
   cp docker-compose.yml docker-compose.yml.backup
   
   # Add notification environment variables to process-matches-service
   # (Manual edit required)
   ```

2. **Create Notification Configuration:**
   ```bash
   # Create notification config directory
   mkdir -p config/notifications
   
   # Copy configuration from container
   docker run --rm -v $(pwd)/config/notifications:/output \
       ghcr.io/pitchconnect/match-list-processor:latest \
       cp /app/config/notification_channels.yml /output/
   ```

3. **Setup Stakeholder Database:**
   ```bash
   # Copy stakeholder template
   docker run --rm -v $(pwd)/data/process-matches-service:/output \
       ghcr.io/pitchconnect/match-list-processor:latest \
       cp /app/config/stakeholders_template.json /output/stakeholders.json
   ```

4. **Configure Environment:**
   ```bash
   # Add notification variables to .env or docker-compose.yml
   echo "NOTIFICATION_SYSTEM_ENABLED=false" >> .env
   # Add other notification variables as needed
   ```

5. **Restart Services:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## 🔧 **Testing Integration**

### **Validate Notification Integration:**
```bash
# Test notification system setup
docker exec process-matches-service python scripts/setup_notifications.py --validate-only

# Test notification channels (dry run)
docker exec process-matches-service python scripts/test_notifications.py --dry-run

# Send test notification
docker exec process-matches-service python scripts/test_notifications.py --channel email
```

## 📊 **Success Metrics**

### **Integration Complete When:**
- ✅ Docker Compose includes all notification environment variables
- ✅ Configuration template includes comprehensive notification section
- ✅ Environment template exists with notification variables
- ✅ Installation scripts setup notification configuration
- ✅ Validation scripts test notification system
- ✅ Documentation references notification capabilities

---

**This integration ensures the comprehensive notification system implemented in match-list-processor is properly supported by the FOGIS deployment infrastructure.**
