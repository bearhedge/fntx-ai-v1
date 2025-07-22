import psycopg2
from psycopg2 import sql
from decimal import Decimal
from datetime import datetime, timedelta
import pytz
import re

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname="options_data",
            user="postgres",
            password="theta_data_2024",
            host="localhost"
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to the database: {e}")
        return None

def get_daily_summary(cursor, summary_date):
    """Fetches the daily summary for a given date."""
    cursor.execute(
        "SELECT opening_nav_hkd, closing_nav_hkd, total_pnl_hkd, net_cash_flow_hkd FROM alm_reporting.daily_summary WHERE summary_date = %s",
        (summary_date,)
    )
    return cursor.fetchone()

def get_daily_commission(cursor, summary_date):
    """Fetches total commission for a given date."""
    cursor.execute(
        """
        SELECT COALESCE(SUM(ABS(ib_commission_hkd)), 0) as total_commission
        FROM alm_reporting.chronological_events 
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
        """,
        (summary_date,)
    )
    result = cursor.fetchone()
    return result[0] if result else Decimal(0)

def get_daily_assignments(cursor, summary_date):
    """Counts assignments for a given date."""
    cursor.execute(
        """
        SELECT COUNT(*) as assignment_count
        FROM alm_reporting.chronological_events 
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
        AND (event_type = 'Assignment' OR LOWER(description) LIKE %s)
        """,
        (summary_date, '%assigned%')
    )
    result = cursor.fetchone()
    return result[0] if result else 0

def get_previous_day_assignments(cursor, current_date):
    """Get detailed assignments from the previous trading day."""
    # Get previous trading day
    prev_date = current_date - timedelta(days=1)
    
    cursor.execute(
        """
        SELECT event_timestamp, description, event_type
        FROM alm_reporting.chronological_events 
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
        AND (event_type = 'Assignment' OR LOWER(description) LIKE %s)
        ORDER BY event_timestamp
        """,
        (prev_date, '%assigned%')
    )
    
    assignments = []
    for ts, desc, etype in cursor.fetchall():
        # Extract option details from assignment
        opt_match = re.search(r'SPY\s+\d{6}([CP])(\d{8})', desc)
        if opt_match:
            option_type = opt_match.group(1)
            strike_str = opt_match.group(2)
            strike = float(strike_str) / 1000
            assignments.append({
                'timestamp': ts,
                'type': 'Call' if option_type == 'C' else 'Put',
                'strike': strike,
                'symbol': 'SPY'
            })
    
    return assignments

def get_assignment_cover_pnl(cursor, summary_date, assignments):
    """Calculate P&L from covering previous day's assignments."""
    if not assignments:
        return Decimal(0)
    
    # Get stock trades on current day that could be assignment covers
    est = pytz.timezone('US/Eastern')
    day_start = est.localize(datetime.combine(summary_date, datetime.min.time()))
    day_end = day_start + timedelta(days=1)
    
    cursor.execute(
        """
        SELECT event_timestamp, description, realized_pnl_hkd, cash_impact_hkd
        FROM alm_reporting.chronological_events
        WHERE event_timestamp >= %s AND event_timestamp < %s
        AND event_type = 'Trade'
        AND description LIKE %s
        AND description NOT LIKE %s
        ORDER BY event_timestamp
        """,
        (day_start, day_end, '%SPY%', '%SPY %[0-9]%')
    )
    
    total_assignment_pnl = Decimal(0)
    stock_trades = cursor.fetchall()
    
    # Look for stock trades that match assignment quantities
    for ts, desc, pnl, cash in stock_trades:
        # Check if this is a stock trade (not option)
        if not is_option_symbol(desc):
            # Extract quantity from description
            qty_match = re.search(r'(Buy|Sell)\s+(\d+)\s+SPY', desc)
            if qty_match:
                action = qty_match.group(1)
                qty = int(qty_match.group(2))
                
                # Assignment covers are typically:
                # - Buy 100 shares (for call assignment - we were short)
                # - Sell 100 shares (for put assignment - we were long)
                # - Usually happen early in the day
                # - Have negative P&L
                if qty == 100 and pnl and pnl < 0:
                    # This is likely an assignment cover
                    total_assignment_pnl += pnl
    
    return total_assignment_pnl

