#!/usr/bin/env python3
"""
Integration tests for FOGIS management script commands.
Tests the new update, version, and check-updates functionality.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ManagementCommandTester:
    """Test suite for FOGIS management script commands."""

    def __init__(self):
        self.script_path = Path("./manage_fogis_system.sh")
        self.test_results = []
        self.services = [
            "fogis-api-client-service",
            "team-logo-combiner",
            "match-list-processor",
            "match-list-change-detector",
            "fogis-calendar-phonebook-sync",
            "google-drive-service",
        ]

    def run_command(
        self, command: List[str], timeout: int = 30
    ) -> Tuple[int, str, str]:
        """Run a shell command and return exit code, stdout, stderr."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=Path(__file__).parent,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return -1, "", str(e)

    def test_script_exists(self) -> bool:
        """Test that the management script exists and is executable."""
        print("🔍 Testing script existence and permissions...")

        if not self.script_path.exists():
            print(f"❌ Script not found: {self.script_path}")
            return False

        if not os.access(self.script_path, os.X_OK):
            print(f"❌ Script not executable: {self.script_path}")
            return False

        print("✅ Management script exists and is executable")
        return True

    def test_help_command(self) -> bool:
        """Test the help command shows new update-related commands."""
        print("🔍 Testing help command...")

        exit_code, stdout, stderr = self.run_command(
            ["bash", str(self.script_path), "--help"]
        )

        if exit_code != 0:
            print(f"❌ Help command failed: {stderr}")
            print(f"   Command: bash {self.script_path} --help")
            return False

        required_commands = ["check-updates", "update", "version", "rollback"]
        missing_commands = []

        for cmd in required_commands:
            if cmd not in stdout:
                missing_commands.append(cmd)

        if missing_commands:
            print(f"❌ Missing commands in help: {missing_commands}")
            return False

        print("✅ Help command shows all new update commands")
        return True

    def test_version_command(self) -> bool:
        """Test the version command functionality."""
        print("🔍 Testing version command...")

        exit_code, stdout, stderr = self.run_command(
            ["bash", str(self.script_path), "version"]
        )

        if exit_code != 0:
            print(f"❌ Version command failed: {stderr}")
            return False

        # Check if output contains service information (allow for "not found" messages)
        if "service" not in stdout.lower():
            print(f"❌ Version output doesn't contain expected service information")
            print(f"Output: {stdout}")
            return False

        print("✅ Version command works correctly")
        return True

    def test_check_updates_command(self) -> bool:
        """Test the check-updates command functionality."""
        print("🔍 Testing check-updates command...")

        exit_code, stdout, stderr = self.run_command(
            ["bash", str(self.script_path), "check-updates"], timeout=60
        )

        # Command may return 0 (no updates) or 1 (updates available) - both are valid
        if exit_code not in [0, 1]:
            print(f"❌ Check-updates command failed unexpectedly: {stderr}")
            return False

        # Check if output contains expected update information
        expected_phrases = ["checking", "update", "service"]
        found_phrases = sum(
            1 for phrase in expected_phrases if phrase.lower() in stdout.lower()
        )

        if found_phrases < 2:
            print(f"❌ Check-updates output doesn't contain expected information")
            print(f"Output: {stdout}")
            return False

        if exit_code == 0:
            print("✅ Check-updates command works - no updates available")
        else:
            print("✅ Check-updates command works - updates available")

        return True

    def test_rollback_command(self) -> bool:
        """Test the rollback command provides guidance."""
        print("🔍 Testing rollback command...")

        exit_code, stdout, stderr = self.run_command(
            ["bash", str(self.script_path), "rollback"]
        )

        if exit_code != 0:
            print(f"❌ Rollback command failed: {stderr}")
            return False

        # Check if output contains rollback guidance
        expected_terms = ["rollback", "version", "docker"]
        found_terms = sum(
            1 for term in expected_terms if term.lower() in stdout.lower()
        )

        if found_terms < 2:
            print(f"❌ Rollback output doesn't contain expected guidance")
            print(f"Output: {stdout}")
            return False

        print("✅ Rollback command provides proper guidance")
        return True

    def test_docker_availability(self) -> bool:
        """Test that Docker is available for testing."""
        print("🔍 Testing Docker availability...")

        exit_code, stdout, stderr = self.run_command(["docker", "--version"])

        if exit_code != 0:
            print(f"❌ Docker not available: {stderr}")
            return False

        print(f"✅ Docker available: {stdout.strip()}")
        return True

    def test_docker_compose_availability(self) -> bool:
        """Test that Docker Compose is available."""
        print("🔍 Testing Docker Compose availability...")

        exit_code, stdout, stderr = self.run_command(["docker-compose", "--version"])

        if exit_code != 0:
            print(f"❌ Docker Compose not available: {stderr}")
            return False

        print(f"✅ Docker Compose available: {stdout.strip()}")
        return True

    def run_all_tests(self) -> bool:
        """Run all integration tests."""
        print("🧪 FOGIS Management Commands Integration Test")
        print("=" * 50)

        tests = [
            ("Script Existence", self.test_script_exists),
            ("Docker Availability", self.test_docker_availability),
            ("Docker Compose Availability", self.test_docker_compose_availability),
            ("Help Command", self.test_help_command),
            ("Version Command", self.test_version_command),
            ("Check Updates Command", self.test_check_updates_command),
            ("Rollback Command", self.test_rollback_command),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            print(f"\n📋 Running: {test_name}")
            try:
                if test_func():
                    passed += 1
                    self.test_results.append((test_name, "PASS", ""))
                else:
                    self.test_results.append(
                        (test_name, "FAIL", "Test function returned False")
                    )
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                self.test_results.append((test_name, "ERROR", str(e)))

        print(f"\n📊 Test Results: {passed}/{total} tests passed")

        # Print detailed results
        print("\n📋 Detailed Results:")
        for test_name, status, error in self.test_results:
            status_emoji = "✅" if status == "PASS" else "❌"
            print(f"{status_emoji} {test_name}: {status}")
            if error:
                print(f"   Error: {error}")

        return passed == total


def main():
    """Main test execution."""
    tester = ManagementCommandTester()

    if tester.run_all_tests():
        print("\n🎉 All integration tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some integration tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
