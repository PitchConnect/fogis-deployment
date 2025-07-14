#!/usr/bin/env python3
"""
Test suite for FOGIS One-Click Setup System

This test suite verifies that all components of the one-click setup system
work correctly, including the platform manager, setup script, and web installer.

Usage:
    python3 test_one_click_setup.py
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class TestPlatformManager(unittest.TestCase):
    """Test the platform manager functionality."""

    def setUp(self):
        """Set up test environment."""
        # Import here to avoid issues if platform_manager doesn't exist
        try:
            from platform_manager import MultiPlatformManager, PlatformInfo

            self.MultiPlatformManager = MultiPlatformManager
            self.PlatformInfo = PlatformInfo
        except ImportError:
            self.skipTest("platform_manager module not available")

    def test_platform_detection(self):
        """Test platform detection works."""
        manager = self.MultiPlatformManager()
        platform_info = manager.detect_platform()

        self.assertIsNotNone(platform_info)
        self.assertIsNotNone(platform_info.os_name)
        self.assertIsNotNone(platform_info.distribution)
        self.assertIsNotNone(platform_info.architecture)
        self.assertIsNotNone(platform_info.package_manager)

    def test_package_name_resolution(self):
        """Test package name resolution."""
        manager = self.MultiPlatformManager()
        manager.detect_platform()

        # Test core packages
        git_package = manager.resolve_package_name("git")
        docker_package = manager.resolve_package_name("docker")
        python_package = manager.resolve_package_name("python3")

        self.assertIsNotNone(git_package)
        self.assertIsNotNone(docker_package)
        self.assertIsNotNone(python_package)

    def test_prerequisite_verification(self):
        """Test prerequisite verification."""
        manager = self.MultiPlatformManager()
        prereqs = manager.verify_prerequisites(["git", "python3"])

        self.assertIsInstance(prereqs, dict)
        self.assertIn("git", prereqs)
        self.assertIn("python3", prereqs)


class TestSetupScript(unittest.TestCase):
    """Test the setup script functionality."""

    def setUp(self):
        """Set up test environment."""
        self.script_path = Path("fogis-deployment/setup_fogis_system.sh")
        if not self.script_path.exists():
            self.skipTest("Setup script not found")

    def test_help_option(self):
        """Test that help option works."""
        result = subprocess.run(
            [str(self.script_path), "--help"], capture_output=True, text=True
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("FOGIS One-Click Setup System", result.stdout)
        self.assertIn("--auto", result.stdout)
        self.assertIn("--verbose", result.stdout)
        self.assertIn("--resume", result.stdout)
        self.assertIn("--rollback", result.stdout)

    def test_script_is_executable(self):
        """Test that the script is executable."""
        self.assertTrue(os.access(self.script_path, os.X_OK))

    def test_rollback_option(self):
        """Test rollback functionality."""
        # Create a temporary progress file
        progress_file = Path("fogis-deployment/.setup_progress")
        progress_file.write_text("test_progress")

        try:
            result = subprocess.run(
                [str(self.script_path), "--rollback"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Should complete successfully
            self.assertEqual(result.returncode, 0)
            self.assertIn("Rollback completed", result.stdout)

        finally:
            # Clean up
            if progress_file.exists():
                progress_file.unlink()


class TestWebInstaller(unittest.TestCase):
    """Test the web installer functionality."""

    def setUp(self):
        """Set up test environment."""
        self.installer_path = Path("install.sh")
        if not self.installer_path.exists():
            self.skipTest("Web installer not found")

    def test_installer_is_executable(self):
        """Test that the installer is executable."""
        self.assertTrue(os.access(self.installer_path, os.X_OK))

    def test_installer_has_correct_shebang(self):
        """Test that the installer has correct shebang."""
        with open(self.installer_path, "r") as f:
            first_line = f.readline().strip()

        self.assertEqual(first_line, "#!/bin/bash")


class TestInstallFogisScript(unittest.TestCase):
    """Test the install-fogis.py script."""

    def setUp(self):
        """Set up test environment."""
        self.script_path = Path("install-fogis.py")
        if not self.script_path.exists():
            self.skipTest("install-fogis.py script not found")

    def test_help_option(self):
        """Test that help option works."""
        result = subprocess.run(
            ["python3", str(self.script_path), "--help"], capture_output=True, text=True
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("FOGIS Multi-Platform Installation System", result.stdout)
        self.assertIn("--install-prereqs", result.stdout)
        self.assertIn("--skip-prereqs", result.stdout)
        self.assertIn("--verbose", result.stdout)

    def test_prerequisite_check(self):
        """Test prerequisite checking."""
        result = subprocess.run(
            ["python3", str(self.script_path), "--skip-prereqs"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("Installation Complete", result.stdout)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""

    def test_all_scripts_exist(self):
        """Test that all required scripts exist."""
        required_files = [
            "platform_manager.py",
            "install-fogis.py",
            "install.sh",
            "fogis-deployment/setup_fogis_system.sh",
            "fogis-deployment/manage_fogis_system.sh",
        ]

        for file_path in required_files:
            with self.subTest(file=file_path):
                self.assertTrue(Path(file_path).exists(), f"Missing file: {file_path}")

    def test_python_imports(self):
        """Test that Python modules can be imported."""
        try:
            import platform_manager

            self.assertTrue(hasattr(platform_manager, "MultiPlatformManager"))
            self.assertTrue(hasattr(platform_manager, "PlatformInfo"))
        except ImportError as e:
            self.fail(f"Failed to import platform_manager: {e}")

    def test_setup_script_syntax(self):
        """Test that setup script has valid bash syntax."""
        result = subprocess.run(
            ["bash", "-n", "fogis-deployment/setup_fogis_system.sh"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, f"Bash syntax error: {result.stderr}")

    def test_web_installer_syntax(self):
        """Test that web installer has valid bash syntax."""
        result = subprocess.run(
            ["bash", "-n", "install.sh"], capture_output=True, text=True
        )

        self.assertEqual(result.returncode, 0, f"Bash syntax error: {result.stderr}")


def run_tests():
    """Run all tests and return results."""
    print("🧪 FOGIS One-Click Setup Test Suite")
    print("===================================")
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestPlatformManager,
        TestSetupScript,
        TestWebInstaller,
        TestInstallFogisScript,
        TestIntegration,
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print()
    print("📊 Test Summary")
    print("===============")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")

    if result.errors:
        print("\n🚨 Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")

    success = len(result.failures) == 0 and len(result.errors) == 0

    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")

    return success


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
