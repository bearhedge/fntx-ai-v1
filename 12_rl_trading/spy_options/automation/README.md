# Automation Directory

This directory contains scheduled tasks that run automatically without manual intervention.

## Files

### scheduled_retraining.py
- **Purpose**: Retrains the AI model with accumulated trading experiences
- **Schedule**: Runs every Sunday at 2 AM (via cron)
- **Process**:
  1. Checks if enough new data exists (minimum 20 trades)
  2. Exports user feedback and decisions from past week
  3. Rents a GPU instance for 3 hours
  4. Fine-tunes the model with new experiences
  5. Validates the new model
  6. Deploys if validation passes
  7. Sends email notification with results
- **Cost**: ~$20/month (GPU rental)

## Setup

### 1. Configure Cron Job
```bash
# Edit crontab
crontab -e

# Add this line (runs every Sunday at 2 AM)
0 2 * * 0 /usr/bin/python3 /home/info/fntx-ai-v1/12_rl_trading/spy_options/automation/scheduled_retraining.py
```

### 2. Set Environment Variables
Create `.env` file:
```bash
DB_HOST=localhost
DB_USER=info
DB_NAME=fntx_ai_memory
EMAIL_TO=your-email@domain.com
```

### 3. Test Run
```bash
# Test without waiting for Sunday
python scheduled_retraining.py
```

## Logs

All retraining logs are saved to:
```
/home/info/fntx-ai-v1/12_rl_trading/spy_options/logs/evolution/
```

Format: `evolution_YYYYMMDD_HHMMSS.log`

## What Happens Each Week

1. **Data Collection**: All your trading decisions and feedback from the week
2. **GPU Training**: ~3 hours of fine-tuning on Tesla T4
3. **Model Update**: New model incorporates your preferences
4. **Notification**: Email sent with results

## Manual Override

To force retraining outside of schedule:
```bash
cd /home/info/fntx-ai-v1/12_rl_trading/spy_options/automation
python scheduled_retraining.py
```

## Monitoring

Check if working:
```bash
# View cron logs
grep CRON /var/log/syslog

# Check recent runs
ls -la ../logs/evolution/
```