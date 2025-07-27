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

# Daily NAV Import at 7:00 AM HKT
echo "# Daily NAV Import - Runs at 7:00 AM HKT (11:00 PM UTC previous day)" >> "$CRON_FILE"
echo "0 23 * * * cd /home/info/fntx-ai-v1 && /usr/bin/python3 /home/info/fntx-ai-v1/01_backend/scripts/daily_flex_import.py >> /home/info/fntx-ai-v1/logs/daily_import.log 2>&1" >> "$CRON_FILE"
echo "" >> "$CRON_FILE"

# Exercise Detection at 7:00 AM HKT
echo "# Exercise Detection - Runs at 7:00 AM HKT (11:00 PM UTC previous day)" >> "$CRON_FILE"
echo "0 23 * * * cd /home/info/fntx-ai-v1 && /usr/bin/python3 /home/info/fntx-ai-v1/01_backend/scripts/exercise_detector.py >> /home/info/fntx-ai-v1/logs/exercise_detection.log 2>&1" >> "$CRON_FILE"
echo "" >> "$CRON_FILE"

# Optional: Historical data update at 3:00 AM HKT (less frequent)
echo "# Historical Data Update - Runs at 3:00 AM HKT on Sundays (7:00 PM UTC Saturday)" >> "$CRON_FILE"
echo "0 19 * * 6 cd /home/info/fntx-ai-v1 && /usr/bin/python3 /home/info/fntx-ai-v1/01_backend/scripts/historical_backfill.py >> /home/info/fntx-ai-v1/logs/historical_backfill.log 2>&1" >> "$CRON_FILE"
echo "" >> "$CRON_FILE"

# Install the cron file
crontab "$CRON_FILE"

# Clean up
rm -f "$CRON_FILE"

echo "✅ Cron jobs installed successfully!"
echo ""
echo "Scheduled tasks:"
echo "  - Daily NAV Import: 7:00 AM HKT (11:00 PM UTC)"
echo "  - Exercise Detection: 7:00 AM HKT (11:00 PM UTC)"
echo "  - Historical Backfill: 3:00 AM HKT Sundays (7:00 PM UTC Saturday)"
echo ""
echo "To view current cron jobs: crontab -l"
echo "To edit cron jobs: crontab -e"
echo "To remove all cron jobs: crontab -r"
echo ""
echo "Note: Hong Kong is UTC+8, so 7:00 AM HKT = 11:00 PM UTC (previous day)"