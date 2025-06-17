# Phase 6: Stateful Dialogue System

## Overview

The Stateful Dialogue System provides intelligent, context-aware conversation management for FNTX.ai. It maintains conversation history, understands user intent, tracks entities across messages, and generates appropriate responses based on the full context of the interaction.

## Architecture

### Core Components

1. **Dialogue Manager** (`dialogue_manager.py`)
   - Manages active conversations
   - Extracts user intent from messages
   - Generates context-aware responses
   - Coordinates with trading sessions
   - Handles conversation flows

2. **Conversation Memory Manager** (`conversation_memory.py`)
   - Persists conversation history
   - Retrieves relevant context
   - Manages conversation continuity
   - Provides semantic search capabilities
   - Consolidates user patterns

3. **Dialogue Schemas** (`schemas.py`)
   - Defines conversation data models
   - Provides intent and entity types
   - Structures conversation flows
   - Manages user preferences

### Memory Architecture

```
┌─────────────────────┐
│  Active Conversation │
│     (In Memory)      │
└─────────┬───────────┘
          │
     ┌────▼────┐
     │  Redis  │ ◄── Short-term (24h)
     │  Cache  │     Active conversations
     └────┬────┘
          │
  ┌───────▼────────┐
  │  PostgreSQL    │ ◄── Medium-term (30d)
  │  Conversation  │     Full history
  │    History     │
  └───────┬────────┘
          │
     ┌────▼─────┐
     │   MCP    │ ◄── Long-term
     │  Vector  │     Semantic search
     │  Store   │     Pattern learning
     └──────────┘
```

## Key Features

### 1. Intent Recognition

The system recognizes various user intents:

```python
class IntentType(Enum):
    # Trading intents
    EXECUTE_TRADE = "execute_trade"
    ANALYZE_MARKET = "analyze_market"
    CHECK_POSITIONS = "check_positions"
    
    # Control intents
    START_SESSION = "start_session"
    STOP_SESSION = "stop_session"
    PAUSE_TRADING = "pause_trading"
    
    # Information intents
    REQUEST_STATUS = "request_status"
    REQUEST_METRICS = "request_metrics"
    REQUEST_EXPLANATION = "request_explanation"
```

### 2. Context-Aware Responses

```python
# System maintains context across messages
User: "What's the market looking like?"
Assistant: "Current market analysis:
• SPY: $447.85
• VIX: 11.25
• Market Regime: favorable_for_selling
• Liquidity: normal"

User: "Should I sell some puts?"
Assistant: "Based on the favorable market conditions I just showed, 
selling SPY puts could be profitable. The low VIX (11.25) suggests 
limited downside risk. Would you like me to analyze specific strikes?"

# The assistant remembers the previous market analysis context
```

### 3. Entity Tracking

The system tracks entities mentioned across conversations:

```python
# Automatically extracts and tracks:
- Symbols: SPY, QQQ, IWM
- Prices: $450, 445.50
- Quantities: 5 contracts, 10 options
- Percentages: 2%, 50% profit
- Dates: today, next Friday, 12/20

# Example usage:
User: "Buy 5 SPY puts"
User: "Actually make it 10"
# System understands "it" refers to SPY puts from context
```

### 4. Conversation Memory

```python
# Short-term memory (current session)
- Last 20 messages
- Active entities
- Current intent
- Working memory

# Medium-term memory (7 days)
- Recent conversations
- Successful trades discussed
- User preferences learned

# Long-term memory (30+ days)
- Conversation patterns
- Common queries
- Trading preferences
- Success metrics
```

### 5. Multi-Turn Conversations

```python
# Complex conversations with state tracking
User: "I want to start trading"
Assistant: "I'll start a trading session for you. [Starting session...]"

User: "What's my risk limit?"
Assistant: "Your current risk parameters:
- Max daily risk: 2% ($2,000)
- Position limit: 3 concurrent positions
- Stop loss: 3x premium"

User: "Change it to 1%"
Assistant: "I'll update your max daily risk to 1% ($1,000). 
This will affect all new trades. Confirm?"

User: "Yes"
Assistant: "Risk limit updated to 1%. You now have $1,000 
daily risk allowance."
```

