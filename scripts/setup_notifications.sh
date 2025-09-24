#!/bin/bash

# FOGIS Deployment - Notification System Setup Script
# This script sets up the notification system for an existing FOGIS deployment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Emojis for better visual feedback
SUCCESS="✅"
ERROR="❌"
WARNING="⚠️"
INFO="ℹ️"
SETUP="🔧"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

print_status() {
    local level=$1
    local message=$2
    
    case $level in
        "SUCCESS")
            echo -e "${GREEN}${SUCCESS} ${message}${NC}"
            ;;
        "ERROR")
            echo -e "${RED}${ERROR} ${message}${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}${WARNING} ${message}${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}${INFO} ${message}${NC}"
            ;;
        "SETUP")
            echo -e "${BLUE}${SETUP} ${message}${NC}"
            ;;
    esac
}

print_header() {
    echo
    echo "============================================================"
    echo "🔔 FOGIS Notification System Setup"
    echo "============================================================"
    echo
}

check_prerequisites() {
    print_status "INFO" "Checking prerequisites..."
    
    # Check if we're in the deployment directory
    if [ ! -f "docker-compose.yml" ]; then
        print_status "ERROR" "docker-compose.yml not found. Please run this script from the FOGIS deployment directory."
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_status "ERROR" "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check if match-list-processor service exists
    if ! docker-compose ps | grep -q "process-matches-service"; then
        print_status "WARNING" "process-matches-service not found. Make sure FOGIS deployment is running."
    fi
    
    print_status "SUCCESS" "Prerequisites check completed"
}

create_notification_config() {
    print_status "SETUP" "Setting up notification configuration..."
    
    # Create notification config directory
    mkdir -p config/notifications
    
    # Copy notification configuration from container if it doesn't exist
    if [ ! -f "config/notifications/notification_channels.yml" ]; then
        print_status "INFO" "Creating notification channels configuration..."
        
        # Try to copy from running container first
        if docker ps | grep -q "process-matches-service"; then
            docker cp process-matches-service:/app/config/notification_channels.yml config/notifications/ 2>/dev/null || {
                print_status "WARNING" "Could not copy from running container, using docker run..."
                docker run --rm -v "$(pwd)/config/notifications:/output" \
                    ghcr.io/pitchconnect/match-list-processor:latest \
                    sh -c "cp /app/config/notification_channels.yml /output/" 2>/dev/null || {
                    print_status "ERROR" "Failed to copy notification configuration. Please check container image."
                    return 1
                }
            }
        else
            docker run --rm -v "$(pwd)/config/notifications:/output" \
                ghcr.io/pitchconnect/match-list-processor:latest \
                sh -c "cp /app/config/notification_channels.yml /output/" 2>/dev/null || {
                print_status "ERROR" "Failed to copy notification configuration. Please check container image."
                return 1
            }
        fi
        
        print_status "SUCCESS" "Notification channels configuration created"
    else
        print_status "INFO" "Notification channels configuration already exists"
    fi
    
    # Copy stakeholder template if it doesn't exist
    if [ ! -f "data/process-matches-service/stakeholders.json" ]; then
        print_status "INFO" "Creating stakeholder database..."
        
        # Ensure data directory exists
        mkdir -p data/process-matches-service
        
        # Try to copy from running container first
        if docker ps | grep -q "process-matches-service"; then
            docker cp process-matches-service:/app/config/stakeholders_template.json data/process-matches-service/stakeholders.json 2>/dev/null || {
                print_status "WARNING" "Could not copy from running container, using docker run..."
                docker run --rm -v "$(pwd)/data/process-matches-service:/output" \
                    ghcr.io/pitchconnect/match-list-processor:latest \
                    sh -c "cp /app/config/stakeholders_template.json /output/stakeholders.json" 2>/dev/null || {
                    print_status "ERROR" "Failed to copy stakeholder template. Please check container image."
                    return 1
                }
            }
        else
            docker run --rm -v "$(pwd)/data/process-matches-service:/output" \
                ghcr.io/pitchconnect/match-list-processor:latest \
                sh -c "cp /app/config/stakeholders_template.json /output/stakeholders.json" 2>/dev/null || {
                print_status "ERROR" "Failed to copy stakeholder template. Please check container image."
                return 1
            }
        fi
        
        print_status "SUCCESS" "Stakeholder database created"
    else
        print_status "INFO" "Stakeholder database already exists"
    fi
}

