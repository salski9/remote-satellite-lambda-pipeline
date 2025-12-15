#!/usr/bin/env python3
"""
Manual Texture Data Loader - Reads texture features from HDFS and writes to Cassandra
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Class name mapping
CLASS_NAMES = {
    1: "AnnualCrop",
    2: "Forest",
    3: "HerbaceousVegetation",
    4: "Highway",
    5: "Industrial",
    6: "Pasture",
    7: "PermanentCrop",
    8: "Residential",
    9: "River",
    10: "SeaLake"
}

def create_spark_session():
    """Initialize Spark session with Cassandra connector"""
    logger.info("Initializing Spark session...")
    
    # Download Cassandra connector JARs
    import os, tempfile, subprocess
    
    temp_dir = tempfile.mkdtemp()
    os.chdir(temp_dir)
    
    jars = [
        "https://repo1.maven.org/maven2/com/datastax/spark/spark-cassandra-connector_2.12/3.4.1/spark-cassandra-connector_2.12-3.4.1.jar",
        "https://repo1.maven.org/maven2/com/datastax/spark/spark-cassandra-connector-driver_2.12/3.4.1/spark-cassandra-connector-driver_2.12-3.4.1.jar",
        "https://repo1.maven.org/maven2/com/datastax/oss/java-driver-core/4.13.0/java-driver-core-4.13.0.jar",
        "https://repo1.maven.org/maven2/com/datastax/oss/java-driver-query-builder/4.13.0/java-driver-query-builder-4.13.0.jar",
        "https://repo1.maven.org/maven2/com/datastax/oss/java-driver-shaded-guava/25.1-jre-graal-sub-1/java-driver-shaded-guava-25.1-jre-graal-sub-1.jar",
        "https://repo1.maven.org/maven2/com/datastax/oss/native-protocol/1.5.1/native-protocol-1.5.1.jar",
        "https://repo1.maven.org/maven2/org/reactivestreams/reactive-streams/1.0.4/reactive-streams-1.0.4.jar",
        "https://repo1.maven.org/maven2/com/typesafe/config/1.4.1/config-1.4.1.jar"
    ]
    
    logger.info("Downloading JARs...")
    for jar_url in jars:
        subprocess.run(['wget', '-q', jar_url], check=True)
    
    jar_files = ','.join([f"{temp_dir}/{os.path.basename(url)}" for url in jars])
    
    spark = SparkSession.builder \
        .appName("TextureDataLoader") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:8020") \
        .config("spark.jars", jar_files) \
        .config("spark.cassandra.connection.host", "localhost") \
        .config("spark.cassandra.connection.port", "9042") \
        .config("spark.sql.extensions", "com.datastax.spark.connector.CassandraSparkExtensions") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    logger.info("Spark session created successfully")
    return spark

def load_texture_data(spark):
    """Load texture features and extract class name directly from image_id"""
    logger.info("Loading data from HDFS...")
    
    # Read texture features
    texture_df = spark.read.parquet("hdfs://localhost:8020/data/processed/texture/texture_features.parquet")
    logger.info(f"Loaded {texture_df.count()} texture features")
    
    # Extract class_name from image_id (format: "ClassName_1234")
    # Split on underscore and take everything before the last underscore
    enriched_df = texture_df.withColumn(
        "class_name",
        regexp_extract(col("image_id"), r"^([A-Za-z]+)_", 1)
    )
    
    logger.info(f"Extracted class names from {enriched_df.count()} records")
    
    # Show sample to verify
    logger.info("Sample data with class names:")
    enriched_df.select("image_id", "class_name", "glcm_contrast", "glcm_energy").show(5, truncate=False)
    
    return enriched_df

def write_texture_stats_to_cassandra(enriched_df):
    """Aggregate texture features and write to Cassandra"""
    logger.info("Computing texture statistics...")
    
    # Compute LBP entropy
    texture_with_entropy = enriched_df.withColumn(
        "lbp_entropy",
        -(col("lbp_hist_0") * log2(col("lbp_hist_0") + lit(1e-10)) +
          col("lbp_hist_1") * log2(col("lbp_hist_1") + lit(1e-10)) +
          col("lbp_hist_2") * log2(col("lbp_hist_2") + lit(1e-10)) +
          col("lbp_hist_3") * log2(col("lbp_hist_3") + lit(1e-10)) +
          col("lbp_hist_4") * log2(col("lbp_hist_4") + lit(1e-10)) +
          col("lbp_hist_5") * log2(col("lbp_hist_5") + lit(1e-10)) +
          col("lbp_hist_6") * log2(col("lbp_hist_6") + lit(1e-10)) +
          col("lbp_hist_7") * log2(col("lbp_hist_7") + lit(1e-10)))
    )
    
    # Aggregate by class
    texture_agg = texture_with_entropy.groupBy("class_name").agg(
        avg("glcm_contrast").alias("glcm_contrast_avg"),
        avg("glcm_homogeneity").alias("glcm_homogeneity_avg"),
        avg("glcm_energy").alias("glcm_energy_avg"),
        avg("glcm_correlation").alias("glcm_correlation_avg"),
        avg("glcm_dissimilarity").alias("glcm_dissimilarity_avg"),
        avg("glcm_asm").alias("glcm_asm_avg"),
        avg("lbp_entropy").alias("lbp_entropy_avg"),
        count("*").alias("texture_sample_count")
    ).withColumn("last_updated", current_timestamp())
    
    logger.info(f"Computed statistics for {texture_agg.count()} classes")
    
    # Show sample
    logger.info("Sample texture statistics:")
    texture_agg.show(5, truncate=False)
    
    # Write to Cassandra
    logger.info("Writing to Cassandra...")
    texture_agg.write \
        .format("org.apache.spark.sql.cassandra") \
        .mode("append") \
        .options(table="multimodal_texture_stats", keyspace="landcover") \
        .save()
    
    logger.info("✓ Texture statistics written to Cassandra successfully!")
    
    return texture_agg.count()

def write_image_stats_to_cassandra(enriched_df):
    """Write image statistics to Cassandra"""
    logger.info("Computing image statistics...")
    
    # Use tabular stats from processed images
    spark = SparkSession.builder.getOrCreate()
    processed_df = spark.read.parquet("hdfs://localhost:8020/data/processed/processed_images.parquet")
    
    # Extract class name from processed_df image_filename
    processed_with_class = processed_df.withColumn(
        "class_name",
        regexp_extract(col("image_filename"), r"^([A-Za-z]+)_", 1)
    )
    
    full_df = processed_with_class.select(
        "class_name", "red_mean", "green_mean", "blue_mean", "brightness_mean"
    )
    
    # Join with texture data to get contrast
    texture_agg = enriched_df.groupBy("class_name").agg(
        avg("glcm_contrast").alias("avg_contrast_temp")
    )
    
    image_stats = full_df.groupBy("class_name").agg(
        avg("red_mean").alias("avg_red_channel"),
        avg("green_mean").alias("avg_green_channel"),
        avg("blue_mean").alias("avg_blue_channel"),
        avg("brightness_mean").alias("avg_brightness"),
        count("*").alias("image_count")
    ).join(texture_agg, on="class_name", how="left") \
     .withColumnRenamed("avg_contrast_temp", "avg_contrast") \
     .withColumn("last_updated", current_timestamp())
    
    logger.info(f"Computed image statistics for {image_stats.count()} classes")
    
    # Write to Cassandra
    logger.info("Writing image stats to Cassandra...")
    image_stats.write \
        .format("org.apache.spark.sql.cassandra") \
        .mode("append") \
        .options(table="multimodal_image_stats", keyspace="landcover") \
        .save()
    
    logger.info("✓ Image statistics written to Cassandra successfully!")
    
    return image_stats.count()

def main():
    """Main execution"""
    print("\n" + "="*80)
    print("MANUAL TEXTURE DATA LOADER")
    print("="*80 + "\n")
    
    try:
        # Create Spark session
        spark = create_spark_session()
        
        # Load data
        enriched_df = load_texture_data(spark)
        
        # Write texture stats
        texture_count = write_texture_stats_to_cassandra(enriched_df)
        
        # Write image stats
        image_count = write_image_stats_to_cassandra(enriched_df)
        
        print("\n" + "="*80)
        print("SUCCESS!")
        print("="*80)
        print(f"✓ Texture statistics written for {texture_count} classes")
        print(f"✓ Image statistics written for {image_count} classes")
        print("✓ Dashboard should now display texture features")
        print("="*80 + "\n")
        
        spark.stop()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
