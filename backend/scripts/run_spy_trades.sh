#!/bin/bash
# Script to execute SPY options trades with virtual environment

cd /home/info/fntx-ai-v1/backend
source ../rl-trading/spy_options/rl_venv/bin/activate
python execute_spy_trades.py "$@"