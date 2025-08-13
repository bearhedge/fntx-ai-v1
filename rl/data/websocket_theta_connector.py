"""
WebSocket-based connector for Theta Terminal - REAL streaming
"""
import asyncio
import websockets
import json
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Callable
import numpy as np
import aiohttp
from .yahoo_price_fetcher import YahooPriceFetcher


class WebSocketThetaConnector:
    """TRUE streaming connector using WebSocket API"""
    
    def __init__(self):
        # WebSocket endpoints
        self.ws_base = "ws://localhost:25520"
        self.rest_base = "http://localhost:25510"
        
        # WebSocket connections
        self.ws_quote = None
        self.ws_trade = None
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
        
        # Subscribed contracts
        self.subscribed_contracts = set()
        
        # Callbacks
        self.on_market_update = None
        
    async def start(self):
        """Start WebSocket streaming connection"""
        self.running = True
        self.logger.info("Starting WebSocket Theta Data streaming")
        
        try:
            # Start Yahoo Finance for real-time SPY
            await self.yahoo_fetcher.start()
            
            # Get initial SPY price via REST
            await self._get_initial_spy_price()
            
            # Connect WebSocket streams
            await self._connect_websockets()
            
            # Subscribe to options
            await self._subscribe_options()
            
            # Start Yahoo price update loop
            self.yahoo_task = asyncio.create_task(
                self.yahoo_fetcher.price_update_loop(
                    callback=self._on_yahoo_update,
                    interval=5
                )
            )
            
            # Start market update loop
            self.update_task = asyncio.create_task(self._market_update_loop())
            
            self.logger.info("WebSocket streaming started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start streaming: {e}")
            raise
            
    async def stop(self):
        """Stop streaming connections"""
        self.running = False
        
        # Close WebSocket connections
        if self.ws_quote:
            await self.ws_quote.close()
        if self.ws_trade:
            await self.ws_trade.close()
            
        # Stop Yahoo
        await self.yahoo_fetcher.stop()
        
        # Cancel tasks
        if hasattr(self, 'yahoo_task'):
            self.yahoo_task.cancel()
        if hasattr(self, 'update_task'):
            self.update_task.cancel()
            
        self.logger.info("Streaming stopped")
        
    async def _connect_websockets(self):
        """Connect to WebSocket endpoints"""
        try:
            # Connect quote stream
            self.ws_quote = await websockets.connect(f"{self.ws_base}/v1/quote")
            self.logger.info("Connected to quote WebSocket stream")
            
            # Start quote handler
            asyncio.create_task(self._handle_quote_stream())
            
            # Connect trade stream
            self.ws_trade = await websockets.connect(f"{self.ws_base}/v1/trade")
            self.logger.info("Connected to trade WebSocket stream")
            
            # Start trade handler
            asyncio.create_task(self._handle_trade_stream())
            
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")
            raise
            
    async def _handle_quote_stream(self):
        """Handle incoming quote messages"""
        try:
            async for message in self.ws_quote:
                try:
                    data = json.loads(message)
                    await self._process_quote_message(data)
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON in quote message: {message}")
                except Exception as e:
                    self.logger.error(f"Error processing quote: {e}")
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("Quote WebSocket connection closed")
            if self.running:
                # Reconnect
                await asyncio.sleep(1)
                await self._connect_websockets()
                
    async def _handle_trade_stream(self):
        """Handle incoming trade messages"""
        try:
            async for message in self.ws_trade:
                try:
                    data = json.loads(message)
                    await self._process_trade_message(data)
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON in trade message: {message}")
                except Exception as e:
                    self.logger.error(f"Error processing trade: {e}")
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("Trade WebSocket connection closed")
            
    async def _process_quote_message(self, data: dict):
        """Process quote stream message"""
        # Expected format: {"contract": "SPY20250709C622000", "bid": 1.56, "ask": 1.58, ...}
        contract = data.get('contract', '')
        
        # Parse contract symbol
        if contract.startswith('SPY'):
            # Extract strike and type
            parts = self._parse_contract(contract)
            if parts:
                strike = parts['strike']
                option_type = parts['type']
                option_key = f"{strike}_{option_type}"
                
                # Update option data
                self.market_data['options_chain'][option_key] = {
                    'strike': strike,
                    'type': option_type,
                    'bid': data.get('bid', 0),
                    'ask': data.get('ask', 0),
                    'last': (data.get('bid', 0) + data.get('ask', 0)) / 2,
                    'bid_size': data.get('bid_size', 0),
                    'ask_size': data.get('ask_size', 0),
                    'volume': self.market_data['options_chain'].get(option_key, {}).get('volume', 0),
                    'open_interest': self.market_data['options_chain'].get(option_key, {}).get('open_interest', 0),
                    'iv': self._estimate_iv(strike, self.market_data['spy_price_realtime'] or self.market_data['spy_price'], option_type),
                    'delta': self._estimate_delta(strike, self.market_data['spy_price_realtime'] or self.market_data['spy_price'], option_type),
                    'gamma': 0.01,
                    'theta': -0.05,
                    'timestamp': datetime.now()
                }
                
                self.market_data['timestamp'] = datetime.now()
                self.logger.debug(f"Quote update: {option_key} bid={data.get('bid')} ask={data.get('ask')}")
                
    async def _process_trade_message(self, data: dict):
        """Process trade stream message"""
        contract = data.get('contract', '')
        
        # Parse contract symbol
        if contract.startswith('SPY'):
            parts = self._parse_contract(contract)
            if parts:
                strike = parts['strike']
                option_type = parts['type']
                option_key = f"{strike}_{option_type}"
                
                # Update volume
                if option_key in self.market_data['options_chain']:
                    opt = self.market_data['options_chain'][option_key]
                    opt['volume'] = opt.get('volume', 0) + data.get('size', 0)
                    opt['last'] = data.get('price', opt['last'])
                    
                    self.logger.debug(f"Trade update: {option_key} price={data.get('price')} size={data.get('size')}")
                    
    def _parse_contract(self, contract: str) -> Optional[Dict]:
        """Parse contract symbol like SPY20250709C622000"""
        try:
            # Format: ROOTYYYYMMDDCPPPPPPP
            if len(contract) >= 17:
                root = contract[:3]
                date_str = contract[3:11]
                option_type = contract[11]
                strike_str = contract[12:]
                
                strike = int(strike_str) / 1000  # Convert from thousandths
                
                return {
                    'root': root,
                    'date': date_str,
                    'type': option_type,
                    'strike': int(strike)
                }
        except:
            return None
            
    async def _get_initial_spy_price(self):
        """Get initial SPY price via REST API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.rest_base}/v2/snapshot/stock/quote?root=SPY"
                async with session.get(url) as resp:
                    data = await resp.json()
                    
                    if 'response' in data and len(data['response']) > 0:
                        # Format: [ms_of_day, bid_size, bid_exchange, bid, bid_condition, ask_size, ask_exchange, ask, ask_condition, date]
                        row = data['response'][0]
                        bid = row[3]
                        ask = row[7]
                        
                        if bid > 0 and ask > 0:
                            self.market_data['spy_price'] = (bid + ask) / 2
                            self.logger.info(f"Initial SPY price: ${self.market_data['spy_price']:.2f}")
                            
        except Exception as e:
            self.logger.error(f"Error getting initial SPY price: {e}")
            self.market_data['spy_price'] = 621.0  # Default
            
    async def _subscribe_options(self):
        """Subscribe to 0DTE options via WebSocket"""
        try:
            if self.market_data['spy_price'] <= 0:
                self.market_data['spy_price'] = 621.0  # Default
                
            spy_price = int(self.market_data['spy_price'])
            exp_date = self._get_0dte_expiration()
            exp_str = exp_date.strftime("%Y%m%d")
            
            # Subscribe to strikes around ATM
            contracts = []
            for offset in range(-10, 11):
                strike = spy_price + offset
                strike_str = f"{strike:06d}"  # Format as 6 digits with leading zeros
                
                # Add call and put
                contracts.append(f"SPY{exp_str}C{strike_str}")
                contracts.append(f"SPY{exp_str}P{strike_str}")
                
            # Send subscription messages
            if self.ws_quote:
                sub_msg = {
                    "action": "subscribe",
                    "contracts": contracts
                }
                await self.ws_quote.send(json.dumps(sub_msg))
                self.logger.info(f"Subscribed to {len(contracts)} option contracts via WebSocket")
                
            if self.ws_trade:
                await self.ws_trade.send(json.dumps(sub_msg))
                self.logger.info("Subscribed to trade stream")
                
            self.subscribed_contracts.update(contracts)
            
        except Exception as e:
            self.logger.error(f"Error subscribing to options: {e}")
            
    async def _on_yahoo_update(self, price: float):
        """Handle Yahoo Finance price update"""
        self.market_data['spy_price_realtime'] = price
        
    async def _market_update_loop(self):
        """Trigger market updates from streaming data"""
        while self.running:
            try:
                if self.on_market_update and self.market_data['timestamp']:
                    # Only trigger if we have fresh data
                    age = (datetime.now() - self.market_data['timestamp']).total_seconds()
                    if age < 5:  # Data less than 5 seconds old
                        await self.on_market_update(self.get_current_snapshot())
                        
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                self.logger.error(f"Market update error: {e}")
                await asyncio.sleep(1)
                
    def _get_0dte_expiration(self) -> date:
        """Get nearest SPY expiration date"""
        today = date.today()
        weekday = today.weekday()
        
        # SPY has expirations Mon/Wed/Fri
        if weekday in [0, 2, 4]:  # Mon, Wed, Fri
            return today
        elif weekday == 1:  # Tuesday -> Wednesday
            return today + timedelta(days=1)
        elif weekday == 3:  # Thursday -> Friday  
            return today + timedelta(days=1)
        else:  # Weekend -> Monday
            days_until_monday = 7 - weekday
            return today + timedelta(days=days_until_monday)
            
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