"""
Conversation Memory Manager
Manages conversation history and context across sessions.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import json
from collections import defaultdict

from ..mcp.context_manager import MCPContextManager
from ..mcp.schemas import MemorySlice, MemoryType, MemoryImportance
from ..database.redis_client import RedisClient
from ..database.postgres_client import PostgresClient
from .schemas import (
    Conversation, ConversationStatus, DialogueMessage, ConversationRole,
    MessageType, ConversationTurn, ConversationContext, Intent,
    ConversationSummary, EntityType
)

logger = logging.getLogger(__name__)


class ConversationMemoryManager:
    """
    Manages conversation memory and retrieval across sessions.
    """
    
    def __init__(self, mcp_manager: MCPContextManager,
                 redis_client: Optional[RedisClient] = None,
                 postgres_client: Optional[PostgresClient] = None):
        self.mcp = mcp_manager
        self.redis = redis_client
        self.postgres = postgres_client
        
        # Active conversations cache
        self._active_conversations: Dict[str, Conversation] = {}
        
        # Context windows
        self.short_term_window = timedelta(hours=4)
        self.medium_term_window = timedelta(days=7)
        self.long_term_window = timedelta(days=30)
        
        # Configuration
        self.max_context_messages = 20
        self.max_memory_search_results = 10
        self.context_relevance_threshold = 0.7
        
    async def initialize(self) -> None:
        """Initialize the conversation memory manager."""
        # Register with MCP
        await self.mcp.register_agent(
            "ConversationMemoryManager",
            ["conversation_memory", "context_retrieval", "dialogue_history"]
        )
        
        # Initialize storage clients if needed
        if not self.redis:
            self.redis = RedisClient()
            await self.redis.initialize()
            
        if not self.postgres:
            self.postgres = PostgresClient()
            await self.postgres.initialize()
            
        logger.info("Conversation Memory Manager initialized")
        
    # Conversation Management
    
    async def create_conversation(self, user_id: str,
                                previous_conversation_id: Optional[str] = None) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            user_id: User identifier
            previous_conversation_id: ID of previous conversation to continue from
            
        Returns:
            New conversation
        """
        conversation = Conversation(user_id=user_id)
        
        # Link to previous conversation if specified
        if previous_conversation_id:
            previous = await self.get_conversation(previous_conversation_id)
            if previous:
                conversation.previous_conversation_id = previous_conversation_id
                # Inherit relevant context
                conversation.context = await self._inherit_context(previous)
                
        # Cache and persist
        self._active_conversations[conversation.conversation_id] = conversation
        await self._save_conversation(conversation)
        
        # Store in MCP for agent access
        await self._store_conversation_start(conversation)
        
        logger.info(f"Created conversation {conversation.conversation_id} for user {user_id}")
        
        return conversation
        
    async def add_message(self, conversation_id: str,
                         message: DialogueMessage) -> None:
        """Add a message to conversation."""
        conversation = await self._ensure_conversation_loaded(conversation_id)
        
        # Add to messages list
        conversation.messages.append(message)
        conversation.last_activity = datetime.utcnow()
        
        # Update context
        await self._update_conversation_context(conversation, message)
        
        # Save changes
        await self._save_conversation(conversation)
        
        # Store significant messages in MCP
        if message.role == ConversationRole.USER:
            await self._store_user_message(conversation, message)
            
    async def complete_turn(self, conversation_id: str,
                           turn: ConversationTurn) -> None:
        """Complete a conversation turn."""
        conversation = await self._ensure_conversation_loaded(conversation_id)
        
        # Add turn
        turn.turn_number = len(conversation.turns) + 1
        conversation.turns.append(turn)
        
        # Update conversation based on turn outcome
        if turn.extracted_intent:
            conversation.context.active_intent = turn.extracted_intent
            
        # Track completed actions
        if turn.assistant_messages:
            for msg in turn.assistant_messages:
                if msg.message_type == MessageType.ACTION:
                    conversation.context.completed_actions.append({
                        'action': msg.metadata.get('action'),
                        'timestamp': msg.timestamp,
                        'result': msg.metadata.get('result')
                    })
                    
        # Save changes
        await self._save_conversation(conversation)
        
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        # Check cache
        if conversation_id in self._active_conversations:
            return self._active_conversations[conversation_id]
            
        # Load from storage
        conversation = await self._load_conversation(conversation_id)
        if conversation:
            self._active_conversations[conversation_id] = conversation
            
        return conversation
        
    async def end_conversation(self, conversation_id: str,
                             status: ConversationStatus = ConversationStatus.COMPLETED) -> None:
        """End a conversation."""
        conversation = await self._ensure_conversation_loaded(conversation_id)
        
        # Update status
        conversation.status = status
        conversation.ended_at = datetime.utcnow()
        
        # Generate summary
        conversation.summary = await self._generate_conversation_summary(conversation)
        
        # Save final state
        await self._save_conversation(conversation)
        
        # Archive to long-term storage
        await self._archive_conversation(conversation)
        
        # Remove from active cache
        self._active_conversations.pop(conversation_id, None)
        
        logger.info(f"Ended conversation {conversation_id} with status {status}")
        
    # Context Retrieval
    
    async def get_relevant_context(self, conversation_id: str,
                                  query: str,
                                  include_history: bool = True) -> Dict[str, Any]:
        """
        Get relevant context for current conversation.
        
        Args:
            conversation_id: Current conversation
            query: Query to find relevant context for
            include_history: Whether to include historical conversations
            
        Returns:
            Relevant context information
        """
        conversation = await self._ensure_conversation_loaded(conversation_id)
        context = {
            'current_context': conversation.context.dict(),
            'recent_messages': [],
            'relevant_history': [],
            'entities': {},
            'patterns': []
        }
        
        # Get recent messages from current conversation
        context['recent_messages'] = [
            msg.dict() for msg in conversation.messages[-self.max_context_messages:]
        ]
        
        # Extract entities from current conversation
        context['entities'] = conversation.context.mentioned_entities
        
        # Search historical conversations if requested
        if include_history:
            # Search in MCP memory
            relevant_memories = await self.mcp.search_memories(
                "ConversationMemoryManager",
                query,
                memory_types=[MemoryType.DIALOGUE],
                limit=self.max_memory_search_results
            )
            
            # Filter by relevance threshold
            for memory in relevant_memories:
                if memory['relevance_score'] >= self.context_relevance_threshold:
                    context['relevant_history'].append({
                        'conversation_id': memory['content'].get('conversation_id'),
                        'summary': memory['content'].get('summary'),
                        'relevance': memory['relevance_score'],
                        'timestamp': memory['timestamp']
                    })
                    
        # Identify conversation patterns
        context['patterns'] = await self._identify_conversation_patterns(
            conversation,
            context['relevant_history']
        )
        
        return context
        
    async def get_user_history(self, user_id: str,
                             limit: int = 10) -> List[ConversationSummary]:
        """Get user's conversation history."""
        # Query from PostgreSQL
        if self.postgres:
            query = """
                SELECT conversation_id, summary
                FROM conversations
                WHERE user_id = $1
                AND ended_at IS NOT NULL
                ORDER BY ended_at DESC
                LIMIT $2
            """
            
            results = await self.postgres.fetch(query, user_id, limit)
            
            summaries = []
            for result in results:
                if result['summary']:
                    summary = ConversationSummary.parse_raw(result['summary'])
                    summaries.append(summary)
                    
            return summaries
            
        return []
        
    async def search_conversations(self, user_id: str,
                                 search_query: str,
                                 date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict[str, Any]]:
        """Search through user's conversations."""
        results = []
        
        # Search in MCP vector store
        memories = await self.mcp.search_memories(
            "ConversationMemoryManager",
            search_query,
            memory_types=[MemoryType.DIALOGUE],
            date_range=date_range,
            limit=50
        )
        
        # Filter by user and format results
        for memory in memories:
            if memory['content'].get('user_id') == user_id:
                results.append({
                    'conversation_id': memory['content'].get('conversation_id'),
                    'message': memory['content'].get('message'),
                    'timestamp': memory['timestamp'],
                    'relevance': memory['relevance_score']
                })
                
        # Sort by relevance
        results.sort(key=lambda x: x['relevance'], reverse=True)
        
        return results[:20]  # Return top 20 results
        
    # Context Management
    
    async def update_working_memory(self, conversation_id: str,
                                  key: str, value: Any) -> None:
        """Update conversation's working memory."""
        conversation = await self._ensure_conversation_loaded(conversation_id)
        conversation.context.working_memory[key] = value
        await self._save_conversation(conversation)
        
    async def clear_working_memory(self, conversation_id: str,
                                 keys: Optional[List[str]] = None) -> None:
        """Clear working memory items."""
        conversation = await self._ensure_conversation_loaded(conversation_id)
        
        if keys:
            for key in keys:
                conversation.context.working_memory.pop(key, None)
        else:
            conversation.context.working_memory.clear()
            
        await self._save_conversation(conversation)
        
    async def track_entity(self, conversation_id: str,
                         entity_type: EntityType,
                         entity_value: Any,
                         metadata: Optional[Dict[str, Any]] = None) -> None:
        """Track an entity mentioned in conversation."""
        conversation = await self._ensure_conversation_loaded(conversation_id)
        
        if entity_type.value not in conversation.context.mentioned_entities:
            conversation.context.mentioned_entities[entity_type.value] = []
            
        entity_data = {
            'value': entity_value,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        conversation.context.mentioned_entities[entity_type.value].append(entity_data)
        
        await self._save_conversation(conversation)
        
    # Memory Operations
    
    async def consolidate_memories(self, user_id: str) -> None:
        """Consolidate user's conversation memories."""
        # Get recent conversations
        recent = await self.get_user_history(user_id, limit=50)
        
        # Extract patterns and insights
        patterns = await self._extract_user_patterns(recent)
        
        # Store consolidated memory
        await self.mcp.store_memory(
            "ConversationMemoryManager",
            MemorySlice(
                memory_type=MemoryType.LEARNING,
                content={
                    'user_id': user_id,
                    'conversation_patterns': patterns,
                    'consolidation_date': datetime.utcnow().isoformat()
                },
                importance=MemoryImportance.HIGH
            )
        )
        
    # Private Methods
    
    async def _ensure_conversation_loaded(self, conversation_id: str) -> Conversation:
        """Ensure conversation is loaded."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")
        return conversation
        
    async def _save_conversation(self, conversation: Conversation) -> None:
        """Save conversation to storage."""
        # Save to Redis for active conversations
        if self.redis and conversation.status in [ConversationStatus.ACTIVE, ConversationStatus.PROCESSING]:
            key = f"conversation:{conversation.conversation_id}"
            await self.redis.set(key, conversation.json(), ex=24 * 3600)  # 24 hour expiry
            
        # Save to PostgreSQL for persistence
        if self.postgres:
            query = """
                INSERT INTO conversations (conversation_id, user_id, data, started_at, last_activity)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (conversation_id) DO UPDATE
                SET data = $3, last_activity = $5
            """
            
            await self.postgres.execute(
                query,
                conversation.conversation_id,
                conversation.user_id,
                conversation.json(),
                conversation.started_at,
                conversation.last_activity
            )
            
    async def _load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Load conversation from storage."""
        # Try Redis first
        if self.redis:
            key = f"conversation:{conversation_id}"
            data = await self.redis.get(key)
            if data:
                return Conversation.parse_raw(data)
                
        # Try PostgreSQL
        if self.postgres:
            query = "SELECT data FROM conversations WHERE conversation_id = $1"
            result = await self.postgres.fetchone(query, conversation_id)
            if result:
                return Conversation.parse_raw(result['data'])
                
        return None
        
    async def _archive_conversation(self, conversation: Conversation) -> None:
        """Archive completed conversation."""
        # Store summary in MCP for searchability
        if conversation.summary:
            await self.mcp.store_memory(
                "ConversationMemoryManager",
                MemorySlice(
                    memory_type=MemoryType.DIALOGUE,
                    content={
                        'conversation_id': conversation.conversation_id,
                        'user_id': conversation.user_id,
                        'summary': conversation.summary.dict(),
                        'duration': str(conversation.ended_at - conversation.started_at),
                        'message_count': len(conversation.messages)
                    },
                    importance=MemoryImportance.MEDIUM
                )
            )
            
        # Remove from Redis
        if self.redis:
            key = f"conversation:{conversation.conversation_id}"
            await self.redis.delete(key)
            
    async def _inherit_context(self, previous: Conversation) -> ConversationContext:
        """Inherit context from previous conversation."""
        new_context = ConversationContext()
        
        # Inherit session linkage
        new_context.session_id = previous.context.session_id
        new_context.agent_states = previous.context.agent_states.copy()
        
        # Inherit entities (with decay)
        for entity_type, entities in previous.context.mentioned_entities.items():
            # Only keep recent entities
            recent_entities = [
                e for e in entities
                if datetime.fromisoformat(e['timestamp']) > datetime.utcnow() - self.short_term_window
            ]
            if recent_entities:
                new_context.mentioned_entities[entity_type] = recent_entities
                
        return new_context
        
    async def _update_conversation_context(self, conversation: Conversation,
                                         message: DialogueMessage) -> None:
        """Update conversation context based on new message."""
        # Update last activity
        conversation.last_activity = message.timestamp
        
        # Extract entities from message
        entities = self._extract_entities(message.content)
        for entity_type, values in entities.items():
            if entity_type not in conversation.context.mentioned_entities:
                conversation.context.mentioned_entities[entity_type] = []
            for value in values:
                conversation.context.mentioned_entities[entity_type].append({
                    'value': value,
                    'timestamp': message.timestamp.isoformat(),
                    'message_id': message.message_id
                })
                
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text (simplified version)."""
        entities = defaultdict(list)
        
        # Extract symbols (e.g., SPY, QQQ)
        import re
        symbols = re.findall(r'\b[A-Z]{2,5}\b', text)
        entities[EntityType.SYMBOL.value] = symbols
        
        # Extract prices (e.g., $450, 450.50)
        prices = re.findall(r'\$?\d+\.?\d*', text)
        entities[EntityType.PRICE.value] = prices
        
        # Extract percentages
        percentages = re.findall(r'\d+\.?\d*%', text)
        entities[EntityType.PERCENTAGE.value] = percentages
        
        return dict(entities)
        
    async def _generate_conversation_summary(self, conversation: Conversation) -> ConversationSummary:
        """Generate summary of conversation."""
        # Extract main topics from intents
        main_topics = list(set([
            turn.extracted_intent.intent_type.value
            for turn in conversation.turns
            if turn.extracted_intent
        ]))
        
        # Extract key decisions
        key_decisions = [
            action['action']
            for action in conversation.context.completed_actions
            if action.get('result') == 'success'
        ]
        
        # Calculate metrics
        total_duration = conversation.ended_at - conversation.started_at if conversation.ended_at else timedelta()
        efficiency_score = min(1.0, 300 / total_duration.total_seconds()) if total_duration else 0.5
        
        return ConversationSummary(
            conversation_id=conversation.conversation_id,
            main_topics=main_topics[:5],  # Top 5 topics
            key_decisions=key_decisions[:5],  # Top 5 decisions
            actions_taken=[a['action'] for a in conversation.context.completed_actions[:5]],
            efficiency_score=efficiency_score
        )
        
    async def _identify_conversation_patterns(self, conversation: Conversation,
                                            relevant_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify patterns in conversation."""
        patterns = []
        
        # Intent sequence pattern
        intent_sequence = [
            turn.extracted_intent.intent_type.value
            for turn in conversation.turns[-5:]  # Last 5 turns
            if turn.extracted_intent
        ]
        
        if len(intent_sequence) >= 2:
            patterns.append({
                'type': 'intent_sequence',
                'pattern': ' -> '.join(intent_sequence),
                'frequency': 1  # Would need historical analysis for real frequency
            })
            
        # Time-based patterns
        if conversation.messages:
            message_times = [msg.timestamp.hour for msg in conversation.messages]
            most_common_hour = max(set(message_times), key=message_times.count)
            patterns.append({
                'type': 'time_preference',
                'pattern': f'most_active_hour_{most_common_hour}',
                'frequency': message_times.count(most_common_hour) / len(message_times)
            })
            
        return patterns
        
    async def _extract_user_patterns(self, summaries: List[ConversationSummary]) -> Dict[str, Any]:
        """Extract patterns from user's conversation history."""
        patterns = {
            'common_topics': defaultdict(int),
            'common_actions': defaultdict(int),
            'success_rate': 0.0,
            'avg_efficiency': 0.0
        }
        
        for summary in summaries:
            # Count topics
            for topic in summary.main_topics:
                patterns['common_topics'][topic] += 1
                
            # Count actions
            for action in summary.actions_taken:
                patterns['common_actions'][action] += 1
                
            # Accumulate metrics
            if summary.efficiency_score:
                patterns['avg_efficiency'] += summary.efficiency_score
                
        # Calculate averages
        if summaries:
            patterns['avg_efficiency'] /= len(summaries)
            
        # Convert defaultdicts to regular dicts
        patterns['common_topics'] = dict(patterns['common_topics'])
        patterns['common_actions'] = dict(patterns['common_actions'])
        
        return patterns
        
    async def _store_conversation_start(self, conversation: Conversation) -> None:
        """Store conversation start in MCP."""
        await self.mcp.store_memory(
            "ConversationMemoryManager",
            MemorySlice(
                memory_type=MemoryType.DIALOGUE,
                content={
                    'event': 'conversation_started',
                    'conversation_id': conversation.conversation_id,
                    'user_id': conversation.user_id,
                    'timestamp': conversation.started_at.isoformat()
                },
                importance=MemoryImportance.LOW
            )
        )
        
    async def _store_user_message(self, conversation: Conversation,
                                message: DialogueMessage) -> None:
        """Store significant user message in MCP."""
        # Only store messages with clear intent or important content
        if message.metadata.get('has_intent') or len(message.content) > 50:
            await self.mcp.store_memory(
                "ConversationMemoryManager",
                MemorySlice(
                    memory_type=MemoryType.DIALOGUE,
                    content={
                        'conversation_id': conversation.conversation_id,
                        'user_id': conversation.user_id,
                        'message': message.content,
                        'message_type': message.message_type.value,
                        'timestamp': message.timestamp.isoformat()
                    },
                    importance=MemoryImportance.MEDIUM
                )
            )