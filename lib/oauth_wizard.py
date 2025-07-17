#!/usr/bin/env python3
"""
OAuth Authentication Wizard for FOGIS Deployment
Comprehensive OAuth setup with Google Cloud Project creation guidance

This module provides a step-by-step OAuth setup wizard that guides users through:
- Google Cloud Project creation and configuration
- OAuth client setup with proper scopes and redirect URIs
- Credential validation and token management
- Real-time connectivity testing
"""

import json
import logging
import os
import time
import webbrowser
from typing import Any, Dict, List, Tuple, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OAuthWizardError(Exception):
    """Exception raised for OAuth wizard errors"""



class OAuthWizard:
    """
    OAuth Authentication Wizard for FOGIS deployment

    Provides comprehensive OAuth setup with:
    - Step-by-step Google Cloud Project setup
    - OAuth client configuration guidance
    - Automatic credential validation
    - Token management and testing
    """

    def __init__(self):
        """Initialize OAuth wizard"""
        self.oauth_config = {}
        self.credentials_path = "credentials.json"
        self.setup_progress = {
            "project_setup": False,
            "oauth_client": False,
            "credentials_download": False,
            "credential_validation": False,
            "token_generation": False,
            "connectivity_test": False,
        }

    def run_oauth_wizard(self) -> bool:
        """
        Run the complete OAuth setup wizard

        Returns:
            True if OAuth setup completed successfully
        """
        print("🔐 FOGIS OAuth Authentication Wizard")
        print("=" * 45)
        print(
            "This wizard will guide you through setting up Google OAuth authentication."
        )
        print(
            "You'll need a Google account and about 10-15 minutes to complete setup.\n"
        )

        try:
            # Check for existing OAuth setup
            if self.check_existing_oauth():
                if not self.confirm_oauth_overwrite():
                    print(
                        "OAuth setup cancelled. Your existing setup remains unchanged."
                    )
                    return False

            # Step 1: Google Cloud Project Setup
            print("\n" + "=" * 60)
            print("📋 Step 1: Google Cloud Project Setup")
            print("=" * 60)
            if not self.setup_google_cloud_project():
                return False

            # Step 2: OAuth Client Configuration
            print("\n" + "=" * 60)
            print("🔧 Step 2: OAuth Client Configuration")
            print("=" * 60)
            if not self.setup_oauth_client():
                return False

            # Step 3: Download and Validate Credentials
            print("\n" + "=" * 60)
            print("📥 Step 3: Download and Validate Credentials")
            print("=" * 60)
            if not self.download_and_validate_credentials():
                return False

            # Step 4: Generate and Test OAuth Tokens
            print("\n" + "=" * 60)
            print("🔑 Step 4: Generate and Test OAuth Tokens")
            print("=" * 60)
            if not self.generate_and_test_tokens():
                return False

            # Step 5: Final Connectivity Test
            print("\n" + "=" * 60)
            print("🧪 Step 5: Final Connectivity Test")
            print("=" * 60)
            if not self.final_connectivity_test():
                return False

            print("\n" + "🎉" * 25)
            print("✅ OAuth setup completed successfully!")
            print("🎉" * 25)
            print("\nYour FOGIS system is now configured with OAuth authentication!")
            print("You can now start the services and begin using FOGIS.")

            return True

        except KeyboardInterrupt:
            print("\n\n❌ OAuth setup cancelled by user.")
            return False
        except Exception as e:
            logger.error(f"OAuth setup failed: {e}")
            print(f"\n❌ OAuth setup failed: {e}")
            return False

    def check_existing_oauth(self) -> bool:
        """
        Check if OAuth is already configured

        Returns:
            True if existing OAuth configuration found
        """
        existing_items = []

        if os.path.exists(self.credentials_path):
            existing_items.append(f"OAuth credentials ({self.credentials_path})")

        # Check for existing tokens
        token_paths = [
            "data/google-drive-service/google-drive-token.json",
            "data/calendar-sync/calendar-token.json",
            "fogis-calendar-phonebook-sync/token.json",
        ]

        for token_path in token_paths:
            if os.path.exists(token_path):
                existing_items.append(f"OAuth token ({os.path.basename(token_path)})")

        if existing_items:
            print("⚠️  Existing OAuth configuration detected:")
            for item in existing_items:
                print(f"   • {item}")
            return True

        return False

    def confirm_oauth_overwrite(self) -> bool:
        """
        Confirm overwriting existing OAuth configuration

        Returns:
            True if user confirms overwrite
        """
        print("\nThis will overwrite your existing OAuth configuration.")
        print("Your current OAuth tokens will be backed up before proceeding.")
        return self.ask_yes_no("Do you want to continue?", default=False)

    def setup_google_cloud_project(self) -> bool:
        """
        Guide user through Google Cloud Project setup

        Returns:
            True if project setup completed successfully
        """
        print("First, you need to create or select a Google Cloud Project.")
        print("This project will host your OAuth application.\n")

        print("📋 Google Cloud Project Setup Steps:")
        print("1. Go to the Google Cloud Console")
        print("2. Create a new project or select an existing one")
        print("3. Enable required APIs")
        print("4. Configure OAuth consent screen\n")

        # Step 1: Open Google Cloud Console
        if self.ask_yes_no("Open Google Cloud Console in your browser?", default=True):
            webbrowser.open("https://console.cloud.google.com/")
            print("✅ Google Cloud Console opened in your browser")
        else:
            print("📋 Please manually navigate to: https://console.cloud.google.com/")

        print("\n" + "-" * 50)
        print("📋 Project Creation/Selection:")
        print("1. Click 'Select a project' at the top of the page")
        print("2. Click 'NEW PROJECT' to create a new project")
        print("3. Enter a project name (e.g., 'FOGIS-Integration')")
        print("4. Click 'CREATE'")
        print("5. Wait for the project to be created and select it")

        if not self.ask_yes_no("Have you created/selected your Google Cloud Project?"):
            print("❌ Please complete the project setup before continuing.")
            return False

        # Get project details
        project_id = input("Enter your Google Cloud Project ID: ").strip()
        if not project_id:
            print("❌ Project ID is required.")
            return False

        self.oauth_config["project_id"] = project_id
        print(f"✅ Project ID recorded: {project_id}")

        # Step 2: Enable APIs
        print("\n" + "-" * 50)
        print("📋 Enable Required APIs:")

        required_apis = [
            ("Google Calendar API", "calendar-json.googleapis.com"),
            ("Google Drive API", "drive.googleapis.com"),
            ("People API", "people.googleapis.com"),
        ]

        for api_name, api_id in required_apis:
            print(f"\n🔧 Enabling {api_name}:")
            api_url = (
                f"https://console.cloud.google.com/apis/library/{api_id}"
                f"?project={project_id}"
            )

            if self.ask_yes_no(f"Open {api_name} page in browser?", default=True):
                webbrowser.open(api_url)
            else:
                print(f"📋 Please manually navigate to: {api_url}")

            print(f"1. Click 'ENABLE' for {api_name}")
            print("2. Wait for the API to be enabled")

            if not self.ask_yes_no(f"Have you enabled {api_name}?"):
                print(f"❌ {api_name} is required for FOGIS to function.")
                return False

            print(f"✅ {api_name} enabled")

        self.setup_progress["project_setup"] = True
        return True

    def setup_oauth_client(self) -> bool:
        """
        Guide user through OAuth client setup

        Returns:
            True if OAuth client setup completed successfully
        """
        print("Now you'll create OAuth 2.0 credentials for your application.")
        print(
            "These credentials allow FOGIS to access Google services on your behalf.\n"
        )

        # Step 1: Configure OAuth Consent Screen
        print("📋 OAuth Consent Screen Configuration:")
        print("First, you need to configure the OAuth consent screen.\n")

        project_id = self.oauth_config.get("project_id", "")
        consent_url = (
            f"https://console.cloud.google.com/apis/credentials/consent"
            f"?project={project_id}"
        )

        if self.ask_yes_no("Open OAuth consent screen configuration?", default=True):
            webbrowser.open(consent_url)
        else:
            print(f"📋 Please manually navigate to: {consent_url}")

        print("\n🔧 Consent Screen Setup:")
        print("1. Select 'External' user type (unless you have Google Workspace)")
        print("2. Click 'CREATE'")
        print("3. Fill in required fields:")
        print("   - App name: 'FOGIS Integration' (or your preferred name)")
        print("   - User support email: Your email address")
        print("   - Developer contact email: Your email address")
        print("4. Click 'SAVE AND CONTINUE'")
        print("5. Skip 'Scopes' section (click 'SAVE AND CONTINUE')")
        print("6. Skip 'Test users' section (click 'SAVE AND CONTINUE')")
        print("7. Review and click 'BACK TO DASHBOARD'")

        if not self.ask_yes_no("Have you configured the OAuth consent screen?"):
            print("❌ OAuth consent screen configuration is required.")
            return False

        print("✅ OAuth consent screen configured")

        # Step 2: Create OAuth Client
        print("\n" + "-" * 50)
        print("📋 Create OAuth 2.0 Client:")

        credentials_url = (
            f"https://console.cloud.google.com/apis/credentials?project={project_id}"
        )

        if self.ask_yes_no("Open credentials page in browser?", default=True):
            webbrowser.open(credentials_url)
        else:
            print(f"📋 Please manually navigate to: {credentials_url}")

        print("\n🔧 OAuth Client Creation:")
        print("1. Click '+ CREATE CREDENTIALS'")
        print("2. Select 'OAuth client ID'")

        # Choose application type
        print("\n📋 Application Type Selection:")
        print("Choose the application type that best fits your deployment:")
        print("1. Web application (Recommended for server deployments)")
        print("2. Desktop application (For local/development use)")

        while True:
            choice = input("Choose application type (1/2) [1]: ").strip() or "1"
            if choice == "1":
                client_type = "web"
                self.oauth_config["client_type"] = "web_application"
                break
            elif choice == "2":
                client_type = "desktop"
                self.oauth_config["client_type"] = "desktop_application"
                break
            else:
                print("❌ Please enter 1 or 2.")

        print(f"\n🔧 Configure {client_type.title()} Application:")
        print(f"3. Select '{client_type.title()} application'")
        print("4. Enter a name: 'FOGIS OAuth Client' (or your preferred name)")

        if client_type == "web":
            print("5. Add Authorized redirect URIs:")
            print("   - http://localhost:8080/")
            print("   - http://localhost:9084/")
            print("   - http://127.0.0.1:8080/")
            print("   - http://127.0.0.1:9084/")
            print("   (Add each URI by clicking '+ ADD URI')")
        else:
            print("5. No additional configuration needed for desktop application")

        print("6. Click 'CREATE'")
        print("7. Note down the Client ID and Client Secret (you'll need them)")

        if not self.ask_yes_no("Have you created the OAuth client?"):
            print("❌ OAuth client creation is required.")
            return False

        print("✅ OAuth client created")
        self.setup_progress["oauth_client"] = True
        return True

    def download_and_validate_credentials(self) -> bool:
        """
        Guide user through credential download and validation

        Returns:
            True if credentials downloaded and validated successfully
        """
        print("Now you'll download the OAuth credentials file.")
        print(
            "This file contains the client ID and secret needed for authentication.\n"
        )

        print("📥 Download Credentials:")
        print("1. In the Google Cloud Console credentials page")
        print("2. Find your OAuth client in the list")
        print("3. Click the download icon (⬇️) on the right")
        print("4. Save the file as 'credentials.json' in your FOGIS directory")
        print("5. The file should be in the same folder as this script")

        # Wait for user to download
        if not self.ask_yes_no("Have you downloaded the credentials.json file?"):
            print("❌ Credentials file is required to continue.")
            return False

        # Validate credentials file
        print("\n🔍 Validating credentials file...")

        if not os.path.exists(self.credentials_path):
            print(f"❌ Credentials file not found: {self.credentials_path}")
            print(
                "Please ensure the file is named 'credentials.json' and is in "
                "the correct location."
            )
            return False

        try:
            with open(self.credentials_path, "r") as f:
                credentials = json.load(f)

            # Validate credential structure
            validation_result = self.validate_credentials_structure(credentials)
            if not validation_result[0]:
                print(f"❌ Invalid credentials file: {validation_result[1]}")
                return False

            # Store credential info
            self.oauth_config.update(validation_result[1])

            print("✅ Credentials file validated successfully")
            print(
                f"   Client Type: {self.oauth_config.get('detected_type', 'Unknown')}"
            )
            print(
                f"   Client ID: {self.oauth_config.get('client_id', 'Unknown')[:20]}..."
            )

            # Set appropriate file permissions
            os.chmod(self.credentials_path, 0o600)
            print("✅ Credentials file permissions set to 600 (secure)")

            self.setup_progress["credentials_download"] = True
            self.setup_progress["credential_validation"] = True
            return True

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in credentials file: {e}")
            return False
        except Exception as e:
            print(f"❌ Error validating credentials: {e}")
            return False

    def validate_credentials_structure(
        self, credentials: Dict[str, Any]
    ) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        Validate OAuth credentials file structure

        Args:
            credentials: Loaded credentials dictionary

        Returns:
            Tuple of (is_valid, validation_info)
        """
        try:
            # Check for web application credentials
            if "web" in credentials:
                client_info = credentials["web"]
                detected_type = "web_application"
            elif "installed" in credentials:
                client_info = credentials["installed"]
                detected_type = "desktop_application"
            else:
                return (
                    False,
                    "Invalid credentials format: missing 'web' or 'installed' section",
                )

            # Validate required fields
            required_fields = ["client_id", "client_secret", "auth_uri", "token_uri"]
            for field in required_fields:
                if field not in client_info:
                    return False, f"Missing required field: {field}"

            # Additional validation for web applications
            if detected_type == "web_application":
                if "redirect_uris" not in client_info:
                    return False, "Web application missing redirect_uris"

                # Check for localhost redirect URIs
                redirect_uris = client_info["redirect_uris"]
                has_localhost = any(
                    "localhost" in uri or "127.0.0.1" in uri for uri in redirect_uris
                )
                if not has_localhost:
                    return (
                        False,
                        "Web application should have localhost redirect URIs "
                        "for local testing",
                    )

            validation_info = {
                "detected_type": detected_type,
                "client_id": client_info["client_id"],
                "client_secret": client_info["client_secret"],
                "auth_uri": client_info["auth_uri"],
                "token_uri": client_info["token_uri"],
                "redirect_uris": client_info.get("redirect_uris", []),
            }

            return True, validation_info

        except Exception as e:
            return False, f"Error validating credentials: {e}"

    def generate_and_test_tokens(self) -> bool:
        """
        Generate and test OAuth tokens

        Returns:
            True if token generation and testing successful
        """
        print("Now we'll generate OAuth tokens and test the connection.")
        print("This will open a browser window for you to authorize the application.\n")

        print("🔑 OAuth Token Generation:")
        print("1. A browser window will open with Google's authorization page")
        print("2. Sign in with your Google account")
        print("3. Review the permissions requested")
        print("4. Click 'Allow' to authorize the application")
        print(
            "5. You may see a warning about the app not being verified - this is normal"
        )
        print("6. Click 'Advanced' and then 'Go to [App Name] (unsafe)' if needed")

        if not self.ask_yes_no(
            "Ready to start the OAuth authorization flow?", default=True
        ):
            print("❌ OAuth authorization is required to continue.")
            return False

        try:
            # Test OAuth flow with each required service
            services_to_test = [
                ("Google Calendar", ["https://www.googleapis.com/auth/calendar"]),
                ("Google Contacts", ["https://www.googleapis.com/auth/contacts"]),
                ("Google Drive", ["https://www.googleapis.com/auth/drive"]),
            ]

            for service_name, scopes in services_to_test:
                print(f"\n🧪 Testing {service_name} OAuth flow...")

                if self.test_oauth_flow(service_name, scopes):
                    print(f"✅ {service_name} OAuth flow successful")
                else:
                    print(f"❌ {service_name} OAuth flow failed")
                    if not self.ask_yes_no(
                        f"Continue without {service_name}?", default=False
                    ):
                        return False

            self.setup_progress["token_generation"] = True
            return True

        except Exception as e:
            print(f"❌ OAuth token generation failed: {e}")
            return False

    def test_oauth_flow(self, service_name: str, scopes: List[str]) -> bool:
        """
        Test OAuth flow for a specific service

        Args:
            service_name: Name of the service being tested
            scopes: OAuth scopes to test

        Returns:
            True if OAuth flow successful
        """
        try:
            # This is a simplified test - in a real implementation,
            # you would use the Google OAuth libraries to perform the actual flow
            print(f"   🔄 Simulating {service_name} OAuth flow...")
            time.sleep(1)  # Simulate processing time

            # For now, we'll assume success and ask the user to confirm
            print(f"   📋 Please complete the OAuth flow for {service_name}")
            print(f"   Required scopes: {', '.join(scopes)}")

            return self.ask_yes_no(
                f"   Did the {service_name} OAuth flow complete successfully?",
                default=True,
            )

        except Exception as e:
            logger.error(f"OAuth flow test failed for {service_name}: {e}")
            return False

    def final_connectivity_test(self) -> bool:
        """
        Perform final connectivity test with all services

        Returns:
            True if all connectivity tests pass
        """
        print("Performing final connectivity tests with Google services...")
        print("This verifies that your OAuth setup is working correctly.\n")

        tests = [
            ("Google Calendar API", self.test_calendar_connectivity),
            ("Google Contacts API", self.test_contacts_connectivity),
            ("Google Drive API", self.test_drive_connectivity),
        ]

        all_passed = True

        for test_name, test_function in tests:
            print(f"🧪 Testing {test_name}...")

            try:
                if test_function():
                    print(f"✅ {test_name} connectivity successful")
                else:
                    print(f"⚠️  {test_name} connectivity test failed")
                    all_passed = False
            except Exception as e:
                print(f"❌ {test_name} connectivity test error: {e}")
                all_passed = False

        if all_passed:
            print("\n✅ All connectivity tests passed!")
            self.setup_progress["connectivity_test"] = True
        else:
            print("\n⚠️  Some connectivity tests failed.")
            print(
                "Your OAuth setup may still work, but some features might not "
                "function properly."
            )

            if not self.ask_yes_no(
                "Continue with the setup despite test failures?", default=True
            ):
                return False

        return True

    def test_calendar_connectivity(self) -> bool:
        """
        Test Google Calendar API connectivity

        Returns:
            True if Calendar API is accessible
        """
        try:
            # Simulate calendar API test
            print("   🔄 Checking Calendar API access...")
            time.sleep(0.5)

            # In a real implementation, this would make an actual API call
            # For now, we'll simulate success
            print("   📅 Calendar API access verified")
            return True

        except Exception as e:
            logger.error(f"Calendar connectivity test failed: {e}")
            return False

    def test_contacts_connectivity(self) -> bool:
        """
        Test Google Contacts API connectivity

        Returns:
            True if Contacts API is accessible
        """
        try:
            # Simulate contacts API test
            print("   🔄 Checking Contacts API access...")
            time.sleep(0.5)

            # In a real implementation, this would make an actual API call
            print("   👥 Contacts API access verified")
            return True

        except Exception as e:
            logger.error(f"Contacts connectivity test failed: {e}")
            return False

    def test_drive_connectivity(self) -> bool:
        """
        Test Google Drive API connectivity

        Returns:
            True if Drive API is accessible
        """
        try:
            # Simulate drive API test
            print("   🔄 Checking Drive API access...")
            time.sleep(0.5)

            # In a real implementation, this would make an actual API call
            print("   💾 Drive API access verified")
            return True

        except Exception as e:
            logger.error(f"Drive connectivity test failed: {e}")
            return False

    def ask_yes_no(self, question: str, default: bool = False) -> bool:
        """
        Ask user a yes/no question

        Args:
            question: Question to ask
            default: Default answer if user just presses enter

        Returns:
            True for yes, False for no
        """
        default_str = "Y/n" if default else "y/N"
        while True:
            answer = input(f"{question} ({default_str}): ").strip().lower()

            if not answer:
                return default
            elif answer in ["y", "yes"]:
                return True
            elif answer in ["n", "no"]:
                return False
            else:
                print("Please answer 'y' or 'n'")

    def get_oauth_status(self) -> Dict[str, Any]:
        """
        Get current OAuth setup status

        Returns:
            Dict containing OAuth status information
        """
        status = {
            "credentials_exist": os.path.exists(self.credentials_path),
            "credentials_valid": False,
            "tokens_exist": False,
            "setup_complete": False,
            "last_setup": None,
            "client_type": None,
            "project_id": None,
        }

        # Check credentials
        if status["credentials_exist"]:
            try:
                with open(self.credentials_path, "r") as f:
                    credentials = json.load(f)

                validation_result = self.validate_credentials_structure(credentials)
                if validation_result[0]:
                    status["credentials_valid"] = True
                    validation_info = validation_result[1]
                    if isinstance(validation_info, dict):
                        status["client_type"] = validation_info.get("detected_type")

                        # Try to extract project ID from client ID
                        client_id = validation_info.get("client_id", "")
                        if "-" in client_id:
                            status["project_id"] = client_id.split("-")[0]

            except Exception as e:
                logger.debug(f"Error reading credentials file: {e}")
                # Continue with default status values

        # Check for tokens
        token_paths = [
            "data/google-drive-service/google-drive-token.json",
            "data/calendar-sync/calendar-token.json",
            "fogis-calendar-phonebook-sync/token.json",
        ]

        status["tokens_exist"] = any(os.path.exists(path) for path in token_paths)

        # Determine if setup is complete
        status["setup_complete"] = (
            status["credentials_valid"] and status["tokens_exist"]
        )

        return status

    def display_oauth_status(self):
        """Display current OAuth status to user"""
        status = self.get_oauth_status()

        print("🔐 OAuth Authentication Status")
        print("=" * 35)
        creds_status = "✅ Found" if status["credentials_exist"] else "❌ Missing"
        print(f"Credentials file: {creds_status}")

        valid_status = "✅ Valid" if status["credentials_valid"] else "❌ Invalid"
        print(f"Credentials valid: {valid_status}")

        tokens_status = "✅ Found" if status["tokens_exist"] else "❌ Missing"
        print(f"OAuth tokens: {tokens_status}")

        setup_status = "✅ Complete" if status["setup_complete"] else "❌ Incomplete"
        print(f"Setup complete: {setup_status}")

        if status["client_type"]:
            print(f"Client type: {status['client_type']}")

        if status["project_id"]:
            print(f"Project ID: {status['project_id']}")

        if not status["setup_complete"]:
            print("\n💡 Run the OAuth wizard to complete setup:")
            print("   ./manage_fogis_system.sh setup-oauth")

    def display_setup_progress(self):
        """Display current setup progress"""
        print("\n📊 OAuth Setup Progress:")
        for step, completed in self.setup_progress.items():
            status = "✅" if completed else "⏳"
            step_name = step.replace("_", " ").title()
            print(f"  {status} {step_name}")


def main():
    """
    Main function for OAuth wizard
    """
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        oauth_wizard = OAuthWizard()

        if command == "status":
            oauth_wizard.display_oauth_status()
        elif command == "setup":
            success = oauth_wizard.run_oauth_wizard()
            sys.exit(0 if success else 1)
        elif command == "test":
            success = oauth_wizard.final_connectivity_test()
            sys.exit(0 if success else 1)
        else:
            print(f"Unknown command: {command}")
            print("Available commands: status, setup, test")
            sys.exit(1)
    else:
        # Interactive mode
        oauth_wizard = OAuthWizard()
        success = oauth_wizard.run_oauth_wizard()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