## Usage Examples

### Starting a Conversation

```python
from backend.dialogue import DialogueManager, ConversationMemoryManager

# Initialize components
memory_manager = ConversationMemoryManager(mcp_manager)
dialogue_manager = DialogueManager(mcp_manager, memory_manager, session_manager)
await dialogue_manager.initialize()

# Start conversation
response = await dialogue_manager.start_conversation(
    user_id="user123",
    initial_message="Hello, I'd like to check my positions"
)

print(response['greeting'])
# "Good morning. I'm ready to assist with your trading operations."

print(response['response']['messages'][0]['content'])
# "You don't have any open positions at the moment."
```

### Processing Messages

```python
# Continue conversation
response = await dialogue_manager.process_message(
    conversation_id=response['conversation_id'],
    message_content="Start a trading session for me"
)

# Response includes:
# - Extracted intent (START_SESSION)
# - Generated responses
# - Actions taken (session started)
# - Updated context
```

### Retrieving Context

```python
# Get relevant context for current conversation
context = await memory_manager.get_relevant_context(
    conversation_id=conv_id,
    query="What did we discuss about SPY yesterday?",
    include_history=True
)

# Returns:
# - Recent messages from current conversation
# - Relevant messages from historical conversations
# - Entities mentioned (SPY)
# - Identified patterns
```

### Searching Conversation History

```python
# Search across all user conversations
results = await memory_manager.search_conversations(
    user_id="user123",
    search_query="profitable SPY trades",
    date_range=(datetime(2024, 12, 1), datetime(2024, 12, 15))
)

# Returns ranked results with:
# - Conversation ID
# - Relevant message
# - Timestamp
# - Relevance score
```

## Intent Handlers

### Execute Trade Handler

```python
# Handles trade execution requests
User: "Sell 5 SPY 440 puts"

# System:
1. Extracts parameters (action=sell, quantity=5, symbol=SPY, strike=440)
2. Checks if session is active
3. Validates parameters
4. Requests confirmation
5. Executes via session manager
```

### Market Analysis Handler

```python
# Provides market analysis
User: "Analyze the market"

# System retrieves and formats:
- Current SPY price
- VIX level
- Market regime
- Support/resistance levels
- Trading recommendations
```

### Session Control Handler

```python
# Manages trading sessions
User: "Start trading"
→ Creates and starts new session

User: "Pause trading"
→ Pauses active session

User: "Stop everything"
→ Stops session and closes positions
```

## Conversation Flows

### Trade Execution Flow

```
User Intent: EXECUTE_TRADE
    ↓
Extract Parameters
    ↓
Validate Requirements ──→ Missing? ──→ Request Clarification
    ↓                                        ↓
Session Active? ──→ No ──→ Suggest Start    │
    ↓                                        │
Request Confirmation ←───────────────────────┘
    ↓
Execute Trade
    ↓
Report Result
```

### Information Request Flow

```
User Intent: REQUEST_EXPLANATION
    ↓
Identify Topic
    ↓
Gather Context ──→ Historical Data
    ↓                    ↓
Generate Explanation ←───┘
    ↓
Check Understanding ──→ Need More? ──→ Provide Details
    ↓
Complete
```

## User Preferences

### Preference Management

```python
preferences = UserPreferences(
    user_id="user123",
    preferred_formality="professional",  # or "casual"
    technical_level="intermediate",      # or "beginner", "advanced"
    confirmation_required=True,
    detailed_explanations=True,
    max_response_length=500,
    include_visualizations=True
)
```

### Adaptive Responses

```python
# Professional + Detailed
"I've analyzed the current market conditions. The SPY is trading at $447.85 
with a VIX level of 11.25, indicating low volatility. The favorable selling 
environment suggests that premium collection strategies may be profitable..."

# Casual + Brief
"Market looks good for selling options! SPY at $447.85, VIX is low (11.25). 
Want me to find some good strikes?"
```

## Memory Consolidation

### Pattern Recognition

The system identifies patterns in user behavior:

