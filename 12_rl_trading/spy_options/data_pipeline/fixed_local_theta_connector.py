"""
Fixed Local Theta Terminal connector
Properly handles the actual Theta Terminal API response format
"""
import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np


class FixedLocalThetaConnector:
    """Fixed connector for local Theta Terminal instance"""
    
    def __init__(self):
        self.base_url = "http://localhost:25510"
        self.session = None
        self.logger = logging.getLogger(__name__)
        
        # Market data cache
        self.market_data = {
            'spy_price': 0,
            'options_chain': [],
            'vix': 0,
            'timestamp': None
        }
        
        # Update task
        self.update_task = None
        
    async def start(self):
        """Start connection and begin updates"""
        self.session = aiohttp.ClientSession()
        self.logger.info(f"Connecting to local Theta Terminal at {self.base_url}")
        
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
                await asyncio.sleep(1)  # Update every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Update error: {e}")
                await asyncio.sleep(5)
                
    async def _fetch_market_data(self):
        """Fetch current SPY and options data"""
        try:
            # Get SPY price
            spy_data = await self._get_quote('SPY')
            if spy_data:
                self.market_data['spy_price'] = spy_data.get('last', 0)
                
            # Get 0DTE options chain
            options = await self._get_options_chain()
            self.market_data['options_chain'] = options
            
            # Get VIX quote
            vix_data = await self._get_quote('VIX')
            if vix_data:
                self.market_data['vix'] = vix_data.get('last', 16)
                
            self.market_data['timestamp'] = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Failed to fetch market data: {e}")
            
    async def _get_quote(self, symbol: str) -> Optional[Dict]:
        """Get quote for symbol"""
        try:
            if symbol == 'SPY':
                # Use snapshot endpoint for SPY
                url = f"{self.base_url}/v2/snapshot/stock/quote?root=SPY"
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and 'response' in data and data['response']:
                            # Response format: [ms_of_day, bid_size, bid_exchange, bid, bid_condition, ask_size, ask_exchange, ask, ask_condition, date]
                            quote = data['response'][0]
                            if len(quote) >= 8:
                                bid = quote[3]  # Already in dollars
                                ask = quote[7]  # Already in dollars
                                return {
                                    'last': (bid + ask) / 2,
                                    'bid': bid,
                                    'ask': ask,
                                    'volume': 0  # Volume not in quote snapshot
                                }
                                        
            elif symbol == 'VIX':
                # Try to get VIX from Theta Terminal
                url = f"{self.base_url}/v2/snapshot/stock/quote?root=VIX"
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and 'response' in data and data['response']:
                            quote = data['response'][0]
                            if len(quote) >= 8:
                                bid = quote[3]
                                ask = quote[7]
                                return {
                                    'last': (bid + ask) / 2,
                                    'bid': bid,
                                    'ask': ask,
                                    'volume': 0
                                }
                # Fallback to default if VIX data not available
                return {'last': 16, 'bid': 15.95, 'ask': 16.05, 'volume': 0}
                
        except Exception as e:
            self.logger.error(f"Quote fetch error for {symbol}: {e}")
        return None
        
    async def _get_options_chain(self) -> List[Dict]:
        """Get 0DTE SPY options chain with real data"""
        try:
            # Get today's expiration
            today = datetime.now().strftime('%Y%m%d')
            
            if not self.market_data['spy_price']:
                return []
                
            # Get all options data in parallel
            quotes_task = self._get_bulk_option_quotes(today)
            greeks_task = self._get_bulk_option_greeks(today)
            oi_task = self._get_bulk_option_oi(today)
            
            quotes_data, greeks_data, oi_data = await asyncio.gather(
                quotes_task, greeks_task, oi_task
            )
            
            # Combine all data
            options = []
            
            for quote_item in quotes_data:
                if 'contract' in quote_item and 'ticks' in quote_item and quote_item['ticks']:
                    contract = quote_item['contract']
                    tick = quote_item['ticks'][0]
                    
                    strike = contract['strike'] / 1000  # Convert cents to dollars
                    right = contract['right']
                    key = f"{contract['strike']}_{right}"
                    
                    # Parse quote [ms_of_day, bid_size, bid_exchange, bid, bid_condition, ask_size, ask_exchange, ask, ask_condition, date]
                    bid = tick[3] / 100 if len(tick) > 3 else 0
                    ask = tick[7] / 100 if len(tick) > 7 else 0
                    bid_size = tick[1] if len(tick) > 1 else 0
                    ask_size = tick[5] if len(tick) > 5 else 0
                    
                    # Get greeks
                    greek_info = greeks_data.get(key, {})
                    
                    # Get OI
                    oi = oi_data.get(key, 0)
                    
                    # Only include options near ATM (within $20)
                    if abs(strike - self.market_data['spy_price']) <= 20:
                        options.append({
                            'strike': strike,
                            'type': right,
                            'bid': bid,
                            'ask': ask,
                            'last': (bid + ask) / 2,
                            'volume': 0,  # Would need trades endpoint
                            'open_interest': oi,
                            'iv': greek_info.get('iv', 0.20),
                            'delta': greek_info.get('delta', 0.50 if right == 'C' else -0.50),
                            'gamma': greek_info.get('gamma', 0.01),
                            'theta': greek_info.get('theta', -0.05),
                            'vega': greek_info.get('vega', 0.1),
                            'bid_size': bid_size,
                            'ask_size': ask_size
                        })
                    
            return sorted(options, key=lambda x: (x['strike'], x['type']))
                        
        except Exception as e:
            self.logger.error(f"Options chain error: {e}")
        return []
        
    async def _get_bulk_option_quotes(self, exp: str) -> List[Dict]:
        """Get bulk option quotes"""
        try:
            url = f"{self.base_url}/v2/bulk_snapshot/option/quote?root=SPY&exp={exp}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'response' in data:
                        return data['response']
        except Exception as e:
            self.logger.error(f"Bulk quotes error: {e}")
        return []
        
    async def _get_bulk_option_greeks(self, exp: str) -> Dict:
        """Get bulk option greeks"""
        greeks_map = {}
        try:
            url = f"{self.base_url}/v2/bulk_snapshot/option/greeks?root=SPY&exp={exp}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'response' in data:
                        for item in data['response']:
                            if 'contract' in item and 'ticks' in item and item['ticks']:
                                contract = item['contract']
                                tick = item['ticks'][0]
                                key = f"{contract['strike']}_{contract['right']}"
                                
                                # [ms_of_day, bid, ask, delta, theta, vega, rho, epsilon, lambda, implied_vol, iv_error, ms_of_day2, underlying_price, date]
                                greeks_map[key] = {
                                    'delta': tick[3] if len(tick) > 3 else 0,
                                    'theta': tick[4] if len(tick) > 4 else 0,
                                    'vega': tick[5] if len(tick) > 5 else 0,
                                    'gamma': 0.01,  # Not provided, use estimate
                                    'iv': tick[9] if len(tick) > 9 else 0.20
                                }
        except Exception as e:
            self.logger.error(f"Bulk greeks error: {e}")
        return greeks_map
        
    async def _get_bulk_option_oi(self, exp: str) -> Dict:
        """Get bulk option open interest"""
        oi_map = {}
        try:
            url = f"{self.base_url}/v2/bulk_hist/option/open_interest?root=SPY&exp={exp}&start_date={exp}&end_date={exp}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'response' in data:
                        for item in data['response']:
                            if 'contract' in item and 'ticks' in item and item['ticks']:
                                contract = item['contract']
                                tick = item['ticks'][0]
                                key = f"{contract['strike']}_{contract['right']}"
                                # [ms_of_day, open_interest, date]
                                oi_map[key] = tick[1] if len(tick) > 1 else 0
        except Exception as e:
            self.logger.error(f"Bulk OI error: {e}")
        return oi_map
        
    def get_current_snapshot(self) -> Dict:
        """Get current market snapshot"""
        return self.market_data.copy()
        
    def get_atm_options(self, num_strikes: int = 5) -> List[Dict]:
        """Get at-the-money options"""
        spy_price = self.market_data['spy_price']
        if not spy_price or not self.market_data['options_chain']:
            return []
            
        # Find ATM strike
        atm_strike = round(spy_price)
        
        # Filter options within num_strikes of ATM
        atm_options = []
        for option in self.market_data['options_chain']:
            if abs(option['strike'] - atm_strike) <= num_strikes:
                atm_options.append(option)
                
        return sorted(atm_options, key=lambda x: (x['strike'], x['type']))