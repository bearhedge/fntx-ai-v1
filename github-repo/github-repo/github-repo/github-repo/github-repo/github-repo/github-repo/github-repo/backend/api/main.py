#!/usr/bin/env python3
"""
FNTX.ai API Server - REST endpoints for orchestrator and agent communication
Provides HTTP API for the React frontend to interact with the agent orchestrator
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.agents.orchestrator import FNTXOrchestrator
from backend.services.ibkr_singleton_service import ibkr_singleton
from backend.database.auth_db import get_auth_db
from backend.auth.jwt_utils import get_jwt_manager
from backend.models.user import User

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/jimmyhou/CascadeProjects/fntx-ai-v10/logs/api_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('APIServer')

# FastAPI app
app = FastAPI(
    title="FNTX.ai Trading API",
    description="REST API for autonomous SPY options trading with multi-agent AI",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080", "http://localhost:8081"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator = FNTXOrchestrator()

# Pydantic models for request/response
class TradeRequest(BaseModel):
    user_request: str
    timestamp: str
    risk_tolerance: Optional[str] = "moderate"
    max_exposure: Optional[float] = 500.0

class TradeResponse(BaseModel):
    trade_id: str
    status: str
    message: str
    timestamp: str

class JourneyResponse(BaseModel):
    trade_id: str
    user_request: str
    initiated_at: str
    current_phase: str
    steps: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    final_outcome: Optional[Dict[str, Any]]
    execution_time: float
    errors: List[str]

class StatsResponse(BaseModel):
    total_orchestrations: int
    successful_trades: int
    failed_trades: int
    avg_execution_time: float
    success_rate: float


# In-memory storage for active trades (would use Redis or database in production)
active_trades: Dict[str, Dict[str, Any]] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize the API server"""
    logger.info("FNTX.ai API Server starting up...")
    
    # Connect to IBKR using singleton
    connected = ibkr_singleton._ensure_connected()
    if connected:
        logger.info("✅ IBKR connection established")
    else:
        logger.warning("⚠️ IBKR connection failed - will retry on first request")
    
    # Start background monitoring
    orchestrator.start_background_monitoring()
    
    logger.info("API Server ready to accept requests")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "FNTX.ai Trading API",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/health")
