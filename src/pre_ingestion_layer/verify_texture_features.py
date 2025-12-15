#!/usr/bin/env python3
"""
Script to verify texture features Parquet file from HDFS
"""

from pyspark.sql import SparkSession

# Initialize Spark with HDFS connection
spark = SparkSession.builder \
    .appName("VerifyTextureFeatures") \
    .master("local[*]") \
    .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:8020") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# Read the texture features from HDFS
hdfs_path = "hdfs://localhost:8020/data/processed/texture/texture_features.parquet"

print("\n" + "="*60)
print("TEXTURE FEATURES VERIFICATION")
print("="*60)
print(f"Reading from: {hdfs_path}\n")

df = spark.read.parquet(hdfs_path)

# Show schema
print("Schema:")
print("-" * 60)
df.printSchema()

# Show total count
total = df.count()
print(f"\nTotal records: {total:,}")

# Show first 10 rows
print("\nFirst 10 rows:")
print("-" * 60)
df.show(10, truncate=False)

# Show statistics for GLCM features
print("\nGLCM Feature Statistics:")
print("-" * 60)
df.select("glcm_contrast", "glcm_homogeneity", "glcm_energy", 
          "glcm_correlation", "glcm_dissimilarity", "glcm_asm").describe().show()

# Show statistics for LBP histogram
print("\nLBP Histogram Statistics:")
print("-" * 60)
df.select("lbp_hist_0", "lbp_hist_1", "lbp_hist_2", "lbp_hist_3",
          "lbp_hist_4", "lbp_hist_5", "lbp_hist_6", "lbp_hist_7").describe().show()

# Check for nulls
print("\nNull Count Check:")
print("-" * 60)
null_counts = df.select([
    df[c].isNull().cast("int").alias(c) for c in df.columns
]).groupBy().sum()
null_counts.show()

print("="*60)
print("VERIFICATION COMPLETE")
print("="*60 + "\n")

spark.stop()
