#!/usr/bin/env python3
"""
Interactive Setup Wizard for FOGIS Deployment
Guides new users through complete FOGIS configuration setup

This module provides an intelligent, user-friendly wizard that guides users
through the complete setup process with smart defaults and validation.
"""

import logging
import os
import re
from datetime import datetime

import yaml

# Import our configuration components
from config_generator import ConfigGenerator
from config_manager import ConfigManager
from config_validator import ConfigValidator
from oauth_wizard import OAuthWizard

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SetupWizardError(Exception):
    """Exception raised for setup wizard errors"""


class InteractiveSetup:
    """
    Interactive setup wizard for FOGIS deployment

    Provides guided setup with:
    - Intelligent defaults
    - Input validation
    - Progress tracking
    - Configuration generation
    """

    def __init__(self):
        """Initialize interactive setup wizard"""
        self.config = {}
        self.setup_progress = {
            "fogis_credentials": False,
            "google_oauth": False,
            "service_ports": False,
            "system_settings": False,
            "validation": False,
        }

    def run_setup_wizard(self) -> bool:
        """
        Run the complete interactive setup wizard

        Returns:
            True if setup completed successfully
        """
        print("🚀 FOGIS Interactive Setup Wizard")
        print("=" * 40)
        print(
            "This wizard will guide you through setting up FOGIS with "
            "portable configuration."
        )
        print("You can press Ctrl+C at any time to exit.\n")

        try:
            # Check for existing configuration
            if self.check_existing_configuration():
                if not self.confirm_overwrite():
                    print(
                        "Setup cancelled. Your existing configuration "
                        "remains unchanged."
                    )
                    return False

            # Initialize configuration structure
            self.initialize_config_structure()

            # Step 1: FOGIS Credentials
            print("\n" + "=" * 50)
            print("📋 Step 1: FOGIS Authentication")
            print("=" * 50)
            if not self.setup_fogis_credentials():
                return False

            # Step 2: Google OAuth Configuration
            print("\n" + "=" * 50)
            print("🔐 Step 2: Google OAuth Configuration")
            print("=" * 50)
            if not self.setup_google_oauth():
                return False

            # Step 3: Service Configuration
            print("\n" + "=" * 50)
            print("⚙️  Step 3: Service Configuration")
            print("=" * 50)
            if not self.setup_service_configuration():
                return False

            # Step 4: System Settings
            print("\n" + "=" * 50)
            print("🖥️  Step 4: System Settings")
            print("=" * 50)
            if not self.setup_system_settings():
                return False

            # Step 5: Review and Save
            print("\n" + "=" * 50)
            print("📝 Step 5: Review and Save Configuration")
            print("=" * 50)
            if not self.review_and_save_configuration():
                return False

            # Step 6: Generate Configuration Files
            print("\n" + "=" * 50)
            print("🔧 Step 6: Generate Configuration Files")
            print("=" * 50)
            if not self.generate_configuration_files():
                return False

            print("\n" + "🎉" * 20)
            print("✅ FOGIS setup completed successfully!")
            print("🎉" * 20)
            print("\nNext steps:")
            print("1. Place your Google OAuth credentials in 'credentials.json'")
            print("2. Run: ./manage_fogis_system.sh setup-auth")
            print("3. Start services: ./manage_fogis_system.sh start")

            return True

        except KeyboardInterrupt:
            print("\n\n❌ Setup cancelled by user.")
            return False
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            print(f"\n❌ Setup failed: {e}")
            return False

    def check_existing_configuration(self) -> bool:
        """
        Check if configuration already exists

        Returns:
            True if existing configuration found
        """
        existing_files = []

        if os.path.exists("fogis-config.yaml"):
            existing_files.append("fogis-config.yaml")
        if os.path.exists(".env"):
            existing_files.append(".env")
        if os.path.exists("fogis-calendar-phonebook-sync/config.json"):
            existing_files.append("config.json")

        if existing_files:
            print("⚠️  Existing configuration detected:")
            for file in existing_files:
                print(f"   • {file}")
            return True

        return False

    def confirm_overwrite(self) -> bool:
        """
        Confirm overwriting existing configuration

        Returns:
            True if user confirms overwrite
        """
        print("\nThis will overwrite your existing configuration.")
        return self.ask_yes_no("Do you want to continue?", default=False)

    def initialize_config_structure(self):
        """Initialize configuration with default structure"""
        config_manager = ConfigManager()
        self.config = config_manager.get_default_config()

        # Update metadata
        self.config["metadata"]["created"] = datetime.now().isoformat()
        self.config["metadata"][
            "description"
        ] = "FOGIS Configuration (Created by Interactive Setup)"

    def setup_fogis_credentials(self) -> bool:
        """
        Setup FOGIS authentication credentials

        Returns:
            True if setup completed successfully
        """
        print("Enter your FOGIS login credentials.")
        print("These are the same credentials you use to log into the FOGIS website.\n")

        # FOGIS Username
        while True:
            username = input("FOGIS Username: ").strip()
            if username:
                self.config["fogis"]["username"] = username
                break
            print("❌ Username cannot be empty. Please try again.")

        # FOGIS Password
        while True:
            password = input("FOGIS Password: ").strip()
            if password:
                self.config["fogis"]["password"] = password
                break
            print("❌ Password cannot be empty. Please try again.")

        # Referee Number
        while True:
            try:
                referee_input = input("Your Referee Number: ").strip()
                referee_number = int(referee_input)
                if referee_number > 0:
                    self.config["fogis"]["referee_number"] = referee_number
                    break
                else:
                    print(
                        "❌ Referee number must be a positive integer. Please try again."
                    )
            except ValueError:
                print("❌ Please enter a valid number.")

        print("✅ FOGIS credentials configured successfully!")
        self.setup_progress["fogis_credentials"] = True
        return True

    def setup_google_oauth(self) -> bool:
        """
        Setup Google OAuth configuration with enhanced wizard

        Returns:
            True if setup completed successfully
        """
        print("Configure Google OAuth settings for calendar and drive integration.")
        print("You can use the comprehensive OAuth wizard or configure manually.\n")

        # Offer OAuth wizard
        print("OAuth Setup Options:")
        print("1. Use OAuth Wizard (Recommended)")
        print("   ✅ Step-by-step Google Cloud Project setup")
        print("   ✅ Automatic credential validation")
        print("   ✅ Real-time connectivity testing")
        print("")
        print("2. Manual Configuration")
        print("   ⚠️  Requires existing OAuth credentials")
        print("   ⚠️  Manual validation required")
        print("")

        while True:
            choice = input("Choose setup method (1/2) [1]: ").strip() or "1"
            if choice == "1":
                return self.run_oauth_wizard_integration()
            elif choice == "2":
                return self.setup_manual_oauth()
            else:
                print("❌ Please enter 1 or 2.")

    def run_oauth_wizard_integration(self) -> bool:
        """
        Run the OAuth wizard and integrate results

        Returns:
            True if OAuth wizard completed successfully
        """
        print("\n🔐 Starting OAuth Authentication Wizard...")
        print("This will guide you through the complete OAuth setup process.\n")

        try:
            oauth_wizard = OAuthWizard()

            if oauth_wizard.run_oauth_wizard():
                # Get OAuth configuration from wizard
                oauth_status = oauth_wizard.get_oauth_status()

                # Update configuration with OAuth results
                if oauth_status["client_type"]:
                    self.config["google"]["oauth"]["client_type"] = oauth_status[
                        "client_type"
                    ]

                # Set calendar ID
                calendar_id = (
                    input("\nGoogle Calendar ID [primary]: ").strip() or "primary"
                )
                self.config["google"]["calendar"]["calendar_id"] = calendar_id

                # Validate calendar ID format if not 'primary'
                if calendar_id != "primary":
                    email_pattern = re.compile(
                        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                    )
                    if not email_pattern.match(calendar_id):
                        print(
                            "⚠️  Calendar ID format may be invalid. Please verify it's correct."
                        )

                # Google Drive folder
                drive_folder = input(
                    "Google Drive folder for WhatsApp assets [WhatsApp_Group_Assets]: "
                ).strip()
                if drive_folder:
                    self.config["google"]["drive"]["folder_base"] = drive_folder

                print("✅ OAuth wizard completed successfully!")
                self.setup_progress["google_oauth"] = True
                return True
            else:
                print("❌ OAuth wizard failed. Falling back to manual configuration...")
                return self.setup_manual_oauth()

        except Exception as e:
            print(f"❌ OAuth wizard error: {e}")
            print("Falling back to manual configuration...")
            return self.setup_manual_oauth()

    def setup_manual_oauth(self) -> bool:
        """
        Setup OAuth configuration manually

        Returns:
            True if manual setup completed successfully
        """
        print("\n📋 Manual OAuth Configuration:")
        print(
            "You'll need to have already created OAuth credentials in Google Cloud Console."
        )
        print("See docs/OAUTH_SETUP_CHECKLIST.md for detailed instructions.\n")

        # Check for existing credentials
        if not os.path.exists("credentials.json"):
            print("⚠️  OAuth credentials file (credentials.json) not found.")
            print("Please download your OAuth credentials from Google Cloud Console")
            print("and save them as 'credentials.json' in this directory.")

            if not self.ask_yes_no("Do you have the credentials.json file ready?"):
                print("❌ OAuth credentials are required to continue.")
                return False

        # OAuth Client Type
        print("OAuth Client Type:")
        print("1. Web Application (Recommended)")
        print("2. Desktop Application")

        while True:
            choice = input("Choose client type (1/2) [1]: ").strip() or "1"
            if choice == "1":
                self.config["google"]["oauth"]["client_type"] = "web_application"
                break
            elif choice == "2":
                self.config["google"]["oauth"]["client_type"] = "desktop_application"
                break
            else:
                print("❌ Please enter 1 or 2.")

        # Calendar ID
        calendar_id = input("Google Calendar ID [primary]: ").strip() or "primary"
        self.config["google"]["calendar"]["calendar_id"] = calendar_id

        # Validate calendar ID format if not 'primary'
        if calendar_id != "primary":
            email_pattern = re.compile(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            )
            if not email_pattern.match(calendar_id):
                print(
                    "⚠️  Calendar ID format may be invalid. Please verify it's correct."
                )

        # Google Drive folder
        drive_folder = input(
            "Google Drive folder for WhatsApp assets [WhatsApp_Group_Assets]: "
        ).strip()
        if drive_folder:
            self.config["google"]["drive"]["folder_base"] = drive_folder

        print("✅ Manual OAuth configuration completed!")
        self.setup_progress["google_oauth"] = True
        return True

    def setup_service_configuration(self) -> bool:
        """
        Setup service configuration

        Returns:
            True if setup completed successfully
        """
        print("Configure service ports and processing settings.")
        print("Default ports are recommended unless you have conflicts.\n")

        # Ask if user wants to customize ports
        if self.ask_yes_no("Do you want to customize service ports?", default=False):
            self.setup_custom_ports()
        else:
            print("✅ Using default service ports")

        # Processing settings
        print("\nProcessing Settings:")

        # Minimum referees for WhatsApp
        while True:
            try:
                min_refs_input = input(
                    "Minimum referees required for WhatsApp group creation [2]: "
                ).strip()
                if not min_refs_input:
                    min_refs = 2
                else:
                    min_refs = int(min_refs_input)

                if min_refs >= 1:
                    self.config["services"]["processing"][
                        "min_referees_for_whatsapp"
                    ] = min_refs
                    break
                else:
                    print("❌ Must be at least 1 referee.")
            except ValueError:
                print("❌ Please enter a valid number.")

        # Match check schedule
        schedule = input("Match check schedule (cron format) [0 * * * *]: ").strip()
        if schedule:
            # Basic cron validation
            if self.validate_cron_schedule(schedule):
                self.config["services"]["processing"]["match_check_schedule"] = schedule
            else:
                print("⚠️  Invalid cron format. Using default: 0 * * * *")

        # Logging level
        print("\nLogging Level:")
        print("1. INFO (Recommended)")
        print("2. DEBUG (Verbose)")
        print("3. WARNING (Minimal)")

        while True:
            choice = input("Choose logging level (1/2/3) [1]: ").strip() or "1"
            if choice == "1":
                self.config["services"]["logging"]["level"] = "INFO"
                break
            elif choice == "2":
                self.config["services"]["logging"]["level"] = "DEBUG"
                self.config["services"]["logging"]["debug_mode"] = True
                break
            elif choice == "3":
                self.config["services"]["logging"]["level"] = "WARNING"
                break
            else:
                print("❌ Please enter 1, 2, or 3.")

        print("✅ Service configuration completed!")
        self.setup_progress["service_ports"] = True
        return True

    def setup_custom_ports(self):
        """Setup custom service ports"""
        print("\nCustom Port Configuration:")
        print("Press Enter to keep default values.\n")

        port_configs = [
            ("api_client", "FOGIS API Client", 9086),
            ("match_processor", "Match Processor", 9082),
            ("calendar_sync", "Calendar Sync", 9083),
            ("calendar_auth", "Calendar Auth", 9084),
            ("logo_combiner", "Logo Combiner", 9088),
            ("google_drive", "Google Drive", 9085),
            ("change_detector", "Change Detector", 9080),
        ]

        used_ports = set()

        for service_key, service_name, default_port in port_configs:
            while True:
                try:
                    port_input = input(
                        f"{service_name} port [{default_port}]: "
                    ).strip()
                    port = int(port_input) if port_input else default_port

                    if port < 1 or port > 65535:
                        print("❌ Port must be between 1 and 65535.")
                        continue

                    if port in used_ports:
                        print("❌ Port already in use by another service.")
                        continue

                    if port < 1024:
                        if not self.ask_yes_no(
                            f"Port {port} requires root privileges. Continue?"
                        ):
                            continue

                    self.config["services"]["ports"][service_key] = port
                    used_ports.add(port)
                    break

                except ValueError:
                    print("❌ Please enter a valid port number.")

    def setup_system_settings(self) -> bool:
        """
        Setup system settings

        Returns:
            True if setup completed successfully
        """
        print("Configure system and Docker settings.\n")

        # Docker restart policy
        print("Docker Restart Policy:")
        print("1. unless-stopped (Recommended)")
        print("2. always")
        print("3. no")

        while True:
            choice = input("Choose restart policy (1/2/3) [1]: ").strip() or "1"
            if choice == "1":
                self.config["system"]["docker"]["restart_policy"] = "unless-stopped"
                break
            elif choice == "2":
                self.config["system"]["docker"]["restart_policy"] = "always"
                break
            elif choice == "3":
                self.config["system"]["docker"]["restart_policy"] = "no"
                break
            else:
                print("❌ Please enter 1, 2, or 3.")

        # Optional: Notification settings
        if self.ask_yes_no(
            "Do you want to configure email notifications?", default=False
        ):
            self.setup_email_notifications()

        print("✅ System settings configured!")
        self.setup_progress["system_settings"] = True
        return True

    def setup_email_notifications(self):
        """Setup email notification configuration"""
        print("\nEmail Notification Setup:")

        self.config.setdefault("notifications", {}).setdefault("email", {})[
            "enabled"
        ] = True

        sender = input("Sender email address: ").strip()
        if sender:
            self.config["notifications"]["email"]["sender"] = sender

        receiver = input("Receiver email address: ").strip()
        if receiver:
            self.config["notifications"]["email"]["receiver"] = receiver

        smtp_server = (
            input("SMTP server [smtp.gmail.com]: ").strip() or "smtp.gmail.com"
        )
        self.config["notifications"]["email"]["smtp_server"] = smtp_server

        while True:
            try:
                smtp_port_input = input("SMTP port [587]: ").strip()
                smtp_port = int(smtp_port_input) if smtp_port_input else 587
                self.config["notifications"]["email"]["smtp_port"] = smtp_port
                break
            except ValueError:
                print("❌ Please enter a valid port number.")

    def review_and_save_configuration(self) -> bool:
        """
        Review configuration and save to file

        Returns:
            True if configuration saved successfully
        """
        print("Review your configuration:\n")

        # Display key configuration items
        print(f"FOGIS Username: {self.config['fogis']['username']}")
        print(f"Referee Number: {self.config['fogis']['referee_number']}")
        print(f"Calendar ID: {self.config['google']['calendar']['calendar_id']}")
        print(f"OAuth Client Type: {self.config['google']['oauth']['client_type']}")
        print(f"Log Level: {self.config['services']['logging']['level']}")
        min_refs = self.config["services"]["processing"]["min_referees_for_whatsapp"]
        print(f"Min Referees for WhatsApp: {min_refs}")

        # Show service ports
        print("\nService Ports:")
        for service, port in self.config["services"]["ports"].items():
            print(f"  {service}: {port}")

        if not self.ask_yes_no("\nSave this configuration?", default=True):
            print("Configuration not saved. You can restart the wizard to try again.")
            return False

        try:
            # Save configuration to file
            with open("fogis-config.yaml", "w") as f:
                yaml.dump(
                    self.config, f, default_flow_style=False, sort_keys=False, indent=2
                )

            # Set appropriate permissions
            os.chmod("fogis-config.yaml", 0o600)

            print("✅ Configuration saved to fogis-config.yaml")
            return True

        except Exception as e:
            print(f"❌ Failed to save configuration: {e}")
            return False

    def generate_configuration_files(self) -> bool:
        """
        Generate configuration files from YAML

        Returns:
            True if generation completed successfully
        """
        try:
            print("Generating .env and config.json files...")

            # Validate configuration first
            validator = ConfigValidator()
            errors, warnings = validator.validate_config()

            if errors:
                print("❌ Configuration validation failed:")
                for error in errors:
                    print(f"   • {error}")
                return False

            if warnings:
                print("⚠️  Configuration warnings:")
                for warning in warnings:
                    print(f"   • {warning}")

            # Generate configuration files
            generator = ConfigGenerator()
            success = generator.generate_all_configs()

            if success:
                print("✅ Configuration files generated successfully!")
                self.setup_progress["validation"] = True
                return True
            else:
                print("❌ Failed to generate configuration files")
                return False

        except Exception as e:
            print(f"❌ Configuration generation failed: {e}")
            return False

    def validate_cron_schedule(self, schedule: str) -> bool:
        """
        Validate cron schedule format

        Args:
            schedule: Cron schedule string

        Returns:
            True if schedule appears valid
        """
        parts = schedule.split()
        if len(parts) != 5:
            return False

        # Basic pattern check
        cron_pattern = re.compile(r"^[\d\*\-\,\/]+$")
        return all(cron_pattern.match(part) for part in parts)

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

    def display_setup_progress(self):
        """Display current setup progress"""
        print("\n📊 Setup Progress:")
        for step, completed in self.setup_progress.items():
            status = "✅" if completed else "⏳"
            step_name = step.replace("_", " ").title()
            print(f"  {status} {step_name}")


def main():
    """
    Main function for interactive setup wizard
    """
    try:
        setup_wizard = InteractiveSetup()
        success = setup_wizard.run_setup_wizard()

        if success:
            print("\n🎉 Setup completed successfully!")
            print("Your FOGIS system is now configured with portable configuration.")
        else:
            print("\n❌ Setup was not completed.")
            print("You can run this wizard again at any time.")

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user.")
        return 1
    except Exception as e:
        logger.error(f"Setup wizard failed: {e}")
        print(f"\n❌ Setup wizard failed: {e}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
