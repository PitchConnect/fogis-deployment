"""
Unit tests for the credential wizard module.
"""

import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lib.credential_wizard import CredentialWizard


class TestCredentialWizard:
    """Test cases for CredentialWizard class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.wizard = CredentialWizard()

    def test_wizard_initialization(self):
        """Test wizard initialization."""
        assert self.wizard.config == {}
        assert self.wizard.oauth_manager is None
        assert self.wizard.calendar_manager is None
        assert self.wizard.fogis_manager is None
        assert self.wizard.storage is None
        assert self.wizard.validator is None

    def test_print_methods(self, capsys):
        """Test print utility methods."""
        self.wizard.print_header("Test Header")
        captured = capsys.readouterr()
        assert "Test Header" in captured.out
        assert "🔐" in captured.out

        self.wizard.print_step(1, "Test Step")
        captured = capsys.readouterr()
        assert "Step 1: Test Step" in captured.out
        assert "📋" in captured.out

        self.wizard.print_success("Success message")
        captured = capsys.readouterr()
        assert "✅ Success message" in captured.out

        self.wizard.print_warning("Warning message")
        captured = capsys.readouterr()
        assert "⚠️  Warning message" in captured.out

        self.wizard.print_error("Error message")
        captured = capsys.readouterr()
        assert "❌ Error message" in captured.out

        self.wizard.print_info("Info message")
        captured = capsys.readouterr()
        assert "ℹ️  Info message" in captured.out

    @patch('builtins.input')
    def test_welcome_screen_accept(self, mock_input):
        """Test welcome screen with user acceptance."""
        mock_input.return_value = 'y'
        result = self.wizard.welcome_screen()
        assert result is True

    @patch('builtins.input')
    def test_welcome_screen_decline(self, mock_input):
        """Test welcome screen with user decline."""
        mock_input.return_value = 'n'
        result = self.wizard.welcome_screen()
        assert result is False

    @patch('builtins.input')
    def test_welcome_screen_invalid_then_accept(self, mock_input):
        """Test welcome screen with invalid input then acceptance."""
        mock_input.side_effect = ['invalid', 'y']
        result = self.wizard.welcome_screen()
        assert result is True

    @patch('os.path.exists')
    @patch('lib.credential_wizard.GoogleOAuthManager')
    def test_setup_google_oauth_no_credentials_file(self, mock_oauth_manager, mock_exists):
        """Test Google OAuth setup when credentials file doesn't exist."""
        mock_exists.return_value = False
        
        with patch('builtins.input', return_value=''):
            result = self.wizard.setup_google_oauth()
            assert result is False

    @patch('os.path.exists')
    @patch('lib.credential_wizard.GoogleOAuthManager')
    @patch('builtins.input')
    def test_setup_google_oauth_success(self, mock_input, mock_oauth_manager, mock_exists):
        """Test successful Google OAuth setup."""
        mock_exists.return_value = True
        mock_input.return_value = ''
        
        # Mock OAuth manager
        mock_manager = Mock()
        mock_manager.validate_credentials_file.return_value = True
        mock_manager.get_credentials.return_value = Mock()
        mock_manager.test_credentials.return_value = {
            'calendar': True,
            'drive': True,
            'contacts': True
        }
        mock_oauth_manager.return_value = mock_manager
        
        result = self.wizard.setup_google_oauth()
        assert result is True
        assert self.wizard.oauth_manager is not None

    @patch('os.path.exists')
    @patch('lib.credential_wizard.GoogleOAuthManager')
    def test_setup_google_oauth_invalid_credentials(self, mock_oauth_manager, mock_exists):
        """Test Google OAuth setup with invalid credentials."""
        mock_exists.return_value = True
        
        # Mock OAuth manager with invalid credentials
        mock_manager = Mock()
        mock_manager.validate_credentials_file.return_value = False
        mock_oauth_manager.return_value = mock_manager
        
        result = self.wizard.setup_google_oauth()
        assert result is False

    @patch('builtins.input')
    def test_setup_calendar_integration_create_new(self, mock_input):
        """Test calendar integration with new calendar creation."""
        mock_input.return_value = '1'
        
        with patch.object(self.wizard, '_create_new_calendar', return_value=True):
            result = self.wizard.setup_calendar_integration()
            assert result is True

    @patch('builtins.input')
    def test_setup_calendar_integration_use_existing(self, mock_input):
        """Test calendar integration with existing calendar."""
        mock_input.return_value = '2'
        
        with patch.object(self.wizard, '_use_existing_calendar', return_value=True):
            result = self.wizard.setup_calendar_integration()
            assert result is True

    @patch('builtins.input')
    def test_setup_calendar_integration_skip(self, mock_input):
        """Test calendar integration skip option."""
        mock_input.return_value = '3'
        
        result = self.wizard.setup_calendar_integration()
        assert result is True

    @patch('builtins.input')
    @patch('getpass.getpass')
    @patch('lib.credential_wizard.FogisAuthManager')
    def test_setup_fogis_auth_success(self, mock_fogis_manager, mock_getpass, mock_input):
        """Test successful FOGIS authentication setup."""
        mock_input.side_effect = ['testuser', '12345']
        mock_getpass.return_value = 'testpass'
        
        # Mock FOGIS manager
        mock_manager = Mock()
        mock_manager.test_connection.return_value = True
        mock_manager.authenticate.return_value = {
            'success': True,
            'referee_info': {'referee_number': '12345', 'name': 'Test User'}
        }
        mock_fogis_manager.return_value = mock_manager
        
        result = self.wizard.setup_fogis_auth()
        assert result is True
        assert self.wizard.config['fogis_username'] == 'testuser'
        assert self.wizard.config['referee_number'] == '12345'

    @patch('builtins.input')
    @patch('getpass.getpass')
    def test_setup_fogis_auth_empty_username(self, mock_getpass, mock_input):
        """Test FOGIS authentication with empty username."""
        mock_input.return_value = ''
        mock_getpass.return_value = 'testpass'
        
        result = self.wizard.setup_fogis_auth()
        assert result is False

    @patch('builtins.input')
    @patch('getpass.getpass')
    def test_setup_fogis_auth_empty_password(self, mock_getpass, mock_input):
        """Test FOGIS authentication with empty password."""
        mock_input.return_value = 'testuser'
        mock_getpass.return_value = ''
        
        result = self.wizard.setup_fogis_auth()
        assert result is False

    def test_validate_and_test_all_pass(self):
        """Test validation when all tests pass."""
        with patch.object(self.wizard, '_test_google_oauth', return_value=True), \
             patch.object(self.wizard, '_test_calendar_access', return_value=True), \
             patch.object(self.wizard, '_test_fogis_auth', return_value=True), \
             patch.object(self.wizard, '_test_credential_storage', return_value=True):
            
            result = self.wizard.validate_and_test()
            assert result is True

    def test_validate_and_test_some_fail(self):
        """Test validation when some tests fail."""
        with patch.object(self.wizard, '_test_google_oauth', return_value=True), \
             patch.object(self.wizard, '_test_calendar_access', return_value=False), \
             patch.object(self.wizard, '_test_fogis_auth', return_value=True), \
             patch.object(self.wizard, '_test_credential_storage', return_value=True):
            
            result = self.wizard.validate_and_test()
            assert result is False

    def test_test_google_oauth_no_manager(self):
        """Test Google OAuth test without manager."""
        result = self.wizard._test_google_oauth()
        assert result is False

    def test_test_calendar_access_no_manager(self):
        """Test calendar access test without manager."""
        result = self.wizard._test_calendar_access()
        assert result is False

    def test_test_fogis_auth_no_manager(self):
        """Test FOGIS auth test without manager."""
        result = self.wizard._test_fogis_auth()
        assert result is False

    @patch('lib.credential_wizard.SecureCredentialStore')
    def test_test_credential_storage_success(self, mock_storage_class):
        """Test successful credential storage test."""
        mock_storage = Mock()
        mock_storage.store_credentials.return_value = True
        mock_storage.retrieve_credentials.return_value = {'test': 'data', 'timestamp': 123456}
        mock_storage.delete_credentials.return_value = True
        mock_storage_class.return_value = mock_storage
        
        result = self.wizard._test_credential_storage()
        assert result is True

    @patch('lib.credential_wizard.SecureCredentialStore')
    def test_save_configuration_success(self, mock_storage_class):
        """Test successful configuration save."""
        mock_storage = Mock()
        mock_storage.store_credentials.return_value = True
        mock_storage_class.return_value = mock_storage
        
        # Set up wizard state
        self.wizard.oauth_manager = Mock()
        self.wizard.oauth_manager.credentials = Mock()
        self.wizard.oauth_manager.get_token_info.return_value = {'valid': True}
        self.wizard.config = {
            'calendar_id': 'test-calendar',
            'calendar_name': 'Test Calendar',
            'fogis_username': 'testuser',
            'fogis_password': 'testpass',
            'referee_number': '12345'
        }
        
        with patch.object(self.wizard, '_update_env_file'), \
             patch.object(self.wizard, '_setup_service_credentials'):
            
            result = self.wizard.save_configuration()
            assert result is True

    def test_update_env_var_new_variable(self):
        """Test adding new environment variable."""
        env_content = ['EXISTING_VAR=value\n']
        self.wizard._update_env_var(env_content, 'NEW_VAR', 'new_value')
        
        assert 'NEW_VAR=new_value\n' in env_content
        assert len(env_content) == 2

    def test_update_env_var_existing_variable(self):
        """Test updating existing environment variable."""
        env_content = ['EXISTING_VAR=old_value\n', 'OTHER_VAR=other\n']
        self.wizard._update_env_var(env_content, 'EXISTING_VAR', 'new_value')
        
        assert 'EXISTING_VAR=new_value\n' in env_content
        assert 'EXISTING_VAR=old_value\n' not in env_content
        assert len(env_content) == 2

    @patch('builtins.input')
    def test_run_complete_success(self, mock_input):
        """Test complete wizard run with success."""
        mock_input.return_value = 'y'
        
        with patch.object(self.wizard, 'welcome_screen', return_value=True), \
             patch.object(self.wizard, 'setup_google_oauth', return_value=True), \
             patch.object(self.wizard, 'setup_calendar_integration', return_value=True), \
             patch.object(self.wizard, 'setup_fogis_auth', return_value=True), \
             patch.object(self.wizard, 'validate_and_test', return_value=True), \
             patch.object(self.wizard, 'save_configuration', return_value=True), \
             patch.object(self.wizard, 'completion_summary'):
            
            result = self.wizard.run()
            assert result == 0

    @patch('builtins.input')
    def test_run_user_decline(self, mock_input):
        """Test wizard run when user declines."""
        mock_input.return_value = 'n'
        
        with patch.object(self.wizard, 'welcome_screen', return_value=False):
            result = self.wizard.run()
            assert result == 0

    def test_run_oauth_failure(self):
        """Test wizard run with OAuth failure."""
        with patch.object(self.wizard, 'welcome_screen', return_value=True), \
             patch.object(self.wizard, 'setup_google_oauth', return_value=False):
            
            result = self.wizard.run()
            assert result == 1

    def test_run_keyboard_interrupt(self):
        """Test wizard run with keyboard interrupt."""
        with patch.object(self.wizard, 'welcome_screen', side_effect=KeyboardInterrupt):
            result = self.wizard.run()
            assert result == 1
