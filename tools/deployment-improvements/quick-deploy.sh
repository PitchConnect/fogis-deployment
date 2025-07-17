#!/bin/bash
set -e

# FOGIS Quick Deploy Script
# This script provides one-command deployment of the FOGIS system
# eliminating all manual troubleshooting steps we encountered.

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/PitchConnect/fogis-deployment.git"
INSTALL_DIR="$HOME/fogis-deployment"
LOG_FILE="$INSTALL_DIR/deployment.log"

# Functions
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        success "$1 is installed"
        return 0
    else
        error "$1 is not installed"
        return 1
    fi
}

install_docker_macos() {
    log "Installing Docker Desktop for macOS..."

    # Check if Homebrew is available
    if command -v brew >/dev/null 2>&1; then
        log "Installing Docker via Homebrew..."
        brew install --cask docker
        success "Docker Desktop installed via Homebrew"
        warning "Please start Docker Desktop from Applications folder"
        warning "Press Enter when Docker Desktop is running..."
        read -r
    else
        warning "Homebrew not found. Please install Docker Desktop manually:"
        warning "1. Visit: https://docs.docker.com/desktop/install/mac-install/"
        warning "2. Download and install Docker Desktop"
        warning "3. Start Docker Desktop"
        warning "4. Press Enter when ready..."
        read -r
    fi
}

install_docker_linux() {
    log "Installing Docker for Linux..."

    # Detect Linux distribution
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
    fi

    case "$OS" in
        "Ubuntu"*)
            log "Installing Docker on Ubuntu..."
            sudo apt-get update
            sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            sudo apt-get update
            sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            sudo systemctl start docker
            sudo systemctl enable docker
            sudo usermod -aG docker "$USER"
            ;;
        "CentOS"*|"Red Hat"*)
            log "Installing Docker on CentOS/RHEL..."
            sudo yum install -y yum-utils
            sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
            sudo systemctl start docker
            sudo systemctl enable docker
            sudo usermod -aG docker "$USER"
            ;;
        *)
            warning "Unsupported Linux distribution: $OS"
            warning "Please install Docker manually: https://docs.docker.com/engine/install/"
            ;;
    esac

    success "Docker installed. You may need to log out and back in for group changes to take effect."
}

check_prerequisites() {
    log "Checking prerequisites..."

    local missing_deps=()

    # Check Python
    if ! check_command python3; then
        missing_deps+=("python3")
    fi

    # Check Git
    if ! check_command git; then
        missing_deps+=("git")
    fi

    # Check Docker
    if ! check_command docker; then
        missing_deps+=("docker")
    else
        # Check if Docker daemon is running
        if ! docker ps >/dev/null 2>&1; then
            error "Docker is installed but not running"
            missing_deps+=("docker-running")
        fi
    fi

    # Check Docker Compose
    if ! docker compose version >/dev/null 2>&1 && ! docker-compose --version >/dev/null 2>&1; then
        missing_deps+=("docker-compose")
    fi

    if [ ${#missing_deps[@]} -eq 0 ]; then
        success "All prerequisites are satisfied"
        return 0
    else
        warning "Missing dependencies: ${missing_deps[*]}"
        return 1
    fi
}

install_prerequisites() {
    log "Installing missing prerequisites..."

    # Detect OS
    case "$OSTYPE" in
        darwin*)
            log "Detected macOS"

            # Install Homebrew if not present
            if ! command -v brew >/dev/null 2>&1; then
                log "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi

            # Install missing packages
            if ! check_command python3; then
                brew install python3
            fi

            if ! check_command git; then
                brew install git
            fi

            if ! check_command docker; then
                install_docker_macos
            fi
            ;;

        linux*)
            log "Detected Linux"

            # Update package manager
            if command -v apt-get >/dev/null 2>&1; then
                sudo apt-get update
                if ! check_command python3; then
                    sudo apt-get install -y python3 python3-pip
                fi
                if ! check_command git; then
                    sudo apt-get install -y git
                fi
            elif command -v yum >/dev/null 2>&1; then
                if ! check_command python3; then
                    sudo yum install -y python3 python3-pip
                fi
                if ! check_command git; then
                    sudo yum install -y git
                fi
            fi

            if ! check_command docker; then
                install_docker_linux
            fi
            ;;

        *)
            error "Unsupported operating system: $OSTYPE"
            exit 1
            ;;
    esac
}

