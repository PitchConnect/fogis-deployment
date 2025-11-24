# FOGIS Integration Tests

This directory contains the integration test suite for the FOGIS Redis pub/sub workflow.

## Quick Start

```bash
# Run all integration tests
./run_integration_tests.sh

# Set up test environment for manual testing
./run_integration_tests.sh --setup-only

# Clean up test environment
./run_integration_tests.sh --cleanup
```

## Directory Structure

```
tests/
├── README.md                           # This file
├── run_integration_tests.sh            # Main test runner script
├── integration/                        # Integration test suite
│   ├── conftest.py                     # Test configuration and fixtures
│   ├── test_redis_pubsub_workflow.py   # Main workflow tests
│   ├── docker-compose.test.yml         # Test environment configuration
│   ├── Dockerfile.test-runner          # Test runner container
│   ├── requirements.txt                # Python test dependencies
│   ├── test-credentials/               # Mock credentials for testing
│   │   └── mock-google-credentials.json
│   ├── test-data/                      # Test data fixtures
│   │   └── stakeholders.json
│   ├── test-output/                    # Test output directory (created at runtime)
│   └── test-reports/                   # Test reports (created at runtime)
└── mock-services/                      # Mock service implementations
    ├── mock_fogis_api.py               # Mock FOGIS API server
    ├── Dockerfile.mock-fogis-api       # Mock API container
    └── requirements.txt                # Mock service dependencies
```

## Test Categories

### 1. Service Health Tests
- Verify all services start correctly
- Check health endpoints
- Validate service connectivity

### 2. Redis Infrastructure Tests
- Test Redis connectivity
- Verify pub/sub functionality
- Check channel configuration

### 3. Data Fetching Tests
- Test FOGIS API Client integration
- Verify mock API scenarios
- Check data format compliance

### 4. Change Detection Tests
- Test match data change detection
- Verify change metadata generation
- Check different change scenarios

### 5. Redis Publishing Tests
- Test message publishing to Redis
- Verify message format compliance
- Check error handling

### 6. Redis Subscription Tests
- Test message subscription
- Verify message reception
- Check subscription management

### 7. End-to-End Workflow Tests
- Complete workflow integration
- Cross-service communication
- Full system validation

## Test Environment

### Services
- **test-redis**: Redis instance on port 6380
- **mock-fogis-api**: Mock FOGIS API on port 8090
- **test-fogis-api-client**: API Client on port 9090
- **test-match-processor**: Match Processor on port 9091
- **test-calendar-sync**: Calendar Service on port 9092

### Networks
- **test-network**: Isolated Docker network for testing

### Volumes
- **test-redis-data**: Redis data persistence
- **test-output**: Test output and logs
- **test-reports**: Test reports and artifacts

## Usage Examples

### Basic Testing
```bash
# Run all tests with verbose output
./run_integration_tests.sh -v

# Run quick tests only (skip slow E2E tests)
./run_integration_tests.sh --quick

# Run specific test
./run_integration_tests.sh test_redis_connectivity
```

### Development Workflow
```bash
# Set up test environment
./run_integration_tests.sh --setup-only

# Run tests manually
cd integration
docker-compose -f docker-compose.test.yml run --rm test-runner

# Clean up when done
./run_integration_tests.sh --cleanup
```

### Debugging
```bash
# Keep environment running after tests
./run_integration_tests.sh --keep-running

# Check service logs
docker logs test-match-processor
docker logs test-calendar-sync

# Monitor Redis activity
docker exec test-redis redis-cli MONITOR
```

## Mock FOGIS API

The mock FOGIS API provides realistic test scenarios:

### Available Endpoints
- `GET /health` - Health check
- `GET /api/matches` - Get match data
- `GET /api/scenarios` - List available scenarios
- `POST /api/scenarios/{scenario}` - Switch scenario
- `POST /api/reset` - Reset to default state

### Test Scenarios
- **default**: Standard match data (2 matches)
- **change_detection**: Modified data for change testing
- **empty**: No matches
- **error**: Simulated API error

### Usage
```bash
# Get matches
curl http://localhost:8090/api/matches

# Switch to change detection scenario
curl -X POST http://localhost:8090/api/scenarios/change_detection

# Reset to default
curl -X POST http://localhost:8090/api/reset
```

## Test Configuration

### Environment Variables
```bash
TEST_REDIS_URL=redis://localhost:6380
TEST_API_CLIENT_URL=http://localhost:9090
TEST_MATCH_PROCESSOR_URL=http://localhost:9091
TEST_CALENDAR_SYNC_URL=http://localhost:9092
TEST_TIMEOUT=300
```

### Redis Channels
```bash
REDIS_MATCH_UPDATES_CHANNEL=test:matches:updates
REDIS_PROCESSOR_STATUS_CHANNEL=test:processor:status
REDIS_CALENDAR_STATUS_CHANNEL=test:calendar:status
```

## Integration with Management System

The tests are integrated with the main FOGIS management system:

```bash
# Via management script
./manage_fogis_system.sh test-integration
./manage_fogis_system.sh test-setup
./manage_fogis_system.sh test-cleanup
```

## Test Reports

Tests generate multiple report formats:
- **JUnit XML**: `test-reports/junit.xml` (for CI)
- **HTML Report**: `test-reports/report.html` (for viewing)
- **JSON Report**: `test-reports/report.json` (for analysis)

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Ensure ports 6380, 8090-9092 are available
2. **Docker Issues**: Check Docker daemon and permissions
3. **Service Startup**: Allow sufficient time for service initialization
4. **Redis Connection**: Verify Redis container is healthy

### Debug Commands
```bash
# Check service health
curl http://localhost:9090/health

# Test Redis
docker exec test-redis redis-cli ping

# View logs
docker logs test-match-processor

# Check network
docker network ls | grep test
```

## Contributing

When adding new tests:

1. Follow existing patterns in `conftest.py`
2. Use descriptive test names and docstrings
3. Include proper assertions with messages
4. Add appropriate pytest markers
5. Update documentation

## Future Enhancements

- Performance and load testing
- Chaos engineering tests
- Security validation tests
- Monitoring integration tests
- Multi-platform testing
