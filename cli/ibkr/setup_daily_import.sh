#!/bin/bash
# Setup script for ALM Daily Import Service

echo "ALM Daily Import Service Setup"
echo "=============================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
SERVICE_DIR="/home/$ACTUAL_USER/fntx-ai-v1/fntx-cli/ibkr"

# Check if service files exist
if [ ! -f "$SERVICE_DIR/alm_daily_import.service" ] || [ ! -f "$SERVICE_DIR/alm_daily_import.timer" ]; then
    echo "Error: Service files not found in $SERVICE_DIR"
    exit 1
fi

# Create logs directory
LOG_DIR="/home/$ACTUAL_USER/fntx-ai-v1/08_logs"
mkdir -p "$LOG_DIR"
chown "$ACTUAL_USER:$ACTUAL_USER" "$LOG_DIR"

echo "1. Enter your database URL (postgresql://username:password@localhost/dbname):"
read -r DB_URL

echo "2. Enter your IBKR Flex Token:"
read -r -s FLEX_TOKEN
echo

# Update service file with actual values
SERVICE_FILE="/etc/systemd/system/alm_daily_import.service"
cp "$SERVICE_DIR/alm_daily_import.service" "$SERVICE_FILE"

# Replace placeholders
sed -i "s|User=info|User=$ACTUAL_USER|g" "$SERVICE_FILE"
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$SERVICE_DIR|g" "$SERVICE_FILE"
sed -i "s|DATABASE_URL=.*|DATABASE_URL=$DB_URL\"|g" "$SERVICE_FILE"
sed -i "s|IBKR_FLEX_TOKEN=.*|IBKR_FLEX_TOKEN=$FLEX_TOKEN\"|g" "$SERVICE_FILE"
sed -i "s|/home/info/|/home/$ACTUAL_USER/|g" "$SERVICE_FILE"

# Copy timer file
cp "$SERVICE_DIR/alm_daily_import.timer" /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

echo
echo "3. Do you want to enable the daily timer? (y/n)"
read -r ENABLE_TIMER

if [ "$ENABLE_TIMER" = "y" ]; then
    systemctl enable alm_daily_import.timer
    systemctl start alm_daily_import.timer
    echo "✓ Timer enabled and started"
    echo
    systemctl status alm_daily_import.timer --no-pager
else
    echo "Timer not enabled. You can enable it later with:"
    echo "  sudo systemctl enable --now alm_daily_import.timer"
fi

echo
echo "4. Do you want to run a test import now? (y/n)"
read -r RUN_TEST

if [ "$RUN_TEST" = "y" ]; then
    echo "Running test import..."
    sudo -u "$ACTUAL_USER" systemctl start alm_daily_import.service
    
    # Wait a moment
    sleep 2
    
    # Show status
    systemctl status alm_daily_import.service --no-pager
    
    # Show logs
    echo
    echo "Recent logs:"
    tail -20 "$LOG_DIR/alm_daily_import.log" 2>/dev/null || echo "No logs yet"
fi

echo
echo "Setup complete!"
echo
echo "Useful commands:"
echo "  View timer status:  systemctl status alm_daily_import.timer"
echo "  View service logs:  journalctl -u alm_daily_import.service -f"
echo "  Run manually:       sudo systemctl start alm_daily_import.service"
echo "  View import logs:   tail -f $LOG_DIR/alm_daily_import.log"