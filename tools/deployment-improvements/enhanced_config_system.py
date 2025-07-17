#!/usr/bin/env python3
"""
Enhanced Configuration System for FOGIS Services

This module provides a robust, validated configuration system that eliminates
the environment variable issues we encountered during deployment.

Key Features:
- Automatic validation of all configuration values
- Clear error messages for missing or invalid configuration
- Type conversion with proper error handling
- Configuration schema validation
- Environment-specific defaults
- Configuration export for debugging
"""

import json
import logging
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class RunMode(Enum):
    """Valid run modes for services."""

    ONESHOT = "oneshot"
    SERVICE = "service"
    DEVELOPMENT = "development"


class LogLevel(Enum):
    """Valid log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ConfigField:
    """Configuration field definition with validation."""

    name: str
    default: Any
    required: bool = False
    validator: Optional[callable] = None
    description: str = ""
    env_var: Optional[str] = None

    def __post_init__(self):
        if self.env_var is None:
            self.env_var = self.name


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""

    pass


class EnhancedConfig:
    """Enhanced configuration system with validation and clear error reporting."""

    def __init__(self, service_name: str, config_fields: List[ConfigField]):
        self.service_name = service_name
        self.config_fields = {field.name: field for field in config_fields}
        self.values: Dict[str, Any] = {}
        self._load_configuration()

    def _load_configuration(self) -> None:
        """Load and validate all configuration values."""
        errors = []

        for field_name, field in self.config_fields.items():
            try:
                value = self._load_field(field)
                self.values[field_name] = value
            except Exception as e:
                errors.append(f"{field_name}: {e}")

        if errors:
            error_msg = f"Configuration errors in {self.service_name}:\n" + "\n".join(
                f"  - {err}" for err in errors
            )
            raise ConfigurationError(error_msg)

    def _load_field(self, field: ConfigField) -> Any:
        """Load and validate a single configuration field."""
        # Get value from environment or use default
        env_value = os.environ.get(field.env_var)

        if env_value is None:
            if field.required:
                raise ValueError(
                    f"Required environment variable {field.env_var} is not set"
                )
            value = field.default
        else:
            # Convert string environment variable to appropriate type
            value = self._convert_value(env_value, field.default, field.name)

        # Validate the value
        if field.validator:
            try:
                field.validator(value)
            except Exception as e:
                raise ValueError(f"Validation failed: {e}")

        return value

    def _convert_value(
        self, env_value: str, default_value: Any, field_name: str
    ) -> Any:
        """Convert environment variable string to appropriate type."""
        if isinstance(default_value, bool):
            return env_value.lower() in ("true", "yes", "1", "on")
        elif isinstance(default_value, int):
            try:
                return int(env_value)
            except ValueError:
                raise ValueError(
                    f"Invalid integer value '{env_value}' for {field_name}"
                )
        elif isinstance(default_value, float):
            try:
                return float(env_value)
            except ValueError:
                raise ValueError(f"Invalid float value '{env_value}' for {field_name}")
        elif isinstance(default_value, list):
            # Support comma-separated lists
            return [item.strip() for item in env_value.split(",") if item.strip()]
        elif isinstance(default_value, Enum):
            # Handle enum types
            try:
                return type(default_value)(env_value.lower())
            except ValueError:
                valid_values = [e.value for e in type(default_value)]
                raise ValueError(
                    f"Invalid value '{env_value}' for {field_name}. Valid values: {valid_values}"
                )
        else:
            return env_value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.values.get(key, default)

    def export_config(self) -> Dict[str, Any]:
        """Export configuration for debugging (excluding sensitive values)."""
        sensitive_keys = {"password", "secret", "key", "token"}

        result = {}
        for key, value in self.values.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                result[key] = "***REDACTED***"
            else:
                result[key] = value

        return result

    def validate_startup(self) -> List[str]:
        """Validate configuration for startup and return any warnings."""
        warnings = []

        # Check for common configuration issues
        if self.get("RUN_MODE") == RunMode.SERVICE:
            if not self.get("HEALTH_SERVER_PORT"):
                warnings.append("Health server port not configured for service mode")

            if self.get("HEALTH_SERVER_HOST") == "127.0.0.1":
                warnings.append(
                    "Health server bound to localhost - may not be accessible in containers"
                )

        return warnings


# Validation functions
def validate_port(port: int) -> None:
    """Validate port number."""
    if not (1 <= port <= 65535):
        raise ValueError(f"Port must be between 1 and 65535, got {port}")


def validate_cron_schedule(schedule: str) -> None:
    """Validate cron schedule format."""
    try:
        from croniter import croniter

        croniter(schedule)
    except Exception as e:
        raise ValueError(f"Invalid cron schedule: {e}")


def validate_url(url: str) -> None:
    """Validate URL format."""
    if url and not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("URL must start with http:// or https://")


# Example configuration for match-list-change-detector
MATCH_LIST_CHANGE_DETECTOR_CONFIG = [
    ConfigField("RUN_MODE", RunMode.ONESHOT, description="Service run mode"),
    ConfigField(
        "CRON_SCHEDULE",
        "0 * * * *",
        validator=validate_cron_schedule,
        description="Cron schedule for periodic execution",
    ),
    ConfigField(
        "HEALTH_SERVER_PORT",
        8000,
        validator=validate_port,
        description="Port for health check server",
    ),
    ConfigField(
        "HEALTH_SERVER_HOST", "0.0.0.0", description="Host for health check server"
    ),
    ConfigField(
        "WEBHOOK_URL",
        "",
        validator=validate_url,
        description="Webhook URL for notifications",
    ),
    ConfigField("LOG_LEVEL", LogLevel.INFO, description="Logging level"),
    ConfigField("FOGIS_USERNAME", "", required=True, description="FOGIS username"),
    ConfigField("FOGIS_PASSWORD", "", required=True, description="FOGIS password"),
]


def create_match_list_detector_config() -> EnhancedConfig:
    """Create configuration for match list change detector."""
    return EnhancedConfig(
        "match-list-change-detector", MATCH_LIST_CHANGE_DETECTOR_CONFIG
    )


if __name__ == "__main__":
    # Example usage
    try:
        config = create_match_list_detector_config()
        print("✅ Configuration loaded successfully!")
        print(f"Run mode: {config.get('RUN_MODE').value}")
        print(
            f"Health server: {config.get('HEALTH_SERVER_HOST')}:{config.get('HEALTH_SERVER_PORT')}"
        )

        warnings = config.validate_startup()
        if warnings:
            print("\n⚠️  Configuration warnings:")
            for warning in warnings:
                print(f"  - {warning}")

        print(f"\n📋 Configuration export:")
        print(json.dumps(config.export_config(), indent=2, default=str))

    except ConfigurationError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
