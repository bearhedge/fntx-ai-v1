import psycopg2
from psycopg2 import sql
from decimal import Decimal
from datetime import datetime, timedelta
import pytz
import re
import numpy as np
from typing import List, Dict, Tuple

# Constants
HKD_USD_RATE = 7.8472
HKT = pytz.timezone('Asia/Hong_Kong')

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

def get_interest_accruals(cursor, summary_date):
    """Get detailed interest accruals data including cumulative balance."""
    # Get daily interest accrual amount
    cursor.execute("""
        SELECT COALESCE(SUM(cash_impact_hkd), 0) as interest_accrual
        FROM alm_reporting.chronological_events
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
        AND event_type = 'Interest_Accrual'
    """, (summary_date,))
    daily_result = cursor.fetchone()
    daily_accrual = daily_result[0] if daily_result else Decimal(0)
    
    # Get cumulative interest accrual up to this date
    cursor.execute("""
        SELECT COALESCE(SUM(cash_impact_hkd), 0) as cumulative_interest
        FROM alm_reporting.chronological_events
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') <= %s
        AND event_type = 'Interest_Accrual'
    """, (summary_date,))
    cumulative_result = cursor.fetchone()
    cumulative_accrual = cumulative_result[0] if cumulative_result else Decimal(0)
    
    return {
        'daily': daily_accrual,
        'cumulative': cumulative_accrual
    }

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
        AND (event_type = 'Option_Assignment' OR LOWER(description) LIKE %s)
        """,
        (summary_date, '%assigned%')
    )
    result = cursor.fetchone()
    return result[0] if result else 0

def check_for_share_disposal(cursor, current_date, lookback_days=5):
    """Check if there are unresolved share positions from recent assignments."""
    # Look back several days for assignments that might not have been disposed yet
    assignments_needing_disposal = []
    
    for days_back in range(1, lookback_days + 1):
        check_date = current_date - timedelta(days=days_back)
        # Skip weekends
        while check_date.weekday() in [5, 6]:
            check_date -= timedelta(days=1)
            days_back += 1
            if days_back > lookback_days + 3:  # Safety limit
                break
        
        # Check for assignments on this date
        cursor.execute("""
            SELECT event_timestamp, description, event_type
            FROM alm_reporting.chronological_events
            WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
            AND event_type = 'Option_Assignment'
            ORDER BY event_timestamp
        """, (check_date,))
        
        assignments = cursor.fetchall()
        if assignments:
            # Check if shares were disposed on subsequent days
            cursor.execute("""
                SELECT COUNT(*) as disposal_count
                FROM alm_reporting.chronological_events
                WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') > %s
                AND DATE(event_timestamp AT TIME ZONE 'US/Eastern') <= %s
                AND event_type = 'Trade'
                AND description LIKE '%%SPY%%'
                -- Exclude option trades
                AND description NOT SIMILAR TO '%%SPY[[:space:]]+[0-9]{6}[CP][0-9]+%%'
                -- Only stock trades
                AND (description LIKE 'Buy%%SPY%%' OR description LIKE 'Sell%%SPY%%')
            """, (check_date, current_date))
            
            disposal_count = cursor.fetchone()[0]
            
            # If no disposals found, track this assignment
            if disposal_count == 0:
                for assignment in assignments:
                    assignments_needing_disposal.append({
                        'date': check_date,
                        'timestamp': assignment[0],
                        'description': assignment[1]
                    })
    
    return assignments_needing_disposal

def get_previous_day_assignments(cursor, current_date):
    """Get detailed assignments from the previous trading day."""
    # Get previous trading day
    prev_date = current_date - timedelta(days=1)
    while prev_date.weekday() in [5, 6]:  # Skip weekends
        prev_date -= timedelta(days=1)
    
    # Execute query with proper parameter handling
    cursor.execute(
        """
        SELECT event_timestamp, description, event_type, cash_impact_hkd, realized_pnl_hkd
        FROM alm_reporting.chronological_events 
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
        AND (event_type = 'Option_Assignment' OR 
             (event_type = 'Option_Assignment_Assumed' AND description LIKE %s) OR
             LOWER(description) LIKE %s)
        ORDER BY event_timestamp
        """,
        (prev_date, '%ASSUMED Assignment%', '%assigned%')
    )
    
    assignments = []
    results = cursor.fetchall()
    if results:
        for row in results:
            ts, desc, etype, cash, pnl = row
            # Extract option details from assignment
            opt_match = re.search(r'SPY\s+(\d{6})([CP])(\d{8})', desc)
            if opt_match:
                option_type = opt_match.group(2)
                strike_str = opt_match.group(3)
                strike = float(strike_str) / 1000
                
                # Determine quantity from description
                qty = 1  # Default to 1 contract
                qty_match = re.search(r'(\d+)\s+contracts?', desc, re.IGNORECASE)
                if qty_match:
                    qty = int(qty_match.group(1))
                
                assignments.append({
                    'timestamp': ts,
                    'type': 'Call' if option_type == 'C' else 'Put',
                    'strike': strike,
                    'symbol': 'SPY',
                    'quantity': qty,
                    'option_symbol': opt_match.group(0)
                })
    
    return assignments

def check_for_pending_assignments(cursor, summary_date):
    """Check for ITM options that are likely to be assigned but not yet in the data."""
    # Get SPY closing price for the date
    cursor.execute("""
        SELECT cash_impact_hkd, description
        FROM alm_reporting.chronological_events
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
        AND event_type = 'Trade'
        AND description LIKE '%%SPY%%'
        ORDER BY event_timestamp DESC
        LIMIT 1
    """, (summary_date,))
    
    last_trade = cursor.fetchone()
    spy_close = None
    
    if last_trade:
        # Try to extract SPY price from the last trade
        import re
        price_match = re.search(r'@\s*([\d.]+)', last_trade[1])
        if price_match:
            spy_close = float(price_match.group(1))
    
    if not spy_close:
        # No SPY price available, can't check for ITM options
        return []
    
    # Get all open short option positions at end of day
    cursor.execute("""
        WITH option_trades AS (
            SELECT 
                description,
                CASE 
                    WHEN cash_impact_hkd > 0 THEN -1  -- Sold option (short)
                    WHEN cash_impact_hkd < 0 THEN 1   -- Bought option (long)
                    ELSE 0
                END as qty_change,
                event_timestamp
            FROM alm_reporting.chronological_events
            WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') <= %s
            AND event_type = 'Trade'
            AND description ~ 'SPY.*[0-9]{2}[A-Z]{3}[0-9]{2}.*[CP]'
        ),
        parsed_options AS (
            SELECT 
                description,
                SUM(qty_change) as net_position,
                -- Extract strike price and option type
                CASE 
                    WHEN description ~ '[0-9]+ C' THEN 'C'
                    WHEN description ~ '[0-9]+ P' THEN 'P'
                    ELSE NULL
                END as option_type,
                CAST(
                    substring(description from '[0-9]+(?= [CP])')
                    AS NUMERIC
                ) as strike
            FROM option_trades
            WHERE description LIKE '%%' || %s || '%%'
            GROUP BY description
        )
        SELECT description, net_position, option_type, strike
        FROM parsed_options
        WHERE net_position < 0  -- Short positions only
        AND (
            (option_type = 'C' AND strike < %s) OR  -- ITM calls
            (option_type = 'P' AND strike > %s)      -- ITM puts
        )
    """, (summary_date, summary_date.strftime('%d%b%y').upper(), spy_close, spy_close))
    
    pending_assignments = []
    results = cursor.fetchall()
    
    for desc, qty, opt_type, strike in results:
        pending_assignments.append({
            'description': desc,
            'quantity': abs(qty),
            'type': 'Call' if opt_type == 'C' else 'Put',
            'strike': float(strike),
            'spy_close': spy_close,
            'assumed': True
        })
    
    return pending_assignments

def get_option_outcomes_for_date(cursor, check_date):
    """Get all option expirations and assignments for a specific date."""
    outcomes = []
    
    # Get expirations
    cursor.execute("""
        SELECT description, event_type, event_timestamp
        FROM alm_reporting.chronological_events
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
        AND event_type = 'Option_Expiration'
        ORDER BY description
    """, (check_date,))
    
    for desc, etype, ts in cursor.fetchall():
        option_match = re.search(r'SPY\s+\d{6}[CP]\d{8}', desc)
        if option_match:
            opt_type, strike = parse_option_details(option_match.group())
            if opt_type and strike:
                outcomes.append({
                    'type': 'expired',
                    'option_type': opt_type,
                    'strike': strike,
                    'symbol': option_match.group(),
                    'timestamp': ts
                })
    
    # Get assignments
    cursor.execute("""
        SELECT description, event_type, event_timestamp
        FROM alm_reporting.chronological_events
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
        AND event_type = 'Option_Assignment'
        ORDER BY description
    """, (check_date,))
    
    for desc, etype, ts in cursor.fetchall():
        option_match = re.search(r'SPY\s+\d{6}[CP]\d{8}', desc)
        if option_match:
            opt_type, strike = parse_option_details(option_match.group())
            if opt_type and strike:
                outcomes.append({
                    'type': 'assigned',
                    'option_type': opt_type,
                    'strike': strike,
                    'symbol': option_match.group(),
                    'timestamp': ts
                })
    
    return outcomes

def get_assignment_cover_pnl(cursor, summary_date, assignments):
    """Calculate overnight P&L from covering previous day's assignments."""
    if not assignments:
        return Decimal(0)
    
    total_overnight_pnl = Decimal(0)
    est = pytz.timezone('US/Eastern')
    day_start = est.localize(datetime.combine(summary_date, datetime.min.time()))
    day_end = day_start + timedelta(days=1)
    
    # Get all stock trades on current day
    cursor.execute(
        """
        SELECT event_timestamp, description, realized_pnl_hkd, cash_impact_hkd
        FROM alm_reporting.chronological_events
        WHERE event_timestamp >= %s AND event_timestamp < %s
        AND event_type = 'Trade'
        AND description LIKE %s
        AND description NOT LIKE %s  -- Exclude options
        AND description NOT LIKE %s  -- Exclude options
        ORDER BY event_timestamp
        """,
        (day_start, day_end, '%SPY%', '%C00%', '%P00%')
    )
    
    stock_trades = cursor.fetchall()
    used_trades = set()  # Track which trades we've matched
    
    # For each assignment, find the corresponding cover trade
    for assignment in assignments:
        strike = assignment['strike']
        option_type = assignment['type']
        qty_contracts = assignment['quantity']
        shares_expected = qty_contracts * 100
        
        # Look for matching stock trade
        for i, (ts, desc, pnl, cash) in enumerate(stock_trades):
            if i in used_trades:
                continue
                
            # Extract action and quantity
            trade_match = re.search(r'(Buy|Sell)\s+(\d+)\s+SPY', desc)
            if not trade_match:
                continue
                
            action = trade_match.group(1)
            qty_shares = int(trade_match.group(2))
            
            # Match assignment type to expected cover action
            # Call assignment (we're short) -> Buy to cover
            # Put assignment (we're long) -> Sell to liquidate
            if ((option_type == 'Call' and action == 'Buy') or 
                (option_type == 'Put' and action == 'Sell')) and \
               qty_shares == shares_expected:
                
                # Calculate cover price from cash impact
                if cash and cash != 0:
                    cover_price_hkd = abs(cash) / qty_shares
                    cover_price_usd = cover_price_hkd / Decimal(str(HKD_USD_RATE))
                    
                    # Calculate overnight P&L
                    if option_type == 'Call':
                        # Call assigned at strike, covered at market
                        # Loss if market > strike: (strike - cover_price) * shares
                        overnight_pnl_usd = (Decimal(str(strike)) - cover_price_usd) * qty_shares
                    else:  # Put
                        # Put assigned at strike, sold at market  
                        # Loss if market < strike: (cover_price - strike) * shares
                        overnight_pnl_usd = (cover_price_usd - Decimal(str(strike))) * qty_shares
                    
                    overnight_pnl_hkd = overnight_pnl_usd * Decimal(str(HKD_USD_RATE))
                    total_overnight_pnl += Decimal(str(overnight_pnl_hkd))
                    
                    used_trades.add(i)
                    break
    
    return total_overnight_pnl

