#!/bin/bash
###############################################################################
#                     MULTIMODAL LAMBDA ARCHITECTURE                          #
#                        COMPLETE SETUP SCRIPT                                #
###############################################################################

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

clear

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║           🌍 MULTIMODAL LAMBDA ARCHITECTURE PIPELINE 🌍                ║
║                                                                       ║
║     Real-time Satellite Image Processing with CSV + RGB Fusion       ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo ""
echo -e "${BLUE}This script will:${NC}"
echo "  1. Start all Docker infrastructure (Kafka, Spark, Cassandra, etc.)"
echo "  2. Initialize Cassandra database schema"
echo "  3. Deploy Spark streaming job"
echo "  4. Start Flask API server"
echo "  5. Start dashboard web server"
echo "  6. Run initial test with sample data"
echo ""
read -p "Press Enter to continue..."
echo ""

# ============================================================================
# STEP 1: START DOCKER INFRASTRUCTURE
# ============================================================================
echo -e "${YELLOW}[1/6] Starting Docker Infrastructure...${NC}"
echo -e "${BLUE}Starting: Kafka, Zookeeper, Spark, Cassandra, HDFS, Hive${NC}"
echo ""

if ! docker ps | grep -q "kafka"; then
    docker compose -f infrastructure/docker-compose.yml up -d
    echo ""
    echo -e "${YELLOW}⏳ Waiting 30 seconds for services to initialize...${NC}"
    sleep 30
else
    echo -e "${GREEN}✓ Services already running${NC}"
fi

# Check services
echo ""
echo -e "${CYAN}Service Status:${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "kafka|spark|cassandra|zookeeper" || true
echo ""
echo -e "${GREEN}✓ Docker infrastructure running${NC}"
sleep 2
echo ""

# ============================================================================
# STEP 2: INITIALIZE CASSANDRA SCHEMA
# ============================================================================
echo -e "${YELLOW}[2/6] Initializing Cassandra Database...${NC}"
echo -e "${BLUE}Creating keyspace and multimodal tables${NC}"
echo ""

# Wait for Cassandra to be fully ready
echo -e "${CYAN}Waiting for Cassandra to be ready...${NC}"
for i in {1..30}; do
    if docker exec cassandra cqlsh -e "DESCRIBE KEYSPACES" > /dev/null 2>&1; then
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

# Apply schema using the infrastructure file
docker exec -i cassandra cqlsh < infrastructure/cassandra_multimodal.cql 2>/dev/null || \
    docker exec cassandra cqlsh << 'CQLEOF'
CREATE KEYSPACE IF NOT EXISTS landcover 
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

CREATE TABLE IF NOT EXISTS landcover.multimodal_tabular_stats (
    class_name text PRIMARY KEY,
    ndvi_avg double,
    ndvi_stddev double,
    red_avg double,
    green_avg double,
    blue_avg double,
    nir_avg double,
    brightness_avg double,
    sample_count bigint
);

CREATE TABLE IF NOT EXISTS landcover.multimodal_image_stats (
    class_name text PRIMARY KEY,
    avg_red_channel double,
    avg_green_channel double,
    avg_blue_channel double,
    avg_brightness double,
    avg_contrast double,
    image_count bigint
);

CREATE TABLE IF NOT EXISTS landcover.multimodal_anomalies (
    class_name text,
    timestamp timestamp,
    image_id text,
    ndvi_mean double,
    brightness double,
    contrast double,
    anomaly_type text,
    PRIMARY KEY (class_name, timestamp, image_id)
);
CQLEOF

echo -e "${GREEN}✓ Cassandra schema initialized${NC}"
sleep 2
echo ""

# ============================================================================
# STEP 3: DEPLOY SPARK STREAMING JOB
# ============================================================================
echo -e "${YELLOW}[3/6] Deploying Spark Streaming Job...${NC}"
echo -e "${BLUE}Multimodal real-time processing: CSV + RGB fusion${NC}"
echo ""

