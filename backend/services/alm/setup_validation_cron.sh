#!/bin/bash
# Setup cron job to validate synthetic events after IBKR data downloads

# Add validation to run 5 minutes after each IBKR download (6:05 PM, 12:05 AM HKT)
VALIDATION_CRON="5 18,0 * * * /usr/bin/python3 /home/info/fntx-ai-v1/backend/alm/validate_synthetic_events.py >> /home/info/fntx-ai-v1/logs/synthetic_validation.log 2>&1"

# Check if validation cron job already exists
if ! crontab -l 2>/dev/null | grep -q "validate_synthetic_events.py"; then
    # Add the cron job
    (crontab -l 2>/dev/null; echo "$VALIDATION_CRON") | crontab -
    echo "Synthetic event validation cron job added successfully!"
    echo "The job will run at 6:05 PM and 12:05 AM HKT (after IBKR downloads)"
else
    echo "Validation cron job already exists"
fi

# Make the validation script executable
chmod +x /home/info/fntx-ai-v1/backend/alm/validate_synthetic_events.py

echo "Setup complete!"