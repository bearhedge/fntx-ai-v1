#!/bin/bash
# Run FNTX without mouse tracking
cd /home/info/fntx-ai-v1/cli
source cli_venv/bin/activate

# Disable mouse tracking
echo -e "\033[?1000l"
echo -e "\033[?1002l"
echo -e "\033[?1003l"

# Run FNTX
python -m cli.main