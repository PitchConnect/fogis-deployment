# Redis Pub/Sub Quick Reference & Checklist

**Quick Start Guide for Redis Pub/Sub Migration**
**Version**: 1.1 | **Date**: 2025-09-21 | **Status**: Phase 1 Complete ✅, Phase 2 In Progress 🔄

## 🎯 **QUICK OVERVIEW**

**Problem**: Redis pub/sub code was incorrectly placed in deployment repository
**Solution**: Distribute across proper service repositories
**Approach**: 4-phase implementation with proper service boundaries

## 🚀 **CURRENT STATUS**

**Phase 1**: ✅ **IMPLEMENTATION COMPLETE** - Redis infrastructure foundation (PR REQUIRED)
**Phase 2**: ✅ **IMPLEMENTATION COMPLETE** - Match processor Redis publishing integration (PR REQUIRED)
**Phase 3**: ⏳ **READY FOR IMPLEMENTATION** - Calendar service Redis subscription integration
**Phase 4**: ⏳ **READY FOR IMPLEMENTATION** - End-to-end validation and testing

## 🚨 **IMMEDIATE ACTION REQUIRED: PULL REQUEST SUBMISSIONS**

### **Phase 1 PR Submission**
```bash
# Target: fogis-deployment repository
git checkout -b feature/redis-pubsub-infrastructure
# Copy Phase 1 files and create PR
```

### **Phase 2 PR Submission**
```bash
# Target: match-list-processor repository
git checkout -b feature/redis-publishing-integration
# Copy Phase 2 files and create PR
```

### **Phase 3 Implementation**
```bash
# Target: fogis-calendar-phonebook-sync repository
git checkout -b feature/redis-subscription-integration
# Implement Phase 3 and create PR
```

### **Phase 4 Implementation**
```bash
# Target: fogis-api-client-python repository
git checkout -b feature/shared-redis-utilities
# Implement Phase 4 and create PR
```

## 📋 **IMPLEMENTATION CHECKLIST**

### **✅ Phase 1: Infrastructure (Week 1)**
**Repository**: `fogis-deployment`

- [ ] **Add Redis service to docker-compose.yml**
  ```yaml
  redis:
    image: redis:7-alpine
    container_name: fogis-redis
    ports: ["6379:6379"]
    healthcheck: ["CMD", "redis-cli", "ping"]
  ```

- [ ] **Create redis_infrastructure.py**
  - Redis deployment orchestration
  - Health validation
  - Integration with deploy_fogis.py

- [ ] **Update validation_system.py**
  - Add Redis health checks
  - Graceful degradation handling

- [ ] **Test infrastructure**
  - Redis container deployment
  - Health check validation
  - Deployment orchestration

### **✅ Phase 2: Match Processor (Week 2)**
**Repository**: `match-list-processor`

- [ ] **Add Redis dependency**
  ```bash
  echo "redis>=4.5.0" >> requirements.txt
  ```

- [ ] **Create src/redis_integration.py**
  - MatchProcessorRedis class
  - publish_match_updates() function
  - Connection handling with fallback

- [ ] **Integrate with match processing**
  ```python
  # After successful processing
  redis_success = publish_match_updates(all_matches, changes)
  if not redis_success:
      # HTTP fallback
  ```

- [ ] **Test publishing**
  - Unit tests for Redis publishing
  - Integration with Redis container
  - HTTP fallback scenarios

### **✅ Phase 3: Calendar Service (Week 3)**
**Repository**: `fogis-calendar-phonebook-sync`

- [ ] **Add Redis dependency**
  ```bash
  echo "redis>=4.5.0" >> requirements.txt
  ```

- [ ] **Create src/redis_integration.py**
  - CalendarServiceRedis class
  - subscribe_to_match_updates() function
  - Background subscription thread

- [ ] **Integrate with Flask app**
  ```python
  def handle_match_updates(matches, metadata):
      sync_matches_to_calendar(matches)
  
  subscribe_to_match_updates(handle_match_updates)
  ```

- [ ] **Test subscription**
  - Unit tests for Redis subscription
  - End-to-end pub/sub flow
  - HTTP fallback scenarios

### **✅ Phase 4: Validation (Week 4)**

- [ ] **End-to-end testing**
  - Full pub/sub flow
  - Performance validation
  - Error handling

- [ ] **Documentation updates**
  - Service-specific README files
  - Integration guides
  - Troubleshooting docs

- [ ] **Production readiness**
  - Staging environment testing
  - Rollback procedures
  - Monitoring setup

## 🔗 **REPOSITORY MAPPING**

| Component | Current Location | Target Repository |
|-----------|------------------|-------------------|
| **Redis Infrastructure** | deployment-improvements/ | `fogis-deployment` |
| **Match Publishing** | local-patches/match-list-processor/ | `match-list-processor` |
| **Calendar Subscription** | local-patches/fogis-calendar-phonebook-sync/ | `fogis-calendar-phonebook-sync` |

