# FOGIS Centralized Logging Troubleshooting Guide

## Quick Reference

### Service Status Check
```bash
# Check all monitoring services
docker-compose ps loki grafana promtail

# Check service health
curl http://localhost:3100/ready    # Loki
curl http://localhost:3000/api/health  # Grafana
```

### Common Log Queries
```bash
# View all recent logs
curl 'http://localhost:3100/loki/api/v1/query?query={service_name=~".*"}&limit=100'

# View errors only
curl 'http://localhost:3100/loki/api/v1/query?query={level="ERROR"}&limit=50'

# View OAuth events
curl 'http://localhost:3100/loki/api/v1/query?query={oauth_event="true"}&limit=50'
```

## Common Issues and Solutions

### 1. Loki Service Failing to Start

**Symptoms:**
- Loki container in restart loop
- Error: `failed parsing config: field per_stream_retention not found`

**Solution:**
```bash
# Check Loki logs
docker logs fogis-loki --tail 20

# Restart with fixed configuration
docker-compose stop loki
docker-compose up -d loki

# Verify health
curl http://localhost:3100/ready
```

**Root Cause:** Configuration incompatibility with Loki version

### 2. No Logs Appearing in Grafana

**Symptoms:**
- Grafana shows "No data" in dashboards
- Loki is running but no logs visible

**Diagnosis Steps:**
```bash
# 1. Check if Promtail is running
docker-compose ps promtail

# 2. Check Promtail logs for errors
docker logs fogis-promtail --tail 20

# 3. Test Loki API directly
curl 'http://localhost:3100/loki/api/v1/query?query={service_name=~".*"}'

# 4. Check if services are generating logs
docker logs match-list-processor --tail 10
```

**Common Solutions:**
- **Promtail not running:** `docker-compose up -d promtail`
- **Wrong project name in config:** Check `promtail-config.yaml` filter
- **No recent logs:** Services may be idle, wait for next processing cycle

### 3. Grafana Dashboard Not Loading

**Symptoms:**
- Grafana accessible but dashboards empty
- "Dashboard not found" errors

**Solution:**
```bash
# 1. Check if dashboards are mounted
docker exec fogis-grafana ls -la /etc/grafana/provisioning/dashboards/

# 2. Restart Grafana to reload dashboards
docker-compose restart grafana

# 3. Check Grafana logs
docker logs fogis-grafana --tail 20

# 4. Manually import dashboard if needed
# Go to Grafana UI > + > Import > Upload JSON file
```

### 4. High Memory Usage

**Symptoms:**
- Loki consuming excessive memory
- System performance degradation

**Solution:**
```bash
# 1. Check current memory usage
docker stats fogis-loki

# 2. Adjust retention settings in loki-config.yaml
# Reduce retention_period from 720h to 168h (7 days)

# 3. Force cleanup
docker exec fogis-loki rm -rf /loki/chunks/fake/*

# 4. Restart Loki
docker-compose restart loki
```

### 5. OAuth Authentication Alerts Not Working

**Symptoms:**
- OAuth failures not triggering alerts
- Missing OAuth events in logs

**Diagnosis:**
```bash
# 1. Check for OAuth events in logs
curl 'http://localhost:3100/loki/api/v1/query?query={oauth_event="true"}'

# 2. Test OAuth failure detection
docker logs google-drive-service | grep -i "401\|unauthorized"

# 3. Check Promtail parsing
docker logs fogis-promtail | grep -i oauth
```

**Solution:**
- Ensure services are logging OAuth events with proper format
- Check Promtail regex patterns in `promtail-config.yaml`
- Verify alert rules in Grafana

## Performance Optimization

### Log Retention Management
```yaml
# In loki-config.yaml
limits_config:
  retention_period: 168h  # 7 days for general logs
  
# For high-volume environments, reduce to:
  retention_period: 72h   # 3 days
```

### Query Performance
```bash
# Use time ranges to limit query scope
{service_name="match-list-processor"} [1h]

# Use specific labels instead of regex when possible
{service_name="match-list-processor"} instead of {service_name=~"match.*"}

# Limit results
{level="ERROR"} | limit 100
```

