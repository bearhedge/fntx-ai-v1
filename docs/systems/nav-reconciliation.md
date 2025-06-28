# Daily NAV Import Setup

This replaces the cron-based daily NAV import with a systemd timer for better system integration.

## Installation

1. Copy the service and timer files to systemd directory:
```bash
sudo cp fntx-daily-nav.service /etc/systemd/system/
sudo cp fntx-daily-nav.timer /etc/systemd/system/
```

2. Reload systemd daemon:
```bash
sudo systemctl daemon-reload
```

3. Enable and start the timer:
```bash
sudo systemctl enable fntx-daily-nav.timer
sudo systemctl start fntx-daily-nav.timer
```

## Management Commands

### Check timer status:
```bash
systemctl status fntx-daily-nav.timer
systemctl list-timers fntx-daily-nav.timer
```

### Check last run:
```bash
systemctl status fntx-daily-nav.service
journalctl -u fntx-daily-nav.service -n 50
```

### Run manually:
```bash
sudo systemctl start fntx-daily-nav.service
```

### Disable/Enable:
```bash
sudo systemctl disable fntx-daily-nav.timer
sudo systemctl enable fntx-daily-nav.timer
```

## Troubleshooting

### View logs:
```bash
journalctl -u fntx-daily-nav.service -f
journalctl -u fntx-daily-nav.timer -f
```

### Test the service:
```bash
sudo systemctl start fntx-daily-nav.service
```

## Migration from Cron

After confirming the systemd timer works correctly:

1. Remove the old cron entry:
```bash
crontab -e
# Remove the line for daily_nav_cron.sh
```

2. Archive the old cron script:
```bash
mv daily_nav_cron.sh ../archive/one_time_scripts/
```

## Benefits over Cron

- Better logging with journald
- Automatic restart on failure
- Persistent execution (runs if system was down)
- Better security with systemd sandboxing
- Easier monitoring and management