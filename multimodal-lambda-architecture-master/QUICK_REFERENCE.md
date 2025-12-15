# 📚 Quick Reference Guide

## 🎯 Essential Commands

### First Time Setup
```bash
./setup.sh
```
**Takes 2-3 minutes. Does everything automatically!**

### View Dashboard
```bash
# Open in browser:
http://localhost:8000/multimodal.html
```

### Process All Data (27,000 events)
```bash
./run_full_pipeline.sh
```

### Quick Test (500 events)
```bash
./test_multimodal.sh 500
```

### Continuous Streaming
```bash
source .venv/bin/activate
python src/producer/continuous_producer.py
```

---

## 🔍 Monitoring

### Check Services
```bash
docker ps
```

### Check Streaming Job
```bash
docker exec spark-master ps aux | grep spark_streaming_multimodal
```

### View Logs
```bash
# Streaming logs
docker exec spark-master tail -f /tmp/multimodal_streaming.log

# API logs
tail -f logs/api.log

# Dashboard logs
tail -f logs/dashboard.log
```

### Query Data
```bash
# All classes
docker exec cassandra cqlsh -e "SELECT class_name, sample_count FROM landcover.multimodal_tabular_stats;"

# Anomalies count
docker exec cassandra cqlsh -e "SELECT COUNT(*) FROM landcover.multimodal_anomalies;"

# Via API
curl http://127.0.0.1:5000/api/multimodal/summary | jq
```

---

## 🛠️ Troubleshooting

### Restart Everything
```bash
docker-compose down
./setup.sh
```

### Restart Streaming Job
```bash
docker exec spark-master pkill -f spark_streaming_multimodal
docker exec spark-master rm -rf /tmp/spark_multimodal_ckpt
docker cp src/speed_layer/spark_streaming_multimodal.py spark-master:/opt/spark/jobs/
docker exec -d spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 \
  /opt/spark/jobs/spark_streaming_multimodal.py
```

### Restart API
```bash
pkill -f "python src/serving/app.py"
source .venv/bin/activate
python src/serving/app.py > logs/api.log 2>&1 &
```

### Clear All Data
```bash
docker exec cassandra cqlsh -e "TRUNCATE landcover.multimodal_tabular_stats;"
docker exec cassandra cqlsh -e "TRUNCATE landcover.multimodal_image_stats;"
docker exec cassandra cqlsh -e "TRUNCATE landcover.multimodal_anomalies;"
```

---

## 📊 URLs Quick Access

| Service | URL |
|---------|-----|
| **Dashboard** | http://localhost:8000/multimodal.html |
| **API** | http://127.0.0.1:5000 |
| **Spark UI** | http://localhost:8080 |
| **HDFS UI** | http://localhost:9870 |

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `setup.sh` | Complete automated setup |
| `run_full_pipeline.sh` | Process all 27K events |
| `test_multimodal.sh` | Quick test with subset |
| `src/producer/kafka_producer_multimodal.py` | Main data producer |
| `src/producer/continuous_producer.py` | Continuous streaming |
| `src/speed_layer/spark_streaming_multimodal.py` | Real-time processing |
| `src/serving/app.py` | REST API |
| `dashboard/multimodal.html` | Main dashboard |

---

## 🎨 Data Flow

```
CSV + Images → Producer → Kafka → Spark Streaming → Cassandra → API → Dashboard
```

---

## ⚡ Performance Metrics

- **Producer**: 100-200 events/sec
- **Streaming**: 5-15 sec latency
- **Image Processing**: ~5ms per image
- **Full Dataset**: 15-30 minutes

---

For detailed documentation, see **README.md**
