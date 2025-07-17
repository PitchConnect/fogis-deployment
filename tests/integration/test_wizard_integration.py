"""
Integration tests for the credential wizard.
"""

import os
import shutil
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from lib.credential_wizard import CredentialWizard
from lib.secure_storage import SecureCredentialStore


class TestCredentialWizardIntegration:
    """Integration test cases for CredentialWizard."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.wizard = CredentialWizard()

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("builtins.input")
    @patch("lib.credential_wizard.GoogleOAuthManager")
    @patch("lib.credential_wizard.CalendarManager")
    @patch("lib.credential_wizard.FogisAuthManager")
    @patch("lib.credential_wizard.SecureCredentialStore")
    @patch("os.path.exists")
    def test_complete_wizard_flow_success(
        self,
        mock_exists,
        mock_storage_class,
        mock_fogis_class,
        mock_calendar_class,
        mock_oauth_class,
        mock_input,
    ):
        """Test complete wizard flow with all components working."""
        # Mock user inputs
        mock_input.side_effect = [
            "y",  # Welcome screen
            "1",  # Create new calendar
            "n",  # Don't share calendar
            "testuser",  # FOGIS username
            "12345",  # Referee number
            "n",  # Don't retry failed tests
        ]

        # Mock file existence
        mock_exists.return_value = True

        # Mock OAuth manager
        mock_oauth = Mock()
        mock_oauth.validate_credentials_file.return_value = True
        mock_oauth.get_credentials.return_value = Mock()
        mock_oauth.test_credentials.return_value = {
            "calendar": True,
            "drive": True,
            "contacts": True,
        }
        mock_oauth.credentials = Mock()
        mock_oauth.get_token_info.return_value = {"valid": True}
        mock_oauth_class.return_value = mock_oauth

        # Mock calendar manager
        mock_calendar = Mock()
        mock_calendar.create_fogis_calendar.return_value = "test-calendar-id"
        mock_calendar.validate_calendar_access.return_value = {
            "valid": True,
            "calendar_info": {"summary": "Test Calendar"},
        }
        mock_calendar.create_test_event.return_value = "test-event-id"
        mock_calendar_class.return_value = mock_calendar

        # Mock FOGIS manager
        mock_fogis = Mock()
        mock_fogis.test_connection.return_value = True
        mock_fogis.authenticate.return_value = {
            "success": True,
            "referee_info": {"referee_number": "12345", "name": "Test User"},
        }
        mock_fogis.validate_session.return_value = True
        mock_fogis_class.return_value = mock_fogis

        # Mock storage
        mock_storage = Mock()
        mock_storage.store_credentials.return_value = True
        mock_storage.retrieve_credentials.return_value = {"test": "data"}
        mock_storage.delete_credentials.return_value = True
        mock_storage_class.return_value = mock_storage

        # Mock getpass for password input
        with patch("getpass.getpass", return_value="testpass"), patch.object(
            self.wizard, "_update_env_file"
        ), patch.object(self.wizard, "_setup_service_credentials"):
            result = self.wizard.run()

            # Verify successful completion
            assert result == 0

            # Verify configuration was saved
            assert "fogis_username" in self.wizard.config
            assert "calendar_id" in self.wizard.config
            assert self.wizard.config["fogis_username"] == "testuser"
            assert self.wizard.config["calendar_id"] == "test-calendar-id"

    @patch("builtins.input")
    def test_wizard_user_cancellation(self, mock_input):
        """Test wizard cancellation by user."""
        mock_input.return_value = "n"  # User declines

        result = self.wizard.run()
        assert result == 0  # Should exit gracefully

    @patch("builtins.input")
    @patch("os.path.exists")
    def test_wizard_missing_credentials_file(self, mock_exists, mock_input):
        """Test wizard behavior when credentials file is missing."""
        mock_input.side_effect = ["y", ""]  # Accept wizard, then empty input for file
        mock_exists.return_value = False

        result = self.wizard.run()
        assert result == 1  # Should fail

    def test_secure_storage_integration(self):
        """Test secure storage integration."""
        # Create storage in test directory
        storage = SecureCredentialStore(storage_dir=self.test_dir)

        # Test data
        test_credentials = {
            "username": "testuser",
            "password": "testpass",
            "api_key": "test_key",
        }

        # Store and retrieve
        assert storage.store_credentials("test_service", test_credentials)
        retrieved = storage.retrieve_credentials("test_service")
        assert retrieved == test_credentials

        # Test encryption by checking file content
        credential_file = os.path.join(self.test_dir, "test_service.enc")
        assert os.path.exists(credential_file)

        # File should be encrypted (not readable as plain text)
        with open(credential_file, "rb") as f:
            content = f.read()
            assert b"testuser" not in content  # Should be encrypted
            assert b"testpass" not in content  # Should be encrypted

    @patch("lib.credential_wizard.GoogleOAuthManager")
    def test_oauth_manager_integration(self, mock_oauth_class):
        """Test OAuth manager integration."""
        # Mock OAuth manager
        mock_oauth = Mock()
        mock_oauth.validate_credentials_file.return_value = True
        mock_oauth.get_credentials.return_value = Mock()
        mock_oauth.test_credentials.return_value = {
            "calendar": True,
            "drive": True,
            "contacts": True,
        }
        mock_oauth_class.return_value = mock_oauth

        # Test OAuth setup
        with patch("os.path.exists", return_value=True), patch(
            "builtins.input", return_value=""
        ):
            result = self.wizard.setup_google_oauth()
            assert result is True
            assert self.wizard.oauth_manager is not None

    @patch("lib.credential_wizard.FogisAuthManager")
    def test_fogis_manager_integration(self, mock_fogis_class):
        """Test FOGIS manager integration."""
        # Mock FOGIS manager
        mock_fogis = Mock()
        mock_fogis.test_connection.return_value = True
        mock_fogis.authenticate.return_value = {
            "success": True,
            "referee_info": {"referee_number": "12345", "name": "Test User"},
        }
        mock_fogis_class.return_value = mock_fogis

        # Test FOGIS setup
        with patch("builtins.input", side_effect=["testuser", "12345"]), patch(
            "getpass.getpass", return_value="testpass"
        ):
            result = self.wizard.setup_fogis_auth()
            assert result is True
            assert self.wizard.fogis_manager is not None
            assert self.wizard.config["fogis_username"] == "testuser"

    def test_env_file_operations(self):
        """Test environment file operations."""
        # Create test .env file
        env_file = os.path.join(self.test_dir, ".env")
        with open(env_file, "w") as f:
            f.write("EXISTING_VAR=existing_value\n")
            f.write("FOGIS_USERNAME=old_user\n")

        # Test updating environment variables
        with patch("os.path.exists", return_value=True), patch(
            "builtins.open",
            mock_open(
                read_data="EXISTING_VAR=existing_value\nFOGIS_USERNAME=old_user\n"
            ),
        ):
            env_content = ["EXISTING_VAR=existing_value\n", "FOGIS_USERNAME=old_user\n"]

            # Update existing variable
            self.wizard._update_env_var(env_content, "FOGIS_USERNAME", "new_user")
            assert "FOGIS_USERNAME=new_user\n" in env_content
            assert "FOGIS_USERNAME=old_user\n" not in env_content

            # Add new variable
            self.wizard._update_env_var(env_content, "NEW_VAR", "new_value")
            assert "NEW_VAR=new_value\n" in env_content

    @patch("builtins.input")
    @patch("lib.credential_wizard.GoogleOAuthManager")
    @patch("lib.credential_wizard.CalendarManager")
    def test_calendar_creation_flow(
        self, mock_calendar_class, mock_oauth_class, mock_input
    ):
        """Test calendar creation flow."""
        mock_input.side_effect = ["1", "n"]  # Create new calendar, don't share

        # Mock OAuth manager
        mock_oauth = Mock()
        mock_oauth.credentials = Mock()
        self.wizard.oauth_manager = mock_oauth

        # Mock calendar manager
        mock_calendar = Mock()
        mock_calendar.create_fogis_calendar.return_value = "new-calendar-id"
        mock_calendar.validate_calendar_access.return_value = {
            "valid": True,
            "calendar_info": {"summary": "FOGIS Matches - 2024"},
        }
        mock_calendar_class.return_value = mock_calendar

        result = self.wizard.setup_calendar_integration()
        assert result is True
        assert self.wizard.config["calendar_id"] == "new-calendar-id"

    def test_validation_and_testing_flow(self):
        """Test validation and testing flow."""
        # Set up wizard state
        self.wizard.oauth_manager = Mock()
        self.wizard.oauth_manager.credentials = Mock()
        self.wizard.calendar_manager = Mock()
        self.wizard.fogis_manager = Mock()
        self.wizard.config = {"calendar_id": "test-calendar"}

        # Mock test methods to return success
        with patch.object(
            self.wizard, "_test_google_oauth", return_value=True
        ), patch.object(
            self.wizard, "_test_calendar_access", return_value=True
        ), patch.object(
            self.wizard, "_test_fogis_auth", return_value=True
        ), patch.object(
            self.wizard, "_test_credential_storage", return_value=True
        ):
            result = self.wizard.validate_and_test()
            assert result is True

    @patch("shutil.copy")
    @patch("os.makedirs")
    @patch("os.path.exists")
    def test_service_credentials_setup(self, mock_exists, mock_makedirs, mock_copy):
        """Test service credentials setup."""
        mock_exists.return_value = True

        self.wizard._setup_service_credentials()

        # Verify directories are created
        mock_makedirs.assert_any_call(
            "data/fogis-calendar-phonebook-sync", exist_ok=True
        )
        mock_makedirs.assert_any_call("data/google-drive-service", exist_ok=True)

        # Verify token files are copied
        mock_copy.assert_any_call(
            "token.json", "data/fogis-calendar-phonebook-sync/token.json"
        )
        mock_copy.assert_any_call(
            "token.json", "data/google-drive-service/google-drive-token.json"
        )
