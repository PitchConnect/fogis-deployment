# Redis Monitoring Guide

**Document Version**: 1.0  
**Created**: 2025-09-21  
**Purpose**: Comprehensive monitoring and alerting guide for Redis infrastructure in FOGIS  
**Status**: Production Ready  

## 🎯 **MONITORING OVERVIEW**

This guide provides comprehensive monitoring strategies for Redis infrastructure in the FOGIS deployment system. It covers automated health checks, performance monitoring, alerting, and operational dashboards.

### **Monitoring Objectives**
- **Availability**: Ensure Redis service is always accessible
- **Performance**: Monitor response times and throughput
- **Resource Usage**: Track memory, CPU, and network utilization
- **Data Integrity**: Verify persistence and data consistency
- **Service Integration**: Monitor pub/sub functionality for FOGIS services

## 📊 **MONITORING ARCHITECTURE**

### **Monitoring Components**

```
┌─────────────────────────────────────────────────────────────┐
│                    FOGIS REDIS MONITORING                   │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Health Checks   │  │ Performance     │  │ Alerting    │ │
│  │ - Connectivity  │  │ - Memory Usage  │  │ - Thresholds│ │
│  │ - Pub/Sub       │  │ - Response Time │  │ - Escalation│ │
│  │ - Persistence   │  │ - Throughput    │  │ - Recovery  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Data Collection │  │ Visualization   │  │ Automation  │ │
│  │ - Metrics       │  │ - Dashboards    │  │ - Scripts   │ │
│  │ - Logs          │  │ - Reports       │  │ - Recovery  │ │
│  │ - Events        │  │ - Trends        │  │ - Scaling   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🏥 **HEALTH MONITORING**

### **Automated Health Checks**

#### **Comprehensive Health Assessment**
```bash
# Run complete health check
python3 deployment-improvements/redis_health_monitoring.py

# Quick health status
python3 -c "
from deployment-improvements.redis_health_monitoring import is_redis_healthy
print('✅ HEALTHY' if is_redis_healthy() else '❌ UNHEALTHY')
"
```

#### **Health Check Categories**

**1. Connectivity Monitoring**
- Redis ping response time
- Connection establishment success
- Network latency measurement

**2. Pub/Sub Functionality**
- Channel publishing capability
- Message delivery verification
- Subscriber notification tracking

**3. Performance Monitoring**
- Memory usage and fragmentation
- Command processing rate
- Client connection count
- Cache hit rate analysis

**4. Persistence Monitoring**
- AOF configuration verification
- Data durability confirmation
- Backup status validation

### **Health Status Interpretation**

| Status | Criteria | Response |
|--------|----------|----------|
| **HEALTHY** | All checks pass, performance optimal | Continue monitoring |
| **DEGRADED** | Minor issues, functionality maintained | Investigate warnings |
| **UNHEALTHY** | Critical failures, service impacted | Immediate action required |
| **UNKNOWN** | Cannot assess status | Check connectivity |

## 📈 **PERFORMANCE MONITORING**

### **Key Performance Indicators (KPIs)**

#### **Response Time Metrics**
```bash
# Monitor Redis latency
docker exec fogis-redis redis-cli --latency-history -i 1

# Check command processing time
docker exec fogis-redis redis-cli INFO commandstats
```

#### **Memory Utilization**
```bash
# Memory usage monitoring
docker exec fogis-redis redis-cli INFO memory

# Memory fragmentation analysis
docker exec fogis-redis redis-cli MEMORY STATS
```

#### **Throughput Metrics**
```bash
# Operations per second
docker exec fogis-redis redis-cli INFO stats | grep instantaneous_ops_per_sec

# Total commands processed
docker exec fogis-redis redis-cli INFO stats | grep total_commands_processed
```

### **Performance Thresholds**

#### **Memory Thresholds**
- **Warning**: > 200MB (78% of 256MB limit)
- **Critical**: > 240MB (94% of 256MB limit)
- **Emergency**: > 250MB (98% of 256MB limit)

#### **Response Time Thresholds**
- **Good**: < 10ms average response time
- **Warning**: 10-50ms average response time
- **Critical**: > 50ms average response time

#### **Connection Thresholds**
- **Normal**: < 20 connected clients
- **Warning**: 20-50 connected clients
- **Critical**: > 50 connected clients

### **Performance Monitoring Script**

```bash
#!/bin/bash
# redis_performance_monitor.sh

