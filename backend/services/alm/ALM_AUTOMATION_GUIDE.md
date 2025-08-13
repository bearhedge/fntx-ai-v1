# ALM Automation Implementation Guide

## Overview
This guide provides a modular approach to implementing the ALM (Asset Liability Management) automation system. The system automates the daily workflow of downloading IBKR FlexQuery reports, processing the data, and generating daily narratives.

## System Architecture
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ IBKR FlexQuery │────▶│ File Management  │────▶│ Database Import │
│     API         │     │    System        │     │   (Append Mode) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                           │
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Systemd Timer   │────▶│ Date Processing  │────▶│   Calculation   │
│  (Daily 5PM)    │     │    Module        │     │     Engine      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Implementation Modules

### Module Execution Order
1. **Module 1: Database Schema Updates** - Create tracking tables and indexes
2. **Module 2: Build ALM Data Append Mode** - Modify data import for incremental updates
3. **Module 3: FlexQuery Download Module** - Implement API download functionality
4. **Module 4: File Management System** - Handle file rotation and archiving
5. **Module 5: Date Range Processing** - Business day logic and backfill
6. **Module 6: Integration Layer** - Connect all components
7. **Module 7: Systemd Service Setup** - Schedule automated execution

## Key Requirements
- **Database**: PostgreSQL with `options_data` database
- **Python**: 3.8+ with required packages
- **IBKR**: FlexQuery tokens and query IDs configured
- **Storage**: `/home/info/fntx-ai-v1/04_data/` directory
- **Permissions**: Read/write access to data directories

## Implementation Timeline
- **Phase 1** (Modules 1-2): Database preparation - 1 hour
- **Phase 2** (Modules 3-4): Download and file management - 2 hours
- **Phase 3** (Module 5): Date processing logic - 1 hour
- **Phase 4** (Module 6): Integration - 2 hours
- **Phase 5** (Module 7): Deployment - 1 hour

## Safety Checklist
Before starting implementation:
- [ ] Backup existing ALM database tables
- [ ] Verify IBKR FlexQuery credentials
- [ ] Ensure sufficient disk space (>5GB)
- [ ] Check Python environment and dependencies
- [ ] Review current data in `/04_data/` directory

## Module Independence
Each module is designed to be:
- **Self-contained**: Can be implemented independently
- **Testable**: Includes validation procedures
- **Reversible**: Has rollback instructions
- **Documented**: Clear implementation steps

## Error Handling Strategy
1. **Logging**: All modules log to `/home/info/fntx-ai-v1/08_logs/alm_automation.log`
2. **Database Tracking**: Failed imports recorded in `import_history` table
3. **File Backup**: Archive old files before deletion
4. **Transaction Safety**: Database operations use transactions
5. **Retry Logic**: Automatic retry for transient failures

## Testing Approach
1. **Unit Tests**: Each module tested independently
2. **Integration Tests**: End-to-end workflow validation
3. **Historical Backfill**: Test with July 19-21 data
4. **Daily Run**: Validate automated daily execution

## Success Criteria
The system is considered successfully implemented when:
1. Historical data (July 19-21) is correctly imported
2. Daily automation runs without manual intervention
3. File rotation maintains exactly 3 recent files per type
4. Calculation engine generates accurate narratives
5. All errors are logged and recoverable

## Next Steps
Proceed to **Module 1: Database Schema Updates** to begin implementation.

---

## Quick Reference

### Environment Variables
```bash
export IBKR_FLEX_TOKEN="355054594472094189405478"
export IBKR_FLEX_QUERY_ID="1244257"  # NAV Query
```

### Key Paths
- Data Directory: `/home/info/fntx-ai-v1/04_data/`
- Archive Directory: `/home/info/fntx-ai-v1/04_data/archive/`
- Log Directory: `/home/info/fntx-ai-v1/08_logs/`
- Script Location: `/home/info/fntx-ai-v1/01_backend/alm/`

### Database Connection
```
Host: localhost
Database: options_data
User: postgres
Password: theta_data_2024
Schema: alm_reporting
```

### Manual Commands
```bash
# Run daily update
python3 /home/info/fntx-ai-v1/01_backend/alm/alm_automation.py

# Run historical backfill
python3 /home/info/fntx-ai-v1/01_backend/alm/alm_automation.py --backfill --start-date 2025-07-19 --end-date 2025-07-21

# Check import history
psql -U postgres -d options_data -c "SELECT * FROM alm_reporting.import_history ORDER BY import_date DESC;"
```