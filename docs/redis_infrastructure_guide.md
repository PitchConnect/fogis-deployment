# Redis Infrastructure Setup Guide

**Document Version**: 1.0  
**Created**: 2025-09-21  
**Purpose**: Comprehensive guide for Redis infrastructure setup in FOGIS deployment  
**Status**: Production Ready  

## 🎯 **OVERVIEW**

This guide provides step-by-step instructions for setting up Redis infrastructure as part of the FOGIS deployment system. Redis serves as the pub/sub communication backbone for real-time match data synchronization between services.

### **Redis Infrastructure Components**
- **Redis Container**: Redis 7-alpine with persistence and memory optimization
- **Health Monitoring**: Comprehensive health checks and performance monitoring
- **Deployment Validation**: Automated validation and readiness assessment
- **Integration Support**: Ready for service integration with pub/sub channels

## 🚀 **QUICK START**

### **Prerequisites**
- Docker Engine 20.10+ and Docker Compose 2.0+
- FOGIS deployment repository cloned and configured
- Network access for container image downloads

### **1. Deploy Redis Infrastructure**
```bash
# Navigate to FOGIS deployment directory
cd /path/to/fogis-deployment

# Deploy Redis service via docker-compose
docker-compose up -d redis

# Verify Redis deployment
docker ps | grep fogis-redis
```

### **2. Validate Deployment**
```bash
# Run automated validation
python3 deployment-improvements/redis_deployment_validation.py

# Check health status
python3 deployment-improvements/redis_health_monitoring.py
```

### **3. Test Pub/Sub Functionality**
```bash
# Test Redis pub/sub channels
docker exec fogis-redis redis-cli PUBLISH fogis:test "Hello FOGIS"

# Verify Redis connectivity
docker exec fogis-redis redis-cli ping
```

## 🔧 **DETAILED SETUP**

### **Docker Compose Configuration**

The Redis service is configured in `docker-compose.yml`:

```yaml
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
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    environment:
      - REDIS_REPLICATION_MODE=master

volumes:
  redis-data:
    driver: local
```

### **Configuration Details**

#### **Memory Management**
- **Max Memory**: 256MB limit to prevent resource exhaustion
- **Eviction Policy**: `allkeys-lru` - removes least recently used keys when memory limit reached
- **Persistence**: AOF (Append Only File) enabled for data durability

#### **Network Configuration**
- **Port**: 6379 (standard Redis port)
- **Network**: Connected to `fogis-network` for service communication
- **Container Name**: `fogis-redis` for consistent service discovery

#### **Health Monitoring**
- **Health Check**: Redis ping command every 30 seconds
- **Startup Grace**: 10 seconds before health checks begin
- **Retry Logic**: 3 retries before marking unhealthy

### **Persistence Configuration**

Redis is configured with AOF persistence for data durability:

```bash
# Verify AOF is enabled
docker exec fogis-redis redis-cli CONFIG GET appendonly

# Check AOF status
docker exec fogis-redis redis-cli INFO persistence
```

**AOF Benefits:**
- **Durability**: Every write operation is logged
- **Recovery**: Automatic recovery on container restart
- **Consistency**: Ensures data consistency across restarts

## 🏥 **HEALTH MONITORING**

### **Automated Health Checks**

The Redis infrastructure includes comprehensive health monitoring:

```python
# Check overall Redis health
from deployment-improvements.redis_health_monitoring import check_redis_health

health_status = check_redis_health()
print(f"Redis Status: {health_status['overall_status']}")
```

### **Health Check Categories**

#### **1. Connectivity Check**
- Tests basic Redis connection
- Validates ping/pong response
- Measures response time

#### **2. Pub/Sub Functionality**
- Tests channel publishing
- Validates pub/sub operations
- Ensures message delivery capability

#### **3. Performance Monitoring**
- Memory usage tracking
- Client connection monitoring
- Command processing statistics
- Hit rate analysis

#### **4. Persistence Validation**
- AOF configuration verification
- Data durability confirmation
- Recovery capability testing

### **Health Status Levels**

| Status | Description | Action Required |
|--------|-------------|-----------------|
| **HEALTHY** | All checks pass | None - system operational |
| **DEGRADED** | Minor issues detected | Monitor - system functional |
| **UNHEALTHY** | Critical issues found | Investigate - system may fail |
| **UNKNOWN** | Cannot determine status | Check connectivity |

## 🔍 **VALIDATION & TESTING**

### **Deployment Validation**

Run comprehensive deployment validation:

```bash
# Full validation report
python3 deployment-improvements/redis_deployment_validation.py

# Quick validation check
python3 -c "
from deployment-improvements.redis_deployment_validation import validate_redis_infrastructure
print('✅ READY' if validate_redis_infrastructure() else '❌ FAILED')
"
```

### **Manual Testing**

#### **Basic Connectivity**
```bash
# Test Redis ping
docker exec fogis-redis redis-cli ping
# Expected: PONG

# Test basic operations
docker exec fogis-redis redis-cli SET test_key "test_value"
docker exec fogis-redis redis-cli GET test_key
# Expected: "test_value"
```

#### **Pub/Sub Testing**
```bash
# Terminal 1: Subscribe to test channel
docker exec -it fogis-redis redis-cli SUBSCRIBE fogis:test

# Terminal 2: Publish test message
docker exec fogis-redis redis-cli PUBLISH fogis:test "Hello FOGIS"
```

#### **Performance Testing**
```bash
# Check Redis info
docker exec fogis-redis redis-cli INFO

# Monitor real-time stats
docker exec fogis-redis redis-cli --latency-history -i 1
```

## 🔧 **INTEGRATION WITH FOGIS DEPLOYMENT**

### **Deployment Integration**

