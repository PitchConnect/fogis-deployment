# FOGIS Calendar Sync Health Report
Generated: 2025-06-25 14:52:00

## System Status
[0;34mℹ️  Checking container status...[0m
[0;32m✅ Container fogis-api-client-service is running[0m
[0;32m✅ Container fogis-calendar-phonebook-sync is running[0m
[0;32m✅ Container match-list-processor is running[0m
[0;31m❌ Container match-list-change-detector is not running[0m
- Containers: ❌ Some not running
[0;34mℹ️  Checking credentials configuration...[0m
[0;31m❌ .env file not found - FOGIS credentials not configured[0m
- Credentials: ❌ Missing
[0;34mℹ️  Checking FOGIS API Client health...[0m
[0;31m❌ FOGIS API Client degraded - missing credentials[0m
- FOGIS API: ❌ Issues detected
[0;34mℹ️  Checking Calendar Sync service health...[0m
[0;31m❌ Calendar Sync missing Google authentication[0m
- Calendar Sync: ❌ Issues detected
[0;34mℹ️  Checking match data access...[0m
[0;31m❌ Match data API returning 500 error - likely credential issue[0m
- Match Data: ❌ Not accessible

## Recommendations
1. Set up FOGIS credentials: Create .env file with FOGIS_USERNAME and FOGIS_PASSWORD
2. Set up Google OAuth: Run ./manage_fogis_system.sh setup-auth
3. Restart services after credential setup: ./manage_fogis_system.sh restart
4. Test match processing: ./manage_fogis_system.sh test
5. Enable automated processing: ./manage_fogis_system.sh cron-add
