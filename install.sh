#!/bin/bash

# Installation script for Amazon Job Poller Server
echo "📦 Installing Amazon Job Poller Server Dependencies"
echo "================================================="

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "🐍 Python version: $python_version"

if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 7) else 1)'; then
    echo "✅ Python version is compatible"
else
    echo "❌ Python 3.7+ is required"
    exit 1
fi

# Install pip if not available
if ! command -v pip3 &> /dev/null; then
    echo "📦 Installing pip..."
    sudo apt-get update
    sudo apt-get install -y python3-pip
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Check if installation was successful
if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Update server_config.json with your credentials"
    echo "2. Run: ./start.sh"
    echo ""
    echo "For help: ./start.sh help"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi
