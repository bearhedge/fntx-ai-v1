#!/bin/bash
# Stop Enhanced SPY Downloader Script

set -e

SCRIPT_DIR="/home/info/fntx-ai-v1"
PID_FILE="$SCRIPT_DIR/runtime/pids/enhanced_downloader.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Enhanced SPY Downloader Stopper${NC}"
echo -e "${BLUE}===================================${NC}"

if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}⚠️ No PID file found. Downloader may not be running.${NC}"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! kill -0 "$PID" 2>/dev/null; then
    echo -e "${YELLOW}⚠️ Process $PID is not running. Cleaning up PID file.${NC}"
    rm -f "$PID_FILE"
    exit 1
fi

echo -e "${YELLOW}📡 Sending graceful shutdown signal to process $PID${NC}"

# Send SIGTERM for graceful shutdown
kill -TERM "$PID"

# Wait for graceful shutdown
echo -e "${BLUE}⏳ Waiting for graceful shutdown...${NC}"
for i in {1..30}; do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo -e "${GREEN}✅ Process stopped gracefully${NC}"
        rm -f "$PID_FILE"
        echo -e "${GREEN}🧹 Cleaned up PID file${NC}"
        echo -e "${BLUE}💾 Download progress has been saved and can be resumed${NC}"
        exit 0
    fi
    echo -n "."
    sleep 1
done

echo ""
echo -e "${YELLOW}⚠️ Process didn't stop gracefully. Forcing shutdown...${NC}"

# Force kill if graceful shutdown failed
kill -KILL "$PID"
rm -f "$PID_FILE"

echo -e "${RED}🔥 Process forcefully terminated${NC}"
echo -e "${YELLOW}⚠️ Some data might not have been saved${NC}"