#!/usr/bin/env python3
"""
Script to verify processed_images.parquet from HDFS
"""

from pyspark.sql import SparkSession

# Initialize Spark with HDFS connection
spark = SparkSession.builder \
    .appName("VerifyHDFSOutput") \
    .master("local[*]") \
    .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:8020") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# Read the processed data from HDFS
hdfs_path = "hdfs://localhost:8020/data/processed/processed_images.parquet"

print("\n" + "="*60)
print("PROCESSED IMAGES VERIFICATION (FROM HDFS)")
print("="*60)
print(f"Reading from: {hdfs_path}\n")

df = spark.read.parquet(hdfs_path)

# Show schema
print("Schema:")
print("-" * 60)
df.printSchema()

# Show total count
total = df.count()
print(f"\nTotal records: {total}")

# Show all columns
print(f"\nColumns ({len(df.columns)}):")
print("-" * 60)
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")

# Show first 10 rows (basic columns)
print("\nSample Data (basic columns):")
print("-" * 60)
df.select("image_id", "class_id", "vegetation_index", 
          "vegetation_index_indexed", "ndvi_mean", "red_mean").show(10, truncate=False)

# Show feature vectors
print("\nFeature Vectors:")
print("-" * 60)
df.select("image_id", "raw_features", "final_features").show(5, truncate=True)

# Statistics on numeric columns
print("\nNumeric Feature Statistics:")
print("-" * 60)
df.select("ndvi_mean", "ndvi_std", "ndvi_min", "ndvi_max",
          "red_mean", "green_mean", "blue_mean").describe().show()

print("="*60)
print("VERIFICATION COMPLETE")
print("="*60 + "\n")

spark.stop()
