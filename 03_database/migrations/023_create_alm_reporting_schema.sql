-- Migration: Create alm_reporting Schema and Tables (v2)
--
-- This migration creates the dedicated schema and tables for the
-- Automated ALM Reporting System, ensuring the 'info' user is the owner.

-- Step 1: Drop the schema if it exists to ensure a clean slate
DROP SCHEMA IF EXISTS alm_reporting CASCADE;

-- Step 2: Create the schema and set the application user as the owner
CREATE SCHEMA alm_reporting AUTHORIZATION info;

-- The 'info' user now owns the schema and all objects within it,
-- so no further GRANT statements are needed.

-- Table to store every atomic financial event in chronological order
CREATE TABLE alm_reporting.chronological_events (
    event_id BIGSERIAL PRIMARY KEY,
    event_timestamp TIMESTAMPTZ NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    cash_impact_hkd NUMERIC(18, 4) NOT NULL,
    realized_pnl_hkd NUMERIC(18, 4) DEFAULT 0.00,
    nav_after_event_hkd NUMERIC(18, 4) NOT NULL,
    source_transaction_id TEXT UNIQUE
);

CREATE INDEX idx_event_timestamp ON alm_reporting.chronological_events (event_timestamp);

-- Table for the final, reconciled daily summary
CREATE TABLE alm_reporting.daily_summary (
    summary_date DATE PRIMARY KEY,
    opening_nav_hkd NUMERIC(18, 4) NOT NULL,
    closing_nav_hkd NUMERIC(18, 4) NOT NULL,
    total_pnl_hkd NUMERIC(18, 4) NOT NULL,
    net_cash_flow_hkd NUMERIC(18, 4) NOT NULL
);