MEMORY_USAGE=$(docker exec fogis-redis redis-cli INFO memory | grep used_memory: | cut -d: -f2 | tr -d '\r')
MEMORY_MB=$((MEMORY_USAGE / 1024 / 1024))

OPS_PER_SEC=$(docker exec fogis-redis redis-cli INFO stats | grep instantaneous_ops_per_sec | cut -d: -f2 | tr -d '\r')
CONNECTED_CLIENTS=$(docker exec fogis-redis redis-cli INFO clients | grep connected_clients | cut -d: -f2 | tr -d '\r')

echo "Redis Performance Metrics:"
echo "Memory Usage: ${MEMORY_MB}MB"
echo "Operations/sec: ${OPS_PER_SEC}"
echo "Connected Clients: ${CONNECTED_CLIENTS}"

# Check thresholds
if [ "$MEMORY_MB" -gt 200 ]; then
    echo "WARNING: High memory usage (${MEMORY_MB}MB > 200MB)"
fi

if [ "$CONNECTED_CLIENTS" -gt 20 ]; then
    echo "WARNING: High client count (${CONNECTED_CLIENTS} > 20)"
fi
```

## 🚨 **ALERTING SYSTEM**

### **Alert Categories**

#### **Critical Alerts (Immediate Response)**
- Redis service unavailable
- Memory usage > 94%
- Persistence failures
- Pub/sub functionality broken

#### **Warning Alerts (Monitor Closely)**
- Memory usage > 78%
- Response time > 10ms
- Client connections > 20
- Performance degradation

#### **Info Alerts (Awareness)**
- Service restarts
- Configuration changes
- Maintenance activities
- Performance improvements

### **Alert Implementation**

#### **Health Check Alerting**
```bash
#!/bin/bash
# redis_health_alert.sh

HEALTH_JSON=$(python3 deployment-improvements/redis_health_monitoring.py 2>/dev/null)
OVERALL_STATUS=$(echo "$HEALTH_JSON" | jq -r '.overall_status')

case "$OVERALL_STATUS" in
    "healthy")
        echo "INFO: Redis is healthy"
        exit 0
        ;;
    "degraded")
        echo "WARNING: Redis is degraded but functional"
        echo "$HEALTH_JSON" | jq '.health_checks'
        exit 1
        ;;
    "unhealthy")
        echo "CRITICAL: Redis is unhealthy"
        echo "$HEALTH_JSON" | jq '.health_checks'
        exit 2
        ;;
    *)
        echo "UNKNOWN: Cannot determine Redis status"
        exit 3
        ;;
esac
```

#### **Performance Alerting**
```bash
#!/bin/bash
# redis_performance_alert.sh

PERFORMANCE_DATA=$(python3 deployment-improvements/redis_health_monitoring.py 2>/dev/null)
MEMORY_MB=$(echo "$PERFORMANCE_DATA" | jq -r '.health_checks.performance.metrics.used_memory_mb')
CLIENTS=$(echo "$PERFORMANCE_DATA" | jq -r '.health_checks.performance.metrics.connected_clients')

# Memory alerts
if (( $(echo "$MEMORY_MB > 240" | bc -l) )); then
    echo "CRITICAL: Redis memory usage critical (${MEMORY_MB}MB > 240MB)"
    exit 2
elif (( $(echo "$MEMORY_MB > 200" | bc -l) )); then
    echo "WARNING: Redis memory usage high (${MEMORY_MB}MB > 200MB)"
    exit 1
fi

# Client connection alerts
if [ "$CLIENTS" -gt 50 ]; then
    echo "CRITICAL: Too many Redis clients ($CLIENTS > 50)"
    exit 2
elif [ "$CLIENTS" -gt 20 ]; then
    echo "WARNING: High Redis client count ($CLIENTS > 20)"
    exit 1
fi

echo "INFO: Redis performance within normal parameters"
exit 0
```

### **Alert Escalation**

#### **Escalation Levels**
1. **Level 1**: Automated recovery attempts
2. **Level 2**: Team notification
3. **Level 3**: On-call engineer notification
4. **Level 4**: Management escalation

#### **Automated Recovery**
```bash
#!/bin/bash
# redis_auto_recovery.sh

echo "Attempting Redis auto-recovery..."

