#!/usr/bin/env python3
"""
Unit tests for ConfigValidator
Tests validation logic and error detection
"""

import unittest
import tempfile
import os
import yaml
from pathlib import Path

# Add the lib directory to the path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))

from config_validator import ConfigValidator, ConfigValidationError


class TestConfigValidator(unittest.TestCase):
    """Test cases for ConfigValidator class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Valid configuration
        self.valid_config = {
            'metadata': {'version': '2.0'},
            'fogis': {
                'username': 'test_user',
                'password': 'test_pass',
                'referee_number': 12345
            },
            'google': {
                'oauth': {
                    'client_type': 'web_application',
                    'scopes': [
                        'https://www.googleapis.com/auth/calendar',
                        'https://www.googleapis.com/auth/contacts',
                        'https://www.googleapis.com/auth/drive'
                    ]
                },
                'calendar': {
                    'calendar_id': 'primary'
                }
            },
            'services': {
                'ports': {
                    'api_client': 9086,
                    'match_processor': 9082,
                    'calendar_sync': 9083
                },
                'processing': {
                    'min_referees_for_whatsapp': 2,
                    'match_check_schedule': '0 * * * *'
                },
                'logging': {
                    'level': 'INFO'
                }
            },
            'system': {
                'docker': {
                    'restart_policy': 'unless-stopped'
                }
            }
        }

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)

    def test_load_valid_config(self):
        """Test loading valid configuration"""
        with open('fogis-config.yaml', 'w') as f:
            yaml.dump(self.valid_config, f)

        validator = ConfigValidator()
        self.assertEqual(validator.config['fogis']['username'], 'test_user')

    def test_load_missing_config(self):
        """Test loading missing configuration file"""
        with self.assertRaises(ConfigValidationError):
            ConfigValidator()

    def test_validate_complete_config(self):
        """Test validation of complete, valid configuration"""
        with open('fogis-config.yaml', 'w') as f:
            yaml.dump(self.valid_config, f)

        validator = ConfigValidator()
        errors, warnings = validator.validate_config()

        self.assertEqual(len(errors), 0)
        # May have warnings but no errors

    def test_validate_missing_sections(self):
        """Test validation with missing required sections"""
        incomplete_config = {
            'fogis': {
                'username': 'test_user'
            }
        }

        with open('fogis-config.yaml', 'w') as f:
            yaml.dump(incomplete_config, f)

        validator = ConfigValidator()
        errors, warnings = validator.validate_config()

        # Should have errors for missing sections
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('Missing required section' in error for error in errors))

    def test_validate_fogis_credentials(self):
        """Test FOGIS credentials validation"""
        # Test missing credentials
        config_missing_creds = self.valid_config.copy()
        config_missing_creds['fogis'] = {}

        with open('fogis-config.yaml', 'w') as f:
            yaml.dump(config_missing_creds, f)

        validator = ConfigValidator()
        errors = validator.validate_fogis_credentials()

        self.assertGreater(len(errors), 0)
        self.assertTrue(any('Missing FOGIS credential' in error for error in errors))

        # Test invalid referee number
        config_invalid_referee = self.valid_config.copy()
        config_invalid_referee['fogis']['referee_number'] = 'invalid'

        with open('fogis-config.yaml', 'w') as f:
            yaml.dump(config_invalid_referee, f)

        validator = ConfigValidator()
        errors = validator.validate_fogis_credentials()

        self.assertTrue(any('must be a valid integer' in error for error in errors))

    def test_validate_google_oauth_missing_section(self):
        """Test Google OAuth configuration validation - missing OAuth section"""
        # Test missing OAuth section
        import copy
        config_no_oauth = copy.deepcopy(self.valid_config)
        del config_no_oauth['google']['oauth']

        with open('fogis-config.yaml', 'w') as f:
            yaml.dump(config_no_oauth, f)

        validator = ConfigValidator()
        errors, warnings = validator.validate_google_oauth()

        self.assertTrue(any('Missing Google OAuth configuration' in error for error in errors))

    def test_validate_google_oauth_missing_scopes(self):
        """Test Google OAuth configuration validation - missing scopes"""
        # Test missing scopes
        import copy
        config_missing_scopes = copy.deepcopy(self.valid_config)
        config_missing_scopes['google']['oauth']['scopes'] = ['https://www.googleapis.com/auth/calendar']

        with open('fogis-config.yaml', 'w') as f:
            yaml.dump(config_missing_scopes, f)

        validator = ConfigValidator()
        errors, warnings = validator.validate_google_oauth()

        self.assertTrue(any('Missing recommended OAuth scope' in warning for warning in warnings))

    def test_check_port_conflicts(self):
        """Test port conflict detection"""
        config_port_conflict = self.valid_config.copy()
        config_port_conflict['services']['ports']['match_processor'] = 9086  # Same as api_client

        with open('fogis-config.yaml', 'w') as f:
            yaml.dump(config_port_conflict, f)

        validator = ConfigValidator()
        errors = validator.check_port_conflicts()

        self.assertTrue(any('Port conflict detected' in error for error in errors))

    def test_validate_service_configuration(self):
        """Test service configuration validation"""
        # Test invalid log level
        config_invalid_log = self.valid_config.copy()
        config_invalid_log['services']['logging']['level'] = 'INVALID'

        with open('fogis-config.yaml', 'w') as f:
            yaml.dump(config_invalid_log, f)

        validator = ConfigValidator()
        warnings = validator.validate_service_configuration()

        self.assertTrue(any('Invalid log level' in warning for warning in warnings))

        # Test invalid cron schedule
        config_invalid_cron = self.valid_config.copy()
        config_invalid_cron['services']['processing']['match_check_schedule'] = 'invalid cron'

        with open('fogis-config.yaml', 'w') as f:
            yaml.dump(config_invalid_cron, f)

        validator = ConfigValidator()
        warnings = validator.validate_service_configuration()

        self.assertTrue(any('Invalid cron schedule format' in warning for warning in warnings))

    def test_is_valid_cron(self):
        """Test cron expression validation"""
        # Create a dummy config file for the validator
        with open('fogis-config.yaml', 'w') as f:
            yaml.dump(self.valid_config, f)

        validator = ConfigValidator()

        # Valid cron expressions
        self.assertTrue(validator._is_valid_cron('0 * * * *'))
        self.assertTrue(validator._is_valid_cron('*/5 0 * * 1'))
        self.assertTrue(validator._is_valid_cron('0 9-17 * * 1-5'))

        # Invalid cron expressions
        self.assertFalse(validator._is_valid_cron('invalid'))
        self.assertFalse(validator._is_valid_cron('0 * * *'))  # Too few fields
        self.assertFalse(validator._is_valid_cron('0 * * * * *'))  # Too many fields

    def test_get_validation_summary(self):
        """Test validation summary generation"""
        # Create a dummy config file for the validator
        with open('fogis-config.yaml', 'w') as f:
            yaml.dump(self.valid_config, f)

        validator = ConfigValidator('fogis-config.yaml')

        errors = ['Error 1', 'Error 2']
        warnings = ['Warning 1']

        summary = validator.get_validation_summary(errors, warnings)

        self.assertIn('❌ Configuration validation failed', summary)
        self.assertIn('Error 1', summary)
        self.assertIn('⚠️  Configuration warnings', summary)
        self.assertIn('Warning 1', summary)

        # Test success case
        summary_success = validator.get_validation_summary([], [])
        self.assertIn('✅ Configuration validation passed', summary_success)


if __name__ == '__main__':
    unittest.main()