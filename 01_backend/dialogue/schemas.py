"""
Stateful Dialogue System Schemas
Data models for conversation management and context tracking.
"""

from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class ConversationRole(str, Enum):
    """Roles in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    AGENT = "agent"


class MessageType(str, Enum):
    """Types of messages in dialogue."""
    QUERY = "query"
    RESPONSE = "response"
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"
    ACTION = "action"
    NOTIFICATION = "notification"
    ERROR = "error"


class ConversationStatus(str, Enum):
    """Status of a conversation."""
    ACTIVE = "active"
    PAUSED = "paused"
    WAITING_INPUT = "waiting_input"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class IntentType(str, Enum):
    """Types of user intents."""
    # Trading intents
    EXECUTE_TRADE = "execute_trade"
    ANALYZE_MARKET = "analyze_market"
    CHECK_POSITIONS = "check_positions"
    MODIFY_STRATEGY = "modify_strategy"
    
    # Information intents
    REQUEST_STATUS = "request_status"
    REQUEST_METRICS = "request_metrics"
    REQUEST_EXPLANATION = "request_explanation"
    
    # Control intents
    START_SESSION = "start_session"
    STOP_SESSION = "stop_session"
    PAUSE_TRADING = "pause_trading"
    RESUME_TRADING = "resume_trading"
    
    # Configuration intents
    UPDATE_SETTINGS = "update_settings"
    CHANGE_RISK_PARAMS = "change_risk_params"
    
    # General intents
    GREETING = "greeting"
    HELP = "help"
    UNCLEAR = "unclear"


class EntityType(str, Enum):
    """Types of entities in messages."""
    SYMBOL = "symbol"
    PRICE = "price"
    QUANTITY = "quantity"
    DATE = "date"
    PERCENTAGE = "percentage"
    STRATEGY = "strategy"
    AGENT = "agent"
    METRIC = "metric"


class DialogueMessage(BaseModel):
    """Individual message in a dialogue."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = Field(..., description="Parent conversation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Message content
    role: ConversationRole = Field(..., description="Message sender role")
    content: str = Field(..., description="Message text content")
    message_type: MessageType = Field(..., description="Type of message")
    
    # Structured data
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional message metadata"
    )
    attachments: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Attached data (charts, tables, etc.)"
    )
    
    # Context
    in_reply_to: Optional[str] = Field(None, description="ID of message being replied to")
    thread_id: Optional[str] = Field(None, description="Thread within conversation")
    
    # Processing
    processed: bool = Field(default=False, description="Whether message was processed")
    processing_time_ms: Optional[float] = Field(None, description="Time to process")


class Intent(BaseModel):
    """Extracted intent from user message."""
    intent_type: IntentType = Field(..., description="Type of intent")
    confidence: float = Field(..., description="Confidence score (0-1)")
    
    # Parameters
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Intent parameters"
    )
    
    # Entities
    entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Extracted entities"
    )
    
    # Context requirements
    requires_confirmation: bool = Field(
        default=False,
        description="Whether intent requires confirmation"
    )
    requires_auth: bool = Field(
        default=False,
        description="Whether intent requires authentication"
    )


class ConversationContext(BaseModel):
    """Context maintained during a conversation."""
    # Current state
    active_topic: Optional[str] = Field(None, description="Current discussion topic")
    active_intent: Optional[Intent] = Field(None, description="Intent being processed")
    
    # Session linkage
    session_id: Optional[str] = Field(None, description="Linked trading session")
    agent_states: Dict[str, str] = Field(
        default_factory=dict,
        description="States of involved agents"
    )
    
    # Working memory
    working_memory: Dict[str, Any] = Field(
        default_factory=dict,
        description="Short-term context storage"
    )
    
    # Entity tracking
    mentioned_entities: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Entities mentioned in conversation"
    )
    
    # Dialogue state
    awaiting_response: bool = Field(default=False, description="Waiting for user input")
    clarification_needed: Optional[str] = Field(None, description="What needs clarification")
    
    # Action tracking
    pending_actions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Actions awaiting execution"
    )
    completed_actions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Completed actions in conversation"
    )


class ConversationTurn(BaseModel):
    """A complete turn in conversation (user message + assistant response)."""
    turn_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = Field(..., description="Parent conversation")
    turn_number: int = Field(..., description="Sequential turn number")
    
    # Messages
    user_message: DialogueMessage = Field(..., description="User's message")
    assistant_messages: List[DialogueMessage] = Field(
        ...,
        description="Assistant's response(s)"
    )
    
    # Understanding
    extracted_intent: Optional[Intent] = Field(None, description="Understood intent")
    sentiment: Optional[str] = Field(None, description="User sentiment")
    
    # Outcome
    success: bool = Field(default=True, description="Whether turn was successful")
    error_message: Optional[str] = Field(None, description="Error if any")
    
    # Timing
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = Field(None, description="When turn completed")
    total_duration_ms: Optional[float] = Field(None, description="Total turn duration")


