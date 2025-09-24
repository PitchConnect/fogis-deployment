#!/usr/bin/env python3
"""
Monkey patch to replace FOGIS authentication with OAuth-enabled version.
This script patches the FogisApiClient.login method at runtime.
"""

import logging
from typing import Any, Dict

# Set up logging
logger = logging.getLogger(__name__)


def patch_fogis_authentication():
    """Monkey patch the FogisApiClient.login method with OAuth support."""

    try:
        # Import the modules we need
        from fogis_api_client.fogis_api_client import (
            FogisApiClient,
            FogisAPIRequestError,
            FogisLoginError,
        )
        from fogis_api_client.internal.auth import (
            FogisAuthenticationError,
            FogisOAuthAuthenticationError,
            authenticate,
        )

        # Store the original login method
        original_login = FogisApiClient.login

        def oauth_enabled_login(self) -> Dict[str, Any]:
            """
            OAuth-enabled login method that replaces the original.

            Returns:
                Dict[str, Any]: The session cookies if login is successful
            """
            # If cookies are already set, return them without logging in again
            if self.cookies:
                self.logger.debug("Already authenticated, using existing cookies")
                return self.cookies

            # If no username/password provided, we can't log in
            if not (self.username and self.password):
                error_msg = (
                    "Login failed: No credentials provided and no cookies available"
                )
                self.logger.error(error_msg)
                raise FogisLoginError(error_msg)

            try:
                # Use the OAuth-enabled authentication
                self.logger.info("Using OAuth-enabled authentication")
                auth_result = authenticate(
                    self.session, self.username, self.password, self.BASE_URL
                )

                # Handle different authentication methods
                if "oauth_authenticated" in auth_result:
                    if auth_result.get("authentication_method") == "oauth_hybrid":
                        # OAuth hybrid: OAuth login + ASP.NET cookies
                        self.cookies = {
                            k: v
                            for k, v in auth_result.items()
                            if not k.startswith("oauth")
                            and not k.startswith("authentication")
                        }
                        self.logger.info("OAuth hybrid authentication successful")
                    else:
                        # Pure OAuth authentication
                        self.cookies = {
                            "oauth_access_token": auth_result.get("access_token", "")
                        }
                        self.logger.info("OAuth authentication successful")
                elif "aspnet_authenticated" in auth_result:
                    # Traditional ASP.NET authentication
                    self.cookies = {
                        k: v
                        for k, v in auth_result.items()
                        if not k.startswith("aspnet")
                    }
                    self.logger.info("ASP.NET authentication successful")
                else:
                    # Unknown result format
                    self.logger.error("Unknown authentication result format")
                    raise FogisLoginError(
                        "Authentication completed but result format is unknown"
                    )

                # Set cookies in session
                for key, value in self.cookies.items():
                    self.session.cookies.set(key, value)

                self.logger.info(f"Login successful with {len(self.cookies)} cookies")
                return self.cookies

            except (FogisAuthenticationError, FogisOAuthAuthenticationError) as e:
                error_msg = f"Login failed: {e}"
                self.logger.error(error_msg)
                raise FogisLoginError(error_msg) from e
            except Exception as e:
                error_msg = f"Login request failed: {e}"
                self.logger.error(error_msg)
                raise FogisAPIRequestError(error_msg) from e

        # Replace the login method
        FogisApiClient.login = oauth_enabled_login

        logger.info("✅ Successfully patched FogisApiClient.login with OAuth support")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to patch FogisApiClient: {e}")
        return False


if __name__ == "__main__":
    # Apply the patch
    success = patch_fogis_authentication()
    if success:
        print("✅ OAuth monkey patch applied successfully")
    else:
        print("❌ Failed to apply OAuth monkey patch")
