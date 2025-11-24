#!/bin/bash

# Verification script for integration test fixes
# Tests all the implemented fixes to ensure they work correctly

set -euo pipefail

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

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_DIR="$SCRIPT_DIR/integration"

# Verification functions
verify_pytest_markers() {
    log_info "Verifying pytest markers are present..."

    local test_file="$TEST_DIR/test_redis_pubsub_workflow.py"
    local markers_found=0

    # Check for specific markers
    if grep -q "@pytest.mark.health" "$test_file"; then
        markers_found=$((markers_found + 1))
    fi

    if grep -q "@pytest.mark.redis" "$test_file"; then
        markers_found=$((markers_found + 1))
    fi

    if grep -q "@pytest.mark.integration" "$test_file"; then
        markers_found=$((markers_found + 1))
    fi

    if grep -q "@pytest.mark.workflow" "$test_file"; then
        markers_found=$((markers_found + 1))
    fi

    if [ $markers_found -ge 4 ]; then
        log_success "Pytest markers are properly implemented"
        return 0
    else
        log_error "Missing pytest markers (found $markers_found, expected at least 4)"
        return 1
    fi
}

verify_environment_variables() {
    log_info "Verifying environment variable handling..."

    local conftest_file="$TEST_DIR/conftest.py"

    # Check for Docker detection logic
    if grep -q "in_docker.*dockerenv" "$conftest_file"; then
        log_success "Docker detection logic is implemented"
    else
        log_error "Docker detection logic is missing"
        return 1
    fi

    # Check for container-internal URLs
    if grep -q "test-redis:6379" "$conftest_file"; then
        log_success "Container-internal URLs are configured"
    else
        log_error "Container-internal URLs are missing"
        return 1
    fi

    return 0
}

verify_pytest_configuration() {
    log_info "Verifying pytest configuration..."

    local pytest_ini="$TEST_DIR/pytest.ini"

    # Check for correct section header
    if grep -q "^\[pytest\]" "$pytest_ini"; then
        log_success "Pytest configuration syntax is correct"
    else
        log_error "Pytest configuration syntax is incorrect"
        return 1
    fi

    # Check for markers section
    if grep -q "markers =" "$pytest_ini"; then
        log_success "Pytest markers are defined"
    else
        log_error "Pytest markers are not defined"
        return 1
    fi

    return 0
}

verify_imports() {
    log_info "Verifying imports..."

    local test_file="$TEST_DIR/test_redis_pubsub_workflow.py"
    local mock_file="$SCRIPT_DIR/mock-services/mock_fogis_api.py"

    # Check for os import in test file
    if grep -q "^import os" "$test_file"; then
        log_success "Missing 'os' import has been added"
    else
        log_error "Missing 'os' import in test file"
        return 1
    fi

    # Check that uuid import is removed from mock file
    if ! grep -q "import uuid" "$mock_file"; then
        log_success "Unused 'uuid' import has been removed"
    else
        log_error "Unused 'uuid' import still present in mock file"
        return 1
    fi

    return 0
}

verify_resource_limits() {
    log_info "Verifying resource limits in Docker Compose..."

    local compose_file="$TEST_DIR/docker-compose.test.yml"

    # Check for deploy.resources sections
    local resource_sections=$(grep -c "deploy:" "$compose_file" || echo "0")

    if [ "$resource_sections" -ge 5 ]; then
        log_success "Resource limits are configured for services"
    else
        log_error "Resource limits are missing (found $resource_sections sections)"
        return 1
    fi

    # Check for memory limits
    if grep -q "memory: " "$compose_file"; then
        log_success "Memory limits are configured"
    else
        log_error "Memory limits are missing"
        return 1
    fi

    return 0
}

verify_dynamic_health_checks() {
    log_info "Verifying dynamic health check implementation..."

    local runner_script="$SCRIPT_DIR/run_integration_tests.sh"

    # Check for health check function
    if grep -q "wait_for_service_health" "$runner_script"; then
        log_success "Dynamic health check function is implemented"
    else
        log_error "Dynamic health check function is missing"
        return 1
    fi

    # Check that fixed sleep is replaced
    if ! grep -q "sleep 30" "$runner_script"; then
        log_success "Fixed 30-second wait has been replaced"
    else
        log_warning "Fixed 30-second wait may still be present"
    fi

    return 0
}

verify_cleanup_improvements() {
    log_info "Verifying cleanup improvements..."

    local runner_script="$SCRIPT_DIR/run_integration_tests.sh"

    # Check for force cleanup option
    if grep -q "force-cleanup" "$runner_script"; then
        log_success "Force cleanup option is implemented"
    else
        log_error "Force cleanup option is missing"
        return 1
    fi

    # Check for robust cleanup logic
    if grep -q "docker stop.*test-redis" "$runner_script"; then
        log_success "Robust cleanup logic is implemented"
    else
        log_error "Robust cleanup logic is missing"
        return 1
    fi

    return 0
}

verify_file_syntax() {
    log_info "Verifying file syntax..."

    # Check Python syntax
    local python_files=(
        "$TEST_DIR/test_redis_pubsub_workflow.py"
        "$TEST_DIR/conftest.py"
        "$SCRIPT_DIR/mock-services/mock_fogis_api.py"
    )

    for file in "${python_files[@]}"; do
        if python3 -m py_compile "$file" 2>/dev/null; then
            log_success "Python syntax OK: $(basename "$file")"
        else
            log_error "Python syntax error in: $(basename "$file")"
            return 1
        fi
    done

    # Check YAML syntax
    if command -v yamllint >/dev/null 2>&1; then
        if yamllint "$TEST_DIR/docker-compose.test.yml" >/dev/null 2>&1; then
            log_success "YAML syntax OK: docker-compose.test.yml"
        else
            log_warning "YAML syntax issues in docker-compose.test.yml (yamllint)"
        fi
    else
        log_info "yamllint not available, skipping YAML syntax check"
    fi

    return 0
}

verify_docker_compose_validity() {
    log_info "Verifying Docker Compose configuration..."

    cd "$TEST_DIR"

    # Check if docker-compose config is valid
    if docker-compose -f docker-compose.test.yml config >/dev/null 2>&1; then
        log_success "Docker Compose configuration is valid"
    else
        log_error "Docker Compose configuration has errors"
        return 1
    fi

    return 0
}

# Main verification function
run_verification() {
    log_info "Starting verification of integration test fixes..."
    echo ""

    local failed_checks=0

    # Run all verification checks
    verify_pytest_markers || failed_checks=$((failed_checks + 1))
    echo ""

    verify_environment_variables || failed_checks=$((failed_checks + 1))
    echo ""

    verify_pytest_configuration || failed_checks=$((failed_checks + 1))
    echo ""

    verify_imports || failed_checks=$((failed_checks + 1))
    echo ""

    verify_resource_limits || failed_checks=$((failed_checks + 1))
    echo ""

    verify_dynamic_health_checks || failed_checks=$((failed_checks + 1))
    echo ""

    verify_cleanup_improvements || failed_checks=$((failed_checks + 1))
    echo ""

    verify_file_syntax || failed_checks=$((failed_checks + 1))
    echo ""

    verify_docker_compose_validity || failed_checks=$((failed_checks + 1))
    echo ""

    # Summary
    if [ $failed_checks -eq 0 ]; then
        log_success "All verification checks passed! ✅"
        log_info "The integration test suite is ready for execution."
        return 0
    else
        log_error "$failed_checks verification check(s) failed! ❌"
        log_info "Please review and fix the issues before proceeding."
        return 1
    fi
}

# Run verification
run_verification
