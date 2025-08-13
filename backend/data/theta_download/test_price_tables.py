#!/usr/bin/env python3
import psycopg2
from datetime import date

# Test both price tables
conn = psycopg2.connect(
    host="localhost",
    database="options_data",
    user="postgres",
    password="theta_data_2024"
)

cursor = conn.cursor()

# Test SPY
cursor.execute("""
    SELECT COUNT(*), MIN(date), MAX(date) 
    FROM spy_prices_raw
""")
spy_count, spy_min, spy_max = cursor.fetchone()
print(f"SPY: {spy_count} records from {spy_min} to {spy_max}")

# Test specific date
cursor.execute("""
    SELECT open, high, low, close 
    FROM spy_prices_raw 
    WHERE date = '2022-12-05'
""")
spy_price = cursor.fetchone()
print(f"SPY on 2022-12-05: {spy_price}")

# Test QQQ
cursor.execute("""
    SELECT COUNT(*), MIN(date), MAX(date) 
    FROM qqq_prices_raw
""")
qqq_count, qqq_min, qqq_max = cursor.fetchone()
print(f"\nQQQ: {qqq_count} records from {qqq_min} to {qqq_max}")

# Test specific date
cursor.execute("""
    SELECT open, high, low, close 
    FROM qqq_prices_raw 
    WHERE date = '2022-12-05'
""")
qqq_price = cursor.fetchone()
print(f"QQQ on 2022-12-05: {qqq_price}")

conn.close()