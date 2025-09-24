# Standardized Redis Configuration

## Overview
This document defines the standardized Redis configuration for both match-list-processor and fogis-calendar-phonebook-sync repositories, resolving the configuration complexity issues identified in the code review.

## Key Changes
- **Reduced from 15+ environment variables to 3 essential variables**
- **Standardized variable names across both repositories**
- **Consolidated dual configuration classes into single `RedisConfig` class**
- **Simplified configuration loading and validation**

## Standardized Environment Variables

### Essential Variables (3 total)
```bash
# Core Redis Configuration
REDIS_URL=redis://fogis-redis:6379          # Redis connection URL
REDIS_ENABLED=true                          # Enable/disable Redis integration
REDIS_TIMEOUT=5                             # Connection timeout in seconds
```

### Optional Variables (for advanced configuration)
```bash
# Advanced Configuration (optional)
REDIS_MATCH_UPDATES_CHANNEL=fogis:matches:updates      # Custom channel names
REDIS_PROCESSOR_STATUS_CHANNEL=fogis:processor:status
REDIS_SYSTEM_ALERTS_CHANNEL=fogis:system:alerts
```

## Configuration Class Standardization

### Before (Complex)
- **Calendar Service**: `RedisSubscriptionConfig` with 15+ fields
- **Match Processor**: `RedisConfig` with 12+ fields
- **Different variable names**: `REDIS_PUBSUB_ENABLED` vs `REDIS_ENABLED`
- **Complex validation and management classes**

### After (Simplified)
- **Both Services**: Single `RedisConfig` class with 4 essential fields
- **Standardized variable names**: `REDIS_ENABLED` for both services
- **Simple configuration loading**: No complex validation or management layers

## Implementation Changes

### Calendar Service (fogis-calendar-phonebook-sync)
```python
# Before: Complex configuration
from redis_integration.config import (
    RedisSubscriptionConfig,
    RedisSubscriptionConfigManager,
    get_redis_subscription_config,
    get_redis_subscription_config_manager,
    reload_redis_subscription_config,
)

# After: Simplified configuration
from redis_integration.config import RedisConfig, get_redis_config, reload_redis_config
```

### Match Processor (match-list-processor)
```python
# Before: Complex configuration with different class name
from redis_integration.config import RedisConfig  # (but with 12+ fields)

# After: Simplified configuration (same interface, fewer fields)
from redis_integration.config import RedisConfig, get_redis_config, reload_redis_config
```

## Migration Guide

### For Existing Deployments
1. **Update environment variables**:
   ```bash
   # Replace old variables
   REDIS_PUBSUB_ENABLED=true          → REDIS_ENABLED=true
   REDIS_CONNECTION_TIMEOUT=5         → REDIS_TIMEOUT=5
   REDIS_SOCKET_TIMEOUT=5             → (removed - uses REDIS_TIMEOUT)
   REDIS_MAX_RETRIES=3                → (removed - uses defaults)
   REDIS_RETRY_DELAY=1.0              → (removed - uses defaults)
   REDIS_HEALTH_CHECK_INTERVAL=30     → (removed - uses defaults)
   REDIS_SUBSCRIPTION_TIMEOUT=1       → (removed - uses defaults)
   REDIS_DECODE_RESPONSES=true        → (removed - always true)
   REDIS_AUTO_RECONNECT=true          → (removed - always true)
   REDIS_RETRY_ON_TIMEOUT=true        → (removed - always true)
   ```

2. **Keep essential variables**:
   ```bash
   REDIS_URL=redis://fogis-redis:6379  # Keep as-is
   REDIS_ENABLED=true                  # Standardized name
   REDIS_TIMEOUT=5                     # Simplified timeout
   ```

### Backward Compatibility
- **Calendar service** still checks both `REDIS_ENABLED` and `REDIS_PUBSUB_ENABLED` for compatibility
- **Match processor** uses standardized `REDIS_ENABLED` variable
- **Default values** ensure system works without explicit configuration

## Benefits of Standardization

### Reduced Complexity
- **85% fewer configuration options** to manage
- **Single configuration class** across both services
- **Consistent variable naming** eliminates confusion

### Improved Maintainability
- **Fewer configuration files** to maintain
- **Simpler deployment scripts** with fewer variables
- **Reduced documentation** requirements

### Better Developer Experience
- **Easier to understand** configuration requirements
- **Faster setup** for new developers
- **Consistent patterns** across services

## Testing Configuration

### Minimal Test Configuration
```bash
# .env.test
REDIS_URL=redis://localhost:6379
REDIS_ENABLED=true
REDIS_TIMEOUT=1
```

### Production Configuration
```bash
# .env.production
REDIS_URL=redis://fogis-redis:6379
REDIS_ENABLED=true
REDIS_TIMEOUT=5
```

## Validation

### Configuration Validation (Simplified)
```python
def validate_config(config: RedisConfig) -> bool:
    """Simple configuration validation."""
    if not config.enabled:
        return True
    
    if not config.url or not config.url.startswith(("redis://", "rediss://")):
        logger.error(f"Invalid Redis URL: {config.url}")
        return False
    
    if config.timeout <= 0:
        logger.error(f"Invalid timeout: {config.timeout}")
        return False
    
    return True
```

This standardization resolves the configuration complexity issues while maintaining full functionality and backward compatibility.
