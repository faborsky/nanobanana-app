#!/bin/bash
# Setup script for Nanobanana

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up Nanobanana..."

# Find a suitable Python version (3.11+)
PYTHON=""
for py in python3.12 python3.11 python3.13 python3; do
    if command -v "$py" &> /dev/null; then
        version=$("$py" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$("$py" -c "import sys; print(sys.version_info.major)")
        minor=$("$py" -c "import sys; print(sys.version_info.minor)")
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON="$py"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Error: Python 3.11+ is required but not found."
    echo "Install it with: brew install python@3.12"
    exit 1
fi

echo "Using $PYTHON ($(${PYTHON} --version))"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv .venv
fi

# Activate and install
echo "Installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -e .

# Create .env from example if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "Created .env file. Please edit it and add your GEMINI_API_KEY."
fi

echo ""
echo "Setup complete!"
echo ""
echo "To activate the environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "Or use the run.sh script to run commands directly."
