#!/bin/bash
#
# Calendar Sync Fix Script
# Purpose: Diagnose and fix calendar sync issues for FOGIS deployment
# Date: October 5, 2025
#

set -e

echo "=================================================="
echo "FOGIS Calendar Sync Diagnostic & Fix Tool"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

print_info() {
    echo -e "${YELLOW}ℹ️${NC}  $1"
}

# Step 1: Check service status
echo "Step 1: Checking service status..."
echo "-----------------------------------"

if docker ps | grep -q "process-matches-service"; then
    print_status "Match-list-processor service is running"
else
    print_error "Match-list-processor service is NOT running"
    exit 1
fi

if docker ps | grep -q "fogis-calendar-phonebook-sync"; then
    print_status "Calendar sync service is running"
else
    print_error "Calendar sync service is NOT running"
    exit 1
fi

if docker ps | grep -q "fogis-redis"; then
    print_status "Redis service is running"
else
    print_error "Redis service is NOT running"
    exit 1
fi

echo ""

# Step 2: Check for recent sync errors
echo "Step 2: Checking for recent sync errors..."
echo "-------------------------------------------"

if docker logs fogis-calendar-phonebook-sync --tail 200 2>&1 | grep -qi "error\|failed\|exception"; then
    print_error "Errors found in calendar sync logs"
    echo ""
    echo "Recent errors:"
    docker logs fogis-calendar-phonebook-sync --tail 200 2>&1 | grep -i "error\|failed\|exception" | tail -10
    echo ""
else
    print_warning "No recent errors in calendar sync logs (but also no sync activity)"
fi

echo ""

# Step 3: Check match data
echo "Step 3: Checking match data..."
echo "-------------------------------"

if [ -f "data/process-matches-service/previous_matches.json" ]; then
    MATCH_COUNT=$(cat data/process-matches-service/previous_matches.json | grep -c '"matchid"' || echo "0")
    print_status "Found $MATCH_COUNT matches in data store"

    # Check for Grebbestads IF match
    if grep -q "Grebbestads IF" data/process-matches-service/previous_matches.json; then
        print_status "Grebbestads IF - IK Tord match is present in data"
    else
        print_warning "Grebbestads IF - IK Tord match NOT found in data"
    fi
else
    print_error "Match data file not found"
fi

echo ""

# Step 4: Provide fix options
echo "Step 4: Fix Options"
echo "-------------------"
echo ""
echo "Based on the diagnostic report, the calendar sync is broken due to"
echo "FOGIS API authentication failure. Here are your options:"
echo ""
echo "Option 1: Test FOGIS API Authentication"
echo "  - Verify credentials are correct"
echo "  - Test login to FOGIS"
echo ""
echo "Option 2: Force Fresh Sync (Recommended)"
echo "  - Delete previous matches cache"
echo "  - Restart match-list-processor"
echo "  - System will treat all matches as new"
echo ""
echo "Option 3: Manual Sync Trigger"
echo "  - Trigger calendar sync via API"
echo "  - Requires authentication to be working"
echo ""
echo "Option 4: View Detailed Logs"
echo "  - View full logs for debugging"
echo ""

read -p "Select an option (1-4) or 'q' to quit: " choice

case $choice in
    1)
        echo ""
        echo "Testing FOGIS API Authentication..."
        echo "-----------------------------------"

        # Check if credentials are set
        if docker exec fogis-calendar-phonebook-sync env | grep -q "FOGIS_USERNAME"; then
            USERNAME=$(docker exec fogis-calendar-phonebook-sync env | grep "FOGIS_USERNAME" | cut -d'=' -f2)
            print_status "FOGIS_USERNAME is set: $USERNAME"
        else
            print_error "FOGIS_USERNAME is not set"
        fi

        if docker exec fogis-calendar-phonebook-sync env | grep -q "FOGIS_PASSWORD"; then
            print_status "FOGIS_PASSWORD is set (value hidden)"
        else
            print_error "FOGIS_PASSWORD is not set"
        fi

        echo ""
        print_info "To test authentication, try logging in to FOGIS web interface manually"
        print_info "URL: https://fogis.svenskfotboll.se/"
        ;;

    2)
        echo ""
        echo "Force Fresh Sync"
        echo "----------------"
        print_warning "This will delete the previous matches cache and restart the service"
        print_warning "All matches will be treated as new and synced to calendar"
        echo ""
        read -p "Are you sure you want to continue? (yes/no): " confirm

        if [ "$confirm" = "yes" ]; then
            echo ""
            print_info "Stopping match-list-processor service..."
            docker-compose stop process-matches-service

            print_info "Backing up previous matches..."
            if [ -f "data/process-matches-service/previous_matches.json" ]; then
                cp data/process-matches-service/previous_matches.json \
                   data/process-matches-service/previous_matches.json.backup.$(date +%Y%m%d_%H%M%S)
                print_status "Backup created"
            fi

            print_info "Deleting previous matches cache..."
            rm -f data/process-matches-service/previous_matches.json
            print_status "Cache deleted"

            print_info "Starting match-list-processor service..."
            docker-compose up -d process-matches-service
            print_status "Service started"

            echo ""
            print_status "Fresh sync initiated!"
            print_info "Monitor logs with: docker logs -f process-matches-service"
            print_info "Wait for next processing cycle (up to 1 hour) or restart service to trigger immediately"
        else
            print_info "Operation cancelled"
        fi
        ;;

    3)
        echo ""
        echo "Manual Sync Trigger"
        echo "-------------------"
        print_info "Triggering calendar sync via API..."

        if curl -X POST http://localhost:9083/sync 2>&1; then
            echo ""
            print_status "Sync request sent"
            print_info "Check logs: docker logs -f fogis-calendar-phonebook-sync"
        else
            echo ""
            print_error "Failed to trigger sync"
            print_info "Make sure the calendar sync service is running and accessible"
        fi
        ;;

    4)
        echo ""
        echo "Detailed Logs"
        echo "-------------"
        echo ""
        echo "Select which logs to view:"
        echo "1. Match-list-processor logs"
        echo "2. Calendar sync logs"
        echo "3. Both"
        echo ""
        read -p "Select (1-3): " log_choice

        case $log_choice in
            1)
                echo ""
                print_info "Match-list-processor logs (last 100 lines):"
                echo "-------------------------------------------"
                docker logs process-matches-service --tail 100
                ;;
            2)
                echo ""
                print_info "Calendar sync logs (last 100 lines):"
                echo "------------------------------------"
                docker logs fogis-calendar-phonebook-sync --tail 100
                ;;
            3)
                echo ""
                print_info "Match-list-processor logs (last 50 lines):"
                echo "-------------------------------------------"
                docker logs process-matches-service --tail 50
                echo ""
                print_info "Calendar sync logs (last 50 lines):"
                echo "------------------------------------"
                docker logs fogis-calendar-phonebook-sync --tail 50
                ;;
            *)
                print_error "Invalid choice"
                ;;
        esac
        ;;

    q|Q)
        print_info "Exiting..."
        exit 0
        ;;

    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "=================================================="
echo "For detailed diagnostic report, see:"
echo "MATCH_SYNC_DIAGNOSTIC_REPORT.md"
echo "=================================================="
