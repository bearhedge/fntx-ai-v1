# Gemini Execution Checklist for ALM Automation

## What's Already Created
1. **Main automation script**: `/home/info/fntx-ai-v1/01_backend/alm/alm_automation.py`
   - Complete automation system with all features
   - Fixed import to use `generate_daily_narrative` function directly
   - Just needs the database tables and append-mode script

2. **Implementation guides**:
   - `ALM_AUTOMATION_GUIDE.md` - Master guide
   - `modules/Module_1_Database_Schema.md` - Database setup (ready to execute)

## Immediate Execution Steps for Gemini

### Step 1: Execute Module 1 (Database Setup)
```bash
# Create SQL files from Module 1 guide and execute them
cd /home/info/fntx-ai-v1/01_backend/alm/
mkdir -p sql
# Copy SQL from Module_1_Database_Schema.md into individual files
# Then execute:
psql -U postgres -d options_data -f sql/01_create_import_history.sql
psql -U postgres -d options_data -f sql/02_create_processing_status.sql
psql -U postgres -d options_data -f sql/03_modify_existing_tables.sql
psql -U postgres -d options_data -f sql/04_create_file_tracking.sql
```

### Step 2: Create Append-Mode Script
Create `/home/info/fntx-ai-v1/01_backend/alm/build_alm_data_append.py` by:
1. Copy existing `build_alm_data.py`
2. Modify line 53: Remove TRUNCATE statement
3. Add ON CONFLICT DO UPDATE to all INSERT statements
4. Add `--append` argument handling

### Step 3: Test Historical Backfill
```bash
# Setup tracking tables
python3 alm_automation.py --setup

# Run backfill for July 19-21
python3 alm_automation.py --backfill --start-date 2025-07-19 --end-date 2025-07-21
```

### Step 4: Setup Daily Automation
```bash
# Create systemd service
sudo cp /home/info/fntx-ai-v1/01_backend/services/alm-daily-update.service /etc/systemd/system/alm-automation.service
# Update ExecStart to: /usr/bin/python3 /home/info/fntx-ai-v1/01_backend/alm/alm_automation.py
sudo systemctl daemon-reload
sudo systemctl enable alm-automation.timer
sudo systemctl start alm-automation.timer
```

## Key Points for Gemini
1. The main automation script is **already complete** - just needs database tables
2. The script correctly imports `generate_daily_narrative` function (not a class)
3. Start with Module 1 (database) - it has all SQL ready to copy/paste
4. The append-mode script is a simple modification of existing `build_alm_data.py`
5. Test with July 19-21 dates before enabling daily automation

## What NOT to Do
- Don't modify the existing `build_alm_data.py` - create a new append version
- Don't delete existing data - the new system adds to it
- Don't skip the database setup - it's required for tracking

This gives Gemini a clear, executable path without needing all 7 modules documented!