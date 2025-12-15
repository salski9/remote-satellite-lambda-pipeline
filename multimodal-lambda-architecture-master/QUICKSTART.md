# 🚀 Multimodal Lambda Architecture - Quick Start Guide

## Overview
This project implements a complete **Lambda Architecture** for processing **multimodal satellite data**:
- **CSV/Tabular Data**: NDVI, spectral bands (Red, Green, Blue, NIR)
- **RGB Images**: 27,000 JPEG images (64x64 pixels) across 10 land cover classes

## Architecture Components

### Batch Layer
- **Apache Spark**: Batch processing of historical data
- **Apache Hive**: Data warehouse for aggregated results
- **HDFS**: Distributed file storage

### Speed Layer
- **Apache Kafka**: Real-time event streaming
- **Spark Streaming**: Real-time multimodal processing
- **Apache Cassandra**: Low-latency data storage

### Serving Layer
- **Flask API**: REST endpoints for querying both layers
- **Dashboard**: Real-time visualization with Chart.js

---

## 🎯 Quick Start (Automated)

### Option 1: Run Full Pipeline (All 27,000 Events)
```bash
./run_full_pipeline.sh
```

This will:
1. Check all services are running
2. Start multimodal streaming job
3. Process all 27,000 events in batches
4. Display final statistics

**Time**: ~15-30 minutes depending on hardware

### Option 2: Quick Test (500 Events)
```bash
./test_pipeline.sh 500
```

**Time**: ~1 minute

### Option 3: Continuous Streaming
```bash
python src/producer/continuous_producer.py --batch-size 100 --batch-interval 10
```

Press `Ctrl+C` to stop gracefully.

---

## 📋 Manual Step-by-Step

### 1. Start Infrastructure
```bash
docker-compose up -d
```

Wait 30 seconds for all services to initialize.

### 2. Apply Cassandra Schema
```bash
docker exec cassandra cqlsh -f /home/malek/Desktop/ProjectBigData/src/speed_layer/cassandra_multimodal.cql
```

### 3. Start Multimodal Streaming Job
```bash
docker cp src/speed_layer/spark_streaming_multimodal.py spark-master:/opt/spark/jobs/

docker exec -d spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 \
  /opt/spark/jobs/spark_streaming_multimodal.py
```

### 4. Start Flask API
```bash
source .venv/bin/activate
python src/serving/app.py &
```

### 5. Start Dashboard Server
```bash
cd dashboard
python -m http.server 8000 &
cd ..
```

### 6. Produce Multimodal Events
```bash
# Small test
python src/producer/kafka_producer_multimodal.py --limit 100 --delay 0.001

# Large batch
python src/producer/kafka_producer_multimodal.py --limit 5000 --delay 0.001
```

### 7. View Results

**Dashboard**: http://localhost:8000/multimodal.html

**API Endpoints**:
```bash
# Summary
curl http://127.0.0.1:5000/api/multimodal/summary | jq

# Tabular stats (CSV data)
curl http://127.0.0.1:5000/api/multimodal/tabular-stats | jq

# Image stats (RGB data)
curl http://127.0.0.1:5000/api/multimodal/image-stats | jq

# Anomalies (fusion)
curl http://127.0.0.1:5000/api/multimodal/anomalies | jq
```

**Cassandra Direct**:
```bash
docker exec cassandra cqlsh -e "SELECT * FROM landcover.multimodal_tabular_stats;"
docker exec cassandra cqlsh -e "SELECT * FROM landcover.multimodal_image_stats;"
docker exec cassandra cqlsh -e "SELECT COUNT(*) FROM landcover.multimodal_anomalies;"
```

---

## 🔍 Monitoring

### Check Streaming Job Status
```bash
docker exec spark-master ps aux | grep spark_streaming_multimodal
```

### View Streaming Logs
```bash
docker exec spark-master tail -f /tmp/multimodal_streaming.log
```

### Check Kafka Topics
```bash
# List messages
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic multimodal-events \
  --from-beginning \
  --max-messages 5

# Count messages
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic multimodal-events
```

### Check Cassandra Data
```bash
docker exec cassandra cqlsh -e "
  SELECT class_name, sample_count, image_count 
  FROM landcover.multimodal_tabular_stats;
"
```

### Spark UI
http://localhost:8080

### Kafka UI (if installed)
http://localhost:8090

---

## 📊 Data Flow

