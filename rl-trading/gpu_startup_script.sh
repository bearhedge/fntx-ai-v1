#!/bin/bash
# Startup script for NVIDIA T4 GPU setup on Ubuntu 22.04
# Exit immediately if a command exits with a non-zero status
set -e

# Log all output to a file for debugging
exec > >(tee /var/log/startup-script.log|logger -t startup-script -s) 2>&1

echo "Starting GPU VM setup for RL training..."

# 1. Update package lists
echo "Updating apt package lists..."
sudo apt update -y

# 2. Install necessary packages
echo "Installing prerequisites..."
sudo apt install -y build-essential software-properties-common ubuntu-drivers-common wget

# 3. Install NVIDIA drivers using Ubuntu's driver installer (simpler approach)
echo "Installing NVIDIA drivers..."
sudo ubuntu-drivers autoinstall

# 4. Install CUDA toolkit 11.8 (compatible with PyTorch 2.0+)
echo "Installing CUDA 11.8..."
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo apt update -y
sudo apt install -y cuda-11-8

# 5. Set up environment variables
echo "Setting up CUDA environment variables..."
echo 'export PATH=/usr/local/cuda-11.8/bin${PATH:+:${PATH}}' >> /home/$USER/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-11.8/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}' >> /home/$USER/.bashrc

# 6. Install Python 3.11 and pip
echo "Installing Python 3.11..."
sudo apt install -y python3.11 python3.11-venv python3-pip

# 7. Install Docker (useful for containerized training)
echo "Installing Docker..."
sudo apt install -y docker.io
sudo usermod -aG docker $USER

echo "Startup script completed! Rebooting to load drivers..."
sudo reboot