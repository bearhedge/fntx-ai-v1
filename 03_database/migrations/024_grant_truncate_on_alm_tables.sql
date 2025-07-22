
-- Migration: Grant TRUNCATE permission on alm_reporting tables
--
-- This migration grants the necessary TRUNCATE permission to the 'info' user
-- so that the ETL script can clear the tables before loading new data.

GRANT TRUNCATE ON TABLE alm_reporting.chronological_events, alm_reporting.daily_summary TO info;