# Prepare Spark container (fix Ivy cache directory for package downloads)
echo -e "${CYAN}Preparing Spark environment...${NC}"
docker exec -u root spark-master mkdir -p /home/spark/.ivy2/cache 2>/dev/null || true
docker exec -u root spark-master chown -R spark:spark /home/spark 2>/dev/null || true

# Copy streaming job to Spark container
docker exec spark-master mkdir -p /opt/spark/jobs
docker cp src/speed_layer/spark_streaming_multimodal.py spark-master:/opt/spark/jobs/

# Stop any existing streaming job
docker exec spark-master pkill -f spark_streaming_multimodal 2>/dev/null || true
docker exec spark-master rm -rf /tmp/spark_multimodal_ckpt 2>/dev/null || true

# Start streaming job
docker exec -d spark-master bash -c "/opt/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 \
    /opt/spark/jobs/spark_streaming_multimodal.py > /tmp/multimodal_streaming.log 2>&1"

echo -e "${CYAN}Waiting for Spark job to initialize (downloading packages)...${NC}"
sleep 15

# Check if job is running
RETRY=0
MAX_RETRIES=6
while [ $RETRY -lt $MAX_RETRIES ]; do
    if docker exec spark-master ps aux | grep -q "[s]park_streaming_multimodal.py"; then
        echo -e "${GREEN}✓ Spark streaming job deployed and running${NC}"
        break
    fi
    echo -n "."
    sleep 5
    RETRY=$((RETRY+1))
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo ""
    echo -e "${RED}⚠ Warning: Streaming job may not have started properly${NC}"
    echo -e "${YELLOW}Check logs: docker exec spark-master tail -50 /tmp/multimodal_streaming.log${NC}"
fi
sleep 2
echo ""

# ============================================================================
# STEP 4: START FLASK API
# ============================================================================
echo -e "${YELLOW}[4/6] Starting Flask API Server...${NC}"
echo -e "${BLUE}REST API with multimodal endpoints${NC}"
echo ""

# Stop any existing API
pkill -f "python src/serving/app.py" 2>/dev/null || true
sleep 2

# Verify Cassandra keyspace exists before starting API
if ! docker exec cassandra cqlsh -e "DESCRIBE KEYSPACE landcover;" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cassandra keyspace not found. Reinitializing...${NC}"
    docker exec -i cassandra cqlsh < infrastructure/cassandra_multimodal.cql
    sleep 2
fi

# Start API in background
source .venv/bin/activate
nohup python src/serving/app.py > logs/api.log 2>&1 &
API_PID=$!

# Wait for API to start and verify it's working
echo -e "${CYAN}Waiting for API to start...${NC}"
RETRY=0
MAX_RETRIES=10
while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s http://127.0.0.1:5000/api/multimodal/summary > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Flask API running on http://127.0.0.1:5000${NC}"
        echo -e "${CYAN}  PID: $API_PID${NC}"
        break
    fi
    echo -n "."
    sleep 2
    RETRY=$((RETRY+1))
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo ""
    echo -e "${RED}⚠ API failed to start. Check logs/api.log${NC}"
fi
sleep 2
echo ""

# ============================================================================
# STEP 5: START DASHBOARD
# ============================================================================
echo -e "${YELLOW}[5/6] Starting Dashboard Web Server...${NC}"
echo -e "${BLUE}Real-time visualization dashboard${NC}"
echo ""

# Stop any existing dashboard server
pkill -f "python.*http.server.*8000" 2>/dev/null || true
sleep 1

# Start dashboard server
cd dashboard
nohup python -m http.server 8000 > ../logs/dashboard.log 2>&1 &
DASH_PID=$!
cd ..

sleep 2
echo -e "${GREEN}✓ Dashboard running on http://localhost:8000${NC}"
echo -e "${CYAN}  PID: $DASH_PID${NC}"
sleep 2
echo ""

