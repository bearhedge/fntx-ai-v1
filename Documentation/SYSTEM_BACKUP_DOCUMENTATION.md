# FNTX System Backup Documentation
**Created:** 2025-07-27
**Purpose:** Complete system state backup before GCP VM migration

## Current System Overview

### Project Structure
```
/home/info/fntx-ai-v1/
├── blockchain/                    # Main blockchain signature system
│   ├── contracts/core/           # Smart contracts
│   │   ├── FNTX.sol             # Main token contract
│   │   ├── TrackRecordV3.sol    # Full on-chain version
│   │   └── TrackRecordIPFS.sol  # IPFS version (cheaper)
│   ├── cli/                     # Terminal interface
│   │   ├── ascii_art_generator.py    # Shaded ASCII art
│   │   └── nft_terminal_viewer.py    # NFT display system
│   ├── blockchain_integration/   # Python blockchain interface
│   │   ├── signatures/          # Daily signature system
│   │   └── verification/        # Data validation
│   ├── demo/                    # Demonstration scripts
│   │   ├── show_shaded_art.py   # ASCII art demos
│   │   └── simple_demo.py       # Basic functionality
│   ├── tests/                   # Test infrastructure
│   ├── venv/                    # Python virtual environment
│   └── requirements.txt         # Python dependencies
└── 01_backend/                  # Trading calculation engine
    ├── alm/                     # Asset liability management
    ├── llm/                     # LLM integration
    └── execute_spy_trades.py    # Main trading execution
```

### Key Achievements Completed
1. **Blockchain Signature System**: Complete daily trading record storage
2. **ASCII Art NFTs**: Shaded, pencil-sketch style visualizations
3. **Grace Period Logic**: 24-hour correction window
4. **Dual Storage Options**: Full on-chain vs IPFS (cheaper)
5. **CLI Visualization**: Rich terminal NFT display
6. **Test Infrastructure**: TDD-ready testing framework

## Critical Files to Backup

### Smart Contracts
- `/blockchain/contracts/core/FNTX.sol`
- `/blockchain/contracts/core/TrackRecordV3.sol` (full on-chain)
- `/blockchain/contracts/core/TrackRecordIPFS.sol` (IPFS version)

### Python Implementation
- `/blockchain/cli/ascii_art_generator.py` (shaded art system)
- `/blockchain/cli/nft_terminal_viewer.py` (display system)
- `/blockchain/blockchain_integration/signatures/signature_engine.py`
- `/blockchain/blockchain_integration/verification/preview_tool.py`
- `/blockchain/requirements.txt`

### Configuration Files
- `/blockchain/venv/` (virtual environment)
- `/home/info/.claude/CLAUDE.md` (SuperClaude configuration)
- Any `.env` files with API keys

### Trading System
- `/01_backend/` (entire directory)
- Historical options data (~100GB)

## Dependencies and Packages

### System Dependencies
```bash
# Core system packages
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl
```

### Python Environment
```bash
cd /home/info/fntx-ai-v1/blockchain
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Key Python Packages
- rich>=13.0.0 (terminal visualization)
- plotext>=5.2.0 (terminal charts)
- web3>=6.0.0 (blockchain integration)
- python-dotenv>=1.0.0 (environment variables)
- pytest>=7.0.0 (testing)

## Current Progress Status

### Completed Features ✅
1. **ASCII Art System**: Pencil-sketch style with shading (░▒▓█)
2. **NFT Viewer**: Multiple display modes (card, chart, gallery, shaded, labubu)
3. **Smart Contracts**: Both expensive (full on-chain) and cheap (IPFS) versions
4. **Grace Period**: 24-hour correction window with burn-and-remint
5. **CLI Demos**: Working demonstrations of all features

### In Progress 🚧
1. **Fixed-Price Token Mechanism**: HKD 0.01 vending machine design
2. **Website Streaming**: Daily NFT publication system
3. **Testnet Deployment**: Ready for Mumbai/Sepolia testing

### Planned Features 📋
1. **IPFS Integration**: Cheaper storage option
2. **Website Frontend**: Daily NFT streaming
3. **AI Art Generation**: Labubu character variations
4. **Multi-token Ecosystem**: FNTX, FNTX-MEME, FNTX-STABLE

## Recent Technical Decisions

### Storage Approach
- **Option A**: Full on-chain (TrackRecordV3.sol) - ~200k gas
- **Option B**: IPFS hash only (TrackRecordIPFS.sol) - ~50k gas (75% cheaper)
- Both implemented, user can choose based on cost preference

### ASCII Art Design
- Moved from simple line drawings to shaded pencil-sketch style
- Characters: ` ·:;░▒▓█` for depth and texture
- Different themes: mountains (profit), waves (small profit), zen (neutral), valleys (loss)
- Labubu characters that change based on performance

### Blockchain Architecture
- Polygon network for low gas fees
- ERC-721 NFTs for each trading day
- Grace period prevents permanent mistakes
- Upgradeable contracts for future improvements

## Cost Optimization Context

### Current Situation
- **Credits Remaining**: HKD 9,600
- **Current Burn Rate**: HKD 3,000/month
- **Time Until Depletion**: ~3.2 months

### Recommended New Setup
- **Instance**: e2-medium (2 vCPU, 4GB RAM)
- **Storage**: 500GB Standard Persistent Disk
- **Region**: us-central1-a
- **Projected Cost**: HKD 546/month (82% savings)

## Migration Checklist

### Pre-Migration
- [ ] Export all code to GitHub backup
- [ ] Document current VM configuration
- [ ] List all installed packages and versions
- [ ] Backup environment variables and configs
- [ ] Note any custom system configurations

### During Migration
- [ ] Create new VM with recommended specs
- [ ] Install basic system dependencies
- [ ] Clone/restore project files
- [ ] Recreate Python virtual environment
- [ ] Test all functionality

### Post-Migration
- [ ] Verify all demos work correctly
- [ ] Test blockchain integration
- [ ] Confirm ASCII art displays properly
- [ ] Set up cost monitoring alerts
- [ ] Update documentation with new setup

## Emergency Recovery Procedures

### If Migration Fails
1. Keep current VM running temporarily
2. Debug new VM setup step by step
3. Use current VM to troubleshoot
4. Only delete old VM when new one is confirmed working

### If Data Loss Occurs
1. Restore from GitHub backup
2. Rebuild virtual environment from requirements.txt
3. Regenerate any temporary/cache files
4. Test functionality systematically

## Contact Information
- **Primary Developer**: info@fntx-ai-vm
- **Backup Repository**: To be created on GitHub
- **Documentation**: This file + inline code comments

---

**CRITICAL**: Do not delete old VM until new one is 100% confirmed working with all features tested!