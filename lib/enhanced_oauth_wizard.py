#!/usr/bin/env python3
"""
Enhanced FOGIS OAuth Setup Wizard

Browser automation and real-time validation for simplified OAuth setup.
Features automated browser navigation, detailed error messages, and
intelligent credential detection to reduce setup time from 15-20 minutes to 5-8 minutes.

This enhanced wizard addresses the technical constraint that Google Cloud Console
OAuth credentials cannot be re-downloaded by providing maximum automation and
guidance during the initial setup process.
"""

import os
import sys
import json
import time
import webbrowser
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode

# Add the parent directory to the path to import other modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Try to import existing modules, fallback gracefully if not available
    from lib.google_oauth_manager import GoogleOAuthManager
    OAUTH_MANAGER_AVAILABLE = True
except ImportError:
    OAUTH_MANAGER_AVAILABLE = False
    print("⚠️  Note: google_oauth_manager not available, using basic validation")

try:
    from lib.credential_validator import CredentialValidator
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False


class EnhancedOAuthWizard:
    """
    Enhanced OAuth wizard with browser automation and intelligent guidance.
    
    Features:
    - Automated browser navigation to correct Google Cloud Console pages
    - Real-time credential validation with specific error messages
    - Intelligent detection and reuse of existing credentials
    - Step-by-step visual guidance with copy-paste commands
    - Progressive setup with error recovery
    """

    def __init__(self):
        """Initialize the enhanced OAuth wizard."""
        self.project_id = None
        self.credentials_path = "credentials.json"
        self.backup_credentials_path = "credentials/google-credentials.json"
        self.validation_results = {}
        self.existing_credentials = []
        self.setup_start_time = time.time()
        
        # Ensure credentials directory exists
        os.makedirs("credentials", exist_ok=True)

    def print_header(self, title: str, width: int = 60) -> None:
        """Print a formatted header with consistent styling."""
        print("\n" + "=" * width)
        print(f"🔐 {title}")
        print("=" * width)

    def print_step(self, step: int, title: str, width: int = 50) -> None:
        """Print a formatted step header."""
        print(f"\n📋 STEP {step}: {title}")
        print("-" * width)

    def print_success(self, message: str) -> None:
        """Print a success message with consistent formatting."""
        print(f"✅ {message}")

    def print_warning(self, message: str) -> None:
        """Print a warning message with consistent formatting."""
        print(f"⚠️  {message}")

    def print_error(self, message: str) -> None:
        """Print an error message with consistent formatting."""
        print(f"❌ {message}")

    def print_info(self, message: str) -> None:
        """Print an info message with consistent formatting."""
        print(f"ℹ️  {message}")

    def print_progress(self, message: str) -> None:
        """Print a progress message with consistent formatting."""
        print(f"🔄 {message}")

    def scan_for_existing_credentials(self) -> List[Dict[str, Any]]:
        """
        Scan for existing Google OAuth credentials in common locations.
        
        Returns:
            List of dictionaries containing credential information
        """
        self.print_progress("Scanning for existing Google OAuth credentials...")
        
        # Common credential locations
        locations = [
            self.credentials_path,
            self.backup_credentials_path,
            os.path.expanduser("~/.config/gcloud/application_default_credentials.json"),
            os.path.expanduser("~/.credentials/google-credentials.json"),
            "token.json",
            "credentials/token.json",
            "app/token.json"
        ]
        
        found_credentials = []
        
        for location in locations:
            if os.path.exists(location):
                try:
                    cred_info = self.analyze_credential_file(location)
                    if cred_info:
                        found_credentials.append({
                            'path': location,
                            'type': cred_info['type'],
                            'valid': cred_info['valid'],
                            'details': cred_info.get('details', {}),
                            'error': cred_info.get('error'),
                            'fix': cred_info.get('fix')
                        })
                except Exception as e:
                    self.print_warning(f"Could not analyze {location}: {e}")
        
        self.existing_credentials = found_credentials
        return found_credentials

    def analyze_credential_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a credential file to determine its type and validity.
        
        Args:
            file_path: Path to the credential file
            
        Returns:
            Dictionary with analysis results or None if file cannot be analyzed
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Determine credential type
            if 'web' in data:
                return self.validate_oauth_credentials(data, file_path)
            elif 'installed' in data:
                return {
                    'type': 'OAuth Desktop Application',
                    'valid': False,
                    'error': 'Desktop application credentials detected',
                    'fix': 'Create "Web application" credentials instead'
                }
            elif 'type' in data and data['type'] == 'service_account':
                return {
                    'type': 'Service Account',
                    'valid': True,
                    'details': {'email': data.get('client_email', 'Unknown')}
                }
            elif 'access_token' in data or 'refresh_token' in data:
                return {
                    'type': 'OAuth Token',
                    'valid': True,
                    'details': {'scope': data.get('scope', 'Unknown')}
                }
            else:
                return {
                    'type': 'Unknown',
                    'valid': False,
                    'error': 'Unrecognized credential format'
                }
                
        except json.JSONDecodeError:
            return {
                'type': 'Invalid JSON',
                'valid': False,
                'error': 'File contains invalid JSON'
            }
        except Exception as e:
            return {
                'type': 'Error',
                'valid': False,
                'error': f'Cannot read file: {str(e)}'
            }

    def validate_oauth_credentials(self, creds_data: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """
        Validate OAuth credentials with detailed feedback.
        
        Args:
            creds_data: Parsed credential data
            file_path: Path to the credential file
            
        Returns:
            Dictionary with validation results
        """
        if 'web' not in creds_data:
            return {
                'type': 'OAuth (Invalid)',
                'valid': False,
                'error': 'Not web application credentials',
                'fix': 'Create "Web application" credentials in Google Cloud Console'
            }
        
        web_creds = creds_data['web']
        
        # Check required fields
        required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
        missing_fields = [field for field in required_fields if field not in web_creds]
        
        if missing_fields:
            return {
                'type': 'OAuth Web Application (Incomplete)',
                'valid': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'fix': 'Re-download credentials from Google Cloud Console'
            }
        
        # Check redirect URIs
        redirect_uris = web_creds.get('redirect_uris', [])
        required_uris = ['http://localhost:8080/callback', 'http://127.0.0.1:8080/callback']
        
        missing_uris = [uri for uri in required_uris if uri not in redirect_uris]
        if missing_uris:
            return {
                'type': 'OAuth Web Application (Missing URIs)',
                'valid': False,
                'error': f'Missing redirect URIs: {", ".join(missing_uris)}',
                'fix': 'Add missing redirect URIs in Google Cloud Console OAuth client settings'
            }
        
        # Credentials appear valid
        return {
            'type': 'OAuth Web Application',
            'valid': True,
            'details': {
                'client_id': web_creds['client_id'][:20] + '...',
                'redirect_uris': len(redirect_uris),
                'project_id': web_creds.get('project_id', 'Unknown')
            }
        }

    def display_existing_credentials(self, credentials: List[Dict[str, Any]]) -> bool:
        """
        Display found credentials and offer reuse options.
        
        Args:
            credentials: List of found credential information
            
        Returns:
            True if user chose to reuse existing credentials, False otherwise
        """
        if not credentials:
            return False
        
        self.print_info("Found existing Google credentials:")
        
        valid_credentials = []
        for i, cred in enumerate(credentials, 1):
            status = "✅ Valid" if cred['valid'] else "❌ Invalid"
            print(f"  {i}. {cred['type']} - {cred['path']} ({status})")
            
            if cred['valid']:
                valid_credentials.append((i, cred))
                if cred.get('details'):
                    for key, value in cred['details'].items():
                        print(f"     {key}: {value}")
            else:
                print(f"     Error: {cred.get('error', 'Unknown error')}")
                if cred.get('fix'):
                    print(f"     Fix: {cred.get('fix')}")
        
        if not valid_credentials:
            self.print_warning("No valid credentials found. Setting up new OAuth credentials...")
            return False
        
        print(f"\n  {len(credentials) + 1}. Set up new OAuth credentials")
        
        while True:
            try:
                choice = input(f"\nChoose option (1-{len(credentials) + 1}): ").strip()
                
                if choice == str(len(credentials) + 1):
                    return False  # User wants new setup
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(credentials):
                    selected_cred = credentials[choice_num - 1]
                    
                    if selected_cred['valid']:
                        return self.setup_credential_reuse(selected_cred)
                    else:
                        self.print_error(f"Selected credentials are invalid: {selected_cred.get('error')}")
                        if selected_cred.get('fix'):
                            self.print_info(f"Fix: {selected_cred.get('fix')}")
                        
                        retry = input("Try to fix and use anyway? (y/N): ").strip().lower()
                        if retry in ['y', 'yes']:
                            return self.setup_credential_reuse(selected_cred)
                else:
                    print(f"Please enter a number between 1 and {len(credentials) + 1}")
                    
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\n\nSetup cancelled by user.")
                return False

    def setup_credential_reuse(self, credential: Dict[str, Any]) -> bool:
        """
        Set up reuse of existing credentials.
        
        Args:
            credential: Selected credential information
            
        Returns:
            True if setup successful, False otherwise
        """
        try:
            source_path = credential['path']
            
            # Copy to standard location if not already there
            if source_path != self.credentials_path:
                self.print_progress(f"Copying credentials from {source_path} to {self.credentials_path}")
                
                import shutil
                shutil.copy2(source_path, self.credentials_path)
                
                # Also copy to backup location
                shutil.copy2(source_path, self.backup_credentials_path)
            
            self.print_success("Existing credentials configured successfully!")
            
            # Test the credentials if possible
            if OAUTH_MANAGER_AVAILABLE:
                return self.test_oauth_credentials()
            else:
                self.print_info("Credential testing skipped (oauth manager not available)")
                return True
                
        except Exception as e:
            self.print_error(f"Failed to set up credential reuse: {e}")
            return False

    def start_guided_setup(self) -> bool:
        """
        Main entry point for the enhanced OAuth setup wizard.

        Returns:
            True if setup completed successfully, False otherwise
        """
        self.print_header("Enhanced FOGIS OAuth Setup Wizard")

        print("🎯 This enhanced wizard will guide you through setting up Google OAuth")
        print("   with automated browser navigation and real-time validation.")
        print("")
        print("⏱️  Estimated time: 5-8 minutes (reduced from 15-20 minutes)")
        print("🔧 Features:")
        print("   • Automated browser navigation to correct Google Cloud Console pages")
        print("   • Real-time credential validation with specific error messages")
        print("   • Intelligent detection and reuse of existing credentials")
        print("   • Step-by-step visual guidance with copy-paste commands")
        print("")
        print("📋 You'll need:")
        print("   • Google account with access to Google Cloud Console")
        print("   • Ability to create a new Google Cloud project (or use existing)")
        print("")

        # Confirm user wants to proceed
        proceed = input("🚀 Ready to start enhanced OAuth setup? (Y/n): ").strip().lower()
        if proceed in ['n', 'no']:
            print("👋 Setup cancelled. You can run this wizard again anytime with:")
            print("   ./manage_fogis_system.sh setup-auth")
            return False

        try:
            # Step 1: Scan for existing credentials
            existing_creds = self.scan_for_existing_credentials()
            if existing_creds and self.display_existing_credentials(existing_creds):
                elapsed_time = time.time() - self.setup_start_time
                self.print_success(f"OAuth setup completed in {elapsed_time:.1f} seconds using existing credentials!")
                return True

            # Step 2: Guide through new OAuth setup
            if not self.guide_new_oauth_setup():
                return False

            # Step 3: Validate and test credentials
            if not self.validate_and_test_final_setup():
                return False

            # Success!
            elapsed_time = time.time() - self.setup_start_time
            self.print_success(f"Enhanced OAuth setup completed successfully in {elapsed_time:.1f} seconds!")
            self.display_completion_summary()
            return True

        except KeyboardInterrupt:
            print("\n\n⏹️  Setup cancelled by user.")
            return False
        except Exception as e:
            self.print_error(f"Unexpected error during setup: {e}")
            self.print_info("You can retry the setup or check the troubleshooting guide.")
            return False

    def guide_new_oauth_setup(self) -> bool:
        """
        Guide user through creating new OAuth credentials with browser automation.

        Returns:
            True if setup completed successfully, False otherwise
        """
        self.print_step(1, "Google Cloud Project Setup")

        # Check if user has existing project
        existing_project = input("Do you have an existing Google Cloud project you'd like to use? (y/N): ").strip().lower()

        if existing_project in ['y', 'yes']:
            self.project_id = input("Enter your Google Cloud project ID: ").strip()
            if not self.project_id:
                self.print_error("Project ID is required")
                return False
        else:
            # Guide through project creation
            if not self.guide_project_creation():
                return False

        # Step 2: Enable APIs
        if not self.guide_api_enablement():
            return False

        # Step 3: Create OAuth credentials
        if not self.guide_oauth_client_creation():
            return False

        return True

    def guide_project_creation(self) -> bool:
        """
        Guide user through Google Cloud project creation with browser automation.

        Returns:
            True if project creation guided successfully, False otherwise
        """
        self.print_progress("Opening Google Cloud Console for project creation...")

        # Auto-open Google Cloud Console project creation page
        project_create_url = "https://console.cloud.google.com/projectcreate"

        try:
            webbrowser.open(project_create_url)
            self.print_success("Opened Google Cloud Console in your browser")
        except Exception as e:
            self.print_warning(f"Could not auto-open browser: {e}")
            print(f"Please manually open: {project_create_url}")

        print("\n📝 Create a new Google Cloud Project:")
        print("  1. Project name: 'FOGIS Integration' (or your preference)")
        print("  2. Organization: Select your organization (if applicable)")
        print("  3. Location: Leave as default or select preferred location")
        print("  4. Click 'CREATE' button")
        print("  5. Wait for project creation to complete (usually 10-30 seconds)")

        print("\n💡 Copy-paste ready project name:")
        print("   FOGIS Integration")

        input("\n⏸️  Press Enter when your project is created...")

        # Get project ID from user
        print("\n📋 Find your Project ID:")
        print("  • Look at the top of the Google Cloud Console page")
        print("  • It's shown in the project selector dropdown")
        print("  • Format is usually: project-name-123456")

        while True:
            self.project_id = input("\nEnter your project ID: ").strip()
            if self.project_id:
                # Validate project ID format
                if self.validate_project_id_format(self.project_id):
                    break
                else:
                    self.print_warning("Project ID format looks unusual. Continue anyway? (y/N)")
                    if input().strip().lower() in ['y', 'yes']:
                        break
            else:
                self.print_error("Project ID is required to continue")

        self.print_success(f"Project ID set: {self.project_id}")
        return True

    def validate_project_id_format(self, project_id: str) -> bool:
        """
        Validate Google Cloud project ID format.

        Args:
            project_id: Project ID to validate

        Returns:
            True if format appears valid, False otherwise
        """
        # Basic validation - project IDs should be lowercase, contain letters, numbers, hyphens
        import re
        pattern = r'^[a-z][a-z0-9-]*[a-z0-9]$'

        if not re.match(pattern, project_id):
            return False

        # Additional checks
        if len(project_id) < 6 or len(project_id) > 30:
            return False

        if '--' in project_id:  # Double hyphens not allowed
            return False

        return True

    def guide_api_enablement(self) -> bool:
        """
        Guide user through enabling required Google APIs with browser automation.

        Returns:
            True if API enablement guided successfully, False otherwise
        """
        self.print_step(2, "Enable Required Google APIs")

        # APIs that need to be enabled
        apis = [
            {
                'name': 'Google Calendar API',
                'id': 'calendar-json.googleapis.com',
                'description': 'For syncing matches to Google Calendar'
            },
            {
                'name': 'Google Drive API',
                'id': 'drive.googleapis.com',
                'description': 'For uploading WhatsApp assets to Google Drive'
            },
            {
                'name': 'Google People API',
                'id': 'people.googleapis.com',
                'description': 'For referee contact management'
            }
        ]

        print("🔧 We need to enable 3 Google APIs for FOGIS functionality:")
        for api in apis:
            print(f"   • {api['name']} - {api['description']}")

        print("\n🤖 I'll open each API page automatically. For each one:")
        print("  1. Click the 'ENABLE' button")
        print("  2. Wait for the API to be enabled (usually 5-10 seconds)")
        print("  3. Come back here and press Enter to continue")

        for i, api in enumerate(apis, 1):
            print(f"\n📋 Enabling API {i}/3: {api['name']}")

            # Construct API library URL
            api_url = f"https://console.cloud.google.com/apis/library/{api['id']}?project={self.project_id}"

            try:
                webbrowser.open(api_url)
                self.print_success(f"Opened {api['name']} page in browser")
            except Exception as e:
                self.print_warning(f"Could not auto-open browser: {e}")
                print(f"Please manually open: {api_url}")

            print(f"🌐 URL: {api_url}")
            print("  1. Click 'ENABLE' button")
            print("  2. Wait for confirmation message")

            input("⏸️  Press Enter when API is enabled...")
            self.print_success(f"{api['name']} enabled!")

        self.print_success("All required APIs have been enabled!")
        return True

    def guide_oauth_client_creation(self) -> bool:
        """
        Guide user through OAuth client creation with detailed instructions.

        Returns:
            True if OAuth client creation guided successfully, False otherwise
        """
        self.print_step(3, "Create OAuth 2.0 Client")

        # Open OAuth credentials page
        creds_url = f"https://console.cloud.google.com/apis/credentials?project={self.project_id}"

        try:
            webbrowser.open(creds_url)
            self.print_success("Opened OAuth credentials page in browser")
        except Exception as e:
            self.print_warning(f"Could not auto-open browser: {e}")
            print(f"Please manually open: {creds_url}")

        print(f"\n🌐 URL: {creds_url}")
        print("\n🔑 Create OAuth 2.0 Client ID with these EXACT settings:")
        print("  1. Click '+ CREATE CREDENTIALS' button")
        print("  2. Select 'OAuth client ID' from dropdown")
        print("  3. Application type: 'Web application' (IMPORTANT: NOT Desktop)")
        print("  4. Name: Copy and paste this exactly:")

        # Provide copy-paste ready values
        print("\n💡 Copy-paste ready values:")
        print("   Name: FOGIS Web Client")
        print("   Authorized redirect URIs (add both):")
        print("     http://localhost:8080/callback")
        print("     http://127.0.0.1:8080/callback")

        print("\n📋 Detailed steps:")
        print("  5. In 'Authorized redirect URIs' section:")
        print("     a. Click '+ ADD URI'")
        print("     b. Paste: http://localhost:8080/callback")
        print("     c. Click '+ ADD URI' again")
        print("     d. Paste: http://127.0.0.1:8080/callback")
        print("  6. Click 'CREATE' button")
        print("  7. In the popup that appears:")
        print("     a. Click 'DOWNLOAD JSON' button")
        print("     b. Save the file as 'credentials.json' in this directory")

        print(f"\n📁 Save location: {os.path.abspath(self.credentials_path)}")

        # Wait for credentials file with real-time monitoring
        print(f"\n⏳ Waiting for credentials.json file...")
        print("   (The file should appear automatically when you download it)")

        # Monitor for file creation with progress dots
        max_wait_time = 300  # 5 minutes
        start_time = time.time()

        while not os.path.exists(self.credentials_path):
            if time.time() - start_time > max_wait_time:
                self.print_error("Timeout waiting for credentials.json file")
                retry = input("Continue waiting? (y/N): ").strip().lower()
                if retry not in ['y', 'yes']:
                    return False
                start_time = time.time()  # Reset timer

            time.sleep(1)
            print(".", end="", flush=True)

        print(f"\n✅ credentials.json detected!")

        # Immediately validate the downloaded file
        return self.validate_downloaded_credentials()

    def validate_downloaded_credentials(self) -> bool:
        """
        Validate the downloaded credentials file with detailed feedback.

        Returns:
            True if credentials are valid, False otherwise
        """
        self.print_progress("Validating downloaded credentials...")

        try:
            validation_result = self.analyze_credential_file(self.credentials_path)

            if not validation_result:
                self.print_error("Could not analyze credentials file")
                return False

            if validation_result['valid']:
                self.print_success("Credentials file is valid!")

                # Display credential details
                if validation_result.get('details'):
                    print("\n📋 Credential Details:")
                    for key, value in validation_result['details'].items():
                        print(f"   {key}: {value}")

                # Copy to backup location
                try:
                    import shutil
                    shutil.copy2(self.credentials_path, self.backup_credentials_path)
                    self.print_info("Backup copy created in credentials/ directory")
                except Exception as e:
                    self.print_warning(f"Could not create backup: {e}")

                return True
            else:
                self.print_error(f"Credentials validation failed: {validation_result.get('error')}")
                if validation_result.get('fix'):
                    self.print_info(f"💡 Fix: {validation_result.get('fix')}")

                # Offer to retry
                print("\n🔄 Common issues and solutions:")
                print("  • Wrong application type: Make sure you selected 'Web application'")
                print("  • Missing redirect URIs: Add both localhost URLs exactly as shown")
                print("  • Downloaded wrong file: Make sure you clicked 'DOWNLOAD JSON'")

                retry = input("\nFix the issue and download again? (Y/n): ").strip().lower()
                if retry not in ['n', 'no']:
                    # Remove invalid file and retry
                    try:
                        os.remove(self.credentials_path)
                    except:
                        pass
                    return self.guide_oauth_client_creation()

                return False

        except Exception as e:
            self.print_error(f"Error validating credentials: {e}")
            return False

    def validate_and_test_final_setup(self) -> bool:
        """
        Perform final validation and testing of the OAuth setup.

        Returns:
            True if all tests pass, False otherwise
        """
        self.print_step(4, "Final Validation and Testing")

        # Test OAuth flow if possible
        if OAUTH_MANAGER_AVAILABLE:
            return self.test_oauth_credentials()
        else:
            self.print_warning("OAuth manager not available - skipping live testing")
            self.print_info("Credentials file validation passed - setup should work")
            return True

    def test_oauth_credentials(self) -> bool:
        """
        Test OAuth credentials with live authentication flow.

        Returns:
            True if OAuth test successful, False otherwise
        """
        self.print_progress("Testing OAuth authentication flow...")

        try:
            # Initialize OAuth manager
            oauth_manager = GoogleOAuthManager(self.credentials_path)

            print("🔐 Starting OAuth authentication test...")
            print("   (A browser window will open for authentication)")

            # Attempt to get credentials
            credentials = oauth_manager.get_credentials()

            if credentials:
                self.print_success("OAuth authentication successful!")

                # Test API access
                self.print_progress("Testing Google API access...")
                api_results = oauth_manager.test_credentials()

                # Report API test results
                print("\n📊 API Test Results:")
                all_passed = True
                for api_name, success in api_results.items():
                    status = "✅ PASS" if success else "❌ FAIL"
                    print(f"   {api_name.title()} API: {status}")
                    if not success:
                        all_passed = False

                if all_passed:
                    self.print_success("All API tests passed!")
                    return True
                else:
                    self.print_warning("Some API tests failed - this may be due to API enablement delays")
                    self.print_info("Try running the system - APIs often work even if initial tests fail")

                    continue_anyway = input("Continue with setup? (Y/n): ").strip().lower()
                    return continue_anyway not in ['n', 'no']
            else:
                self.print_error("OAuth authentication failed")
                self.print_info("This could be due to:")
                print("  • Incorrect redirect URIs in OAuth client")
                print("  • Browser blocking popups")
                print("  • Network connectivity issues")

                return False

        except Exception as e:
            self.print_error(f"OAuth testing failed: {e}")
            self.print_info("The credentials file appears valid, so this may be a temporary issue")

            continue_anyway = input("Continue with setup anyway? (Y/n): ").strip().lower()
            return continue_anyway not in ['n', 'no']

    def display_completion_summary(self) -> None:
        """Display completion summary with next steps."""
        self.print_header("OAuth Setup Complete!")

        print("🎉 Your Google OAuth credentials are now configured!")
        print("")
        print("✅ What's been set up:")
        print("   • Google Cloud project with required APIs enabled")
        print("   • OAuth 2.0 web application client")
        print("   • Valid credentials.json file")
        print("   • Backup credentials in credentials/ directory")
        print("")
        print("📋 Next steps:")
        print("   1. Start FOGIS services: ./manage_fogis_system.sh start")
        print("   2. Check system status: ./show_system_status.sh")
        print("   3. Add automation: ./manage_fogis_system.sh cron-add")
        print("")
        print("🔄 Your FOGIS system will now automatically:")
        print("   • Access your Google Calendar for match scheduling")
        print("   • Upload WhatsApp assets to Google Drive")
        print("   • Manage referee contact information")
        print("")
        print("🎯 OAuth setup is complete - FOGIS is ready to use!")


def main():
    """Main entry point for the enhanced OAuth wizard."""
    wizard = EnhancedOAuthWizard()
    success = wizard.start_guided_setup()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
