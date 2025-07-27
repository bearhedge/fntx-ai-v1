
-- Migration: Grant SELECT permission on alm_reporting tables
--
-- This migration grants the necessary SELECT permission to the 'info' user
-- so that the narrative script and the user can read from the tables.

GRANT SELECT ON ALL TABLES IN SCHEMA alm_reporting TO info;