## 🚀 **QUICK START COMMANDS**

### **Phase 1: Infrastructure**
```bash
# Clone deployment repository
git clone https://github.com/PitchConnect/fogis-deployment.git
cd fogis-deployment
git checkout -b feature/redis-infrastructure

# Add Redis to docker-compose.yml
# Create redis_infrastructure.py
# Update validation_system.py

# Test deployment
docker-compose up -d redis
docker exec fogis-redis redis-cli ping
```

### **Phase 2: Match Processor**
```bash
# Clone match processor repository
git clone https://github.com/PitchConnect/match-list-processor.git
cd match-list-processor
git checkout -b feature/redis-publishing

# Add dependency
echo "redis>=4.5.0" >> requirements.txt

# Create src/redis_integration.py
# Integrate with existing match processing

# Test
python -m pytest tests/test_redis_integration.py
```

### **Phase 3: Calendar Service**
```bash
# Clone calendar service repository
git clone https://github.com/PitchConnect/fogis-calendar-phonebook-sync.git
cd fogis-calendar-phonebook-sync
git checkout -b feature/redis-subscription

# Add dependency
echo "redis>=4.5.0" >> requirements.txt

# Create src/redis_integration.py
# Integrate with Flask app

# Test
python -m pytest tests/test_redis_integration.py
```

## 🔧 **KEY INTEGRATION POINTS**

### **Match Processor Integration**
```python
# In existing match processing workflow
try:
    # After successful processing and storage
    all_matches = list(current_matches_dict.values())
    redis_success = publish_match_updates(all_matches, changes)
    
    if redis_success:
        logger.info("📡 Published via Redis")
    else:
        logger.info("📞 Using HTTP fallback")
        # Existing HTTP notification
        
except Exception as e:
    logger.error(f"Publishing failed: {e}")
    # Continue processing - don't fail on publishing
```

### **Calendar Service Integration**
```python
# In Flask app initialization
from src.redis_integration import subscribe_to_match_updates

def handle_match_updates(matches, metadata):
    """Handle Redis match updates."""
    if metadata.get('has_changes', True):
        sync_matches_to_calendar(matches)  # Existing function

# Start subscription
if subscribe_to_match_updates(handle_match_updates):
    logger.info("✅ Redis subscription active")
else:
    logger.info("⚠️ Using HTTP endpoints only")
```

## 🚨 **EMERGENCY PROCEDURES**

### **Quick Disable**
```bash
# Disable Redis integration via environment
export REDIS_PUBSUB_ENABLED=false

# Or stop Redis container
docker stop fogis-redis
```

### **Rollback Sequence**
1. **Disable calendar subscription** → HTTP endpoints active
2. **Disable match publishing** → HTTP notifications active  
3. **Stop Redis container** → Full HTTP fallback
4. **Revert service versions** → Previous working state

## 📊 **MONITORING & VALIDATION**

### **Health Checks**
```bash
# Redis infrastructure
docker exec fogis-redis redis-cli ping

# Service integration
curl http://localhost:9083/health  # Calendar service
curl http://localhost:9082/health  # Match processor
```

### **Message Flow Testing**
```bash
# Test Redis pub/sub
docker exec fogis-redis redis-cli MONITOR

# Test message publishing
docker exec fogis-redis redis-cli PUBLISH fogis_matches '{"test": true}'

# Check subscribers
docker exec fogis-redis redis-cli PUBSUB CHANNELS
```

## 🔍 **TROUBLESHOOTING**

### **Common Issues**
- **Redis connection failed** → Check container status, network connectivity
- **No subscribers** → Verify calendar service Redis integration
- **Publishing failed** → Check match processor Redis integration
- **HTTP fallback active** → Expected behavior when Redis unavailable

### **Debug Commands**
```bash
# Check Redis logs
docker logs fogis-redis

# Check service logs
docker logs process-matches-service
docker logs fogis-calendar-phonebook-sync

# Test Redis connectivity
docker exec fogis-redis redis-cli ping
docker exec fogis-redis redis-cli info
```

## 📚 **REFERENCE LINKS**

- **Full Migration Plan**: `REDIS_PUBSUB_MIGRATION_PLAN.md`
- **Closed PRs**: #61 (Infrastructure), #62 (Match Processor), #63 (Calendar Service)
- **Repositories**:
  - https://github.com/PitchConnect/fogis-deployment
  - https://github.com/PitchConnect/match-list-processor
  - https://github.com/PitchConnect/fogis-calendar-phonebook-sync

---

**Status**: Ready for implementation  
**Next**: Begin Phase 1 in `fogis-deployment` repository
