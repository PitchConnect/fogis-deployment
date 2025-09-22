#!/usr/bin/env python3
"""
Tests for Redis Infrastructure Management

This module tests the Redis infrastructure deployment and management
functionality for the FOGIS deployment system.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis infrastructure testing
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess
import sys

# Add deployment-improvements to path
sys.path.append(str(Path(__file__).parent.parent / "deployment-improvements"))

from redis_infrastructure import (
    RedisInfrastructureManager,
    RedisDeploymentConfig,
    RedisDeploymentResult,
    deploy_redis_infrastructure,
    validate_redis_infrastructure
)

class TestRedisDeploymentConfig(unittest.TestCase):
    """Test Redis deployment configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RedisDeploymentConfig()
        
        self.assertEqual(config.container_name, "fogis-redis")
        self.assertEqual(config.image, "redis:7-alpine")
        self.assertEqual(config.port, 6379)
        self.assertEqual(config.max_memory, "256mb")
        self.assertEqual(config.memory_policy, "allkeys-lru")
        self.assertTrue(config.persistence_enabled)
        self.assertEqual(config.health_check_timeout, 30)
        self.assertEqual(config.deployment_timeout, 60)
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = RedisDeploymentConfig(
            container_name="test-redis",
            image="redis:6-alpine",
            port=6380,
            max_memory="512mb",
            persistence_enabled=False
        )
        
        self.assertEqual(config.container_name, "test-redis")
        self.assertEqual(config.image, "redis:6-alpine")
        self.assertEqual(config.port, 6380)
        self.assertEqual(config.max_memory, "512mb")
        self.assertFalse(config.persistence_enabled)

