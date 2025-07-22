#!/usr/bin/env python3
"""
Quick summary of December 2022 data
"""
import psycopg2
import sys

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Just count records
cur.execute("""
SELECT 
    'OHLC' as type, COUNT(*) as count 
FROM theta.options_ohlc 
WHERE datetime >= '2022-12-01' AND datetime < '2023-01-01'
UNION ALL
SELECT 
    'Greeks', COUNT(*) 
FROM theta.options_greeks 
WHERE datetime >= '2022-12-01' AND datetime < '2023-01-01'
UNION ALL
SELECT 
    'IV', COUNT(*) 
FROM theta.options_iv 
WHERE datetime >= '2022-12-01' AND datetime < '2023-01-01'
""")

print("December 2022 Data Summary:")
print("-"*30)
for typ, count in cur.fetchall():
    print(f"{typ}: {count:,} records")

cur.close()
conn.close()