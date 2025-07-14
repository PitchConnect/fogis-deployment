#!/usr/bin/env python3
"""
Unit tests for ConfigManager
Tests configuration mode detection, loading, and hierarchy
"""

import os

# Add the lib directory to the path
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))

from config_manager import ConfigManager, ConfigurationError


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Sample YAML configuration
        self.sample_yaml_config = {
            "metadata": {"version": "2.0"},
            "fogis": {
                "username": "test_user",
                "password": "test_pass",
                "referee_number": 12345,
            },
            "google": {
                "oauth": {"scopes": ["calendar", "contacts", "drive"]},
                "calendar": {"calendar_id": "primary"},
            },
            "services": {
                "ports": {"api_client": 9086, "match_processor": 9082},
                "logging": {"level": "INFO", "debug_mode": False},
            },
        }

        # Sample .env content
        self.sample_env_content = """
FOGIS_USERNAME=env_user
FOGIS_PASSWORD=env_pass
USER_REFEREE_NUMBER=54321
LOG_LEVEL=DEBUG
API_CLIENT_PORT=8086
"""

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        import shutil

        shutil.rmtree(self.test_dir)

    def test_detect_mode_portable(self):
        """Test detection of portable configuration mode"""
        # Create fogis-config.yaml
        with open("fogis-config.yaml", "w") as f:
            yaml.dump(self.sample_yaml_config, f)

        config_manager = ConfigManager()
        self.assertEqual(config_manager.mode, "portable")

    def test_detect_mode_legacy(self):
        """Test detection of legacy configuration mode"""
        # Create .env file
        with open(".env", "w") as f:
            f.write(self.sample_env_content)

        config_manager = ConfigManager()
        self.assertEqual(config_manager.mode, "legacy")

    def test_detect_mode_new_installation(self):
        """Test detection of new installation mode"""
        config_manager = ConfigManager()
        self.assertEqual(config_manager.mode, "new_installation")

    def test_load_yaml_config(self):
        """Test loading YAML configuration"""
        # Create fogis-config.yaml
        with open("fogis-config.yaml", "w") as f:
            yaml.dump(self.sample_yaml_config, f)

        config_manager = ConfigManager()
        self.assertEqual(config_manager.config["fogis"]["username"], "test_user")
        self.assertEqual(config_manager.config["fogis"]["referee_number"], 12345)

    def test_load_yaml_config_invalid_file(self):
        """Test loading invalid YAML configuration"""
        # Create invalid YAML file
        with open("fogis-config.yaml", "w") as f:
            f.write("invalid: yaml: content: [")

        with self.assertRaises(ConfigurationError):
            ConfigManager()

    @patch.dict(
        os.environ,
        {
            "FOGIS_USERNAME": "env_user",
            "FOGIS_PASSWORD": "env_pass",
            "USER_REFEREE_NUMBER": "54321",
            "LOG_LEVEL": "DEBUG",
        },
    )
    def test_load_legacy_config(self):
        """Test loading legacy configuration from environment"""
        # Create .env file
        with open(".env", "w") as f:
            f.write(self.sample_env_content)

        config_manager = ConfigManager()
        self.assertEqual(config_manager.mode, "legacy")
        self.assertEqual(config_manager.config["fogis"]["username"], "env_user")
        self.assertEqual(config_manager.config["fogis"]["referee_number"], 54321)

    def test_get_value_hierarchy(self):
        """Test configuration value hierarchy (env > yaml > default)"""
        # Create YAML config
        with open("fogis-config.yaml", "w") as f:
            yaml.dump(self.sample_yaml_config, f)

        with patch.dict(os.environ, {"FOGIS_USERNAME": "env_override"}):
            config_manager = ConfigManager()

            # Environment variable should override YAML
            self.assertEqual(config_manager.get_value("FOGIS_USERNAME"), "env_override")

            # YAML value should be used when no env override
            self.assertEqual(config_manager.get_value("fogis.username"), "test_user")

            # Default value should be used when neither exists
            self.assertEqual(
                config_manager.get_value("nonexistent.key", "default"), "default"
            )

    def test_get_nested_value(self):
        """Test getting nested configuration values"""
        with open("fogis-config.yaml", "w") as f:
            yaml.dump(self.sample_yaml_config, f)

        config_manager = ConfigManager()

        # Test nested value access
        self.assertEqual(
            config_manager._get_nested_value(config_manager.config, "fogis.username"),
            "test_user",
        )
        self.assertEqual(
            config_manager._get_nested_value(
                config_manager.config, "services.ports.api_client"
            ),
            9086,
        )

        # Test non-existent nested value
        self.assertIsNone(
            config_manager._get_nested_value(config_manager.config, "nonexistent.key")
        )

    def test_convert_env_value(self):
        """Test environment value type conversion"""
        config_manager = ConfigManager()

        # Test boolean conversion
        self.assertTrue(config_manager._convert_env_value("true"))
        self.assertTrue(config_manager._convert_env_value("1"))
        self.assertFalse(config_manager._convert_env_value("false"))
        self.assertFalse(config_manager._convert_env_value("0"))

        # Test integer conversion
        self.assertEqual(config_manager._convert_env_value("123"), 123)

        # Test string passthrough
        self.assertEqual(
            config_manager._convert_env_value("test_string"), "test_string"
        )


if __name__ == "__main__":
    unittest.main()
