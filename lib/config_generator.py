#!/usr/bin/env python3
"""
Configuration File Generator for FOGIS Deployment
Generates .env, config.json, and docker-compose environment from fogis-config.yaml

This module provides functionality to generate all required configuration files
from a single portable YAML configuration file, maintaining compatibility with
existing file formats and structures.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import sys

# Debug information
print(f"DEBUG: Python executable: {sys.executable}", file=sys.stderr)
print(f"DEBUG: Python path: {sys.path[:3]}", file=sys.stderr)

try:
    import yaml
    print("DEBUG: YAML import successful", file=sys.stderr)
except ImportError as e:
    print(f"DEBUG: YAML import failed: {e}", file=sys.stderr)
    print("DEBUG: Attempting to install PyYAML...", file=sys.stderr)
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml"])
    import yaml
    print("DEBUG: YAML installed and imported successfully", file=sys.stderr)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigGenerationError(Exception):
    """Exception raised for configuration generation errors"""



class ConfigGenerator:
    """
    Generate configuration files from fogis-config.yaml

    Supports generation of:
    - .env file for environment variables
    - config.json for calendar sync service
    - docker-compose environment variables
    - Validation of generated configurations
    """

    def __init__(self, config_file: str = "fogis-config.yaml"):
        """
        Initialize configuration generator

        Args:
            config_file: Path to YAML configuration file
        """
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """
        Load YAML configuration file

        Returns:
            Dict containing configuration data

        Raises:
            ConfigGenerationError: If configuration file is invalid or missing
        """
        try:
            with open(self.config_file, "r") as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict):
                raise ConfigGenerationError(
                    f"Invalid YAML configuration in {self.config_file}"
                )

            logger.debug(f"Loaded configuration from {self.config_file}")
            return config

        except FileNotFoundError:
            raise ConfigGenerationError(
                f"Configuration file {self.config_file} not found"
            )
        except yaml.YAMLError as e:
            raise ConfigGenerationError(f"Invalid YAML in {self.config_file}: {e}")

    def generate_env_file(self, output_path: str = ".env") -> str:
        """
        Generate .env file from YAML configuration

        Args:
            output_path: Path where .env file should be written

        Returns:
            String content of generated .env file
        """
        env_lines = [
            "# FOGIS Deployment Configuration",
            f"# Generated from {self.config_file} on {datetime.now().isoformat()}",
            f"# Configuration version: "
            f"{self.config.get('metadata', {}).get('version', 'unknown')}",
            "",
            "# FOGIS Authentication",
        ]

        # FOGIS credentials
        fogis_config = self.config.get("fogis", {})
        env_lines.extend(
            [
                f"FOGIS_USERNAME={fogis_config.get('username', '')}",
                f"FOGIS_PASSWORD={fogis_config.get('password', '')}",
                f"USER_REFEREE_NUMBER={fogis_config.get('referee_number', 0)}",
                "",
            ]
        )

        # Google configuration
        google_config = self.config.get("google", {})
        calendar_config = google_config.get("calendar", {})
        oauth_config = google_config.get("oauth", {})

        env_lines.extend(
            [
                "# Google Configuration",
                "GOOGLE_CREDENTIALS_PATH=credentials/google-credentials.json",
                f"GOOGLE_CALENDAR_ID={calendar_config.get('calendar_id', 'primary')}",
                f"GOOGLE_SCOPES={','.join(oauth_config.get('scopes', []))}",
                "",
            ]
        )

        # Service ports
        services_config = self.config.get("services", {})
        ports_config = services_config.get("ports", {})

        env_lines.extend(
            [
                "# Service Ports",
                f"API_CLIENT_PORT={ports_config.get('api_client', 9086)}",
                f"MATCH_PROCESSOR_PORT={ports_config.get('match_processor', 9082)}",
                f"CALENDAR_SYNC_PORT={ports_config.get('calendar_sync', 9083)}",
                f"CALENDAR_AUTH_PORT={ports_config.get('calendar_auth', 9084)}",
                f"CALENDAR_WEB_TRIGGER_PORT={ports_config.get('calendar_web_trigger', 9087)}",
                f"LOGO_COMBINER_PORT={ports_config.get('logo_combiner', 9088)}",
                f"DRIVE_SERVICE_PORT={ports_config.get('google_drive', 9085)}",
                f"MATCH_DETECTOR_PORT={ports_config.get('change_detector', 9080)}",
                "",
            ]
        )

        # Processing configuration
        processing_config = services_config.get("processing", {})
        env_lines.extend(
            [
                "# Processing Configuration",
                f"MIN_REFEREES_FOR_WHATSAPP={processing_config.get('min_referees_for_whatsapp', 2)}",
                f"MATCH_CHECK_SCHEDULE={processing_config.get('match_check_schedule', '0 * * * *')}",
                f"FORCE_FRESH_PROCESSING={str(processing_config.get('force_fresh_processing', True)).lower()}",
                f"SERVICE_INTERVAL={processing_config.get('service_interval', 300)}",
                "",
            ]
        )

        # System configuration
        logging_config = services_config.get("logging", {})
        system_config = self.config.get("system", {})
        docker_config = system_config.get("docker", {})
        drive_config = google_config.get("drive", {})

        env_lines.extend(
            [
                "# System Configuration",
                f"LOG_LEVEL={logging_config.get('level', 'INFO')}",
                f"DEBUG_MODE={'1' if logging_config.get('debug_mode', False) else '0'}",
                f"RESTART_POLICY={docker_config.get('restart_policy', 'unless-stopped')}",
                f"GDRIVE_FOLDER_BASE={drive_config.get('folder_base', 'WhatsApp_Group_Assets')}",
                "",
            ]
        )

        env_content = "\n".join(env_lines)

        # Write to file
        with open(output_path, "w") as f:
            f.write(env_content)

        logger.info(f"Generated .env file: {output_path}")
        return env_content

    def generate_docker_compose_env(self) -> Dict[str, str]:
        """
        Generate environment variables for docker-compose

        Returns:
            Dict containing environment variables for docker-compose
        """
        fogis_config = self.config.get("fogis", {})
        services_config = self.config.get("services", {})
        ports_config = services_config.get("ports", {})
        logging_config = services_config.get("logging", {})

        return {
            "FOGIS_USERNAME": str(fogis_config.get("username", "")),
            "FOGIS_PASSWORD": str(fogis_config.get("password", "")),
            "USER_REFEREE_NUMBER": str(fogis_config.get("referee_number", 0)),
            "LOG_LEVEL": logging_config.get("level", "INFO"),
            "DEBUG_MODE": "1" if logging_config.get("debug_mode", False) else "0",
            "API_CLIENT_PORT": str(ports_config.get("api_client", 9086)),
            "MATCH_PROCESSOR_PORT": str(ports_config.get("match_processor", 9082)),
            "CALENDAR_SYNC_PORT": str(ports_config.get("calendar_sync", 9083)),
            "CALENDAR_AUTH_PORT": str(ports_config.get("calendar_auth", 9084)),
            "CALENDAR_WEB_TRIGGER_PORT": str(
                ports_config.get("calendar_web_trigger", 9087)
            ),
            "LOGO_COMBINER_PORT": str(ports_config.get("logo_combiner", 9088)),
            "DRIVE_SERVICE_PORT": str(ports_config.get("google_drive", 9085)),
            "MATCH_DETECTOR_PORT": str(ports_config.get("change_detector", 9080)),
        }

    def generate_calendar_config(
        self, output_path: str = "fogis-calendar-phonebook-sync/config.json"
    ) -> Dict[str, Any]:
        """
        Generate config.json for calendar sync service

        Args:
            output_path: Path where config.json should be written

        Returns:
            Dict containing calendar configuration
        """
        google_config = self.config.get("google", {})
        calendar_config = google_config.get("calendar", {})
        oauth_config = google_config.get("oauth", {})
        fogis_config = self.config.get("fogis", {})
        services_config = self.config.get("services", {})
        ports_config = services_config.get("ports", {})
        notifications_config = self.config.get("notifications", {})
        email_config = notifications_config.get("email", {})
        discord_config = notifications_config.get("discord", {})
        slack_config = notifications_config.get("slack", {})

        config = {
            "CALENDAR_ID": calendar_config.get("calendar_id", "primary"),
            "SYNC_TAG": calendar_config.get("sync_tag", "FOGIS_CALENDAR_SYNC"),
            "DAYS_TO_KEEP_PAST_EVENTS": calendar_config.get(
                "days_to_keep_past_events", 7
            ),
            "USER_REFEREE_NUMBER": fogis_config.get("referee_number", 0),
            "SCOPES": oauth_config.get(
                "scopes",
                [
                    "https://www.googleapis.com/auth/calendar",
                    "https://www.googleapis.com/auth/contacts",
                    "https://www.googleapis.com/auth/drive",
                ],
            ),
            "CREDENTIALS_FILE": "credentials.json",
            "TOKEN_REFRESH_BUFFER_DAYS": 1,
            "AUTH_SERVER_PORT": ports_config.get("calendar_auth", 9084),
            "AUTH_SERVER_HOST": "0.0.0.0",  # nosec B104 - intentional for Docker
            "NOTIFICATION_METHOD": (
                "email" if email_config.get("enabled", False) else "none"
            ),
            "NOTIFICATION_EMAIL_SENDER": email_config.get("sender", ""),
            "NOTIFICATION_EMAIL_RECEIVER": email_config.get("receiver", ""),
            "SMTP_SERVER": email_config.get("smtp_server", "smtp.gmail.com"),
            "SMTP_PORT": email_config.get("smtp_port", 587),
            "DISCORD_WEBHOOK_URL": discord_config.get("webhook_url", ""),
            "SLACK_WEBHOOK_URL": slack_config.get("webhook_url", ""),
        }

        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write to file
        with open(output_path, "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"Generated calendar config: {output_path}")
        return config

    def generate_all_configs(self) -> bool:
        """
        Generate all configuration files from YAML

        Returns:
            True if all configurations generated successfully

        Raises:
            ConfigGenerationError: If any configuration generation fails
        """
        try:
            # Generate .env file
            self.generate_env_file()

            # Generate calendar config
            self.generate_calendar_config()

            # Copy credentials file if it exists
            self.copy_credentials_file()

            logger.info("All configuration files generated successfully")
            return True

        except Exception as e:
            raise ConfigGenerationError(f"Failed to generate configurations: {e}")

    def copy_credentials_file(self):
        """
        Copy Google OAuth credentials to container credentials directory
        """
        source_path = "credentials.json"
        dest_dir = Path("credentials")
        dest_path = dest_dir / "google-credentials.json"

        if os.path.exists(source_path):
            # Ensure destination directory exists
            dest_dir.mkdir(exist_ok=True)

            # Copy credentials file
            import shutil

            shutil.copy2(source_path, dest_path)

            # Set appropriate permissions
            os.chmod(dest_path, 0o600)

            logger.info(f"Copied credentials: {source_path} -> {dest_path}")
        else:
            logger.warning(f"Credentials file not found: {source_path}")

    def validate_generated_configs(self) -> bool:
        """
        Validate that all generated configuration files are valid

        Returns:
            True if all configurations are valid
        """
        try:
            # Validate .env file exists and is readable
            if not os.path.exists(".env"):
                logger.error(".env file not found")
                return False

            # Validate calendar config exists and is valid JSON
            calendar_config_path = "fogis-calendar-phonebook-sync/config.json"
            if os.path.exists(calendar_config_path):
                with open(calendar_config_path, "r") as f:
                    json.load(f)  # Will raise exception if invalid JSON
            else:
                logger.warning(f"Calendar config not found: {calendar_config_path}")

            # Validate credentials file
            if not os.path.exists("credentials/google-credentials.json"):
                logger.warning(
                    "Google credentials file not found in credentials directory"
                )

            logger.info("Configuration validation completed")
            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False


def main():
    """
    Main function for testing configuration generator
    """
    try:
        generator = ConfigGenerator()

        print("Generating configuration files...")
        success = generator.generate_all_configs()

        if success:
            print("✅ All configuration files generated successfully!")

            # Validate generated configurations
            if generator.validate_generated_configs():
                print("✅ All configurations validated successfully!")
            else:
                print("⚠️  Some configuration validations failed")
        else:
            print("❌ Configuration generation failed")

    except ConfigGenerationError as e:
        print(f"Configuration generation error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
