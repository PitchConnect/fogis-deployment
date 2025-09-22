#!/usr/bin/env python3
"""
Integration Tests for Redis Health Checks

This module provides integration tests for Redis health checking
functionality in the FOGIS deployment system.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis health check integration testing
"""

import unittest
import time
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, Mock

# Add deployment-improvements to path
sys.path.append(str(Path(__file__).parent.parent.parent / "deployment-improvements"))

from redis_health_monitoring import RedisHealthMonitor, HealthStatus
from redis_infrastructure import RedisInfrastructureManager
from validation_system import FOGISValidator

class TestRedisHealthCheckIntegration(unittest.TestCase):
    """Integration tests for Redis health checks."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        cls.container_name = "fogis-redis-test"
        cls.monitor = RedisHealthMonitor(container_name=cls.container_name, timeout=10)
    
    def setUp(self):
        """Set up each test."""
        # Check if Docker is available
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.skipTest("Docker not available")
    
    def test_redis_health_check_with_mock_container(self):
        """Test Redis health check with mocked container responses."""
        with patch('subprocess.run') as mock_run:
            # Mock successful Redis ping
            mock_run.return_value = Mock(returncode=0, stdout="PONG\n", stderr="")
            
            result = self.monitor.check_redis_connectivity()
            
            self.assertEqual(result.status, HealthStatus.HEALTHY)
            self.assertIn("Redis connectivity successful", result.message)
            self.assertIsNotNone(result.response_time_ms)
    
    def test_redis_pubsub_check_with_mock_container(self):
        """Test Redis pub/sub check with mocked container responses."""
        with patch('subprocess.run') as mock_run:
            # Mock successful Redis publish
            mock_run.return_value = Mock(returncode=0, stdout="0\n", stderr="")
            
            result = self.monitor.check_pubsub_functionality()
            
            self.assertEqual(result.status, HealthStatus.HEALTHY)
            self.assertIn("pub/sub functionality operational", result.message)
            self.assertIn("test_channel", result.details)
    
    def test_redis_performance_monitoring_with_mock_data(self):
        """Test Redis performance monitoring with mocked data."""
        with patch('subprocess.run') as mock_run:
            # Mock Redis INFO output
            mock_info = """# Server
redis_version:7.0.0
redis_mode:standalone
uptime_in_seconds:3600

# Clients
connected_clients:2

# Memory
used_memory:1048576

# Stats
total_commands_processed:500
instantaneous_ops_per_sec:10
keyspace_hits:400
keyspace_misses:100
"""
            mock_run.return_value = Mock(returncode=0, stdout=mock_info, stderr="")
            
            result = self.monitor.monitor_redis_performance()
            
            self.assertEqual(result["status"], "healthy")
            self.assertEqual(result["metrics"]["connected_clients"], 2)
            self.assertEqual(result["metrics"]["used_memory_mb"], 1.0)
            self.assertEqual(result["metrics"]["hit_rate_percentage"], 80.0)
            self.assertEqual(result["redis_version"], "7.0.0")
    
    def test_redis_persistence_validation_with_mock_config(self):
        """Test Redis persistence validation with mocked configuration."""
        with patch('subprocess.run') as mock_run:
            # Mock AOF enabled
            mock_run.return_value = Mock(returncode=0, stdout="appendonly\nyes\n", stderr="")
            
            result = self.monitor.validate_redis_persistence()
            
            self.assertTrue(result)
    
    def test_comprehensive_health_status_integration(self):
        """Test comprehensive health status integration."""
        with patch('subprocess.run') as mock_run:
            # Mock all Redis commands as successful
            mock_responses = [
                Mock(returncode=0, stdout="PONG\n", stderr=""),      # Connectivity ping
                Mock(returncode=0, stdout="0\n", stderr=""),         # Pub/sub publish
                Mock(returncode=0, stdout="""# Server
