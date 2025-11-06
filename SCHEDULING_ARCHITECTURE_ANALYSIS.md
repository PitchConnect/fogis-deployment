# Scheduling Architecture Analysis & Recommendations

**Date:** 2025-11-06
**Investigation:** Calendar Sync Scheduling vs Match Processor Scheduling
**Status:** ✅ ANALYSIS COMPLETE

---

## Executive Summary

**Key Findings:**
1. ✅ **Calendar sync service is purely event-driven** - No independent hourly polling
2. ✅ **Match processor is correctly configured** - Hourly processing via `SERVICE_INTERVAL=3600`
3. ⚠️ **Configuration discrepancy exists** - `fogis-config.yaml` has conflicting settings
4. ✅ **Current architecture is sound** - No need for dedicated scheduler service

**Recommendation:** Keep current architecture with improved configuration management.

---

## 1. Calendar Sync Service Analysis

### Investigation Results

**Question:** Does `fogis-calendar-phonebook-sync` have independent hourly polling?

**Answer:** ✅ **NO** - The service is **purely event-driven** via Redis pub/sub.

### Evidence

**Service Architecture:**
```python
# app.py - Calendar sync service
@app.route("/health", methods=["GET"])
def health_check():
    # Only health check endpoint exists

# Redis subscriber runs in background thread
redis_integration = add_redis_to_calendar_app(app, calendar_sync_callback)
# Listens for Redis messages, no scheduled tasks
```

**No Scheduling Found:**
- ❌ No cron jobs
- ❌ No `Timer` objects
- ❌ No `schedule` library usage
- ❌ No `CALENDAR_SYNC_INTERVAL` environment variable used
- ✅ Only Redis pub/sub subscription thread

**Environment Variables:**
```bash
$ docker exec fogis-calendar-phonebook-sync env | grep -E "INTERVAL|SCHEDULE|SYNC"
CALENDAR_SYNC_PORT=9089  # Only port configuration, no scheduling
```

### Conclusion

The calendar sync service is **correctly implemented as a passive consumer**:
- Starts Redis subscriber thread on startup
- Waits for messages on `fogis:matches:updates` channel
- Processes matches when messages arrive
- No independent polling or scheduling

**This is the correct design** ✅

---

## 2. Match Processor Configuration Analysis

### Current Configuration

**Docker Compose Settings:**
```yaml
process-matches-service:
  environment:
    - PROCESSOR_MODE=unified
    - RUN_MODE=service                    # Persistent service mode
    - SERVICE_INTERVAL=3600               # 1 hour (3600 seconds)
    - ENABLE_CHANGE_CATEGORIZATION=true
```

**Actual Runtime Values:**
```bash
$ docker exec process-matches-service env | grep SERVICE_INTERVAL
SERVICE_INTERVAL=3600  # ✅ Correctly set to 1 hour
```

**Service Behavior:**
```python
# src/app_unified.py
self.service_interval = int(os.environ.get("SERVICE_INTERVAL", "300"))  # Default: 5 minutes

# Service loop
while self.running:
    self._process_cycle()

    # Sleep for SERVICE_INTERVAL seconds
    sleep_remaining = self.service_interval
    while sleep_remaining > 0 and self.running:
        time.sleep(1)
        sleep_remaining -= 1
```

### Configuration Discrepancy

**Problem:** `fogis-config.yaml` has conflicting settings:

```yaml
# fogis-config.yaml (NOT USED by Docker Compose)
services:
  processing:
    match_check_schedule: "0 * * * *"   # Cron format (NOT USED)
    service_interval: 300               # 5 minutes (OVERRIDDEN)
```

**Docker Compose Overrides:**
```yaml
# docker-compose.yml (ACTUAL CONFIGURATION)
environment:
  - SERVICE_INTERVAL=3600  # ✅ This is what's actually used
```

### Why This Happened

1. **Image Update:** Container was created on 2025-10-16, restarted on 2025-11-06 21:14
2. **Configuration Source:** Docker Compose environment variables take precedence
3. **Config File Ignored:** `fogis-config.yaml` is not mounted or used by the container
4. **Correct Behavior:** The service IS running hourly as intended

---

## 3. Architecture Evaluation

### Current Design

```
┌─────────────────────────────────────────────────────────────┐
│ match-list-processor (ACTIVE, SCHEDULED)                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Service Loop (SERVICE_INTERVAL=3600)                    │ │
│ │ while running:                                          │ │
│ │   1. Fetch matches from FOGIS API                       │ │
│ │   2. Detect changes vs cached data                      │ │
│ │   3. Publish to Redis (fogis:matches:updates)           │ │
│ │   4. Sleep for 3600 seconds (1 hour)                    │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Redis Pub/Sub
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ fogis-calendar-phonebook-sync (PASSIVE, EVENT-DRIVEN)       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Redis Subscriber Thread                                 │ │
│ │ while True:                                             │ │
│ │   message = redis.listen()                              │ │
│ │   if message.type == "match_updates":                   │ │
│ │     sync_calendar(matches)                              │ │
│ │     update_contacts(referees)                           │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Pros of Current Design

✅ **Clear separation of concerns**
- Match processor: Active scheduler, data fetcher, change detector
- Calendar sync: Passive consumer, event processor

✅ **Reliable scheduling**
- Built into the service itself
- No external dependencies (cron, scheduler service)
- Survives container restarts

✅ **Simple deployment**
- Single container per service
- No additional scheduler infrastructure
- Easy to understand and debug

✅ **Resilient**
- If calendar sync crashes, match processor continues
- If match processor crashes, calendar sync waits for next message
- Docker restart policy handles failures

### Cons of Current Design

⚠️ **Configuration management**
- Multiple sources of truth (docker-compose.yml, fogis-config.yaml, .env.template)
- Easy to have conflicting values
- Not immediately obvious which takes precedence

⚠️ **Limited flexibility**
- Changing schedule requires container restart
- Can't easily adjust schedule without redeployment
- No dynamic schedule adjustment

---

## 4. Alternative: Dedicated Scheduler Service

### Option A: External Cron-based Scheduler

```yaml
fogis-scheduler:
  image: alpine:latest
  command: crond -f -l 2
  volumes:
    - ./crontab:/etc/crontabs/root
  depends_on:
    - process-matches-service
