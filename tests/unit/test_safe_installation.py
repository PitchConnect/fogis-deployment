"""
Integration tests for the FOGIS Safe Installation System.

This module contains comprehensive integration tests for the complete
safe installation workflow, including conflict detection, backup creation,
installation modes, and rollback scenarios.
"""

import os
import subprocess
import tempfile
import time
from unittest.mock import patch

import pytest


class TestSafeInstallationIntegration:
    """Integration test cases for safe installation system."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_install_dir = "/tmp/test_fogis_deployment"
        self.test_backup_dir = "/tmp/test_fogis_backups"

        # Clean up any existing test directories
        for directory in [self.test_install_dir, self.test_backup_dir]:
            if os.path.exists(directory):
                subprocess.run(["rm", "-rf", directory], check=False)

        # Clean up temporary files
        for temp_file in ["/tmp/fogis_backup_location", "/tmp/fogis_upgrade_state"]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def teardown_method(self):
        """Clean up after each test."""
        # Clean up test directories
        for directory in [self.test_install_dir, self.test_backup_dir]:
            if os.path.exists(directory):
                subprocess.run(["rm", "-rf", directory], check=False)

        # Clean up backup files
        subprocess.run(
            ["find", "/tmp", "-name", "fogis-backup-*.tar.gz", "-delete"], check=False
        )

        # Clean up temporary files
        for temp_file in ["/tmp/fogis_backup_location", "/tmp/fogis_upgrade_state"]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def create_mock_installation(self):
        """Create a mock FOGIS installation for testing."""
        os.makedirs(f"{self.test_install_dir}/credentials", exist_ok=True)
        os.makedirs(f"{self.test_install_dir}/data", exist_ok=True)
        os.makedirs(f"{self.test_install_dir}/logs", exist_ok=True)

        # Create mock credential files
        with open(
            f"{self.test_install_dir}/credentials/google-credentials.json", "w"
        ) as f:
            f.write('{"type": "service_account", "project_id": "test-project"}')

        # Create mock configuration files
        with open(f"{self.test_install_dir}/.env", "w") as f:
            f.write("FOGIS_USERNAME=test_user\nFOGIS_PASSWORD=test_pass")

        with open(f"{self.test_install_dir}/docker-compose.yml", "w") as f:
            f.write("version: '3.8'\nservices:\n  test:\n    image: test")

        # Create mock data files
        with open(f"{self.test_install_dir}/data/match_data.json", "w") as f:
            f.write('{"matches": [{"id": 1, "team1": "A", "team2": "B"}]}')

        # Create mock log files
        with open(f"{self.test_install_dir}/logs/system.log", "w") as f:
            f.write("2023-01-01 00:00:00 - System started\n")

    def test_fresh_installation_no_conflicts(self):
        """Test fresh installation when no conflicts exist."""
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/installation_safety.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"detect_all_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 0
        assert "No conflicts detected" in result.stdout
        assert "safe to proceed with fresh installation" in result.stdout

    def test_conflict_detection_with_existing_installation(self):
        """Test conflict detection when existing installation exists."""
        # Create mock installation
        self.create_mock_installation()

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/installation_safety.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"detect_all_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 1  # Conflicts found
        assert "Existing FOGIS installation detected" in result.stdout
        assert "Directory:" in result.stdout
        assert "Credentials:" in result.stdout
        assert "Data:" in result.stdout
        assert "Logs:" in result.stdout

    def test_safe_upgrade_workflow(self):
        """Test complete safe upgrade workflow."""
        # Create mock installation
        self.create_mock_installation()

        # Test safe upgrade execution
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/installation_safety.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"BACKUP_BASE_DIR={self.test_backup_dir} && "
                f"perform_safe_upgrade",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 0
        assert "PERFORMING SAFE UPGRADE" in result.stdout
        assert "Creating comprehensive backup" in result.stdout
        assert "Graceful service shutdown" in result.stdout
        assert "Preserving critical data" in result.stdout
        assert "Removing old installation" in result.stdout
        assert "Safe upgrade preparation completed" in result.stdout

        # Verify that installation directory was removed
        assert not os.path.exists(self.test_install_dir)

        # Verify that upgrade state file was created
        assert os.path.exists("/tmp/fogis_upgrade_state")

        # Verify that backup was created
        assert os.path.exists("/tmp/fogis_backup_location")

    def test_force_clean_installation_workflow(self):
        """Test force clean installation workflow."""
        # Create mock installation
        self.create_mock_installation()

        # Test force clean execution
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/installation_safety.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"BACKUP_BASE_DIR={self.test_backup_dir} && "
                f"perform_force_clean",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 0
        assert "PERFORMING FORCE CLEAN INSTALLATION" in result.stdout
        assert "Creating backup before destruction" in result.stdout
        assert "Graceful service shutdown" in result.stdout
        assert "Complete removal of installation" in result.stdout
        assert "Force clean completed" in result.stdout

        # Verify that installation directory was removed
        assert not os.path.exists(self.test_install_dir)

        # Verify that backup was created
        assert os.path.exists("/tmp/fogis_backup_location")

    def test_conflict_check_only_mode(self):
        """Test conflict check only mode."""
        # Create mock installation
        self.create_mock_installation()

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/installation_safety.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"perform_conflict_check",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 0
        assert "CONFLICT CHECK ONLY MODE" in result.stdout
        assert "Conflicts detected" in result.stdout
        assert "Recommended next steps" in result.stdout
        assert "Detailed report saved to" in result.stdout

        # Verify that installation was not modified
        assert os.path.exists(self.test_install_dir)
        assert os.path.exists(
            f"{self.test_install_dir}/credentials/google-credentials.json"
        )

    def test_restore_preserved_data_workflow(self):
        """Test data restoration after upgrade."""
        # Create mock installation
        self.create_mock_installation()

        # Perform safe upgrade
        subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/installation_safety.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"BACKUP_BASE_DIR={self.test_backup_dir} && "
                f"perform_safe_upgrade",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        # Create new installation directory
        os.makedirs(self.test_install_dir, exist_ok=True)

        # Test data restoration
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/installation_safety.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"restore_preserved_data",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 0
        assert "Restoring preserved data from upgrade" in result.stdout
        assert "Credentials restored" in result.stdout
        assert "Essential data restored" in result.stdout
        assert "Data restoration completed" in result.stdout

        # Verify that data was restored
        assert os.path.exists(
            f"{self.test_install_dir}/credentials/google-credentials.json"
        )
        assert os.path.exists(f"{self.test_install_dir}/data/match_data.json")

    def test_graceful_service_shutdown(self):
        """Test graceful service shutdown functionality."""
        # Create mock installation with management script
        self.create_mock_installation()

        # Create mock management script
        with open(f"{self.test_install_dir}/manage_fogis_system.sh", "w") as f:
            f.write(
                """#!/bin/bash
