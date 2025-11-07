# Configuration Improvements - Preventing Future Issues

**Date:** 2025-11-06
**Purpose:** Prevent configuration drift and ensure reliable scheduling
**Priority:** HIGH

---

## Problem Statement

During the referee hash bug investigation, we discovered:

1. **Stale cache issue:** Match processor hadn't picked up the 4th referee (Magnus Lindgren) because it hadn't run since 06:27:44
2. **Configuration discrepancy:** `fogis-config.yaml` specifies `service_interval: 300` (5 minutes) but Docker Compose uses `SERVICE_INTERVAL=3600` (1 hour)
3. **Multiple sources of truth:** Configuration exists in 3 places with different values

**Impact:** If Docker Compose configuration is accidentally removed or reset, the service could revert to a 5-minute interval (too frequent) or fail to schedule at all.

---

## Recommended Solutions

### Solution 1: Explicit Defaults in Docker Compose ✅ RECOMMENDED

**Approach:** Make Docker Compose the single source of truth with explicit, well-documented values.

**Implementation:**

```yaml
# docker-compose.yml
process-matches-service:
  image: ghcr.io/pitchconnect/match-list-processor:latest
  container_name: process-matches-service
  command: ["python", "-m", "src.app_unified"]
  environment:
    # ============================================================================
    # SCHEDULING CONFIGURATION
    # ============================================================================
    # SERVICE_INTERVAL: Time in seconds between processing cycles
    #
    # IMPORTANT: This is the PRIMARY configuration for scheduling.
    # Do NOT rely on fogis-config.yaml for scheduling in Docker deployments.
    #
    # Recommended values:
    #   - 1800  = 30 minutes (for testing/development)
    #   - 3600  = 1 hour (PRODUCTION RECOMMENDED)
    #   - 7200  = 2 hours (low-frequency updates)
    #
    # Current setting: 1 hour (3600 seconds)
    # ============================================================================
    - SERVICE_INTERVAL=${SERVICE_INTERVAL:-3600}

    # ============================================================================
    # PROCESSOR MODE CONFIGURATION
    # ============================================================================
    - PROCESSOR_MODE=unified
    - RUN_MODE=service
    - ENABLE_CHANGE_CATEGORIZATION=true

    # ... rest of configuration
```

**Benefits:**
- ✅ Clear documentation in the file that matters
- ✅ Default value (`:-3600`) ensures fallback if env var missing
- ✅ Easy to override via `.env` file if needed
- ✅ No code changes required

---

### Solution 2: Startup Validation ✅ RECOMMENDED

**Approach:** Add validation checks when the service starts to catch configuration issues early.

**Implementation:**

Add to `src/app_unified.py`:

```python
def validate_and_log_configuration(self):
    """Validate configuration and log scheduling details."""
    interval = self.service_interval
    run_mode = self.run_mode

    # Log configuration
    logger.info("=" * 60)
    logger.info("SCHEDULING CONFIGURATION")
    logger.info("=" * 60)
    logger.info(f"Run Mode: {run_mode}")
    logger.info(f"Service Interval: {interval} seconds ({interval/60:.1f} minutes, {interval/3600:.2f} hours)")
    logger.info(f"Equivalent Cron: Every {interval/3600:.0f} hour(s)")

    # Validation warnings
    if interval < 300:  # Less than 5 minutes
        logger.warning("⚠️  SERVICE_INTERVAL is very short (<5 minutes). This may cause excessive API calls.")
        logger.warning("⚠️  Recommended: 3600 (1 hour) for production")

    if interval > 86400:  # More than 24 hours
        logger.warning("⚠️  SERVICE_INTERVAL is very long (>24 hours). Match updates may be delayed.")
        logger.warning("⚠️  Recommended: 3600 (1 hour) for production")

    if run_mode != "service":
        logger.warning(f"⚠️  RUN_MODE={run_mode} - Service will not run continuously")

    logger.info("=" * 60)

    # Return validation status
    return 300 <= interval <= 86400  # Valid range: 5 minutes to 24 hours
```

**Call during initialization:**

```python
def __init__(self, is_test_mode: bool = False):
    # ... existing initialization ...

    # Validate configuration
    if not self.validate_and_log_configuration():
        logger.error("❌ Configuration validation failed!")
        logger.error("❌ Service may not behave as expected")
    else:
        logger.info("✅ Configuration validation passed")
```

**Benefits:**
- ✅ Immediate feedback on startup
- ✅ Clear logging of actual configuration
- ✅ Catches misconfiguration before it causes issues
- ✅ Helps with debugging

---

### Solution 3: Health Check Enhancement ✅ RECOMMENDED

**Approach:** Add scheduling status to health check endpoint.

**Implementation:**

Add to health check response:

```python
@app.route("/health", methods=["GET"])
def health_check():
    """Enhanced health check with scheduling status."""

    # Calculate time since last processing cycle
    time_since_last_cycle = time.time() - last_processing_time
    next_cycle_in = service_interval - time_since_last_cycle

    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "scheduling": {
            "interval_seconds": service_interval,
            "interval_hours": round(service_interval / 3600, 2),
            "last_cycle": datetime.fromtimestamp(last_processing_time).isoformat(),
            "seconds_since_last_cycle": int(time_since_last_cycle),
            "next_cycle_in_seconds": int(max(0, next_cycle_in)),
            "cycles_completed": cycle_count
        }
    }

    return jsonify(health_data), 200
```

