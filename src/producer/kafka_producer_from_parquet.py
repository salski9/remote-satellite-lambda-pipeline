#!/usr/bin/env python3
"""
Simplified Kafka Producer - Reads from Pre-Ingestion Parquet Files
No CSV loading, no feature extraction - just read and stream!
"""

from pyspark.sql import SparkSession
from kafka import KafkaProducer
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Class name mapping (land cover classes)
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
    """Initialize Spark session with HDFS configuration"""
    logger.info("Initializing Spark session...")
    
    spark = SparkSession.builder \
        .appName("ParquetToKafkaProducer") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:8020") \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    logger.info("Spark session created successfully")
    return spark

def read_parquet_files(spark):
    """Read processed images and texture features from HDFS"""
    logger.info("Reading Parquet files from HDFS...")
    
    # Read processed images (CSV features + ML vectors)
    processed_path = "hdfs://localhost:8020/data/processed/processed_images.parquet"
    logger.info(f"Reading: {processed_path}")
    processed_df = spark.read.parquet(processed_path)
    logger.info(f"Loaded {processed_df.count()} processed images")
    
    # Read texture features (GLCM + LBP)
    texture_path = "hdfs://localhost:8020/data/processed/texture/texture_features.parquet"
    logger.info(f"Reading: {texture_path}")
    texture_df = spark.read.parquet(texture_path)
    logger.info(f"Loaded {texture_df.count()} texture feature records")
    
    return processed_df, texture_df

def join_dataframes(processed_df, texture_df):
    """Join processed images with texture features on image_id"""
    logger.info("Joining DataFrames on image_id...")
    
    # LEFT JOIN to keep all processed images even if texture is missing
    enriched_df = processed_df.join(
        texture_df,
        on="image_id",
        how="left"
    )
    
    total_records = enriched_df.count()
    logger.info(f"Joined DataFrame contains {total_records} records")
    
    return enriched_df

def vector_to_list(vector):
    """Convert Spark DenseVector to Python list"""
    if vector is None:
        return None
    try:
        return vector.toArray().tolist()
    except:
        return None

def safe_get(row_dict, key, default=None):
    """Safely get value from row dictionary"""
    return row_dict.get(key, default)

