#!/bin/bash
# Setup monthly cron job for ALM report archiving

# Create the cron job that runs on the last day of each month at 11:55 PM
CRON_JOB="55 23 28-31 * * [ \$(date -d '+1 day' +\%d) -eq 01 ] && /usr/bin/python3 /home/info/fntx-ai-v1/backend/alm/monthly_archive.py >> /home/info/fntx-ai-v1/logs/monthly_alm_archive.log 2>&1"

# Check if cron job already exists
if ! crontab -l 2>/dev/null | grep -q "monthly_archive.py"; then
    # Add the cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Monthly ALM archive cron job added successfully!"
    echo "The job will run on the last day of each month at 11:55 PM"
else
    echo "Monthly ALM archive cron job already exists"
fi

# Create log directory if it doesn't exist
mkdir -p /home/info/fntx-ai-v1/logs

# Make the archive script executable
chmod +x /home/info/fntx-ai-v1/backend/alm/monthly_archive.py

echo "Setup complete!"
echo ""
echo "To test the monthly archive script manually, run:"
echo "python3 /home/info/fntx-ai-v1/backend/alm/monthly_archive.py"
echo ""
echo "To view the cron job, run:"
echo "crontab -l"