case "$1" in
    stop)
        echo "Services stopped"
        exit 0
        ;;
    cron-remove)
        echo "Cron jobs removed"
        exit 0
        ;;
    *)
        exit 1
        ;;
esac
"""
            )
        os.chmod(f"{self.test_install_dir}/manage_fogis_system.sh", 0o755)

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/installation_safety.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"graceful_service_shutdown",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 0
        assert "Performing graceful service shutdown" in result.stdout
        assert "Using management script for shutdown" in result.stdout
        assert "Services stopped via management script" in result.stdout
        assert "Cron jobs removed" in result.stdout
        assert "Graceful shutdown completed" in result.stdout

    def test_backup_and_restore_integration(self):
        """Test complete backup and restore integration."""
        # Create mock installation
        self.create_mock_installation()

        # Create backup
        backup_result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/backup_manager.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"BACKUP_BASE_DIR={self.test_backup_dir} && "
                f"create_installation_backup integration-test",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert backup_result.returncode == 0
        assert "Backup created:" in backup_result.stdout

        # Get backup location
        backup_file = f"{self.test_backup_dir}/integration-test.tar.gz"
        assert os.path.exists(backup_file)

        # Remove original installation
        subprocess.run(["rm", "-rf", self.test_install_dir], check=False)

        # Restore from backup
        restore_result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/backup_manager.sh && "
                f"restore_from_backup {backup_file} {self.test_install_dir}",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert restore_result.returncode == 0
        assert "Restore completed successfully" in restore_result.stdout

        # Verify restored content
        assert os.path.exists(
            f"{self.test_install_dir}/credentials/google-credentials.json"
        )
        assert os.path.exists(f"{self.test_install_dir}/.env")
        assert os.path.exists(f"{self.test_install_dir}/docker-compose.yml")

        # Verify content integrity
        with open(
            f"{self.test_install_dir}/credentials/google-credentials.json", "r"
        ) as f:
            content = f.read()
            assert "test-project" in content

    def test_installation_mode_execution_fresh(self):
        """Test installation mode execution for fresh installation."""
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/installation_safety.sh && "
                f"INSTALL_MODE=fresh && "
                f"execute_installation_mode",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 0
        assert "Proceeding with fresh installation" in result.stdout

    def test_installation_mode_execution_check(self):
        """Test installation mode execution for conflict check."""
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/installation_safety.sh && "
                f"INSTALL_MODE=check && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"execute_installation_mode",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 1  # Expected for check mode
        assert "CONFLICT CHECK ONLY MODE" in result.stdout


class TestSafeInstallationErrorHandling:
    """Test error handling and edge cases for safe installation."""

    def test_backup_failure_handling(self):
        """Test behavior when backup creation fails."""
        # Try to create backup in non-existent directory with no permissions
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/installation_safety.sh && "
                f"INSTALL_DIR=/nonexistent && "
                f"BACKUP_BASE_DIR=/root/restricted && "
                f"perform_safe_upgrade",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        # Should handle backup failure gracefully
        assert result.returncode in [0, 1]

    def test_docker_command_failures(self):
        """Test behavior when Docker commands fail."""
        # This test assumes Docker is not available or fails
        # The functions should handle this gracefully
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/installation_safety.sh && "
                f"graceful_service_shutdown",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        # Should complete even if Docker commands fail
        assert result.returncode == 0
        assert "Graceful shutdown completed" in result.stdout

    def test_invalid_installation_mode(self):
        """Test behavior with invalid installation mode."""
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/installation_safety.sh && "
                f"INSTALL_MODE=invalid && "
                f"execute_installation_mode",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 1
        assert "Invalid installation mode" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__])
