# FNTX Daily Signature Flow

## Complete Process Flow

This document details the exact steps for generating and submitting daily trading signatures to the blockchain.

## 1. Automated Daily Trigger (UTC 00:00)

The process begins automatically every day at midnight UTC via systemd timer:

```bash
# /etc/systemd/system/fntx-signature.timer
[Timer]
OnCalendar=daily
Persistent=true
```

## 2. Data Collection Phase (00:00 - 00:15)

### Step 2.1: Query Trading Database
```python
# Collect from existing calculation engine output
trading_data = db.query("""
    SELECT * FROM daily_summary 
    WHERE date = CURRENT_DATE - INTERVAL '1 day'
""")
```

### Step 2.2: Extract Required Metrics
- Account balances (opening/closing)
- All trades executed
- P&L breakdown (gross, commissions, fees)
- Greeks at market close
- Position outcomes (expired/assigned/stopped)

### Step 2.3: Calculate Rolling Metrics
```python
# Calculate 30-day, MTD, YTD, All-time metrics
metrics = {
    'win_rate_30d': calculate_win_rate(last_30_days),
    'sharpe_ratio_30d': calculate_sharpe(last_30_days),
    'volatility_30d': calculate_volatility(last_30_days),
    # ... etc for all timeframes
}
```

## 3. Verification Phase (00:15 - 00:30)

### Step 3.1: Mathematical Consistency
```python
# Verify balance equation
assert (opening_balance + deposits - withdrawals + net_pnl == closing_balance)

# Verify P&L components
assert (gross_pnl + commissions + interest + fees == net_pnl)
```

### Step 3.2: Logical Constraints
```python
# Check bounds
assert -1 <= delta_exposure <= 1
assert 0 <= win_rate <= 100
assert position_size_pct >= 0
```

### Step 3.3: Cross-Reference Validation
```python
# Verify calculations
assert implied_turnover == contracts * 100 * spy_price
assert margin_used <= account_balance
```

### Step 3.4: Historical Consistency
```python
# Check for anomalies
if daily_return > 10%:
    log_warning("Unusual daily return")
if volatility_30d > volatility_ytd * 2:
    log_warning("Volatility spike detected")
```

## 4. Merkle Tree Generation (00:30 - 00:45)

### Step 4.1: Organize Data by Category
```python
categories = {
    'core': ['date', 'timestamp', 'trading_day_num'],
    'account': ['opening_balance', 'closing_balance', 'deposits', 'withdrawals'],
    'pnl': ['gross_pnl', 'commissions', 'interest_expense', 'net_pnl'],
    'trading': ['contracts_traded', 'implied_turnover', 'position_size_pct'],
    'greeks': ['delta', 'gamma', 'theta', 'vega'],
    'performance': ['sharpe_30d', 'volatility_30d', 'win_rate_30d'],
    'fund': ['dpi', 'tvpi', 'rvpi']
}
```

### Step 4.2: Create Merkle Leaves
```python
leaves = []
for category, fields in categories.items():
    for field in fields:
        leaf = f"{field}:{metrics[field]}"
        leaves.append(hash(leaf))
```

### Step 4.3: Build Tree
```
         Root
        /    \
    Hash1    Hash2
    /  \      /  \
  Leaf1 Leaf2 Leaf3 Leaf4
```

## 5. Blockchain Submission (00:45 - 01:00)

### Step 5.1: Prepare Transaction Data
```python
signature_data = {
    'date': 20240115,
    'merkle_root': merkle_tree.root,
    'metrics': convert_to_blockchain_format(all_metrics)
}
```

### Step 5.2: Check FNTX Balance
```python
balance = blockchain.get_fntx_balance()
if balance < BURN_AMOUNT:
    raise InsufficientFNTXError()
```

### Step 5.3: Submit to Smart Contract
```python
# This burns 10 FNTX and stores the record
tx_hash = track_record_contract.postDailyRecord(signature_data)
```

### Step 5.4: Wait for Confirmation
```python
receipt = wait_for_transaction_receipt(tx_hash)
if receipt.status == 0:
    raise TransactionFailedError()
```

## 6. Post-Submission (01:00+)

### Step 6.1: Store Locally
```python
# Keep local copy for fast access
local_storage.save({
    'date': date,
    'signature': signature_data,
    'tx_hash': tx_hash,
    'block_number': receipt.block_number
})
```

### Step 6.2: Emit Events
```python
# Notify monitoring systems
events.emit('signature_posted', {
    'date': date,
    'tx_hash': tx_hash,
    'net_pnl': net_pnl,
    'implied_turnover': implied_turnover
})
```

### Step 6.3: Update Aggregation Pool
```python
# For multi-user statistics
aggregation_pool.update({
    'user': user_address,
    'date': date,
    'encrypted_metrics': encrypt(sensitive_metrics)
})
```

## Error Handling

### Retry Logic
```python
@retry(max_attempts=3, backoff=exponential)
def submit_to_blockchain(data):
    try:
        return blockchain.submit(data)
    except TransactionError as e:
        log.error(f"Submission failed: {e}")
        raise
```

### Fallback Storage
```python
if blockchain_unavailable:
    # Store in queue for later submission
    pending_queue.add({
        'date': date,
        'data': signature_data,
        'attempts': 0
    })
```

### Alert Conditions
- Verification failures
- Insufficient FNTX balance
- Network connectivity issues
- Unusual metric values

## Manual Signature Generation

For testing or recovery, signatures can be generated manually:

```bash
# Generate signature for specific date
fntx signature generate --date 2024-01-15

# Verify existing signature
fntx signature verify --date 2024-01-15 --tx-hash 0x123...

# Resubmit failed signature
fntx signature resubmit --date 2024-01-15
```

## Multi-User Aggregation Flow

When multiple users participate:

### Individual Submission
Each user submits their encrypted metrics:
```python
encrypted_data = encrypt_with_homomorphic_key(metrics)
aggregator.submit(user_address, encrypted_data)
```

### Aggregation Calculation
Smart contract aggregates without decryption:
```solidity
totalAUM = sum(all_encrypted_aum_values)
totalVolume = sum(all_encrypted_volume_values)
```

### Public Viewing
Anyone can view aggregated totals:
```python
totals = aggregator.get_public_totals()
# Returns: {total_aum: 50000000, total_volume: 2500000000, user_count: 23}
```

## Verification by Third Parties

Anyone can verify a signature:

### Step 1: Get On-Chain Data
```python
record = blockchain.get_record(trader_address, date)
merkle_root = record.merkle_root
```

### Step 2: Verify Merkle Proof
```python
# Verify specific metric
proof = get_merkle_proof('net_pnl', 1250)
is_valid = verify_proof(proof, merkle_root)
```

### Step 3: Check Historical Consistency
```python
# Compare with previous days
history = blockchain.get_records(trader_address, last_30_days)
analyze_consistency(history)
```

This flow ensures complete transparency and verifiability while maintaining efficiency and privacy where needed.