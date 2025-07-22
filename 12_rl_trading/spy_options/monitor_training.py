"""
Monitor GPU training progress with 5% interval updates
"""
import os
import time
import re
from datetime import datetime
import subprocess

def parse_training_log(log_content):
    """Parse training log for progress information"""
    # Find all timestep entries
    timestep_pattern = r'total_timesteps\s*\|\s*(\d+)'
    reward_pattern = r'ep_rew_mean\s*\|\s*([-\d.]+)'
    fps_pattern = r'fps\s*\|\s*(\d+)'
    
    timesteps = re.findall(timestep_pattern, log_content)
    rewards = re.findall(reward_pattern, log_content)
    fps_values = re.findall(fps_pattern, log_content)
    
    if timesteps:
        current_timesteps = int(timesteps[-1])
        current_reward = float(rewards[-1]) if rewards else 0.0
        current_fps = int(fps_values[-1]) if fps_values else 0
        return current_timesteps, current_reward, current_fps
    
    return 0, 0.0, 0

def monitor_remote_training():
    """Monitor training progress on GPU VM"""
    target_timesteps = 2_000_000
    check_interval = 30  # seconds
    last_reported_progress = 0
    
    print("Starting training monitor...")
    print(f"Target: {target_timesteps:,} timesteps")
    print("Updates every 5% progress\n")
    
    while True:
        try:
            # Get latest log from GPU VM
            result = subprocess.run([
                'ssh', 'fntx-ai-gpu',
                'tail -n 1000 ~/fntx-ai-v1/12_rl_trading/spy_options/logs/training/train_2m_*.log 2>/dev/null | tail -n 500'
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout:
                current_timesteps, current_reward, current_fps = parse_training_log(result.stdout)
                
                if current_timesteps > 0:
                    progress = (current_timesteps / target_timesteps) * 100
                    
                    # Report at 5% intervals
                    if progress >= last_reported_progress + 5:
                        last_reported_progress = int(progress / 5) * 5
                        
                        # Calculate ETA
                        if current_fps > 0:
                            remaining_steps = target_timesteps - current_timesteps
                            eta_seconds = remaining_steps / current_fps
                            eta_hours = eta_seconds / 3600
                            
                            print(f"\n{'='*60}")
                            print(f"PROGRESS UPDATE: {last_reported_progress}%")
                            print(f"{'='*60}")
                            print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"Timesteps: {current_timesteps:,} / {target_timesteps:,}")
                            print(f"Average Reward: {current_reward:.2f}")
                            print(f"Training Speed: {current_fps} FPS")
                            print(f"ETA: {eta_hours:.1f} hours")
                            print(f"{'='*60}")
                    
                    # Check if complete
                    if current_timesteps >= target_timesteps:
                        print("\n🎉 TRAINING COMPLETE! 🎉")
                        print(f"Final timesteps: {current_timesteps:,}")
                        print(f"Final average reward: {current_reward:.2f}")
                        break
            
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
            break
        except Exception as e:
            print(f"Error: {str(e)}")
            time.sleep(check_interval)

def start_monitoring_script():
    """Create a script to run monitoring in background"""
    script_content = '''#!/bin/bash
# Monitor training progress
cd ~/fntx-ai-v1/12_rl_trading/spy_options
nohup python3 monitor_training.py > monitor.log 2>&1 &
echo "Monitor started with PID: $!"
'''
    
    with open('start_monitor.sh', 'w') as f:
        f.write(script_content)
    
    os.chmod('start_monitor.sh', 0o755)
    print("Monitor script created: start_monitor.sh")

if __name__ == "__main__":
    # Check if we should create the script or run monitoring
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--create-script':
        start_monitoring_script()
    else:
        monitor_remote_training()