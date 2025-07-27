#!/bin/bash
# Script to create T4 GPU VM in Taiwan region

# Variables
VM_NAME="fntx-rl-gpu"
ZONE="asia-east1-a"  # Taiwan zone (adjust if needed: asia-east1-a, asia-east1-b, or asia-east1-c)
MACHINE_TYPE="n1-standard-8"  # 8 vCPUs, 30GB RAM
BOOT_DISK_SIZE="100GB"  # As discussed
PROJECT_ID=$(gcloud config get-value project)

echo "Creating GPU VM in Taiwan region..."
echo "VM Name: $VM_NAME"
echo "Zone: $ZONE"
echo "Machine Type: $MACHINE_TYPE with 1x T4 GPU"
echo "Disk: $BOOT_DISK_SIZE SSD"
echo "Project: $PROJECT_ID"

# Create the VM
gcloud compute instances create $VM_NAME \
    --zone=$ZONE \
    --machine-type=$MACHINE_TYPE \
    --accelerator="type=nvidia-tesla-t4,count=1" \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=$BOOT_DISK_SIZE \
    --boot-disk-type=pd-ssd \
    --maintenance-policy=TERMINATE \
    --restart-on-failure \
    --metadata-from-file startup-script=/home/info/fntx-ai-v1/12_rl_trading/gpu_startup_script.sh \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --tags=gpu-vm,ml-training

echo "VM creation initiated!"
echo ""
echo "Next steps after VM is ready (wait ~5 minutes for startup script):"
echo "1. SSH into the VM: gcloud compute ssh $VM_NAME --zone=$ZONE"
echo "2. Verify GPU: nvidia-smi"
echo "3. Clone your repository and continue setup"