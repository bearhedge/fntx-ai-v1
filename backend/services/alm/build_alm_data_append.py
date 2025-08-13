import pandas as pd
from sqlalchemy import create_engine, text
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, time
import argparse
import pytz
from spy_price_fetcher import get_spy_closing_price

# --- Configuration ---
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
DATABASE_URL = "postgresql://postgres:theta_data_2024@localhost:5432/options_data"
DEFAULT_DATA_DIR = "/home/info/fntx-ai-v1/database/ibkr/data"
HKD_USD_RATE = 7.8472

def get_newest_xml_files(directory, file_type_prefix):
    """Finds the most recent XML file for a given type."""
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.startswith(file_type_prefix) and f.endswith(".xml")]
    if not files:
        return None
    return max(files, key=os.path.getmtime)

def check_itm_options_for_assignment(trades_tree, exercises_tree, target_date):
    """
    Check for options that expired ITM and assume assignment if not found in exercises.
    Returns a list of assumed assignment events.
    """
    assumed_assignments = []
    
    # First, collect all actual assignments AND expirations from exercises_tree
    actual_assignments = set()
    actual_expirations = set()
    if exercises_tree:
        for statement in exercises_tree.findall(".//FlexStatement"):
            for opt_event in statement.findall(".//OptionEAE"):
                trans_type = opt_event.get('transactionType')
                symbol = opt_event.get('symbol')
                date = opt_event.get('date')
                
                if trans_type == 'Assignment':
                    actual_assignments.add((symbol, date))
                elif trans_type == 'Expiration':
                    actual_expirations.add((symbol, date))
    
    logging.info(f"Found {len(actual_assignments)} actual assignments and {len(actual_expirations)} actual expirations from IBKR")
    
    # Get SPY closing price for the target date from Yahoo Finance
    target_date_str = target_date.strftime("%Y%m%d")
    spy_close_price = get_spy_closing_price(target_date)
    
    if spy_close_price is None:
        logging.warning(f"Could not fetch SPY closing price from Yahoo Finance for {target_date}")
        return assumed_assignments
    
    logging.info(f"Using SPY closing price from Yahoo Finance for {target_date_str}: ${spy_close_price:.2f}")
    
    # Track short option positions
    short_options = {}  # symbol -> (quantity, strike, putCall, expiry)
    all_trades = trades_tree.findall(".//Trade")
    
    for trade in all_trades:
        attribs = trade.attrib
        symbol = attribs.get('symbol', '')
        
        # Check if it's an option trade
        if not any(x in symbol for x in ['C00', 'P00']):
            continue
            
        # Get trade details
        quantity = int(attribs.get('quantity', 0))
        expiry = attribs.get('expiry', '')
        
        # Track net position
        if symbol in short_options:
            short_options[symbol] = (
                short_options[symbol][0] + quantity,
                attribs.get('strike', 0),
                attribs.get('putCall', ''),
                expiry,
                float(attribs.get('closePrice', 0))
            )
        else:
            short_options[symbol] = (
                quantity,
                attribs.get('strike', 0),
                attribs.get('putCall', ''),
                expiry,
                float(attribs.get('closePrice', 0))
            )
    
    # Check for options expiring on target_date that are short and ITM
    for symbol, (net_qty, strike, put_call, expiry, close_price) in short_options.items():
        # Skip if not short or not expiring on target date
        if net_qty >= 0 or expiry != target_date_str:
            continue
            
        # Skip if already have actual assignment
        if (symbol, target_date_str) in actual_assignments:
            continue
            
        # Check if ITM based on actual SPY price
        strike_float = float(strike)
        is_itm = False
        
        if put_call == 'C':
            # Call is ITM if SPY price > strike
            is_itm = spy_close_price > strike_float
            # Also check if near-the-money (within $5) and has significant close price
            near_money = abs(spy_close_price - strike_float) < 5.0 and close_price > 0.15
        else:
            # Put is ITM if SPY price < strike
            is_itm = spy_close_price < strike_float
            # Also check if near-the-money (within $5) and has significant close price
            near_money = abs(spy_close_price - strike_float) < 5.0 and close_price > 0.15
        
        # For OTM options that closed at zero, create expiration event
        if close_price == 0 and not is_itm:
            # Skip if IBKR already has this expiration
            if (symbol, target_date_str) in actual_expirations:
                logging.info(f"Skipping synthetic expiration for {symbol} - IBKR data exists")
                continue
                
            # Create expiration event for OTM option
            naive_dt = datetime.strptime(f"{target_date_str} 16:20:00", "%Y%m%d %H:%M:%S")
            edt = pytz.timezone('US/Eastern')
            event_ts = edt.localize(naive_dt)
            
            # Get premium collected from selling this option
            premium_collected = 0
            for trade in all_trades:
                if trade.attrib.get('symbol') == symbol:
                    qty = int(trade.attrib.get('quantity', 0))
                    if qty < 0:  # Selling
                        premium_collected += abs(float(trade.attrib.get('proceeds', 0))) * HKD_USD_RATE
            
            expiry_event = {
                'event_timestamp': event_ts,
                'event_type': 'Option_Expiration',
                'description': f"{symbol} Expiration @ ${strike} (OTM {put_call}, SPY@${spy_close_price:.2f}) [SYNTHETIC]",
                'cash_impact_hkd': 0,
                'realized_pnl_hkd': 0,
                'ib_commission_hkd': 0,
                'source_transaction_id': f"EXPIRY_{symbol}_{target_date_str}",
                'is_synthetic': True
            }
            assumed_assignments.append(expiry_event)
            
            # Also create the Buy @ 0 trade that indicates expiration
            buy_event = {
                'event_timestamp': event_ts,
                'event_type': 'Trade',
                'description': f"Buy {abs(net_qty)} {symbol} @ 0 [SYNTHETIC]",
                'cash_impact_hkd': 0,
                'realized_pnl_hkd': premium_collected,  # The premium we collected when selling
                'ib_commission_hkd': 0,
                'source_transaction_id': f"BUY_EXPIRY_{symbol}_{target_date_str}",
                'is_synthetic': True
            }
            assumed_assignments.append(buy_event)
            continue
        
        if is_itm or near_money:
            # Skip if IBKR already has assignment or expiration for this option
            if (symbol, target_date_str) in actual_assignments or (symbol, target_date_str) in actual_expirations:
                logging.info(f"Skipping assumed assignment for {symbol} - IBKR data exists")
                continue
                
            status = "ITM" if is_itm else "Near-the-money"
            logging.info(f"Assuming assignment for {status} option {symbol}: SPY@${spy_close_price:.2f}, Strike=${strike_float}, {put_call}, Close=${close_price}")
            
            # Create assumed assignment event
            naive_dt = datetime.strptime(f"{target_date_str} 16:20:00", "%Y%m%d %H:%M:%S")
            # Add EDT timezone
            edt = pytz.timezone('US/Eastern')
            event_ts = edt.localize(naive_dt)
            
            # Calculate assumed P&L based on SPY closing price
            if put_call == 'C':
                # Call assignment - forced to sell at strike when market is higher
                # Loss = (market price - strike) * 100 * quantity
                description = f"{symbol} Assignment @ ${strike} (ITM Call, SPY@${spy_close_price:.2f}) [SYNTHETIC]"
                assumed_pnl = (strike_float - spy_close_price) * 100 * abs(net_qty) * HKD_USD_RATE
            else:
                # Put assignment - forced to buy at strike when market is lower
                # Loss = (strike - market price) * 100 * quantity
                description = f"{symbol} Assignment @ ${strike} (ITM Put, SPY@${spy_close_price:.2f}) [SYNTHETIC]"
                assumed_pnl = (spy_close_price - strike_float) * 100 * abs(net_qty) * HKD_USD_RATE
            
            event = {
                'event_timestamp': event_ts,
                'event_type': 'Option_Assignment_Assumed',
                'description': description,
                'cash_impact_hkd': 0,  # Cash impact from stock trade
                'realized_pnl_hkd': assumed_pnl,
                'ib_commission_hkd': 0,
                'source_transaction_id': f"ASSUMED_{symbol}_{target_date_str}",
                'option_symbol': symbol,
                'strike': strike_float,
                'put_call': put_call,
                'quantity': abs(net_qty),
                'is_synthetic': True
            }
            assumed_assignments.append(event)
            
            # Also create the assumed stock transaction
            stock_qty = abs(net_qty) * 100
            if put_call == 'C':
                # Call assigned - we deliver (sell) stock
                stock_event = {
                    'event_timestamp': event_ts,
                    'event_type': 'Trade',
                    'description': f"SPY Delivery (Call Assignment) @ ${strike} [SYNTHETIC]",
                    'cash_impact_hkd': stock_qty * strike_float * HKD_USD_RATE,
                    'realized_pnl_hkd': 0,
                    'ib_commission_hkd': 0,
                    'source_transaction_id': f"ASSUMED_STOCK_{symbol}_{target_date_str}"
                }
            else:
                # Put assigned - we receive (buy) stock
                stock_event = {
                    'event_timestamp': event_ts,
                    'event_type': 'Trade',
                    'description': f"SPY Receipt (Put Assignment) @ ${strike} [SYNTHETIC]",
                    'cash_impact_hkd': -stock_qty * strike_float * HKD_USD_RATE,
                    'realized_pnl_hkd': 0,
                    'ib_commission_hkd': 0,
                    'source_transaction_id': f"ASSUMED_STOCK_{symbol}_{target_date_str}"
                }
            assumed_assignments.append(stock_event)
    
    # Count synthetic events created
    synthetic_expirations = len([e for e in assumed_assignments if e['event_type'] == 'Option_Expiration'])
    synthetic_assignments = len([e for e in assumed_assignments if 'Option_Assignment' in e['event_type']])
    
    if synthetic_expirations > 0 or synthetic_assignments > 0:
        logging.info(f"Created {synthetic_expirations} synthetic expirations and {synthetic_assignments} synthetic assignments")
    
    return assumed_assignments

