#!/bin/bash
#
# Setup script for ALM daily automation
# This script installs systemd services for automatic daily ALM updates

echo "Setting up ALM daily automation..."

# Copy service files to systemd directory
sudo cp /home/info/fntx-ai-v1/01_backend/services/alm-daily-update.service /etc/systemd/system/
sudo cp /home/info/fntx-ai-v1/01_backend/services/alm-daily-update.timer /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable and start the timer
sudo systemctl enable alm-daily-update.timer
sudo systemctl start alm-daily-update.timer

# Show status
echo "Checking timer status..."
sudo systemctl status alm-daily-update.timer

echo "
ALM automation setup complete!

The system will now automatically:
- Update ALM data daily at 5:00 PM EDT (after market close)
- Process only LBD (Last Business Day) files
- Update the database with new events and summaries

To check the timer schedule:
  sudo systemctl list-timers alm-daily-update.timer

To manually run the update:
  sudo systemctl start alm-daily-update.service

To view logs:
  sudo journalctl -u alm-daily-update.service
"