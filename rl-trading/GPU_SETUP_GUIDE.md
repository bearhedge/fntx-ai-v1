# GPU VM Setup Guide for RL Training

## Creating the VM

Run this command to create your T4 GPU VM in Taiwan:
```bash
cd /home/info/fntx-ai-v1/12_rl_trading
./create_gpu_vm.sh
```

## After VM Creation (Wait ~5 minutes for startup script)

### 1. SSH into the new VM:
```bash
gcloud compute ssh fntx-rl-gpu --zone=asia-east1-a
```

### 2. Verify GPU is working:
```bash
nvidia-smi
# Should show Tesla T4 with 16GB memory
```

### 3. Clone your repository:
```bash
# Option A: If using GitHub
git clone [your-repo-url]

# Option B: Copy from CPU VM
gcloud compute scp --recurse \
    info@[CPU-VM-NAME]:/home/info/fntx-ai-v1/12_rl_trading \
    ~/fntx-ai-v1/ \
    --zone=[CPU-VM-ZONE]
```

### 4. Set up Python environment:
```bash
cd ~/fntx-ai-v1/12_rl_trading/spy_options
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### 5. Install PyTorch with GPU support:
```bash
# For CUDA 11.8 (what we installed)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 6. Install other dependencies:
```bash
pip install -r requirements.txt
```

### 7. Configure database connection to CPU VM:

First, get the internal IP of your CPU VM:
```bash
gcloud compute instances describe [CPU-VM-NAME] --zone=[CPU-VM-ZONE] \
    --format='get(networkInterfaces[0].networkIP)'
```

Then create `.env` file:
```bash
cat > .env << EOF
# Database Configuration (pointing to CPU VM)
DB_HOST=[INTERNAL_IP_OF_CPU_VM]
DB_PORT=5432
DB_NAME=fntx_trading
DB_USER=info
DB_PASSWORD=

# Environment
ENVIRONMENT=development
DEBUG=true
EOF
```

### 8. Test the setup:
```bash
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU Name: {torch.cuda.get_device_name(0)}')"
```

## Training Workflow

### Initial Training:
```bash
# On GPU VM
cd ~/fntx-ai-v1/12_rl_trading/spy_options
source venv/bin/activate
python train.py --timesteps 100000  # Start small for testing

# After training completes
gsutil cp models/final/ppo_baseline_*.pkl gs://[your-bucket]/models/
```

### Transfer Model to CPU VM:
```bash
# On CPU VM
gsutil cp gs://[your-bucket]/models/ppo_baseline_*.pkl \
    /home/info/fntx-ai-v1/12_rl_trading/spy_options/models/
```

### Shutdown GPU VM to save money:
```bash
# From your local machine
gcloud compute instances stop fntx-rl-gpu --zone=asia-east1-a
```

## Database Firewall Setup

On your CPU VM, allow connections from GPU VM:
```bash
# Get GPU VM's internal IP
gcloud compute instances describe fntx-rl-gpu --zone=asia-east1-a \
    --format='get(networkInterfaces[0].networkIP)'

# Add PostgreSQL rule (if not already open)
# Edit /etc/postgresql/*/main/postgresql.conf
# Set: listen_addresses = '*'

# Edit /etc/postgresql/*/main/pg_hba.conf
# Add: host all all [GPU-INTERNAL-IP]/32 trust

# Restart PostgreSQL
sudo systemctl restart postgresql
```

## Cost Management

- **Running**: ~$0.35/hour (T4) + ~$0.12/hour (VM) = ~$0.47/hour
- **Stopped**: ~$0.05/hour (just disk storage)
- **Best Practice**: Only run during training, stop when idle

## Next Steps

1. Test with small training run (100k timesteps)
2. Monitor GPU usage with `nvidia-smi`
3. Scale up to full training (500k-1M timesteps)
4. Implement model serving API on CPU VM