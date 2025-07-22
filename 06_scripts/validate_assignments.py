

import pandas as pd
from sqlalchemy import create_engine, text
import logging

# --- Configuration ---
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

DATABASE_URL = "postgresql://info:your_password@localhost:5432/options_data"

def validate_assignments(db_url: str):
    """
    Connects to the database and validates the outcome of all closed option positions.

    It checks for the definitive 'BookTrade' patterns to categorize each
    option's closure as either 'Expired' or 'Assigned'.
    """
    try:
        engine = create_engine(db_url)
        with engine.connect() as connection:
            logging.info("Successfully connected to the database.")

            # Query to get all closed option positions (identified by a BookTrade)
            # and all stock BookTrades which signify assignment.
            sql_query = """
            SELECT
                trade_date,
                symbol,
                quantity,
                trade_price,
                transaction_type,
                option_type,
                strike_price
            FROM
                portfolio.trades
            WHERE
                transaction_type = 'BookTrade'
            ORDER BY
                trade_date, symbol;
            """
            df = pd.read_sql(text(sql_query), connection)
            logging.info(f"Retrieved {len(df)} BookTrade transactions for analysis.")

    except Exception as e:
        logging.error(f"Database connection or query failed: {e}")
        return

    # Separate options from the underlying stock trades
    options_df = df[df['symbol'] != 'SPY'].copy()
    stock_assignments_df = df[df['symbol'] == 'SPY'].copy()

    results = []

    # Iterate through each closed option position to validate its outcome
    for index, option_trade in options_df.iterrows():
        trade_date = option_trade['trade_date']
        strike_price = option_trade['strike_price']
        
        # Check for a corresponding stock assignment on the same day at the strike price
        matching_assignment = stock_assignments_df[
            (stock_assignments_df['trade_date'] == trade_date) &
            (stock_assignments_df['trade_price'] == strike_price)
        ]

        outcome = "Expired"
        if not matching_assignment.empty:
            outcome = "Assigned"

        results.append({
            "Trade Date": trade_date.strftime('%Y-%m-%d'),
            "Contract": option_trade['symbol'],
            "Strike": strike_price,
            "Type": option_trade['option_type'],
            "Outcome": outcome
        })

    # --- Generate and Print the Report ---
    if not results:
        print("No closed option positions found to validate.")
        return
        
    report_df = pd.DataFrame(results)
    # Remove duplicates to show one outcome per contract per day
    report_df.drop_duplicates(inplace=True)

    print("\n--- Option Expiration & Assignment Validation Report ---")
    print(report_df.to_string(index=False))
    print("\n--- End of Report ---")


if __name__ == '__main__':
    validate_assignments(DATABASE_URL)

