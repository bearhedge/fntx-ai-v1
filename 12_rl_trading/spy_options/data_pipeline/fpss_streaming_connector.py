"""
True streaming connector using Theta Terminal FPSS (Fast Protocol Streaming Service)
Connects to port 10000 for real-time market data streaming
"""
import asyncio
import socket
import struct
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import numpy as np
from .yahoo_price_fetcher import YahooPriceFetcher


class FPSSStreamingConnector:
    """True streaming connector using FPSS protocol on port 10000"""
    
    def __init__(self):
        # Connection settings
        self.host = "localhost"
        self.fpss_port = 10000  # FPSS streaming port
        self.mdds_port = 11000  # MDDS query port
        
        # Connection state
        self.fpss_reader = None
        self.fpss_writer = None
        self.mdds_reader = None
        self.mdds_writer = None
        self.running = False
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Yahoo Finance for real-time SPY
        self.yahoo_fetcher = YahooPriceFetcher()
        
        # Market data cache
        self.market_data = {
            'spy_price': 0,
            'spy_price_realtime': 0,  # From Yahoo
            'options_chain': {},  # Strike -> option data
            'vix': 0,
            'timestamp': None
        }
        
        # Subscription tracking
        self.subscriptions = set()
        
    async def start(self):
        """Start FPSS streaming connection"""
        self.running = True
        self.logger.info("Starting FPSS streaming connection")
        
        try:
            # Start Yahoo Finance
            await self.yahoo_fetcher.start()
            
            # Connect to FPSS streaming port
            self.fpss_reader, self.fpss_writer = await asyncio.open_connection(
                self.host, self.fpss_port
            )
            self.logger.info(f"Connected to FPSS on port {self.fpss_port}")
            
            # Connect to MDDS query port for initial data
            self.mdds_reader, self.mdds_writer = await asyncio.open_connection(
                self.host, self.mdds_port
            )
            self.logger.info(f"Connected to MDDS on port {self.mdds_port}")
            
            # Get initial SPY price
            await self._query_spy_price()
            
            # Subscribe to SPY stock updates
            await self._subscribe_spy()
            
            # Subscribe to options based on current price
            await self._subscribe_options()
            
            # Start streaming tasks
            self.stream_task = asyncio.create_task(self._stream_handler())
            self.yahoo_task = asyncio.create_task(
                self.yahoo_fetcher.price_update_loop(
                    callback=self._on_yahoo_update,
                    interval=5
                )
            )
            
            self.logger.info("FPSS streaming started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start FPSS streaming: {e}")
            raise
            
    async def stop(self):
        """Stop streaming connection"""
        self.running = False
        
        if self.fpss_writer:
            self.fpss_writer.close()
            await self.fpss_writer.wait_closed()
            
        if self.mdds_writer:
            self.mdds_writer.close()
            await self.mdds_writer.wait_closed()
            
        await self.yahoo_fetcher.stop()
        
        self.logger.info("FPSS streaming stopped")
        
    async def _query_spy_price(self):
        """Query current SPY price via MDDS"""
        try:
            # MDDS protocol: send query for SPY stock quote
            query = {
                "msg_type": "QUERY",
                "sec_type": "STOCK",
                "req_type": "QUOTE",
                "root": "SPY"
            }
            
            await self._send_mdds_message(query)
            response = await self._read_mdds_response()
            
            if response and 'bid' in response and 'ask' in response:
                self.market_data['spy_price'] = (response['bid'] + response['ask']) / 2
                self.logger.info(f"Initial SPY price: ${self.market_data['spy_price']:.2f}")
                
        except Exception as e:
            self.logger.error(f"Error querying SPY price: {e}")
            
    async def _subscribe_spy(self):
        """Subscribe to SPY stock updates"""
        try:
            # FPSS subscription message
            sub_msg = {
                "msg_type": "SUBSCRIBE",
                "sec_type": "STOCK",
                "req_type": "QUOTE",
                "root": "SPY"
            }
            
            await self._send_fpss_message(sub_msg)
            self.subscriptions.add("SPY_STOCK")
            self.logger.info("Subscribed to SPY stock updates")
            
        except Exception as e:
            self.logger.error(f"Error subscribing to SPY: {e}")
            
    async def _subscribe_options(self):
        """Subscribe to 0DTE options around current price"""
        try:
            if self.market_data['spy_price'] <= 0:
                return
                
            spy_price = int(self.market_data['spy_price'])
            exp_date = self._get_0dte_expiration()
            
            # Subscribe to strikes around ATM
            for offset in range(-10, 11):
                strike = spy_price + offset
                
                for right in ['C', 'P']:
                    sub_msg = {
                        "msg_type": "SUBSCRIBE",
                        "sec_type": "OPTION",
                        "req_type": "QUOTE",
                        "root": "SPY",
                        "exp": exp_date,
                        "strike": strike * 1000,  # In thousandths
                        "right": right
                    }
                    
                    await self._send_fpss_message(sub_msg)
                    sub_key = f"SPY_{exp_date}_{strike}_{right}"
                    self.subscriptions.add(sub_key)
                    
            self.logger.info(f"Subscribed to {len(self.subscriptions)-1} option contracts")
            
        except Exception as e:
            self.logger.error(f"Error subscribing to options: {e}")
            
    async def _stream_handler(self):
        """Handle incoming stream messages"""
        while self.running:
            try:
                # Read stream message
                message = await self._read_fpss_message()
                if message:
                    await self._process_stream_message(message)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Stream handler error: {e}")
                await asyncio.sleep(1)
                
    async def _process_stream_message(self, message: dict):
        """Process incoming stream update"""
        try:
            msg_type = message.get('msg_type')
            sec_type = message.get('sec_type')
            
            if msg_type == 'QUOTE':
                if sec_type == 'STOCK':
                    # SPY stock update
                    bid = message.get('bid', 0)
                    ask = message.get('ask', 0)
                    if bid > 0 and ask > 0:
                        self.market_data['spy_price'] = (bid + ask) / 2
                        self.market_data['timestamp'] = datetime.now()
                        
                elif sec_type == 'OPTION':
                    # Option quote update
                    strike = message.get('strike', 0) / 1000
                    right = message.get('right')
                    bid = message.get('bid', 0)
                    ask = message.get('ask', 0)
                    
                    if strike > 0 and right:
                        option_key = f"{int(strike)}_{right}"
                        
                        self.market_data['options_chain'][option_key] = {
                            'strike': int(strike),
                            'type': right,
                            'bid': bid,
                            'ask': ask,
                            'last': (bid + ask) / 2 if bid > 0 or ask > 0 else 0,
                            'volume': message.get('volume', 0),
                            'open_interest': message.get('open_interest', 0),
                            'iv': message.get('iv', self._estimate_iv(strike, self.market_data['spy_price'], right)),
                            'delta': message.get('delta', self._estimate_delta(strike, self.market_data['spy_price'], right)),
                            'gamma': message.get('gamma', 0.01),
                            'theta': message.get('theta', -0.05),
                            'timestamp': datetime.now()
                        }
                        
        except Exception as e:
            self.logger.error(f"Error processing stream message: {e}")
            
    async def _send_fpss_message(self, message: dict):
        """Send message to FPSS stream"""
        if self.fpss_writer:
            data = json.dumps(message).encode() + b'\n'
            self.fpss_writer.write(data)
            await self.fpss_writer.drain()
            
    async def _read_fpss_message(self):
        """Read message from FPSS stream"""
        if self.fpss_reader:
            try:
                data = await self.fpss_reader.readline()
                if data:
                    return json.loads(data.decode().strip())
            except:
                pass
        return None
        
    async def _send_mdds_message(self, message: dict):
        """Send query to MDDS port"""
        if self.mdds_writer:
            data = json.dumps(message).encode() + b'\n'
            self.mdds_writer.write(data)
            await self.mdds_writer.drain()
            
    async def _read_mdds_response(self):
        """Read response from MDDS port"""
        if self.mdds_reader:
            try:
                data = await self.mdds_reader.readline()
                if data:
                    return json.loads(data.decode().strip())
            except:
                pass
        return None
        
    async def _on_yahoo_update(self, price: float):
        """Handle Yahoo Finance price update"""
        self.market_data['spy_price_realtime'] = price
        
    def _get_0dte_expiration(self) -> str:
        """Get today's date for 0DTE options"""
        return datetime.now().strftime('%Y%m%d')
        
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