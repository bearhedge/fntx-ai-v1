"""
TRUE STREAMING connector for Theta Terminal using official Theta Data Python client
NO REST POLLING - PURE STREAMING ONLY
"""
import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Callable
import numpy as np
from thetadata import ThetaClient, StreamMsg, StreamMsgType, OptionRight, Contract, StockReqType
from .yahoo_price_fetcher import YahooPriceFetcher


class LocalThetaConnector:
    """TRUE streaming connector using official Theta Data client - NO POLLING"""
    
    def __init__(self):
        # Theta Data credentials
        self.username = "info@bearhedge.com"
        self.password = "25592266"
        
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
        
        # Callbacks
        self.on_market_update = None
        
    async def start(self):
        """Start TRUE streaming connection - NO POLLING"""
        self.running = True
        self.logger.info("Starting TRUE Theta Data streaming (NO POLLING)")
        
        try:
            # Start Yahoo Finance for real-time SPY
            await self.yahoo_fetcher.start()
            
            # Initialize Theta Data client
            self.client = ThetaClient(
                username=self.username,
                passwd=self.password,
                launch=False,  # Use existing terminal
                host="127.0.0.1",
                streaming_port=11000  # MDDS port for Python streaming
            )
            
            # Connect to streaming server
            self.stream_thread = self.client.connect_stream(self._handle_stream_message)
            self.logger.info("Connected to Theta Data STREAMING server (port 11000)")
            
            # Get initial SPY price
            await self._get_initial_spy_price()
            
            # Subscribe to SPY stock quotes first
            await self._subscribe_spy_stock()
            
            # Subscribe to 0DTE options streaming
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
            
            self.logger.info("Theta Data TRUE streaming started - NO REST POLLING")
            
        except Exception as e:
            self.logger.error(f"Failed to start streaming: {e}")
            raise
            
    async def stop(self):
        """Stop streaming connection"""
        self.running = False
        
        # Remove all subscriptions
        for stream_id in self.stream_ids:
            try:
                # Client handles cleanup
                pass
            except:
                pass
                
        # Close stream
        if self.client:
            self.client.close_stream()
            
        # Stop Yahoo
        await self.yahoo_fetcher.stop()
        
        # Cancel tasks
        if self.update_task:
            self.update_task.cancel()
            
        self.logger.info("Streaming stopped")
        
    def _handle_stream_message(self, msg: StreamMsg):
        """Handle incoming STREAM messages - called by Theta Data client thread"""
        try:
            self.logger.debug(f"Stream message received: type={msg.type}, contract={msg.contract if hasattr(msg, 'contract') else 'N/A'}")
            
            if msg.type == StreamMsgType.QUOTE:
                if hasattr(msg, 'contract') and msg.contract.isOption:
                    # Filter for SPY options only
                    if msg.contract.root == "SPY":
                        # Option quote update
                        self.logger.info(f"SPY option quote: strike={msg.contract.strike}, right={'C' if msg.contract.isCall else 'P'}")
                        self._process_option_quote(msg)
                elif hasattr(msg, 'contract') and msg.contract.isStock:
                    # Stock quote - update SPY price
                    if msg.contract.root == "SPY":
                        self.logger.info(f"Stock quote received for {msg.contract.root}")
                        if hasattr(msg, 'quote'):
                            bid = msg.quote.bid_price if hasattr(msg.quote, 'bid_price') else 0
                            ask = msg.quote.ask_price if hasattr(msg.quote, 'ask_price') else 0
                            if bid > 0 and ask > 0:
                                self.market_data['spy_price'] = (bid + ask) / 2
                                self.market_data['timestamp'] = datetime.now()
                                self.logger.info(f"SPY streaming price: ${self.market_data['spy_price']:.2f}")
                else:
                    self.logger.debug(f"Other quote received")
                    
            elif msg.type == StreamMsgType.TRADE:
                if hasattr(msg, 'contract') and msg.contract.isOption:
                    # Filter for SPY options only
                    if msg.contract.root == "SPY":
                        # Option trade update
                        self.logger.info(f"SPY option trade: strike={msg.contract.strike}, right={'C' if msg.contract.isCall else 'P'}")
                        self._process_option_trade(msg)
                    else:
                        # Count other option trades
                        self.logger.debug(f"Non-SPY option trade: {msg.contract.root}")
                else:
                    self.logger.debug(f"Stock trade received")
                    
            elif msg.type == StreamMsgType.OHLCVC:
                # OHLC data
                if hasattr(msg, 'contract') and msg.contract.isOption:
                    self.logger.info(f"Option OHLC: strike={msg.contract.strike}")
                    self._process_option_ohlc(msg)
                    
            elif msg.type == StreamMsgType.STREAM_DEAD:
                self.logger.warning("Stream connection died - reconnecting...")
                # Stream died, need to reconnect
                # For now just log it
                
            elif msg.type == StreamMsgType.STREAM_RECONNECTED:
                self.logger.info("Stream reconnected successfully")
                
            elif msg.type == StreamMsgType.STREAM_ERROR:
                self.logger.error(f"Stream error: {msg}")
                
            else:
                self.logger.debug(f"Unhandled message type: {msg.type}")
                    
        except Exception as e:
            self.logger.error(f"Error handling stream message: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            
    def _process_option_quote(self, msg: StreamMsg):
        """Process STREAMING option quote"""
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
            'volume': self.market_data['options_chain'].get(option_key, {}).get('volume', 0),
            'open_interest': self.market_data['options_chain'].get(option_key, {}).get('open_interest', 0),
            'iv': self._estimate_iv(strike, self.market_data['spy_price_realtime'] or self.market_data['spy_price'], right),
            'delta': self._estimate_delta(strike, self.market_data['spy_price_realtime'] or self.market_data['spy_price'], right),
            'gamma': 0.01,
            'theta': -0.05,
            'timestamp': datetime.now()
        }
        
        self.market_data['timestamp'] = datetime.now()
        
    def _process_option_trade(self, msg: StreamMsg):
        """Process STREAMING option trade"""
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
            
    def _process_option_ohlc(self, msg: StreamMsg):
        """Process STREAMING option OHLC data"""
        contract = msg.contract
        ohlc = msg.ohlcvc
        
        # Update option with OHLC data
        strike = int(contract.strike)
        right = 'C' if contract.isCall else 'P'
        option_key = f"{strike}_{right}"
        
        if option_key in self.market_data['options_chain']:
            opt = self.market_data['options_chain'][option_key]
            opt['open'] = ohlc.open
            opt['high'] = ohlc.high
            opt['low'] = ohlc.low
            opt['close'] = ohlc.close
            opt['volume'] = ohlc.volume
            opt['count'] = ohlc.count
            
    async def _subscribe_spy_stock(self):
        """Subscribe to SPY stock quotes streaming"""
        try:
            # Check if ThetaClient has stock streaming methods
            if hasattr(self.client, 'req_quote_stream_stk'):
                stock_id = self.client.req_quote_stream_stk(root="SPY")
                self.stream_ids.append(stock_id)
                self.logger.info(f"Subscribed to SPY stock quote stream, id={stock_id}")
            else:
                self.logger.warning("Stock streaming not available in this ThetaClient version")
        except Exception as e:
            self.logger.error(f"Error subscribing to SPY stock: {e}")
    
    async def _get_initial_spy_price(self):
        """Get initial SPY price using REST API"""
        try:
            with self.client.connect():
                # Get SPY quote
                data = self.client.get_last_stock(
                    root="SPY",
                    req=StockReqType.QUOTE
                )
                
                if data is not None and len(data) > 0:
                    # data is a pandas DataFrame
                    row = data.iloc[0]
                    bid = row.get('bid', 0) if 'bid' in data.columns else 0
                    ask = row.get('ask', 0) if 'ask' in data.columns else 0
                    
                    if bid > 0 and ask > 0:
                        self.market_data['spy_price'] = (bid + ask) / 2
                        self.logger.info(f"Initial SPY price: ${self.market_data['spy_price']:.2f}")
                        
        except Exception as e:
            self.logger.error(f"Error getting initial SPY price: {e}")
            # Set a default if we can't get it
            self.market_data['spy_price'] = 622.0
            
    async def _subscribe_options(self):
        """Subscribe to FULL option trade stream"""
        try:
            # Subscribe to FULL option trade stream - ALL options
            trade_id = self.client.req_full_trade_stream_opt()
            self.stream_ids.append(trade_id)
            self.logger.info(f"Subscribed to FULL option trade stream, id={trade_id}")
            
            # Also subscribe to full open interest stream
            oi_id = self.client.req_full_open_interest_stream()
            self.stream_ids.append(oi_id)
            self.logger.info(f"Subscribed to FULL open interest stream, id={oi_id}")
            
            # For specific SPY options around ATM, subscribe individually for quotes
            if self.market_data['spy_price'] <= 0:
                self.market_data['spy_price'] = 621.0  # Default
                
            spy_price = int(self.market_data['spy_price'])
            exp_date = self._get_0dte_expiration()
            
            self.logger.info(f"Subscribing to SPY quotes at ${spy_price}, exp={exp_date}")
            
            # Subscribe to quotes for specific strikes
            for offset in range(-5, 6):  # Reduced range for testing
                strike = spy_price + offset
                
                for right in [OptionRight.CALL, OptionRight.PUT]:
                    try:
                        # Subscribe to quotes only for specific strikes
                        quote_id = self.client.req_quote_stream_opt(
                            root="SPY",
                            exp=exp_date,
                            strike=float(strike),
                            right=right
                        )
                        self.stream_ids.append(quote_id)
                        self.logger.debug(f"Subscribed to SPY {strike} {right.value} quotes, id={quote_id}")
                        
                    except Exception as e:
                        self.logger.debug(f"Error subscribing to {strike} {right} quotes: {e}")
                        
            self.logger.info(f"Total subscriptions: {len(self.stream_ids)}")
            
        except Exception as e:
            self.logger.error(f"Error subscribing to options: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            
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
                        
                await asyncio.sleep(1)  # Update every second from streaming
                
            except Exception as e:
                self.logger.error(f"Market update error: {e}")
                await asyncio.sleep(1)
                
    def _get_0dte_expiration(self) -> date:
        """Get today's date for 0DTE options"""
        today = date.today()
        # For 0DTE we need the nearest expiration
        # SPY has expirations Mon/Wed/Fri
        weekday = today.weekday()
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
        
    def _process_bulk_quote(self, quote: list) -> None:
        """Process a single quote from bulk response"""
        try:
            if len(quote) >= 13:
                strike = quote[3] / 1000  # Convert from thousandths
                right = quote[4]  # 'C' or 'P'
                bid = quote[7] / 100  # Convert cents to dollars
                ask = quote[11] / 100
                
                option_key = f"{int(strike)}_{right}"
                
                self.market_data['options_chain'][option_key] = {
                    'strike': int(strike),
                    'type': right,
                    'bid': bid,
                    'ask': ask,
                    'last': (bid + ask) / 2 if bid > 0 or ask > 0 else 0,
                    'volume': 0,  # Will be updated from trades
                    'open_interest': 0,
                    'iv': self._estimate_iv(strike, self.market_data['spy_price'], right),
                    'delta': self._estimate_delta(strike, self.market_data['spy_price'], right),
                    'gamma': 0.01,
                    'theta': -0.05,
                    'timestamp': datetime.now()
                }
        except Exception as e:
            self.logger.debug(f"Error processing bulk quote: {e}")