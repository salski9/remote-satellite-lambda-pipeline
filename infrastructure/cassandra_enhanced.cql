-- Enhanced Cassandra Schema for Pre-Ingestion Integration
-- Supports: CSV features + ML vectors + Texture features (GLCM + LBP)

-- Create keyspace if not exists
CREATE KEYSPACE IF NOT EXISTS landcover 
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE landcover;

-- ============================================================================
-- EXISTING TABLES (from multimodal lambda architecture)
-- ============================================================================

-- Table 1: Multimodal Tabular Statistics (from CSV data)
-- Stores latest aggregated statistics per class (updated on each batch)
CREATE TABLE IF NOT EXISTS multimodal_tabular_stats (
    class_name TEXT PRIMARY KEY,
    ndvi_avg DOUBLE,
    ndvi_stddev DOUBLE,
    red_avg DOUBLE,
    green_avg DOUBLE,
    blue_avg DOUBLE,
    nir_avg DOUBLE,
    brightness_avg DOUBLE,
    sample_count BIGINT,
    last_updated TIMESTAMP
);

-- Table 2: Multimodal Image Statistics (from RGB images)
CREATE TABLE IF NOT EXISTS multimodal_image_stats (
    class_name TEXT PRIMARY KEY,
    avg_red_channel DOUBLE,
    avg_green_channel DOUBLE,
    avg_blue_channel DOUBLE,
    avg_brightness DOUBLE,
    avg_contrast DOUBLE,
    image_count BIGINT,
    last_updated TIMESTAMP
);

-- Table 2b: Cumulative Event Counter (tracks total events processed)
CREATE TABLE IF NOT EXISTS multimodal_event_totals (
    class_name TEXT PRIMARY KEY,
    total_events BIGINT,
    total_images BIGINT,
    first_seen TIMESTAMP,
    last_updated TIMESTAMP
);

-- Table 3: Multimodal Anomalies (fusion of both modalities)
CREATE TABLE IF NOT EXISTS multimodal_anomalies (
    class_name TEXT,
    timestamp TIMESTAMP,
    image_id TEXT,
    ndvi_mean DOUBLE,
    ndvi_min DOUBLE,
    ndvi_max DOUBLE,
    brightness DOUBLE,
    contrast DOUBLE,
    anomaly_type TEXT,
    PRIMARY KEY (class_name, timestamp, image_id)
) WITH CLUSTERING ORDER BY (timestamp DESC, image_id ASC);

-- ============================================================================
-- NEW TABLES (for pre-ingestion integration)
-- ============================================================================

-- Table 4: ML-Ready Feature Vectors (from pre-ingestion pipeline)
-- Stores pre-computed, normalized feature vectors for ML applications
CREATE TABLE IF NOT EXISTS multimodal_ml_features (
    class_name TEXT PRIMARY KEY,
    avg_final_features TEXT,      -- JSON array of averaged normalized features
    feature_dimension INT,         -- Dimension of feature vector (e.g., 10)
    sample_count BIGINT,          -- Number of samples in this batch
    last_updated TIMESTAMP
);

-- Table 5: Texture Feature Statistics (GLCM + LBP from pre-ingestion)
-- Stores aggregated texture features for advanced image analysis
CREATE TABLE IF NOT EXISTS multimodal_texture_stats (
    class_name TEXT PRIMARY KEY,
    
    -- GLCM (Gray-Level Co-occurrence Matrix) features
    glcm_contrast_avg DOUBLE,      -- Measure of local variations
    glcm_homogeneity_avg DOUBLE,   -- Measure of texture uniformity
    glcm_energy_avg DOUBLE,        -- Measure of texture uniformity/patterns
    glcm_correlation_avg DOUBLE,   -- Linear dependency of gray levels
    glcm_dissimilarity_avg DOUBLE, -- Measure of texture variation
    glcm_asm_avg DOUBLE,          -- Angular Second Moment
    
    -- LBP (Local Binary Pattern) entropy
    lbp_entropy_avg DOUBLE,        -- Measure of texture complexity
    
    -- Metadata
    texture_sample_count BIGINT,
    last_updated TIMESTAMP
);

-- ============================================================================
-- BACKWARD COMPATIBILITY TABLES
-- ============================================================================

-- Original tables (keep for backward compatibility)
CREATE TABLE IF NOT EXISTS realtime_ndvi_by_class (
    class_name TEXT PRIMARY KEY,
    ndvi_avg DOUBLE,
    ndvi_stddev DOUBLE
);

CREATE TABLE IF NOT EXISTS anomaly_alerts (
    class_name TEXT,
    timestamp TIMESTAMP,
    image_id TEXT,
    ndvi_mean DOUBLE,
    ndvi_min DOUBLE,
    ndvi_max DOUBLE,
    PRIMARY KEY (class_name, timestamp, image_id)
) WITH CLUSTERING ORDER BY (timestamp DESC, image_id ASC);

-- ============================================================================
-- SCHEMA SUMMARY
-- ============================================================================
-- Total Tables: 7
-- 
-- Data Flow:
-- 1. Pre-Ingestion Layer → Parquet files (HDFS)
-- 2. Kafka Producer → Read Parquet → Stream to Kafka
-- 3. Spark Streaming → Process events → Write to Cassandra
-- 4. Flask API → Query Cassandra → Serve to Dashboard
--
-- New Capabilities:
-- - ML-ready feature vectors (pre-normalized)
-- - Advanced texture analysis (GLCM + LBP)
-- - Three-way feature fusion (CSV + RGB + Texture)
-- ============================================================================
