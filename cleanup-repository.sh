#!/bin/bash
#
# Repository Cleanup Script
# Purpose: Remove temporary debug scripts, investigation reports, and organize documentation
# Safety: Includes dry-run mode and confirmation prompts
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
FILES_TO_DELETE=0
FILES_TO_MOVE=0
DIRS_TO_CREATE=0

# Mode flags
DRY_RUN=true
INTERACTIVE=true

# Print functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC}  $1"
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Repository cleanup script to remove temporary files and organize documentation.

OPTIONS:
    --dry-run       Show what would be done without making changes (default)
    --execute       Actually perform the cleanup operations
    --yes           Skip confirmation prompts (use with caution!)
    --help          Show this help message

EXAMPLES:
    $0                          # Dry-run mode (safe, shows what would happen)
    $0 --execute                # Execute with confirmation prompts
    $0 --execute --yes          # Execute without prompts (dangerous!)

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --execute)
            DRY_RUN=false
            shift
            ;;
        --yes)
            INTERACTIVE=false
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Display mode
print_header "Repository Cleanup Script"
if [ "$DRY_RUN" = true ]; then
    print_warning "DRY-RUN MODE: No changes will be made"
    print_info "Use --execute to actually perform cleanup"
else
    print_warning "EXECUTE MODE: Changes will be made to your repository"
    if [ "$INTERACTIVE" = false ]; then
        print_warning "Non-interactive mode: No confirmation prompts"
    fi
fi
echo ""

# Function to delete file
delete_file() {
    local file="$1"
    local reason="$2"

    if [ -f "$file" ]; then
        FILES_TO_DELETE=$((FILES_TO_DELETE + 1))
        if [ "$DRY_RUN" = true ]; then
            echo "  [DRY-RUN] Would delete: $file"
            echo "            Reason: $reason"
        else
            rm "$file"
            print_success "Deleted: $file"
        fi
    else
        if [ "$DRY_RUN" = true ]; then
            echo "  [SKIP] File not found: $file"
        fi
    fi
}

# Function to move file
move_file() {
    local src="$1"
    local dest="$2"
    local reason="$3"

    if [ -f "$src" ]; then
        FILES_TO_MOVE=$((FILES_TO_MOVE + 1))
        if [ "$DRY_RUN" = true ]; then
            echo "  [DRY-RUN] Would move: $src"
            echo "            To: $dest"
            echo "            Reason: $reason"
        else
            mkdir -p "$(dirname "$dest")"
            mv "$src" "$dest"
            print_success "Moved: $src → $dest"
        fi
    else
        if [ "$DRY_RUN" = true ]; then
            echo "  [SKIP] File not found: $src"
        fi
    fi
}

# Function to create directory
create_dir() {
    local dir="$1"

    if [ ! -d "$dir" ]; then
        DIRS_TO_CREATE=$((DIRS_TO_CREATE + 1))
        if [ "$DRY_RUN" = true ]; then
            echo "  [DRY-RUN] Would create directory: $dir"
        else
            mkdir -p "$dir"
            print_success "Created directory: $dir"
        fi
    fi
}

# ============================================================================
# FILE LISTS
# ============================================================================

# Python debug/test scripts to delete
PYTHON_SCRIPTS_TO_DELETE=(
    "force_sync_match_6143017.py"
    "force_update_match_6143017.py"
    "manual_sync_match_6143017.py"
    "subscriber_fix_auto_restart.py"
    "subscriber_fix_watchdog.py"
    "app_with_redis_integration.py"
    "calendar_service_redis_subscriber_update.py"
    "match_list_processor_publisher_integration.py"
    "match_list_processor_redis_formatter_update.py"
    "enhanced_schema_v2_implementation.py"
    "enhanced_schema_v2_integration_test.py"
    "enhanced_schema_validation_tests.py"
    "logging_analysis.py"
)

# Shell scripts to delete
SHELL_SCRIPTS_TO_DELETE=(
    "apply_subscriber_fix.sh"
    "direct_force_sync.sh"
)

# Configuration variants to delete
CONFIG_FILES_TO_DELETE=(
    "ci_updated.yml"
    "precommit_updated.yaml"
    "pyproject_fixed.toml"
    "pyproject_original.toml"
    "pyproject_updated.toml"
    "enhanced_schema_v2_corrected.json"
)

# Test images to delete
TEST_IMAGES_TO_DELETE=(
    "enhanced_schema_logo_test.png"
    "team_db_id_logo_test.png"
)

