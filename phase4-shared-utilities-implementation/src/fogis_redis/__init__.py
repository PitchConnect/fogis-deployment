"""
FOGIS Redis Shared Utilities

This module provides shared Redis utilities for the FOGIS system, including
common functionality for pub/sub operations, testing, and monitoring across
all FOGIS services.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Shared Redis utilities for FOGIS system
"""

from .client import FogisRedisClient
from .publisher import FogisRedisPublisher
from .subscriber import FogisRedisSubscriber
from .testing import FogisRedisTestSuite
from .monitoring import FogisRedisMonitor
from .config import FogisRedisConfig
from .utils import (
    test_redis_connection,
    validate_redis_url,
    format_redis_message,
    parse_redis_message
)

__version__ = "1.0.0"
__author__ = "FOGIS System Architecture Team"

__all__ = [
    # Core components
    'FogisRedisClient',
    'FogisRedisPublisher', 
    'FogisRedisSubscriber',
    'FogisRedisTestSuite',
    'FogisRedisMonitor',
    'FogisRedisConfig',
    
    # Utility functions
    'test_redis_connection',
    'validate_redis_url',
    'format_redis_message',
    'parse_redis_message'
]

# Package metadata
PACKAGE_INFO = {
    "name": "fogis-redis",
    "version": __version__,
    "description": "Shared Redis utilities for FOGIS system",
    "author": __author__,
    "license": "MIT",
    "python_requires": ">=3.7",
    "dependencies": [
        "redis>=4.5.0"
    ]
}
