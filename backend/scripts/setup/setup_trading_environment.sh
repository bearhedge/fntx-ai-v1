#!/bin/bash
# FNTX.AI Trading Environment Setup Script
# Run this once to set up ThetaTerminal and all dependencies

set -e  # Exit on error

echo "======================================"
echo "FNTX.AI Trading Environment Setup"
echo "======================================"

# 1. Install Python dependencies
echo -e "\n1. Installing Python dependencies..."
cd backend
pip3 install -r requirements.txt
cd ..

# 2. Create directories for ThetaTerminal
echo -e "\n2. Setting up ThetaTerminal directories..."
mkdir -p ~/fntx-trading/{thetadata,logs,data}

# 3. Download ThetaTerminal if not exists
THETA_DIR=~/fntx-trading/thetadata
THETA_JAR=$THETA_DIR/ThetaTerminal.jar

if [ ! -f "$THETA_JAR" ]; then
    echo -e "\n3. Downloading ThetaTerminal..."
    cd $THETA_DIR
    # Download ThetaTerminal (you'll need to get the actual download link from thetadata.net)
    # wget https://thetadata.net/downloads/ThetaTerminal.jar -O ThetaTerminal.jar
    echo "Please download ThetaTerminal.jar from thetadata.net and place it in $THETA_DIR"
else
    echo -e "\n3. ThetaTerminal already exists at $THETA_JAR"
fi

# 4. Create systemd service for ThetaTerminal (optional - for auto-start)
echo -e "\n4. Creating systemd service files..."

# ThetaTerminal service
cat > ~/fntx-trading/thetadata/thetadata.service << 'EOF'
[Unit]
Description=ThetaData Terminal Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/fntx-trading/thetadata
ExecStart=/usr/bin/java -jar /home/$USER/fntx-trading/thetadata/ThetaTerminal.jar
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 5. Create start/stop scripts
echo -e "\n5. Creating management scripts..."

# Start script
cat > ~/fntx-trading/start_trading_services.sh << 'EOF'
#!/bin/bash
# Start all trading services

echo "Starting ThetaTerminal..."
cd ~/fntx-trading/thetadata
nohup java -jar ThetaTerminal.jar > ~/fntx-trading/logs/thetadata.log 2>&1 &
echo $! > ~/fntx-trading/thetadata/thetadata.pid

echo "Waiting for ThetaTerminal to start..."
sleep 10

echo "ThetaTerminal started. PID: $(cat ~/fntx-trading/thetadata/thetadata.pid)"
echo "Logs: ~/fntx-trading/logs/thetadata.log"

echo -e "\nIMPORTANT: Make sure to also start:"
echo "1. IB Gateway or TWS with API enabled on port 4001"
echo "2. The FNTX.AI backend services"
EOF

# Stop script
cat > ~/fntx-trading/stop_trading_services.sh << 'EOF'
#!/bin/bash
# Stop all trading services

if [ -f ~/fntx-trading/thetadata/thetadata.pid ]; then
    echo "Stopping ThetaTerminal..."
    kill $(cat ~/fntx-trading/thetadata/thetadata.pid)
    rm ~/fntx-trading/thetadata/thetadata.pid
else
    echo "ThetaTerminal not running"
fi
EOF

chmod +x ~/fntx-trading/start_trading_services.sh
chmod +x ~/fntx-trading/stop_trading_services.sh

# 6. Create configuration file
echo -e "\n6. Creating configuration file..."
cat > ~/fntx-trading/config.json << 'EOF'
{
    "thetadata": {
        "host": "localhost",
        "port": 11000,
        "auto_start": true
    },
    "ibkr": {
        "host": "localhost",
        "port": 4001,
        "client_id": 1
    },
    "services": {
        "thetadata_jar": "~/fntx-trading/thetadata/ThetaTerminal.jar",
        "log_dir": "~/fntx-trading/logs"
    }
}
EOF

echo -e "\n======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Download ThetaTerminal.jar from thetadata.net"
echo "2. Place it in: $THETA_DIR"
echo "3. Start services with: ~/fntx-trading/start_trading_services.sh"
echo "4. Stop services with: ~/fntx-trading/stop_trading_services.sh"
echo ""
echo "For automatic startup on boot:"
echo "sudo cp ~/fntx-trading/thetadata/thetadata.service /etc/systemd/system/"
echo "sudo systemctl enable thetadata.service"
echo "sudo systemctl start thetadata.service"