def get_events_for_period(cursor, start_time, end_time):
    """Fetches all chronological events within a given time window."""
    cursor.execute(
        """
        SELECT event_timestamp, event_type, description, cash_impact_hkd, realized_pnl_hkd, 
               COALESCE(ib_commission_hkd, 0) as ib_commission_hkd, 
               CASE 
                   WHEN event_type = 'Assignment' THEN true
                   ELSE false
               END as is_assignment
        FROM alm_reporting.chronological_events 
        WHERE event_timestamp >= %s AND event_timestamp < %s
        ORDER BY event_timestamp
        """,
        (start_time, end_time)
    )
    return cursor.fetchall()

def format_hdk(amount):
    """Formats a decimal amount as HKD currency."""
    if amount is None: amount = Decimal(0)
    return f"{amount:,.2f} HKD"

def calculate_plug(opening_nav, gross_pnl, net_cash_flow, closing_nav):
    """Calculates the reconciliation difference (plug)."""
    expected_closing = opening_nav + gross_pnl + net_cash_flow
    return expected_closing - closing_nav

def generate_summary_table(cursor):
    """Generates the daily summary table with all requested columns."""
    cursor.execute("""
        SELECT 
            summary_date,
            opening_nav_hkd,
            closing_nav_hkd,
            total_pnl_hkd,
            net_cash_flow_hkd
        FROM alm_reporting.daily_summary
        ORDER BY summary_date
    """)
    
    summaries = cursor.fetchall()
    
    # Print table header with proper alignment
    print("\n" + "╔" + "═" * 138 + "╗")
    print("║" + " " * 50 + "DAILY PERFORMANCE SUMMARY" + " " * 52 + "║")
    print("╚" + "═" * 138 + "╝")
    print()
    
    # Print column headers with consistent formatting
    print("┌─────────────┬─────────────────┬─────────────────┬──────────────┬──────────────┬──────────────┬─────────────────┬────────────┬────────────┐")
    print("│    Date     │   Opening NAV   │  Net Cashflow   │  Gross P&L   │ Commissions  │ Net P&L (%)  │   Closing NAV   │    Plug    │ Assignment │")
    print("├─────────────┼─────────────────┼─────────────────┼──────────────┼──────────────┼──────────────┼─────────────────┼────────────┼────────────┤")
    
    for summary_date, opening_nav, closing_nav, gross_pnl, net_cash_flow in summaries:
        # Get commission for the day
        commission = get_daily_commission(cursor, summary_date)
        
        # Get assignment count for the day
        assignment_count = get_daily_assignments(cursor, summary_date)
        has_assignment = '     ✓     ' if assignment_count > 0 else '     -     '
        
        # Calculate net P&L percentage
        net_pnl = gross_pnl - commission
        net_pnl_pct = (net_pnl / opening_nav * 100) if opening_nav != 0 else 0
        
        # Calculate plug
        plug = calculate_plug(opening_nav, gross_pnl, net_cash_flow, closing_nav)
        
        # Format the row with consistent column widths
        print(f"│ {summary_date.strftime('%Y-%m-%d'):^11} │ {opening_nav:>15,.2f} │ {net_cash_flow:>15,.2f} │ {gross_pnl:>12,.2f} │ {commission:>12,.2f} │ {net_pnl_pct:>11.2f}% │ {closing_nav:>15,.2f} │ {plug:>10,.2f} │{has_assignment}│")
    
    print("└─────────────┴─────────────────┴─────────────────┴──────────────┴──────────────┴──────────────┴─────────────────┴────────────┴────────────┘")
    print("\n")

def group_events(events, time_window_minutes=5):
    """Groups consecutive trading events within time windows."""
    if not events: return []
    
    grouped = []
    current_group = [events[0]]
    
    for i in range(1, len(events)):
        time_diff = (events[i][0] - events[i-1][0]).total_seconds() / 60
        
        # Group if: both are trades AND within time window AND same type (option vs stock)
        prev_is_option = is_option_symbol(events[i-1][2])
        curr_is_option = is_option_symbol(events[i][2])
        
        if (events[i][1] == 'Trade' and events[i-1][1] == 'Trade' and 
            time_diff < time_window_minutes and prev_is_option == curr_is_option):
            current_group.append(events[i])
        else:
            grouped.append(current_group)
            current_group = [events[i]]
    
    grouped.append(current_group)
    return grouped

def is_option_symbol(symbol):
    """Check if a symbol is an option."""
    return bool(re.search(r'\d{6}[CP]\d{8}', symbol))

