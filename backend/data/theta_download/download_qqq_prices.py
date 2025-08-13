#!/usr/bin/env python3
import yfinance as yf
import psycopg2
from datetime import datetime, date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download NON-ADJUSTED QQQ prices from Yahoo Finance
conn = psycopg2.connect(
    host="localhost",
    database="options_data",
    user="postgres",
    password="theta_data_2024"
)

# Create table
with open('create_qqq_price_table.sql', 'r') as f:
    conn.cursor().execute(f.read())
    conn.commit()

# Download QQQ data from Dec 2022 to present
ticker = yf.Ticker("QQQ")
start_date = "2022-12-01"
end_date = datetime.now().strftime("%Y-%m-%d")

logger.info(f"Downloading QQQ prices from {start_date} to {end_date}")

# Get NON-ADJUSTED prices (auto_adjust=False)
df = ticker.history(start=start_date, end=end_date, auto_adjust=False)

# Insert into database
cursor = conn.cursor()
inserted = 0
for idx, row in df.iterrows():
    try:
        cursor.execute("""
            INSERT INTO qqq_price_data (date, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (date) DO NOTHING
        """, (
            idx.date(),
            float(row['Open']),
            float(row['High']),
            float(row['Low']),
            float(row['Close']),
            int(row['Volume'])
        ))
        if cursor.rowcount > 0:
            inserted += 1
        conn.commit()  # Commit each row
    except Exception as e:
        logger.error(f"Error inserting {idx}: {e}")
        conn.rollback()  # Rollback on error
logger.info(f"Inserted {inserted} QQQ price records")

# Verify
cursor.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM qqq_price_data")
count, min_date, max_date = cursor.fetchone()
logger.info(f"Total records: {count}, Date range: {min_date} to {max_date}")

conn.close()