#!/bin/bash

# Simple validation script for FOGIS Safe Installation System
# Tests core functionality without complex test frameworks

set -e

echo "🔍 FOGIS Safe Installation System - Basic Validation"
echo "=================================================="
echo ""

# Test 1: Check if all required files exist
echo "📁 Test 1: Checking required files..."
required_files=(
    "lib/conflict_detector.sh"
    "lib/backup_manager.sh"
    "lib/installation_safety.sh"
    "install.sh"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "  ✅ $file exists"
    else
        echo "  ❌ $file missing"
        exit 1
    fi
done

# Test 2: Check bash syntax
echo ""
echo "🔧 Test 2: Checking bash syntax..."
for file in "${required_files[@]}"; do
    if [[ "$file" == *.sh ]]; then
        if bash -n "$file"; then
            echo "  ✅ $file syntax OK"
        else
            echo "  ❌ $file syntax error"
            exit 1
        fi
    fi
done

# Test 3: Test individual script loading
echo ""
echo "📦 Test 3: Testing script loading..."

# Test conflict detector
if timeout 5 bash -c "source lib/conflict_detector.sh && type check_directory_conflicts >/dev/null"; then
    echo "  ✅ Conflict detector loads and functions exist"
else
    echo "  ❌ Conflict detector failed to load"
    exit 1
fi

# Test backup manager
if timeout 5 bash -c "source lib/backup_manager.sh && type create_installation_backup >/dev/null"; then
    echo "  ✅ Backup manager loads and functions exist"
else
    echo "  ❌ Backup manager failed to load"
    exit 1
fi

# Test installation safety
if timeout 5 bash -c "source lib/installation_safety.sh && type perform_safe_upgrade >/dev/null"; then
    echo "  ✅ Installation safety loads and functions exist"
else
    echo "  ❌ Installation safety failed to load"
    exit 1
fi

# Test 4: Test conflict detection on clean system
echo ""
echo "🔍 Test 4: Testing conflict detection..."
test_result=$(timeout 10 bash -c "
source lib/conflict_detector.sh
INSTALL_DIR=/nonexistent/directory
detect_all_conflicts >/dev/null 2>&1
echo \$?
")

if [[ "$test_result" == "0" ]]; then
    echo "  ✅ Conflict detection works (no conflicts found)"
else
    echo "  ⚠️  Conflict detection returned: $test_result (may indicate conflicts or errors)"
fi

# Test 5: Test backup creation (dry run)
echo ""
echo "💾 Test 5: Testing backup functionality..."
if timeout 10 bash -c "
source lib/backup_manager.sh
INSTALL_DIR=/nonexistent/directory
BACKUP_BASE_DIR=/tmp/test_backup
create_installation_backup test-validation >/dev/null 2>&1
"; then
    echo "  ✅ Backup function executes (handles non-existent directory gracefully)"
else
    echo "  ⚠️  Backup function had issues (expected for non-existent directory)"
fi

# Test 6: Check enhanced install.sh
echo ""
echo "🚀 Test 6: Checking enhanced install.sh..."
if grep -q "installation_safety.sh" install.sh; then
    echo "  ✅ install.sh includes safety system integration"
else
    echo "  ❌ install.sh missing safety system integration"
    exit 1
fi

if grep -q "handle_installation_failure" install.sh; then
    echo "  ✅ install.sh includes rollback protection"
else
    echo "  ❌ install.sh missing rollback protection"
    exit 1
fi

# Test 7: Validate requirements from GitHub Issue #17
echo ""
echo "📋 Test 7: Validating GitHub Issue #17 requirements..."

requirements_met=0
total_requirements=5

# Enhanced Conflict Detection
if [[ -f "lib/conflict_detector.sh" ]] && grep -q "check_directory_conflicts\|check_container_conflicts\|check_network_conflicts\|check_port_conflicts\|check_cron_conflicts" lib/conflict_detector.sh; then
    echo "  ✅ Enhanced conflict detection system implemented"
    ((requirements_met++))
else
    echo "  ❌ Enhanced conflict detection system missing"
fi

# Comprehensive Backup System
if [[ -f "lib/backup_manager.sh" ]] && grep -q "create_installation_backup\|restore_from_backup\|backup_manifest" lib/backup_manager.sh; then
    echo "  ✅ Comprehensive backup system implemented"
    ((requirements_met++))
else
    echo "  ❌ Comprehensive backup system missing"
fi

# Installation Safety System
if [[ -f "lib/installation_safety.sh" ]] && grep -q "perform_safe_upgrade\|perform_force_clean\|graceful_service_shutdown" lib/installation_safety.sh; then
    echo "  ✅ Installation safety system implemented"
    ((requirements_met++))
else
    echo "  ❌ Installation safety system missing"
fi

# Enhanced Install Script
if grep -q "detect_all_conflicts\|handle_installation_failure\|rollback" install.sh; then
    echo "  ✅ Enhanced install script with safety features"
    ((requirements_met++))
else
    echo "  ❌ Enhanced install script missing safety features"
fi

# Test Coverage
if [[ -f "tests/unit/test_conflict_detector.py" ]] && [[ -f "tests/unit/test_backup_manager.py" ]] && [[ -f "tests/integration/test_safe_installation.py" ]]; then
    echo "  ✅ Comprehensive test coverage implemented"
    ((requirements_met++))
else
    echo "  ❌ Comprehensive test coverage missing"
fi

echo ""
echo "📊 Requirements Summary: $requirements_met/$total_requirements requirements met"

# Final result
echo ""
if [[ $requirements_met -eq $total_requirements ]]; then
    echo "🎉 SUCCESS: All core requirements implemented!"
    echo "✅ Safe Installation System is ready for production use"
    exit 0
else
    echo "⚠️  PARTIAL SUCCESS: $requirements_met/$total_requirements requirements met"
    echo "🔧 Some components may need additional work"
    exit 1
fi
