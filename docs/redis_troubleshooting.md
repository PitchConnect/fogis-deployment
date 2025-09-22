# Redis Troubleshooting Guide

**Document Version**: 1.0  
**Created**: 2025-09-21  
**Purpose**: Comprehensive troubleshooting guide for Redis infrastructure in FOGIS  
**Status**: Production Ready  

## 🚨 **EMERGENCY PROCEDURES**

### **Redis Service Down**
```bash
# 1. Check container status
docker ps | grep fogis-redis

# 2. If not running, start Redis
docker-compose up -d redis

# 3. Check logs for errors
docker-compose logs redis

# 4. Validate deployment
python3 deployment-improvements/redis_deployment_validation.py
```

### **Complete System Recovery**
```bash
# 1. Stop all services
docker-compose down

# 2. Remove Redis container and volume (DATA LOSS!)
docker-compose down -v

# 3. Redeploy from scratch
docker-compose up -d redis

# 4. Validate recovery
python3 deployment-improvements/redis_health_monitoring.py
```

## 🔍 **DIAGNOSTIC PROCEDURES**

### **Health Check Diagnostics**

#### **Step 1: Basic Connectivity**
```bash
# Test Redis ping
docker exec fogis-redis redis-cli ping
# Expected: PONG

# If fails, check:
docker ps | grep fogis-redis  # Container running?
docker-compose logs redis     # Any error messages?
```

#### **Step 2: Pub/Sub Functionality**
```bash
# Test publishing
docker exec fogis-redis redis-cli PUBLISH test "hello"
# Expected: (integer) 0 (no subscribers)

# If fails, check Redis logs:
docker-compose logs redis | grep -i error
```

#### **Step 3: Performance Check**
```bash
# Check Redis info
docker exec fogis-redis redis-cli INFO

# Monitor memory usage
docker exec fogis-redis redis-cli INFO memory

# Check client connections
docker exec fogis-redis redis-cli INFO clients
```

### **Automated Diagnostics**

#### **Run Comprehensive Health Check**
```bash
python3 deployment-improvements/redis_health_monitoring.py
```

**Expected Output:**
```
📊 Redis Health Status: healthy
🔗 Connectivity: healthy
📡 Pub/Sub: healthy
⚡ Performance: healthy
💾 Persistence: enabled
```

#### **Run Deployment Validation**
```bash
python3 deployment-improvements/redis_deployment_validation.py
```

**Expected Output:**
```
Overall Status: READY
Total Checks: 4
Passed: 4
Failed: 0
Ready for Production: True
```

## 🐛 **COMMON ISSUES & SOLUTIONS**

### **Issue 1: Container Won't Start**

#### **Symptoms:**
- `docker-compose up -d redis` fails
- Container exits immediately
- "Port already in use" errors

#### **Diagnosis:**
```bash
# Check if port 6379 is in use
netstat -tulpn | grep 6379
lsof -i :6379

# Check Docker logs
docker-compose logs redis

# Check disk space
df -h
```

#### **Solutions:**

**Port Conflict:**
```bash
# Find process using port 6379
sudo lsof -i :6379

# Kill conflicting process (if safe)
sudo kill -9 <PID>

# Or change Redis port in docker-compose.yml
ports:
  - "6380:6379"  # Use different external port
```

**Disk Space:**
```bash
# Clean up Docker
docker system prune -f

# Remove unused volumes
docker volume prune -f

# Check available space
df -h
```

**Permission Issues:**
```bash
# Fix Docker permissions
sudo chown -R $USER:$USER /var/lib/docker

# Restart Docker service
sudo systemctl restart docker
```

### **Issue 2: Connection Refused**

#### **Symptoms:**
- `redis-cli ping` fails
- Services can't connect to Redis
- "Connection refused" errors

#### **Diagnosis:**
```bash
# Check container status
docker ps | grep fogis-redis

# Check container health
docker inspect fogis-redis | grep Health

# Test network connectivity
docker exec fogis-redis redis-cli ping
```

#### **Solutions:**

**Container Not Running:**
```bash
# Start Redis container
docker-compose up -d redis

# Check startup logs
docker-compose logs redis
```

