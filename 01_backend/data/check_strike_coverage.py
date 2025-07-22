#!/usr/bin/env python3
"""Check strike coverage around correct ATM"""
import sys
import psycopg2

sys.path.append('/home/info/fntx-ai-v1/01_backend')
from config.theta_config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

cursor.execute("""
    SELECT DISTINCT strike 
    FROM theta.options_contracts 
    WHERE symbol = 'SPY' AND expiration = '2023-01-03'
    ORDER BY strike
""")

strikes = [int(row[0]) for row in cursor.fetchall()]
print(f'Available strikes: {strikes}')
print(f'Range: ${min(strikes)} - ${max(strikes)}')

correct_atm = 384
print(f'\nCorrect ATM: ${correct_atm}')
print(f'Critical strikes around ATM (±10):')
for s in range(correct_atm - 10, correct_atm + 11):
    if s in strikes:
        print(f'  ${s} ✓')
    else:
        print(f'  ${s} ✗ MISSING')

cursor.close()
conn.close()