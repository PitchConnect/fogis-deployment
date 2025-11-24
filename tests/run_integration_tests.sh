#!/bin/bash

# Redis Pub/Sub Integration Test Runner
# Runs the complete cross-service integration test suite

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_DIR="$SCRIPT_DIR/integration"
COMPOSE_FILE="$TEST_DIR/docker-compose.test.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Redis Pub/Sub Integration Test Runner

USAGE:
    $0 [OPTIONS] [TEST_PATTERN]

OPTIONS:
    -h, --help          Show this help message
    -v, --verbose       Enable verbose output
    -q, --quick         Run quick tests only (skip E2E)
    -c, --cleanup       Clean up test environment after run
    -s, --setup-only    Set up test environment without running tests
    -t, --timeout SEC   Set test timeout (default: 300)
    --no-build          Skip building test images
    --keep-running      Keep test environment running after tests
    --force-cleanup     Force cleanup with image removal
    --remove-images     Remove test images during cleanup

TEST_PATTERN:
    Optional pytest pattern to run specific tests
    Examples:
        test_service_health
        test_redis_*
        test_complete_end_to_end_workflow

EXAMPLES:
    $0                                    # Run all integration tests
    $0 -v test_redis_connectivity         # Run specific test with verbose output
    $0 --quick                           # Run quick tests only
    $0 --setup-only                      # Set up environment for manual testing
    $0 --cleanup                         # Clean up test environment

EOF
}

# Default configuration
VERBOSE=false
QUICK_MODE=false
CLEANUP_AFTER=false
SETUP_ONLY=false
TIMEOUT=300
BUILD_IMAGES=true
KEEP_RUNNING=false
FORCE_CLEANUP=false
REMOVE_TEST_IMAGES=false
TEST_PATTERN=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -q|--quick)
            QUICK_MODE=true
            shift
            ;;
        -c|--cleanup)
            CLEANUP_AFTER=true
            shift
            ;;
        -s|--setup-only)
            SETUP_ONLY=true
            shift
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --no-build)
            BUILD_IMAGES=false
            shift
            ;;
        --keep-running)
            KEEP_RUNNING=true
            shift
            ;;
        --force-cleanup)
            FORCE_CLEANUP=true
            CLEANUP_AFTER=true
            REMOVE_TEST_IMAGES=true
            shift
            ;;
        --remove-images)
            REMOVE_TEST_IMAGES=true
            shift
            ;;
        -*)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            TEST_PATTERN="$1"
            shift
            ;;
    esac
done

# Health check function
wait_for_service_health() {
    local service_name="$1"
    local health_url="$2"
    local max_wait="${3:-120}"
    local check_interval="${4:-5}"

    log_info "Waiting for $service_name to be healthy..."

    local elapsed=0
    while [ $elapsed -lt $max_wait ]; do
        if curl -s -f "$health_url" >/dev/null 2>&1; then
            log_success "$service_name is healthy"
            return 0
        fi

        sleep $check_interval
        elapsed=$((elapsed + check_interval))

        if [ $((elapsed % 30)) -eq 0 ]; then
            log_info "Still waiting for $service_name... (${elapsed}s elapsed)"
        fi
    done

    log_error "$service_name failed to become healthy within ${max_wait}s"
    return 1
}

# Wait for all services to be healthy
wait_for_all_services() {
    log_info "Waiting for all services to be healthy..."

    # Wait for Redis
    if ! wait_for_service_health "Redis" "http://localhost:6380" 60 2; then
        # Try Redis ping directly
        if docker exec test-redis redis-cli ping >/dev/null 2>&1; then
            log_success "Redis is healthy (via ping)"
        else
            log_error "Redis is not responding"
            return 1
        fi
    fi

    # Wait for Mock API
    if ! wait_for_service_health "Mock FOGIS API" "http://localhost:8090/health" 60 5; then
        return 1
    fi

    # Wait for API Client
    if ! wait_for_service_health "FOGIS API Client" "http://localhost:9090/health" 120 5; then
        log_warning "FOGIS API Client health check failed, but continuing..."
    fi

    # Wait for Match Processor
    if ! wait_for_service_health "Match Processor" "http://localhost:9091/health" 120 5; then
        # Try alternative health endpoint
        if ! wait_for_service_health "Match Processor" "http://localhost:9091/health/simple" 60 5; then
            log_warning "Match Processor health check failed, but continuing..."
        fi
    fi

    # Wait for Calendar Sync
    if ! wait_for_service_health "Calendar Sync" "http://localhost:9092/health" 120 5; then
        log_warning "Calendar Sync health check failed, but continuing..."
    fi

    log_success "Service health checks completed"
    return 0
}

