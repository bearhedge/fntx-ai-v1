# FNTX Automated Setup Script

## Quick Setup Commands

### 1. One-Command System Setup
```bash
# Copy and paste this entire block:
curl -sSL https://raw.githubusercontent.com/your-repo/fntx-setup/main/setup.sh | bash
```

### 2. Manual Setup (if automated fails)

#### Step 1: System Dependencies
```bash
#!/bin/bash
# FNTX System Setup - Run on fresh Ubuntu 22.04 VM

set -e  # Exit on any error

echo "🚀 Starting FNTX System Setup..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
echo "🔧 Installing essential packages..."
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
    unzip \
    build-essential

# Install Node.js (for future web development)
echo "📊 Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

echo "✅ System dependencies installed!"
```

#### Step 2: Project Structure
```bash
# Create project directory
echo "📁 Creating project structure..."
cd /home/$(whoami)
mkdir -p fntx-ai-v1/Documentation

# Clone or restore project files
echo "📥 Setting up project files..."
cd fntx-ai-v1

# If you have a git repo:
# git clone YOUR_BACKUP_REPO_URL .

# If restoring from backup:
# wget YOUR_BACKUP_URL
# tar -xzf backup.tar.gz

echo "✅ Project structure created!"
```

#### Step 3: Python Environment
```bash
echo "🐍 Setting up Python environment..."
cd fntx-ai-v1/blockchain

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
cat > requirements.txt << 'EOF'
rich>=13.0.0
plotext>=5.2.0
web3>=6.0.0
python-dotenv>=1.0.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
eth-account>=0.8.0
hexbytes>=0.3.0
EOF

pip install -r requirements.txt

echo "✅ Python environment ready!"
```

#### Step 4: Environment Configuration
```bash
echo "⚙️ Configuring environment..."

# Add convenient aliases
echo '# FNTX Aliases' >> ~/.bashrc
echo 'alias fntx-activate="cd ~/fntx-ai-v1/blockchain && source venv/bin/activate"' >> ~/.bashrc
echo 'alias fntx-demo="cd ~/fntx-ai-v1/blockchain/demo && source ../venv/bin/activate && python show_shaded_art.py"' >> ~/.bashrc
echo 'alias fntx-test="cd ~/fntx-ai-v1/blockchain && source venv/bin/activate && python -m pytest tests/"' >> ~/.bashrc
source ~/.bashrc

echo "✅ Environment configured!"
```

#### Step 5: Verification
```bash
echo "🧪 Testing installation..."

# Test Python environment
cd ~/fntx-ai-v1/blockchain
source venv/bin/activate

# Test imports
python3 -c "
import rich
import plotext
import web3
print('✅ All Python packages working!')
"

# Test ASCII art (if files exist)
if [ -f "cli/ascii_art_generator.py" ]; then
    python3 -c "
from cli.ascii_art_generator import ASCIIArtGenerator
gen = ASCIIArtGenerator()
print('✅ ASCII Art Generator working!')
"
fi

echo "🎉 Setup complete! Run 'fntx-demo' to see the magic!"
```

## Complete Setup Script (setup.sh)

