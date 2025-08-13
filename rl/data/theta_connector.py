"""
Theta Terminal data connector for real-time options data
Handles WebSocket streaming and REST API calls
"""
import asyncio
import json
import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Callable
import numpy as np
from collections import defaultdict
import aiohttp
import websockets


class ThetaDataConnector:
    """Connects to Theta Terminal for real-time SPY options data"""
    
    def __init__(self, api_key: str, rest_url: str = "https://api.thetadata.com/v1"):
        self.api_key = api_key
        self.rest_url = rest_url
        self.ws_url = "wss://stream.thetadata.com"
        
        # Current market snapshot
        self.market_data = {
            'spy': {
                'last': None,
                'bid': None,
                'ask': None,
                'volume': 0,
                'timestamp': None
            },
            'options': {},  # key: symbol, value: option data
            'last_update': None
        }
        
        # Callbacks
        self.on_spy_update = None
        self.on_options_update = None
        
        # Connection state
        self.ws = None
        self.running = False
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    async def start(self):
        """Start WebSocket connection and begin streaming"""
        self.running = True
        
        # First, get initial options chain via REST
        await self._fetch_0dte_chain()
        
        # Then start WebSocket for real-time updates
        await self._connect_websocket()
        
    async def stop(self):
        """Stop streaming and close connections"""
        self.running = False
        if self.ws:
            await self.ws.close()
            
    async def _fetch_0dte_chain(self):
        """Fetch today's expiring options chain via REST API"""
        today = datetime.now().strftime('%Y%m%d')
        
        async with aiohttp.ClientSession() as session:
            # Get SPY options expiring today
            url = f"{self.rest_url}/options/chain"
            params = {
                'root': 'SPY',
                'exp': today,
                'api_key': self.api_key
            }
            
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._process_options_chain(data)
                else:
                    self.logger.error(f"Failed to fetch options chain: {resp.status}")
                    
    def _process_options_chain(self, chain_data: dict):
        """Process options chain data"""
        for option in chain_data.get('options', []):
            symbol = option['symbol']
            self.market_data['options'][symbol] = {
                'strike': float(option['strike']),
                'type': option['type'],  # 'C' or 'P'
                'bid': float(option['bid']),
                'ask': float(option['ask']),
                'last': float(option['last']),
                'iv': float(option['iv']),
                'delta': float(option.get('delta', 0)),
                'volume': int(option.get('volume', 0)),
                'oi': int(option.get('oi', 0)),
                'timestamp': datetime.now()
            }
            
    async def _connect_websocket(self):
        """Connect to Theta WebSocket for real-time data"""
        async with websockets.connect(self.ws_url) as websocket:
            self.ws = websocket
            
            # Authenticate
            auth_msg = {
                'type': 'auth',
                'api_key': self.api_key
            }
            await websocket.send(json.dumps(auth_msg))
            
            # Subscribe to SPY and 0DTE options
            await self._subscribe_to_streams()
            
            # Listen for updates
            while self.running:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    await self._handle_message(json.loads(message))
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    self.logger.error(f"WebSocket error: {e}")
                    break
                    
    async def _subscribe_to_streams(self):
        """Subscribe to required data streams"""
        # Subscribe to SPY quotes
        spy_sub = {
            'type': 'subscribe',
            'symbol': 'SPY',
            'data_type': 'quote'
        }
        await self.ws.send(json.dumps(spy_sub))
        
        # Subscribe to 0DTE options quotes
        for symbol in self.market_data['options'].keys():
            opt_sub = {
                'type': 'subscribe',
                'symbol': symbol,
                'data_type': 'quote'
            }
            await self.ws.send(json.dumps(opt_sub))
            
    async def _handle_message(self, msg: dict):
        """Process incoming WebSocket message"""
        msg_type = msg.get('type')
        
        if msg_type == 'quote':
            symbol = msg['symbol']
            
            if symbol == 'SPY':
                # Update SPY data
                self.market_data['spy'].update({
                    'last': float(msg['last']),
                    'bid': float(msg['bid']),
                    'ask': float(msg['ask']),
                    'volume': int(msg['volume']),
                    'timestamp': datetime.now()
                })
                
                if self.on_spy_update:
                    await self.on_spy_update(self.market_data['spy'])
                    
            elif symbol in self.market_data['options']:
                # Update option data
                opt_data = self.market_data['options'][symbol]
                opt_data.update({
                    'bid': float(msg['bid']),
                    'ask': float(msg['ask']),
                    'last': float(msg['last']),
                    'timestamp': datetime.now()
                })
                
                if self.on_options_update:
                    await self.on_options_update(symbol, opt_data)
                    
        self.market_data['last_update'] = datetime.now()
        
    def get_current_snapshot(self) -> dict:
        """Get current market data snapshot"""
        return {
            'spy_price': self.market_data['spy']['last'],
            'spy_bid': self.market_data['spy']['bid'],
            'spy_ask': self.market_data['spy']['ask'],
            'options_chain': list(self.market_data['options'].values()),
            'timestamp': self.market_data['last_update']
        }
        
    def get_atm_options(self, num_strikes: int = 5) -> List[dict]:
        """Get at-the-money options (closest strikes to spot)"""
        if not self.market_data['spy']['last']:
            return []
            
        spy_price = self.market_data['spy']['last']
        
        # Group by strike
        strikes = defaultdict(dict)
        for symbol, opt in self.market_data['options'].items():
            strike = opt['strike']
            opt_type = opt['type']
            strikes[strike][opt_type] = opt
            
        # Sort by distance from spot
        sorted_strikes = sorted(strikes.keys(), 
                               key=lambda x: abs(x - spy_price))
        
        # Get closest strikes
        atm_options = []
        for strike in sorted_strikes[:num_strikes]:
            if 'C' in strikes[strike] and 'P' in strikes[strike]:
                atm_options.append({
                    'strike': strike,
                    'call': strikes[strike]['C'],
                    'put': strikes[strike]['P']
                })
                
        return atm_options
        
    def get_options_by_delta(self, delta_range: tuple = (0.15, 0.25)) -> List[dict]:
        """Get options within specified delta range"""
        filtered = []
        
        for symbol, opt in self.market_data['options'].items():
            if delta_range[0] <= abs(opt.get('delta', 0)) <= delta_range[1]:
                filtered.append(opt)
                
        return filtered


