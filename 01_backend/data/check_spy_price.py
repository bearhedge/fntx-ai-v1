#!/usr/bin/env python3
import yfinance as yf
from datetime import datetime

spy = yf.Ticker('SPY')
data = spy.history(start='2023-01-03', end='2023-01-04')
print('Yahoo Finance SPY data for Jan 3, 2023:')
print(f'Open: ${data["Open"].iloc[0]:.2f}')
print(f'High: ${data["High"].iloc[0]:.2f}')
print(f'Low: ${data["Low"].iloc[0]:.2f}')
print(f'Close: ${data["Close"].iloc[0]:.2f}')