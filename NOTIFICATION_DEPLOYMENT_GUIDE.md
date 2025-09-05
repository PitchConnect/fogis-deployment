# FOGIS Notification System Deployment Guide

This guide provides step-by-step instructions for deploying the FOGIS notification system in production.

## 📋 Prerequisites

- FOGIS deployment is running and healthy
- Email account with SMTP access (Gmail recommended)
- Access to modify environment variables
- Docker and docker-compose installed

## 🔧 Configuration Steps

### Step 1: Configure Email Settings

1. **Edit the `.env` file** in the `fogis-deployment` directory:

```bash
cd fogis-deployment
nano .env
```

2. **Update the notification settings** with your email configuration:

```bash
# Notification System Configuration
NOTIFICATIONS_ENABLED=true

# Email Configuration (Primary notification channel)
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=fogis-notifications@yourcompany.com
SMTP_USE_TLS=true

# Discord Configuration (Optional)
DISCORD_ENABLED=false
DISCORD_WEBHOOK_URL=
DISCORD_BOT_USERNAME=FOGIS Match Bot

# Webhook Configuration (Optional)
WEBHOOK_ENABLED=false
WEBHOOK_URL=
WEBHOOK_AUTH_TOKEN=
```

### Step 2: Gmail App Password Setup (if using Gmail)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate an App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
   - Use this password as `SMTP_PASSWORD`

### Step 3: Update Stakeholder Information

1. **Edit the stakeholder configuration**:

```bash
nano data/stakeholders.json
```

2. **Update your email address** in the stakeholder configuration:

```json
{
  "stakeholders": {
    "bartek-svaberg": {
      "stakeholder_id": "bartek-svaberg",
      "name": "Bartek Svaberg",
      "role": "Referee",
      "email": "your-actual-email@gmail.com",
      "contact_info": {
        "email": {
          "address": "your-actual-email@gmail.com",
          "verified": true,
          "primary": true
        }
      }
    }
  }
}
```

## 🚀 Deployment Commands

### Step 1: Test Configuration

```bash
# Run the notification test script
./test-notifications.sh
```

This will:
- Validate your configuration
- Check service health
- Send a test email notification

### Step 2: Deploy Services

```bash
# Stop services
docker-compose down

# Start services with new configuration
docker-compose up -d

# Check service status
docker-compose ps
```

### Step 3: Verify Deployment

```bash
# Check logs for notification system
docker logs process-matches-service | grep -i notification

# Check Grafana alerts
docker logs fogis-grafana | grep -i alert

# Monitor service health
docker logs process-matches-service -f
```

## 📧 Notification Types You'll Receive

### 1. System Health Alerts
- **Service Down**: When FOGIS services stop responding
- **Authentication Failures**: When FOGIS login fails
- **OAuth Issues**: When Google API access fails
- **Processing Errors**: When match processing encounters issues

### 2. Match Change Notifications
- **New Assignments**: When you're assigned to new matches
- **Schedule Changes**: When match times or venues change
- **Cancellations**: When matches are cancelled
- **Assignment Updates**: When your role changes

### 3. Critical System Alerts
- **Database Issues**: When data storage fails
- **API Failures**: When external APIs are unavailable
- **Configuration Errors**: When system configuration is invalid

## 🔍 Monitoring and Troubleshooting

### Check Notification System Status

```bash
# View notification service logs
docker logs process-matches-service | grep -i notification

# Check email delivery status
docker exec process-matches-service cat /app/data/notification_analytics.json

# View stakeholder configuration
docker exec process-matches-service cat /app/data/stakeholders.json
```

### Common Issues and Solutions

#### 1. Email Not Sending

**Problem**: Test email fails to send

**Solutions**:
- Verify SMTP credentials in `.env`
- Check if Gmail App Password is correct
- Ensure 2FA is enabled on Gmail account
- Check firewall/network restrictions

#### 2. No Match Notifications

**Problem**: Not receiving match change notifications

**Solutions**:
- Verify stakeholder configuration has correct email
- Check if match processing service is running
- Verify notification preferences in stakeholder config
- Check service logs for processing errors

#### 3. Too Many Notifications

**Problem**: Receiving too many notifications

**Solutions**:
- Adjust notification preferences in stakeholder config
- Modify alert thresholds in Grafana configuration
- Enable quiet hours in notification preferences

### Log Locations

- **Notification Service**: `docker logs process-matches-service`
- **Grafana Alerts**: `docker logs fogis-grafana`
- **Email Delivery**: `/app/data/notification_analytics.json`
- **System Health**: `docker logs fogis-api-client-service`

## 🔄 Maintenance

### Regular Tasks

1. **Monitor notification delivery rates**
2. **Review and update stakeholder preferences**
3. **Check email account storage limits**
4. **Update alert thresholds based on system behavior**

### Monthly Tasks

1. **Review notification analytics**
2. **Update stakeholder contact information**
3. **Test notification channels**
4. **Review and optimize alert rules**

## 📞 Support

If you encounter issues:

1. **Check the logs** using the commands above
2. **Run the test script** to verify configuration
3. **Review this guide** for common solutions
4. **Check the FOGIS deployment documentation**

## 🎉 Success Indicators

You'll know the notification system is working when:

- ✅ Test email is received successfully
- ✅ Service logs show "Notification service initialized"
- ✅ Match processing logs show notification delivery
- ✅ You receive alerts for any system issues
- ✅ Match change notifications arrive promptly

The notification system will now automatically keep you informed about your referee assignments and any system issues that require attention!
