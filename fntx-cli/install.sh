#\!/bin/bash

echo "Installing FNTX CLI..."

# Check if Python 3 is installed
if \! command -v python3 &> /dev/null; then
    echo "Python 3 is required. Please install it first."
    exit 1
fi

# Install in user directory to avoid permission issues
pip3 install --user -e .

echo ""
echo "Installation complete\!"
echo "Try running: fntx test"
echo ""
echo "If 'fntx' command not found, add this to your ~/.bashrc or ~/.zshrc:"
echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