# Check if container is running
if ! docker ps | grep -q fogis-redis; then
    echo "Redis container not running, attempting restart..."
    docker-compose up -d redis
    sleep 10
fi

# Validate recovery
if python3 -c "from deployment-improvements.redis_health_monitoring import is_redis_healthy; exit(0 if is_redis_healthy() else 1)"; then
    echo "Redis auto-recovery successful"
    exit 0
else
    echo "Redis auto-recovery failed, escalating..."
    exit 1
fi
```

## 📊 **MONITORING DASHBOARDS**

### **Real-Time Monitoring Dashboard**

#### **Command-Line Dashboard**
```bash
#!/bin/bash
# redis_dashboard.sh

while true; do
    clear
    echo "=== FOGIS Redis Monitoring Dashboard ==="
    echo "Timestamp: $(date)"
    echo ""
    
    # Health Status
    HEALTH_STATUS=$(python3 -c "
from deployment-improvements.redis_health_monitoring import check_redis_health
import json
health = check_redis_health()
print(health['overall_status'])
" 2>/dev/null)
    
    echo "🏥 Health Status: $HEALTH_STATUS"
    echo ""
    
    # Performance Metrics
    echo "📊 Performance Metrics:"
    docker exec fogis-redis redis-cli INFO memory | grep -E "used_memory_human|mem_fragmentation_ratio"
    docker exec fogis-redis redis-cli INFO stats | grep -E "instantaneous_ops_per_sec|total_commands_processed"
    docker exec fogis-redis redis-cli INFO clients | grep connected_clients
    echo ""
    
    # Pub/Sub Status
    echo "📡 Pub/Sub Channels:"
    docker exec fogis-redis redis-cli PUBSUB CHANNELS | head -5
    echo ""
    
    # Container Status
    echo "🐳 Container Status:"
    docker ps | grep fogis-redis
    echo ""
    
    sleep 5
done
```

### **Historical Monitoring**

#### **Metrics Collection Script**
```bash
#!/bin/bash
# redis_metrics_collector.sh

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOGFILE="/var/log/redis_metrics.log"

# Collect metrics
MEMORY_USAGE=$(docker exec fogis-redis redis-cli INFO memory | grep used_memory: | cut -d: -f2 | tr -d '\r')
OPS_PER_SEC=$(docker exec fogis-redis redis-cli INFO stats | grep instantaneous_ops_per_sec | cut -d: -f2 | tr -d '\r')
CONNECTED_CLIENTS=$(docker exec fogis-redis redis-cli INFO clients | grep connected_clients | cut -d: -f2 | tr -d '\r')
HIT_RATE=$(docker exec fogis-redis redis-cli INFO stats | grep keyspace_hit_rate | cut -d: -f2 | tr -d '\r')

# Log metrics
echo "$TIMESTAMP,$MEMORY_USAGE,$OPS_PER_SEC,$CONNECTED_CLIENTS,$HIT_RATE" >> "$LOGFILE"
```

#### **Metrics Analysis**
```bash
#!/bin/bash
# redis_metrics_analysis.sh

LOGFILE="/var/log/redis_metrics.log"

echo "=== Redis Metrics Analysis (Last 24 Hours) ==="

# Memory usage trends
echo "Memory Usage Trends:"
tail -n 288 "$LOGFILE" | awk -F, '{print $2}' | awk '{
    sum += $1; count++
    if ($1 > max) max = $1
    if (min == 0 || $1 < min) min = $1
} END {
    print "Average:", sum/count/1024/1024 "MB"
    print "Maximum:", max/1024/1024 "MB"
    print "Minimum:", min/1024/1024 "MB"
}'

# Operations per second trends
echo ""
echo "Operations/Second Trends:"
tail -n 288 "$LOGFILE" | awk -F, '{print $3}' | awk '{
    sum += $1; count++
    if ($1 > max) max = $1
} END {
    print "Average:", sum/count "ops/sec"
    print "Peak:", max "ops/sec"
}'
```

## 🔧 **OPERATIONAL MONITORING**

### **Service Integration Monitoring**

#### **FOGIS Service Health Check**
```bash
#!/bin/bash
# fogis_redis_integration_check.sh

echo "=== FOGIS Redis Integration Health Check ==="

# Check Redis availability
if ! docker exec fogis-redis redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis not available"
    exit 1
