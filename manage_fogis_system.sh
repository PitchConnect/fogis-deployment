#!/bin/bash

# FOGIS System Management Script
# Easy commands for managing the FOGIS containerized system

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to show usage
show_usage() {
    echo "🔧 FOGIS System Management"
    echo "=========================="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start       - Start all FOGIS services"
    echo "  stop        - Stop all FOGIS services"
    echo "  restart     - Restart all FOGIS services"
    echo "  status      - Show service status"
    echo "  logs        - Show logs for all services"
    echo "  logs [name] - Show logs for specific service"
    echo "  test        - Run a test match processing"
    echo "  health      - Check health of all services"
    echo "  cron-add    - Add hourly cron job"
    echo "  cron-remove - Remove cron job"
    echo "  cron-status - Show cron job status"
    echo "  setup-auth  - Enhanced OAuth setup wizard (5-8 min setup)"
    echo "  clean       - Clean up stopped containers and images"
    echo "  check-updates - Check for available image updates"
    echo "  update      - Update all services to latest versions"
    echo "  version     - Show current service versions"
    echo "  rollback    - Rollback to previous version"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 logs match-list-processor"
    echo "  $0 test"
    echo "  $0 check-updates"
    echo "  $0 update"
}

# Function to add cron job
add_cron() {
    CRON_COMMAND="0 * * * * cd $SCRIPT_DIR && docker-compose -f docker-compose-master.yml run --rm match-list-processor python match_list_processor.py >> logs/cron/match-processing.log 2>&1"

    if crontab -l 2>/dev/null | grep -q "match-list-processor"; then
        print_warning "FOGIS cron job already exists"
    else
        (crontab -l 2>/dev/null; echo "$CRON_COMMAND") | crontab -
        print_status "Cron job added - runs every hour"
    fi
}

# Function to check for image updates
check_updates() {
    print_info "Checking for available image updates..."

    local services=(
        "ghcr.io/pitchconnect/fogis-api-client-service"
        "ghcr.io/pitchconnect/team-logo-combiner"
        "ghcr.io/pitchconnect/match-list-processor"
        "ghcr.io/pitchconnect/match-list-change-detector"
        "ghcr.io/pitchconnect/fogis-calendar-phonebook-sync"
        "ghcr.io/pitchconnect/google-drive-service"
    )

    local updates_available=false

    for service in "${services[@]}"; do
        local current_digest=$(docker images --digests "$service:latest" --format "{{.Digest}}" 2>/dev/null)
        local remote_digest=$(docker manifest inspect "$service:latest" 2>/dev/null | jq -r '.config.digest' 2>/dev/null)

        if [ "$current_digest" != "$remote_digest" ] && [ -n "$remote_digest" ]; then
            echo "🔄 $service: Update available"
            updates_available=true
        else
            echo "✅ $service: Up to date"
        fi
    done

    if [ "$updates_available" = true ]; then
        print_info "Updates available! Run '$0 update' to update all services."
        return 1
    else
        print_status "All services are up to date"
        return 0
    fi
}

# Function to update all services
update_services() {
    print_info "Updating all FOGIS services..."

    # Stop services
    print_info "Stopping services..."
    docker-compose -f docker-compose-master.yml down

    # Pull latest images
    print_info "Pulling latest images..."
    docker-compose -f docker-compose-master.yml pull

    # Start services
    print_info "Starting updated services..."
    docker-compose -f docker-compose-master.yml up -d

    # Wait for services to be ready
    sleep 30

    # Check health
    print_info "Verifying service health..."
    if docker-compose -f docker-compose-master.yml ps | grep -q "Up"; then
        print_status "Update completed successfully"
    else
        print_error "Some services failed to start after update"
        return 1
    fi
}

# Function to show current versions
show_versions() {
    print_info "Current service versions:"

    local services=(
        "fogis-api-client-service"
        "team-logo-combiner"
        "match-list-processor"
        "match-list-change-detector"
        "fogis-calendar-phonebook-sync"
        "google-drive-service"
    )

    for service in "${services[@]}"; do
        local image_info=$(docker images "ghcr.io/pitchconnect/$service" --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}" | tail -n +2)
        if [ -n "$image_info" ]; then
            echo "📦 $service: $image_info"
        else
            echo "❌ $service: Not found locally"
        fi
    done
}

