#!/bin/bash
# FNTX Agent Launcher Script

echo "🚀 FNTX Agent - The Utopian Machine"
echo "===================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run the CLI
echo ""
echo "Starting FNTX Agent..."
python -m cli.main "$@"