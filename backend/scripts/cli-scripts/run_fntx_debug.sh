#!/bin/bash
# Debug script to run fntx with environment checks

echo "=== FNTX Debug Information ==="
echo "Terminal: $TERM"
echo "Colors: $(tput colors)"
echo "Python: $(which python3)"
echo ""

echo "Setting environment..."
export TEXTUAL_DEBUG=1
export PYTHONPATH="/home/info/fntx-ai-v1/cli:$PYTHONPATH"

echo "Running FNTX..."
cd /home/info/fntx-ai-v1/cli
python3 -m cli.main