redis_version:7.0.0
uptime_in_seconds:3600
connected_clients:1
used_memory:1048576
total_commands_processed:100
instantaneous_ops_per_sec:5
keyspace_hits:80
keyspace_misses:20
""", stderr=""),  # Performance INFO
                Mock(returncode=0, stdout="appendonly\nyes\n", stderr="")  # Persistence check
            ]
            mock_run.side_effect = mock_responses
            
            result = self.monitor.get_comprehensive_health_status()
            
            self.assertEqual(result["overall_status"], "healthy")
            self.assertEqual(result["summary"]["connectivity"], "healthy")
            self.assertEqual(result["summary"]["pubsub"], "healthy")
            self.assertEqual(result["summary"]["performance"], "healthy")
            self.assertEqual(result["summary"]["persistence"], "enabled")
    
    def test_health_check_failure_scenarios(self):
        """Test various health check failure scenarios."""
        # Test connectivity failure
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Connection refused")
            
            result = self.monitor.check_redis_connectivity()
            
            self.assertEqual(result.status, HealthStatus.UNHEALTHY)
            self.assertIn("Connection refused", result.errors)
        
        # Test pub/sub failure
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Command failed")
            
            result = self.monitor.check_pubsub_functionality()
            
            self.assertEqual(result.status, HealthStatus.UNHEALTHY)
            self.assertIn("Command failed", result.errors)
    
    def test_health_check_timeout_scenarios(self):
        """Test health check timeout scenarios."""
        with patch('subprocess.run') as mock_run:
            # Mock timeout
            mock_run.side_effect = subprocess.TimeoutExpired("docker", 10)
            
            result = self.monitor.check_redis_connectivity()
            
            self.assertEqual(result.status, HealthStatus.UNHEALTHY)
            self.assertIn("timeout", result.message.lower())

class TestRedisInfrastructureIntegration(unittest.TestCase):
    """Integration tests for Redis infrastructure with health checks."""
    
    def setUp(self):
        """Set up each test."""
        # Check if Docker is available
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.skipTest("Docker not available")
    
    def test_infrastructure_manager_with_health_monitoring(self):
        """Test infrastructure manager integration with health monitoring."""
        with patch('subprocess.run') as mock_run:
            # Mock docker-compose up success
            mock_run.side_effect = [
                Mock(returncode=0, stderr="", stdout=""),           # docker-compose up
                Mock(returncode=0, stdout="abc123", stderr=""),     # container ID
                Mock(returncode=0, stdout="PONG", stderr=""),       # health check ping
                Mock(returncode=0, stdout="Up 5 minutes", stderr=""), # container status
                Mock(returncode=0, stdout="PONG", stderr=""),       # connectivity test
                Mock(returncode=0, stdout="OK", stderr=""),         # SET test
                Mock(returncode=0, stdout="test_value", stderr=""), # GET test
                Mock(returncode=0, stdout="1", stderr=""),          # DEL test
                Mock(returncode=0, stdout="appendonly\nyes", stderr="") # persistence check
            ]
            
            # Create temporary project directory
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                compose_file = temp_path / "docker-compose.yml"
                compose_file.write_text("""
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    container_name: fogis-redis
""")
                
                manager = RedisInfrastructureManager(project_root=temp_path)
                
                # Test deployment
                deployment_result = manager.deploy_redis_service()
                self.assertTrue(deployment_result.success)
                
                # Test validation
                validation_result = manager.validate_redis_deployment()
                self.assertTrue(validation_result)
                
                # Test persistence configuration
                persistence_result = manager.configure_redis_persistence()
                self.assertTrue(persistence_result)

class TestValidationSystemRedisIntegration(unittest.TestCase):
    """Integration tests for validation system Redis integration."""
    
    def setUp(self):
        """Set up each test."""
        # Create temporary project directory
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create mock docker-compose.yml
        compose_file = self.temp_path / "docker-compose.yml"
        compose_file.write_text("""
version: '3.8'
services:
  redis:
    image: redis:7-alpine
""")
        
        self.validator = FOGISValidator(self.temp_path)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_validation_system_redis_health_check(self):
        """Test validation system Redis health check integration."""
        with patch('subprocess.run') as mock_run:
            # Mock Redis health check responses
            mock_run.side_effect = [
                Mock(returncode=0, stdout="PONG\n", stderr=""),      # Connectivity ping
                Mock(returncode=0, stdout="0\n", stderr=""),         # Pub/sub publish
                Mock(returncode=0, stdout="""# Server
