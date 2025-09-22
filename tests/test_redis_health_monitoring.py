#!/usr/bin/env python3
"""
Tests for Redis Health Monitoring

This module tests the Redis health monitoring functionality
for the FOGIS deployment system.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis health monitoring testing
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Add deployment-improvements to path
sys.path.append(str(Path(__file__).parent.parent / "deployment-improvements"))

from redis_health_monitoring import (
    RedisHealthMonitor,
    HealthStatus,
    HealthCheckResult,
    RedisPerformanceMetrics,
    check_redis_health,
    is_redis_healthy
)

class TestHealthStatus(unittest.TestCase):
    """Test HealthStatus enumeration."""
    
    def test_health_status_values(self):
        """Test health status enumeration values."""
        self.assertEqual(HealthStatus.HEALTHY.value, "healthy")
        self.assertEqual(HealthStatus.DEGRADED.value, "degraded")
        self.assertEqual(HealthStatus.UNHEALTHY.value, "unhealthy")
        self.assertEqual(HealthStatus.UNKNOWN.value, "unknown")

class TestHealthCheckResult(unittest.TestCase):
    """Test HealthCheckResult dataclass."""
    
    def test_health_check_result_creation(self):
        """Test health check result creation."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Test successful",
            timestamp=datetime.now(),
            response_time_ms=50.0
        )
        
        self.assertEqual(result.status, HealthStatus.HEALTHY)
        self.assertEqual(result.message, "Test successful")
        self.assertEqual(result.response_time_ms, 50.0)
        self.assertEqual(result.details, {})
        self.assertEqual(result.errors, [])
    
    def test_health_check_result_with_errors(self):
        """Test health check result with errors."""
        result = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            message="Test failed",
            timestamp=datetime.now(),
            errors=["Error 1", "Error 2"]
        )
        
        self.assertEqual(result.status, HealthStatus.UNHEALTHY)
        self.assertEqual(result.errors, ["Error 1", "Error 2"])

class TestRedisPerformanceMetrics(unittest.TestCase):
    """Test RedisPerformanceMetrics dataclass."""
    
    def test_performance_metrics_creation(self):
        """Test performance metrics creation."""
        metrics = RedisPerformanceMetrics(
            connected_clients=5,
            used_memory_mb=128.5,
            total_commands_processed=1000,
            instantaneous_ops_per_sec=50,
            keyspace_hits=800,
            keyspace_misses=200,
            uptime_seconds=3600,
            hit_rate_percentage=80.0
        )
        
        self.assertEqual(metrics.connected_clients, 5)
        self.assertEqual(metrics.used_memory_mb, 128.5)
        self.assertEqual(metrics.total_commands_processed, 1000)
        self.assertEqual(metrics.hit_rate_percentage, 80.0)

