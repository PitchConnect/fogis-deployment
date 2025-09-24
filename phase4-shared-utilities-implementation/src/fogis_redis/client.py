#!/usr/bin/env python3
"""
FOGIS Redis Client

This module provides a unified Redis client for the FOGIS system with
common functionality for connection management, health monitoring, and
error handling across all FOGIS services.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Shared Redis client for FOGIS system
"""

import logging
import time
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class FogisRedisConfig:
    """Configuration for FOGIS Redis client."""
    url: str = "redis://fogis-redis:6379"
    decode_responses: bool = True
    socket_connect_timeout: int = 5
    socket_timeout: int = 5
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

class FogisRedisClient:
    """Unified Redis client for FOGIS system with comprehensive error handling."""
    
    def __init__(self, config: FogisRedisConfig = None, service_name: str = "fogis-service"):
        """
        Initialize FOGIS Redis client.
        
        Args:
            config: Redis configuration
            service_name: Name of the service using this client
        """
        self.config = config or FogisRedisConfig()
        self.service_name = service_name
        self.client: Optional[redis.Redis] = None
        self.last_health_check = datetime.min
        self.connection_attempts = 0
        self.is_connected = False
        self.last_error: Optional[str] = None
        self.connection_stats = {
            'total_connections': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'last_connected': None,
            'uptime_start': None,
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0
        }
        
        logger.info(f"🔧 FOGIS Redis Client initialized for {self.service_name}")
        logger.info(f"   Redis URL: {self.config.url}")
        logger.info(f"   Redis Available: {REDIS_AVAILABLE}")
        
        if REDIS_AVAILABLE:
            self._connect()
        else:
            logger.warning("⚠️ Redis package not available - Redis functionality disabled")
    
    def _connect(self) -> bool:
        """
        Establish Redis connection with retry logic.
        
        Returns:
            bool: True if connection successful
        """
        if not REDIS_AVAILABLE:
            return False
        
        try:
            self.connection_attempts += 1
            self.connection_stats['total_connections'] += 1
            
            logger.debug(f"🔌 Attempting Redis connection for {self.service_name} (attempt {self.connection_attempts})")
            
            self.client = redis.from_url(
                self.config.url,
                decode_responses=self.config.decode_responses,
                socket_connect_timeout=self.config.socket_connect_timeout,
                socket_timeout=self.config.socket_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                health_check_interval=self.config.health_check_interval
            )
            
            # Test connection
            self.client.ping()
            
            self.is_connected = True
            self.last_error = None
            self.connection_attempts = 0
            self.last_health_check = datetime.now()
            self.connection_stats['successful_connections'] += 1
            self.connection_stats['last_connected'] = datetime.now().isoformat()
            
            if self.connection_stats['uptime_start'] is None:
                self.connection_stats['uptime_start'] = datetime.now().isoformat()
            
            logger.info(f"✅ Redis connection established for {self.service_name}")
            return True
            
        except Exception as e:
            self.is_connected = False
            self.last_error = str(e)
            self.connection_stats['failed_connections'] += 1
            
            logger.warning(f"⚠️ Redis connection failed for {self.service_name} (attempt {self.connection_attempts}): {e}")
            return False
    
    def ensure_connection(self) -> bool:
        """
        Ensure Redis connection is active, reconnect if necessary.
        
        Returns:
            bool: True if connection is active
        """
        if not REDIS_AVAILABLE:
            return False
        
        # Check if we need to perform health check
        now = datetime.now()
        if (now - self.last_health_check).seconds >= self.config.health_check_interval:
            self._health_check()
        
        # If not connected, try to reconnect
        if not self.is_connected:
            if self.connection_attempts < self.config.max_retries:
                time.sleep(self.config.retry_delay)
                return self._connect()
            else:
                logger.error(f"❌ Redis connection failed for {self.service_name} after {self.config.max_retries} attempts")
                return False
        
        return True
    
    def _health_check(self) -> bool:
        """
        Perform Redis health check.
        
        Returns:
            bool: True if Redis is healthy
        """
        if not REDIS_AVAILABLE or not self.client:
            return False
        
        try:
            self.client.ping()
            self.is_connected = True
            self.last_health_check = datetime.now()
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Redis health check failed for {self.service_name}: {e}")
            self.is_connected = False
            self.last_error = str(e)
            return False
    
    def execute_operation(self, operation: str, *args, **kwargs) -> Any:
        """
        Execute Redis operation with error handling and statistics tracking.
        
        Args:
            operation: Redis operation name (e.g., 'get', 'set', 'publish')
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Any: Operation result or None if failed
        """
        if not self.ensure_connection():
            logger.warning(f"⚠️ Cannot execute {operation} for {self.service_name}: Redis not available")
            self.connection_stats['failed_operations'] += 1
            return None
        
        try:
            self.connection_stats['total_operations'] += 1
            
            # Get the operation method from Redis client
            method = getattr(self.client, operation)
            result = method(*args, **kwargs)
            
            self.connection_stats['successful_operations'] += 1
            logger.debug(f"✅ Redis {operation} successful for {self.service_name}")
            
            return result
            
        except Exception as e:
            self.connection_stats['failed_operations'] += 1
            logger.error(f"❌ Redis {operation} failed for {self.service_name}: {e}")
            self.is_connected = False
            self.last_error = str(e)
            return None
    
    def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        return self.execute_operation('get', key)
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis."""
        result = self.execute_operation('set', key, value, ex=ex)
        return result is not None
    
    def publish(self, channel: str, message: str) -> Optional[int]:
        """Publish message to Redis channel."""
        return self.execute_operation('publish', channel, message)
    
    def delete(self, *keys: str) -> Optional[int]:
        """Delete keys from Redis."""
        return self.execute_operation('delete', *keys)
    
    def exists(self, *keys: str) -> Optional[int]:
        """Check if keys exist in Redis."""
        return self.execute_operation('exists', *keys)
    
    def ping(self) -> bool:
        """Ping Redis server."""
        result = self.execute_operation('ping')
        return result is not None
    
    def info(self, section: str = None) -> Optional[Dict[str, Any]]:
        """Get Redis server information."""
        return self.execute_operation('info', section)
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get comprehensive connection status and statistics.
        
        Returns:
            Dict[str, Any]: Connection status information
        """
        # Calculate uptime
        uptime_seconds = 0
        if self.connection_stats['uptime_start']:
            uptime_start = datetime.fromisoformat(self.connection_stats['uptime_start'])
            uptime = datetime.now() - uptime_start
            uptime_seconds = uptime.total_seconds()
        
        return {
            "service_name": self.service_name,
            "redis_available": REDIS_AVAILABLE,
            "is_connected": self.is_connected,
            "connection_attempts": self.connection_attempts,
            "last_error": self.last_error,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check != datetime.min else None,
            "uptime_seconds": uptime_seconds,
            "config": {
                "url": self.config.url,
                "timeout": self.config.socket_timeout,
                "max_retries": self.config.max_retries
            },
            "statistics": self.connection_stats.copy()
        }
    
    def reset_statistics(self) -> None:
        """Reset connection statistics."""
        self.connection_stats = {
            'total_connections': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'last_connected': None,
            'uptime_start': None,
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0
        }
        logger.info(f"📊 Connection statistics reset for {self.service_name}")
    
    def close(self) -> None:
        """Close Redis connection gracefully."""
        logger.info(f"🔌 Closing Redis connection for {self.service_name}")
        
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.warning(f"⚠️ Error closing Redis client for {self.service_name}: {e}")
        
        self.client = None
        self.is_connected = False