```bash
#!/bin/bash
# FNTX Complete Setup Script
# Usage: curl -sSL https://your-url/setup.sh | bash

set -e
clear

echo "
██████╗ ███╗   ██╗████████╗██╗  ██╗
██╔════╝ ████╗  ██║╚══██╔══╝╚██╗██╔╝
█████╗   ██╔██╗ ██║   ██║    ╚███╔╝ 
██╔══╝   ██║╚██╗██║   ██║    ██╔██╗ 
██║      ██║ ╚████║   ██║   ██╔╝ ██╗
╚═╝      ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝

🚀 FNTX Blockchain Trading NFT System
📦 Automated Setup Script
"

# Check if running on Ubuntu
if ! grep -q "Ubuntu" /etc/lsb-release 2>/dev/null; then
    echo "❌ This script requires Ubuntu 22.04 LTS"
    exit 1
fi

echo "🔍 Checking system requirements..."

# Update system
echo "📦 Updating system..."
sudo apt update -qq && sudo apt upgrade -y -qq

# Install dependencies
echo "🔧 Installing dependencies..."
sudo apt install -y -qq \
    python3 python3-pip python3-venv git curl wget \
    htop vim screen unzip build-essential

# Install Node.js
echo "📊 Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash - >/dev/null 2>&1
sudo apt-get install -y -qq nodejs

# Create project structure
echo "📁 Creating project..."
cd /home/$(whoami)
mkdir -p fntx-ai-v1/{blockchain/{cli,contracts,blockchain_integration,demo,tests},Documentation}
cd fntx-ai-v1/blockchain

# Setup Python environment
echo "🐍 Setting up Python..."
python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip

# Install Python packages
echo "📚 Installing packages..."
cat > requirements.txt << 'EOF'
rich>=13.0.0
plotext>=5.2.0
web3>=6.0.0
python-dotenv>=1.0.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
eth-account>=0.8.0
hexbytes>=0.3.0
EOF

pip install -q -r requirements.txt

# Add aliases
echo "⚙️ Configuring environment..."
cat >> ~/.bashrc << 'EOF'

# FNTX Project Aliases
alias fntx-activate="cd ~/fntx-ai-v1/blockchain && source venv/bin/activate"
alias fntx-demo="cd ~/fntx-ai-v1/blockchain/demo && source ../venv/bin/activate && python show_shaded_art.py"
alias fntx-test="cd ~/fntx-ai-v1/blockchain && source venv/bin/activate && python -m pytest tests/"
alias fntx-backup="cd ~ && tar -czf fntx-backup-$(date +%Y%m%d).tar.gz fntx-ai-v1/"
EOF

# Test installation
echo "🧪 Testing installation..."
python3 -c "import rich, plotext, web3; print('✅ All packages installed successfully!')"

echo "
🎉 FNTX Setup Complete! 

📁 Project location: ~/fntx-ai-v1/
🐍 Python env: fntx-activate
📊 Run demo: fntx-demo
🧪 Run tests: fntx-test
💾 Backup: fntx-backup

Next steps:
1. Restore your project files
2. Run 'source ~/.bashrc' to enable aliases
3. Test with 'fntx-demo'
"
```

## Emergency Recovery Script

```bash
#!/bin/bash
# Emergency recovery if something breaks

echo "🚨 FNTX Emergency Recovery"

# Check what's broken
echo "🔍 Diagnosing issues..."

# Check Python
if ! python3 --version; then
    echo "❌ Python missing - reinstalling..."
    sudo apt install -y python3 python3-pip python3-venv
fi

# Check virtual environment
if [ ! -d "~/fntx-ai-v1/blockchain/venv" ]; then
    echo "❌ Virtual environment missing - recreating..."
    cd ~/fntx-ai-v1/blockchain
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Check imports
cd ~/fntx-ai-v1/blockchain
source venv/bin/activate
python3 -c "
try:
    import rich, plotext, web3
    print('✅ Python packages OK')
except ImportError as e:
    print(f'❌ Missing package: {e}')
    exit(1)
"

# Check file structure
REQUIRED_DIRS=(
    "~/fntx-ai-v1/blockchain/cli"
    "~/fntx-ai-v1/blockchain/contracts" 
    "~/fntx-ai-v1/blockchain/demo"
    "~/fntx-ai-v1/Documentation"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "❌ Missing directory: $dir"
        mkdir -p "$dir"
        echo "✅ Created $dir"
    fi
done

echo "🎉 Recovery complete!"
```

## Backup and Restore

### Create Backup
```bash
#!/bin/bash
# Create backup before migration
BACKUP_NAME="fntx-backup-$(date +%Y%m%d-%H%M%S)"

echo "📦 Creating backup: $BACKUP_NAME"

tar -czf ~/$BACKUP_NAME.tar.gz \
    -C ~/fntx-ai-v1 \
    blockchain/cli \
    blockchain/contracts \
    blockchain/blockchain_integration \
    blockchain/demo \
    blockchain/requirements.txt \
    Documentation

echo "✅ Backup created: ~/$BACKUP_NAME.tar.gz"
echo "💾 Size: $(du -h ~/$BACKUP_NAME.tar.gz | cut -f1)"
```

### Restore from Backup
```bash
#!/bin/bash
# Restore from backup
BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./restore.sh backup-file.tar.gz"
    exit 1
fi

echo "📥 Restoring from: $BACKUP_FILE"

cd ~/fntx-ai-v1
tar -xzf "$BACKUP_FILE"

echo "✅ Files restored!"
echo "🔄 Setting up Python environment..."

cd blockchain
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "🎉 Restore complete!"
```