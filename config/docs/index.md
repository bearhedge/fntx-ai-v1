# FNTX AI Documentation Library

Welcome to the organized documentation for the FNTX AI trading system. All documentation is now organized by subject matter for easy navigation.

## 📁 Documentation Structure

### 01_ALM_Trading/
**Asset Liability Management & Trading Documentation**
- `ALM_REPORTING_COMPLETE_GUIDE.md` - Complete guide to ALM system with real-time integration
- `EXERCISE_MANAGEMENT_SYSTEM.md` - Options exercise detection and management
- `exercise_workflow.md` - Detailed workflow for handling exercises
- `FLEXQUERY_CONFIGURATION_UPDATE.md` - IBKR FlexQuery setup and configuration
- `nav-reconciliation.md` - NAV reconciliation procedures
- `trade-logging.md` - Trade logging and tracking system

### 02_Infrastructure/
**System Infrastructure & Database Documentation**
- `DATABASE_SCHEMAS.md` - Complete database schema documentation
- `POSTGRESQL_DATABASE_GUIDE.md` - PostgreSQL setup and management
- `Domain_Setup.md` - Domain and networking configuration
- `database.md` - Database setup procedures
- `authentication.md` - Authentication system documentation

### 03_Development/
**Development Guides & Best Practices**
- `development-guide.md` - General development guidelines
- `comprehensive-integration-guide.md` - System integration guide
- `frontend-integration.md` - Frontend development and integration
- `orchestration-guide.md` - Service orchestration patterns

### 04_Setup_Configuration/
**Setup & Configuration Guides**
- `RL_SYSTEM_CONFIGURATION.md` - RL trading system configuration
- `google-oauth-*.md` - Google OAuth setup guides
- `ibkr-flex.md` - IBKR FlexQuery configuration
- `trading-environment.md` - Trading environment setup
- `vnc-desktop.md` - VNC desktop configuration
- `gemini.md` - Gemini VM setup

### 05_Business_Planning/
**Business Documents & Planning**
- `Business plan.md` - FNTX AI business plan
- `Paper 1.txt` & `Paper 2.txt` - Research papers
- `GCP_Cost_Breakdown.txt` - Cloud infrastructure costs

### 06_Operations/
**Operational Procedures & Monitoring**
- `EMERGENCY_COST_SHUTDOWN.md` - Emergency shutdown procedures
- `data-download.md` - Data download procedures
- `monitoring.md` - System monitoring guide

### 07_Integrations/
**External System Integrations**
- `SUPERCLAUD_INTEGRATION.md` - SuperClaude integration
- `theta-data.md` - Theta data integration
- `theta-data-upgrade.md` - Theta upgrade procedures

### 08_Archives/
**Archived Documentation**
- Reserved for deprecated documentation

### 09_Migration_History/
**Migration & Change History**
- `gemini-migration-summary.md` - Gemini migration log
- `CHANGELOG_MASTER_TRACKER.md` - Master changelog

## 🚀 Quick Start

For new users, start with:
1. **Infrastructure Setup**: See `02_Infrastructure/POSTGRESQL_DATABASE_GUIDE.md`
2. **ALM System**: Read `01_ALM_Trading/ALM_REPORTING_COMPLETE_GUIDE.md`
3. **Trading Setup**: Follow `04_Setup_Configuration/trading-environment.md`

## 📊 Current System Status

- **ALM System**: Fully automated with real-time integration
- **Database**: PostgreSQL with `alm_reporting` schema
- **Trading**: Live SPY options via IB Gateway (port 4002)
- **Automation**: systemd timers for daily updates

## 🔧 Key Components

### Backend Services
- `/backend/alm/` - ALM calculation and automation
- `/backend/services/` - Real-time data services
- `/backend/trading/` - Trading execution

### Data Sources
- **T+1**: IBKR FlexQuery reports (5 PM HKT daily)
- **T+0**: IB Gateway API (real-time during market hours)

## 📝 Documentation Standards

All documentation follows these standards:
- Clear section headers with numbering
- Code examples with syntax highlighting
- Step-by-step procedures
- Troubleshooting sections
- Update history tracking

Last Updated: July 28, 2025