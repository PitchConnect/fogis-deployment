#!/usr/bin/env python3
"""
Basic test to verify the credential wizard can be imported and initialized.
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_wizard_import():
    """Test that the wizard can be imported."""
    try:
        from lib.credential_wizard import CredentialWizard
        print("✅ CredentialWizard import successful")
        return True
    except ImportError as e:
        print(f"❌ CredentialWizard import failed: {e}")
        return False

def test_wizard_initialization():
    """Test that the wizard can be initialized."""
    try:
        from lib.credential_wizard import CredentialWizard
        wizard = CredentialWizard()
        print("✅ CredentialWizard initialization successful")
        print(f"   - Config: {wizard.config}")
        print(f"   - OAuth manager: {wizard.oauth_manager}")
        print(f"   - Calendar manager: {wizard.calendar_manager}")
        print(f"   - FOGIS manager: {wizard.fogis_manager}")
        print(f"   - Storage: {wizard.storage}")
        print(f"   - Validator: {wizard.validator}")
        return True
    except Exception as e:
        print(f"❌ CredentialWizard initialization failed: {e}")
        return False

def test_oauth_manager_import():
    """Test that the OAuth manager can be imported."""
    try:
        from lib.google_oauth_manager import GoogleOAuthManager
        print("✅ GoogleOAuthManager import successful")
        return True
    except ImportError as e:
        print(f"❌ GoogleOAuthManager import failed: {e}")
        return False

def test_calendar_manager_import():
    """Test that the calendar manager can be imported."""
    try:
        from lib.calendar_manager import CalendarManager
        print("✅ CalendarManager import successful")
        return True
    except ImportError as e:
        print(f"❌ CalendarManager import failed: {e}")
        return False

def test_fogis_manager_import():
    """Test that the FOGIS manager can be imported."""
    try:
        from lib.fogis_auth_manager import FogisAuthManager
        print("✅ FogisAuthManager import successful")
        return True
    except ImportError as e:
        print(f"❌ FogisAuthManager import failed: {e}")
        return False

def test_secure_storage_import():
    """Test that the secure storage can be imported."""
    try:
        from lib.secure_storage import SecureCredentialStore
        print("✅ SecureCredentialStore import successful")
        return True
    except ImportError as e:
        print(f"❌ SecureCredentialStore import failed: {e}")
        return False

def test_validator_import():
    """Test that the validator can be imported."""
    try:
        from lib.credential_validator import CredentialValidator
        print("✅ CredentialValidator import successful")
        return True
    except ImportError as e:
        print(f"❌ CredentialValidator import failed: {e}")
        return False

def main():
    """Run all basic tests."""
    print("🧪 Running basic credential wizard tests...")
    print("=" * 50)
    
    tests = [
        test_wizard_import,
        test_oauth_manager_import,
        test_calendar_manager_import,
        test_fogis_manager_import,
        test_secure_storage_import,
        test_validator_import,
        test_wizard_initialization,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
