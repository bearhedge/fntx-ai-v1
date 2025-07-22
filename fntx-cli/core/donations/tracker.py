"""
Donation tracking and persistence
"""
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from collections import defaultdict

from .models import Donation, DonationStatus, DonationSummary
from .calculator import DonationCalculator

logger = logging.getLogger(__name__)


class DonationTracker:
    """Track and manage donation records"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / ".fntx" / "donations"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.donations_file = self.data_dir / "donations.json"
        self.calculator = DonationCalculator()
        self._donations_cache: Dict[str, Donation] = {}
        self._load_donations()
        
    def _load_donations(self):
        """Load donations from disk"""
        if self.donations_file.exists():
            try:
                with open(self.donations_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        donation = Donation(**item)
                        self._donations_cache[donation.id] = donation
                logger.info(f"Loaded {len(self._donations_cache)} donation records")
            except Exception as e:
                logger.error(f"Error loading donations: {e}")
                
    def _save_donations(self):
        """Persist donations to disk"""
        try:
            data = [d.dict() for d in self._donations_cache.values()]
            with open(self.donations_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.debug(f"Saved {len(data)} donation records")
        except Exception as e:
            logger.error(f"Error saving donations: {e}")
            
    def record_donation(self, donation: Donation) -> None:
        """Record a new donation"""
        self._donations_cache[donation.id] = donation
        self._save_donations()
        logger.info(f"Recorded donation {donation.id}: ${donation.donation_amount:.2f}")
        
    def record_trade(
        self,
        trade_id: str,
        entry_price: float,
        exit_price: float,
        quantity: int,
        entry_commission: float = 0.0,
        exit_commission: float = 0.0,
        other_fees: float = 0.0
    ) -> Optional[Donation]:
        """Record a trade and calculate donation if profitable"""
        donation = self.calculator.calculate_donation(
            trade_id=trade_id,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            entry_commission=entry_commission,
            exit_commission=exit_commission,
            other_fees=other_fees
        )
        
        if donation:
            self.record_donation(donation)
            
        return donation
        
    def get_donation(self, donation_id: str) -> Optional[Donation]:
        """Get a specific donation by ID"""
        return self._donations_cache.get(donation_id)
        
    def get_donations_by_status(self, status: DonationStatus) -> List[Donation]:
        """Get all donations with a specific status"""
        return [
            d for d in self._donations_cache.values()
            if d.status == status
        ]
        
    def get_pending_donations(self) -> List[Donation]:
        """Get all pending donations"""
        return self.get_donations_by_status(DonationStatus.CALCULATED)
        
    def mark_donation_sent(self, donation_id: str, transaction_hash: str) -> None:
        """Mark a donation as sent with blockchain transaction hash"""
        donation = self.get_donation(donation_id)
        if donation:
            donation.status = DonationStatus.SENT
            donation.transaction_hash = transaction_hash
            self._save_donations()
            logger.info(f"Donation {donation_id} marked as sent: {transaction_hash}")
            
    def mark_donation_confirmed(self, donation_id: str) -> None:
        """Mark a donation as confirmed on blockchain"""
        donation = self.get_donation(donation_id)
        if donation:
            donation.status = DonationStatus.CONFIRMED
            donation.confirmed_at = datetime.utcnow()
            self._save_donations()
            logger.info(f"Donation {donation_id} confirmed")
            
    def get_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> DonationSummary:
        """Get donation summary statistics"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
            
        # Filter donations by date range
        donations = [
            d for d in self._donations_cache.values()
            if start_date <= d.timestamp <= end_date
        ]
        
        # Calculate summary stats
        summary = DonationSummary(
            period_start=start_date,
            period_end=end_date,
            total_trades=len(donations),
            profitable_trades=len([d for d in donations if d.net_profit > 0]),
            total_gross_profit=sum(d.gross_profit for d in donations),
            total_net_profit=sum(d.net_profit for d in donations),
            total_donated=sum(
                d.donation_amount for d in donations
                if d.status in [DonationStatus.SENT, DonationStatus.CONFIRMED]
            ),
            pending_donations=sum(
                d.donation_amount for d in donations
                if d.status in [DonationStatus.CALCULATED, DonationStatus.SCHEDULED]
            )
        )
        
        # Estimate impact (rough approximation)
        # Assuming $50 per transfusion unit, 2 units per transfusion
        if summary.total_donated > 0:
            summary.estimated_transfusions_funded = int(summary.total_donated / 100)
            summary.estimated_lives_impacted = summary.estimated_transfusions_funded // 12  # Monthly transfusions
            
        return summary
        
    def get_monthly_report(self, year: int, month: int) -> Dict:
        """Generate monthly donation report"""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
            
        summary = self.get_summary(start_date, end_date)
        
        # Get daily breakdown
        daily_donations = defaultdict(float)
        donations = [
            d for d in self._donations_cache.values()
            if start_date <= d.timestamp <= end_date
        ]
        
        for donation in donations:
            day = donation.timestamp.strftime("%Y-%m-%d")
            daily_donations[day] += donation.donation_amount
            
        return {
            "period": f"{year}-{month:02d}",
            "summary": summary.dict(),
            "daily_breakdown": dict(daily_donations),
            "total_donations": len(donations),
            "recipient": DonationCalculator.RECIPIENT_NAME
        }