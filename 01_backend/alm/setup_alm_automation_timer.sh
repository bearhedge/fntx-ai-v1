#!/bin/bash
# Setup ALM Automation Timer
# This script installs and enables the systemd timer for daily ALM automation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Setting up ALM Automation Timer..."

# Copy service and timer files to systemd directory
echo "Copying systemd files..."
sudo cp "$SCRIPT_DIR/alm-automation.service" /etc/systemd/system/
sudo cp "$SCRIPT_DIR/alm-automation.timer" /etc/systemd/system/

# Set proper permissions
sudo chmod 644 /etc/systemd/system/alm-automation.service
sudo chmod 644 /etc/systemd/system/alm-automation.timer

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable and start the timer
echo "Enabling and starting ALM automation timer..."
sudo systemctl enable alm-automation.timer
sudo systemctl start alm-automation.timer

# Check status
echo ""
echo "Timer status:"
sudo systemctl status alm-automation.timer --no-pager

echo ""
echo "Next scheduled run:"
sudo systemctl list-timers alm-automation.timer --no-pager

echo ""
echo "ALM Automation Timer setup complete!"
echo ""
echo "The timer will run at 12:00 PM Hong Kong time (04:00 UTC) every Tuesday through Saturday."
echo ""
echo "Useful commands:"
echo "  - Check timer status: sudo systemctl status alm-automation.timer"
echo "  - Check service logs: sudo journalctl -u alm-automation.service"
echo "  - Run manually: sudo systemctl start alm-automation.service"
echo "  - Stop timer: sudo systemctl stop alm-automation.timer"
echo "  - Disable timer: sudo systemctl disable alm-automation.timer"