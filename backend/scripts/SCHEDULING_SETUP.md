# FNTX Trading System - Scheduling Setup

This system requires daily automated tasks to run at specific times. Choose one of the following methods:

## Option 1: Cron (Recommended for Linux/Mac)

Run the setup script:
```bash
chmod +x /home/info/fntx-ai-v1/scripts/setup_cron_jobs.sh
/home/info/fntx-ai-v1/scripts/setup_cron_jobs.sh
```

Verify cron jobs:
```bash
crontab -l
```

## Option 2: Systemd Timers (For systemd-based Linux)

```bash
# Copy service files
sudo cp /home/info/fntx-ai-v1/scripts/systemd/*.service /etc/systemd/system/
sudo cp /home/info/fntx-ai-v1/scripts/systemd/*.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start timers
sudo systemctl enable fntx-daily-import.timer
sudo systemctl enable fntx-exercise-detector.timer
sudo systemctl start fntx-daily-import.timer
sudo systemctl start fntx-exercise-detector.timer

# Check status
sudo systemctl status fntx-daily-import.timer
sudo systemctl status fntx-exercise-detector.timer
```

## Option 3: Python Scheduler (Platform Independent)

Run as a background process:
```bash
# Make executable
chmod +x /home/info/fntx-ai-v1/scripts/scheduler.py

# Run in background using nohup
nohup python3 /home/info/fntx-ai-v1/scripts/scheduler.py > /home/info/fntx-ai-v1/logs/scheduler.log 2>&1 &

# Or use screen/tmux
screen -dmS fntx-scheduler python3 /home/info/fntx-ai-v1/scripts/scheduler.py
```

To stop the scheduler:
```bash
# Find process
ps aux | grep scheduler.py
# Kill process
kill <PID>
```

## Option 4: Manual Execution

If automated scheduling is not available, run these commands daily at 7:00 AM HKT:

```bash
# Daily NAV import
python3 /home/info/fntx-ai-v1/01_backend/scripts/daily_flex_import.py

# Exercise detection
python3 /home/info/fntx-ai-v1/01_backend/scripts/exercise_detector.py
```

## Scheduled Tasks

| Task | Time (HKT) | Time (UTC) | Frequency | Purpose |
|------|------------|------------|-----------|---------|
| Daily NAV Import | 7:00 AM | 11:00 PM* | Daily | Fetch account balance from IBKR |
| Exercise Detection | 7:00 AM | 11:00 PM* | Daily | Detect and dispose of exercised options |
| Historical Backfill | 3:00 AM | 7:00 PM* | Weekly (Sunday) | Update historical data |

*Previous day due to timezone difference

## Monitoring

Check logs in `/home/info/fntx-ai-v1/logs/`:
- `daily_import.log` - NAV import results
- `exercise_detection.log` - Exercise detection and disposal
- `scheduler.log` - Scheduler status (if using Python scheduler)

## Important Notes

1. **Hong Kong Timezone**: All times are in HKT (UTC+8)
2. **Exercise Detection**: Runs at 7:00 AM HKT to catch exercises before market open
3. **Extended Hours Trading**: Disposal orders placed for pre-market execution
4. **Database Updates**: Both scripts update the PostgreSQL database automatically