#!/bin/bash

# Show ALM Performance Data
# This script is called by run_terminal_ui.py to display ALM performance

# Set up environment
export PYTHONPATH="/home/info/fntx-ai-v1:$PYTHONPATH"

echo "════════════════════════════════════════════════════════════════════════════════"
echo "                        ALM PERFORMANCE REPORT                                  "
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# Run the calculation engine to generate the summary table and narratives
cd /home/info/fntx-ai-v1/01_backend/alm
python3 calculation_engine.py 2>&1

# Check if the command was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to generate ALM performance report"
    exit 1
fi