# FNTX Blockchain Trading Signature System

<div align="center">

![FNTX Logo](https://via.placeholder.com/200x80/1a1a1a/ffffff?text=FNTX)

**Immutable Trading Performance as ASCII Art NFTs**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Blockchain](https://img.shields.io/badge/Blockchain-Polygon-purple.svg)](https://polygon.technology)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

Turn your daily trading performance into beautiful ASCII art NFTs stored permanently on the blockchain.

</div>

## 🎨 What is FNTX?

FNTX creates **immutable daily trading records** as **ASCII art NFTs** on the blockchain. Each trading day becomes a unique, verifiable visualization of your performance - like a permanent diary of your trading journey.

### Key Features
- 🎨 **Shaded ASCII Art**: Pencil-sketch style NFTs using `░▒▓█` characters
- ⛓️ **Blockchain Storage**: Immutable records on Polygon (low gas fees)
- 🕐 **Grace Period**: 24-hour correction window before permanent storage
- 🖥️ **CLI Interface**: Rich terminal visualization (no web browser needed)
- 💰 **Dual Storage**: Choose full on-chain or cheaper IPFS options

## 🚀 Quick Demo

```bash
# Clone and setup
git clone https://github.com/bearhedge/fntx-ai-v1.git
cd fntx-ai-v1/blockchain
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# See the magic ✨
cd demo && python show_shaded_art.py
```

### Example ASCII Art NFT
```
█████████████████████████████████████████████████████████████
██                    FNTX TRADING DAY                     ██
██                     2025-01-26                        ██
█████████████████████████████████████████████████████████████
██                         ▄█▄                             ██
██                        ▄███▄                            ██
██                       ▄█████▄      +$2,450              ██
██                      ▄███▓███▄                          ██
██                     ▄█████████▄                         ██
██  Win Rate:  82.5% ████████████░░░  Sharpe:  2.3         ██
█████████████████████████████████████████████████████████████
```

## 📁 Project Structure

```
fntx-ai-v1/
├── blockchain/                          # 🎯 Main blockchain system
│   ├── contracts/core/                  # Smart contracts
│   │   ├── FNTX.sol                    # Token contract (1 trillion supply)
│   │   ├── TrackRecordV3.sol           # Full on-chain storage
│   │   └── TrackRecordIPFS.sol         # Cheaper IPFS version
│   ├── cli/                            # Terminal interface
│   │   ├── ascii_art_generator.py      # Shaded ASCII art creation
│   │   └── nft_terminal_viewer.py      # Rich terminal NFT display
│   ├── blockchain_integration/         # Python ↔ Blockchain
│   │   ├── signatures/                 # Daily signature system
│   │   └── verification/               # Multi-layer data validation
│   ├── demo/                           # 🎮 Try it yourself!
│   │   ├── show_shaded_art.py         # ASCII art showcase
│   │   └── simple_demo.py             # Basic functionality
│   └── tests/                          # Test infrastructure
├── Documentation/                       # 📚 Complete guides
│   ├── SYSTEM_BACKUP_DOCUMENTATION.md
│   ├── VM_SETUP_GUIDE.md
│   ├── GCP_COST_OPTIMIZATION_PLAN.md
│   └── AUTOMATED_SETUP_SCRIPT.md
└── 01_backend/                         # Trading calculation engine
```

## 🎨 ASCII Art Styles

FNTX creates different art styles based on your trading performance:

| Performance | Style | Example |
|-------------|-------|---------|
| **Big Profit** | Mountain Peaks | `▄███████▄` with shading |
| **Small Profit** | Ocean Waves | `░▒▓█▓▒░` wave patterns |
| **Neutral** | Zen Garden | Balanced geometric patterns |
| **Loss** | Shadow Valley | Shaded valley with depth |

### Character Palette
```
Light → Dark: ░ ▒ ▓ █
Texture:      ·∴∵ (particles)
Effects:      ◢◣◤◥ (energy)
Special:      ○●□■ (shapes)
```

## ⛓️ Blockchain Architecture

### Smart Contract Options

#### 1. Full On-Chain Storage (TrackRecordV3.sol)
- **Storage**: All 36 trading metrics on blockchain
- **Gas Cost**: ~200,000 gas (~$1-5 on Polygon)
- **Benefits**: Fully decentralized, immediately queryable
- **Best For**: When cost isn't a concern

#### 2. IPFS Hybrid (TrackRecordIPFS.sol) 
- **Storage**: Hash + key metrics on-chain, full data on IPFS
- **Gas Cost**: ~50,000 gas (75% cheaper!)
- **Benefits**: Much cheaper while maintaining verifiability
- **Best For**: Daily posting, cost optimization

### Grace Period System
- ⏰ **24-hour correction window** after posting
- 🔥 **Burn & remint**: Fix mistakes by burning old NFT + minting corrected version
- 💰 **Cost**: 10 FNTX for posting + 5 FNTX for corrections
- 🔒 **Immutable**: After 24 hours, record becomes permanent

## 🖥️ CLI Interface

### Multiple View Modes
```bash
# Activate environment
source blockchain/venv/bin/activate

# View modes
fntx-demo card      # Trading card style
fntx-demo shaded    # Pencil-sketch ASCII art
fntx-demo labubu    # Character-based (changes with P&L)
fntx-demo gallery   # Multiple days overview
fntx-demo detailed  # Full metrics breakdown
```

### Blockchain Verification
Each NFT shows:
- 🔗 **Transaction Hash**: Polygon blockchain proof
- 📦 **Block Number**: Permanent block reference  
- 📁 **IPFS Hash**: Decentralized metadata storage
- 🏷️ **Token ID**: Unique NFT identifier

## 💾 Installation & Setup

### Prerequisites
- Python 3.8+ 
- Git
- Terminal with Unicode support

### Quick Setup
```bash
# 1. Clone repository
git clone https://github.com/bearhedge/fntx-ai-v1.git
cd fntx-ai-v1

# 2. Setup Python environment  
cd blockchain
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Test installation
cd demo
python show_shaded_art.py
```

### Dependencies
```
rich>=13.0.0          # Terminal visualization
plotext>=5.2.0        # Terminal charts  
web3>=6.0.0           # Blockchain integration
python-dotenv>=1.0.0  # Environment variables
pytest>=7.0.0         # Testing framework
```

## 🔮 Future Roadmap

### Phase 1: Foundation ✅
- [x] ASCII art generation system
- [x] Smart contracts with grace period
- [x] CLI visualization interface
- [x] Comprehensive documentation

### Phase 2: Deployment (In Progress)
- [ ] Mumbai/Sepolia testnet deployment
- [ ] IPFS integration for cheaper storage
- [ ] Website for daily NFT streaming
- [ ] Fixed-price token system (HKD 0.01)

### Phase 3: Ecosystem
- [ ] Multi-token system (FNTX, FNTX-MEME, FNTX-STABLE)
- [ ] AI-generated Labubu character variations
- [ ] Community features and sharing
- [ ] DeFi integrations and utility

## 💰 Cost Structure

### FNTX Token Economics
- **Total Supply**: 1 trillion FNTX tokens
- **Target Price**: HKD 0.01 per token (fixed)
- **Burn Mechanism**: 10 FNTX per daily record
- **Correction Fee**: 5 FNTX additional

### Gas Costs (Polygon)
- **Full On-Chain**: ~$1-5 per NFT
- **IPFS Hybrid**: ~$0.25-1.25 per NFT
- **Correction**: Same as original post

## 🧪 Testing

```bash
# Run all tests
cd blockchain
source venv/bin/activate
python -m pytest tests/ -v

# Test specific components
pytest tests/unit/test_signature_engine.py
pytest tests/unit/test_ascii_art_generator.py

# Integration tests
pytest tests/integration/
```

## 📖 Documentation

Complete documentation available in `/Documentation/`:

- **[System Backup](Documentation/SYSTEM_BACKUP_DOCUMENTATION.md)**: Complete current state
- **[VM Setup Guide](Documentation/VM_SETUP_GUIDE.md)**: Step-by-step new environment setup  
- **[Cost Optimization](Documentation/GCP_COST_OPTIMIZATION_PLAN.md)**: 82% GCP cost reduction plan
- **[Automated Setup](Documentation/AUTOMATED_SETUP_SCRIPT.md)**: One-command installation

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## ⚠️ Risk Warning

**Options trading involves substantial risk and is not suitable for all investors.** This software creates immutable records of trading activity for transparency and verification purposes. Past performance does not guarantee future results.

## 📄 License

This project is proprietary software. All rights reserved.

---

<div align="center">

**Turn your trading performance into blockchain art** 🎨⛓️

Made with ❤️ and lots of ░▒▓█

</div>