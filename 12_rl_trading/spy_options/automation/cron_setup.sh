#!/bin/bash
# Setup cron job for weekly retraining

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create cron entry
CRON_CMD="0 2 * * 0 cd $SCRIPT_DIR && $SCRIPT_DIR/../venv/bin/python3 $SCRIPT_DIR/scheduled_retraining.py >> $SCRIPT_DIR/../logs/evolution/cron.log 2>&1"

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "scheduled_retraining.py"; then
    echo "Cron job already exists"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "Cron job added successfully"
fi

# Show current crontab
echo "Current crontab:"
crontab -l | grep scheduled_retraining