#!/usr/bin/env python3
"""
============================================================
TEXTURE FEATURE EXTRACTION BATCH JOB
============================================================
This PySpark script extracts texture features from RGB JPG images
stored in HDFS and outputs a Parquet file for downstream processing.

Features Extracted:
- GLCM (Gray-Level Co-occurrence Matrix) features
- LBP (Local Binary Patterns) histogram

Author: Data Engineering Team
============================================================
"""

import io
import numpy as np
from PIL import Image
from typing import Optional, Tuple

from pyspark.sql import SparkSession
from pyspark.sql.functions import regexp_extract, col, udf
from pyspark.sql.types import (
    StructType, StructField, FloatType, StringType
)

# Import scikit-image for texture analysis
from skimage.feature import graycomatrix, graycoprops, local_binary_pattern


# ============================================================
# TEXTURE FEATURE EXTRACTION FUNCTIONS
# ============================================================

def extract_texture_features(image_bytes: bytes) -> Optional[dict]:
    """
    Extract GLCM and LBP texture features from a JPG image.
    
    Args:
        image_bytes: Raw bytes of the JPG image
        
    Returns:
        Dictionary containing 14 texture features, or None if processing fails
    """
    try:
        # Step 1: Decode JPG bytes to PIL Image
        img = Image.open(io.BytesIO(image_bytes))
        
        # Step 2: Convert to grayscale
        if img.mode != 'L':
            img = img.convert('L')
        
        # Step 3: Convert to numpy array
        gray_array = np.array(img)
        
        # Step 4: Quantize to 16 gray levels for GLCM computation
        # This reduces computational complexity while preserving texture information
        quantized = (gray_array // 16).astype(np.uint8)
        
        # --------------------------------------------------------
        # GLCM Feature Extraction
        # --------------------------------------------------------
        # Compute Gray-Level Co-occurrence Matrix
        # distances: [1] - consider adjacent pixels
        # angles: [0] - horizontal direction (0 degrees)
        # levels: 16 - number of gray levels after quantization
        # symmetric: True - make matrix symmetric
        # normed: True - normalize the matrix
        glcm = graycomatrix(
            quantized,
            distances=[1],
            angles=[0],
            levels=16,
            symmetric=True,
            normed=True
        )
        
        # Extract GLCM properties
        glcm_contrast = float(graycoprops(glcm, 'contrast')[0, 0])
        glcm_homogeneity = float(graycoprops(glcm, 'homogeneity')[0, 0])
        glcm_energy = float(graycoprops(glcm, 'energy')[0, 0])
        glcm_correlation = float(graycoprops(glcm, 'correlation')[0, 0])
        glcm_dissimilarity = float(graycoprops(glcm, 'dissimilarity')[0, 0])
        glcm_asm = float(graycoprops(glcm, 'ASM')[0, 0])  # Angular Second Moment
        
        # --------------------------------------------------------
        # LBP Feature Extraction
        # --------------------------------------------------------
        # Compute Local Binary Patterns
        # P: number of circularly symmetric neighbor points (8)
        # R: radius of circle (1)
        # method: 'uniform' - only uniform patterns
        lbp = local_binary_pattern(
            gray_array,
            P=8,
            R=1,
            method='uniform'
        )
        
        # Compute normalized histogram with 8 bins
        # The uniform LBP with P=8 produces patterns in range [0, 9]
        # We create 8 bins to capture the distribution
        hist, _ = np.histogram(
            lbp.ravel(),
            bins=8,
            range=(0, 8),
            density=True  # Normalize to get probabilities
        )
        
        # Ensure histogram values are floats
        lbp_hist = [float(h) for h in hist]
        
        # --------------------------------------------------------
        # Return all features as a dictionary
        # --------------------------------------------------------
        return {
            'glcm_contrast': glcm_contrast,
            'glcm_homogeneity': glcm_homogeneity,
            'glcm_energy': glcm_energy,
            'glcm_correlation': glcm_correlation,
            'glcm_dissimilarity': glcm_dissimilarity,
            'glcm_asm': glcm_asm,
            'lbp_hist_0': lbp_hist[0],
            'lbp_hist_1': lbp_hist[1],
            'lbp_hist_2': lbp_hist[2],
            'lbp_hist_3': lbp_hist[3],
            'lbp_hist_4': lbp_hist[4],
            'lbp_hist_5': lbp_hist[5],
            'lbp_hist_6': lbp_hist[6],
            'lbp_hist_7': lbp_hist[7]
        }
        
    except Exception as e:
        # Handle corrupted or unreadable images
        print(f"Error processing image: {str(e)}")
        return None


# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    """
    Main execution function for texture feature extraction pipeline.
    """
    
    print("\n" + "="*60)
    print("TEXTURE FEATURE EXTRACTION BATCH JOB")
    print("="*60)
    print("Reading JPG images from HDFS")
    print("Extracting GLCM and LBP texture features")
    print("="*60 + "\n")
    
    # --------------------------------------------------------
    # Step 1: Initialize Spark Session with HDFS Configuration
    # --------------------------------------------------------
    print("✓ Initializing Spark session with HDFS connection...")
    
    spark = SparkSession.builder \
        .appName("TextureExtractionJPG") \
        .master("local[*]") \
        .config("spark.driver.memory", "4g") \
        .config("spark.executor.memory", "4g") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:8020") \
        .getOrCreate()
    
    # Set log level to reduce verbosity
    spark.sparkContext.setLogLevel("WARN")
    
    print(f"✓ Spark version: {spark.version}")
    print(f"✓ Connected to HDFS: hdfs://localhost:8020\n")
    
    # --------------------------------------------------------
    # Step 2: Read JPG Images from HDFS
    # --------------------------------------------------------
    hdfs_input_path = "hdfs://localhost:8020/data/raw/images/jpg/*"
    print(f"Reading JPG images from: {hdfs_input_path}")
    
    try:
        # Read binary files (JPG images) from HDFS
        images_df = spark.read.format("binaryFile").load(hdfs_input_path)
        
        total_images = images_df.count()
        print(f"✓ Found {total_images} JPG images in HDFS\n")
        
    except Exception as e:
        print(f"✗ Error reading images from HDFS: {str(e)}")
        spark.stop()
        return
    
    # --------------------------------------------------------
    # Step 3: Extract image_id from file path
    # --------------------------------------------------------
    print("Extracting image_id from filenames...")
    
    # Use regex to extract image_id pattern (e.g., "AnnualCrop_1.jpg" -> "AnnualCrop_1")
    # Pattern matches: CategoryName_Number.jpg
    images_df = images_df.withColumn(
        "image_id",
        regexp_extract(col("path"), r"([^/]+)\.jpg$", 1)
    )
    
    # Filter out rows where image_id extraction failed
    images_df = images_df.filter(col("image_id") != "")
    
    print(f"✓ Successfully extracted image_id for {images_df.count()} images\n")
    
    # --------------------------------------------------------
    # Step 4: Define UDF Schema for Texture Features
    # --------------------------------------------------------
    print("Setting up texture feature extraction UDF...")
    
    # Define the schema for the UDF return type
    texture_schema = StructType([
        StructField("glcm_contrast", FloatType(), True),
        StructField("glcm_homogeneity", FloatType(), True),
        StructField("glcm_energy", FloatType(), True),
        StructField("glcm_correlation", FloatType(), True),
        StructField("glcm_dissimilarity", FloatType(), True),
        StructField("glcm_asm", FloatType(), True),
        StructField("lbp_hist_0", FloatType(), True),
        StructField("lbp_hist_1", FloatType(), True),
        StructField("lbp_hist_2", FloatType(), True),
        StructField("lbp_hist_3", FloatType(), True),
        StructField("lbp_hist_4", FloatType(), True),
        StructField("lbp_hist_5", FloatType(), True),
        StructField("lbp_hist_6", FloatType(), True),
        StructField("lbp_hist_7", FloatType(), True)
    ])
    
    # Register the UDF
    extract_features_udf = udf(extract_texture_features, texture_schema)
    
    print("✓ Texture extraction UDF registered\n")
    
    # --------------------------------------------------------
    # Step 5: Apply UDF to Extract Texture Features
    # --------------------------------------------------------
    print("Extracting texture features from images...")
    print("(This may take several minutes depending on dataset size)\n")
    
    # Apply the UDF to the 'content' column (image bytes)
    features_df = images_df.withColumn(
        "features",
        extract_features_udf(col("content"))
    )
    
    # --------------------------------------------------------
    # Step 6: Expand Features and Select Final Columns
    # --------------------------------------------------------
    print("Expanding feature columns...")
    
    # Expand the struct into individual columns
    final_df = features_df.select(
        col("image_id"),
        col("features.glcm_contrast").alias("glcm_contrast"),
        col("features.glcm_homogeneity").alias("glcm_homogeneity"),
        col("features.glcm_energy").alias("glcm_energy"),
        col("features.glcm_correlation").alias("glcm_correlation"),
        col("features.glcm_dissimilarity").alias("glcm_dissimilarity"),
        col("features.glcm_asm").alias("glcm_asm"),
        col("features.lbp_hist_0").alias("lbp_hist_0"),
        col("features.lbp_hist_1").alias("lbp_hist_1"),
        col("features.lbp_hist_2").alias("lbp_hist_2"),
        col("features.lbp_hist_3").alias("lbp_hist_3"),
        col("features.lbp_hist_4").alias("lbp_hist_4"),
        col("features.lbp_hist_5").alias("lbp_hist_5"),
        col("features.lbp_hist_6").alias("lbp_hist_6"),
        col("features.lbp_hist_7").alias("lbp_hist_7")
    )
    
    # --------------------------------------------------------
    # Step 7: Filter Out Failed Extractions
    # --------------------------------------------------------
    print("Filtering out corrupted or unreadable images...")
    
    # Remove rows where feature extraction failed (all nulls)
    final_df = final_df.filter(col("glcm_contrast").isNotNull())
    
    successful_count = final_df.count()
    failed_count = total_images - successful_count
    
    print(f"✓ Successfully processed: {successful_count} images")
    if failed_count > 0:
        print(f"✗ Failed to process: {failed_count} images\n")
    else:
        print()
    
    # --------------------------------------------------------
    # Step 8: Display Sample Results
    # --------------------------------------------------------
    print("Sample texture features (first 5 rows):")
    print("-" * 60)
    final_df.show(5, truncate=False)
    
    # Display schema
    print("\nOutput Schema:")
    print("-" * 60)
    final_df.printSchema()
    
    # --------------------------------------------------------
    # Step 9: Write Results to HDFS as Parquet
    # --------------------------------------------------------
    hdfs_output_path = "hdfs://localhost:8020/data/processed/texture/texture_features.parquet"
    
    print(f"\nWriting results to HDFS: {hdfs_output_path}")
    
    try:
        final_df.write \
            .mode("overwrite") \
            .parquet(hdfs_output_path)
        
        print("✓ Texture features successfully written to HDFS\n")
        
    except Exception as e:
        print(f"✗ Error writing to HDFS: {str(e)}\n")
        spark.stop()
        return
    
    # --------------------------------------------------------
    # Step 10: Summary Statistics
    # --------------------------------------------------------
    print("="*60)
    print("BATCH JOB COMPLETED SUCCESSFULLY")
    print("="*60)
    print(f"Total images processed: {successful_count}")
    print(f"Output location: {hdfs_output_path}")
    print(f"Output schema: 15 columns (1 ID + 14 texture features)")
    print("="*60 + "\n")
    
    # Stop Spark session
    spark.stop()
    print("✓ Spark session stopped\n")


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
