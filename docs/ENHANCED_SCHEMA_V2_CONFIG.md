# Enhanced Schema v2.0 Configuration Guide

## Overview

This guide documents the environment variable configuration for Enhanced Schema v2.0 implementation in the FOGIS deployment system. Enhanced Schema v2.0 provides corrected Organization ID mapping for logo service integration and complete contact data for calendar sync.

## Key Features

- **Organization ID Mapping**: Uses `lag1foreningid`/`lag2foreningid` for logo service integration
- **Complete Contact Data**: Full referee and team contact information for calendar sync
- **Multi-Version Publishing**: Supports both v1.0 (legacy) and v2.0 (enhanced) schemas
- **Backward Compatibility**: Existing services continue working with v1.0 schema

## Environment Variables

### Match List Processor Service

#### Redis Configuration
```bash
# Basic Redis connection
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_ENABLED=true

# Enhanced Schema v2.0 configuration
REDIS_SCHEMA_VERSION=2.0          # Primary schema version
REDIS_PUBLISH_LEGACY=true         # Publish v1.0 for backward compatibility
REDIS_PUBLISH_V1=true             # Explicitly publish v1.0 schema
REDIS_PUBLISH_V2=true             # Explicitly publish v2.0 schema
```

#### Logo Service Integration
```bash
# Logo service configuration
LOGO_COMBINER_URL=http://team-logo-combiner:5002
LOGO_SERVICE_ENABLED=true
```

### Calendar Service (fogis-calendar-phonebook-sync)

#### Redis Subscription Configuration
```bash
# Basic Redis connection
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_ENABLED=true

# Enhanced Schema v2.0 subscription
REDIS_SCHEMA_VERSION=2.0          # Primary schema version to subscribe to
REDIS_FALLBACK_SCHEMAS=1.5,1.0    # Fallback schema versions
REDIS_SUBSCRIPTION_TIMEOUT=30     # Subscription timeout in seconds
```

#### Logo Service Integration
```bash
# Logo service configuration
LOGO_COMBINER_URL=http://team-logo-combiner:5002
LOGO_SERVICE_ENABLED=true
LOGO_CACHE_ENABLED=true
```

## Schema Version Details

### Enhanced Schema v2.0 Structure

```json
{
  "schema_version": "2.0",
  "schema_type": "enhanced_with_contacts_and_logo_ids",
  "backward_compatible": true,
  "new_fields": ["teams.home.logo_id", "teams.away.logo_id", "team_contacts", "referees.contact"],
  "message_id": "uuid",
  "timestamp": "2025-09-26T10:30:00Z",
  "source": "match-list-processor",
  "payload": {
    "matches": [
      {
        "match_id": 6170049,
        "teams": {
          "home": {
            "name": "Lindome GIF",
            "id": 26405,                    // Database reference (lag1lagid)
            "logo_id": 10741,              // Organization ID for logo service (lag1foreningid)
            "organization_id": 10741
          },
          "away": {
            "name": "Jonsereds IF",
            "id": 25562,                    // Database reference (lag2lagid)
            "logo_id": 9595,               // Organization ID for logo service (lag2foreningid)
            "organization_id": 9595
          }
        },
        "referees": [
          {
            "name": "Bartek Svaberg",
            "role": "Huvuddomare",
            "contact": {
              "mobile": "0709423055",
              "email": "bartek.svaberg@gmail.com",
              "address": {
                "street": "Lilla Tulteredsvägen 50",
                "postal_code": "43331",
                "city": "Partille"
              }
            }
          }
        ],
        "team_contacts": [
          {
            "name": "Morgan Johansson",
            "team_name": "Landvetter IS Senior",
            "contact": {
              "mobile": "0733472740",
              "email": "morgan@kalltorpsbygg.se"
            }
          }
        ]
      }
    ],
    "detailed_changes": [
      {
        "field": "avsparkstid",
        "from": "19:00",
        "to": "19:15",
        "category": "time_change",
        "priority": "high"
      }
    ]
  }
}
```

### Legacy Schema v1.0 Structure

```json
{
  "schema_version": "1.0",
  "message_id": "uuid",
  "timestamp": "2025-09-26T10:30:00Z",
  "source": "match-list-processor",
  "payload": {
    "matches": [
      {
        "match_id": 6170049,
        "teams": "Lindome GIF vs Jonsereds IF",
        "date": "2025-09-19",
        "time": "19:00",
        "venue": "Lindome IP",
        "referees": ["Bartek Svaberg"]
      }
    ]
  }
}
```

## Redis Channel Configuration

### Publishing Channels (Match List Processor)

