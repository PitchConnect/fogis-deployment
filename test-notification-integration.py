#!/usr/bin/env python3
"""
Advanced notification system integration test.
This script tests the full notification system including stakeholder management.
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_stakeholder_configuration():
    """Test stakeholder configuration file."""
    stakeholder_file = Path("data/stakeholders.json")
    
    if not stakeholder_file.exists():
        logger.error(f"❌ Stakeholder file not found: {stakeholder_file}")
        return False
    
    try:
        with open(stakeholder_file, 'r') as f:
            stakeholders = json.load(f)
        
        logger.info("✅ Stakeholder configuration loaded successfully")
        
        # Check for required stakeholders
        required_stakeholders = ["bartek-svaberg", "system-admin"]
        for stakeholder_id in required_stakeholders:
            if stakeholder_id in stakeholders.get("stakeholders", {}):
                stakeholder = stakeholders["stakeholders"][stakeholder_id]
                email = stakeholder.get("contact_info", {}).get("email", {}).get("address")
                logger.info(f"✅ Found stakeholder: {stakeholder.get('name')} ({email})")
            else:
                logger.warning(f"⚠️ Missing stakeholder: {stakeholder_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load stakeholder configuration: {e}")
        return False


def test_notification_channels_config():
    """Test notification channels configuration."""
    config_file = Path("../match-list-processor/config/notification_channels.yml")
    
    if not config_file.exists():
        logger.error(f"❌ Notification channels config not found: {config_file}")
        return False
    
    try:
        import yaml
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info("✅ Notification channels configuration loaded")
        
        # Check email configuration
        email_config = config.get("email", {})
        if email_config.get("enabled"):
            logger.info("✅ Email notifications enabled")
        else:
            logger.warning("⚠️ Email notifications disabled")
        
        return True
        
    except ImportError:
        logger.warning("⚠️ PyYAML not available, skipping YAML config test")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to load notification channels config: {e}")
        return False


def load_env_file():
    """Load environment variables from .env file."""
    env_file = Path(".env")
    if not env_file.exists():
        logger.warning("⚠️ .env file not found")
        return False

    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"').strip("'")
                    os.environ[key] = value

        logger.info("✅ Environment variables loaded from .env file")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to load .env file: {e}")
        return False


def test_environment_variables():
    """Test notification environment variables."""
    # First try to load from .env file
    load_env_file()

    required_vars = [
        "NOTIFICATIONS_ENABLED",
        "EMAIL_ENABLED",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_FROM"
    ]

    logger.info("🔧 Checking environment variables...")

    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if "PASSWORD" in var:
                logger.info(f"✅ {var}: {'*' * len(value)}")
            else:
                logger.info(f"✅ {var}: {value}")
        else:
            missing_vars.append(var)
            logger.error(f"❌ {var}: NOT SET")

    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        return False

    return True


def test_docker_container_access():
    """Test Docker container access and notification system."""
    import subprocess
    
    try:
        # Check if container is running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=process-matches-service", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if "process-matches-service" not in result.stdout:
            logger.error("❌ process-matches-service container not running")
            return False
        
        logger.info("✅ process-matches-service container is running")
        
        # Test container health
        result = subprocess.run(
            ["docker", "exec", "process-matches-service", "curl", "-f", "http://localhost:8000/health/simple"],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("✅ Container health check passed")
        
        # Check if notification system files exist in container
        result = subprocess.run(
            ["docker", "exec", "process-matches-service", "ls", "-la", "/app/data/"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if "stakeholders.json" in result.stdout:
            logger.info("✅ Stakeholder configuration found in container")
        else:
            logger.warning("⚠️ Stakeholder configuration not found in container")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Docker container test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing container: {e}")
        return False


def test_notification_system_import():
    """Test if notification system can be imported in container."""
    import subprocess
    
    test_script = '''
import sys
sys.path.append("/app")

try:
    from src.notifications.notification_service import NotificationService
    print("✅ NotificationService imported successfully")
    
    from src.notifications.models.notification_models import ChangeNotification
    print("✅ ChangeNotification imported successfully")
    
    from src.notifications.stakeholders.stakeholder_manager import StakeholderManager
    print("✅ StakeholderManager imported successfully")
    
    print("✅ All notification system components available")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
'''
    
    try:
        # Write test script to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            temp_script = f.name
        
        # Copy to container
        subprocess.run(
            ["docker", "cp", temp_script, "process-matches-service:/tmp/test_imports.py"],
            check=True
        )
        
        # Run test in container
        result = subprocess.run(
            ["docker", "exec", "process-matches-service", "python", "/tmp/test_imports.py"],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("✅ Notification system imports test passed")
        logger.info(result.stdout)
        
        # Clean up
        os.unlink(temp_script)
        subprocess.run(
            ["docker", "exec", "process-matches-service", "rm", "/tmp/test_imports.py"],
            check=True
        )
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Import test failed: {e}")
        if e.stdout:
            logger.error(f"stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in import test: {e}")
        return False


def main():
    """Run all notification system tests."""
    logger.info("🧪 Starting comprehensive notification system test...")
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Stakeholder Configuration", test_stakeholder_configuration),
        ("Notification Channels Config", test_notification_channels_config),
        ("Docker Container Access", test_docker_container_access),
        ("Notification System Imports", test_notification_system_import),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running test: {test_name}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ Test {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n📋 Test Results Summary:")
    logger.info("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} {test_name}")
        if result:
            passed += 1
    
    logger.info("=" * 50)
    logger.info(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Notification system is ready.")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
