#!/bin/bash
cd /home/info/fntx-ai-v1
source venv/bin/activate
export PYTHONPATH=/home/info/fntx-ai-v1
cd backend
source .env
export GEMINI_API_KEY=$GEMINI_API_KEY
cd ..
python3 -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload