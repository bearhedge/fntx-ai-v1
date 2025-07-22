#!/bin/bash
# Start 0DTE download in tmux session
# This allows the download to continue even if your laptop sleeps

echo "=================================================="
echo "0DTE SPY OPTIONS DOWNLOAD - BACKGROUND LAUNCHER"
echo "=================================================="
echo ""

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "Error: tmux is not installed!"
    echo "Install with: sudo apt-get install tmux (Ubuntu/Debian)"
    echo "          or: brew install tmux (macOS)"
    exit 1
fi

# Check if session already exists
if tmux has-session -t odte_download 2>/dev/null; then
    echo "⚠️  A download session is already running!"
    echo ""
    echo "Options:"
    echo "  View it: tmux attach -t odte_download"
    echo "  Kill it: tmux kill-session -t odte_download"
    echo ""
    read -p "Kill existing session and start new? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        tmux kill-session -t odte_download
        echo "Killed existing session."
    else
        echo "Exiting..."
        exit 1
    fi
fi

# Create new session
echo "Creating new tmux session 'odte_download'..."
tmux new-session -d -s odte_download

# Send commands to the session
tmux send-keys -t odte_download "cd $(pwd)" C-m
tmux send-keys -t odte_download "echo '================================================'" C-m
tmux send-keys -t odte_download "echo '0DTE DOWNLOAD STARTED'" C-m
tmux send-keys -t odte_download "echo 'Date range: January 2023 - June 2025'" C-m
tmux send-keys -t odte_download "echo 'Strategy: Core (±10) then Extended (±20)'" C-m
tmux send-keys -t odte_download "echo '================================================'" C-m
tmux send-keys -t odte_download "echo ''" C-m

# Start the master orchestrator
tmux send-keys -t odte_download "python3 master_0dte_orchestrator.py --run" C-m

echo ""
echo "✅ Download started successfully!"
echo ""
echo "📍 Session Commands:"
echo "   View progress:  tmux attach -t odte_download"
echo "   Detach:        Press Ctrl+B then D"
echo "   Kill session:  tmux kill-session -t odte_download"
echo ""
echo "📊 Monitor progress in another terminal:"
echo "   python3 monitor_0dte_progress.py --dashboard"
echo ""
echo "The download will continue running even if:"
echo "- You close this terminal"
echo "- Your laptop goes to sleep"
echo "- You disconnect from SSH"
echo ""