- **`match_updates`**: Default channel (Enhanced Schema v2.0)
- **`match_updates_v2`**: Explicit Enhanced Schema v2.0 channel
- **`match_updates_v1`**: Legacy Schema v1.0 channel

### Subscription Channels (Calendar Service)

- **Primary**: `match_updates` or `match_updates_v2` for Enhanced Schema v2.0
- **Fallback**: `match_updates_v1` for Legacy Schema v1.0

## Logo Service Integration

### Organization ID Mapping

Enhanced Schema v2.0 correctly maps Organization IDs for logo service integration:

- **Home Team Logo ID**: `match.lag1foreningid` → `teams.home.logo_id`
- **Away Team Logo ID**: `match.lag2foreningid` → `teams.away.logo_id`

### Logo Service Validation

```bash
# Test logo service with Organization IDs
curl -X POST http://localhost:9088/create_avatar \
     -H "Content-Type: application/json" \
     -d '{"team1_id": "10741", "team2_id": "9595"}' \
     --output test_logo.png

# Validate logo size (should be > 100KB for real logos)
logo_size=$(wc -c < test_logo.png)
if [ $logo_size -gt 100000 ]; then
    echo "✅ Logo service integration successful: ${logo_size} bytes"
else
    echo "❌ Logo service integration failed: ${logo_size} bytes (fallback logos)"
fi
```

## Performance Configuration

### Redis Performance Tuning

```bash
# Performance tuning environment variables
REDIS_SUBSCRIPTION_TIMEOUT=30      # Subscription timeout
REDIS_MESSAGE_SIZE_LIMIT=5120      # 5KB message size limit
REDIS_CONNECTION_POOL_SIZE=10      # Connection pool size
```

### Logo Service Performance

```bash
# Logo service performance configuration
LOGO_SERVICE_TIMEOUT=30            # Logo service request timeout
LOGO_CACHE_ENABLED=true           # Enable logo caching
```

## Deployment Validation

### Environment Variable Validation

```bash
# Validate Enhanced Schema v2.0 configuration
echo "REDIS_SCHEMA_VERSION: $REDIS_SCHEMA_VERSION"
echo "REDIS_PUBLISH_LEGACY: $REDIS_PUBLISH_LEGACY"
echo "LOGO_SERVICE_ENABLED: $LOGO_SERVICE_ENABLED"

# Expected output:
# REDIS_SCHEMA_VERSION: 2.0
# REDIS_PUBLISH_LEGACY: true
# LOGO_SERVICE_ENABLED: true
```

### Service Connectivity Validation

```bash
# Test Redis connectivity
docker exec fogis-redis redis-cli ping

# Test logo service connectivity
curl -f http://localhost:9088/health

# Test calendar service Enhanced Schema v2.0 subscription
curl -f http://localhost:9083/health
```

## Troubleshooting

### Common Issues

1. **Logo Service Returns Fallback Images**
   - Check Organization ID mapping in Enhanced Schema v2.0
   - Validate `lag1foreningid`/`lag2foreningid` values
   - Test logo service with known Organization IDs

2. **Calendar Service Not Receiving Enhanced Data**
   - Verify `REDIS_SCHEMA_VERSION=2.0` in calendar service
   - Check Redis channel subscriptions
   - Validate Enhanced Schema v2.0 message format

3. **Backward Compatibility Issues**
   - Ensure `REDIS_PUBLISH_LEGACY=true` in match processor
   - Verify v1.0 schema publishing to `match_updates_v1` channel
   - Check fallback schema configuration in calendar service

### Debugging Commands

```bash
# Monitor Redis channels
docker exec fogis-redis redis-cli MONITOR

# Check Enhanced Schema v2.0 messages
docker exec fogis-redis redis-cli PSUBSCRIBE "match_updates*"

# Validate message sizes
docker logs process-matches-service | grep "Enhanced Schema"
```

## Migration Guide

### From v1.0 to v2.0

1. **Update Environment Variables**: Add Enhanced Schema v2.0 configuration
2. **Deploy Services**: Update match-list-processor and calendar service
3. **Validate Integration**: Test logo service and contact data
4. **Monitor Performance**: Check Redis message sizes and processing times

### Rollback Procedure

1. **Set Schema Version**: `REDIS_SCHEMA_VERSION=1.0`
2. **Disable v2.0 Publishing**: `REDIS_PUBLISH_V2=false`
3. **Restart Services**: Restart match-list-processor and calendar service
4. **Validate Fallback**: Ensure v1.0 schema continues working

---

**Implementation Status**: ✅ Ready for deployment
**Last Updated**: 2025-09-26
**Version**: Enhanced Schema v2.0
