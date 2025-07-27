# GPU VM Setup Guide for RL Training (Debian)

## After CUDA Installation Completes

### 1. Reboot to load drivers:
```bash
sudo reboot
```

### 2. SSH back in and verify GPU:
```bash
ssh info@34.22.91.71
nvidia-smi
# Should show Tesla T4 with 16GB memory
```

### 3. Install Python 3.11:
```bash
# Debian 12 comes with Python 3.11
python3 --version
sudo apt install -y python3.11-venv python3-pip
```

### 4. Copy your RL code from CPU VM:
```bash
# From GPU VM, copy the RL directory
scp -r info@fntx-ai-vm:/home/info/fntx-ai-v1/12_rl_trading ~/fntx-ai-v1/
```

### 5. Set up Python environment:
```bash
cd ~/fntx-ai-v1/12_rl_trading/spy_options
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### 6. Install PyTorch with GPU support:
```bash
# For CUDA 12.x (what we just installed)
pip install torch torchvision torchaudio
```

### 7. Install other dependencies:
```bash
pip install -r requirements.txt
```

### 8. Configure database connection:
Create `.env` file pointing to your CPU VM's internal IP:
```bash
cat > .env << EOF
# Database Configuration (pointing to CPU VM)
DB_HOST=10.140.0.2  # Replace with your CPU VM's internal IP
DB_PORT=5432
DB_NAME=fntx_trading
DB_USER=info
DB_PASSWORD=

# Environment
ENVIRONMENT=development
DEBUG=true
EOF
```

### 9. Test GPU setup:
```bash
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU Name: {torch.cuda.get_device_name(0)}')"
```

## Training Workflow

### Run training:
```bash
cd ~/fntx-ai-v1/12_rl_trading/spy_options
source venv/bin/activate
python train.py --timesteps 100000  # Start with small test
```

### Stop GPU VM when done:
```bash
# From your local machine
gcloud compute instances stop fntx-ai-gpu --zone=asia-northeast3-a
```

## Cost: ~$0.47/hour running, ~$0.05/hour stopped