# Match Processor Service Behavior Guide

## Overview

The `match-list-processor` service is designed to process FOGIS match data, create WhatsApp assets, upload files to Google Drive, and trigger calendar synchronization. This guide explains the service's intended behavior and addresses common misconceptions about its operation.

## Service Operation Mode

### Current Behavior (Intended Design)

The match processor operates in a **process-and-exit** pattern:

1. **Startup**: Service starts and initializes health server
2. **Processing**: Fetches matches, processes data, creates assets
3. **Upload**: Uploads WhatsApp assets to Google Drive
4. **Calendar Sync**: Triggers calendar synchronization
5. **Completion**: Saves state and gracefully shuts down
6. **Restart**: Docker automatically restarts the service (restart policy: `unless-stopped`)

### Why This Pattern?

```yaml
# Docker Compose Configuration
match-list-processor:
  restart: unless-stopped
  environment:
    - RUN_MODE=service
    - FORCE_FRESH_PROCESSING=true  # For migration scenarios
```

**Benefits:**
- ✅ **Clean state**: Each run starts with fresh environment
- ✅ **Resource efficiency**: No persistent memory usage between runs
- ✅ **Error recovery**: Automatic restart on failures
- ✅ **Consistent processing**: Predictable execution pattern

## Service Health and Monitoring

### Health Check Behavior

The service provides health endpoints during active processing:

```bash
# Check health during processing window
curl -s http://localhost:9082/health | jq .

# Expected response during processing:
{
  "status": "healthy",
  "dependencies": {
    "fogis_api": "healthy",
    "google_drive": "healthy",
    "calendar_sync": "healthy"
  }
}
```

### Monitoring Service Activity

```bash
# Check current container status
docker ps | grep match-list-processor

# View processing logs
docker logs match-list-processor --tail 50

# Monitor for successful processing
docker logs match-list-processor | grep -E "(uploaded|Google Drive|calendar sync)"
```

## Processing Modes

### Fresh Processing Mode

For migration and testing scenarios:

```yaml
environment:
  - FORCE_FRESH_PROCESSING=true
```

**Behavior:**
- Processes all matches regardless of previous state
- Creates WhatsApp assets for all matches
- Uploads all assets to Google Drive
- Triggers calendar sync for all matches

### Incremental Processing Mode

For production operation:

```yaml
environment:
  - FORCE_FRESH_PROCESSING=false
```

**Behavior:**
- Compares current matches with previous state
- Only processes new or modified matches
- Skips unchanged matches for efficiency
- Maintains state between runs

## Expected Log Patterns

### Successful Processing Cycle

```
2025-07-18 13:01:39,203 - INFO - Starting match list processor...
2025-07-18 13:01:39,203 - INFO - Starting health server on port 8000...
2025-07-18 13:01:39,518 - INFO - Health server started on port 8000
2025-07-18 13:01:39,606 - INFO - Health server starting up...
2025-07-18 13:01:39,203 - INFO - Found 6 matches to process
2025-07-18 13:01:40,123 - INFO - Creating WhatsApp group description for match 6144642
2025-07-18 13:01:41,456 - INFO - File uploaded to Google Drive: https://drive.google.com/file/d/...
2025-07-18 13:01:42,789 - INFO - Triggering calendar sync...
2025-07-18 13:01:43,203 - INFO - Match list processor execution finished.
2025-07-18 13:01:43,205 - INFO - Shutting down health server...
2025-07-18 13:01:43,987 - INFO - Health server stopped
```

### Key Success Indicators

- ✅ **Health server starts**: Service is operational
- ✅ **Matches processed**: Data fetching and processing working
- ✅ **Files uploaded**: Google Drive integration functional
- ✅ **Calendar sync triggered**: End-to-end workflow complete
- ✅ **Graceful shutdown**: Clean completion

## Troubleshooting

### "Service Keeps Restarting"

**This is normal behavior**, not an error. The service is designed to:
1. Complete its work
2. Exit cleanly
3. Restart automatically via Docker