def parse_option_details(symbol):
    """Parse option symbol to extract type and strike."""
    match = re.search(r'(\d{6})([CP])(\d{8})', symbol)
    if match:
        date_str, option_type, strike_str = match.groups()
        strike = float(strike_str) / 1000
        return option_type, strike
    return None, None

def generate_daily_narrative(cursor, summary_date):
    """Generates a narrative summary for a single day."""
    # Get daily summary data
    daily_summary = get_daily_summary(cursor, summary_date)
    if not daily_summary:
        return
    
    opening_nav, closing_nav, total_pnl, net_cash_flow = daily_summary
    
    # Print date header with formatting
    print("\n" + "─" * 80)
    print(f"**{summary_date.strftime('%A, %B %d, %Y')}**")
    print("─" * 80)
    
    # Check for previous day's assignments
    prev_assignments = get_previous_day_assignments(cursor, summary_date)
    assignment_pnl = get_assignment_cover_pnl(cursor, summary_date, prev_assignments)
    
    # Get events for the day
    est = pytz.timezone('US/Eastern')
    day_start = est.localize(datetime.combine(summary_date, datetime.min.time()))
    day_end = day_start + timedelta(days=1)
    
    cursor.execute("""
        SELECT event_timestamp, event_type, description, cash_impact_hkd, realized_pnl_hkd
        FROM alm_reporting.chronological_events
        WHERE event_timestamp >= %s AND event_timestamp < %s
        AND event_type IN ('Trade', 'Assignment', 'Expiration')
        ORDER BY event_timestamp
    """, (day_start, day_end))
    
    events = cursor.fetchall()
    
    # Count trades and analyze contracts
    trade_count = 0
    contracts_opened = []  # Store full event data
    contracts_closed = []
    assignments = []
    expirations = []
    
    for ts, etype, desc, cash, pnl in events:
        if etype == 'Trade' and is_option_symbol(desc) and 'Assigned' not in desc:
            option_type, strike = parse_option_details(desc)
            if option_type:
                contract_desc = f"{option_type} {strike:.0f}"
                # Check if this is an expiration (16:20 ET with 0 cash)
                ts_et = ts.astimezone(est)
                is_expiration_trade = ('Buy' in desc and ts_et.hour == 16 and ts_et.minute == 20 
                                     and (cash == 0 or cash is None))
                
                if 'Sell' in desc and cash and cash > 0:
                    trade_count += 1  # Count opening trades
                    contracts_opened.append((ts, etype, desc, cash, pnl, contract_desc))
                elif 'Buy' in desc and not is_expiration_trade:
                    trade_count += 1  # Count real closing trades (not expirations)
                    # This is a real close/stop-out with premium paid
                    contracts_closed.append(contract_desc)
                elif is_expiration_trade:
                    # Don't count expiration as a trade
                    expirations.append(contract_desc)
        elif etype == 'Assignment' or 'Assigned' in desc:
            option_match = re.search(r'SPY\s+\d{6}[CP]\d{8}', desc)
            if option_match:
                option_type, strike = parse_option_details(option_match.group())
                if option_type:
                    assignments.append(f"{option_type} {strike:.0f}")
        elif etype == 'Expiration':
            # Handle explicit Expiration events
            option_match = re.search(r'SPY\s+\d{6}[CP]\d{8}', desc)
            if option_match:
                option_type, strike = parse_option_details(option_match.group())
                if option_type and f"{option_type} {strike:.0f}" not in expirations:
                    expirations.append(f"{option_type} {strike:.0f}")
    
    # Generate narrative with better formatting
    print(f"\n**Opening Position**")
    print(f"   NAV at market open: **{format_hdk(opening_nav)}**")
    
    # Show assignment impact from previous day
    if prev_assignments and assignment_pnl != 0:
        print(f"\n**Assignment Impact from Previous Day**")
        for assignment in prev_assignments:
            if assignment['type'] == 'Call':
                print(f"   Yesterday's ${assignment['strike']:.0f} Call assignment required delivering 100 shares")
            else:
                print(f"   Yesterday's ${assignment['strike']:.0f} Put assignment required receiving 100 shares")
        
        if assignment_pnl < 0:
            print(f"   • Assignment loss: **{format_hdk(assignment_pnl)}** (shares bought/sold at unfavorable price)")
        else:
            print(f"   • Assignment gain: **{format_hdk(assignment_pnl)}**")
        
        # Show adjusted NAV
        adjusted_opening_nav = opening_nav + assignment_pnl
        print(f"   • Adjusted NAV after assignment impact: **{format_hdk(adjusted_opening_nav)}**")
    
    # Trading activity section
    if trade_count > 0 or assignments:
        print(f"\n**Trading Activity**")
        
        if trade_count > 0:
            print(f"   Total trades executed: {trade_count}")
            
            if contracts_opened:
                print(f"\n   **New Positions Opened:**")
                for ts, etype, desc, cash, pnl, contract_desc in contracts_opened:
                    option_type, strike = parse_option_details(desc)
                    if option_type:
                        # Extract expiry date from option symbol
                        expiry_match = re.search(r'SPY\s+(\d{6})', desc)
                        expiry_str = expiry_match.group(1) if expiry_match else ""
                        # Format expiry date
                        if expiry_str:
                            year = "20" + expiry_str[0:2]
                            month = expiry_str[2:4]
                            day = expiry_str[4:6]
                            expiry_formatted = f"{month}/{day}/{year}"
                        else:
                            expiry_formatted = ""
                        contract_type = "Put" if option_type == "P" else "Call"
                        print(f"      • Sold 1 SPY {expiry_formatted} ${strike:.0f} {contract_type}")
                        print(f"        - Premium received: {format_hdk(cash)}")
                        print(f"        - Execution time: {ts.astimezone(pytz.timezone('US/Eastern')).strftime('%I:%M %p ET')}")
        
        if expirations:
            print(f"\n   **Expired Positions:**")
            for exp in expirations:
                exp_type = "Put" if "P" in exp else "Call"
                strike = exp.split()[1]
                print(f"      • SPY ${strike} {exp_type} expired")
        
        if contracts_closed:
            print(f"\n   **Closed Positions (Stop-Loss/Buy-to-Close):**")
            for closed in contracts_closed:
                closed_type = "Put" if "P" in closed else "Call"
                strike = closed.split()[1]
                print(f"      • SPY ${strike} {closed_type} position closed")
                print(f"        - Position was stopped out to limit losses")
        
        if assignments:
            print(f"\n   **Option Assignments:**")
            for assign in assignments:
                assign_type = "Put" if "P" in assign else "Call"
                strike = assign.split()[1]
                if "P" in assign:
                    print(f"      • SPY ${strike} Put assigned")
                    print(f"        - Received 100 shares at ${strike} per share")
                else:
                    print(f"      • SPY ${strike} Call assigned")
                    print(f"        - Delivered 100 shares at ${strike} per share")
    else:
        print(f"\n**Trading Activity**")
        print(f"   No trades were executed today")
        # Check for small P&L on no-trade days (like currency adjustments)
        if abs(total_pnl) > 0 and abs(total_pnl) < 1:
            print(f"   Small P&L adjustment of {format_hdk(total_pnl)} (likely currency/rounding)")
    
    # Day summary
    print(f"\n**Day Summary**")
    # Calculate return excluding cash flows for true performance
    nav_change = closing_nav - opening_nav - net_cash_flow
    nav_change_pct = (nav_change / opening_nav * 100) if opening_nav != 0 else 0
    
    print(f"   Closing NAV: **{format_hdk(closing_nav)}**")
    if nav_change_pct >= 0:
        print(f"   Daily Return: **+{nav_change_pct:.2f}%**")
    else:
        print(f"   Daily Return: **{nav_change_pct:.2f}%**")
    
    # Gross P&L
    print(f"   Gross P&L: {format_hdk(total_pnl)}")
    
    # Commission impact
    commission = get_daily_commission(cursor, summary_date)
    if commission > 0:
        print(f"   Total Commissions: {format_hdk(commission)}")
        net_pnl = total_pnl - commission
        print(f"   Net P&L: {format_hdk(net_pnl)}")
    
    # Net cashflow
    if net_cash_flow != 0:
        if net_cash_flow > 0:
            print(f"   Cash Flow: +{format_hdk(net_cash_flow)} (deposit)")
        else:
            print(f"   Cash Flow: -{format_hdk(abs(net_cash_flow))} (withdrawal)")
    
    # Assignment tracking
    assignment_count = get_daily_assignments(cursor, summary_date)
    if assignment_count > 0:
        print(f"   Assignments Today: {assignment_count}")

