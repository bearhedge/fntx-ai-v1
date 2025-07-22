#!/bin/bash
# Post-training model transfer script

echo "==================================="
echo "Post-Training Model Transfer"
echo "==================================="

# Create directories
mkdir -p models/gpu_trained
mkdir -p logs/gpu_training

# Get latest model from GPU
echo "Finding latest model on GPU..."
LATEST_MODEL=$(ssh fntx-ai-gpu "cd ~/fntx-ai-v1/12_rl_trading/spy_options && ls -t ppo_gpu_test_* 2>/dev/null | head -1")

if [ -z "$LATEST_MODEL" ]; then
    echo "ERROR: No model found on GPU"
    exit 1
fi

echo "Found model: $LATEST_MODEL"

# Transfer model
echo "Transferring model..."
scp -r fntx-ai-gpu:~/fntx-ai-v1/12_rl_trading/spy_options/$LATEST_MODEL models/gpu_trained/

# Transfer logs
echo "Transferring training logs..."
scp -r fntx-ai-gpu:~/fntx-ai-v1/12_rl_trading/spy_options/logs/training/* logs/gpu_training/

# Create metadata file
echo "Creating metadata..."
cat > models/gpu_trained/training_metadata.json << EOF
{
    "model_name": "$LATEST_MODEL",
    "training_completed": "$(date)",
    "total_timesteps": 2000000,
    "dataset": "SPY 0DTE Options 2022-2025",
    "episodes": 633,
    "gpu": "Tesla T4",
    "framework": "stable-baselines3 PPO"
}
EOF

# Create backup
echo "Creating backup..."
BACKUP_NAME="spy_options_model_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf $BACKUP_NAME models/gpu_trained/ logs/gpu_training/

echo "Transfer complete!"
echo "Model saved to: models/gpu_trained/$LATEST_MODEL"
echo "Backup created: $BACKUP_NAME"
echo ""
echo "Next steps:"
echo "1. Stop GPU instance: aws ec2 stop-instances --instance-ids YOUR_INSTANCE_ID"
echo "2. Run: python serve_model.py"