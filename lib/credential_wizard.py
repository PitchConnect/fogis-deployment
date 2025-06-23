#!/usr/bin/env python3
"""
FOGIS Credential Management Wizard

Interactive wizard that guides users through setting up all authentication
credentials with validation, testing, and secure storage.

This module implements the main wizard interface and orchestrates the
credential setup process for Google OAuth, FOGIS authentication, and
calendar configuration.
"""

import os
import sys
import time
from typing import Dict, Any, Optional

# Add the parent directory to the path to import other modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from lib.google_oauth_manager import GoogleOAuthManager
    from lib.calendar_manager import CalendarManager
    from lib.fogis_auth_manager import FogisAuthManager
    from lib.credential_validator import CredentialValidator

    # Try to import secure storage, fallback to simple storage if needed
    try:
        from lib.secure_storage import SecureCredentialStore
    except Exception:
        from lib.simple_storage import SimpleCredentialStore as SecureCredentialStore

except ImportError as e:
    print(f"❌ Error importing credential wizard modules: {e}")
    print("📦 Please ensure all required dependencies are installed:")
    print("   pip3 install -r requirements.txt")
    sys.exit(1)


class CredentialWizard:
    """
    Main credential setup wizard that orchestrates the entire authentication
    setup process for the FOGIS system.
    """

    def __init__(self):
        """Initialize the credential wizard."""
        self.config = {}
        self.oauth_manager = None
        self.calendar_manager = None
        self.fogis_manager = None
        self.storage = None
        self.validator = None

    def print_header(self, title: str) -> None:
        """Print a formatted header."""
        print("\n" + "=" * 50)
        print(f"🔐 {title}")
        print("=" * 50)

    def print_step(self, step: int, title: str) -> None:
        """Print a formatted step header."""
        print(f"\n📋 Step {step}: {title}")
        print("-" * 30)

    def print_success(self, message: str) -> None:
        """Print a success message."""
        print(f"✅ {message}")

    def print_warning(self, message: str) -> None:
        """Print a warning message."""
        print(f"⚠️  {message}")

    def print_error(self, message: str) -> None:
        """Print an error message."""
        print(f"❌ {message}")

    def print_info(self, message: str) -> None:
        """Print an info message."""
        print(f"ℹ️  {message}")

    def welcome_screen(self) -> bool:
        """Display welcome screen and get user confirmation."""
        self.print_header("FOGIS Credential Setup Wizard")
        
        print("\n🎯 This wizard will help you set up:")
        print("   • Google OAuth credentials (Calendar, Drive, Contacts)")
        print("   • Dedicated FOGIS calendar (isolated from personal calendars)")
        print("   • FOGIS authentication with validation")
        print("   • Secure credential storage with encryption")
        
        print("\n⏱️  Estimated time: 5-10 minutes")
        print("📋 You'll need:")
        print("   • Google Cloud Console access")
        print("   • FOGIS username and password")
        print("   • Your referee number")
        
        print("\n🔒 Privacy & Security:")
        print("   • Creates dedicated calendar (no personal data access)")
        print("   • Credentials are encrypted and stored securely")
        print("   • Only necessary permissions are requested")
        
        while True:
            choice = input("\n🚀 Ready to start? (y/n): ").strip().lower()
            if choice in ['y', 'yes']:
                return True
            elif choice in ['n', 'no']:
                print("\n👋 Setup cancelled. Run './manage_fogis_system.sh setup-auth' when ready.")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")

    def setup_google_oauth(self) -> bool:
        """Set up Google OAuth credentials."""
        self.print_step(1, "Google OAuth Setup")
        
        print("🔗 Setting up Google OAuth credentials...")
        print("\nWe need to configure Google OAuth to access:")
        print("   • Google Calendar (for match scheduling)")
        print("   • Google Drive (for WhatsApp asset uploads)")
        print("   • Google Contacts (for referee phonebook)")
        
        # Check if credentials.json exists
        if not os.path.exists('credentials.json'):
            print("\n📋 Google Cloud Console Setup Required:")
            print("1. Go to https://console.cloud.google.com/")
            print("2. Create a new project or select existing one")
            print("3. Enable APIs: Calendar, Drive, Contacts")
            print("4. Create OAuth 2.0 credentials (Desktop application)")
            print("5. Download credentials as 'credentials.json'")
            print("6. Place the file in this directory")
            
            input("\n⏸️  Press Enter when credentials.json is ready...")
            
            if not os.path.exists('credentials.json'):
                self.print_error("credentials.json not found. Please follow the setup instructions.")
                return False
        
        self.print_success("Google credentials file found")
        
        # Initialize OAuth manager and validate credentials
        try:
            self.oauth_manager = GoogleOAuthManager(credentials_file='credentials.json')

            self.print_info("Validating Google credentials...")
            if not self.oauth_manager.validate_credentials_file():
                self.print_error("Invalid credentials file format")
                return False

            self.print_info("Testing OAuth authentication...")
            credentials = self.oauth_manager.get_credentials()
            if not credentials:
                self.print_error("OAuth authentication failed")
                return False

            # Test API access
            api_results = self.oauth_manager.test_credentials()
            failed_apis = [api for api, success in api_results.items() if not success]

            if failed_apis:
                self.print_warning(f"Some APIs failed: {', '.join(failed_apis)}")
                retry = input("Continue anyway? (y/N): ").strip().lower()
                if retry not in ['y', 'yes']:
                    return False

            self.print_success("Google OAuth setup completed")
            return True
        except Exception as e:
            self.print_error(f"Google OAuth setup failed: {e}")
            return False

    def setup_calendar_integration(self) -> bool:
        """Set up Google Calendar integration with dedicated calendar."""
        self.print_step(2, "Calendar Configuration")
        
        print("📅 Setting up Google Calendar integration...")
        print("\nFor privacy and organization, we'll create a dedicated FOGIS calendar.")
        print("This ensures match events don't mix with your personal calendar.")
        
        print("\nOptions:")
        print("1. Create a new dedicated FOGIS calendar (Recommended)")
        print("2. Use an existing calendar")
        print("3. Skip calendar integration for now")
        
        while True:
            choice = input("\nChoose option (1-3): ").strip()
            
            if choice == "1":
                return self._create_new_calendar()
            elif choice == "2":
                return self._use_existing_calendar()
            elif choice == "3":
                self.print_warning("Skipping calendar integration")
                return True
            else:
                print("Please enter 1, 2, or 3.")

    def _create_new_calendar(self) -> bool:
        """Create a new dedicated FOGIS calendar."""
        calendar_name = f"FOGIS Matches - {time.strftime('%Y')}"

        print(f"\n📅 Creating calendar: {calendar_name}")
        print("🌍 Time Zone: Europe/Stockholm")
        print("📝 Description: Automated FOGIS match scheduling")

        try:
            if not self.oauth_manager or not self.oauth_manager.credentials:
                self.print_error("Google OAuth not configured")
                return False

            # Initialize calendar manager
            self.calendar_manager = CalendarManager(self.oauth_manager.credentials)

            # Create the calendar
            calendar_id = self.calendar_manager.create_fogis_calendar(
                calendar_name,
                "Automated FOGIS match scheduling - Created by credential wizard"
            )

            if not calendar_id:
                self.print_error("Failed to create calendar")
                return False

            self.print_success(f"Calendar created successfully!")
            self.print_info(f"Calendar ID: {calendar_id}")

            # Validate calendar access
            validation = self.calendar_manager.validate_calendar_access(calendar_id)
            if not validation['valid']:
                self.print_error(f"Calendar validation failed: {validation.get('error', 'Unknown error')}")
                return False

            # Ask about sharing
            share = input("\n👥 Share calendar with team members? (y/N): ").strip().lower()
            if share in ['y', 'yes']:
                email = input("Enter team member email: ").strip()
                if email and '@' in email:
                    if self.calendar_manager.share_calendar(calendar_id, email, 'writer'):
                        self.print_success(f"Calendar shared with {email}")
                    else:
                        self.print_warning(f"Failed to share calendar with {email}")

            self.config['calendar_id'] = calendar_id
            self.config['calendar_name'] = calendar_name
            return True

        except Exception as e:
            self.print_error(f"Failed to create calendar: {e}")
            return False

    def _use_existing_calendar(self) -> bool:
        """Use an existing calendar."""
        try:
            if not self.oauth_manager or not self.oauth_manager.credentials:
                self.print_error("Google OAuth not configured")
                return False

            # Initialize calendar manager if not already done
            if not self.calendar_manager:
                self.calendar_manager = CalendarManager(self.oauth_manager.credentials)

            print("\n📋 Available calendars:")
            calendars = self.calendar_manager.list_calendars()

            if not calendars:
                self.print_error("No calendars found")
                return False

            # Display calendars with numbers
            for i, calendar in enumerate(calendars[:10], 1):  # Limit to first 10
                access_info = f"({calendar['access_role']})" if calendar['access_role'] != 'owner' else ""
                primary_info = " (Primary)" if calendar.get('primary') else ""
                print(f"  {i}. {calendar['summary']}{primary_info} {access_info}")

            print(f"  {len(calendars[:10]) + 1}. Enter custom calendar ID")

            while True:
                choice = input(f"\nSelect calendar (1-{len(calendars[:10]) + 1}): ").strip()

                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(calendars[:10]):
                        # Selected from list
                        selected_calendar = calendars[choice_num - 1]
                        calendar_id = selected_calendar['id']
                        break
                    elif choice_num == len(calendars[:10]) + 1:
                        # Custom calendar ID
                        calendar_id = input("Enter calendar ID: ").strip()
                        if calendar_id:
                            break
                        else:
                            print("Please enter a valid calendar ID")
                    else:
                        print(f"Please enter a number between 1 and {len(calendars[:10]) + 1}")
                except ValueError:
                    print("Please enter a valid number")

            # Validate calendar access
            self.print_info("Validating calendar access...")
            validation = self.calendar_manager.validate_calendar_access(calendar_id)

            if validation['valid']:
                self.config['calendar_id'] = calendar_id
                self.config['calendar_name'] = validation['calendar_info'].get('summary', 'Selected Calendar')
                self.print_success("Calendar access confirmed")
                return True
            else:
                self.print_error(f"Calendar validation failed: {validation.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            self.print_error(f"Error selecting calendar: {e}")
            return False

    def setup_fogis_auth(self) -> bool:
        """Set up FOGIS authentication."""
        self.print_step(3, "FOGIS Authentication")
        
        print("🔑 Setting up FOGIS authentication...")
        print("Enter your FOGIS login credentials:")
        
        username = input("\nFOGIS Username: ").strip()
        if not username:
            self.print_error("Username is required")
            return False
        
        import getpass
        password = getpass.getpass("FOGIS Password: ")
        if not password:
            self.print_error("Password is required")
            return False
        
        referee_number = input("Referee Number (from FOGIS profile): ").strip()
        if not referee_number:
            self.print_error("Referee number is required")
            return False
        
        # Test FOGIS login
        self.print_info("Testing FOGIS authentication...")

        try:
            # Initialize FOGIS auth manager
            self.fogis_manager = FogisAuthManager()

            # Test connection first
            if not self.fogis_manager.test_connection():
                self.print_error("Cannot connect to FOGIS website. Please check your internet connection.")
                return False

            # Test authentication
            auth_result = self.fogis_manager.authenticate(username, password)

            if auth_result['success']:
                self.print_success("FOGIS authentication successful")

                # Extract referee information
                referee_info = auth_result.get('referee_info', {})
                detected_referee_number = referee_info.get('referee_number')

                if detected_referee_number:
                    self.print_info(f"Auto-detected referee ID: {detected_referee_number}")
                    if detected_referee_number != referee_number:
                        self.print_warning(f"Entered referee number ({referee_number}) differs from detected ({detected_referee_number})")
                        use_detected = input("Use auto-detected referee number? (Y/n): ").strip().lower()
                        if use_detected not in ['n', 'no']:
                            referee_number = detected_referee_number
                else:
                    self.print_info(f"Using provided referee ID: {referee_number}")

                # Display additional referee info if available
                if referee_info.get('name'):
                    self.print_info(f"Referee name: {referee_info['name']}")

                self.config['fogis_username'] = username
                self.config['fogis_password'] = password
                self.config['referee_number'] = referee_number
                self.config['referee_info'] = referee_info
                return True
            else:
                error_msg = auth_result.get('error', 'Authentication failed')
                self.print_error(f"FOGIS authentication failed: {error_msg}")

                # Offer retry
                retry = input("Retry with different credentials? (y/N): ").strip().lower()
                if retry in ['y', 'yes']:
                    return self.setup_fogis_auth()
                return False

        except Exception as e:
            self.print_error(f"FOGIS authentication failed: {e}")
            return False

    def validate_and_test(self) -> bool:
        """Validate all configurations and test integrations."""
        self.print_step(4, "Validation & Testing")
        
        print("🔍 Testing all integrations...")
        
        tests = [
            ("Google OAuth", self._test_google_oauth),
            ("Calendar Access", self._test_calendar_access),
            ("FOGIS Authentication", self._test_fogis_auth),
            ("Credential Storage", self._test_credential_storage),
        ]
        
        all_passed = True
        for test_name, test_func in tests:
            print(f"\n🧪 Testing {test_name}...")
            try:
                if test_func():
                    self.print_success(f"{test_name} - PASSED")
                else:
                    self.print_error(f"{test_name} - FAILED")
                    all_passed = False
            except Exception as e:
                self.print_error(f"{test_name} - ERROR: {e}")
                all_passed = False
        
        return all_passed

    def _test_google_oauth(self) -> bool:
        """Test Google OAuth functionality."""
        try:
            if not self.oauth_manager or not self.oauth_manager.credentials:
                return False

            # Test API access
            api_results = self.oauth_manager.test_credentials()
            required_apis = ['calendar', 'drive', 'contacts']

            for api in required_apis:
                if not api_results.get(api, False):
                    self.print_error(f"Google {api.title()} API test failed")
                    return False

            return True
        except Exception:
            return False

    def _test_calendar_access(self) -> bool:
        """Test calendar access and permissions."""
        try:
            if not self.calendar_manager or 'calendar_id' not in self.config:
                return False

            # Validate calendar access
            validation = self.calendar_manager.validate_calendar_access(self.config['calendar_id'])
            return validation.get('valid', False)
        except Exception:
            return False

    def _test_fogis_auth(self) -> bool:
        """Test FOGIS authentication."""
        try:
            if not self.fogis_manager:
                return False

            # Test session validity
            return self.fogis_manager.validate_session()
        except Exception:
            return False

    def _test_credential_storage(self) -> bool:
        """Test credential storage and encryption."""
        try:
            # Initialize storage if not already done
            if not self.storage:
                self.storage = SecureCredentialStore()

            # Test storage functionality with dummy data
            test_data = {'test': 'data', 'timestamp': time.time()}

            # Test store and retrieve
            if not self.storage.store_credentials('test_service', test_data):
                return False

            retrieved = self.storage.retrieve_credentials('test_service')
            if retrieved != test_data:
                return False

            # Clean up test data
            self.storage.delete_credentials('test_service')
            return True
        except Exception:
            return False

    def save_configuration(self) -> bool:
        """Save all configuration securely."""
        self.print_step(5, "Saving Configuration")

        print("💾 Saving credentials securely...")

        try:
            # Initialize storage if not already done
            if not self.storage:
                self.storage = SecureCredentialStore()

            # Save Google OAuth credentials
            if self.oauth_manager and self.oauth_manager.credentials:
                oauth_data = {
                    'token_info': self.oauth_manager.get_token_info(),
                    'credentials_file': 'credentials.json'
                }
                self.storage.store_credentials('google_oauth', oauth_data)
                self.print_info("Google OAuth credentials saved")

            # Save calendar configuration
            if 'calendar_id' in self.config:
                calendar_data = {
                    'calendar_id': self.config['calendar_id'],
                    'calendar_name': self.config.get('calendar_name', ''),
                    'configured_at': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                self.storage.store_credentials('calendar_config', calendar_data)
                self.print_info("Calendar configuration saved")

            # Save FOGIS credentials
            if 'fogis_username' in self.config:
                fogis_data = {
                    'username': self.config['fogis_username'],
                    'password': self.config['fogis_password'],
                    'referee_number': self.config['referee_number'],
                    'referee_info': self.config.get('referee_info', {})
                }
                self.storage.store_credentials('fogis_auth', fogis_data)
                self.print_info("FOGIS credentials saved")

            # Update .env file for Docker services
            self._update_env_file()

            # Copy credentials to service directories
            self._setup_service_credentials()

            self.print_success("All credentials saved and encrypted")
            self.print_success("Configuration files updated")
            return True

        except Exception as e:
            self.print_error(f"Failed to save configuration: {e}")
            return False

    def completion_summary(self) -> None:
        """Display completion summary and next steps."""
        self.print_header("Setup Complete!")
        
        print("🎉 Your FOGIS system is now configured!")
        
        print("\n✅ Configured Services:")
        if 'calendar_id' in self.config:
            print(f"   📅 Google Calendar: {self.config.get('calendar_name', 'Configured')}")
        print("   ☁️  Google Drive: Ready for uploads")
        print("   📞 Google Contacts: Referee phonebook sync")
        print("   🔑 FOGIS Authentication: Validated")
        
        print("\n📋 Next Steps:")
        print("1. Start the system: ./manage_fogis_system.sh start")
        print("2. Check system status: ./show_system_status.sh")
        print("3. Add automation: ./manage_fogis_system.sh cron-add")
        
        print("\n🔄 Your FOGIS system will now automatically:")
        print("   • Check for new matches every hour")
        print("   • Create WhatsApp group assets")
        print("   • Sync matches to your dedicated calendar")
        print("   • Upload assets to Google Drive")
        
        print("\n🎯 Your FOGIS system is ready to use!")

    def _update_env_file(self) -> None:
        """Update .env file with new configuration."""
        try:
            env_content = []

            # Read existing .env file if it exists
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    env_content = f.readlines()

            # Update or add FOGIS credentials
            if 'fogis_username' in self.config:
                self._update_env_var(env_content, 'FOGIS_USERNAME', self.config['fogis_username'])
                self._update_env_var(env_content, 'FOGIS_PASSWORD', self.config['fogis_password'])
                self._update_env_var(env_content, 'USER_REFEREE_NUMBER', self.config['referee_number'])

            # Update calendar configuration
            if 'calendar_id' in self.config:
                self._update_env_var(env_content, 'GOOGLE_CALENDAR_ID', self.config['calendar_id'])

            # Write updated .env file
            with open('.env', 'w') as f:
                f.writelines(env_content)

            # Set secure permissions
            os.chmod('.env', 0o600)

        except Exception as e:
            self.print_warning(f"Could not update .env file: {e}")

    def _update_env_var(self, env_content: list, var_name: str, var_value: str) -> None:
        """Update or add an environment variable in the content list."""
        var_line = f"{var_name}={var_value}\n"

        # Find existing variable
        for i, line in enumerate(env_content):
            if line.startswith(f"{var_name}="):
                env_content[i] = var_line
                return

        # Add new variable
        env_content.append(var_line)

    def _setup_service_credentials(self) -> None:
        """Set up credentials for Docker services."""
        try:
            # Create data directories
            os.makedirs('data/fogis-calendar-phonebook-sync', exist_ok=True)
            os.makedirs('data/google-drive-service', exist_ok=True)

            # Copy token.json to service directories if it exists
            if os.path.exists('token.json'):
                import shutil

                # Copy to calendar service
                shutil.copy('token.json', 'data/fogis-calendar-phonebook-sync/token.json')

                # Copy to drive service (different filename)
                shutil.copy('token.json', 'data/google-drive-service/google-drive-token.json')

                self.print_info("Service credentials configured")

        except Exception as e:
            self.print_warning(f"Could not set up service credentials: {e}")

    def run(self) -> int:
        """Run the complete credential setup wizard."""
        try:
            # Welcome and confirmation
            if not self.welcome_screen():
                return 0
            
            # Step-by-step setup
            if not self.setup_google_oauth():
                return 1
            
            if not self.setup_calendar_integration():
                return 1
            
            if not self.setup_fogis_auth():
                return 1
            
            if not self.validate_and_test():
                self.print_warning("Some tests failed. Please check the configuration.")
                retry = input("\nRetry failed tests? (y/N): ").strip().lower()
                if retry in ['y', 'yes']:
                    if not self.validate_and_test():
                        return 1
                else:
                    return 1
            
            if not self.save_configuration():
                return 1
            
            # Success summary
            self.completion_summary()
            return 0
            
        except KeyboardInterrupt:
            print("\n\n⏹️  Setup cancelled by user.")
            return 1
        except Exception as e:
            self.print_error(f"Unexpected error: {e}")
            return 1


def main():
    """Main entry point for the credential wizard."""
    wizard = CredentialWizard()
    return wizard.run()


if __name__ == "__main__":
    sys.exit(main())