class TestRedisDeploymentResult(unittest.TestCase):
    """Test Redis deployment result."""
    
    def test_successful_result(self):
        """Test successful deployment result."""
        result = RedisDeploymentResult(
            success=True,
            message="Deployment successful",
            container_id="abc123"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Deployment successful")
        self.assertEqual(result.container_id, "abc123")
        self.assertEqual(result.errors, [])
    
    def test_failed_result_with_errors(self):
        """Test failed deployment result with errors."""
        result = RedisDeploymentResult(
            success=False,
            message="Deployment failed",
            errors=["Error 1", "Error 2"]
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.message, "Deployment failed")
        self.assertEqual(result.errors, ["Error 1", "Error 2"])

class TestRedisInfrastructureManager(unittest.TestCase):
    """Test Redis infrastructure manager."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.compose_file = self.temp_dir / "docker-compose.yml"
        
        # Create a mock docker-compose.yml with Redis service
        self.compose_file.write_text("""
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    container_name: fogis-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - fogis-network
    command: redis-server --appendonly yes
volumes:
  redis-data:
networks:
  fogis-network:
""")
        
        self.manager = RedisInfrastructureManager(project_root=self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test manager initialization."""
        self.assertEqual(self.manager.project_root, self.temp_dir)
        self.assertEqual(self.manager.compose_file, self.compose_file)
        self.assertEqual(self.manager.config.container_name, "fogis-redis")
    
    def test_validate_redis_service_definition(self):
        """Test Redis service definition validation."""
        # Should pass with our mock compose file
        self.assertTrue(self.manager._validate_redis_service_definition())
        
        # Should fail with missing compose file
        self.compose_file.unlink()
        self.assertFalse(self.manager._validate_redis_service_definition())
    
    @patch('subprocess.run')
    def test_deploy_redis_service_success(self, mock_run):
        """Test successful Redis service deployment."""
        # Mock successful docker-compose up
        mock_run.return_value = Mock(returncode=0, stderr="", stdout="")
        
        # Mock container ID retrieval
        with patch.object(self.manager, '_get_container_id', return_value="abc123"):
            # Mock health check
            with patch.object(self.manager, '_wait_for_redis_health', return_value="healthy"):
                result = self.manager.deploy_redis_service()
        
        self.assertTrue(result.success)
        self.assertEqual(result.container_id, "abc123")
        self.assertEqual(result.health_status, "healthy")
        
        # Verify docker-compose was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("docker-compose", args)
        self.assertIn("up", args)
        self.assertIn("-d", args)
        self.assertIn("redis", args)
    
    @patch('subprocess.run')
    def test_deploy_redis_service_failure(self, mock_run):
        """Test failed Redis service deployment."""
        # Mock failed docker-compose up
        mock_run.return_value = Mock(returncode=1, stderr="Deployment failed", stdout="")
        
        result = self.manager.deploy_redis_service()
        
        self.assertFalse(result.success)
        self.assertIn("Deployment failed", result.message)
        self.assertIn("Deployment failed", result.errors)
    
    @patch('subprocess.run')
    def test_deploy_redis_service_timeout(self, mock_run):
        """Test Redis service deployment timeout."""
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired("docker-compose", 60)
        
        result = self.manager.deploy_redis_service()
        
        self.assertFalse(result.success)
        self.assertIn("timeout", result.message.lower())
        self.assertIn("Deployment timeout", result.errors)
    
    @patch('subprocess.run')
    def test_validate_redis_deployment_success(self, mock_run):
        """Test successful Redis deployment validation."""
        # Mock container running check
        mock_run.side_effect = [
            Mock(returncode=0, stdout="Up 5 minutes"),  # Container status
            Mock(returncode=0, stdout="PONG"),          # Redis ping
            Mock(returncode=0, stdout="OK"),            # Redis SET
            Mock(returncode=0, stdout="deployment_test"),    # Redis GET
            Mock(returncode=0, stdout="1")              # Redis DEL
        ]
        
        result = self.manager.validate_redis_deployment()
        
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_validate_redis_deployment_failure(self, mock_run):
        """Test failed Redis deployment validation."""
        # Mock container not running
        mock_run.return_value = Mock(returncode=0, stdout="")
        
        result = self.manager.validate_redis_deployment()
        
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_configure_redis_persistence_enabled(self, mock_run):
        """Test Redis persistence configuration when enabled."""
        # Mock AOF enabled
        mock_run.return_value = Mock(returncode=0, stdout="appendonly\nyes")
        
        result = self.manager.configure_redis_persistence()
        
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_configure_redis_persistence_disabled(self, mock_run):
        """Test Redis persistence configuration when disabled."""
        config = RedisDeploymentConfig(persistence_enabled=False)
        manager = RedisInfrastructureManager(config=config, project_root=self.temp_dir)
        
        result = manager.configure_redis_persistence()
        
        self.assertTrue(result)  # Should return True when disabled by config
    
    @patch('subprocess.run')
    def test_get_redis_info_success(self, mock_run):
        """Test getting Redis server information."""
        # Mock Redis INFO output
        mock_info = """# Server
redis_version:7.0.0
redis_mode:standalone
uptime_in_seconds:3600
connected_clients:2
used_memory_human:1.5M
total_commands_processed:1000
"""
        mock_run.return_value = Mock(returncode=0, stdout=mock_info)
        
        info = self.manager.get_redis_info()
        
        self.assertEqual(info["status"], "available")
        self.assertEqual(info["version"], "7.0.0")
        self.assertEqual(info["mode"], "standalone")
        self.assertEqual(info["uptime_seconds"], "3600")
        self.assertEqual(info["connected_clients"], "2")
    
    @patch('subprocess.run')
    def test_get_redis_info_failure(self, mock_run):
        """Test getting Redis server information failure."""
        mock_run.return_value = Mock(returncode=1, stderr="Connection failed")
        
        info = self.manager.get_redis_info()
        
        self.assertEqual(info["status"], "unavailable")
        self.assertIn("Connection failed", info["error"])

class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.compose_file = self.temp_dir / "docker-compose.yml"
        
        # Create a mock docker-compose.yml
        self.compose_file.write_text("""
version: '3.8'
services:
  redis:
    image: redis:7-alpine
""")
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    @patch('redis_infrastructure.RedisInfrastructureManager')
    def test_deploy_redis_infrastructure_success(self, mock_manager_class):
        """Test deploy_redis_infrastructure convenience function success."""
        # Mock successful deployment
        mock_manager = Mock()
        mock_result = Mock(success=True)
        mock_manager.deploy_redis_service.return_value = mock_result
        mock_manager.configure_redis_persistence.return_value = True
        mock_manager_class.return_value = mock_manager
        
        result = deploy_redis_infrastructure(self.temp_dir)
        
        self.assertTrue(result)
        mock_manager.deploy_redis_service.assert_called_once()
        mock_manager.configure_redis_persistence.assert_called_once()
    
    @patch('redis_infrastructure.RedisInfrastructureManager')
    def test_deploy_redis_infrastructure_failure(self, mock_manager_class):
        """Test deploy_redis_infrastructure convenience function failure."""
        # Mock failed deployment
        mock_manager = Mock()
        mock_result = Mock(success=False)
        mock_manager.deploy_redis_service.return_value = mock_result
        mock_manager_class.return_value = mock_manager
        
        result = deploy_redis_infrastructure(self.temp_dir)
        
        self.assertFalse(result)
        mock_manager.deploy_redis_service.assert_called_once()
    
    @patch('redis_infrastructure.RedisInfrastructureManager')
    def test_validate_redis_infrastructure_success(self, mock_manager_class):
        """Test validate_redis_infrastructure convenience function success."""
        # Mock successful validation
        mock_manager = Mock()
        mock_manager.validate_redis_deployment.return_value = True
        mock_manager_class.return_value = mock_manager
        
        result = validate_redis_infrastructure(self.temp_dir)
        
        self.assertTrue(result)
        mock_manager.validate_redis_deployment.assert_called_once()
    
    @patch('redis_infrastructure.RedisInfrastructureManager')
    def test_validate_redis_infrastructure_failure(self, mock_manager_class):
        """Test validate_redis_infrastructure convenience function failure."""
        # Mock failed validation
        mock_manager = Mock()
        mock_manager.validate_redis_deployment.return_value = False
        mock_manager_class.return_value = mock_manager
        
        result = validate_redis_infrastructure(self.temp_dir)
        
        self.assertFalse(result)
        mock_manager.validate_redis_deployment.assert_called_once()

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
