#!/bin/bash
# Enhanced SPY Downloader Background Starter
# Runs the download process in background with proper logging and monitoring

set -e

SCRIPT_DIR="/home/info/fntx-ai-v1"
LOG_DIR="$SCRIPT_DIR/logs"
VENV_DIR="$SCRIPT_DIR/venv"
DOWNLOADER_SCRIPT="$SCRIPT_DIR/enhanced_spy_downloader.py"
PID_FILE="$SCRIPT_DIR/runtime/pids/enhanced_downloader.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Enhanced SPY Options Downloader Launcher${NC}"
echo -e "${BLUE}=============================================${NC}"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${YELLOW}⚠️ Downloader is already running (PID: $PID)${NC}"
        echo "Use './stop_enhanced_download.sh' to stop it first"
        exit 1
    else
        echo -e "${YELLOW}⚠️ Removing stale PID file${NC}"
        rm -f "$PID_FILE"
    fi
fi

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$SCRIPT_DIR/runtime/pids"

# Activate virtual environment if it exists
if [ -d "$VENV_DIR" ]; then
    echo -e "${GREEN}📦 Activating virtual environment${NC}"
    source "$VENV_DIR/bin/activate"
else
    echo -e "${YELLOW}⚠️ No virtual environment found, using system Python${NC}"
fi

# Check Python dependencies
echo -e "${BLUE}🔍 Checking dependencies${NC}"
python3 -c "import psycopg2, requests" 2>/dev/null || {
    echo -e "${RED}❌ Missing dependencies. Installing...${NC}"
    pip3 install psycopg2-binary requests
}

# Set environment variables
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
export PYTHONUNBUFFERED=1

# Log file with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
MAIN_LOG="$LOG_DIR/enhanced_downloader_$TIMESTAMP.log"
BACKGROUND_LOG="$LOG_DIR/enhanced_downloader_background.log"

echo -e "${GREEN}📝 Logs will be written to:${NC}"
echo "   Main: $MAIN_LOG"
echo "   Background: $BACKGROUND_LOG"

# Start the downloader in background
echo -e "${GREEN}🚀 Starting Enhanced SPY Downloader in background...${NC}"

nohup python3 "$DOWNLOADER_SCRIPT" > "$BACKGROUND_LOG" 2>&1 &
DOWNLOADER_PID=$!

# Save PID
echo "$DOWNLOADER_PID" > "$PID_FILE"

# Wait a moment to see if it started successfully
sleep 3

if kill -0 "$DOWNLOADER_PID" 2>/dev/null; then
    echo -e "${GREEN}✅ Enhanced Downloader started successfully!${NC}"
    echo -e "${GREEN}   PID: $DOWNLOADER_PID${NC}"
    echo -e "${GREEN}   Log: $BACKGROUND_LOG${NC}"
    echo ""
    echo -e "${BLUE}📊 To monitor progress:${NC}"
    echo "   tail -f $BACKGROUND_LOG"
    echo ""
    echo -e "${BLUE}🛑 To stop:${NC}"
    echo "   ./stop_enhanced_download.sh"
    echo ""
    echo -e "${BLUE}📈 To check status:${NC}"
    echo "   ./status_enhanced_download.sh"
    echo ""
    echo -e "${YELLOW}💡 The process will run independently and survive session disconnects${NC}"
    echo -e "${YELLOW}💡 Download will automatically resume if interrupted${NC}"
else
    echo -e "${RED}❌ Failed to start downloader${NC}"
    echo -e "${RED}Check the log file: $BACKGROUND_LOG${NC}"
    rm -f "$PID_FILE"
    exit 1
fi