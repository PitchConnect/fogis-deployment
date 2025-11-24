# Loki Docker Volume Migration Guide

This guide provides step-by-step instructions for migrating Loki monitoring data from the repository directory to a Docker named volume.

## Problem

Currently, Loki stores data inside the repository at `./monitoring/loki/`, causing:
- Hundreds of chunk files accumulating in the repository
- WAL (Write-Ahead Log) files tracked by Git
- Index and compactor data in the working directory
- Large repository size and clutter

## Solution

Migrate Loki data to a Docker named volume that:
- Persists data outside the repository
- Is not tracked by Git
- Is managed by Docker
- Can be easily backed up and restored

---

## Prerequisites

- Docker and Docker Compose installed
- Access to the fogis-deployment repository
- Loki service currently running (or previously run)

---

## Migration Steps

### Step 1: Stop Loki Service

```bash
# Stop Loki to prevent data corruption during migration
docker-compose stop loki

# Verify it's stopped
docker ps | grep loki
```

### Step 2: Create Docker Named Volume

```bash
# Create a named volume for Loki data
docker volume create fogis-loki-data

# Verify creation
docker volume ls | grep fogis-loki-data
```

### Step 3: Backup Existing Data (Optional but Recommended)

If you want to preserve existing Loki data:

```bash
# Create a backup of current data
tar -czf loki-data-backup-$(date +%Y%m%d-%H%M%S).tar.gz monitoring/loki/

# Verify backup
ls -lh loki-data-backup-*.tar.gz
```

### Step 4: Copy Existing Data to Docker Volume (Optional)

If you want to preserve existing logs:

```bash
# Copy data from repository to Docker volume
docker run --rm \
  -v $(pwd)/monitoring/loki:/source:ro \
  -v fogis-loki-data:/dest \
  alpine sh -c "cp -r /source/* /dest/ 2>/dev/null || true"

# Verify data was copied
docker run --rm -v fogis-loki-data:/loki alpine ls -la /loki/
```

**Note:** If you don't need to preserve existing logs, skip this step and start fresh.

### Step 5: Update docker-compose.yml

Edit `docker-compose.yml` to use the named volume:

```yaml
services:
  loki:
    image: grafana/loki:2.9.0
    container_name: fogis-loki
    ports:
      - "3100:3100"
    volumes:
      - fogis-loki-data:/loki  # ← Changed from ./monitoring/loki:/loki
      - ./monitoring/loki-config.yaml:/etc/loki/local-config.yaml
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - fogis-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3100/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

# Add volume definition at the bottom of the file
volumes:
  grafana-storage:  # Existing volume
  fogis-loki-data:  # ← Add this new volume
    driver: local
```

### Step 6: Start Loki Service

```bash
# Start Loki with new volume configuration
docker-compose up -d loki

# Wait for Loki to start
sleep 10

# Check Loki health
curl -s http://localhost:3100/ready
```

Expected output: `ready`

### Step 7: Verify Loki is Working

```bash
# Check Loki logs
docker logs fogis-loki --tail 50

# Verify Loki is receiving logs
curl -s http://localhost:3100/metrics | grep loki_ingester_streams

# Check Grafana can connect to Loki
curl -s http://localhost:3000/api/health
```

### Step 8: Update .gitignore

Add patterns to prevent accidentally tracking Loki data in the future:

```bash
# Add to .gitignore
cat >> .gitignore << 'EOF'

# Loki monitoring data (now using Docker volumes)
monitoring/loki/chunks/
monitoring/loki/wal/
monitoring/loki/boltdb-shipper-active/
monitoring/loki/boltdb-shipper-cache/
monitoring/loki/boltdb-shipper-compactor/
EOF
```

### Step 9: Clean Up Repository

Remove Loki data directories from the repository:

```bash
# Remove runtime data directories
rm -rf monitoring/loki/chunks
rm -rf monitoring/loki/wal
rm -rf monitoring/loki/boltdb-shipper-active
rm -rf monitoring/loki/boltdb-shipper-cache
rm -rf monitoring/loki/boltdb-shipper-compactor

# Keep the configuration and structure
# monitoring/loki-config.yaml - KEEP
# monitoring/loki/rules/ - KEEP (if exists)

# Verify what's left
ls -la monitoring/loki/
```

### Step 10: Stage Changes for Commit

```bash
# Stage .gitignore changes
git add .gitignore

# Stage docker-compose.yml changes
git add docker-compose.yml

# Stage removal of Loki data directories
git add monitoring/loki/

# Review changes
git status
git diff --cached
```

---

## Verification Checklist

- [ ] Loki service is running: `docker ps | grep loki`
- [ ] Loki is healthy: `curl http://localhost:3100/ready`
- [ ] Grafana can connect to Loki
- [ ] New logs are being ingested
- [ ] Docker volume exists: `docker volume ls | grep fogis-loki-data`
- [ ] Repository is clean: No chunk/wal files in `monitoring/loki/`
- [ ] .gitignore updated to prevent future tracking

---

## Rollback Procedure

If something goes wrong:

```bash
# Stop Loki
docker-compose stop loki

# Restore docker-compose.yml from git
git restore docker-compose.yml

# Restore Loki data from backup (if created)
tar -xzf loki-data-backup-*.tar.gz

# Start Loki with old configuration
docker-compose up -d loki
```

---

## Docker Volume Management

### View Volume Details

```bash
docker volume inspect fogis-loki-data
```

### Backup Volume

```bash
docker run --rm \
  -v fogis-loki-data:/source:ro \
  -v $(pwd):/backup \
  alpine tar -czf /backup/loki-volume-backup-$(date +%Y%m%d-%H%M%S).tar.gz -C /source .
```

### Restore Volume

```bash
docker run --rm \
  -v fogis-loki-data:/dest \
  -v $(pwd):/backup \
  alpine sh -c "cd /dest && tar -xzf /backup/loki-volume-backup-*.tar.gz"
```

### Remove Volume (Caution!)

```bash
# Stop Loki first
docker-compose stop loki

# Remove volume (deletes all data!)
docker volume rm fogis-loki-data
```

---

## Next Steps

After completing the Loki migration:

1. Monitor Loki for 24-48 hours to ensure stability
2. Proceed to Step 3: Review infrastructure files
3. Commit all changes:
   ```bash
   git commit -m "Migrate Loki data to Docker volume and clean up repository"
   ```

---

## Troubleshooting

### Loki won't start

```bash
# Check logs
docker logs fogis-loki

# Check volume permissions
docker run --rm -v fogis-loki-data:/loki alpine ls -la /loki/

# Verify configuration
docker exec fogis-loki cat /etc/loki/local-config.yaml
```

### No logs appearing

```bash
# Check Promtail is running
docker ps | grep promtail

# Check Promtail logs
docker logs fogis-promtail --tail 50

# Verify Promtail can reach Loki
docker exec fogis-promtail wget -O- http://loki:3100/ready
```

### Volume is full

```bash
# Check volume size
docker system df -v | grep fogis-loki-data

# Reduce retention in loki-config.yaml
# Change retention_period from 720h to 168h (7 days)
```
