# FNTX Blockchain Signature System Architecture

## Overview

The FNTX Blockchain Signature System provides comprehensive, immutable daily trading records with multi-user aggregation capabilities. This document outlines the complete architecture and data flow.

## Directory Structure

```
blockchain/
├── contracts/
│   ├── core/                      # Core FNTX contracts
│   │   ├── FNTX.sol              # Token contract
│   │   ├── TrackRecord.sol       # Basic track record
│   │   └── TrackRecordV2.sol     # 36-field comprehensive record
│   │
│   ├── signatures/                # Signature system contracts
│   │   ├── SignatureEngine.sol    # Main signature contract
│   │   ├── DataVerifier.sol       # On-chain verification
│   │   └── MerkleAggregator.sol   # Multi-user aggregation
│   │
│   └── nft/                       # Labubu NFT contracts
│       └── LabubuArt.sol          # Daily art generation
│
├── web3/                          # Python integration
│   ├── core/                      # Core blockchain functionality
│   │   ├── integration.py         # Basic blockchain interface
│   │   ├── track_record_v2.py     # 36-field record interface
│   │   └── data_adapter.py        # Calculation engine adapter
│   │
│   └── signatures/                # Signature system
│       ├── signature_engine.py    # Daily signature generation
│       ├── data_verifier.py       # Multi-layer verification
│       ├── merkle_tree.py         # Merkle tree implementation
│       └── daily_service.py       # Automated daily service
│
└── services/                      # Automated services
    └── daily-signature/           # Daily automation
        └── service.py             # Main service script
```

## Data Flow

### 1. Daily Trading Activity
```
Trading System → Calculation Engine → Database
                                          ↓
                                   Extract metrics
                                          ↓
                                   Data Adapter
```

### 2. Signature Generation (Daily at UTC 00:00)
```
Data Collection → Verification → Merkle Tree → Blockchain Submission
       ↓              ↓              ↓                ↓
   Get metrics    Multi-layer    Hash all      Post to smart
   from DB        validation     metrics       contract
```

### 3. Multi-User Aggregation
```
User 1 Signature ─┐
User 2 Signature ─┼─→ Aggregate Merkle Root → Public Totals
User N Signature ─┘   (Privacy preserved)      (AUM, Volume, etc.)
```

## Comprehensive Signature Fields (36 Total)

### Box 1: Identity & Time (3 fields)
- `date`: YYYYMMDD format
- `timestamp`: Unix timestamp of first trade
- `trading_day_num`: Sequential day counter

### Box 2: Account State (4 fields)
- `opening_balance`: Starting balance for the day
- `closing_balance`: Ending balance
- `deposits`: Daily deposits
- `withdrawals`: Daily withdrawals

### Box 3: P&L Breakdown (5 fields)
- `gross_pnl`: Trading P&L before costs
- `commissions`: Trading commissions (negative)
- `interest_expense`: Margin interest (negative)
- `interest_accruals`: Interest earned on cash
- `net_pnl`: Total net P&L

### Box 4: Performance Metrics (6 fields)
All metrics calculated for multiple timeframes (30d, MTD, YTD, All-time)
- `net_return_pct`: Daily return percentage
- `annualized_return`: Annualized return
- `sharpe_ratio`: Risk-adjusted return
- `sortino_ratio`: Downside risk-adjusted return
- `volatility`: Return volatility
- `max_drawdown`: Maximum peak-to-trough decline

### Box 5: Trading Activity (7 fields)
- `contracts_total`: Total option contracts traded
- `put_contracts`: Put contracts sold
- `call_contracts`: Call contracts sold
- `premium_collected`: Option premium received
- `margin_used`: Margin/buying power utilized
- `position_size_pct`: Position as % of account
- `implied_turnover`: Notional value traded

### Box 6: Greeks (4 fields)
- `delta_exposure`: Directional risk
- `gamma_exposure`: Delta change risk
- `theta_income`: Time decay income
- `vega_exposure`: Volatility risk

### Box 7: Win/Loss Tracking (4 fields)
- `positions_expired`: Winning trades (expired worthless)
- `positions_assigned`: Losing trades (assigned)
- `positions_stopped`: Losing trades (stopped out)
- `win_rate`: Win percentage

### Box 8: Fund Metrics (3 fields)
- `dpi`: Distributions to Paid-In capital
- `tvpi`: Total Value to Paid-In capital
- `rvpi`: Residual Value to Paid-In capital

## Verification Layers

### Layer 1: Mathematical Consistency
- Balance equation verification
- P&L component summation
- Win rate calculation accuracy

### Layer 2: Logical Constraints
- Greeks bounds checking (-1 ≤ delta ≤ 1)
- Position size limits
- Reasonable volatility ranges

### Layer 3: Cross-Reference Validation
- Implied turnover calculation
- Margin vs position size
- Interest accruals vs cash balance

### Layer 4: Historical Consistency
- Detect unusual daily changes
- Compare recent vs historical metrics
- Flag statistical anomalies

## Merkle Tree Structure

```
                    Root Hash
                   /          \
            Core Data      Performance Data
           /        \         /          \
      Account    Trading  Metrics     Greeks
      /    \      /    \    /    \     /   \
   Open Close  Cont Turn  Sharp Vol Delta Gamma
```

## Smart Contract Integration

### Daily Record Submission
1. Generate signature with all 36 fields
2. Create Merkle tree of all data
3. Submit to TrackRecordV2 contract
4. Burn 10 FNTX tokens
5. Emit verification event

### Multi-User Aggregation
1. Each user submits encrypted metrics
2. Smart contract aggregates without decryption
3. Public can view totals only
4. Individual data remains private

## Automated Daily Process

### Schedule (UTC)
- 00:00 - Start daily process
- 00:15 - Collect all trading data
- 00:30 - Run verification checks
- 00:45 - Generate Merkle tree
- 01:00 - Submit to blockchain

### Error Handling
- Retry failed submissions 3 times
- Alert on verification failures
- Store locally if blockchain unavailable
- Submit retroactively when available

## Security Considerations

1. **Private Key Management**
   - Keys stored in secure enclave
   - Never exposed in logs
   - Rotated quarterly

2. **Data Integrity**
   - Multiple verification layers
   - Cryptographic hashing
   - Immutable blockchain storage

3. **Access Control**
   - Only authorized signers
   - Rate limiting on submissions
   - Audit trail for all actions

## Integration Points

### With Calculation Engine
- Read-only access to trading metrics
- No modification of calculation logic
- Data adapter handles transformation

### With CLI
- `fntx signature generate` - Manual signature
- `fntx signature verify` - Verify a signature
- `fntx signature history` - View past signatures

### With Backend Services
- Automated daily service integration
- Monitoring and alerting
- Performance metrics dashboard

## Future Enhancements

1. **Labubu NFT Art**
   - Daily generative art based on trading
   - Milestone NFTs for achievements
   - Collectible trading history

2. **Advanced Aggregation**
   - Strategy-specific pools
   - Regional aggregations
   - Time-based competitions

3. **Enhanced Privacy**
   - Zero-knowledge proofs
   - Homomorphic encryption
   - Selective disclosure

This architecture provides a robust, scalable foundation for immutable trading records while maintaining flexibility for future enhancements.