### Resource Limits
```yaml
# In docker-compose.yml, add resource limits
services:
  loki:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

## Monitoring Best Practices

### 1. Regular Health Checks
```bash
#!/bin/bash
# Add to cron for automated monitoring
curl -f http://localhost:3100/ready || echo "Loki down"
curl -f http://localhost:3000/api/health || echo "Grafana down"
```

### 2. Log Volume Monitoring
```bash
# Check log ingestion rate
curl 'http://localhost:3100/loki/api/v1/query?query=rate({service_name=~".*"}[5m])'

# Alert if rate is too high (>100 logs/second)
```

### 3. Disk Space Management
```bash
# Monitor Loki storage usage
du -sh ./monitoring/loki/

# Set up automated cleanup if needed
find ./monitoring/loki/chunks -mtime +7 -delete
```

## Alert Configuration

### Critical Alerts Setup
1. **Service Down Detection:**
   - Query: `sum(count_over_time({service_name=~"fogis-.*"} |~ "healthy" [5m])) by (service_name) == 0`
   - Threshold: 0 healthy reports in 5 minutes

2. **OAuth Failure Detection:**
   - Query: `sum(count_over_time({oauth_event="true"} |~ "401|unauthorized" [5m])) > 0`
   - Threshold: Any OAuth failures in 5 minutes

3. **API Error Detection:**
   - Query: `sum(count_over_time({service_name=~".*"} |~ "500 Server Error" [5m])) > 2`
   - Threshold: More than 2 API errors in 5 minutes

### Notification Channels
```bash
# Slack webhook example
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"FOGIS Alert: Service Down"}' \
  YOUR_SLACK_WEBHOOK_URL

# Email notification (requires SMTP setup)
# Configure in Grafana > Alerting > Notification channels
```

## Advanced Troubleshooting

### Log Parsing Issues
```bash
# Test regex patterns
echo "2025-08-09 19:14:00,761 - ERROR - Error fetching matches" | \
  grep -P '(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'

# Debug Promtail parsing
docker exec fogis-promtail cat /tmp/positions.yaml
```

### Network Connectivity
```bash
# Test internal Docker network
docker exec match-list-processor ping loki
docker exec match-list-processor curl http://loki:3100/ready

# Check port bindings
netstat -tlnp | grep -E "3000|3100"
```

### Data Corruption Recovery
```bash
# If Loki data is corrupted
docker-compose stop loki
rm -rf ./monitoring/loki/chunks/*
rm -rf ./monitoring/loki/rules/*
docker-compose up -d loki
```

## Emergency Procedures

### Complete Reset
```bash
# Stop all monitoring services
docker-compose stop loki grafana promtail

# Remove containers and volumes
docker rm fogis-loki fogis-grafana fogis-promtail
docker volume rm fogis-deployment_grafana-storage

# Clean data directories
rm -rf ./monitoring/loki/chunks/*
rm -rf ./monitoring/loki/rules/*

# Restart setup
./setup-centralized-logging.sh
```

### Backup and Restore
```bash
# Backup monitoring configuration
tar -czf monitoring-backup-$(date +%Y%m%d).tar.gz ./monitoring/

# Restore from backup
tar -xzf monitoring-backup-YYYYMMDD.tar.gz
docker-compose restart loki grafana promtail
```

## Getting Help

### Log Collection for Support
```bash
# Collect all relevant logs
mkdir -p /tmp/fogis-logs-$(date +%Y%m%d)
docker logs fogis-loki > /tmp/fogis-logs-$(date +%Y%m%d)/loki.log
docker logs fogis-grafana > /tmp/fogis-logs-$(date +%Y%m%d)/grafana.log
docker logs fogis-promtail > /tmp/fogis-logs-$(date +%Y%m%d)/promtail.log
cp ./monitoring/*.yaml /tmp/fogis-logs-$(date +%Y%m%d)/
tar -czf fogis-monitoring-debug-$(date +%Y%m%d).tar.gz /tmp/fogis-logs-$(date +%Y%m%d)/
```

### Useful Resources
- [Loki Documentation](https://grafana.com/docs/loki/)
- [Grafana Documentation](https://grafana.com/docs/grafana/)
- [Promtail Configuration](https://grafana.com/docs/loki/latest/clients/promtail/configuration/)
- [LogQL Query Language](https://grafana.com/docs/loki/latest/logql/)

This troubleshooting guide covers the most common issues encountered with the FOGIS centralized logging setup. For additional support, refer to the main implementation documentation and service-specific logs.
