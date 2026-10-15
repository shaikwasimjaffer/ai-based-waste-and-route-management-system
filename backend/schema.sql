-- ====================================================================
-- SmartWaste: AI-Based Smart Waste Collection and Route Optimization System
-- Relational Database Management System (PostgreSQL 18 / MySQL 8.0 DDL)
-- 3NF Normalized Schema Specification matching PBL Final Documentation
-- ====================================================================

-- 1. DROP EXISTING TABLES (In reverse dependency order)
DROP TABLE IF EXISTS activity_logs CASCADE;
DROP TABLE IF EXISTS route_plans CASCADE;
DROP TABLE IF EXISTS collection_history CASCADE;
DROP TABLE IF EXISTS sensor_data CASCADE;
DROP TABLE IF EXISTS workers CASCADE;
DROP TABLE IF EXISTS bins CASCADE;

-- 2. CREATE BINS MASTER TABLE (Table 5 in Documentation)
CREATE TABLE bins (
    id VARCHAR(50) PRIMARY KEY,
    sensor_id VARCHAR(50),
    location VARCHAR(200) NOT NULL,
    street_address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    postal_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'USA',
    zone VARCHAR(50) NOT NULL DEFAULT 'Zone A',
    bin_type VARCHAR(50) NOT NULL DEFAULT 'general',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    capacity_liters INTEGER DEFAULT 240,
    height_cm DOUBLE PRECISION DEFAULT 100.0,
    fill DOUBLE PRECISION DEFAULT 0.0 CHECK (fill >= 0.0 AND fill <= 100.0),
    status VARCHAR(20) DEFAULT 'normal' CHECK (status IN ('urgent', 'warning', 'normal', 'collected')),
    battery_level DOUBLE PRECISION DEFAULT 100.0,
    collected BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index on fill level and status for fast dispatch queries
CREATE INDEX idx_bins_fill ON bins (fill);
CREATE INDEX idx_bins_status ON bins (status);
CREATE INDEX idx_bins_zone ON bins (zone);

-- 3. CREATE WORKERS MASTER TABLE (Table 7 in Documentation)
CREATE TABLE workers (
    id VARCHAR(50) PRIMARY KEY,
    badge_number VARCHAR(50) UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(30),
    assigned_truck_id VARCHAR(50),
    vehicle_type VARCHAR(50) DEFAULT 'diesel',
    truck_capacity_tons DOUBLE PRECISION DEFAULT 2.5,
    shift_status VARCHAR(20) DEFAULT 'On Shift' CHECK (shift_status IN ('On Shift', 'Off Shift')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. CREATE SENSOR_DATA TELEMETRY STREAM TABLE (Table 6 in Documentation)
CREATE TABLE sensor_data (
    reading_id SERIAL PRIMARY KEY,
    bin_id VARCHAR(50) NOT NULL REFERENCES bins(id) ON DELETE CASCADE,
    raw_distance_cm DOUBLE PRECISION NOT NULL CHECK (raw_distance_cm >= 0.0),
    calculated_fill_pct DOUBLE PRECISION NOT NULL CHECK (calculated_fill_pct >= 0.0 AND calculated_fill_pct <= 100.0),
    battery_voltage DOUBLE PRECISION DEFAULT 3.70,
    temperature_celsius DOUBLE PRECISION DEFAULT 25.00,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sensor_data_bin_ts ON sensor_data (bin_id, timestamp);

-- 5. CREATE COLLECTION_HISTORY TRANSACTION LEDGER TABLE (Table 8 in Documentation)
CREATE TABLE collection_history (
    id VARCHAR(50) PRIMARY KEY,
    bin_id VARCHAR(50) NOT NULL REFERENCES bins(id) ON DELETE CASCADE,
    worker_id VARCHAR(50) REFERENCES workers(id) ON DELETE SET NULL,
    location VARCHAR(200),
    collection_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fill_level_before DOUBLE PRECISION CHECK (fill_level_before >= 0.0 AND fill_level_before <= 100.0),
    fill_level_after DOUBLE PRECISION DEFAULT 0.0,
    waste_weight_kg DOUBLE PRECISION DEFAULT 0.0,
    notes TEXT,
    status VARCHAR(50) DEFAULT 'Complete'
);

CREATE INDEX idx_collection_history_ts ON collection_history (collection_timestamp);

-- 6. CREATE ROUTE_PLANS OPTIMIZATION TABLE (Table 9 in Documentation)
CREATE TABLE route_plans (
    id VARCHAR(50) PRIMARY KEY,
    route_name VARCHAR(150) NOT NULL,
    worker_id VARCHAR(50) REFERENCES workers(id) ON DELETE SET NULL,
    generation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_distance_km DOUBLE PRECISION DEFAULT 0.0 CHECK (total_distance_km >= 0.0),
    estimated_time_min DOUBLE PRECISION DEFAULT 0.0,
    fuel_consumed_liters DOUBLE PRECISION DEFAULT 0.0,
    co2_emissions_kg DOUBLE PRECISION DEFAULT 0.0,
    status VARCHAR(50) DEFAULT 'Pending' CHECK (status IN ('Pending', 'In Progress', 'Completed')),
    traffic_condition VARCHAR(50) DEFAULT 'moderate',
    traffic_delay_minutes DOUBLE PRECISION DEFAULT 0.0,
    optimized BOOLEAN DEFAULT TRUE,
    waypoint_sequence TEXT
);

-- 7. CREATE ACTIVITY_LOGS TABLE (Live Telemetry Event Feed)
CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,
    icon VARCHAR(10) DEFAULT '◉',
    title VARCHAR(100) NOT NULL,
    detail VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ====================================================================
-- AUTOMATED DATABASE TRIGGERS (Section 3.6 in Documentation)
-- ====================================================================

-- Function for Trigger 1: Live Status Synchronization Trigger
CREATE OR REPLACE FUNCTION trg_sync_bin_status()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE bins
    SET 
        fill = NEW.calculated_fill_pct,
        status = CASE 
            WHEN NEW.calculated_fill_pct >= 85.0 THEN 'urgent'
            WHEN NEW.calculated_fill_pct >= 65.0 THEN 'warning'
            ELSE 'normal'
        END,
        collected = FALSE,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.bin_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sensor_status_sync
AFTER INSERT ON sensor_data
FOR EACH ROW
EXECUTE FUNCTION trg_sync_bin_status();

-- Function for Trigger 2: Collection Audit and Reset Trigger
CREATE OR REPLACE FUNCTION trg_reset_bin_on_collection()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE bins
    SET 
        fill = 0.0,
        status = 'normal',
        collected = TRUE,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.bin_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_collection_audit_reset
AFTER INSERT ON collection_history
FOR EACH ROW
EXECUTE FUNCTION trg_reset_bin_on_collection();

-- Verification Query
SELECT 'SmartWaste 3NF Schema & Triggers Created Successfully' AS status;
