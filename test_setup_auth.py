#!/usr/bin/env python3
"""
Test script to verify the setup-auth command works correctly.
"""

import os
import subprocess
import sys


def test_setup_auth_command():
    """Test the setup-auth command."""
    print("🧪 Testing setup-auth command...")

    try:
        # Test the command with 'n' input to decline setup
        result = subprocess.run(
            ["./manage_fogis_system.sh", "setup-auth"],
            input="n\n",
            text=True,
            capture_output=True,
            timeout=10,
        )

        if result.returncode == 0:
            print("✅ setup-auth command executed successfully")

            # Check for expected output
            if "FOGIS Credential Setup Wizard" in result.stdout:
                print("✅ Wizard welcome screen displayed")
            else:
                print("❌ Wizard welcome screen not found")
                return False

            if "Setup cancelled" in result.stdout:
                print("✅ User cancellation handled correctly")
            else:
                print("❌ User cancellation not handled")
                return False

            return True
        else:
            print(f"❌ setup-auth command failed with return code: {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ setup-auth command timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing setup-auth command: {e}")
        return False


def test_manage_script_help():
    """Test that the manage script shows the setup-auth option."""
    print("\n🧪 Testing manage script help...")

    try:
        result = subprocess.run(
            ["./manage_fogis_system.sh"], capture_output=True, text=True, timeout=5
        )

        if "setup-auth" in result.stdout:
            print("✅ setup-auth option shown in help")
            return True
        else:
            print("❌ setup-auth option not found in help")
            print(f"STDOUT: {result.stdout}")
            return False

    except Exception as e:
        print(f"❌ Error testing manage script help: {e}")
        return False


def test_minimal_wizard_direct():
    """Test the minimal wizard directly."""
    print("\n🧪 Testing minimal wizard directly...")

    try:
        result = subprocess.run(
            ["python3", "lib/minimal_wizard.py"],
            input="n\n",
            text=True,
            capture_output=True,
            timeout=10,
        )

        if result.returncode == 0:
            print("✅ Minimal wizard executed successfully")

            if "FOGIS Credential Setup Wizard" in result.stdout:
                print("✅ Minimal wizard welcome screen displayed")
                return True
            else:
                print("❌ Minimal wizard welcome screen not found")
                return False
        else:
            print(f"❌ Minimal wizard failed with return code: {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error testing minimal wizard: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Testing FOGIS Credential Setup Wizard")
    print("=" * 50)

    tests = [
        test_manage_script_help,
        test_minimal_wizard_direct,
        test_setup_auth_command,
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
        print("🎉 All tests passed! The credential wizard is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