# ============================================================================
# STEP 6: RUN INITIAL TEST
# ============================================================================
echo -e "${YELLOW}[6/6] Running Initial Test...${NC}"
echo -e "${BLUE}Processing 500 multimodal events (all 10 land cover classes)${NC}"
echo ""

python src/producer/kafka_producer_multimodal.py --limit 500 --delay 0.001

echo ""
echo -e "${CYAN}⏳ Waiting 20 seconds for Spark to process events...${NC}"
sleep 20
echo ""

# ============================================================================
# VERIFICATION
# ============================================================================
echo -e "${YELLOW}Verifying Results...${NC}"
echo ""

echo -e "${CYAN}═══ Classes Processed ═══${NC}"
docker exec cassandra cqlsh -e "SELECT class_name, sample_count FROM landcover.multimodal_tabular_stats;" 2>/dev/null || echo "Waiting for data..."
echo ""

echo -e "${CYAN}═══ API Summary ═══${NC}"
curl -s http://127.0.0.1:5000/api/multimodal/summary 2>/dev/null | python3 -m json.tool || echo "API initializing..."
echo ""

# ============================================================================
# SUCCESS MESSAGE
# ============================================================================
echo -e "${GREEN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║                  ✅  SETUP COMPLETED SUCCESSFULLY!  ✅                  ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"
echo ""

echo -e "${CYAN}📊 Access Points:${NC}"
echo ""
echo -e "  ${GREEN}🌐 Dashboard (MAIN):${NC}  http://localhost:8000/multimodal.html"
echo -e "     ${BLUE}→ Real-time charts, statistics, and anomaly feed${NC}"
echo ""
echo -e "  ${GREEN}🔌 API Endpoints:${NC}     http://127.0.0.1:5000"
echo -e "     ${BLUE}→ /api/multimodal/summary${NC}"
echo -e "     ${BLUE}→ /api/multimodal/tabular-stats${NC}"
echo -e "     ${BLUE}→ /api/multimodal/image-stats${NC}"
echo -e "     ${BLUE}→ /api/multimodal/anomalies${NC}"
echo ""
echo -e "  ${GREEN}⚡ Spark UI:${NC}           http://localhost:8080"
echo -e "     ${BLUE}→ Monitor streaming job status${NC}"
echo ""

echo -e "${CYAN}🎯 Next Steps:${NC}"
echo ""
echo -e "  ${YELLOW}1.${NC} Open dashboard:  ${GREEN}http://localhost:8000/multimodal.html${NC}"
echo -e "  ${YELLOW}2.${NC} Process all data: ${GREEN}./run_full_pipeline.sh${NC}"
echo -e "  ${YELLOW}3.${NC} Continuous mode:  ${GREEN}python src/producer/continuous_producer.py${NC}"
echo ""

echo -e "${CYAN}📚 Documentation:${NC}"
echo -e "  ${BLUE}→ README.md          ${NC} Complete project overview"
echo -e "  ${BLUE}→ QUICKSTART.md      ${NC} Detailed usage guide"
echo -e "  ${BLUE}→ MULTIMODAL_README.md${NC} Technical architecture"
echo ""

echo -e "${CYAN}🛠️  Useful Commands:${NC}"
echo ""
echo -e "  ${BLUE}# Check streaming job status${NC}"
echo -e "  docker exec spark-master ps aux | grep spark_streaming_multimodal"
echo ""
echo -e "  ${BLUE}# View streaming logs${NC}"
echo -e "  docker exec spark-master tail -f /tmp/multimodal_streaming.log"
echo ""
echo -e "  ${BLUE}# Query Cassandra directly${NC}"
echo -e "  docker exec cassandra cqlsh -e \"SELECT * FROM landcover.multimodal_tabular_stats;\""
echo ""
echo -e "  ${BLUE}# Stop all services${NC}"
echo -e "  docker-compose down"
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}💡 The dashboard updates automatically every 5 seconds!${NC}"
echo ""
