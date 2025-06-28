#!/bin/bash

# FNTX AI Development Environment Startup Script
echo "Starting FNTX AI Development Environment..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the project root directory (two levels up from scripts/dev)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo "Project root: $PROJECT_ROOT"

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "${YELLOW}Warning: Port $port is already in use${NC}"
        return 1
    fi
    return 0
}

# Kill any existing processes
echo -e "${BLUE}Cleaning up existing processes...${NC}"
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

# Check required ports
echo -e "${BLUE}Checking ports...${NC}"
check_port 8080  # Frontend (Vite configured)
check_port 8002  # Orchestrator API

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

# Start backend services
echo -e "${GREEN}Starting Backend Services...${NC}"

# Orchestrator API Backend (Port 8000) - Main API for agent coordination
echo -e "${BLUE}Starting Orchestrator API Backend on port 8000...${NC}"
cd "$PROJECT_ROOT" && source venv/bin/activate && PYTHONPATH="$PROJECT_ROOT" python3 -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload > logs/api_server.log 2>&1 &
API_PID=$!

# Start EnvironmentWatcher Agent
echo -e "${BLUE}Starting EnvironmentWatcher Agent...${NC}"
cd "$PROJECT_ROOT" && source venv/bin/activate && PYTHONPATH="$PROJECT_ROOT" python3 -m backend.agents.environment_watcher > logs/environment_watcher.log 2>&1 &
ENV_PID=$!

# Wait a moment for backends to start
sleep 3

# Start Frontend (Port 8080 - Vite configured)
echo -e "${GREEN}Starting Frontend on port 8080...${NC}"
cd "$PROJECT_ROOT/frontend" && npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!

# Save PIDs for cleanup
echo "$API_PID" > "$PROJECT_ROOT/runtime/pids/api_server.pid"
echo "$ENV_PID" > "$PROJECT_ROOT/runtime/pids/environment_watcher.pid"
echo "$FRONTEND_PID" > "$PROJECT_ROOT/runtime/pids/frontend.pid"

# Wait for services to be ready
echo -e "${BLUE}Waiting for services to be ready...${NC}"
sleep 5

# Check service health
echo -e "${GREEN}Service Status:${NC}"
curl -s http://localhost:8000/health > /dev/null && echo -e "✓ Orchestrator API: ${GREEN}Running${NC}" || echo -e "✗ Orchestrator API: ${YELLOW}Failed${NC}"
curl -s http://localhost:8080 > /dev/null && echo -e "✓ Frontend: ${GREEN}Running${NC}" || echo -e "✗ Frontend: ${YELLOW}Failed${NC}"
ps -p $ENV_PID > /dev/null && echo -e "✓ EnvironmentWatcher: ${GREEN}Running${NC}" || echo -e "✗ EnvironmentWatcher: ${YELLOW}Failed${NC}"

echo -e "\n${GREEN}FNTX AI Development Environment Ready!${NC}"
echo -e "Frontend: ${BLUE}http://localhost:8080${NC}"
echo -e "Orchestrator API: ${BLUE}http://localhost:8000${NC}"

echo -e "\n${YELLOW}Logs are available in the 'logs' directory${NC}"
echo -e "${YELLOW}Run './scripts/stop-dev.sh' to stop all services${NC}"

# Keep script running to show logs
echo -e "\n${BLUE}Press Ctrl+C to stop all services...${NC}"
trap 'echo -e "\n${YELLOW}Stopping all services...${NC}"; pkill -P $$; exit' INT

# Follow logs
tail -f "$PROJECT_ROOT/logs"/*.log 2>/dev/null