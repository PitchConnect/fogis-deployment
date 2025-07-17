"""
Unit tests for the FOGIS Backup Management System.

This module contains comprehensive unit tests for backup creation,
restoration, and management functionality.
"""

import os
import subprocess
import tempfile
import tarfile
from unittest.mock import Mock, patch
import pytest


class TestBackupManager:
    """Test cases for backup management functions."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        self.test_install_dir = "/tmp/test_fogis_deployment"
        self.test_backup_dir = "/tmp/test_fogis_backups"
        self.test_env = {
            "INSTALL_DIR": self.test_install_dir,
            "BACKUP_BASE_DIR": self.test_backup_dir,
            "BACKUP_RETENTION_DAYS": "30"
        }
        
        # Create test installation structure
        os.makedirs(f"{self.test_install_dir}/credentials", exist_ok=True)
        os.makedirs(f"{self.test_install_dir}/data", exist_ok=True)
        os.makedirs(f"{self.test_install_dir}/logs", exist_ok=True)
        os.makedirs(self.test_backup_dir, exist_ok=True)
        
        # Create test files
        with open(f"{self.test_install_dir}/credentials/google-credentials.json", "w") as f:
            f.write('{"type": "service_account", "project_id": "test"}')
        
        with open(f"{self.test_install_dir}/docker-compose-master.yml", "w") as f:
            f.write("version: '3.8'\nservices:\n  test:\n    image: test")
        
        with open(f"{self.test_install_dir}/.env", "w") as f:
            f.write("FOGIS_USERNAME=test\nFOGIS_PASSWORD=test")
        
        with open(f"{self.test_install_dir}/data/test.json", "w") as f:
            f.write('{"test": "data"}')
        
        with open(f"{self.test_install_dir}/logs/test.log", "w") as f:
            f.write("2023-01-01 00:00:00 - Test log entry")
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clean up test directories
        for directory in [self.test_install_dir, self.test_backup_dir]:
            if os.path.exists(directory):
                subprocess.run(["rm", "-rf", directory], check=False)
        
        # Clean up any backup files in /tmp
        subprocess.run([
            "find", "/tmp", "-name", "fogis-backup-*.tar.gz", "-delete"
        ], check=False)
        
        # Clean up temporary files
        for temp_file in ["/tmp/fogis_backup_location"]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_create_installation_backup_success(self):
        """Test successful backup creation."""
        result = subprocess.run([
            "bash", "-c", 
            f"source fogis-deployment/lib/backup_manager.sh && "
            f"INSTALL_DIR={self.test_install_dir} && "
            f"BACKUP_BASE_DIR={self.test_backup_dir} && "
            f"create_installation_backup test-backup"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 0
        assert "Backup created:" in result.stdout
        assert "Backup size:" in result.stdout
        
        # Check that backup file was created
        backup_file = f"{self.test_backup_dir}/test-backup.tar.gz"
        assert os.path.exists(backup_file)
        
        # Check that backup location was stored
        assert os.path.exists("/tmp/fogis_backup_location")
        with open("/tmp/fogis_backup_location", "r") as f:
            stored_location = f.read().strip()
            assert stored_location == backup_file
    
    def test_create_installation_backup_no_install_dir(self):
        """Test backup creation when no installation directory exists."""
        result = subprocess.run([
            "bash", "-c", 
            f"source fogis-deployment/lib/backup_manager.sh && "
            f"INSTALL_DIR=/nonexistent && "
            f"BACKUP_BASE_DIR={self.test_backup_dir} && "
            f"create_installation_backup test-backup"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 0
        assert "No installation directory found" in result.stdout
    
    def test_backup_content_verification(self):
        """Test that backup contains expected content."""
        # Create backup
        result = subprocess.run([
            "bash", "-c", 
            f"source fogis-deployment/lib/backup_manager.sh && "
            f"INSTALL_DIR={self.test_install_dir} && "
            f"BACKUP_BASE_DIR={self.test_backup_dir} && "
            f"create_installation_backup test-backup"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 0
        
        # Extract and verify backup content
        backup_file = f"{self.test_backup_dir}/test-backup.tar.gz"
        extract_dir = "/tmp/test_backup_extract"
        os.makedirs(extract_dir, exist_ok=True)
        
        with tarfile.open(backup_file, "r:gz") as tar:
            tar.extractall(extract_dir)
        
        # Check that expected files are in backup
        backup_content_dir = os.path.join(extract_dir, "test-backup")
        assert os.path.exists(f"{backup_content_dir}/credentials/google-credentials.json")
        assert os.path.exists(f"{backup_content_dir}/configs/.env")
        assert os.path.exists(f"{backup_content_dir}/configs/docker-compose-master.yml")
        assert os.path.exists(f"{backup_content_dir}/data/test.json")
        assert os.path.exists(f"{backup_content_dir}/logs/test.log")
        assert os.path.exists(f"{backup_content_dir}/BACKUP_MANIFEST.txt")
        
        # Verify manifest content
        with open(f"{backup_content_dir}/BACKUP_MANIFEST.txt", "r") as f:
            manifest = f.read()
            assert "FOGIS Installation Backup" in manifest
            assert "Restore Instructions" in manifest
            assert "Security Notes" in manifest
        
        # Clean up
        subprocess.run(["rm", "-rf", extract_dir], check=False)
    
    def test_restore_from_backup_success(self):
        """Test successful backup restoration."""
        # First create a backup
        subprocess.run([
            "bash", "-c", 
            f"source fogis-deployment/lib/backup_manager.sh && "
            f"INSTALL_DIR={self.test_install_dir} && "
            f"BACKUP_BASE_DIR={self.test_backup_dir} && "
            f"create_installation_backup test-backup"
        ], capture_output=True, text=True, cwd=".")
        
        backup_file = f"{self.test_backup_dir}/test-backup.tar.gz"
        
        # Remove original installation
        subprocess.run(["rm", "-rf", self.test_install_dir], check=False)
        
        # Restore from backup
        restore_dir = "/tmp/test_restore"
        result = subprocess.run([
            "bash", "-c", 
            f"source fogis-deployment/lib/backup_manager.sh && "
            f"restore_from_backup {backup_file} {restore_dir}"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 0
        assert "Restore completed successfully" in result.stdout
        
        # Verify restored content
        assert os.path.exists(f"{restore_dir}/credentials/google-credentials.json")
        assert os.path.exists(f"{restore_dir}/.env")
        assert os.path.exists(f"{restore_dir}/docker-compose-master.yml")
        
        # Clean up
        subprocess.run(["rm", "-rf", restore_dir], check=False)
    
    def test_restore_from_backup_invalid_file(self):
        """Test restoration with invalid backup file."""
        result = subprocess.run([
            "bash", "-c", 
            f"source fogis-deployment/lib/backup_manager.sh && "
            f"restore_from_backup /nonexistent/backup.tar.gz"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 1
        assert "Backup file not found" in result.stdout
    
    def test_list_backups_empty(self):
        """Test listing backups when no backups exist."""
        # Ensure backup directory is empty
        subprocess.run(["rm", "-rf", self.test_backup_dir], check=False)
        
        result = subprocess.run([
            "bash", "-c", 
            f"source fogis-deployment/lib/backup_manager.sh && "
            f"BACKUP_BASE_DIR={self.test_backup_dir} && "
            f"list_backups"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 0
        assert "No backup directory found" in result.stdout or "No backups found" in result.stdout
    
    def test_list_backups_with_backups(self):
        """Test listing backups when backups exist."""
        # Create multiple backups
        for i in range(3):
            subprocess.run([
                "bash", "-c", 
                f"source fogis-deployment/lib/backup_manager.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"BACKUP_BASE_DIR={self.test_backup_dir} && "
                f"create_installation_backup test-backup-{i}"
            ], capture_output=True, text=True, cwd=".")
        
        result = subprocess.run([
            "bash", "-c", 
            f"source fogis-deployment/lib/backup_manager.sh && "
            f"BACKUP_BASE_DIR={self.test_backup_dir} && "
            f"list_backups"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 0
        assert "Found 3 backup(s)" in result.stdout
        assert "test-backup-0" in result.stdout
        assert "test-backup-1" in result.stdout
        assert "test-backup-2" in result.stdout
        assert "Size:" in result.stdout
        assert "Date:" in result.stdout
    
    def test_cleanup_old_backups_no_old_backups(self):
        """Test cleanup when no old backups exist."""
        result = subprocess.run([
            "bash", "-c", 
            f"source fogis-deployment/lib/backup_manager.sh && "
            f"BACKUP_BASE_DIR={self.test_backup_dir} && "
            f"cleanup_old_backups 30"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 0
        assert "No old backups to clean" in result.stdout or "No backup directory found" in result.stdout
    
    def test_backup_manifest_creation(self):
        """Test that backup manifest is created correctly."""
        # Create backup
        subprocess.run([
            "bash", "-c", 
            f"source fogis-deployment/lib/backup_manager.sh && "
            f"INSTALL_DIR={self.test_install_dir} && "
            f"BACKUP_BASE_DIR={self.test_backup_dir} && "
            f"create_installation_backup test-manifest"
        ], capture_output=True, text=True, cwd=".")
        
        # Extract and check manifest
        backup_file = f"{self.test_backup_dir}/test-manifest.tar.gz"
        extract_dir = "/tmp/test_manifest_extract"
        os.makedirs(extract_dir, exist_ok=True)
        
        with tarfile.open(backup_file, "r:gz") as tar:
            tar.extractall(extract_dir)
        
        manifest_file = f"{extract_dir}/test-manifest/BACKUP_MANIFEST.txt"
        assert os.path.exists(manifest_file)
        
        with open(manifest_file, "r") as f:
            manifest = f.read()
            
        # Check manifest sections
        assert "FOGIS Installation Backup" in manifest
        assert "Created:" in manifest
        assert "Source:" in manifest
        assert "Contents:" in manifest
        assert "File Counts:" in manifest
        assert "Restore Instructions:" in manifest
        assert "Security Notes:" in manifest
        
        # Check that file counts are present
        assert "Credentials:" in manifest
        assert "Configurations:" in manifest
        assert "Data files:" in manifest
        assert "Log files:" in manifest
        
        # Clean up
        subprocess.run(["rm", "-rf", extract_dir], check=False)


class TestBackupManagerEdgeCases:
    """Test edge cases and error conditions for backup manager."""
    
    def test_backup_with_permission_errors(self):
        """Test backup creation with permission errors."""
        # This test would require specific permission setups
        # For now, we'll test that the functions handle errors gracefully
        result = subprocess.run([
            "bash", "-c", 
            f"source fogis-deployment/lib/backup_manager.sh && "
            f"INSTALL_DIR=/root/restricted && "
            f"BACKUP_BASE_DIR=/tmp/test_backup && "
            f"create_installation_backup test-perm"
        ], capture_output=True, text=True, cwd=".")
        
        # Should handle permission errors gracefully
        assert result.returncode in [0, 1]
    
    def test_backup_with_disk_space_issues(self):
        """Test backup behavior when disk space is limited."""
        # This would require creating a scenario with limited disk space
        # For now, we'll ensure the function exists and can be called
        result = subprocess.run([
            "bash", "-c", 
            f"source fogis-deployment/lib/backup_manager.sh && "
            f"type create_installation_backup"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 0
        assert "create_installation_backup is a function" in result.stdout
    
    def test_corrupted_backup_restoration(self):
        """Test restoration from corrupted backup file."""
        # Create a corrupted backup file
        corrupted_backup = "/tmp/corrupted_backup.tar.gz"
        with open(corrupted_backup, "w") as f:
            f.write("This is not a valid tar.gz file")
        
        result = subprocess.run([
            "bash", "-c", 
            f"source fogis-deployment/lib/backup_manager.sh && "
            f"restore_from_backup {corrupted_backup} /tmp/test_restore"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 1
        assert "Failed to extract backup" in result.stdout
        
        # Clean up
        os.remove(corrupted_backup)


if __name__ == "__main__":
    pytest.main([__file__])
