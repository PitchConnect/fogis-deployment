#!/usr/bin/env python3
"""
Migration Tool for FOGIS Deployment
Converts legacy .env + config.json to portable fogis-config.yaml

This module provides safe migration from legacy configuration files to the new
portable configuration system with comprehensive backup and rollback capabilities.
"""

import json
import logging
import os
import shutil
import tarfile
from datetime import datetime
from typing import Any, Dict, List

import yaml

# Import our configuration components
from config_generator import ConfigGenerator
from config_manager import ConfigManager
from config_validator import ConfigValidator
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Exception raised for migration-related errors"""


class MigrationTool:
    """
    Migrate from legacy to portable configuration

    Provides safe migration with:
    - Automatic backup creation
    - Configuration validation
    - Rollback capability
    - Comprehensive error handling
    """

    def __init__(self):
        """Initialize migration tool"""
        self.backup_dir = None
        self.migration_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    def run_migration_wizard(self) -> bool:
        """
        Interactive migration wizard

        Returns:
            True if migration completed successfully
        """
        print("🔄 Migration to Portable Configuration")
        print("=" * 40)

        # Analyze current setup
        current_setup = self.analyze_current_setup()
        self.display_migration_benefits(current_setup)

        if not self.confirm_migration():
            print("Migration cancelled. Your current setup remains unchanged.")
            return False

        try:
            # Create backup
            print("📦 Creating backup of current configuration...")
            backup_file = self.create_pre_migration_backup()
            print(f"✅ Backup created: {backup_file}")

            # Perform migration
            print("🔄 Converting configuration...")
            success = self.migrate_legacy_to_portable()

            if success:
                print("✅ Migration completed successfully!")
                print(f"📦 Backup saved as: {backup_file}")
                print("🚀 Your system is now using portable configuration!")

                # Offer to test new configuration
                if self.ask_yes_no("Would you like to test the new configuration?"):
                    self.test_migrated_configuration()
            else:
                print("❌ Migration failed. Restoring from backup...")
                self.restore_from_backup(backup_file)

            return success

        except Exception as e:
            logger.error(f"Migration failed with error: {e}")
            if self.backup_dir:
                print("❌ Migration failed. Restoring from backup...")
                self.restore_from_backup(backup_file)
            return False

    def analyze_current_setup(self) -> Dict[str, Any]:
        """
        Analyze current configuration setup

        Returns:
            Dict containing analysis of current setup
        """
        analysis = {
            "has_env_file": os.path.exists(".env"),
            "has_config_json": os.path.exists(
                "fogis-calendar-phonebook-sync/config.json"
            ),
            "has_credentials": os.path.exists("credentials.json"),
            "has_tokens": self.check_oauth_tokens(),
            "services_running": self.check_running_services(),
            "has_portable_config": os.path.exists("fogis-config.yaml"),
            "env_file_size": os.path.getsize(".env") if os.path.exists(".env") else 0,
            "config_complexity": self.assess_config_complexity(),
        }

        logger.debug(f"Current setup analysis: {analysis}")
        return analysis

    def display_migration_benefits(self, current_setup: Dict[str, Any]):
        """
        Display migration benefits to user

        Args:
            current_setup: Analysis of current configuration
        """
        print("\n📋 Current Configuration Analysis:")
        env_status = "✅ Found" if current_setup["has_env_file"] else "❌ Not found"
        print(f"   • .env file: {env_status}")

        config_status = "✅ Found" if current_setup["has_config_json"] else "❌ Not found"
        print(f"   • config.json: {config_status}")

        creds_status = "✅ Found" if current_setup["has_credentials"] else "❌ Not found"
        print(f"   • OAuth credentials: {creds_status}")

        tokens_status = "✅ Found" if current_setup["has_tokens"] else "❌ Not found"
        print(f"   • OAuth tokens: {tokens_status}")

        if current_setup["has_portable_config"]:
            print("⚠️  Portable configuration already exists!")
            print("   Migration will update the existing fogis-config.yaml file.")

        print("\n🚀 Benefits of Portable Configuration:")
        print("   ✅ Single configuration file (fogis-config.yaml)")
        print("   ✅ Easy backup and migration")
        print("   ✅ Infrastructure as Code support")
        print("   ✅ Enhanced validation and error checking")
        print("   ✅ Automatic configuration file generation")
        print("   ✅ Better documentation and comments")

        print("\n🛡️  Migration Safety:")
        print("   ✅ Automatic backup of current configuration")
        print("   ✅ Validation before applying changes")
        print("   ✅ Rollback capability if migration fails")
        print("   ✅ No data loss - all settings preserved")

    def confirm_migration(self) -> bool:
        """
        Confirm migration with user

        Returns:
            True if user confirms migration
        """
        print("\n" + "=" * 50)
        return self.ask_yes_no("Do you want to proceed with the migration?")

    def migrate_legacy_to_portable(self) -> bool:
        """
        Convert legacy configuration to portable format

        Returns:
            True if migration completed successfully

        Raises:
            MigrationError: If migration fails
        """
        try:
            # Load legacy configuration
            legacy_config = self.load_legacy_config()

            # Convert to YAML structure
            yaml_config = self.convert_to_yaml_structure(legacy_config)

            # Validate converted configuration
            # Temporarily save config for validation
            temp_config_path = f"fogis-config-temp-{self.migration_timestamp}.yaml"
            with open(temp_config_path, "w") as f:
                yaml.dump(yaml_config, f, default_flow_style=False, sort_keys=False)

            # Validate the temporary config
            temp_validator = ConfigValidator(temp_config_path)
            errors, warnings = temp_validator.validate_config()

            # Remove temporary file
            os.remove(temp_config_path)

            if errors:
                raise MigrationError(f"Validation failed: {errors}")

            if warnings:
                print("⚠️  Configuration warnings:")
                for warning in warnings:
                    print(f"   • {warning}")

                if not self.ask_yes_no("Continue with migration despite warnings?"):
                    return False

            # Save YAML configuration
            self.save_yaml_config(yaml_config)

            # Generate derived configuration files
            generator = ConfigGenerator()
            generator.generate_all_configs()

            print("✅ Configuration files generated successfully")
            return True

        except Exception as e:
            raise MigrationError(f"Migration failed: {e}")

    def load_legacy_config(self) -> Dict[str, Any]:
        """
        Load configuration from legacy .env and config.json files

        Returns:
            Dict containing legacy configuration

        Raises:
            MigrationError: If legacy configuration cannot be loaded
        """
        config = {}

        # Load .env file
        if os.path.exists(".env"):
            load_dotenv(".env")
            config.update(self._convert_env_to_config())
            logger.info("Loaded configuration from .env file")
        else:
            logger.warning("No .env file found")

        # Load calendar config.json if it exists
        calendar_config_path = "fogis-calendar-phonebook-sync/config.json"
        if os.path.exists(calendar_config_path):
            try:
                with open(calendar_config_path, "r") as f:
                    calendar_config = json.load(f)
                config.update(self._convert_calendar_config(calendar_config))
                logger.info("Loaded configuration from calendar config.json")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Could not load calendar config: {e}")

        if not config:
            raise MigrationError("No legacy configuration found to migrate")

        return config

    def convert_to_yaml_structure(
        self, legacy_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert legacy configuration to YAML structure

        Args:
            legacy_config: Legacy configuration dictionary

        Returns:
            Dict in portable YAML configuration format
        """
        # Start with default configuration structure
        config_manager = ConfigManager()
        yaml_config = config_manager.get_default_config()

        # Update metadata
        yaml_config["metadata"]["created"] = datetime.now().isoformat()
        yaml_config["metadata"][
            "description"
        ] = "FOGIS Configuration (Migrated from Legacy)"

        # Merge legacy configuration
        self._merge_legacy_into_yaml(legacy_config, yaml_config)

        return yaml_config

    def _merge_legacy_into_yaml(
        self, legacy_config: Dict[str, Any], yaml_config: Dict[str, Any]
    ):
        """
        Merge legacy configuration into YAML structure

        Args:
            legacy_config: Legacy configuration to merge
            yaml_config: Target YAML configuration (modified in place)
        """
        # FOGIS credentials
        if "fogis" in legacy_config:
            yaml_config["fogis"].update(legacy_config["fogis"])

        # Google configuration
        if "google" in legacy_config:
            if "calendar" in legacy_config["google"]:
                yaml_config["google"]["calendar"].update(
                    legacy_config["google"]["calendar"]
                )
            if "oauth" in legacy_config["google"]:
                yaml_config["google"]["oauth"].update(legacy_config["google"]["oauth"])
            if "drive" in legacy_config["google"]:
                yaml_config["google"]["drive"].update(legacy_config["google"]["drive"])

        # Services configuration
        if "services" in legacy_config:
            if "ports" in legacy_config["services"]:
                yaml_config["services"]["ports"].update(
                    legacy_config["services"]["ports"]
                )
            if "logging" in legacy_config["services"]:
                yaml_config["services"]["logging"].update(
                    legacy_config["services"]["logging"]
                )
            if "processing" in legacy_config["services"]:
                yaml_config["services"]["processing"].update(
                    legacy_config["services"]["processing"]
                )

        # System configuration
        if "system" in legacy_config:
            if "docker" in legacy_config["system"]:
                yaml_config["system"]["docker"].update(
                    legacy_config["system"]["docker"]
                )

    def _convert_env_to_config(self) -> Dict[str, Any]:
        """
        Convert environment variables to configuration structure

        Returns:
            Dict containing configuration from environment variables
        """
        config: Dict[str, Any] = {}

        # FOGIS credentials
        if os.getenv("FOGIS_USERNAME"):
            config.setdefault("fogis", {})["username"] = os.getenv("FOGIS_USERNAME")
        if os.getenv("FOGIS_PASSWORD"):
            config.setdefault("fogis", {})["password"] = os.getenv("FOGIS_PASSWORD")
        if os.getenv("USER_REFEREE_NUMBER"):
            config.setdefault("fogis", {})["referee_number"] = int(
                os.getenv("USER_REFEREE_NUMBER", 0)
            )

        # Google configuration
        if os.getenv("GOOGLE_CALENDAR_ID"):
            config.setdefault("google", {}).setdefault("calendar", {})[
                "calendar_id"
            ] = os.getenv("GOOGLE_CALENDAR_ID")

        # Service ports
        port_mapping = {
            "API_CLIENT_PORT": "api_client",
            "MATCH_PROCESSOR_PORT": "match_processor",
            "CALENDAR_SYNC_PORT": "calendar_sync",
            "CALENDAR_AUTH_PORT": "calendar_auth",
            "CALENDAR_WEB_TRIGGER_PORT": "calendar_web_trigger",
            "LOGO_COMBINER_PORT": "logo_combiner",
            "DRIVE_SERVICE_PORT": "google_drive",
            "MATCH_DETECTOR_PORT": "change_detector",
        }

        for env_key, config_key in port_mapping.items():
            if os.getenv(env_key):
                config.setdefault("services", {}).setdefault("ports", {})[
                    config_key
                ] = int(os.getenv(env_key))

        # Logging configuration
        if os.getenv("LOG_LEVEL"):
            config.setdefault("services", {}).setdefault("logging", {})[
                "level"
            ] = os.getenv("LOG_LEVEL")
        if os.getenv("DEBUG_MODE"):
            config.setdefault("services", {}).setdefault("logging", {})[
                "debug_mode"
            ] = (os.getenv("DEBUG_MODE").lower() == "1")

        # Processing configuration
        if os.getenv("MIN_REFEREES_FOR_WHATSAPP"):
            config.setdefault("services", {}).setdefault("processing", {})[
                "min_referees_for_whatsapp"
            ] = int(os.getenv("MIN_REFEREES_FOR_WHATSAPP"))
        if os.getenv("MATCH_CHECK_SCHEDULE"):
            config.setdefault("services", {}).setdefault("processing", {})[
                "match_check_schedule"
            ] = os.getenv("MATCH_CHECK_SCHEDULE")
        if os.getenv("FORCE_FRESH_PROCESSING"):
            config.setdefault("services", {}).setdefault("processing", {})[
                "force_fresh_processing"
            ] = (os.getenv("FORCE_FRESH_PROCESSING").lower() == "true")

        return config

    def _convert_calendar_config(
        self, calendar_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert calendar config.json to portable configuration format

        Args:
            calendar_config: Calendar configuration from config.json

        Returns:
            Dict containing converted configuration
        """
        config: Dict[str, Any] = {}

        # Google calendar configuration
        if "CALENDAR_ID" in calendar_config:
            config.setdefault("google", {}).setdefault("calendar", {})[
                "calendar_id"
            ] = calendar_config["CALENDAR_ID"]

        if "SYNC_TAG" in calendar_config:
            config.setdefault("google", {}).setdefault("calendar", {})[
                "sync_tag"
            ] = calendar_config["SYNC_TAG"]

        if "DAYS_TO_KEEP_PAST_EVENTS" in calendar_config:
            config.setdefault("google", {}).setdefault("calendar", {})[
                "days_to_keep_past_events"
            ] = calendar_config["DAYS_TO_KEEP_PAST_EVENTS"]

        if "SCOPES" in calendar_config:
            config.setdefault("google", {}).setdefault("oauth", {})[
                "scopes"
            ] = calendar_config["SCOPES"]

        # FOGIS configuration
        if "USER_REFEREE_NUMBER" in calendar_config:
            config.setdefault("fogis", {})["referee_number"] = calendar_config[
                "USER_REFEREE_NUMBER"
            ]

        # Notification configuration
        if calendar_config.get("NOTIFICATION_METHOD") == "email":
            config.setdefault("notifications", {}).setdefault("email", {})[
                "enabled"
            ] = True
            if "NOTIFICATION_EMAIL_SENDER" in calendar_config:
                config["notifications"]["email"]["sender"] = calendar_config[
                    "NOTIFICATION_EMAIL_SENDER"
                ]
            if "NOTIFICATION_EMAIL_RECEIVER" in calendar_config:
                config["notifications"]["email"]["receiver"] = calendar_config[
                    "NOTIFICATION_EMAIL_RECEIVER"
                ]
            if "SMTP_SERVER" in calendar_config:
                config["notifications"]["email"]["smtp_server"] = calendar_config[
                    "SMTP_SERVER"
                ]
            if "SMTP_PORT" in calendar_config:
                config["notifications"]["email"]["smtp_port"] = calendar_config[
                    "SMTP_PORT"
                ]

        return config

    def save_yaml_config(self, yaml_config: Dict[str, Any]):
        """
        Save YAML configuration to file

        Args:
            yaml_config: Configuration to save
        """
        with open("fogis-config.yaml", "w") as f:
            yaml.dump(
                yaml_config, f, default_flow_style=False, sort_keys=False, indent=2
            )

        # Set appropriate permissions
        os.chmod("fogis-config.yaml", 0o600)

        logger.info("Saved portable configuration to fogis-config.yaml")

    def create_pre_migration_backup(self) -> str:
        """
        Create comprehensive backup before migration

        Returns:
            Path to backup file

        Raises:
            MigrationError: If backup creation fails
        """
        try:
            backup_filename = f"fogis-config-backup-{self.migration_timestamp}.tar.gz"
            backup_path = os.path.abspath(backup_filename)

            with tarfile.open(backup_path, "w:gz") as tar:
                # Backup .env file
                if os.path.exists(".env"):
                    tar.add(".env", arcname="env_backup/.env")

                # Backup config.json
                calendar_config_path = "fogis-calendar-phonebook-sync/config.json"
                if os.path.exists(calendar_config_path):
                    tar.add(calendar_config_path, arcname="config_backup/config.json")

                # Backup credentials.json
                if os.path.exists("credentials.json"):
                    tar.add(
                        "credentials.json",
                        arcname="credentials_backup/credentials.json",
                    )

                # Backup OAuth tokens
                token_files = [
                    "data/google-drive-service/google-drive-token.json",
                    "data/calendar-sync/calendar-token.json",
                    "fogis-calendar-phonebook-sync/token.json",
                ]

                for token_file in token_files:
                    if os.path.exists(token_file):
                        tar.add(
                            token_file,
                            arcname=f"tokens_backup/{os.path.basename(token_file)}",
                        )

                # Backup existing portable config if it exists
                if os.path.exists("fogis-config.yaml"):
                    tar.add(
                        "fogis-config.yaml", arcname="portable_backup/fogis-config.yaml"
                    )

                # Create migration metadata
                metadata = {
                    "migration_timestamp": self.migration_timestamp,
                    "migration_tool_version": "2.0",
                    "backup_contents": {
                        "env_file": os.path.exists(".env"),
                        "config_json": os.path.exists(calendar_config_path),
                        "credentials": os.path.exists("credentials.json"),
                        "existing_portable": os.path.exists("fogis-config.yaml"),
                        "token_files": [f for f in token_files if os.path.exists(f)],
                    },
                }

                # Save metadata to temporary file and add to backup
                metadata_file = f"migration-metadata-{self.migration_timestamp}.json"
                with open(metadata_file, "w") as f:
                    json.dump(metadata, f, indent=2)
                tar.add(metadata_file, arcname="migration-metadata.json")
                os.remove(metadata_file)

            self.backup_dir = backup_path
            logger.info(f"Created backup: {backup_path}")
            return backup_path

        except Exception as e:
            raise MigrationError(f"Failed to create backup: {e}")

    def restore_from_backup(self, backup_path: str) -> bool:
        """
        Restore configuration from backup

        Args:
            backup_path: Path to backup file

        Returns:
            True if restore completed successfully
        """
        try:
            print(f"🔄 Restoring from backup: {backup_path}")

            with tarfile.open(backup_path, "r:gz") as tar:
                # Extract all files safely
                self._safe_extract(tar, ".")

                # Move files back to their original locations
                if os.path.exists("env_backup/.env"):
                    shutil.move("env_backup/.env", ".env")
                    shutil.rmtree("env_backup", ignore_errors=True)

                if os.path.exists("config_backup/config.json"):
                    os.makedirs("fogis-calendar-phonebook-sync", exist_ok=True)
                    shutil.move(
                        "config_backup/config.json",
                        "fogis-calendar-phonebook-sync/config.json",
                    )
                    shutil.rmtree("config_backup", ignore_errors=True)

                if os.path.exists("credentials_backup/credentials.json"):
                    shutil.move(
                        "credentials_backup/credentials.json", "credentials.json"
                    )
                    shutil.rmtree("credentials_backup", ignore_errors=True)

                # Restore token files
                if os.path.exists("tokens_backup"):
                    for token_file in os.listdir("tokens_backup"):
                        src = os.path.join("tokens_backup", token_file)

                        # Determine destination based on filename
                        if "google-drive-token" in token_file:
                            dest_dir = "data/google-drive-service"
                            os.makedirs(dest_dir, exist_ok=True)
                            dest = os.path.join(dest_dir, token_file)
                        elif "calendar-token" in token_file:
                            dest_dir = "data/calendar-sync"
                            os.makedirs(dest_dir, exist_ok=True)
                            dest = os.path.join(dest_dir, token_file)
                        else:
                            dest = os.path.join(
                                "fogis-calendar-phonebook-sync", token_file
                            )

                        shutil.move(src, dest)

                    shutil.rmtree("tokens_backup", ignore_errors=True)

                # Remove migrated portable config if restore is happening
                if os.path.exists("fogis-config.yaml"):
                    os.remove("fogis-config.yaml")

                # Restore original portable config if it existed
                if os.path.exists("portable_backup/fogis-config.yaml"):
                    shutil.move(
                        "portable_backup/fogis-config.yaml", "fogis-config.yaml"
                    )
                    shutil.rmtree("portable_backup", ignore_errors=True)

            print("✅ Configuration restored from backup successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            print(f"❌ Failed to restore from backup: {e}")
            return False

    def check_oauth_tokens(self) -> bool:
        """
        Check if OAuth tokens exist

        Returns:
            True if OAuth tokens are found
        """
        token_files = [
            "data/google-drive-service/google-drive-token.json",
            "data/calendar-sync/calendar-token.json",
            "fogis-calendar-phonebook-sync/token.json",
        ]

        return any(os.path.exists(token_file) for token_file in token_files)

    def check_running_services(self) -> bool:
        """
        Check if FOGIS services are currently running

        Returns:
            True if services are running
        """
        try:
            import subprocess

            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose-master.yml", "ps", "-q"],
                capture_output=True,
                text=True,
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    def assess_config_complexity(self) -> str:
        """
        Assess complexity of current configuration

        Returns:
            String describing configuration complexity
        """
        complexity_score = 0

        if os.path.exists(".env"):
            with open(".env", "r") as f:
                lines = f.readlines()
                complexity_score += len(
                    [
                        line
                        for line in lines
                        if line.strip() and not line.startswith("#")
                    ]
                )

        if os.path.exists("fogis-calendar-phonebook-sync/config.json"):
            complexity_score += 5  # JSON config adds complexity

        if self.check_oauth_tokens():
            complexity_score += 3  # OAuth tokens add complexity

        if complexity_score <= 5:
            return "Simple"
        elif complexity_score <= 15:
            return "Moderate"
        else:
            return "Complex"

    def _safe_extract(self, tar: tarfile.TarFile, path: str = "."):
        """
        Safely extract tar file to prevent directory traversal attacks

        Args:
            tar: TarFile object to extract
            path: Destination path for extraction
        """

        def is_within_directory(directory: str, target: str) -> bool:
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
            prefix = os.path.commonpath([abs_directory, abs_target])
            return prefix == abs_directory

        for member in tar.getmembers():
            member_path = os.path.join(path, member.name)
            if not is_within_directory(path, member_path):
                raise Exception(f"Attempted path traversal in tar file: {member.name}")

            # Extract individual member safely
            tar.extract(member, path)

    def test_migrated_configuration(self) -> bool:
        """
        Test the migrated configuration

        Returns:
            True if configuration tests pass
        """
        try:
            print("🧪 Testing migrated configuration...")

            # Test configuration loading
            config_manager = ConfigManager()
            if config_manager.mode != "portable":
                print("❌ Configuration not in portable mode")
                return False

            # Test configuration validation
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

            # Test configuration generation
            generator = ConfigGenerator()
            if not generator.validate_generated_configs():
                print("❌ Generated configuration validation failed")
                return False

            print("✅ Configuration test passed!")
            return True

        except Exception as e:
            print(f"❌ Configuration test failed: {e}")
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

    def get_migration_status(self) -> Dict[str, Any]:
        """
        Get current migration status

        Returns:
            Dict containing migration status information
        """
        status = {
            "current_mode": "unknown",
            "has_legacy_config": False,
            "has_portable_config": False,
            "migration_needed": False,
            "backup_files": [],
            "last_migration": None,
        }

        # Detect current configuration mode
        if os.path.exists("fogis-config.yaml"):
            status["current_mode"] = "portable"
            status["has_portable_config"] = True
        elif os.path.exists(".env"):
            status["current_mode"] = "legacy"
            status["has_legacy_config"] = True
        else:
            status["current_mode"] = "none"

        # Check if migration is needed
        status["migration_needed"] = (
            status["has_legacy_config"] and not status["has_portable_config"]
        )

        # Find backup files
        backup_pattern = "fogis-config-backup-*.tar.gz"
        import glob

        backup_files: List[str] = sorted(glob.glob(backup_pattern), reverse=True)
        status["backup_files"] = backup_files

        # Get last migration timestamp from most recent backup
        if backup_files:
            try:
                latest_backup = backup_files[0]
                # Extract timestamp from filename
                timestamp_str = latest_backup.replace(
                    "fogis-config-backup-", ""
                ).replace(".tar.gz", "")
                status["last_migration"] = datetime.strptime(
                    timestamp_str, "%Y%m%d-%H%M%S"
                )
            except Exception:
                pass

        return status

    def display_migration_status(self):
        """Display current migration status to user"""
        status = self.get_migration_status()

        print("📊 Migration Status")
        print("=" * 20)
        print(f"Current mode: {status['current_mode']}")
        print(f"Has legacy config: {'✅' if status['has_legacy_config'] else '❌'}")
        print(f"Has portable config: {'✅' if status['has_portable_config'] else '❌'}")
        print(f"Migration needed: {'✅' if status['migration_needed'] else '❌'}")

        if status["backup_files"]:
            print(f"Available backups: {len(status['backup_files'])}")
            print("Recent backups:")
            for backup in status["backup_files"][:3]:  # Show 3 most recent
                print(f"  • {backup}")
        else:
            print("Available backups: None")

        if status["last_migration"]:
            timestamp = status["last_migration"].strftime("%Y-%m-%d %H:%M:%S")
            print(f"Last migration: {timestamp}")


def main():
    """
    Main function for migration tool
    """
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        migration_tool = MigrationTool()

        if command == "status":
            migration_tool.display_migration_status()
        elif command == "migrate":
            success = migration_tool.run_migration_wizard()
            sys.exit(0 if success else 1)
        elif command == "test":
            success = migration_tool.test_migrated_configuration()
            sys.exit(0 if success else 1)
        else:
            print(f"Unknown command: {command}")
            print("Available commands: status, migrate, test")
            sys.exit(1)
    else:
        # Interactive mode
        migration_tool = MigrationTool()
        success = migration_tool.run_migration_wizard()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
