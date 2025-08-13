"""
Yahoo Finance real-time price fetcher for SPY and VIX
"""
import asyncio
import aiohttp
import logging
from datetime import datetime
import json


class YahooPriceFetcher:
    """Fetches real-time SPY price and VIX from Yahoo Finance"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.last_price = None
        self.last_vix = None
        self.last_update = None
        
    async def start(self):
        """Initialize session"""
        self.session = aiohttp.ClientSession()
        
    async def stop(self):
        """Close session"""
        if self.session:
            await self.session.close()
            
    async def get_spy_price(self):
        """Fetch current SPY price from Yahoo Finance"""
        try:
            # Yahoo Finance API endpoint for real-time quote
            url = "https://query1.finance.yahoo.com/v8/finance/chart/SPY"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract price from response
                    result = data.get('chart', {}).get('result', [])
                    if result:
                        meta = result[0].get('meta', {})
                        regular_price = meta.get('regularMarketPrice')
                        
                        if regular_price:
                            self.last_price = regular_price
                            self.last_update = datetime.now()
                            self.logger.info(f"Yahoo Finance SPY: ${regular_price:.2f}")
                            return regular_price
                        
        except Exception as e:
            self.logger.error(f"Error fetching Yahoo price: {e}")
            
        return self.last_price  # Return cached price if fetch fails
        
    async def get_vix(self):
        """Fetch current VIX from Yahoo Finance"""
        try:
            # Yahoo Finance API endpoint for VIX
            url = "https://query1.finance.yahoo.com/v8/finance/chart/^VIX"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract price from response
                    result = data.get('chart', {}).get('result', [])
                    if result:
                        meta = result[0].get('meta', {})
                        regular_price = meta.get('regularMarketPrice')
                        
                        if regular_price:
                            self.last_vix = regular_price
                            self.logger.info(f"Yahoo Finance VIX: {regular_price:.2f}")
                            return regular_price
                            
        except Exception as e:
            self.logger.error(f"Error fetching VIX: {e}")
            
        return self.last_vix  # Return cached VIX if fetch fails
        
    async def price_update_loop(self, callback=None, interval=5):
        """Continuously update price and VIX at specified interval"""
        while True:
            try:
                # Fetch both SPY and VIX
                spy_price = await self.get_spy_price()
                vix = await self.get_vix()
                
                if callback:
                    # Pass both values to callback
                    await callback({'spy': spy_price, 'vix': vix})
                    
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Price update loop error: {e}")
                await asyncio.sleep(interval)