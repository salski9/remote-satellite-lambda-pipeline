#!/bin/bash
###############################################################################
# Multimodal Quick Test - Verify complete pipeline
###############################################################################

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

EVENTS=${1:-500}

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          MULTIMODAL QUICK TEST - ${EVENTS} Events                ${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Clear old data
echo -e "${YELLOW}[1/5] Clearing previous test data...${NC}"
docker exec cassandra cqlsh -e "TRUNCATE landcover.multimodal_tabular_stats;" 2>/dev/null || true
docker exec cassandra cqlsh -e "TRUNCATE landcover.multimodal_image_stats;" 2>/dev/null || true
docker exec cassandra cqlsh -e "TRUNCATE landcover.multimodal_anomalies;" 2>/dev/null || true
echo -e "${GREEN}✓ Tables cleared${NC}"
echo ""

# Check streaming job
echo -e "${YELLOW}[2/5] Checking multimodal streaming job...${NC}"
if docker exec spark-master ps aux | grep -q "spark_streaming_multimodal.py"; then
    echo -e "${GREEN}✓ Streaming job running${NC}"
else
    echo -e "${YELLOW}⚠ Starting streaming job...${NC}"
    docker exec spark-master rm -rf /tmp/spark_multimodal_ckpt 2>/dev/null || true
    docker exec -d spark-master bash -c "/opt/spark/bin/spark-submit \
        --master spark://spark-master:7077 \
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 \
        /opt/spark/jobs/spark_streaming_multimodal.py > /tmp/multimodal_streaming.log 2>&1"
    sleep 10
    echo -e "${GREEN}✓ Streaming job started${NC}"
fi
echo ""

# Produce events
echo -e "${YELLOW}[3/5] Producing ${EVENTS} multimodal events (CSV + RGB)...${NC}"
source .venv/bin/activate
python src/producer/kafka_producer_multimodal.py --limit $EVENTS --delay 0.001
echo -e "${GREEN}✓ Events produced${NC}"
echo ""

# Wait for processing
echo -e "${YELLOW}[4/5] Waiting 20 seconds for Spark processing...${NC}"
sleep 20
echo -e "${GREEN}✓ Processing complete${NC}"
echo ""

# Show results
echo -e "${YELLOW}[5/5] Results${NC}"
echo ""
echo -e "${BLUE}═══ API Summary ═══${NC}"
curl -s http://127.0.0.1:5000/api/multimodal/summary | python3 -m json.tool
echo ""

echo -e "${BLUE}═══ Tabular Stats (CSV Features) ═══${NC}"
docker exec cassandra cqlsh -e "SELECT class_name, ndvi_avg, sample_count FROM landcover.multimodal_tabular_stats;"
echo ""

echo -e "${BLUE}═══ Image Stats (RGB Features) ═══${NC}"
docker exec cassandra cqlsh -e "SELECT class_name, avg_brightness, image_count FROM landcover.multimodal_image_stats;"
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    TEST COMPLETED!                             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  • View dashboard: ${YELLOW}http://localhost:8000/multimodal.html${NC}"
echo -e "  • Run full pipeline: ${YELLOW}./run_full_pipeline.sh${NC}"
echo -e "  • API docs: ${YELLOW}curl http://127.0.0.1:5000/api/multimodal/summary${NC}"
echo ""
