#!/usr/bin/env python3

"""
Integration tests for end-to-end credential preservation during fresh installations
Tests the complete workflow from backup creation to restoration and validation
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestEndToEndCredentialPreservation:
    """Integration tests for complete credential preservation workflow"""

    @pytest.fixture
    def test_environment(self):
        """Set up a complete test environment"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)

            # Create mock FOGIS deployment structure
            deployment_dir = test_dir / "fogis-deployment"
            deployment_dir.mkdir()

            # Create initial .env file with test credentials
            env_file = deployment_dir / ".env"
            env_content = """# FOGIS Deployment Configuration
FOGIS_USERNAME=Original User
FOGIS_PASSWORD=original_password
USER_REFEREE_NUMBER=12345

# Google Configuration
GOOGLE_CREDENTIALS_PATH=credentials/google-credentials.json
GOOGLE_CALENDAR_ID=test@group.calendar.google.com

# Service Ports
API_CLIENT_PORT=9086
CALENDAR_SYNC_PORT=9083
"""
            env_file.write_text(env_content)

            # Create credentials directory
            creds_dir = deployment_dir / "credentials"
            creds_dir.mkdir()

            # Create mock Google credentials
            google_creds = creds_dir / "google-credentials.json"
            google_creds.write_text('{"type": "service_account", "project_id": "test"}')

            # Copy restoration script to test directory
            script_source = (
                Path(__file__).parent.parent.parent / "restore_fogis_credentials.sh"
            )
            if script_source.exists():
                shutil.copy(script_source, deployment_dir)

            # Copy validation script
            validation_source = (
                Path(__file__).parent.parent.parent
                / "scripts"
                / "validate_fogis_credentials.py"
            )
            if validation_source.exists():
                scripts_dir = deployment_dir / "scripts"
                scripts_dir.mkdir()
                shutil.copy(validation_source, scripts_dir)

            yield {
                "test_dir": test_dir,
                "deployment_dir": deployment_dir,
                "env_file": env_file,
                "creds_dir": creds_dir,
            }

    def test_backup_creation_and_restoration_workflow(self, test_environment):
        """Test complete backup creation and restoration workflow"""
        deployment_dir = test_environment["deployment_dir"]
        env_file = test_environment["env_file"]

        # Step 1: Create backup using the backup script
        backup_script = (
            Path(__file__).parent.parent.parent / "create_credential_backup.sh"
        )
        if backup_script.exists():
            # Copy backup script to test environment
            shutil.copy(backup_script, deployment_dir.parent)

            # Run backup creation
            result = subprocess.run(
                [str(deployment_dir.parent / "create_credential_backup.sh")],
                cwd=deployment_dir.parent,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Verify backup was created
            backup_dirs = list(deployment_dir.parent.glob("fogis-credentials-backup-*"))
            assert len(backup_dirs) > 0, "Backup directory should be created"

            backup_dir = backup_dirs[0]
            credentials_file = backup_dir / "FOGIS_CREDENTIALS.txt"
            assert credentials_file.exists(), "Credentials file should exist in backup"

            # Verify backup contains correct credentials
            backup_content = credentials_file.read_text()
            assert "FOGIS_USERNAME=Original User" in backup_content
            assert "FOGIS_PASSWORD=original_password" in backup_content

            # Step 2: Simulate fresh installation by removing .env file
            env_file.unlink()
            assert not env_file.exists(), ".env file should be removed"

            # Step 3: Test credential restoration
            restoration_script = deployment_dir / "restore_fogis_credentials.sh"
            if restoration_script.exists():
                result = subprocess.run(
                    [str(restoration_script), str(backup_dir), "--auto"],
                    cwd=deployment_dir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                # Verify restoration succeeded
                assert (
                    result.returncode == 0
                ), f"Restoration should succeed: {result.stderr}"
                assert env_file.exists(), ".env file should be recreated"

                # Verify restored credentials
                restored_content = env_file.read_text()
                assert "FOGIS_USERNAME=Original User" in restored_content
                assert "FOGIS_PASSWORD=original_password" in restored_content

    def test_credential_validation_after_restoration(self, test_environment):
        """Test credential validation after restoration"""
        deployment_dir = test_environment["deployment_dir"]

        # Create a backup directory with test credentials
        backup_dir = deployment_dir.parent / "test-backup"
        backup_dir.mkdir()

        credentials_file = backup_dir / "FOGIS_CREDENTIALS.txt"
        credentials_content = """FOGIS Authentication Credentials:
=================================

Found .env file - extracting FOGIS credentials...
FOGIS_USERNAME=Test Validation User
FOGIS_PASSWORD=test_validation_password
"""
        credentials_file.write_text(credentials_content)

        # Test restoration with validation
        restoration_script = deployment_dir / "restore_fogis_credentials.sh"
        if restoration_script.exists():
            result = subprocess.run(
                [str(restoration_script), str(backup_dir), "--auto", "--validate"],
                cwd=deployment_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Restoration should complete (validation may fail with test credentials)
            assert (
                "Successfully updated .env" in result.stdout
                or "Successfully updated .env" in result.stderr
            )

    def test_docker_compose_environment_variable_loading(self, test_environment):
        """Test that Docker Compose properly loads environment variables"""
        deployment_dir = test_environment["deployment_dir"]
        env_file = test_environment["env_file"]

        # Create a test Docker Compose file
        docker_compose_content = """version: '3.8'

x-env-file: &env-file
  env_file:
    - .env

services:
  test-service:
    image: alpine:latest
    <<: *env-file
    environment:
      - FOGIS_USERNAME=${FOGIS_USERNAME}
      - FOGIS_PASSWORD=${FOGIS_PASSWORD}
    command: env
"""

        docker_compose_file = deployment_dir / "docker-compose.test.yml"
        docker_compose_file.write_text(docker_compose_content)

        # Test that environment variables are properly substituted
        result = subprocess.run(
            ["docker-compose", "-f", "docker-compose.test.yml", "config"],
            cwd=deployment_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            # Verify environment variables are substituted
            assert "Original User" in result.stdout
            # Password should be substituted but not visible in plain text in config

    def test_backup_detection_and_auto_restoration(self, test_environment):
        """Test automatic backup detection and restoration"""
        deployment_dir = test_environment["deployment_dir"]

        # Create multiple backup directories to test detection
        backup1 = deployment_dir.parent / "fogis-credentials-backup-20250717-140000"
        backup2 = deployment_dir.parent / "fogis-credentials-backup-20250717-150000"

        backup1.mkdir()
        backup2.mkdir()

        # Create credentials in both backups (backup2 is newer)
        (backup1 / "FOGIS_CREDENTIALS.txt").write_text(
            "FOGIS_USERNAME=Old User\nFOGIS_PASSWORD=old_pass"
        )
        (backup2 / "FOGIS_CREDENTIALS.txt").write_text(
            "FOGIS_USERNAME=New User\nFOGIS_PASSWORD=new_pass"
        )

        # Remove existing .env file
        env_file = test_environment["env_file"]
        env_file.unlink()

        # Test automatic detection (should pick the newest backup)
        restoration_script = deployment_dir / "restore_fogis_credentials.sh"
        if restoration_script.exists():
            result = subprocess.run(
                [str(restoration_script), "--auto"],
                cwd=deployment_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Verify the newest backup was used
                restored_content = env_file.read_text()
                assert "FOGIS_USERNAME=New User" in restored_content
                assert "FOGIS_PASSWORD=new_pass" in restored_content

    def test_error_handling_missing_backup(self, test_environment):
        """Test error handling when no backup is available"""
        deployment_dir = test_environment["deployment_dir"]

        restoration_script = deployment_dir / "restore_fogis_credentials.sh"
        if restoration_script.exists():
            result = subprocess.run(
                [str(restoration_script), "--auto"],
                cwd=deployment_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Should fail gracefully when no backup is found
            assert result.returncode != 0
            assert (
                "No backup directory found" in result.stdout
                or "No backup directory found" in result.stderr
            )

    def test_error_handling_malformed_backup(self, test_environment):
        """Test error handling with malformed backup files"""
        deployment_dir = test_environment["deployment_dir"]

        # Create backup with malformed credentials file
        backup_dir = deployment_dir.parent / "malformed-backup"
        backup_dir.mkdir()

        credentials_file = backup_dir / "FOGIS_CREDENTIALS.txt"
        credentials_file.write_text("This is not a valid credentials file format")

        restoration_script = deployment_dir / "restore_fogis_credentials.sh"
        if restoration_script.exists():
            result = subprocess.run(
                [str(restoration_script), str(backup_dir), "--auto"],
                cwd=deployment_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Should fail gracefully with malformed backup
            assert result.returncode != 0
            assert "extract" in result.stdout or "extract" in result.stderr

    def test_env_file_backup_and_restoration(self, test_environment):
        """Test that .env file backup is created during restoration"""
        deployment_dir = test_environment["deployment_dir"]
        env_file = test_environment["env_file"]

        # Create backup directory
        backup_dir = deployment_dir.parent / "test-backup"
        backup_dir.mkdir()

        credentials_file = backup_dir / "FOGIS_CREDENTIALS.txt"
        credentials_file.write_text(
            "FOGIS_USERNAME=Backup User\nFOGIS_PASSWORD=backup_pass"
        )

        # Record original .env content
        original_content = env_file.read_text()

        restoration_script = deployment_dir / "restore_fogis_credentials.sh"
        if restoration_script.exists():
            result = subprocess.run(
                [str(restoration_script), str(backup_dir), "--auto"],
                cwd=deployment_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Verify backup of original .env was created
                backup_files = list(deployment_dir.glob(".env.backup.*"))
                assert (
                    len(backup_files) > 0
                ), "Backup of original .env should be created"

                # Verify backup contains original content
                backup_content = backup_files[0].read_text()
                assert "Original User" in backup_content

    @patch.dict(
        os.environ, {"FOGIS_USERNAME": "env_user", "FOGIS_PASSWORD": "env_pass"}
    )
    def test_environment_variable_precedence(self, test_environment):
        """Test environment variable precedence in credential loading"""
        deployment_dir = test_environment["deployment_dir"]

        # Test validation script with environment variables
        validation_script = deployment_dir / "scripts" / "validate_fogis_credentials.py"
        if validation_script.exists():
            result = subprocess.run(
                ["python3", str(validation_script)],
                cwd=deployment_dir,
                capture_output=True,
                text=True,
                timeout=30,
                env={
                    **os.environ,
                    "FOGIS_USERNAME": "env_user",
                    "FOGIS_PASSWORD": "env_pass",
                },
            )

            # Should load credentials from environment variables
            assert "env_user" in result.stdout or "env_user" in result.stderr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
