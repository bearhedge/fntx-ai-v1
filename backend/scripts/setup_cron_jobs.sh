#!/bin/bash

# Setup Cron Jobs for FNTX AI Trading System
# This script sets up the automated tasks for exercise detection and daily imports

echo "Setting up cron jobs for FNTX AI Trading System..."

# Create a temporary cron file
CRON_FILE="/tmp/fntx_cron_jobs"

# Get existing cron jobs (if any)
crontab -l > "$CRON_FILE" 2>/dev/null || true

# Remove any existing FNTX-related cron jobs to avoid duplicates
grep -v "fntx-ai-v1" "$CRON_FILE" > "$CRON_FILE.tmp" || true
mv "$CRON_FILE.tmp" "$CRON_FILE"

# Add new cron jobs
echo "" >> "$CRON_FILE"
echo "# FNTX AI Trading System - Automated Tasks" >> "$CRON_FILE"
echo "" >> "$CRON_FILE"

# ALM Daily Update at 12:00 PM HKT  
echo "# ALM Daily Update - Runs at 12:00 PM HKT (04:00 UTC)" >> "$CRON_FILE"
echo "0 4 * * * cd /home/info/fntx-ai-v1/backend/alm && PYTHONPATH=/home/info/fntx-ai-v1 IBKR_FLEX_TOKEN=355054594472094189405478 /home/info/fntx-ai-v1/rl-trading/spy_options/rl_venv/bin/python3 /home/info/fntx-ai-v1/backend/alm/alm_automation.py >> /home/info/fntx-ai-v1/logs/alm_automation.log 2>&1" >> "$CRON_FILE"
echo "" >> "$CRON_FILE"

# Exercise Detection - Runs at 6:00 PM HKT (10:00 AM UTC) and 12:00 AM HKT (4:00 PM UTC)
echo "# Exercise Detection - First check at 6:00 PM HKT (10:00 AM UTC)" >> "$CRON_FILE"
echo "0 10 * * * cd /home/info/fntx-ai-v1/backend/scripts && PYTHONPATH=/home/info/fntx-ai-v1 IBKR_FLEX_TOKEN=355054594472094189405478 /home/info/fntx-ai-v1/rl-trading/spy_options/rl_venv/bin/python3 /home/info/fntx-ai-v1/backend/scripts/exercise_detector.py >> /home/info/fntx-ai-v1/logs/exercise_detection.log 2>&1" >> "$CRON_FILE"
echo "# Exercise Detection - Second check at 12:00 AM HKT (4:00 PM UTC)" >> "$CRON_FILE"
echo "0 16 * * * cd /home/info/fntx-ai-v1/backend/scripts && PYTHONPATH=/home/info/fntx-ai-v1 IBKR_FLEX_TOKEN=355054594472094189405478 /home/info/fntx-ai-v1/rl-trading/spy_options/rl_venv/bin/python3 /home/info/fntx-ai-v1/backend/scripts/exercise_detector.py >> /home/info/fntx-ai-v1/logs/exercise_detection.log 2>&1" >> "$CRON_FILE"
echo "" >> "$CRON_FILE"

# Optional: Historical data update at 3:00 AM HKT (less frequent)
echo "# Historical Data Update - Runs at 3:00 AM HKT on Sundays (7:00 PM UTC Saturday)" >> "$CRON_FILE"
echo "0 19 * * 6 cd /home/info/fntx-ai-v1 && /usr/bin/python3 /home/info/fntx-ai-v1/backend/scripts/historical_backfill.py >> /home/info/fntx-ai-v1/logs/historical_backfill.log 2>&1" >> "$CRON_FILE"
echo "" >> "$CRON_FILE"

# Install the cron file
crontab "$CRON_FILE"

# Clean up
rm -f "$CRON_FILE"

echo "✅ Cron jobs installed successfully!"
echo ""
echo "Scheduled tasks:"
echo "  - ALM Daily Update: 12:00 PM HKT (04:00 UTC)"
echo "  - Exercise Detection: 6:00 PM HKT (10:00 AM UTC) and 12:00 AM HKT (4:00 PM UTC)"
echo "  - Historical Backfill: 3:00 AM HKT Sundays (7:00 PM UTC Saturday)"
echo ""
echo "To view current cron jobs: crontab -l"
echo "To edit cron jobs: crontab -e"
echo "To remove all cron jobs: crontab -r"
echo ""
echo "Note: Hong Kong is UTC+8"
echo "  - 12:00 PM HKT = 04:00 UTC (ALM NAV updates)"
echo "  - 6:00 PM HKT = 10:00 AM UTC (first exercise check)"
echo "  - 12:00 AM HKT = 4:00 PM UTC (second exercise check)"