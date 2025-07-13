#!/usr/bin/env python3
"""
Unit tests for MigrationTool
Tests migration from legacy to portable configuration
"""

import unittest
import tempfile
import os
import yaml
import json
import tarfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# Add the lib directory to the path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))

from migration_tool import MigrationTool, MigrationError


class TestMigrationTool(unittest.TestCase):
    """Test cases for MigrationTool class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Sample .env content
        self.sample_env_content = """
FOGIS_USERNAME=test_user
FOGIS_PASSWORD=test_pass
USER_REFEREE_NUMBER=12345
LOG_LEVEL=INFO
API_CLIENT_PORT=9086
MATCH_PROCESSOR_PORT=9082
GOOGLE_CALENDAR_ID=primary
"""

        # Sample config.json content
        self.sample_config_json = {
            "CALENDAR_ID": "primary",
            "SYNC_TAG": "FOGIS_CALENDAR_SYNC",
            "USER_REFEREE_NUMBER": 12345,
            "SCOPES": [
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/contacts",
                "https://www.googleapis.com/auth/drive"
            ],
            "NOTIFICATION_METHOD": "email",
            "NOTIFICATION_EMAIL_SENDER": "test@example.com",
            "NOTIFICATION_EMAIL_RECEIVER": "admin@example.com"
        }

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)

    def test_analyze_current_setup(self):
        """Test analysis of current setup"""
        # Create test files
        with open('.env', 'w') as f:
            f.write(self.sample_env_content)

        os.makedirs('fogis-calendar-phonebook-sync', exist_ok=True)
        with open('fogis-calendar-phonebook-sync/config.json', 'w') as f:
            json.dump(self.sample_config_json, f)

        migration_tool = MigrationTool()
        analysis = migration_tool.analyze_current_setup()

        self.assertTrue(analysis['has_env_file'])
        self.assertTrue(analysis['has_config_json'])
        self.assertFalse(analysis['has_portable_config'])
        self.assertGreater(analysis['env_file_size'], 0)

    @patch.dict(os.environ, {
        'FOGIS_USERNAME': 'test_user',
        'FOGIS_PASSWORD': 'test_pass',
        'USER_REFEREE_NUMBER': '12345',
        'LOG_LEVEL': 'INFO'
    })
    @patch('lib.migration_tool.load_dotenv')
    def test_load_legacy_config(self, mock_load_dotenv):
        """Test loading legacy configuration"""
        # Create test files
        with open('.env', 'w') as f:
            f.write(self.sample_env_content)

        os.makedirs('fogis-calendar-phonebook-sync', exist_ok=True)
        with open('fogis-calendar-phonebook-sync/config.json', 'w') as f:
            json.dump(self.sample_config_json, f)

        migration_tool = MigrationTool()
        legacy_config = migration_tool.load_legacy_config()

        # Check that config was loaded from both sources
        self.assertIn('fogis', legacy_config)
        self.assertIn('google', legacy_config)

        # Check values from config.json
        self.assertEqual(legacy_config['google']['calendar']['calendar_id'], 'primary')
        self.assertEqual(legacy_config['fogis']['referee_number'], 12345)

        # Check that email notifications were configured
        self.assertTrue(legacy_config['notifications']['email']['enabled'])
        self.assertEqual(legacy_config['notifications']['email']['sender'], 'test@example.com')

    def test_convert_to_yaml_structure(self):
        """Test conversion to YAML structure"""
        legacy_config = {
            'fogis': {
                'username': 'test_user',
                'password': 'test_pass',
                'referee_number': 12345
            },
            'google': {
                'calendar': {
                    'calendar_id': 'primary'
                },
                'oauth': {
                    'scopes': ['calendar', 'contacts', 'drive']
                }
            }
        }

        migration_tool = MigrationTool()
        yaml_config = migration_tool.convert_to_yaml_structure(legacy_config)

        # Check structure
        self.assertIn('metadata', yaml_config)
        self.assertIn('fogis', yaml_config)
        self.assertIn('google', yaml_config)
        self.assertIn('services', yaml_config)

        # Check values
        self.assertEqual(yaml_config['fogis']['username'], 'test_user')
        self.assertEqual(yaml_config['fogis']['referee_number'], 12345)
        self.assertEqual(yaml_config['google']['calendar']['calendar_id'], 'primary')

    def test_create_pre_migration_backup(self):
        """Test backup creation"""
        # Create test files
        with open('.env', 'w') as f:
            f.write(self.sample_env_content)

        with open('credentials.json', 'w') as f:
            json.dump({'type': 'service_account'}, f)

        migration_tool = MigrationTool()
        backup_path = migration_tool.create_pre_migration_backup()

        # Check backup file exists
        self.assertTrue(os.path.exists(backup_path))
        self.assertTrue(backup_path.endswith('.tar.gz'))

        # Check backup contents
        with tarfile.open(backup_path, 'r:gz') as tar:
            names = tar.getnames()
            self.assertIn('env_backup/.env', names)
            self.assertIn('credentials_backup/credentials.json', names)
            self.assertIn('migration-metadata.json', names)

    def test_get_migration_status(self):
        """Test migration status detection"""
        migration_tool = MigrationTool()

        # Test new installation
        status = migration_tool.get_migration_status()
        self.assertEqual(status['current_mode'], 'none')
        self.assertFalse(status['migration_needed'])

        # Test legacy mode
        with open('.env', 'w') as f:
            f.write(self.sample_env_content)

        status = migration_tool.get_migration_status()
        self.assertEqual(status['current_mode'], 'legacy')
        self.assertTrue(status['migration_needed'])

        # Test portable mode
        with open('fogis-config.yaml', 'w') as f:
            yaml.dump({'metadata': {'version': '2.0'}}, f)

        status = migration_tool.get_migration_status()
        self.assertEqual(status['current_mode'], 'portable')
        self.assertFalse(status['migration_needed'])

    @patch('migration_tool.MigrationTool.ask_yes_no')
    def test_confirm_migration(self, mock_ask):
        """Test migration confirmation"""
        migration_tool = MigrationTool()

        # Test user confirms
        mock_ask.return_value = True
        self.assertTrue(migration_tool.confirm_migration())

        # Test user declines
        mock_ask.return_value = False
        self.assertFalse(migration_tool.confirm_migration())

    def test_check_oauth_tokens(self):
        """Test OAuth token detection"""
        migration_tool = MigrationTool()

        # No tokens
        self.assertFalse(migration_tool.check_oauth_tokens())

        # Create token file
        os.makedirs('data/google-drive-service', exist_ok=True)
        with open('data/google-drive-service/google-drive-token.json', 'w') as f:
            json.dump({'token': 'test'}, f)

        self.assertTrue(migration_tool.check_oauth_tokens())

    def test_assess_config_complexity(self):
        """Test configuration complexity assessment"""
        migration_tool = MigrationTool()

        # Simple configuration
        with open('.env', 'w') as f:
            f.write("FOGIS_USERNAME=test\n")

        complexity = migration_tool.assess_config_complexity()
        self.assertEqual(complexity, "Simple")

        # Complex configuration
        with open('.env', 'w') as f:
            f.write("\n".join([f"VAR{i}=value{i}" for i in range(20)]))

        complexity = migration_tool.assess_config_complexity()
        self.assertEqual(complexity, "Complex")


if __name__ == '__main__':
    unittest.main()