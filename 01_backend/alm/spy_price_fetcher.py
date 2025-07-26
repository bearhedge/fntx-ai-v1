#!/usr/bin/env python3
"""
SPY Price Fetcher Module
Fetches official SPY closing prices from Yahoo Finance API
"""
import yfinance as yf
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict
import json
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cache file to store fetched prices
CACHE_FILE = os.path.join(os.path.dirname(__file__), '.spy_price_cache.json')

class SPYPriceFetcher:
    def __init__(self):
        self.cache = self._load_cache()
        
    def _load_cache(self) -> Dict[str, float]:
        """Load cached prices from file"""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            logging.warning(f"Failed to save cache: {e}")
    
    def get_spy_closing_price(self, date: datetime) -> Optional[float]:
        """
        Fetch official SPY closing price from Yahoo Finance
        
        Args:
            date: The date to fetch closing price for
            
        Returns:
            SPY closing price or None if not found
        """
        date_str = date.strftime('%Y-%m-%d')
        
        # Check cache first
        if date_str in self.cache:
            logging.info(f"Using cached SPY price for {date_str}: ${self.cache[date_str]}")
            return self.cache[date_str]
        
        try:
            # Create ticker object
            spy = yf.Ticker('SPY')
            
            # Fetch data for a range to handle weekends/holidays
            # Get 5 days of data ending on the requested date + 1
            start_date = date - timedelta(days=5)
            end_date = date + timedelta(days=1)
            
            logging.info(f"Fetching SPY data from Yahoo Finance for {date_str}")
            data = spy.history(start=start_date, end=end_date)
            
            if data.empty:
                logging.warning(f"No SPY data found for date range around {date_str}")
                return None
            
            # Find the exact date or the most recent trading day before it
            if date_str in data.index.strftime('%Y-%m-%d').tolist():
                # Exact date found
                idx = data.index.strftime('%Y-%m-%d').tolist().index(date_str)
                close_price = float(data['Close'].iloc[idx])
                logging.info(f"Found SPY closing price for {date_str}: ${close_price:.2f}")
            else:
                # Find the most recent trading day before the requested date
                valid_dates = data.index[data.index <= date]
                if valid_dates.empty:
                    logging.warning(f"No trading days found on or before {date_str}")
                    return None
                
                latest_date = valid_dates[-1]
                close_price = float(data.loc[latest_date, 'Close'])
                logging.info(f"Using SPY closing price from {latest_date.strftime('%Y-%m-%d')} "
                           f"(most recent before {date_str}): ${close_price:.2f}")
            
            # Cache the result
            self.cache[date_str] = close_price
            self._save_cache()
            
            return close_price
            
        except Exception as e:
            logging.error(f"Error fetching SPY price from Yahoo Finance: {e}")
            return None
    
    def get_spy_prices_range(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """
        Fetch SPY closing prices for a date range
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary of date strings to closing prices
        """
        try:
            spy = yf.Ticker('SPY')
            
            # Add buffer for weekends
            buffer_start = start_date - timedelta(days=3)
            buffer_end = end_date + timedelta(days=1)
            
            logging.info(f"Fetching SPY data from {start_date.strftime('%Y-%m-%d')} "
                        f"to {end_date.strftime('%Y-%m-%d')}")
            
            data = spy.history(start=buffer_start, end=buffer_end)
            
            if data.empty:
                logging.warning("No SPY data found for the date range")
                return {}
            
            # Extract closing prices for each day
            prices = {}
            for date in data.index:
                if start_date.date() <= date.date() <= end_date.date():
                    date_str = date.strftime('%Y-%m-%d')
                    close_price = float(data.loc[date, 'Close'])
                    prices[date_str] = close_price
                    self.cache[date_str] = close_price
            
            self._save_cache()
            logging.info(f"Fetched {len(prices)} SPY closing prices")
            
            return prices
            
        except Exception as e:
            logging.error(f"Error fetching SPY price range: {e}")
            return {}


# Singleton instance
_fetcher = None

def get_spy_closing_price(date: datetime) -> Optional[float]:
    """
    Convenience function to fetch SPY closing price
    
    Args:
        date: The date to fetch closing price for
        
    Returns:
        SPY closing price or None if not found
    """
    global _fetcher
    if _fetcher is None:
        _fetcher = SPYPriceFetcher()
    return _fetcher.get_spy_closing_price(date)


if __name__ == "__main__":
    # Test the fetcher
    import sys
    
    if len(sys.argv) > 1:
        test_date = datetime.strptime(sys.argv[1], '%Y-%m-%d')
    else:
        test_date = datetime(2025, 7, 23)
    
    print(f"\nTesting SPY price fetcher for {test_date.strftime('%Y-%m-%d')}")
    print("-" * 50)
    
    fetcher = SPYPriceFetcher()
    price = fetcher.get_spy_closing_price(test_date)
    
    if price:
        print(f"✅ SPY closing price: ${price:.2f}")
    else:
        print("❌ Failed to fetch SPY closing price")
    
    # Test range fetch
    print(f"\nTesting range fetch for July 2025")
    print("-" * 50)
    
    start = datetime(2025, 7, 21)
    end = datetime(2025, 7, 23)
    
    prices = fetcher.get_spy_prices_range(start, end)
    for date_str, price in sorted(prices.items()):
        print(f"{date_str}: ${price:.2f}")