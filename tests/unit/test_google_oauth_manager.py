"""
Unit tests for the Google OAuth manager module.
"""

import json
import os
import sys
from unittest.mock import Mock, mock_open, patch

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from lib.google_oauth_manager import GoogleOAuthManager


class TestGoogleOAuthManager:
    """Test cases for GoogleOAuthManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = GoogleOAuthManager("test_credentials.json")

    def test_manager_initialization(self):
        """Test OAuth manager initialization."""
        assert self.manager.credentials_file == "test_credentials.json"
        assert self.manager.token_file == "token.json"
        assert self.manager.credentials is None
        assert self.manager.REQUIRED_SCOPES == [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/contacts",
            "https://www.googleapis.com/auth/drive",
        ]

    @patch("os.path.exists")
    def test_validate_credentials_file_not_exists(self, mock_exists):
        """Test credentials file validation when file doesn't exist."""
        mock_exists.return_value = False
        result = self.manager.validate_credentials_file()
        assert result is False

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    def test_validate_credentials_file_invalid_json(self, mock_file, mock_exists):
        """Test credentials file validation with invalid JSON."""
        mock_exists.return_value = True
        result = self.manager.validate_credentials_file()
        assert result is False

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_validate_credentials_file_missing_sections(self, mock_file, mock_exists):
        """Test credentials file validation with missing sections."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps({"invalid": "structure"})

        result = self.manager.validate_credentials_file()
        assert result is False

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_validate_credentials_file_missing_fields(self, mock_file, mock_exists):
        """Test credentials file validation with missing required fields."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(
            {
                "installed": {
                    "client_id": "test_id"
                    # Missing client_secret
                }
            }
        )

        result = self.manager.validate_credentials_file()
        assert result is False

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_validate_credentials_file_valid_installed(self, mock_file, mock_exists):
        """Test credentials file validation with valid installed app credentials."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(
            {
                "installed": {
                    "client_id": "test_id",
                    "client_secret": "test_secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
        )

        result = self.manager.validate_credentials_file()
        assert result is True

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_validate_credentials_file_valid_web(self, mock_file, mock_exists):
        """Test credentials file validation with valid web app credentials."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(
            {
                "web": {
                    "client_id": "test_id",
                    "client_secret": "test_secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
        )

        result = self.manager.validate_credentials_file()
        assert result is True

    @patch("os.path.exists")
    def test_load_existing_token_no_file(self, mock_exists):
        """Test loading existing token when file doesn't exist."""
        mock_exists.return_value = False
        result = self.manager.load_existing_token()
        assert result is False

    @patch("os.path.exists")
    @patch("google.oauth2.credentials.Credentials.from_authorized_user_file")
    def test_load_existing_token_valid(self, mock_from_file, mock_exists):
        """Test loading valid existing token."""
        mock_exists.return_value = True

        # Mock valid credentials
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_from_file.return_value = mock_credentials

        result = self.manager.load_existing_token()
        assert result is True
        assert self.manager.credentials == mock_credentials

    @patch("os.path.exists")
    @patch("google.oauth2.credentials.Credentials.from_authorized_user_file")
    @patch("google.auth.transport.requests.Request")
    def test_load_existing_token_expired_with_refresh(
        self, mock_request, mock_from_file, mock_exists
    ):
        """Test loading expired token with refresh capability."""
        mock_exists.return_value = True

        # Mock expired credentials with refresh token
        mock_credentials = Mock()
        mock_credentials.valid = False
        mock_credentials.expired = True
        mock_credentials.refresh_token = "refresh_token"
        mock_from_file.return_value = mock_credentials

        with patch.object(self.manager, "_save_token"):
            result = self.manager.load_existing_token()
            assert result is True
            mock_credentials.refresh.assert_called_once()

    @patch("os.path.exists")
    @patch("google.oauth2.credentials.Credentials.from_authorized_user_file")
    def test_load_existing_token_invalid(self, mock_from_file, mock_exists):
        """Test loading invalid existing token."""
        mock_exists.return_value = True

        # Mock invalid credentials
        mock_credentials = Mock()
        mock_credentials.valid = False
        mock_credentials.expired = True
        mock_credentials.refresh_token = None
        mock_from_file.return_value = mock_credentials

        result = self.manager.load_existing_token()
        assert result is False

    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
    @patch("builtins.input")
    def test_perform_oauth_flow_success(self, mock_input, mock_flow_class):
        """Test successful OAuth flow."""
        mock_input.return_value = "http://localhost:8080/callback?code=test_code"

        # Mock flow
        mock_flow = Mock()
        mock_credentials = Mock()
        mock_flow.authorization_url.return_value = ("http://auth.url", "state")
        mock_flow.credentials = mock_credentials
        mock_flow_class.return_value = mock_flow

        with patch.object(self.manager, "_save_token"):
            result = self.manager.perform_oauth_flow()
            assert result is True
            assert self.manager.credentials == mock_credentials

    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
    @patch("builtins.input")
    def test_perform_oauth_flow_invalid_callback(self, mock_input, mock_flow_class):
        """Test OAuth flow with invalid callback URL."""
        mock_input.return_value = "invalid_url"

        mock_flow = Mock()
        mock_flow.authorization_url.return_value = ("http://auth.url", "state")
        mock_flow_class.return_value = mock_flow

        result = self.manager.perform_oauth_flow()
        assert result is False

    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file")
    def test_perform_oauth_flow_exception(self, mock_flow_class):
        """Test OAuth flow with exception."""
        mock_flow_class.side_effect = Exception("OAuth error")

        result = self.manager.perform_oauth_flow()
        assert result is False

    @patch("builtins.open", new_callable=mock_open)
    def test_save_token(self, mock_file):
        """Test saving token to file."""
        mock_credentials = Mock()
        mock_credentials.to_json.return_value = '{"token": "data"}'
        self.manager.credentials = mock_credentials

        self.manager._save_token()
        mock_file.assert_called_once_with("token.json", "w")
        mock_file().write.assert_called_once_with('{"token": "data"}')

    def test_get_credentials_with_existing_token(self):
        """Test getting credentials with existing valid token."""
        with patch.object(self.manager, "load_existing_token", return_value=True):
            mock_credentials = Mock()
            self.manager.credentials = mock_credentials

            result = self.manager.get_credentials()
            assert result == mock_credentials

    def test_get_credentials_with_oauth_flow(self):
        """Test getting credentials through OAuth flow."""
        with patch.object(
            self.manager, "load_existing_token", return_value=False
        ), patch.object(
            self.manager, "validate_credentials_file", return_value=True
        ), patch.object(
            self.manager, "perform_oauth_flow", return_value=True
        ):
            mock_credentials = Mock()
            self.manager.credentials = mock_credentials

            result = self.manager.get_credentials()
            assert result == mock_credentials

    def test_get_credentials_failure(self):
        """Test getting credentials with all methods failing."""
        with patch.object(
            self.manager, "load_existing_token", return_value=False
        ), patch.object(self.manager, "validate_credentials_file", return_value=False):
            result = self.manager.get_credentials()
            assert result is None

    @patch("googleapiclient.discovery.build")
    def test_test_credentials_success(self, mock_build):
        """Test successful credential testing."""
        # Mock credentials
        mock_credentials = Mock()
        self.manager.credentials = mock_credentials

        # Mock API services
        mock_calendar_service = Mock()
        mock_drive_service = Mock()
        mock_people_service = Mock()

        mock_build.side_effect = [
            mock_calendar_service,
            mock_drive_service,
            mock_people_service,
        ]

        # Mock API calls
        mock_calendar_service.calendarList().list().execute.return_value = {}
        mock_drive_service.about().get().execute.return_value = {}
        mock_people_service.people().connections().list().execute.return_value = {}

        result = self.manager.test_credentials()

        assert result["calendar"] is True
        assert result["drive"] is True
        assert result["contacts"] is True

    def test_test_credentials_no_credentials(self):
        """Test credential testing without credentials."""
        self.manager.credentials = None

        result = self.manager.test_credentials()

        assert result["calendar"] is False
        assert result["drive"] is False
        assert result["contacts"] is False

    def test_get_token_info_with_credentials(self):
        """Test getting token info with valid credentials."""
        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.expired = False
        mock_credentials.refresh_token = "refresh_token"
        mock_credentials.expiry = None
        mock_credentials.scopes = ["scope1", "scope2"]
        self.manager.credentials = mock_credentials

        result = self.manager.get_token_info()

        assert result["valid"] is True
        assert result["expired"] is False
        assert result["has_refresh_token"] is True
        assert result["scopes"] == ["scope1", "scope2"]

    def test_get_token_info_no_credentials(self):
        """Test getting token info without credentials."""
        self.manager.credentials = None

        result = self.manager.get_token_info()
        assert result == {}

    @patch("google.auth.transport.requests.Request")
    @patch("os.path.exists")
    @patch("os.remove")
    def test_revoke_credentials_success(self, mock_remove, mock_exists, mock_request):
        """Test successful credential revocation."""
        mock_exists.return_value = True
        mock_credentials = Mock()
        self.manager.credentials = mock_credentials

        result = self.manager.revoke_credentials()

        assert result is True
        assert self.manager.credentials is None
        mock_credentials.revoke.assert_called_once()
        mock_remove.assert_called_once_with("token.json")

    @patch("os.path.exists")
    def test_revoke_credentials_no_token_file(self, mock_exists):
        """Test credential revocation when no token file exists."""
        mock_exists.return_value = False
        self.manager.credentials = None

        result = self.manager.revoke_credentials()
        assert result is True
