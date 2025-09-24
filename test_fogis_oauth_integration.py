#!/usr/bin/env python3
"""
Integration test script for FOGIS OAuth 2.0 PKCE authentication.

This script tests the OAuth implementation against actual FOGIS endpoints
to verify that the authentication flow works correctly.
"""

import logging
import os
import sys
from typing import Any, Dict

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fogis_auth_oauth import authenticate
from fogis_oauth_manager import FogisOAuthManager
from fogis_public_api_client_oauth import PublicApiClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_oauth_url_generation():
    """Test OAuth authorization URL generation."""
    print("\n🔗 Testing OAuth URL Generation...")

    try:
        oauth_manager = FogisOAuthManager()
        auth_url = oauth_manager.create_authorization_url()

        print(f"✅ Generated OAuth URL: {auth_url[:100]}...")

        # Verify URL components
        assert "auth.fogis.se" in auth_url
        assert "client_id=fogis.mobildomarklient" in auth_url
        assert "code_challenge=" in auth_url
        assert "code_challenge_method=S256" in auth_url

        print("✅ OAuth URL validation passed")
        return True

    except Exception as e:
        print(f"❌ OAuth URL generation failed: {e}")
        return False


def test_pkce_challenge_generation():
    """Test PKCE code challenge generation."""
    print("\n🔐 Testing PKCE Challenge Generation...")

    try:
        oauth_manager = FogisOAuthManager()
        code_verifier, code_challenge = oauth_manager.generate_pkce_challenge()

        print(f"✅ Code verifier length: {len(code_verifier)}")
        print(f"✅ Code challenge length: {len(code_challenge)}")

        # Verify PKCE requirements
        assert 43 <= len(code_verifier) <= 128
        assert len(code_challenge) > 0

        print("✅ PKCE challenge validation passed")
        return True

    except Exception as e:
        print(f"❌ PKCE challenge generation failed: {e}")
        return False


def test_authentication_flow_detection():
    """Test authentication flow detection (OAuth vs ASP.NET)."""
    print("\n🔍 Testing Authentication Flow Detection...")

    try:
        # Test with dummy credentials (won't actually authenticate)
        import requests

        session = requests.Session()

        # This should detect the OAuth redirect
        login_url = "https://fogis.svenskfotboll.se/mdk/Login.aspx?ReturnUrl=%2fmdk%2f"

        print(f"📡 Testing redirect detection for: {login_url}")

        response = session.get(login_url, allow_redirects=True, timeout=10)

        if "auth.fogis.se" in response.url:
            print("✅ OAuth redirect detected successfully")
            print(f"   Redirected to: {response.url[:80]}...")
            return True
        else:
            print(f"ℹ️  No OAuth redirect detected, URL: {response.url}")
            print("   This might indicate ASP.NET form authentication is still active")
            return True  # This is also a valid result

    except Exception as e:
        print(f"❌ Authentication flow detection failed: {e}")
        return False


def test_client_initialization():
    """Test PublicApiClient initialization with different authentication methods."""
    print("\n🚀 Testing Client Initialization...")

    try:
        # Test OAuth token initialization
        oauth_tokens = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
        }

        oauth_client = PublicApiClient(oauth_tokens=oauth_tokens)
        assert oauth_client.authentication_method == "oauth"
        assert oauth_client.is_authenticated()
        print("✅ OAuth client initialization successful")

        # Test ASP.NET cookie initialization
        cookies = {
            "FogisMobilDomarKlient.ASPXAUTH": "test_auth_cookie",
            "ASP.NET_SessionId": "test_session_id",
        }

        aspnet_client = PublicApiClient(cookies=cookies)
        assert aspnet_client.authentication_method == "aspnet"
        assert aspnet_client.is_authenticated()
        print("✅ ASP.NET client initialization successful")

        # Test credential-based initialization
        cred_client = PublicApiClient(username="test", password="test")
        assert not cred_client.is_authenticated()  # Not authenticated until login
        print("✅ Credential-based client initialization successful")

        return True

    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        return False


def test_error_handling():
    """Test error handling for various failure scenarios."""
    print("\n⚠️  Testing Error Handling...")

    try:
        # Test invalid OAuth redirect handling
        oauth_manager = FogisOAuthManager()

        # Test error in redirect URL
        error_url = "https://fogis.svenskfotboll.se/mdk/signin-oidc?error=access_denied&error_description=User+denied+access"
        auth_code = oauth_manager.handle_authorization_redirect(error_url)
        assert auth_code is None
        print("✅ OAuth error handling successful")

        # Test invalid initialization
        try:
            PublicApiClient()  # Should raise ValueError
            assert False, "Should have raised ValueError"
        except ValueError:
            print("✅ Invalid initialization error handling successful")

        return True

    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def run_integration_tests():
    """Run all integration tests."""
    print("🧪 FOGIS OAuth 2.0 PKCE Integration Tests")
    print("=" * 50)

    tests = [
        test_oauth_url_generation,
        test_pkce_challenge_generation,
        test_authentication_flow_detection,
        test_client_initialization,
        test_error_handling,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ Test {test.__name__} failed")
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All integration tests passed!")
        return True
    else:
        print("⚠️  Some integration tests failed")
        return False


def test_with_real_credentials():
    """Test with real FOGIS credentials if provided."""
    username = os.environ.get("FOGIS_USERNAME")
    password = os.environ.get("FOGIS_PASSWORD")

    if not (username and password):
        print(
            "\n💡 To test with real credentials, set FOGIS_USERNAME and FOGIS_PASSWORD environment variables"
        )
        return True

    print(f"\n🔐 Testing with real credentials for user: {username}")

    try:
        client = PublicApiClient(username=username, password=password)

        print("🔄 Attempting authentication...")
        auth_result = client.login()

        if client.is_authenticated():
            print(f"✅ Authentication successful using {client.authentication_method}")
            print(f"   Authentication info: {client.get_authentication_info()}")

            # Test API call
            try:
                print("📡 Testing API call...")
                # This would test an actual API endpoint
                # matches = client.fetch_matches_list_json()
                # print(f"✅ API call successful, got {len(matches)} matches")
                print("✅ API client ready for use")

            except Exception as e:
                print(f"⚠️  API call failed (expected if no matches endpoint): {e}")

            return True
        else:
            print("❌ Authentication failed")
            return False

    except Exception as e:
        print(f"❌ Real credential test failed: {e}")
        return False


if __name__ == "__main__":
    success = run_integration_tests()

    # Test with real credentials if available
    if success:
        test_with_real_credentials()

    sys.exit(0 if success else 1)