class TestRedisHealthMonitor(unittest.TestCase):
    """Test Redis health monitor."""
    
    def setUp(self):
        """Set up test environment."""
        self.monitor = RedisHealthMonitor(container_name="test-redis", timeout=5)
    
    def test_initialization(self):
        """Test monitor initialization."""
        self.assertEqual(self.monitor.container_name, "test-redis")
        self.assertEqual(self.monitor.timeout, 5)
    
    @patch('subprocess.run')
    def test_check_redis_connectivity_success(self, mock_run):
        """Test successful Redis connectivity check."""
        # Mock successful ping
        mock_run.return_value = Mock(returncode=0, stdout="PONG\n", stderr="")
        
        result = self.monitor.check_redis_connectivity()
        
        self.assertEqual(result.status, HealthStatus.HEALTHY)
        self.assertEqual(result.message, "Redis connectivity successful")
        self.assertIsNotNone(result.response_time_ms)
        self.assertEqual(result.details["ping_response"], "PONG")
    
    @patch('subprocess.run')
    def test_check_redis_connectivity_failure(self, mock_run):
        """Test failed Redis connectivity check."""
        # Mock failed ping
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Connection refused")
        
        result = self.monitor.check_redis_connectivity()
        
        self.assertEqual(result.status, HealthStatus.UNHEALTHY)
        self.assertEqual(result.message, "Redis ping failed")
        self.assertIn("Connection refused", result.errors)
    
    @patch('subprocess.run')
    def test_check_redis_connectivity_timeout(self, mock_run):
        """Test Redis connectivity check timeout."""
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("docker", 5)
        
        result = self.monitor.check_redis_connectivity()
        
        self.assertEqual(result.status, HealthStatus.UNHEALTHY)
        self.assertIn("timeout", result.message.lower())
        self.assertIn("Connection timeout", result.errors)
    
    @patch('subprocess.run')
    def test_check_pubsub_functionality_success(self, mock_run):
        """Test successful pub/sub functionality check."""
        # Mock successful publish
        mock_run.return_value = Mock(returncode=0, stdout="0\n", stderr="")
        
        result = self.monitor.check_pubsub_functionality()
        
        self.assertEqual(result.status, HealthStatus.HEALTHY)
        self.assertEqual(result.message, "Redis pub/sub functionality operational")
        self.assertIn("test_channel", result.details)
        self.assertEqual(result.details["subscribers_notified"], 0)
    
    @patch('subprocess.run')
    def test_check_pubsub_functionality_failure(self, mock_run):
        """Test failed pub/sub functionality check."""
        # Mock failed publish
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Command failed")
        
        result = self.monitor.check_pubsub_functionality()
        
        self.assertEqual(result.status, HealthStatus.UNHEALTHY)
        self.assertEqual(result.message, "Redis pub/sub test failed")
        self.assertIn("Command failed", result.errors)
    
    @patch('subprocess.run')
    def test_monitor_redis_performance_success(self, mock_run):
        """Test successful Redis performance monitoring."""
        # Mock Redis INFO output
        mock_info = """# Clients
connected_clients:5

# Memory
used_memory:134217728

# Stats
total_commands_processed:1000
instantaneous_ops_per_sec:50
keyspace_hits:800
keyspace_misses:200

# Server
uptime_in_seconds:3600
redis_version:7.0.0
redis_mode:standalone
"""
        mock_run.return_value = Mock(returncode=0, stdout=mock_info, stderr="")
        
        result = self.monitor.monitor_redis_performance()
        
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["metrics"]["connected_clients"], 5)
        self.assertEqual(result["metrics"]["used_memory_mb"], 128.0)
        self.assertEqual(result["metrics"]["total_commands_processed"], 1000)
        self.assertEqual(result["metrics"]["hit_rate_percentage"], 80.0)
        self.assertEqual(result["redis_version"], "7.0.0")
    
    @patch('subprocess.run')
    def test_monitor_redis_performance_high_memory_warning(self, mock_run):
        """Test Redis performance monitoring with high memory warning."""
        # Mock Redis INFO with high memory usage
        mock_info = """# Memory
used_memory:268435456

# Stats
total_commands_processed:1000
keyspace_hits:800
keyspace_misses:200

# Server
uptime_in_seconds:3600
connected_clients:5
instantaneous_ops_per_sec:50
"""
        mock_run.return_value = Mock(returncode=0, stdout=mock_info, stderr="")
        
        result = self.monitor.monitor_redis_performance()
        
        self.assertEqual(result["status"], "warning")
        self.assertIn("High memory usage", result["warnings"][0])
    
    @patch('subprocess.run')
    def test_monitor_redis_performance_failure(self, mock_run):
        """Test failed Redis performance monitoring."""
        # Mock failed INFO command
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Connection failed")
        
        result = self.monitor.monitor_redis_performance()
        
        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to get Redis INFO", result["message"])
    
    @patch('subprocess.run')
    def test_validate_redis_persistence_enabled(self, mock_run):
        """Test Redis persistence validation when enabled."""
        # Mock AOF enabled
        mock_run.return_value = Mock(returncode=0, stdout="appendonly\nyes\n", stderr="")
        
        result = self.monitor.validate_redis_persistence()
        
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_validate_redis_persistence_disabled(self, mock_run):
        """Test Redis persistence validation when disabled."""
        # Mock AOF disabled
        mock_run.return_value = Mock(returncode=0, stdout="appendonly\nno\n", stderr="")
        
        result = self.monitor.validate_redis_persistence()
        
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_validate_redis_persistence_failure(self, mock_run):
        """Test Redis persistence validation failure."""
        # Mock command failure
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Connection failed")
        
        result = self.monitor.validate_redis_persistence()
        
        self.assertFalse(result)
    
    @patch.object(RedisHealthMonitor, 'check_redis_connectivity')
    @patch.object(RedisHealthMonitor, 'check_pubsub_functionality')
    @patch.object(RedisHealthMonitor, 'monitor_redis_performance')
    @patch.object(RedisHealthMonitor, 'validate_redis_persistence')
    def test_get_comprehensive_health_status_healthy(self, mock_persistence, mock_performance, 
                                                   mock_pubsub, mock_connectivity):
        """Test comprehensive health status when all checks pass."""
        # Mock all checks as healthy
        mock_connectivity.return_value = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Connectivity OK",
            timestamp=datetime.now(),
            response_time_ms=10.0
        )
        
        mock_pubsub.return_value = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Pub/sub OK",
            timestamp=datetime.now(),
            response_time_ms=15.0
        )
        
        mock_performance.return_value = {"status": "healthy", "metrics": {}}
        mock_persistence.return_value = True
        
        result = self.monitor.get_comprehensive_health_status()
        
        self.assertEqual(result["overall_status"], "healthy")
        self.assertEqual(result["summary"]["connectivity"], "healthy")
        self.assertEqual(result["summary"]["pubsub"], "healthy")
        self.assertEqual(result["summary"]["performance"], "healthy")
        self.assertEqual(result["summary"]["persistence"], "enabled")
    
    @patch.object(RedisHealthMonitor, 'check_redis_connectivity')
    @patch.object(RedisHealthMonitor, 'check_pubsub_functionality')
    @patch.object(RedisHealthMonitor, 'monitor_redis_performance')
    @patch.object(RedisHealthMonitor, 'validate_redis_persistence')
    def test_get_comprehensive_health_status_unhealthy(self, mock_persistence, mock_performance,
                                                     mock_pubsub, mock_connectivity):
        """Test comprehensive health status when connectivity fails."""
        # Mock connectivity as unhealthy
        mock_connectivity.return_value = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            message="Connection failed",
            timestamp=datetime.now(),
            errors=["Connection refused"]
        )
        
        mock_pubsub.return_value = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Pub/sub OK",
            timestamp=datetime.now()
        )
        
        mock_performance.return_value = {"status": "healthy"}
        mock_persistence.return_value = True
        
        result = self.monitor.get_comprehensive_health_status()
        
        self.assertEqual(result["overall_status"], "unhealthy")
        self.assertEqual(result["summary"]["connectivity"], "unhealthy")

class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""
    
    @patch('redis_health_monitoring.RedisHealthMonitor')
    def test_check_redis_health(self, mock_monitor_class):
        """Test check_redis_health convenience function."""
        # Mock health status
        mock_monitor = Mock()
        mock_health_status = {"overall_status": "healthy", "summary": {}}
        mock_monitor.get_comprehensive_health_status.return_value = mock_health_status
        mock_monitor_class.return_value = mock_monitor
        
        result = check_redis_health("test-redis")
        
        self.assertEqual(result, mock_health_status)
        mock_monitor_class.assert_called_once_with("test-redis")
        mock_monitor.get_comprehensive_health_status.assert_called_once()
    
    @patch('redis_health_monitoring.RedisHealthMonitor')
    def test_is_redis_healthy_true(self, mock_monitor_class):
        """Test is_redis_healthy convenience function when healthy."""
        # Mock healthy connectivity
        mock_monitor = Mock()
        mock_connectivity = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="OK",
            timestamp=datetime.now()
        )
        mock_monitor.check_redis_connectivity.return_value = mock_connectivity
        mock_monitor_class.return_value = mock_monitor
        
        result = is_redis_healthy("test-redis")
        
        self.assertTrue(result)
    
    @patch('redis_health_monitoring.RedisHealthMonitor')
    def test_is_redis_healthy_false(self, mock_monitor_class):
        """Test is_redis_healthy convenience function when unhealthy."""
        # Mock unhealthy connectivity
        mock_monitor = Mock()
        mock_connectivity = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            message="Failed",
            timestamp=datetime.now()
        )
        mock_monitor.check_redis_connectivity.return_value = mock_connectivity
        mock_monitor_class.return_value = mock_monitor
        
        result = is_redis_healthy("test-redis")
        
        self.assertFalse(result)

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
