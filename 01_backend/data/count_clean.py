#!/usr/bin/env python3
"""
Just count the clean data we should have
"""
import psycopg2
import sys

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

print("COUNTING CLEAN 0DTE DATA")
print("="*40)

# Count clean OHLC
cursor.execute("""
SELECT COUNT(*)
FROM theta.options_ohlc o
JOIN theta.options_contracts oc ON o.contract_id = oc.contract_id
WHERE oc.contract_id BETWEEN 117799 AND 119374
  AND oc.symbol = 'SPY'
  AND o.datetime >= '2022-12-01' 
  AND o.datetime < '2023-01-01'
  AND oc.expiration = o.datetime::date
""")
clean_ohlc = cursor.fetchone()[0]

# Count clean Greeks (excluding 16:00)
cursor.execute("""
SELECT COUNT(*)
FROM theta.options_greeks g
JOIN theta.options_contracts oc ON g.contract_id = oc.contract_id
WHERE oc.contract_id BETWEEN 117799 AND 119374
  AND oc.symbol = 'SPY'
  AND g.datetime >= '2022-12-01' 
  AND g.datetime < '2023-01-01'
  AND g.datetime::time != '16:00:00'
  AND oc.expiration = g.datetime::date
""")
clean_greeks = cursor.fetchone()[0]

# Count clean IV
cursor.execute("""  
SELECT COUNT(*)
FROM theta.options_iv i
JOIN theta.options_contracts oc ON i.contract_id = oc.contract_id
WHERE oc.contract_id BETWEEN 117799 AND 119374
  AND oc.symbol = 'SPY'
  AND i.datetime >= '2022-12-01' 
  AND i.datetime < '2023-01-01'
  AND oc.expiration = i.datetime::date
""")
clean_iv = cursor.fetchone()[0]

print(f"Clean OHLC: {clean_ohlc:,}")
print(f"Clean Greeks: {clean_greeks:,}")
print(f"Clean IV: {clean_iv:,}")

expected = 1576 * 78
print(f"\nExpected: {expected:,}")
print(f"OHLC: {clean_ohlc/expected*100:.1f}%")
print(f"Greeks: {clean_greeks/expected*100:.1f}%")  
print(f"IV: {clean_iv/expected*100:.1f}%")

cursor.close()
conn.close()