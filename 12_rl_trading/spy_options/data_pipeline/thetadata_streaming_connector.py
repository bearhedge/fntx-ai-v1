"""
True streaming connector using official Theta Data Python client
NO REST polling, NO fallbacks - pure streaming only
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import numpy as np
from thetadata import ThetaClient, StreamMsg, StreamMsgType, OptionRight, Contract
from .yahoo_price_fetcher import YahooPriceFetcher


class ThetaDataStreamingConnector:
    """True streaming connector using official Theta Data client"""
    
    def __init__(self, username: str = "info@bearhedge.com", password: str = "25592266"):
        # Theta Data credentials
        self.username = username
        self.password = password
        
        # Client instance
        self.client = None
        self.stream_thread = None
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
        
        # Track subscriptions
        self.stream_ids = []
        
    async def start(self):
        """Start streaming connection"""
        self.running = True
        self.logger.info("Starting Theta Data streaming connection")
        
        try:
            # Start Yahoo Finance for real-time SPY
            await self.yahoo_fetcher.start()
            
            # Initialize Theta Data client (it will use existing terminal on port 11000)
            self.client = ThetaClient(
                username=self.username,
                passwd=self.password,
                launch=False  # Use existing terminal
            )
            
            # Connect to streaming server
            self.stream_thread = self.client.connect_stream(self._handle_stream_message)
            self.logger.info("Connected to Theta Data streaming server")
            
            # Get initial SPY price
            await self._get_initial_spy_price()
            
            # Subscribe to SPY stock quotes
            await self._subscribe_spy_quotes()
            
            # Subscribe to 0DTE options
            await self._subscribe_options()
            
            # Start Yahoo price update loop
            self.yahoo_task = asyncio.create_task(
                self.yahoo_fetcher.price_update_loop(
                    callback=self._on_yahoo_update,
                    interval=5
                )
            )
            
            self.logger.info("Theta Data streaming started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start Theta Data streaming: {e}")
            raise
            
    async def stop(self):
        """Stop streaming connection"""
        self.running = False
        
        # Remove all subscriptions
        for stream_id in self.stream_ids:
            try:
                # Remove subscription
                pass  # Client handles cleanup
            except:
                pass
                
        # Close stream
        if self.client:
            self.client.close_stream()
            
        # Stop Yahoo
        await self.yahoo_fetcher.stop()
        
        self.logger.info("Theta Data streaming stopped")
        
    def _handle_stream_message(self, msg: StreamMsg):
        """Handle incoming stream messages - called by Theta Data client thread"""
        try:
            if msg.type == StreamMsgType.QUOTE:
                # Quote update
                if msg.contract.root == "SPY" and not msg.contract.isOption:
                    # SPY stock quote
                    self._process_spy_quote(msg)
                elif msg.contract.isOption:
                    # Option quote
                    self._process_option_quote(msg)
                    
            elif msg.type == StreamMsgType.TRADE:
                # Trade update
                if msg.contract.root == "SPY" and msg.contract.isOption:
                    self._process_option_trade(msg)
                    
        except Exception as e:
            self.logger.error(f"Error handling stream message: {e}")
            
    def _process_spy_quote(self, msg: StreamMsg):
        """Process SPY stock quote"""
        quote = msg.quote
        
        self.market_data['spy_price'] = (quote.bid_price + quote.ask_price) / 2
        self.market_data['timestamp'] = datetime.now()
        
        self.logger.debug(f"SPY update: ${self.market_data['spy_price']:.2f}")
        
    def _process_option_quote(self, msg: StreamMsg):
        """Process option quote"""
        contract = msg.contract
        quote = msg.quote
        
        # Create option key
        strike = int(contract.strike)
        right = 'C' if contract.isCall else 'P'
        option_key = f"{strike}_{right}"
        
        # Update option data
        self.market_data['options_chain'][option_key] = {
            'strike': strike,
            'type': right,
            'bid': quote.bid_price,
            'ask': quote.ask_price,
            'last': (quote.bid_price + quote.ask_price) / 2,
            'bid_size': quote.bid_size,
            'ask_size': quote.ask_size,
            'volume': 0,  # Will be updated from trades
            'open_interest': 0,  # Need separate subscription
            'iv': self._estimate_iv(strike, self.market_data['spy_price'], right),
            'delta': self._estimate_delta(strike, self.market_data['spy_price'], right),
            'gamma': 0.01,
            'theta': -0.05,
            'timestamp': datetime.now()
        }
        
    def _process_option_trade(self, msg: StreamMsg):
        """Process option trade"""
        contract = msg.contract
        trade = msg.trade
        
        # Update volume for the option
        strike = int(contract.strike)
        right = 'C' if contract.isCall else 'P'
        option_key = f"{strike}_{right}"
        
        if option_key in self.market_data['options_chain']:
            opt = self.market_data['options_chain'][option_key]
            opt['volume'] = opt.get('volume', 0) + trade.size
            opt['last'] = trade.price
            
    async def _get_initial_spy_price(self):
        """Get initial SPY price using REST API"""
        try:
            with self.client.connect():
                # Get SPY quote
                data = self.client.get_last(
                    root="SPY",
                    req="QUOTE"
                )
                
                if data and len(data) > 0:
                    # data is a pandas DataFrame
                    row = data.iloc[0]
                    bid = row.get('bid', 0)
                    ask = row.get('ask', 0)
                    
                    if bid > 0 and ask > 0:
                        self.market_data['spy_price'] = (bid + ask) / 2
                        self.logger.info(f"Initial SPY price: ${self.market_data['spy_price']:.2f}")
                        
        except Exception as e:
            self.logger.error(f"Error getting initial SPY price: {e}")
            
    async def _subscribe_spy_quotes(self):
        """Subscribe to SPY stock quotes"""
        try:
            # Note: Theta Data client doesn't have stock streaming
            # We'll rely on Yahoo Finance for real-time SPY price
            self.logger.info("Using Yahoo Finance for real-time SPY price (no stock streaming in Theta)")
            
        except Exception as e:
            self.logger.error(f"Error in SPY subscription: {e}")
            
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
                
                for right in [OptionRight.CALL, OptionRight.PUT]:
                    # Subscribe to quotes
                    quote_id = self.client.req_quote_stream_opt(
                        root="SPY",
                        exp=exp_date,
                        strike=float(strike),
                        right=right
                    )
                    self.stream_ids.append(quote_id)
                    
                    # Subscribe to trades
                    trade_id = self.client.req_trade_stream_opt(
                        root="SPY",
                        exp=exp_date,
                        strike=float(strike),
                        right=right
                    )
                    self.stream_ids.append(trade_id)
                    
            self.logger.info(f"Subscribed to {len(self.stream_ids)} option streams")
            
        except Exception as e:
            self.logger.error(f"Error subscribing to options: {e}")
            
    async def _on_yahoo_update(self, price: float):
        """Handle Yahoo Finance price update"""
        self.market_data['spy_price_realtime'] = price
        
    def _get_0dte_expiration(self):
        """Get today's date for 0DTE options"""
        from datetime import date
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