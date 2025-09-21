# Redis Pub/Sub Integration for Calendar Service

This directory contains minimal Redis pub/sub integration for the FOGIS calendar service to receive real-time match updates from the match-list-processor.

## Overview

The calendar service Redis integration enables real-time calendar synchronization by subscribing to match updates published by the match-list-processor via Redis pub/sub, while maintaining full backward compatibility with existing HTTP endpoints.

## Integration Approach

### Minimal Integration Philosophy
- **Non-invasive**: Adds Redis functionality without modifying existing calendar service code
- **Optional enhancement**: Redis improves responsiveness but HTTP endpoints remain functional
- **Graceful degradation**: Service works normally if Redis is unavailable
- **Background operation**: Redis subscription runs in background thread

### Components

#### 1. `redis_pubsub_integration.py` (280 lines)
Core Redis pub/sub client for calendar service:
```python
from redis_pubsub_integration import subscribe_to_match_updates

def handle_matches(matches, metadata):
    # Your existing calendar sync logic
    sync_matches_to_calendar(matches)

# Start Redis subscription
subscribe_to_match_updates(handle_matches)
```

#### 2. `app_redis_integration.py` (200 lines)
Flask app integration for Redis pub/sub:
```python
from app_redis_integration import integrate_redis_with_flask_app

# Add to existing Flask app
redis_integration = integrate_redis_with_flask_app(app)
```

#### 3. `integrate_with_existing_app.py` (250 lines)
Simple integration script for existing calendar service:
```python
from integrate_with_existing_app import start_minimal_redis_integration

# Start Redis integration in background
start_minimal_redis_integration()
```

#### 4. `Dockerfile.redis-patch`
Docker build patch to add Redis functionality to existing calendar service image.

## Usage

### Option 1: Docker Integration (Recommended)
Use the Dockerfile patch to build an enhanced calendar service image:

```bash
# Build enhanced calendar service with Redis
docker build -f local-patches/fogis-calendar-phonebook-sync/Dockerfile.redis-patch \
  -t fogis-calendar-service-redis:latest .

# Update docker-compose.yml to use enhanced image
# Change: image: ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest
# To:     image: fogis-calendar-service-redis:latest
```

### Option 2: Runtime Integration
Add Redis integration to existing calendar service at runtime:

```python
# Add to existing calendar service startup
from integrate_with_existing_app import integrate_with_flask_app

# If using Flask
redis_integration = integrate_with_flask_app(app)

# Or for general service startup
from integrate_with_existing_app import integrate_with_service_startup
integrate_with_service_startup()
```

### Option 3: Custom Integration
Integrate with existing calendar sync logic:

```python
from integrate_with_existing_app import integrate_with_existing_sync_function

def my_calendar_sync(matches):
    # Your existing calendar sync logic
    for match in matches:
        create_calendar_event(match)

# Connect Redis to existing sync function
integrate_with_existing_sync_function(my_calendar_sync)
```

## Architecture

### Before Integration
```
[Match-List-Processor] --HTTP POST--> [Calendar Service /sync endpoint]
```

### After Integration
```
[Match-List-Processor] --Redis Pub/Sub--> [Calendar Service Redis Subscriber]
                      \                   /
                       --HTTP (fallback)--
```

### Benefits
- **Real-time updates**: Immediate calendar sync when matches change
- **Reduced latency**: No HTTP request overhead
- **Reliable fallback**: HTTP endpoints remain available
- **Scalable**: Multiple calendar services can subscribe
- **Event-driven**: Only sync when changes occur

## Configuration

### Environment Variables
Calendar service automatically receives Redis configuration:
```yaml
environment:
  - REDIS_URL=redis://redis:6379
  - REDIS_PUBSUB_ENABLED=true  # Enable/disable Redis pub/sub
```

### Redis Channels
- `fogis_matches`: Match updates from match-list-processor
- `fogis_status`: Processing status updates

## Monitoring

### Health Endpoints
Enhanced calendar service includes Redis status endpoints:

```bash
# Check Redis integration status
curl http://localhost:9083/redis-status

# Test Redis functionality
curl -X POST http://localhost:9083/redis-test
```

### Logging
Redis integration provides detailed logging:
```
✅ Redis pub/sub integration enabled for calendar service
📡 Subscribed to match updates from match-list-processor
📅 Received 15 matches via Redis pub/sub
🗓️ Triggering calendar sync for 15 matches...
✅ Calendar sync triggered successfully (sync #3)
```

## Integration Examples

### Flask App Integration
```python
from flask import Flask
from integrate_with_existing_app import integrate_with_flask_app

app = Flask(__name__)

# Your existing routes
@app.route('/sync', methods=['POST'])
def sync_endpoint():
    # Existing HTTP sync logic
    pass

# Add Redis integration
redis_integration = integrate_with_flask_app(app)

if __name__ == '__main__':
    app.run()
```

### Service Startup Integration
```python
import threading
from integrate_with_existing_app import start_minimal_redis_integration

def main():
    # Start your existing calendar service
    start_calendar_service()
    
    # Start Redis integration in background
    redis_thread = threading.Thread(
        target=start_minimal_redis_integration, 
        daemon=True
    )
    redis_thread.start()
    
    # Continue with existing service logic
    run_service_loop()
```

### Custom Sync Function Integration
```python
from integrate_with_existing_app import integrate_with_existing_sync_function

def existing_calendar_sync(matches):
    """Your existing calendar sync logic."""
    for match in matches:
        # Create/update calendar events
        event = create_calendar_event(match)
        calendar_api.events().insert(calendarId='primary', body=event).execute()

# Connect Redis to existing function
integrate_with_existing_sync_function(existing_calendar_sync)
```

## Backward Compatibility

### Existing Functionality Preserved
- All existing HTTP endpoints continue to work
- Existing calendar sync logic unchanged
- Existing authentication and OAuth flows preserved
- No breaking changes to service interface

### Graceful Degradation
- Service works normally if Redis is unavailable
- HTTP sync endpoints remain as fallback
- No service failures due to Redis issues
- Automatic reconnection if Redis becomes available

## Troubleshooting

### Redis Not Available
If Redis is unavailable, calendar service continues using HTTP endpoints:
```
⚠️ Redis not available - calendar service will use HTTP endpoints only
```

### Redis Connection Issues
Check Redis connectivity:
```bash
# Test Redis directly
docker exec fogis-redis redis-cli ping

# Check calendar service Redis status
curl http://localhost:9083/redis-status
```

### Integration Issues
Verify Redis client installation:
```bash
# Check if Redis client is available
docker exec fogis-calendar-phonebook-sync python -c "import redis; print('Redis client available')"
```

## Implementation Details

### Code Changes Summary
- **New files**: 4 files (~1000 lines total)
- **Existing code modified**: 0 lines (non-invasive integration)
- **Integration approach**: Additive enhancement, not replacement
- **Deployment impact**: Optional Docker image rebuild

### Design Principles
1. **Non-invasive**: No changes to existing calendar service code
2. **Optional**: Redis enhances but doesn't replace existing functionality
3. **Backward compatible**: All existing functionality preserved
4. **Graceful degradation**: Service works without Redis
5. **Production ready**: Uses background threads and error handling

This integration provides the requested Redis pub/sub functionality while respecting the existing, proven calendar service architecture.