clone_repository() {
    log "Cloning FOGIS deployment repository..."

    if [ -d "$INSTALL_DIR" ]; then
        log "Directory $INSTALL_DIR already exists. Updating..."
        cd "$INSTALL_DIR"
        git pull
    else
        log "Cloning repository to $INSTALL_DIR..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi

    success "Repository ready at $INSTALL_DIR"
}

setup_environment() {
    log "Setting up environment..."

    # Create log file
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"

    # Make scripts executable
    chmod +x deployment-improvements/*.py
    chmod +x deployment-improvements/*.sh

    success "Environment setup complete"
}

run_deployment() {
    log "Running FOGIS deployment..."

    cd "$INSTALL_DIR"

    # Run the master deployment script
    if python3 deployment-improvements/deploy_fogis.py; then
        success "FOGIS deployment completed successfully!"

        echo ""
        echo "🎉 FOGIS is now running!"
        echo ""
        echo "📋 Quick Status Check:"
        echo "  curl http://localhost:9080/health"
        echo ""
        echo "📊 Monitoring:"
        echo "  python3 deployment-improvements/validation_system.py --monitor 10"
        echo ""
        echo "📖 Full Documentation:"
        echo "  cat deployment-improvements/README_IMPROVED.md"
        echo ""
        echo "🔧 Management:"
        echo "  docker-compose -f docker-compose.yml ps"
        echo "  docker-compose -f docker-compose.yml logs -f"
        echo ""

        return 0
    else
        error "FOGIS deployment failed"

        echo ""
        echo "🔍 Troubleshooting:"
        echo "  1. Check logs: cat $LOG_FILE"
        echo "  2. Run diagnostics: python3 deployment-improvements/validation_system.py"
        echo "  3. Check setup: python3 deployment-improvements/setup_wizard.py"
        echo "  4. View service logs: docker-compose -f docker-compose.yml logs"
        echo ""

        return 1
    fi
}

main() {
    echo ""
    echo "🚀 FOGIS Quick Deploy Script"
    echo "============================"
    echo ""
    echo "This script will automatically:"
    echo "  ✅ Check and install prerequisites"
    echo "  ✅ Clone the FOGIS deployment repository"
    echo "  ✅ Run the complete deployment process"
    echo "  ✅ Validate the deployment"
    echo ""

    # Ask for confirmation
    read -p "Continue with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Deployment cancelled by user"
        exit 0
    fi

    log "Starting FOGIS quick deployment..."

    # Check prerequisites
    if ! check_prerequisites; then
        log "Installing missing prerequisites..."
        install_prerequisites

        # Re-check after installation
        if ! check_prerequisites; then
            error "Failed to install all prerequisites"
            exit 1
        fi
    fi

    # Clone repository
    clone_repository

    # Setup environment
    setup_environment

    # Run deployment
    if run_deployment; then
        success "FOGIS deployment completed successfully!"
        echo ""
        echo "📍 Installation location: $INSTALL_DIR"
        echo "📄 Deployment log: $LOG_FILE"
        echo ""
        exit 0
    else
        error "FOGIS deployment failed"
        echo ""
        echo "📄 Check deployment log: $LOG_FILE"
        echo "📞 For support, see: $INSTALL_DIR/deployment-improvements/README_IMPROVED.md"
        echo ""
        exit 1
    fi
}

# Handle script interruption
trap 'echo ""; error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"
