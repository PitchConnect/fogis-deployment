#!/usr/bin/env python3
"""
Unit tests for MonitoringSetup
Tests monitoring and health check functionality
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the lib directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))

from monitoring_setup import MonitoringError, MonitoringSetup  # noqa: E402


class TestMonitoringSetup(unittest.TestCase):
    """Test cases for MonitoringSetup class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create test config file
        self.config_content = """
metadata:
  version: "2.0"

services:
  ports:
    calendar_sync: 8080
    google_drive: 8081
    match_list_processor: 8082
"""

        with open("test-config.yaml", "w") as f:
            f.write(self.config_content)

        self.monitoring = MonitoringSetup("test-config.yaml")

    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        import shutil

        shutil.rmtree(self.test_dir)

    def test_load_config_success(self):
        """Test successful config loading"""
        config = self.monitoring._load_config()
        self.assertIn("services", config)
        self.assertEqual(config["services"]["ports"]["calendar_sync"], 8080)

    def test_load_config_missing_file(self):
        """Test loading non-existent config file"""
        monitoring = MonitoringSetup("nonexistent.yaml")
        config = monitoring._load_config()
        self.assertEqual(config, {})

    def test_get_service_endpoints(self):
        """Test service endpoint generation"""
        endpoints = self.monitoring._get_service_endpoints()

        self.assertIn("calendar_sync", endpoints)
        self.assertIn("google_drive", endpoints)
        self.assertEqual(endpoints["calendar_sync"], "http://localhost:8080/health")
        self.assertEqual(endpoints["google_drive"], "http://localhost:8081/health")

    @patch("monitoring_setup.requests.get")
    def test_check_service_health_success(self, mock_get):
        """Test successful service health check"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_get.return_value = mock_response

        results = self.monitoring._check_service_health()

        self.assertIn("calendar_sync", results)
        self.assertEqual(results["calendar_sync"]["status"], "healthy")
        self.assertEqual(results["calendar_sync"]["status_code"], 200)

    @patch("monitoring_setup.requests.get")
    def test_check_service_health_connection_error(self, mock_get):
        """Test service health check with connection error"""
        # Mock connection error
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError()

        results = self.monitoring._check_service_health()

        self.assertIn("calendar_sync", results)
        self.assertEqual(results["calendar_sync"]["status"], "down")
        self.assertEqual(results["calendar_sync"]["error"], "Connection refused")

    @patch("monitoring_setup.requests.get")
    def test_check_service_health_timeout(self, mock_get):
        """Test service health check with timeout"""
        # Mock timeout
        import requests

        mock_get.side_effect = requests.exceptions.Timeout()

        results = self.monitoring._check_service_health()

        self.assertIn("calendar_sync", results)
        self.assertEqual(results["calendar_sync"]["status"], "timeout")
        self.assertEqual(results["calendar_sync"]["error"], "Request timeout")

    @patch("monitoring_setup.psutil.cpu_percent")
    @patch("monitoring_setup.psutil.virtual_memory")
    @patch("monitoring_setup.psutil.disk_usage")
    def test_check_system_health(self, mock_disk, mock_memory, mock_cpu):
        """Test system health check"""
        # Mock system metrics
        mock_cpu.return_value = 50.0

        mock_memory_obj = MagicMock()
        mock_memory_obj.percent = 60.0
        mock_memory_obj.total = 8 * 1024**3  # 8GB
        mock_memory_obj.available = 3 * 1024**3  # 3GB
        mock_memory.return_value = mock_memory_obj

        mock_disk_obj = MagicMock()
        mock_disk_obj.total = 100 * 1024**3  # 100GB
        mock_disk_obj.used = 50 * 1024**3  # 50GB
        mock_disk_obj.free = 50 * 1024**3  # 50GB
        mock_disk.return_value = mock_disk_obj

        results = self.monitoring._check_system_health()

        self.assertIn("cpu", results)
        self.assertIn("memory", results)
        self.assertIn("disk", results)

        self.assertEqual(results["cpu"]["usage_percent"], 50.0)
        self.assertEqual(results["memory"]["usage_percent"], 60.0)
        self.assertEqual(results["disk"]["usage_percent"], 50.0)

    @patch("monitoring_setup.subprocess.run")
    def test_check_docker_health_success(self, mock_run):
        """Test successful Docker health check"""
        # Mock successful docker info
        mock_info_result = MagicMock()
        mock_info_result.returncode = 0
        mock_info_result.stdout = '{"ServerVersion": "20.10.0"}'

        # Mock successful docker ps
        mock_ps_result = MagicMock()
        mock_ps_result.returncode = 0
        mock_ps_result.stdout = '{"Names": "test-container", "Image": "test-image", "Status": "Up", "Ports": "8080:8080"}\n'

        mock_run.side_effect = [mock_info_result, mock_ps_result, mock_ps_result]

        results = self.monitoring._check_docker_health()

        self.assertEqual(results["status"], "healthy")
        self.assertTrue(results["daemon_running"])
        self.assertIn("containers", results)

    @patch("monitoring_setup.subprocess.run")
    def test_check_docker_health_daemon_error(self, mock_run):
        """Test Docker health check with daemon error"""
        # Mock failed docker info
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        results = self.monitoring._check_docker_health()

        self.assertEqual(results["status"], "error")
        self.assertEqual(results["error"], "Docker daemon not accessible")

    def test_determine_overall_status_healthy(self):
        """Test determining overall status when healthy"""
        health_report = {
            "docker": {"status": "healthy"},
            "services": {
                "service1": {"status": "healthy"},
                "service2": {"status": "healthy"},
            },
            "system": {
                "cpu": {"status": "healthy"},
                "memory": {"status": "healthy"},
                "disk": {"status": "healthy"},
            },
        }

        status = self.monitoring._determine_overall_status(health_report)
        self.assertEqual(status, "healthy")

    def test_determine_overall_status_critical(self):
        """Test determining overall status when critical"""
        health_report = {"docker": {"status": "error"}, "services": {}, "system": {}}

        status = self.monitoring._determine_overall_status(health_report)
        self.assertEqual(status, "critical")

    def test_determine_overall_status_degraded(self):
        """Test determining overall status when degraded"""
        health_report = {
            "docker": {"status": "healthy"},
            "services": {
                "service1": {"status": "down"},
                "service2": {"status": "healthy"},
            },
            "system": {
                "cpu": {"status": "healthy"},
                "memory": {"status": "healthy"},
                "disk": {"status": "healthy"},
            },
        }

        status = self.monitoring._determine_overall_status(health_report)
        self.assertEqual(status, "degraded")

    def test_save_health_report(self):
        """Test saving health report"""
        health_report = {
            "timestamp": "2025-01-01T00:00:00",
            "overall_status": "healthy",
            "services": {},
            "system": {},
            "docker": {},
        }

        self.monitoring._save_health_report(health_report)

        # Check that monitoring directory was created
        monitoring_dir = Path("monitoring")
        self.assertTrue(monitoring_dir.exists())

        # Check that latest report exists
        latest_file = monitoring_dir / "health-report-latest.json"
        self.assertTrue(latest_file.exists())

        # Verify content
        with open(latest_file, "r") as f:
            saved_report = json.load(f)

        self.assertEqual(saved_report["overall_status"], "healthy")

    @patch("monitoring_setup.requests.get")
    def test_collect_performance_metrics(self, mock_get):
        """Test collecting performance metrics"""
        # Mock service response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with patch("monitoring_setup.psutil.cpu_percent", return_value=50.0), patch(
            "monitoring_setup.psutil.virtual_memory"
        ) as mock_memory, patch("monitoring_setup.psutil.disk_usage") as mock_disk:
            mock_memory.return_value.percent = 60.0
            mock_disk.return_value.used = 50 * 1024**3
            mock_disk.return_value.total = 100 * 1024**3

            metrics = self.monitoring._collect_performance_metrics()

        self.assertIn("timestamp", metrics)
        self.assertIn("system", metrics)
        self.assertIn("services", metrics)
        self.assertEqual(metrics["system"]["cpu_percent"], 50.0)

    def test_calculate_trend_increasing(self):
        """Test trend calculation for increasing values"""
        values = [10, 20, 30, 40, 50]
        trend = self.monitoring._calculate_trend(values)

        self.assertEqual(trend["direction"], "increasing")
        self.assertGreater(trend["rate"], 0)
        self.assertEqual(trend["current"], 50)

    def test_calculate_trend_decreasing(self):
        """Test trend calculation for decreasing values"""
        values = [50, 40, 30, 20, 10]
        trend = self.monitoring._calculate_trend(values)

        self.assertEqual(trend["direction"], "decreasing")
        self.assertLess(trend["rate"], 0)
        self.assertEqual(trend["current"], 10)

    def test_calculate_trend_stable(self):
        """Test trend calculation for stable values"""
        values = [25, 24, 26, 25, 25]
        trend = self.monitoring._calculate_trend(values)

        self.assertEqual(trend["direction"], "stable")
        self.assertEqual(trend["current"], 25)

    def test_generate_performance_recommendations_high_cpu(self):
        """Test performance recommendations for high CPU"""
        current_metrics = {
            "system": {"cpu_percent": 85, "memory_percent": 50, "disk_percent": 50}
        }
        trends = {}

        recommendations = self.monitoring._generate_performance_recommendations(
            current_metrics, trends
        )

        self.assertTrue(any("CPU usage" in rec for rec in recommendations))

    def test_generate_performance_recommendations_high_memory(self):
        """Test performance recommendations for high memory"""
        current_metrics = {
            "system": {"cpu_percent": 50, "memory_percent": 90, "disk_percent": 50}
        }
        trends = {}

        recommendations = self.monitoring._generate_performance_recommendations(
            current_metrics, trends
        )

        self.assertTrue(any("memory usage" in rec for rec in recommendations))

    def test_monitoring_directory_creation(self):
        """Test that monitoring directory is created"""
        monitoring_dir = Path("monitoring")
        self.assertTrue(monitoring_dir.exists())
        self.assertTrue(monitoring_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
