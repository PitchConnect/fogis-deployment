# Redis Pub/Sub Integration Testing Guide

## Overview

This document describes the comprehensive integration testing framework for the Redis pub/sub workflow between FOGIS services. The test suite verifies the complete cross-service communication flow from data fetching to calendar updates.

## Test Architecture

### Services Under Test

1. **FOGIS API Client** (`ghcr.io/pitchconnect/fogis-api-client-python:latest`)
   - Provides centralized API access to FOGIS data
   - Tested via mock FOGIS API server

2. **Match List Processor** (`ghcr.io/pitchconnect/match-list-processor:latest`)
   - Fetches match data and detects changes
   - Publishes updates to Redis pub/sub

3. **Calendar and Contacts Sync Service** (`ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest`)
   - Subscribes to Redis pub/sub messages
   - Processes match updates for calendar/contacts sync

4. **Redis Infrastructure** (`redis:7-alpine`)
   - Provides pub/sub messaging between services

### Test Components

- **Mock FOGIS API Server**: Lightweight Flask server simulating FOGIS API responses
- **Test Data Fixtures**: Predefined match data for consistent testing
- **Redis Message Validation**: Ensures proper message format compliance
- **Health Check Utilities**: Verifies service availability and readiness

## Test Workflow Verification

The integration tests verify these critical workflow steps:

### 1. Data Fetching
- ✅ Match List Processor successfully fetches data via FOGIS API Client
- ✅ Mock FOGIS API provides realistic test scenarios
- ✅ API Client properly formats and returns match data

### 2. Change Detection
- ✅ Match List Processor detects changes between data fetches
- ✅ Different scenarios (new matches, updated matches, no changes)
- ✅ Proper change metadata generation

### 3. Redis Publishing
- ✅ Match List Processor publishes to correct Redis channels
- ✅ Message format compliance with expected schema
- ✅ Non-blocking operation with error handling

### 4. Redis Subscription
- ✅ Calendar Service subscribes to match update channels
- ✅ Message reception and parsing
- ✅ Graceful handling of connection issues

### 5. Message Processing
- ✅ Calendar Service processes received messages
- ✅ Proper calendar/contacts update workflow
- ✅ Error handling and logging

## Quick Start

### Running All Tests

```bash
# Using the management script (recommended)
./manage_fogis_system.sh test-integration

# Or directly
./tests/run_integration_tests.sh
```

### Running Specific Tests

```bash
# Test Redis connectivity only
./tests/run_integration_tests.sh test_redis_connectivity

# Test complete workflow
./tests/run_integration_tests.sh test_complete_end_to_end_workflow

# Quick tests (skip slow E2E tests)
./tests/run_integration_tests.sh --quick
```

### Setting Up Test Environment

```bash
# Set up test environment without running tests
./manage_fogis_system.sh test-setup

# Or with the test script
./tests/run_integration_tests.sh --setup-only
```

## Test Environment

### Docker Compose Configuration

The test environment uses `tests/integration/docker-compose.test.yml` with:

- **Isolated Network**: `test-network` prevents conflicts with production
- **Test Ports**: Different ports (6380, 8090, 9090-9092) avoid conflicts
- **Mock Services**: Mock FOGIS API replaces external dependencies
- **Test Data**: Predefined fixtures for consistent testing

### Environment Variables

```bash
# Core test configuration
TEST_REDIS_URL=redis://localhost:6380
TEST_API_CLIENT_URL=http://localhost:9090
TEST_MATCH_PROCESSOR_URL=http://localhost:9091
TEST_CALENDAR_SYNC_URL=http://localhost:9092
TEST_TIMEOUT=300

# Redis channels for testing
REDIS_MATCH_UPDATES_CHANNEL=test:matches:updates
REDIS_PROCESSOR_STATUS_CHANNEL=test:processor:status
REDIS_CALENDAR_STATUS_CHANNEL=test:calendar:status
```

## Mock FOGIS API Server

### Available Scenarios

The mock server provides different test scenarios:

1. **default**: Standard match data with 2 matches
2. **change_detection**: Modified data to test change detection
3. **empty**: No matches (empty response)
4. **error**: Simulated API error for error handling tests

### Scenario Management

```bash
# List available scenarios
curl http://localhost:8090/api/scenarios

# Switch to change detection scenario
curl -X POST http://localhost:8090/api/scenarios/change_detection

# Reset to default
curl -X POST http://localhost:8090/api/reset
```

## Redis Message Format

### Expected Message Structure

