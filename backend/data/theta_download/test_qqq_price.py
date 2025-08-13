#!/usr/bin/env python3
import requests
from datetime import date

# Test QQQ price data retrieval
rest_base = "http://127.0.0.1:25510"
symbol = "QQQ"
trading_date = date(2022, 12, 5)
date_str = trading_date.strftime("%Y%m%d")

url = f"{rest_base}/hist/stock/eod?root={symbol}&start_date={date_str}&end_date={date_str}"
print(f"Testing URL: {url}")

response = requests.get(url)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:500]}")