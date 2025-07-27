"""
Donation data models
"""
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DonationStatus(Enum):
    """Status of a donation"""
    PENDING = "pending"
    CALCULATED = "calculated"
    SCHEDULED = "scheduled"
    SENT = "sent"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class Donation(BaseModel):
    """Donation record model"""
    id: str = Field(description="Unique donation ID")
    trade_id: str = Field(description="Associated trade ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Financial details
    gross_profit: float = Field(description="Gross profit from trade")
    commissions: float = Field(description="Total commissions paid")
    net_profit: float = Field(description="Net profit after commissions")
    donation_amount: float = Field(description="1% of net profit")
    
    # Donation details
    recipient: str = Field(default="Thalassaemia Foundation")
    recipient_address: Optional[str] = Field(default=None, description="Blockchain address")
    
    # Status tracking
    status: DonationStatus = Field(default=DonationStatus.PENDING)
    transaction_hash: Optional[str] = Field(default=None, description="Blockchain tx hash")
    confirmed_at: Optional[datetime] = Field(default=None)
    
    # Metadata
    notes: Optional[str] = Field(default=None)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DonationSummary(BaseModel):
    """Summary statistics for donations"""
    total_trades: int = 0
    profitable_trades: int = 0
    total_gross_profit: float = 0.0
    total_net_profit: float = 0.0
    total_donated: float = 0.0
    pending_donations: float = 0.0
    
    # Time-based stats
    period_start: datetime
    period_end: datetime
    
    # Impact metrics
    estimated_transfusions_funded: int = 0
    estimated_lives_impacted: int = 0