```

**Crontab:**
```cron
0 * * * * curl -X POST http://process-matches-service:8000/trigger
```

**Pros:**
- ✅ Familiar cron syntax
- ✅ Easy to modify schedule without code changes
- ✅ Centralized scheduling

**Cons:**
- ❌ Additional container to manage
- ❌ Requires HTTP endpoint on match processor
- ❌ More complex failure modes
- ❌ Harder to debug
- ❌ Network dependency between containers

### Option B: Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: fogis-match-processor
spec:
  schedule: "0 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: processor
            image: ghcr.io/pitchconnect/match-list-processor:latest
```

**Pros:**
- ✅ Native Kubernetes scheduling
- ✅ Job history and logging
- ✅ Retry policies

**Cons:**
- ❌ Requires Kubernetes (not Docker Compose)
- ❌ More complex infrastructure
- ❌ Overkill for single-user deployment

---

## 5. Recommendations

### Primary Recommendation: Keep Current Architecture ✅

**Rationale:**
1. Current design is working correctly
2. Simple, reliable, easy to understand
3. No external dependencies
4. Appropriate for Docker Compose deployment

### Configuration Improvements

**1. Consolidate Configuration Sources**

Create a single source of truth in `docker-compose.yml`:

```yaml
process-matches-service:
  environment:
    # Scheduling (PRIMARY SOURCE OF TRUTH)
    - SERVICE_INTERVAL=3600  # 1 hour in seconds

    # Document the schedule clearly
    # Equivalent to cron: "0 * * * *" (every hour on the hour)
```

**2. Add Configuration Validation**

Add startup validation in the match processor:

```python
# src/app_unified.py
def validate_configuration(self):
    """Validate configuration on startup."""
    interval = self.service_interval

    if interval < 300:  # Less than 5 minutes
        logger.warning(f"SERVICE_INTERVAL={interval}s is very short. Recommended: 3600s (1 hour)")

    if interval > 86400:  # More than 24 hours
        logger.warning(f"SERVICE_INTERVAL={interval}s is very long. Recommended: 3600s (1 hour)")

    logger.info(f"✅ Scheduling configured: Processing every {interval}s ({interval/3600:.1f} hours)")
```

**3. Update Documentation**

Add clear comments in `docker-compose.yml`:

```yaml
# Match list processor - Scheduled processing every hour
process-matches-service:
  environment:
    # SCHEDULING CONFIGURATION
    # ========================
    # SERVICE_INTERVAL: Time in seconds between processing cycles
    # Default: 3600 (1 hour)
    #
    # Common values:
    #   - 1800  = 30 minutes
    #   - 3600  = 1 hour (RECOMMENDED)
    #   - 7200  = 2 hours
    #   - 14400 = 4 hours
    - SERVICE_INTERVAL=3600
```

**4. Remove Conflicting Configuration**

Update `fogis-config.yaml` to clarify it's not used for scheduling:

```yaml
services:
  processing:
    # NOTE: Scheduling is configured in docker-compose.yml via SERVICE_INTERVAL
    # The match_check_schedule cron format is NOT used in Docker Compose deployments
    # match_check_schedule: "0 * * * *"  # DEPRECATED - Use SERVICE_INTERVAL instead

    min_referees_for_whatsapp: 2
    force_fresh_processing: true
```

---

## 6. Implementation Plan

### Phase 1: Documentation (Immediate)

- [x] Document current architecture
- [ ] Add comments to docker-compose.yml
- [ ] Update fogis-config.yaml with deprecation notices
- [ ] Create SCHEDULING_ARCHITECTURE.md (this document)

### Phase 2: Validation (Next Deployment)

- [ ] Add configuration validation on startup
- [ ] Log scheduling configuration clearly
- [ ] Add health check for scheduling status

### Phase 3: Monitoring (Future Enhancement)

- [ ] Add metrics for processing cycle timing
- [ ] Alert if processing cycles are skipped
- [ ] Dashboard showing last processing time

---

## 7. Conclusion

**Current State:** ✅ **WORKING CORRECTLY**

- Match processor runs hourly (`SERVICE_INTERVAL=3600`)
- Calendar sync is purely event-driven (no independent polling)
- Architecture is sound and appropriate for the use case

**Action Required:** 📝 **DOCUMENTATION ONLY**

- Clarify configuration precedence
- Remove conflicting settings
- Add validation and logging

**No Code Changes Needed** - The system is functioning as designed.

---

## Appendix: Configuration Precedence

**Order of precedence (highest to lowest):**

1. **Docker Compose `environment:`** ← **WINNER** (Currently used)
2. **Docker Compose `env_file:`** (`.env` file)
3. **Container default values** (hardcoded in code)
4. **fogis-config.yaml** ← NOT USED (file not mounted)

**Current effective configuration:**
```bash
SERVICE_INTERVAL=3600  # From docker-compose.yml environment
RUN_MODE=service       # From docker-compose.yml environment
PROCESSOR_MODE=unified # From docker-compose.yml environment
```