class MockThetaConnector(ThetaDataConnector):
    """Mock connector for testing without real API"""
    
    def __init__(self):
        super().__init__(api_key="mock")
        self.logger.info("Using mock Theta connector")
        self.update_task = None
        self.last_update_time = None
        
    async def start(self):
        """Generate mock data"""
        self.running = True
        
        # Mock SPY data
        self.market_data['spy'] = {
            'last': 628.50,
            'bid': 628.45,
            'ask': 628.55,
            'volume': 1000000,
            'timestamp': datetime.now()
        }
        
        # Generate mock options chain
        spy_price = self.market_data['spy']['last']
        
        for i in range(-10, 11):  # 21 strikes around ATM
            strike = round(spy_price + i)
            
            # Mock call
            call_symbol = f"SPY{strike}C"
            self.market_data['options'][call_symbol] = {
                'strike': strike,
                'type': 'C',
                'bid': max(0.10, spy_price - strike - 0.50),
                'ask': max(0.15, spy_price - strike - 0.45),
                'last': max(0.12, spy_price - strike - 0.48),
                'iv': 0.15 + abs(i) * 0.01,  # IV smile
                'delta': 0.5 - i * 0.05,
                'volume': 1000 - abs(i) * 50,
                'oi': 5000 - abs(i) * 200,
                'timestamp': datetime.now()
            }
            
            # Mock put
            put_symbol = f"SPY{strike}P"
            self.market_data['options'][put_symbol] = {
                'strike': strike,
                'type': 'P',
                'bid': max(0.10, strike - spy_price - 0.50),
                'ask': max(0.15, strike - spy_price - 0.45),
                'last': max(0.12, strike - spy_price - 0.48),
                'iv': 0.15 + abs(i) * 0.01,  # IV smile
                'delta': -0.5 - i * 0.05,
                'volume': 1000 - abs(i) * 50,
                'oi': 5000 - abs(i) * 200,
                'timestamp': datetime.now()
            }
            
        self.logger.info(f"Mock data initialized: SPY at {spy_price}, "
                        f"{len(self.market_data['options'])} options")
        
        # Don't start continuous updates - let dashboard control update timing
        self.last_update_time = datetime.now()
        
    async def _connect_websocket(self):
        """Mock connector doesn't use websocket - updates are controlled by dashboard"""
        pass
        
    def get_current_snapshot(self) -> dict:
        """Get current market snapshot with controlled updates"""
        # Only update prices if enough time has passed (prevents rapid updates)
        now = datetime.now()
        if self.last_update_time and (now - self.last_update_time).total_seconds() > 0.5:
            # Simulate small price movements
            old_price = self.market_data['spy']['last']
            change = np.random.normal(0, 0.05)  # Smaller changes
            new_price = old_price + change
            
            self.market_data['spy'].update({
                'last': new_price,
                'bid': new_price - 0.05,
                'ask': new_price + 0.05,
                'timestamp': now
            })
            
            # Update option prices based on new spot
            for symbol, opt in self.market_data['options'].items():
                delta = opt.get('delta', 0)
                price_change = delta * change
                
                opt['last'] = max(0.05, opt['last'] + price_change)
                opt['bid'] = max(0.05, opt['bid'] + price_change)
                opt['ask'] = max(0.10, opt['ask'] + price_change)
                opt['timestamp'] = now
                
            self.last_update_time = now
            
        # Return snapshot using parent's method
        return super().get_current_snapshot()


if __name__ == "__main__":
    # Test the mock connector
    async def test():
        connector = MockThetaConnector()
        await connector.start()
        
        # Get a few snapshots
        for i in range(5):
            await asyncio.sleep(2)
            snapshot = connector.get_current_snapshot()
            print(f"\nSnapshot {i+1}:")
            print(f"SPY: ${snapshot['spy_price']:.2f}")
            print(f"Options: {len(snapshot['options_chain'])}")
            
            atm = connector.get_atm_options(3)
            print(f"ATM strikes: {[opt['strike'] for opt in atm]}")
            
    asyncio.run(test())