"""
Donation calculator for 1% founder's fee on net profits
"""
import logging
from typing import Optional
from datetime import datetime
import uuid

from .models import Donation, DonationStatus

logger = logging.getLogger(__name__)


class DonationCalculator:
    """Calculate 1% donation on net profits"""
    
    DONATION_PERCENTAGE = 0.01  # 1% of net profits
    RECIPIENT_NAME = "Thalassaemia Foundation"
    
    def __init__(self, recipient_address: Optional[str] = None):
        self.recipient_address = recipient_address
        
    def calculate_donation(
        self,
        trade_id: str,
        entry_price: float,
        exit_price: float,
        quantity: int,
        entry_commission: float = 0.0,
        exit_commission: float = 0.0,
        other_fees: float = 0.0
    ) -> Optional[Donation]:
        """
        Calculate donation amount from trade results
        
        Args:
            trade_id: Unique identifier for the trade
            entry_price: Price at trade entry
            exit_price: Price at trade exit
            quantity: Number of contracts/shares
            entry_commission: Commission paid on entry
            exit_commission: Commission paid on exit
            other_fees: Any other fees (exchange, regulatory, etc.)
            
        Returns:
            Donation object if profit > 0, None otherwise
        """
        # Calculate gross profit
        gross_profit = (exit_price - entry_price) * quantity
        
        # Calculate total costs
        total_commissions = entry_commission + exit_commission + other_fees
        
        # Calculate net profit
        net_profit = gross_profit - total_commissions
        
        # Only donate on profitable trades
        if net_profit <= 0:
            logger.info(f"Trade {trade_id} not profitable (net: ${net_profit:.2f}), no donation")
            return None
            
        # Calculate 1% donation
        donation_amount = net_profit * self.DONATION_PERCENTAGE
        
        # Create donation record
        donation = Donation(
            id=str(uuid.uuid4()),
            trade_id=trade_id,
            gross_profit=gross_profit,
            commissions=total_commissions,
            net_profit=net_profit,
            donation_amount=donation_amount,
            recipient=self.RECIPIENT_NAME,
            recipient_address=self.recipient_address,
            status=DonationStatus.CALCULATED,
            notes=f"1% of net profit from trade {trade_id}"
        )
        
        logger.info(
            f"Donation calculated for trade {trade_id}: "
            f"${donation_amount:.2f} (1% of ${net_profit:.2f} net profit)"
        )
        
        return donation
        
    def calculate_from_option_trade(
        self,
        trade_id: str,
        premium_collected: float,
        premium_paid: float,
        quantity: int,
        total_commissions: float = 0.0
    ) -> Optional[Donation]:
        """
        Calculate donation from options trade (simplified for premiums)
        
        Args:
            trade_id: Unique identifier for the trade
            premium_collected: Total premium collected (selling options)
            premium_paid: Total premium paid (buying options)
            quantity: Number of contracts
            total_commissions: All commissions and fees
            
        Returns:
            Donation object if profit > 0, None otherwise
        """
        # For options, profit is premium collected minus premium paid
        gross_profit = (premium_collected - premium_paid) * quantity * 100  # x100 for options
        
        # Calculate net profit
        net_profit = gross_profit - total_commissions
        
        # Only donate on profitable trades
        if net_profit <= 0:
            logger.info(f"Options trade {trade_id} not profitable (net: ${net_profit:.2f}), no donation")
            return None
            
        # Calculate 1% donation
        donation_amount = net_profit * self.DONATION_PERCENTAGE
        
        # Create donation record
        donation = Donation(
            id=str(uuid.uuid4()),
            trade_id=trade_id,
            gross_profit=gross_profit,
            commissions=total_commissions,
            net_profit=net_profit,
            donation_amount=donation_amount,
            recipient=self.RECIPIENT_NAME,
            recipient_address=self.recipient_address,
            status=DonationStatus.CALCULATED,
            notes=f"1% of net profit from options trade {trade_id}"
        )
        
        logger.info(
            f"Donation calculated for options trade {trade_id}: "
            f"${donation_amount:.2f} (1% of ${net_profit:.2f} net profit)"
        )
        
        return donation