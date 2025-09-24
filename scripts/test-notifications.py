#!/usr/bin/env python3
"""
Test script for FOGIS notification system.
This script tests all configured notification channels to ensure they work correctly.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add the match-list-processor to the path
sys.path.append('/app')

from src.notifications.notification_service import NotificationService
from src.notifications.models.notification_models import (
    ChangeNotification,
    NotificationChannel,
    NotificationPriority,
    NotificationRecipient
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_test_config() -> Dict[str, Any]:
    """Load test configuration from environment variables."""
    return {
        "enabled": True,
        "stakeholder_storage_path": "/app/data/stakeholders.json",
        "analytics_storage_path": "/app/data/notification_analytics.json",
        "channels": {
            "email": {
                "enabled": os.getenv("EMAIL_ENABLED", "false").lower() == "true",
                "smtp_server": os.getenv("SMTP_HOST", "smtp.gmail.com"),
                "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                "smtp_username": os.getenv("SMTP_USERNAME", ""),
                "smtp_password": os.getenv("SMTP_PASSWORD", ""),
                "email_from": os.getenv("SMTP_FROM", ""),
                "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            },
            "discord": {
                "enabled": os.getenv("DISCORD_ENABLED", "false").lower() == "true",
                "webhook_url": os.getenv("DISCORD_WEBHOOK_URL", ""),
                "bot_username": os.getenv("DISCORD_BOT_USERNAME", "FOGIS Test Bot"),
            }
        }
    }


def create_test_notification() -> ChangeNotification:
    """Create a test notification for system testing."""
    recipient = NotificationRecipient(
        stakeholder_id="bartek-svaberg",
        name="Bartek Svaberg",
        channels=[NotificationChannel.EMAIL]
    )
    
    return ChangeNotification(
        notification_id="test-notification-001",
        title="🧪 FOGIS Notification System Test",
        message="This is a test notification to verify that the FOGIS notification system is working correctly.",
        priority=NotificationPriority.MEDIUM,
        recipients=[recipient],
        metadata={
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "test_type": "system_verification"
        }
    )


def create_test_match_change_notification() -> ChangeNotification:
    """Create a test match change notification."""
    recipient = NotificationRecipient(
        stakeholder_id="bartek-svaberg",
        name="Bartek Svaberg",
        channels=[NotificationChannel.EMAIL]
    )
    
    return ChangeNotification(
        notification_id="test-match-change-001",
        title="⚽ Test Match Assignment Change",
        message="""
🏟️ **Match Assignment Update**

**Match:** Test Team A vs Test Team B
**Date:** 2025-09-06 15:00
**Venue:** Test Stadium
**Role:** Referee

**Change:** This is a test notification for match assignment changes.

This notification confirms that match change alerts are working correctly.
        """.strip(),
        priority=NotificationPriority.HIGH,
        recipients=[recipient],
        metadata={
            "test": True,
            "match_id": "test-match-001",
            "change_type": "assignment",
            "timestamp": datetime.now().isoformat()
        }
    )


def create_test_system_alert() -> ChangeNotification:
    """Create a test system alert notification."""
    recipient = NotificationRecipient(
        stakeholder_id="system-admin",
        name="System Administrator",
        channels=[NotificationChannel.EMAIL]
    )
    
    return ChangeNotification(
        notification_id="test-system-alert-001",
        title="🚨 Test System Alert",
        message="""
⚠️ **System Health Test Alert**

**Component:** Notification System
**Status:** Testing
**Time:** {timestamp}

**Description:** This is a test system alert to verify that critical system notifications are working correctly.

**Action Required:** No action required - this is a test.

**Next Steps:** If you receive this notification, the system alert mechanism is functioning properly.
        """.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        priority=NotificationPriority.CRITICAL,
        recipients=[recipient],
        metadata={
            "test": True,
            "alert_type": "system_health",
            "component": "notification_system",
            "timestamp": datetime.now().isoformat()
        }
    )


async def test_notification_system():
    """Test the notification system with various notification types."""
    logger.info("🧪 Starting FOGIS notification system test...")
    
    # Load configuration
    config = load_test_config()
    logger.info(f"Configuration loaded: {json.dumps(config, indent=2, default=str)}")
    
    # Initialize notification service
    notification_service = NotificationService(config)
    
    # Test 1: Basic system test notification
    logger.info("📧 Test 1: Sending basic system test notification...")
    test_notification = create_test_notification()
    try:
        results = await notification_service._send_notifications([test_notification])
        logger.info(f"✅ Basic test notification sent. Results: {results}")
    except Exception as e:
        logger.error(f"❌ Basic test notification failed: {e}")
    
    # Test 2: Match change notification
    logger.info("⚽ Test 2: Sending match change test notification...")
    match_notification = create_test_match_change_notification()
    try:
        results = await notification_service._send_notifications([match_notification])
        logger.info(f"✅ Match change test notification sent. Results: {results}")
    except Exception as e:
        logger.error(f"❌ Match change test notification failed: {e}")
    
    # Test 3: System alert notification
    logger.info("🚨 Test 3: Sending system alert test notification...")
    alert_notification = create_test_system_alert()
    try:
        results = await notification_service._send_notifications([alert_notification])
        logger.info(f"✅ System alert test notification sent. Results: {results}")
    except Exception as e:
        logger.error(f"❌ System alert test notification failed: {e}")
    
    # Get system statistics
    logger.info("📊 Getting notification system statistics...")
    try:
        stats = notification_service.stakeholder_manager.get_statistics()
        logger.info(f"📈 Stakeholder statistics: {stats}")
        
        broadcaster_stats = notification_service.broadcaster.get_delivery_statistics()
        logger.info(f"📈 Broadcaster statistics: {broadcaster_stats}")
    except Exception as e:
        logger.error(f"❌ Failed to get statistics: {e}")
    
    logger.info("🎉 FOGIS notification system test completed!")


if __name__ == "__main__":
    asyncio.run(test_notification_system())
