# FNTX Blockchain Quick Start Guide

## Overview

FNTX uses blockchain to create immutable, verifiable trading track records. This guide will help you get started.

## Setup

1. **Install Dependencies**
   ```bash
   cd blockchain
   npm install
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your private key and RPC URLs
   ```

3. **Compile Contracts**
   ```bash
   npm run compile
   ```

## Testing

Run the test suite:
```bash
npm test
```

## Deployment

### Deploy to Testnet (Mumbai)
```bash
npm run deploy:testnet
```

This will:
- Deploy FNTX token (1 trillion supply to your wallet)
- Deploy upgradeable TrackRecord contract
- Save addresses to `deployments/mumbai.json`

### Deploy to Mainnet (Polygon)
```bash
npm run deploy:mainnet
```

**Warning**: This costs real money (~$40 in MATIC)

## Using from Python

```python
from blockchain.web3 import FNTXBlockchain

# Initialize
fntx = FNTXBlockchain(
    network="mumbai",
    private_key="your_private_key"
)

# Check balance
balance = fntx.get_fntx_balance()
print(f"Balance: {balance} FNTX")

# Post daily record
from datetime import datetime
from blockchain.web3.utils import format_date, ipfs_upload

# Prepare data
trading_data = {
    "date": "2024-01-15",
    "pnl": 1250.50,
    "trades": 5,
    "win_rate": 0.80
}

# Upload to IPFS
ipfs_hash = ipfs_upload(trading_data)

# Post to blockchain
date = format_date(datetime.now())
tx_hash = fntx.post_daily_record(date, ipfs_hash)
print(f"Posted record: {tx_hash}")
```

## Gas Costs

- Deployment: ~$40 total (one-time)
- Post record: ~$0.01-0.05 per day
- Token burns: 10 FNTX per record (adjustable)

## Architecture

```
User → CLI → Wallet → Blockchain
              ↓
        Burns FNTX tokens
              ↓
        Stores IPFS hash
              ↓
     Immutable track record
```

## Value Creation

1. **Scarcity**: Token burning reduces supply
2. **Utility**: Verified track records have value
3. **Network Effect**: More traders = more demand
4. **Target**: 1 FNTX = 1 HKD through adoption

## Next Steps

1. Get testnet MATIC from faucet
2. Deploy to testnet
3. Test with small amounts
4. Integrate with CLI
5. Launch on mainnet when ready