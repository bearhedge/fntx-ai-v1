# Virtual Environment Setup Guide
**One-time setup documentation for FNTX migration**

## Overview

This guide helps you recreate the Python virtual environment for the FNTX blockchain system. The virtual environment contains all Python packages needed to run ASCII art demos, blockchain integration, and CLI tools.

**⚠️ Note: This is a temporary file that will be deleted after successful VM migration.**

## What's NOT on GitHub

The following are excluded from GitHub but needed for full functionality:

### 1. Virtual Environment (`blockchain/venv/`)
- **Size**: ~500MB of Python packages
- **Contains**: All installed Python dependencies
- **Why excluded**: Large, machine-specific, easily recreated

### 2. Large Backup Files 
- **Files**: Various `.tar.gz` backup archives
- **Size**: 100MB+ each  
- **Why excluded**: Exceed GitHub's 100MB file limit
- **Status**: ✅ No longer needed (code is on GitHub)

### 3. Cache and Temporary Files
- **Files**: `__pycache__/`, `*.pyc`, log files
- **Why excluded**: Auto-generated, not needed for restoration

## Virtual Environment Recreation

### Step 1: Prerequisites Check
```bash
# Verify Python version (needs 3.8+)
python3 --version

# Verify pip is available
python3 -m pip --version

# Verify venv module
python3 -m venv --help
```

### Step 2: Create Virtual Environment
```bash
# Navigate to blockchain directory
cd /home/$(whoami)/fntx-ai-v1/blockchain

# Create new virtual environment
python3 -m venv venv

# Verify creation
ls -la venv/
# Should show: bin/ include/ lib/ pyvenv.cfg
```

### Step 3: Activate Environment
```bash
# Activate (Linux/Mac)
source venv/bin/activate

# Verify activation (should show venv path)
which python
which pip

# Should see (venv) in your prompt
```

### Step 4: Install Dependencies
```bash
# Upgrade pip first
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt

# Verify installation
pip list
```

### Step 5: Test Installation
```bash
# Test core imports
python3 -c "
import rich
import plotext  
import web3
print('✅ All core packages working!')
"

# Test FNTX components (if files exist)
python3 -c "
try:
    from cli.ascii_art_generator import ASCIIArtGenerator
    from cli.nft_terminal_viewer import TerminalNFTViewer
    print('✅ FNTX components working!')
except ImportError as e:
    print(f'⚠️ FNTX components not found: {e}')
"
```

## Required Python Packages

### Core Dependencies
```txt
rich>=13.0.0          # Terminal visualization and colors
plotext>=5.2.0        # Terminal-based charts and graphs
web3>=6.0.0           # Blockchain integration with Ethereum/Polygon
python-dotenv>=1.0.0  # Environment variable management
```

### Testing Framework
```txt
pytest>=7.0.0         # Test framework
pytest-asyncio>=0.21.0 # Async testing support
```

### Blockchain & Crypto
```txt
eth-account>=0.8.0    # Ethereum account management
hexbytes>=0.3.0       # Hex byte manipulation
```

### Full requirements.txt Content
```txt
# Core dependencies
rich>=13.0.0
plotext>=5.2.0
web3>=6.0.0
python-dotenv>=1.0.0

# Testing
pytest>=7.0.0
pytest-asyncio>=0.21.0

# Additional dependencies
eth-account>=0.8.0
hexbytes>=0.3.0
```

## Troubleshooting

### Common Issues

#### 1. Permission Errors
```bash
# If you get permission errors
sudo chown -R $(whoami):$(whoami) venv/
```

#### 2. Package Installation Fails
```bash
# Update system packages first
sudo apt update
sudo apt install python3-dev python3-pip build-essential

# Then retry pip install
pip install -r requirements.txt
```

#### 3. Import Errors
```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Check if packages are installed
pip list | grep rich
pip list | grep web3
```

#### 4. Rich/Plotext Display Issues
```bash
# Test terminal support
python3 -c "
from rich.console import Console
console = Console()
console.print('Hello [bold red]World[/]!')
"

# If issues, check terminal compatibility
echo $TERM
```

## Environment Variables

### Optional .env File
```bash
# Create .env file for API keys (if needed)
cd /home/$(whoami)/fntx-ai-v1/blockchain
cat > .env << 'EOF'
# Blockchain configuration
POLYGON_RPC_URL=https://polygon-rpc.com
MUMBAI_RPC_URL=https://rpc-mumbai.maticvigil.com

# API Keys (if needed)
INFURA_PROJECT_ID=your_project_id_here
ALCHEMY_API_KEY=your_api_key_here

# IPFS Configuration
IPFS_GATEWAY=https://ipfs.io/ipfs/
PINATA_API_KEY=your_pinata_key_here

# Development settings
DEBUG=true
LOG_LEVEL=INFO
EOF
```

## Verification Checklist

After setup, verify everything works:

- [ ] Virtual environment created successfully
- [ ] All packages from requirements.txt installed
- [ ] No import errors when testing core packages
- [ ] Rich terminal output displays correctly
- [ ] ASCII art demos run without errors
- [ ] Virtual environment activates properly

## Quick Test Commands

```bash
# Activate environment
source venv/bin/activate

# Test package imports
python3 -c "import rich, plotext, web3; print('✅ Core packages OK')"

# Test FNTX demos (if available)
cd demo
python show_shaded_art.py

# Test terminal output
python3 -c "
from rich.console import Console
console = Console()
console.print('[bold green]FNTX Virtual Environment Ready! ✅[/bold green]')
"
```

## Size Estimates

### Virtual Environment Sizes
- **Fresh venv**: ~20MB (just Python)
- **With requirements**: ~500MB (all packages)
- **With cache**: ~600MB (includes pip cache)

### Installation Time
- **On good connection**: 2-5 minutes
- **On slow connection**: 5-15 minutes
- **Depends on**: Internet speed, system specs

## Cleanup After Migration

Once the new VM is working correctly:

```bash
# Remove this temporary documentation
rm Documentation/VIRTUAL_ENVIRONMENT_SETUP.md

# Commit the cleanup
git add .
git commit -m "Remove temporary migration documentation"
git push origin main
```

---

**⚠️ IMPORTANT**: This file is temporary and should be deleted after successful VM migration. Once your new environment is working, this documentation is no longer needed since the setup process will be documented in the permanent VM_SETUP_GUIDE.md file.