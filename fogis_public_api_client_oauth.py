"""
Enhanced FOGIS Public API Client with OAuth 2.0 Support

This module provides the main API client interface with support for both
OAuth 2.0 PKCE authentication and ASP.NET form authentication fallback.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, cast

import requests
from jsonschema import ValidationError

# Import the enhanced authentication module
try:
    # Try relative import first (when used as part of package)
    from .internal.auth import (
        FogisAuthenticationError,
        FogisOAuthAuthenticationError,
        authenticate,
    )
except ImportError:
    # Fallback to direct import (when used standalone)
    from fogis_auth_oauth import (
        FogisAuthenticationError,
        FogisOAuthAuthenticationError,
        authenticate,
    )


# Custom exceptions
class FogisLoginError(Exception):
    """Exception raised when login to FOGIS fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class FogisAPIRequestError(Exception):
    """Exception raised when an API request to FOGIS fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class FogisDataError(Exception):
    """Exception raised when FOGIS returns invalid or unexpected data."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class PublicApiClient:
    """
    Enhanced FOGIS API client with OAuth 2.0 PKCE support.

    This client automatically handles both OAuth 2.0 and ASP.NET authentication
    based on the server's response, providing seamless authentication regardless
    of which method FOGIS is using.
    """

    BASE_URL = "https://fogis.svenskfotboll.se/mdk"

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        cookies: Optional[Dict[str, str]] = None,
        oauth_tokens: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the FOGIS API client.

        Args:
            username: FOGIS username
            password: FOGIS password
            cookies: Optional pre-existing session cookies (ASP.NET)
            oauth_tokens: Optional pre-existing OAuth tokens
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.logger = logging.getLogger("fogis_api_client.api")

        # Authentication state
        self.cookies: Optional[Dict[str, str]] = None
        self.oauth_tokens: Optional[Dict[str, Any]] = None
        self.authentication_method: Optional[str] = None  # 'oauth' or 'aspnet'

        # Initialize with provided authentication
        if oauth_tokens:
            self.oauth_tokens = oauth_tokens
            self.authentication_method = "oauth"
            # Set OAuth authorization header
            if "access_token" in oauth_tokens:
                self.session.headers["Authorization"] = (
                    f"Bearer {oauth_tokens['access_token']}"
                )
            self.logger.info("Initialized with OAuth tokens")

        elif cookies:
            self.cookies = cookies
            self.authentication_method = "aspnet"
            # Add cookies to the session
            for key, value in cookies.items():
                if isinstance(value, str) and not key.startswith("oauth"):
                    self.session.cookies.set(key, value)
            self.logger.info("Initialized with ASP.NET cookies")

        elif not (username and password):
            raise ValueError(
                "Either username and password OR cookies/oauth_tokens must be provided"
            )

    def login(self) -> Union[Dict[str, str], Dict[str, Any]]:
        """
        Logs into the FOGIS API using OAuth 2.0 or ASP.NET authentication.

        Returns:
            Authentication tokens/cookies if login is successful

        Raises:
            FogisLoginError: If login fails
            FogisAPIRequestError: If there is an error during the login request
        """
        # If already authenticated, return existing credentials
        if self.oauth_tokens and self.authentication_method == "oauth":
            self.logger.debug("Already authenticated with OAuth, using existing tokens")
            return self.oauth_tokens
        elif self.cookies and self.authentication_method == "aspnet":
            self.logger.debug(
                "Already authenticated with ASP.NET, using existing cookies"
            )
            return self.cookies

        # If no username/password provided, we can't log in
        if not (self.username and self.password):
            error_msg = "Login failed: No credentials provided and no existing authentication available"
            self.logger.error(error_msg)
            raise FogisLoginError(error_msg)

        try:
            # Attempt authentication using the enhanced auth module
            auth_result = authenticate(
                self.session, self.username, self.password, self.BASE_URL
            )

            # Determine authentication method based on result
            if "oauth_authenticated" in auth_result:
                # Check if this is OAuth hybrid (OAuth login + ASP.NET cookies)
                if auth_result.get("authentication_method") == "oauth_hybrid":
                    # OAuth hybrid: OAuth login but ASP.NET session cookies for API access
                    self.cookies = {
                        k: v
                        for k, v in auth_result.items()
                        if not k.startswith("oauth")
                        and not k.startswith("authentication")
                    }
                    self.authentication_method = "oauth_hybrid"
                    self.logger.info(
                        "OAuth hybrid authentication successful (OAuth login + ASP.NET cookies)"
                    )

                    # Set cookies in session for API calls
                    for key, value in self.cookies.items():
                        self.session.cookies.set(key, value)

                    return self.cookies
                else:
                    # Pure OAuth authentication with tokens
                    self.oauth_tokens = auth_result
                    self.authentication_method = "oauth"
                    self.logger.info("OAuth authentication successful")
                    return self.oauth_tokens

            elif "aspnet_authenticated" in auth_result:
                # Traditional ASP.NET authentication
                self.cookies = {
                    k: v for k, v in auth_result.items() if not k.startswith("aspnet")
                }
                self.authentication_method = "aspnet"
                self.logger.info("ASP.NET authentication successful")
                return self.cookies

            else:
                # Unknown authentication result
                self.logger.error("Unknown authentication result format")
                raise FogisLoginError(
                    "Authentication completed but result format is unknown"
                )

        except FogisOAuthAuthenticationError as e:
            error_msg = f"OAuth authentication failed: {e}"
            self.logger.error(error_msg)
            raise FogisLoginError(error_msg) from e

        except FogisAuthenticationError as e:
            error_msg = f"Authentication failed: {e}"
            self.logger.error(error_msg)
            raise FogisLoginError(error_msg) from e

        except requests.exceptions.RequestException as e:
            error_msg = f"Login request failed: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

    def refresh_authentication(self) -> bool:
        """
        Refresh authentication tokens/session.

        Returns:
            True if refresh was successful, False otherwise
        """
        if self.authentication_method == "oauth" and self.oauth_tokens:
            # Try to refresh OAuth tokens
            try:
                from fogis_oauth_manager import FogisOAuthManager

                oauth_manager = FogisOAuthManager(self.session)

                # Set current tokens
                oauth_manager.access_token = self.oauth_tokens.get("access_token")
                oauth_manager.refresh_token = self.oauth_tokens.get("refresh_token")

                # Attempt refresh
                if oauth_manager.refresh_access_token():
                    # Update stored tokens
                    self.oauth_tokens.update(
                        {
                            "access_token": oauth_manager.access_token,
                            "refresh_token": oauth_manager.refresh_token,
                            "expires_in": oauth_manager.token_expires_in,
                        }
                    )
                    self.logger.info("OAuth tokens refreshed successfully")
                    return True
                else:
                    self.logger.error("OAuth token refresh failed")
                    return False

            except Exception as e:
                self.logger.error(f"Error refreshing OAuth tokens: {e}")
                return False

        elif self.authentication_method == "aspnet":
            # For ASP.NET, we need to re-authenticate
            try:
                self.cookies = None
                self.login()
                return True
            except Exception as e:
                self.logger.error(f"Error re-authenticating ASP.NET session: {e}")
                return False

        return False

    def is_authenticated(self) -> bool:
        """
        Check if the client is currently authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        if self.authentication_method == "oauth":
            return self.oauth_tokens is not None and "access_token" in self.oauth_tokens
        elif self.authentication_method in ["aspnet", "oauth_hybrid"]:
            return self.cookies is not None and len(self.cookies) > 0
        return False

    def get_authentication_info(self) -> Dict[str, Any]:
        """
        Get information about the current authentication state.

        Returns:
            Dictionary with authentication information
        """
        return {
            "method": self.authentication_method,
            "authenticated": self.is_authenticated(),
            "has_oauth_tokens": self.oauth_tokens is not None,
            "has_aspnet_cookies": self.cookies is not None,
            "oauth_token_info": (
                self.oauth_tokens.get("expires_in") if self.oauth_tokens else None
            ),
        }

    def _ensure_authenticated(self) -> None:
        """
        Ensure the client is authenticated, performing login if necessary.

        Raises:
            FogisLoginError: If authentication fails
        """
        if not self.is_authenticated():
            self.logger.info("Not authenticated, performing automatic login...")
            self.login()

    def _make_authenticated_request(
        self, method: str, url: str, **kwargs
    ) -> requests.Response:
        """
        Make an authenticated request to the FOGIS API.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            FogisAPIRequestError: If the request fails
        """
        # Ensure we're authenticated
        self._ensure_authenticated()

        # Make the request
        try:
            response = self.session.request(method, url, **kwargs)

            # Check for authentication errors
            if response.status_code == 401:
                self.logger.warning(
                    "Received 401 Unauthorized, attempting to refresh authentication"
                )
                if self.refresh_authentication():
                    # Retry the request
                    response = self.session.request(method, url, **kwargs)
                else:
                    raise FogisAPIRequestError("Authentication refresh failed")

            return response

        except requests.exceptions.RequestException as e:
            raise FogisAPIRequestError(f"Request failed: {e}")

    # Placeholder for additional API methods
    def fetch_matches_list_json(
        self, filter_params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch the list of matches for the logged-in referee.

        Args:
            filter_params: Optional filter parameters

        Returns:
            List of match dictionaries
        """
        # This would be implemented with the actual FOGIS API endpoints
        # For now, return a placeholder
        self.logger.info("Fetching matches list...")

        # Make authenticated request to matches endpoint
        matches_url = f"{self.BASE_URL}/api/matches"
        response = self._make_authenticated_request("GET", matches_url)

        if response.status_code == 200:
            return response.json()
        else:
            raise FogisAPIRequestError(
                f"Failed to fetch matches: {response.status_code}"
            )


# Maintain backward compatibility
FogisApiClient = PublicApiClient
