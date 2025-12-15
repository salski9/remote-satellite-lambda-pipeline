# 🌍 Multimodal Lambda Architecture for Satellite Image Processing

**Real-time land cover analysis combining CSV metadata with RGB image features**

---

## 📋 Table of Contents

- [Quick Start (3 Steps)](#-quick-start-3-steps)
- [What This Project Does](#-what-this-project-does)
- [Architecture Overview](#-architecture-overview)
- [Project Structure](#-project-structure)
- [Usage Scenarios](#-usage-scenarios)
- [Monitoring & Visualization](#-monitoring--visualization)
- [Troubleshooting](#-troubleshooting)
- [Technical Details](#-technical-details)

---

## 🚀 Quick Start (3 Steps)

### Prerequisites
- Docker & Docker Compose installed
- Python 3.11+ with pip
- 8GB+ RAM recommended
- 20GB free disk space

### Step 1: Install Dependencies
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python packages
pip install -r requirements.txt
```

### Step 2: Run Complete Setup
```bash
# This single command does EVERYTHING:
# - Starts all Docker services (Kafka, Spark, Cassandra, etc.)
# - Initializes database
# - Deploys streaming job
# - Starts API and dashboard
# - Runs test with 500 events
./setup.sh
```

### Step 3: View Dashboard
```bash
# Open in your browser:
http://localhost:8000/multimodal.html
```

**That's it!** 🎉 The pipeline is running and processing data.

---

## 🎯 What This Project Does

This is a **complete Lambda Architecture** implementation for processing satellite imagery data in real-time.

### Input Data
- **27,000 satellite images** (EuroSAT RGB dataset)
  - 10 land cover classes
  - 64×64 pixel JPEGs
  - Classes: Forest, River, Highway, Industrial, etc.
  
- **CSV metadata** for each image
  - NDVI (vegetation index)
  - Spectral bands (Red, Green, Blue, NIR)
  - Geospatial metadata

### What It Does
1. **Reads** CSV data + loads corresponding RGB images
2. **Extracts** image features (color statistics, brightness, contrast)
3. **Streams** unified multimodal events to Kafka
4. **Processes** in real-time with Spark Streaming
5. **Fuses** CSV and image features for advanced analytics
6. **Detects** anomalies using both data modalities
7. **Stores** results in Cassandra for low-latency access
8. **Visualizes** everything in a real-time dashboard

### Output
- **Real-time statistics** per land cover class
- **Multimodal anomaly detection** (fusion of CSV + image data)
- **Interactive dashboard** with live updates
- **REST API** for data access

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                             │
│  CSV Files (27K rows)        RGB Images (27K JPEGs)        │
└────────────┬─────────────────────────┬──────────────────────┘
             │                         │
             └─────────┐   ┌───────────┘
                       ▼   ▼
            ┏━━━━━━━━━━━━━━━━━━━━━━━━┓
            ┃  Multimodal Producer   ┃  (Python + PIL + NumPy)
            ┃  • Merge CSV + Images  ┃
            ┃  • Extract features    ┃
            ┗━━━━━━━━━━┳━━━━━━━━━━━━━┛
                       ▼
            ╔═══════════════════════╗
            ║  Apache Kafka         ║  (Message Queue)
            ║  Topic: multimodal    ║
            ╚═══════════┬═══════════╝
                        ▼
            ┏━━━━━━━━━━━━━━━━━━━━━━━━┓
            ┃  Spark Streaming      ┃  (Real-time Processing)
            ┃  • Tabular analytics  ┃
            ┃  • Image analytics    ┃
            ┃  • Multimodal fusion  ┃
            ┗━━━━━━━━━━┳━━━━━━━━━━━━━┛
                       ▼
        ┌──────────────┴──────────────┐
        ▼              ▼               ▼
┏━━━━━━━━━━━┓ ┏━━━━━━━━━━━┓ ┏━━━━━━━━━━━┓
┃ Tabular   ┃ ┃ Image     ┃ ┃ Anomalies ┃
┃ Stats     ┃ ┃ Stats     ┃ ┃ (Fusion)  ┃
┗━━━━┳━━━━━┛ ┗━━━━┳━━━━━┛ ┗━━━━┳━━━━━━┛
     └─────────────┼────────────┘
            ┏━━━━━━▼━━━━━━┓
            ┃  Cassandra  ┃  (Storage)
            ┗━━━━━━┳━━━━━━┛
                   ▼
            ┏━━━━━━━━━━━━┓
            ┃  Flask API ┃  (REST)
            ┗━━━━━━┳━━━━━┛
                   ▼
            ┏━━━━━━━━━━━━┓
            ┃  Dashboard ┃  (Visualization)
            ┗━━━━━━━━━━━━┛
```

---

## 📁 Project Structure

```
ProjectBigData/
│
├── setup.sh                    # 🚀 MAIN SETUP SCRIPT (run this!)
├── run_full_pipeline.sh        # Process all 27K events
├── test_multimodal.sh          # Quick test with subset
│
├── data/
│   ├── *.csv                   # CSV metadata files
│   └── EuroSAT_RGB/            # 27K RGB images (10 classes)
│
├── src/
│   ├── producer/
│   │   ├── kafka_producer_multimodal.py   # 🔥 Main producer
│   │   └── continuous_producer.py         # Continuous streaming
│   │
│   ├── speed_layer/
│   │   └── spark_streaming_multimodal.py  # Real-time processing
│   │
│   └── serving/
│       └── app.py                         # Flask REST API
│
├── dashboard/
│   ├── multimodal.html         # 🎨 Main dashboard (OPEN THIS!)
│   └── index.html              # Legacy dashboard
│
├── infrastructure/
│   └── docker-compose.yml      # All services definition
│
├── logs/                       # Log files
│
└── README.md                   # This file
```

---

## 📊 Usage Scenarios

### 1. Complete Setup (First Time)
```bash
./setup.sh
```
Does everything automatically. After 2-3 minutes, open: http://localhost:8000/multimodal.html

### 2. Quick Test (500 events, ~1 minute)
```bash
./test_multimodal.sh 500
```

### 3. Process All Data (27,000 events, ~20 minutes)
```bash
./run_full_pipeline.sh
```

### 4. Continuous Streaming (runs until Ctrl+C)
```bash
source .venv/bin/activate
python src/producer/continuous_producer.py --batch-size 200
```

### 5. Manual Event Production
```bash
source .venv/bin/activate
python src/producer/kafka_producer_multimodal.py --limit 1000 --delay 0.001
```

---

## 🖥️ Monitoring & Visualization

### 1. Main Dashboard (Recommended)
**URL**: http://localhost:8000/multimodal.html

**Features**:
- 4 summary statistic cards
- 4 interactive charts (NDVI, RGB, brightness, counts)
- Real-time anomaly feed
- Auto-refresh every 5 seconds

### 2. REST API
**Base URL**: http://127.0.0.1:5000

**Endpoints**:
```bash
# Summary statistics
curl http://127.0.0.1:5000/api/multimodal/summary | jq

# Tabular stats (CSV features)
curl http://127.0.0.1:5000/api/multimodal/tabular-stats | jq

# Image stats (RGB features)
curl http://127.0.0.1:5000/api/multimodal/image-stats | jq

# Anomalies (multimodal fusion)
curl http://127.0.0.1:5000/api/multimodal/anomalies | jq
```

### 3. Spark UI
**URL**: http://localhost:8080

Monitor streaming job status, execution times, and resource usage.

### 4. Direct Cassandra Queries
```bash
# View all classes
docker exec cassandra cqlsh -e "SELECT * FROM landcover.multimodal_tabular_stats;"

# View image stats
docker exec cassandra cqlsh -e "SELECT * FROM landcover.multimodal_image_stats;"

# Count anomalies
docker exec cassandra cqlsh -e "SELECT COUNT(*) FROM landcover.multimodal_anomalies;"
```

### 5. Streaming Job Logs
```bash
docker exec spark-master tail -f /tmp/multimodal_streaming.log
```

---

## 🔧 Troubleshooting

### Services Won't Start
```bash
# Stop everything
docker-compose down

# Remove volumes (fresh start)
docker-compose down -v

# Start again
./setup.sh
```

### Dashboard Shows No Data
```bash
# 1. Check API is running
curl http://127.0.0.1:5000/api/multimodal/summary

# 2. Check Cassandra has data
docker exec cassandra cqlsh -e "SELECT COUNT(*) FROM landcover.multimodal_tabular_stats;"

# 3. Restart API
pkill -f "python src/serving/app.py"
source .venv/bin/activate
python src/serving/app.py &
```

### Streaming Job Not Processing
```bash
# Check if job is running
docker exec spark-master ps aux | grep spark_streaming_multimodal

# If not, restart it
docker exec spark-master pkill -f spark_streaming_multimodal
docker exec spark-master rm -rf /tmp/spark_multimodal_ckpt
docker cp src/speed_layer/spark_streaming_multimodal.py spark-master:/opt/spark/jobs/
docker exec -d spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 \
  /opt/spark/jobs/spark_streaming_multimodal.py
```

### Kafka Issues
```bash
# Check Kafka topics
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Check messages in topic
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic multimodal-events \
  --max-messages 5
```

### Port Already in Use
```bash
# Check what's using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>

# Or change API port in src/serving/app.py
```

---

## 📚 Technical Details

### Technologies Used

**Infrastructure**:
- Apache Kafka 7.5.1 (Confluent)
- Apache Spark 3.5.1
- Apache Cassandra 4.1
- Apache Hive + HDFS
- PostgreSQL (Hive metastore)
- ZooKeeper

**Python Stack**:
- Python 3.11
- PySpark 3.5.1
- kafka-python 2.0.2
- cassandra-driver 3.29.0
- Flask 3.0.2
- PIL (Pillow) 12.0.0
- NumPy 2.3.5
- pandas

**Frontend**:
- Chart.js 4.4.0
- Vanilla JavaScript
- HTML5/CSS3

### Data Processing Pipeline

1. **Producer** (`kafka_producer_multimodal.py`):
   - Loads CSV files (NDVI, spectral bands)
   - Matches RGB images by class and ID
   - Extracts image features using PIL/NumPy
   - Produces unified events to Kafka
   - Shuffles data to ensure class diversity

2. **Streaming** (`spark_streaming_multimodal.py`):
   - Consumes from Kafka every 5 seconds
   - Parses JSON with multimodal schema
   - Three-stage processing:
     - Tabular: Aggregate CSV features by class
     - Image: Aggregate RGB features by class
     - Fusion: Detect anomalies using both modalities
   - Writes to 3 Cassandra tables

3. **API** (`app.py`):
   - Flask REST API
   - 8 endpoints (4 multimodal + 4 legacy)
   - CORS enabled
   - Direct Cassandra queries

4. **Dashboard** (`multimodal.html`):
   - Real-time Chart.js visualizations
   - 4 summary cards
   - 4 interactive charts
   - Live anomaly feed
   - Auto-refresh (5s interval)

### Performance

- **Producer**: 100-200 events/second
- **Image Processing**: ~5ms per 64×64 JPEG
- **Streaming Latency**: 5-15 seconds
- **Event Size**: ~700 bytes (500 tabular + 200 image)
- **Full Dataset**: 27K events in 15-30 minutes

### Land Cover Classes

1. **AnnualCrop** - Agricultural crops (seasonal)
2. **Forest** - Dense tree coverage
3. **HerbaceousVegetation** - Grasslands, meadows
4. **Highway** - Roads, paved surfaces
5. **Industrial** - Factories, warehouses
6. **Pasture** - Grazing land
7. **PermanentCrop** - Orchards, vineyards
8. **Residential** - Urban housing
9. **River** - Flowing water bodies
10. **SeaLake** - Large water bodies

---

## 📖 Additional Documentation

- **QUICKSTART.md** - Detailed setup and configuration
- **MULTIMODAL_README.md** - Technical architecture deep dive
- **STATUS.md** - Current implementation status

---

## 🎓 Learning Outcomes

This project demonstrates:
- ✅ Lambda Architecture (batch + speed + serving layers)
- ✅ Real-time stream processing with Spark
- ✅ Distributed systems (Kafka, Cassandra)
- ✅ Multimodal data fusion (CSV + images)
- ✅ Computer vision (image feature extraction)
- ✅ RESTful API design
- ✅ Real-time data visualization
- ✅ Docker containerization
- ✅ Big data engineering patterns

---

## 🤝 Support

If you encounter issues:

1. Check the **Troubleshooting** section above
2. Review logs:
   - API: `logs/api.log`
   - Dashboard: `logs/dashboard.log`
   - Streaming: `docker exec spark-master tail /tmp/multimodal_streaming.log`
3. Verify all services: `docker ps`
4. Check documentation in `QUICKSTART.md`

---

## 📄 License

This project is for educational purposes.

---

**🚀 Ready to start? Run: `./setup.sh`**