**Network Issues:**
```bash
# Check network exists
docker network ls | grep fogis-network

# Recreate network if missing
docker network create fogis-network

# Restart with network
docker-compose down && docker-compose up -d redis
```

**Redis Configuration:**
```bash
# Check Redis config
docker exec fogis-redis redis-cli CONFIG GET "*"

# Reset to defaults if needed
docker exec fogis-redis redis-cli CONFIG RESETSTAT
```

### **Issue 3: High Memory Usage**

#### **Symptoms:**
- Memory warnings in health checks
- Slow Redis performance
- Container OOM kills

#### **Diagnosis:**
```bash
# Check memory usage
docker exec fogis-redis redis-cli INFO memory

# Monitor memory over time
watch "docker exec fogis-redis redis-cli INFO memory | grep used_memory_human"

# Check for memory leaks
docker exec fogis-redis redis-cli INFO clients
```

#### **Solutions:**

**Immediate Relief:**
```bash
# Flush all data (DATA LOSS!)
docker exec fogis-redis redis-cli FLUSHALL

# Or flush specific database
docker exec fogis-redis redis-cli FLUSHDB
```

**Configuration Tuning:**
```bash
# Adjust memory policy
docker exec fogis-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Set memory limit
docker exec fogis-redis redis-cli CONFIG SET maxmemory 256mb

# Enable key expiration
docker exec fogis-redis redis-cli CONFIG SET maxmemory-samples 5
```

**Persistent Fix:**
Edit `docker-compose.yml`:
```yaml
command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### **Issue 4: Persistence Problems**

#### **Symptoms:**
- Data lost after container restart
- AOF errors in logs
- Persistence warnings in health checks

#### **Diagnosis:**
```bash
# Check AOF status
docker exec fogis-redis redis-cli CONFIG GET appendonly

# Check AOF file
docker exec fogis-redis ls -la /data/

# Check for AOF errors
docker-compose logs redis | grep -i aof
```

#### **Solutions:**

**Enable AOF:**
```bash
# Enable AOF persistence
docker exec fogis-redis redis-cli CONFIG SET appendonly yes

# Force AOF rewrite
docker exec fogis-redis redis-cli BGREWRITEAOF
```

**Fix Corrupted AOF:**
```bash
# Stop Redis
docker-compose stop redis

# Fix AOF file
docker run --rm -v fogis-deployment_redis-data:/data redis:7-alpine redis-check-aof --fix /data/appendonly.aof

# Restart Redis
docker-compose up -d redis
```

**Reset Persistence:**
```bash
# Stop Redis
docker-compose stop redis

# Remove data volume (DATA LOSS!)
docker volume rm fogis-deployment_redis-data

# Restart Redis
docker-compose up -d redis
```

### **Issue 5: Pub/Sub Not Working**

#### **Symptoms:**
- Messages not delivered
- Pub/sub health checks fail
- Services not receiving updates

#### **Diagnosis:**
```bash
# Test pub/sub manually
# Terminal 1:
docker exec -it fogis-redis redis-cli SUBSCRIBE test

# Terminal 2:
docker exec fogis-redis redis-cli PUBLISH test "hello"

# Check for subscribers
docker exec fogis-redis redis-cli PUBSUB CHANNELS
```

#### **Solutions:**

**Channel Issues:**
```bash
# List active channels
docker exec fogis-redis redis-cli PUBSUB CHANNELS

# Check subscribers
docker exec fogis-redis redis-cli PUBSUB NUMSUB fogis:matches:updates

# Test with different channel
docker exec fogis-redis redis-cli PUBLISH fogis:test "test message"
```

**Service Integration:**
```bash
# Check service logs for Redis errors
docker-compose logs match-list-processor | grep -i redis
docker-compose logs fogis-calendar-phonebook-sync | grep -i redis

# Verify service Redis configuration
# Check environment variables and connection strings
```

## 🔧 **PERFORMANCE TROUBLESHOOTING**

### **Slow Response Times**

#### **Diagnosis:**
```bash
# Monitor latency
docker exec fogis-redis redis-cli --latency

# Check slow queries
docker exec fogis-redis redis-cli SLOWLOG GET 10

