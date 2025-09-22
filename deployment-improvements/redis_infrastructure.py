#!/usr/bin/env python3
"""
Redis Infrastructure Management for FOGIS Deployment

This module provides Redis infrastructure deployment and management functionality
for the FOGIS deployment system. It focuses on infrastructure orchestration,
deployment automation, and basic connectivity validation.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis pub/sub infrastructure integration
"""

import logging
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class RedisDeploymentConfig:
    """Configuration for Redis deployment."""
    container_name: str = "fogis-redis"
    image: str = "redis:7-alpine"
    port: int = 6379
    max_memory: str = "256mb"
    memory_policy: str = "allkeys-lru"
    persistence_enabled: bool = True
    health_check_timeout: int = 30
    deployment_timeout: int = 60

@dataclass
class RedisDeploymentResult:
    """Result of Redis deployment operation."""
    success: bool
    message: str
    container_id: Optional[str] = None
    deployment_time: Optional[datetime] = None
    health_status: Optional[str] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class RedisInfrastructureManager:
    """Manages Redis infrastructure deployment and validation for FOGIS."""
    
    def __init__(self, config: RedisDeploymentConfig = None, project_root: Path = None):
        """
        Initialize Redis infrastructure manager.
        
        Args:
            config: Redis deployment configuration
            project_root: Path to project root directory
        """
        self.config = config or RedisDeploymentConfig()
        self.project_root = project_root or Path.cwd()
        self.compose_file = self.project_root / "docker-compose.yml"
        
        logger.info(f"🔧 Redis Infrastructure Manager initialized")
        logger.info(f"   Project root: {self.project_root}")
        logger.info(f"   Container: {self.config.container_name}")
        logger.info(f"   Image: {self.config.image}")
    
    def deploy_redis_service(self) -> RedisDeploymentResult:
        """
        Deploy Redis service via docker-compose.
        
        Returns:
            RedisDeploymentResult: Deployment result with status and details
        """
        start_time = datetime.now()
        
        try:
            logger.info("🚀 Starting Redis service deployment...")
            
            # Validate docker-compose.yml exists
            if not self.compose_file.exists():
                return RedisDeploymentResult(
                    success=False,
                    message=f"docker-compose.yml not found at {self.compose_file}",
                    deployment_time=start_time,
                    errors=["Missing docker-compose.yml file"]
                )
            
            # Check if Redis service is defined in docker-compose.yml
            if not self._validate_redis_service_definition():
                return RedisDeploymentResult(
                    success=False,
                    message="Redis service not defined in docker-compose.yml",
                    deployment_time=start_time,
                    errors=["Redis service definition missing"]
                )
            
            # Deploy Redis service
            logger.info("📦 Deploying Redis container...")
            deploy_result = subprocess.run([
                "docker-compose", "up", "-d", "redis"
            ], cwd=self.project_root, capture_output=True, text=True, timeout=self.config.deployment_timeout)
            
            if deploy_result.returncode != 0:
                error_msg = f"Redis deployment failed: {deploy_result.stderr}"
                logger.error(error_msg)
                return RedisDeploymentResult(
                    success=False,
                    message=error_msg,
                    deployment_time=start_time,
                    errors=[deploy_result.stderr]
                )
            
            # Get container ID
            container_id = self._get_container_id()
            
            # Wait for Redis to be healthy
            logger.info("⏳ Waiting for Redis to be healthy...")
            health_status = self._wait_for_redis_health()
            
            if health_status == "healthy":
                logger.info("✅ Redis service deployed successfully")
                return RedisDeploymentResult(
                    success=True,
                    message="Redis service deployed and healthy",
                    container_id=container_id,
                    deployment_time=start_time,
                    health_status=health_status
                )
            else:
                logger.warning("⚠️ Redis deployed but health check failed")
                return RedisDeploymentResult(
                    success=False,
                    message=f"Redis deployed but not healthy: {health_status}",
                    container_id=container_id,
                    deployment_time=start_time,
                    health_status=health_status,
                    errors=[f"Health check failed: {health_status}"]
                )
                
        except subprocess.TimeoutExpired:
            error_msg = f"Redis deployment timeout after {self.config.deployment_timeout} seconds"
            logger.error(error_msg)
            return RedisDeploymentResult(
                success=False,
                message=error_msg,
                deployment_time=start_time,
                errors=["Deployment timeout"]
            )
        except Exception as e:
            error_msg = f"Redis deployment failed with exception: {e}"
            logger.error(error_msg)
            return RedisDeploymentResult(
                success=False,
                message=error_msg,
                deployment_time=start_time,
                errors=[str(e)]
            )
    
    def validate_redis_deployment(self) -> bool:
        """
        Validate Redis deployment and basic functionality.
        
        Returns:
            bool: True if Redis is deployed and functional
        """
        try:
            logger.info("🔍 Validating Redis deployment...")
            
            # Check if container is running
            if not self._is_container_running():
                logger.error("❌ Redis container is not running")
                return False
            
            # Test Redis connectivity
            if not self._test_redis_connectivity():
                logger.error("❌ Redis connectivity test failed")
                return False
            
            # Test Redis basic operations
            if not self._test_redis_operations():
                logger.error("❌ Redis operations test failed")
                return False
            
            logger.info("✅ Redis deployment validation successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Redis deployment validation failed: {e}")
            return False
    
    def configure_redis_persistence(self) -> bool:
        """
        Configure Redis persistence settings.
        
        Returns:
            bool: True if persistence configuration successful
        """
        try:
            if not self.config.persistence_enabled:
                logger.info("📋 Redis persistence disabled by configuration")
                return True
            
            logger.info("💾 Configuring Redis persistence...")
            
            # Verify AOF is enabled (configured in docker-compose.yml)
            result = subprocess.run([
                "docker", "exec", self.config.container_name,
                "redis-cli", "CONFIG", "GET", "appendonly"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and "yes" in result.stdout:
                logger.info("✅ Redis AOF persistence is enabled")
                return True
            else:
                logger.warning("⚠️ Redis AOF persistence not enabled")
                return False
                
        except Exception as e:
            logger.error(f"❌ Redis persistence configuration failed: {e}")
            return False
    
    def get_redis_info(self) -> Dict[str, Any]:
        """
        Get Redis server information and statistics.
        
        Returns:
            Dict[str, Any]: Redis server information
        """
        try:
            result = subprocess.run([
                "docker", "exec", self.config.container_name,
                "redis-cli", "INFO"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Parse Redis INFO output
                info = {}
                for line in result.stdout.split('\n'):
                    if ':' in line and not line.startswith('#'):
                        key, value = line.split(':', 1)
                        info[key.strip()] = value.strip()
                
                return {
                    "status": "available",
                    "version": info.get("redis_version", "unknown"),
                    "mode": info.get("redis_mode", "unknown"),
                    "uptime_seconds": info.get("uptime_in_seconds", "0"),
                    "connected_clients": info.get("connected_clients", "0"),
                    "used_memory": info.get("used_memory_human", "0"),
                    "total_commands_processed": info.get("total_commands_processed", "0")
                }
            else:
                return {"status": "unavailable", "error": result.stderr}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _validate_redis_service_definition(self) -> bool:
        """Validate that Redis service is defined in docker-compose.yml."""
        try:
            with open(self.compose_file, 'r') as f:
                content = f.read()
                return 'redis:' in content and 'image: redis:' in content
        except Exception:
            return False
    
    def _get_container_id(self) -> Optional[str]:
        """Get Redis container ID."""
        try:
            result = subprocess.run([
                "docker", "ps", "-q", "-f", f"name={self.config.container_name}"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return None
        except Exception:
            return None
    
    def _wait_for_redis_health(self) -> str:
        """Wait for Redis to be healthy."""
        for attempt in range(self.config.health_check_timeout):
            try:
                result = subprocess.run([
                    "docker", "exec", self.config.container_name,
                    "redis-cli", "ping"
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0 and "PONG" in result.stdout:
                    return "healthy"
                
                time.sleep(1)
                
            except Exception:
                time.sleep(1)
                continue
        
        return "unhealthy"
    
    def _is_container_running(self) -> bool:
        """Check if Redis container is running."""
        try:
            result = subprocess.run([
                "docker", "ps", "-f", f"name={self.config.container_name}", "--format", "{{.Status}}"
            ], capture_output=True, text=True, timeout=10)
            
            return result.returncode == 0 and "Up" in result.stdout
        except Exception:
            return False
    
    def _test_redis_connectivity(self) -> bool:
        """Test basic Redis connectivity."""
        try:
            result = subprocess.run([
                "docker", "exec", self.config.container_name,
                "redis-cli", "ping"
            ], capture_output=True, text=True, timeout=10)
            
            return result.returncode == 0 and "PONG" in result.stdout
        except Exception:
            return False
    
    def _test_redis_operations(self) -> bool:
        """Test basic Redis operations."""
        try:
            # Test SET operation
            set_result = subprocess.run([
                "docker", "exec", self.config.container_name,
                "redis-cli", "SET", "fogis:test", "deployment_test"
            ], capture_output=True, text=True, timeout=10)
            
            if set_result.returncode != 0:
                return False
            
            # Test GET operation
            get_result = subprocess.run([
                "docker", "exec", self.config.container_name,
                "redis-cli", "GET", "fogis:test"
            ], capture_output=True, text=True, timeout=10)
            
            if get_result.returncode != 0 or "deployment_test" not in get_result.stdout:
                return False
            
            # Clean up test key
            subprocess.run([
                "docker", "exec", self.config.container_name,
                "redis-cli", "DEL", "fogis:test"
            ], capture_output=True, text=True, timeout=10)
            
            return True
            
        except Exception:
            return False

# Convenience functions for external use
def deploy_redis_infrastructure(project_root: Path = None) -> bool:
    """
    Deploy Redis infrastructure for FOGIS.
    
    Args:
        project_root: Path to project root directory
        
    Returns:
        bool: True if deployment successful
    """
    manager = RedisInfrastructureManager(project_root=project_root)
    result = manager.deploy_redis_service()
    
    if result.success:
        # Configure persistence
        manager.configure_redis_persistence()
        return True
    
    return False

def validate_redis_infrastructure(project_root: Path = None) -> bool:
    """
    Validate Redis infrastructure deployment.
    
    Args:
        project_root: Path to project root directory
        
    Returns:
        bool: True if validation successful
    """
    manager = RedisInfrastructureManager(project_root=project_root)
    return manager.validate_redis_deployment()

if __name__ == "__main__":
    # Test Redis infrastructure deployment
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🧪 Testing Redis infrastructure deployment...")
    
    # Deploy Redis
    if deploy_redis_infrastructure():
        logger.info("✅ Redis infrastructure deployment test successful")
        
        # Validate deployment
        if validate_redis_infrastructure():
            logger.info("✅ Redis infrastructure validation test successful")
        else:
            logger.error("❌ Redis infrastructure validation test failed")
    else:
        logger.error("❌ Redis infrastructure deployment test failed")