# Investigation reports to delete (Category B from analysis)
INVESTIGATION_REPORTS_TO_DELETE=(
    "ALINGSAS_HACKEN_MATCH_INVESTIGATION_REPORT.md"
    "CALENDAR_SYNC_FIX_RESULTS.md"
    "CALENDAR_SYNC_INVESTIGATION_REPORT.md"
    "CI_CD_RESOLUTION_SUMMARY.md"
    "CODE_CHANGES_REVIEW_AND_RECOMMENDATIONS.md"
    "COMPREHENSIVE_DEPLOYMENT_ANALYSIS.md"
    "DEPLOYMENT_STATUS_SUMMARY.md"
    "END_TO_END_REDIS_TEST_RESULTS.md"
    "END_TO_END_VERIFICATION_REPORT.md"
    "FINAL_CI_CD_STATUS.md"
    "FINAL_ROOT_CAUSE_AND_SOLUTION.md"
    "FOGIS_API_AUTH_CLARIFICATION.md"
    "FOGIS_API_INVESTIGATION_REPORT.md"
    "GITHUB_ISSUES_SUMMARY.md"
    "GOOGLE_PEOPLE_API_INVESTIGATION_FINDINGS.md"
    "IMPLEMENTATION_COMPLETE_SUMMARY.md"
    "INVESTIGATION_COMPLETE_SUMMARY.md"
    "INVESTIGATION_SUMMARY_COMPLETE.md"
    "MATCH_SYNC_DIAGNOSTIC_REPORT.md"
    "PR_CREATION_SUMMARY.md"
    "PR_SUMMARY.md"
    "REDIS_FIX_IMPLEMENTATION_LOG.md"
    "REDIS_INTEGRATION_IMPLEMENTATION_COMPLETE.md"
    "REDIS_INTEGRATION_NEXT_STEPS.md"
    "REDIS_PUBSUB_FIX_SUMMARY.md"
    "REDIS_PUBSUB_INVESTIGATION_REPORT.md"
    "REDIS_PUBSUB_MISSING_IMPLEMENTATION.md"
    "REDIS_TEST_ARCHITECTURE_IMPLEMENTATION_PLAN.md"
    "SCHEMA_COMPLIANCE_INVESTIGATION_REPORT.md"
    "SERVICE_RESTORATION_REPORT.md"
    "SUBSCRIBER_FIX_RECOMMENDATIONS.md"
    "SUBSCRIBER_FIX_TESTING_GUIDE.md"
    "TASK_COMPLETION_REPORT.md"
    "TASK_EXECUTION_COMPLETE_REPORT.md"
    "github_issues_implementation_plan.md"
)

# Additional documentation files to delete (after manual review)
ADDITIONAL_DOCS_TO_DELETE=(
    "QUICK_REFERENCE_REDIS_INTEGRATION.md"
    "REDIS_INTEGRATION_IMPLEMENTATION_GUIDE.md"
    "team-logo-worker-README.md"
)

# Permanent documentation to move to docs/
PERMANENT_DOCS=(
    "ARM64_IMPLEMENTATION_SUMMARY.md"
    "CALENDAR_SERVICE_AUTHENTICATION.md"
    "CALENDAR_SYNC_REFEREE_HASH_FIX.md"
    "CALENDAR_SYNC_ROOT_CAUSE_ANALYSIS.md"
    "CONFIGURATION_IMPROVEMENTS.md"
    "DEPENDABOT_TESTING_STRATEGY.md"
    "DEPLOYMENT_PREREQUISITES.md"
    "CONTAINER_IMAGE_WEBHOOK_AUTOMATION_PLAN.md"
)

# Architectural documentation to move to docs/architecture/
ARCHITECTURE_DOCS=(
    "REDIS_PUBSUB_VS_STREAMS_ANALYSIS.md"
    "redis_message_schema_analysis.md"
    "redis_schema_evolution_strategy.md"
)

# Operational documentation to move to docs/operations/
OPERATIONS_DOCS=(
    "WEBHOOK_AUTOMATION_SETUP_GUIDE.md"
)

# Deleted Loki files to stage for commit
LOKI_DELETED_FILES=(
    "monitoring/loki/boltdb-shipper-active/index_20307/1754769757439227007.temp"
    "monitoring/loki/boltdb-shipper-active/index_20308/1754769757482740007.temp"
    "monitoring/loki/boltdb-shipper-active/index_20309/1754769757497158257.temp"
    "monitoring/loki/boltdb-shipper-active/index_20355/1758745074383423297.temp"
    "monitoring/loki/boltdb-shipper-active/index_20355/1758745800.snapshot"
)

# ============================================================================
# CONFIRMATION PROMPT
# ============================================================================

