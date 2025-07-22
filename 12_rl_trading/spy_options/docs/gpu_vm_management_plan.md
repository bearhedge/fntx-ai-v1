# GPU VM Management & Post-Training Plan

## Current Training Status
- Training 2M timesteps on Tesla T4 GPU
- Progress: ~8.2% (163k timesteps)
- ETA: ~3.4 hours
- Running at ~152 FPS

## GPU VM Management Options

### 1. **STOP Instance (Recommended)**
- **What it does**: Pauses the VM, preserves disk/data
- **Cost**: Only pay for disk storage (~$0.04/GB/month)
- **Restart**: Can restart anytime, keeps same IP
- **Use when**: Training complete, not needed for days/weeks

### 2. **DELETE Instance**
- **What it does**: Removes VM completely
- **Cost**: No ongoing charges
- **Data**: All data lost unless saved elsewhere
- **Use when**: Completely done with GPU work

### 3. **Keep Running**
- **Cost**: ~$0.35/hour for g4dn.xlarge
- **Use when**: Need GPU frequently (daily inference)

## Post-Training Action Plan

### Phase 1: Model Preservation (Immediately after training)
```bash
# 1. Copy trained model to CPU VM
scp -r fntx-ai-gpu:~/fntx-ai-v1/12_rl_trading/spy_options/ppo_gpu_test_* ./models/

# 2. Copy training logs
scp -r fntx-ai-gpu:~/fntx-ai-v1/12_rl_trading/spy_options/logs ./gpu_training_logs/

# 3. Create backup
tar -czf spy_options_model_2m_$(date +%Y%m%d).tar.gz models/ gpu_training_logs/
```

### Phase 2: Model Deployment (CPU VM)
1. **Create Inference API** (FastAPI on CPU VM)
   - Load trained model
   - Endpoint: POST /predict
   - Input: current market state
   - Output: action (hold/sell call/sell put)

2. **Integration Points**
   - Connect to orchestrator
   - Real-time data feed
   - Position tracking
   - Risk management

### Phase 3: GPU VM Decision

#### Option A: STOP Instance (Recommended)
```bash
# Stop instance via AWS CLI
aws ec2 stop-instances --instance-ids i-xxxxxxxxx

# To restart later:
aws ec2 start-instances --instance-ids i-xxxxxxxxx
```

#### Option B: Scheduled Start/Stop
```python
# Lambda function for cost optimization
def manage_gpu_instance(event, context):
    if event['action'] == 'start':
        # Start for nightly retraining
        ec2.start_instances(InstanceIds=[INSTANCE_ID])
    elif event['action'] == 'stop':
        # Stop after training complete
        ec2.stop_instances(InstanceIds=[INSTANCE_ID])
```

## Recommended Architecture

### For Production:
1. **Inference**: CPU VM (always on)
   - Model serving API
   - Real-time predictions
   - Low latency requirements

2. **Training**: GPU VM (on-demand)
   - Weekly/monthly retraining
   - Stop when not in use
   - Start via automation

### Cost Optimization:
- **Daily inference**: CPU only (~$20/month)
- **Weekly retrain**: GPU 4hrs/week (~$6/month)
- **Total**: ~$26/month vs $252/month always-on GPU

## Next Steps After Training

1. **Transfer model & logs to CPU VM**
2. **Create model serving API**
3. **Test inference performance**
4. **STOP GPU instance**
5. **Set up automated retraining schedule**

## GPU VM Restart Checklist
When you need GPU again:
```bash
# 1. Start instance
aws ec2 start-instances --instance-ids i-xxxxxxxxx

# 2. Get new public IP
aws ec2 describe-instances --instance-ids i-xxxxxxxxx

# 3. Update SSH config with new IP
echo "Host fntx-ai-gpu
    HostName NEW_IP_HERE
    User info
    IdentityFile ~/.ssh/fntx-ai-key.pem" >> ~/.ssh/config

# 4. SSH and activate environment
ssh fntx-ai-gpu
cd ~/fntx-ai-v1/12_rl_trading/spy_options
source venv_gpu/bin/activate
```

## Data Persistence Strategy
Important files to preserve:
- `/home/info/fntx-ai-v1/` - All code
- `*.pkl.gz` - Training data
- `ppo_gpu_test_*` - Trained models
- `logs/` - Training history

These persist when instance is STOPPED, but not TERMINATED.