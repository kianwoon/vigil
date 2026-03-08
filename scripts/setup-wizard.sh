#!/bin/bash
# NanoClaw Executor Setup Script
# Runs the interactive configuration wizard

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Starting NanoClaw Executor Setup Wizard..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check if CLI dependencies are installed
if ! python3 -c "import questionary" 2>/dev/null; then
    echo "CLI dependencies not found. Installing..."
    pip3 install -r "$PROJECT_ROOT/requirements-cli.txt"
fi

# Run the setup wizard
cd "$PROJECT_ROOT"
python3 -m cli.setup "$@"
