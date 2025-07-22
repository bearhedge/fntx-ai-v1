"""
Stateful Dialogue System
Provides context-aware conversation management with memory.
"""

from .schemas import (
    # Enums
    ConversationRole,
    MessageType,
    ConversationStatus,
    IntentType,
    EntityType,
    
    # Core models
    DialogueMessage,
    Intent,
    ConversationContext,
    ConversationTurn,
    Conversation,
    
    # Summary and analysis
    ConversationSummary,
    
    # Templates and flows
    ResponseTemplate,
    ConversationFlow,
    UserPreferences
)

from .conversation_memory import ConversationMemoryManager
from .dialogue_manager import DialogueManager

__all__ = [
    # Enums
    'ConversationRole',
    'MessageType',
    'ConversationStatus',
    'IntentType',
    'EntityType',
    
    # Core models
    'DialogueMessage',
    'Intent',
    'ConversationContext',
    'ConversationTurn',
    'Conversation',
    
    # Summary and analysis
    'ConversationSummary',
    
    # Templates and flows
    'ResponseTemplate',
    'ConversationFlow',
    'UserPreferences',
    
    # Managers
    'ConversationMemoryManager',
    'DialogueManager'
]