**Benefits:**
- ✅ External monitoring can verify scheduling
- ✅ Easy to check if service is running on schedule
- ✅ Helps diagnose "why hasn't it run?" issues

---

### Solution 4: Configuration File Cleanup ⚠️ OPTIONAL

**Approach:** Remove or deprecate unused configuration in `fogis-config.yaml`.

**Implementation:**

```yaml
# fogis-config.yaml
services:
  processing:
    min_referees_for_whatsapp: 2
    force_fresh_processing: true

    # DEPRECATED: The following settings are NOT used in Docker Compose deployments
    # Scheduling is configured via docker-compose.yml environment variables
    #
    # match_check_schedule: "0 * * * *"   # NOT USED - See docker-compose.yml SERVICE_INTERVAL
    # service_interval: 300               # NOT USED - See docker-compose.yml SERVICE_INTERVAL
```

**Benefits:**
- ✅ Reduces confusion
- ✅ Makes it clear where configuration lives
- ⚠️ May break non-Docker deployments (if any exist)

---

### Solution 5: Monitoring & Alerting 🔮 FUTURE

**Approach:** Add monitoring to detect when processing cycles are missed.

**Implementation:**

```python
# Prometheus metrics
from prometheus_client import Counter, Gauge, Histogram

processing_cycles_total = Counter('fogis_processing_cycles_total', 'Total processing cycles completed')
processing_cycle_duration = Histogram('fogis_processing_cycle_duration_seconds', 'Processing cycle duration')
time_since_last_cycle = Gauge('fogis_time_since_last_cycle_seconds', 'Time since last processing cycle')

# Update metrics
processing_cycles_total.inc()
processing_cycle_duration.observe(cycle_duration)
time_since_last_cycle.set(time.time() - last_cycle_time)
```

**Alert Rules:**

```yaml
# Prometheus alert
- alert: FogisProcessingStalled
  expr: fogis_time_since_last_cycle_seconds > 7200  # 2 hours
  for: 5m
  annotations:
    summary: "FOGIS processing has stalled"
    description: "No processing cycle in {{ $value }} seconds"
```

**Benefits:**
- ✅ Proactive detection of issues
- ✅ Historical data for analysis
- ⚠️ Requires Prometheus infrastructure

---

## Implementation Priority

### Phase 1: Immediate (This Week)

1. ✅ **Update docker-compose.yml** with detailed comments and default values
2. ✅ **Add startup validation** to log configuration clearly
3. ✅ **Document architecture** (SCHEDULING_ARCHITECTURE_ANALYSIS.md)

### Phase 2: Next Deployment (Next Week)

4. ⚠️ **Enhance health check** with scheduling status
5. ⚠️ **Clean up fogis-config.yaml** with deprecation notices

### Phase 3: Future Enhancement (Next Month)

6. 🔮 **Add Prometheus metrics** for monitoring
7. 🔮 **Set up alerting** for stalled processing

---

## Testing the Changes

### Test 1: Verify Default Value

```bash
# Remove SERVICE_INTERVAL from environment
docker-compose down
# Edit docker-compose.yml, remove SERVICE_INTERVAL line
docker-compose up -d process-matches-service

# Check logs - should show 3600 (default)
docker logs process-matches-service | grep "Service Interval"
# Expected: "Service Interval: 3600 seconds (60.0 minutes, 1.00 hours)"
```

### Test 2: Verify Override

```bash
# Set custom value via .env
echo "SERVICE_INTERVAL=1800" >> .env
docker-compose up -d process-matches-service

# Check logs - should show 1800 (30 minutes)
docker logs process-matches-service | grep "Service Interval"
# Expected: "Service Interval: 1800 seconds (30.0 minutes, 0.50 hours)"
```

### Test 3: Verify Validation

```bash
# Set invalid value (too short)
echo "SERVICE_INTERVAL=60" >> .env
docker-compose up -d process-matches-service

# Check logs - should show warning
docker logs process-matches-service | grep "WARNING"
# Expected: "⚠️  SERVICE_INTERVAL is very short (<5 minutes)"
```

---

## Rollback Plan

If changes cause issues:

1. **Revert docker-compose.yml** to previous version
2. **Restart services:** `docker-compose restart process-matches-service`
3. **Verify scheduling:** `docker logs process-matches-service | grep "Service Interval"`

---

## Success Criteria

✅ **Configuration is clear and documented**
✅ **Default values prevent misconfiguration**
✅ **Startup logs show scheduling configuration**
✅ **Health check includes scheduling status**
✅ **No more "why didn't it run?" questions**

---

## Related Documents

- `SCHEDULING_ARCHITECTURE_ANALYSIS.md` - Architecture overview
- `CALENDAR_SYNC_REFEREE_HASH_FIX.md` - Original bug that led to this investigation
- `REFEREE_HASH_FIX_SUMMARY.md` - Summary of referee hash fix
