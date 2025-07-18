#!/usr/bin/env python3
"""
Unified Configuration Manager for FOGIS Deployment
Supports both legacy (.env) and portable (YAML) configuration modes

This module provides a unified interface for configuration management that supports:
- Legacy configuration mode (.env + config.json files)
- Portable configuration mode (single fogis-config.yaml file)
- Configuration hierarchy with environment variable overrides
- Automatic mode detection and backward compatibility
"""

import json
import logging
import os
from typing import Any, Dict, Optional, Union

import yaml
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors"""


class ConfigManager:
    """
    Unified configuration management for FOGIS deployment

    Supports both legacy and portable configuration modes with automatic
    detection and seamless fallback between modes.
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager

        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file or "fogis-config.yaml"
        self.mode = self.detect_mode()
        self.config = self.load_configuration()
        self.env_vars = self.load_environment_variables()

        logger.info(f"Configuration manager initialized in {self.mode} mode")

    def detect_mode(self) -> str:
        """
        Auto-detect configuration mode based on available files

        Returns:
            str: Configuration mode ('portable', 'legacy', or 'new_installation')
        """
        if os.path.exists(self.config_file):
            return "portable"
        elif os.path.exists(".env"):
            return "legacy"
        else:
            return "new_installation"

    def load_configuration(self) -> Dict[str, Any]:
        """
        Load configuration based on detected mode

        Returns:
            Dict containing configuration data
        """
        if self.mode == "portable":
            return self.load_yaml_config()
        elif self.mode == "legacy":
            return self.load_legacy_config()
        else:
            return self.get_default_config()

    def load_yaml_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file

        Returns:
            Dict containing YAML configuration

        Raises:
            ConfigurationError: If YAML file is invalid or missing
        """
        try:
            with open(self.config_file, "r") as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict):
                raise ConfigurationError(
                    f"Invalid YAML configuration in {self.config_file}"
                )

            logger.debug(f"Loaded portable configuration from {self.config_file}")
            return config

        except FileNotFoundError:
            raise ConfigurationError(f"Configuration file {self.config_file} not found")
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {self.config_file}: {e}")

    def load_legacy_config(self) -> Dict[str, Any]:
        """
        Load configuration from legacy .env and config.json files

        Returns:
            Dict containing legacy configuration converted to portable format
        """
        config = {}

        # Load .env file
        if os.path.exists(".env"):
            load_dotenv(".env")
            config.update(self._convert_env_to_config())

        # Load calendar config.json if it exists
        calendar_config_path = "fogis-calendar-phonebook-sync/config.json"
        if os.path.exists(calendar_config_path):
            try:
                with open(calendar_config_path, "r") as f:
                    calendar_config = json.load(f)
                config.update(self._convert_calendar_config(calendar_config))
            except (json.JSONDecodeError, FileNotFoundError) as e:
                logger.warning(f"Could not load calendar config: {e}")

        logger.debug("Loaded legacy configuration from .env and config.json files")
        return config

    def load_environment_variables(self) -> Dict[str, str]:
        """
        Load environment variables for override capability

        Returns:
            Dict containing environment variables
        """
        return dict(os.environ)

    def get_value(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with hierarchy support

        Priority order (highest to lowest):
        1. Environment variables
        2. Configuration file (YAML or legacy)
        3. Default value

        Args:
            key: Configuration key to retrieve
            default: Default value if key not found

        Returns:
            Configuration value
        """
        # 1. Environment variables (highest priority)
        env_value = self.env_vars.get(key)
        if env_value is not None:
            return self._convert_env_value(env_value)

        # 2. Configuration file (YAML or legacy)
        config_value = self._get_nested_value(self.config, key)
        if config_value is not None:
            return config_value

        # 3. Default value
        return default

    def get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration structure

        Returns:
            Dict containing default configuration
        """
        return {
            "metadata": {
                "version": "2.0",
                "created": "",
                "description": "FOGIS Complete System Configuration",
            },
            "fogis": {"username": "", "password": "", "referee_number": 0},
            "google": {
                "oauth": {
                    "client_type": "web_application",
                    "scopes": [
                        "https://www.googleapis.com/auth/calendar",
                        "https://www.googleapis.com/auth/contacts",
                        "https://www.googleapis.com/auth/drive",
                    ],
                },
                "calendar": {
                    "calendar_id": "primary",
                    "sync_tag": "FOGIS_CALENDAR_SYNC",
                    "days_to_keep_past_events": 7,
                },
                "drive": {
                    "folder_base": "WhatsApp_Group_Assets",
                    "auto_create_folders": True,
                },
            },
            "services": {
                "ports": {
                    "api_client": 9086,
                    "match_processor": 9082,
                    "calendar_sync": 9083,
                    "calendar_auth": 9084,
                    "calendar_web_trigger": 9087,
                    "logo_combiner": 9088,
                    "google_drive": 9085,
                    "change_detector": 9080,
                },
                "processing": {
                    "min_referees_for_whatsapp": 2,
                    "match_check_schedule": "0 * * * *",
                    "force_fresh_processing": True,
                    "service_interval": 300,
                },
                "logging": {
                    "level": "INFO",
                    "debug_mode": False,
                    "verbose_logging": False,
                },
            },
            "system": {
                "docker": {
                    "restart_policy": "unless-stopped",
                    "network_name": "fogis-network",
                    "use_ghcr_images": True,
                },
                "paths": {
                    "data": "/app/data",
                    "logs": "/app/logs",
                    "credentials": "/app/credentials",
                    "temp": "/tmp",  # nosec B108 - standard temp directory
                },
            },
        }

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

        if "SCOPES" in calendar_config:
            config.setdefault("google", {}).setdefault("oauth", {})[
                "scopes"
            ] = calendar_config["SCOPES"]

        # FOGIS configuration
        if "USER_REFEREE_NUMBER" in calendar_config:
            config.setdefault("fogis", {})["referee_number"] = calendar_config[
                "USER_REFEREE_NUMBER"
            ]

        return config

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Any:
        """
        Get value from nested dictionary using dot notation

        Args:
            data: Dictionary to search
            key: Key in dot notation (e.g., 'services.ports.api_client')

        Returns:
            Value if found, None otherwise
        """
        keys = key.split(".")
        current = data

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None

        return current

    def _convert_env_value(self, value: str) -> Union[str, int, bool]:
        """
        Convert environment variable string to appropriate type

        Args:
            value: String value from environment variable

        Returns:
            Converted value (string, int, or bool)
        """
        # Boolean conversion
        if value.lower() in ("true", "false", "1", "0"):
            return value.lower() in ("true", "1")

        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass

        # Return as string
        return value


def main():
    """
    Main function for testing configuration manager
    """
    try:
        config_manager = ConfigManager()
        print(f"Configuration mode: {config_manager.mode}")
        print(
            f"FOGIS username: {config_manager.get_value('fogis.username', 'Not configured')}"
        )
        print(
            f"API client port: {config_manager.get_value('services.ports.api_client', 9086)}"
        )

    except ConfigurationError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
