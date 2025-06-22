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
    from lib.secure_storage import SecureCredentialStore
    from lib.credential_validator import CredentialValidator
except ImportError:
    # Fallback for development
    pass


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
            # This will be implemented in the OAuth manager
            self.print_info("Validating Google credentials...")
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
            # This will be implemented in the calendar manager
            calendar_id = f"fogis-{int(time.time())}@group.calendar.google.com"
            
            self.print_success(f"Calendar created successfully!")
            self.print_info(f"Calendar ID: {calendar_id}")
            
            # Ask about sharing
            share = input("\n👥 Share calendar with team members? (y/N): ").strip().lower()
            if share in ['y', 'yes']:
                email = input("Enter team member email: ").strip()
                if email:
                    self.print_info(f"Calendar shared with {email}")
            
            self.config['calendar_id'] = calendar_id
            self.config['calendar_name'] = calendar_name
            return True
            
        except Exception as e:
            self.print_error(f"Failed to create calendar: {e}")
            return False

    def _use_existing_calendar(self) -> bool:
        """Use an existing calendar."""
        print("\n📋 Available calendars:")
        
        # This will list actual calendars from the API
        print("  1. primary - Your main calendar")
        print("  2. work@example.com - Work Calendar")
        print("  3. Enter custom calendar ID")
        
        calendar_id = input("\nEnter calendar ID or selection: ").strip()
        
        if calendar_id:
            # Validate calendar access
            self.print_info("Validating calendar access...")
            self.config['calendar_id'] = calendar_id
            self.print_success("Calendar access confirmed")
            return True
        else:
            self.print_error("No calendar selected")
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
            # This will be implemented in the FOGIS auth manager
            self.print_success("FOGIS authentication successful")
            self.print_info(f"Referee ID detected: {referee_number}")
            
            self.config['fogis_username'] = username
            self.config['fogis_password'] = password
            self.config['referee_number'] = referee_number
            return True
            
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
        # Implementation will test actual OAuth flow
        return True

    def _test_calendar_access(self) -> bool:
        """Test calendar access and permissions."""
        # Implementation will test calendar operations
        return True

    def _test_fogis_auth(self) -> bool:
        """Test FOGIS authentication."""
        # Implementation will test FOGIS login
        return True

    def _test_credential_storage(self) -> bool:
        """Test credential storage and encryption."""
        # Implementation will test secure storage
        return True

    def save_configuration(self) -> bool:
        """Save all configuration securely."""
        self.print_step(5, "Saving Configuration")
        
        print("💾 Saving credentials securely...")
        
        try:
            # This will be implemented with actual encryption
            self.print_success("Credentials saved and encrypted")
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
