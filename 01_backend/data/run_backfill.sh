#!/bin/bash
# Run the final minutes backfill in background with nohup

echo "Starting 3:59 PM backfill process..."
echo "This will add a single 3:59 PM 1-minute bar for all existing contracts"
echo "Process will run in background. Check logs at: /home/info/fntx-ai-v1/08_logs/backfill_final_minutes.log"
echo ""

# Change to the data directory
cd /home/info/fntx-ai-v1/01_backend/data

# Run with nohup
nohup python3 backfill_final_minutes.py > /home/info/fntx-ai-v1/08_logs/backfill_final_minutes_console.log 2>&1 &

# Get the PID
PID=$!
echo "Backfill process started with PID: $PID"
echo ""
echo "To monitor progress:"
echo "  tail -f /home/info/fntx-ai-v1/08_logs/backfill_final_minutes.log"
echo ""
echo "To check if still running:"
echo "  ps -p $PID"
echo ""
echo "To stop the process:"
echo "  kill $PID"