def get_events_for_period(cursor, start_time, end_time):
    """Fetches all chronological events within a given time window."""
    cursor.execute(
        """
        SELECT event_timestamp, event_type, description, cash_impact_hkd, realized_pnl_hkd, 
               COALESCE(ib_commission_hkd, 0) as ib_commission_hkd, 
               CASE 
                   WHEN event_type = 'Option_Assignment' THEN true
                   ELSE false
               END as is_assignment
        FROM alm_reporting.chronological_events 
        WHERE event_timestamp >= %s AND event_timestamp < %s
        AND event_type NOT IN ('Interest_Payment', 'Interest_Accrual_Change')  -- Exclude interest events from main flow
        ORDER BY event_timestamp
        """,
        (start_time, end_time)
    )
    return cursor.fetchall()

def get_interest_events_for_period(cursor, start_time, end_time):
    """Fetches interest-related events within a given time window."""
    cursor.execute(
        """
        SELECT event_timestamp, event_type, description, cash_impact_hkd, realized_pnl_hkd, 
               COALESCE(ib_commission_hkd, 0) as ib_commission_hkd
        FROM alm_reporting.chronological_events 
        WHERE event_timestamp >= %s AND event_timestamp < %s
        AND event_type IN ('Interest_Payment', 'Interest_Accrual_Change')
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
        # Skip June 30, 2025 (bad data)
        if summary_date.year == 2025 and summary_date.month == 6 and summary_date.day == 30:
            continue
            
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
    
    # Display performance metrics after the table
    display_performance_metrics(cursor)
    
    print("\n")

def calculate_performance_metrics(cursor) -> Dict[str, float]:
    """Calculate various performance metrics from daily returns."""
    # Fetch daily NAV data
    cursor.execute("""
        SELECT 
            summary_date,
            opening_nav_hkd,
            closing_nav_hkd,
            total_pnl_hkd,
            net_cash_flow_hkd
        FROM alm_reporting.daily_summary
        WHERE summary_date >= '2025-07-01'
        AND opening_nav_hkd > 0
        ORDER BY summary_date
    """)
    
    data = cursor.fetchall()
    if len(data) < 2:
        return {}
    
    # Calculate daily returns and track capital flows
    daily_returns = []
    nav_values = []
    total_capital_invested = Decimal(0)
    total_distributions = Decimal(0)
    current_nav = Decimal(0)
    
    for i, (date, opening_nav, closing_nav, pnl, cash_flow) in enumerate(data):
        # Skip June 30, 2025 (bad data)
        if date.year == 2025 and date.month == 6 and date.day == 30:
            continue
            
        # Track capital flows for DPI, TVPI, RVPI calculations
        if cash_flow > 0:  # Positive cash flow = capital injection
            total_capital_invested += cash_flow
        elif cash_flow < 0:  # Negative cash flow = distribution
            total_distributions += abs(cash_flow)
            
        # Calculate return excluding cash flows
        if opening_nav > 0:
            # Return = (Closing NAV - Opening NAV - Net Cash Flow) / Opening NAV
            daily_return = float((closing_nav - opening_nav - cash_flow) / opening_nav)
            daily_returns.append(daily_return)
            nav_values.append(float(closing_nav))
            current_nav = closing_nav  # Track latest NAV
    
    if not daily_returns:
        return {}
    
    # Convert to numpy array for calculations
    returns = np.array(daily_returns)
    
    # Risk-free rate (5% annual)
    risk_free_rate = 0.05
    daily_rf = risk_free_rate / 252
    
    # Calculate traditional metrics
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1) if len(returns) > 1 else 0
    
    # Sharpe Ratio
    sharpe_ratio = (mean_return - daily_rf) / std_return * np.sqrt(252) if std_return > 0 else 0
    
    # Annualized metrics
    annualized_return = mean_return * 252
    annualized_volatility = std_return * np.sqrt(252)
    
    # Maximum Drawdown
    cumulative_returns = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdowns = (cumulative_returns - running_max) / running_max
    max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
    
    # Win Rate
    win_rate = np.sum(returns > 0) / len(returns) if len(returns) > 0 else 0
    
    # Sortino Ratio (downside deviation)
    downside_returns = returns[returns < 0]
    downside_std = np.std(downside_returns, ddof=1) if len(downside_returns) > 1 else 0
    sortino_ratio = (mean_return - daily_rf) / downside_std * np.sqrt(252) if downside_std > 0 else 0
    
    # Calmar Ratio
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # Calculate DPI, TVPI, RVPI metrics
    dpi = float(total_distributions / total_capital_invested) if total_capital_invested > 0 else 0
    tvpi = float((total_distributions + current_nav) / total_capital_invested) if total_capital_invested > 0 else 0
    rvpi = float(current_nav / total_capital_invested) if total_capital_invested > 0 else 0
    
    return {
        'sharpe_ratio': sharpe_ratio,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_volatility,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'sortino_ratio': sortino_ratio,
        'calmar_ratio': calmar_ratio,
        'dpi': dpi,
        'tvpi': tvpi,
        'rvpi': rvpi,
        'total_days': len(returns),
        'positive_days': int(np.sum(returns > 0)),
        'negative_days': int(np.sum(returns < 0)),
        'total_capital_invested': float(total_capital_invested),
        'total_distributions': float(total_distributions),
        'current_nav': float(current_nav)
    }

def display_performance_metrics(cursor):
    """Display performance metrics in a formatted table."""
    metrics = calculate_performance_metrics(cursor)
    
    if not metrics:
        print("\n[Performance metrics unavailable - insufficient data]")
        return
    
    # Print metrics table
    print("\n╔════════════════════════════════════════════════════╗")
    print("║              PERFORMANCE METRICS                   ║")
    print("╚════════════════════════════════════════════════════╝")
    print()
    print("┌─────────────────────────┬──────────────────────────┐")
    print("│ Metric                  │ Value                    │")
    print("├─────────────────────────┼──────────────────────────┤")
    
    # Format and display each metric
    print(f"│ Sharpe Ratio           │ {metrics['sharpe_ratio']:>24.2f} │")
    print(f"│ Sortino Ratio          │ {metrics['sortino_ratio']:>24.2f} │")
    print(f"│ Calmar Ratio           │ {metrics['calmar_ratio']:>24.2f} │")
    print(f"│ Annualized Return      │ {metrics['annualized_return']*100:>23.2f}% │")
    print(f"│ Annualized Volatility  │ {metrics['annualized_volatility']*100:>23.2f}% │")
    print(f"│ Maximum Drawdown       │ {metrics['max_drawdown']*100:>23.2f}% │")
    print(f"│ Win Rate               │ {metrics['win_rate']*100:>23.1f}% │")
    print("├─────────────────────────┼──────────────────────────┤")
    print(f"│ DPI                    │ {metrics['dpi']:>24.2f} │")
    print(f"│ TVPI                   │ {metrics['tvpi']:>24.2f} │")
    print(f"│ RVPI                   │ {metrics['rvpi']:>24.2f} │")
    print("└─────────────────────────┴──────────────────────────┘")
    
    # Add performance analysis
    print("\nPerformance Analysis:")
    print(f"✓ Based on {metrics['total_days']} trading days ({metrics['positive_days']} positive, {metrics['negative_days']} negative)")
    
    # Interpret Sharpe Ratio
    if metrics['sharpe_ratio'] >= 2.0:
        print("✓ Sharpe Ratio of {:.2f} indicates exceptional risk-adjusted returns".format(metrics['sharpe_ratio']))
    elif metrics['sharpe_ratio'] >= 1.5:
        print("✓ Sharpe Ratio of {:.2f} indicates excellent risk-adjusted returns".format(metrics['sharpe_ratio']))
    elif metrics['sharpe_ratio'] >= 1.0:
        print("✓ Sharpe Ratio of {:.2f} indicates good risk-adjusted returns".format(metrics['sharpe_ratio']))
    elif metrics['sharpe_ratio'] >= 0.5:
        print("✓ Sharpe Ratio of {:.2f} indicates acceptable risk-adjusted returns".format(metrics['sharpe_ratio']))
    else:
        print("⚠ Sharpe Ratio of {:.2f} indicates poor risk-adjusted returns".format(metrics['sharpe_ratio']))
    
    # Interpret Win Rate
    if metrics['win_rate'] >= 0.8:
        print("✓ Win rate of {:.1f}% shows exceptional consistency".format(metrics['win_rate']*100))
    elif metrics['win_rate'] >= 0.6:
        print("✓ Win rate of {:.1f}% shows strong consistency".format(metrics['win_rate']*100))
    else:
        print("✓ Win rate of {:.1f}%".format(metrics['win_rate']*100))
    
    # Interpret Maximum Drawdown
    if abs(metrics['max_drawdown']) <= 0.05:
        print("✓ Maximum drawdown of {:.2f}% demonstrates excellent risk control".format(abs(metrics['max_drawdown']*100)))
    elif abs(metrics['max_drawdown']) <= 0.10:
        print("✓ Maximum drawdown of {:.2f}% demonstrates good risk control".format(abs(metrics['max_drawdown']*100)))
    else:
        print("⚠ Maximum drawdown of {:.2f}% indicates significant risk exposure".format(abs(metrics['max_drawdown']*100)))

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
    # Check for either format:
    # 1. SPY 21JUL25 630 P (trade format)
    # 2. SPY 250721P00630000 (assignment/expiration format)
    return bool(re.search(r'SPY.*\d+\s*[PC]', symbol) or re.search(r'\d{6}[CP]\d{8}', symbol))

def parse_option_details(symbol):
    """Parse option symbol to extract type and strike."""
    # Try format 1: SPY 250721P00630000
    match = re.search(r'(\d{6})([CP])(\d{8})', symbol)
    if match:
        date_str, option_type, strike_str = match.groups()
        strike = float(strike_str) / 1000
        return option_type, strike
    
    # Try format 2: SPY 21JUL25 630 P
    match = re.search(r'SPY\s+\d+[A-Z]+\d+\s+(\d+)\s*([PC])', symbol)
    if match:
        strike_str, option_type = match.groups()
        strike = float(strike_str)
        return option_type, strike
    
    return None, None

def track_net_positions(cursor, up_to_date):
    """Track net option positions up to a given date to determine what's actually held."""
    cursor.execute("""
        SELECT 
            CASE 
                WHEN description ~ 'SPY\\s+\\d{6}[CP]\\d{8}' THEN 
                    (regexp_match(description, 'SPY\\s+(\\d{6}[CP]\\d{8})'))[1]
                WHEN description ~ 'SPY.*\\d+\\s*[PC]' THEN
                    description
                ELSE description
            END as option_symbol,
            SUM(CASE 
                WHEN cash_impact_hkd > 0 THEN -1  -- Sold option (short)
                WHEN cash_impact_hkd < 0 THEN 1   -- Bought option (long)
                ELSE 0
            END) as net_qty
        FROM alm_reporting.chronological_events
        WHERE event_type = 'Trade' 
        AND description ~ 'SPY.*[CP]'
        AND event_timestamp < %s
        AND description NOT LIKE '%%Assigned%%'
        GROUP BY option_symbol
        HAVING SUM(CASE 
            WHEN cash_impact_hkd > 0 THEN -1
            WHEN cash_impact_hkd < 0 THEN 1
            ELSE 0
        END) != 0
    """, (up_to_date,))
    
    positions = {}
    for row in cursor.fetchall():
        if row[1] != 0:  # Only track non-zero positions
            positions[row[0]] = row[1]
    return positions

def generate_daily_narrative(cursor, summary_date):
    """Generates a narrative summary for a single day."""
    # Skip June 30, 2025 (bad data with 0 NAV but has P&L)
    if summary_date.year == 2025 and summary_date.month == 6 and summary_date.day == 30:
        return
    
    # Get daily summary data
    daily_summary = get_daily_summary(cursor, summary_date)
    if not daily_summary:
        return
    
    opening_nav, closing_nav, total_pnl, net_cash_flow = daily_summary
    
    # Print date header with formatting
    print()
    print("─" * 80)
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
        AND event_type IN ('Trade', 'Option_Assignment', 'Option_Expiration')
        ORDER BY event_timestamp
    """, (day_start, day_end))
    
    events = cursor.fetchall()
    
    # Also get expirations that occurred today (may be reported T+1)
    cursor.execute("""
        SELECT event_timestamp, event_type, description, cash_impact_hkd, realized_pnl_hkd
        FROM alm_reporting.chronological_events
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
        AND event_type = 'Option_Expiration'
        ORDER BY event_timestamp
    """, (summary_date,))
    
    expirations_today = cursor.fetchall()
    
    # Add today's expirations to events if not already included
    for exp in expirations_today:
        if exp not in events:
            events.append(exp)
    
    # Sort all events by timestamp
    events = sorted(events, key=lambda x: x[0])
    
    # Get net positions at start of day to track what can expire
    day_start_positions = track_net_positions(cursor, day_start)
    
    # Count trades and analyze contracts
    trade_count = 0
    contracts_opened = []  # Store full event data
    contracts_closed = []
    
    for ts, etype, desc, cash, pnl in events:
        if etype == 'Trade' and is_option_symbol(desc) and 'Assigned' not in desc:
            option_type, strike = parse_option_details(desc)
            if option_type:
                contract_desc = f"{option_type} {strike:.0f}"
                # Check if this is an expiration (16:20 ET with 0 cash)
                ts_et = ts.astimezone(est)
                is_expiration_trade = (ts_et.hour == 16 and ts_et.minute == 20 
                                     and (cash == 0 or cash is None))
                
                if cash > 0:
                    # Opening trade - selling option, receiving premium
                    trade_count += 1
                    contracts_opened.append((ts, etype, desc, cash, pnl, contract_desc))
                elif cash < 0 and not is_expiration_trade:
                    # Closing trade - buying back option, paying premium
                    trade_count += 1
                    contracts_closed.append(contract_desc)
    
    # Generate narrative with better formatting
    print(f"\n**Opening Position**")
    print(f"   NAV at market open: **{format_hdk(opening_nav)}**")
    
    # Show assignment impact from previous day
    if prev_assignments:
        print(f"\n**Assignment Workflow from Previous Trading Day**")
        
        # Group assignments by type for clearer presentation
        put_assignments = [a for a in prev_assignments if a['type'] == 'Put']
        call_assignments = [a for a in prev_assignments if a['type'] == 'Call']
        
        # Show the assignments
        for assignment in prev_assignments:
            option_symbol = assignment.get('option_symbol', '')
            quantity = assignment.get('quantity', 1)
            strike = assignment.get('strike', 0)
            assignment_time = assignment.get('timestamp', None)
            
            if assignment_time:
                hkt_time = assignment_time.astimezone(HKT)
                time_str = hkt_time.strftime('%I:%M %p HKT')
                # Check if assignment is on next day
                if hkt_time.date() > summary_date:
                    time_str += " (next day)"
            else:
                time_str = "04:20 AM HKT (next day)"  # 16:20 EDT = 04:20 AM HKT next day
            
            if assignment['type'] == 'Call':
                print(f"   • **{time_str} (Assignment):** SPY ${strike:.0f} Call assigned")
                print(f"     - Short {quantity * 100} shares created at ${strike:.2f}/share")
            else:
                print(f"   • **{time_str} (Assignment):** SPY ${strike:.0f} Put assigned")
                print(f"     - Long {quantity * 100} shares created at ${strike:.2f}/share")
        
        # Get share disposal trades - ONLY actual stock trades (no options)
        # Check ALL times, not just pre-market, since disposals can happen anytime
        cursor.execute("""
            SELECT description, cash_impact_hkd, event_timestamp, realized_pnl_hkd
            FROM alm_reporting.chronological_events
            WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
            AND event_type = 'Trade'
            AND description LIKE '%%SPY%%'
            -- Exclude option trades (pattern: SPY   YYMMDD[CP]SSSSSSSS)
            AND description NOT SIMILAR TO '%%SPY[[:space:]]+[0-9]{6}[CP][0-9]+%%'
            -- Only stock trades should remain
            AND (description LIKE 'Buy%%SPY%%' OR description LIKE 'Sell%%SPY%%')
            AND description NOT LIKE '%%Option%%'
            ORDER BY event_timestamp
        """, (summary_date,))
        
        cover_trades = cursor.fetchall()
        
        if cover_trades:
            print(f"\n   **Share Disposal:**")
            total_disposal_pnl = Decimal(0)
            
            for i, trade in enumerate(cover_trades):
                desc = trade[0]
                cash_hkd = trade[1]
                timestamp = trade[2]
                pnl_hkd = trade[3]
                
                # Extract quantity and action from description
                trade_match = re.search(r'(Buy|Sell)\s+(\d+)\s+', desc)
                if trade_match:
                    action = trade_match.group(1)
                    qty = int(trade_match.group(2))
                    
                    # Format time and check if it's next day
                    hkt_time = timestamp.astimezone(HKT)
                    time_str = hkt_time.strftime('%I:%M %p HKT')
                    
                    # Check if disposal is on next day
                    if hkt_time.date() > summary_date:
                        time_str += " (next day)"
                    
                    # Calculate price from cash impact
                    price_usd = abs(cash_hkd) / Decimal(str(HKD_USD_RATE)) / qty
                    
                    print(f"   • **{time_str}:** {desc}")
                    print(f"     - {action} {qty} shares at ${price_usd:.2f}")
                    
                    # Match to assignment and calculate overnight P&L
                    overnight_pnl = Decimal(0)  # Initialize to avoid UnboundLocalError
                    if i < len(prev_assignments):
                        assignment = prev_assignments[i]
                        strike = assignment['strike']
                        
                        if assignment['type'] == 'Call' and action == 'Buy':
                            # Covered short from call assignment
                            overnight_pnl = (Decimal(str(strike)) - price_usd) * qty
                            print(f"     - Overnight P&L: ${overnight_pnl:.2f} (${strike:.2f} - ${price_usd:.2f}) × {qty}")
                        elif assignment['type'] == 'Put' and action == 'Sell':
                            # Liquidated long from put assignment  
                            overnight_pnl = (price_usd - Decimal(str(strike))) * qty
                            print(f"     - Overnight P&L: ${overnight_pnl:.2f} (${price_usd:.2f} - ${strike:.2f}) × {qty}")
                        
                        total_disposal_pnl += overnight_pnl * Decimal(str(HKD_USD_RATE))
            
            if total_disposal_pnl != 0:
                print(f"\n   **Total P&L from disposal:** {format_hdk(total_disposal_pnl)}")
                # Show adjusted NAV after disposal
                adjusted_nav = opening_nav + total_disposal_pnl
                print(f"   **Adjusted NAV after disposal:** {format_hdk(adjusted_nav)}")
        elif assignment_pnl != 0:
            # Show calculated overnight P&L even if we don't have the cover trades
            print(f"\n   **Overnight P&L Impact:** {format_hdk(assignment_pnl)}")
        
    
    # Trading activity section
    if trade_count > 0:
        print(f"\n**Trading Activity**")
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
                    print(f"        - Execution time: {ts.astimezone(HKT).strftime('%I:%M %p HKT')}")
        
        # Get all option outcomes for today
        option_outcomes = get_option_outcomes_for_date(cursor, summary_date)
        
        # Separate expirations and assignments
        expirations = [o for o in option_outcomes if o['type'] == 'expired']
        assignments_today = [o for o in option_outcomes if o['type'] == 'assigned']
        
        # Display expirations
        if expirations:
            print(f"\n   **Expired Positions:**")
            for exp in sorted(expirations, key=lambda x: (x['option_type'], x['strike'])):
                exp_type = "Put" if exp['option_type'] == "P" else "Call"
                print(f"      • SPY ${exp['strike']:.0f} {exp_type} expired")
        
        # Display assignments
        if assignments_today:
            print(f"\n   **Option Assignments:**")
            for assign in sorted(assignments_today, key=lambda x: (x['option_type'], x['strike'])):
                assign_type = "Put" if assign['option_type'] == "P" else "Call"
                print(f"      • SPY ${assign['strike']:.0f} {assign_type} assigned")
                if assign['option_type'] == "P":
                    print(f"        - Received 100 shares at ${assign['strike']:.0f} per share")
                else:
                    print(f"        - Delivered 100 shares at ${assign['strike']:.0f} per share")
                print(f"        - NAV impact: None (asset exchange only)")
        
        # Display closed positions if any
        if contracts_closed:
            print(f"\n   **Closed Positions (Stop-Loss/Buy-to-Close):**")
            for closed in contracts_closed:
                closed_type = "Put" if "P" in closed else "Call"
                strike = closed.split()[1]
                print(f"      • SPY ${strike} {closed_type} position closed")
                print(f"        - Position was stopped out to limit losses")
        
        # Check for undisposed share positions from previous assignments
        undisposed_assignments = check_for_share_disposal(cursor, summary_date)
        # Filter out today's assignments which were already shown
        undisposed_assignments = [a for a in undisposed_assignments if a['date'] != summary_date]
        if undisposed_assignments:
            print(f"\n   **Pending Share Positions from Previous Assignments:**")
            for assignment in undisposed_assignments:
                days_ago = (summary_date - assignment['date']).days
                assignment_desc = assignment['description']
                # Extract strike price from description
                strike_match = re.search(r'@\s*\$?(\d+(?:\.\d+)?)', assignment_desc)
                if strike_match:
                    strike = float(strike_match.group(1))
                    if 'Put' in assignment_desc:
                        print(f"      • Long 100 SPY shares from Put assignment at ${strike:.0f} ({days_ago} day{'s' if days_ago > 1 else ''} ago)")
                    else:
                        print(f"      • Short 100 SPY shares from Call assignment at ${strike:.0f} ({days_ago} day{'s' if days_ago > 1 else ''} ago)")
        
    else:
        print(f"\n**Trading Activity**")
        print(f"   No trades were executed today")
        
        # Check for share disposals from previous assignments
        undisposed_assignments = check_for_share_disposal(cursor, summary_date)
        if undisposed_assignments:
            print(f"\n   **Pending Share Positions from Previous Assignments:**")
            for assignment in undisposed_assignments:
                days_ago = (summary_date - assignment['date']).days
                assignment_desc = assignment['description']
                # Extract strike price from description
                strike_match = re.search(r'@\s*\$?(\d+(?:\.\d+)?)', assignment_desc)
                if strike_match:
                    strike = float(strike_match.group(1))
                    if 'Put' in assignment_desc:
                        print(f"      • Long 100 SPY shares from Put assignment at ${strike:.0f} ({days_ago} day{'s' if days_ago > 1 else ''} ago)")
                    else:
                        print(f"      • Short 100 SPY shares from Call assignment at ${strike:.0f} ({days_ago} day{'s' if days_ago > 1 else ''} ago)")
        # Check for small P&L on no-trade days (like currency adjustments)
        if abs(total_pnl) > 0 and abs(total_pnl) < 1:
            print(f"   Small P&L adjustment of {format_hdk(total_pnl)} (likely currency/rounding)")
        
        # Get all option outcomes for today using our helper function
        option_outcomes = get_option_outcomes_for_date(cursor, summary_date)
        
        # Separate expirations and assignments
        expirations = [o for o in option_outcomes if o['type'] == 'expired']
        assignments_today = [o for o in option_outcomes if o['type'] == 'assigned']
        
        # Display expirations
        if expirations:
            print(f"\n   **Expired Positions:**")
            for exp in sorted(expirations, key=lambda x: (x['option_type'], x['strike'])):
                exp_type = "Put" if exp['option_type'] == "P" else "Call"
                print(f"      • SPY ${exp['strike']:.0f} {exp_type} expired")
        
        # Display assignments
        if assignments_today:
            print(f"\n   **Option Assignments:**")
            for assign in sorted(assignments_today, key=lambda x: (x['option_type'], x['strike'])):
                assign_type = "Put" if assign['option_type'] == "P" else "Call"
                print(f"      • SPY ${assign['strike']:.0f} {assign_type} assigned")
                if assign['option_type'] == "P":
                    print(f"        - Received 100 shares at ${assign['strike']:.0f} per share")
                else:
                    print(f"        - Delivered 100 shares at ${assign['strike']:.0f} per share")
                print(f"        - NAV impact: None (asset exchange only)")
    
    # Day summary
    print(f"\n**Day Summary**")
    
    # Get all P&L components for proper reconciliation
    cursor.execute("""
        SELECT 
            COALESCE(SUM(realized_pnl_hkd), 0) as total_realized_pnl,
            COALESCE(SUM(cash_impact_hkd), 0) as total_cash_impact,
            COALESCE(SUM(ib_commission_hkd), 0) as total_commission,
            COUNT(CASE WHEN event_type = 'Option_Assignment' THEN 1 END) as assignment_count,
            COUNT(CASE WHEN event_type = 'Trade' AND description LIKE '%%SPY%%' 
                      AND description NOT LIKE '%%Option%%' THEN 1 END) as stock_trades
        FROM alm_reporting.chronological_events
        WHERE DATE(event_timestamp AT TIME ZONE 'US/Eastern') = %s
    """, (summary_date,))
    
    day_stats = cursor.fetchone()
    realized_pnl_total = day_stats[0] if day_stats else Decimal(0)
    cash_impact_total = day_stats[1] if day_stats else Decimal(0)
    commission_total = day_stats[2] if day_stats else Decimal(0)
    assignments_today = day_stats[3] if day_stats else 0
    stock_trades_today = day_stats[4] if day_stats else 0
    
    # Calculate return excluding cash flows for true performance
    nav_change = closing_nav - opening_nav - net_cash_flow
    nav_change_pct = (nav_change / opening_nav * 100) if opening_nav != 0 else 0
    
    # Get interest accruals for the day
    interest_data = get_interest_accruals(cursor, summary_date)
    daily_interest = interest_data['daily']
    cumulative_interest = interest_data['cumulative']
    
    # Calculate expected closing NAV with all components
    expected_closing_nav = opening_nav + total_pnl + net_cash_flow
    nav_discrepancy = closing_nav - expected_closing_nav
    
    print(f"   Closing NAV: **{format_hdk(closing_nav)}**")
    
    # Show detailed NAV reconciliation
    if abs(nav_discrepancy) > 0.01:  # Any discrepancy
        print(f"\n   **NAV Reconciliation:**")
        print(f"      Opening NAV: {format_hdk(opening_nav)}")
        print(f"      + Total P&L: {format_hdk(total_pnl)}")
        print(f"      + Net Cash Flow: {format_hdk(net_cash_flow)}")
        print(f"      = Expected NAV: {format_hdk(expected_closing_nav)}")
        print(f"      Actual Closing NAV: {format_hdk(closing_nav)}")
        
        if abs(nav_discrepancy) > 1:  # Significant discrepancy
            print(f"      Discrepancy: {format_hdk(nav_discrepancy)}")
            
            # Check if discrepancy is likely the $1 withdrawal fee
            if 7.5 <= abs(nav_discrepancy) <= 8.5 and net_cash_flow < 0:
                print(f"      *Likely withdrawal fee ($1 USD = ~8 HKD)*")
            # Try to identify other sources
            elif assignments_today > 0 and stock_trades_today > 0:
                print(f"      *Note: {assignments_today} assignment(s) and {stock_trades_today} stock trade(s) today - timing differences may apply*")
            elif daily_interest != 0:
                print(f"      *Note: Interest accrual of {format_hdk(daily_interest)} may not be fully reflected*")
    
    if nav_change_pct >= 0:
        print(f"   Daily Return: **+{nav_change_pct:.2f}%**")
    else:
        print(f"   Daily Return: **{nav_change_pct:.2f}%**")
    
    # Gross P&L
    print(f"   Gross P&L: {format_hdk(total_pnl)}")
    
    # Show interest accruals
    if daily_interest != 0:
        print(f"   Interest Accrued Today: {format_hdk(daily_interest)}")
    if cumulative_interest != 0:
        print(f"   Cumulative Interest Balance: {format_hdk(cumulative_interest)}")
    
    # Commission impact
    commission = get_daily_commission(cursor, summary_date)
    if commission > 0:
        print(f"   Total Commissions: {format_hdk(commission)}")
        net_pnl = total_pnl - commission
        print(f"   Net P&L: {format_hdk(net_pnl)}")
    
    # Net cashflow
    if net_cash_flow != 0:
        if net_cash_flow > 0:
            print(f"   Deposit: +{net_cash_flow:,.0f}")
        else:
            print(f"   Withdrawal: -{abs(net_cash_flow):,.0f}")
    
    # Assignment tracking
    assignment_count = get_daily_assignments(cursor, summary_date)
    if assignment_count > 0:
        print(f"   Assignments Today: {assignment_count}")
    
    # Check for pending assignments (ITM options that may be assigned T+1)
    pending_assignments = check_for_pending_assignments(cursor, summary_date)
    if pending_assignments:
        print(f"\n**Pending Assignments (T+1 Settlement Expected):**")
        for pending in pending_assignments:
            strike = pending['strike']
            option_type = pending['type']
            spy_close = pending['spy_close']
            
            if option_type == 'Call':
                itm_amount = spy_close - strike
                print(f"   • SPY ${strike:.0f} Call is ITM by ${itm_amount:.2f} (SPY closed at ${spy_close:.2f})")
                print(f"     - Expected assignment: Deliver 100 shares at ${strike:.2f}")
                print(f"     - Estimated overnight P&L: **-{format_hdk(itm_amount * 100 * HKD_USD_RATE)}**")
            else:
                itm_amount = strike - spy_close
                print(f"   • SPY ${strike:.0f} Put is ITM by ${itm_amount:.2f} (SPY closed at ${spy_close:.2f})")
                print(f"     - Expected assignment: Receive 100 shares at ${strike:.2f}")
                print(f"     - Estimated overnight P&L if sold at open: Will depend on next day's price")
        
        print(f"\n   *Note: These assignments are expected but not yet confirmed in settlement data.*")

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
    interest_events = get_interest_events_for_period(cursor, period_start, period_end)
    
    pre_market_events = [e for e in all_events if e[0] < market_open_time]
    intraday_events = [e for e in all_events if e[0] >= market_open_time]

    running_nav = Decimal(str(previous_closing_nav))
    assignment_positions = {}  # Track {symbol: {'strike': price, 'quantity': shares, 'timestamp': datetime}}
    overnight_pnl_total = Decimal(0)  # Track total overnight P&L for adjusted NAV
    
    # Process interest events separately to include in NAV
    total_interest_impact = Decimal(0)
    interest_accrual_change = Decimal(0)
    interest_payments = Decimal(0)
    
    for event in interest_events:
        ts, etype, desc, cash, pnl, comm = event
        # For interest accrual changes, use realized_pnl_hkd (no cash impact)
        # For interest payments, use cash_impact_hkd
        if etype == 'Interest_Accrual_Change':
            interest_accrual_change += (pnl or 0)
            total_interest_impact += (pnl or 0)
        elif etype == 'Interest_Payment':
            interest_payments += (cash or 0) + (pnl or 0)
            total_interest_impact += (cash or 0) + (pnl or 0)
    
    # Include interest impact in the running NAV
    running_nav += total_interest_impact
    
    print(f"* **Previous Close ({period_start.astimezone(hkt).strftime('%Y-%m-%d %H:%M:%S HKT')}):**")
    print(f"    * **Starting NAV:** {format_hdk(running_nav - total_interest_impact)}")
    if total_interest_impact != 0:
        print(f"    * **Interest Adjustments:** {format_hdk(total_interest_impact)}")
        if interest_accrual_change != 0:
            print(f"        - Interest Accrual Change: {format_hdk(interest_accrual_change)}")
        if interest_payments != 0:
            print(f"        - Interest Payments: {format_hdk(interest_payments)}")
    print(f"    * **Adjusted Starting NAV:** {format_hdk(running_nav)}\n")

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
            
            print(f"    * **{ts.astimezone(hkt).strftime('%H:%M HKT')}:** {enhance_trade_description(desc, pnl, cash, is_expiration)}")
            
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
        
        print(f"* **Market Open ({market_open_time.astimezone(hkt).strftime('%H:%M HKT')}):**")
        if abs(overnight_pnl_total) > 1:
            print(f"    * **Official Opening NAV:** {format_hdk(opening_nav)}")
            print(f"    * **Adjusted Opening NAV:** {format_hdk(adjusted_opening_nav)} (includes overnight P&L from assignment covers)")
            print(f"    * **Actual NAV:** {format_hdk(running_nav)} (after all pre-market activity)")
        else:
            print(f"    * **Opening NAV:** {format_hdk(opening_nav)}")
    else:
        # First day or no overnight events
        print(f"* **Market Open ({market_open_time.astimezone(hkt).strftime('%H:%M HKT')}):** The day begins.")
        print(f"    * **Opening NAV:** {format_hdk(opening_nav)}")
        running_nav = Decimal(str(opening_nav))  # Use official opening NAV for first day
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
                
                print(f"    * **{first_ts.astimezone(hkt).strftime('%H:%M')} - {last_ts.astimezone(hkt).strftime('%H:%M HKT')}:** Series of {len(group)} trades:")
                
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
                    
                    
                    print(f"    * **{ts.astimezone(hkt).strftime('%H:%M HKT')}:** {enhance_trade_description(desc, pnl, cash, is_expiration)}")
                    
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
    if total_interest_impact != 0:
        print(f"    * **Interest Impact:** {format_hdk(total_interest_impact)}")
        if interest_accrual_change != 0:
            print(f"        - Interest Accrual Change: {format_hdk(interest_accrual_change)}")
        if interest_payments != 0:
            print(f"        - Interest Payments: {format_hdk(interest_payments)}")
    if overnight_pnl_total != 0:
        print(f"    * **Overnight P&L from Previous Day's Assignments:** {format_hdk(overnight_pnl_total)}")
    
    # Include interest impact in final NAV calculation
    final_calculated_nav = opening_nav + (total_pnl or 0) + (net_cash_flow or 0) + total_interest_impact
    discrepancy = final_calculated_nav - closing_nav
    if abs(discrepancy) > 1:
        print(f"    * **Reconciliation Note:** The calculated closing NAV based on daily components (including interest) is {format_hdk(final_calculated_nav)}, showing a discrepancy of {format_hdk(discrepancy)}.")
    
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
                # Skip June 30, 2025 (bad data)
                if summary_date.year == 2025 and summary_date.month == 6 and summary_date.day == 30:
                    continue
                generate_daily_narrative(cursor, summary_date)
        
        conn.close()

if __name__ == "__main__":
    main()