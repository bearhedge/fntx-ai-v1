# MCP Integration Migration Guide

This guide explains how to migrate existing FNTX.ai agents to use the new Model Context Protocol (MCP) memory system.

## Overview

The MCP system provides:
- **Persistent Memory**: Agent memories persist across sessions
- **Semantic Search**: Find relevant memories using natural language
- **Context Sharing**: Agents can share insights and coordinate
- **Tiered Storage**: Hot (Redis), Warm (PostgreSQL), Cold (GCS) memory tiers
- **Learning Integration**: Automatic pattern recognition and improvement

## Migration Steps

### 1. Environment Setup

Add these environment variables to your `.env` file:

```bash
# Redis Configuration
MCP_REDIS_HOST=localhost
MCP_REDIS_PORT=6379
MCP_REDIS_PASSWORD=your_password

# PostgreSQL Configuration  
MCP_POSTGRES_HOST=localhost
MCP_POSTGRES_PORT=5432
MCP_POSTGRES_DATABASE=fntx_mcp
MCP_POSTGRES_USER=postgres
MCP_POSTGRES_PASSWORD=your_password

# Google Cloud Storage
MCP_GCS_BUCKET=fntx-mcp-storage
MCP_GCS_CREDENTIALS_PATH=/path/to/credentials.json

# Pinecone Configuration
MCP_PINECONE_API_KEY=your_api_key
MCP_PINECONE_ENVIRONMENT=us-east-1
MCP_PINECONE_INDEX=fntx-agent-memories

# OpenAI Configuration
MCP_OPENAI_API_KEY=your_openai_key
```

### 2. Initialize MCP System

Add MCP initialization to your application startup:

```python
from backend.mcp import MCPContextManager
from backend.mcp.config import get_environment_config

# In your app initialization
async def startup():
    # Initialize MCP
    mcp_config = get_environment_config()
    mcp_manager = MCPContextManager(mcp_config)
    await mcp_manager.initialize()
    
    # Store globally for agent access
    app.state.mcp = mcp_manager
```

### 3. Update Agent Base Class

Create a new base class for MCP-enabled agents:

```python
from backend.mcp.schemas import MemorySlice, MemoryType, MemoryImportance

class MCPAgent:
    def __init__(self, agent_id: str, mcp_manager: MCPContextManager):
        self.agent_id = agent_id
        self.mcp = mcp_manager
        
    async def initialize(self):
        """Register with MCP system"""
        capabilities = self.get_capabilities()
        await self.mcp.register_agent(self.agent_id, capabilities)
        
    def get_capabilities(self):
        """Override in subclasses"""
        return []
        
    async def remember(self, content: dict, memory_type: MemoryType, 
                      importance: MemoryImportance = MemoryImportance.MEDIUM):
        """Store a memory"""
        memory = MemorySlice(
            memory_type=memory_type,
            content=content,
            importance=importance
        )
        return await self.mcp.store_memory(self.agent_id, memory)
```

### 4. Migrate Individual Agents

#### Environment Watcher Agent

```python
class EnvironmentWatcherAgent(MCPAgent):
    def get_capabilities(self):
        return ['market_monitoring', 'regime_detection', 'risk_alerts']
        
    async def update_market_conditions(self, market_data):
        # Store observation in MCP
        await self.remember(
            content={
                'spy_price': market_data['spy_price'],
                'vix_level': market_data['vix_level'],
                'regime': market_data['regime'],
                'timestamp': datetime.utcnow().isoformat()
            },
            memory_type=MemoryType.MARKET_OBSERVATION,
            importance=MemoryImportance.HIGH if market_data['regime_change'] else MemoryImportance.MEDIUM
        )
        
        # Share critical updates
        if market_data['regime_change']:
            await self.mcp.share_context(
                self.agent_id,
                ['StrategicPlannerAgent', 'ExecutorAgent'],
                {'regime_change': market_data}
            )
```

#### Strategic Planner Agent

```python  
class StrategicPlannerAgent(MCPAgent):
    def get_capabilities(self):
        return ['strategic_planning', 'risk_assessment', 'strategy_selection']
        
    async def plan_strategy(self, session_id: str):
        # Use agent context for session tracking
        async with self.mcp.agent_context(self.agent_id, session_id) as ctx:
            # Search for similar market conditions
            market_desc = await self._get_market_description()
            similar_conditions = await ctx.semantic_search(market_desc)
            
            # Analyze past successes
            recent_trades = await ctx.retrieve_memories(
                MemoryQuery(
                    memory_types=[MemoryType.TRADE_OUTCOME],
                    start_time=datetime.utcnow() - timedelta(days=7)
                )
            )
            
            # Create strategy
            strategy = self._create_strategy(similar_conditions, recent_trades)
            
            # Store plan
            await ctx.store_memory(MemorySlice(
                memory_type=MemoryType.STRATEGIC_PLANNING,
                content=strategy,
                importance=MemoryImportance.HIGH
            ))
            
            return strategy
```

