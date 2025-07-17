#!/bin/bash

# FOGIS System Recovery Script
# Handles system recovery after Docker restarts, updates, or failures

set -e

echo "🔄 FOGIS SYSTEM RECOVERY"
echo "======================="

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

# Check if Docker is running
check_docker() {
    log_info "Checking Docker status..."
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    log_success "Docker is running"
}

# Check data persistence
check_data_persistence() {
    log_info "Checking data persistence..."

    local critical_files=(
        "data/match-list-change-detector/previous_matches.json"
        "data/fogis-calendar-phonebook-sync/token.json"
        "data/google-drive-service/google-drive-token.json"
    )

    local missing_files=()
    for file in "${critical_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done

    if [ ${#missing_files[@]} -gt 0 ]; then
        log_warning "Missing critical files:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        log_warning "You may need to re-authenticate services"
    else
        log_success "All critical data files present"
    fi
}

# Start services in correct order
start_services() {
    log_info "Starting FOGIS services in correct order..."

    # Start core services first
    log_info "Starting core services..."
    docker-compose -f docker-compose.yml up -d fogis-api-client-service
    sleep 10

    # Start processing services
    log_info "Starting processing services..."
    docker-compose -f docker-compose.yml up -d match-list-processor team-logo-combiner google-drive-service
    sleep 15

    # Start sync services
    log_info "Starting sync services..."
    docker-compose -f docker-compose.yml up -d fogis-calendar-phonebook-sync
    sleep 10

    # Start change detector and scheduler
    log_info "Starting monitoring services..."
    docker-compose -f docker-compose.yml up -d match-list-change-detector cron-scheduler

    log_success "All services started"
}

# Check service health
check_service_health() {
    log_info "Checking service health..."

    local services=(
        "fogis-api-client-service:9086"
        "match-list-change-detector:9082"
        "match-list-processor:9081"
        "team-logo-combiner:9088"
        "google-drive-service:9085"
        "fogis-calendar-phonebook-sync:9083"
    )

    local unhealthy_services=()

    for service_port in "${services[@]}"; do
        local service=$(echo "$service_port" | cut -d: -f1)
        local port=$(echo "$service_port" | cut -d: -f2)

        log_info "Checking $service..."

        local healthy=false
        for i in {1..30}; do
            if curl -f "http://localhost:$port/health" &>/dev/null; then
                log_success "$service is healthy"
                healthy=true
                break
            fi
            sleep 2
        done

        if [ "$healthy" = false ]; then
            log_error "$service failed health check"
            unhealthy_services+=("$service")
        fi
    done

    if [ ${#unhealthy_services[@]} -gt 0 ]; then
        log_error "Unhealthy services detected:"
        for service in "${unhealthy_services[@]}"; do
            echo "  - $service"
        done
        return 1
    fi

    log_success "All services are healthy"
    return 0
}

# Check authentication status
check_authentication() {
    log_info "Checking authentication status..."

    # Check if tokens exist and are not expired
    local auth_issues=()

    if [ ! -f "data/fogis-calendar-phonebook-sync/token.json" ]; then
        auth_issues+=("Calendar/Contacts authentication missing")
    fi

    if [ ! -f "data/google-drive-service/google-drive-token.json" ]; then
        auth_issues+=("Google Drive authentication missing")
    fi

    if [ ${#auth_issues[@]} -gt 0 ]; then
        log_warning "Authentication issues detected:"
        for issue in "${auth_issues[@]}"; do
            echo "  - $issue"
        done
        log_info "Run: python authenticate_all_services.py"
        return 1
    fi

    log_success "Authentication appears to be in place"
    return 0
}

# Main recovery process
main() {
    echo "🔄 Starting system recovery process..."
    echo ""

    check_docker
    check_data_persistence
    start_services

    if check_service_health; then
        if check_authentication; then
            echo ""
            echo "🎉 SYSTEM RECOVERY COMPLETE!"
            echo "✅ All services are running and healthy"
            echo "✅ Authentication is in place"
            echo ""
            echo "🌐 Service URLs:"
            echo "- FOGIS API Client: http://localhost:9086/health"
            echo "- Match Change Detector: http://localhost:9082/health"
            echo "- Match Processor: http://localhost:9081/health"
            echo "- Avatar Service: http://localhost:9088/health"
            echo "- Google Drive: http://localhost:9085/health"
            echo "- Calendar Sync: http://localhost:9083/health"
        else
            echo ""
            echo "⚠️  SYSTEM RECOVERED WITH AUTHENTICATION ISSUES"
            echo "Please run: python authenticate_all_services.py"
        fi
    else
        echo ""
        echo "❌ SYSTEM RECOVERY FAILED"
        echo "Some services are not healthy. Check logs:"
        echo "docker-compose -f docker-compose.yml logs [service-name]"
        exit 1
    fi
}

# Run recovery
main "$@"
