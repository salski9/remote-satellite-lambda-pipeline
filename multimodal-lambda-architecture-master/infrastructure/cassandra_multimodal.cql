-- Extended Cassandra Schema for Multimodal Data
-- Supports both tabular (CSV) and image (RGB) features

-- Create keyspace if not exists
CREATE KEYSPACE IF NOT EXISTS landcover 
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE landcover;

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
