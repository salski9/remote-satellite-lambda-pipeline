#!/bin/bash
###############################################################################
# Multimodal Lambda Architecture Pipeline - Full Automation Script
###############################################################################

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
BATCH_SIZE=500
DELAY=0.001
TOTAL_EVENTS=${1:-27000}  # Default: process all 27,000 images

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  MULTIMODAL LAMBDA ARCHITECTURE - FULL PIPELINE AUTOMATION     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Total events to process: ${TOTAL_EVENTS}${NC}"
echo -e "${GREEN}Batch size: ${BATCH_SIZE}${NC}"
echo -e "${GREEN}Delay per event: ${DELAY}s${NC}"
echo ""

# Check services
echo -e "${YELLOW}[1/6] Checking infrastructure status...${NC}"
if ! docker ps | grep -q "kafka"; then
    echo -e "${RED}✗ Kafka not running! Start with: docker-compose up -d${NC}"
    exit 1
fi
if ! docker ps | grep -q "cassandra"; then
    echo -e "${RED}✗ Cassandra not running! Start with: docker-compose up -d${NC}"
    exit 1
fi
if ! docker ps | grep -q "spark-master"; then
    echo -e "${RED}✗ Spark not running! Start with: docker-compose up -d${NC}"
    exit 1
fi
echo -e "${GREEN}✓ All services running${NC}"
echo ""

# Check streaming job
echo -e "${YELLOW}[2/6] Checking Spark streaming job...${NC}"
if docker exec spark-master ps aux | grep -q "spark_streaming_multimodal.py"; then
    echo -e "${GREEN}✓ Multimodal streaming job is running${NC}"
else
    echo -e "${YELLOW}⚠ Starting multimodal streaming job...${NC}"
    docker exec spark-master rm -rf /tmp/spark_multimodal_ckpt
    docker exec -d spark-master bash -c "/opt/spark/bin/spark-submit \
        --master spark://spark-master:7077 \
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 \
        /opt/spark/jobs/spark_streaming_multimodal.py > /tmp/multimodal_streaming.log 2>&1"
    sleep 10
    echo -e "${GREEN}✓ Streaming job started${NC}"
fi
echo ""

# Check API
echo -e "${YELLOW}[3/6] Checking Flask API...${NC}"
if curl -s http://127.0.0.1:5000/api/batch/class-stats > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Flask API is running on port 5000${NC}"
else
    echo -e "${YELLOW}⚠ API not responding. Start with: python src/serving/app.py${NC}"
fi
echo ""

# Clear old Cassandra data for fresh run
echo -e "${YELLOW}Clearing existing Cassandra data...${NC}"
docker exec cassandra cqlsh -e "TRUNCATE landcover.multimodal_tabular_stats;" 2>/dev/null || true
docker exec cassandra cqlsh -e "TRUNCATE landcover.multimodal_image_stats;" 2>/dev/null || true
docker exec cassandra cqlsh -e "TRUNCATE landcover.multimodal_anomalies;" 2>/dev/null || true
echo -e "${GREEN}✓ Tables cleared${NC}"
echo ""

# Produce events in batches
echo -e "${YELLOW}[4/6] Producing multimodal events...${NC}"
BATCHES=$((($TOTAL_EVENTS + $BATCH_SIZE - 1) / $BATCH_SIZE))
echo -e "${GREEN}Processing ${BATCHES} batches of ${BATCH_SIZE} events...${NC}"
echo ""

source .venv/bin/activate

for ((i=1; i<=BATCHES; i++)); do
    EVENTS=$BATCH_SIZE
    if [ $i -eq $BATCHES ]; then
        # Last batch might be smaller
        REMAINING=$(($TOTAL_EVENTS - ($BATCH_SIZE * ($BATCHES - 1))))
        EVENTS=$REMAINING
    fi
    
    echo -e "${BLUE}Batch $i/$BATCHES: Producing ${EVENTS} events...${NC}"
    python src/producer/kafka_producer_multimodal.py --limit $EVENTS --delay $DELAY
    
    # Show progress every 5 batches
    if [ $((i % 5)) -eq 0 ] || [ $i -eq $BATCHES ]; then
        PROCESSED=$(($i * $BATCH_SIZE))
        if [ $PROCESSED -gt $TOTAL_EVENTS ]; then
            PROCESSED=$TOTAL_EVENTS
        fi
        echo -e "${GREEN}Progress: ${PROCESSED}/${TOTAL_EVENTS} events produced${NC}"
        echo ""
    fi
    
    # Wait for processing between large batches
    if [ $((i % 10)) -eq 0 ]; then
        echo -e "${YELLOW}Waiting 20 seconds for Spark processing...${NC}"
        sleep 20
    fi
done

echo ""
echo -e "${GREEN}✓ All events produced!${NC}"
echo ""

# Wait for final processing
echo -e "${YELLOW}[5/6] Waiting for final Spark processing (30 seconds)...${NC}"
sleep 30
echo -e "${GREEN}✓ Processing complete${NC}"
echo ""

# Verify results
echo -e "${YELLOW}[6/6] Verifying results...${NC}"
echo ""
echo -e "${BLUE}═══ Multimodal Tabular Stats (CSV data) ═══${NC}"
docker exec cassandra cqlsh -e "SELECT class_name, ndvi_avg, brightness_avg, sample_count FROM landcover.multimodal_tabular_stats;"
echo ""

echo -e "${BLUE}═══ Multimodal Image Stats (RGB data) ═══${NC}"
docker exec cassandra cqlsh -e "SELECT class_name, avg_brightness, avg_contrast, image_count FROM landcover.multimodal_image_stats;"
echo ""

echo -e "${BLUE}═══ Multimodal Anomalies (Fusion) ═══${NC}"
docker exec cassandra cqlsh -e "SELECT COUNT(*) as anomaly_count FROM landcover.multimodal_anomalies;"
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║               PIPELINE COMPLETED SUCCESSFULLY!                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. View dashboard: ${YELLOW}http://localhost:8000${NC}"
echo -e "  2. Check API: ${YELLOW}curl http://127.0.0.1:5000/api/realtime/ndvi${NC}"
echo -e "  3. Monitor Spark UI: ${YELLOW}http://localhost:8080${NC}"
echo ""