```json
{
  "matches": [
    {
      "match_id": "MATCH001",
      "home_team": "Team A",
      "away_team": "Team B",
      "date": "2025-10-01",
      "time": "15:00",
      "venue": "Stadium Name",
      "referee": "Referee Name",
      "assistant_referees": ["Assistant 1", "Assistant 2"]
    }
  ],
  "timestamp": "2025-09-25T10:00:00Z",
  "source": "match-list-processor",
  "metadata": {
    "total_matches": 1,
    "has_changes": true,
    "new_matches_count": 1,
    "updated_matches_count": 0,
    "processing_timestamp": "2025-09-25T10:00:00Z"
  }
}
```

### Channel Conventions

- `test:matches:updates` - Match data updates
- `test:processor:status` - Match processor status
- `test:calendar:status` - Calendar service status

## Test Execution Options

### Command Line Options

```bash
./tests/run_integration_tests.sh [OPTIONS] [TEST_PATTERN]

OPTIONS:
  -h, --help          Show help message
  -v, --verbose       Enable verbose output
  -q, --quick         Run quick tests only (skip E2E)
  -c, --cleanup       Clean up test environment after run
  -s, --setup-only    Set up test environment without running tests
  -t, --timeout SEC   Set test timeout (default: 300)
  --no-build          Skip building test images
  --keep-running      Keep test environment running after tests
```

### Examples

```bash
# Verbose output with cleanup
./tests/run_integration_tests.sh -v -c

# Quick tests only
./tests/run_integration_tests.sh --quick

# Set up environment for manual testing
./tests/run_integration_tests.sh --setup-only

# Run specific test with custom timeout
./tests/run_integration_tests.sh -t 600 test_complete_end_to_end_workflow
```

## Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check service health
curl http://localhost:9090/health  # API Client
curl http://localhost:9091/health  # Match Processor
curl http://localhost:9092/health  # Calendar Sync

# Check logs
docker logs test-fogis-api-client
docker logs test-match-processor
docker logs test-calendar-sync
```

#### Redis Connection Issues
```bash
# Test Redis connectivity
docker exec test-redis redis-cli ping

# Check Redis logs
docker logs test-redis

# Monitor Redis activity
docker exec test-redis redis-cli MONITOR
```

#### Test Failures
```bash
# Run with verbose output
./tests/run_integration_tests.sh -v

# Check test reports
cat tests/integration/test-reports/junit.xml
open tests/integration/test-reports/report.html
```

### Manual Testing

When test environment is set up (`--setup-only`), you can manually test:

```bash
# Test mock API
curl http://localhost:8090/api/matches

# Test Redis pub/sub
docker exec test-redis redis-cli PUBLISH test:matches:updates '{"test": true}'

# Monitor Redis channels
docker exec test-redis redis-cli SUBSCRIBE test:matches:updates
```

## CI/CD Integration

### GitHub Actions Integration

The test suite can be integrated into CI/CD pipelines:

```yaml
- name: Run Integration Tests
  run: |
    ./tests/run_integration_tests.sh --quick --cleanup

- name: Upload Test Reports
  uses: actions/upload-artifact@v3
  if: always()
  with:
    name: integration-test-reports
    path: tests/integration/test-reports/
```

### Test Reports

The test suite generates:
- **JUnit XML**: `test-reports/junit.xml` for CI integration
- **HTML Report**: `test-reports/report.html` for detailed analysis
- **JSON Report**: `test-reports/report.json` for programmatic analysis

## Maintenance

### Updating Test Data

1. Modify `tests/integration/test-data/stakeholders.json`
2. Update mock scenarios in `tests/mock-services/mock_fogis_api.py`
3. Adjust test expectations in test files

### Adding New Tests

1. Create test files in `tests/integration/`
2. Use existing fixtures from `conftest.py`
3. Follow naming convention: `test_*.py`
4. Add appropriate pytest markers for categorization

### Updating Dependencies

1. Update `tests/integration/requirements.txt`
2. Rebuild test images: `docker-compose -f tests/integration/docker-compose.test.yml build`

## Best Practices

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Cleanup**: Use fixtures for proper setup/teardown
3. **Timeouts**: Set appropriate timeouts for async operations
4. **Assertions**: Use descriptive assertion messages
5. **Logging**: Include sufficient logging for debugging
6. **Documentation**: Document complex test scenarios

## Future Enhancements

- **Performance Testing**: Add load testing for Redis pub/sub
- **Chaos Testing**: Test resilience with service failures
- **Security Testing**: Validate message encryption and authentication
- **Monitoring Integration**: Test with Grafana/Prometheus metrics
