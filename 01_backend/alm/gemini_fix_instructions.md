# ALM Calculation Engine Fix Instructions for Gemini

## Overview
The calculation_engine.py file needs critical fixes to properly display ALM (Asset Liability Management) reports. The current output is missing premiums, showing wrong NAV calculations, and incorrectly handling assignments.

## UPDATE: Comprehensive Framework (Added by Claude after deep analysis)

### Critical Design Principles
1. **Assignments are NAV-neutral** - No immediate P&L impact
2. **Trust IBKR data** - Share quantities from IBKR are already correct
3. **Overnight P&L tracking** - Link assignments to subsequent cover trades
4. **Professional narrative** - Match the role model example format
5. **Event grouping** - Combine rapid trades into logical blocks

## Current Issues

### 1. Missing Option Premiums
**Problem**: Option trades have cash_impact_hkd values in the database that represent premiums received/paid, but these aren't displayed.

**Database Evidence**:
```
July 17 Options Sold:
- SPY Put: cash_impact_hkd = 55.98 HKD
- SPY Call: cash_impact_hkd = 118.76 HKD  
- SPY Put: cash_impact_hkd = 278.53 HKD
- SPY Call: cash_impact_hkd = 142.30 HKD
Total Premium Received: 595.57 HKD

July 18 Options Sold:
- SPY Put: cash_impact_hkd = 307.09 HKD
- SPY Call: cash_impact_hkd = 283.55 HKD
Total Premium Received: 590.64 HKD
```

### 2. Assignment Cash Impact Bug
**Problem**: Assignments show massive cash impacts (492,804 HKD) when they should be NAV-neutral.

**Database Evidence**:
```
July 17 20:20: 'Assigned 100 shares of SPY' with cash_impact = 492,804 HKD (WRONG!)
```

### 3. Wrong Opening NAV
**Problem**: July 18 opening NAV shows 79,754.81 but should be ~78,609 after overnight assignment loss.

**Expected Flow**:
```
July 17 Closing: 79,754.81 HKD
Overnight: SPY assigned at $628, covered at $629.45
Loss: (628.00 - 629.45) × 100 = -145 USD = -1,145.44 HKD
July 18 Opening: 79,754.81 - 1,145.44 = 78,609.37 HKD
```

## Required Fixes

### Fix 1: Display Option Premiums
In the event processing section, when handling Trade events that are options:

```python
# For option trades, display the premium
if event_type == 'Trade' and is_option_symbol(description):
    if cash_impact_hkd > 0:
        print(f"        * **Premium Received:** {format_hdk(cash_impact_hkd)}")
    elif cash_impact_hkd < 0:
        print(f"        * **Premium Paid:** {format_hdk(abs(cash_impact_hkd))}")
```

### Fix 2: Handle Assignments Correctly
Assignments must be NAV-neutral. The current code tries to handle this but the database has wrong data:

```python
# When processing assignment pairs:
# 1. The option assignment has is_assignment=True and cash_impact=0
# 2. The stock assignment has is_assignment=True but WRONG cash_impact
# 3. Override the cash impact to 0 for assignments
if is_assignment:
    cash_impact_hkd = Decimal(0)  # Force NAV-neutral
```

### Fix 3: Calculate Overnight P&L
Track assignment prices and calculate P&L when positions are closed:

```python
# When assignment occurs on July 17:
assignment_positions['SPY'] = {
    'strike': 628.00,
    'quantity': -100,  # Short position
    'date': 'July 17'
}

# When covering on July 18 at 629.45:
if 'SPY' in assignment_positions:
    cover_price = 629.45
    strike = assignment_positions['SPY']['strike']
    qty = assignment_positions['SPY']['quantity']
    overnight_pnl = (strike - cover_price) * abs(qty) * 7.8472  # USD to HKD
    # overnight_pnl = (628 - 629.45) * 100 * 7.8472 = -1,145.44 HKD
```

### Fix 4: Enhance Trade Descriptions
The enhance_trade_description function I started needs to be used:

```python
# In event processing:
description = enhance_trade_description(desc, cash_impact, pnl)
```

This will change:
- "Buy 1 SPY" → "Buy 100 shares of SPY (Cover Short)"
- "Sell 1 SPY 250718C00629000" → "Sell 1 SPY 250718C00629000 (Open Short)"

### Fix 5: Handle Option Expirations
Detect when options expire (they have 0 cash impact but positive P&L):

