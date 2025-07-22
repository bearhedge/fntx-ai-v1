import os
import sys
import psycopg2

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config.theta_config import DB_CONFIG

def check_available_contracts():
    """Check which SPY contracts have data on Sep 30, 2024"""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        
        # Find contracts with OHLC data on 2024-09-30
        cursor.execute("""
            SELECT DISTINCT 
                oc.contract_id,
                oc.symbol,
                oc.strike,
                oc.option_type,
                oc.expiration,
                COUNT(DISTINCT ohlc.id) as ohlc_records,
                MIN(ohlc.datetime) as first_data,
                MAX(ohlc.datetime) as last_data
            FROM theta.options_contracts oc
            JOIN theta.options_ohlc ohlc ON oc.contract_id = ohlc.contract_id
            WHERE oc.symbol = 'SPY' 
            AND oc.expiration = '2024-09-30'
            AND ohlc.datetime::date = '2024-09-30'
            GROUP BY oc.contract_id, oc.symbol, oc.strike, oc.option_type, oc.expiration
            ORDER BY oc.strike, oc.option_type;
        """)
        
        contracts = cursor.fetchall()
        
        print(f"SPY contracts with data on Sep 30, 2024:")
        print(f"{'Contract ID':<12} {'Strike':<8} {'Type':<6} {'Records':<10} {'First Data':<20} {'Last Data':<20}")
        print("-" * 80)
        
        for contract in contracts:
            print(f"{contract[0]:<12} ${contract[2]:<7.0f} {contract[3]:<6} {contract[5]:<10} {str(contract[6]):<20} {str(contract[7]):<20}")
        
        # Check all available strikes for calls expiring 2024-09-30
        cursor.execute("""
            SELECT strike, COUNT(*) as count
            FROM theta.options_contracts
            WHERE symbol = 'SPY' 
            AND option_type = 'C'
            AND expiration = '2024-09-30'
            GROUP BY strike
            ORDER BY strike;
        """)
        
        strikes = cursor.fetchall()
        print(f"\n\nAll available Call strikes expiring 2024-09-30:")
        print("Strikes:", [f"${s[0]}" for s in strikes])
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_available_contracts()