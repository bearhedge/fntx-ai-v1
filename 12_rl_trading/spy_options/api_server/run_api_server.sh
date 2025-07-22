#!/bin/bash
# Startup script for SPY Options AI API Server with Memory

# Set environment variables
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_USER="info"
export DB_PASSWORD=""
export DB_NAME="fntx_trading"
export MODEL_PATH="../models/gpu_trained/ppo_gpu_test_20250706_074954.zip"
export API_PORT="8100"

# Create required directories
mkdir -p ../models
mkdir -p ../logs/api_server

# Activate virtual environment if exists
if [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# Check if database exists, create if not
echo "Checking database..."
if ! psql -U $DB_USER -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo "Creating database $DB_NAME..."
    createdb -U $DB_USER $DB_NAME
    
    # Run schema creation
    psql -U $DB_USER -d $DB_NAME -f ../memory_system/database_schema.sql
    echo "Database schema created"
else
    echo "Database $DB_NAME exists"
fi

# Start the API server
echo "Starting SPY Options AI API Server on port $API_PORT..."
echo "Model: $MODEL_PATH"
echo "Database: $DB_NAME"
echo "Memory System: Enabled"
echo "Adapter Network: Enabled"
echo ""
echo "API Endpoints:"
echo "  GET  http://localhost:$API_PORT/         - Status"
echo "  POST http://localhost:$API_PORT/predict  - Get prediction"
echo "  POST http://localhost:$API_PORT/feedback - Submit feedback"
echo ""

# Run with uvicorn (auto-reload in dev)
python -m uvicorn main:app --host 0.0.0.0 --port $API_PORT --reload --log-level info