class ConversationSummary(BaseModel):
    """Summary of conversation for quick reference."""
    conversation_id: str = Field(..., description="Conversation being summarized")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Key points
    main_topics: List[str] = Field(..., description="Main topics discussed")
    key_decisions: List[str] = Field(..., description="Important decisions made")
    actions_taken: List[str] = Field(..., description="Actions executed")
    
    # Outcomes
    objectives_achieved: List[str] = Field(
        default_factory=list,
        description="User objectives that were met"
    )
    unresolved_items: List[str] = Field(
        default_factory=list,
        description="Items left unresolved"
    )
    
    # Metrics
    user_satisfaction: Optional[float] = Field(
        None,
        description="Estimated satisfaction (0-1)"
    )
    efficiency_score: Optional[float] = Field(
        None,
        description="Conversation efficiency (0-1)"
    )


class Conversation(BaseModel):
    """Complete conversation with full history and context."""
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User identifier")
    status: ConversationStatus = Field(default=ConversationStatus.ACTIVE)
    
    # Temporal
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = Field(None, description="When conversation ended")
    
    # Content
    turns: List[ConversationTurn] = Field(
        default_factory=list,
        description="All conversation turns"
    )
    messages: List[DialogueMessage] = Field(
        default_factory=list,
        description="All messages in order"
    )
    
    # Context
    context: ConversationContext = Field(
        default_factory=ConversationContext,
        description="Current conversation context"
    )
    
    # Summary
    summary: Optional[ConversationSummary] = Field(
        None,
        description="Conversation summary"
    )
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Conversation tags")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    # Continuity
    previous_conversation_id: Optional[str] = Field(
        None,
        description="Previous conversation in chain"
    )
    next_conversation_id: Optional[str] = Field(
        None,
        description="Next conversation in chain"
    )


class ResponseTemplate(BaseModel):
    """Template for generating responses."""
    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Template name")
    
    # Matching
    intent_types: List[IntentType] = Field(..., description="Intents this handles")
    conditions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Conditions for using template"
    )
    
    # Content
    template_text: str = Field(..., description="Response template with variables")
    variables: List[str] = Field(..., description="Required variables")
    
    # Variations
    variations: List[str] = Field(
        default_factory=list,
        description="Alternative phrasings"
    )
    
    # Tone
    formality: str = Field(default="professional", description="Response formality")
    personality_traits: List[str] = Field(
        default_factory=list,
        description="Personality traits to express"
    )
    
    # Usage
    usage_count: int = Field(default=0, description="Times template used")
    last_used: Optional[datetime] = Field(None, description="Last usage time")
    effectiveness_score: Optional[float] = Field(
        None,
        description="Template effectiveness"
    )


class ConversationFlow(BaseModel):
    """Defines a conversation flow pattern."""
    flow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Flow name")
    description: str = Field(..., description="Flow description")
    
    # Flow definition
    initial_intent: IntentType = Field(..., description="Starting intent")
    steps: List[Dict[str, Any]] = Field(..., description="Flow steps")
    
    # Branching
    decision_points: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Points where flow branches"
    )
    
    # End conditions
    success_conditions: List[Dict[str, Any]] = Field(
        ...,
        description="Conditions for successful completion"
    )
    failure_conditions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Conditions for flow failure"
    )
    
    # Timeouts
    max_duration: timedelta = Field(
        default=timedelta(minutes=30),
        description="Maximum flow duration"
    )
    idle_timeout: timedelta = Field(
        default=timedelta(minutes=5),
        description="Timeout for user inactivity"
    )


class UserPreferences(BaseModel):
    """User's dialogue preferences."""
    user_id: str = Field(..., description="User identifier")
    
    # Communication style
    preferred_formality: str = Field(
        default="professional",
        description="Preferred communication formality"
    )
    technical_level: str = Field(
        default="intermediate",
        description="Technical understanding level"
    )
    
    # Interaction preferences
    confirmation_required: bool = Field(
        default=True,
        description="Require confirmation for actions"
    )
    detailed_explanations: bool = Field(
        default=True,
        description="Provide detailed explanations"
    )
    
    # Notification preferences
    notify_on_trades: bool = Field(default=True, description="Notify on trade execution")
    notify_on_alerts: bool = Field(default=True, description="Notify on market alerts")
    
    # Response preferences
    max_response_length: int = Field(
        default=500,
        description="Maximum response length in characters"
    )
    include_visualizations: bool = Field(
        default=True,
        description="Include charts and graphs"
    )
    
    # Learning
    adapt_to_patterns: bool = Field(
        default=True,
        description="Learn from interaction patterns"
    )
    remembered_contexts: List[str] = Field(
        default_factory=list,
        description="Contexts to remember across conversations"
    )