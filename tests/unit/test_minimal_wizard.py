"""
Unit tests for the minimal credential wizard module.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import os
import sys
import tempfile
import shutil

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lib.minimal_wizard import MinimalCredentialWizard


class TestMinimalCredentialWizard:
    """Test cases for MinimalCredentialWizard class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.wizard = MinimalCredentialWizard()

    def test_wizard_initialization(self):
        """Test wizard initialization."""
        assert self.wizard.config == {}

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
    @patch('builtins.open', new_callable=mock_open)
    def test_setup_google_oauth_success(self, mock_file, mock_exists):
        """Test successful Google OAuth setup."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = '{"installed": {"client_id": "test", "client_secret": "secret"}}'
        
        with patch('json.load', return_value={'installed': {'client_id': 'test', 'client_secret': 'secret'}}):
            result = self.wizard.setup_google_oauth()
            assert result is True
            assert self.wizard.config['google_credentials'] == 'credentials.json'

    @patch('os.path.exists')
    @patch('builtins.input')
    def test_setup_google_oauth_missing_file(self, mock_input, mock_exists):
        """Test Google OAuth setup when credentials file is missing."""
        mock_exists.return_value = False
        mock_input.return_value = ''
        
        result = self.wizard.setup_google_oauth()
        assert result is False

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.input')
    def test_setup_google_oauth_invalid_format(self, mock_input, mock_file, mock_exists):
        """Test Google OAuth setup with invalid credentials format."""
        mock_exists.return_value = True
        mock_input.return_value = ''
        
        with patch('json.load', return_value={'invalid': 'format'}):
            result = self.wizard.setup_google_oauth()
            assert result is False

    @patch('builtins.input')
    @patch('time.strftime')
    def test_setup_calendar_integration_create_new(self, mock_strftime, mock_input):
        """Test calendar integration with new calendar creation."""
        mock_strftime.return_value = '2024'
        mock_input.return_value = '1'
        
        result = self.wizard.setup_calendar_integration()
        assert result is True
        assert 'calendar_id' in self.wizard.config
        assert 'calendar_name' in self.wizard.config
        assert 'FOGIS Matches - 2024' in self.wizard.config['calendar_name']

    @patch('builtins.input')
    def test_setup_calendar_integration_use_existing(self, mock_input):
        """Test calendar integration with existing calendar."""
        mock_input.side_effect = ['2', 'test-calendar-id']
        
        result = self.wizard.setup_calendar_integration()
        assert result is True
        assert self.wizard.config['calendar_id'] == 'test-calendar-id'

    @patch('builtins.input')
    def test_setup_calendar_integration_skip(self, mock_input):
        """Test calendar integration skip option."""
        mock_input.return_value = '3'
        
        result = self.wizard.setup_calendar_integration()
        assert result is True

    @patch('builtins.input')
    @patch('getpass.getpass')
    @patch('time.sleep')
    def test_setup_fogis_auth_success(self, mock_sleep, mock_getpass, mock_input):
        """Test successful FOGIS authentication setup."""
        mock_input.side_effect = ['testuser', '12345']
        mock_getpass.return_value = 'testpass'
        mock_sleep.return_value = None
        
        result = self.wizard.setup_fogis_auth()
        assert result is True
        assert self.wizard.config['fogis_username'] == 'testuser'
        assert self.wizard.config['fogis_password'] == 'testpass'
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

    @patch('builtins.input')
    @patch('getpass.getpass')
    def test_setup_fogis_auth_empty_referee_number(self, mock_getpass, mock_input):
        """Test FOGIS authentication with empty referee number."""
        mock_input.side_effect = ['testuser', '']
        mock_getpass.return_value = 'testpass'
        
        result = self.wizard.setup_fogis_auth()
        assert result is False

    @patch('os.makedirs')
    @patch('os.chmod')
    def test_save_configuration_success(self, mock_chmod, mock_makedirs):
        """Test successful configuration save."""
        self.wizard.config = {
            'fogis_username': 'testuser',
            'fogis_password': 'testpass',
            'referee_number': '12345',
            'calendar_id': 'test-calendar'
        }
        
        with patch.object(self.wizard, '_update_env_file'):
            result = self.wizard.save_configuration()
            assert result is True
            
            # Verify directories are created
            mock_makedirs.assert_any_call('data/fogis-calendar-phonebook-sync', exist_ok=True)
            mock_makedirs.assert_any_call('data/google-drive-service', exist_ok=True)

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

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='OLD_VAR=old_value\n')
    @patch('os.chmod')
    def test_update_env_file(self, mock_chmod, mock_file, mock_exists):
        """Test updating .env file."""
        mock_exists.return_value = True
        self.wizard.config = {
            'fogis_username': 'testuser',
            'fogis_password': 'testpass',
            'referee_number': '12345',
            'calendar_id': 'test-calendar'
        }
        
        self.wizard._update_env_file()
        
        # Verify file operations
        mock_file.assert_called()
        mock_chmod.assert_called_with('.env', 0o600)

    def test_completion_summary(self, capsys):
        """Test completion summary display."""
        self.wizard.config = {
            'calendar_id': 'test-calendar',
            'calendar_name': 'Test Calendar'
        }
        
        self.wizard.completion_summary()
        captured = capsys.readouterr()
        
        assert "Setup Complete!" in captured.out
        assert "Test Calendar" in captured.out
        assert "Next Steps:" in captured.out

    @patch('builtins.input')
    def test_run_complete_success(self, mock_input):
        """Test complete wizard run with success."""
        mock_input.return_value = 'y'
        
        with patch.object(self.wizard, 'welcome_screen', return_value=True), \
             patch.object(self.wizard, 'setup_google_oauth', return_value=True), \
             patch.object(self.wizard, 'setup_calendar_integration', return_value=True), \
             patch.object(self.wizard, 'setup_fogis_auth', return_value=True), \
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

    def test_run_calendar_failure(self):
        """Test wizard run with calendar setup failure."""
        with patch.object(self.wizard, 'welcome_screen', return_value=True), \
             patch.object(self.wizard, 'setup_google_oauth', return_value=True), \
             patch.object(self.wizard, 'setup_calendar_integration', return_value=False):
            
            result = self.wizard.run()
            assert result == 1

    def test_run_fogis_failure(self):
        """Test wizard run with FOGIS setup failure."""
        with patch.object(self.wizard, 'welcome_screen', return_value=True), \
             patch.object(self.wizard, 'setup_google_oauth', return_value=True), \
             patch.object(self.wizard, 'setup_calendar_integration', return_value=True), \
             patch.object(self.wizard, 'setup_fogis_auth', return_value=False):
            
            result = self.wizard.run()
            assert result == 1

    def test_run_save_failure(self):
        """Test wizard run with save configuration failure."""
        with patch.object(self.wizard, 'welcome_screen', return_value=True), \
             patch.object(self.wizard, 'setup_google_oauth', return_value=True), \
             patch.object(self.wizard, 'setup_calendar_integration', return_value=True), \
             patch.object(self.wizard, 'setup_fogis_auth', return_value=True), \
             patch.object(self.wizard, 'save_configuration', return_value=False):
            
            result = self.wizard.run()
            assert result == 1

    def test_run_keyboard_interrupt(self):
        """Test wizard run with keyboard interrupt."""
        with patch.object(self.wizard, 'welcome_screen', side_effect=KeyboardInterrupt):
            result = self.wizard.run()
            assert result == 1

    def test_run_unexpected_exception(self):
        """Test wizard run with unexpected exception."""
        with patch.object(self.wizard, 'welcome_screen', side_effect=Exception("Unexpected error")):
            result = self.wizard.run()
            assert result == 1
