#!/bin/bash

# Test script for restoration path detection logic

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Initialize TARGET_DIR as empty
TARGET_DIR=""

echo "=== Testing Restoration Path Detection ==="
echo "Current directory: $(pwd)"
echo "Initial TARGET_DIR: '$TARGET_DIR'"
echo

# Determine target directory if not set
if [[ -z "$TARGET_DIR" ]]; then
    echo "TARGET_DIR is empty, detecting path..."
    if [[ -f "manage_fogis_system.sh" && -f "setup_fogis_system.sh" ]]; then
        # Running from within fogis-deployment directory
        TARGET_DIR="."
        log_info "Detected execution from within fogis-deployment directory"
    elif [[ -d "fogis-deployment" && -f "fogis-deployment/manage_fogis_system.sh" ]]; then
        # Running from parent directory (web installer context)
        TARGET_DIR="fogis-deployment"
        log_info "Detected execution from parent directory"
    else
        log_error "Cannot determine FOGIS deployment directory structure"
        log_error "Please run this script from either:"
        log_error "  1. Within the fogis-deployment directory, or"
        log_error "  2. From the parent directory containing fogis-deployment/"
        exit 1
    fi
else
    echo "TARGET_DIR was already set to: '$TARGET_DIR'"
fi

echo
echo "Final TARGET_DIR: '$TARGET_DIR'"

# Validate target directory exists
if [ ! -d "$TARGET_DIR" ]; then
    log_error "Target directory not found: $TARGET_DIR"
    exit 1
else
    log_success "Target directory validated: $TARGET_DIR"
fi

echo
log_success "✅ Path detection test completed successfully!"
echo "Target directory: $TARGET_DIR"