**Verification:**
```bash
# Check if processing is successful
docker logs match-list-processor | grep -E "(uploaded|calendar sync|execution finished)"

# If you see these messages, the service is working correctly
```

### No Processing Activity

**Check configuration:**
```bash
# Verify FORCE_FRESH_PROCESSING setting
docker exec match-list-processor env | grep FORCE_FRESH_PROCESSING

# Check for previous state that might prevent processing
ls -la data/match-list-processor/previous_matches.json
```

**Force fresh processing:**
```bash
# Remove previous state to force reprocessing
rm -f data/match-list-processor/previous_matches.json

# Restart service
docker restart match-list-processor
```

### Health Endpoint Not Available

**Expected behavior**: Health endpoint is only available during active processing.

```bash
# Check if service is currently processing
docker ps | grep match-list-processor

# If container shows "Restarting", wait for next processing cycle
# If container is "Up", health endpoint should be available
```

### Processing Errors

**Check dependencies:**
```bash
# Verify FOGIS API access
curl -s http://localhost:9081/health

# Verify Google Drive service
curl -s http://localhost:9085/health

# Verify calendar sync service
curl -s http://localhost:9083/health
```

## Performance Expectations

### Processing Time

Typical processing cycle:
- **Startup**: 2-3 seconds
- **Match processing**: 1-2 seconds per match
- **Asset creation**: 2-3 seconds per match
- **Google Drive upload**: 1-2 seconds per file
- **Calendar sync**: 3-5 seconds
- **Shutdown**: 1-2 seconds

**Total cycle time**: 30-60 seconds for 6 matches

### Resource Usage

- **Memory**: ~100-200MB during processing
- **CPU**: Moderate usage during asset creation
- **Network**: Upload bandwidth for Google Drive
- **Disk**: Temporary files during processing

## Configuration Best Practices

### For Migration/Testing

```yaml
match-list-processor:
  environment:
    - FORCE_FRESH_PROCESSING=true
    - RUN_MODE=service
  restart: unless-stopped
```

### For Production

```yaml
match-list-processor:
  environment:
    - FORCE_FRESH_PROCESSING=false
    - RUN_MODE=service
  restart: unless-stopped
```

### Monitoring Setup

```bash
# Create monitoring script
cat > monitor_processor.sh << 'EOF'
#!/bin/bash
while true; do
    echo "$(date): Checking processor status..."
    
    # Check if container is running
    if docker ps | grep -q match-list-processor; then
        echo "  ✅ Container running"
        
        # Check health if available
        if curl -s http://localhost:9082/health >/dev/null 2>&1; then
            echo "  ✅ Health endpoint responding"
        else
            echo "  ⏳ Processing cycle (health endpoint not available)"
        fi
    else
        echo "  ⚠️ Container not running"
    fi
    
    # Check recent processing activity
    recent_uploads=$(docker logs match-list-processor --since 5m 2>/dev/null | grep -c "uploaded to Google Drive" || echo 0)
    if [ "$recent_uploads" -gt 0 ]; then
        echo "  ✅ Recent processing activity: $recent_uploads uploads"
    fi
    
    echo ""
    sleep 30
done
EOF

chmod +x monitor_processor.sh
```

## Integration Points

### Calendar Sync Integration

The processor triggers calendar sync via HTTP:

```bash
# Manual trigger (for testing)
curl -X POST http://localhost:9083/sync
```

### Google Drive Integration

Files are uploaded with specific naming patterns:

```
WhatsApp Group Description - [Match ID].txt
WhatsApp Group Avatar - [Match ID].png
```

### State Management

Processing state is maintained in:

```
data/match-list-processor/previous_matches.json
```

## Summary

The match processor service operates correctly when:
- ✅ Container restarts regularly (every 1-2 minutes)
- ✅ Processing logs show successful match handling
- ✅ Files are uploaded to Google Drive
- ✅ Calendar sync is triggered
- ✅ Health endpoint responds during processing windows

**This restart pattern is the intended design, not a bug.** The service completes its work and exits cleanly, allowing Docker to restart it for the next processing cycle.