# Function to rollback to previous version
rollback_services() {
    print_warning "Rollback functionality requires version tags to be implemented"
    print_info "Current implementation uses :latest tags only"
    print_info "To rollback manually:"
    echo "  1. Stop services: $0 stop"
    echo "  2. Pull specific version: docker pull ghcr.io/pitchconnect/SERVICE:VERSION"
    echo "  3. Update docker-compose.yml with specific version tags"
    echo "  4. Start services: $0 start"
}

# Function to remove cron job
remove_cron() {
    if crontab -l 2>/dev/null | grep -q "match-list-processor"; then
        crontab -l 2>/dev/null | grep -v "match-list-processor" | crontab -
        print_status "Cron job removed"
    else
        print_warning "No FOGIS cron job found"
    fi
}

# Function to show cron status
cron_status() {
    if crontab -l 2>/dev/null | grep -q "match-list-processor"; then
        print_status "FOGIS cron job is active:"
        crontab -l 2>/dev/null | grep "match-list-processor"
    else
        print_warning "No FOGIS cron job found"
    fi
}

# Main script logic
case "$1" in
    start)
        print_info "Starting FOGIS services..."
        docker-compose -f docker-compose-master.yml up -d
        print_status "Services started"
        ;;
    stop)
        print_info "Stopping FOGIS services..."
        docker-compose -f docker-compose-master.yml down
        print_status "Services stopped"
        ;;
    restart)
        print_info "Restarting FOGIS services..."
        docker-compose -f docker-compose-master.yml restart
        print_status "Services restarted"
        ;;
    status)
        print_info "FOGIS Service Status:"
        echo ""
        docker-compose -f docker-compose-master.yml ps
        ;;
    logs)
        if [ -z "$2" ]; then
            print_info "Showing logs for all services..."
            docker-compose -f docker-compose-master.yml logs --tail=50
        else
            print_info "Showing logs for $2..."
            docker-compose -f docker-compose-master.yml logs --tail=50 "$2"
        fi
        ;;
    test)
        print_info "Running test match processing..."
        echo ""
        docker-compose -f docker-compose-master.yml run --rm match-list-processor python match_list_processor.py
        print_status "Test completed"
        ;;
    health)
        print_info "Checking service health..."
        echo ""
        services=("fogis-api-client-service:9086" "team-logo-combiner:9088" "fogis-calendar-phonebook-sync:9084" "google-drive-service:9085")
        for service in "${services[@]}"; do
            name=$(echo "$service" | cut -d: -f1)
            port=$(echo "$service" | cut -d: -f2)
            if curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
                print_status "$name is healthy"
            else
                print_warning "$name is not responding"
            fi
        done
        ;;
    cron-add)
        add_cron
        ;;
    cron-remove)
        remove_cron
        ;;
    cron-status)
        cron_status
        ;;
    setup-auth)
        print_info "Starting enhanced OAuth setup wizard..."

        # Check if enhanced wizard is available
        if [[ -f "lib/enhanced_oauth_wizard.py" ]]; then
            print_info "Using enhanced OAuth wizard with browser automation..."
            if python3 lib/enhanced_oauth_wizard.py; then
                print_status "Enhanced OAuth setup completed successfully!"
            else
                print_error "Enhanced OAuth setup failed"
                print_info "Falling back to standard credential wizard..."

                # Fallback to original wizard
                if ! python3 lib/credential_wizard.py 2>/dev/null; then
                    print_info "Using minimal credential wizard..."
                    python3 lib/minimal_wizard.py
                fi
            fi
        else
            print_warning "Enhanced OAuth wizard not found, using standard wizard..."
            # Try the full wizard first, fallback to minimal wizard if needed
            if ! python3 lib/credential_wizard.py 2>/dev/null; then
                print_info "Using minimal credential wizard..."
                python3 lib/minimal_wizard.py
            fi
        fi
        ;;
    clean)
        print_info "Cleaning up Docker containers and images..."
        docker system prune -f
        print_status "Cleanup completed"
        ;;
    check-updates)
        check_updates
        ;;
    update)
        update_services
        ;;
    version)
        show_versions
        ;;
    rollback)
        rollback_services
        ;;
    *)
        show_usage
        ;;
esac
