#!/usr/bin/env python3
"""
Redis Deployment Extension for FOGIS

This module extends the existing FOGIS deployment system to include
Redis infrastructure for pub/sub communication.

Integrates with existing deploy_fogis.py orchestrator.

Author: System Architecture Team  
Date: 2025-09-21
Issue: Redis pub/sub integration with existing deployment
"""

import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class RedisDeploymentExtension:
    """Extension to deploy Redis infrastructure for FOGIS."""
    
    def __init__(self, project_root: Path):
        """Initialize Redis deployment extension."""
        self.project_root = Path(project_root)
    
    def deploy_redis_infrastructure(self) -> bool:
        """
        Deploy Redis infrastructure for pub/sub communication.
        
        Returns:
            bool: True if deployment successful
        """
        try:
            logger.info("🔧 Deploying Redis infrastructure for pub/sub...")
            
            # Check if Redis is already defined in docker-compose.yml
            if not self._verify_redis_in_compose():
                logger.error("❌ Redis not found in docker-compose.yml")
                logger.info("💡 Please add Redis service to docker-compose.yml")
                return False
            
            # Deploy Redis service
            if not self._start_redis_service():
                logger.error("❌ Failed to start Redis service")
                return False
            
            # Wait for Redis to be ready
            if not self._wait_for_redis_ready():
                logger.error("❌ Redis failed to become ready")
                return False
            
            # Install Redis client in services
            if not self._install_redis_clients():
                logger.warning("⚠️ Failed to install Redis clients - pub/sub may not work")
                # Don't fail deployment for this
            
            logger.info("✅ Redis infrastructure deployed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Redis deployment failed: {e}")
            return False
    
    def _verify_redis_in_compose(self) -> bool:
        """Verify Redis service is defined in docker-compose.yml."""
        try:
            compose_file = self.project_root / "docker-compose.yml"
            if not compose_file.exists():
                return False
            
            with open(compose_file, 'r') as f:
                content = f.read()
            
            # Check for Redis service definition
            if 'redis:' in content and 'image: redis' in content:
                logger.info("✅ Redis service found in docker-compose.yml")
                return True
            else:
                logger.error("❌ Redis service not found in docker-compose.yml")
                return False
                
        except Exception as e:
            logger.error(f"Failed to verify Redis in compose file: {e}")
            return False
    
    def _start_redis_service(self) -> bool:
        """Start Redis service using docker-compose."""
        try:
            logger.info("Starting Redis service...")
            
            result = subprocess.run([
                'docker-compose', 'up', '-d', 'redis'
            ], cwd=self.project_root, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("✅ Redis service started")
                return True
            else:
                logger.error(f"Failed to start Redis: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Redis startup timed out")
            return False
        except Exception as e:
            logger.error(f"Error starting Redis: {e}")
            return False
    
    def _wait_for_redis_ready(self, timeout: int = 30) -> bool:
        """Wait for Redis to be ready."""
        try:
            logger.info("Waiting for Redis to be ready...")
            
            for attempt in range(timeout):
                try:
                    result = subprocess.run([
                        'docker', 'exec', 'fogis-redis', 'redis-cli', 'ping'
                    ], capture_output=True, text=True, timeout=5)
                    
                    if result.returncode == 0 and 'PONG' in result.stdout:
                        logger.info("✅ Redis is ready")
                        return True
                        
                except subprocess.TimeoutExpired:
                    pass
                
                time.sleep(1)
            
            logger.error("❌ Redis failed to become ready within timeout")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for Redis: {e}")
            return False
    
    def _install_redis_clients(self) -> bool:
        """Install Redis Python client in services."""
        try:
            logger.info("Installing Redis clients in services...")
            
            services = [
                'process-matches-service',
                'fogis-calendar-phonebook-sync'
            ]
            
            success_count = 0
            
            for service in services:
                try:
                    logger.info(f"Installing Redis client in {service}...")
                    
                    result = subprocess.run([
                        'docker', 'exec', '-u', 'root', service,
                        'pip', 'install', 'redis'
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        logger.info(f"✅ Redis client installed in {service}")
                        success_count += 1
                    else:
                        logger.warning(f"⚠️ Failed to install Redis client in {service}: {result.stderr}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error installing Redis client in {service}: {e}")
            
            if success_count > 0:
                logger.info(f"✅ Redis clients installed in {success_count}/{len(services)} services")
                return True
            else:
                logger.error("❌ Failed to install Redis clients in any service")
                return False
                
        except Exception as e:
            logger.error(f"Error installing Redis clients: {e}")
            return False
    
    def validate_redis_deployment(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate Redis deployment and return status.
        
        Returns:
            Tuple of (success, status_dict)
        """
        try:
            logger.info("🔍 Validating Redis deployment...")
            
            status = {
                'redis_running': False,
                'redis_responsive': False,
                'pub_sub_available': False,
                'services_connected': [],
                'errors': []
            }
            
            # Check if Redis container is running
            result = subprocess.run([
                'docker', 'ps', '--filter', 'name=fogis-redis', '--format', '{{.Status}}'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and 'Up' in result.stdout:
                status['redis_running'] = True
                logger.info("✅ Redis container is running")
            else:
                status['errors'].append("Redis container not running")
                logger.error("❌ Redis container not running")
            
            # Check if Redis is responsive
            if status['redis_running']:
                result = subprocess.run([
                    'docker', 'exec', 'fogis-redis', 'redis-cli', 'ping'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0 and 'PONG' in result.stdout:
                    status['redis_responsive'] = True
                    logger.info("✅ Redis is responsive")
                else:
                    status['errors'].append("Redis not responsive")
                    logger.error("❌ Redis not responsive")
            
            # Test pub/sub functionality
            if status['redis_responsive']:
                try:
                    # Test basic pub/sub
                    test_result = subprocess.run([
                        'docker', 'exec', 'fogis-redis', 'redis-cli', 'publish', 'test', 'hello'
                    ], capture_output=True, text=True, timeout=5)
                    
                    if test_result.returncode == 0:
                        status['pub_sub_available'] = True
                        logger.info("✅ Redis pub/sub functionality available")
                    else:
                        status['errors'].append("Redis pub/sub not working")
                        logger.error("❌ Redis pub/sub not working")
                        
                except Exception as e:
                    status['errors'].append(f"Pub/sub test failed: {e}")
                    logger.error(f"❌ Pub/sub test failed: {e}")
            
            # Check service connectivity
            services = ['process-matches-service', 'fogis-calendar-phonebook-sync']
            for service in services:
                try:
                    result = subprocess.run([
                        'docker', 'exec', service, 'python', '-c',
                        'import redis; redis.from_url("redis://redis:6379").ping(); print("OK")'
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0 and 'OK' in result.stdout:
                        status['services_connected'].append(service)
                        logger.info(f"✅ {service} can connect to Redis")
                    else:
                        logger.warning(f"⚠️ {service} cannot connect to Redis")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error testing {service} Redis connection: {e}")
            
            # Overall success
            overall_success = (
                status['redis_running'] and 
                status['redis_responsive'] and 
                status['pub_sub_available']
            )
            
            if overall_success:
                logger.info("✅ Redis deployment validation successful")
            else:
                logger.error("❌ Redis deployment validation failed")
                logger.error(f"Errors: {status['errors']}")
            
            return overall_success, status
            
        except Exception as e:
            logger.error(f"❌ Redis validation error: {e}")
            return False, {'error': str(e)}

def extend_fogis_deployment_with_redis(project_root: Path) -> bool:
    """
    Main function to extend FOGIS deployment with Redis.
    
    This function can be called from the existing deploy_fogis.py
    to add Redis functionality.
    
    Args:
        project_root: Path to FOGIS project root
        
    Returns:
        bool: True if Redis deployment successful
    """
    try:
        redis_deployer = RedisDeploymentExtension(project_root)
        
        # Deploy Redis infrastructure
        if not redis_deployer.deploy_redis_infrastructure():
            logger.error("❌ Redis deployment failed")
            return False
        
        # Validate deployment
        success, status = redis_deployer.validate_redis_deployment()
        
        if success:
            logger.info("🎉 Redis pub/sub infrastructure ready!")
            logger.info("📡 Services can now use Redis for pub/sub communication")
            return True
        else:
            logger.error("❌ Redis validation failed")
            logger.error("💡 Pub/sub will fall back to HTTP communication")
            return False
            
    except Exception as e:
        logger.error(f"❌ Redis deployment extension failed: {e}")
        return False

if __name__ == "__main__":
    # Test the extension
    from pathlib import Path
    project_root = Path.cwd()
    extend_fogis_deployment_with_redis(project_root)
