"""
Multimodal Spark Streaming Job
Processes both tabular (CSV) and image (RGB) features in real-time
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Define multimodal schema
multimodal_schema = StructType([
    StructField("image_id", StringType()),
    StructField("class_name", StringType()),
    StructField("class_id", IntegerType()),
    StructField("timestamp", StringType()),
    
    # Tabular: NDVI features
    StructField("ndvi_mean", DoubleType()),
    StructField("ndvi_std", DoubleType()),
    StructField("ndvi_min", DoubleType()),
    StructField("ndvi_max", DoubleType()),
    
    # Tabular: Spectral bands
    StructField("red_mean", DoubleType()),
    StructField("green_mean", DoubleType()),
    StructField("blue_mean", DoubleType()),
    StructField("nir_mean", DoubleType()),
    StructField("brightness_mean", DoubleType()),
    
    # Image metadata
    StructField("image_filename", StringType()),
    StructField("width", IntegerType()),
    StructField("height", IntegerType()),
    StructField("vegetation_index", StringType()),
    StructField("has_image", BooleanType()),
    StructField("image_path", StringType()),
    
    # Image: RGB features
    StructField("rgb_features", StructType([
        StructField("rgb_mean", ArrayType(DoubleType())),  # [R, G, B] means
        StructField("rgb_std", ArrayType(DoubleType())),   # [R, G, B] std devs
        StructField("rgb_min", ArrayType(DoubleType())),
        StructField("rgb_max", ArrayType(DoubleType())),
        StructField("brightness", DoubleType()),
        StructField("contrast", DoubleType()),
    ]))
])

def update_cumulative_totals(spark, batch_df):
    """Update cumulative event totals by reading existing counts from Cassandra"""
    try:
        # Read existing totals from Cassandra
        existing_totals = spark.read \
            .format("org.apache.spark.sql.cassandra") \
            .options(table="multimodal_event_totals", keyspace="landcover") \
            .load()
        
        # Calculate new batch counts
        new_counts = batch_df.groupBy("class_name").agg(
            count("*").alias("new_events"),
            sum(when(col("has_image") == True, 1).otherwise(0)).alias("new_images")
        )
        
        # Join and sum up totals
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
        
        # Write back to Cassandra (overwrites with new totals)
        updated.write \
            .format("org.apache.spark.sql.cassandra") \
            .mode("append") \
            .options(table="multimodal_event_totals", keyspace="landcover") \
            .save()
            
        return updated.count()
    except Exception as e:
        print(f"⚠ Could not update cumulative totals: {e}")
        # First time - just write initial counts
        initial_counts = batch_df.groupBy("class_name").agg(
            count("*").alias("total_events"),
            sum(when(col("has_image") == True, 1).otherwise(0)).alias("total_images")
        ).withColumn("first_seen", current_timestamp()) \
         .withColumn("last_updated", current_timestamp())
        
        initial_counts.write \
            .format("org.apache.spark.sql.cassandra") \
            .mode("append") \
            .options(table="multimodal_event_totals", keyspace="landcover") \
            .save()
        return initial_counts.count()

def process_multimodal_batch(batch_df, batch_id):
    """Process multimodal batch combining tabular and image features"""
    if batch_df.count() == 0:
        return
    
    print(f"\n{'='*80}")
    print(f"Processing Multimodal Batch {batch_id}")
    print(f"{'='*80}")
    
    # 1. Tabular Analytics: NDVI aggregation by class
    # Note: sample_count represents events in current batch
    # For cumulative totals, query multimodal_event_totals table
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
    
    # Write tabular aggregates
    tabular_agg.write \
        .format("org.apache.spark.sql.cassandra") \
        .mode("append") \
        .options(table="multimodal_tabular_stats", keyspace="landcover") \
        .save()
    
    print(f"✓ Tabular features aggregated ({tabular_agg.count()} classes)")
    
    # 1b. Update cumulative event totals
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()
    total_classes = update_cumulative_totals(spark, batch_df)
    print(f"✓ Cumulative totals updated ({total_classes} classes)")
    
    # 2. Image Analytics: RGB feature aggregation
    image_df = batch_df.filter(col("has_image") == True)
    
    if image_df.count() > 0:
        # Extract RGB channel means
        image_agg = image_df.withColumn("r_mean", col("rgb_features.rgb_mean")[0]) \
                            .withColumn("g_mean", col("rgb_features.rgb_mean")[1]) \
                            .withColumn("b_mean", col("rgb_features.rgb_mean")[2]) \
                            .withColumn("brightness", col("rgb_features.brightness")) \
                            .withColumn("contrast", col("rgb_features.contrast"))
        
        # Aggregate by class
        rgb_stats = image_agg.groupBy("class_name").agg(
            avg("r_mean").alias("avg_red_channel"),
            avg("g_mean").alias("avg_green_channel"),
            avg("b_mean").alias("avg_blue_channel"),
            avg("brightness").alias("avg_brightness"),
            avg("contrast").alias("avg_contrast"),
            count("*").alias("image_count")
        )
        
        # Add timestamp
        rgb_stats = rgb_stats.withColumn("last_updated", current_timestamp())
        
        # Write image aggregates
        rgb_stats.write \
            .format("org.apache.spark.sql.cassandra") \
            .mode("append") \
            .options(table="multimodal_image_stats", keyspace="landcover") \
            .save()
        
        print(f"✓ Image features aggregated ({rgb_stats.count()} classes)")
    
    # 3. Multimodal Fusion: Detect anomalies using both modalities
    # Anomaly = unusual NDVI + unusual brightness combination
    multimodal_df = batch_df.filter(col("has_image") == True)
    
    if multimodal_df.count() > 0:
        # Compute global statistics
        stats = multimodal_df.agg(
            avg("ndvi_mean").alias("global_ndvi_mean"),
            stddev("ndvi_mean").alias("global_ndvi_std"),
            avg("rgb_features.brightness").alias("global_brightness_mean"),
            stddev("rgb_features.brightness").alias("global_brightness_std")
        ).collect()[0]
        
        # Detect multimodal anomalies (outliers in both NDVI and brightness)
        anomalies = multimodal_df.filter(
            (abs(col("ndvi_mean") - lit(stats["global_ndvi_mean"])) > 2 * lit(stats["global_ndvi_std"])) |
            (abs(col("rgb_features.brightness") - lit(stats["global_brightness_mean"])) > 2 * lit(stats["global_brightness_std"]))
        ).select(
            "image_id",
            "class_name",
            "ndvi_mean",
            "ndvi_min",
            "ndvi_max",
            col("rgb_features.brightness").alias("brightness"),
            col("rgb_features.contrast").alias("contrast"),
            to_timestamp(col("timestamp")).alias("timestamp"),
            lit("multimodal").alias("anomaly_type")
        )
        
        if anomalies.count() > 0:
            # Write multimodal anomalies
            anomalies.write \
                .format("org.apache.spark.sql.cassandra") \
                .mode("append") \
                .options(table="multimodal_anomalies", keyspace="landcover") \
                .save()
            
            print(f"✓ Multimodal anomalies detected: {anomalies.count()}")
    
    print(f"{'='*80}\n")

def main():
    print("\n" + "="*80)
    print("MULTIMODAL SPARK STREAMING JOB")
    print("Processing: Tabular (CSV) + Image (RGB) data")
    print("="*80 + "\n")
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("MultimodalStreaming") \
        .config("spark.cassandra.connection.host", "cassandra") \
        .config("spark.cassandra.connection.port", "9042") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # Read from Kafka
    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9092") \
        .option("subscribe", "multimodal-events") \
        .option("startingOffsets", "latest") \
        .load()
    
    # Parse JSON with multimodal schema
    parsed_df = df.select(
        from_json(col("value").cast("string"), multimodal_schema).alias("data")
    ).select("data.*")
    
    # Process with foreachBatch for multimodal analytics
    query = parsed_df.writeStream \
        .foreachBatch(process_multimodal_batch) \
        .outputMode("update") \
        .trigger(processingTime='15 seconds') \
        .option("checkpointLocation", "/tmp/spark_multimodal_ckpt") \
        .start()
    
    print("✓ Multimodal streaming job started")
    print("  - Listening to topic: multimodal-events")
    print("  - Processing both tabular and image features")
    print("  - Writing to 3 Cassandra tables")
    print("\nPress Ctrl+C to stop...")
    
    query.awaitTermination()

if __name__ == '__main__':
    main()
