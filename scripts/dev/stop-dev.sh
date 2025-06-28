#!/bin/bash

# FNTX AI Development Environment Stop Script
echo "Stopping FNTX AI Development Environment..."

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Kill processes by PID if files exist
if [ -f runtime/pids/api_server.pid ]; then
    kill $(cat runtime/pids/api_server.pid) 2>/dev/null && echo -e "${GREEN}✓ Stopped Orchestrator API${NC}" || echo -e "${YELLOW}Warning: Orchestrator API already stopped${NC}"
    rm runtime/pids/api_server.pid
fi

if [ -f runtime/pids/environment_watcher.pid ]; then
    kill $(cat runtime/pids/environment_watcher.pid) 2>/dev/null && echo -e "${GREEN}✓ Stopped EnvironmentWatcher${NC}" || echo -e "${YELLOW}Warning: EnvironmentWatcher already stopped${NC}"
    rm runtime/pids/environment_watcher.pid
fi

if [ -f runtime/pids/frontend.pid ]; then
    kill $(cat runtime/pids/frontend.pid) 2>/dev/null && echo -e "${GREEN}✓ Stopped Frontend${NC}" || echo -e "${YELLOW}Warning: Frontend already stopped${NC}"
    rm runtime/pids/frontend.pid
fi

# Fallback: kill by process name
pkill -f "uvicorn" 2>/dev/null
pkill -f "vite" 2>/dev/null

echo -e "${GREEN}All services stopped!${NC}"