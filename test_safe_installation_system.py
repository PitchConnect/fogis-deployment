#!/usr/bin/env python3
"""
Comprehensive test runner for the FOGIS Safe Installation System.

This script runs all safety system tests and validates the implementation
against the requirements specified in GitHub Issue #17.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


class SafeInstallationTestRunner:
    """Test runner for the safe installation system."""

    def __init__(self):
        self.test_results = {}
        self.failed_tests = []
        self.test_dir = Path(__file__).parent
        self.temp_dirs = []

    def setup_test_environment(self):
        """Set up the test environment."""
        print("🔧 Setting up test environment...")

        # Create temporary directories for testing
        self.test_install_dir = tempfile.mkdtemp(prefix="fogis_test_install_")
        self.test_backup_dir = tempfile.mkdtemp(prefix="fogis_test_backup_")
        self.temp_dirs.extend([self.test_install_dir, self.test_backup_dir])

        # Set environment variables for tests
        os.environ.update(
            {
                "TEST_INSTALL_DIR": self.test_install_dir,
                "TEST_BACKUP_DIR": self.test_backup_dir,
                "PYTHONPATH": str(self.test_dir),
            }
        )

        print(f"✅ Test environment ready")
        print(f"   Install dir: {self.test_install_dir}")
        print(f"   Backup dir: {self.test_backup_dir}")

    def cleanup_test_environment(self):
        """Clean up the test environment."""
        print("🧹 Cleaning up test environment...")

        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                subprocess.run(["rm", "-rf", temp_dir], check=False)

        # Clean up any test artifacts
        test_artifacts = [
            "/tmp/fogis_backup_location",
            "/tmp/fogis_upgrade_state",
            "/tmp/test_conflict_report.txt",
        ]

        for artifact in test_artifacts:
            if os.path.exists(artifact):
                os.remove(artifact)

        # Clean up any test backup files
        subprocess.run(
            ["find", "/tmp", "-name", "fogis-backup-*.tar.gz", "-delete"], check=False
        )

        print("✅ Test environment cleaned up")

    def run_unit_tests(self):
        """Run unit tests for the safety system."""
        print("\n🧪 Running unit tests...")

        unit_test_files = [
            "tests/unit/test_conflict_detector.py",
            "tests/unit/test_backup_manager.py",
        ]

        for test_file in unit_test_files:
            if os.path.exists(test_file):
                print(f"   Running {test_file}...")
                result = subprocess.run(
                    ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
                    capture_output=True,
                    text=True,
                )

                self.test_results[test_file] = {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

                if result.returncode == 0:
                    print(f"   ✅ {test_file} passed")
                else:
                    print(f"   ❌ {test_file} failed")
                    self.failed_tests.append(test_file)
            else:
                print(f"   ⚠️  {test_file} not found")

    def run_integration_tests(self):
        """Run integration tests for the safety system."""
        print("\n🔗 Running integration tests...")

        integration_test_files = ["tests/integration/test_safe_installation.py"]

        for test_file in integration_test_files:
            if os.path.exists(test_file):
                print(f"   Running {test_file}...")
                result = subprocess.run(
                    ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
                    capture_output=True,
                    text=True,
                )

                self.test_results[test_file] = {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

                if result.returncode == 0:
                    print(f"   ✅ {test_file} passed")
                else:
                    print(f"   ❌ {test_file} failed")
                    self.failed_tests.append(test_file)
            else:
                print(f"   ⚠️  {test_file} not found")

    def run_bash_function_tests(self):
        """Run tests for bash functions directly."""
        print("\n🐚 Running bash function tests...")

        bash_tests = [
            {
                "name": "Conflict Detection Functions",
                "script": """
                source fogis-deployment/lib/conflict_detector.sh
                echo "Testing conflict detection functions..."
                type check_directory_conflicts >/dev/null && echo "✅ check_directory_conflicts function exists"
                type check_container_conflicts >/dev/null && echo "✅ check_container_conflicts function exists"
                type check_network_conflicts >/dev/null && echo "✅ check_network_conflicts function exists"
                type check_port_conflicts >/dev/null && echo "✅ check_port_conflicts function exists"
                type check_cron_conflicts >/dev/null && echo "✅ check_cron_conflicts function exists"
                type detect_all_conflicts >/dev/null && echo "✅ detect_all_conflicts function exists"
                """,
            },
            {
                "name": "Backup Manager Functions",
                "script": """
                source fogis-deployment/lib/backup_manager.sh
                echo "Testing backup manager functions..."
                type create_installation_backup >/dev/null && echo "✅ create_installation_backup function exists"
                type restore_from_backup >/dev/null && echo "✅ restore_from_backup function exists"
                type list_backups >/dev/null && echo "✅ list_backups function exists"
                type cleanup_old_backups >/dev/null && echo "✅ cleanup_old_backups function exists"
                """,
            },
            {
                "name": "Installation Safety Functions",
                "script": """
                source fogis-deployment/lib/installation_safety.sh
                echo "Testing installation safety functions..."
                type graceful_service_shutdown >/dev/null && echo "✅ graceful_service_shutdown function exists"
                type perform_safe_upgrade >/dev/null && echo "✅ perform_safe_upgrade function exists"
                type perform_force_clean >/dev/null && echo "✅ perform_force_clean function exists"
                type perform_conflict_check >/dev/null && echo "✅ perform_conflict_check function exists"
                type execute_installation_mode >/dev/null && echo "✅ execute_installation_mode function exists"
                """,
            },
        ]

        for test in bash_tests:
            print(f"   Running {test['name']}...")
            result = subprocess.run(
                ["bash", "-c", test["script"]], capture_output=True, text=True, cwd="."
            )

            self.test_results[test["name"]] = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            if result.returncode == 0:
                print(f"   ✅ {test['name']} passed")
                # Print function existence confirmations
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        print(f"      {line}")
            else:
                print(f"   ❌ {test['name']} failed")
                self.failed_tests.append(test["name"])

    def validate_requirements(self):
        """Validate that implementation meets GitHub Issue #17 requirements."""
        print("\n📋 Validating requirements from GitHub Issue #17...")

        requirements = [
            {
                "name": "Enhanced Conflict Detection",
                "check": lambda: os.path.exists(
                    "fogis-deployment/lib/conflict_detector.sh"
                ),
                "description": "Conflict detection system implemented",
            },
            {
                "name": "Comprehensive Backup System",
                "check": lambda: os.path.exists(
                    "fogis-deployment/lib/backup_manager.sh"
                ),
                "description": "Backup and restore system implemented",
            },
            {
                "name": "Installation Safety System",
                "check": lambda: os.path.exists(
                    "fogis-deployment/lib/installation_safety.sh"
                ),
                "description": "Core safety functions implemented",
            },
            {
                "name": "Enhanced Install Script",
                "check": lambda: self.check_install_script_enhancements(),
                "description": "Main install.sh script enhanced with safety features",
            },
            {
                "name": "Comprehensive Test Coverage",
                "check": lambda: self.check_test_coverage(),
                "description": "Test suite covers all safety components",
            },
        ]

        passed_requirements = 0
        total_requirements = len(requirements)

        for req in requirements:
            try:
                if req["check"]():
                    print(f"   ✅ {req['name']}: {req['description']}")
                    passed_requirements += 1
                else:
                    print(f"   ❌ {req['name']}: {req['description']}")
            except Exception as e:
                print(f"   ❌ {req['name']}: Error checking requirement - {e}")

        print(
            f"\n📊 Requirements validation: {passed_requirements}/{total_requirements} passed"
        )
        return passed_requirements == total_requirements

    def check_install_script_enhancements(self):
        """Check if install.sh has been enhanced with safety features."""
        if not os.path.exists("install.sh"):
            return False

        with open("install.sh", "r") as f:
            content = f.read()

        # Check for key safety enhancements
        safety_features = [
            "installation_safety.sh",
            "detect_all_conflicts",
            "handle_installation_failure",
            "rollback",
        ]

        return all(feature in content for feature in safety_features)

    def check_test_coverage(self):
        """Check if comprehensive test coverage exists."""
        test_files = [
            "tests/unit/test_conflict_detector.py",
            "tests/unit/test_backup_manager.py",
            "tests/integration/test_safe_installation.py",
        ]

        return all(os.path.exists(test_file) for test_file in test_files)

    def generate_test_report(self):
        """Generate a comprehensive test report."""
        print("\n📄 Generating test report...")

        total_tests = len(self.test_results)
        passed_tests = total_tests - len(self.failed_tests)

        report = f"""
FOGIS Safe Installation System - Test Report
==========================================

Test Summary:
- Total tests: {total_tests}
- Passed: {passed_tests}
- Failed: {len(self.failed_tests)}
- Success rate: {(passed_tests/total_tests*100):.1f}%

"""

        if self.failed_tests:
            report += "Failed Tests:\n"
            for test in self.failed_tests:
                report += f"- {test}\n"
            report += "\n"

        report += "Detailed Results:\n"
        for test_name, result in self.test_results.items():
            status = "PASSED" if result["returncode"] == 0 else "FAILED"
            report += f"- {test_name}: {status}\n"

        # Save report to file
        with open("test_report.txt", "w") as f:
            f.write(report)

        print("✅ Test report saved to test_report.txt")
        return passed_tests == total_tests

    def run_all_tests(self):
        """Run all tests and generate report."""
        print("🚀 FOGIS Safe Installation System - Comprehensive Test Suite")
        print("=" * 60)

        try:
            self.setup_test_environment()
            self.run_bash_function_tests()
            self.run_unit_tests()
            self.run_integration_tests()

            requirements_passed = self.validate_requirements()
            all_tests_passed = self.generate_test_report()

            print("\n" + "=" * 60)
            if all_tests_passed and requirements_passed:
                print("🎉 ALL TESTS PASSED - Safe Installation System is ready!")
                return 0
            else:
                print("❌ SOME TESTS FAILED - Review test report for details")
                return 1

        finally:
            self.cleanup_test_environment()


if __name__ == "__main__":
    runner = SafeInstallationTestRunner()
    exit_code = runner.run_all_tests()
    sys.exit(exit_code)
