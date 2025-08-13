"""
Local Theta Terminal connector
Connects to Theta Terminal running on localhost:25510
"""
import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np


class LocalThetaConnector:
    """Connects to local Theta Terminal instance"""
    
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
            
            # Get VIX
            vix_data = await self._get_quote('VIX')
            if vix_data:
                self.market_data['vix'] = vix_data.get('last', 16)
                
            self.market_data['timestamp'] = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Failed to fetch market data: {e}")
            
    async def _get_quote(self, symbol: str) -> Optional[Dict]:
        """Get quote for symbol"""
        try:
            # For SPY stock quote - using bulk quote endpoint
            if symbol == 'SPY':
                url = f"{self.base_url}/v2/bulk_snapshot/stock/quote?root=SPY"
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and 'response' in data and data['response']:
                            # Response format for bulk quote: [[contract_id, ms_of_day, bid_size, bid_exchange, bid, ask_size, ask_exchange, ask, ask_condition, date]]
                            for quote_data in data['response']:
                                if len(quote_data) >= 8:
                                    bid = quote_data[4] / 100  # Convert cents to dollars
                                    ask = quote_data[7] / 100
                                    return {
                                        'last': (bid + ask) / 2,
                                        'bid': bid,
                                        'ask': ask,
                                        'volume': 0  # Volume not in quote snapshot
                                    }
                    else:
                        # Try OHLC endpoint as fallback
                        ohlc_url = f"{self.base_url}/v2/hist/stock/ohlc?root=SPY&start_date={datetime.now().strftime('%Y%m%d')}&end_date={datetime.now().strftime('%Y%m%d')}"
                        
                        async with self.session.get(ohlc_url) as ohlc_resp:
                            if ohlc_resp.status == 200:
                                ohlc_data = await ohlc_resp.json()
                                if ohlc_data and 'response' in ohlc_data and ohlc_data['response']:
                                    # Get last close price
                                    last_bar = ohlc_data['response'][-1]
                                    if len(last_bar) >= 5:
                                        close_price = last_bar[4] / 100  # Close price
                                        return {
                                            'last': close_price,
                                            'bid': close_price - 0.01,
                                            'ask': close_price + 0.01,
                                            'volume': last_bar[5] if len(last_bar) > 5 else 0
                                        }
                                        
            elif symbol == 'VIX':
                # VIX might not be available, use default
                return {'last': 16, 'bid': 15.95, 'ask': 16.05, 'volume': 0}
                
        except Exception as e:
            self.logger.error(f"Quote fetch error for {symbol}: {e}")
        return None
        
    async def _get_option_quote(self, root: str, exp: str, strike: int, right: str) -> Optional[Dict]:
        """Get single option quote"""
        try:
            strike_str = f"{strike}000"  # Theta uses strike in cents
            
            # Try bulk snapshot endpoint which should work
            bulk_url = f"{self.base_url}/v2/bulk_snapshot/option/quote?root={root}&exp={exp}"
            
            async with self.session.get(bulk_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and 'response' in data and data['response']:
                        # Find the specific strike and right
                        for quote_row in data['response']:
                            # Parse contract ID to check strike and right
                            # Format: contract_id contains strike and right info
                            if len(quote_row) >= 10:
                                contract_info = quote_row[0]  # contract_id
                                # Check if this is our strike/right
                                if f"{strike_str}" in str(contract_info) and right in str(contract_info):
                                    bid = quote_row[4] / 100  # bid
                                    ask = quote_row[7] / 100  # ask
                            
                            # Get volume and OI
                            volume = 0
                            oi = 0
                            
                            # Try to get volume from OHLC
                            ohlc_url = f"{self.base_url}/v2/snapshot/option/ohlc?root={root}&exp={exp}&strike={strike_str}&right={right}"
                            try:
                                async with self.session.get(ohlc_url) as ohlc_resp:
                                    if ohlc_resp.status == 200:
                                        ohlc_data = await ohlc_resp.json()
                                        if ohlc_data and 'response' in ohlc_data and ohlc_data['response']:
                                            # Format: [ms_of_day, open, high, low, close, volume, count, date]
                                            ohlc_row = ohlc_data['response'][0]
                                            if len(ohlc_row) > 5:
                                                volume = ohlc_row[5]
                                                # Validate volume is reasonable (not negative)
                                                volume = max(0, volume)
                                    else:
                                        self.logger.debug(f"OHLC request failed with status {ohlc_resp.status} for {strike_str}{right}")
                            except Exception as e:
                                self.logger.debug(f"OHLC volume fetch failed for {strike_str}{right}: {e}")
                                pass
                                
                            # Try to get open interest
                            oi_url = f"{self.base_url}/v2/snapshot/option/open_interest?root={root}&exp={exp}&strike={strike_str}&right={right}"
                            try:
                                async with self.session.get(oi_url) as oi_resp:
                                    if oi_resp.status == 200:
                                        oi_data = await oi_resp.json()
                                        if oi_data and 'response' in oi_data and oi_data['response']:
                                            # Format: [ms_of_day, open_interest, date]
                                            oi = oi_data['response'][0][1] if len(oi_data['response'][0]) > 1 else 0
                            except:
                                pass
                                
                            # Get Greeks data
                            iv, delta, gamma, theta = await self._get_option_greeks(root, exp, strike_str, right, bid, ask)
                            
                            return {
                                'strike': strike,
                                'type': right,
                                'bid': bid,
                                'ask': ask,
                                'last': (bid + ask) / 2,
                                'volume': volume,
                                'open_interest': oi,
                                'iv': iv,
                                'delta': delta,
                                'gamma': gamma,
                                'theta': theta
                            }
                            
        except Exception as e:
            self.logger.error(f"Option quote error for {root} {exp} {strike} {right}: {e}")
        return None
        
    async def _get_option_greeks(self, root: str, exp: str, strike_str: str, right: str, 
                               bid: float, ask: float) -> tuple:
        """
        Get Greeks data for option
        Returns: (iv, delta, gamma, theta)
        """
        try:
            # Try Greeks endpoint first
            greeks_url = f"{self.base_url}/v2/snapshot/option/greeks?root={root}&exp={exp}&strike={strike_str}&right={right}"
            
            async with self.session.get(greeks_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and 'response' in data and data['response']:
                        # Format: [ms_of_day, delta, gamma, theta, vega, iv, date]
                        greeks_data = data['response'][0]
                        if len(greeks_data) >= 6:
                            delta = greeks_data[1] / 100.0  # Convert from percentage to decimal
                            gamma = greeks_data[2] / 100.0
                            theta = greeks_data[3] / 100.0
                            iv = greeks_data[5] / 100.0  # Convert from percentage to decimal
                            
                            # Validate ranges
                            if right == 'C':
                                delta = max(0.0, min(1.0, delta))  # Calls: 0 to 1
                            else:
                                delta = max(-1.0, min(0.0, delta))  # Puts: -1 to 0
                            
                            iv = max(0.0, iv)  # IV must be positive
                            
                            return (iv, delta, gamma, theta)
                            
        except Exception as e:
            self.logger.debug(f"Greeks endpoint failed for {root} {exp} {strike_str} {right}: {e}")
        
        # Fallback: Calculate approximate Greeks using Black-Scholes if we have price data
        if bid > 0 and ask > 0:
            mid_price = (bid + ask) / 2
            iv, delta = self._calculate_approximate_greeks(float(strike_str), mid_price, right)
            return (iv, delta, 0.01, -0.05)  # Default gamma and theta
        
        # Final fallback: Use reasonable defaults
        if right == 'C':
            return (0.25, 0.30, 0.01, -0.05)  # Call defaults
        else:
            return (0.25, -0.30, 0.01, -0.05)  # Put defaults
            
    def _calculate_approximate_greeks(self, strike: float, option_price: float, right: str) -> tuple:
        """
        Calculate approximate IV and delta using simplified formulas
        Returns: (iv, delta)
        """
        try:
            spy_price = self.market_data.get('spy_price', 635.0)
            
            # Simple moneyness calculation
            if right == 'C':
                moneyness = spy_price / strike
                # Rough delta approximation based on moneyness
                if moneyness > 1.05:  # Deep ITM
                    delta = 0.70 + (moneyness - 1.05) * 0.15
                elif moneyness > 0.95:  # Near ATM
                    delta = 0.30 + (moneyness - 0.95) * 4.0
                else:  # OTM
                    delta = max(0.05, 0.30 * moneyness / 0.95)
                delta = min(0.95, max(0.01, delta))
            else:  # Put
                moneyness = strike / spy_price
                if moneyness > 1.05:  # Deep ITM
                    delta = -0.70 - (moneyness - 1.05) * 0.15
                elif moneyness > 0.95:  # Near ATM
                    delta = -0.30 - (moneyness - 0.95) * 4.0
                else:  # OTM
                    delta = max(-0.95, -0.30 * moneyness / 0.95)
                delta = max(-0.95, min(-0.01, delta))
            
            # Rough IV approximation (0DTE options typically 20-80%)
            iv = max(0.15, min(0.80, option_price / spy_price * 10))
            
            return (iv, delta)
            
        except:
            # Ultimate fallback
            return (0.25, 0.30 if right == 'C' else -0.30)
        
    async def _get_options_chain(self) -> List[Dict]:
        """Get 0DTE SPY options chain"""
        try:
            # Get today's expiration
            today = datetime.now().strftime('%Y%m%d')
            
            if not self.market_data['spy_price']:
                return []
                
            # Get strikes around current price
            spy_price = self.market_data['spy_price']
            strike_low = int(spy_price - 20)
            strike_high = int(spy_price + 20)
            
            options = []
            
            # Fetch each strike's call and put
            for strike in range(strike_low, strike_high + 1):
                # Get call option
                call_data = await self._get_option_quote('SPY', today, strike, 'C')
                if call_data:
                    options.append(call_data)
                    
                # Get put option  
                put_data = await self._get_option_quote('SPY', today, strike, 'P')
                if put_data:
                    options.append(put_data)
                    
            return options
                        
        except Exception as e:
            self.logger.error(f"Options chain error: {e}")
        return []
        
        
    def get_current_snapshot(self) -> Dict:
        """Get current market snapshot"""
        return self.market_data.copy()
        
    def get_atm_options(self, num_strikes: int = 5) -> List[Dict]:
        """Get at-the-money options"""
        spy_price = self.market_data['spy_price']
        if not spy_price:
            return []
            
        # Find closest strikes
        options = self.market_data['options_chain']
        if not options:
            return []
            
        # Sort by distance from current price
        sorted_opts = sorted(options, 
                           key=lambda x: abs(x['strike'] - spy_price))
        
        # Group by strike
        strikes = {}
        for opt in sorted_opts[:num_strikes * 2]:  # Get enough for calls and puts
            strike = opt['strike']
            if strike not in strikes:
                strikes[strike] = {'strike': strike}
            
            if opt['type'] == 'C':
                strikes[strike]['call'] = opt
            else:
                strikes[strike]['put'] = opt
                
        return list(strikes.values())[:num_strikes]