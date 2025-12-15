"""
PySpark Pre-Ingestion Layer
============================
This script implements a complete pre-ingestion pipeline for satellite image data.
It loads CSV feature files, applies MLlib transformations, and outputs processed data.

Requirements:
- Runs in Spark local mode
- Loads 3 CSV files and joins them on image_id
- Applies StringIndexer and OneHotEncoder to vegetation_index
- Builds VectorAssembler for feature engineering
- Applies StandardScaler for normalization
- Saves transformed data as Parquet
- Saves fitted pipeline model
"""

from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, OneHotEncoder, VectorAssembler, StandardScaler
from pyspark.sql.functions import col
import os


def initialize_spark(app_name="SatelliteImagePreIngestion"):
    """
    Initialize Spark session in local mode with HDFS connectivity.
    
    Args:
        app_name: Name of the Spark application
        
    Returns:
        SparkSession object
    """
    spark = SparkSession.builder \
        .appName(app_name) \
        .master("local[*]") \
        .config("spark.driver.memory", "4g") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:8020") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    print(f"✓ Spark session initialized: {app_name}")
    print(f"✓ Spark version: {spark.version}")
    print(f"✓ Running in local mode with HDFS connectivity")
    print(f"✓ HDFS cluster: hdfs://localhost:8020")
    
    return spark


def load_csv_data(spark, metadata_path, ndvi_path, spectral_path, texture_path=None):
    """
    Load the CSV files and optional texture features from HDFS into DataFrames.
    
    Args:
        spark: SparkSession object
        metadata_path: Path to metadata.csv
        ndvi_path: Path to ndvi_stats.csv
        spectral_path: Path to spectral_data.csv
        texture_path: Optional path to texture_features.parquet in HDFS
        
    Returns:
        Tuple of (metadata_df, ndvi_df, spectral_df, texture_df)
    """
    print("\n" + "="*60)
    print("LOADING DATA")
    print("="*60)
    
    # Load metadata.csv
    metadata_df = spark.read.csv(
        metadata_path,
        header=True,
        inferSchema=True
    )
    print(f"✓ Loaded metadata.csv: {metadata_df.count()} records")
    
    # Load ndvi_stats.csv
    ndvi_df = spark.read.csv(
        ndvi_path,
        header=True,
        inferSchema=True
    )
    print(f"✓ Loaded ndvi_stats.csv: {ndvi_df.count()} records")
    
    # Load spectral_data.csv
    spectral_df = spark.read.csv(
        spectral_path,
        header=True,
        inferSchema=True
    )
    print(f"✓ Loaded spectral_data.csv: {spectral_df.count()} records")
    
    # Load texture features from HDFS if path provided
    texture_df = None
    if texture_path:
        print(f"\nLoading texture features from HDFS: {texture_path}")
        texture_df = spark.read.parquet(texture_path)
        print(f"✓ Loaded texture_features.parquet: {texture_df.count()} records")
    
    return metadata_df, ndvi_df, spectral_df, texture_df


def join_dataframes(metadata_df, ndvi_df, spectral_df, texture_df=None):
    """
    Join the DataFrames on image_id column.
    
    Args:
        metadata_df: DataFrame with metadata
        ndvi_df: DataFrame with NDVI statistics
        spectral_df: DataFrame with spectral data
        texture_df: Optional DataFrame with texture features
        
    Returns:
        Joined DataFrame
    """
    print("\n" + "="*60)
    print("JOINING DATAFRAMES")
    print("="*60)
    
    # Join metadata with ndvi_stats
    joined_df = metadata_df.join(ndvi_df, on="image_id", how="inner")
    print(f"✓ Joined metadata + ndvi_stats: {joined_df.count()} records")
    
    # Join with spectral_data
    joined_df = joined_df.join(spectral_df, on="image_id", how="inner")
    print(f"✓ Joined with spectral_data: {joined_df.count()} records")
    
    # Join with texture features if available
    if texture_df is not None:
        joined_df = joined_df.join(texture_df, on="image_id", how="inner")
        print(f"✓ Joined with texture_features: {joined_df.count()} records")
    
    # Verify base required columns are present
    expected_columns = [
        "image_id", "class_id", "vegetation_index",
        "ndvi_mean", "ndvi_std", "ndvi_min", "ndvi_max",
        "red_mean", "green_mean", "blue_mean", "nir_mean", "brightness_mean"
    ]
    
    actual_columns = joined_df.columns
    missing_columns = set(expected_columns) - set(actual_columns)
    
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    print(f"✓ Base required columns present: {len(expected_columns)} columns")
    
    # Show all columns including texture features if joined
    if texture_df is not None:
        texture_cols = [c for c in joined_df.columns if c.startswith(('glcm_', 'lbp_'))]
        if texture_cols:
            print(f"✓ Texture feature columns: {len(texture_cols)} columns")
            print(f"  ({', '.join(texture_cols[:5])}...)")
    
    print(f"✓ Total columns in joined DataFrame: {len(joined_df.columns)}")
    
    return joined_df


