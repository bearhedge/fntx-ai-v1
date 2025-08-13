#!/bin/bash

# Script to run ThetaTerminal download in background with nohup

cd /home/info/fntx-ai-v1/backend/data/theta_download

echo "Starting 1-minute data download for SPY and QQQ with IV data..."
echo "Log file: /home/info/fntx-ai-v1/backend/data/theta_download/download_improved.log"
echo ""

# Check if we want test or full download
if [ "$1" == "--full" ]; then
    echo "Running FULL historical download (Dec 2022 - present)"
    echo "This will take several hours..."
    nohup /home/info/fntx-ai-v1/config/venv/bin/python3 download_1min_data_improved.py --full > nohup.out 2>&1 &
else
    echo "Running TEST download (1 week each - Dec 5-9 2022 for SPY, Jan 9-13 2023 for QQQ)"
    echo "This should take 5-10 minutes..."
    nohup /home/info/fntx-ai-v1/config/venv/bin/python3 download_1min_data_improved.py > nohup.out 2>&1 &
fi

# Get the PID
PID=$!
echo "Download process started with PID: $PID"
echo ""
echo "To monitor progress:"
echo "  tail -f download_improved.log"
echo ""
echo "To check if still running:"
echo "  ps -p $PID"
echo ""
echo "To stop the download:"
echo "  kill $PID"