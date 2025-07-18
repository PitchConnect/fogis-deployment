#!/usr/bin/env python3
"""
Configuration Validator for FOGIS Deployment
Validates fogis-config.yaml for completeness and correctness

This module provides comprehensive validation of FOGIS configuration files,
checking for required fields, valid values, port conflicts, and other
configuration issues that could prevent successful deployment.
"""

import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Exception raised for configuration validation errors"""


class ConfigValidator:
    """
    Validate configuration structure and required fields

    Provides comprehensive validation including:
    - Required sections and fields
    - FOGIS credentials validation
    - Google OAuth configuration validation
    - Port conflict detection
    - File path validation
    """

    def __init__(self, config_file: str = "fogis-config.yaml"):
        """
        Initialize configuration validator

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
            ConfigValidationError: If configuration file is invalid or missing
        """
        try:
            with open(self.config_file, "r") as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict):
                raise ConfigValidationError(
                    f"Invalid YAML configuration in {self.config_file}"
                )

            logger.debug(f"Loaded configuration from {self.config_file}")
            return config

        except FileNotFoundError:
            raise ConfigValidationError(
                f"Configuration file {self.config_file} not found"
            )
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML in {self.config_file}: {e}")

    def validate_config(self) -> Tuple[List[str], List[str]]:
        """
        Comprehensive configuration validation

        Returns:
            Tuple of (errors, warnings) lists
        """
        errors = []
        warnings = []

        # Validate required sections
        section_errors = self.validate_required_sections()
        errors.extend(section_errors)

        # Validate FOGIS credentials
        fogis_errors = self.validate_fogis_credentials()
        errors.extend(fogis_errors)

        # Validate Google OAuth configuration
        oauth_errors, oauth_warnings = self.validate_google_oauth()
        errors.extend(oauth_errors)
        warnings.extend(oauth_warnings)

        # Check for port conflicts
        port_errors = self.check_port_conflicts()
        errors.extend(port_errors)

        # Validate file paths
        path_warnings = self.validate_file_paths()
        warnings.extend(path_warnings)

        # Validate service configuration
        service_warnings = self.validate_service_configuration()
        warnings.extend(service_warnings)

        return errors, warnings

    def validate_required_sections(self) -> List[str]:
        """
        Validate that all required configuration sections are present

        Returns:
            List of error messages for missing sections
        """
        errors = []
        required_sections = ["metadata", "fogis", "google", "services", "system"]

        for section in required_sections:
            if section not in self.config:
                errors.append(f"Missing required section: {section}")

        return errors

    def validate_fogis_credentials(self) -> List[str]:
        """
        Validate FOGIS credentials completeness

        Returns:
            List of error messages for missing or invalid FOGIS credentials
        """
        errors = []

        if "fogis" not in self.config:
            errors.append("Missing FOGIS configuration section")
            return errors

        fogis_config = self.config["fogis"]
        required_fields = ["username", "password", "referee_number"]

        for field in required_fields:
            if field not in fogis_config or not fogis_config[field]:
                errors.append(f"Missing FOGIS credential: {field}")

        # Validate referee number is numeric
        if "referee_number" in fogis_config:
            try:
                referee_num = int(fogis_config["referee_number"])
                if referee_num <= 0:
                    errors.append("FOGIS referee_number must be a positive integer")
            except (ValueError, TypeError):
                errors.append("FOGIS referee_number must be a valid integer")

        return errors

    def validate_google_oauth(self) -> Tuple[List[str], List[str]]:
        """
        Validate Google OAuth configuration

        Returns:
            Tuple of (errors, warnings) for Google OAuth configuration
        """
        errors: List[str] = []
        warnings: List[str] = []

        if "google" not in self.config:
            errors.append("Missing Google configuration section")
            return errors, warnings

        google_config = self.config["google"]

        # Validate OAuth section
        if "oauth" not in google_config:
            errors.append("Missing Google OAuth configuration")
        else:
            oauth_config = google_config["oauth"]

            # Check required OAuth scopes
            required_scopes = [
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/contacts",
                "https://www.googleapis.com/auth/drive",
            ]

            actual_scopes = oauth_config.get("scopes", [])
            for scope in required_scopes:
                if scope not in actual_scopes:
                    warnings.append(f"Missing recommended OAuth scope: {scope}")

            # Validate client type
            client_type = oauth_config.get("client_type", "")
            if client_type != "web_application":
                warnings.append(
                    f"OAuth client_type should be 'web_application', found: {client_type}"
                )

        # Validate calendar configuration
        if "calendar" in google_config:
            calendar_config = google_config["calendar"]
            calendar_id = calendar_config.get("calendar_id", "")

            if calendar_id and calendar_id != "primary":
                # Validate calendar ID format (basic check)
                if not re.match(
                    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", calendar_id
                ):
                    warnings.append(f"Calendar ID format may be invalid: {calendar_id}")

        return errors, warnings

    def check_port_conflicts(self) -> List[str]:
        """
        Check for port conflicts in service configuration

        Returns:
            List of error messages for port conflicts
        """
        errors: List[str] = []

        if "services" not in self.config or "ports" not in self.config["services"]:
            return errors

        ports_config = self.config["services"]["ports"]

        # Check for duplicate ports
        seen_ports = set()
        for service, port in ports_config.items():
            if port in seen_ports:
                errors.append(
                    f"Port conflict detected: {port} is used by multiple services"
                )
            seen_ports.add(port)

        # Check for ports in reserved ranges
        for service, port in ports_config.items():
            if isinstance(port, int):
                if port < 1024:
                    # Note: This is a warning but we can't return warnings from this method
                    # So we'll treat it as an error for now
                    errors.append(
                        f"Service {service} uses privileged port {port} (< 1024)"
                    )
                elif port > 65535:
                    errors.append(
                        f"Service {service} uses invalid port {port} (> 65535)"
                    )

        return errors

    def validate_file_paths(self) -> List[str]:
        """
        Validate file paths and permissions

        Returns:
            List of warning messages for file path issues
        """
        warnings = []

        # Check for credentials.json file
        if not os.path.exists("credentials.json"):
            warnings.append(
                "Google OAuth credentials file (credentials.json) not found"
            )
        else:
            # Check file permissions
            stat_info = os.stat("credentials.json")
            if stat_info.st_mode & 0o077:
                warnings.append(
                    "credentials.json has overly permissive permissions (should be 600)"
                )

        # Check for required directories
        required_dirs = ["data", "logs", "credentials"]
        for dir_name in required_dirs:
            if not os.path.exists(dir_name):
                warnings.append(f"Required directory does not exist: {dir_name}")

        return warnings

    def validate_service_configuration(self) -> List[str]:
        """
        Validate service-specific configuration

        Returns:
            List of warning messages for service configuration issues
        """
        warnings: List[str] = []

        if "services" not in self.config:
            return warnings

        services_config = self.config["services"]

        # Validate processing configuration
        if "processing" in services_config:
            processing_config = services_config["processing"]

            # Check minimum referees value
            min_referees = processing_config.get("min_referees_for_whatsapp", 2)
            if not isinstance(min_referees, int) or min_referees < 1:
                warnings.append(
                    "min_referees_for_whatsapp should be a positive integer"
                )

            # Check cron schedule format
            schedule = processing_config.get("match_check_schedule", "")
            if schedule and not self._is_valid_cron(schedule):
                warnings.append(f"Invalid cron schedule format: {schedule}")

        # Validate logging configuration
        if "logging" in services_config:
            logging_config = services_config["logging"]

            log_level = logging_config.get("level", "INFO")
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if log_level not in valid_levels:
                warnings.append(
                    f"Invalid log level: {log_level}. Valid levels: {valid_levels}"
                )

        return warnings

    def _is_valid_cron(self, cron_expression: str) -> bool:
        """
        Basic validation of cron expression format

        Args:
            cron_expression: Cron expression to validate

        Returns:
            True if cron expression appears valid
        """
        # Basic cron validation (5 fields: minute hour day month weekday)
        parts = cron_expression.split()
        if len(parts) != 5:
            return False

        # Each part should be numeric, *, or contain valid cron characters
        cron_pattern = re.compile(r"^[\d\*\-\,\/]+$")
        return all(cron_pattern.match(part) for part in parts)

    def get_validation_summary(self, errors: List[str], warnings: List[str]) -> str:
        """
        Generate a formatted validation summary

        Args:
            errors: List of error messages
            warnings: List of warning messages

        Returns:
            Formatted validation summary string
        """
        summary = []

        if errors:
            summary.append("❌ Configuration validation failed:")
            for error in errors:
                summary.append(f"   • {error}")

        if warnings:
            summary.append("⚠️  Configuration warnings:")
            for warning in warnings:
                summary.append(f"   • {warning}")

        if not errors and not warnings:
            summary.append("✅ Configuration validation passed!")

        return "\n".join(summary)


def main():
    """
    Main function for testing configuration validator
    """
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = "fogis-config.yaml"

    if not Path(config_file).exists():
        print(f"❌ Configuration file not found: {config_file}")
        sys.exit(1)

    try:
        validator = ConfigValidator(config_file)
        errors, warnings = validator.validate_config()

        # Print validation summary
        summary = validator.get_validation_summary(errors, warnings)
        print(summary)

        # Exit with appropriate code
        if errors:
            sys.exit(1)
        else:
            sys.exit(0)

    except ConfigValidationError as e:
        print(f"❌ Configuration validation error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
