#!/usr/bin/env python3
"""
Integration for ThetaTerminal data into fntx.ai chatbot
"""
import pandas as pd
from typing import Dict, Any
from 01_backend.api.theta_options_endpoint import ThetaOptionsProvider

class ThetaDataAgent:
    """Agent for handling ThetaTerminal data requests in chat"""
    
    def __init__(self):
        self.provider = ThetaOptionsProvider()
    
    async def process_request(self, user_input: str) -> Dict[str, Any]:
        """Process user requests for option data"""
        
        # Detect what user is asking for
        user_input_lower = user_input.lower()
        
        if "option chain" in user_input_lower or "spy chain" in user_input_lower:
            # Get option chain
            df = self.provider.get_spy_chain()
            
            # Format for display
            formatted_output = self._format_chain(df)
            
            return {
                "type": "option_chain",
                "message": formatted_output,
                "data": df.to_dict('records'),
                "raw_dataframe": df
            }
        
        elif "straddle" in user_input_lower:
            # Get straddle prices
            df = self.provider.get_spy_chain(603, 608)  # Your strikes
            straddle_info = self._format_straddles(df)
            
            return {
                "type": "straddle_prices", 
                "message": straddle_info,
                "data": df.to_dict('records')
            }
            
        elif "my positions" in user_input_lower or "position" in user_input_lower:
            # Check current positions
            position_info = await self._check_positions()
            return {
                "type": "positions",
                "message": position_info
            }
        
        return {
            "type": "unknown",
            "message": "I can help you with:\n- SPY option chain\n- Straddle prices\n- Your current positions"
        }
    
    def _format_chain(self, df: pd.DataFrame) -> str:
        """Format option chain for chat display"""
        output = "📊 **SPY Option Chain**\n\n"
        output += "```\n"
        output += df.to_string(index=False, float_format=lambda x: f'{x:.2f}')
        output += "\n```\n"
        return output
    
    def _format_straddles(self, df: pd.DataFrame) -> str:
        """Format straddle information"""
        output = "📈 **SPY Straddle Prices**\n\n"
        
        for _, row in df.iterrows():
            strike = row['Strike']
            straddle = row['Straddle']
            output += f"**{strike} Straddle**: ${straddle:.2f}\n"
            output += f"  • Put: ${row['Put_Mid']:.2f} ({row['Put_Bid']:.2f}x{row['Put_Ask']:.2f})\n"
            output += f"  • Call: ${row['Call_Mid']:.2f} ({row['Call_Bid']:.2f}x{row['Call_Ask']:.2f})\n\n"
        
        return output
    
    async def _check_positions(self) -> str:
        """Check current positions vs market"""
        # Get current prices
        df = self.provider.get_spy_chain(603, 608)
        
        output = "📋 **Your Positions**\n\n"
        
        # 603 PUT
        put_603 = df[df['Strike'] == 603].iloc[0]
        put_pnl = 0.39 - put_603['Put_Mid']
        output += f"**603 PUT** (Sold @ $0.39)\n"
        output += f"  • Current: ${put_603['Put_Mid']:.2f} ({put_603['Put_Bid']:.2f}x{put_603['Put_Ask']:.2f})\n"
        output += f"  • P&L: ${put_pnl:.2f} ({'✅ Profit' if put_pnl > 0 else '❌ Loss'})\n\n"
        
        # 608 CALL
        call_608 = df[df['Strike'] == 608].iloc[0]
        call_pnl = 0.13 - call_608['Call_Mid']
        output += f"**608 CALL** (Sold @ $0.13)\n"
        output += f"  • Current: ${call_608['Call_Mid']:.2f} ({call_608['Call_Bid']:.2f}x{call_608['Call_Ask']:.2f})\n"
        output += f"  • P&L: ${call_pnl:.2f} ({'✅ Profit' if call_pnl > 0 else '❌ Loss'})\n\n"
        
        total_pnl = (put_pnl + call_pnl) * 100
        output += f"**Total P&L**: ${total_pnl:.2f}"
        
        return output

# Integration function for the main chatbot
async def handle_options_request(user_input: str) -> str:
    """Main integration point for the chatbot"""
    agent = ThetaDataAgent()
    result = await agent.process_request(user_input)
    return result['message']