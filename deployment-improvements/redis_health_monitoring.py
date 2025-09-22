#!/usr/bin/env python3
"""
Redis Health Monitoring for FOGIS Deployment

This module provides comprehensive Redis health monitoring functionality
for the FOGIS deployment system. It includes connectivity checks, performance
monitoring, and pub/sub functionality validation.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis pub/sub health monitoring
"""

import logging
import subprocess
import time
import json
from typing import Dict, Any, Optional, List, NamedTuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    status: HealthStatus
    message: str
    timestamp: datetime
    details: Dict[str, Any] = None
    response_time_ms: Optional[float] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.errors is None:
            self.errors = []

@dataclass
class RedisPerformanceMetrics:
    """Redis performance metrics."""
    connected_clients: int
    used_memory_mb: float
    total_commands_processed: int
    instantaneous_ops_per_sec: int
    keyspace_hits: int
    keyspace_misses: int
    uptime_seconds: int
    hit_rate_percentage: float

class RedisHealthMonitor:
    """Comprehensive Redis health monitoring for FOGIS."""
    
    def __init__(self, container_name: str = "fogis-redis", timeout: int = 10):
        """
        Initialize Redis health monitor.
        
        Args:
            container_name: Name of Redis container
            timeout: Timeout for health check operations
        """
        self.container_name = container_name
        self.timeout = timeout
        
        logger.info(f"🏥 Redis Health Monitor initialized for container: {container_name}")
    
    def check_redis_connectivity(self) -> HealthCheckResult:
        """
        Test Redis connection and basic operations.
        
        Returns:
            HealthCheckResult: Connectivity check result
        """
        start_time = time.time()
        
        try:
            logger.debug("🔍 Checking Redis connectivity...")
            
            # Test basic ping
            ping_result = subprocess.run([
                "docker", "exec", self.container_name,
                "redis-cli", "ping"
            ], capture_output=True, text=True, timeout=self.timeout)
            
            response_time = (time.time() - start_time) * 1000
            
            if ping_result.returncode == 0 and "PONG" in ping_result.stdout:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message="Redis connectivity successful",
                    timestamp=datetime.now(),
                    response_time_ms=response_time,
                    details={"ping_response": ping_result.stdout.strip()}
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message="Redis ping failed",
                    timestamp=datetime.now(),
                    response_time_ms=response_time,
                    errors=[ping_result.stderr]
                )
                
        except subprocess.TimeoutExpired:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connectivity check timeout after {self.timeout}s",
                timestamp=datetime.now(),
                errors=["Connection timeout"]
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"Redis connectivity check failed: {e}",
                timestamp=datetime.now(),
                errors=[str(e)]
            )
    
    def check_pubsub_functionality(self) -> HealthCheckResult:
        """
        Test Redis pub/sub functionality.
        
        Returns:
            HealthCheckResult: Pub/sub functionality check result
        """
        start_time = time.time()
        
        try:
            logger.debug("📡 Checking Redis pub/sub functionality...")
            
            # Test channel publishing
            test_channel = "fogis:health:test"
            test_message = f"health_check_{int(time.time())}"
            
            publish_result = subprocess.run([
                "docker", "exec", self.container_name,
                "redis-cli", "PUBLISH", test_channel, test_message
            ], capture_output=True, text=True, timeout=self.timeout)
            
            response_time = (time.time() - start_time) * 1000
            
            if publish_result.returncode == 0:
                # Parse number of subscribers (should be 0 for test)
                subscribers = int(publish_result.stdout.strip()) if publish_result.stdout.strip().isdigit() else 0
                
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message="Redis pub/sub functionality operational",
                    timestamp=datetime.now(),
                    response_time_ms=response_time,
                    details={
                        "test_channel": test_channel,
                        "test_message": test_message,
                        "subscribers_notified": subscribers
                    }
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message="Redis pub/sub test failed",
                    timestamp=datetime.now(),
                    response_time_ms=response_time,
                    errors=[publish_result.stderr]
                )
                
        except subprocess.TimeoutExpired:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Redis pub/sub check timeout after {self.timeout}s",
                timestamp=datetime.now(),
                errors=["Pub/sub timeout"]
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"Redis pub/sub check failed: {e}",
                timestamp=datetime.now(),
                errors=[str(e)]
            )
    
    def monitor_redis_performance(self) -> Dict[str, Any]:
        """
        Monitor Redis performance metrics.
        
        Returns:
            Dict[str, Any]: Performance metrics and status
        """
        try:
            logger.debug("📊 Monitoring Redis performance...")
            
            # Get Redis INFO
            info_result = subprocess.run([
                "docker", "exec", self.container_name,
                "redis-cli", "INFO"
            ], capture_output=True, text=True, timeout=self.timeout)
            
            if info_result.returncode != 0:
                return {
                    "status": "error",
                    "message": "Failed to get Redis INFO",
                    "error": info_result.stderr
                }
            
            # Parse Redis INFO output
            info_data = {}
            for line in info_result.stdout.split('\n'):
                if ':' in line and not line.startswith('#'):
                    key, value = line.split(':', 1)
                    info_data[key.strip()] = value.strip()
            
            # Extract key metrics
            connected_clients = int(info_data.get('connected_clients', 0))
            used_memory = info_data.get('used_memory', '0')
            used_memory_mb = float(used_memory) / (1024 * 1024) if used_memory.isdigit() else 0
            total_commands = int(info_data.get('total_commands_processed', 0))
            instantaneous_ops = int(info_data.get('instantaneous_ops_per_sec', 0))
            keyspace_hits = int(info_data.get('keyspace_hits', 0))
            keyspace_misses = int(info_data.get('keyspace_misses', 0))
            uptime_seconds = int(info_data.get('uptime_in_seconds', 0))
            
            # Calculate hit rate
            total_requests = keyspace_hits + keyspace_misses
            hit_rate = (keyspace_hits / total_requests * 100) if total_requests > 0 else 100
            
            metrics = RedisPerformanceMetrics(
                connected_clients=connected_clients,
                used_memory_mb=used_memory_mb,
                total_commands_processed=total_commands,
                instantaneous_ops_per_sec=instantaneous_ops,
                keyspace_hits=keyspace_hits,
                keyspace_misses=keyspace_misses,
                uptime_seconds=uptime_seconds,
                hit_rate_percentage=hit_rate
            )
            
            # Determine performance status
            status = "healthy"
            warnings = []
            
            if used_memory_mb > 200:  # 200MB threshold
                status = "warning"
                warnings.append(f"High memory usage: {used_memory_mb:.1f}MB")
            
            if connected_clients > 50:  # 50 clients threshold
                status = "warning"
                warnings.append(f"High client count: {connected_clients}")
            
            if hit_rate < 80 and total_requests > 100:  # 80% hit rate threshold
                status = "warning"
                warnings.append(f"Low hit rate: {hit_rate:.1f}%")
            
            return {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "metrics": {
                    "connected_clients": connected_clients,
                    "used_memory_mb": round(used_memory_mb, 2),
                    "total_commands_processed": total_commands,
                    "instantaneous_ops_per_sec": instantaneous_ops,
                    "keyspace_hits": keyspace_hits,
                    "keyspace_misses": keyspace_misses,
                    "uptime_seconds": uptime_seconds,
                    "hit_rate_percentage": round(hit_rate, 2)
                },
                "warnings": warnings,
                "redis_version": info_data.get('redis_version', 'unknown'),
                "redis_mode": info_data.get('redis_mode', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"❌ Redis performance monitoring failed: {e}")
            return {
                "status": "error",
                "message": f"Performance monitoring failed: {e}",
                "timestamp": datetime.now().isoformat()
            }
    
    def validate_redis_persistence(self) -> bool:
        """
        Validate Redis data persistence configuration.
        
        Returns:
            bool: True if persistence is properly configured
        """
        try:
            logger.debug("💾 Validating Redis persistence...")
            
            # Check AOF configuration
            aof_result = subprocess.run([
                "docker", "exec", self.container_name,
                "redis-cli", "CONFIG", "GET", "appendonly"
            ], capture_output=True, text=True, timeout=self.timeout)
            
            if aof_result.returncode == 0 and "yes" in aof_result.stdout:
                logger.debug("✅ Redis AOF persistence enabled")
                return True
            else:
                logger.warning("⚠️ Redis AOF persistence not enabled")
                return False
                
        except Exception as e:
            logger.error(f"❌ Redis persistence validation failed: {e}")
            return False
    
    def get_comprehensive_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive Redis health status.
        
        Returns:
            Dict[str, Any]: Comprehensive health status
        """
        logger.info("🏥 Performing comprehensive Redis health check...")
        
        health_checks = {}
        overall_status = HealthStatus.HEALTHY
        
        # Connectivity check
        connectivity = self.check_redis_connectivity()
        health_checks["connectivity"] = {
            "status": connectivity.status.value,
            "message": connectivity.message,
            "response_time_ms": connectivity.response_time_ms,
            "details": connectivity.details,
            "errors": connectivity.errors
        }
        
        if connectivity.status != HealthStatus.HEALTHY:
            overall_status = HealthStatus.UNHEALTHY
        
        # Pub/sub functionality check
        pubsub = self.check_pubsub_functionality()
        health_checks["pubsub"] = {
            "status": pubsub.status.value,
            "message": pubsub.message,
            "response_time_ms": pubsub.response_time_ms,
            "details": pubsub.details,
            "errors": pubsub.errors
        }
        
        if pubsub.status != HealthStatus.HEALTHY and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
        # Performance monitoring
        performance = self.monitor_redis_performance()
        health_checks["performance"] = performance
        
        if performance.get("status") == "warning" and overall_status == HealthStatus.HEALTHY:
            overall_status = HealthStatus.DEGRADED
        
        # Persistence validation
        persistence_ok = self.validate_redis_persistence()
        health_checks["persistence"] = {
            "status": "healthy" if persistence_ok else "warning",
            "enabled": persistence_ok,
            "message": "AOF persistence enabled" if persistence_ok else "AOF persistence disabled"
        }
        
        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "container_name": self.container_name,
            "health_checks": health_checks,
            "summary": {
                "connectivity": connectivity.status.value,
                "pubsub": pubsub.status.value,
                "performance": performance.get("status", "unknown"),
                "persistence": "enabled" if persistence_ok else "disabled"
            }
        }

# Convenience functions for external use
def check_redis_health(container_name: str = "fogis-redis") -> Dict[str, Any]:
    """
    Check Redis health status.
    
    Args:
        container_name: Name of Redis container
        
    Returns:
        Dict[str, Any]: Health status information
    """
    monitor = RedisHealthMonitor(container_name)
    return monitor.get_comprehensive_health_status()

def is_redis_healthy(container_name: str = "fogis-redis") -> bool:
    """
    Check if Redis is healthy.
    
    Args:
        container_name: Name of Redis container
        
    Returns:
        bool: True if Redis is healthy
    """
    monitor = RedisHealthMonitor(container_name)
    connectivity = monitor.check_redis_connectivity()
    return connectivity.status == HealthStatus.HEALTHY

if __name__ == "__main__":
    # Test Redis health monitoring
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🧪 Testing Redis health monitoring...")
    
    # Check Redis health
    health_status = check_redis_health()
    
    logger.info(f"📊 Redis Health Status: {health_status['overall_status']}")
    logger.info(f"🔗 Connectivity: {health_status['summary']['connectivity']}")
    logger.info(f"📡 Pub/Sub: {health_status['summary']['pubsub']}")
    logger.info(f"⚡ Performance: {health_status['summary']['performance']}")
    logger.info(f"💾 Persistence: {health_status['summary']['persistence']}")
    
    if health_status['overall_status'] == 'healthy':
        logger.info("✅ Redis health monitoring test successful")
    else:
        logger.warning("⚠️ Redis health monitoring detected issues")
        
    # Print detailed health information
    print(json.dumps(health_status, indent=2))