if [ "$DRY_RUN" = false ] && [ "$INTERACTIVE" = true ]; then
    print_header "Confirmation Required"
    echo "This script will:"
    echo "  • Create 4 directories (scripts/diagnostics, docs, docs/architecture, docs/operations)"
    echo "  • Move 1 script to scripts/diagnostics/"
    echo "  • Move ${#PERMANENT_DOCS[@]} documentation files to docs/"
    echo "  • Move ${#ARCHITECTURE_DOCS[@]} architectural docs to docs/architecture/"
    echo "  • Move ${#OPERATIONS_DOCS[@]} operational docs to docs/operations/"
    echo "  • Delete ${#PYTHON_SCRIPTS_TO_DELETE[@]} Python scripts"
    echo "  • Delete ${#SHELL_SCRIPTS_TO_DELETE[@]} shell scripts"
    echo "  • Delete ${#CONFIG_FILES_TO_DELETE[@]} configuration files"
    echo "  • Delete ${#TEST_IMAGES_TO_DELETE[@]} test images"
    echo "  • Delete ${#INVESTIGATION_REPORTS_TO_DELETE[@]} investigation reports"
    echo "  • Delete ${#ADDITIONAL_DOCS_TO_DELETE[@]} additional documentation files"
    echo "  • Stage ${#LOKI_DELETED_FILES[@]} deleted Loki files for commit"
    echo ""
    print_warning "Total files to delete: $((${#PYTHON_SCRIPTS_TO_DELETE[@]} + ${#SHELL_SCRIPTS_TO_DELETE[@]} + ${#CONFIG_FILES_TO_DELETE[@]} + ${#TEST_IMAGES_TO_DELETE[@]} + ${#INVESTIGATION_REPORTS_TO_DELETE[@]} + ${#ADDITIONAL_DOCS_TO_DELETE[@]}))"
    echo ""
    read -p "Do you want to proceed? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        print_info "Cleanup cancelled by user"
        exit 0
    fi
    echo ""
fi

# ============================================================================
# CLEANUP OPERATIONS
# ============================================================================

print_header "Step 1: Creating Directories"
create_dir "scripts/diagnostics"
create_dir "docs"
create_dir "docs/architecture"
create_dir "docs/operations"
echo ""

print_header "Step 2: Relocating Utility Scripts"
move_file "fix_calendar_sync.sh" "scripts/diagnostics/calendar-sync-diagnostic.sh" "Reusable diagnostic tool"
echo ""

print_header "Step 3: Moving Permanent Documentation"
for doc in "${PERMANENT_DOCS[@]}"; do
    move_file "$doc" "docs/$doc" "Permanent documentation"
done
echo ""

print_header "Step 4: Moving Architectural Documentation"
for doc in "${ARCHITECTURE_DOCS[@]}"; do
    move_file "$doc" "docs/architecture/$doc" "Architectural decision record"
done
echo ""

print_header "Step 5: Moving Operational Documentation"
for doc in "${OPERATIONS_DOCS[@]}"; do
    move_file "$doc" "docs/operations/$doc" "Operational guide"
done
echo ""

print_header "Step 6: Deleting Python Debug/Test Scripts"
for script in "${PYTHON_SCRIPTS_TO_DELETE[@]}"; do
    delete_file "$script" "One-off debug/test script"
done
echo ""

print_header "Step 7: Deleting Shell Scripts"
for script in "${SHELL_SCRIPTS_TO_DELETE[@]}"; do
    delete_file "$script" "One-off debug script"
done
echo ""

print_header "Step 8: Deleting Configuration Variants"
for config in "${CONFIG_FILES_TO_DELETE[@]}"; do
    delete_file "$config" "Temporary configuration variant"
done
echo ""

print_header "Step 9: Deleting Test Images"
for image in "${TEST_IMAGES_TO_DELETE[@]}"; do
    delete_file "$image" "Test artifact"
done
echo ""

print_header "Step 10: Deleting Investigation Reports"
for report in "${INVESTIGATION_REPORTS_TO_DELETE[@]}"; do
    delete_file "$report" "Temporary investigation report"
done
echo ""

print_header "Step 11: Deleting Additional Documentation Files"
for doc in "${ADDITIONAL_DOCS_TO_DELETE[@]}"; do
    delete_file "$doc" "Temporary implementation guide"
done
echo ""

print_header "Step 12: Staging Deleted Loki Files"
if [ "$DRY_RUN" = false ]; then
    if command -v git &> /dev/null; then
        for file in "${LOKI_DELETED_FILES[@]}"; do
            if git ls-files --error-unmatch "$file" &> /dev/null; then
                git add "$file" 2>/dev/null || true
                print_success "Staged for commit: $file"
            fi
        done
    else
        print_warning "Git not found, skipping staging of deleted Loki files"
    fi
else
    print_info "Would stage ${#LOKI_DELETED_FILES[@]} deleted Loki files for commit"
fi
echo ""

# ============================================================================
# SUMMARY
# ============================================================================

print_header "Cleanup Summary"
echo "Directories to create: $DIRS_TO_CREATE"
echo "Files to move: $FILES_TO_MOVE"
echo "Files to delete: $FILES_TO_DELETE"
echo ""

if [ "$DRY_RUN" = true ]; then
    print_info "This was a DRY-RUN. No changes were made."
    echo ""
    print_info "To execute the cleanup, run:"
    echo "  $0 --execute"
    echo ""
    print_info "To execute without confirmation prompts:"
    echo "  $0 --execute --yes"
else
    print_success "Cleanup completed!"
    echo ""
    print_info "Next steps:"
    echo "  1. Review the files listed in 'Step 9: Files Requiring Manual Review'"
    echo "  2. Run 'git status' to see all changes"
    echo "  3. Proceed with Loki Docker volume migration"
    echo "  4. Review infrastructure files (.github/workflows, cloudflare-worker, tests/)"
fi
echo ""