Redis is integrated as Phase 4 in the FOGIS deployment process:

```python
# In deploy_fogis.py
def _deploy_redis_infrastructure(self) -> bool:
    """Deploy Redis infrastructure for pub/sub communication."""
    redis_manager = RedisInfrastructureManager(project_root=self.project_root)
    deployment_result = redis_manager.deploy_redis_service()
    
    if deployment_result.success:
        redis_manager.configure_redis_persistence()
        return redis_manager.validate_redis_deployment()
    
    return False
```

### **Service Discovery**

Services can connect to Redis using:
- **Container Name**: `fogis-redis`
- **Network**: `fogis-network`
- **Port**: `6379`
- **URL**: `redis://fogis-redis:6379`

### **Channel Conventions**

FOGIS services use standardized channel naming:

```
fogis:matches:updates     # Match data updates
fogis:processor:status    # Match processor status
fogis:calendar:status     # Calendar service status
fogis:system:alerts       # System-wide alerts
```

## 🛠️ **MAINTENANCE & OPERATIONS**

### **Container Management**

```bash
# Start Redis service
docker-compose up -d redis

# Stop Redis service
docker-compose stop redis

# Restart Redis service
docker-compose restart redis

# View Redis logs
docker-compose logs -f redis
```

### **Data Management**

```bash
# Backup Redis data
docker exec fogis-redis redis-cli BGSAVE

# Check data directory
docker exec fogis-redis ls -la /data

# Monitor memory usage
docker exec fogis-redis redis-cli INFO memory
```

### **Performance Tuning**

#### **Memory Optimization**
```bash
# Check memory usage
docker exec fogis-redis redis-cli INFO memory

# Monitor key expiration
docker exec fogis-redis redis-cli INFO keyspace

# Adjust memory policy if needed
docker exec fogis-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

#### **Connection Monitoring**
```bash
# Monitor client connections
docker exec fogis-redis redis-cli INFO clients

# List connected clients
docker exec fogis-redis redis-cli CLIENT LIST
```

## 🚨 **TROUBLESHOOTING**

### **Common Issues**

#### **Redis Container Won't Start**
```bash
# Check container logs
docker-compose logs redis

# Verify port availability
netstat -tulpn | grep 6379

# Check disk space
df -h
```

#### **Connection Refused**
```bash
# Verify container is running
docker ps | grep fogis-redis

# Check network connectivity
docker exec fogis-redis redis-cli ping

# Verify network configuration
docker network inspect fogis-network
```

#### **Memory Issues**
```bash
# Check memory usage
docker exec fogis-redis redis-cli INFO memory

# Monitor memory warnings
docker-compose logs redis | grep -i memory

# Adjust memory limits if needed
# Edit docker-compose.yml maxmemory setting
```

### **Health Check Failures**

If health checks fail:

1. **Check Redis logs**: `docker-compose logs redis`
2. **Verify connectivity**: `docker exec fogis-redis redis-cli ping`
3. **Test pub/sub**: `docker exec fogis-redis redis-cli PUBLISH test "message"`
4. **Check persistence**: `docker exec fogis-redis redis-cli CONFIG GET appendonly`

## 📊 **MONITORING & ALERTS**

### **Key Metrics to Monitor**

- **Memory Usage**: Should stay below 200MB
- **Connected Clients**: Monitor for connection leaks
- **Command Processing**: Track operations per second
- **Hit Rate**: Monitor cache efficiency
- **Persistence Status**: Ensure AOF is working

### **Automated Monitoring**

The health monitoring system provides:
- Real-time status checks
- Performance metrics collection
- Automatic alerting for issues
- Integration with FOGIS validation system

## 🔐 **SECURITY CONSIDERATIONS**

### **Network Security**
- Redis is isolated within `fogis-network`
- No external access by default
- Container-to-container communication only

### **Data Security**
- AOF persistence for data durability
- Memory-only sensitive data handling
- Automatic cleanup of expired keys

### **Access Control**
- No authentication required within private network
- Container isolation provides security boundary
- Service-specific channel naming prevents conflicts

## 📚 **ADDITIONAL RESOURCES**

### **Documentation**
- [Redis Troubleshooting Guide](redis_troubleshooting.md)
- [Redis Monitoring Guide](redis_monitoring_guide.md)
- [FOGIS Migration Plan](../REDIS_PUBSUB_MIGRATION_PLAN.md)

### **Scripts & Tools**
- `redis_infrastructure.py` - Infrastructure management
- `redis_health_monitoring.py` - Health monitoring
- `redis_deployment_validation.py` - Deployment validation

### **Testing**
- `tests/test_redis_infrastructure.py` - Unit tests
- `tests/test_redis_health_monitoring.py` - Health monitoring tests
- `tests/integration/test_redis_health_checks.py` - Integration tests

---

**Status**: ✅ **PRODUCTION READY**
**Next Steps**: Proceed with Phase 2 - Match Processor Integration
**Support**: See troubleshooting guide for common issues

## 🎯 **QUICK REFERENCE**

### **Essential Commands**
```bash
# Deploy Redis
docker-compose up -d redis

# Check health
python3 deployment-improvements/redis_health_monitoring.py

# Validate deployment
python3 deployment-improvements/redis_deployment_validation.py

# Test connectivity
docker exec fogis-redis redis-cli ping

# View logs
docker-compose logs -f redis
```

### **Key Files**
- `docker-compose.yml` - Redis service configuration
- `deployment-improvements/redis_infrastructure.py` - Infrastructure management
- `deployment-improvements/redis_health_monitoring.py` - Health monitoring
- `deployment-improvements/redis_deployment_validation.py` - Validation
- `docs/redis_troubleshooting.md` - Troubleshooting guide
