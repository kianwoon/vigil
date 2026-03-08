#!/bin/bash

# NanoClaw Role 2 Setup Script
# Intelligent Test Executor with Browser Health Monitoring

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_msg() {
    local color=$1
    local msg=$2
    echo -e "${color}${msg}${NC}"
}

# Print header
print_header() {
    echo ""
    print_msg "$BLUE" "═══════════════════════════════════════════════════════"
    print_msg "$BLUE" "  NanoClaw Role 2: Intelligent Test Executor Setup"
    print_msg "$BLUE" "═══════════════════════════════════════════════════════"
    echo ""
}

# Check command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python() {
    print_msg "$YELLOW" "▶ Checking Python version..."

    if ! command_exists python3; then
        print_msg "$RED" "✗ Python 3 is not installed"
        print_msg "$YELLOW" "  Please install Python 3.11+ from https://www.python.org/"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
        print_msg "$RED" "✗ Python 3.11+ is required (found $PYTHON_VERSION)"
        exit 1
    fi

    print_msg "$GREEN" "✓ Python $PYTHON_VERSION detected"
}

# Check Docker
check_docker() {
    print_msg "$YELLOW" "▶ Checking Docker installation..."

    if ! command_exists docker; then
        print_msg "$RED" "✗ Docker is not installed"
        print_msg "$YELLOW" "  Please install Docker from https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker info >/dev/null 2>&1; then
        print_msg "$RED" "✗ Docker is not running"
        print_msg "$YELLOW" "  Please start Docker Desktop"
        exit 1
    fi

    print_msg "$GREEN" "✓ Docker is running"
}

# Check Docker Compose
check_docker_compose() {
    print_msg "$YELLOW" "▶ Checking Docker Compose..."

    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        print_msg "$RED" "✗ Docker Compose is not installed"
        print_msg "$YELLOW" "  Please install Docker Compose from https://docs.docker.com/compose/install/"
        exit 1
    fi

    print_msg "$GREEN" "✓ Docker Compose is available"
}

# Setup environment file
setup_env() {
    print_msg "$YELLOW" "▶ Setting up environment configuration..."

    if [ -f .env ]; then
        print_msg "$YELLOW" "  ⚠ .env file already exists"
        read -p "  Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_msg "$GREEN" "  Keeping existing .env file"
            return
        fi
    fi

    cp .env.example .env

    print_msg "$YELLOW" ""
    print_msg "$YELLOW" "  Please configure your environment variables in .env:"
    print_msg "$YELLOW" ""
    print_msg "$YELLOW" "  Required:"
    print_msg "$YELLOW" "  - JIRA_BASE_URL (your Jira instance URL)"
    print_msg "$YELLOW" "  - JIRA_EMAIL (your Jira email)"
    print_msg "$YELLOW" "  - JIRA_API_TOKEN (your Jira API token)"
    print_msg "$YELLOW" ""
    print_msg "$YELLOW" "  Optional:"
    print_msg "$YELLOW" "  - SHARED_VOLUME_PATH (path to Role 1's shared volume)"
    print_msg "$YELLOW" "  - WHATSAPP_WEBHOOK_URL (for WhatsApp triggers)"
    print_msg "$YELLOW" ""

    read -p "  Press Enter to continue after configuring .env..."

    print_msg "$GREEN" "✓ Environment file created"
}

# Create necessary directories
create_directories() {
    print_msg "$YELLOW" "▶ Creating directories..."

    mkdir -p shared/scripts
    mkdir -p shared/results
    mkdir -p shared/traces
    mkdir -p shared/metrics

    # Create .gitkeep files
    touch shared/scripts/.gitkeep
    touch shared/results/.gitkeep
    touch shared/traces/.gitkeep
    touch shared/metrics/.gitkeep

    print_msg "$GREEN" "✓ Directories created"
}

# Pull Docker images
pull_images() {
    print_msg "$YELLOW" "▶ Pulling Docker images (this may take a few minutes)..."

    cd docker

    if command_exists docker-compose; then
        docker-compose pull
    else
        docker compose pull
    fi

    cd ..

    print_msg "$GREEN" "✓ Docker images pulled"
}

# Build Docker images
build_images() {
    print_msg "$YELLOW" "▶ Building Docker images..."

    cd docker

    if command_exists docker-compose; then
        docker-compose build
    else
        docker compose build
    fi

    cd ..

    print_msg "$GREEN" "✓ Docker images built"
}

# Start services
start_services() {
    print_msg "$YELLOW" "▶ Starting NanoClaw services..."

    cd docker

    if command_exists docker-compose; then
        docker-compose up -d
    else
        docker compose up -d
    fi

    cd ..

    print_msg "$GREEN" "✓ Services started"
}

# Show service status
show_status() {
    print_msg "$YELLOW" "▶ Service status:"
    echo ""

    cd docker

    if command_exists docker-compose; then
        docker-compose ps
    else
        docker compose ps
    fi

    cd ""

    echo ""
}

# Show next steps
show_next_steps() {
    print_msg "$BLUE" ""
    print_msg "$BLUE" "═══════════════════════════════════════════════════════"
    print_msg "$BLUE" "  Setup Complete!"
    print_msg "$BLUE" "═══════════════════════════════════════════════════════"
    print_msg "$BLUE" ""
    print_msg "$GREEN" "Services running:"
    print_msg "$GREEN" "  • Executor API:    http://localhost:8001"
    print_msg "$GREEN" "  • Monitor API:     http://localhost:8002"
    print_msg "$GREEN" "  • Jira Integrator: http://localhost:8003"
    print_msg "$BLUE" ""
    print_msg "$YELLOW" "Quick start:"
    print_msg "$YELLOW" "  1. Place test scripts in shared/scripts/"
    print_msg "$YELLOW" "  2. Execute tests via API:"
    print_msg "$YELLOW" "     curl -X POST http://localhost:8001/api/v1/execute \\"
    print_msg "$YELLOW" "       -H 'Content-Type: application/json' \\"
    print_msg "$YELLOW" "       -d '{\"job_id\": \"test-1\", \"jira_ticket\": \"QA-123\", \"script_path\": \"test_example.py\"}'"
    print_msg "$BLUE" ""
    print_msg "$YELLOW" "Useful commands:"
    print_msg "$YELLOW" "  • View logs: cd docker && docker-compose logs -f [service]"
    print_msg "$YELLOW" "  • Stop services: cd docker && docker-compose down"
    print_msg "$YELLOW" "  • Restart service: cd docker && docker-compose restart [service]"
    print_msg "$BLUE" ""
    print_msg "$YELLOW" "Documentation:"
    print_msg "$YELLOW" "  • README.md for detailed usage"
    print_msg "$YELLOW" "  • docs/ for architecture and API docs"
    print_msg "$BLUE" ""
}

# Main setup flow
main() {
    print_header

    # Check prerequisites
    check_python
    check_docker
    check_docker_compose

    # Setup
    create_directories
    setup_env

    # Docker setup
    pull_images
    build_images
    start_services

    # Show status
    sleep 2  # Give services time to start
    show_status

    # Next steps
    show_next_steps
}

# Run main
main