```python
# Automatically learns:
- Preferred trading times
- Common question types
- Successful strategy patterns
- Risk tolerance trends

# Example patterns:
{
    "common_intents": ["CHECK_POSITIONS", "ANALYZE_MARKET"],
    "active_hours": [9, 10, 14, 15],
    "success_patterns": ["morning_put_sales", "vix_spike_trades"],
    "avg_conversation_length": 8.5
}
```

### Performance Tracking

```python
# Conversation metrics
- Total conversations: 156
- Avg duration: 12 minutes
- Success rate: 89%
- User satisfaction: 4.7/5
- Intent recognition accuracy: 94%
```

## Integration Points

### 1. Session Management

```python
# Dialogue system integrates with sessions
if intent.intent_type == IntentType.START_SESSION:
    session = await session_manager.create_session(SessionType.REGULAR)
    conversation.context.session_id = session.session_id
```

### 2. MCP Memory

```python
# Significant interactions stored in MCP
await mcp.store_memory(
    "ConversationMemoryManager",
    MemorySlice(
        memory_type=MemoryType.DIALOGUE,
        content={
            'user_query': "Best time to sell puts?",
            'assistant_response': "Morning after market open...",
            'outcome': "user_executed_trade"
        }
    )
)
```

### 3. Agent Coordination

```python
# Dialogue can trigger agent actions
if intent.intent_type == IntentType.ANALYZE_MARKET:
    await mcp.share_context(
        "DialogueManager",
        ["EnvironmentWatcherAgent"],
        {"request": "detailed_market_analysis"}
    )
```

## Advanced Features

### 1. Contextual Clarification

```python
# System asks for clarification based on context
User: "Buy it"
System: "I see you were looking at SPY 440 puts earlier. 
         Did you mean buy SPY 440 puts?"
```

### 2. Proactive Suggestions

```python
# Based on patterns and context
System: "I notice you usually check positions at market open. 
         Would you like me to set up a daily summary?"
```

### 3. Learning from Feedback

```python
# Implicit learning
User: "That's not what I meant"
System: [Adjusts confidence scores and patterns]

# Explicit feedback
User: "Good analysis"
System: [Reinforces current approach patterns]
```

## Error Handling

### Conversation Recovery

```python
# If conversation is interrupted
try:
    response = await dialogue_manager.process_message(conv_id, message)
except ConversationNotFoundError:
    # Attempt to recover from memory
    conversation = await memory_manager.get_conversation(conv_id)
    if conversation:
        # Resume conversation
        response = await dialogue_manager.resume_conversation(conversation)
```

### Intent Ambiguity

```python
# When intent is unclear
if intent.confidence < 0.5:
    # Ask for clarification
    response = "I'm not sure what you'd like to do. Did you mean to:
    1. Check your positions
    2. Analyze the market
    3. Execute a trade"
```

## Performance Optimization

### Caching Strategy

1. **Active Conversations**: In-memory cache
2. **Recent Messages**: Redis with 24h TTL
3. **User Preferences**: Local cache with periodic refresh
4. **Intent Patterns**: Pre-computed and cached

### Response Time Targets

- Intent extraction: < 50ms
- Context retrieval: < 100ms
- Response generation: < 200ms
- Total round trip: < 500ms

## Security Considerations

### Data Protection

- Conversation data encrypted at rest
- PII detection and masking
- Secure credential handling
- Audit trail for all actions

### Access Control

- User authentication required
- Session-based authorization
- Rate limiting per user
- Suspicious pattern detection

## Future Enhancements

1. **Multi-language Support**: Conversations in multiple languages
2. **Voice Integration**: Speech-to-text and text-to-speech
3. **Sentiment Analysis**: Emotion detection and response adaptation
4. **Advanced NLU**: Transformer-based intent recognition
5. **Conversation Analytics**: Detailed insights and optimization
6. **Plugin System**: Custom intent handlers and responses
7. **Multi-modal Responses**: Charts, graphs, and visualizations

## Conclusion

The Stateful Dialogue System transforms FNTX.ai from a simple command executor to an intelligent conversational partner. It maintains context, learns from interactions, and provides increasingly personalized assistance. The system ensures users can interact naturally while maintaining full control over their trading operations.