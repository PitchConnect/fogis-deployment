# Redis Schema Evolution Strategy

## Schema Versioning Framework

### Version Header Structure
```json
{
  "schema_version": "2.0",
  "schema_type": "enhanced_with_contacts",
  "backward_compatible": true,
  "deprecated_fields": [],
  "new_fields": ["team_contacts", "referees.contact"],
  "message_id": "uuid",
  "timestamp": "2025-09-26T10:30:00Z",
  "source": "match-list-processor",
  "payload": { /* match data */ }
}
```

## Schema Evolution Levels

### Level 1: Simplified (Current - v1.0)
- **Size**: 203 bytes
- **Fields**: 6 basic fields
- **Use Case**: Basic notifications
- **Status**: Maintained for backward compatibility

### Level 2: Enhanced Structure (v1.5)
- **Size**: 1.1 KB
- **Fields**: Structured data without contacts
- **Use Case**: Rich notifications, basic integrations
- **Status**: Intermediate option

### Level 3: Enhanced with Contacts (v2.0) - RECOMMENDED
- **Size**: 3.6 KB
- **Fields**: Complete functional data including contacts
- **Use Case**: Calendar sync, full integrations
- **Status**: Primary recommendation

### Level 4: Full FOGIS (v3.0) - Future
- **Size**: 6 KB
- **Fields**: Complete FOGIS object
- **Use Case**: Advanced analytics, complete integration
- **Status**: Future consideration

## Backward Compatibility Strategy

### Multi-Schema Publishing
```python
# Publisher sends multiple schema versions simultaneously
def publish_match_updates(matches, changes):
    base_message = create_base_message(matches, changes)

    # Publish to different channels based on schema level
    publish_to_channel("match_updates_v1", create_v1_message(base_message))
    publish_to_channel("match_updates_v2", create_v2_message(base_message))
    publish_to_channel("match_updates", create_v2_message(base_message))  # Default to latest
```

### Subscriber Schema Declaration
```python
# Subscribers declare their preferred schema version
class RedisSubscriber:
    def __init__(self, preferred_schema="2.0", fallback_schemas=["1.5", "1.0"]):
        self.preferred_schema = preferred_schema
        self.fallback_schemas = fallback_schemas

    def subscribe(self):
        # Try preferred schema first
        channel = f"match_updates_v{self.preferred_schema}"
        self.subscribe_to_channel(channel)
```

## Field Addition Strategy

### Incremental Field Addition
```json
{
  "schema_version": "2.1",
  "new_in_version": {
    "2.1": ["weather_conditions", "attendance_estimate"],
    "2.0": ["team_contacts", "referees.contact"],
    "1.5": ["venue.coordinates", "competition.category"]
  },
  "payload": {
    // Existing v2.0 fields
    "weather_conditions": {  // New in v2.1
      "temperature": 15,
      "conditions": "partly_cloudy",
      "wind_speed": 5
    },
    "attendance_estimate": 150  // New in v2.1
  }
}
```

### Field Deprecation Process
```json
{
  "schema_version": "2.2",
  "deprecated_fields": {
    "teams.legacy_format": {
      "deprecated_in": "2.2",
      "removal_planned": "3.0",
      "replacement": "teams.home, teams.away"
    }
  }
}
```

## Implementation Phases

### Phase 1: Contact-Aware Schema (Immediate)
1. **Deploy v2.0** with contact data
2. **Maintain v1.0** for backward compatibility
3. **Update calendar service** to use v2.0
4. **Monitor performance** and subscriber adoption

### Phase 2: Multi-Version Support (Short-term)
1. **Implement schema versioning** framework
2. **Add subscriber preferences** mechanism
3. **Create migration tools** for existing subscribers
4. **Establish deprecation timeline** for v1.0

### Phase 3: Advanced Features (Medium-term)
1. **Add analytics fields** (v2.1): weather, attendance, performance metrics
2. **Add mobile app fields** (v2.2): social media links, photos, live updates
3. **Add integration fields** (v2.3): external system IDs, sync status

### Phase 4: Full Integration (Long-term)
1. **Evaluate v3.0** with complete FOGIS object
2. **Implement conditional publishing** based on subscriber needs
3. **Add real-time field updates** for live match data
4. **Create schema marketplace** for custom field requests

## Security and Contact Data Handling

### Tiered Access Control
```json
{
  "schema_version": "2.0",
  "access_level": "contacts_included",
  "subscriber_permissions": {
    "calendar_service": ["full_contacts"],
    "analytics_service": ["no_contacts"],
    "mobile_app": ["public_contacts_only"]
  }
}
```

### Contact Data Sanitization
```python
def sanitize_contact_data(contact, access_level):
    if access_level == "full_contacts":
        return contact  # Full access for calendar service
    elif access_level == "public_contacts_only":
        return {
            "name": contact["name"],
            "role": contact["role"],
            "contact": {
                "email": contact["contact"]["email"]  # Email only
            }
        }
    else:
        return {
            "name": contact["name"],
            "role": contact["role"]
            # No contact details
        }
```

## Performance Considerations

### Message Size Management
- **v1.0**: 203 bytes - Excellent for high-frequency updates
- **v2.0**: 3.6 KB - Good for real-time with rich data
- **v3.0**: 6 KB - Acceptable for complete integration

### Redis Memory Impact (1000 matches)
- **v1.0**: 203 KB
- **v2.0**: 3.6 MB
- **v3.0**: 6 MB

### Network Bandwidth
- **Real-time updates**: v2.0 suitable for sub-second updates
- **Batch processing**: v3.0 acceptable for periodic sync
- **Mobile networks**: v1.0 optimal for mobile subscribers

## Migration Timeline

### Immediate (Next 2 weeks)
- ✅ Deploy v2.0 schema with contacts
- ✅ Update calendar service to use v2.0
- ✅ Maintain v1.0 for backward compatibility

### Short-term (1-2 months)
- 🔄 Implement schema versioning framework
- 🔄 Add subscriber preference mechanism
- 🔄 Create migration documentation

### Medium-term (3-6 months)
- 📈 Add analytics fields (v2.1)
- 📱 Add mobile app fields (v2.2)
- 🔗 Add integration fields (v2.3)

### Long-term (6+ months)
- 🚀 Evaluate full FOGIS object publishing (v3.0)
- 🎯 Implement conditional field publishing
- 📊 Create schema usage analytics

## Conclusion

The schema evolution strategy provides:
- ✅ **Immediate solution** for contact data requirements
- ✅ **Backward compatibility** for existing subscribers
- ✅ **Incremental enhancement** capability
- ✅ **Performance optimization** through tiered schemas
- ✅ **Security controls** for sensitive data access
- ✅ **Future-proof architecture** for unknown requirements
