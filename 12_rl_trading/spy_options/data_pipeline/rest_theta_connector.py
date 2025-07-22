"""
REST-based connector for Theta Terminal - Fast polling approach
This is temporary until we figure out WebSocket streaming
"""
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Callable
import numpy as np
from .yahoo_price_fetcher import YahooPriceFetcher


class RESTThetaConnector:
    """REST API connector using fast polling"""
    
    def __init__(self):
        # REST endpoints
        self.rest_base = "http://localhost:25510"
        
        # Running state
        self.running = False
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Yahoo Finance for real-time SPY
        self.yahoo_fetcher = YahooPriceFetcher()
        
        # Market data cache
        self.market_data = {
            'spy_price': 0,
            'spy_price_realtime': 0,  # From Yahoo
            'options_chain': {},  # Strike_Type -> option data
            'vix': 0,
            'timestamp': None
        }
        
        # Callbacks
        self.on_market_update = None
        
        # HTTP session
        self.session = None
        
    async def start(self):
        """Start REST polling"""
        self.running = True
        self.logger.info("Starting REST-based Theta Data connector")
        
        try:
            # Create HTTP session
            self.session = aiohttp.ClientSession()
            
            # Start Yahoo Finance for real-time SPY
            await self.yahoo_fetcher.start()
            
            # Get initial SPY price
            await self._get_spy_price()
            
            # Start Yahoo price update loop (1 second interval for real-time)
            self.yahoo_task = asyncio.create_task(
                self.yahoo_fetcher.price_update_loop(
                    callback=self._on_yahoo_update,
                    interval=1
                )
            )
            
            # Start polling loop
            self.poll_task = asyncio.create_task(self._polling_loop())
            
            self.logger.info("REST polling started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start: {e}")
            raise
            
    async def stop(self):
        """Stop polling"""
        self.running = False
        
        # Close HTTP session
        if self.session:
            await self.session.close()
            
        # Stop Yahoo
        await self.yahoo_fetcher.stop()
        
        # Cancel tasks
        if hasattr(self, 'yahoo_task'):
            self.yahoo_task.cancel()
        if hasattr(self, 'poll_task'):
            self.poll_task.cancel()
            
        self.logger.info("Polling stopped")
        
    async def _polling_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                # Get option chain data
                await self._fetch_options_chain()
                
                # Trigger callback if registered
                if self.on_market_update:
                    await self.on_market_update(self.get_current_snapshot())
                    
                # Poll every 500ms for near real-time updates
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Polling error: {e}")
                await asyncio.sleep(1)
                
    async def _get_spy_price(self):
        """Get SPY stock price"""
        try:
            url = f"{self.rest_base}/v2/snapshot/stock/quote?root=SPY"
            async with self.session.get(url) as resp:
                data = await resp.json()
                
                if 'response' in data and len(data['response']) > 0:
                    # Format: [ms_of_day, bid_size, bid_exchange, bid, bid_condition, ask_size, ask_exchange, ask, ask_condition, date]
                    row = data['response'][0]
                    bid = row[3]
                    ask = row[7]
                    
                    if bid > 0 and ask > 0:
                        self.market_data['spy_price'] = (bid + ask) / 2
                        self.logger.info(f"SPY price: ${self.market_data['spy_price']:.2f}")
                        
        except Exception as e:
            self.logger.error(f"Error getting SPY price: {e}")
            
    async def _fetch_options_chain(self):
        """Fetch full options chain with quotes, volume, OI, and greeks"""
        try:
            # Get expiration date
            exp_date = self._get_0dte_expiration()
            exp_str = exp_date.strftime("%Y%m%d")
            
            # Fetch multiple data types in parallel
            tasks = [
                self._fetch_option_quotes(exp_str),
                self._fetch_option_ohlc(exp_str),  # Contains volume
                self._fetch_option_oi(exp_str),    # Open interest
                self._fetch_option_greeks(exp_str) # Real greeks
            ]
            
            quotes, ohlc, oi, greeks = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process quotes first
            if isinstance(quotes, dict) and 'response' in quotes:
                for contract_data in quotes['response']:
                    if 'contract' in contract_data:
                        contract = contract_data['contract']
                        
                        # Parse contract details
                        if 'right' in contract and 'strike' in contract:
                            strike = int(contract['strike'] / 1000)  # Convert from thousandths
                            right = contract['right']
                            option_key = f"{strike}_{right}"
                            
                            # Get quote data
                            ticks = contract_data.get('ticks', [])
                            if ticks and len(ticks[0]) >= 10:
                                tick = ticks[0]
                                # Format: [ms_of_day, bid_size, bid_exchange, bid, bid_condition, ask_size, ask_exchange, ask, ask_condition, date]
                                
                                self.market_data['options_chain'][option_key] = {
                                    'strike': strike,
                                    'type': right,
                                    'bid': tick[3],
                                    'ask': tick[7],
                                    'last': (tick[3] + tick[7]) / 2 if tick[3] > 0 or tick[7] > 0 else 0,
                                    'bid_size': tick[1],
                                    'ask_size': tick[5],
                                    'volume': 0,
                                    'open_interest': 0,
                                    'iv': self._estimate_iv(strike, self.market_data['spy_price_realtime'] or self.market_data['spy_price'], right),
                                    'delta': self._estimate_delta(strike, self.market_data['spy_price_realtime'] or self.market_data['spy_price'], right),
                                    'gamma': 0.01,
                                    'theta': -0.05,
                                    'timestamp': datetime.now()
                                }
            
            # Update with OHLC data (volume)
            if isinstance(ohlc, dict) and 'response' in ohlc:
                for contract_data in ohlc['response']:
                    if 'contract' in contract_data:
                        contract = contract_data['contract']
                        strike = int(contract['strike'] / 1000)
                        right = contract['right']
                        option_key = f"{strike}_{right}"
                        
                        if option_key in self.market_data['options_chain']:
                            ticks = contract_data.get('ticks', [])
                            if ticks and len(ticks[0]) >= 10:
                                # Format includes volume
                                self.market_data['options_chain'][option_key]['volume'] = ticks[0][5]
            
            # Update with open interest
            if isinstance(oi, dict) and 'response' in oi:
                for contract_data in oi['response']:
                    if 'contract' in contract_data:
                        contract = contract_data['contract']
                        strike = int(contract['strike'] / 1000)
                        right = contract['right']
                        option_key = f"{strike}_{right}"
                        
                        if option_key in self.market_data['options_chain']:
                            ticks = contract_data.get('ticks', [])
                            if ticks and len(ticks[0]) >= 2:
                                self.market_data['options_chain'][option_key]['open_interest'] = ticks[0][1]
            
            # Update with real greeks
            if isinstance(greeks, dict) and 'response' in greeks:
                for contract_data in greeks['response']:
                    if 'contract' in contract_data:
                        contract = contract_data['contract']
                        strike = int(contract['strike'] / 1000)
                        right = contract['right']
                        option_key = f"{strike}_{right}"
                        
                        if option_key in self.market_data['options_chain']:
                            ticks = contract_data.get('ticks', [])
                            if ticks and len(ticks[0]) >= 5:
                                # Format: [ms_of_day, delta, gamma, theta, vega, rho, date]
                                self.market_data['options_chain'][option_key]['delta'] = ticks[0][1]
                                self.market_data['options_chain'][option_key]['gamma'] = ticks[0][2]
                                self.market_data['options_chain'][option_key]['theta'] = ticks[0][3]
                                self.market_data['options_chain'][option_key]['iv'] = ticks[0][4] / 100  # Convert to decimal
                    
            self.market_data['timestamp'] = datetime.now()
            self.logger.debug(f"Updated {len(self.market_data['options_chain'])} option contracts")
                    
        except Exception as e:
            self.logger.error(f"Error fetching options chain: {e}")
            
    async def _fetch_option_quotes(self, exp_str: str):
        """Fetch option quotes"""
        url = f"{self.rest_base}/v2/bulk_snapshot/option/quote?root=SPY&exp={exp_str}"
        async with self.session.get(url) as resp:
            return await resp.json()
            
    async def _fetch_option_ohlc(self, exp_str: str):
        """Fetch option OHLC with volume"""
        url = f"{self.rest_base}/v2/bulk_snapshot/option/ohlc?root=SPY&exp={exp_str}"
        async with self.session.get(url) as resp:
            return await resp.json()
            
    async def _fetch_option_oi(self, exp_str: str):
        """Fetch option open interest"""
        url = f"{self.rest_base}/v2/bulk_snapshot/option/open_interest?root=SPY&exp={exp_str}"
        async with self.session.get(url) as resp:
            return await resp.json()
            
    async def _fetch_option_greeks(self, exp_str: str):
        """Fetch option greeks"""
        url = f"{self.rest_base}/v2/bulk_snapshot/option/greeks?root=SPY&exp={exp_str}"
        async with self.session.get(url) as resp:
            return await resp.json()
            
    async def _on_yahoo_update(self, data: dict):
        """Handle Yahoo Finance price update"""
        if isinstance(data, dict):
            self.market_data['spy_price_realtime'] = data.get('spy', 0)
            self.market_data['vix'] = data.get('vix', 0)
            self.logger.info(f"Yahoo update - SPY: ${data.get('spy', 0):.2f}, VIX: {data.get('vix', 0):.2f}")
        else:
            # Legacy support for just price
            self.market_data['spy_price_realtime'] = data
            self.logger.info(f"Yahoo update - SPY: ${data:.2f}")
        
    def _get_0dte_expiration(self) -> date:
        """Get 0DTE expiration - always today for true 0DTE"""
        # For 0DTE, we want options expiring TODAY
        return date.today()
            
    def _estimate_iv(self, strike: float, spy_price: float, right: str) -> float:
        """Estimate IV based on moneyness"""
        if spy_price <= 0:
            return 0.20
            
        moneyness = strike / spy_price
        base_iv = 0.185
        otm_adjustment = abs(1 - moneyness) * 0.3
        
        if right == 'P':
            otm_adjustment *= 1.1
            
        return base_iv + otm_adjustment
        
    def _estimate_delta(self, strike: float, spy_price: float, right: str) -> float:
        """Estimate delta based on moneyness"""
        if spy_price <= 0:
            return 0.5 if right == 'C' else -0.5
            
        moneyness = strike / spy_price
        
        if right == 'C':
            if moneyness < 0.98:
                return min(0.95, 0.7 + (0.98 - moneyness) * 2)
            elif moneyness > 1.02:
                return max(0.05, 0.3 - (moneyness - 1.02) * 2)
            else:
                return 0.5
        else:
            if moneyness > 1.02:
                return max(-0.95, -0.7 - (moneyness - 1.02) * 2)
            elif moneyness < 0.98:
                return min(-0.05, -0.3 + (0.98 - moneyness) * 2)
            else:
                return -0.5
                
    def get_current_snapshot(self) -> Dict:
        """Get current market snapshot"""
        snapshot = self.market_data.copy()
        snapshot['options_chain'] = list(self.market_data['options_chain'].values())
        return snapshot
        
    def get_atm_options(self, num_strikes: int = 5) -> List[Dict]:
        """Get at-the-money options"""
        spy_price = self.market_data.get('spy_price_realtime') or self.market_data['spy_price']
        if not spy_price:
            return []
            
        options = list(self.market_data['options_chain'].values())
        if not options:
            return []
            
        # Sort by distance from current price
        sorted_opts = sorted(options, key=lambda x: abs(x['strike'] - spy_price))
        
        # Group by strike
        strikes = {}
        for opt in sorted_opts[:num_strikes * 2]:
            strike = opt['strike']
            if strike not in strikes:
                strikes[strike] = {'strike': strike}
            
            if opt['type'] == 'C':
                strikes[strike]['call'] = opt
            else:
                strikes[strike]['put'] = opt
                
        return list(strikes.values())[:num_strikes]