#!/bin/bash

# FOGIS One-Line Web Installer
# Usage: curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/PitchConnect/fogis-deployment.git"
INSTALL_DIR="$HOME/fogis-deployment"
BRANCH="main"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_progress() {
    echo -e "${PURPLE}🔄 $1${NC}"
}

log_header() {
    echo -e "${CYAN}$1${NC}"
}

# Show header
show_header() {
    echo ""
    log_header "🚀 FOGIS ONE-LINE INSTALLER"
    log_header "============================"
    echo ""
    echo "This installer will:"
    echo "  ✅ Download the FOGIS deployment system"
    echo "  ✅ Install prerequisites automatically"
    echo "  ✅ Set up the complete FOGIS environment"
    echo "  ✅ Configure all services and automation"
    echo ""
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        echo "Please run as a regular user with sudo privileges"
        exit 1
    fi
}

# Detect platform
detect_platform() {
    local os_type=$(uname -s)
    local arch=$(uname -m)
    
    log_info "Detecting platform..."
    
    case $os_type in
        "Darwin")
            echo "macOS detected ($arch)"
            ;;
        "Linux")
            if [[ -f /etc/os-release ]]; then
                local distro=$(grep '^NAME=' /etc/os-release | cut -d'"' -f2)
                echo "Linux detected: $distro ($arch)"
            else
                echo "Linux detected ($arch)"
            fi
            ;;
        *)
            log_warning "Unknown platform: $os_type"
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local missing=()
    
    # Check Git
    if ! command -v git &> /dev/null; then
        missing+=("git")
    fi
    
    # Check Python3
    if ! command -v python3 &> /dev/null; then
        missing+=("python3")
    fi
    
    # Check curl
    if ! command -v curl &> /dev/null; then
        missing+=("curl")
    fi
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_warning "Missing prerequisites: ${missing[*]}"
        
        # Try to install missing prerequisites
        if command -v apt &> /dev/null; then
            log_info "Installing prerequisites with apt..."
            sudo apt update
            for pkg in "${missing[@]}"; do
                sudo apt install -y "$pkg"
            done
        elif command -v yum &> /dev/null; then
            log_info "Installing prerequisites with yum..."
            for pkg in "${missing[@]}"; do
                sudo yum install -y "$pkg"
            done
        elif command -v brew &> /dev/null; then
            log_info "Installing prerequisites with brew..."
            for pkg in "${missing[@]}"; do
                brew install "$pkg"
            done
        else
            log_error "Cannot install prerequisites automatically"
            echo "Please install: ${missing[*]}"
            exit 1
        fi
    fi
    
    log_success "Prerequisites satisfied"
}

# Download FOGIS deployment
download_fogis() {
    log_info "Downloading FOGIS deployment system..."
    
    # Remove existing directory if it exists
    if [[ -d "$INSTALL_DIR" ]]; then
        log_warning "Existing installation found at $INSTALL_DIR"
        read -p "Remove existing installation? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
        else
            log_error "Installation cancelled"
            exit 1
        fi
    fi
    
    # Clone the repository
    log_progress "Cloning repository..."
    if git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"; then
        log_success "Repository cloned successfully"
    else
        log_error "Failed to clone repository"
        exit 1
    fi
}

# Run the setup
run_setup() {
    log_info "Starting FOGIS setup..."
    
    cd "$INSTALL_DIR"
    
    # Make scripts executable
    chmod +x *.sh
    chmod +x fogis-deployment/*.sh
    
    # Run the enhanced setup script
    log_progress "Running one-click setup..."
    echo ""
    
    if ./fogis-deployment/setup_fogis_system.sh --auto; then
        log_success "FOGIS setup completed successfully!"
    else
        log_error "Setup failed"
        echo ""
        echo "📋 Manual setup options:"
        echo "  cd $INSTALL_DIR"
        echo "  ./fogis-deployment/setup_fogis_system.sh --resume"
        echo ""
        exit 1
    fi
}

# Show completion message
show_completion() {
    echo ""
    log_header "🎉 INSTALLATION COMPLETE!"
    log_header "========================="
    echo ""
    log_success "FOGIS has been installed successfully!"
    echo ""
    echo "📁 Installation directory: $INSTALL_DIR"
    echo ""
    echo "🔧 Quick commands:"
    echo "  cd $INSTALL_DIR"
    echo "  ./fogis-deployment/manage_fogis_system.sh status"
    echo "  ./fogis-deployment/manage_fogis_system.sh setup-auth"
    echo "  ./fogis-deployment/show_system_status.sh"
    echo ""
    echo "📖 Documentation:"
    echo "  • README: $INSTALL_DIR/fogis-deployment/README.md"
    echo "  • Prerequisites: $INSTALL_DIR/fogis-deployment/DEPLOYMENT_PREREQUISITES.md"
    echo ""
    echo "🌐 Service URLs (once running):"
    echo "  • FOGIS API: http://localhost:9086/health"
    echo "  • Team Logos: http://localhost:9088/health"
    echo "  • Google Drive: http://localhost:9085/health"
    echo "  • Calendar Sync: http://localhost:9084/health"
    echo ""
    log_success "🚀 FOGIS is ready to use!"
}

# Main execution
main() {
    show_header
    check_root
    detect_platform
    check_prerequisites
    download_fogis
    run_setup
    show_completion
}

# Handle interruption
trap 'echo ""; log_warning "Installation interrupted"; exit 1' INT TERM

# Run main function
main "$@"
