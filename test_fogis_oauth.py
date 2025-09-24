"""
Comprehensive test suite for FOGIS OAuth 2.0 PKCE authentication implementation.
"""

import base64
import hashlib
import json
import unittest
from unittest.mock import MagicMock, Mock, patch
from urllib.parse import parse_qs, urlparse

import requests

from fogis_auth_oauth import (
    FogisAuthenticationError,
    FogisOAuthAuthenticationError,
    authenticate,
)
from fogis_oauth_manager import FogisOAuthManager
from fogis_public_api_client_oauth import FogisLoginError, PublicApiClient


class TestFogisOAuthManager(unittest.TestCase):
    """Test cases for FogisOAuthManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.oauth_manager = FogisOAuthManager()

    def test_generate_pkce_challenge(self):
        """Test PKCE code challenge generation."""
        code_verifier, code_challenge = self.oauth_manager.generate_pkce_challenge()

        # Verify code verifier format
        self.assertIsInstance(code_verifier, str)
        self.assertGreaterEqual(len(code_verifier), 43)
        self.assertLessEqual(len(code_verifier), 128)

        # Verify code challenge is correct SHA256 hash
        expected_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("utf-8")).digest()
            )
            .decode("utf-8")
            .rstrip("=")
        )

        self.assertEqual(code_challenge, expected_challenge)
        self.assertEqual(self.oauth_manager.code_verifier, code_verifier)

    def test_generate_state_and_nonce(self):
        """Test OAuth state and nonce generation."""
        state, nonce = self.oauth_manager.generate_state_and_nonce()

        # Verify state format
        self.assertIsInstance(state, str)
        self.assertGreater(len(state), 20)

        # Verify nonce format (timestamp.part1part2)
        self.assertIsInstance(nonce, str)
        self.assertIn(".", nonce)

        timestamp_part, token_part = nonce.split(".", 1)
        self.assertTrue(timestamp_part.isdigit())
        self.assertGreater(len(token_part), 20)

        self.assertEqual(self.oauth_manager.state, state)
        self.assertEqual(self.oauth_manager.nonce, nonce)

    def test_create_authorization_url(self):
        """Test OAuth authorization URL creation."""
        auth_url = self.oauth_manager.create_authorization_url()

        # Parse the URL
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)

        # Verify base URL
        self.assertEqual(parsed_url.scheme, "https")
        self.assertEqual(parsed_url.netloc, "auth.fogis.se")
        self.assertEqual(parsed_url.path, "/connect/authorize")

        # Verify required parameters
        self.assertEqual(query_params["client_id"][0], "fogis.mobildomarklient")
        self.assertEqual(query_params["response_type"][0], "code")
        self.assertEqual(query_params["code_challenge_method"][0], "S256")
        self.assertIn("code_challenge", query_params)
        self.assertIn("state", query_params)
        self.assertIn("nonce", query_params)

        # Verify FOGIS-specific parameters
        self.assertEqual(query_params["x-client-SKU"][0], "ID_NET472")
        self.assertEqual(query_params["x-client-ver"][0], "8.13.0.0")

    def test_handle_authorization_redirect_success(self):
        """Test successful authorization code extraction."""
        redirect_url = "https://fogis.svenskfotboll.se/mdk/signin-oidc?code=test_auth_code&state=test_state"

        auth_code = self.oauth_manager.handle_authorization_redirect(redirect_url)

        self.assertEqual(auth_code, "test_auth_code")

    def test_handle_authorization_redirect_error(self):
        """Test authorization redirect with error."""
        redirect_url = "https://fogis.svenskfotboll.se/mdk/signin-oidc?error=access_denied&error_description=User+denied+access"

        auth_code = self.oauth_manager.handle_authorization_redirect(redirect_url)

        self.assertIsNone(auth_code)

    @patch("requests.Session.post")
    def test_exchange_code_for_tokens_success(self, mock_post):
        """Test successful token exchange."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_post.return_value = mock_response

        # Set up OAuth manager state
        self.oauth_manager.code_verifier = "test_code_verifier"

        # Test token exchange
        result = self.oauth_manager.exchange_code_for_tokens("test_auth_code")

        self.assertTrue(result)
        self.assertEqual(self.oauth_manager.access_token, "test_access_token")
        self.assertEqual(self.oauth_manager.refresh_token, "test_refresh_token")
        self.assertEqual(self.oauth_manager.token_expires_in, 3600)

    @patch("requests.Session.post")
    def test_exchange_code_for_tokens_failure(self, mock_post):
        """Test failed token exchange."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid authorization code"
        mock_post.return_value = mock_response

        # Set up OAuth manager state
        self.oauth_manager.code_verifier = "test_code_verifier"

        # Test token exchange
        result = self.oauth_manager.exchange_code_for_tokens("invalid_code")

        self.assertFalse(result)
        self.assertIsNone(self.oauth_manager.access_token)

    @patch("requests.Session.post")
    def test_refresh_access_token_success(self, mock_post):
        """Test successful token refresh."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        # Set up OAuth manager state
        self.oauth_manager.refresh_token = "test_refresh_token"

        # Test token refresh
        result = self.oauth_manager.refresh_access_token()

        self.assertTrue(result)
        self.assertEqual(self.oauth_manager.access_token, "new_access_token")

    def test_is_authenticated(self):
        """Test authentication status check."""
        # Initially not authenticated
        self.assertFalse(self.oauth_manager.is_authenticated())

        # Set access token
        self.oauth_manager.access_token = "test_token"
        self.assertTrue(self.oauth_manager.is_authenticated())

    def test_clear_tokens(self):
        """Test token clearing."""
        # Set up some tokens
        self.oauth_manager.access_token = "test_access_token"
        self.oauth_manager.refresh_token = "test_refresh_token"
        self.oauth_manager.session.headers["Authorization"] = "Bearer test_token"

        # Clear tokens
        self.oauth_manager.clear_tokens()

        # Verify everything is cleared
        self.assertIsNone(self.oauth_manager.access_token)
        self.assertIsNone(self.oauth_manager.refresh_token)
        self.assertNotIn("Authorization", self.oauth_manager.session.headers)


