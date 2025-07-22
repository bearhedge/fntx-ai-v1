#!/bin/bash
# Install ClaudePoint for checkpoint management
# https://github.com/andycufari/ClaudePoint

set -e

echo "Installing ClaudePoint..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

# Install ClaudePoint in virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install claudepoint
else
    echo "Error: Virtual environment not found. Please activate venv first."
    exit 1
fi

# Create checkpoints directory
mkdir -p data/checkpoints

# Create ClaudePoint configuration
cat > .claudepoint.yml << EOF
# ClaudePoint Configuration
checkpoint_dir: data/checkpoints
db_path: data/checkpoints/claude.db

# Patterns to include in checkpoints
include:
  - "*.py"
  - "*.js"
  - "*.tsx"
  - "*.json"
  - "*.md"
  - "*.sh"
  - "*.conf"
  - "*.sql"

# Patterns to exclude
exclude:
  - "venv/"
  - "node_modules/"
  - "*.pyc"
  - "__pycache__/"
  - "*.log"
  - "dist/"
  - ".git/"
  - "*.db"
  - "*.jar"

# Checkpoint settings
auto_checkpoint: false
max_checkpoints: 50
compression: true
EOF

echo "✅ ClaudePoint installed successfully!"
echo ""
echo "Usage:"
echo "  claudepoint save 'Description of changes'"
echo "  claudepoint list"
echo "  claudepoint restore <checkpoint-id>"
echo ""
echo "Checkpoints will be stored in: data/checkpoints/"