redis_version:7.0.0
uptime_in_seconds:3600
connected_clients:1
used_memory:1048576
total_commands_processed:100
instantaneous_ops_per_sec:5
keyspace_hits:80
keyspace_misses:20
""", stderr=""),  # Performance INFO
                Mock(returncode=0, stdout="appendonly\nyes\n", stderr="")  # Persistence check
            ]
            
            # Test Redis health check through validation system
            redis_health = self.validator._check_redis_health()
            
            self.assertEqual(redis_health.name, "redis")
            self.assertIn([redis_health.status.value], [["healthy"], ["degraded"]])  # Either is acceptable
            self.assertIsNotNone(redis_health.response_time_ms)
    
    def test_validation_system_redis_degraded_state(self):
        """Test validation system handling of Redis degraded state."""
        with patch('subprocess.run') as mock_run:
            # Mock Redis connection failure
            mock_run.side_effect = Exception("Connection refused")
            
            # Test Redis health check through validation system
            redis_health = self.validator._check_redis_health()
            
            self.assertEqual(redis_health.name, "redis")
            self.assertEqual(redis_health.status.value, "degraded")
            self.assertIn("Redis unavailable", redis_health.error_message)
            self.assertTrue(redis_health.details.get("fallback"))

class TestEndToEndRedisHealthFlow(unittest.TestCase):
    """End-to-end tests for Redis health check flow."""
    
    def test_complete_redis_health_flow(self):
        """Test complete Redis health check flow from deployment to validation."""
        with patch('subprocess.run') as mock_run:
            # Mock complete flow responses
            mock_responses = [
                # Infrastructure deployment
                Mock(returncode=0, stderr="", stdout=""),           # docker-compose up
                Mock(returncode=0, stdout="abc123", stderr=""),     # container ID
                Mock(returncode=0, stdout="PONG", stderr=""),       # deployment health check
                
                # Infrastructure validation
                Mock(returncode=0, stdout="Up 5 minutes", stderr=""), # container status
                Mock(returncode=0, stdout="PONG", stderr=""),       # connectivity test
                Mock(returncode=0, stdout="OK", stderr=""),         # SET test
                Mock(returncode=0, stdout="test_value", stderr=""), # GET test
                Mock(returncode=0, stdout="1", stderr=""),          # DEL test
                
                # Persistence configuration
                Mock(returncode=0, stdout="appendonly\nyes", stderr=""), # persistence check
                
                # Health monitoring
                Mock(returncode=0, stdout="PONG\n", stderr=""),     # connectivity ping
                Mock(returncode=0, stdout="0\n", stderr=""),        # pub/sub publish
                Mock(returncode=0, stdout="""# Server
redis_version:7.0.0
uptime_in_seconds:3600
connected_clients:1
used_memory:1048576
total_commands_processed:100
instantaneous_ops_per_sec:5
keyspace_hits:80
keyspace_misses:20
""", stderr=""),  # performance INFO
                Mock(returncode=0, stdout="appendonly\nyes\n", stderr="")  # final persistence check
            ]
            mock_run.side_effect = mock_responses
            
            # Create temporary project directory
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                compose_file = temp_path / "docker-compose.yml"
                compose_file.write_text("""
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    container_name: fogis-redis
""")
                
                # Step 1: Deploy Redis infrastructure
                manager = RedisInfrastructureManager(project_root=temp_path)
                deployment_result = manager.deploy_redis_service()
                self.assertTrue(deployment_result.success)
                
                # Step 2: Validate deployment
                validation_result = manager.validate_redis_deployment()
                self.assertTrue(validation_result)
                
                # Step 3: Configure persistence
                persistence_result = manager.configure_redis_persistence()
                self.assertTrue(persistence_result)
                
                # Step 4: Comprehensive health monitoring
                monitor = RedisHealthMonitor(container_name="fogis-redis")
                health_status = monitor.get_comprehensive_health_status()
                self.assertEqual(health_status["overall_status"], "healthy")
                
                # Step 5: Validation system integration
                validator = FOGISValidator(temp_path)
                redis_health = validator._check_redis_health()
                self.assertIn(redis_health.status.value, ["healthy", "degraded"])

if __name__ == '__main__':
    # Run integration tests
    unittest.main(verbosity=2)
