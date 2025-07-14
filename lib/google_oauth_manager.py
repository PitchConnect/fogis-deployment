"""
Google OAuth Manager

Handles Google OAuth authentication flow, token management, and credential validation
for the FOGIS system. Supports Calendar, Drive, and Contacts APIs.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


class GoogleOAuthManager:
    """
    Manages Google OAuth authentication and token lifecycle for FOGIS services.

    This class handles the complete OAuth flow including:
    - Initial authentication
    - Token refresh
    - Credential validation
    - Scope management
    """

    # Required scopes for FOGIS functionality
    REQUIRED_SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/contacts",
        "https://www.googleapis.com/auth/drive",
    ]

    def __init__(self, credentials_file: str = "credentials.json"):
        """
        Initialize the OAuth manager.

        Args:
            credentials_file: Path to the Google OAuth credentials JSON file
        """
        self.credentials_file = credentials_file
        self.token_file = "token.json"
        self.credentials: Optional[Credentials] = None
        self.logger = logging.getLogger(__name__)

    def validate_credentials_file(self) -> bool:
        """
        Validate that the credentials.json file exists and has the correct format.

        Returns:
            True if credentials file is valid, False otherwise
        """
        if not os.path.exists(self.credentials_file):
            self.logger.error(f"Credentials file not found: {self.credentials_file}")
            return False

        try:
            with open(self.credentials_file, "r") as f:
                creds_data = json.load(f)

            # Check for required fields in OAuth credentials
            if "installed" not in creds_data and "web" not in creds_data:
                self.logger.error(
                    "Invalid credentials format: missing 'installed' or 'web' section"
                )
                return False

            # Get the appropriate section
            client_config = creds_data.get("installed") or creds_data.get("web")

            required_fields = ["client_id", "client_secret"]
            for field in required_fields:
                if field not in client_config:
                    self.logger.error(f"Missing required field in credentials: {field}")
                    return False

            self.logger.info("Credentials file validation passed")
            return True

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in credentials file: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error validating credentials file: {e}")
            return False

    def load_existing_token(self) -> bool:
        """
        Load existing token from file if available and valid.

        Returns:
            True if existing valid token was loaded, False otherwise
        """
        if not os.path.exists(self.token_file):
            self.logger.info("No existing token file found")
            return False

        try:
            self.credentials = Credentials.from_authorized_user_file(
                self.token_file, self.REQUIRED_SCOPES
            )

            if self.credentials and self.credentials.valid:
                self.logger.info("Loaded valid existing credentials")
                return True
            elif (
                self.credentials
                and self.credentials.expired
                and self.credentials.refresh_token
            ):
                self.logger.info("Refreshing expired credentials")
                self.credentials.refresh(Request())
                self._save_token()
                return True
            else:
                self.logger.info("Existing credentials are invalid")
                return False

        except Exception as e:
            self.logger.error(f"Error loading existing token: {e}")
            return False

    def perform_oauth_flow(self) -> bool:
        """
        Perform the complete OAuth authentication flow.

        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            # Create the flow using the client secrets file
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, self.REQUIRED_SCOPES
            )

            # Set redirect URI for desktop application
            flow.redirect_uri = "http://localhost:8080/callback"

            # Generate authorization URL
            auth_url, state = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",  # Force consent to ensure refresh token
            )

            print(f"\n🔗 Please visit this URL to authorize the application:")
            print(f"{auth_url}")
            print("\n📋 Instructions:")
            print("1. Click the link above or copy it to your browser")
            print("2. Sign in to your Google account")
            print("3. Grant permissions for Calendar, Drive, and Contacts")
            print("4. Copy the ENTIRE callback URL from your browser")
            print("5. Paste it below and press Enter")

            # Get authorization response from user
            callback_url = input("\n📥 Paste the callback URL here: ").strip()

            if not callback_url.startswith("http://localhost:8080/callback"):
                self.logger.error("Invalid callback URL provided")
                return False

            # Exchange authorization code for credentials
            flow.fetch_token(authorization_response=callback_url)
            self.credentials = flow.credentials

            # Save the credentials for future use
            self._save_token()

            self.logger.info("OAuth flow completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"OAuth flow failed: {e}")
            return False

    def _save_token(self) -> None:
        """Save credentials to token file."""
        if self.credentials:
            with open(self.token_file, "w") as token:
                token.write(self.credentials.to_json())
            self.logger.info(f"Token saved to {self.token_file}")

    def get_credentials(self) -> Optional[Credentials]:
        """
        Get valid credentials, performing authentication if necessary.

        Returns:
            Valid Google credentials or None if authentication failed
        """
        # Try to load existing token first
        if self.load_existing_token():
            return self.credentials

        # Validate credentials file
        if not self.validate_credentials_file():
            return None

        # Perform OAuth flow
        if self.perform_oauth_flow():
            return self.credentials

        return None

    def test_credentials(self) -> Dict[str, bool]:
        """
        Test credentials against all required APIs.

        Returns:
            Dictionary with test results for each API
        """
        if not self.credentials:
            return {"calendar": False, "drive": False, "contacts": False}

        results = {}

        # Test Calendar API
        try:
            from googleapiclient.discovery import build

            service = build("calendar", "v3", credentials=self.credentials)
            service.calendarList().list(maxResults=1).execute()
            results["calendar"] = True
        except Exception as e:
            self.logger.error(f"Calendar API test failed: {e}")
            results["calendar"] = False

        # Test Drive API
        try:
            from googleapiclient.discovery import build

            service = build("drive", "v3", credentials=self.credentials)
            service.about().get(fields="user").execute()
            results["drive"] = True
        except Exception as e:
            self.logger.error(f"Drive API test failed: {e}")
            results["drive"] = False

        # Test Contacts API (People API)
        try:
            from googleapiclient.discovery import build

            service = build("people", "v1", credentials=self.credentials)
            service.people().connections().list(
                resourceName="people/me", pageSize=1, personFields="names"
            ).execute()
            results["contacts"] = True
        except Exception as e:
            self.logger.error(f"Contacts API test failed: {e}")
            results["contacts"] = False

        return results

    def get_token_info(self) -> Dict[str, Any]:
        """
        Get information about the current token.

        Returns:
            Dictionary with token information
        """
        if not self.credentials:
            return {}

        return {
            "valid": self.credentials.valid,
            "expired": self.credentials.expired,
            "has_refresh_token": bool(self.credentials.refresh_token),
            "expiry": self.credentials.expiry.isoformat()
            if self.credentials.expiry
            else None,
            "scopes": self.credentials.scopes,
        }

    def revoke_credentials(self) -> bool:
        """
        Revoke the current credentials and remove token file.

        Returns:
            True if revocation was successful, False otherwise
        """
        try:
            if self.credentials:
                # Revoke the token
                revoke = Request()
                self.credentials.revoke(revoke)
                self.credentials = None

            # Remove token file
            if os.path.exists(self.token_file):
                os.remove(self.token_file)

            self.logger.info("Credentials revoked successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error revoking credentials: {e}")
            return False