def parse_and_insert_data(db_url: str, append: bool, data_dir: str = None):
    """Parses financial data from the latest XML files and inserts into the database."""
    engine = create_engine(db_url)
    
    if data_dir is None:
        data_dir = DEFAULT_DATA_DIR
    
    if not append:
        logging.warning("Running in non-append mode. This will clear existing data.")
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("TRUNCATE TABLE alm_reporting.chronological_events, alm_reporting.daily_summary RESTART IDENTITY;"))

    # Define file prefixes
    file_prefixes = {
        "Trades": "Trades_",
        "Cash_Transactions": "Cash_Transactions_",
        "NAV": "NAV_",
        "Exercises_and_Expiries": "Exercises_and_Expiries_",
        "Interest_Accruals": "Interest_Accruals_"
    }

    # Get latest files
    trade_file = get_newest_xml_files(data_dir, file_prefixes["Trades"])
    cash_file = get_newest_xml_files(data_dir, file_prefixes["Cash_Transactions"])
    nav_file = get_newest_xml_files(data_dir, file_prefixes["NAV"])
    exercises_file = get_newest_xml_files(data_dir, file_prefixes["Exercises_and_Expiries"])
    interest_file = get_newest_xml_files(data_dir, file_prefixes["Interest_Accruals"])

    if not all([trade_file, cash_file, nav_file]):
        logging.error("Core XML files (Trades, Cash, NAV) are missing. Aborting.")
        return
    
    # Log if optional files are missing but continue
    if not exercises_file:
        logging.warning("Exercises and Expiries file not found, continuing without it")
    if not interest_file:
        logging.warning("Interest Accruals file not found, continuing without it")

    logging.info(f"Processing trade file: {trade_file}")
    logging.info(f"Processing cash transaction file: {cash_file}")
    logging.info(f"Processing NAV file: {nav_file}")
    if exercises_file:
        logging.info(f"Processing exercises and expiries file: {exercises_file}")
    if interest_file:
        logging.info(f"Processing interest accruals file: {interest_file}")

    # --- Process Trades ---
    trades_tree = ET.parse(trade_file)
    all_trades = trades_tree.findall(".//Trade")
    
    events_to_insert = []
    for trade in all_trades:
        attribs = trade.attrib
        
        # Skip trades without tradeDate (e.g., summary records)
        trade_date = attribs.get('tradeDate')
        if not trade_date:
            continue
            
        # Handle dateTime field if present, otherwise use tradeDate + default time
        date_time = attribs.get('dateTime')
        if date_time:
            # Format: "20250701;121417 EDT"
            dt_parts = date_time.split()  # ["20250701;121417", "EDT"]
            naive_dt = datetime.strptime(dt_parts[0], "%Y%m%d;%H%M%S")
            # Add EDT timezone - this is critical for correct time conversion!
            edt = pytz.timezone('US/Eastern')
            event_ts = edt.localize(naive_dt)
        else:
            trade_time = attribs.get('tradeTime', '16:00:00')
            naive_dt = datetime.strptime(f"{trade_date} {trade_time}", "%Y%m%d %H:%M:%S")
            # Assume EDT timezone for trades without explicit timezone
            edt = pytz.timezone('US/Eastern')
            event_ts = edt.localize(naive_dt)
        
        pnl = float(attribs.get('fifoPnlRealized', 0))
        commission = float(attribs.get('ibCommission', 0))
        
        # Build a better description for trades
        description = attribs.get('description', '')
        symbol = attribs.get('symbol', '')
        quantity = int(attribs.get('quantity', 0))
        
        # If description is incomplete (e.g., just "SPDR S&P 500 ETF TRUST"), build a better one
        if description and ('Buy' not in description and 'Sell' not in description) and quantity != 0:
            # Determine action based on quantity sign
            action = 'Buy' if quantity > 0 else 'Sell'
            abs_quantity = abs(quantity)
            
            # For stock trades, use symbol if available
            if symbol and symbol != description:
                description = f"{action} {abs_quantity} {symbol}"
            else:
                # Try to extract symbol from description
                if 'SPY' in description or 'SPDR' in description:
                    description = f"{action} {abs_quantity} SPY"
                else:
                    description = f"{action} {abs_quantity} {description}"
            
            # Add price if available
            trade_price = attribs.get('tradePrice')
            if trade_price:
                description += f" @ {trade_price}"
        
        event = {
            'event_timestamp': event_ts,
            'event_type': 'Trade',
            'description': description,
            'cash_impact_hkd': (float(attribs.get('proceeds', 0)) + commission) * HKD_USD_RATE,
            'realized_pnl_hkd': pnl * HKD_USD_RATE,
            'ib_commission_hkd': commission * HKD_USD_RATE,
            'source_transaction_id': attribs.get('transactionID')
        }
        events_to_insert.append(event)

    # --- Process Cash Transactions ---
    cash_tree = ET.parse(cash_file)
    
    # Process each FlexStatement in the cash file
    for statement in cash_tree.findall(".//FlexStatement"):
        report_date = statement.get('toDate')  # Use the statement date
        if not report_date:
            continue
            
        # Find all cash transactions within this statement
        cash_trans = statement.findall(".//CashTransaction")
        
        for trans in cash_trans:
            attribs = trans.attrib
            # Skip trades, as they are handled separately
            if attribs.get('type') == 'Trade':
                continue
                
            # Use report date with time based on transaction type
            # For deposits: assume 8:00 AM ET (before market open)
            # For withdrawals: assume 4:00 PM ET (after market close)
            if attribs.get('type') == 'Deposits/Withdrawals':
                amount = float(attribs.get('amount', 0))
                if amount > 0:  # Deposit
                    naive_dt = datetime.strptime(f"{report_date} 08:00:00", "%Y%m%d %H:%M:%S")
                else:  # Withdrawal
                    naive_dt = datetime.strptime(f"{report_date} 16:00:00", "%Y%m%d %H:%M:%S")
            else:
                naive_dt = datetime.strptime(f"{report_date} 16:00:00", "%Y%m%d %H:%M:%S")
            # Add EDT timezone
            edt = pytz.timezone('US/Eastern')
            event_ts = edt.localize(naive_dt)
            
            # Check currency to avoid double conversion
            currency = attribs.get('currency', 'USD')
            amount = float(attribs.get('amount', 0))
            
            event = {
                'event_timestamp': event_ts,
                'event_type': attribs.get('type'),
                'description': attribs.get('description'),
                'cash_impact_hkd': amount if currency == 'HKD' else amount * HKD_USD_RATE,
                'realized_pnl_hkd': 0,
                'ib_commission_hkd': 0,
                'source_transaction_id': attribs.get('transactionID')
            }
            events_to_insert.append(event)
    
    # --- Process Exercises and Expiries ---
    if exercises_file:
        try:
            exercises_tree = ET.parse(exercises_file)
            
            # Track processed events to avoid duplicates
            processed_events = set()
            
            # Process each FlexStatement in the exercises file
            for statement in exercises_tree.findall(".//FlexStatement"):
                report_date = statement.get('toDate')
                if not report_date:
                    continue
                    
                # Find all OptionEAE (Option Exercise/Assignment/Expiration) entries
                option_events = statement.findall(".//OptionEAE")
                
                for i, opt_event in enumerate(option_events):
                    attribs = opt_event.attrib
                    
                    # Get the transaction type - Exercise, Assignment, or Expiration
                    trans_type = attribs.get('transactionType', '')
                    if trans_type not in ['Exercise', 'Assignment', 'Expiration']:
                        continue
                    
                    # Parse date and time
                    event_date = attribs.get('date', report_date)
                    # Set assignment time to 4:30 PM EDT (after market close)
                    event_date_obj = datetime.strptime(event_date, "%Y%m%d")
                    naive_dt = datetime.combine(event_date_obj, datetime.strptime("16:30:00", "%H:%M:%S").time())
                    # Add EDT timezone
                    edt = pytz.timezone('US/Eastern')
                    event_ts = edt.localize(naive_dt)
                    
                    # Create unique key for this event
                    trade_id = attribs.get('tradeID', '')
                    event_key = (attribs.get('symbol'), event_date, trans_type, trade_id)
                    
                    # Skip if we've already processed this event
                    if event_key in processed_events:
                        logging.info(f"Skipping duplicate {trans_type} event: {attribs.get('symbol')} on {event_date}")
                        continue
                    processed_events.add(event_key)
                    
                    # Calculate cash impact and P&L
                    quantity = int(attribs.get('quantity', 0))
                    strike = float(attribs.get('strike', 0))
                    cash_impact = 0
                    realized_pnl = 0
                    
                    if trans_type in ['Exercise', 'Assignment'] and strike > 0:
                        # Look for the next OptionEAE entry which should be the stock transaction
                        if i + 1 < len(option_events):
                            next_event = option_events[i + 1]
                            next_attribs = next_event.attrib
                            
                            # Check if this is the corresponding stock transaction
                            if next_attribs.get('transactionType') in ['Buy', 'Sell']:
                                stock_price = float(next_attribs.get('tradePrice', 0))
                                market_price = float(next_attribs.get('markPrice', 0))
                                stock_quantity = int(next_attribs.get('quantity', 0))
                                
                                # Use market price if available, otherwise use trade price
                                reference_price = market_price if market_price > 0 else stock_price
                                
                                # For puts assigned: loss = (strike - market_price) * quantity * 100
                                # For calls assigned: loss = (market_price - strike) * quantity * 100
                                if attribs.get('putCall') == 'P':
                                    # Put assignment - we're forced to buy above market
                                    realized_pnl = (reference_price - strike) * abs(stock_quantity) * HKD_USD_RATE
                                elif attribs.get('putCall') == 'C':
                                    # Call assignment - we're forced to sell below market
                                    realized_pnl = (strike - reference_price) * abs(stock_quantity) * HKD_USD_RATE
                                
                                # For assignments, we don't record cash impact here - it comes from the stock trade
                                cash_impact = 0  # The cash impact comes from the actual stock buy/sell
                                
                                logging.info(f"Assignment P&L for {attribs.get('symbol')}: "
                                           f"Strike=${strike}, Market=${reference_price}, "
                                           f"P&L={realized_pnl/HKD_USD_RATE:.2f} USD")
                    
                    # Use tradeID if transactionID is not available (common for assignments)
                    transaction_id = attribs.get('transactionID') or attribs.get('tradeID')
                    
                    event = {
                        'event_timestamp': event_ts,
                        'event_type': f'Option_{trans_type}',
                        'description': f"{attribs.get('symbol')} {trans_type} @ ${strike}",
                        'cash_impact_hkd': cash_impact,
                        'realized_pnl_hkd': realized_pnl,
                        'ib_commission_hkd': 0,
                        'source_transaction_id': transaction_id
                    }
                    events_to_insert.append(event)
                    
        except Exception as e:
            logging.error(f"Error processing exercises and expiries: {e}")
    
    # --- Process Interest Accruals ---
    if interest_file:
        try:
            interest_tree = ET.parse(interest_file)
            
            # Process each FlexStatement in the interest file
            for statement in interest_tree.findall(".//FlexStatement"):
                # Find InterestAccruals section
                for accrual in statement.findall(".//InterestAccrual"):
                    attribs = accrual.attrib
                    
                    # Get date range for the accrual
                    to_date = attribs.get('toDate')
                    if not to_date:
                        continue
                    
                    # Use the end date for the event
                    naive_dt = datetime.strptime(f"{to_date} 16:00:00", "%Y%m%d %H:%M:%S")
                    # Add EDT timezone
                    edt = pytz.timezone('US/Eastern')
                    event_ts = edt.localize(naive_dt)
                    
                    # Get interest accrued amount
                    interest_amount = float(attribs.get('interestAccrued', 0))
                    
                    if interest_amount != 0:  # Only record if there's actual interest
                        event = {
                            'event_timestamp': event_ts,
                            'event_type': 'Interest_Accrual',
                            'description': f"Interest accrued in {attribs.get('currencyPrimary', 'USD')}",
                            'cash_impact_hkd': interest_amount * HKD_USD_RATE,
                            'realized_pnl_hkd': 0,
                            'ib_commission_hkd': 0,
                            'source_transaction_id': f"INT_{to_date}_{attribs.get('currencyPrimary', 'USD')}"
                        }
                        events_to_insert.append(event)
                        
        except Exception as e:
            logging.error(f"Error processing interest accruals: {e}")
    
    # --- Check for ITM options that should be assumed as assigned ---
    # Get the date we're processing (use the most recent date from events)
    if events_to_insert:
        dates_in_events = [e['event_timestamp'].date() for e in events_to_insert]
        most_recent_date = max(dates_in_events)
        
        # Check for ITM options on the most recent date
        logging.info(f"Checking for ITM options on {most_recent_date} that may have been assigned...")
        assumed_assignments = check_itm_options_for_assignment(
            trades_tree, 
            exercises_tree if exercises_file else None, 
            most_recent_date
        )
        
        if assumed_assignments:
            logging.info(f"Found {len(assumed_assignments)} assumed assignment events")
            events_to_insert.extend(assumed_assignments)
    
    logging.info(f"Found a total of {len(events_to_insert)} events in the XML files.")

    # Store initial events for later insertion after we generate interest events
    initial_events = events_to_insert.copy()

    # --- Update Daily Summaries ---
    logging.info("Calculating and updating daily summaries.")
    
    # Process daily summaries even if no events to get NAV data
    if initial_events:
        df = pd.DataFrame(initial_events)
    else:
        # Create empty DataFrame with required columns
        df = pd.DataFrame(columns=['event_timestamp', 'event_type', 'cash_impact_hkd', 'realized_pnl_hkd'])
    
    if True:  # Always process to get NAV data
        df['date'] = pd.to_datetime(df['event_timestamp']).dt.date
        
        # Log the date range of events found
        min_date = df['date'].min()
        max_date = df['date'].max()
        logging.info(f"Date range of events found in XML: {min_date} to {max_date}")

        # Aggregate financial data from events
        # First calculate total P&L
        summary_agg = df.groupby('date').agg(
            total_pnl_hkd=('realized_pnl_hkd', 'sum')
        ).reset_index()
        
        # Calculate net cash flow separately - only from Deposits/Withdrawals
        cash_flow_df = df[df['event_type'] == 'Deposits/Withdrawals'].groupby('date').agg(
            net_cash_flow_hkd=('cash_impact_hkd', 'sum')
        ).reset_index()
        
        # Merge the aggregations
        summary_agg = summary_agg.merge(cash_flow_df, on='date', how='left')
        summary_agg['net_cash_flow_hkd'] = summary_agg['net_cash_flow_hkd'].fillna(0)

        # Get NAV data from all FlexStatements in the NAV file
        nav_tree = ET.parse(nav_file)
        nav_data = {}
        
        # Process each FlexStatement to get daily NAV values
        for statement in nav_tree.findall(".//FlexStatement"):
            change_in_nav = statement.find(".//ChangeInNAV")
            if change_in_nav is not None:
                statement_date = statement.get('toDate')
                if statement_date:
                    nav_date = datetime.strptime(statement_date, "%Y%m%d").date()
                    
                    # Calculate total P&L from all components
                    mtm = float(change_in_nav.get('mtm', 0))
                    realized = float(change_in_nav.get('realized', 0))
                    interest = float(change_in_nav.get('interest', 0))
                    change_in_interest_accruals = float(change_in_nav.get('changeInInterestAccruals', 0))
                    commissions = float(change_in_nav.get('commissions', 0))
                    
                    # Total P&L includes all components
                    total_nav_pnl = mtm + realized + interest + change_in_interest_accruals + commissions
                    
                    nav_data[nav_date] = {
                        'opening_nav_hkd': float(change_in_nav.get('startingValue', 0)),
                        'closing_nav_hkd': float(change_in_nav.get('endingValue', 0)),
                        'nav_calculated_pnl': total_nav_pnl,
                        'mtm': mtm,
                        'realized': realized,
                        'interest': interest,
                        'change_in_interest_accruals': change_in_interest_accruals,
                        'commissions': commissions
                    }
        
        # Merge NAV data with summary aggregates
        summary_agg = summary_agg.rename(columns={'date': 'summary_date'})
        
        # Add NAV data for each date
        for idx, row in summary_agg.iterrows():
            date_val = row['summary_date']
            if date_val in nav_data:
                summary_agg.at[idx, 'opening_nav_hkd'] = nav_data[date_val]['opening_nav_hkd']
                summary_agg.at[idx, 'closing_nav_hkd'] = nav_data[date_val]['closing_nav_hkd']
                # Use the NAV-calculated P&L which includes MTM, interest accruals, etc.
                summary_agg.at[idx, 'total_pnl_hkd'] = nav_data[date_val]['nav_calculated_pnl']
                
                # Also generate interest-related events
                nav_info = nav_data[date_val]
                naive_dt = datetime.combine(date_val, datetime.min.time()).replace(hour=16)
                # Add EDT timezone
                edt = pytz.timezone('US/Eastern')
                event_ts = edt.localize(naive_dt)
                
                # Generate event for interest payments
                if nav_info['interest'] != 0:
                    interest_event = {
                        'event_timestamp': event_ts,
                        'event_type': 'Interest_Payment',
                        'description': 'Interest paid/received',
                        'cash_impact_hkd': nav_info['interest'] * HKD_USD_RATE,
                        'realized_pnl_hkd': nav_info['interest'] * HKD_USD_RATE,
                        'ib_commission_hkd': 0,
                        'source_transaction_id': f"INT_PAID_{date_val.strftime('%Y%m%d')}"
                    }
                    events_to_insert.append(interest_event)
                
                # Generate event for interest accrual changes
                if nav_info['change_in_interest_accruals'] != 0:
                    accrual_event = {
                        'event_timestamp': event_ts,
                        'event_type': 'Interest_Accrual_Change',
                        'description': f"Change in interest accruals: {nav_info['change_in_interest_accruals'] * HKD_USD_RATE:.2f} HKD",
                        'cash_impact_hkd': 0,  # Accruals don't impact cash
                        'realized_pnl_hkd': nav_info['change_in_interest_accruals'] * HKD_USD_RATE,  # Include in P&L
                        'ib_commission_hkd': 0,
                        'source_transaction_id': f"INT_ACCRUAL_{date_val.strftime('%Y%m%d')}"
                    }
                    events_to_insert.append(accrual_event)
            else:
                logging.warning(f"No NAV data found for date {date_val}")
                summary_agg.at[idx, 'opening_nav_hkd'] = 0
                summary_agg.at[idx, 'closing_nav_hkd'] = 0
        
        logging.info(f"Calculated summary data for {len(summary_agg)} dates")

        # Insert or update the summary table for all dates
        with engine.connect() as connection:
            with connection.begin():
                for _, row in summary_agg.iterrows():
                    upsert_sql = text("""
                        INSERT INTO alm_reporting.daily_summary (
                            summary_date, opening_nav_hkd, closing_nav_hkd, 
                            total_pnl_hkd, net_cash_flow_hkd
                        ) VALUES (
                            :summary_date, :opening_nav_hkd, :closing_nav_hkd, 
                            :total_pnl_hkd, :net_cash_flow_hkd
                        )
                        ON CONFLICT (summary_date) DO UPDATE SET
                            opening_nav_hkd = EXCLUDED.opening_nav_hkd,
                            closing_nav_hkd = EXCLUDED.closing_nav_hkd,
                            total_pnl_hkd = EXCLUDED.total_pnl_hkd,
                            net_cash_flow_hkd = EXCLUDED.net_cash_flow_hkd,
                            last_updated = CURRENT_TIMESTAMP;
                    """)
                    connection.execute(upsert_sql, row.to_dict())
                logging.info(f"Upserted daily summaries for {len(summary_agg)} dates")
                
    # Now insert all events including interest events
    if events_to_insert:
        # Ensure all events have is_synthetic field
        for event in events_to_insert:
            if 'is_synthetic' not in event:
                event['is_synthetic'] = False
                
        with engine.connect() as connection:
            with connection.begin():
                insert_sql = text("""
                    INSERT INTO alm_reporting.chronological_events (
                        event_timestamp, event_type, description, cash_impact_hkd, 
                        realized_pnl_hkd, ib_commission_hkd, source_transaction_id, is_synthetic
                    ) VALUES (
                        :event_timestamp, :event_type, :description, :cash_impact_hkd, 
                        :realized_pnl_hkd, :ib_commission_hkd, :source_transaction_id,
                        COALESCE(:is_synthetic, FALSE)
                    )
                    ON CONFLICT (source_transaction_id) DO NOTHING;
                """)
                result = connection.execute(insert_sql, events_to_insert)
                logging.info(f"Successfully inserted {result.rowcount} new events (including interest) into the database.")

    logging.info("Append-mode data build process completed.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build ALM data, with an option for append-only.')
    parser.add_argument('--append', action='store_true', help='Run in append-only mode, ignoring duplicates.')
    parser.add_argument('--data-dir', type=str, help='Directory containing XML data files')
    args = parser.parse_args()
    
    parse_and_insert_data(DATABASE_URL, args.append, args.data_dir)