def build_pipeline(include_texture=False):
    """
    Build the MLlib Pipeline with all transformation stages.
    
    Pipeline stages:
    1. StringIndexer: vegetation_index → vegetation_index_indexed
    2. OneHotEncoder: vegetation_index_indexed → vegetation_index_encoded
    3. VectorAssembler: numeric features + encoded → raw_features
    4. StandardScaler: raw_features → final_features
    
    Args:
        include_texture: Whether to include texture features in the pipeline
    
    Returns:
        Pipeline object
    """
    print("\n" + "="*60)
    print("BUILDING MLLIB PIPELINE")
    print("="*60)
    
    # Stage 1: StringIndexer for vegetation_index
    indexer = StringIndexer(
        inputCol="vegetation_index",
        outputCol="vegetation_index_indexed",
        handleInvalid="keep"
    )
    print("✓ Stage 1: StringIndexer (vegetation_index → vegetation_index_indexed)")
    
    # Stage 2: OneHotEncoder for indexed vegetation_index
    encoder = OneHotEncoder(
        inputCol="vegetation_index_indexed",
        outputCol="vegetation_index_encoded"
    )
    print("✓ Stage 2: OneHotEncoder (vegetation_index_indexed → vegetation_index_encoded)")
    
    # Stage 3: VectorAssembler to combine all features
    # Base features: NDVI features, spectral features, and encoded vegetation_index
    feature_columns = [
        "ndvi_mean", "ndvi_std", "ndvi_min", "ndvi_max",
        "red_mean", "green_mean", "blue_mean",
        "nir_mean", "brightness_mean",
        "vegetation_index_encoded"
    ]
    
    # Add texture features if requested
    if include_texture:
        texture_columns = [
            "glcm_contrast", "glcm_homogeneity", "glcm_energy",
            "glcm_correlation", "glcm_dissimilarity", "glcm_asm",
            "lbp_hist_0", "lbp_hist_1", "lbp_hist_2", "lbp_hist_3",
            "lbp_hist_4", "lbp_hist_5", "lbp_hist_6", "lbp_hist_7"
        ]
        feature_columns.extend(texture_columns)
        print(f"✓ Including texture features: {len(texture_columns)} columns")
    
    assembler = VectorAssembler(
        inputCols=feature_columns,
        outputCol="raw_features"
    )
    print("✓ Stage 3: VectorAssembler (→ raw_features)")
    print(f"  Total input columns: {len(feature_columns)}")
    
    # Stage 4: StandardScaler for normalization
    scaler = StandardScaler(
        inputCol="raw_features",
        outputCol="final_features",
        withMean=True,
        withStd=True
    )
    print("✓ Stage 4: StandardScaler (raw_features → final_features)")
    
    # Create the pipeline
    pipeline = Pipeline(stages=[indexer, encoder, assembler, scaler])
    print("\n✓ Pipeline created with 4 stages")
    
    return pipeline


def fit_and_transform(pipeline, df):
    """
    Fit the pipeline on the data and transform it.
    
    Args:
        pipeline: MLlib Pipeline object
        df: Input DataFrame
        
    Returns:
        Tuple of (fitted_model, transformed_df)
    """
    print("\n" + "="*60)
    print("FITTING AND TRANSFORMING DATA")
    print("="*60)
    
    # Fit the pipeline
    print("Fitting pipeline...")
    pipeline_model = pipeline.fit(df)
    print("✓ Pipeline fitted successfully")
    
    # Transform the data
    print("Transforming data...")
    transformed_df = pipeline_model.transform(df)
    print("✓ Data transformed successfully")
    
    # Show schema of transformed data
    print("\nTransformed DataFrame Schema:")
    print("-" * 60)
    for field in transformed_df.schema.fields:
        print(f"  {field.name}: {field.dataType}")
    
    return pipeline_model, transformed_df