# Monitor operations
docker exec fogis-redis redis-cli MONITOR
```

#### **Solutions:**
```bash
# Reset slow log
docker exec fogis-redis redis-cli SLOWLOG RESET

# Optimize memory
docker exec fogis-redis redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Check for blocking operations
docker exec fogis-redis redis-cli CLIENT LIST
```

### **High CPU Usage**

#### **Diagnosis:**
```bash
# Check Redis stats
docker exec fogis-redis redis-cli INFO stats

# Monitor CPU usage
docker stats fogis-redis

# Check for expensive operations
docker exec fogis-redis redis-cli INFO commandstats
```

#### **Solutions:**
```bash
# Limit client connections
docker exec fogis-redis redis-cli CONFIG SET maxclients 100

# Optimize configuration
docker exec fogis-redis redis-cli CONFIG SET tcp-keepalive 60

# Monitor and kill expensive operations
docker exec fogis-redis redis-cli CLIENT KILL TYPE normal
```

## 📊 **MONITORING & ALERTING**

### **Key Metrics to Watch**

#### **Memory Metrics:**
```bash
# Memory usage
docker exec fogis-redis redis-cli INFO memory | grep used_memory_human

# Memory fragmentation
docker exec fogis-redis redis-cli INFO memory | grep mem_fragmentation_ratio
```

#### **Performance Metrics:**
```bash
# Operations per second
docker exec fogis-redis redis-cli INFO stats | grep instantaneous_ops_per_sec

# Hit rate
docker exec fogis-redis redis-cli INFO stats | grep keyspace_hits
```

#### **Connection Metrics:**
```bash
# Connected clients
docker exec fogis-redis redis-cli INFO clients | grep connected_clients

# Rejected connections
docker exec fogis-redis redis-cli INFO stats | grep rejected_connections
```

### **Automated Monitoring Setup**

#### **Health Check Script:**
```bash
#!/bin/bash
# redis_health_check.sh

HEALTH_OUTPUT=$(python3 deployment-improvements/redis_health_monitoring.py 2>&1)
STATUS=$(echo "$HEALTH_OUTPUT" | grep "Redis Health Status:" | awk '{print $4}')

if [ "$STATUS" != "healthy" ]; then
    echo "ALERT: Redis health status is $STATUS"
    echo "$HEALTH_OUTPUT"
    exit 1
fi

echo "Redis is healthy"
exit 0
```

#### **Cron Job Setup:**
```bash
# Add to crontab for regular monitoring
# crontab -e
*/5 * * * * /path/to/redis_health_check.sh >> /var/log/redis_health.log 2>&1
```

## 🆘 **ESCALATION PROCEDURES**

### **When to Escalate**

1. **Redis completely unavailable** for > 5 minutes
2. **Data corruption** detected
3. **Memory usage** consistently > 90%
4. **Multiple service failures** due to Redis issues
5. **Performance degradation** affecting user experience

### **Escalation Information to Collect**

```bash
# System information
docker --version
docker-compose --version
uname -a
df -h

# Redis information
docker-compose logs redis > redis_logs.txt
python3 deployment-improvements/redis_health_monitoring.py > redis_health.json
python3 deployment-improvements/redis_deployment_validation.py > redis_validation.txt

# Container information
docker inspect fogis-redis > redis_inspect.json
docker stats fogis-redis --no-stream > redis_stats.txt
```

### **Emergency Contacts**

- **System Administrator**: Check deployment documentation
- **Development Team**: For service integration issues
- **Infrastructure Team**: For Docker/container issues

## 📚 **ADDITIONAL RESOURCES**

### **Documentation**
- [Redis Infrastructure Guide](redis_infrastructure_guide.md)
- [Redis Monitoring Guide](redis_monitoring_guide.md)
- [FOGIS Migration Plan](../REDIS_PUBSUB_MIGRATION_PLAN.md)

### **External Resources**
- [Redis Official Documentation](https://redis.io/documentation)
- [Redis Troubleshooting](https://redis.io/topics/problems)
- [Docker Troubleshooting](https://docs.docker.com/config/daemon/troubleshoot/)

---

**Document Status**: ✅ **PRODUCTION READY**  
**Last Updated**: 2025-09-21  
**Review Schedule**: Monthly or after incidents