```python
# In event processing:
if event_type == 'Trade' and is_option_symbol(description):
    if cash_impact == 0 and realized_pnl > 0:
        print(f"    * **Option Expiration:** {description}")
        print(f"        * **Premium Retained:** {format_hdk(realized_pnl)}")
```

## Complete Fix Implementation

The generate_professional_narrative function needs a complete rewrite. Here's the structure:

```python
def generate_professional_narrative(cursor, summary_date, previous_closing_nav):
    # ... setup code ...
    
    running_nav = previous_closing_nav
    overnight_pnl = Decimal(0)
    assignment_positions = {}
    
    # Special handling for July 17
    if summary_date.strftime('%Y-%m-%d') == '2025-07-17':
        print(f"* **Market Open (21:30 HKT / 09:30 EDT):** The day begins.")
        print(f"    * **Opening NAV:** {format_hdk(opening_nav)}\n")
        running_nav = opening_nav
    
    # Process pre-market events
    if pre_market_events:
        # Handle overnight assignments and pre-market trades
        # Calculate overnight P&L from assignments
        
    # For other days, show opening with overnight adjustments
    if summary_date.strftime('%Y-%m-%d') != '2025-07-17':
        print(f"* **Market Open (21:30 HKT / 09:30 EDT):**")
        print(f"    * **Opening NAV:** Your true opening NAV is **{format_hdk(running_nav)}**")
        if overnight_pnl != 0:
            print(f"        * This reflects overnight P&L of {format_hdk(overnight_pnl)}")
    
    # Process intraday events with proper premium display
    # Group day trades
    # Show option expirations
    # Display proper closing NAV
```

## Testing

After implementing fixes, run:
```bash
cd /home/info/fntx-ai-v1/01_backend/alm
python3 calculation_engine.py
```

Expected output for July 17-18 should match the format in `/home/info/fntx-ai-v1/05_docs/ALM_REPORTING_COMPLETE_GUIDE.md`

## Key Points
1. **Assignments are NAV-neutral** - no immediate P&L impact
2. **Option premiums must be displayed** for all option trades
3. **Overnight P&L** must be calculated when assigned positions are closed
4. **Trade descriptions** need context (Open Short, Cover Short, etc.)
5. **Option expirations** should show premium retained

## Database Query for Verification
```python
import psycopg2
conn = psycopg2.connect(dbname='options_data', user='postgres', password='theta_data_2024', host='localhost')
cur = conn.cursor()
cur.execute("""
SELECT event_timestamp, event_type, description, cash_impact_hkd, realized_pnl_hkd, is_assignment 
FROM alm_reporting.chronological_events 
WHERE event_timestamp::date BETWEEN '2025-07-17' AND '2025-07-18' 
ORDER BY event_timestamp
""")
```

## Complete Implementation Guide (PRIORITY ORDER)

### Step 1: Fix Assignment Cash Impact (CRITICAL BUG)
In `generate_professional_narrative()` function, when processing events:
```python
# Around line 106-108 and 126-128, BEFORE calculating nav_impact:
if is_assign:
    cash = Decimal(0)  # Force assignments to be NAV-neutral
```

### Step 2: Add Assignment Tracking System
Add this at the beginning of `generate_professional_narrative()` (after line 98):
```python
assignment_positions = {}  # Track {symbol: {'strike': price, 'quantity': shares, 'timestamp': datetime}}
```

When processing assignments (in both pre-market and intraday sections):
```python
if is_assign and 'option' in desc.lower():
    # Extract strike price from option symbol (e.g., SPY 250717C00628000 -> 628.00)
    match = re.search(r'[CP](\d{8})$', desc)
    if match:
        strike_price = Decimal(match.group(1)) / 1000
        assignment_positions['SPY'] = {
            'strike': strike_price,
            'quantity': -100 if 'call' in desc.lower() else 100,
            'timestamp': ts
        }
```

### Step 3: Calculate Overnight P&L
When processing a stock trade that might be covering an assignment:
```python
# Add after line 110 (pre-market) and 131 (intraday):
if 'SPY' in desc and not is_option_symbol(desc) and 'SPY' in assignment_positions:
    # This is likely a cover trade
    cover_price = extract_price_from_desc(desc)  # You'll need to parse the price
    assignment = assignment_positions['SPY']
    overnight_pnl = (assignment['strike'] - cover_price) * abs(assignment['quantity']) * Decimal('7.8472')
    
    # Add to the narrative
    print(f"        * **Overnight P&L from assignment:** {format_hdk(overnight_pnl)}")
    
    # Clear the assignment position
    del assignment_positions['SPY']
```

