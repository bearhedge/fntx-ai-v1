"""
Dialogue Manager
Manages context-aware conversations with users.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Callable
from datetime import datetime, timedelta
import json

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from ..session.lifecycle_manager import SessionLifecycleManager
from ..session.schemas import SessionStatus, SessionType
from .conversation_memory import ConversationMemoryManager
from .schemas import (
    Conversation, ConversationStatus, DialogueMessage, ConversationRole,
    MessageType, ConversationTurn, Intent, IntentType, EntityType,
    ResponseTemplate, ConversationFlow, UserPreferences
)

logger = logging.getLogger(__name__)


class DialogueManager:
    """
    Manages stateful dialogue with context awareness and memory.
    """
    
    def __init__(self, mcp_manager: MCPContextManager,
                 conversation_memory: ConversationMemoryManager,
                 session_manager: Optional[SessionLifecycleManager] = None):
        self.mcp = mcp_manager
        self.memory = conversation_memory
        self.session_manager = session_manager
        
        # Active conversations
        self._active_conversations: Dict[str, Conversation] = {}
        self._conversation_locks: Dict[str, asyncio.Lock] = {}
        
        # Response templates
        self._response_templates: Dict[str, ResponseTemplate] = {}
        self._load_default_templates()
        
        # Conversation flows
        self._conversation_flows: Dict[str, ConversationFlow] = {}
        self._load_default_flows()
        
        # Intent handlers
        self._intent_handlers: Dict[IntentType, Callable] = {}
        self._register_default_handlers()
        
        # User preferences cache
        self._user_preferences: Dict[str, UserPreferences] = {}
        
        # Configuration
        self.default_timeout = timedelta(minutes=30)
        self.typing_indicator_delay = 0.5
        self.max_response_length = 500
        
    async def initialize(self) -> None:
        """Initialize the dialogue manager."""
        # Register with MCP
        await self.mcp.register_agent(
            "DialogueManager",
            ["conversation_management", "intent_processing", "response_generation"]
        )
        
        # Initialize memory manager
        await self.memory.initialize()
        
        logger.info("Dialogue Manager initialized")
        
    # Conversation Management
    
    async def start_conversation(self, user_id: str,
                               initial_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a new conversation with a user.
        
        Args:
            user_id: User identifier
            initial_message: Optional opening message
            
        Returns:
            Conversation start response
        """
        # Create conversation
        conversation = await self.memory.create_conversation(user_id)
        
        # Add to active conversations
        self._active_conversations[conversation.conversation_id] = conversation
        self._conversation_locks[conversation.conversation_id] = asyncio.Lock()
        
        # Load user preferences
        preferences = await self._load_user_preferences(user_id)
        self._user_preferences[user_id] = preferences
        
        # Generate greeting
        response = await self._generate_greeting(conversation, preferences)
        
        # Process initial message if provided
        if initial_message:
            user_msg = DialogueMessage(
                conversation_id=conversation.conversation_id,
                role=ConversationRole.USER,
                content=initial_message,
                message_type=MessageType.QUERY
            )
            
            await self.memory.add_message(conversation.conversation_id, user_msg)
            
            # Process the message
            turn_response = await self.process_message(
                conversation.conversation_id,
                initial_message
            )
            
            return {
                'conversation_id': conversation.conversation_id,
                'greeting': response,
                'response': turn_response
            }
            
        return {
            'conversation_id': conversation.conversation_id,
            'greeting': response,
            'status': 'ready'
        }
        
    async def process_message(self, conversation_id: str,
                            message_content: str) -> Dict[str, Any]:
        """
        Process a user message and generate response.
        
        Args:
            conversation_id: Conversation identifier
            message_content: User's message
            
        Returns:
            Response data
        """
        async with self._conversation_locks.get(conversation_id, asyncio.Lock()):
            conversation = await self._ensure_conversation_active(conversation_id)
            
            # Update status
            conversation.status = ConversationStatus.PROCESSING
            
            # Create user message
            user_message = DialogueMessage(
                conversation_id=conversation_id,
                role=ConversationRole.USER,
                content=message_content,
                message_type=MessageType.QUERY
            )
            
            # Add to conversation
            await self.memory.add_message(conversation_id, user_message)
            
            # Extract intent
            intent = await self._extract_intent(message_content, conversation)
            
            # Get relevant context
            context = await self.memory.get_relevant_context(
                conversation_id,
                message_content
            )
            
            # Generate response based on intent
            response_messages = await self._generate_response(
                conversation,
                user_message,
                intent,
                context
            )
            
            # Create conversation turn
            turn = ConversationTurn(
                conversation_id=conversation_id,
                user_message=user_message,
                assistant_messages=response_messages,
                extracted_intent=intent
            )
            
            # Complete turn
            await self.memory.complete_turn(conversation_id, turn)
            
            # Update conversation status
            conversation.status = ConversationStatus.ACTIVE
            
            # Format response
            return {
                'conversation_id': conversation_id,
                'turn_id': turn.turn_id,
                'intent': intent.dict() if intent else None,
                'messages': [msg.dict() for msg in response_messages],
                'status': conversation.status.value
            }
            
    async def end_conversation(self, conversation_id: str,
                             reason: str = "user_ended") -> Dict[str, Any]:
        """End a conversation."""
        conversation = await self._ensure_conversation_active(conversation_id)
        
        # Generate farewell
        farewell = await self._generate_farewell(conversation, reason)
        
        # End conversation in memory
        await self.memory.end_conversation(
            conversation_id,
            ConversationStatus.COMPLETED
        )
        
        # Remove from active
        self._active_conversations.pop(conversation_id, None)
        self._conversation_locks.pop(conversation_id, None)
        
        return {
            'conversation_id': conversation_id,
            'farewell': farewell,
            'summary': conversation.summary.dict() if conversation.summary else None
        }
        
    # Intent Processing
    
    async def _extract_intent(self, message: str,
                            conversation: Conversation) -> Optional[Intent]:
        """Extract intent from user message."""
        # Simple keyword-based intent extraction
        # In production, this would use NLP models
        
        message_lower = message.lower()
        
        # Trading intents
        if any(word in message_lower for word in ['buy', 'sell', 'trade', 'execute']):
            return Intent(
                intent_type=IntentType.EXECUTE_TRADE,
                confidence=0.8,
                parameters=self._extract_trade_parameters(message),
                requires_confirmation=True
            )
            
        elif any(word in message_lower for word in ['analyze', 'analysis', 'market']):
            return Intent(
                intent_type=IntentType.ANALYZE_MARKET,
                confidence=0.9,
                parameters={'query': message}
            )
            
        elif any(word in message_lower for word in ['position', 'holdings', 'portfolio']):
            return Intent(
                intent_type=IntentType.CHECK_POSITIONS,
                confidence=0.9,
                parameters={}
            )
            
        # Control intents
        elif any(word in message_lower for word in ['start', 'begin', 'initiate']):
            if 'session' in message_lower or 'trading' in message_lower:
                return Intent(
                    intent_type=IntentType.START_SESSION,
                    confidence=0.85,
                    parameters={},
                    requires_confirmation=True
                )
                
        elif any(word in message_lower for word in ['stop', 'end', 'close']):
            if 'session' in message_lower or 'trading' in message_lower:
                return Intent(
                    intent_type=IntentType.STOP_SESSION,
                    confidence=0.85,
                    parameters={},
                    requires_confirmation=True
                )
                
        # Information intents
        elif any(word in message_lower for word in ['status', 'how', 'what']):
            return Intent(
                intent_type=IntentType.REQUEST_STATUS,
                confidence=0.7,
                parameters={}
            )
            
        elif any(word in message_lower for word in ['metric', 'performance', 'pnl', 'profit']):
            return Intent(
                intent_type=IntentType.REQUEST_METRICS,
                confidence=0.8,
                parameters={}
            )
            
        elif any(word in message_lower for word in ['explain', 'why', 'understand']):
            return Intent(
                intent_type=IntentType.REQUEST_EXPLANATION,
                confidence=0.75,
                parameters={'topic': self._extract_explanation_topic(message)}
            )
            
        # General intents
        elif any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning']):
            return Intent(
                intent_type=IntentType.GREETING,
                confidence=0.95,
                parameters={}
            )
            
        elif any(word in message_lower for word in ['help', 'assist', 'support']):
            return Intent(
                intent_type=IntentType.HELP,
                confidence=0.9,
                parameters={}
            )
            
        # Default to unclear
        return Intent(
            intent_type=IntentType.UNCLEAR,
            confidence=0.3,
            parameters={'original_message': message}
        )
        
    def _extract_trade_parameters(self, message: str) -> Dict[str, Any]:
        """Extract trading parameters from message."""
        params = {}
        
        # Extract action (buy/sell)
        if 'sell' in message.lower():
            params['action'] = 'sell'
        elif 'buy' in message.lower():
            params['action'] = 'buy'
            
        # Extract symbol (simplified - looks for uppercase words)
        import re
        symbols = re.findall(r'\b[A-Z]{2,5}\b', message)
        if symbols:
            params['symbol'] = symbols[0]
            
        # Extract quantity
        quantities = re.findall(r'\b(\d+)\s*(?:contract|option|share)', message.lower())
        if quantities:
            params['quantity'] = int(quantities[0])
            
        return params
        
    def _extract_explanation_topic(self, message: str) -> str:
        """Extract what user wants explained."""
        # Remove common words
        words = message.lower().split()
        topic_words = [
            w for w in words
            if w not in ['explain', 'why', 'what', 'how', 'please', 'can', 'you']
        ]
        return ' '.join(topic_words[:5])  # First 5 relevant words
        
    # Response Generation
    
    async def _generate_response(self, conversation: Conversation,
                               user_message: DialogueMessage,
                               intent: Optional[Intent],
                               context: Dict[str, Any]) -> List[DialogueMessage]:
        """Generate response messages based on intent and context."""
        responses = []
        
        if not intent:
            # No clear intent
            response = await self._generate_clarification_request(conversation)
            responses.append(response)
            return responses
            
        # Get handler for intent
        handler = self._intent_handlers.get(intent.intent_type)
        if handler:
            handler_responses = await handler(conversation, intent, context)
            responses.extend(handler_responses)
        else:
            # Default response
            response = DialogueMessage(
                conversation_id=conversation.conversation_id,
                role=ConversationRole.ASSISTANT,
                content=f"I understand you want to {intent.intent_type.value}, but I'm not sure how to help with that yet.",
                message_type=MessageType.RESPONSE
            )
            responses.append(response)
            
        # Add to conversation
        for response in responses:
            await self.memory.add_message(conversation.conversation_id, response)
            
        return responses
        
    # Intent Handlers
    
    async def _handle_execute_trade(self, conversation: Conversation,
                                  intent: Intent,
                                  context: Dict[str, Any]) -> List[DialogueMessage]:
        """Handle trade execution intent."""
        responses = []
        params = intent.parameters
        
        # Check if we have all required parameters
        if not all(k in params for k in ['action', 'symbol']):
            response = DialogueMessage(
                conversation_id=conversation.conversation_id,
                role=ConversationRole.ASSISTANT,
                content="I need more information to execute a trade. What would you like to trade?",
                message_type=MessageType.CLARIFICATION
            )
            responses.append(response)
            return responses
            
        # Check if session is active
        if not conversation.context.session_id or not self.session_manager:
            response = DialogueMessage(
                conversation_id=conversation.conversation_id,
                role=ConversationRole.ASSISTANT,
                content="There's no active trading session. Would you like me to start one?",
                message_type=MessageType.RESPONSE
            )
            responses.append(response)
            return responses
            
        # Generate confirmation request
        if intent.requires_confirmation:
            confirmation_msg = f"I'll {params['action']} {params.get('quantity', 1)} {params['symbol']} option(s). Is this correct?"
            response = DialogueMessage(
                conversation_id=conversation.conversation_id,
                role=ConversationRole.ASSISTANT,
                content=confirmation_msg,
                message_type=MessageType.CONFIRMATION,
                metadata={'pending_action': params}
            )
            conversation.context.awaiting_response = True
            responses.append(response)
            
        return responses
        
    async def _handle_analyze_market(self, conversation: Conversation,
                                   intent: Intent,
                                   context: Dict[str, Any]) -> List[DialogueMessage]:
        """Handle market analysis intent."""
        responses = []
        
        # Get market data from context
        if 'current_context' in context:
            market_state = context['current_context'].get('market_state')
            if market_state:
                analysis = f"Current market analysis:\n"
                analysis += f"• SPY: ${market_state.get('spy_price', 0)}\n"
                analysis += f"• VIX: {market_state.get('vix_level', 0)}\n"
                analysis += f"• Market Regime: {market_state.get('market_regime', 'unknown')}\n"
                analysis += f"• Liquidity: {market_state.get('liquidity_status', 'normal')}"
                
                response = DialogueMessage(
                    conversation_id=conversation.conversation_id,
                    role=ConversationRole.ASSISTANT,
                    content=analysis,
                    message_type=MessageType.RESPONSE,
                    metadata={'data_type': 'market_analysis'}
                )
                responses.append(response)
            else:
                response = DialogueMessage(
                    conversation_id=conversation.conversation_id,
                    role=ConversationRole.ASSISTANT,
                    content="I don't have current market data available. Let me check the latest information.",
                    message_type=MessageType.RESPONSE
                )
                responses.append(response)
                
        return responses
        
    async def _handle_check_positions(self, conversation: Conversation,
                                    intent: Intent,
                                    context: Dict[str, Any]) -> List[DialogueMessage]:
        """Handle position check intent."""
        responses = []
        
        # Get trading state from context
        trading_state = context.get('current_context', {}).get('trading_state')
        
        if trading_state and trading_state.get('open_positions'):
            positions_summary = "Current positions:\n"
            for position in trading_state['open_positions']:
                positions_summary += f"• {position['symbol']}: {position['quantity']} @ ${position['entry_price']}\n"
                
            response = DialogueMessage(
                conversation_id=conversation.conversation_id,
                role=ConversationRole.ASSISTANT,
                content=positions_summary,
                message_type=MessageType.RESPONSE,
                metadata={'data_type': 'positions'}
            )
        else:
            response = DialogueMessage(
                conversation_id=conversation.conversation_id,
                role=ConversationRole.ASSISTANT,
                content="You don't have any open positions at the moment.",
                message_type=MessageType.RESPONSE
            )
            
        responses.append(response)
        return responses
        
    async def _handle_start_session(self, conversation: Conversation,
                                  intent: Intent,
                                  context: Dict[str, Any]) -> List[DialogueMessage]:
        """Handle session start intent."""
        responses = []
        
        if self.session_manager:
            # Check if already has session
            if conversation.context.session_id:
                response = DialogueMessage(
                    conversation_id=conversation.conversation_id,
                    role=ConversationRole.ASSISTANT,
                    content="You already have an active trading session. Would you like to see its status?",
                    message_type=MessageType.RESPONSE
                )
            else:
                # Start new session
                session = await self.session_manager.create_session(SessionType.REGULAR)
                await self.session_manager.start_session(session.session_id)
                
                conversation.context.session_id = session.session_id
                
                response = DialogueMessage(
                    conversation_id=conversation.conversation_id,
                    role=ConversationRole.ASSISTANT,
                    content=f"I've started a new trading session ({session.session_id[:8]}...). The system is now actively monitoring markets and ready to execute trades.",
                    message_type=MessageType.ACTION,
                    metadata={'action': 'session_started', 'session_id': session.session_id}
                )
        else:
            response = DialogueMessage(
                conversation_id=conversation.conversation_id,
                role=ConversationRole.ASSISTANT,
                content="Session management is not available at the moment.",
                message_type=MessageType.ERROR
            )
            
        responses.append(response)
        return responses
        
    async def _handle_help(self, conversation: Conversation,
                         intent: Intent,
                         context: Dict[str, Any]) -> List[DialogueMessage]:
        """Handle help intent."""
        help_text = """Here's what I can help you with:

**Trading Operations:**
• Execute trades (buy/sell SPY options)
• Check your current positions
• Analyze market conditions

**Session Management:**
• Start/stop trading sessions
• Pause/resume trading
• Check session status

**Information:**
• View performance metrics
• Get explanations of trading decisions
• Review trading history

**Settings:**
• Update risk parameters
• Change trading preferences

Just let me know what you'd like to do!"""
        
        response = DialogueMessage(
            conversation_id=conversation.conversation_id,
            role=ConversationRole.ASSISTANT,
            content=help_text,
            message_type=MessageType.RESPONSE
        )
        
        return [response]
        
    # Helper Methods
    
    async def _ensure_conversation_active(self, conversation_id: str) -> Conversation:
        """Ensure conversation is active."""
        if conversation_id not in self._active_conversations:
            # Try to load from memory
            conversation = await self.memory.get_conversation(conversation_id)
            if conversation and conversation.status == ConversationStatus.ACTIVE:
                self._active_conversations[conversation_id] = conversation
                self._conversation_locks[conversation_id] = asyncio.Lock()
            else:
                raise ValueError(f"Conversation {conversation_id} is not active")
                
        return self._active_conversations[conversation_id]
        
    async def _generate_greeting(self, conversation: Conversation,
                               preferences: UserPreferences) -> str:
        """Generate personalized greeting."""
        hour = datetime.now().hour
        
        if hour < 12:
            time_greeting = "Good morning"
        elif hour < 18:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"
            
        if preferences.preferred_formality == "casual":
            return f"{time_greeting}! I'm here to help with your trading. What's on your mind?"
        else:
            return f"{time_greeting}. I'm ready to assist with your trading operations. How may I help you today?"
            
    async def _generate_farewell(self, conversation: Conversation,
                               reason: str) -> str:
        """Generate farewell message."""
        if conversation.summary:
            if conversation.summary.actions_taken:
                return f"Thank you for trading with me today. We executed {len(conversation.summary.actions_taken)} actions. Have a great day!"
            else:
                return "Thank you for chatting. Feel free to return anytime you need trading assistance. Goodbye!"
        else:
            return "Goodbye! Feel free to start a new conversation whenever you need help."
            
    async def _generate_clarification_request(self, conversation: Conversation) -> DialogueMessage:
        """Generate clarification request."""
        templates = [
            "I'm not sure I understand. Could you please clarify what you'd like me to do?",
            "I didn't quite catch that. Could you rephrase your request?",
            "I want to make sure I help you correctly. Can you tell me more about what you need?"
        ]
        
        import random
        content = random.choice(templates)
        
        return DialogueMessage(
            conversation_id=conversation.conversation_id,
            role=ConversationRole.ASSISTANT,
            content=content,
            message_type=MessageType.CLARIFICATION
        )
        
    async def _load_user_preferences(self, user_id: str) -> UserPreferences:
        """Load user preferences from storage."""
        # For now, return defaults
        # In production, this would load from database
        return UserPreferences(user_id=user_id)
        
    def _register_default_handlers(self) -> None:
        """Register default intent handlers."""
        self._intent_handlers = {
            IntentType.EXECUTE_TRADE: self._handle_execute_trade,
            IntentType.ANALYZE_MARKET: self._handle_analyze_market,
            IntentType.CHECK_POSITIONS: self._handle_check_positions,
            IntentType.START_SESSION: self._handle_start_session,
            IntentType.HELP: self._handle_help,
        }
        
    def _load_default_templates(self) -> None:
        """Load default response templates."""
        # This would load from configuration
        pass
        
    def _load_default_flows(self) -> None:
        """Load default conversation flows."""
        # This would load from configuration
        pass