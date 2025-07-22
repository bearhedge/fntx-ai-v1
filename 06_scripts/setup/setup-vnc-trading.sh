#!/bin/bash
# One-time setup script for VNC Trading Desktop

set -e

echo "======================================"
echo "FNTX.AI VNC Trading Desktop Setup"
echo "======================================"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo "Please run this script as a normal user, not root"
   exit 1
fi

# Install required packages
echo "Installing VNC and desktop environment..."
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    tightvncserver \
    xfce4 \
    xfce4-goodies \
    dbus-x11 \
    firefox-esr \
    wget \
    curl

# Set up VNC password
echo "Setting up VNC password..."
mkdir -p ~/.vnc
echo "fntx2024" | vncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd

# Create VNC startup script
echo "Creating VNC startup script..."
cat > ~/.vnc/xstartup << 'EOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
export XKL_XMODMAP_DISABLE=1
export XDG_CURRENT_DESKTOP="XFCE"

xfce4-session &
EOF
chmod +x ~/.vnc/xstartup

# Download and install IB Gateway
echo "Downloading IB Gateway..."
cd ~
if [ ! -f "ibgateway-latest-standalone-linux-x64.sh" ]; then
    wget -q https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-standalone-linux-x64.sh
    chmod +x ibgateway-latest-standalone-linux-x64.sh
    echo -e "\n\n\n\n" | ./ibgateway-latest-standalone-linux-x64.sh -q
fi

# Create systemd service
echo "Setting up VNC as a system service..."
sudo tee /etc/systemd/system/vncserver@.service > /dev/null << 'EOF'
[Unit]
Description=VNC Server for IB Gateway on %i
After=network.target

[Service]
Type=forking
User=info
Group=info
WorkingDirectory=/home/info

# Clean any existing lock files
ExecStartPre=/bin/bash -c '/usr/bin/vncserver -kill %i > /dev/null 2>&1 || :'
ExecStart=/usr/bin/vncserver %i -geometry 1920x1080 -depth 24
ExecStop=/usr/bin/vncserver -kill %i

# Auto-restart if crashed
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable vncserver@:1.service
sudo systemctl start vncserver@:1.service

# Open firewall port (if using GCP)
if command -v gcloud &> /dev/null; then
    echo "Opening firewall port 5901..."
    gcloud compute firewall-rules create allow-vnc \
        --allow tcp:5901 \
        --source-ranges 0.0.0.0/0 \
        --description "Allow VNC access" 2>/dev/null || echo "Firewall rule already exists"
fi

echo ""
echo "======================================"
echo "VNC Trading Desktop Setup Complete!"
echo "======================================"
echo ""
echo "Connect using VNC viewer:"
echo "  Address: $(curl -s ifconfig.me 2>/dev/null || echo "YOUR_VM_IP"):5901"
echo "  Password: fntx2024"
echo ""
echo "VNC service status:"
sudo systemctl status vncserver@:1.service --no-pager | head -10
echo ""
echo "To restart VNC: sudo systemctl restart vncserver@:1"
echo "To view logs: sudo journalctl -u vncserver@:1 -f"