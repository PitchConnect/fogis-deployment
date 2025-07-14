#!/bin/bash

# Comprehensive Validation Script for FOGIS Headless Deployment System
# Tests all headless deployment capabilities and CI/CD integration scenarios

set -e

echo "🤖 FOGIS Headless Deployment System - Comprehensive Validation"
echo "============================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Test function wrapper
run_test() {
    local test_name="$1"
    local test_command="$2"

    echo ""
    log_info "Test: $test_name"
    ((TOTAL_TESTS++))

    if eval "$test_command"; then
        log_success "$test_name - PASSED"
        ((TESTS_PASSED++))
        return 0
    else
        log_error "$test_name - FAILED"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test 1: Headless Mode Parameter Parsing
test_parameter_parsing() {
    local result=$(bash -c "
        source install.sh
        parse_arguments --headless --mode=upgrade --auto-confirm --timeout=600 --operation-id=test-123
        echo \"HEADLESS:\$HEADLESS_MODE|MODE:\$INSTALL_MODE|CONFIRM:\$AUTO_CONFIRM|TIMEOUT:\$TIMEOUT_SECONDS|ID:\$OPERATION_ID\"
    " 2>/dev/null)

    [[ "$result" == "HEADLESS:true|MODE:upgrade|CONFIRM:true|TIMEOUT:600|ID:test-123" ]] || return 1
    return 0
}

# Test 2: Environment Variable Configuration
test_environment_variables() {
    local result=$(FOGIS_HEADLESS=true FOGIS_INSTALL_MODE=force FOGIS_AUTO_CONFIRM=true bash -c "
        source install.sh
        load_environment_config
        echo \"HEADLESS:\$HEADLESS_MODE|MODE:\$INSTALL_MODE|CONFIRM:\$AUTO_CONFIRM\"
    " 2>/dev/null)

    [[ "$result" == "HEADLESS:true|MODE:force|CONFIRM:true" ]] || return 1
    return 0
}

# Test 3: CI/CD Environment Auto-Detection
test_cicd_detection() {
    local result=$(GITHUB_ACTIONS=true bash -c "
        source install.sh
        load_environment_config
        echo \"HEADLESS:\$HEADLESS_MODE\"
    " 2>/dev/null)

    [[ "$result" == "HEADLESS:true" ]] || return 1
    return 0
}

# Test 4: Configuration Validation
test_configuration_validation() {
    # Test invalid mode
    local result1=$(bash -c "
        source install.sh
        HEADLESS_MODE=true
        INSTALL_MODE=invalid
        validate_headless_config
    " 2>&1)

    [[ $? -ne 0 ]] && [[ "$result1" == *"Invalid installation mode"* ]] || return 1

    # Test invalid timeout
    local result2=$(bash -c "
        source install.sh
        HEADLESS_MODE=true
        TIMEOUT_SECONDS=30
        validate_headless_config
    " 2>&1)

    [[ $? -ne 0 ]] && [[ "$result2" == *"Invalid timeout seconds"* ]] || return 1

    return 0
}

# Test 5: Structured JSON Logging
test_structured_logging() {
    local result=$(bash -c "
        source install.sh
        HEADLESS_MODE=true
        OPERATION_ID=test-logging
        log_info 'Test message'
    " 2>/dev/null)

    # Validate JSON structure
    echo "$result" | jq -e '.timestamp and .level == "info" and .operation_id == "test-logging" and .message == "Test message"' >/dev/null || return 1
    return 0
}

# Test 6: Progress Reporting
test_progress_reporting() {
    local result=$(bash -c "
        source install.sh
        HEADLESS_MODE=true
        OPERATION_ID=test-progress
        report_progress 'setup' 3 5 'Installing components'
    " 2>/dev/null)

    # Validate progress JSON structure
    echo "$result" | jq -e '.level == "progress" and .phase == "setup" and .step == 3 and .total_steps == 5 and .progress_percent == 60' >/dev/null || return 1
    return 0
}

# Test 7: Intelligent Conflict Resolution
test_intelligent_defaults() {
    local test_dir="/tmp/test_headless_conflicts_$$"
    mkdir -p "$test_dir/credentials"
    echo '{"test": "data"}' > "$test_dir/credentials/test.json"
    echo "FOGIS_USERNAME=test" > "$test_dir/.env"

    local result=$(bash -c "
        source install.sh
        INSTALL_DIR='$test_dir'
        HEADLESS_MODE=true

        # Mock docker ps to return running containers
        docker() {
            if [[ \"\$1\" == \"ps\" ]]; then
                echo \"fogis-api-client-service\"
            else
                command docker \"\$@\" 2>/dev/null || true
            fi
        }
        export -f docker

        handle_headless_conflicts /tmp/test 2>/dev/null
        echo \"MODE:\$INSTALL_MODE\"
    ")

    # Clean up
    rm -rf "$test_dir"

    [[ "$result" == "MODE:upgrade" ]] || return 1
    return 0
}

# Test 8: Help System
test_help_system() {
    local result=$(bash -c "
        source install.sh
        show_headless_usage
    " 2>/dev/null)

    [[ "$result" == *"FOGIS Headless Installation"* ]] && \
    [[ "$result" == *"--headless"* ]] && \
    [[ "$result" == *"Exit Codes:"* ]] || return 1
    return 0
}

# Test 9: Error Handling and Exit Codes
test_error_handling() {
    # Test invalid configuration exit code
    bash -c "
        source install.sh
        HEADLESS_MODE=true
        INSTALL_MODE=invalid
        validate_headless_config
    " >/dev/null 2>&1
    local exit_code=$?

    [[ $exit_code -eq 50 ]] || return 1  # EXIT_INVALID_CONFIG
    return 0
}

# Test 10: Headless Environment Validation
test_environment_validation() {
    local result=$(bash -c "
        source lib/installation_safety.sh
        validate_headless_environment
    " 2>/dev/null)

    [[ $? -eq 0 ]] || return 1
    return 0
}

# Test 11: Health Verification System
test_health_verification() {
    # Create mock installation for health check
    local test_dir="/tmp/test_health_$$"
    mkdir -p "$test_dir"
    echo "version: '3.8'" > "$test_dir/docker-compose-master.yml"
    echo "FOGIS_USERNAME=test" > "$test_dir/.env"
    chmod +x "$test_dir/manage_fogis_system.sh" 2>/dev/null || touch "$test_dir/manage_fogis_system.sh"

    local result=$(bash -c "
        source lib/installation_safety.sh
        INSTALL_DIR='$test_dir'
        HEADLESS_MODE=true
        OPERATION_ID=test-health
        verify_installation_health
    " 2>/dev/null)

    local exit_code=$?

    # Clean up
    rm -rf "$test_dir"

    [[ $exit_code -eq 0 ]] || return 1
    return 0
}

# Test 12: Timeout Handling
test_timeout_handling() {
    # Test timeout setup (without actually timing out)
    local result=$(timeout 5 bash -c "
        source install.sh
        HEADLESS_MODE=true
        TIMEOUT_SECONDS=10
        setup_timeout_handling
        sleep 1
        echo 'timeout_test_passed'
    " 2>/dev/null)

    [[ "$result" == "timeout_test_passed" ]] || return 1
    return 0
}

# Test 13: Backward Compatibility
test_backward_compatibility() {
    # Test that interactive mode still works
    local result=$(bash -c "
        source install.sh
        HEADLESS_MODE=false
        log_info 'Interactive mode test'
    " 2>/dev/null)

    # Should not be JSON in interactive mode
    [[ "$result" != *"timestamp"* ]] && [[ "$result" == *"Interactive mode test"* ]] || return 1
    return 0
}

# Test 14: Multiple CI/CD Environment Detection
test_multiple_cicd_environments() {
    # Test Jenkins
    local result1=$(JENKINS_URL=http://jenkins.example.com bash -c "
        source install.sh
        load_environment_config
        echo \"HEADLESS:\$HEADLESS_MODE\"
    " 2>/dev/null)

    # Test GitLab CI
    local result2=$(GITLAB_CI=true bash -c "
        source install.sh
        load_environment_config
        echo \"HEADLESS:\$HEADLESS_MODE\"
    " 2>/dev/null)

    [[ "$result1" == "HEADLESS:true" ]] && [[ "$result2" == "HEADLESS:true" ]] || return 1
    return 0
}

# Test 15: Configuration Precedence
test_configuration_precedence() {
    # Environment variable should override default, command line should override environment
    local result=$(FOGIS_INSTALL_MODE=upgrade bash -c "
        source install.sh
        load_environment_config
        parse_arguments --mode=force
        echo \"MODE:\$INSTALL_MODE\"
    " 2>/dev/null)

    [[ "$result" == "MODE:force" ]] || return 1
    return 0
}

# Run all tests
echo "🧪 Running comprehensive headless deployment tests..."

run_test "Parameter Parsing" "test_parameter_parsing"
run_test "Environment Variables" "test_environment_variables"
run_test "CI/CD Auto-Detection" "test_cicd_detection"
run_test "Configuration Validation" "test_configuration_validation"
run_test "Structured JSON Logging" "test_structured_logging"
run_test "Progress Reporting" "test_progress_reporting"
run_test "Intelligent Conflict Resolution" "test_intelligent_defaults"
run_test "Help System" "test_help_system"
run_test "Error Handling and Exit Codes" "test_error_handling"
run_test "Environment Validation" "test_environment_validation"
run_test "Health Verification" "test_health_verification"
run_test "Timeout Handling" "test_timeout_handling"
run_test "Backward Compatibility" "test_backward_compatibility"
run_test "Multiple CI/CD Environments" "test_multiple_cicd_environments"
run_test "Configuration Precedence" "test_configuration_precedence"

# Final results
echo ""
echo "📊 HEADLESS DEPLOYMENT VALIDATION RESULTS"
echo "=========================================="
echo "Total Tests: $TOTAL_TESTS"
echo "Passed: $TESTS_PASSED"
echo "Failed: $TESTS_FAILED"
echo "Success Rate: $(( TESTS_PASSED * 100 / TOTAL_TESTS ))%"

echo ""
if [[ $TESTS_FAILED -eq 0 ]]; then
    log_success "🎉 ALL HEADLESS DEPLOYMENT TESTS PASSED!"
    echo ""
    echo "✅ Headless deployment system is fully functional and ready for production"
    echo "✅ All CI/CD integration scenarios validated"
    echo "✅ Intelligent conflict resolution working correctly"
    echo "✅ Structured logging and monitoring integration ready"
    echo "✅ Error handling and timeout mechanisms operational"
    echo "✅ Backward compatibility with interactive mode maintained"
    echo ""
    echo "🚀 READY FOR CI/CD AND AUTOMATED DEPLOYMENT USE"
    echo ""
    exit 0
else
    log_error "❌ SOME HEADLESS DEPLOYMENT TESTS FAILED"
    echo ""
    echo "🔧 Please review failed tests and fix issues before proceeding"
    echo ""
    exit 1
fi
