-- ============================================================================
-- Cassandra Schema for Batch Processing Layer
-- Stores batch-computed views from Hive/HDFS
-- ============================================================================

-- Create keyspace for batch views
CREATE KEYSPACE IF NOT EXISTS batch_views
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE batch_views;

-- ============================================================================
-- Class statistics from batch processing
-- ============================================================================
CREATE TABLE IF NOT EXISTS class_statistics_table (
    class_id int,
    class_name text,
    total_samples bigint,
    avg_ndvi double,
    std_ndvi double,
    min_ndvi double,
    max_ndvi double,
    avg_red double,
    avg_green double,
    avg_blue double,
    avg_nir double,
    avg_brightness double,
    avg_glcm_contrast double,
    avg_glcm_homogeneity double,
    avg_glcm_energy double,
    avg_glcm_correlation double,
    avg_lbp_entropy double,
    batch_timestamp text,
    PRIMARY KEY (class_id)
);

-- ============================================================================
-- Temporal trends from batch processing
-- ============================================================================
CREATE TABLE IF NOT EXISTS temporal_trends_table (
    period text,
    class_id int,
    class_name text,
    samples bigint,
    avg_ndvi double,
    avg_brightness double,
    avg_texture_complexity double,
    batch_timestamp text,
    PRIMARY KEY (period, class_id)
);

-- ============================================================================
-- Class separability from batch processing
-- ============================================================================
CREATE TABLE IF NOT EXISTS separability_table (
    class_id_1 int,
    class_name_1 text,
    class_id_2 int,
    class_name_2 text,
    euclidean_distance double,
    batch_timestamp text,
    PRIMARY KEY ((class_id_1, class_id_2))
);

-- ============================================================================
-- Feature correlations from batch processing
-- ============================================================================
CREATE TABLE IF NOT EXISTS correlations_table (
    feature_1 text,
    feature_2 text,
    correlation double,
    batch_timestamp text,
    PRIMARY KEY ((feature_1, feature_2))
);
