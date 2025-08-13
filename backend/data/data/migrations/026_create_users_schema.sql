-- Create users schema for FNTX authentication system
-- Migration: 026_create_users_schema.sql
-- Description: Creates user authentication tables for the FNTX trading system

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    CONSTRAINT username_format CHECK (username ~ '^[a-zA-Z0-9_]+$'),
    CONSTRAINT email_format CHECK (email ~ '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
);

-- Create user sessions table for JWT token management
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    refresh_token_hash VARCHAR(255) UNIQUE,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE
);

-- Create user profiles table for additional user information
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(255),
    avatar_url TEXT,
    bio TEXT,
    trading_experience VARCHAR(50) CHECK (trading_experience IN ('beginner', 'intermediate', 'advanced', 'expert')),
    risk_tolerance VARCHAR(50) CHECK (risk_tolerance IN ('conservative', 'moderate', 'aggressive')),
    preferred_strategies TEXT[], -- Array of preferred trading strategies
    notification_preferences JSONB DEFAULT '{"email": true, "push": false, "sms": false}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create authentication attempts table for security monitoring
CREATE TABLE IF NOT EXISTS auth_attempts (
    id SERIAL PRIMARY KEY,
    username_or_email VARCHAR(255),
    ip_address INET NOT NULL,
    user_agent TEXT,
    attempt_type VARCHAR(20) CHECK (attempt_type IN ('login', 'register', 'reset_password')),
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create password reset tokens table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_auth_attempts_timestamp ON auth_attempts(created_at, ip_address);

-- Grant permissions (adjust based on your database users)
GRANT SELECT, INSERT, UPDATE ON users TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_sessions TO postgres;
GRANT SELECT, INSERT, UPDATE ON user_profiles TO postgres;
GRANT SELECT, INSERT ON auth_attempts TO postgres;
GRANT SELECT, INSERT, UPDATE ON password_reset_tokens TO postgres;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO postgres;