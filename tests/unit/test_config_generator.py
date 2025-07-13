#!/usr/bin/env python3
"""
Unit tests for ConfigGenerator
Tests .env and config.json generation from YAML
"""

import unittest
import tempfile
import os
import yaml
import json
from pathlib import Path
from unittest.mock import patch, mock_open

# Add the lib directory to the path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))

from config_generator import ConfigGenerator, ConfigGenerationError


class TestConfigGenerator(unittest.TestCase):
    """Test cases for ConfigGenerator class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Sample YAML configuration
        self.sample_config = {
            'metadata': {
                'version': '2.0',
                'created': '2025-01-12T10:00:00Z'
            },
            'fogis': {
                'username': 'test_user',
                'password': 'test_pass',
                'referee_number': 12345
            },
            'google': {
                'oauth': {
                    'scopes': [
                        'https://www.googleapis.com/auth/calendar',
                        'https://www.googleapis.com/auth/contacts',
                        'https://www.googleapis.com/auth/drive'
                    ]
                },
                'calendar': {
                    'calendar_id': 'primary',
                    'sync_tag': 'FOGIS_CALENDAR_SYNC',
                    'days_to_keep_past_events': 7
                },
                'drive': {
                    'folder_base': 'WhatsApp_Group_Assets'
                }
            },
            'services': {
                'ports': {
                    'api_client': 9086,
                    'match_processor': 9082,
                    'calendar_sync': 9083,
                    'calendar_auth': 9084,
                    'logo_combiner': 9088,
                    'google_drive': 9085,
                    'change_detector': 9080
                },
                'processing': {
                    'min_referees_for_whatsapp': 2,
                    'match_check_schedule': '0 * * * *',
                    'force_fresh_processing': True,
                    'service_interval': 300
                },
                'logging': {
                    'level': 'INFO',
                    'debug_mode': False,
                    'verbose_logging': False
                }
            },
            'system': {
                'docker': {
                    'restart_policy': 'unless-stopped'
                }
            },
            'notifications': {
                'email': {
                    'enabled': True,
                    'sender': 'test@example.com',
                    'receiver': 'admin@example.com',
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587
                }
            }
        }

        # Create the YAML config file
        with open('fogis-config.yaml', 'w') as f:
            yaml.dump(self.sample_config, f)

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)

    def test_load_config(self):
        """Test loading YAML configuration"""
        generator = ConfigGenerator()
        self.assertEqual(generator.config['fogis']['username'], 'test_user')
        self.assertEqual(generator.config['fogis']['referee_number'], 12345)

    def test_load_config_missing_file(self):
        """Test loading missing configuration file"""
        os.remove('fogis-config.yaml')

        with self.assertRaises(ConfigGenerationError):
            ConfigGenerator()

    def test_generate_env_file(self):
        """Test .env file generation"""
        generator = ConfigGenerator()
        env_content = generator.generate_env_file()

        # Check that .env file was created
        self.assertTrue(os.path.exists('.env'))

        # Check content
        self.assertIn('FOGIS_USERNAME=test_user', env_content)
        self.assertIn('FOGIS_PASSWORD=test_pass', env_content)
        self.assertIn('USER_REFEREE_NUMBER=12345', env_content)
        self.assertIn('API_CLIENT_PORT=9086', env_content)
        self.assertIn('LOG_LEVEL=INFO', env_content)
        self.assertIn('GOOGLE_CALENDAR_ID=primary', env_content)

    def test_generate_docker_compose_env(self):
        """Test docker-compose environment generation"""
        generator = ConfigGenerator()
        env_vars = generator.generate_docker_compose_env()

        # Check required environment variables
        self.assertEqual(env_vars['FOGIS_USERNAME'], 'test_user')
        self.assertEqual(env_vars['FOGIS_PASSWORD'], 'test_pass')
        self.assertEqual(env_vars['USER_REFEREE_NUMBER'], '12345')
        self.assertEqual(env_vars['LOG_LEVEL'], 'INFO')
        self.assertEqual(env_vars['API_CLIENT_PORT'], '9086')
        self.assertEqual(env_vars['DEBUG_MODE'], '0')

    def test_generate_calendar_config(self):
        """Test calendar config.json generation"""
        generator = ConfigGenerator()

        # Create the output directory
        os.makedirs('fogis-calendar-phonebook-sync', exist_ok=True)

        config = generator.generate_calendar_config()

        # Check that config.json was created
        self.assertTrue(os.path.exists('fogis-calendar-phonebook-sync/config.json'))

        # Check content
        self.assertEqual(config['CALENDAR_ID'], 'primary')
        self.assertEqual(config['SYNC_TAG'], 'FOGIS_CALENDAR_SYNC')
        self.assertEqual(config['USER_REFEREE_NUMBER'], 12345)
        self.assertEqual(config['AUTH_SERVER_PORT'], 9084)
        self.assertEqual(config['NOTIFICATION_METHOD'], 'email')
        self.assertEqual(config['NOTIFICATION_EMAIL_SENDER'], 'test@example.com')

    def test_generate_all_configs(self):
        """Test generating all configuration files"""
        generator = ConfigGenerator()

        # Create required directories
        os.makedirs('fogis-calendar-phonebook-sync', exist_ok=True)
        os.makedirs('credentials', exist_ok=True)

        # Create a dummy credentials file
        with open('credentials.json', 'w') as f:
            json.dump({'type': 'service_account'}, f)

        success = generator.generate_all_configs()

        self.assertTrue(success)
        self.assertTrue(os.path.exists('.env'))
        self.assertTrue(os.path.exists('fogis-calendar-phonebook-sync/config.json'))

    def test_validate_generated_configs(self):
        """Test validation of generated configurations"""
        generator = ConfigGenerator()

        # Generate configs first
        generator.generate_env_file()

        os.makedirs('fogis-calendar-phonebook-sync', exist_ok=True)
        generator.generate_calendar_config()

        # Validation should pass
        self.assertTrue(generator.validate_generated_configs())

    def test_validate_generated_configs_missing_env(self):
        """Test validation with missing .env file"""
        generator = ConfigGenerator()

        # Validation should fail without .env file
        self.assertFalse(generator.validate_generated_configs())


if __name__ == '__main__':
    unittest.main()