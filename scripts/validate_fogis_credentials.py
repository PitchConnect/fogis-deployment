#!/usr/bin/env python3

"""
FOGIS Credential Validation Script
Validates FOGIS credentials by testing authentication with the FOGIS API
Part of the credential preservation improvement initiative
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FOGISCredentialValidator:
    """Validates FOGIS credentials by testing authentication"""

    def __init__(self, username: str = None, password: str = None):
        """Initialize validator with credentials"""
        self.username = username or os.getenv("FOGIS_USERNAME")
        self.password = password or os.getenv("FOGIS_PASSWORD")
        self.session = requests.Session()
        self.session.timeout = 30

        # FOGIS API endpoints
        self.base_url = "https://fogis.se"
        self.login_url = f"{self.base_url}/login"
        self.matches_url = f"{self.base_url}/matches"

    def load_credentials_from_env_file(self, env_file: str = ".env") -> bool:
        """Load credentials from .env file"""
        try:
            if not os.path.exists(env_file):
                logger.warning(f"Environment file not found: {env_file}")
                return False

            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("FOGIS_USERNAME="):
                        self.username = line.split("=", 1)[1].strip("\"'")
                    elif line.startswith("FOGIS_PASSWORD="):
                        self.password = line.split("=", 1)[1].strip("\"'")

            return bool(self.username and self.password)

        except Exception as e:
            logger.error(f"Error loading credentials from {env_file}: {e}")
            return False

    def validate_credentials_format(self) -> Tuple[bool, str]:
        """Validate credential format and presence"""
        if not self.username:
            return False, "FOGIS username not provided"

        if not self.password:
            return False, "FOGIS password not provided"

        if len(self.username.strip()) == 0:
            return False, "FOGIS username is empty"

        if len(self.password.strip()) == 0:
            return False, "FOGIS password is empty"

        return True, "Credentials format is valid"

    def test_fogis_authentication(self) -> Tuple[bool, str, Dict]:
        """Test FOGIS authentication by attempting login"""
        try:
            logger.info("Testing FOGIS authentication...")

            # First, get the login page to establish session
            logger.debug("Fetching login page...")
            response = self.session.get(self.login_url)
            response.raise_for_status()

            # Prepare login data
            login_data = {"username": self.username, "password": self.password}

            # Attempt login
            logger.debug("Attempting login...")
            login_response = self.session.post(
                self.login_url, data=login_data, allow_redirects=True
            )

            # Check if login was successful
            if login_response.status_code == 200:
                # Check for common login failure indicators
                response_text = login_response.text.lower()

                if any(
                    indicator in response_text
                    for indicator in ["invalid", "incorrect", "failed", "error", "fel"]
                ):
                    return (
                        False,
                        "Login failed: Invalid credentials",
                        {
                            "status_code": login_response.status_code,
                            "response_length": len(login_response.text),
                        },
                    )

                # Try to access a protected resource to confirm authentication
                logger.debug("Testing access to protected resource...")
                matches_response = self.session.get(self.matches_url)

                if matches_response.status_code == 200:
                    return (
                        True,
                        "FOGIS authentication successful",
                        {
                            "status_code": matches_response.status_code,
                            "authenticated": True,
                            "response_length": len(matches_response.text),
                        },
                    )
                else:
                    return (
                        False,
                        f"Authentication failed: Unable to access protected resource (HTTP {matches_response.status_code})",
                        {
                            "status_code": matches_response.status_code,
                            "authenticated": False,
                        },
                    )
            else:
                return (
                    False,
                    f"Login failed: HTTP {login_response.status_code}",
                    {"status_code": login_response.status_code, "authenticated": False},
                )

        except requests.exceptions.Timeout:
            return False, "Authentication failed: Request timeout", {"error": "timeout"}
        except requests.exceptions.ConnectionError:
            return (
                False,
                "Authentication failed: Connection error",
                {"error": "connection"},
            )
        except requests.exceptions.RequestException as e:
            return False, f"Authentication failed: {str(e)}", {"error": str(e)}
        except Exception as e:
            return (
                False,
                f"Unexpected error during authentication: {str(e)}",
                {"error": str(e)},
            )

    def validate(self) -> Tuple[bool, str, Dict]:
        """Perform complete credential validation"""
        logger.info("Starting FOGIS credential validation...")

        # Step 1: Load credentials if not provided
        if not self.username or not self.password:
            logger.info("Loading credentials from .env file...")
            if not self.load_credentials_from_env_file():
                return False, "Could not load FOGIS credentials", {}

        # Step 2: Validate credential format
        logger.info("Validating credential format...")
        format_valid, format_message = self.validate_credentials_format()
        if not format_valid:
            return False, format_message, {}

        logger.info(f"Credentials loaded for user: {self.username}")

        # Step 3: Test authentication
        logger.info("Testing FOGIS authentication...")
        auth_success, auth_message, auth_details = self.test_fogis_authentication()

        return auth_success, auth_message, auth_details


def print_colored(message: str, color: str = "white"):
    """Print colored output"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "white": "\033[0m",
    }
    print(f"{colors.get(color, colors['white'])}{message}\033[0m")


def main():
    """Main validation function"""
    print_colored("🔐 FOGIS Credential Validation", "blue")
    print_colored("=" * 35, "blue")
    print()

    # Parse command line arguments
    username = None
    password = None

    if len(sys.argv) > 1:
        if sys.argv[1] in ["-h", "--help"]:
            print("Usage: python3 validate_fogis_credentials.py [username] [password]")
            print()
            print("If no arguments provided, credentials will be loaded from .env file")
            print(
                "Environment variables FOGIS_USERNAME and FOGIS_PASSWORD are also supported"
            )
            sys.exit(0)
        elif len(sys.argv) >= 3:
            username = sys.argv[1]
            password = sys.argv[2]

    # Create validator
    validator = FOGISCredentialValidator(username, password)

    # Perform validation
    try:
        success, message, details = validator.validate()

        if success:
            print_colored("✅ " + message, "green")
            print()
            print_colored("Validation Details:", "blue")
            for key, value in details.items():
                print(f"  • {key}: {value}")
            print()
            print_colored("🎉 FOGIS credentials are valid and working!", "green")
            sys.exit(0)
        else:
            print_colored("❌ " + message, "red")
            print()
            if details:
                print_colored("Error Details:", "yellow")
                for key, value in details.items():
                    print(f"  • {key}: {value}")
                print()

            print_colored("💡 Troubleshooting Tips:", "yellow")
            print("  • Verify your FOGIS username and password are correct")
            print("  • Check your internet connection")
            print("  • Ensure FOGIS website is accessible")
            print("  • Try logging in manually at https://fogis.se")
            print()
            sys.exit(1)

    except KeyboardInterrupt:
        print_colored("\n⏹️  Validation cancelled by user", "yellow")
        sys.exit(1)
    except Exception as e:
        print_colored(f"❌ Unexpected error: {str(e)}", "red")
        logger.exception("Unexpected error during validation")
        sys.exit(1)


if __name__ == "__main__":
    main()
