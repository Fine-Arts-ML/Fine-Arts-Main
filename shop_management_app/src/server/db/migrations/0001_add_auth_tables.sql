-- Migration: 0001_add_auth_tables
-- Description: Add authentication tables for user accounts and sessions

-- User Accounts table: Maps Nextcloud users to app roles
CREATE TABLE IF NOT EXISTS bre_user_accounts (
    id SERIAL PRIMARY KEY,
    nextcloud_uid VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    allowed_gallery_ids JSONB DEFAULT '[]',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Sessions table: Server-side session storage
CREATE TABLE IF NOT EXISTS bre_sessions (
    id VARCHAR(128) PRIMARY KEY,
    user_id INTEGER REFERENCES bre_user_accounts(id),
    session_data JSONB NOT NULL DEFAULT '{}',
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_bre_user_accounts_nextcloud_uid ON bre_user_accounts(nextcloud_uid);
CREATE INDEX IF NOT EXISTS idx_bre_user_accounts_role ON bre_user_accounts(role);
CREATE INDEX IF NOT EXISTS idx_bre_sessions_expires_at ON bre_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_bre_sessions_user_id ON bre_sessions(user_id);

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_bre_user_accounts_updated_at
    BEFORE UPDATE ON bre_user_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
