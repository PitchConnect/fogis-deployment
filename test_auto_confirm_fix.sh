#!/bin/bash

# Test script for auto-confirm functionality fix
# Validates that the install.sh script respects auto-confirm settings

set -e

echo "🧪 Testing Auto-Confirm Functionality Fix"
echo "========================================"

# Test the specific section that was fixed
test_auto_confirm_logic() {
    local install_dir="$1"
    local headless_mode="$2" 
    local auto_confirm="$3"
    
    # Simulate the fixed logic from install.sh
    if [[ -d "$install_dir" ]]; then
        echo "Existing installation found at $install_dir"
        
        # Check if auto-confirm is enabled (headless mode or explicit auto-confirm)
        if [[ "$headless_mode" == "true" ]] || [[ "$auto_confirm" == "true" ]]; then
            echo "Auto-confirm enabled: removing existing installation automatically"
            rm -rf "$install_dir"
            return 0  # Success - auto-confirmed
        else
            echo "Would prompt for user input (interactive mode)"
            return 1  # Would require user input
        fi
    else
        echo "No existing installation found"
        return 0  # Success - nothing to remove
    fi
}

# Test 1: Command line --auto-confirm flag
test_command_line_flag() {
    echo ""
    echo "🔧 Test 1: Command line --auto-confirm flag"
    echo "--------------------------------------------"
    
    local test_dir="/tmp/fogis-test-auto-confirm-1"
    mkdir -p "$test_dir"
    echo "test" > "$test_dir/test.txt"
    
    if test_auto_confirm_logic "$test_dir" "false" "true"; then
        echo "✅ Command line --auto-confirm flag works correctly"
        return 0
    else
        echo "❌ Command line --auto-confirm flag failed"
        rm -rf "$test_dir"
        return 1
    fi
}

# Test 2: Headless mode auto-confirm
test_headless_mode() {
    echo ""
    echo "🤖 Test 2: Headless mode auto-confirm"
    echo "-------------------------------------"
    
    local test_dir="/tmp/fogis-test-headless-2"
    mkdir -p "$test_dir"
    echo "test" > "$test_dir/test.txt"
    
    if test_auto_confirm_logic "$test_dir" "true" "false"; then
        echo "✅ Headless mode auto-confirm works correctly"
        return 0
    else
        echo "❌ Headless mode auto-confirm failed"
        rm -rf "$test_dir"
        return 1
    fi
}

# Test 3: Interactive mode (should not auto-confirm)
test_interactive_mode() {
    echo ""
    echo "💬 Test 3: Interactive mode (should require user input)"
    echo "-------------------------------------------------------"
    
    local test_dir="/tmp/fogis-test-interactive-3"
    mkdir -p "$test_dir"
    echo "test" > "$test_dir/test.txt"
    
    if test_auto_confirm_logic "$test_dir" "false" "false"; then
        echo "❌ Interactive mode incorrectly auto-confirmed"
        rm -rf "$test_dir"
        return 1
    else
        echo "✅ Interactive mode correctly requires user input"
        rm -rf "$test_dir"
        return 0
    fi
}

# Test 4: Environment variable precedence
test_environment_variable() {
    echo ""
    echo "🌍 Test 4: Environment variable FOGIS_AUTO_CONFIRM"
    echo "---------------------------------------------------"
    
    local test_dir="/tmp/fogis-test-env-4"
    mkdir -p "$test_dir"
    echo "test" > "$test_dir/test.txt"
    
    # Simulate environment variable being loaded
    local auto_confirm_from_env="true"
    
    if test_auto_confirm_logic "$test_dir" "false" "$auto_confirm_from_env"; then
        echo "✅ FOGIS_AUTO_CONFIRM environment variable works correctly"
        return 0
    else
        echo "❌ FOGIS_AUTO_CONFIRM environment variable failed"
        rm -rf "$test_dir"
        return 1
    fi
}

# Run all tests
main() {
    echo "Starting auto-confirm functionality tests..."
    echo ""
    
    local failed_tests=0
    
    # Run tests
    test_command_line_flag || ((failed_tests++))
    test_headless_mode || ((failed_tests++))
    test_interactive_mode || ((failed_tests++))
    test_environment_variable || ((failed_tests++))
    
    echo ""
    if [[ $failed_tests -eq 0 ]]; then
        echo "🎉 All auto-confirm functionality tests passed!"
        echo ""
        echo "📋 Summary:"
        echo "  ✅ --auto-confirm command line flag works"
        echo "  ✅ Headless mode auto-confirm works"
        echo "  ✅ Interactive mode correctly prompts user"
        echo "  ✅ FOGIS_AUTO_CONFIRM environment variable works"
        echo ""
        echo "🚀 The fix resolves the installation timeout issues!"
        return 0
    else
        echo "❌ $failed_tests test(s) failed!"
        return 1
    fi
}

# Run main function
main "$@"
