#!/usr/bin/env python3
"""
Unit tests for InteractiveSetup
Tests interactive setup wizard functionality
"""

import unittest
import tempfile
import os
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from io import StringIO

# Add the lib directory to the path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))

from interactive_setup import InteractiveSetup, SetupWizardError


class TestInteractiveSetup(unittest.TestCase):
    """Test cases for InteractiveSetup class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        self.setup_wizard = InteractiveSetup()

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)

    def test_initialize_config_structure(self):
        """Test configuration structure initialization"""
        self.setup_wizard.initialize_config_structure()

        # Check required sections exist
        self.assertIn('metadata', self.setup_wizard.config)
        self.assertIn('fogis', self.setup_wizard.config)
        self.assertIn('google', self.setup_wizard.config)
        self.assertIn('services', self.setup_wizard.config)
        self.assertIn('system', self.setup_wizard.config)

        # Check metadata
        self.assertEqual(self.setup_wizard.config['metadata']['version'], '2.0')
        self.assertIn('Interactive Setup', self.setup_wizard.config['metadata']['description'])

    def test_check_existing_configuration(self):
        """Test existing configuration detection"""
        # No existing configuration
        self.assertFalse(self.setup_wizard.check_existing_configuration())

        # Create existing files
        with open('fogis-config.yaml', 'w') as f:
            yaml.dump({'test': 'config'}, f)

        self.assertTrue(self.setup_wizard.check_existing_configuration())

        # Test with .env file
        os.remove('fogis-config.yaml')
        with open('.env', 'w') as f:
            f.write('TEST=value')

        self.assertTrue(self.setup_wizard.check_existing_configuration())

    @patch('builtins.input')
    def test_setup_fogis_credentials(self, mock_input):
        """Test FOGIS credentials setup"""
        # Mock user inputs
        mock_input.side_effect = ['test_user', 'test_pass', '12345']

        self.setup_wizard.initialize_config_structure()
        result = self.setup_wizard.setup_fogis_credentials()

        self.assertTrue(result)
        self.assertEqual(self.setup_wizard.config['fogis']['username'], 'test_user')
        self.assertEqual(self.setup_wizard.config['fogis']['password'], 'test_pass')
        self.assertEqual(self.setup_wizard.config['fogis']['referee_number'], 12345)
        self.assertTrue(self.setup_wizard.setup_progress['fogis_credentials'])

    @patch('builtins.input')
    def test_setup_fogis_credentials_validation(self, mock_input):
        """Test FOGIS credentials validation"""
        # Test empty username handling
        mock_input.side_effect = ['', 'test_user', 'test_pass', '12345']

        self.setup_wizard.initialize_config_structure()
        result = self.setup_wizard.setup_fogis_credentials()

        self.assertTrue(result)
        self.assertEqual(self.setup_wizard.config['fogis']['username'], 'test_user')

    @patch('builtins.input')
    def test_setup_google_oauth(self, mock_input):
        """Test Google OAuth setup"""
        # Mock user inputs: client type, calendar ID, drive folder
        mock_input.side_effect = ['1', 'primary', 'WhatsApp_Assets']

        self.setup_wizard.initialize_config_structure()
        result = self.setup_wizard.setup_google_oauth()

        self.assertTrue(result)
        self.assertEqual(self.setup_wizard.config['google']['oauth']['client_type'], 'web_application')
        self.assertEqual(self.setup_wizard.config['google']['calendar']['calendar_id'], 'primary')
        self.assertEqual(self.setup_wizard.config['google']['drive']['folder_base'], 'WhatsApp_Assets')
        self.assertTrue(self.setup_wizard.setup_progress['google_oauth'])

    @patch('interactive_setup.InteractiveSetup.ask_yes_no')
    @patch('builtins.input')
    def test_setup_service_configuration(self, mock_input, mock_ask):
        """Test service configuration setup"""
        # Mock inputs: don't customize ports, min referees, schedule, log level
        mock_ask.return_value = False  # Don't customize ports
        mock_input.side_effect = ['2', '0 * * * *', '1']  # min_refs, schedule, log_level

        self.setup_wizard.initialize_config_structure()
        result = self.setup_wizard.setup_service_configuration()

        self.assertTrue(result)
        self.assertEqual(self.setup_wizard.config['services']['processing']['min_referees_for_whatsapp'], 2)
        self.assertEqual(self.setup_wizard.config['services']['logging']['level'], 'INFO')
        self.assertTrue(self.setup_wizard.setup_progress['service_ports'])

    @patch('interactive_setup.InteractiveSetup.ask_yes_no')
    @patch('builtins.input')
    def test_setup_system_settings(self, mock_input, mock_ask):
        """Test system settings setup"""
        # Mock inputs: restart policy, no email notifications
        mock_input.side_effect = ['1']  # restart policy
        mock_ask.return_value = False  # no email notifications

        self.setup_wizard.initialize_config_structure()
        result = self.setup_wizard.setup_system_settings()

        self.assertTrue(result)
        self.assertEqual(self.setup_wizard.config['system']['docker']['restart_policy'], 'unless-stopped')
        self.assertTrue(self.setup_wizard.setup_progress['system_settings'])

    @patch('interactive_setup.InteractiveSetup.ask_yes_no')
    def test_review_and_save_configuration(self, mock_ask):
        """Test configuration review and save"""
        self.setup_wizard.initialize_config_structure()
        self.setup_wizard.config['fogis']['username'] = 'test_user'
        self.setup_wizard.config['fogis']['referee_number'] = 12345

        # Mock user confirms save
        mock_ask.return_value = True

        result = self.setup_wizard.review_and_save_configuration()

        self.assertTrue(result)
        self.assertTrue(os.path.exists('fogis-config.yaml'))

        # Verify saved content
        with open('fogis-config.yaml', 'r') as f:
            saved_config = yaml.safe_load(f)

        self.assertEqual(saved_config['fogis']['username'], 'test_user')
        self.assertEqual(saved_config['fogis']['referee_number'], 12345)

    def test_validate_cron_schedule(self):
        """Test cron schedule validation"""
        # Valid schedules
        self.assertTrue(self.setup_wizard.validate_cron_schedule('0 * * * *'))
        self.assertTrue(self.setup_wizard.validate_cron_schedule('*/5 0 * * 1'))
        self.assertTrue(self.setup_wizard.validate_cron_schedule('0 9-17 * * 1-5'))

        # Invalid schedules
        self.assertFalse(self.setup_wizard.validate_cron_schedule('invalid'))
        self.assertFalse(self.setup_wizard.validate_cron_schedule('0 * * *'))  # Too few fields
        self.assertFalse(self.setup_wizard.validate_cron_schedule('0 * * * * *'))  # Too many fields

    @patch('builtins.input')
    def test_ask_yes_no(self, mock_input):
        """Test yes/no question handling"""
        # Test yes responses
        mock_input.return_value = 'y'
        self.assertTrue(self.setup_wizard.ask_yes_no("Test question?"))

        mock_input.return_value = 'yes'
        self.assertTrue(self.setup_wizard.ask_yes_no("Test question?"))

        # Test no responses
        mock_input.return_value = 'n'
        self.assertFalse(self.setup_wizard.ask_yes_no("Test question?"))

        mock_input.return_value = 'no'
        self.assertFalse(self.setup_wizard.ask_yes_no("Test question?"))

        # Test default handling
        mock_input.return_value = ''
        self.assertTrue(self.setup_wizard.ask_yes_no("Test question?", default=True))
        self.assertFalse(self.setup_wizard.ask_yes_no("Test question?", default=False))

    @patch('builtins.input')
    def test_setup_custom_ports(self, mock_input):
        """Test custom port setup"""
        # Mock port inputs (use defaults for most, custom for one)
        mock_input.side_effect = ['', '', '', '', '9999', '', '']  # Custom port for logo_combiner

        self.setup_wizard.initialize_config_structure()
        self.setup_wizard.setup_custom_ports()

        # Check that custom port was set
        self.assertEqual(self.setup_wizard.config['services']['ports']['logo_combiner'], 9999)
        # Check that defaults were kept for others
        self.assertEqual(self.setup_wizard.config['services']['ports']['api_client'], 9086)

    @patch('interactive_setup.InteractiveSetup.ask_yes_no')
    @patch('builtins.input')
    def test_setup_email_notifications(self, mock_input, mock_ask):
        """Test email notification setup"""
        mock_input.side_effect = ['sender@test.com', 'receiver@test.com', 'smtp.test.com', '587']

        self.setup_wizard.initialize_config_structure()
        self.setup_wizard.setup_email_notifications()

        self.assertTrue(self.setup_wizard.config['notifications']['email']['enabled'])
        self.assertEqual(self.setup_wizard.config['notifications']['email']['sender'], 'sender@test.com')
        self.assertEqual(self.setup_wizard.config['notifications']['email']['receiver'], 'receiver@test.com')
        self.assertEqual(self.setup_wizard.config['notifications']['email']['smtp_server'], 'smtp.test.com')
        self.assertEqual(self.setup_wizard.config['notifications']['email']['smtp_port'], 587)

    def test_display_setup_progress(self):
        """Test setup progress display"""
        # Set some progress
        self.setup_wizard.setup_progress['fogis_credentials'] = True
        self.setup_wizard.setup_progress['google_oauth'] = False

        # This should not raise an exception
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            self.setup_wizard.display_setup_progress()
            output = mock_stdout.getvalue()

            self.assertIn('Setup Progress', output)
            self.assertIn('✅', output)  # Completed item
            self.assertIn('⏳', output)  # Pending item


if __name__ == '__main__':
    unittest.main()