#!/bin/bash

# FOGIS System Status Display
echo "🎯 FOGIS SYSTEM STATUS OVERVIEW"
echo "=================================="
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running"
    echo "Please start Docker Desktop first"
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check service status
echo "📊 SERVICE STATUS:"
echo "==================="

if docker-compose -f docker-compose.yml ps >/dev/null 2>&1; then
    docker-compose -f docker-compose.yml ps
else
    echo "⚠️  Services not started yet"
    echo "Run: ./manage_fogis_system.sh start"
fi

echo ""

# Check cron status
echo "⏰ AUTOMATED SCHEDULING:"
echo "========================"

if crontab -l 2>/dev/null | grep -q "match-list-processor"; then
    echo "✅ Hourly cron job is active"
    echo "Next run: At the top of the next hour"
else
    echo "⚠️  No automatic scheduling set up"
    echo "To add: ./manage_fogis_system.sh cron-add"
fi

echo ""

# Show available commands
echo "🔧 AVAILABLE COMMANDS:"
echo "====================="
echo ""
echo "System Management:"
echo "  ./manage_fogis_system.sh start     - Start all services"
echo "  ./manage_fogis_system.sh stop      - Stop all services"
echo "  ./manage_fogis_system.sh status    - Show detailed status"
echo "  ./manage_fogis_system.sh test      - Test the system"
echo ""
echo "Automation:"
echo "  ./manage_fogis_system.sh cron-add    - Add hourly automation"
echo "  ./manage_fogis_system.sh cron-remove - Remove automation"
echo "  ./manage_fogis_system.sh cron-status - Check automation"
echo ""

echo "🎉 Your FOGIS system is ready to use!"
echo ""
