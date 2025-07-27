# FNTX Project Overview
**Last Updated:** 2025-07-27  
**Status:** Ready for GCP Migration

## Project Summary
FNTX is a blockchain-based trading signature system that creates immutable daily trading records as ASCII art NFTs. Each trading day becomes a collectible visualization stored permanently on the blockchain.

## Key Features Completed ✅

### 1. Blockchain Signature System
- **Daily NFT Creation**: Each trading day becomes a unique NFT
- **Grace Period**: 24-hour correction window before immutability
- **Dual Storage Options**: Full on-chain vs IPFS (75% cheaper)
- **Multi-layer Verification**: Prevents data manipulation

### 2. Shaded ASCII Art System
- **Pencil-Sketch Style**: Uses ░▒▓█ characters for depth
- **Performance-Based Themes**:
  - Profit days: Mountain peaks with shading
  - Loss days: Shadow valleys with depth
  - Neutral days: Zen garden patterns
- **Labubu Characters**: Change expression based on P&L

### 3. CLI Terminal Interface
- **Multiple View Modes**: Card, chart, detailed, gallery, shaded, labubu
- **Rich Visualizations**: No web browser needed
- **Blockchain Verification**: Shows tx hash, block number, IPFS links
- **Interactive Demos**: Complete working examples

### 4. Smart Contract Architecture
- **TrackRecordV3**: Full 36-field on-chain storage (~200k gas)
- **TrackRecordIPFS**: Cheaper IPFS version (~50k gas)
- **Grace Period Logic**: Burn-and-remint correction system
- **Upgradeable Contracts**: Future-proof design

## Technical Architecture

### Storage Approaches
```
Option A: Full On-Chain (TrackRecordV3.sol)
- All 36 trading metrics stored on blockchain
- Higher gas cost (~200k gas)
- Fully decentralized
- Immediately queryable

Option B: IPFS Hash (TrackRecordIPFS.sol)  
- Only hash + key metrics on-chain
- 75% cheaper gas costs (~50k gas)
- Full data on IPFS
- Requires IPFS infrastructure
```

### ASCII Art Examples
```
Big Profit (Mountain Theme):
█████████████████████████████████
██         +$5,251              ██
██        ▄█████▄               ██
██       ▄███▓███▄              ██
██      ▄█████████▄             ██
██     ▄███▓█▓█▓███▄            ██
█████████████████████████████████

Small Loss (Valley Theme):
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
▓▓        -$750              ▓▓
▓▓███████████▓▒░░░░░░░▒▓███████▓▓
▓▓█████▓▒░              ░▒▓█████▓▓
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
```

## File Structure
```
fntx-ai-v1/
├── Documentation/                    # All project documentation
│   ├── SYSTEM_BACKUP_DOCUMENTATION.md
│   ├── VM_SETUP_GUIDE.md
│   ├── GCP_COST_OPTIMIZATION_PLAN.md
│   └── FNTX_PROJECT_OVERVIEW.md (this file)
├── blockchain/                       # Main blockchain system
│   ├── contracts/core/               # Smart contracts
│   ├── cli/                         # Terminal interface
│   ├── blockchain_integration/       # Python blockchain interface
│   ├── demo/                        # Working demonstrations
│   └── tests/                       # Test infrastructure
└── 01_backend/                      # Trading calculation engine
```

## Current Development Status

### Completed Components
- [x] ASCII art generator with shading system
- [x] NFT terminal viewer with multiple modes
- [x] Smart contracts (both storage approaches)
- [x] Grace period correction system
- [x] CLI demonstrations and examples
- [x] Test infrastructure setup
- [x] Documentation and setup guides

### Ready for Next Steps
- [ ] Testnet deployment (Mumbai/Sepolia)
- [ ] IPFS integration for cheaper storage
- [ ] Website frontend for daily streaming
- [ ] Fixed-price token mechanism (HKD 0.01)
- [ ] AI-generated Labubu variations

## Migration Context

### Why Migrating
- **Current Cost**: HKD 3,000/month (unsustainable)
- **Credits Remaining**: HKD 9,600 (3.2 months left)
- **Target Cost**: HKD 566/month (82% reduction)
- **Extended Timeline**: 17+ months with same credits

### Migration Plan
1. **Document** current state ✅
2. **Create** new e2-medium VM in us-central1-a
3. **Restore** project from documentation
4. **Test** all functionality
5. **Delete** expensive old resources

## Future Roadmap

### Phase 1: Cost Optimization (Immediate)
- Complete GCP migration to cheaper infrastructure
- Set up cost monitoring and alerts
- Optimize storage usage

### Phase 2: Deployment (1-2 months)
- Deploy to testnet for real blockchain testing
- Implement IPFS storage integration
- Connect to live trading data

### Phase 3: Product Launch (2-4 months)
- Website for daily NFT streaming
- Fixed-price token system (HKD 0.01)
- Public access to trading NFTs

### Phase 4: Ecosystem (4-6 months)
- Multi-token system (FNTX, FNTX-MEME, FNTX-STABLE)
- AI-generated art variations
- Community features and sharing

## Key Design Decisions

### Blockchain Choice: Polygon
- **Reason**: Low gas fees, Ethereum compatibility
- **Cost**: ~$1-5 per NFT mint vs $50-200 on Ethereum
- **Speed**: 2-second block times

### Storage Strategy: Dual Options
- **Full On-Chain**: For maximum decentralization
- **IPFS Hybrid**: For cost optimization
- **User Choice**: Let users decide based on budget

### Art Style: Shaded ASCII
- **Aesthetic**: Pencil-sketch with depth
- **Compatibility**: Works in any terminal
- **Uniqueness**: Each day's performance creates different art

### Grace Period: 24 Hours
- **Purpose**: Allow correction of honest mistakes
- **Implementation**: Burn old NFT, mint new one
- **Cost**: Additional 5 FNTX tokens for corrections

## Success Metrics

### Technical
- All ASCII art demos working perfectly
- Smart contracts deployed and tested
- CLI interface fully functional
- Zero data loss during migration

### Financial  
- Monthly costs below HKD 600
- Credits lasting 17+ months
- No unexpected billing spikes

### User Experience
- Beautiful ASCII art in terminal
- Easy blockchain verification
- Simple correction process
- Rich visualization options

---

**Next Immediate Action**: Execute GCP migration plan to reduce costs by 82% while preserving all functionality.