#### Executor Agent

```python
class ExecutorAgent(MCPAgent):
    def get_capabilities(self):
        return ['trade_execution', 'order_management', 'position_monitoring']
        
    async def execute_trade(self, plan: dict, session_id: str):
        async with self.mcp.agent_context(self.agent_id, session_id) as ctx:
            # Store execution start
            await ctx.store_memory(MemorySlice(
                memory_type=MemoryType.EXECUTION_PLAN,
                content={
                    'plan': plan,
                    'start_time': datetime.utcnow().isoformat(),
                    'status': 'executing'
                },
                importance=MemoryImportance.HIGH
            ))
            
            # Execute trade
            result = await self._execute_ibkr_trade(plan)
            
            # Store outcome
            outcome_memory = await ctx.store_memory(MemorySlice(
                memory_type=MemoryType.TRADE_OUTCOME,
                content=result,
                importance=MemoryImportance.CRITICAL
            ))
            
            # Notify evaluator
            await ctx.share_context(
                ['EvaluatorAgent'],
                {'trade_completed': result}
            )
            
            return result
```

### 5. Update Existing Memory Files

Convert existing JSON memory files to MCP:

```python
async def migrate_existing_memories():
    # Load existing memories
    with open('backend/agents/memory/environment_watcher_memory.json') as f:
        env_memory = json.load(f)
        
    # Convert to MCP memories
    async with mcp_manager.agent_context('EnvironmentWatcherAgent') as ctx:
        # Migrate regime history
        for regime_change in env_memory.get('regime_history', []):
            await ctx.store_memory(MemorySlice(
                memory_type=MemoryType.MARKET_OBSERVATION,
                content=regime_change,
                importance=MemoryImportance.HIGH,
                created_at=datetime.fromisoformat(regime_change['timestamp'])
            ))
```

### 6. Enable Learning & Reflection

Add reflection methods to agents:

```python
class EvaluatorAgent(MCPAgent):
    async def evaluate_session(self, session_id: str):
        # Evaluate performance
        evaluation = await self._calculate_metrics(session_id)
        
        # Submit reflection
        reflection = {
            'session_id': session_id,
            'performance': evaluation,
            'patterns': self._identify_patterns(evaluation),
            'improvements': self._suggest_improvements(evaluation)
        }
        
        await self.mcp.submit_reflection(self.agent_id, reflection)
```

### 7. Update API Endpoints

Modify endpoints to use MCP:

```python
@app.post("/api/agent/memory/search")
async def search_memories(query: str, agent_id: str):
    """Semantic search across agent memories"""
    memories = await app.state.mcp.semantic_search(
        agent_id=agent_id,
        query_text=query,
        scope="session"
    )
    return {"memories": [m.dict() for m in memories]}

@app.get("/api/agent/{agent_id}/insights")
async def get_agent_insights(agent_id: str):
    """Get learning insights for an agent"""
    insights = await app.state.mcp.get_learning_insights(
        agent_id=agent_id,
        timeframe=timedelta(days=30)
    )
    return insights
```

## Best Practices

1. **Memory Types**: Use appropriate memory types for different content
2. **Importance Levels**: Mark critical memories (trades, risks) as HIGH/CRITICAL
3. **Session Context**: Always use agent_context for session tracking
4. **Semantic Search**: Use descriptive text for better search results
5. **Context Sharing**: Share insights proactively between agents
6. **Reflection**: Submit regular reflections for continuous learning

## Monitoring & Maintenance

1. **Memory Stats**: Monitor memory usage per agent
2. **Archival**: Old memories automatically archive to cold storage
3. **Performance**: Use batch operations for bulk memory storage
4. **Cleanup**: Implement memory consolidation for long sessions

## Troubleshooting

1. **Connection Issues**: Check all database connections are configured
2. **Memory Not Found**: Ensure proper memory type and importance
3. **Search Quality**: Improve search by using more descriptive content
4. **Performance**: Adjust batch sizes and concurrent operations

## Next Steps

After migrating:
1. Test memory persistence across sessions
2. Verify semantic search quality
3. Monitor inter-agent communication
4. Review learning insights
5. Optimize memory archival schedule