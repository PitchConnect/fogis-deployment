#!/bin/bash

# FOGIS Notification System Test Script
# This script tests the notification system by running test notifications

set -e

echo "🧪 FOGIS Notification System Test"
echo "=================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found. Please configure your notification settings first."
    exit 1
fi

# Source environment variables
source .env

# Check if notifications are enabled
if [ "${NOTIFICATIONS_ENABLED}" != "true" ]; then
    echo "❌ Error: Notifications are not enabled. Set NOTIFICATIONS_ENABLED=true in .env"
    exit 1
fi

# Check if email is configured
if [ "${EMAIL_ENABLED}" != "true" ]; then
    echo "❌ Error: Email notifications are not enabled. Set EMAIL_ENABLED=true in .env"
    exit 1
fi

# Validate email configuration
if [ -z "${SMTP_USERNAME}" ] || [ -z "${SMTP_PASSWORD}" ]; then
    echo "❌ Error: Email configuration incomplete. Please set SMTP_USERNAME and SMTP_PASSWORD in .env"
    echo ""
    echo "📝 To configure email notifications:"
    echo "1. Edit the .env file"
    echo "2. Set SMTP_USERNAME to your email address"
    echo "3. Set SMTP_PASSWORD to your email password or app password"
    echo "4. Set SMTP_FROM to your sender email address"
    echo ""
    echo "Example for Gmail:"
    echo "SMTP_USERNAME=your-email@gmail.com"
    echo "SMTP_PASSWORD=your-app-password"
    echo "SMTP_FROM=fogis-notifications@yourcompany.com"
    exit 1
fi

echo "✅ Configuration validated"
echo ""

# Test 1: Check if match processor service is running
echo "🔍 Test 1: Checking if match processor service is running..."
if docker ps | grep -q "process-matches-service"; then
    echo "✅ Match processor service is running"
else
    echo "❌ Match processor service is not running. Starting services..."
    docker-compose up -d process-matches-service
    echo "⏳ Waiting for service to start..."
    sleep 10
fi

# Test 2: Check service health
echo ""
echo "🏥 Test 2: Checking service health..."
if curl -f http://localhost:9082/health/simple > /dev/null 2>&1; then
    echo "✅ Match processor service is healthy"
else
    echo "❌ Match processor service health check failed"
    echo "📋 Service logs:"
    docker logs process-matches-service --tail 20
fi

# Test 3: Run notification test inside container
echo ""
echo "📧 Test 3: Running notification system test..."
echo "This will send test notifications to: ${SMTP_USERNAME}"
echo ""

# Create a simple test script that can run in the container
echo "📝 Creating test script..."
cat > /tmp/simple-notification-test.py << 'EOF'
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def test_email_notification():
    """Test email notification directly."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_username)

    print(f"🔧 SMTP Configuration:")
    print(f"   Host: {smtp_host}")
    print(f"   Port: {smtp_port}")
    print(f"   Username: {smtp_username}")
    print(f"   From: {smtp_from}")
    print(f"   Password: {'*' * len(smtp_password) if smtp_password else 'NOT SET'}")

    if not smtp_username or not smtp_password:
        print("❌ SMTP credentials not configured")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_from
        msg['To'] = smtp_username
        msg['Subject'] = "[FOGIS TEST] Notification System Test"
        
        body = f"""
🧪 FOGIS Notification System Test

This is a test email to verify that the FOGIS notification system is working correctly.

Test Details:
- Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- SMTP Server: {smtp_host}:{smtp_port}
- From: {smtp_from}
- To: {smtp_username}

If you receive this email, your notification system is configured correctly! ✅

Next steps:
1. The system will now send notifications for match changes
2. You'll receive alerts for system health issues
3. Authentication failures will be reported automatically

Best regards,
FOGIS Notification System
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        print("📡 Connecting to SMTP server...")
        server = smtplib.SMTP(smtp_host, smtp_port)
        print("🔐 Starting TLS...")
        server.starttls()
        print("🔑 Logging in...")
        server.login(smtp_username, smtp_password)
        print("📧 Sending email...")
        text = msg.as_string()
        server.sendmail(smtp_from, smtp_username, text)
        server.quit()

        print("✅ Test email sent successfully!")
        return True

    except Exception as e:
        print(f"❌ Failed to send test email: {e}")
        import traceback
        print(f"📋 Full error details:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_email_notification()
EOF

# Verify the test script was created
if [ ! -f "/tmp/simple-notification-test.py" ]; then
    echo "❌ Failed to create test script"
    exit 1
fi

echo "✅ Test script created successfully"

# Copy the test script to the container
echo "📋 Copying test script to container..."
if docker cp /tmp/simple-notification-test.py process-matches-service:/tmp/simple-notification-test.py; then
    echo "✅ Test script copied to container"
else
    echo "❌ Failed to copy test script to container"
    exit 1
fi

# Run the test in the container with environment variables
echo "🚀 Running notification test in container..."
if docker exec -e SMTP_HOST="${SMTP_HOST}" \
              -e SMTP_PORT="${SMTP_PORT}" \
              -e SMTP_USERNAME="${SMTP_USERNAME}" \
              -e SMTP_PASSWORD="${SMTP_PASSWORD}" \
              -e SMTP_FROM="${SMTP_FROM}" \
              -e SMTP_USE_TLS="${SMTP_USE_TLS}" \
              process-matches-service python /tmp/simple-notification-test.py; then
    echo "✅ Notification test completed successfully!"
    echo ""
    echo "📬 Check your email (${SMTP_USERNAME}) for the test notification."
else
    echo "❌ Notification test failed"
    echo "📋 Container logs:"
    docker logs process-matches-service --tail 10
fi

echo ""
echo "🎉 Notification system test completed!"
echo ""
echo "📋 Summary:"
echo "- Configuration: ✅ Validated"
echo "- Service Health: ✅ Checked"
echo "- Email Test: ✅ Attempted"
echo ""
echo "📧 If you received the test email, your notification system is ready!"
echo ""
echo "🔄 To restart services with new configuration:"
echo "docker-compose down && docker-compose up -d"
echo ""
echo "📊 To view logs:"
echo "docker logs process-matches-service -f"

# Clean up
rm -f /tmp/simple-notification-test.py
