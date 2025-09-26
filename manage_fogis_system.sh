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
    echo ""
    echo "Configuration Management:"
    echo "  config-init     - Initialize portable configuration"
    echo "  config-validate - Validate configuration"
    echo "  config-generate - Generate config files from YAML"
    echo "  config-migrate  - Migrate from legacy to portable configuration"
    echo "  config-status   - Show configuration status and migration info"
    echo "  config-info     - Display detailed configuration information"
    echo "  setup-wizard    - Run interactive setup wizard for new installations"
    echo ""
    echo "OAuth Management:"
    echo "  setup-oauth     - Run comprehensive OAuth authentication wizard"
    echo "  oauth-status    - Show OAuth authentication status"
    echo "  oauth-test      - Test OAuth connectivity with Google services"
    echo ""
    echo "Backup Management:"
    echo "  backup-create   - Create system backup (complete, config, or credentials)"
    echo "  backup-restore  - Restore system from backup"
    echo "  backup-list     - List available backups"
    echo ""
    echo "Infrastructure as Code:"
    echo "  iac-generate    - Generate Infrastructure as Code templates"
    echo ""
    echo "Monitoring and Health:"
    echo "  health-check    - Run comprehensive system health check"
    echo "  performance-report - Generate detailed performance report"
    echo ""
    echo "Quick Deployment:"
    echo "  quick-setup     - Lightning-fast deployment (5-10 minutes)"
    echo ""
    echo "Testing Commands:"
    echo "  test-integration - Run Redis pub/sub integration tests"
    echo "  test-setup      - Set up integration test environment"
    echo "  test-cleanup    - Clean up integration test environment"
    echo ""
    echo "Other Commands:"
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
    CRON_COMMAND="0 * * * * cd $SCRIPT_DIR && docker-compose -f docker-compose.yml run --rm match-list-processor python match_list_processor.py >> logs/cron/match-processing.log 2>&1"

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
    docker-compose -f docker-compose.yml down

    # Pull latest images
    print_info "Pulling latest images..."
    docker-compose -f docker-compose.yml pull

    # Start services
    print_info "Starting updated services..."
    docker-compose -f docker-compose.yml up -d

    # Wait for services to be ready
    sleep 30

    # Check health
    print_info "Verifying service health..."
    if docker-compose -f docker-compose.yml ps | grep -q "Up"; then
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
        docker-compose -f docker-compose.yml up -d
        print_status "Services started"
        ;;
    stop)
        print_info "Stopping FOGIS services..."
        docker-compose -f docker-compose.yml down
        print_status "Services stopped"
        ;;
    restart)
        print_info "Restarting FOGIS services..."
        docker-compose -f docker-compose.yml restart
        print_status "Services restarted"
        ;;
    status)
        print_info "FOGIS Service Status:"
        echo ""
        docker-compose -f docker-compose.yml ps
        ;;
    logs)
        if [ -z "$2" ]; then
            print_info "Showing logs for all services..."
            docker-compose -f docker-compose.yml logs --tail=50
        else
            print_info "Showing logs for $2..."
            docker-compose -f docker-compose.yml logs --tail=50 "$2"
        fi
        ;;
    test)
        print_info "Running test match processing..."
        echo ""
        docker-compose -f docker-compose.yml run --rm match-list-processor python match_list_processor.py
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
    config-init)
        print_info "Initializing portable configuration..."
        if [[ -f "fogis-config.yaml" ]]; then
            print_warning "fogis-config.yaml already exists"
            read -p "Overwrite? (y/N): " confirm
            if [[ $confirm != "y" ]]; then
                print_info "Operation cancelled"
                exit 0
            fi
        fi

        if [[ ! -f "templates/fogis-config.template.yaml" ]]; then
            print_error "Configuration template not found: templates/fogis-config.template.yaml"
            exit 1
        fi

        cp templates/fogis-config.template.yaml fogis-config.yaml
        print_status "Portable configuration initialized"
        print_info "Edit fogis-config.yaml and run: $0 config-generate"
        ;;
    config-validate)
        print_info "Validating configuration..."
        if ! python3 lib/config_validator.py; then
            print_error "Configuration validation failed"
            exit 1
        fi
        print_status "Configuration validation passed"
        ;;
    config-generate)
        print_info "Generating configuration files..."
        if ! python3 lib/config_generator.py; then
            print_error "Configuration generation failed"
            exit 1
        fi
        print_status "Configuration files generated successfully"
        ;;
    config-migrate)
        print_info "Starting configuration migration..."
        if ! python3 lib/migration_tool.py migrate; then
            print_error "Configuration migration failed"
            exit 1
        fi
        print_status "Configuration migration completed successfully"
        ;;
    config-status)
        print_info "Configuration status:"
        python3 lib/migration_tool.py status
        ;;
    config-info)
        print_info "Configuration information:"
        echo ""

        # Detect current configuration mode
        if [[ -f "fogis-config.yaml" ]]; then
            print_status "Current mode: Portable Configuration"
            echo "Configuration file: fogis-config.yaml"

            # Show basic config info
            if command -v python3 >/dev/null 2>&1; then
                python3 -c "
import yaml
try:
    with open('fogis-config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    print(f\"Version: {config.get('metadata', {}).get('version', 'Unknown')}\")
    print(f\"Created: {config.get('metadata', {}).get('created', 'Unknown')}\")
    print(f\"FOGIS User: {config.get('fogis', {}).get('username', 'Not configured')}\")
    print(f\"Calendar ID: {config.get('google', {}).get('calendar', {}).get('calendar_id', 'Not configured')}\")
except Exception as e:
    print(f\"Error reading configuration: {e}\")
"
            fi
        elif [[ -f ".env" ]]; then
            print_status "Current mode: Legacy Configuration"
            echo "Configuration files: .env, config.json"

            # Show basic .env info
            if [[ -f ".env" ]]; then
                echo "FOGIS User: $(grep '^FOGIS_USERNAME=' .env 2>/dev/null | cut -d'=' -f2 || echo 'Not configured')"
                echo "Calendar ID: $(grep '^GOOGLE_CALENDAR_ID=' .env 2>/dev/null | cut -d'=' -f2 || echo 'Not configured')"
            fi
        else
            print_warning "No configuration found"
            echo "Run './manage_fogis_system.sh setup-wizard' to get started"
        fi

        echo ""
        echo "Available backups:"
        ls -la fogis-config-backup-*.tar.gz 2>/dev/null || echo "  No backups found"
        ;;
    setup-wizard)
        print_info "Starting interactive setup wizard..."
        if ! python3 lib/interactive_setup.py; then
            print_error "Setup wizard failed"
            exit 1
        fi
        print_status "Setup wizard completed successfully"
        ;;
    setup-oauth)
        print_info "Starting OAuth authentication wizard..."
        if ! python3 lib/oauth_wizard.py setup; then
            print_error "OAuth setup failed"
            exit 1
        fi
        print_status "OAuth authentication setup completed successfully"
        ;;
    oauth-status)
        print_info "OAuth authentication status:"
        python3 lib/oauth_wizard.py status
        ;;
    oauth-test)
        print_info "Testing OAuth connectivity..."
        if ! python3 lib/oauth_wizard.py test; then
            print_error "OAuth connectivity test failed"
            exit 1
        fi
        print_status "OAuth connectivity test completed successfully"
        ;;
    backup-create)
        backup_type="${2:-complete}"
        print_info "Creating $backup_type backup..."
        if ! python3 lib/backup_manager.py create "$backup_type"; then
            print_error "Backup creation failed"
            exit 1
        fi
        print_status "Backup created successfully"
        ;;
    backup-restore)
        if [ -z "${2:-}" ]; then
            print_error "Usage: $0 backup-restore <backup_file> [--auto-start]"
            exit 1
        fi
        backup_file="$2"
        auto_start="${3:-}"

        print_info "Restoring from backup: $backup_file"
        if ! python3 lib/backup_manager.py restore "$backup_file"; then
            print_error "Backup restore failed"
            exit 1
        fi

        # Auto-start services if requested
        if [ "$auto_start" = "--auto-start" ]; then
            print_info "Auto-starting services after restore..."
            if ! docker compose up -d; then
                print_warning "Failed to auto-start services. You may need to start them manually."
            else
                print_status "Services started successfully"
            fi
        fi

        print_status "Backup restored successfully"
        ;;
    backup-list)
        print_info "Available backups:"
        python3 lib/backup_manager.py list
        ;;
    iac-generate)
        platform="${2:-all}"
        print_info "Generating Infrastructure as Code templates for: $platform"
        if ! python3 lib/iac_generator.py "$platform"; then
            print_error "IaC template generation failed"
            exit 1
        fi
        print_status "Infrastructure as Code templates generated successfully"
        ;;
    health-check)
        print_info "Running comprehensive health check..."
        if ! python3 lib/monitoring_setup.py health-check; then
            print_error "Health check failed"
            exit 1
        fi
        print_status "Health check completed successfully"
        ;;
    performance-report)
        print_info "Generating performance report..."
        if ! python3 lib/monitoring_setup.py performance-report; then
            print_error "Performance report generation failed"
            exit 1
        fi
        print_status "Performance report generated successfully"
        ;;
    quick-setup)
        print_info "Starting lightning-fast FOGIS deployment..."
        if ! bash scripts/quick-setup.sh; then
            print_error "Quick setup failed"
            exit 1
        fi
        print_status "Quick setup completed successfully"
        ;;
    test-integration)
        print_info "Running Redis pub/sub integration tests..."
        echo ""
        if [ -f "tests/run_integration_tests.sh" ]; then
            ./tests/run_integration_tests.sh "$@"
        else
            print_error "Integration test script not found. Please ensure tests/run_integration_tests.sh exists."
            exit 1
        fi
        ;;
    test-setup)
        print_info "Setting up integration test environment..."
        echo ""
        if [ -f "tests/run_integration_tests.sh" ]; then
            ./tests/run_integration_tests.sh --setup-only
        else
            print_error "Integration test script not found. Please ensure tests/run_integration_tests.sh exists."
            exit 1
        fi
        ;;
    test-cleanup)
        print_info "Cleaning up integration test environment..."
        echo ""
        if [ -f "tests/run_integration_tests.sh" ]; then
            ./tests/run_integration_tests.sh --cleanup
        else
            print_error "Integration test script not found. Please ensure tests/run_integration_tests.sh exists."
            exit 1
        fi
        ;;
    *)
        show_usage
        ;;
esac
