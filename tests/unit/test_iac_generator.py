#!/usr/bin/env python3
"""
Unit tests for IaCGenerator
Tests Infrastructure as Code template generation
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add the lib directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))

from iac_generator import IaCGenerator, IaCGeneratorError  # noqa: E402


class TestIaCGenerator(unittest.TestCase):
    """Test cases for IaCGenerator class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create test config file
        self.config_content = """
metadata:
  version: "2.0"
  created_at: "2025-01-01T00:00:00"

fogis:
  username: "test_user"
  password: "test_password"
  referee_number: 12345

services:
  ports:
    calendar_sync: 8080
    google_drive: 8081
    match_list_processor: 8082

google:
  oauth:
    client_type: "web_application"
  calendar:
    calendar_id: "primary"
"""

        with open("test-config.yaml", "w") as f:
            f.write(self.config_content)

        self.generator = IaCGenerator("test-config.yaml")

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        import shutil

        shutil.rmtree(self.test_dir)

    def test_load_config_success(self):
        """Test successful config loading"""
        config = self.generator._load_config()
        self.assertIn("fogis", config)
        self.assertIn("services", config)
        self.assertEqual(config["fogis"]["username"], "test_user")

    def test_load_config_missing_file(self):
        """Test loading non-existent config file"""
        with self.assertRaises(IaCGeneratorError):
            IaCGenerator("nonexistent.yaml")

    def test_generate_terraform_templates(self):
        """Test Terraform template generation"""
        files = self.generator.generate_terraform_templates()

        self.assertEqual(len(files), 4)

        # Check that all expected files are generated
        expected_files = [
            "main.tf",
            "variables.tf",
            "outputs.tf",
            "terraform.tfvars.example",
        ]
        for expected_file in expected_files:
            self.assertTrue(any(expected_file in f for f in files))

        # Verify files exist
        for file_path in files:
            self.assertTrue(os.path.exists(file_path))

    def test_generate_ansible_templates(self):
        """Test Ansible template generation"""
        files = self.generator.generate_ansible_templates()

        self.assertEqual(len(files), 3)

        # Check that all expected files are generated
        expected_files = ["playbook.yml", "inventory.yml", "all.yml"]
        for expected_file in expected_files:
            self.assertTrue(any(expected_file in f for f in files))

        # Verify files exist
        for file_path in files:
            self.assertTrue(os.path.exists(file_path))

    def test_generate_kubernetes_templates(self):
        """Test Kubernetes template generation"""
        files = self.generator.generate_kubernetes_templates()

        self.assertEqual(len(files), 5)

        # Check that all expected files are generated
        expected_files = [
            "namespace.yaml",
            "configmap.yaml",
            "secrets.yaml",
            "deployments.yaml",
            "services.yaml",
        ]
        for expected_file in expected_files:
            self.assertTrue(any(expected_file in f for f in files))

        # Verify files exist
        for file_path in files:
            self.assertTrue(os.path.exists(file_path))

    def test_generate_all_templates(self):
        """Test generating all templates"""
        results = self.generator.generate_all_templates()

        self.assertIn("terraform", results)
        self.assertIn("ansible", results)
        self.assertIn("kubernetes", results)

        # Verify each platform has files
        self.assertGreater(len(results["terraform"]), 0)
        self.assertGreater(len(results["ansible"]), 0)
        self.assertGreater(len(results["kubernetes"]), 0)

    def test_terraform_main_content(self):
        """Test Terraform main.tf content"""
        files = self.generator.generate_terraform_templates()
        main_tf_file = next(f for f in files if "main.tf" in f)

        with open(main_tf_file, "r") as f:
            content = f.read()

        # Check for key Terraform resources
        self.assertIn('resource "aws_vpc"', content)
        self.assertIn('resource "aws_instance"', content)
        self.assertIn('resource "aws_security_group"', content)

        # Check for port configuration
        self.assertIn("8080", content)  # calendar_sync port
        self.assertIn("8081", content)  # google_drive port

    def test_terraform_variables_content(self):
        """Test Terraform variables.tf content"""
        files = self.generator.generate_terraform_templates()
        variables_tf_file = next(f for f in files if "variables.tf" in f)

        with open(variables_tf_file, "r") as f:
            content = f.read()

        # Check for key variables
        self.assertIn('variable "aws_region"', content)
        self.assertIn('variable "instance_type"', content)
        self.assertIn('variable "key_pair_name"', content)

    def test_ansible_playbook_content(self):
        """Test Ansible playbook content"""
        files = self.generator.generate_ansible_templates()
        playbook_file = next(f for f in files if "playbook.yml" in f)

        with open(playbook_file, "r") as f:
            content = f.read()

        # Check for key Ansible tasks
        self.assertIn("Install Docker", content)
        self.assertIn("Start FOGIS services", content)
        self.assertIn("docker compose up -d", content)

    def test_ansible_inventory_content(self):
        """Test Ansible inventory content"""
        files = self.generator.generate_ansible_templates()
        inventory_file = next(f for f in files if "inventory.yml" in f)

        with open(inventory_file, "r") as f:
            content = f.read()

        # Check for inventory structure
        self.assertIn("fogis_servers:", content)
        self.assertIn("ansible_host:", content)
        self.assertIn("ansible_user:", content)

    def test_kubernetes_namespace_content(self):
        """Test Kubernetes namespace content"""
        files = self.generator.generate_kubernetes_templates()
        namespace_file = next(f for f in files if "namespace.yaml" in f)

        with open(namespace_file, "r") as f:
            content = f.read()

        # Check for namespace definition
        self.assertIn("kind: Namespace", content)
        self.assertIn("name: fogis", content)

    def test_kubernetes_configmap_content(self):
        """Test Kubernetes ConfigMap content"""
        files = self.generator.generate_kubernetes_templates()
        configmap_file = next(f for f in files if "configmap.yaml" in f)

        with open(configmap_file, "r") as f:
            content = f.read()

        # Check for ConfigMap definition
        self.assertIn("kind: ConfigMap", content)
        self.assertIn("FOGIS_USERNAME:", content)
        self.assertIn("USER_REFEREE_NUMBER:", content)

    def test_kubernetes_deployments_content(self):
        """Test Kubernetes deployments content"""
        files = self.generator.generate_kubernetes_templates()
        deployments_file = next(f for f in files if "deployments.yaml" in f)

        with open(deployments_file, "r") as f:
            content = f.read()

        # Check for deployment definitions
        self.assertIn("kind: Deployment", content)
        self.assertIn("fogis-calendar-sync", content)
        self.assertIn("fogis-google-drive", content)
        self.assertIn("ghcr.io/pitchconnect/", content)

    def test_kubernetes_services_content(self):
        """Test Kubernetes services content"""
        files = self.generator.generate_kubernetes_templates()
        services_file = next(f for f in files if "services.yaml" in f)

        with open(services_file, "r") as f:
            content = f.read()

        # Check for service definitions
        self.assertIn("kind: Service", content)
        self.assertIn("fogis-calendar-sync-service", content)
        self.assertIn("fogis-google-drive-service", content)

    def test_templates_directory_creation(self):
        """Test that templates directory is created"""
        # Generator should create templates/iac directory
        templates_dir = Path("templates/iac")
        self.assertTrue(templates_dir.exists())
        self.assertTrue(templates_dir.is_dir())

    def test_platform_specific_directories(self):
        """Test that platform-specific directories are created"""
        self.generator.generate_all_templates()

        terraform_dir = Path("templates/iac/terraform")
        ansible_dir = Path("templates/iac/ansible")
        kubernetes_dir = Path("templates/iac/kubernetes")

        self.assertTrue(terraform_dir.exists())
        self.assertTrue(ansible_dir.exists())
        self.assertTrue(kubernetes_dir.exists())

    def test_config_values_in_templates(self):
        """Test that config values are properly substituted in templates"""
        files = self.generator.generate_terraform_templates()
        main_tf_file = next(f for f in files if "main.tf" in f)

        with open(main_tf_file, "r") as f:
            content = f.read()

        # Check that port values from config are used
        self.assertIn("8080", content)  # calendar_sync port
        self.assertIn("8081", content)  # google_drive port

    @patch("iac_generator.yaml.safe_load")
    def test_config_loading_error(self, mock_yaml):
        """Test config loading error handling"""
        mock_yaml.side_effect = Exception("YAML error")

        with self.assertRaises(IaCGeneratorError):
            IaCGenerator("test-config.yaml")


if __name__ == "__main__":
    unittest.main()
