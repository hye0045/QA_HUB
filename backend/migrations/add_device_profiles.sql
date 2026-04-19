-- Migration: Tạo bảng quản lý Model Redmine (DeviceModelProfiles)
-- DB: PostgreSQL (QA_HUB)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS device_model_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR NOT NULL UNIQUE,
    project_id VARCHAR NOT NULL,
    tracker_id INTEGER NOT NULL DEFAULT 38,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT timezone('utc', now())
);

-- Insert a default Kyocera Profile
INSERT INTO device_model_profiles (id, name, project_id, tracker_id)
VALUES (uuid_generate_v4(), 'Kyocera Default (eb1242)', 'eb1242', 38)
ON CONFLICT (name) DO NOTHING;
