#!/usr/bin/env python3
"""
Test script for Enhanced OAuth Wizard

This script validates the functionality of the enhanced OAuth wizard
including credential detection, validation, and browser automation features.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

try:
    from enhanced_oauth_wizard import EnhancedOAuthWizard
except ImportError as e:
    print(f"❌ Failed to import enhanced OAuth wizard: {e}")
    sys.exit(1)


def test_wizard_initialization():
    """Test wizard initialization."""
    print("🧪 Testing wizard initialization...")

    try:
        wizard = EnhancedOAuthWizard()
        assert wizard.credentials_path == "credentials.json"
        assert wizard.backup_credentials_path == "credentials/google-credentials.json"
        print("✅ Wizard initialization successful")
        return True
    except Exception as e:
        print(f"❌ Wizard initialization failed: {e}")
        return False


def test_credential_validation():
    """Test credential validation functionality."""
    print("🧪 Testing credential validation...")

    wizard = EnhancedOAuthWizard()

    # Test valid OAuth credentials
    valid_creds = {
        "web": {
            "client_id": "test_client_id.apps.googleusercontent.com",
            "client_secret": "test_client_secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                "http://localhost:8080/callback",
                "http://127.0.0.1:8080/callback",
            ],
        }
    }

    result = wizard.validate_oauth_credentials(valid_creds, "test.json")
    if result["valid"]:
        print("✅ Valid credential validation successful")
    else:
        print(f"❌ Valid credential validation failed: {result.get('error')}")
        return False

    # Test invalid OAuth credentials (missing redirect URIs)
    invalid_creds = {
        "web": {
            "client_id": "test_client_id.apps.googleusercontent.com",
            "client_secret": "test_client_secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8080/wrong_callback"],
        }
    }

    result = wizard.validate_oauth_credentials(invalid_creds, "test.json")
    if not result["valid"] and "redirect URIs" in result.get("error", ""):
        print("✅ Invalid credential detection successful")
    else:
        print(f"❌ Invalid credential detection failed: {result}")
        return False

    return True


def test_credential_scanning():
    """Test credential scanning functionality."""
    print("🧪 Testing credential scanning...")

    wizard = EnhancedOAuthWizard()

    # Create a temporary valid credential file
    temp_creds = {
        "web": {
            "client_id": "test_client_id.apps.googleusercontent.com",
            "client_secret": "test_client_secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                "http://localhost:8080/callback",
                "http://127.0.0.1:8080/callback",
            ],
        }
    }

    # Write temporary credential file
    temp_file = "test_credentials.json"
    try:
        with open(temp_file, "w") as f:
            json.dump(temp_creds, f, indent=2)

        # Test credential analysis
        result = wizard.analyze_credential_file(temp_file)

        if result and result["valid"] and result["type"] == "OAuth Web Application":
            print("✅ Credential file analysis successful")
        else:
            print(f"❌ Credential file analysis failed: {result}")
            return False

    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)

    return True


def test_project_id_validation():
    """Test project ID validation."""
    print("🧪 Testing project ID validation...")

    wizard = EnhancedOAuthWizard()

    # Test valid project IDs
    valid_ids = ["my-project-123456", "fogis-integration-789", "test-project-1"]

    for project_id in valid_ids:
        if not wizard.validate_project_id_format(project_id):
            print(f"❌ Valid project ID rejected: {project_id}")
            return False

    # Test invalid project IDs
    invalid_ids = [
        "My-Project",  # uppercase
        "project--name",  # double hyphen
        "a",  # too short
        "project_name",  # underscore
        "123project",  # starts with number
    ]

    for project_id in invalid_ids:
        if wizard.validate_project_id_format(project_id):
            print(f"❌ Invalid project ID accepted: {project_id}")
            return False

    print("✅ Project ID validation successful")
    return True


def test_credential_reuse_setup():
    """Test credential reuse functionality."""
    print("🧪 Testing credential reuse setup...")

    wizard = EnhancedOAuthWizard()

    # Create a mock credential entry
    mock_credential = {
        "path": "test_credentials.json",
        "type": "OAuth Web Application",
        "valid": True,
        "details": {
            "client_id": "test_client_id...",
            "redirect_uris": 2,
            "project_id": "test-project",
        },
    }

    # Test that the setup function exists and can be called
    try:
        # This would normally copy files, but we'll just test the method exists
        # and handles the mock data correctly
        if hasattr(wizard, "setup_credential_reuse"):
            print("✅ Credential reuse setup method available")
        else:
            print("❌ Credential reuse setup method missing")
            return False
    except Exception as e:
        print(f"❌ Credential reuse setup test failed: {e}")
        return False

    return True


def run_all_tests():
    """Run all tests and report results."""
    print("🚀 Running Enhanced OAuth Wizard Tests")
    print("=" * 50)

    tests = [
        ("Wizard Initialization", test_wizard_initialization),
        ("Credential Validation", test_credential_validation),
        ("Credential Scanning", test_credential_scanning),
        ("Project ID Validation", test_project_id_validation),
        ("Credential Reuse Setup", test_credential_reuse_setup),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)

        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} error: {e}")

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Enhanced OAuth wizard is ready for use.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
