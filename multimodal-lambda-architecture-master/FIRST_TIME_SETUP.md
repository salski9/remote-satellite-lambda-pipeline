# 🚀 FIRST TIME SETUP - Complete Guide

## Prerequisites

- Docker & Docker Compose installed
- Python 3.11+ installed
- 8GB+ RAM recommended
- Linux/macOS (tested on Ubuntu)

---

## ⚡ Quick Setup (3 Steps)

### Step 1: Install Python Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Fix Spark Container (One-Time Setup)

```bash
# Start Docker services
docker compose -f infrastructure/docker-compose.yml up -d

# Wait for services to start (60 seconds)
sleep 60

# Fix Spark Ivy cache directory (required for package downloads)
docker exec -u root spark-master mkdir -p /home/spark/.ivy2/cache
docker exec -u root spark-master chown -R spark:spark /home/spark
```

### Step 3: Run Setup Script

```bash
./setup.sh
```

**Press Enter** when prompted. The script will:
- ✓ Initialize Cassandra database
- ✓ Deploy Spark streaming job
- ✓ Start Flask API server
- ✓ Start dashboard web server  
- ✓ Run initial test with 500 events

---

## 🌐 Access the Application

### Main Dashboard
**http://localhost:8000/multimodal.html**

You'll see:
- Real-time statistics for all 10 land cover classes
- Interactive charts (NDVI, RGB, brightness, contrast)
- Live anomaly detection feed
- Auto-refresh every 5 seconds

### API Endpoints
**http://127.0.0.1:5000**

- `/api/multimodal/summary` - Overall statistics
- `/api/multimodal/tabular-stats` - CSV-based stats
- `/api/multimodal/image-stats` - RGB image stats
- `/api/multimodal/anomalies` - Detected anomalies

### Monitoring
- **Spark UI**: http://localhost:8080
- **HDFS UI**: http://localhost:9870

---

## 📊 Land Cover Classes (10 Total)

1. **AnnualCrop** - Agricultural crops
2. **Forest** - Dense tree coverage
3. **HerbaceousVegetation** - Grasslands
4. **Highway** - Roads and paved areas
5. **Industrial** - Factories and warehouses
6. **Pasture** - Grazing land
7. **PermanentCrop** - Orchards and vineyards
8. **Residential** - Urban housing
9. **River** - Flowing water
10. **SeaLake** - Lakes and seas

---

## 🧪 Testing the Pipeline

### Quick Test (500 events)
```bash
./test_multimodal.sh 500
```

### Full Pipeline (27,000 events)
```bash
./run_full_pipeline.sh
```

### Continuous Streaming
```bash
source .venv/bin/activate
python src/producer/continuous_producer.py
```

---

## ✅ Verification Commands

### Check Services
```bash
docker ps | grep -E "kafka|spark|cassandra"
```

### Check Spark Streaming Job
```bash
docker exec spark-master ps aux | grep spark_streaming_multimodal
```

### Check API
```bash
curl http://127.0.0.1:5000/api/multimodal/summary | jq
```

### Check Cassandra Data
```bash
docker exec cassandra cqlsh -e "SELECT class_name, sample_count FROM landcover.multimodal_tabular_stats;"
```

### View Spark Logs
```bash
docker exec spark-master tail -f /tmp/multimodal_streaming.log
```

---

## ⚠️ Troubleshooting

### Problem: Spark job not starting
**Symptom**: No data in Cassandra after producing events  
**Solution**:
```bash
# Check Ivy cache directory exists
docker exec spark-master ls -la /home/spark/.ivy2/cache

# If not, create it:
docker exec -u root spark-master mkdir -p /home/spark/.ivy2/cache
docker exec -u root spark-master chown -R spark:spark /home/spark

# Restart Spark job
docker exec spark-master pkill -f spark_streaming_multimodal
docker exec -d spark-master bash -c "/opt/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 \
    /opt/spark/jobs/spark_streaming_multimodal.py > /tmp/multimodal_streaming.log 2>&1"
```

### Problem: API not connecting to Cassandra
**Symptom**: API returns connection errors  
**Solution**:
```bash
# Check if keyspace exists
docker exec cassandra cqlsh -e "DESCRIBE KEYSPACES;"

# If 'landcover' not in list, initialize schema:
docker exec -i cassandra cqlsh < infrastructure/cassandra_multimodal.cql

# Restart API
pkill -f "python src/serving/app.py"
source .venv/bin/activate
python src/serving/app.py > logs/api.log 2>&1 &
```