def save_outputs(transformed_df, pipeline_model, parquet_path, model_path):
    """
    Save the transformed DataFrame and fitted pipeline model.
    
    Args:
        transformed_df: Transformed DataFrame
        pipeline_model: Fitted pipeline model
        parquet_path: Output path for Parquet file
        model_path: Output path for pipeline model
    """
    print("\n" + "="*60)
    print("SAVING OUTPUTS")
    print("="*60)
    
    # Save transformed data as Parquet
    print(f"Saving transformed data to: {parquet_path}")
    transformed_df.write.mode("overwrite").parquet(parquet_path)
    print("✓ Parquet data saved successfully")
    
    # Verify columns in saved Parquet
    saved_columns = transformed_df.columns
    print(f"  Saved columns ({len(saved_columns)}): {', '.join(saved_columns)}")
    
    # Save the fitted pipeline model
    print(f"\nSaving pipeline model to: {model_path}")
    pipeline_model.write().overwrite().save(model_path)
    print("✓ Pipeline model saved successfully")


def display_summary(transformed_df):
    """
    Display summary statistics and sample data.
    
    Args:
        transformed_df: Transformed DataFrame
    """
    print("\n" + "="*60)
    print("DATA SUMMARY")
    print("="*60)
    
    # Show count
    total_records = transformed_df.count()
    print(f"Total records: {total_records}")
    
    # Show sample records
    print("\nSample records (first 5):")
    print("-" * 60)
    transformed_df.select(
        "image_id", "class_id", "vegetation_index",
        "vegetation_index_indexed", "ndvi_mean", "red_mean"
    ).show(5, truncate=False)
    
    # Show feature vector info
    print("\nFeature vectors:")
    print("-" * 60)
    transformed_df.select("image_id", "raw_features", "final_features").show(3, truncate=True)


def main():
    """
    Main execution function for the pre-ingestion pipeline.
    """
    print("\n" + "="*60)
    print("SATELLITE IMAGE PRE-INGESTION PIPELINE")
    print("="*60)
    print("Running in Spark local mode")
    print("Processing CSV-based features only (no image files)")
    print("="*60)
    
    # Configuration
    # Use file:// prefix for local files when HDFS is the default filesystem
    import os
    current_dir = os.getcwd()
    METADATA_PATH = f"file://{current_dir}/data/metadata.csv"
    NDVI_PATH = f"file://{current_dir}/data/ndvi_stats.csv"
    SPECTRAL_PATH = f"file://{current_dir}/data/spectral_data.csv"
    TEXTURE_PATH = "hdfs://localhost:8020/data/processed/texture/texture_features.parquet"
    PARQUET_OUTPUT = "hdfs://localhost:8020/data/processed/processed_images.parquet"
    MODEL_OUTPUT = f"file://{current_dir}/pre_ingestion_pipeline_model"
    
    # Set to True to include texture features from HDFS
    # NOTE: Texture features must have matching image_ids with CSV data
    # Current CSV sample data uses IMG_001, IMG_002, etc.
    # Texture features use SeaLake_XXXX format
    # Set to False if image_ids don't match
    INCLUDE_TEXTURE = False  # Changed to False due to image_id mismatch
    
    try:
        # Step 1: Initialize Spark
        spark = initialize_spark()
        
        # Step 2: Load CSV data and texture features
        metadata_df, ndvi_df, spectral_df, texture_df = load_csv_data(
            spark, METADATA_PATH, NDVI_PATH, SPECTRAL_PATH,
            TEXTURE_PATH if INCLUDE_TEXTURE else None
        )
        
        # Step 3: Join DataFrames
        joined_df = join_dataframes(metadata_df, ndvi_df, spectral_df, texture_df)
        
        # Step 4: Build MLlib Pipeline
        pipeline = build_pipeline(include_texture=INCLUDE_TEXTURE)
        
        # Step 5: Fit and transform data
        pipeline_model, transformed_df = fit_and_transform(pipeline, joined_df)
        
        # Step 6: Save outputs
        save_outputs(transformed_df, pipeline_model, PARQUET_OUTPUT, MODEL_OUTPUT)
        
        # Step 7: Display summary
        display_summary(transformed_df)
        
        print("\n" + "="*60)
        print("PIPELINE EXECUTION COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"✓ Transformed data saved to: {PARQUET_OUTPUT}")
        print(f"✓ Pipeline model saved to: {MODEL_OUTPUT}")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        raise
    
    finally:
        # Stop Spark session
        if 'spark' in locals():
            spark.stop()
            print("✓ Spark session stopped")


if __name__ == "__main__":
    main()