update_docker_compose() {
    print_status "SETUP" "Checking Docker Compose configuration..."
    
    # Check if notification environment variables are already present
    if grep -q "NOTIFICATION_SYSTEM_ENABLED" docker-compose.yml; then
        print_status "INFO" "Notification environment variables already present in docker-compose.yml"
        return 0
    fi
    
    print_status "WARNING" "Docker Compose needs manual update for notification environment variables"
    print_status "INFO" "Please add the following environment variables to the process-matches-service section:"
    echo
    echo "      # Notification System Configuration"
    echo "      - NOTIFICATION_SYSTEM_ENABLED=\${NOTIFICATION_SYSTEM_ENABLED:-false}"
    echo "      - EMAIL_ENABLED=\${EMAIL_ENABLED:-false}"
    echo "      - SMTP_HOST=\${SMTP_HOST:-smtp.gmail.com}"
    echo "      - SMTP_PORT=\${SMTP_PORT:-587}"
    echo "      - SMTP_USERNAME=\${SMTP_USERNAME}"
    echo "      - SMTP_PASSWORD=\${SMTP_PASSWORD}"
    echo "      - SMTP_FROM=\${SMTP_FROM}"
    echo "      - DISCORD_ENABLED=\${DISCORD_ENABLED:-false}"
    echo "      - DISCORD_WEBHOOK_URL=\${DISCORD_WEBHOOK_URL}"
    echo "      - WEBHOOK_ENABLED=\${WEBHOOK_ENABLED:-false}"
    echo "      - WEBHOOK_URL=\${WEBHOOK_URL}"
    echo
    echo "And add this volume mount:"
    echo "      - ./config/notifications:/app/config/notifications"
    echo
}

setup_environment() {
    print_status "SETUP" "Setting up environment configuration..."
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        if [ -f ".env.template" ]; then
            print_status "INFO" "Creating .env file from template..."
            cp .env.template .env
            print_status "SUCCESS" ".env file created from template"
        else
            print_status "WARNING" ".env.template not found. Please create .env file manually."
            return 1
        fi
    else
        print_status "INFO" ".env file already exists"
    fi
    
    # Check if notification variables are present in .env
    if ! grep -q "NOTIFICATION_SYSTEM_ENABLED" .env; then
        print_status "WARNING" "Notification environment variables not found in .env"
        print_status "INFO" "Please add notification configuration to your .env file"
        print_status "INFO" "See .env.template for notification variable examples"
    else
        print_status "SUCCESS" "Notification environment variables found in .env"
    fi
}

test_notification_system() {
    print_status "SETUP" "Testing notification system..."
    
    # Check if service is running
    if ! docker ps | grep -q "process-matches-service"; then
        print_status "WARNING" "process-matches-service is not running. Please start the service to test notifications."
        return 0
    fi
    
    # Test notification system setup
    print_status "INFO" "Running notification system validation..."
    if docker exec process-matches-service python scripts/setup_notifications.py --validate-only 2>/dev/null; then
        print_status "SUCCESS" "Notification system validation passed"
    else
        print_status "WARNING" "Notification system validation failed. Check configuration."
    fi
    
    # Test notification channels (dry run)
    print_status "INFO" "Testing notification channels (dry run)..."
    if docker exec process-matches-service python scripts/test_notifications.py --dry-run 2>/dev/null; then
        print_status "SUCCESS" "Notification channel test passed"
    else
        print_status "WARNING" "Notification channel test failed. Check configuration."
    fi
}

print_next_steps() {
    print_status "INFO" "Setup completed! Next steps:"
    echo
    echo "1. 📧 Configure Email Notifications:"
    echo "   - Edit .env file and set EMAIL_ENABLED=true"
    echo "   - Add your SMTP credentials (Gmail example in .env.template)"
    echo "   - For Gmail: Enable 2FA and generate App Password"
    echo
    echo "2. 👥 Configure Stakeholders:"
    echo "   - Edit data/process-matches-service/stakeholders.json"
    echo "   - Replace example email addresses with real ones"
    echo "   - Configure notification preferences"
    echo
    echo "3. 💬 Configure Discord (Optional):"
    echo "   - Create Discord webhook in your server"
    echo "   - Set DISCORD_ENABLED=true and DISCORD_WEBHOOK_URL in .env"
    echo
    echo "4. 🔧 Update Docker Compose:"
    echo "   - Add notification environment variables to docker-compose.yml"
    echo "   - Add notification config volume mount"
    echo "   - See NOTIFICATION_SYSTEM_INTEGRATION.md for details"
    echo
    echo "5. 🚀 Enable and Test:"
    echo "   - Set NOTIFICATION_SYSTEM_ENABLED=true in .env"
    echo "   - Restart services: docker-compose down && docker-compose up -d"
    echo "   - Test: docker exec process-matches-service python scripts/test_notifications.py --dry-run"
    echo
    echo "📚 Documentation:"
    echo "   - NOTIFICATION_SYSTEM_INTEGRATION.md - Integration guide"
    echo "   - match-list-processor/NOTIFICATION_QUICKSTART.md - Quick start guide"
    echo "   - match-list-processor/docs/NOTIFICATION_DEPLOYMENT_GUIDE.md - Full deployment guide"
}

main() {
    print_header
    
    cd "$DEPLOYMENT_ROOT"
    
    print_status "INFO" "Starting notification system setup for FOGIS deployment..."
    print_status "INFO" "Deployment directory: $(pwd)"
    
    # Run setup steps
    check_prerequisites
    create_notification_config
    update_docker_compose
    setup_environment
    test_notification_system
    
    echo
    print_status "SUCCESS" "Notification system setup completed!"
    
    print_next_steps
}

# Run main function
main "$@"