class TestFogisAuthentication(unittest.TestCase):
    """Test cases for FOGIS authentication functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.session = requests.Session()
        self.username = "test_user"
        self.password = "test_password"
        self.base_url = "https://fogis.svenskfotboll.se/mdk"

    @patch("requests.Session.get")
    def test_authenticate_oauth_redirect(self, mock_get):
        """Test authentication when redirected to OAuth."""
        # Mock OAuth redirect response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = (
            "https://auth.fogis.se/connect/authorize?client_id=fogis.mobildomarklient"
        )
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with patch("fogis_auth_oauth._handle_oauth_authentication") as mock_oauth:
            mock_oauth.return_value = {
                "access_token": "test_token",
                "oauth_authenticated": True,
            }

            result = authenticate(
                self.session, self.username, self.password, self.base_url
            )

            self.assertIn("access_token", result)
            self.assertTrue(result.get("oauth_authenticated"))

    @patch("requests.Session.get")
    def test_authenticate_aspnet_fallback(self, mock_get):
        """Test authentication with ASP.NET fallback."""
        # Mock ASP.NET response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://fogis.svenskfotboll.se/mdk/Login.aspx"
        mock_response.text = '<input name="__VIEWSTATE" value="test_viewstate" />'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with patch("fogis_auth_oauth._handle_aspnet_authentication") as mock_aspnet:
            mock_aspnet.return_value = {
                "FogisMobilDomarKlient.ASPXAUTH": "test_cookie",
                "aspnet_authenticated": True,
            }

            result = authenticate(
                self.session, self.username, self.password, self.base_url
            )

            self.assertIn("FogisMobilDomarKlient.ASPXAUTH", result)
            self.assertTrue(result.get("aspnet_authenticated"))


class TestPublicApiClient(unittest.TestCase):
    """Test cases for PublicApiClient class."""

    def setUp(self):
        """Set up test fixtures."""
        self.username = "test_user"
        self.password = "test_password"

    def test_init_with_oauth_tokens(self):
        """Test initialization with OAuth tokens."""
        oauth_tokens = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
        }

        client = PublicApiClient(oauth_tokens=oauth_tokens)

        self.assertEqual(client.oauth_tokens, oauth_tokens)
        self.assertEqual(client.authentication_method, "oauth")
        self.assertTrue(client.is_authenticated())

    def test_init_with_aspnet_cookies(self):
        """Test initialization with ASP.NET cookies."""
        cookies = {
            "FogisMobilDomarKlient.ASPXAUTH": "test_auth_cookie",
            "ASP.NET_SessionId": "test_session_id",
        }

        client = PublicApiClient(cookies=cookies)

        self.assertEqual(client.cookies, cookies)
        self.assertEqual(client.authentication_method, "aspnet")
        self.assertTrue(client.is_authenticated())

    def test_init_with_credentials(self):
        """Test initialization with username and password."""
        client = PublicApiClient(username=self.username, password=self.password)

        self.assertEqual(client.username, self.username)
        self.assertEqual(client.password, self.password)
        self.assertFalse(client.is_authenticated())

    def test_init_without_credentials(self):
        """Test initialization without any credentials."""
        with self.assertRaises(ValueError):
            PublicApiClient()

    @patch("fogis_public_api_client_oauth.authenticate")
    def test_login_oauth_success(self, mock_authenticate):
        """Test successful OAuth login."""
        mock_authenticate.return_value = {
            "access_token": "test_access_token",
            "oauth_authenticated": True,
        }

        client = PublicApiClient(username=self.username, password=self.password)
        result = client.login()

        self.assertIn("access_token", result)
        self.assertEqual(client.authentication_method, "oauth")

    @patch("fogis_public_api_client_oauth.authenticate")
    def test_login_aspnet_success(self, mock_authenticate):
        """Test successful ASP.NET login."""
        mock_authenticate.return_value = {
            "FogisMobilDomarKlient.ASPXAUTH": "test_cookie",
            "aspnet_authenticated": True,
        }

        client = PublicApiClient(username=self.username, password=self.password)
        result = client.login()

        self.assertIn("FogisMobilDomarKlient.ASPXAUTH", result)
        self.assertEqual(client.authentication_method, "aspnet")


if __name__ == "__main__":
    # Run the test suite
    unittest.main(verbosity=2)