def enhance_trade_description(desc, pnl=None, cash=None, is_expiration=False):
    """Enhance trade descriptions with context and proper formatting."""
    # Handle expirations specially
    if is_expiration:
        match = re.search(r'(SPY\s+\d{6}[CP]\d{8})', desc)
        if match:
            option_symbol = match.group(1)
            return f"{option_symbol} expired worthless"
    
    # Handle assignments
    if 'assigned' in desc.lower():
        # Option assignment
        opt_match = re.search(r'(SPY\s+\d{6}[CP]\d{8})', desc)
        if opt_match:
            option_symbol = opt_match.group(1)
            strike_match = re.search(r'[CP](\d{8})$', option_symbol)
            if strike_match:
                strike = float(strike_match.group(1)) / 1000
                option_type = 'Call' if 'C' in option_symbol else 'Put'
                return f"SPY {strike:.0f} {option_type} assigned (100 shares {'short' if option_type == 'Call' else 'long'} at ${strike:.2f})"
        # Stock assignment
        else:
            return "Assigned 100 shares of SPY"
    
    # Handle regular trades
    if is_option_symbol(desc):
        # First remove any existing context like "(Cover Short)"
        desc_clean = re.sub(r'\s*\([^)]*\)\s*$', '', desc).strip()
        match = re.match(r'(Buy|Sell)\s+(-?\d+)\s+(.*)', desc_clean)
        if match:
            action, qty, symbol = match.groups()
            qty = abs(int(qty))
            context = ""
            if action == 'Sell':
                context = "(Sell to Open)" if cash and cash > 0 else "(Sell)"
            else: # Buy
                if pnl is not None and pnl != 0:
                    context = "(Buy to Close)"
                else:
                    context = "(Buy to Open)"
            return f"{action} {qty} {symbol} {context}"
    else:
        # Stock trades
        match = re.match(r'(Buy|Sell)\s+(-?\d+)\s+(\w+)', desc)
        if match:
            action, qty, symbol = match.groups()
            qty = abs(int(qty))
            # Fix quantity display - IBKR already gives us correct share count
            context = "(Covering Assignment)" if action == 'Buy' and pnl and pnl < 0 else ""
            return f"{action} {qty} shares of {symbol} {context}".strip()
    return desc