### Step 4: Event Grouping Logic
Replace the current event processing with grouped logic:
```python
def group_events(events, time_window_minutes=15):
    """Groups consecutive trading events within time windows."""
    if not events: return []
    
    grouped = []
    current_group = [events[0]]
    
    for i in range(1, len(events)):
        time_diff = (events[i][0] - events[i-1][0]).total_seconds() / 60
        
        # Group if: both are trades AND within time window
        if (events[i][1] == 'Trade' and events[i-1][1] == 'Trade' and 
            time_diff < time_window_minutes):
            current_group.append(events[i])
        else:
            grouped.append(current_group)
            current_group = [events[i]]
    
    grouped.append(current_group)
    return grouped

# Use in the intraday section:
grouped_events = group_events(intraday_events)
for group in grouped_events:
    if len(group) > 1:
        # Process as a group with net P&L
        net_pnl = sum((e[4] or 0) + (e[5] or 0) for e in group)
        # ... print grouped narrative
    else:
        # Process individual event
```

### Step 5: Enhanced Trade Descriptions
Update the `enhance_trade_description()` function:
```python
def enhance_trade_description(desc, pnl=None, cash=None):
    """Enhance trade descriptions with context and proper formatting."""
    # For assignments
    if 'assigned' in desc.lower() or 'exercised' in desc.lower():
        return desc
    
    # For options
    if is_option_symbol(desc):
        match = re.match(r'(Buy|Sell)\s+(-?\d+)\s+(.*)', desc)
        if match:
            action, qty, symbol = match.groups()
            qty = abs(int(qty))
            
            # Determine context
            if action == 'Sell' and cash and cash > 0:
                context = "(Sell to Open - Collecting Premium)"
            elif action == 'Buy' and pnl and pnl != 0:
                context = "(Buy to Close - Covering Short)"
            else:
                context = ""
            
            return f"{action} {qty} {symbol} {context}".strip()
    
    # For stocks
    else:
        # Add context for stock trades (especially covers)
        if 'Buy' in desc and pnl and pnl < 0:
            return desc + " (Covering Assigned Position)"
    
    return desc
```

### Step 6: Market Open Logic Fix
For days after assignments, show the adjusted NAV:
```python
# Replace lines 119-121 with:
if pre_market_events:
    # Calculate overnight impact
    overnight_impact = sum((e[4] or 0) + (e[5] or 0) for e in pre_market_events)
    
    print(f"* **Market Open ({market_open_time.astimezone(hkt).strftime('%H:%M HKT')} / 09:30 EDT):**")
    if abs(overnight_impact) > 1:
        print(f"    * **Opening NAV:** Your true opening NAV is **{format_hdk(running_nav)}**, reflecting overnight activity")
        print(f"    * The broker's Official Opening NAV of {format_hdk(opening_nav)} does not yet include pre-market trades")
    else:
        print(f"    * **Opening NAV:** {format_hdk(opening_nav)}")
else:
    # First day or no overnight events
    print(f"* **Market Open ({market_open_time.astimezone(hkt).strftime('%H:%M HKT')} / 09:30 EDT):** The day begins.")
    print(f"    * **Opening NAV:** {format_hdk(opening_nav)}")
```

### Step 7: Option Expiration Detection
Add logic to detect option expirations:
```python
# In event processing:
if is_option_symbol(desc) and cash == 0 and pnl and pnl > 0:
    print(f"    * **Option Expiration:** {desc}")
    print(f"        * **Premium Retained:** {format_hdk(pnl)}")
```

## Testing Checklist
1. Run: `python3 /home/info/fntx-ai-v1/01_backend/alm/calculation_engine.py`
2. Verify assignments show as NAV-neutral
3. Check option premiums are displayed
4. Confirm overnight P&L is calculated correctly
5. Ensure trades are grouped intelligently
6. Match output format to role model in ALM_REPORTING_COMPLETE_GUIDE.md

## Final Notes
- The calculation_engine.py file is at: `/home/info/fntx-ai-v1/01_backend/alm/calculation_engine.py`
- Helper functions already exist: `is_option_symbol()`, `enhance_trade_description()`
- The main work is in the `generate_professional_narrative()` function starting at line 77
- Focus on getting the NAV calculations correct first, then formatting
- If timeout occurs, this guide has everything needed to complete implementation