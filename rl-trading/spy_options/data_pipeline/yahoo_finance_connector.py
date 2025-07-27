"""
Yahoo Finance connector for SPY price
Fallback when Theta Terminal REST API isn't available
"""
import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional
import json


class YahooFinanceConnector:
    """Gets SPY price from Yahoo Finance"""
    
    def __init__(self):
        self.session = None
        self.logger = logging.getLogger(__name__)
        
        # Market data cache
        self.market_data = {
            'spy_price': 0,
            'options_chain': [],  # Empty for now
            'vix': 0,
            'timestamp': None
        }
        
        # Update task
        self.update_task = None
        
    async def start(self):
        """Start connection and begin updates"""
        self.session = aiohttp.ClientSession()
        self.logger.info("Starting Yahoo Finance connector for SPY data")
        
        # Start periodic updates
        self.update_task = asyncio.create_task(self._update_loop())
        
        # Initial update
        await self._fetch_market_data()
        
    async def stop(self):
        """Stop connection"""
        if self.update_task:
            self.update_task.cancel()
        if self.session:
            await self.session.close()
            
    async def _update_loop(self):
        """Periodic market data updates"""
        while True:
            try:
                await self._fetch_market_data()
                await asyncio.sleep(2)  # Update every 2 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Update error: {e}")
                await asyncio.sleep(5)
                
    async def _fetch_market_data(self):
        """Fetch current SPY price from Yahoo Finance"""
        try:
            # Yahoo Finance API endpoint
            url = "https://query1.finance.yahoo.com/v8/finance/chart/SPY"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract price
                    result = data.get('chart', {}).get('result', [])
                    if result:
                        meta = result[0].get('meta', {})
                        price = meta.get('regularMarketPrice', 0)
                        
                        if price > 0:
                            self.market_data['spy_price'] = price
                            self.logger.info(f"SPY price: ${price:.2f}")
                            
                    # Try to get VIX
                    vix_url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX"
                    async with self.session.get(vix_url) as vix_response:
                        if vix_response.status == 200:
                            vix_data = await vix_response.json()
                            vix_result = vix_data.get('chart', {}).get('result', [])
                            if vix_result:
                                vix_meta = vix_result[0].get('meta', {})
                                vix_price = vix_meta.get('regularMarketPrice', 16)
                                self.market_data['vix'] = vix_price
                                
                    self.market_data['timestamp'] = datetime.now()
                    
        except Exception as e:
            self.logger.error(f"Failed to fetch market data: {e}")
            
    def get_current_snapshot(self) -> Dict:
        """Get current market snapshot"""
        return self.market_data.copy()
        
    def get_atm_options(self, num_strikes: int = 5) -> List[Dict]:
        """Return empty list - no options data from Yahoo Finance"""
        return []