### Problem: Dashboard shows no data
**Solution**:
```bash
# 1. Verify services are running
docker ps

# 2. Check API is responding
curl http://127.0.0.1:5000/api/multimodal/summary

# 3. If API returns 0 events, produce some:
source .venv/bin/activate
python src/producer/kafka_producer_multimodal.py --limit 100 --delay 0.001

# 4. Wait 20 seconds and refresh dashboard
```

### Problem: Docker services won't start
**Solution**:
```bash
docker compose -f infrastructure/docker-compose.yml down
docker compose -f infrastructure/docker-compose.yml up -d
sleep 60  # Wait for services to initialize
```

### Problem: Want to start completely fresh
**Solution**:
```bash
./cleanup.sh
docker compose -f infrastructure/docker-compose.yml down
# Then follow setup steps from beginning
```

---

## 🔄 Daily Usage (After First Setup)

If you've already completed the first-time setup, subsequent runs are simpler:

```bash
# 1. Activate Python environment
source .venv/bin/activate

# 2. Start services (if not running)
docker compose -f infrastructure/docker-compose.yml up -d

# 3. Check if streaming job is running
docker exec spark-master ps aux | grep spark_streaming_multimodal

# 4. If not running, restart it:
./setup.sh
# (or manually deploy just the Spark job)

# 5. Open dashboard
# http://localhost:8000/multimodal.html
```

---

## 📁 Project Structure

```
ProjectBigData/
├── setup.sh                    ⭐ Main setup script
├── test_multimodal.sh          🧪 Quick test
├── run_full_pipeline.sh        📊 Process all data
├── cleanup.sh                  🧹 Reset project
├── infrastructure/
│   ├── docker-compose.yml      🐋 All services
│   ├── cassandra_multimodal.cql 💾 Database schema
│   └── init_hdfs.sh            💾 HDFS setup
├── src/
│   ├── producer/               📤 Kafka producers
│   ├── speed_layer/            ⚡ Spark streaming
│   ├── serving/                🔌 Flask API
│   └── batch_layer/            📊 Batch processing
├── dashboard/
│   └── multimodal.html         🌐 Main dashboard
└── data/
    ├── *.csv                   📄 Metadata (27K rows)
    └── EuroSAT_RGB/            🖼️  Images (27K JPEGs)
```

---

## 🎯 What Gets Processed

### Input Data
- **27,000 satellite images** (RGB JPEGs, 64x64 pixels)
- **4 CSV files** with tabular features:
  - NDVI statistics (vegetation index)
  - Spectral band data (B02-B08)
  - Class labels (10 land cover types)

### Processing Pipeline
1. **Producer**: Reads CSV + loads RGB images → Kafka
2. **Spark Streaming**: Processes both modalities in real-time
3. **Cassandra**: Stores aggregated statistics
4. **API**: Serves data to dashboard
5. **Dashboard**: Visualizes results with auto-refresh

### Output
- Real-time statistics per class
- Multimodal anomaly detection
- Interactive visualizations
- ~100-200 events/second throughput

---

## 📚 Additional Documentation

- **README.md** - Complete project overview
- **QUICK_REFERENCE.md** - Command cheat sheet
- **MULTIMODAL_README.md** - Technical architecture details
- **PROJECT_STRUCTURE.txt** - Visual project map

---

## ✨ Success Checklist

After setup, verify these are working:

- [ ] Docker containers running (kafka, spark, cassandra)
- [ ] Spark streaming job active
- [ ] Flask API responding on port 5000
- [ ] Dashboard accessible on port 8000
- [ ] Test events produce data in all 10 classes
- [ ] Dashboard shows real-time updates

---

## 💡 Tips

1. **First run takes longer** (5-10 minutes) due to:
   - Docker image downloads
   - Spark package downloads (Kafka connector, Cassandra connector)
   - Service initialization

2. **Subsequent runs are faster** (1-2 minutes)

3. **Monitor resources**: Keep an eye on RAM usage
   - Kafka: ~512MB
   - Spark: ~2GB
   - Cassandra: ~1GB

4. **Dashboard auto-refreshes**: No need to manually reload

5. **Check logs** if something seems wrong:
   - Spark: `docker exec spark-master tail -f /tmp/multimodal_streaming.log`
   - API: `tail -f logs/api.log`

---

## 🚀 Ready to Start?

```bash
# Complete first-time setup (copy-paste all):
python3 -m venv .venv && \
source .venv/bin/activate && \
pip install -r requirements.txt && \
docker compose -f infrastructure/docker-compose.yml up -d && \
sleep 60 && \
docker exec -u root spark-master mkdir -p /home/spark/.ivy2/cache && \
docker exec -u root spark-master chown -R spark:spark /home/spark && \
./setup.sh
```

Then open: **http://localhost:8000/multimodal.html** 🎉
