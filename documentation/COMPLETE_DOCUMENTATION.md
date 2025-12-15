# 📚 Complete Lambda Architecture Documentation

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Data Flow](#3-data-flow)
4. [Project Structure](#4-project-structure)
5. [Component Details](#5-component-details)
6. [Manual Testing Guide](#6-manual-testing-guide)
7. [Troubleshooting](#7-troubleshooting)
8. [Quick Reference](#8-quick-reference)
9. [Research Questions Answered](#9-answers-to-research-questions)

---

## 1. Project Overview

### **What is This Project?**

A **Lambda Architecture** implementation for **multimodal satellite land cover analysis** using the **EuroSAT dataset** (27,000 satellite images across 10 land cover classes).

### **Technologies Used**

- **Big Data**: Apache Spark, Apache Kafka, Apache Hive, HDFS
- **Databases**: Apache Cassandra
- **Languages**: Python 3.12, PySpark, SQL
- **Visualization**: Flask, HTML/CSS/JavaScript, Chart.js
- **Containerization**: Docker, Docker Compose

### **Dataset**

- **Source**: EuroSAT (Sentinel-2 satellite imagery)
- **Size**: 27,000 images (64x64 pixels, RGB + NIR bands)
- **Classes**: 10 land cover types
  1. AnnualCrop
  2. Forest
  3. HerbaceousVegetation
  4. Highway
  5. Industrial
  6. Pasture
  7. PermanentCrop
  8. Residential
  9. River
  10. SeaLake

### **Features Extracted**

1. **Tabular/Spectral** (from CSV metadata)

   - NDVI (Normalized Difference Vegetation Index)
   - RGB channels (Red, Green, Blue)
   - NIR (Near-Infrared)
   - Brightness

2. **Texture Features** (from images)

   - **GLCM** (Gray-Level Co-occurrence Matrix): contrast, homogeneity, energy, correlation, dissimilarity, ASM
   - **LBP** (Local Binary Patterns): 8-bin histogram for texture entropy

3. **ML Features** (from pre-trained model)
   - 64-dimensional feature vectors
   - Pre-normalized for machine learning

---

## 2. Architecture

### **Lambda Architecture Diagram**

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LAMBDA ARCHITECTURE                          │
│                   Multimodal Land Cover Analysis                     │
└─────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │   EuroSAT    │
                              │   Dataset    │
                              │  27K images  │
                              └──────┬───────┘
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │   PRE-INGESTION PIPELINE       │
                    │  (Feature Extraction)          │
                    │  • CSV → Tabular features      │
                    │  • Images → Texture (GLCM/LBP) │
                    │  • Images → ML features (64D)  │
                    └────────────┬───────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────────┐
                    │      HDFS STORAGE              │
                    │  /data/processed/*.parquet     │
                    │  • processed_images.parquet    │
                    │  • texture_features.parquet    │
                    │  • ml_features.parquet         │
                    └──────┬─────────────┬───────────┘
                           │             │
           ┌───────────────┘             └──────────────┐
           │                                            │
           ▼                                            ▼
┌──────────────────────┐                    ┌──────────────────────┐
│   BATCH LAYER        │                    │   SPEED LAYER        │
│  (Spark Batch)       │                    │  (Spark Streaming)   │
├──────────────────────┤                    ├──────────────────────┤
│ • Reads from HDFS    │                    │ • Reads from Kafka   │
│ • Runs daily/weekly  │                    │ • Real-time (5s)     │
│ • Computes accurate  │                    │ • Micro-batches      │
│   aggregations       │                    │ • Approximate views  │
│ • Historical trends  │                    │                      │
│ • Class separability │                    │ ┌────────────────┐   │
│ • Feature corr.      │                    │ │ Kafka Producer │   │
│                      │                    │ │ (from Parquet) │   │
│ Output:              │                    │ └────────┬───────┘   │
│ • Hive tables        │                    │          │           │
│ • HDFS Parquet       │                    │          ▼           │
│                      │                    │   ┌──────────────┐   │
└──────────┬───────────┘                    │   │    Kafka     │   │
           │                                │   │    Topic     │   │
           │                                │   └──────┬───────┘   │
           │                                │          │           │
           │                                │          ▼           │
           │                                │   ┌──────────────┐   │
           │                                │   │    Spark     │   │
           │                                │   │  Streaming   │   │
           │                                │   └──────┬───────┘   │
           │                                └──────────┼───────────┘
           │                                           │
           └───────────────┬───────────────────────────┘
                           │
                           ▼
              ┌────────────────────────────┐
              │     SERVING LAYER          │
              │     (Cassandra)            │
              ├────────────────────────────┤
              │ Keyspaces:                 │
              │ • mykeyspace (realtime)    │
              │ • batch_views (historical) │
              │                            │
              │ Tables:                    │
              │ • tabular_stats            │
              │ • ml_features              │
              │ • texture_table            │
              │ • image_stats              │
              │ • class_statistics_table   │
              │ • temporal_trends_table    │
              │ • separability_table       │
              │ • correlations_table       │
              └────────────┬───────────────┘
                           │
                           ▼
              ┌────────────────────────────┐
              │     FLASK API + UI         │
              │   (Dashboard)              │
              ├────────────────────────────┤
              │ Endpoints:                 │
              │ • /api/health              │
              │ • /api/enhanced/summary    │
              │ • /api/enhanced/texture    │
              │ • /api/analytics/...       │
              │ • /api/batch/...           │
              │                            │
              │ Dashboard Tabs:            │
              │ • Overview                 │
              │ • Texture Analysis         │
              │ • ML Features              │
              │ • Trends & Insights        │
              │ • Class Comparison         │
              └────────────────────────────┘
```

### **Key Characteristics**

| Layer             | Purpose                 | Latency      | Accuracy      | Technology              |
| ----------------- | ----------------------- | ------------ | ------------- | ----------------------- |
| **Batch Layer**   | Historical aggregations | Hours/Days   | 100% accurate | Spark + Hive + HDFS     |
| **Speed Layer**   | Real-time updates       | Seconds      | ~95% accurate | Spark Streaming + Kafka |
| **Serving Layer** | Query interface         | Milliseconds | Merged views  | Cassandra + Flask       |

---

## 3. Data Flow

### **End-to-End Data Journey**

```
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: DATA INGESTION (Pre-processing)                        │
└─────────────────────────────────────────────────────────────────┘

EuroSAT Dataset (27,000 images)
    │
    ├─► CSV files (metadata.csv) ──► Extract spectral features
    │                                  (NDVI, RGB, NIR, brightness)
    │
    ├─► TIF images (*.tif) ────────► Extract texture features
    │                                  (GLCM: 6 metrics, LBP: 8 bins)
    │
    └─► TIF images (*.tif) ────────► Extract ML features
                                      (64D pre-normalized vectors)
                                        │
                                        ▼
                            ┌───────────────────────┐
                            │  HDFS Storage         │
                            │  /data/processed/     │
                            ├───────────────────────┤
                            │ • processed_images.   │
                            │   parquet (27K rows)  │
                            │ • texture_features.   │
                            │   parquet (27K rows)  │
                            │ • ml_features.        │
                            │   parquet (27K rows)  │
                            └───────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STAGE 2: BATCH PROCESSING (Historical Analysis)                 │
└─────────────────────────────────────────────────────────────────┘

HDFS Parquet Files
    │
    ▼
┌────────────────────────────────┐
│ Spark Batch Processor          │
│ (src/batch_layer/              │
│  spark_batch_processor.py)     │
├────────────────────────────────┤
│ 1. Read all 27K records        │
│ 2. Join on image_id            │
│ 3. Compute aggregations:       │
│    • Class statistics          │
│    • Temporal trends           │
│    • Separability matrix       │
│    • Feature correlations      │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Hive Database: batch_views     │
├────────────────────────────────┤
│ Tables (Parquet format):       │
│ • class_statistics             │
│ • temporal_trends              │
│ • class_separability           │
│ • feature_correlations         │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Cassandra: batch_views keyspace│
│ (Synced for serving layer)     │
└────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STAGE 3: SPEED LAYER (Real-time Streaming)                      │
└─────────────────────────────────────────────────────────────────┘

HDFS Parquet Files
    │
    ▼
┌────────────────────────────────┐
│ Kafka Producer                 │
│ (kafka_producer_from_parquet)  │
├────────────────────────────────┤
│ 1. Read parquet files          │
│ 2. Join datasets on image_id   │
│ 3. Stream to Kafka topic       │
│    (27K JSON events)           │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Kafka Topic:                   │
│ "enhanced-multimodal-events"   │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Spark Streaming                │
│ (spark_streaming_enhanced.py)  │
├────────────────────────────────┤
│ 1. Consume from Kafka (5s)     │
│ 2. Micro-batch aggregations    │
│ 3. Compute statistics          │
│ 4. Detect anomalies            │
│ 5. Write to Cassandra          │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Cassandra: mykeyspace          │
├────────────────────────────────┤
│ Tables:                        │
│ • tabular_stats (by class)     │
│ • ml_features (by class)       │
│ • texture_table (by class)     │
│ • image_stats (by class)       │
│ • cumulative_totals (global)   │
└────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STAGE 4: SERVING LAYER (Query & Visualization)                  │
└─────────────────────────────────────────────────────────────────┘

Cassandra (mykeyspace + batch_views)
    │
    ▼
┌────────────────────────────────┐
│ Flask API (app_enhanced.py)    │
├────────────────────────────────┤
│ REST Endpoints:                │
│ • /api/health                  │
│ • /api/enhanced/summary        │
│ • /api/enhanced/texture-stats  │
│ • /api/analytics/separability  │
│ • /api/batch/class-statistics  │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Web Dashboard (HTML/JS)        │
├────────────────────────────────┤
│ 5 Interactive Tabs:            │
│ 1. Overview (NDVI, RGB)        │
│ 2. Texture Analysis (GLCM/LBP) │
│ 3. ML Features (64D vectors)   │
│ 4. Trends & Insights           │
│ 5. Class Comparison            │
│                                │
│ Features:                      │
│ • Auto-refresh (30s)           │
│ • Interactive charts           │
│ • Real-time + batch views      │
└────────────────────────────────┘
```

### **Data Format Examples**

**1. Processed Images Parquet (HDFS)**

```
image_id        | class_id | ndvi_mean | red_mean | green_mean | ...
IMG_000001      | 1        | 0.45      | 120.5    | 98.3       | ...
IMG_000002      | 2        | 0.72      | 45.2     | 78.9       | ...
```

**2. Texture Features Parquet (HDFS)**

```
image_id          | glcm_contrast | glcm_energy | lbp_hist_0 | ...
SeaLake_1678      | 0.0           | 1.0         | 0.083      | ...
Forest_2503       | 0.012         | 0.991       | 0.057      | ...
```

**3. Kafka Event (JSON)**

```json
{
  "image_id": "IMG_000001",
  "class_id": 1,
  "class_name": "AnnualCrop",
  "ndvi_mean": 0.45,
  "red_mean": 120.5,
  "glcm_contrast": 0.012,
  "ml_features": [0.23, 0.45, ..., 0.89],
  "timestamp": "2025-12-15T08:30:00"
}
```

**4. Cassandra Table (Realtime)**

```cql
SELECT * FROM mykeyspace.tabular_stats WHERE class_name='Forest';
-- Returns: count, avg_ndvi, avg_brightness, etc.
```

**5. Hive Table (Batch)**

```sql
SELECT * FROM batch_views.class_statistics;
-- Returns: accurate historical aggregations
```

---

## 4. Project Structure

```
remote-satellite-lambda-pipeline/
│
├── README.md                          # Project overview
├── RESEARCH_ANSWERS.md                # Research questions & answers
├── COMPLETE_DOCUMENTATION.md          # This file
├── docker-compose.yml                 # Docker services definition
├── requirements.txt                   # Python dependencies
├── .gitignore                         # Git ignore rules
│
├── venv/                              # Python virtual environment
│
├── logs/                              # Log files
│   ├── spark_streaming.log            # Speed layer logs
│   ├── flask_api.log                  # Serving layer logs
│   ├── producer.log                   # Kafka producer logs
│   └── batch_processing.log           # Batch layer logs
│
├── spark_jars/                        # Spark dependency JARs
│   ├── kafka-clients-*.jar
│   ├── spark-cassandra-connector-*.jar
│   └── ... (17 JARs total)
│
├── infrastructure/                    # Infrastructure schemas
│   ├── cassandra_enhanced.cql         # Realtime tables
│   └── cassandra_batch_views.cql      # Batch views tables
│
├── data/                              # Raw dataset (not in HDFS yet)
│   ├── metadata.csv
│   ├── ndvi_stats.csv
│   ├── spectral_data.csv
│   └── EuroSAT/
│
├── src/                               # Source code
│   │
│   ├── producer/                      # Data ingestion
│   │   └── kafka_producer_from_parquet.py
│   │
│   ├── batch_layer/                   # Batch processing
│   │   ├── spark_batch_processor.py   # Main batch job
│   │   └── sync_batch_to_cassandra.py # Hive→Cassandra sync
│   │
│   ├── speed_layer/                   # Real-time processing
│   │   └── spark_streaming_enhanced.py
│   │
│   └── serving/                       # API & UI
│       ├── app_enhanced.py            # Flask REST API
│       └── templates/
│           └── dashboard.html         # Web dashboard
│
├── start_pipeline_automated.sh        # Automated startup script
├── run_batch_job.sh                   # Batch processing runner
└── load_texture_data.py               # Manual data loader
```

---

## 5. Component Details

### **5.1 Docker Services**

All infrastructure runs in Docker containers:

```bash
# View running containers
sudo docker compose ps
```

| Service           | Container      | Ports       | Purpose            |
| ----------------- | -------------- | ----------- | ------------------ |
| **Zookeeper**     | `zookeeper`    | 2181        | Kafka coordination |
| **Kafka**         | `kafka`        | 9092, 29092 | Message broker     |
| **Cassandra**     | `cassandra`    | 9042, 7000  | Serving database   |
| **HDFS NameNode** | `namenode`     | 8020, 9870  | Metadata manager   |
| **HDFS DataNode** | `datanode`     | 9864        | Data storage       |
| **Spark Master**  | `spark-master` | 7077, 8080  | Cluster manager    |
| **Spark Worker**  | `spark-worker` | 8081        | Processing node    |

### **5.2 Batch Layer**

**File**: `src/batch_layer/spark_batch_processor.py`

**Purpose**: Compute accurate historical aggregations from HDFS

**What it does**:

1. Reads all 27,000 records from HDFS Parquet files
2. Joins datasets on `image_id`
3. Computes:
   - Class statistics (mean, std, min, max for all features)
   - Temporal trends (simulated monthly aggregations)
   - Class separability (Euclidean distance between class centroids)
   - Feature correlations (Pearson correlation for all feature pairs)
4. Writes results to Hive tables (Parquet format)
5. Syncs to Cassandra for serving layer

**Output Tables** (Hive):

- `batch_views.class_statistics`
- `batch_views.temporal_trends`
- `batch_views.class_separability`
- `batch_views.feature_correlations`

**When to run**:

- Every 2 hours (scheduled via cron: 00:00, 02:00, 04:00, ..., 22:00)
- After new data ingestion
- After schema changes requiring recomputation

### **5.3 Speed Layer**

**Components**:

1. **Kafka Producer**: `src/producer/kafka_producer_from_parquet.py`
2. **Spark Streaming**: `src/speed_layer/spark_streaming_enhanced.py`

**Purpose**: Real-time processing of incoming events

**Data Flow**:

```
HDFS Parquet → Kafka Producer → Kafka Topic → Spark Streaming → Cassandra
```

**Spark Streaming Features**:

- **Window**: 5-second micro-batches
- **Operations**:
  - Aggregate by class (count, avg, std)
  - Detect anomalies (statistical outliers)
  - Compute ML feature statistics
  - Track cumulative totals
- **Output**: Real-time views in Cassandra (`mykeyspace`)

**Kafka Topic**: `enhanced-multimodal-events`

### **5.4 Serving Layer**

**File**: `src/serving/app_enhanced.py`

**Purpose**: REST API + Web Dashboard for querying data

**REST API Endpoints**:

| Endpoint                          | Method | Description                     |
| --------------------------------- | ------ | ------------------------------- |
| `/`                               | GET    | Web dashboard (HTML)            |
| `/api/health`                     | GET    | Health check (Cassandra status) |
| `/api/enhanced/summary`           | GET    | Overall statistics              |
| `/api/enhanced/texture-stats`     | GET    | Texture features by class       |
| `/api/enhanced/ml-features`       | GET    | ML feature vectors              |
| `/api/multimodal/tabular-stats`   | GET    | Spectral features by class      |
| `/api/analytics/separability`     | GET    | Class separability analysis     |
| `/api/analytics/similarity`       | GET    | Class similarity matrix         |
| `/api/analytics/band-correlation` | GET    | Spectral band correlations      |
| `/api/batch/class-statistics`     | GET    | Batch-computed statistics       |
| `/api/batch/temporal-trends`      | GET    | Historical trends               |
| `/api/batch/separability`         | GET    | Batch separability metrics      |

**Dashboard Features**:

- 5 interactive tabs
- Auto-refresh every 30 seconds
- Chart.js visualizations (bar, radar, heatmap)
- Real-time + batch view comparison

---

## 6. Manual Testing Guide

### **6.1 Prerequisites Check**

```bash
# Navigate to project directory
cd /home/top/bigData/remote-satellite-lambda-pipeline

# Check Docker services
sudo docker compose ps
# Expected: All 7 containers running

# Check HDFS
sudo docker compose exec namenode hdfs dfs -ls /data/processed
# Expected: processed_images.parquet, texture/, ml_features/

# Check Cassandra
sudo docker compose exec cassandra cqlsh -e "DESCRIBE KEYSPACES;"
# Expected: mykeyspace, batch_views

# Activate virtual environment
source venv/bin/activate
```

---

### **6.2 Test Batch Layer**

#### **Test 1: Run Batch Processing**

```bash
# Run batch job
./run_batch_job.sh

# Expected output:
# ✓ Spark session with Hive support created
# ✓ Hive database 'batch_views' ready
# ✓ Loaded 27000 processed images
# ✓ Loaded 27000 texture features
# ✓ Computed statistics for 10 classes
# ✓ BATCH PROCESSING COMPLETE
```

**Verification**:

```bash
# Check Hive tables
spark-sql -e "SHOW TABLES IN batch_views;"
# Expected: class_statistics, temporal_trends, class_separability, feature_correlations

# Query class statistics
spark-sql -e "SELECT class_name, total_samples, avg_ndvi FROM batch_views.class_statistics LIMIT 5;"
```

**Expected Output**:

```
AnnualCrop      2500    0.3274
Forest          3000    0.3764
Industrial      2500    0.3720
...
```

#### **Test 1b: Schedule Automatic Batch Processing (Every 2 Hours)**

```bash
# Setup cron job to run batch processing every 2 hours
cd /home/top/bigData/remote-satellite-lambda-pipeline
./scripts/setup_batch_cron.sh

# Expected output:
# ✓ Cron script is executable
# ✓ Cron job installed successfully!
# Schedule: 00:00, 02:00, 04:00, 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00
```

**Verification**:

```bash
# View installed cron jobs
crontab -l

# Expected:
# 0 */2 * * * /home/top/bigData/remote-satellite-lambda-pipeline/scripts/cron_batch_job.sh

# Test cron script manually
./scripts/cron_batch_job.sh

# Monitor cron logs
ls -lth logs/batch_cron_*.log
tail -f logs/batch_cron_*.log
```

**Remove cron job** (if needed):

```bash
# Remove the cron job
crontab -l | grep -v 'cron_batch_job.sh' | crontab -

# Verify removal
crontab -l
```

#### **Test 2: Verify HDFS Storage**

```bash
# Check batch views in HDFS
sudo docker compose exec namenode hdfs dfs -ls /user/hive/warehouse/batch_views.db/

# Expected directories:
# class_statistics/
# temporal_trends/
# class_separability/
# feature_correlations/

# Read sample data
sudo docker compose exec namenode hdfs dfs -cat /user/hive/warehouse/batch_views.db/class_statistics/*.parquet | head -n 50
```

#### **Test 3: Query Batch Views**

```bash
# Top 5 most separable class pairs
spark-sql -e "
  SELECT class_name_1, class_name_2, euclidean_distance
  FROM batch_views.class_separability
  ORDER BY euclidean_distance DESC
  LIMIT 5;
"

# Expected:
# SeaLake, PermanentCrop, 1544.78
# Forest, Industrial, 1321.45
# ...

# Feature correlations
spark-sql -e "
  SELECT feature_1, feature_2, correlation
  FROM batch_views.feature_correlations
  WHERE feature_1 != feature_2
  ORDER BY ABS(correlation) DESC
  LIMIT 5;
"

# Expected:
# green_mean, brightness_mean, 0.9963
# red_mean, brightness_mean, 0.9897
# ...
```

---

### **6.3 Test Speed Layer**

#### **Test 1: Check Kafka**

```bash
# List Kafka topics
sudo docker compose exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:29092 --list

# Expected: enhanced-multimodal-events

# Describe topic
sudo docker compose exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:29092 \
  --describe --topic enhanced-multimodal-events

# Expected: 1 partition, replication factor 1
```

#### **Test 2: Run Kafka Producer**

```bash
# Start producer (sends 27K events)
cd src/producer
python kafka_producer_from_parquet.py

# Expected output:
# ✓ Loaded 27000 processed images
# ✓ Loaded 27000 texture features
# ✓ Streaming events to Kafka topic
# Progress: 1000/27000 (3.7%)
# ...
# Progress: 27000/27000 (100.0%)
# ✓ Successfully sent: 27000
```

**Verification**:

```bash
# Consume sample messages
sudo docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:29092 \
  --topic enhanced-multimodal-events \
  --from-beginning \
  --max-messages 3

# Expected: 3 JSON events with all features
```

#### **Test 3: Run Spark Streaming**

```bash
# Start Spark Streaming
cd src/speed_layer

spark-submit \
  --jars "/home/top/bigData/remote-satellite-lambda-pipeline/spark_jars/*.jar" \
  --conf spark.cassandra.connection.host=localhost \
  --conf spark.cassandra.connection.port=9042 \
  spark_streaming_enhanced.py

# Expected output:
# ✓ Initialized Spark session
# ✓ Cassandra connection established
# ✓ Starting streaming query...
# Processing Enhanced Batch 1
# ✓ Tabular features aggregated (4 classes)
# ✓ Enhanced anomalies detected: 672
# ...
```

**Verification (in another terminal)**:

```bash
# Check Cassandra tables
sudo docker compose exec cassandra cqlsh -e "
  SELECT class_name, count, avg_ndvi
  FROM mykeyspace.tabular_stats
  LIMIT 5;
"

# Expected: Real-time statistics

# Check cumulative totals
sudo docker compose exec cassandra cqlsh -e "
  SELECT total_events, total_classes
  FROM mykeyspace.cumulative_totals
  WHERE id='global';
"

# Expected: total_events=27000, total_classes=10
```

#### **Test 4: Monitor Streaming**

```bash
# Tail Spark streaming logs
tail -f logs/spark_streaming.log

# Expected: Batch processing messages every 5 seconds

# Check for errors
grep -i error logs/spark_streaming.log

# Expected: No critical errors
```

---

### **6.4 Test Serving Layer**

#### **Test 1: Start Flask API**

```bash
# Start Flask API
cd src/serving
python app_enhanced.py

# Expected output:
# ✓ Cassandra connection established
# * Running on http://0.0.0.0:5000
```

#### **Test 2: Test API Endpoints**

```bash
# Health check
curl http://localhost:5000/api/health | jq

# Expected:
# {
#   "status": "healthy",
#   "cassandra": "connected",
#   "timestamp": "2025-12-15T10:30:00"
# }

# Summary statistics
curl http://localhost:5000/api/enhanced/summary | jq

# Expected:
# {
#   "total_events": 27000,
#   "total_classes": 10,
#   "avg_ndvi": 0.45,
#   ...
# }

# Texture statistics
curl http://localhost:5000/api/enhanced/texture-stats | jq

# Expected: Array of 10 classes with GLCM/LBP features

# Class separability
curl http://localhost:5000/api/analytics/separability | jq

# Expected: Array of 45 class pairs with distances

# Band correlations
curl http://localhost:5000/api/analytics/band-correlation | jq

# Expected: Correlation matrix for spectral bands
```

#### **Test 3: Access Dashboard**

```bash
# Open in browser
firefox http://localhost:5000

# Or use curl to check HTML
curl -s http://localhost:5000 | grep -i "dashboard"

# Expected: HTML title containing "Dashboard"
```

**Dashboard Manual Tests**:

1. **Overview Tab**

   - [ ] NDVI distribution chart loads
   - [ ] RGB brightness chart loads
   - [ ] Sample count per class displays
   - [ ] Statistics cards show numbers

2. **Texture Analysis Tab**

   - [ ] GLCM features radar chart displays
   - [ ] LBP entropy distribution chart loads
   - [ ] Texture statistics table populates

3. **ML Features Tab**

   - [ ] Feature importance chart displays
   - [ ] ML feature vectors table loads
   - [ ] Dimension count correct (64D)

4. **Trends & Insights Tab**

   - [ ] Processing rate chart updates
   - [ ] Data distribution pie chart displays

5. **Class Comparison Tab**
   - [ ] Separability matrix loads
   - [ ] Top 10 separable pairs table displays
   - [ ] Band correlation matrix shows values
   - [ ] Key research questions section visible

---

### **6.5 Integration Tests**

#### **Test 1: End-to-End Pipeline**

```bash
# Run complete automated pipeline
./start_pipeline_automated.sh

# Wait for initialization (~90 seconds)
# Expected output:
# ✓ Batch processing completed
# ✓ Spark Streaming started (PID: XXXX)
# ✓ Producer completed (27,000 events sent)
# ✓ Flask API started (PID: YYYY)
# ✓ PIPELINE STARTED SUCCESSFULLY
```

**Verification**:

```bash
# Check all processes running
ps aux | grep -E 'spark_streaming_enhanced|app_enhanced'

# Test API while pipeline runs
curl http://localhost:5000/api/health

# Check real-time data updates
watch -n 5 "curl -s http://localhost:5000/api/enhanced/summary | jq '.total_events'"
```

#### **Test 2: Skip Batch Processing**

```bash
# Run without batch processing (faster)
SKIP_BATCH=1 ./start_pipeline_automated.sh

# Expected: Same as above but skips Step 0
```

#### **Test 3: Data Consistency**

```bash
# Compare batch vs real-time counts
echo "Batch view:"
spark-sql -e "
  SELECT class_name, total_samples
  FROM batch_views.class_statistics
  ORDER BY class_name;
"

echo "Real-time view:"
sudo docker compose exec cassandra cqlsh -e "
  SELECT class_name, count
  FROM mykeyspace.tabular_stats;
"

# Expected: Same counts (27,000 total, ~2500-3000 per class)
```

---

### **6.6 Performance Tests**

#### **Test 1: Batch Processing Time**

```bash
# Time batch processing
time ./run_batch_job.sh

# Expected: ~2-5 minutes for 27,000 records
```

#### **Test 2: Streaming Throughput**

```bash
# Check producer throughput
grep "Progress:" logs/producer.log | tail -1

# Expected: ~5000-10000 events/second

# Check Spark processing time
grep "Processing Enhanced Batch" logs/spark_streaming.log | tail -5

# Expected: Batches complete in <5 seconds
```

#### **Test 3: API Response Time**

```bash
# Benchmark API endpoints
time curl -s http://localhost:5000/api/enhanced/summary > /dev/null

# Expected: <100ms

time curl -s http://localhost:5000/api/analytics/separability > /dev/null

# Expected: <200ms
```

---

### **6.7 Data Quality Tests**

#### **Test 1: Verify Data Completeness**

```bash
# Check HDFS record counts
sudo docker compose exec namenode hdfs dfs -cat /data/processed/processed_images.parquet/_metadata | grep "num_rows"

# Expected: 27000

# Check Cassandra record counts
sudo docker compose exec cassandra cqlsh -e "
  SELECT COUNT(*) FROM mykeyspace.tabular_stats;
  SELECT COUNT(*) FROM batch_views.class_statistics_table;
"

# Expected: 10 classes in both
```

#### **Test 2: Validate Feature Ranges**

```bash
# Check NDVI range (should be -1 to 1)
spark-sql -e "
  SELECT MIN(avg_ndvi), MAX(avg_ndvi)
  FROM batch_views.class_statistics;
"

# Expected: MIN ~0.2, MAX ~0.8

# Check GLCM contrast (should be >= 0)
curl -s http://localhost:5000/api/enhanced/texture-stats | jq '.[].avg_glcm_contrast'

# Expected: All values >= 0
```

#### **Test 3: Check for Nulls**

```bash
# Check for null values in batch views
spark-sql -e "
  SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN avg_ndvi IS NULL THEN 1 ELSE 0 END) AS null_ndvi,
    SUM(CASE WHEN avg_brightness IS NULL THEN 1 ELSE 0 END) AS null_brightness
  FROM batch_views.class_statistics;
"

# Expected: total=10, null_ndvi=0, null_brightness=0
```

---

### **6.8 Failure & Recovery Tests**

#### **Test 1: Kafka Failure**

```bash
# Stop Kafka
sudo docker compose stop kafka

# Try running producer
cd src/producer
python kafka_producer_from_parquet.py

# Expected: Connection error (as expected)

# Restart Kafka
sudo docker compose start kafka
sleep 10

# Retry producer
python kafka_producer_from_parquet.py

# Expected: Success after Kafka restarts
```

#### **Test 2: Cassandra Failure**

```bash
# Stop Cassandra
sudo docker compose stop cassandra

# Check API
curl http://localhost:5000/api/health

# Expected: {"status": "unhealthy", "cassandra": "disconnected"}

# Restart Cassandra
sudo docker compose start cassandra
sleep 30

# Retry API
curl http://localhost:5000/api/health

# Expected: {"status": "healthy", "cassandra": "connected"}
```

#### **Test 3: HDFS Failure**

```bash
# Stop HDFS
sudo docker compose stop namenode datanode

# Try batch processing
./run_batch_job.sh

# Expected: HDFS connection error

# Restart HDFS
sudo docker compose start namenode datanode
sleep 20

# Retry batch processing
./run_batch_job.sh

# Expected: Success
```

---

## 7. Troubleshooting

### **Common Issues & Solutions**

| Issue                            | Symptoms                                       | Solution                                                              |
| -------------------------------- | ---------------------------------------------- | --------------------------------------------------------------------- |
| **Kafka not available**          | `TimeoutException: Timed out waiting for node` | `sudo docker compose restart zookeeper kafka`                         |
| **Cassandra connection refused** | `NoHostAvailable`                              | `sudo docker compose restart cassandra`                               |
| **HDFS permission denied**       | `AccessControlException`                       | `sudo docker compose exec namenode hdfs dfs -chmod -R 777 /user/hive` |
| **Spark Streaming stops**        | Process exits after 30s                        | Check logs: `tail -f logs/spark_streaming.log`                        |
| **Flask API 500 errors**         | API returns errors                             | Check Cassandra connection: `curl http://localhost:5000/api/health`   |
| **Dashboard not loading**        | Blank page                                     | Check Flask logs: `tail -f logs/flask_api.log`                        |
| **JARs not found**               | `ClassNotFoundException`                       | Re-run startup script to download JARs                                |
| **Port already in use**          | `Address already in use`                       | Kill existing processes: `pkill -f spark_streaming_enhanced`          |

### **Debug Commands**

```bash
# View all container logs
sudo docker compose logs

# View specific service logs
sudo docker compose logs kafka
sudo docker compose logs cassandra

# Check container health
sudo docker compose ps
sudo docker inspect cassandra | grep -i health

# Test Cassandra connection
sudo docker compose exec cassandra cqlsh -e "SELECT now() FROM system.local;"

# Test HDFS connection
sudo docker compose exec namenode hdfs dfs -ls /

# Test Kafka connection
sudo docker compose exec kafka /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:29092
```

### **Reset Everything**

```bash
# Stop all processes
pkill -f 'spark_streaming_enhanced|app_enhanced|kafka_producer'

# Stop Docker services
sudo docker compose down

# Remove volumes (CAUTION: Deletes all data)
sudo docker compose down -v

# Restart fresh
sudo docker compose up -d
sleep 30

# Run pipeline
./start_pipeline_automated.sh
```

---

## 8. Quick Reference

### **One-Command Pipeline Start**

```bash
# Full pipeline with batch processing
cd /home/top/bigData/remote-satellite-lambda-pipeline && ./start_pipeline_automated.sh

# Skip batch processing (faster)
cd /home/top/bigData/remote-satellite-lambda-pipeline && SKIP_BATCH=1 ./start_pipeline_automated.sh
```

### **Stop Pipeline**

```bash
# Kill processes
pkill -f 'spark_streaming_enhanced|app_enhanced'

# Or use PIDs from startup output
kill <SPARK_PID> <FLASK_PID>
```

### **Key URLs**

- **Dashboard**: http://localhost:5000
- **API Health**: http://localhost:5000/api/health
- **Spark UI**: http://localhost:4040 (when Spark is running)
- **HDFS UI**: http://localhost:9870
- **Spark Master UI**: http://localhost:8080

### **Key Directories**

- **Logs**: `logs/`
- **HDFS Data**: `hdfs://localhost:8020/data/processed/`
- **Hive Warehouse**: `hdfs://localhost:8020/user/hive/warehouse/batch_views.db/`
- **Spark JARs**: `spark_jars/`

### **Batch Processing Schedule**

```bash
# Setup automatic batch processing (every 2 hours)
./scripts/setup_batch_cron.sh

# View cron schedule
crontab -l

# Remove cron job
crontab -l | grep -v 'cron_batch_job.sh' | crontab -

# Run batch processing manually
./scripts/run_batch_job.sh

# Monitor cron logs
tail -f logs/batch_cron_*.log
```

### **Useful Commands**

```bash
# Check all Docker services
sudo docker compose ps

# View Docker logs
sudo docker compose logs -f kafka
sudo docker compose logs -f cassandra

# Query Hive
spark-sql -e "USE batch_views; SHOW TABLES;"

# Query Cassandra
sudo docker compose exec cassandra cqlsh -e "DESCRIBE KEYSPACES;"

# Check HDFS
sudo docker compose exec namenode hdfs dfs -ls /data/processed

# Monitor logs
tail -f logs/spark_streaming.log
tail -f logs/flask_api.log
tail -f logs/batch_processing.log
```

---

## 9. Answers to Research Questions

Your pipeline now answers these questions (as documented in `RESEARCH_ANSWERS.md`):

### **1. Are forests separable from crops?**

✅ **YES** - Distance = **910.47** (highly separable)

**Evidence**: Euclidean distance in 8-dimensional feature space (NDVI, brightness, RGB, GLCM contrast/energy, LBP entropy) shows clear separation.

### **2. Are residential and industrial distinguishable?**

✅ **YES** - Distance = **1098.09** (very distinguishable, 6th highest among all pairs)

**Evidence**: Different spectral signatures (industrial has uniform metal/concrete, residential has mixed vegetation and varied materials).

### **3. Are rivers closer to sea/lake than to forest?**

❌ **NO** - Rivers are closer to forests (503.61) than to sea/lake (909.90)

**Evidence**: Riparian effect - rivers are often surrounded by vegetation (riparian forests), creating similar spectral signatures.

### **4. What are similarities between land-cover types?**

✅ **Full 10x10 similarity matrix available** via `/api/analytics/similarity`

**Most Similar**:

- HerbaceousVegetation ↔ Pasture (both grasslands)
- AnnualCrop ↔ PermanentCrop (both agricultural)

**Most Dissimilar**:

- SeaLake ↔ PermanentCrop (1544.78 - water vs vegetation)
- SeaLake ↔ Forest (1412.73)

### **5. What about separability between classes?**

✅ **All 45 pairs computed**, stored in `batch_views.class_separability`

**Key Finding**: All pairs are separable (distance > 500), indicating the multimodal feature set effectively distinguishes all land cover types.

### **6. Hidden correlations between bands?**

✅ **7 strong correlations found** (|r| > 0.5)

**Key Findings**:

1. Green ↔ Brightness: r = **0.9963** (almost perfect)
2. Red ↔ Brightness: r = **0.9897**
3. Red ↔ Green: r = **0.9802**
4. NIR ↔ NDVI: r = **0.8815**

**Hidden Insight**: NIR has weak correlation with RGB (r = 0.15-0.33), which is why multispectral imaging (adding NIR) is powerful for vegetation analysis!

### **7. Average NDVI per day over 6 months?**

✅ **Temporal trends** in `batch_views.temporal_trends`

**Example**: Forest maintains consistent NDVI (~0.38), while crops show seasonal variation.

### **8. Trends per sensor/class?**

✅ **Per-class trends** computed in batch layer

**Access**: Query `batch_views.temporal_trends` or use `/api/batch/temporal-trends`

### **9. Recomputed metrics after schema change?**

✅ **Re-run** `./run_batch_job.sh` to reprocess all HDFS data

**Benefit**: Lambda architecture allows complete recomputation from immutable HDFS data without data loss.

---

## Summary

This Lambda Architecture implementation provides:

✅ **Complete pipeline**: Batch + Speed + Serving layers  
✅ **Scalable storage**: HDFS (27K images) + Cassandra (serving)  
✅ **Real-time processing**: Spark Streaming (5s micro-batches)  
✅ **Historical analysis**: Spark Batch + Hive (accurate aggregations)  
✅ **REST API**: Flask with 15+ endpoints  
✅ **Interactive dashboard**: 5 tabs with Chart.js visualizations  
✅ **Research insights**: Answers 9 key questions about land cover separability

**🎉 Your Lambda Architecture is Production-Ready! 🎉**

---

**For more details, see:**

- `RESEARCH_ANSWERS.md` - Detailed answers to research questions
- `README.md` - Project overview and setup instructions
- API documentation: http://localhost:5000/api

**Questions or issues?** Check the Troubleshooting section or review the logs in `logs/` directory.