def create_event(row):
    """Convert Spark Row to Kafka event dictionary"""
    try:
        # Convert Row to dict for easier access
        row_dict = row.asDict()
        
        # Get class name from class_id
        class_id = row_dict.get('class_id', 0)
        class_name = CLASS_NAMES.get(class_id, f"Unknown_{class_id}")
        
        event = {
            # Metadata
            'image_id': row_dict.get('image_id', ''),
            'image_filename': row_dict.get('image_filename', ''),
            'class_id': int(class_id) if class_id is not None else 0,
            'class_name': class_name,
            'timestamp': datetime.utcnow().isoformat(),
            
            # NDVI features (from CSV)
            'ndvi_mean': float(row_dict['ndvi_mean']) if row_dict.get('ndvi_mean') is not None else None,
            'ndvi_std': float(row_dict['ndvi_std']) if row_dict.get('ndvi_std') is not None else None,
            'ndvi_min': float(row_dict['ndvi_min']) if row_dict.get('ndvi_min') is not None else None,
            'ndvi_max': float(row_dict['ndvi_max']) if row_dict.get('ndvi_max') is not None else None,
            
            # Spectral features (from CSV)
            'red_mean': float(row_dict['red_mean']) if row_dict.get('red_mean') is not None else None,
            'green_mean': float(row_dict['green_mean']) if row_dict.get('green_mean') is not None else None,
            'blue_mean': float(row_dict['blue_mean']) if row_dict.get('blue_mean') is not None else None,
            'nir_mean': float(row_dict['nir_mean']) if row_dict.get('nir_mean') is not None else None,
            'brightness_mean': float(row_dict['brightness_mean']) if row_dict.get('brightness_mean') is not None else None,
            
            # Encoded features (from MLlib)
            'vegetation_index': row_dict.get('vegetation_index', ''),
            'vegetation_index_indexed': float(row_dict['vegetation_index_indexed']) if row_dict.get('vegetation_index_indexed') is not None else None,
            'vegetation_index_encoded': vector_to_list(row_dict.get('vegetation_index_encoded')),
            
            # ML-ready vectors (PRE-NORMALIZED!)
            'raw_features': vector_to_list(row_dict.get('raw_features')),
            'final_features': vector_to_list(row_dict.get('final_features')),
            
            # Texture features - GLCM
            'glcm_contrast': float(row_dict['glcm_contrast']) if row_dict.get('glcm_contrast') is not None else None,
            'glcm_homogeneity': float(row_dict['glcm_homogeneity']) if row_dict.get('glcm_homogeneity') is not None else None,
            'glcm_energy': float(row_dict['glcm_energy']) if row_dict.get('glcm_energy') is not None else None,
            'glcm_correlation': float(row_dict['glcm_correlation']) if row_dict.get('glcm_correlation') is not None else None,
            'glcm_dissimilarity': float(row_dict['glcm_dissimilarity']) if row_dict.get('glcm_dissimilarity') is not None else None,
            'glcm_asm': float(row_dict['glcm_asm']) if row_dict.get('glcm_asm') is not None else None,
            
            # Texture features - LBP histogram
            'lbp_hist_0': float(row_dict['lbp_hist_0']) if row_dict.get('lbp_hist_0') is not None else None,
            'lbp_hist_1': float(row_dict['lbp_hist_1']) if row_dict.get('lbp_hist_1') is not None else None,
            'lbp_hist_2': float(row_dict['lbp_hist_2']) if row_dict.get('lbp_hist_2') is not None else None,
            'lbp_hist_3': float(row_dict['lbp_hist_3']) if row_dict.get('lbp_hist_3') is not None else None,
            'lbp_hist_4': float(row_dict['lbp_hist_4']) if row_dict.get('lbp_hist_4') is not None else None,
            'lbp_hist_5': float(row_dict['lbp_hist_5']) if row_dict.get('lbp_hist_5') is not None else None,
            'lbp_hist_6': float(row_dict['lbp_hist_6']) if row_dict.get('lbp_hist_6') is not None else None,
            'lbp_hist_7': float(row_dict['lbp_hist_7']) if row_dict.get('lbp_hist_7') is not None else None,
        }
        
        return event
        
    except Exception as e:
        try:
            row_dict = row.asDict() if hasattr(row, 'asDict') else {}
            image_id = row_dict.get('image_id', 'unknown')
        except:
            image_id = 'unknown'
        logger.error(f"Error creating event for image_id {image_id}: {e}")
        return None

def stream_to_kafka(enriched_df, kafka_servers='localhost:29092', topic='enhanced-multimodal-events'):
    """Stream enriched events to Kafka"""
    logger.info(f"Connecting to Kafka at {kafka_servers}...")
    
    # Create Kafka producer
    producer = KafkaProducer(
        bootstrap_servers=[kafka_servers],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        compression_type='gzip',
        batch_size=16384,
        linger_ms=10
    )
    
    logger.info(f"Streaming events to Kafka topic: {topic}")
    
    # Collect and send events
    rows = enriched_df.collect()
    total_events = len(rows)
    sent_count = 0
    error_count = 0
    
    for idx, row in enumerate(rows, 1):
        # Create event
        event = create_event(row)
        
        if event:
            try:
                # Send to Kafka
                producer.send(topic, value=event)
                sent_count += 1
                
                # Log progress every 1000 events
                if idx % 1000 == 0:
                    logger.info(f"Progress: {idx}/{total_events} events sent ({idx/total_events*100:.1f}%)")
                    
            except Exception as e:
                logger.error(f"Error sending event {idx}: {e}")
                error_count += 1
        else:
            error_count += 1
    
    # Flush and close
    logger.info("Flushing remaining messages...")
    producer.flush()
    producer.close()
    
    logger.info(f"""
    ========================================
    STREAMING COMPLETE
    ========================================
    Total records: {total_events}
    Successfully sent: {sent_count}
    Errors: {error_count}
    Success rate: {sent_count/total_events*100:.1f}%
    ========================================
    """)

def main():
    """Main execution function"""
    try:
        # 1. Create Spark session
        spark = create_spark_session()
        
        # 2. Read Parquet files from HDFS
        processed_df, texture_df = read_parquet_files(spark)
        
        # 3. Join DataFrames
        enriched_df = join_dataframes(processed_df, texture_df)
        
        # 4. Stream to Kafka
        stream_to_kafka(enriched_df)
        
        # 5. Cleanup
        spark.stop()
        logger.info("Spark session stopped. Producer finished successfully!")
        
    except Exception as e:
        logger.error(f"Producer failed with error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
