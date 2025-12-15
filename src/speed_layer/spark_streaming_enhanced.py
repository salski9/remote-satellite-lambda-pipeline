#!/usr/bin/env python3
"""
Enhanced Spark Streaming Job - Processes Pre-Computed Features
Handles: CSV features + ML vectors + Texture features (GLCM + LBP)
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json

# Enhanced schema for pre-computed features
enhanced_schema = StructType([
    # Metadata
    StructField("image_id", StringType()),
    StructField("image_filename", StringType()),
    StructField("class_id", IntegerType()),
    StructField("class_name", StringType()),
    StructField("timestamp", StringType()),
    
    # NDVI features (from CSV)
    StructField("ndvi_mean", DoubleType()),
    StructField("ndvi_std", DoubleType()),
    StructField("ndvi_min", DoubleType()),
    StructField("ndvi_max", DoubleType()),
    
    # Spectral features (from CSV)
    StructField("red_mean", DoubleType()),
    StructField("green_mean", DoubleType()),
    StructField("blue_mean", DoubleType()),
    StructField("nir_mean", DoubleType()),
    StructField("brightness_mean", DoubleType()),
    
    # Encoded features (from MLlib)
    StructField("vegetation_index", StringType()),
    StructField("vegetation_index_indexed", DoubleType()),
    StructField("vegetation_index_encoded", ArrayType(DoubleType())),
    
    # ML-ready vectors (PRE-NORMALIZED!)
    StructField("raw_features", ArrayType(DoubleType())),
    StructField("final_features", ArrayType(DoubleType())),
    
    # Texture features - GLCM
    StructField("glcm_contrast", FloatType()),
    StructField("glcm_homogeneity", FloatType()),
    StructField("glcm_energy", FloatType()),
    StructField("glcm_correlation", FloatType()),
    StructField("glcm_dissimilarity", FloatType()),
    StructField("glcm_asm", FloatType()),
    
    # Texture features - LBP histogram
    StructField("lbp_hist_0", FloatType()),
    StructField("lbp_hist_1", FloatType()),
    StructField("lbp_hist_2", FloatType()),
    StructField("lbp_hist_3", FloatType()),
    StructField("lbp_hist_4", FloatType()),
    StructField("lbp_hist_5", FloatType()),
    StructField("lbp_hist_6", FloatType()),
    StructField("lbp_hist_7", FloatType()),
])

def array_to_json_string(arr):
    """Convert array to JSON string for Cassandra storage"""
    if arr is None:
        return None
    return json.dumps(arr)

# Register UDF
array_to_json_udf = udf(array_to_json_string, StringType())

def update_cumulative_totals(spark, batch_df):
    """Update cumulative event totals"""
    try:
        existing_totals = spark.read \
            .format("org.apache.spark.sql.cassandra") \
            .options(table="multimodal_event_totals", keyspace="landcover") \
            .load()
        
        new_counts = batch_df.groupBy("class_name").agg(
            count("*").alias("new_events"),
            count(when(col("glcm_contrast").isNotNull(), 1)).alias("new_images")
        )
        
        updated = new_counts.alias("new").join(
            existing_totals.alias("old"),
            col("new.class_name") == col("old.class_name"),
            "full_outer"
        ).select(
            coalesce(col("new.class_name"), col("old.class_name")).alias("class_name"),
            (coalesce(col("old.total_events"), lit(0)) + coalesce(col("new.new_events"), lit(0))).alias("total_events"),
            (coalesce(col("old.total_images"), lit(0)) + coalesce(col("new.new_images"), lit(0))).alias("total_images"),
            coalesce(col("old.first_seen"), current_timestamp()).alias("first_seen"),
            current_timestamp().alias("last_updated")
        )
        
        updated.write \
            .format("org.apache.spark.sql.cassandra") \
            .mode("append") \
            .options(table="multimodal_event_totals", keyspace="landcover") \
            .save()
            
        return updated.count()
    except Exception as e:
        print(f"⚠ Could not update cumulative totals: {e}")
        initial_counts = batch_df.groupBy("class_name").agg(
            count("*").alias("total_events"),
            count(when(col("glcm_contrast").isNotNull(), 1)).alias("total_images")
        ).withColumn("first_seen", current_timestamp()) \
         .withColumn("last_updated", current_timestamp())
        
        initial_counts.write \
            .format("org.apache.spark.sql.cassandra") \
            .mode("append") \
            .options(table="multimodal_event_totals", keyspace="landcover") \
            .save()
        return initial_counts.count()

def process_enhanced_batch(batch_df, batch_id):
    """Process batch with pre-computed features"""
    if batch_df.count() == 0:
        return
    
    print(f"\n{'='*80}")
    print(f"Processing Enhanced Batch {batch_id}")
    print(f"{'='*80}")
    
    # 1. Tabular Analytics: CSV features aggregation
    tabular_agg = batch_df.groupBy("class_name").agg(
        avg("ndvi_mean").alias("ndvi_avg"),
        stddev("ndvi_mean").alias("ndvi_stddev"),
        avg("red_mean").alias("red_avg"),
        avg("green_mean").alias("green_avg"),
        avg("blue_mean").alias("blue_avg"),
        avg("nir_mean").alias("nir_avg"),
        avg("brightness_mean").alias("brightness_avg"),
        count("*").alias("sample_count")
    ).withColumn("last_updated", current_timestamp())
    
    tabular_agg.write \
        .format("org.apache.spark.sql.cassandra") \
        .mode("append") \
        .options(table="multimodal_tabular_stats", keyspace="landcover") \
        .save()
    
    print(f"✓ Tabular features aggregated ({tabular_agg.count()} classes)")
    
    # 1b. Update cumulative totals
    spark = SparkSession.builder.getOrCreate()
    total_classes = update_cumulative_totals(spark, batch_df)
    print(f"✓ Cumulative totals updated ({total_classes} classes)")
    
    # 2. ML Features Analytics: Store averaged final_features vectors
    ml_df = batch_df.filter(col("final_features").isNotNull())
    
    if ml_df.count() > 0:
        # Get array size (should be 10 for your case)
        sample_row = ml_df.select("final_features").first()
        feature_dim = len(sample_row["final_features"]) if sample_row else 0
        
        # Aggregate ML features by class
        ml_agg = ml_df.groupBy("class_name").agg(
            # Store as JSON string since Cassandra doesn't support arrays natively
            collect_list("final_features").alias("all_features"),
            count("*").alias("sample_count")
        ).withColumn("feature_dimension", lit(feature_dim)) \
         .withColumn("last_updated", current_timestamp())
        
        # Convert first feature vector to JSON for storage (sample)
        ml_agg = ml_agg.withColumn(
            "avg_final_features",
            array_to_json_udf(col("all_features")[0])
        ).drop("all_features")
        
        ml_agg.write \
            .format("org.apache.spark.sql.cassandra") \
            .mode("append") \
            .options(table="multimodal_ml_features", keyspace="landcover") \
            .save()
        
        print(f"✓ ML features aggregated ({ml_agg.count()} classes, dim={feature_dim})")
    
    # 3. Texture Analytics: GLCM + LBP aggregation
    texture_df = batch_df.filter(col("glcm_contrast").isNotNull())
    
    if texture_df.count() > 0:
        # Compute LBP entropy (measure of texture complexity)
        texture_with_entropy = texture_df.withColumn(
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
        
        # Aggregate texture features by class
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
        
        texture_agg.write \
            .format("org.apache.spark.sql.cassandra") \
            .mode("append") \
            .options(table="multimodal_texture_stats", keyspace="landcover") \
            .save()
        
        print(f"✓ Texture features aggregated ({texture_agg.count()} classes)")
    
    # 4. Image Stats (for backward compatibility)
    image_df = batch_df.filter(col("glcm_contrast").isNotNull())
    
    if image_df.count() > 0:
        image_stats = image_df.groupBy("class_name").agg(
            avg("red_mean").alias("avg_red_channel"),
            avg("green_mean").alias("avg_green_channel"),
            avg("blue_mean").alias("avg_blue_channel"),
            avg("brightness_mean").alias("avg_brightness"),
            avg("glcm_contrast").alias("avg_contrast"),
            count("*").alias("image_count")
        ).withColumn("last_updated", current_timestamp())
        
        image_stats.write \
            .format("org.apache.spark.sql.cassandra") \
            .mode("append") \
            .options(table="multimodal_image_stats", keyspace="landcover") \
            .save()
        
        print(f"✓ Image stats updated ({image_stats.count()} classes)")
    
    # 5. Enhanced Anomaly Detection: Multi-feature fusion
    if batch_df.count() > 0:
        # Compute global statistics
        stats = batch_df.agg(
            avg("ndvi_mean").alias("global_ndvi_mean"),
            stddev("ndvi_mean").alias("global_ndvi_std"),
            avg("brightness_mean").alias("global_brightness_mean"),
            stddev("brightness_mean").alias("global_brightness_std"),
            avg("glcm_contrast").alias("global_contrast_mean"),
            stddev("glcm_contrast").alias("global_contrast_std")
        ).collect()[0]
        
        # Detect anomalies using NDVI + brightness + texture
        anomalies = batch_df.filter(
            (abs(col("ndvi_mean") - lit(stats["global_ndvi_mean"])) > 2 * lit(stats["global_ndvi_std"])) |
            (abs(col("brightness_mean") - lit(stats["global_brightness_mean"])) > 2 * lit(stats["global_brightness_std"])) |
            ((col("glcm_contrast").isNotNull()) & 
             (abs(col("glcm_contrast") - lit(stats["global_contrast_mean"])) > 2 * lit(stats["global_contrast_std"])))
        ).select(
            "image_id",
            "class_name",
            "ndvi_mean",
            "ndvi_min",
            "ndvi_max",
            col("brightness_mean").alias("brightness"),
            col("glcm_contrast").alias("contrast"),
            to_timestamp(col("timestamp")).alias("timestamp"),
            lit("enhanced_multimodal").alias("anomaly_type")
        )
        
        if anomalies.count() > 0:
            anomalies.write \
                .format("org.apache.spark.sql.cassandra") \
                .mode("append") \
                .options(table="multimodal_anomalies", keyspace="landcover") \
                .save()
            
            print(f"✓ Enhanced anomalies detected: {anomalies.count()}")
    
    print(f"{'='*80}\n")

def main():
    print("\n" + "="*80)
    print("ENHANCED SPARK STREAMING JOB")
    print("Processing: Pre-computed CSV + ML vectors + Texture features")
    print("="*80 + "\n")
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("EnhancedMultimodalStreaming") \
        .config("spark.cassandra.connection.host", "localhost") \
        .config("spark.cassandra.connection.port", "9042") \
        .config("spark.sql.streaming.checkpointLocation", "/tmp/spark_enhanced_ckpt") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # Read from Kafka
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:29092") \
        .option("subscribe", "enhanced-multimodal-events") \
        .option("startingOffsets", "latest") \
        .load()
    
    # Parse JSON with enhanced schema
    parsed_df = df.select(
        from_json(col("value").cast("string"), enhanced_schema).alias("data")
    ).select("data.*")
    
    # Process with foreachBatch
    query = parsed_df.writeStream \
        .foreachBatch(process_enhanced_batch) \
        .outputMode("update") \
        .trigger(processingTime='5 seconds') \
        .start()
    
    print("✓ Enhanced streaming job started")
    print("  - Listening to topic: enhanced-multimodal-events")
    print("  - Processing: CSV + ML vectors + Texture features")
    print("  - Writing to 5 Cassandra tables:")
    print("    • multimodal_tabular_stats")
    print("    • multimodal_ml_features (NEW)")
    print("    • multimodal_texture_stats (NEW)")
    print("    • multimodal_image_stats")
    print("    • multimodal_anomalies")
    print("\nPress Ctrl+C to stop...")
    
    query.awaitTermination()

if __name__ == '__main__':
    main()