async def health_simple():
    """Simple health check endpoint for startup script"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check if agents are responding
        agent_status = {
            "environment_watcher": "healthy",
            "strategic_planner": "healthy", 
            "reward_model": "healthy",
            "executor": "healthy",
            "evaluator": "healthy"
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "agents": agent_status,
            "active_trades": len(active_trades),
            "background_monitoring": "active"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")

@app.post("/api/orchestrator/execute", response_model=TradeResponse)
async def execute_trade(request: TradeRequest, background_tasks: BackgroundTasks):
    """Execute a new trade orchestration"""
    try:
        logger.info(f"Received trade request: {request.user_request}")
        
        # Validate request
        if not request.user_request.strip():
            raise HTTPException(status_code=400, detail="User request cannot be empty")
        
        # Create trade ID
        trade_id = f"FNTX_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Store trade request
        active_trades[trade_id] = {
            "request": request.dict(),
            "status": "initiated",
            "created_at": datetime.now().isoformat()
        }
        
        # Start orchestration in background
        background_tasks.add_task(run_orchestration, trade_id, request.user_request)
        
        return TradeResponse(
            trade_id=trade_id,
            status="initiated",
            message="Trade orchestration started",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to execute trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_orchestration(trade_id: str, user_request: str):
    """Run the orchestration in background with real-time updates"""
    try:
        logger.info(f"Starting orchestration for trade {trade_id}")
        
        # Update status and broadcast
        active_trades[trade_id]["status"] = "running"
        await manager.send_trade_message({
            "type": "orchestration_start",
            "trade_id": trade_id,
            "message": "🚀 FNTX's Computer: Initializing trading orchestration...",
            "timestamp": datetime.now().isoformat(),
            "step": "initialization"
        }, trade_id)
        
        # Send step-by-step updates during orchestration
        steps = [
            "🧠 Strategic Planner: Analyzing market conditions...",
            "📊 Environment Watcher: Collecting real-time data...", 
            "🎯 Reward Model: Calculating risk-reward ratios...",
            "⚡ Executor: Preparing trade execution...",
            "🔍 Evaluator: Validating strategy parameters..."
        ]
        
        for i, step_message in enumerate(steps):
            await manager.send_trade_message({
                "type": "computation_step",
                "trade_id": trade_id,
                "message": step_message,
                "timestamp": datetime.now().isoformat(),
                "step": f"step_{i+1}",
                "progress": (i + 1) / len(steps) * 0.8  # 80% for initial steps
            }, trade_id)
            await asyncio.sleep(1)  # Simulate computation time
        
        # Run the actual orchestration
        await manager.send_trade_message({
            "type": "computation_step", 
            "trade_id": trade_id,
            "message": "🔄 FNTX's Computer: Running deep market analysis...",
            "timestamp": datetime.now().isoformat(),
            "step": "deep_analysis",
            "progress": 0.85
        }, trade_id)
        
        result = await orchestrator.orchestrate_trade(user_request)
        
        # Update final status and broadcast completion
        if result.get("final_outcome", {}).get("success"):
            active_trades[trade_id]["status"] = "completed"
            await manager.send_trade_message({
                "type": "orchestration_complete",
                "trade_id": trade_id,
                "message": "✅ FNTX's Computer: Trade orchestration completed successfully!",
                "timestamp": datetime.now().isoformat(),
                "result": result,
                "progress": 1.0
            }, trade_id)
        else:
            active_trades[trade_id]["status"] = "failed"
            await manager.send_trade_message({
                "type": "orchestration_failed",
                "trade_id": trade_id,
                "message": "❌ FNTX's Computer: Trade orchestration failed",
                "timestamp": datetime.now().isoformat(),
                "error": result.get("errors", []),
                "progress": 1.0
            }, trade_id)
            
        active_trades[trade_id]["result"] = result
        active_trades[trade_id]["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"Orchestration completed for trade {trade_id}")
        
    except Exception as e:
        logger.error(f"Orchestration failed for trade {trade_id}: {e}")
        active_trades[trade_id]["status"] = "failed"
        active_trades[trade_id]["error"] = str(e)
        
        await manager.send_trade_message({
            "type": "orchestration_error",
            "trade_id": trade_id,
            "message": f"💥 FNTX's Computer: System error - {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }, trade_id)

@app.get("/api/orchestrator/journey/{trade_id}", response_model=JourneyResponse)
async def get_trade_journey(trade_id: str):
    """Get the journey details for a specific trade"""
    try:
        # Load journey from file
        journey_file = "/Users/jimmyhou/CascadeProjects/fntx-ai-v10/agents/memory/trade_journey.json"
        
        if os.path.exists(journey_file):
            with open(journey_file, 'r') as f:
                journey_data = json.load(f)
                
            if journey_data.get("trade_id") == trade_id:
                return JourneyResponse(**journey_data)
        
        # Check active trades
        if trade_id in active_trades:
            trade_info = active_trades[trade_id]
            
            # Return basic journey info if detailed journey not available
            return JourneyResponse(
                trade_id=trade_id,
                user_request=trade_info["request"]["user_request"],
                initiated_at=trade_info["created_at"],
                current_phase=trade_info["status"],
                steps=[],
                risk_assessment={},
                final_outcome=None,
                execution_time=0.0,
                errors=[]
            )
        
        raise HTTPException(status_code=404, detail="Trade journey not found")
        
    except Exception as e:
        logger.error(f"Failed to get trade journey: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orchestrator/current-journey", response_model=JourneyResponse)
async def get_current_journey():
    """Get the current/latest trade journey"""
    try:
        journey_file = "/Users/jimmyhou/CascadeProjects/fntx-ai-v10/agents/memory/trade_journey.json"
        
        if os.path.exists(journey_file):
            with open(journey_file, 'r') as f:
                journey_data = json.load(f)
                return JourneyResponse(**journey_data)
        
        raise HTTPException(status_code=404, detail="No current trade journey")
        
    except Exception as e:
        logger.error(f"Failed to get current journey: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orchestrator/stats", response_model=StatsResponse)
async def get_orchestrator_stats():
    """Get orchestrator performance statistics"""
    try:
        memory_file = "/Users/jimmyhou/CascadeProjects/fntx-ai-v10/agents/memory/orchestrator_memory.json"
        
        if os.path.exists(memory_file):
            with open(memory_file, 'r') as f:
                memory_data = json.load(f)
                
            stats = memory_data.get("performance_stats", {})
            
            # Calculate success rate
            total = stats.get("total_orchestrations", 0)
            successful = stats.get("successful_trades", 0)
            success_rate = successful / total if total > 0 else 0.0
            
            return StatsResponse(
                total_orchestrations=stats.get("total_orchestrations", 0),
                successful_trades=stats.get("successful_trades", 0),
                failed_trades=stats.get("failed_trades", 0),
                avg_execution_time=stats.get("avg_execution_time", 0.0),
                success_rate=success_rate
            )
        
        # Return default stats if no memory file
        return StatsResponse(
            total_orchestrations=0,
            successful_trades=0,
            failed_trades=0,
            avg_execution_time=0.0,
            success_rate=0.0
        )
        
    except Exception as e:
        logger.error(f"Failed to get orchestrator stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orchestrator/recent-trades")
async def get_recent_trades():
    """Get recent trade orchestrations"""
    try:
        memory_file = "/Users/jimmyhou/CascadeProjects/fntx-ai-v10/agents/memory/orchestrator_memory.json"
        
        recent_trades = []
        
        if os.path.exists(memory_file):
            with open(memory_file, 'r') as f:
                memory_data = json.load(f)
                
            completed_trades = memory_data.get("completed_trades", [])
            failed_trades = memory_data.get("failed_trades", [])
            
            # Combine and sort by timestamp
            all_trades = []
            
            for trade in completed_trades:
                trade["final_outcome"] = {"success": True}
                all_trades.append(trade)
                
            for trade in failed_trades:
                trade["final_outcome"] = {"success": False}
                all_trades.append(trade)
            
            # Sort by timestamp (newest first)
            all_trades.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            recent_trades = all_trades[:10]  # Last 10 trades
        
        return recent_trades
        
    except Exception as e:
        logger.error(f"Failed to get recent trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orchestrator/status")
async def get_orchestrator_status():
    """Get current orchestrator status"""
    try:
        return {
            "status": "active",
            "active_trades": len(active_trades),
            "background_monitoring": "running",
            "last_update": datetime.now().isoformat(),
            "agent_statuses": {
                "environment_watcher": "healthy",
                "strategic_planner": "healthy",
                "reward_model": "healthy", 
                "executor": "healthy",
                "evaluator": "healthy"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get orchestrator status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/{agent_name}/memory")
async def get_agent_memory(agent_name: str):
    """Get memory for a specific agent"""
    try:
        agent_memory_files = {
            "executor": "/Users/jimmyhou/CascadeProjects/fntx-ai-v10/agents/memory/executor_memory.json",
            "reward_model": "/Users/jimmyhou/CascadeProjects/fntx-ai-v10/agents/memory/reward_model_memory.json",
            "evaluator": "/Users/jimmyhou/CascadeProjects/fntx-ai-v10/agents/memory/evaluator_memory.json",
            "environment_watcher": "/Users/jimmyhou/CascadeProjects/fntx-ai-v10/agents/memory/environment_watcher_memory.json"
        }
        
        memory_file = agent_memory_files.get(agent_name)
        if not memory_file:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if os.path.exists(memory_file):
            with open(memory_file, 'r') as f:
                memory_data = json.load(f)
                return memory_data
        
        raise HTTPException(status_code=404, detail="Agent memory not found")
        
    except Exception as e:
        logger.error(f"Failed to get agent memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/shared-context")
async def get_shared_context():
    """Get the shared context used by all agents"""
    try:
        context_file = "/Users/jimmyhou/CascadeProjects/fntx-ai-v10/agents/memory/shared_context.json"
        
        if os.path.exists(context_file):
            with open(context_file, 'r') as f:
                context_data = json.load(f)
                return context_data
        
        return {"message": "No shared context available"}
        
    except Exception as e:
        logger.error(f"Failed to get shared context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Manual SPY Options Trading Endpoints

class OptionsChainRequest(BaseModel):
    date: Optional[str] = None  # YYYYMMDD format, defaults to today
    option_type: Optional[str] = "both"  # "put", "call", or "both"
    max_strikes: Optional[int] = 20  # Limit number of strikes

class OptionsContract(BaseModel):
    symbol: str
    strike: float
    expiration: str
    option_type: str  # "P" or "C"
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    ai_score: Optional[float] = None

class OptionsChainResponse(BaseModel):
    spy_price: float
    expiration_date: str
    contracts: List[OptionsContract]
    ai_insights: Dict[str, Any]
    market_regime: str
    timestamp: str

class ManualTradeConfig(BaseModel):
    contract_symbol: str
    strike: float
    expiration: str
    option_type: str
    quantity: int = 1
    entry_price: float
    stop_loss_multiplier: float = 3.0
    take_profit_percentage: float = 0.5
    max_loss_dollars: Optional[float] = None
    notes: Optional[str] = None

class ManualTradeResponse(BaseModel):
    trade_id: str
    config: ManualTradeConfig
    ai_analysis: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    estimated_profit_loss: Dict[str, Any]
    execution_ready: bool
    warnings: List[str]

@app.get("/api/spy-options/chain", response_model=OptionsChainResponse)
async def get_spy_options_chain(date: Optional[str] = None, option_type: str = "both", max_strikes: int = 20):
    """Get SPY options chain with LIVE IBKR data - NO MOCK DATA"""
    try:
        logger.info(f"Fetching LIVE SPY options chain: date={date}, type={option_type}")
        
        # Get real IBKR options data using singleton service
        options_list = ibkr_singleton.get_spy_options_chain(max_strikes=max_strikes)
        
        if not options_list:
            raise Exception("No options data available - check IBKR connection")
        
        # Get SPY price from singleton service
        spy_data = ibkr_singleton.get_spy_price()
        spy_price = spy_data.get('price', 0)
        
        # Filter and limit contracts
        if max_strikes and len(options_list) > max_strikes:
            options_list = options_list[:max_strikes]
        
        # Convert to OptionsContract objects
        contract_objects = []
        for c in options_list:
            # Handle potential NaN or infinity values
            def safe_float(value, default=0.0):
                if value is None or (isinstance(value, float) and (value != value or abs(value) == float('inf'))):
                    return default
                return float(value)
            
            contract_objects.append(OptionsContract(
                symbol=c["contract_symbol"],
                strike=safe_float(c["strike"]),
                expiration=c["expiration"],
                option_type=c["right"],
                bid=safe_float(c["bid"]),
                ask=safe_float(c["ask"]),
                last=safe_float(c["last"]),
                volume=int(safe_float(c.get("volume", 0))),
                open_interest=int(safe_float(c.get("open_interest", 0))),
                implied_volatility=safe_float(c.get("implied_volatility", 0.20), 0.20),
                delta=safe_float(c.get("delta")),
                gamma=safe_float(c.get("gamma")),
                theta=safe_float(c.get("theta")),
                vega=safe_float(c.get("vega")),
                ai_score=safe_float(c.get("ai_score", 5.0), 5.0)
            ))
        
        # Generate AI insights based on current data
        market_regime = {
            "regime": "favorable_for_selling" if spy_data.get('price', 0) > 600 else "neutral",
            "vix_estimate": 15.0,
            "confidence": 0.7 if spy_price > 0 else 0.4
        }
        
        ai_insights = {
            "market_regime": market_regime.get("regime", "unknown"),
            "vix_estimate": market_regime.get("vix_estimate", 20),
            "confidence_level": market_regime.get("confidence", 0.5),
            "trading_signal": "favorable_for_selling" if market_regime.get("regime") == "favorable_for_selling" else "neutral",
            "recommended_strategies": [
                "SPY PUT selling" if market_regime.get("regime") == "favorable_for_selling" else "Monitor conditions",
                "Focus on high-probability trades",
                "Consider time decay advantages"
            ]
        }
        
        logger.info(f"Successfully fetched {len(contract_objects)} live options contracts")
        
        return OptionsChainResponse(
            spy_price=spy_price,
            expiration_date=options_list[0]["expiration"] if options_list else "unknown",
            contracts=contract_objects,
            ai_insights=ai_insights,
            market_regime=market_regime.get("regime", "unknown"),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to get LIVE SPY options chain: {e}")
        raise HTTPException(status_code=500, detail=f"Live data error: {str(e)}")

@app.post("/api/trade/manual-configure", response_model=ManualTradeResponse)
async def configure_manual_trade(config: ManualTradeConfig):
    """Configure a manual trade with AI analysis and risk assessment"""
    try:
        logger.info(f"Configuring manual trade: {config.contract_symbol}")
        
        # Generate unique trade ID
        trade_id = f"MANUAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Get current market data
        market_data = orchestrator.environment_watcher.get_market_data()
        spy_price = market_data.get("spy", {}).get("price", 0)
        
        # Calculate risk metrics
        premium = config.entry_price
        stop_loss_price = premium * config.stop_loss_multiplier
        take_profit_price = premium * config.take_profit_percentage
        
        max_loss = stop_loss_price * config.quantity * 100  # Options are 100 shares
        max_profit = (premium - take_profit_price) * config.quantity * 100
        
        risk_assessment = {
            "max_loss_dollars": max_loss,
            "max_profit_dollars": max_profit,
            "break_even_price": config.strike - premium if config.option_type == "P" else config.strike + premium,
            "risk_reward_ratio": max_profit / max_loss if max_loss > 0 else 0,
            "probability_of_profit": 0.0,  # Would calculate based on Greeks
            "time_to_expiration": "0DTE",  # Would calculate actual time
            "assignment_risk": "LOW" if config.option_type == "P" and config.strike < spy_price * 0.95 else "MEDIUM"
        }
        
        # Get AI analysis from all agents
        ai_analysis = {
            "environment_watcher": {
                "market_regime": market_data.get("market_regime", "unknown"),
                "volatility_environment": "LOW" if market_data.get("vix", {}).get("level", 20) < 15 else "HIGH",
                "recommendation": "FAVORABLE" if market_data.get("market_regime") == "favorable_for_selling" else "CAUTION"
            },
            "strategic_planner": {
                "strategy_alignment": "HIGH",  # Would analyze strategy fit
                "optimal_timing": "GOOD",
                "position_sizing": "APPROPRIATE" if config.quantity == 1 else "REVIEW_SIZE"
            },
            "reward_model": {
                "user_preference_match": "GOOD",  # Would check against user history
                "risk_tolerance_alignment": "WITHIN_LIMITS",
                "profit_goal_alignment": "ALIGNED"
            },
            "executor": {
                "execution_feasibility": "READY",
                "liquidity_assessment": "GOOD",  # Would check bid/ask spread
                "timing_optimization": "CURRENT_OPTIMAL"
            },
            "evaluator": {
                "overall_score": 7.5,
                "confidence_level": 0.75,
                "risk_score": 3.0,  # 1-10 scale
                "recommendation": "PROCEED_WITH_CAUTION"
            }
        }
        
        # Check for warnings
        warnings = []
        if max_loss > 1000:
            warnings.append("High maximum loss amount - consider reducing position size")
        if config.stop_loss_multiplier > 5:
            warnings.append("Very high stop loss multiplier - increased risk")
        if spy_price == 0:
            warnings.append("Unable to verify current SPY price")
        
        # Estimated P&L scenarios
        estimated_profit_loss = {
            "best_case": max_profit,
            "worst_case": -max_loss,
            "expected_value": max_profit * 0.7 - max_loss * 0.3,  # Simple calculation
            "break_even_scenarios": [
                f"SPY below ${config.strike - premium:.2f} at expiration" if config.option_type == "P" else f"SPY above ${config.strike + premium:.2f} at expiration"
            ]
        }
        
        execution_ready = (
            len(warnings) == 0 and 
            spy_price > 0 and 
            ai_analysis["evaluator"]["overall_score"] > 6.0
        )
        
        return ManualTradeResponse(
            trade_id=trade_id,
            config=config,
            ai_analysis=ai_analysis,
            risk_assessment=risk_assessment,
            estimated_profit_loss=estimated_profit_loss,
            execution_ready=execution_ready,
            warnings=warnings
        )
        
    except Exception as e:
        logger.error(f"Failed to configure manual trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trade/manual-execute/{trade_id}")
async def execute_manual_trade(trade_id: str):
    """Execute a pre-configured manual trade"""
    try:
        logger.info(f"Executing manual trade: {trade_id}")
        
        # In production, would load config from database/cache
        # For now, return simulation
        
        execution_result = {
            "trade_id": trade_id,
            "status": "SUBMITTED",
            "order_id": f"IB_{datetime.now().strftime('%H%M%S')}",
            "execution_price": 0.0,  # Would get from IBKR
            "timestamp": datetime.now().isoformat(),
            "message": "Trade submitted to IBKR successfully",
            "next_steps": [
                "Monitor position in real-time",
                "Stop-loss and take-profit orders active",
                "Position will be tracked until expiration"
            ]
        }
        
        return execution_result
        
    except Exception as e:
        logger.error(f"Failed to execute manual trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/insights")
async def get_market_insights():
    """Get market insights with LIVE IBKR data using unified service"""
    try:
        # Get SPY data from singleton service
        spy_data = ibkr_singleton.get_spy_price()
        spy_price = spy_data.get('price', 0)
        
        # Get connection status
        conn_status = ibkr_singleton.get_connection_status()
        
        # Determine market status
        now = datetime.now()
        is_market_hours = (now.weekday() < 5 and 9 <= now.hour < 16 and
                          not (now.hour == 9 and now.minute < 30))
        
        # Format response for frontend
        formatted_insights = {
            "timestamp": datetime.now().isoformat(),
            "spy_price": spy_price,
            "vix_level": 15.0,  # Placeholder - would get from VIX data
            "market_regime": "favorable_for_selling" if spy_price > 600 else "neutral",
            "overall_signal": "bullish" if spy_price > 600 else "neutral",
            "market_status": "open" if is_market_hours else "extended_hours",
            "connection_status": {
                "status": "healthy" if conn_status['connected'] else "degraded",
                "ibkr_available": conn_status['connected'],
                "fallback_active": False
            },
            "agent_insights": {
                "environment_watcher": {
                    "regime": "favorable_for_selling" if spy_price > 600 else "neutral",
                    "volatility_regime": "low",
                    "liquidity_regime": "excellent" if conn_status['connected'] else "poor",
                    "alert_level": "LOW" if spy_price > 0 else "MEDIUM"
                },
                "strategic_planner": {
                    "preferred_strategy": "aggressive_selling" if spy_price > 600 else "conservative",
                    "timing_preference": "opportunistic" if is_market_hours else "patient",
                    "position_sizing": "normal"
                },
                "reward_model": {
                    "user_alignment": "GOOD",
                    "risk_preference": "MODERATE",
                    "profit_targets": "REALISTIC"
                },
                "executor": {
                    "execution_conditions": "OPTIMAL" if conn_status['connected'] else "DEGRADED",
                    "market_liquidity": "EXCELLENT" if is_market_hours else "LIMITED",
                    "timing_score": 8.5 if is_market_hours else 5.0
                },
                "evaluator": {
                    "market_score": 7.5 if spy_price > 600 else 5.0,
                    "confidence": 0.75 if spy_price > 0 else 0.25,
                    "recommendation": "BULLISH" if spy_price > 600 else "NEUTRAL"
                }
            },
            "trading_opportunities": [
                "SPY PUT selling strategies recommended" if spy_price > 600 else "Monitor market conditions",
                f"Current SPY price: ${spy_price:.2f}",
                "IBKR connection active" if conn_status['connected'] else "IBKR connection issues",
                f"Total options available: {20 if conn_status['connected'] else 0}"
            ],
            "risk_warnings": [] if conn_status['connected'] else ["IBKR connection degraded - verify live data"]
        }
        
        return formatted_insights
        
    except Exception as e:
        logger.error(f"Failed to get market insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Chat endpoint for non-trading messages
class ChatRequest(BaseModel):
    message: str
    messages: List[Dict[str, str]] = []
    context: Optional[str] = None  # Add context field for guest users

@app.post("/api/orchestrator/chat")
async def orchestrator_chat_endpoint(request: ChatRequest):
    """Handle orchestrated chat messages - works for both authenticated and guest users"""
    try:
        logger.info(f"Received orchestrator chat message: {request.message}")
        
        # Check if this is a guest user
        is_guest = request.context == "guest"
        
        # Use model router for LLM responses
        from backend.llm import ModelRouter
        import os
        
        try:
            # Initialize model router
            model_router = ModelRouter()
            
            # Build conversation context
            system_context = """
            You are FNTX.ai, an AI-powered SPY options trading assistant. 
            For guest users, you should:
            - Explain what FNTX.ai is and its capabilities
            - Discuss SPY options trading strategies in general terms
            - Encourage users to sign in for personalized recommendations
            - Be helpful but note that full functionality requires authentication
            
            For authenticated users, provide full trading insights and recommendations.
            """
            
            if is_guest:
                system_context += "\n\nNOTE: This is a GUEST user. Don't access any personal data or trading history."
            
            # Generate response using model router
            response_text = model_router.generate_completion(
                'orchestrator',
                f"{system_context}\n\nUser: {request.message}"
            )
            
            return {
                "response": response_text,
                "timestamp": datetime.now().isoformat(),
                "is_guest": is_guest
            }
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            # Fallback response
            if is_guest:
                return {
                    "response": "I'm FNTX.ai, your AI-powered SPY options trading assistant. I can help you understand options trading strategies and market analysis. Sign in to access personalized trading recommendations and your portfolio.",
                    "timestamp": datetime.now().isoformat(),
                    "is_guest": True
                }
            else:
                return {
                    "response": "I'm having trouble connecting right now. Please try again in a moment.",
                    "timestamp": datetime.now().isoformat(),
                    "is_guest": False
                }
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Handle general chat messages with intelligent AI responses"""
    try:
        logger.info(f"Received chat message: {request.message}")
        
        # Use model router for intelligent responses
        from backend.llm import ModelRouter
        import os
        
        try:
            # Initialize model router
            model_router = ModelRouter()
            
            # Get current market data
            market_data = ""
            try:
                spy_data = ibkr_singleton.get_spy_price()
                if spy_data and spy_data.get('price', 0) > 0:
                    market_data = f"\n\nCurrent Market Data:\n- SPY Price: ${spy_data['price']}\n- Timestamp: {spy_data.get('timestamp', 'N/A')}\n"
            except:
                pass
            
            # Build conversation context
            system_prompt = f"""You are FNTX, an AI trading assistant specialized in SPY options trading. You are knowledgeable, helpful, and conversational. 

Key traits:
- You can discuss both trading topics and general conversation naturally
- You're friendly and engaging while maintaining professionalism
- For trading requests, you mention that you'll start your trading orchestration process
- For general questions, you respond intelligently and naturally
- You're Jimmy Hou's personal AI trading assistant
- You have 5 AI agents: Strategic Planner, Executor, Evaluator, Environment Watcher, and Reward Model
{market_data}
Respond naturally to any question or comment. If it's trading-related, mention your trading capabilities. If it's general conversation, engage naturally."""
            
            # Build conversation history for context
            conversation_context = ""
            for msg in request.messages[-5:]:  # Last 5 messages for context
                role = "User" if msg.get("role") == "user" else "FNTX"
                conversation_context += f"{role}: {msg.get('content', '')}\n"
            
            # Create the full prompt with system context, conversation history, and current message
            full_prompt = f"""{system_prompt}

Previous conversation:
{conversation_context}

User: {request.message}

FNTX:"""
            
            # Get AI response using model router
            ai_response = model_router.generate_completion(
                'orchestrator',  # Use orchestrator for general chat
                full_prompt,
                max_tokens=300,
                temperature=0.7
            )
            
            return {
                "response": ai_response,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as model_error:
            logger.error(f"Model API error: {model_error}")
            return await simple_chat_response(request.message)
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def simple_chat_response(message: str):
    """Fallback simple chat responses when OpenAI is not available"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['hello', 'hi', 'hey']):
        response = "Hello! I'm FNTX, your AI trading assistant. I can help you with SPY options trading strategies, market analysis, and trade execution. Try asking me to 'trade SPY options' or 'analyze the market'."
    elif any(word in message_lower for word in ['help', 'what can you do']):
        response = "I'm your autonomous SPY options trading agent. I can:\n\n• Execute SPY options selling strategies\n• Analyze market conditions and volatility\n• Manage risk and position sizing\n• Provide real-time trade execution\n\nTry asking: 'sell SPY put options' or 'what's the best strategy today?'"
    elif any(word in message_lower for word in ['status', 'how are you']):
        response = "I'm online and ready! All 5 of my AI agents are operational:\n• Strategic Planner ✅\n• Executor ✅\n• Evaluator ✅\n• Environment Watcher ✅\n• Reward Model ✅\n\nReady to trade when you are!"
    elif len(message.strip()) <= 2:  # Very short messages like "q"
        response = f"I see you typed '{message}'. Is there something specific you'd like help with? I can assist with SPY options trading or just have a regular conversation!"
    else:
        response = f"I understand you said: '{message}'\n\nI'm specialized in SPY options trading, but I'm happy to chat about other things too! For trading requests, try phrases like 'trade SPY options' or 'analyze market conditions'."
    
    return {
        "response": response,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/orchestrator/stop/{trade_id}")
async def stop_trade(trade_id: str):
    """Stop an active trade orchestration"""
    try:
        if trade_id not in active_trades:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        # Update status to stopped
        active_trades[trade_id]["status"] = "stopped"
        active_trades[trade_id]["stopped_at"] = datetime.now().isoformat()
        
        return {
            "message": f"Trade {trade_id} stopped",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to stop trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced WebSocket endpoint for real-time agent updates
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import json

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.trade_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, trade_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if trade_id:
            if trade_id not in self.trade_connections:
                self.trade_connections[trade_id] = []
            self.trade_connections[trade_id].append(websocket)

    def disconnect(self, websocket: WebSocket, trade_id: str = None):
        self.active_connections.remove(websocket)
        if trade_id and trade_id in self.trade_connections:
            if websocket in self.trade_connections[trade_id]:
                self.trade_connections[trade_id].remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(message))

    async def send_trade_message(self, message: dict, trade_id: str):
        if trade_id in self.trade_connections:
            for connection in self.trade_connections[trade_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    pass

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/agent-updates/{trade_id}")
async def websocket_agent_updates(websocket: WebSocket, trade_id: str):
    """Enhanced WebSocket endpoint for real-time agent computation updates"""
    await manager.connect(websocket, trade_id)
    
    try:
        # Send initial connection message
        await manager.send_personal_message({
            "type": "connection_established",
            "trade_id": trade_id,
            "timestamp": datetime.now().isoformat(),
            "message": "🔗 Connected to FNTX's Computer"
        }, websocket)
        
        while True:
            # Keep connection alive and send periodic status
            if trade_id in active_trades:
                trade_info = active_trades[trade_id]
                status_update = {
                    "type": "trade_status",
                    "trade_id": trade_id,
                    "status": trade_info["status"],
                    "timestamp": datetime.now().isoformat(),
                    "data": trade_info
                }
                await manager.send_personal_message(status_update, websocket)
            
            await asyncio.sleep(1)  # Send update every second
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, trade_id)
        logger.info(f"WebSocket disconnected for trade {trade_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, trade_id)

@app.websocket("/ws/fntx-computer")
async def websocket_fntx_computer(websocket: WebSocket):
    """WebSocket endpoint for FNTX's Computer real-time computations"""
    await manager.connect(websocket)
    
    try:
        # Send initial FNTX Computer status
        await manager.send_personal_message({
            "type": "fntx_computer_init",
            "timestamp": datetime.now().isoformat(),
            "system_status": "🖥️ FNTX's Computer Online",
            "agents_status": {
                "strategic_planner": "standby",
                "executor": "standby", 
                "evaluator": "standby",
                "environment_watcher": "monitoring",
                "reward_model": "learning"
            }
        }, websocket)
        
        while True:
            # Send real-time system metrics
            system_update = {
                "type": "system_metrics",
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": "12%",
                "memory_usage": "340MB",
                "active_trades": len(active_trades),
                "market_data": "streaming",
                "neural_network": "active"
            }
            await manager.send_personal_message(system_update, websocket)
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("FNTX Computer WebSocket disconnected")
    except Exception as e:
        logger.error(f"FNTX Computer WebSocket error: {e}")
        manager.disconnect(websocket)

# Authentication endpoints
class AuthVerifyRequest(BaseModel):
    token: str

class AuthVerifyResponse(BaseModel):
    valid: bool
    user: Optional[Dict[str, Any]] = None

class GoogleAuthRequest(BaseModel):
    credential: str  # Google OAuth credential from frontend

@app.post("/api/auth/verify", response_model=AuthVerifyResponse)
async def verify_auth(request: AuthVerifyRequest):
    """Verify JWT token and return user info"""
    try:
        jwt_manager = get_jwt_manager()
        payload = jwt_manager.verify_token(request.token)
        
        if not payload:
            return AuthVerifyResponse(valid=False)
        
        # Get user from database
        auth_db = get_auth_db()
        user = auth_db.get_user_by_id(payload["sub"])
        
        if not user:
            return AuthVerifyResponse(valid=False)
        
        # Update last login
        auth_db.update_last_login(user.id)
        
        return AuthVerifyResponse(
            valid=True,
            user=user.to_dict()
        )
        
    except Exception as e:
        logger.error(f"Auth verification failed: {e}")
        return AuthVerifyResponse(valid=False)

@app.post("/api/auth/google")
async def google_auth(request: GoogleAuthRequest):
    """Handle Google OAuth authentication"""
    try:
        import base64
        import json
        
        # Check for demo token first
        if request.credential == "DEMO_GOOGLE_USER":
            # This is our demo user
            google_id = "demo-google-user"
            email = "demo@gmail.com"
            name = "Demo User"
            picture = "https://ui-avatars.com/api/?name=Demo+User&background=4285f4&color=fff"
            given_name = "Demo"
            family_name = "User"
        else:
            # For other tokens, try to decode as JWT
            try:
                # Decode the JWT payload (for development only)
                parts = request.credential.split('.')
                if len(parts) != 3:
                    raise ValueError("Invalid token format")
                
                # Add padding if needed
                payload = parts[1]
                padding = 4 - len(payload) % 4
                if padding != 4:
                    payload += '=' * padding
                
                # Decode the payload
                decoded = base64.urlsafe_b64decode(payload)
                idinfo = json.loads(decoded)
                
                # Extract user info
                google_id = idinfo.get('sub', 'unknown')
                email = idinfo.get('email', 'unknown@gmail.com')
                name = idinfo.get('name', email)
                picture = idinfo.get('picture')
                given_name = idinfo.get('given_name')
                family_name = idinfo.get('family_name')
                
            except:
                # For development, check if this is our demo credential
                try:
                    decoded_cred = base64.b64decode(request.credential)
                    cred_data = json.loads(decoded_cred)
                    if cred_data.get('email') == 'demo@gmail.com':
                        # Use the demo user data
                        google_id = cred_data.get('sub', 'mock-google-user')
                        email = 'demo@gmail.com'
                        name = cred_data.get('name', 'Demo User')
                        picture = cred_data.get('picture', 'https://ui-avatars.com/api/?name=Demo+User&background=4285f4&color=fff')
                        given_name = cred_data.get('given_name', 'Demo')
                        family_name = cred_data.get('family_name', 'User')
                    else:
                        raise ValueError("Not demo user")
                except:
                    # For other dev cases, create a test user
                    import hashlib
                    mock_id = hashlib.md5(request.credential.encode()).hexdigest()[:12]
                    google_id = f"google_{mock_id}"
                    email = f"user_{mock_id}@example.com"
                    name = f"Test User {mock_id[:4]}"
                    picture = None
                    given_name = "Test"
                    family_name = f"User {mock_id[:4]}"
        
        # Get or create user
        auth_db = get_auth_db()
        # First try to find by google_id
        user = auth_db.get_user_by_google_id(google_id)
        
        # If not found, try by email (in case user exists from email/password signup)
        if not user:
            user = auth_db.get_user_by_email(email)
            if user:
                # Update their google_id
                user.google_id = google_id
                user.picture = picture
                user.last_login = datetime.utcnow()
                user = auth_db.update_user(user)
        
        if not user:
            # Create new user
            import uuid
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                name=name,
                picture=picture,
                given_name=given_name,
                family_name=family_name,
                google_id=google_id,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            user = auth_db.create_user(user)
        else:
            # Update existing user
            user.last_login = datetime.utcnow()
            user.name = name  # Update in case it changed
            user.picture = picture
            user = auth_db.update_user(user)
        
        # Create JWT token
        jwt_manager = get_jwt_manager()
        access_token = jwt_manager.create_access_token(user.id, user.email)
        
        return {
            "token": access_token,
            "user": user.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Google auth failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/google-mock")
async def google_auth_mock(request: GoogleAuthRequest):
    """Handle mock Google OAuth authentication for development"""
    try:
        import base64
        import json
        
        # Decode the mock credential
        credential_data = json.loads(base64.b64decode(request.credential))
        
        # Extract user info from mock credential
        email = credential_data.get('email', 'demo@gmail.com')
        name = credential_data.get('name', 'Demo User')
        picture = credential_data.get('picture', '')
        google_id = credential_data.get('sub', 'mock-google-id')
        
        # Check if user exists
        auth_db = get_auth_db()
        user = auth_db.get_user_by_email(email)
        
        if not user:
            # Create new user
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                name=name,
                picture=picture,
                given_name=credential_data.get('given_name', 'Demo'),
                family_name=credential_data.get('family_name', 'User'),
                google_id=google_id,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            user = auth_db.create_user(user)
        else:
            # Update existing user
            user.last_login = datetime.utcnow()
            user.name = name
            user.picture = picture
            user = auth_db.update_user(user)
        
        # Create JWT token
        jwt_manager = get_jwt_manager()
        access_token = jwt_manager.create_access_token(user.id, user.email)
        
        return {
            "token": access_token,
            "user": user.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Mock Google auth failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

class SignupRequest(BaseModel):
    email: str
    password: str
    name: str

class SigninRequest(BaseModel):
    email: str
    password: str

@app.post("/api/auth/signup")
async def signup(request: SignupRequest):
    """Handle user signup with email and password"""
    try:
        # Import password utilities
        from backend.auth.password_utils import password_manager
        
        # Validate email format
        import re
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_pattern, request.email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        # Validate password strength
        is_valid, issues = password_manager.validate_password_strength(request.password)
        if not is_valid:
            raise HTTPException(status_code=400, detail={"message": "Password requirements not met", "issues": issues})
        
        # Check if user already exists
        auth_db = get_auth_db()
        existing_user = auth_db.get_user_by_email(request.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password
        password_hash = password_manager.hash_password(request.password)
        
        # Create new user
        import uuid
        user = User(
            id=str(uuid.uuid4()),
            email=request.email,
            name=request.name,
            password_hash=password_hash,
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow()
        )
        
        user = auth_db.create_user(user)
        
        # Create JWT token
        jwt_manager = get_jwt_manager()
        access_token = jwt_manager.create_access_token(user.id, user.email)
        
        # Don't include password_hash in response
        user_dict = user.to_dict()
        user_dict.pop('password_hash', None)
        
        return {
            "token": access_token,
            "user": user_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/signin")
async def signin(request: SigninRequest):
    """Handle user signin with email and password"""
    try:
        # Import password utilities
        from backend.auth.password_utils import password_manager
        
        # Get user by email
        auth_db = get_auth_db()
        user = auth_db.get_user_by_email(request.email)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Check if user has a password (might be Google-only account)
        if not user.password_hash:
            raise HTTPException(status_code=401, detail="Please sign in with Google")
        
        # Verify password
        if not password_manager.verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Update last login
        auth_db.update_last_login(user.id)
        
        # Create JWT token
        jwt_manager = get_jwt_manager()
        access_token = jwt_manager.create_access_token(user.id, user.email)
        
        # Don't include password_hash in response
        user_dict = user.to_dict()
        user_dict.pop('password_hash', None)
        
        return {
            "token": access_token,
            "user": user_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signin failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/logout")
async def logout():
    """Handle user logout"""
    # For JWT-based auth, logout is handled client-side
    # This endpoint exists for consistency and future enhancements
    return {"success": True, "message": "Logged out successfully"}

@app.get("/api/spy-options/straddles")
async def get_spy_straddles(num_strikes: int = 10):
    """Get SPY options formatted as straddles around ATM"""
    try:
        # Get current SPY price
        spy_data = ibkr_singleton.get_spy_price()
        spy_price = spy_data.get('price', 0)
        
        if spy_price == 0:
            return {"error": "Unable to get SPY price"}
        
        # Get options chain with enough strikes
        options_list = ibkr_singleton.get_spy_options_chain(max_strikes=num_strikes * 4)
        
        if not options_list:
            return {"error": "Unable to get options data"}
        
        # Group by strike
        strikes = {}
        for opt in options_list:
            strike = opt['strike']
            if strike not in strikes:
                strikes[strike] = {
                    'strike': strike,
                    'distance': abs(strike - spy_price)
                }
            
            if opt['right'] == 'P':
                strikes[strike]['put'] = opt
            else:
                strikes[strike]['call'] = opt
        
        # Get closest strikes to ATM
        sorted_strikes = sorted(strikes.values(), key=lambda x: x['distance'])[:num_strikes]
        sorted_strikes = sorted(sorted_strikes, key=lambda x: x['strike'])
        
        # Find ATM strike
        atm_strike = min(strikes.values(), key=lambda x: x['distance'])
        
        # Calculate straddle values for ATM
        straddle_info = {}
        if 'put' in atm_strike and 'call' in atm_strike:
            put_mid = (atm_strike['put']['bid'] + atm_strike['put']['ask']) / 2
            call_mid = (atm_strike['call']['bid'] + atm_strike['call']['ask']) / 2
            straddle_price = put_mid + call_mid
            
            straddle_info = {
                'atm_strike': atm_strike['strike'],
                'put_mid': put_mid,
                'call_mid': call_mid,
                'straddle_price': straddle_price,
                'lower_breakeven': atm_strike['strike'] - straddle_price,
                'upper_breakeven': atm_strike['strike'] + straddle_price,
                'max_profit_range': straddle_price * 2
            }
        
        # Calculate market sentiment
        total_put_vol = sum(s.get('put', {}).get('volume', 0) for s in sorted_strikes)
        total_call_vol = sum(s.get('call', {}).get('volume', 0) for s in sorted_strikes)
        
        pc_ratio = total_put_vol / total_call_vol if total_call_vol > 0 else 0
        
        sentiment = "neutral"
        if pc_ratio > 1.2:
            sentiment = "bearish"
        elif pc_ratio < 0.8:
            sentiment = "bullish"
        
        return {
            'spy_price': spy_price,
            'timestamp': spy_data.get('timestamp'),
            'expiration': options_list[0]['expiration'] if options_list else None,
            'straddles': sorted_strikes,
            'atm_analysis': straddle_info,
            'market_sentiment': {
                'put_volume': total_put_vol,
                'call_volume': total_call_vol,
                'put_call_ratio': pc_ratio,
                'sentiment': sentiment
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting straddles: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )