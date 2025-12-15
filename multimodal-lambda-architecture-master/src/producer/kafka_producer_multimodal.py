"""
Multimodal Kafka Producer
Combines CSV metadata with RGB image features for true multimodal processing
"""
import os
import json
import time
import argparse
import pandas as pd
import numpy as np
from kafka import KafkaProducer
from PIL import Image
from pathlib import Path

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RGB_DIR = os.path.join(DATA_DIR, "EuroSAT_RGB")

def extract_image_features(image_path):
    """Extract RGB features from image"""
    try:
        img = Image.open(image_path)
        img_array = np.array(img)
        
        # Extract color statistics per channel
        features = {
            'rgb_mean': img_array.mean(axis=(0, 1)).tolist(),  # [R_mean, G_mean, B_mean]
            'rgb_std': img_array.std(axis=(0, 1)).tolist(),    # [R_std, G_std, B_std]
            'rgb_min': img_array.min(axis=(0, 1)).tolist(),
            'rgb_max': img_array.max(axis=(0, 1)).tolist(),
            'brightness': float(img_array.mean()),
            'contrast': float(img_array.std()),
        }
        return features
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return None

def find_matching_image(class_name, image_id):
    """Find RGB image file for given class and image_id"""
    class_dir = os.path.join(RGB_DIR, class_name.replace(" ", ""))
    if not os.path.exists(class_dir):
        return None
    
    # Try to match by image_id pattern
    # CSV has IMG_000001, images are like AnnualCrop_1000.jpg
    # Extract numeric part from image_id
    try:
        id_num = int(image_id.split('_')[1])
    except:
        return None
    
    # Look for matching file
    for filename in os.listdir(class_dir):
        if filename.endswith('.jpg'):
            # Try to extract number from filename
            try:
                file_num = int(filename.split('_')[1].split('.')[0])
                # If numbers match (or close match), use this image
                if abs(file_num - id_num) < 100:  # Allow some tolerance
                    return os.path.join(class_dir, filename)
            except:
                continue
    
    # Fallback: return first image in class
    jpg_files = [f for f in os.listdir(class_dir) if f.endswith('.jpg')]
    if jpg_files:
        return os.path.join(class_dir, jpg_files[0])
    
    return None

def produce_multimodal_events(limit=500, delay=0.01, topic='multimodal-events'):
    """Produce multimodal events combining CSV data + RGB image features"""
    
    # Load CSV data
    print("Loading CSV data...")
    ndvi_df = pd.read_csv(os.path.join(DATA_DIR, 'ndvi_stats.csv'))
    spectral_df = pd.read_csv(os.path.join(DATA_DIR, 'spectral_data.csv'))
    images_df = pd.read_csv(os.path.join(DATA_DIR, 'images.csv'))
    classes_df = pd.read_csv(os.path.join(DATA_DIR, 'classes.csv'))
    
    # Merge data
    print("Merging datasets...")
    df = ndvi_df.merge(spectral_df, on='image_id', how='left')
    df = df.merge(images_df, on='image_id', how='left')
    df = df.merge(classes_df, on='class_id', how='left')
    
    # Shuffle to get diverse classes (data is sorted by class)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Limit dataset
    df = df.head(limit)
    
    print(f"Processing {len(df)} multimodal samples...")
    
    # Initialize Kafka producer
    producer = KafkaProducer(
        bootstrap_servers=['localhost:29092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    processed = 0
    failed = 0
    
    for idx, row in df.iterrows():
        try:
            # Base event from CSV
            event = {
                'image_id': row['image_id'],
                'class_name': row['class_name'],
                'class_id': int(row['class_id']),
                'timestamp': pd.Timestamp.utcnow().isoformat(),
                
                # NDVI data (tabular)
                'ndvi_mean': float(row['ndvi_mean']) if pd.notna(row['ndvi_mean']) else None,
                'ndvi_std': float(row['ndvi_std']) if pd.notna(row['ndvi_std']) else None,
                'ndvi_min': float(row['ndvi_min']) if pd.notna(row['ndvi_min']) else None,
                'ndvi_max': float(row['ndvi_max']) if pd.notna(row['ndvi_max']) else None,
                
                # Spectral data (tabular)
                'red_mean': float(row['red_mean']) if pd.notna(row['red_mean']) else None,
                'green_mean': float(row['green_mean']) if pd.notna(row['green_mean']) else None,
                'blue_mean': float(row['blue_mean']) if pd.notna(row['blue_mean']) else None,
                'nir_mean': float(row['nir_mean']) if pd.notna(row['nir_mean']) else None,
                'brightness_mean': float(row['brightness_mean']) if pd.notna(row['brightness_mean']) else None,
                
                # Image metadata
                'image_filename': row['image_filename'] if pd.notna(row['image_filename']) else None,
                'width': int(row['width']) if pd.notna(row['width']) else None,
                'height': int(row['height']) if pd.notna(row['height']) else None,
                
                # Vegetation index
                'vegetation_index': row['vegetation_index'] if pd.notna(row['vegetation_index']) else None,
            }
            
            # Find and process matching RGB image
            image_path = find_matching_image(row['class_name'], row['image_id'])
            if image_path and os.path.exists(image_path):
                rgb_features = extract_image_features(image_path)
                if rgb_features:
                    # Add RGB features to event (image modality)
                    event['rgb_features'] = rgb_features
                    event['has_image'] = True
                    event['image_path'] = image_path
                else:
                    event['has_image'] = False
            else:
                event['has_image'] = False
            
            # Send to Kafka
            producer.send(topic, value=event)
            processed += 1
            
            if processed % 50 == 0:
                print(f"Processed {processed}/{limit} multimodal events...")
            
            time.sleep(delay)
            
        except Exception as e:
            failed += 1
            print(f"Error processing row {idx}: {e}")
            continue
    
    producer.flush()
    producer.close()
    
    print(f"\n{'='*60}")
    print(f"Multimodal Event Production Complete!")
    print(f"{'='*60}")
    print(f"Successfully produced: {processed} events")
    print(f"Failed: {failed} events")
    print(f"Topic: {topic}")
    print(f"Modalities: CSV (tabular) + RGB images (visual)")
    print(f"{'='*60}")
    
    return processed, failed

def main():
    parser = argparse.ArgumentParser(description='Multimodal Kafka Producer')
    parser.add_argument('--limit', type=int, default=500, help='Number of events to produce')
    parser.add_argument('--delay', type=float, default=0.01, help='Delay between events (seconds)')
    parser.add_argument('--topic', type=str, default='multimodal-events', help='Kafka topic name')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("MULTIMODAL KAFKA PRODUCER")
    print(f"{'='*60}")
    print(f"Limit: {args.limit} events")
    print(f"Delay: {args.delay}s per event")
    print(f"Topic: {args.topic}")
    print(f"CSV Data: NDVI + Spectral bands")
    print(f"RGB Images: {RGB_DIR}")
    print(f"{'='*60}\n")
    
    produce_multimodal_events(
        limit=args.limit,
        delay=args.delay,
        topic=args.topic
    )

if __name__ == '__main__':
    main()
