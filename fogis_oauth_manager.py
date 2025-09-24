"""
FOGIS OAuth 2.0 PKCE Authentication Manager

Handles OAuth 2.0 authentication with FOGIS using PKCE (Proof Key for Code Exchange)
to replace the deprecated ASP.NET form authentication.
"""

import base64
import hashlib
import json
import logging
import secrets
import urllib.parse
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import requests


class FogisOAuthManager:
    """
    Manages OAuth 2.0 PKCE authentication flow for FOGIS API.

    This class handles the complete OAuth flow including:
    - PKCE code challenge generation
    - Authorization URL creation
    - Token exchange
    - Token refresh
    - Session management
    """

    # FOGIS OAuth endpoints
    AUTHORIZATION_URL = "https://auth.fogis.se/connect/authorize"
    TOKEN_URL = "https://auth.fogis.se/connect/token"

    # OAuth client configuration
    CLIENT_ID = "fogis.mobildomarklient"
    REDIRECT_URI = "https://fogis.svenskfotboll.se/mdk/signin-oidc"
    SCOPES = "openid fogis profile anvandare personid offline_access"

    def __init__(self, session: Optional[requests.Session] = None):
        """
        Initialize FOGIS OAuth manager.

        Args:
            session: Optional requests session to use
        """
        self.session = session or requests.Session()
        self.logger = logging.getLogger("fogis_api_client.oauth")

        # OAuth state management
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_in: Optional[int] = None
        self.code_verifier: Optional[str] = None
        self.state: Optional[str] = None
        self.nonce: Optional[str] = None

        # Set browser-like headers
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

    def generate_pkce_challenge(self) -> Tuple[str, str]:
        """
        Generate PKCE code verifier and challenge.

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate code verifier (43-128 characters)
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )

        # Generate code challenge (SHA256 hash of verifier)
        code_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("utf-8")).digest()
            )
            .decode("utf-8")
            .rstrip("=")
        )

        self.code_verifier = code_verifier
        return code_verifier, code_challenge

    def generate_state_and_nonce(self) -> Tuple[str, str]:
        """
        Generate OAuth state and OpenID Connect nonce.

        Returns:
            Tuple of (state, nonce)
        """
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Generate nonce for OpenID Connect (timestamp-based like FOGIS expects)
        import time

        timestamp = int(time.time() * 10000000)  # .NET ticks format
        nonce_part1 = secrets.token_hex(16)
        nonce_part2 = secrets.token_hex(16)
        nonce = f"{timestamp}.{nonce_part1}{nonce_part2}"

        self.state = state
        self.nonce = nonce
        return state, nonce

    def create_authorization_url(self) -> str:
        """
        Create OAuth 2.0 authorization URL with PKCE parameters.

        Returns:
            Authorization URL for FOGIS OAuth
        """
        # Generate PKCE challenge
        code_verifier, code_challenge = self.generate_pkce_challenge()

        # Generate state and nonce
        state, nonce = self.generate_state_and_nonce()

        # Build authorization parameters
        params = {
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.REDIRECT_URI,
            "response_type": "code",
            "scope": self.SCOPES,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": f"OpenIdConnect.AuthenticationProperties={state}",
            "nonce": nonce,
            "x-client-SKU": "ID_NET472",
            "x-client-ver": "8.13.0.0",
        }

        # Create authorization URL
        auth_url = f"{self.AUTHORIZATION_URL}?{urllib.parse.urlencode(params)}"

        self.logger.debug(f"Created authorization URL: {auth_url}")
        return auth_url

    def handle_authorization_redirect(self, redirect_url: str) -> Optional[str]:
        """
        Handle authorization redirect and extract authorization code.

        Args:
            redirect_url: The redirect URL from FOGIS OAuth

        Returns:
            Authorization code if successful, None otherwise
        """
        try:
            parsed_url = urlparse(redirect_url)
            query_params = parse_qs(parsed_url.query)

            # Check for error
            if "error" in query_params:
                error = query_params["error"][0]
                error_description = query_params.get(
                    "error_description", ["Unknown error"]
                )[0]
                self.logger.error(
                    f"OAuth authorization error: {error} - {error_description}"
                )
                return None

            # Extract authorization code
            if "code" in query_params:
                auth_code = query_params["code"][0]
                self.logger.debug("Successfully extracted authorization code")
                return auth_code

            self.logger.error("No authorization code found in redirect URL")
            return None

        except Exception as e:
            self.logger.error(f"Error handling authorization redirect: {e}")
            return None

    def exchange_code_for_tokens(self, authorization_code: str) -> bool:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            authorization_code: The authorization code from FOGIS

        Returns:
            True if token exchange was successful, False otherwise
        """
        try:
            # Prepare token request
            token_data = {
                "grant_type": "authorization_code",
                "client_id": self.CLIENT_ID,
                "code": authorization_code,
                "redirect_uri": self.REDIRECT_URI,
                "code_verifier": self.code_verifier,
            }

            # Request tokens
            response = self.session.post(
                self.TOKEN_URL,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )

            if response.status_code == 200:
                token_response = response.json()

                # Store tokens
                self.access_token = token_response.get("access_token")
                self.refresh_token = token_response.get("refresh_token")
                self.token_expires_in = token_response.get("expires_in")

                # Update session headers with access token
                self.session.headers["Authorization"] = f"Bearer {self.access_token}"

                self.logger.info("Successfully exchanged authorization code for tokens")
                return True
            else:
                self.logger.error(
                    f"Token exchange failed: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error exchanging code for tokens: {e}")
            return False

    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using the refresh token.

        Returns:
            True if token refresh was successful, False otherwise
        """
        if not self.refresh_token:
            self.logger.error("No refresh token available")
            return False

        try:
            # Prepare refresh request
            refresh_data = {
                "grant_type": "refresh_token",
                "client_id": self.CLIENT_ID,
                "refresh_token": self.refresh_token,
            }

            # Request new tokens
            response = self.session.post(
                self.TOKEN_URL,
                data=refresh_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )

            if response.status_code == 200:
                token_response = response.json()

                # Update tokens
                self.access_token = token_response.get("access_token")
                if "refresh_token" in token_response:
                    self.refresh_token = token_response["refresh_token"]
                self.token_expires_in = token_response.get("expires_in")

                # Update session headers
                self.session.headers["Authorization"] = f"Bearer {self.access_token}"

                self.logger.info("Successfully refreshed access token")
                return True
            else:
                self.logger.error(
                    f"Token refresh failed: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error refreshing token: {e}")
            return False

    def is_authenticated(self) -> bool:
        """
        Check if the manager has valid authentication.

        Returns:
            True if authenticated, False otherwise
        """
        return self.access_token is not None

    def get_token_info(self) -> Dict[str, Any]:
        """
        Get current token information.

        Returns:
            Dictionary with token information
        """
        return {
            "has_access_token": self.access_token is not None,
            "has_refresh_token": self.refresh_token is not None,
            "expires_in": self.token_expires_in,
            "authenticated": self.is_authenticated(),
        }

    def clear_tokens(self) -> None:
        """Clear all stored tokens and authentication state."""
        self.access_token = None
        self.refresh_token = None
        self.token_expires_in = None
        self.code_verifier = None
        self.state = None
        self.nonce = None

        # Remove authorization header
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]

        self.logger.info("Cleared all OAuth tokens and state")