```
CSV Files (27K rows) ─┐
                      ├──> Multimodal Producer ──> Kafka (multimodal-events)
RGB Images (27K) ─────┘                                     │
                                                            ▼
                                               Spark Streaming (Fusion)
                                                            │
                                     ┌──────────────────────┼──────────────────────┐
                                     ▼                      ▼                      ▼
                          Tabular Stats          Image Stats            Anomalies
                         (CSV features)        (RGB features)       (Multimodal fusion)
                                     │                      │                      │
                                     └──────────────────────┴──────────────────────┘
                                                            ▼
                                                    Cassandra DB
                                                            │
                                                            ▼
                                                       Flask API
                                                            │
                                                            ▼
                                                  Dashboard (Chart.js)
```

---

## 🎨 Multimodal Features

### CSV/Tabular Features
- `ndvi_mean`, `ndvi_std`, `ndvi_min`, `ndvi_max`: Vegetation index
- `red_mean`, `green_mean`, `blue_mean`: Spectral band averages
- `nir_mean`: Near-infrared band
- `brightness_mean`: Overall brightness from CSV

### RGB Image Features
- `rgb_mean`: [R, G, B] channel means
- `rgb_std`: [R, G, B] channel standard deviations
- `rgb_min/max`: Min/max values per channel
- `brightness`: Overall image brightness (computed)
- `contrast`: Image contrast (std of all pixels)

### Fusion Analytics
- **Tabular aggregation**: Averages of CSV features per class
- **Image aggregation**: RGB statistics per class
- **Anomaly detection**: Outliers in NDVI **OR** brightness (multimodal fusion)

---

## 🔧 Configuration

### Producer Settings
```bash
# Fast processing (testing)
python src/producer/kafka_producer_multimodal.py --limit 100 --delay 0.001

# Normal speed (production)
python src/producer/kafka_producer_multimodal.py --limit 27000 --delay 0.01

# Continuous mode
python src/producer/continuous_producer.py --batch-size 200 --batch-interval 15
```

### Streaming Job
- **Processing interval**: 5 seconds (configured in `spark_streaming_multimodal.py`)
- **Checkpoint location**: `/tmp/spark_multimodal_ckpt`
- **Starting offset**: `latest` (only new events)

---

## 🛠️ Troubleshooting

### Streaming job not writing to Cassandra
```bash
# Restart the job
docker exec spark-master pkill -f spark_streaming_multimodal
docker exec spark-master rm -rf /tmp/spark_multimodal_ckpt
# Then start it again (step 3 above)
```

### Dashboard not loading data
```bash
# Check API is running
curl http://127.0.0.1:5000/api/multimodal/summary

# Check CORS is enabled
grep "CORS" src/serving/app.py
```

### Kafka consumer lag
```bash
# Check consumer group lag
docker exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group spark-multimodal-streaming
```

### Empty Cassandra tables
```bash
# Verify streaming job is running
docker exec spark-master ps aux | grep spark_streaming_multimodal

# Check logs for errors
docker exec spark-master tail -100 /tmp/multimodal_streaming.log

# Produce test events
python src/producer/kafka_producer_multimodal.py --limit 50
```

---

## 📈 Performance Metrics

- **Producer**: ~100-200 events/second (with image processing)
- **Image processing**: ~5ms per image (PIL + NumPy)
- **Streaming latency**: 5-10 seconds (configurable)
- **Event size**: ~700 bytes (500 tabular + 200 image)
- **Total dataset**: 27,000 events × 700 bytes ≈ 19 MB

---

## 🎓 Learning Resources

- **Lambda Architecture**: [http://lambda-architecture.net/](http://lambda-architecture.net/)
- **Apache Spark**: [https://spark.apache.org/docs/latest/](https://spark.apache.org/docs/latest/)
- **Apache Kafka**: [https://kafka.apache.org/documentation/](https://kafka.apache.org/documentation/)
- **Cassandra**: [https://cassandra.apache.org/doc/latest/](https://cassandra.apache.org/doc/latest/)

---

## 📝 Land Cover Classes

1. **AnnualCrop**: Agricultural crops planted annually
2. **Forest**: Dense tree coverage
3. **HerbaceousVegetation**: Grasslands and meadows
4. **Highway**: Roads and paved surfaces
5. **Industrial**: Industrial and commercial areas
6. **Pasture**: Grazing land for livestock
7. **PermanentCrop**: Orchards, vineyards
8. **Residential**: Urban residential areas
9. **River**: Water bodies (rivers, streams)
10. **SeaLake**: Large water bodies (seas, lakes)

---

## 🚀 Next Steps

1. ✅ Run full pipeline with all 27,000 events
2. ✅ Monitor dashboard for real-time updates
3. ✅ Explore API endpoints
4. 📊 Add batch layer processing (Hive integration)
5. 🤖 Implement ML models on multimodal features
6. 📈 Add more sophisticated anomaly detection
7. 🌐 Deploy to production cluster

---

**Made with ❤️ using Lambda Architecture + Multimodal AI**
