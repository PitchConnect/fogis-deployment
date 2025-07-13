#!/usr/bin/env python3
"""
Unit tests for OAuthWizard
Tests OAuth authentication wizard functionality
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# Add the lib directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))

from oauth_wizard import OAuthWizard  # noqa: E402


class TestOAuthWizard(unittest.TestCase):
    """Test cases for OAuthWizard class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        self.oauth_wizard = OAuthWizard()

        # Sample credentials for testing
        self.sample_web_credentials = {
            "web": {
                "client_id": "123456789-abcdefghijklmnop.apps.googleusercontent.com",
                "client_secret": "GOCSPX-abcdefghijklmnopqrstuvwxyz",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8080/", "http://localhost:9084/"],
            }
        }

        self.sample_desktop_credentials = {
            "installed": {
                "client_id": "123456789-abcdefghijklmnop.apps.googleusercontent.com",
                "client_secret": "GOCSPX-abcdefghijklmnopqrstuvwxyz",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        import shutil

        shutil.rmtree(self.test_dir)

    def test_check_existing_oauth_no_files(self):
        """Test OAuth detection with no existing files"""
        self.assertFalse(self.oauth_wizard.check_existing_oauth())

    def test_check_existing_oauth_with_credentials(self):
        """Test OAuth detection with existing credentials"""
        with open("credentials.json", "w") as f:
            json.dump(self.sample_web_credentials, f)

        self.assertTrue(self.oauth_wizard.check_existing_oauth())

    def test_check_existing_oauth_with_tokens(self):
        """Test OAuth detection with existing tokens"""
        os.makedirs("data/google-drive-service", exist_ok=True)
        with open("data/google-drive-service/google-drive-token.json", "w") as f:
            json.dump({"token": "test"}, f)

        self.assertTrue(self.oauth_wizard.check_existing_oauth())

    def test_validate_credentials_structure_web(self):
        """Test validation of web application credentials"""
        is_valid, info = self.oauth_wizard.validate_credentials_structure(
            self.sample_web_credentials
        )

        self.assertTrue(is_valid)
        self.assertEqual(info["detected_type"], "web_application")
        self.assertEqual(
            info["client_id"],
            "123456789-abcdefghijklmnop.apps.googleusercontent.com",
        )
        self.assertIn("http://localhost:8080/", info["redirect_uris"])

    def test_validate_credentials_structure_desktop(self):
        """Test validation of desktop application credentials"""
        is_valid, info = self.oauth_wizard.validate_credentials_structure(
            self.sample_desktop_credentials
        )

        self.assertTrue(is_valid)
        self.assertEqual(info["detected_type"], "desktop_application")
        self.assertEqual(
            info["client_id"],
            "123456789-abcdefghijklmnop.apps.googleusercontent.com",
        )

    def test_validate_credentials_structure_invalid(self):
        """Test validation of invalid credentials"""
        invalid_credentials = {"invalid": "structure"}

        is_valid, error = self.oauth_wizard.validate_credentials_structure(
            invalid_credentials
        )

        self.assertFalse(is_valid)
        self.assertIn("missing 'web' or 'installed' section", error)

    def test_validate_credentials_structure_missing_fields(self):
        """Test validation with missing required fields"""
        incomplete_credentials = {"web": {"client_id": "test"}}

        is_valid, error = self.oauth_wizard.validate_credentials_structure(
            incomplete_credentials
        )

        self.assertFalse(is_valid)
        self.assertIn("Missing required field", error)

    def test_validate_credentials_structure_web_no_localhost(self):
        """Test validation of web credentials without localhost redirect"""
        credentials_no_localhost = {
            "web": {
                "client_id": "123456789-abcdefghijklmnop.apps.googleusercontent.com",
                "client_secret": "GOCSPX-abcdefghijklmnopqrstuvwxyz",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["https://example.com/callback"],
            }
        }

        is_valid, error = self.oauth_wizard.validate_credentials_structure(
            credentials_no_localhost
        )

        self.assertFalse(is_valid)
        self.assertIn("should have localhost redirect URIs", error)

    @patch("builtins.input")
    def test_ask_yes_no(self, mock_input):
        """Test yes/no question handling"""
        # Test yes responses
        mock_input.return_value = "y"
        self.assertTrue(self.oauth_wizard.ask_yes_no("Test question?"))

        mock_input.return_value = "yes"
        self.assertTrue(self.oauth_wizard.ask_yes_no("Test question?"))

        # Test no responses
        mock_input.return_value = "n"
        self.assertFalse(self.oauth_wizard.ask_yes_no("Test question?"))

        mock_input.return_value = "no"
        self.assertFalse(self.oauth_wizard.ask_yes_no("Test question?"))

        # Test default handling
        mock_input.return_value = ""
        self.assertTrue(self.oauth_wizard.ask_yes_no("Test question?", default=True))
        self.assertFalse(self.oauth_wizard.ask_yes_no("Test question?", default=False))

    def test_get_oauth_status_no_files(self):
        """Test OAuth status with no files"""
        status = self.oauth_wizard.get_oauth_status()

        self.assertFalse(status["credentials_exist"])
        self.assertFalse(status["credentials_valid"])
        self.assertFalse(status["tokens_exist"])
        self.assertFalse(status["setup_complete"])

    def test_get_oauth_status_with_valid_credentials(self):
        """Test OAuth status with valid credentials"""
        with open("credentials.json", "w") as f:
            json.dump(self.sample_web_credentials, f)

        status = self.oauth_wizard.get_oauth_status()

        self.assertTrue(status["credentials_exist"])
        self.assertTrue(status["credentials_valid"])
        self.assertEqual(status["client_type"], "web_application")
        self.assertEqual(status["project_id"], "123456789")

    def test_get_oauth_status_with_tokens(self):
        """Test OAuth status with tokens"""
        # Create credentials
        with open("credentials.json", "w") as f:
            json.dump(self.sample_web_credentials, f)

        # Create token
        os.makedirs("data/google-drive-service", exist_ok=True)
        with open("data/google-drive-service/google-drive-token.json", "w") as f:
            json.dump({"token": "test"}, f)

        status = self.oauth_wizard.get_oauth_status()

        self.assertTrue(status["credentials_exist"])
        self.assertTrue(status["credentials_valid"])
        self.assertTrue(status["tokens_exist"])
        self.assertTrue(status["setup_complete"])

    @patch("oauth_wizard.OAuthWizard.ask_yes_no")
    def test_confirm_oauth_overwrite(self, mock_ask):
        """Test OAuth overwrite confirmation"""
        # Test user confirms
        mock_ask.return_value = True
        self.assertTrue(self.oauth_wizard.confirm_oauth_overwrite())

        # Test user declines
        mock_ask.return_value = False
        self.assertFalse(self.oauth_wizard.confirm_oauth_overwrite())

    @patch("oauth_wizard.time.sleep")
    def test_test_oauth_flow(self, mock_sleep):
        """Test OAuth flow testing"""
        with patch.object(
            self.oauth_wizard, "ask_yes_no", return_value=True
        ) as mock_ask:
            result = self.oauth_wizard.test_oauth_flow(
                "Google Calendar", ["https://www.googleapis.com/auth/calendar"]
            )
            self.assertTrue(result)
            mock_ask.assert_called_once()

    @patch("oauth_wizard.time.sleep")
    def test_connectivity_tests(self, mock_sleep):
        """Test connectivity test methods"""
        # Test calendar connectivity
        self.assertTrue(self.oauth_wizard.test_calendar_connectivity())

        # Test contacts connectivity
        self.assertTrue(self.oauth_wizard.test_contacts_connectivity())

        # Test drive connectivity
        self.assertTrue(self.oauth_wizard.test_drive_connectivity())

    def test_display_setup_progress(self):
        """Test setup progress display"""
        # Set some progress
        self.oauth_wizard.setup_progress["project_setup"] = True
        self.oauth_wizard.setup_progress["oauth_client"] = False

        # This should not raise an exception
        from io import StringIO

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            self.oauth_wizard.display_setup_progress()
            output = mock_stdout.getvalue()

            self.assertIn("OAuth Setup Progress", output)
            self.assertIn("✅", output)  # Completed item
            self.assertIn("⏳", output)  # Pending item


if __name__ == "__main__":
    unittest.main()