# Convenience functions for external use
def create_fogis_redis_client(redis_url: str = None, service_name: str = "fogis-service") -> FogisRedisClient:
    """
    Create FOGIS Redis client with optional custom URL.
    
    Args:
        redis_url: Custom Redis URL (optional)
        service_name: Name of the service using this client
        
    Returns:
        FogisRedisClient: Configured Redis client
    """
    config = FogisRedisConfig()
    if redis_url:
        config.url = redis_url
    
    return FogisRedisClient(config, service_name)

def test_fogis_redis_connection(redis_url: str = None, service_name: str = "test-service") -> bool:
    """
    Test FOGIS Redis connection availability.
    
    Args:
        redis_url: Custom Redis URL (optional)
        service_name: Name of the service for testing
        
    Returns:
        bool: True if Redis is available and connectable
    """
    client = create_fogis_redis_client(redis_url, service_name)
    status = client.ensure_connection()
    client.close()
    return status

if __name__ == "__main__":
    # Test FOGIS Redis client
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🧪 Testing FOGIS Redis client...")
    
    # Test connection
    if test_fogis_redis_connection():
        logger.info("✅ FOGIS Redis client test successful")
    else:
        logger.error("❌ FOGIS Redis client test failed")
    
    # Test client operations
    client = create_fogis_redis_client(service_name="test-client")
    
    # Test basic operations
    if client.ensure_connection():
        # Test set/get
        client.set("test:key", "test_value", ex=60)
        value = client.get("test:key")
        logger.info(f"📝 Set/Get test: {value}")
        
        # Test publish
        result = client.publish("test:channel", "test_message")
        logger.info(f"📡 Publish test: {result}")
        
        # Test ping
        ping_result = client.ping()
        logger.info(f"🏓 Ping test: {ping_result}")
    
    # Get status
    status = client.get_connection_status()
    logger.info(f"📊 Client Status:")
    logger.info(f"   Service: {status['service_name']}")
    logger.info(f"   Connected: {status['is_connected']}")
    logger.info(f"   Operations: {status['statistics']['total_operations']}")
    
    # Close client
    client.close()

    logger.info("🧪 FOGIS Redis client testing completed")
