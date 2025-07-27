# FNTX VM Setup and Restoration Guide

## Quick GCP VM Setup

### 1. Create New VM Instance

**Console Steps:**
```
Google Cloud Console → Compute Engine → VM Instances → Create Instance

Name: fntx-ai-vm-v2
Region: us-central1-a (cheapest)
Zone: us-central1-a
Machine type: e2-medium (2 vCPU, 4 GB memory)

Boot disk:
- OS: Ubuntu 22.04 LTS
- Size: 500 GB
- Type: Standard persistent disk

Firewall:
- Allow HTTP traffic ✓
- Allow HTTPS traffic ✓
```

**gcloud Command:**
```bash
gcloud compute instances create fntx-ai-vm-v2 \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=500GB \
    --boot-disk-type=pd-standard \
    --tags=http-server,https-server
```

### 2. Connect to VM
```bash
gcloud compute ssh fntx-ai-vm-v2 --zone=us-central1-a
```

## System Setup Script

### 2.1 Basic System Setup
```bash
#!/bin/bash
# FNTX VM Setup Script

# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    htop \
    vim \
    screen \
    unzip

# Install Node.js (for future web development)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Create user directory structure
mkdir -p /home/$(whoami)/fntx-ai-v1
cd /home/$(whoami)/fntx-ai-v1

echo "✅ Basic system setup complete!"
```

### 2.2 Clone Project and Setup Python
```bash
# Clone project (replace with your backup method)
git clone YOUR_BACKUP_REPO_URL fntx-ai-v1
# OR restore from backup files

cd fntx-ai-v1/blockchain

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

echo "✅ Python environment setup complete!"
```

### 2.3 Test Installation
```bash
# Test ASCII art demo
cd demo
python show_shaded_art.py

# If successful, you should see:
# 🎨 FNTX Shaded ASCII Art NFT Demo
# [ASCII art displays]

echo "✅ System restoration complete!"
```

## Project Restoration Checklist

### Essential Files to Restore
```bash
# Create directory structure
mkdir -p blockchain/{contracts,cli,blockchain_integration,demo,tests}

# Core files to copy:
# - blockchain/cli/ascii_art_generator.py
# - blockchain/cli/nft_terminal_viewer.py  
# - blockchain/contracts/core/*.sol
# - blockchain/blockchain_integration/**/*.py
# - blockchain/requirements.txt
# - blockchain/demo/*.py
```

### Verify Core Functionality
```bash
# Test 1: ASCII Art Generator
cd blockchain/demo
python -c "
from cli.ascii_art_generator import ASCIIArtGenerator
gen = ASCIIArtGenerator()
print('✅ ASCII Art Generator working')
"

# Test 2: NFT Viewer
python -c "
from cli.nft_terminal_viewer import TerminalNFTViewer
viewer = TerminalNFTViewer()
print('✅ NFT Terminal Viewer working')
"

# Test 3: Full Demo
python show_shaded_art.py
```

## Configuration Files

### requirements.txt
```
rich>=13.0.0
plotext>=5.2.0
web3>=6.0.0
python-dotenv>=1.0.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
eth-account>=0.8.0
hexbytes>=0.3.0
```

### .bashrc additions
```bash
# Add to ~/.bashrc for convenience
echo 'alias fntx-activate="cd ~/fntx-ai-v1/blockchain && source venv/bin/activate"' >> ~/.bashrc
echo 'alias fntx-demo="cd ~/fntx-ai-v1/blockchain/demo && python show_shaded_art.py"' >> ~/.bashrc
source ~/.bashrc
```

## Cost Monitoring Setup

### 1. Set Billing Alerts
```
Google Cloud Console → Billing → Budgets & alerts

Budget name: FNTX Monthly Budget
Projects: [your-project]
Budget amount: HKD 600
Threshold: 50%, 90%, 100%
Actions: Email alerts
```

### 2. Daily Cost Check Script
```bash
# Create monitoring script
cat > ~/check_costs.sh << 'EOF'
#!/bin/bash
echo "=== GCP Cost Check ==="
echo "Date: $(date)"
echo "Budget: HKD 600/month"
echo "Check actual costs in GCP console:"
echo "https://console.cloud.google.com/billing"
EOF

chmod +x ~/check_costs.sh
```

## Backup Strategy

### Weekly Backup Script
```bash
cat > ~/backup_project.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/tmp/fntx-backup-$(date +%Y%m%d)"
PROJECT_DIR="/home/$(whoami)/fntx-ai-v1"

echo "Creating backup: $BACKUP_DIR"
mkdir -p $BACKUP_DIR

# Backup critical files
cp -r $PROJECT_DIR/blockchain/cli $BACKUP_DIR/
cp -r $PROJECT_DIR/blockchain/contracts $BACKUP_DIR/
cp -r $PROJECT_DIR/blockchain/blockchain_integration $BACKUP_DIR/
cp $PROJECT_DIR/blockchain/requirements.txt $BACKUP_DIR/

# Create archive
tar -czf ~/fntx-backup-$(date +%Y%m%d).tar.gz -C /tmp fntx-backup-$(date +%Y%m%d)
rm -rf $BACKUP_DIR

echo "✅ Backup created: ~/fntx-backup-$(date +%Y%m%d).tar.gz"
EOF

chmod +x ~/backup_project.sh
```

## Troubleshooting

### Common Issues

**1. Python imports not working**
```bash
# Fix: Ensure you're in virtual environment
cd ~/fntx-ai-v1/blockchain
source venv/bin/activate
```

**2. ASCII art not displaying**
```bash
# Fix: Install rich properly
pip install --upgrade rich
```

**3. Permission errors**
```bash
# Fix: Check file permissions
chmod +x ~/fntx-ai-v1/blockchain/demo/*.py
```

### Emergency Rollback
If new VM doesn't work, keep old VM running and:
1. Compare package versions: `pip list`
2. Check system differences: `uname -a`
3. Copy files one by one and test

## Success Validation

### Final Test Checklist
- [ ] VM created with correct specs (e2-medium, 500GB, us-central1-a)
- [ ] Python virtual environment working
- [ ] ASCII art demo displays correctly
- [ ] All file imports working
- [ ] Git/backup restoration successful
- [ ] Billing alerts configured
- [ ] Weekly backup script created
- [ ] Cost projected at <HKD 600/month

**Only delete old VM when ALL checkmarks are complete!**

## Monthly Cost Projection

```
Instance (e2-medium): HKD 234/month
Storage (500GB):      HKD 312/month
Network (minimal):    HKD  20/month
TOTAL:               HKD 566/month

Savings vs current:   82% reduction
Credits last:         17+ months
```