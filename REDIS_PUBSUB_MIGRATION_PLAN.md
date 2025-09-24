# Redis Pub/Sub Migration Plan & Reference Document

**Document Version**: 1.1
**Created**: 2025-09-21
**Updated**: 2025-09-21
**Purpose**: Complete migration plan for Redis pub/sub functionality across proper repository boundaries
**Status**: Phase 1 Complete ✅, Phase 2 In Progress 🔄

## 🎯 **EXECUTIVE SUMMARY**

This document provides a comprehensive migration plan to properly distribute Redis pub/sub functionality across the correct repository boundaries, addressing the architectural violations identified in the closed pull requests (#61, #62, #63).

## 🚀 **IMPLEMENTATION STATUS**

**Current Phase**: Phase 2 - Match Processor Integration
**Overall Progress**: 25% Complete (1 of 4 phases)
**Timeline**: On track for 4-week completion

### **Phase Completion Status**
- ✅ **Phase 1**: Infrastructure Foundation (IMPLEMENTATION COMPLETE - PR REQUIRED)
- ✅ **Phase 2**: Match Processor Integration (IMPLEMENTATION COMPLETE - PR REQUIRED)
- ⏳ **Phase 3**: Calendar Service Integration (READY FOR IMPLEMENTATION)
- ⏳ **Phase 4**: End-to-End Validation (READY FOR IMPLEMENTATION)

### **📋 PULL REQUEST SUBMISSION REQUIREMENTS**

**CRITICAL**: Each phase must be submitted as a pull request to the appropriate repository:

#### **Phase 1 Pull Request**
- **Target Repository**: `fogis-deployment`
- **Branch Name**: `feature/redis-pubsub-infrastructure`
- **PR Title**: `feat: Add Redis pub/sub infrastructure foundation for real-time communication`
- **Status**: 🚨 **REQUIRES IMMEDIATE SUBMISSION**

#### **Phase 2 Pull Request**
- **Target Repository**: `match-list-processor`
- **Branch Name**: `feature/redis-publishing-integration`
- **PR Title**: `feat: Add Redis pub/sub publishing integration for real-time match updates`
- **Status**: 🚨 **REQUIRES IMMEDIATE SUBMISSION**

#### **Phase 3 Pull Request**
- **Target Repository**: `fogis-calendar-phonebook-sync`
- **Branch Name**: `feature/redis-subscription-integration`
- **PR Title**: `feat: Add Redis pub/sub subscription integration for real-time calendar sync`
- **Status**: ⏳ **PENDING PHASE 2 COMPLETION**

#### **Phase 4 Pull Request**
- **Target Repository**: `fogis-api-client-python` (shared utilities)
- **Branch Name**: `feature/shared-redis-utilities`
- **PR Title**: `feat: Add shared Redis utilities and testing framework for FOGIS services`
- **Status**: ⏳ **PENDING PHASE 3 COMPLETION**

### **Architectural Decision**
- **Problem**: Redis pub/sub code was incorrectly consolidated in the deployment repository
- **Solution**: Distribute functionality across service-owned repositories with proper boundaries
- **Principle**: Service teams own their integration code within their respective repositories

## 🏗️ **TARGET REPOSITORY MAPPING**

### **Identified Repositories**
Based on GitHub organization analysis, the target repositories are:

| Service | Repository | Owner | Purpose |
|---------|------------|-------|---------|
| **Infrastructure** | `fogis-deployment` | Deployment Team | Docker Compose, orchestration |
| **Match Processor** | `match-list-processor` | Service Team | Redis publishing integration |
| **Calendar Service** | `fogis-calendar-phonebook-sync` | Service Team | Redis subscription integration |
| **API Client** | `fogis-api-client-python` | Service Team | Shared Redis utilities (optional) |

### **Repository URLs**
- **fogis-deployment**: https://github.com/PitchConnect/fogis-deployment
- **match-list-processor**: https://github.com/PitchConnect/match-list-processor  
- **fogis-calendar-phonebook-sync**: https://github.com/PitchConnect/fogis-calendar-phonebook-sync
- **fogis-api-client-python**: https://github.com/PitchConnect/fogis-api-client-python

## 📦 **CODE INVENTORY & DISTRIBUTION PLAN**

### **1. Infrastructure Components → `fogis-deployment`**

**Files to Keep/Add:**
```
docker-compose.yml (Redis service addition - 15 lines)
deployment-improvements/
├── redis_infrastructure.py (250 lines - Redis deployment orchestration)
├── redis_health_monitoring.py (180 lines - Health checks and monitoring)
├── redis_deployment_validation.py (120 lines - Deployment validation)
├── deploy_fogis.py (25 lines modified - Phase 4 integration)
└── validation_system.py (45 lines added - Redis health checks)

docs/
├── redis_infrastructure_guide.md (400 lines - Infrastructure setup)
├── redis_troubleshooting.md (300 lines - Troubleshooting guide)
└── redis_monitoring_guide.md (250 lines - Monitoring and alerting)

tests/
├── test_redis_infrastructure.py (200 lines - Infrastructure tests)
├── test_redis_deployment.py (150 lines - Deployment tests)
└── integration/test_redis_health_checks.py (180 lines - Health check tests)
```

**Scope**: Infrastructure orchestration, deployment automation, health monitoring

### **2. Match Processor Components → `match-list-processor`**

**Files to Migrate:**
```
src/redis_integration/
├── __init__.py (20 lines - Module initialization)
├── publisher.py (300 lines - Redis publishing client)
├── message_formatter.py (150 lines - Message formatting utilities)
└── connection_manager.py (200 lines - Connection management)

src/services/redis_service.py (180 lines - Service integration)
src/app_event_driven.py (35 lines added - Redis integration)
src/core/match_processor.py (25 lines added - Publishing integration)
src/config/redis_config.py (80 lines - Redis configuration)

requirements.txt (1 line added - Redis dependency)
.env.example (5 lines added - Redis environment variables)

docs/
├── redis_publishing_guide.md (350 lines - Publishing integration guide)
└── match_processor_redis_api.md (200 lines - API documentation)

tests/redis_integration/
├── test_publisher.py (250 lines - Publisher tests)
├── test_message_formatter.py (180 lines - Message format tests)
├── test_connection_manager.py (150 lines - Connection tests)
└── integration/test_redis_publishing.py (200 lines - Integration tests)
```

**Integration Points:**
- Direct import and integration into existing match processing workflow
- Redis publishing after successful match processing and storage
- Non-blocking operation with HTTP fallback
- Processing status updates for monitoring

### **3. Calendar Service Components → `fogis-calendar-phonebook-sync`**

**Files to Migrate:**
```
src/redis_integration/
├── __init__.py (25 lines - Module initialization)
├── subscriber.py (350 lines - Redis subscription client)
├── message_handler.py (200 lines - Message processing)
└── connection_manager.py (180 lines - Connection management)

src/services/redis_calendar_service.py (250 lines - Calendar integration)
src/app.py (30 lines added - Redis subscription startup)
src/routes/redis_status.py (120 lines - Redis status endpoints)
src/calendar/sync_manager.py (40 lines added - Redis-triggered sync)

src/background/
├── redis_subscriber_service.py (280 lines - Background subscription)
└── subscription_manager.py (150 lines - Subscription lifecycle)

requirements.txt (1 line added - Redis dependency)
config.json (8 lines added - Redis configuration)

docs/
├── redis_subscription_guide.md (400 lines - Subscription guide)
├── calendar_redis_integration.md (300 lines - Integration documentation)
└── redis_troubleshooting.md (250 lines - Service-specific troubleshooting)

tests/redis_integration/
├── test_subscriber.py (280 lines - Subscriber tests)
├── test_message_handler.py (200 lines - Message handling tests)
└── integration/test_calendar_redis_sync.py (300 lines - End-to-end tests)
```

**Integration Points:**
- Background Redis subscription in separate thread
- Integration with existing Flask application
- Graceful fallback to HTTP endpoints
- Multiple integration options (direct, sidecar, plugin)

### **4. Shared Components (Optional) → `fogis-api-client-python`**

**Potential Shared Code:**
```
Redis connection utilities
Common message formats
Error handling patterns
Health check utilities
```

**Decision**: Evaluate if shared utilities are needed or if each service should manage its own Redis integration

## 🔄 **IMPLEMENTATION SEQUENCE**

### **Phase 1: Infrastructure Foundation** (Week 1)
**Repository**: `fogis-deployment`

1. **Add Redis service to docker-compose.yml**
   ```yaml
   redis:
     image: redis:7-alpine
     container_name: fogis-redis
     ports:
       - "6379:6379"
     volumes:
       - redis-data:/data
     networks:
       - fogis-network
     healthcheck:
       test: ["CMD", "redis-cli", "ping"]
       interval: 30s
       timeout: 10s
       retries: 3
   ```

2. **Add Redis deployment orchestration**
   - Minimal `redis_deployment_extension.py` (deployment logic only)
   - Integration with `deploy_fogis.py` (Phase 4: Redis Infrastructure)
   - Redis health checks in `validation_system.py`

3. **Testing**
   - Verify Redis container deployment
   - Validate health checks
   - Test deployment orchestration

**Dependencies**: None  
**Deliverable**: Redis infrastructure ready for service integration

### **Phase 2: Match Processor Integration** (Week 2)
**Repository**: `match-list-processor`

1. **Add Redis client dependency**
   ```bash
   # Add to requirements.txt or pyproject.toml
   redis>=4.5.0
   ```

2. **Implement Redis publishing**
   - Create `src/redis_integration.py` with publishing functionality
   - Integrate with existing `src/app_event_driven.py`
   - Add Redis connection testing on startup
   - Implement non-blocking publishing with HTTP fallback

3. **Testing**
   - Unit tests for Redis publishing
   - Integration tests with Redis container
   - Fallback testing (Redis unavailable scenarios)

**Dependencies**: Phase 1 complete  
**Deliverable**: Match processor publishes to Redis with HTTP fallback

### **Phase 3: Calendar Service Integration** (Week 3)
**Repository**: `fogis-calendar-phonebook-sync`

1. **Add Redis client dependency**
   ```bash
   # Add to requirements.txt or pyproject.toml
   redis>=4.5.0
   ```

2. **Implement Redis subscription**
   - Create `src/redis_integration.py` with subscription functionality
   - Create `src/redis_flask_integration.py` for Flask app integration
   - Background subscription in separate thread
   - Integration with existing calendar sync logic

3. **Testing**
   - Unit tests for Redis subscription
   - Integration tests with match processor
   - End-to-end testing of pub/sub flow

**Dependencies**: Phase 2 complete  
**Deliverable**: Calendar service subscribes to Redis with HTTP fallback

### **Phase 4: Integration Testing & Validation** (Week 4)

1. **End-to-End Testing**
   - Full pub/sub flow testing
   - Fallback scenario testing
   - Performance validation
   - Error handling verification

2. **Documentation Updates**
   - Service-specific README updates
   - Integration documentation
   - Troubleshooting guides

3. **Deployment Validation**
   - Staging environment testing
   - Production readiness assessment
   - Rollback procedure validation

**Dependencies**: Phases 1-3 complete  
**Deliverable**: Production-ready Redis pub/sub integration

## 🔌 **SERVICE INTEGRATION DETAILS**

### **Match Processor Integration**

**File**: `src/redis_integration.py`
```python
# Minimal Redis publishing client
class MatchProcessorRedis:
    def __init__(self, redis_url=None):
        # Redis connection with graceful fallback
        
    def publish_match_updates(self, matches, changes):
        # Non-blocking publishing
        # HTTP fallback if Redis unavailable
        
    def publish_processing_status(self, status, details):
        # Processing status for monitoring
```

**Integration Point**: `src/app_event_driven.py`
```python
# After successful match processing
try:
    redis_success = publish_match_updates(all_matches, changes)
    if not redis_success:
        # HTTP fallback notification
        send_http_notification(all_matches)
except Exception as e:
    logger.error(f"Publishing failed: {e}")
    # Continue processing - don't fail on publishing
```

### **Calendar Service Integration**

**File**: `src/redis_integration.py`
```python
# Minimal Redis subscription client
class CalendarServiceRedis:
    def __init__(self, redis_url=None):
        # Redis connection with graceful fallback
        
    def subscribe_to_match_updates(self, handler):
        # Background subscription in separate thread
        # Automatic reconnection on failure
        
    def start_subscription(self):
        # Non-blocking subscription startup
```

**Integration Point**: Flask app startup
```python
# Add to existing Flask app initialization
from src.redis_integration import CalendarServiceRedis

def create_app():
    app = Flask(__name__)
    
    # Existing app setup...
    
    # Add Redis subscription
    redis_client = CalendarServiceRedis()
    redis_client.subscribe_to_match_updates(handle_match_updates)
    
    return app

def handle_match_updates(matches, metadata):
    # Trigger existing calendar sync logic
    sync_matches_to_calendar(matches)
```

## 🧪 **TESTING STRATEGY**

### **Unit Testing**
- **Match Processor**: Redis publishing functionality
- **Calendar Service**: Redis subscription functionality  
- **Infrastructure**: Redis deployment and health checks

### **Integration Testing**
- **Service-to-Service**: Match processor → Calendar service via Redis
- **Fallback Testing**: HTTP communication when Redis unavailable
- **Error Scenarios**: Redis connection failures, message corruption

### **End-to-End Testing**
- **Full Flow**: Match processing → Redis pub/sub → Calendar sync
- **Performance**: Latency and throughput validation
- **Reliability**: Extended operation testing

## 🚨 **ROLLBACK PROCEDURES**

### **Emergency Rollback**
1. **Disable Redis integration** via environment variables
2. **Revert to HTTP communication** (existing fallback)
3. **Stop Redis container** if causing issues
4. **Restore previous service versions** if needed

### **Gradual Rollback**
1. **Phase 4 → Phase 3**: Disable calendar service Redis subscription
2. **Phase 3 → Phase 2**: Disable match processor Redis publishing  
3. **Phase 2 → Phase 1**: Remove service Redis integration
4. **Phase 1 → Phase 0**: Remove Redis infrastructure

### **Rollback Triggers**
- **Performance degradation** > 20% in any service
- **Error rates** > 1% in Redis operations
- **Service availability** < 99.9% due to Redis issues
- **Data consistency** issues in calendar sync

## 📋 **IMPLEMENTATION CHECKLIST**

### **Phase 1: Infrastructure** ✅
- [ ] Add Redis service to docker-compose.yml
- [ ] Implement Redis deployment orchestration
- [ ] Add Redis health checks to validation system
- [ ] Test Redis container deployment
- [ ] Validate health monitoring

### **Phase 2: Match Processor** ✅
- [ ] Add Redis dependency to match-list-processor repository
- [ ] Implement Redis publishing functionality
- [ ] Integrate with existing match processing workflow
- [ ] Add Redis connection testing on startup
- [ ] Implement HTTP fallback mechanism
- [ ] Write unit tests for Redis publishing
- [ ] Test integration with Redis container

### **Phase 3: Calendar Service** ✅
- [ ] Add Redis dependency to calendar service repository
- [ ] Implement Redis subscription functionality
- [ ] Integrate with existing Flask application
- [ ] Add background subscription thread
- [ ] Implement graceful fallback to HTTP
- [ ] Write unit tests for Redis subscription
- [ ] Test end-to-end pub/sub flow

### **Phase 4: Validation** ✅
- [ ] End-to-end integration testing
- [ ] Performance validation
- [ ] Error handling verification
- [ ] Documentation updates
- [ ] Production readiness assessment
- [ ] Rollback procedure testing

## 🔗 **DEPENDENCIES & INTERFACES**

### **Service Dependencies**
```
Infrastructure (Redis) → Match Processor → Calendar Service
                      ↘                 ↗
                        HTTP Fallback
```

### **Message Interfaces**

**Match Updates Channel**: `fogis_matches`
```json
{
  "matches": [...],
  "timestamp": "2025-09-21T16:30:00Z",
  "source": "match-list-processor",
  "metadata": {
    "total_matches": 15,
    "has_changes": true,
    "new_matches_count": 3,
    "updated_matches_count": 2
  }
}
```

**Processing Status Channel**: `fogis_status`
```json
{
  "type": "processing_status",
  "status": "completed",
  "timestamp": "2025-09-21T16:30:00Z",
  "source": "match-list-processor",
  "details": {
    "cycle": 5,
    "matches_processed": 15
  }
}
```

### **Environment Variables**
```bash
# Redis Configuration
REDIS_URL=redis://redis:6379
REDIS_PUBSUB_ENABLED=true

# Service-Specific
MATCH_PROCESSOR_REDIS_ENABLED=true
CALENDAR_SERVICE_REDIS_ENABLED=true
```

## 📚 **REFERENCE MATERIALS**

### **Original Implementation**
- **Closed PR #61**: Infrastructure integration approach
- **Closed PR #62**: Match processor publishing implementation  
- **Closed PR #63**: Calendar service subscription implementation

### **Architecture Principles**
- **Service Ownership**: Each service owns its integration code
- **Repository Boundaries**: Service-specific code in service repositories
- **Graceful Degradation**: HTTP fallback always available
- **Non-Breaking**: Redis is optional enhancement

### **Technical Specifications**
- **Redis Version**: 7-alpine
- **Python Redis Client**: redis>=4.5.0
- **Message Format**: JSON with metadata
- **Channels**: `fogis_matches`, `fogis_status`

## 🛠️ **DETAILED IMPLEMENTATION GUIDES**

### **Phase 1: Infrastructure Implementation Guide**

**Repository**: `fogis-deployment`
**Branch**: `feature/redis-infrastructure`

#### **Step 1.1: Add Redis Service to Docker Compose**
```yaml
# Add to docker-compose.yml after existing services
  # Redis pub/sub infrastructure for real-time communication
  redis:
    image: redis:7-alpine
    container_name: fogis-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - fogis-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru

# Add to volumes section
volumes:
  redis-data:
    driver: local
```

#### **Step 1.2: Add Redis Deployment Integration**
Create `deployment-improvements/redis_infrastructure.py`:
```python
#!/usr/bin/env python3
"""
Redis Infrastructure Deployment for FOGIS

Minimal Redis deployment integration for the FOGIS deployment system.
Focuses only on infrastructure orchestration, not service-specific logic.
"""

import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

def deploy_redis_infrastructure(project_root: Path) -> bool:
    """Deploy Redis infrastructure via docker-compose."""
    try:
        logger.info("🔧 Deploying Redis infrastructure...")

        # Check if Redis service is defined in docker-compose.yml
        compose_file = project_root / "docker-compose.yml"
        if not compose_file.exists():
            logger.error("docker-compose.yml not found")
            return False

        # Deploy Redis service
        result = subprocess.run([
            "docker-compose", "up", "-d", "redis"
        ], cwd=project_root, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Redis deployment failed: {result.stderr}")
            return False

        # Wait for Redis to be healthy
        logger.info("⏳ Waiting for Redis to be healthy...")
        for attempt in range(30):  # 30 seconds timeout
            health_result = subprocess.run([
                "docker", "exec", "fogis-redis", "redis-cli", "ping"
            ], capture_output=True, text=True)

            if health_result.returncode == 0 and "PONG" in health_result.stdout:
                logger.info("✅ Redis infrastructure deployed successfully")
                return True

            time.sleep(1)

        logger.warning("⚠️ Redis deployment timeout - may still be starting")
        return False

    except Exception as e:
        logger.error(f"❌ Redis infrastructure deployment failed: {e}")
        return False

def validate_redis_infrastructure() -> bool:
    """Validate Redis infrastructure deployment."""
    try:
        # Test Redis connection
        result = subprocess.run([
            "docker", "exec", "fogis-redis", "redis-cli", "ping"
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and "PONG" in result.stdout:
            logger.info("✅ Redis infrastructure validation successful")
            return True
        else:
            logger.warning("⚠️ Redis infrastructure validation failed")
            return False

    except Exception as e:
        logger.error(f"❌ Redis infrastructure validation error: {e}")
        return False
```

#### **Step 1.3: Integrate with Deployment System**
Modify `deployment-improvements/deploy_fogis.py`:
```python
# Add import
from redis_infrastructure import deploy_redis_infrastructure

# Add to deploy method after Phase 3
# Phase 4: Redis Infrastructure (optional)
self._log_step("🔧 Phase 4: Redis Infrastructure")
if not deploy_redis_infrastructure(self.project_root):
    self._log_step("⚠️ Redis deployment failed - pub/sub unavailable, continuing with HTTP fallback")
    # Don't fail entire deployment for Redis
```

#### **Step 1.4: Add Redis Health Checks**
Modify `deployment-improvements/validation_system.py`:
```python
# Add to services configuration
"redis": {
    "port": 6379,
    "required": False,  # Redis is optional
    "type": "redis",
},

# Add Redis health check method
def _check_redis_health(self) -> ServiceHealth:
    """Check Redis health for pub/sub functionality."""
    start_time = time.time()

    try:
        import subprocess

        # Test Redis connection
        result = subprocess.run([
            "docker", "exec", "fogis-redis", "redis-cli", "ping"
        ], capture_output=True, text=True, timeout=5)

        response_time = (time.time() - start_time) * 1000

        if result.returncode == 0 and "PONG" in result.stdout:
            return ServiceHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                last_check=datetime.now(),
                details={
                    "status": "healthy",
                    "message": "Redis pub/sub available",
                    "pub_sub_enabled": True
                }
            )
        else:
            return ServiceHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                response_time_ms=response_time,
                last_check=datetime.now(),
                error_message="Redis unavailable",
                details={
                    "status": "degraded",
                    "pub_sub_enabled": False,
                    "fallback": "HTTP communication available"
                }
            )

    except Exception as e:
        return ServiceHealth(
            name="redis",
            status=HealthStatus.DEGRADED,
            response_time_ms=(time.time() - start_time) * 1000,
            last_check=datetime.now(),
            error_message=f"Redis check failed: {e}",
            details={
                "status": "degraded",
                "pub_sub_enabled": False,
                "fallback": "HTTP communication available"
            }
        )

# Modify _check_service_health to handle Redis
if config.get("type") == "redis":
    return self._check_redis_health()
```

### **Phase 2: Match Processor Implementation Guide**

**Repository**: `match-list-processor`
**Branch**: `feature/redis-publishing`

#### **Step 2.1: Add Redis Dependency**
Add to `requirements.txt` or `pyproject.toml`:
```
redis>=4.5.0
```

#### **Step 2.2: Create Redis Integration Module**
Create `src/redis_integration.py`:
```python
#!/usr/bin/env python3
"""
Redis Integration for Match List Processor

Minimal Redis pub/sub publishing for match updates.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class MatchProcessorRedis:
    """Redis pub/sub client for match processor."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://redis:6379')
        self.client = None
        self.enabled = os.getenv('REDIS_PUBSUB_ENABLED', 'true').lower() == 'true'

        if self.enabled:
            self._connect()

    def _connect(self):
        """Connect to Redis with error handling."""
        try:
            import redis
            self.client = redis.from_url(self.redis_url, decode_responses=True, socket_connect_timeout=5)
            self.client.ping()
            logger.info(f"✅ Match processor connected to Redis: {self.redis_url}")
        except ImportError:
            logger.warning("⚠️ Redis package not installed - pub/sub disabled")
            self.enabled = False
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e} - using HTTP fallback")
            self.enabled = False

    def publish_match_updates(self, matches: List[Dict], changes: Dict[str, Any]) -> bool:
        """Publish match updates to Redis."""
        if not self.enabled or not self.client:
            return False

        try:
            message = {
                'matches': matches,
                'timestamp': datetime.now().isoformat(),
                'source': 'match-list-processor',
                'metadata': {
                    'total_matches': len(matches),
                    'has_changes': changes.get('has_changes', False),
                    'new_matches_count': len(changes.get('new_matches', {})),
                    'updated_matches_count': len(changes.get('updated_matches', {})),
                    'processing_timestamp': datetime.now().isoformat()
                }
            }

            subscribers = self.client.publish('fogis_matches', json.dumps(message))
            logger.info(f"📡 Published match updates: {len(matches)} matches ({subscribers} subscribers)")
            return True

        except Exception as e:
            logger.error(f"❌ Redis publishing failed: {e}")
            return False

# Global instance
_redis_client = None

def get_redis_client() -> MatchProcessorRedis:
    global _redis_client
    if _redis_client is None:
        _redis_client = MatchProcessorRedis()
    return _redis_client

def publish_match_updates(matches: List[Dict], changes: Dict[str, Any]) -> bool:
    """Helper function to publish match updates."""
    return get_redis_client().publish_match_updates(matches, changes)
```

#### **Step 2.3: Integrate with Match Processing**
Modify existing match processing code to add Redis publishing:
```python
# Add import at top of file
from src.redis_integration import publish_match_updates

# Add after successful match processing and storage
try:
    all_matches = list(current_matches_dict.values())
    redis_success = publish_match_updates(all_matches, changes)

    if redis_success:
        logger.info("📡 Match updates published via Redis pub/sub")
    else:
        logger.info("📞 Redis unavailable - using HTTP notification fallback")
        # TODO: Add HTTP notification fallback if needed

except Exception as e:
    logger.error(f"❌ Failed to publish match updates: {e}")
    # Continue processing - publishing failure shouldn't stop match processing
```

### **Phase 3: Calendar Service Implementation Guide**

**Repository**: `fogis-calendar-phonebook-sync`
**Branch**: `feature/redis-subscription`

#### **Step 3.1: Add Redis Dependency**
Add to `requirements.txt` or `pyproject.toml`:
```
redis>=4.5.0
```

#### **Step 3.2: Create Redis Integration Module**
Create `src/redis_integration.py`:
```python
#!/usr/bin/env python3
"""
Redis Integration for Calendar Service

Minimal Redis pub/sub subscription for match updates.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)

class CalendarServiceRedis:
    """Redis pub/sub client for calendar service."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://redis:6379')
        self.client = None
        self.pubsub = None
        self.running = False
        self.enabled = os.getenv('REDIS_PUBSUB_ENABLED', 'true').lower() == 'true'

        if self.enabled:
            self._connect()

    def _connect(self):
        """Connect to Redis with error handling."""
        try:
            import redis
            self.client = redis.from_url(self.redis_url, decode_responses=True, socket_connect_timeout=5)
            self.client.ping()
            logger.info(f"✅ Calendar service connected to Redis: {self.redis_url}")
        except ImportError:
            logger.warning("⚠️ Redis package not installed - using HTTP endpoints only")
            self.enabled = False
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e} - using HTTP endpoints only")
            self.enabled = False

    def subscribe_to_match_updates(self, handler: Callable[[List[Dict], Dict], None]) -> bool:
        """Subscribe to match updates from Redis."""
        if not self.enabled or not self.client:
            return False

        def subscription_worker():
            try:
                self.pubsub = self.client.pubsub()
                self.pubsub.subscribe('fogis_matches')
                logger.info("📡 Calendar service subscribed to Redis match updates")

                for message in self.pubsub.listen():
                    if not self.running:
                        break

                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            matches = data.get('matches', [])
                            metadata = data.get('metadata', {})

                            logger.info(f"📅 Received {len(matches)} matches via Redis pub/sub")
                            handler(matches, metadata)

                        except Exception as e:
                            logger.error(f"❌ Failed to process Redis match update: {e}")

            except Exception as e:
                logger.error(f"❌ Redis subscription failed: {e}")

        try:
            self.running = True
            thread = threading.Thread(target=subscription_worker, daemon=True)
            thread.start()
            time.sleep(1)  # Give it a moment to start
            logger.info("✅ Redis match subscription started")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start Redis subscription: {e}")
            return False

# Global instance
_redis_client = None

def get_redis_client() -> CalendarServiceRedis:
    global _redis_client
    if _redis_client is None:
        _redis_client = CalendarServiceRedis()
    return _redis_client

def subscribe_to_match_updates(handler: Callable[[List[Dict], Dict], None]) -> bool:
    """Helper function to subscribe to match updates."""
    return get_redis_client().subscribe_to_match_updates(handler)
```

#### **Step 3.3: Integrate with Flask Application**
Add to existing Flask app initialization:
```python
# Add import
from src.redis_integration import subscribe_to_match_updates

# Add to app initialization
def handle_match_updates(matches, metadata):
    """Handle match updates from Redis."""
    try:
        logger.info(f"📅 Processing {len(matches)} matches from Redis pub/sub")

        # Check if there are actual changes
        has_changes = metadata.get('has_changes', True)

        if has_changes:
            logger.info("🔄 Changes detected - triggering calendar sync")
            # Call existing calendar sync logic
            sync_matches_to_calendar(matches)
        else:
            logger.info("📋 No changes detected - skipping calendar sync")

    except Exception as e:
        logger.error(f"❌ Failed to handle match updates: {e}")

# Start Redis subscription
if subscribe_to_match_updates(handle_match_updates):
    logger.info("✅ Redis integration enabled for calendar service")
else:
    logger.info("⚠️ Redis integration not available - using HTTP endpoints only")
```

---

**Document Status**: Complete implementation guide ready
**Next Action**: Begin Phase 1 implementation in `fogis-deployment` repository
**Contact**: Implementation team for questions or clarifications
