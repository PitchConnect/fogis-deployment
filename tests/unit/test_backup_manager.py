#!/usr/bin/env python3
"""
Unit tests for BackupManager
Tests backup and restore functionality
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add the lib directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))

from backup_manager import BackupError, BackupManager  # noqa: E402


class TestBackupManager(unittest.TestCase):
    """Test cases for BackupManager class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create test backup directory
        self.backup_dir = Path(self.test_dir) / "test_backups"
        self.backup_manager = BackupManager(str(self.backup_dir))

        # Create test files
        self.create_test_files()

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        import shutil

        shutil.rmtree(self.test_dir)

    def create_test_files(self):
        """Create test files for backup testing"""
        # Create config files
        with open("fogis-config.yaml", "w") as f:
            f.write("test: config")

        with open(".env", "w") as f:
            f.write("TEST_VAR=value")

        # Create credentials
        with open("credentials.json", "w") as f:
            json.dump({"test": "credentials"}, f)

        # Create data directories
        os.makedirs("data/test", exist_ok=True)
        with open("data/test/data.json", "w") as f:
            json.dump({"test": "data"}, f)

        # Create logs directory
        os.makedirs("logs", exist_ok=True)
        with open("logs/test.log", "w") as f:
            f.write("test log")

    def test_create_config_backup(self):
        """Test creating configuration backup"""
        backup_file = self.backup_manager.create_backup("config")

        self.assertTrue(os.path.exists(backup_file))
        self.assertIn("config", backup_file)
        self.assertTrue(self.backup_manager.validate_backup(backup_file))

    def test_create_credentials_backup(self):
        """Test creating credentials backup"""
        backup_file = self.backup_manager.create_backup("credentials")

        self.assertTrue(os.path.exists(backup_file))
        self.assertIn("credentials", backup_file)
        self.assertTrue(self.backup_manager.validate_backup(backup_file))

    def test_create_complete_backup(self):
        """Test creating complete system backup"""
        backup_file = self.backup_manager.create_backup("complete")

        self.assertTrue(os.path.exists(backup_file))
        self.assertIn("complete", backup_file)
        self.assertTrue(self.backup_manager.validate_backup(backup_file))

    def test_invalid_backup_type(self):
        """Test creating backup with invalid type"""
        with self.assertRaises(BackupError):
            self.backup_manager.create_backup("invalid")

    def test_validate_backup_valid(self):
        """Test validating a valid backup"""
        backup_file = self.backup_manager.create_backup("config")
        self.assertTrue(self.backup_manager.validate_backup(backup_file))

    def test_validate_backup_nonexistent(self):
        """Test validating non-existent backup"""
        self.assertFalse(self.backup_manager.validate_backup("nonexistent.tar.gz"))

    def test_list_backups_empty(self):
        """Test listing backups when none exist"""
        backups = self.backup_manager.list_backups()
        self.assertEqual(len(backups), 0)

    def test_list_backups_with_backups(self):
        """Test listing backups when some exist"""
        # Create a few backups
        self.backup_manager.create_backup("config")
        self.backup_manager.create_backup("credentials")

        backups = self.backup_manager.list_backups()
        self.assertEqual(len(backups), 2)

        # Check backup info structure
        for backup in backups:
            self.assertIn("type", backup)
            self.assertIn("created_at", backup)
            self.assertIn("file_path", backup)

    def test_get_backup_info(self):
        """Test getting backup information"""
        backup_file = self.backup_manager.create_backup("config")
        backup_info = self.backup_manager.get_backup_info(backup_file)

        self.assertIsNotNone(backup_info)
        self.assertEqual(backup_info["type"], "config")
        self.assertIn("created_at", backup_info)
        self.assertIn("file_size", backup_info)

    def test_get_backup_info_invalid(self):
        """Test getting info for invalid backup"""
        backup_info = self.backup_manager.get_backup_info("nonexistent.tar.gz")
        self.assertIsNone(backup_info)

    def test_delete_backup(self):
        """Test deleting a backup"""
        backup_file = self.backup_manager.create_backup("config")
        self.assertTrue(os.path.exists(backup_file))

        result = self.backup_manager.delete_backup(backup_file)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(backup_file))

    def test_delete_nonexistent_backup(self):
        """Test deleting non-existent backup"""
        result = self.backup_manager.delete_backup("nonexistent.tar.gz")
        self.assertFalse(result)

    def test_cleanup_old_backups(self):
        """Test cleaning up old backups"""
        # Test with no backups (should delete nothing)
        deleted_count = self.backup_manager.cleanup_old_backups(keep_count=5)
        self.assertEqual(deleted_count, 0)

        # Create one backup
        backup1 = self.backup_manager.create_backup("config")

        # Test cleanup with keep_count larger than current count (should delete nothing)
        deleted_count = self.backup_manager.cleanup_old_backups(keep_count=10)
        self.assertEqual(deleted_count, 0)

        # Verify backup still exists
        backups = self.backup_manager.list_backups()
        self.assertEqual(len(backups), 1)

        # Test cleanup with keep_count = 0 (should delete all)
        deleted_count = self.backup_manager.cleanup_old_backups(keep_count=0)
        self.assertEqual(deleted_count, 1)

        # Verify no backups remain
        backups_after = self.backup_manager.list_backups()
        self.assertEqual(len(backups_after), 0)

    def test_restore_config_backup(self):
        """Test restoring configuration backup"""
        # Create backup
        backup_file = self.backup_manager.create_backup("config")

        # Modify original files
        with open("fogis-config.yaml", "w") as f:
            f.write("modified: config")

        # Restore backup
        result = self.backup_manager.restore_backup(backup_file)
        self.assertTrue(result)

        # Verify restoration
        with open("fogis-config.yaml", "r") as f:
            content = f.read()
            self.assertEqual(content, "test: config")

    def test_restore_nonexistent_backup(self):
        """Test restoring non-existent backup"""
        with self.assertRaises(BackupError):
            self.backup_manager.restore_backup("nonexistent.tar.gz")

    @patch("backup_manager.tarfile.open")
    def test_restore_invalid_backup(self, mock_tarfile):
        """Test restoring invalid backup file"""
        # Mock tarfile to raise exception
        mock_tarfile.side_effect = Exception("Invalid archive")

        # Create a dummy file
        dummy_backup = self.backup_dir / "dummy.tar.gz"
        dummy_backup.touch()

        with self.assertRaises(BackupError):
            self.backup_manager.restore_backup(str(dummy_backup))

    def test_map_config_file_destination(self):
        """Test mapping config file destinations"""
        mapping = self.backup_manager._map_config_file_destination("fogis-config.yaml")
        self.assertEqual(mapping, Path("fogis-config.yaml"))

        mapping = self.backup_manager._map_config_file_destination(".env")
        self.assertEqual(mapping, Path(".env"))

        mapping = self.backup_manager._map_config_file_destination("unknown.txt")
        self.assertIsNone(mapping)

    def test_map_token_file_destination(self):
        """Test mapping token file destinations"""
        mapping = self.backup_manager._map_token_file_destination(
            "google-drive-token.json"
        )
        self.assertEqual(
            mapping, Path("data/google-drive-service/google-drive-token.json")
        )

        mapping = self.backup_manager._map_token_file_destination("unknown-token.json")
        self.assertIsNone(mapping)

    def test_backup_manifest_creation(self):
        """Test backup manifest creation"""
        backup_file = self.backup_manager.create_backup("config")

        # Extract and check manifest
        import tarfile

        with tarfile.open(backup_file, "r:gz") as tar:
            manifest_member = None
            for member in tar.getmembers():
                if member.name.endswith("backup_manifest.json"):
                    manifest_member = member
                    break

            self.assertIsNotNone(manifest_member)

            # Extract manifest
            with tempfile.TemporaryDirectory() as temp_dir:
                tar.extract(manifest_member, temp_dir)
                manifest_path = Path(temp_dir) / manifest_member.name

                with open(manifest_path, "r") as f:
                    manifest = json.load(f)

                self.assertIn("backup_info", manifest)
                self.assertIn("files", manifest)
                self.assertIn("directories", manifest)
                self.assertEqual(manifest["backup_info"]["type"], "config")


if __name__ == "__main__":
    unittest.main()