fi

# Test FOGIS channels
CHANNELS=("fogis:matches:updates" "fogis:processor:status" "fogis:calendar:status" "fogis:system:alerts")

for channel in "${CHANNELS[@]}"; do
    RESULT=$(docker exec fogis-redis redis-cli PUBLISH "$channel" "health_check_$(date +%s)" 2>/dev/null)
    if [ "$RESULT" = "0" ]; then
        echo "✅ Channel $channel: OK"
    else
        echo "⚠️ Channel $channel: $RESULT subscribers"
    fi
done

echo "✅ FOGIS Redis integration health check complete"
```

### **Backup and Recovery Monitoring**

#### **Backup Status Check**
```bash
#!/bin/bash
# redis_backup_monitor.sh

echo "=== Redis Backup Status ==="

# Check AOF status
AOF_STATUS=$(docker exec fogis-redis redis-cli CONFIG GET appendonly | tail -1)
echo "AOF Persistence: $AOF_STATUS"

# Check last save time
LAST_SAVE=$(docker exec fogis-redis redis-cli LASTSAVE)
CURRENT_TIME=$(date +%s)
TIME_DIFF=$((CURRENT_TIME - LAST_SAVE))

echo "Last Save: $(date -d @$LAST_SAVE)"
echo "Time Since Last Save: $((TIME_DIFF / 60)) minutes"

# Check data directory
DATA_SIZE=$(docker exec fogis-redis du -sh /data 2>/dev/null | cut -f1)
echo "Data Directory Size: $DATA_SIZE"

# Backup recommendations
if [ "$TIME_DIFF" -gt 3600 ]; then
    echo "⚠️ WARNING: No backup in over 1 hour"
fi

if [ "$AOF_STATUS" != "yes" ]; then
    echo "❌ CRITICAL: AOF persistence disabled"
fi
```

## 📅 **MONITORING SCHEDULE**

### **Automated Monitoring Tasks**

#### **Continuous Monitoring (Every 30 seconds)**
- Health status checks
- Basic connectivity tests
- Critical threshold monitoring

#### **Regular Monitoring (Every 5 minutes)**
- Performance metrics collection
- Memory usage analysis
- Client connection monitoring

#### **Periodic Monitoring (Every hour)**
- Comprehensive health assessment
- Historical trend analysis
- Backup status verification

#### **Daily Monitoring**
- Performance report generation
- Capacity planning analysis
- Security audit checks

### **Cron Job Configuration**

```bash
# Add to crontab: crontab -e

# Health checks every 5 minutes
*/5 * * * * /path/to/redis_health_alert.sh >> /var/log/redis_health.log 2>&1

# Performance monitoring every 5 minutes
*/5 * * * * /path/to/redis_metrics_collector.sh

# Integration checks every 15 minutes
*/15 * * * * /path/to/fogis_redis_integration_check.sh >> /var/log/redis_integration.log 2>&1

# Daily performance analysis
0 6 * * * /path/to/redis_metrics_analysis.sh > /var/log/redis_daily_report.log 2>&1

# Weekly backup verification
0 7 * * 1 /path/to/redis_backup_monitor.sh >> /var/log/redis_backup.log 2>&1
```

## 📚 **MONITORING BEST PRACTICES**

### **Monitoring Guidelines**

1. **Proactive Monitoring**: Monitor trends, not just current status
2. **Threshold Tuning**: Adjust thresholds based on actual usage patterns
3. **Alert Fatigue**: Avoid too many low-priority alerts
4. **Documentation**: Keep monitoring procedures documented and updated
5. **Testing**: Regularly test monitoring and alerting systems

### **Performance Optimization**

1. **Baseline Establishment**: Establish performance baselines
2. **Trend Analysis**: Monitor long-term trends for capacity planning
3. **Bottleneck Identification**: Identify and address performance bottlenecks
4. **Resource Planning**: Plan resource allocation based on monitoring data

### **Security Monitoring**

1. **Access Monitoring**: Monitor client connections and access patterns
2. **Configuration Monitoring**: Track configuration changes
3. **Anomaly Detection**: Detect unusual usage patterns
4. **Audit Logging**: Maintain audit logs for security analysis

---

**Document Status**: ✅ **PRODUCTION READY**  
**Next Review**: Monthly or after significant changes  
**Monitoring Contact**: System Administrator
