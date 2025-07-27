# Module 1: Database Schema Updates

## Objective
Create database tracking tables and prepare the schema for append-mode operations. This module ensures the database can track import history and handle incremental data updates without duplicating records.

## Prerequisites
- [ ] PostgreSQL database `options_data` is accessible
- [ ] User has CREATE TABLE permissions on `alm_reporting` schema
- [ ] Backup of existing ALM tables completed

## Implementation Steps

### Step 1: Connect to Database
```bash
psql -U postgres -d options_data -h localhost
# Password: theta_data_2024
```

### Step 2: Create Import History Table
This table tracks successful imports and helps identify which dates need processing.

```sql
-- File: /home/info/fntx-ai-v1/01_backend/alm/sql/01_create_import_history.sql

CREATE TABLE IF NOT EXISTS alm_reporting.import_history (
    import_id SERIAL PRIMARY KEY,
    import_date DATE NOT NULL UNIQUE,
    import_type VARCHAR(20) DEFAULT 'DAILY',
    status VARCHAR(20) NOT NULL,
    files_processed JSONB,
    records_imported INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_import_history_date ON alm_reporting.import_history(import_date DESC);
CREATE INDEX idx_import_history_status ON alm_reporting.import_history(status);

-- Add comments for documentation
COMMENT ON TABLE alm_reporting.import_history IS 'Tracks ALM data import history for automation';
COMMENT ON COLUMN alm_reporting.import_history.import_type IS 'DAILY, BACKFILL, or MANUAL';
COMMENT ON COLUMN alm_reporting.import_history.status IS 'PENDING, PROCESSING, SUCCESS, or FAILED';
COMMENT ON COLUMN alm_reporting.import_history.files_processed IS 'JSON array of processed file paths';
```

### Step 3: Create Processing Status Table
This table monitors the current state of the automation workflow.

```sql
-- File: /home/info/fntx-ai-v1/01_backend/alm/sql/02_create_processing_status.sql

CREATE TABLE IF NOT EXISTS alm_reporting.processing_status (
    status_id SERIAL PRIMARY KEY,
    process_name VARCHAR(50) NOT NULL,
    current_state VARCHAR(20) NOT NULL,
    last_run_date DATE,
    last_success_date DATE,
    next_scheduled_run TIMESTAMP,
    configuration JSONB,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create unique constraint on process name
CREATE UNIQUE INDEX idx_processing_status_name ON alm_reporting.processing_status(process_name);

-- Insert default automation process
INSERT INTO alm_reporting.processing_status (process_name, current_state, configuration)
VALUES ('ALM_DAILY_AUTOMATION', 'READY', 
    '{"max_files_to_keep": 3, "retry_attempts": 3, "timeout_seconds": 300}'::jsonb)
ON CONFLICT (process_name) DO NOTHING;
```

### Step 4: Add Duplicate Prevention to Existing Tables
Modify existing tables to support append mode with duplicate detection.

```sql
-- File: /home/info/fntx-ai-v1/01_backend/alm/sql/03_modify_existing_tables.sql

-- Add unique constraint to chronological_events to prevent duplicates
ALTER TABLE alm_reporting.chronological_events 
ADD CONSTRAINT uk_chronological_events_transaction 
UNIQUE (source_transaction_id);

-- Add ON CONFLICT handling capability
ALTER TABLE alm_reporting.daily_summary
ADD CONSTRAINT uk_daily_summary_date
UNIQUE (summary_date);

-- Add last_updated column for tracking
ALTER TABLE alm_reporting.daily_summary
ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE alm_reporting.chronological_events
ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create trigger to auto-update last_updated
CREATE OR REPLACE FUNCTION update_last_updated_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_daily_summary_last_updated 
BEFORE UPDATE ON alm_reporting.daily_summary 
FOR EACH ROW EXECUTE FUNCTION update_last_updated_column();

CREATE TRIGGER update_chronological_events_last_updated 
BEFORE UPDATE ON alm_reporting.chronological_events 
FOR EACH ROW EXECUTE FUNCTION update_last_updated_column();
```

### Step 5: Create File Tracking Table
Track processed files to avoid reprocessing.

