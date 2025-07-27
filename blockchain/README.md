# FNTX Blockchain Infrastructure

## Overview

The FNTX blockchain layer provides immutable, verifiable trading track records using Polygon network for low transaction costs.

## Architecture

### Smart Contracts

1. **FNTX.sol** - ERC-20 token contract
   - Total Supply: 1,000,000,000,000 (1 trillion)
   - Decimals: 18
   - Features: Transfer, Burn
   - Immutable once deployed

2. **TrackRecord.sol** - Upgradeable track record storage
   - Stores daily performance hashes (32 bytes)
   - Burns FNTX tokens for each record (initially 10 FNTX)
   - Upgradeable proxy pattern for future improvements

### Directory Structure

```
blockchain/
├── contracts/          # Solidity smart contracts
├── scripts/           # Deployment and interaction scripts
├── test/             # Contract test suites
└── web3/             # Python integration with CLI
```

## Setup

```bash
# Install dependencies
cd blockchain
npm install

# Compile contracts
npx hardhat compile

# Run tests
npx hardhat test

# Deploy to testnet
npx hardhat run scripts/deploy.js --network mumbai
```

## Token Economics

- **Initial Supply**: 1 trillion FNTX (all owned by deployer)
- **Burn Mechanism**: Users burn FNTX to post track records
- **Value Creation**: Scarcity through burning + utility from verified records
- **Target**: 1 FNTX = 1 HKD through adoption and utility

## Integration with CLI

The CLI integrates with blockchain through:
1. Wallet connection (MetaMask or similar)
2. FNTX balance checking
3. Track record posting with token burn
4. Verification of historical records

## Deployment Costs

- FNTX Token: ~$10-20 on Polygon
- TrackRecord Contract: ~$20-30 (upgradeable)
- Daily Operations: ~$0.01-0.05 per track record post

## Security Considerations

- Smart contracts will be tested extensively on testnet
- Consider professional audit before mainnet deployment
- Use established patterns (OpenZeppelin) for token implementation