# Cleanup function
cleanup_test_environment() {
    log_info "Cleaning up test environment..."

    cd "$TEST_DIR"

    # Stop containers gracefully first
    log_info "Stopping containers gracefully..."
    docker-compose -f docker-compose.test.yml stop 2>/dev/null || true

    # Force stop any remaining containers
    log_info "Force stopping any remaining containers..."
    docker stop test-redis test-match-processor test-calendar-sync test-fogis-api-client mock-fogis-api test-runner 2>/dev/null || true

    # Remove containers and volumes
    log_info "Removing containers and volumes..."
    docker-compose -f docker-compose.test.yml down --volumes --remove-orphans 2>/dev/null || true

    # Remove any orphaned containers
    docker rm -f test-redis test-match-processor test-calendar-sync test-fogis-api-client mock-fogis-api test-runner 2>/dev/null || true

    # Remove test network if it exists
    docker network rm test-network 2>/dev/null || true

    # Remove test images if they exist (only if explicitly requested)
    if [[ "${REMOVE_TEST_IMAGES:-false}" == "true" ]]; then
        log_info "Removing test images..."
        docker rmi $(docker images -q "*test*" 2>/dev/null) 2>/dev/null || true
        docker rmi $(docker images -q "tests_*" 2>/dev/null) 2>/dev/null || true
    fi

    # Clean up test output directories
    log_info "Cleaning up test output directories..."
    rm -rf test-output test-reports 2>/dev/null || true

    # Remove any temporary files
    find . -name "*.tmp" -delete 2>/dev/null || true
    find . -name "*.log" -delete 2>/dev/null || true

    log_success "Test environment cleaned up"
}

# Setup function
setup_test_environment() {
    log_info "Setting up integration test environment..."

    # Change to test directory
    cd "$TEST_DIR"

    # Create necessary directories
    mkdir -p test-output test-reports

    # Create .env file for testing if it doesn't exist
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        log_warning "No .env file found, creating minimal test configuration"
        cat > "$PROJECT_ROOT/.env" << 'EOF'
# Minimal configuration for integration testing
FOGIS_USERNAME=test_user
FOGIS_PASSWORD=test_password
DEBUG_MODE=1
LOG_LEVEL=DEBUG
REDIS_ENABLED=true
REDIS_URL=redis://test-redis:6379
EOF
    fi

    # Build test images if requested
    if [[ "$BUILD_IMAGES" == "true" ]]; then
        log_info "Building test images..."
        docker-compose -f docker-compose.test.yml build
    fi

    # Start test infrastructure
    log_info "Starting test infrastructure..."
    docker-compose -f docker-compose.test.yml up -d test-redis mock-fogis-api

    # Wait for infrastructure to be ready
    log_info "Waiting for test infrastructure to be ready..."
    sleep 5

    # Start services
    log_info "Starting test services..."
    docker-compose -f docker-compose.test.yml up -d

    # Wait for all services to be healthy
    if ! wait_for_all_services; then
        log_error "Some services failed to start properly"
        log_info "Continuing with available services..."
    fi

    log_success "Test environment setup complete"
}

# Run tests function
run_tests() {
    log_info "Running integration tests..."

    cd "$TEST_DIR"

    # Build pytest command
    PYTEST_CMD="python -m pytest"

    if [[ "$VERBOSE" == "true" ]]; then
        PYTEST_CMD="$PYTEST_CMD --verbose"
    fi

    if [[ "$QUICK_MODE" == "true" ]]; then
        PYTEST_CMD="$PYTEST_CMD -m 'not slow'"
    fi

    # Add timeout
    PYTEST_CMD="$PYTEST_CMD --timeout=$TIMEOUT"

    # Add test pattern if specified
    if [[ -n "$TEST_PATTERN" ]]; then
        PYTEST_CMD="$PYTEST_CMD -k '$TEST_PATTERN'"
    fi

    # Add output options
    PYTEST_CMD="$PYTEST_CMD --junit-xml=test-reports/junit.xml --html=test-reports/report.html --self-contained-html"

    # Run tests in container
    log_info "Executing: $PYTEST_CMD"

    if docker-compose -f docker-compose.test.yml run --rm test-runner $PYTEST_CMD; then
        log_success "Integration tests completed successfully"
        return 0
    else
        log_error "Integration tests failed"
        return 1
    fi
}

# Main execution
main() {
    log_info "Starting Redis Pub/Sub Integration Test Suite"
    log_info "Project root: $PROJECT_ROOT"
    log_info "Test directory: $TEST_DIR"

    # Handle cleanup-only mode
    if [[ "$FORCE_CLEANUP" == "true" && "$SETUP_ONLY" == "false" && -z "$TEST_PATTERN" ]]; then
        log_info "Running force cleanup..."
        cleanup_test_environment
        exit 0
    fi

    # Trap cleanup on exit if requested
    if [[ "$CLEANUP_AFTER" == "true" ]]; then
        trap cleanup_test_environment EXIT
    fi

    # Setup test environment
    if ! setup_test_environment; then
        log_error "Failed to set up test environment"
        exit 1
    fi

    # Run tests unless setup-only mode
    if [[ "$SETUP_ONLY" == "false" ]]; then
        if run_tests; then
            log_success "All tests completed successfully!"
            exit_code=0
        else
            log_error "Tests failed!"
            exit_code=1
        fi

        # Cleanup if not keeping running
        if [[ "$KEEP_RUNNING" == "false" && "$CLEANUP_AFTER" == "false" ]]; then
            cleanup_test_environment
        fi

        exit $exit_code
    else
        log_info "Test environment is ready for manual testing"
        log_info "Services available at:"
        log_info "  - Redis: localhost:6380"
        log_info "  - Mock FOGIS API: localhost:8090"
        log_info "  - FOGIS API Client: localhost:9090"
        log_info "  - Match Processor: localhost:9091"
        log_info "  - Calendar Sync: localhost:9092"
        log_info ""
        log_info "To run tests manually:"
        log_info "  cd $TEST_DIR"
        log_info "  docker-compose -f docker-compose.test.yml run --rm test-runner"
        log_info ""
        log_info "To cleanup:"
        log_info "  $0 --cleanup"
    fi
}

# Run main function
main "$@"
