#!/bin/bash
# Setup script for Nanobanana

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up Nanobanana..."

# Check Python version
if ! command -v python3.12 &> /dev/null; then
    echo "Error: Python 3.12 is required but not found."
    echo "Install it with: brew install python@3.12"
    exit 1
fi

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3.12 -m venv .venv
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