```sql
-- File: /home/info/fntx-ai-v1/01_backend/alm/sql/04_create_file_tracking.sql

CREATE TABLE IF NOT EXISTS alm_reporting.processed_files (
    file_id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL UNIQUE,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT,
    file_hash VARCHAR(64),
    process_date DATE NOT NULL,
    records_count INTEGER,
    processing_status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_processed_files_type ON alm_reporting.processed_files(file_type);
CREATE INDEX idx_processed_files_date ON alm_reporting.processed_files(process_date DESC);
```

## Testing Steps

### Test 1: Verify Tables Created
```sql
-- Check all tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'alm_reporting' 
AND table_name IN ('import_history', 'processing_status', 'processed_files')
ORDER BY table_name;

-- Expected output: 3 rows
```

### Test 2: Verify Constraints
```sql
-- Check unique constraints
SELECT conname, conrelid::regclass 
FROM pg_constraint 
WHERE connamespace = 'alm_reporting'::regnamespace 
AND contype = 'u'
ORDER BY conname;

-- Should show constraints for duplicate prevention
```

### Test 3: Test Import History Insert
```sql
-- Test insert
INSERT INTO alm_reporting.import_history 
(import_date, status, files_processed, records_imported)
VALUES 
('2025-07-19', 'SUCCESS', '["NAV_MTD.xml", "Trades_MTD.xml"]'::jsonb, 150);

-- Verify insert
SELECT * FROM alm_reporting.import_history WHERE import_date = '2025-07-19';

-- Test duplicate prevention
INSERT INTO alm_reporting.import_history 
(import_date, status)
VALUES ('2025-07-19', 'SUCCESS');
-- Should fail with unique constraint violation
```

## Validation Checklist
- [ ] All 4 SQL scripts execute without errors
- [ ] Tables created in `alm_reporting` schema
- [ ] Unique constraints prevent duplicate entries
- [ ] Triggers update last_updated columns
- [ ] Test inserts work as expected
- [ ] Duplicate inserts are properly rejected

## Rollback Instructions
If issues occur, run this rollback script:

```sql
-- File: /home/info/fntx-ai-v1/01_backend/alm/sql/99_rollback_module_1.sql

-- Drop new tables (preserves existing data)
DROP TABLE IF EXISTS alm_reporting.import_history CASCADE;
DROP TABLE IF EXISTS alm_reporting.processing_status CASCADE;
DROP TABLE IF EXISTS alm_reporting.processed_files CASCADE;

-- Remove constraints from existing tables
ALTER TABLE alm_reporting.chronological_events 
DROP CONSTRAINT IF EXISTS uk_chronological_events_transaction;

ALTER TABLE alm_reporting.daily_summary
DROP CONSTRAINT IF EXISTS uk_daily_summary_date;

-- Remove added columns
ALTER TABLE alm_reporting.daily_summary
DROP COLUMN IF EXISTS last_updated;

ALTER TABLE alm_reporting.chronological_events
DROP COLUMN IF EXISTS last_updated;

-- Drop triggers and function
DROP TRIGGER IF EXISTS update_daily_summary_last_updated ON alm_reporting.daily_summary;
DROP TRIGGER IF EXISTS update_chronological_events_last_updated ON alm_reporting.chronological_events;
DROP FUNCTION IF EXISTS update_last_updated_column();
```

## Common Issues and Solutions

### Issue 1: Permission Denied
**Error**: `ERROR: permission denied for schema alm_reporting`
**Solution**: 
```sql
GRANT ALL ON SCHEMA alm_reporting TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA alm_reporting TO postgres;
```

### Issue 2: Schema Does Not Exist
**Error**: `ERROR: schema "alm_reporting" does not exist`
**Solution**:
```sql
CREATE SCHEMA IF NOT EXISTS alm_reporting;
```

### Issue 3: Duplicate Key Violation
**Error**: `ERROR: duplicate key value violates unique constraint`
**Solution**: This is expected behavior - use ON CONFLICT clause in INSERT statements

## Next Steps
After successful implementation:
1. Run validation queries to confirm setup
2. Document any customizations made
3. Proceed to **Module 2: Build ALM Data Append Mode**

## Module Completion Checklist
- [ ] All tables created successfully
- [ ] Constraints and indexes in place
- [ ] Test data inserted and validated
- [ ] Rollback script tested (optional)
- [ ] No errors in PostgreSQL logs