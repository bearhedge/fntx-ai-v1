"""
Real-time feedback collector for RLHF
Captures user decisions and reasoning for model improvement
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import asyncio
import psycopg2
from psycopg2.extras import Json

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import DB_CONFIG


@dataclass
class FeedbackRecord:
    """Single feedback record from user interaction"""
    timestamp: datetime
    
    # Context
    market_conditions: Dict[str, float]
    model_prediction: Dict[str, float]
    suggested_action: int
    suggested_strike: float
    
    # User response
    user_decision: str  # 'accepted', 'rejected', 'modified'
    user_reasoning: Optional[str] = None
    modified_action: Optional[int] = None
    modified_strike: Optional[float] = None
    
    # Model state
    model_confidence: float = 0.0
    action_probabilities: List[float] = None
    
    # Market outcome (filled later)
    market_outcome: Optional[Dict] = None
    outcome_timestamp: Optional[datetime] = None


class FeedbackCollector:
    """Collects and stores user feedback for RLHF training"""
    
    def __init__(self, save_dir: str = "logs/feedback"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # In-memory buffer
        self.feedback_buffer = []
        self.session_stats = {
            'suggestions_made': 0,
            'suggestions_accepted': 0,
            'suggestions_rejected': 0,
            'feedback_provided': 0
        }
        
        # Database connection
        self.db_conn = None
        
    def connect_database(self) -> bool:
        """Connect to database for persistent storage"""
        try:
            self.db_conn = psycopg2.connect(**DB_CONFIG)
            self._create_feedback_table()
            self.logger.info("RLHF database connection successful")
            return True
        except psycopg2.OperationalError as e:
            self.logger.warning(f"Database not available: {e}")
            self.logger.info("RLHF feedback will be saved to files only")
            return False
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            self.logger.info("RLHF feedback will be saved to files only")
            return False
            
    def _create_feedback_table(self):
        """Create feedback table if it doesn't exist"""
        with self.db_conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading.rlhf_feedback (
                    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    
                    -- Market context
                    spy_price DECIMAL(10,2),
                    vix DECIMAL(10,2),
                    time_of_day INTEGER,  -- minutes since open
                    
                    -- Model suggestion
                    suggested_action INTEGER,
                    suggested_strike DECIMAL(10,2),
                    model_confidence DECIMAL(5,4),
                    action_probabilities JSONB,
                    
                    -- User response
                    user_decision VARCHAR(20),
                    user_reasoning TEXT,
                    modified_action INTEGER,
                    modified_strike DECIMAL(10,2),
                    
                    -- Outcome tracking
                    market_outcome JSONB,
                    outcome_timestamp TIMESTAMP WITH TIME ZONE,
                    
                    -- Session info
                    session_id VARCHAR(50),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.db_conn.commit()
            
    def record_suggestion(self, 
                         market_data: Dict,
                         model_prediction: Dict,
                         suggestion: Dict) -> str:
        """Record a new suggestion for feedback tracking"""
        self.session_stats['suggestions_made'] += 1
        
        # Create feedback record
        feedback = FeedbackRecord(
            timestamp=datetime.now(),
            market_conditions={
                'spy_price': market_data.get('spy_price', 0),
                'vix': market_data.get('vix', 0),
                'time_of_day': self._get_minutes_since_open()
            },
            model_prediction={
                'action': model_prediction.get('action', 0),
                'confidence': model_prediction.get('confidence', 0)
            },
            suggested_action=suggestion['action'],
            suggested_strike=suggestion['strike'],
            model_confidence=model_prediction.get('confidence', 0),
            action_probabilities=model_prediction.get('action_probs', [])
        )
        
        # Add to buffer
        self.feedback_buffer.append(feedback)
        
        # Return ID for tracking
        return f"feedback_{len(self.feedback_buffer)-1}"
        
    def record_user_response(self,
                           feedback_id: str,
                           decision: str,
                           reasoning: Optional[str] = None,
                           modified_suggestion: Optional[Dict] = None):
        """Record user's response to a suggestion"""
        # Extract index from feedback_id
        try:
            idx = int(feedback_id.split('_')[1])
            feedback = self.feedback_buffer[idx]
        except (IndexError, ValueError):
            self.logger.error(f"Invalid feedback ID: {feedback_id}")
            return
            
        # Update feedback record
        feedback.user_decision = decision
        feedback.user_reasoning = reasoning
        
        if modified_suggestion:
            feedback.modified_action = modified_suggestion.get('action')
            feedback.modified_strike = modified_suggestion.get('strike')
            
        # Update stats
        if decision == 'accepted':
            self.session_stats['suggestions_accepted'] += 1
        elif decision == 'rejected':
            self.session_stats['suggestions_rejected'] += 1
            
        if reasoning:
            self.session_stats['feedback_provided'] += 1
            
        # Save to database
        self._save_feedback_to_db(feedback)
        
    def _save_feedback_to_db(self, feedback: FeedbackRecord):
        """Save feedback record to database"""
        if not self.db_conn:
            # Fallback to file storage
            self._save_feedback_to_file(feedback)
            return
            
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO trading.rlhf_feedback (
                        timestamp, spy_price, vix, time_of_day,
                        suggested_action, suggested_strike, model_confidence,
                        action_probabilities, user_decision, user_reasoning,
                        modified_action, modified_strike
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    feedback.timestamp,
                    feedback.market_conditions['spy_price'],
                    feedback.market_conditions['vix'],
                    feedback.market_conditions['time_of_day'],
                    feedback.suggested_action,
                    feedback.suggested_strike,
                    feedback.model_confidence,
                    Json(feedback.action_probabilities),
                    feedback.user_decision,
                    feedback.user_reasoning,
                    feedback.modified_action,
                    feedback.modified_strike
                ))
                self.db_conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to save feedback to DB: {e}")
            self._save_feedback_to_file(feedback)
            
    def _save_feedback_to_file(self, feedback: FeedbackRecord):
        """Save feedback to JSON file as backup"""
        date_str = datetime.now().strftime('%Y%m%d')
        file_path = self.save_dir / f"feedback_{date_str}.jsonl"
        
        feedback_dict = asdict(feedback)
        # Convert datetime objects to strings
        feedback_dict['timestamp'] = feedback_dict['timestamp'].isoformat()
        if feedback_dict['outcome_timestamp']:
            feedback_dict['outcome_timestamp'] = feedback_dict['outcome_timestamp'].isoformat()
            
        with open(file_path, 'a') as f:
            json.dump(feedback_dict, f)
            f.write('\n')
            
    def get_feedback_patterns(self) -> Dict:
        """Analyze feedback patterns for insights"""
        if not self.feedback_buffer:
            return {}
            
        patterns = {
            'common_rejection_reasons': {},
            'acceptance_conditions': [],
            'modification_patterns': []
        }
        
        # Analyze rejection reasons
        for feedback in self.feedback_buffer:
            if feedback.user_decision == 'rejected' and feedback.user_reasoning:
                reason_lower = feedback.user_reasoning.lower()
                
                # Categorize reasons
                if 'strike' in reason_lower:
                    patterns['common_rejection_reasons']['strike_preference'] = \
                        patterns['common_rejection_reasons'].get('strike_preference', 0) + 1
                elif 'timing' in reason_lower or 'wait' in reason_lower:
                    patterns['common_rejection_reasons']['timing'] = \
                        patterns['common_rejection_reasons'].get('timing', 0) + 1
                elif 'risk' in reason_lower:
                    patterns['common_rejection_reasons']['risk_concern'] = \
                        patterns['common_rejection_reasons'].get('risk_concern', 0) + 1
                        
        return patterns
        
    def get_session_summary(self) -> Dict:
        """Get summary of current session"""
        summary = self.session_stats.copy()
        
        if summary['suggestions_made'] > 0:
            summary['acceptance_rate'] = (
                summary['suggestions_accepted'] / summary['suggestions_made']
            )
            summary['feedback_rate'] = (
                summary['feedback_provided'] / summary['suggestions_made']
            )
        else:
            summary['acceptance_rate'] = 0
            summary['feedback_rate'] = 0
            
        # Add pattern analysis
        summary['patterns'] = self.get_feedback_patterns()
        
        return summary
        
    def _get_minutes_since_open(self) -> int:
        """Calculate minutes since market open"""
        now = datetime.now()
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        
        if now < market_open:
            return 0
            
        return int((now - market_open).total_seconds() / 60)
        
    async def update_market_outcome(self, feedback_id: str, outcome: Dict):
        """Update feedback with actual market outcome (async)"""
        try:
            idx = int(feedback_id.split('_')[1])
            feedback = self.feedback_buffer[idx]
            
            feedback.market_outcome = outcome
            feedback.outcome_timestamp = datetime.now()
            
            # Update in database if connected
            if self.db_conn:
                await self._update_outcome_in_db(feedback)
                
        except (IndexError, ValueError):
            self.logger.error(f"Invalid feedback ID for outcome update: {feedback_id}")
            
    async def _update_outcome_in_db(self, feedback: FeedbackRecord):
        """Update market outcome in database"""
        # This would be implemented with async database connection
        pass
        
    def export_for_training(self) -> Path:
        """Export collected feedback for RLHF training"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_path = self.save_dir / f"rlhf_training_data_{timestamp}.json"
        
        # Prepare data for export
        training_data = {
            'session_summary': self.get_session_summary(),
            'feedback_records': []
        }
        
        for feedback in self.feedback_buffer:
            if feedback.user_reasoning:  # Only include records with reasoning
                record = asdict(feedback)
                # Convert timestamps
                record['timestamp'] = record['timestamp'].isoformat()
                if record['outcome_timestamp']:
                    record['outcome_timestamp'] = record['outcome_timestamp'].isoformat()
                training_data['feedback_records'].append(record)
                
        # Save to file
        with open(export_path, 'w') as f:
            json.dump(training_data, f, indent=2)
            
        self.logger.info(f"Exported {len(training_data['feedback_records'])} "
                        f"feedback records to {export_path}")
        
        return export_path