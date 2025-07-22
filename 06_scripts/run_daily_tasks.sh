#!/bin/bash
# Run daily tasks manually for testing

echo "=================================="
echo "FNTX Daily Tasks - Manual Run"
echo "=================================="
echo "Time: $(date)"
echo ""

cd /home/info/fntx-ai-v1

# Run daily NAV import
echo "1. Running Daily NAV Import..."
echo "------------------------------"
python3 /home/info/fntx-ai-v1/01_backend/scripts/daily_flex_import.py
echo ""

# Run exercise detection
echo "2. Running Exercise Detection..."
echo "--------------------------------"
python3 /home/info/fntx-ai-v1/01_backend/scripts/exercise_detector.py
echo ""

echo "=================================="
echo "Daily tasks completed!"
echo "=================================="