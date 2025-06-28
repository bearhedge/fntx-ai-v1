#!/bin/bash
# Status checker for Enhanced SPY Downloader

set -e

SCRIPT_DIR="/home/info/fntx-ai-v1"
PID_FILE="$SCRIPT_DIR/runtime/pids/enhanced_downloader.pid"
CHECKPOINT_FILE="$SCRIPT_DIR/download_checkpoint.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📊 Enhanced SPY Downloader Status${NC}"
echo -e "${BLUE}================================${NC}"

# Check if process is running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${GREEN}✅ Downloader is running (PID: $PID)${NC}"
        
        # Show process info
        echo -e "${BLUE}📈 Process Information:${NC}"
        ps -p "$PID" -o pid,ppid,pcpu,pmem,etime,cmd --no-headers || echo "   Process details unavailable"
        
        # Check memory usage
        if command -v pmap >/dev/null 2>&1; then
            MEMORY=$(pmap -x "$PID" 2>/dev/null | tail -1 | awk '{print $3}' || echo "Unknown")
            echo -e "${BLUE}💾 Memory usage: ${MEMORY}K${NC}"
        fi
        
    else
        echo -e "${RED}❌ Downloader is not running (stale PID file)${NC}"
        rm -f "$PID_FILE"
    fi
else
    echo -e "${YELLOW}⚠️ Downloader is not running${NC}"
fi

# Check checkpoint file
if [ -f "$CHECKPOINT_FILE" ]; then
    echo ""
    echo -e "${BLUE}📊 Last Checkpoint Information:${NC}"
    
    # Extract key information from checkpoint
    if command -v jq >/dev/null 2>&1; then
        TIMESTAMP=$(jq -r '.timestamp' "$CHECKPOINT_FILE" 2>/dev/null || echo "Unknown")
        CURRENT_EXP=$(jq -r '.progress.current_expiration' "$CHECKPOINT_FILE" 2>/dev/null || echo "Unknown")
        EXP_INDEX=$(jq -r '.progress.expiration_index' "$CHECKPOINT_FILE" 2>/dev/null || echo "Unknown")
        TOTAL_EXP=$(jq -r '.progress.total_expirations' "$CHECKPOINT_FILE" 2>/dev/null || echo "Unknown")
        PROCESSED=$(jq -r '.stats.contracts_processed' "$CHECKPOINT_FILE" 2>/dev/null || echo "Unknown")
        SKIPPED=$(jq -r '.stats.contracts_skipped' "$CHECKPOINT_FILE" 2>/dev/null || echo "Unknown")
        OHLC_RECORDS=$(jq -r '.stats.ohlc_records' "$CHECKPOINT_FILE" 2>/dev/null || echo "Unknown")
        
        echo -e "   ${GREEN}Last Update:${NC} $TIMESTAMP"
        echo -e "   ${GREEN}Current Expiration:${NC} $CURRENT_EXP"
        echo -e "   ${GREEN}Progress:${NC} $EXP_INDEX / $TOTAL_EXP expirations"
        echo -e "   ${GREEN}Contracts Processed:${NC} $PROCESSED"
        echo -e "   ${GREEN}Contracts Skipped:${NC} $SKIPPED"
        echo -e "   ${GREEN}OHLC Records:${NC} $OHLC_RECORDS"
    else
        echo -e "   ${YELLOW}Install 'jq' for detailed checkpoint analysis${NC}"
        echo -e "   ${BLUE}Raw checkpoint data:${NC}"
        head -5 "$CHECKPOINT_FILE"
    fi
else
    echo -e "${YELLOW}⚠️ No checkpoint file found${NC}"
fi

# Check recent log activity
LOG_DIR="$SCRIPT_DIR/logs"
if [ -d "$LOG_DIR" ]; then
    LATEST_LOG=$(find "$LOG_DIR" -name "enhanced_downloader_*.log" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    
    if [ -n "$LATEST_LOG" ]; then
        echo ""
        echo -e "${BLUE}📝 Recent Log Activity:${NC}"
        echo -e "   ${GREEN}Latest log:${NC} $LATEST_LOG"
        
        # Show last few lines of log
        echo -e "   ${GREEN}Last 5 lines:${NC}"
        tail -5 "$LATEST_LOG" 2>/dev/null | sed 's/^/     /' || echo "     Unable to read log"
        
        # Show log size
        LOG_SIZE=$(du -h "$LATEST_LOG" 2>/dev/null | cut -f1 || echo "Unknown")
        echo -e "   ${GREEN}Log size:${NC} $LOG_SIZE"
    fi
fi

# Database quick check
echo ""
echo -e "${BLUE}💾 Database Quick Check:${NC}"
VENV_DIR="$SCRIPT_DIR/venv"
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
fi

python3 -c "
import sys
sys.path.append('$SCRIPT_DIR')
try:
    from backend.config.theta_config import DB_CONFIG
    import psycopg2
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM theta.options_ohlc')
    count = cursor.fetchone()[0]
    print(f'   Total OHLC records: {count:,}')
    cursor.close()
    conn.close()
except Exception as e:
    print(f'   Database error: {e}')
" 2>/dev/null

echo ""
echo -e "${BLUE}🔧 Control Commands:${NC}"
echo -e "   ${GREEN}Start:${NC} ./start_enhanced_download.sh"
echo -e "   ${GREEN}Stop:${NC} ./stop_enhanced_download.sh"
echo -e "   ${GREEN}Monitor:${NC} tail -f logs/enhanced_downloader_background.log"