def generate_professional_narrative(cursor, summary_date, previous_closing_nav):
    """Generates the final, correct report based on the manually verified logic."""
    daily_summary = get_daily_summary(cursor, summary_date)
    if not daily_summary: return previous_closing_nav

    opening_nav, closing_nav, total_pnl, net_cash_flow = daily_summary
    
    # Track adjusted NAVs
    adjusted_opening_nav = opening_nav
    adjusted_closing_nav = closing_nav
    
    hkt = pytz.timezone('Asia/Hong_Kong')
    est = pytz.timezone('US/Eastern')

    period_start = est.localize(datetime.combine(summary_date - timedelta(days=1), datetime.min.time()) + timedelta(hours=16))
    period_end = est.localize(datetime.combine(summary_date, datetime.min.time()) + timedelta(hours=16))
    market_open_time = est.localize(datetime.combine(summary_date, datetime.min.time()) + timedelta(hours=9, minutes=30))

    print(f"### **US Trading Day: {summary_date.strftime('%A, %B %d, %Y')}**\n")
    
    all_events = get_events_for_period(cursor, period_start, period_end)
    
    pre_market_events = [e for e in all_events if e[0] < market_open_time]
    intraday_events = [e for e in all_events if e[0] >= market_open_time]

    running_nav = previous_closing_nav
    assignment_positions = {}  # Track {symbol: {'strike': price, 'quantity': shares, 'timestamp': datetime}}
    overnight_pnl_total = Decimal(0)  # Track total overnight P&L for adjusted NAV
    print(f"* **Previous Close ({period_start.astimezone(hkt).strftime('%Y-%m-%d %H:%M:%S HKT')}):**")
    print(f"    * **Starting NAV:** {format_hdk(running_nav)}\n")

    if pre_market_events:
        print("* **Overnight / Pre-Market Period:**\n")
        for event in pre_market_events:
            ts, etype, desc, cash, pnl, comm, is_assign = event
            
            # Fix: Force assignments to be NAV-neutral
            if is_assign:
                cash = Decimal(0)
                
            # FIX: Always include cash impact in NAV calculation for trades
            nav_impact = (cash or 0) + (pnl or 0) + (comm or 0)
            running_nav += nav_impact
            
            # Check if this is an expiration
            is_expiration = (etype == 'Expiration' or 
                           (ts.astimezone(est).hour == 16 and ts.astimezone(est).minute == 20 and 
                            is_option_symbol(desc) and (cash or 0) == 0 and (pnl or 0) > 0 and 'Buy' in desc))
            
            print(f"    * **{ts.astimezone(hkt).strftime('%H:%M HKT')} ({ts.astimezone(est).strftime('%H:%M EDT')}):** {enhance_trade_description(desc, pnl, cash, is_expiration)}")
            
            # Track assignments for overnight P&L
            if is_assign:
                # Look for option symbol pattern in description
                opt_match = re.search(r'SPY\s+\d{6}[CP]\d{8}', desc)
                if opt_match:
                    # Extract strike from option symbol
                    strike_match = re.search(r'[CP](\d{8})$', opt_match.group())
                    if strike_match:
                        strike_price = Decimal(strike_match.group(1)) / 1000
                        assignment_positions['SPY'] = {
                            'strike': strike_price,
                            'quantity': -100 if 'C' in opt_match.group() else 100,
                            'timestamp': ts
                        }
            
            # Check if this is a cover trade for an assignment
            if 'SPY' in desc and not is_option_symbol(desc) and 'SPY' in assignment_positions:
                # Extract price from description (e.g., "Buy 100 SPY @ 629.45")
                price_match = re.search(r'@\s*([\d.]+)', desc)
                if price_match:
                    cover_price = Decimal(price_match.group(1))
                    assignment = assignment_positions['SPY']
                    # Calculate P&L: For short position (call assignment), loss when cover price > strike
                    # For long position (put assignment), loss when cover price < strike
                    if assignment['quantity'] < 0:  # Short from call assignment
                        overnight_pnl = (assignment['strike'] - cover_price) * abs(assignment['quantity']) * Decimal('7.8472')
                    else:  # Long from put assignment
                        overnight_pnl = (cover_price - assignment['strike']) * abs(assignment['quantity']) * Decimal('7.8472')
                    overnight_pnl_total += overnight_pnl
                    print(f"        * **Overnight P&L from assignment:** {format_hdk(overnight_pnl)}")
                    del assignment_positions['SPY']
            
            # Show details based on event type
            if is_expiration:
                print(f"        * **Premium Retained:** {format_hdk(pnl)}")
            elif is_option_symbol(desc) and etype == 'Trade' and not is_expiration:
                if (cash or 0) > 0: 
                    print(f"        * **Premium Received:** {format_hdk(cash)}")
                elif (cash or 0) < 0:
                    print(f"        * **Premium Paid:** {format_hdk(abs(cash or 0))}")
                    
            if pnl is not None and pnl != 0 and not is_expiration: 
                print(f"        * **P&L Impact:** {format_hdk(pnl)}")
            if comm is not None and comm != 0: 
                print(f"        * **Commissions:** {format_hdk(comm)}")
            if is_assign: 
                print(f"        * **NAV Impact:** This asset exchange has no immediate P&L impact.")
            print(f"        * **NAV becomes:** {format_hdk(running_nav)}\n")

    # Calculate adjusted opening NAV
    if overnight_pnl_total != 0:
        adjusted_opening_nav = opening_nav + overnight_pnl_total
    
    # Market Open logic - handle different scenarios
    if pre_market_events:
        # Calculate overnight impact
        overnight_impact = sum((e[4] or 0) + (e[5] or 0) for e in pre_market_events)
        
        print(f"* **Market Open ({market_open_time.astimezone(hkt).strftime('%H:%M HKT')} / 09:30 EDT):**")
        if abs(overnight_pnl_total) > 1:
            print(f"    * **Official Opening NAV:** {format_hdk(opening_nav)}")
            print(f"    * **Adjusted Opening NAV:** {format_hdk(adjusted_opening_nav)} (includes overnight P&L from assignment covers)")
            print(f"    * **Actual NAV:** {format_hdk(running_nav)} (after all pre-market activity)")
        else:
            print(f"    * **Opening NAV:** {format_hdk(opening_nav)}")
    else:
        # First day or no overnight events
        print(f"* **Market Open ({market_open_time.astimezone(hkt).strftime('%H:%M HKT')} / 09:30 EDT):** The day begins.")
        print(f"    * **Opening NAV:** {format_hdk(opening_nav)}")
        running_nav = opening_nav  # Use official opening NAV for first day
    print()

    if intraday_events:
        print("* **Intraday Trading Period:**\n")
        
        # Group events for better narrative flow
        grouped_events = group_events(intraday_events)
        
        for group in grouped_events:
            if len(group) > 1 and all(e[1] == 'Trade' for e in group):
                # Process as a group - show net impact
                first_ts = group[0][0]
                last_ts = group[-1][0]
                
                # Calculate group totals
                group_cash = sum(e[3] or 0 for e in group)
                group_pnl = sum(e[4] or 0 for e in group)
                group_comm = sum(e[5] or 0 for e in group)
                # FIX: Include cash impact (premiums) in NAV calculation
                group_nav_impact = group_cash + group_pnl + group_comm
                
                # Apply group impact to NAV
                running_nav += group_nav_impact
                
                print(f"    * **{first_ts.astimezone(hkt).strftime('%H:%M')} - {last_ts.astimezone(hkt).strftime('%H:%M HKT')} ({first_ts.astimezone(est).strftime('%H:%M EDT')}):** Series of {len(group)} trades:")
                
                # Show individual trades in the group
                for event in group:
                    ts, etype, desc, cash, pnl, comm, is_assign = event
                    # Check if this is an expiration (Expiration event type or 16:20 EDT with $0 cash)
                    # For trades marked as "Buy" at 16:20 with $0 cash and positive P&L, these are expirations
                    is_expiration = (etype == 'Expiration' or 
                                   (ts.astimezone(est).hour == 16 and ts.astimezone(est).minute == 20 and 
                                    is_option_symbol(desc) and (cash or 0) == 0 and (pnl or 0) > 0 and 'Buy' in desc))
                    print(f"        - {enhance_trade_description(desc, pnl, cash, is_expiration)}")
                
                # Show group summary
                if is_option_symbol(group[0][2]) and group_cash != 0:
                    print(f"        * **Net Premium:** {format_hdk(group_cash)}")
                if group_pnl != 0:
                    print(f"        * **Net P&L Impact:** {format_hdk(group_pnl)}")
                if group_comm != 0:
                    print(f"        * **Total Commissions:** {format_hdk(group_comm)}")
                print(f"        * **NAV becomes:** {format_hdk(running_nav)}\n")
                
            else:
                # Process single event
                for event in group:
                    ts, etype, desc, cash, pnl, comm, is_assign = event
                    
                    # Fix: Force assignments to be NAV-neutral
                    if is_assign:
                        cash = Decimal(0)
                        
                    # FIX: Always include cash impact in NAV calculation
                    nav_impact = (cash or 0) + (pnl or 0) + (comm or 0)
                    running_nav += nav_impact
                    
                    # Detect option expiration: Expiration event type or 16:20 EDT trades with $0 cost
                    # For trades marked as "Buy" at 16:20 with $0 cash and positive P&L, these are expirations
                    is_expiration = (etype == 'Expiration' or 
                                   (ts.astimezone(est).hour == 16 and ts.astimezone(est).minute == 20 and 
                                    is_option_symbol(desc) and (cash or 0) == 0 and (pnl or 0) > 0 and 'Buy' in desc))
                    
                    
                    print(f"    * **{ts.astimezone(hkt).strftime('%H:%M HKT')} ({ts.astimezone(est).strftime('%H:%M EDT')}):** {enhance_trade_description(desc, pnl, cash, is_expiration)}")
                    
                    # Track assignments for overnight P&L
                    if is_assign:
                        # Look for option symbol pattern in description
                        opt_match = re.search(r'SPY\s+\d{6}[CP]\d{8}', desc)
                        if opt_match:
                            # Extract strike from option symbol
                            strike_match = re.search(r'[CP](\d{8})$', opt_match.group())
                            if strike_match:
                                strike_price = Decimal(strike_match.group(1)) / 1000
                                assignment_positions['SPY'] = {
                                    'strike': strike_price,
                                    'quantity': -100 if 'C' in opt_match.group() else 100,
                                    'timestamp': ts
                                }
                    
                    # Check if this is a cover trade for an assignment
                    if 'SPY' in desc and not is_option_symbol(desc) and 'SPY' in assignment_positions:
                        # Extract price from description (e.g., "Buy 100 SPY @ 629.45")
                        price_match = re.search(r'@\s*([\d.]+)', desc)
                        if price_match:
                            cover_price = Decimal(price_match.group(1))
                            assignment = assignment_positions['SPY']
                            # Calculate P&L: For short position (call assignment), loss when cover price > strike
                            # For long position (put assignment), loss when cover price < strike
                            if assignment['quantity'] < 0:  # Short from call assignment
                                overnight_pnl = (assignment['strike'] - cover_price) * abs(assignment['quantity']) * Decimal('7.8472')
                            else:  # Long from put assignment
                                overnight_pnl = (cover_price - assignment['strike']) * abs(assignment['quantity']) * Decimal('7.8472')
                            overnight_pnl_total += overnight_pnl
                            print(f"        * **Overnight P&L from assignment:** {format_hdk(overnight_pnl)}")
                            del assignment_positions['SPY']
                    
                    # Show details based on event type
                    if is_expiration:
                        print(f"        * **Premium Retained:** {format_hdk(pnl)}")
                    elif is_option_symbol(desc) and etype == 'Trade' and not is_expiration:
                        if (cash or 0) > 0: 
                            print(f"        * **Premium Received:** {format_hdk(cash)}")
                        elif (cash or 0) < 0:
                            print(f"        * **Premium Paid:** {format_hdk(abs(cash or 0))}")
                            
                    if pnl is not None and pnl != 0 and not (is_option_symbol(desc) and cash == 0): 
                        print(f"        * **P&L Impact:** {format_hdk(pnl)}")
                    if comm is not None and comm != 0: 
                        print(f"        * **Commissions:** {format_hdk(comm)}")
                    if is_assign: 
                        print(f"        * **NAV Impact:** This asset exchange has no immediate P&L impact.")
                    
                    print(f"        * **NAV becomes:** {format_hdk(running_nav)}\n")

    print(f"* **Market Close ({period_end.astimezone(hkt).strftime('%Y-%m-%d %H:%M:%S HKT')}):**")
    
    # Calculate adjusted closing NAV based on outstanding assignments
    anticipated_pnl = Decimal(0)
    if assignment_positions:
        # Calculate anticipated P&L from assignments that will be covered tomorrow
        # Use a reasonable estimate for next day's price (same as assignment strike for now)
        for symbol, assignment in assignment_positions.items():
            # Anticipated P&L is 0 since we expect to cover at market price
            # This is just a placeholder - in reality would need next day's price
            anticipated_pnl += 0
        
        adjusted_closing_nav = closing_nav + anticipated_pnl
        print(f"    * **Official Closing NAV:** {format_hdk(closing_nav)}")
        if anticipated_pnl != 0:
            print(f"    * **Adjusted Closing NAV:** {format_hdk(adjusted_closing_nav)} (includes anticipated P&L from today's assignments)")
        
        # List outstanding assignments
        print(f"    * **Outstanding Assignments:**")
        for symbol, assignment in assignment_positions.items():
            print(f"        - {abs(assignment['quantity'])} shares of {symbol} {'short' if assignment['quantity'] < 0 else 'long'} at ${assignment['strike']:.2f}")
    else:
        print(f"    * **Official Closing NAV:** {format_hdk(closing_nav)}")
    
    # Show daily summary
    print(f"\n* **Daily Summary:**")
    print(f"    * **Total P&L:** {format_hdk(total_pnl)}")
    print(f"    * **Net Cash Flow:** {format_hdk(net_cash_flow)}")
    if overnight_pnl_total != 0:
        print(f"    * **Overnight P&L from Previous Day's Assignments:** {format_hdk(overnight_pnl_total)}")
    
    final_calculated_nav = opening_nav + (total_pnl or 0) + (net_cash_flow or 0)
    discrepancy = final_calculated_nav - closing_nav
    if abs(discrepancy) > 1:
        print(f"    * **Reconciliation Note:** The calculated closing NAV based on daily components is {format_hdk(final_calculated_nav)}, showing a discrepancy of {format_hdk(discrepancy)}.")
    
    print("\n" + "="*80 + "\n")
    
    return closing_nav

def main():
    """Main function to generate the ALM report."""
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cursor:
            # Generate summary table first
            generate_summary_table(cursor)
            
            # Generate daily narratives
            print("## **Daily Narratives**\n")
            cursor.execute("SELECT summary_date FROM alm_reporting.daily_summary ORDER BY summary_date;")
            dates = [row[0] for row in cursor.fetchall()]
            
            for summary_date in dates:
                generate_daily_narrative(cursor, summary_date)
        
        conn.close()

if __name__ == "__main__":
    main()