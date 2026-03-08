#!/bin/bash

# NanoClaw Role 2 Test Runner
# Runs unit and integration tests with coverage reporting

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
    print_msg "$BLUE" "  NanoClaw Role 2: Test Runner"
    print_msg "$BLUE" "═══════════════════════════════════════════════════════"
    echo ""
}

# Check Python virtual environment
check_venv() {
    print_msg "$YELLOW" "▶ Checking virtual environment..."

    if [[ "$VIRTUAL_ENV" == "" ]]; then
        print_msg "$YELLOW" "  ⚠ No virtual environment detected"
        print_msg "$YELLOW" "  Creating virtual environment..."

        python3 -m venv venv
        source venv/bin/activate

        print_msg "$GREEN" "  ✓ Virtual environment created and activated"
    else
        print_msg "$GREEN" "  ✓ Virtual environment active: $VIRTUAL_ENV"
    fi
}

# Install dependencies
install_deps() {
    print_msg "$YELLOW" "▶ Installing dependencies..."

    pip install --quiet -r executor/requirements.txt
    pip install --quiet -r monitor/requirements.txt
    pip install --quiet -r jira_integrator/requirements.txt
    pip install --quiet -r requirements-dev.txt

    print_msg "$GREEN" "  ✓ Dependencies installed"
}

# Run unit tests
run_unit_tests() {
    print_msg "$YELLOW" "▶ Running unit tests..."
    echo ""

    pytest -v -m "unit" --cov=executor --cov=monitor --cov=jira_integrator \
        --cov-report=term-missing --cov-report=html:htmlcov \
        || return 1

    echo ""
    print_msg "$GREEN" "  ✓ Unit tests passed"
}

# Run integration tests
run_integration_tests() {
    print_msg "$YELLOW" "▶ Running integration tests..."
    echo ""

    pytest -v -m "integration" \
        || return 1

    echo ""
    print_msg "$GREEN" "  ✓ Integration tests passed"
}

# Run all tests
run_all_tests() {
    print_msg "$YELLOW" "▶ Running all tests with coverage..."
    echo ""

    pytest -v \
        --cov=executor --cov=monitor --cov=jira_integrator \
        --cov-report=term-missing --cov-report=html:htmlcov \
        --cov-fail-under=80 \
        || return 1

    echo ""
    print_msg "$GREEN" "  ✓ All tests passed (coverage ≥ 80%)"
}

# Show coverage report
show_coverage() {
    print_msg "$YELLOW" "▶ Coverage report:"
    echo ""

    # Check if coverage report exists
    if [ -f htmlcov/index.html ]; then
        echo "Open htmlcov/index.html in your browser for detailed report"
        echo ""

        # Try to open in browser (macOS only)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open htmlcov/index.html 2>/dev/null || true
        fi
    fi
}

# Main test flow
main() {
    print_header

    # Parse arguments
    TEST_TYPE=${1:-all}

    case $TEST_TYPE in
        unit)
            check_venv
            install_deps
            run_unit_tests
            show_coverage
            ;;
        integration)
            check_venv
            install_deps
            run_integration_tests
            ;;
        all)
            check_venv
            install_deps
            run_all_tests
            show_coverage
            ;;
        *)
            echo "Usage: $0 [unit|integration|all]"
            echo ""
            echo "Options:"
            echo "  unit        - Run unit tests only"
            echo "  integration - Run integration tests only"
            echo "  all         - Run all tests (default)"
            exit 1
            ;;
    esac

    print_msg "$BLUE" ""
    print_msg "$BLUE" "═══════════════════════════════════════════════════════"
    print_msg "$BLUE" "  Tests Complete!"
    print_msg "$BLUE" "═══════════════════════════════════════════════════════"
    print_msg "$BLUE" ""
}

# Run main
main "$@"
