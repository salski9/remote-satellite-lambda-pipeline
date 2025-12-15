#!/usr/bin/env python3
"""
Batch Processing Layer - Lambda Architecture
Reads historical data from HDFS, computes accurate aggregations
Runs periodically (daily/weekly) for comprehensive analytics
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CLASS_NAMES = {
    1: "AnnualCrop", 2: "Forest", 3: "HerbaceousVegetation",
    4: "Highway", 5: "Industrial", 6: "Pasture",
    7: "PermanentCrop", 8: "Residential", 9: "River", 10: "SeaLake"
}

def create_spark_session():
    """Initialize Spark with Hive support"""
    logger.info("Initializing Spark session with Hive support...")
    
    spark = SparkSession.builder \
        .appName("BatchProcessingLayer") \
        .config("spark.sql.warehouse.dir", "hdfs://localhost:8020/user/hive/warehouse") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:8020") \
        .config("spark.driver.memory", "4g") \
        .config("spark.executor.memory", "4g") \
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
        .enableHiveSupport() \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    logger.info("✓ Spark session with Hive support created")
    return spark

def create_hive_database(spark):
    """Create Hive database for batch views"""
    logger.info("Creating Hive database for batch views...")
    
    spark.sql("CREATE DATABASE IF NOT EXISTS batch_views")
    spark.sql("USE batch_views")
    
    logger.info("✓ Hive database 'batch_views' ready")

def read_source_data(spark):
    """Read all historical data from HDFS Parquet files"""
    logger.info("=" * 80)
    logger.info("READING SOURCE DATA FROM HDFS")
    logger.info("=" * 80)
    
    # Read processed images (contains all spectral features)
    processed_path = "hdfs://localhost:8020/data/processed/processed_images.parquet"
    logger.info(f"Reading: {processed_path}")
    processed_df = spark.read.parquet(processed_path)
    logger.info(f"✓ Loaded {processed_df.count()} processed images")
    
    # NOTE: Texture features are not joined due to image_id mismatch
    # processed_images uses IMG_000001 format
    # texture_features uses SeaLake_1678 format
    # This would require a proper ID mapping from the pre-ingestion phase
    
    return processed_df

def compute_class_statistics(spark, enriched_df):
    """Compute comprehensive class-level statistics"""
    logger.info("=" * 80)
    logger.info("COMPUTING CLASS STATISTICS (Batch View)")
    logger.info("=" * 80)
    
    # Add class name
    class_name_udf = udf(lambda x: CLASS_NAMES.get(x, f"Unknown_{x}"), StringType())
    enriched_df = enriched_df.withColumn("class_name", class_name_udf(col("class_id")))
    
    # Aggregate by class
    class_stats = enriched_df.groupBy("class_id", "class_name").agg(
        # Count
        count("*").alias("total_samples"),
        
        # NDVI statistics
        avg("ndvi_mean").alias("avg_ndvi"),
        stddev("ndvi_mean").alias("std_ndvi"),
        min("ndvi_mean").alias("min_ndvi"),
        max("ndvi_mean").alias("max_ndvi"),
        
        # Spectral statistics
        avg("red_mean").alias("avg_red"),
        avg("green_mean").alias("avg_green"),
        avg("blue_mean").alias("avg_blue"),
        avg("nir_mean").alias("avg_nir"),
        avg("brightness_mean").alias("avg_brightness")
    ).orderBy("class_id")
    
    # Add timestamp
    class_stats = class_stats.withColumn("batch_timestamp", lit(datetime.now().isoformat()))
    
    logger.info(f"✓ Computed statistics for {class_stats.count()} classes")
    
    # Save to Hive table
    logger.info("Saving to Hive table: batch_views.class_statistics")
    class_stats.write \
        .mode("overwrite") \
        .format("parquet") \
        .saveAsTable("batch_views.class_statistics")
    
    logger.info("✓ Class statistics saved to Hive")
    
    return class_stats

def compute_temporal_trends(spark, enriched_df):
    """Compute temporal trends (simulated - using class_id as proxy for time)"""
    logger.info("=" * 80)
    logger.info("COMPUTING TEMPORAL TRENDS (Batch View)")
    logger.info("=" * 80)
    
    # Add class name
    class_name_udf = udf(lambda x: CLASS_NAMES.get(x, f"Unknown_{x}"), StringType())
    enriched_df = enriched_df.withColumn("class_name", class_name_udf(col("class_id")))
    
    # Simulate monthly trends (group by class as time periods)
    trends = enriched_df.groupBy("class_id", "class_name").agg(
        count("*").alias("samples"),
        avg("ndvi_mean").alias("avg_ndvi"),
        avg("brightness_mean").alias("avg_brightness"),
        avg("red_mean").alias("avg_red"),
        avg("green_mean").alias("avg_green"),
        avg("blue_mean").alias("avg_blue")
    ).orderBy("class_id")
    
    # Add metadata
    trends = trends.withColumn("batch_timestamp", lit(datetime.now().isoformat()))
    trends = trends.withColumn("period", concat(lit("Month_"), col("class_id")))
    
    logger.info(f"✓ Computed trends for {trends.count()} periods")
    
    # Save to Hive
    logger.info("Saving to Hive table: batch_views.temporal_trends")
    trends.write \
        .mode("overwrite") \
        .format("parquet") \
        .saveAsTable("batch_views.temporal_trends")
    
    logger.info("✓ Temporal trends saved to Hive")
    
    return trends

def compute_class_separability(spark, enriched_df):
    """Compute pairwise class separability metrics"""
    logger.info("=" * 80)
    logger.info("COMPUTING CLASS SEPARABILITY (Batch View)")
    logger.info("=" * 80)
    
    # Add class name
    class_name_udf = udf(lambda x: CLASS_NAMES.get(x, f"Unknown_{x}"), StringType())
    enriched_df = enriched_df.withColumn("class_name", class_name_udf(col("class_id")))
    
    # Compute class centroids (using spectral features only)
    centroids = enriched_df.groupBy("class_id", "class_name").agg(
        avg("ndvi_mean").alias("centroid_ndvi"),
        avg("red_mean").alias("centroid_red"),
        avg("green_mean").alias("centroid_green"),
        avg("blue_mean").alias("centroid_blue"),
        avg("nir_mean").alias("centroid_nir"),
        avg("brightness_mean").alias("centroid_brightness")
    )
    
    # Self-join to compute all pairs
    centroids_a = centroids.alias("a")
    centroids_b = centroids.alias("b")
    
    pairs = centroids_a.join(
        centroids_b,
        col("a.class_id") < col("b.class_id")
    )
    
    # Compute Euclidean distance (using 6 spectral features)
    separability = pairs.select(
        col("a.class_id").alias("class_id_1"),
        col("a.class_name").alias("class_name_1"),
        col("b.class_id").alias("class_id_2"),
        col("b.class_name").alias("class_name_2"),
        sqrt(
            pow(col("a.centroid_ndvi") - col("b.centroid_ndvi"), 2) +
            pow(col("a.centroid_red") - col("b.centroid_red"), 2) +
            pow(col("a.centroid_green") - col("b.centroid_green"), 2) +
            pow(col("a.centroid_blue") - col("b.centroid_blue"), 2) +
            pow(col("a.centroid_nir") - col("b.centroid_nir"), 2) +
            pow(col("a.centroid_brightness") - col("b.centroid_brightness"), 2)
        ).alias("euclidean_distance"),
        lit(datetime.now().isoformat()).alias("batch_timestamp")
    ).orderBy(desc("euclidean_distance"))
    
    logger.info(f"✓ Computed separability for {separability.count()} class pairs")
    
    # Save to Hive
    logger.info("Saving to Hive table: batch_views.class_separability")
    separability.write \
        .mode("overwrite") \
        .format("parquet") \
        .saveAsTable("batch_views.class_separability")
    
    logger.info("✓ Class separability saved to Hive")
    
    return separability

def compute_feature_correlations(spark, enriched_df):
    """Compute correlation matrix for all features"""
    logger.info("=" * 80)
    logger.info("COMPUTING FEATURE CORRELATIONS (Batch View)")
    logger.info("=" * 80)
    
    # Select numeric features (spectral only - texture features have mismatched image_ids)
    feature_cols = [
        "ndvi_mean", "red_mean", "green_mean", "blue_mean", 
        "nir_mean", "brightness_mean"
    ]
    
    correlations = []
    for i, col1 in enumerate(feature_cols):
        for col2 in feature_cols[i:]:
            corr = enriched_df.stat.corr(col1, col2)
            correlations.append({
                "feature_1": col1,
                "feature_2": col2,
                "correlation": float(corr) if corr is not None else 0.0,
                "batch_timestamp": datetime.now().isoformat()
            })
    
    # Create DataFrame
    corr_df = spark.createDataFrame(correlations)
    
    logger.info(f"✓ Computed {corr_df.count()} feature correlations")
    
    # Save to Hive
    logger.info("Saving to Hive table: batch_views.feature_correlations")
    corr_df.write \
        .mode("overwrite") \
        .format("parquet") \
        .saveAsTable("batch_views.feature_correlations")
    
    logger.info("✓ Feature correlations saved to Hive")
    
    return corr_df

def display_summary(class_stats, trends, separability, correlations):
    """Display batch processing summary"""
    logger.info("=" * 80)
    logger.info("BATCH PROCESSING SUMMARY")
    logger.info("=" * 80)
    
    print("\n📊 CLASS STATISTICS (First 5 rows):")
    class_stats.select("class_name", "total_samples", "avg_ndvi", "avg_brightness").show(5)
    
    print("\n📈 TEMPORAL TRENDS (First 5 rows):")
    trends.select("period", "class_name", "avg_ndvi", "avg_red", "avg_brightness").show(5)
    
    print("\n⚖️ CLASS SEPARABILITY (Top 5 most separable pairs):")
    separability.select("class_name_1", "class_name_2", "euclidean_distance").show(5)
    
    print("\n🔗 FEATURE CORRELATIONS (Top 5 strongest):")
    correlations.filter(col("feature_1") != col("feature_2")) \
        .orderBy(abs(col("correlation")).desc()) \
        .select("feature_1", "feature_2", "correlation").show(5)
    
    logger.info("=" * 80)
    logger.info("✓ BATCH PROCESSING COMPLETE")
    logger.info("=" * 80)
    logger.info("Batch views stored in Hive database: batch_views")
    logger.info("Tables created:")
    logger.info("  • batch_views.class_statistics")
    logger.info("  • batch_views.temporal_trends")
    logger.info("  • batch_views.class_separability")
    logger.info("  • batch_views.feature_correlations")
    logger.info("=" * 80)

def main():
    """Main batch processing execution"""
    try:
        # 1. Initialize Spark with Hive
        spark = create_spark_session()
        
        # 2. Create Hive database
        create_hive_database(spark)
        
        # 3. Read source data from HDFS
        enriched_df = read_source_data(spark)
        
        # 4. Compute batch views
        class_stats = compute_class_statistics(spark, enriched_df)
        trends = compute_temporal_trends(spark, enriched_df)
        separability = compute_class_separability(spark, enriched_df)
        correlations = compute_feature_correlations(spark, enriched_df)
        
        # 5. Display summary
        display_summary(class_stats, trends, separability, correlations)
        
        # 6. Cleanup
        spark.stop()
        logger.info("✓ Batch processing finished successfully!")
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
