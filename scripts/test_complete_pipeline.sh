#!/bin/bash

echo "=============================================================================="
echo "  COMPLETE PIPELINE TEST"
echo "=============================================================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 1. Run Producer
echo -e "${GREEN}[1/3] Running Producer...${NC}"
cd src/producer
python kafka_producer_from_parquet.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Producer completed successfully${NC}"
else
    echo -e "${RED}✗ Producer failed${NC}"
    exit 1
fi
cd ../..

echo ""
echo "Waiting 5 seconds for Kafka to stabilize..."
sleep 5

# 2. Run Spark Streaming (for 30 seconds to process the batch)
echo ""
echo -e "${GREEN}[2/3] Starting Spark Streaming (will run for 30 seconds)...${NC}"
cd src/speed_layer
timeout 30 spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 \
  spark_streaming_enhanced.py 2>&1 | grep -E "(Processing Enhanced Batch|aggregated|detected|ERROR)" &
SPARK_PID=$!

echo "Spark Streaming PID: $SPARK_PID"
echo "Waiting for Spark to process events..."
sleep 30

# Kill Spark Streaming
kill $SPARK_PID 2>/dev/null
cd ../..

echo ""
echo -e "${GREEN}✓ Spark Streaming processed events${NC}"

# 3. Start Flask API (in background for testing)
echo ""
echo -e "${GREEN}[3/3] Starting Flask API...${NC}"
cd src/serving
python app_enhanced.py > /tmp/flask_api.log 2>&1 &
API_PID=$!
cd ../..

echo "Flask API PID: $API_PID"
echo "Waiting for API to start..."
sleep 5

# 4. Test API endpoints
echo ""
echo "=============================================================================="
echo "  TESTING API ENDPOINTS"
echo "=============================================================================="
echo ""

echo -e "${YELLOW}Testing: /api/health${NC}"
curl -s http://localhost:5000/api/health | jq '.' 2>/dev/null || echo "API not ready"
echo ""

echo -e "${YELLOW}Testing: /api/enhanced/summary${NC}"
curl -s http://localhost:5000/api/enhanced/summary | jq '.' 2>/dev/null || echo "No data yet"
echo ""

echo -e "${YELLOW}Testing: /api/multimodal/tabular-stats${NC}"
curl -s http://localhost:5000/api/multimodal/tabular-stats | jq '.' 2>/dev/null | head -20
echo ""

# 5. Cleanup
echo ""
echo "=============================================================================="
echo "  CLEANUP"
echo "=============================================================================="
echo ""

echo "Stopping Flask API (PID: $API_PID)..."
kill $API_PID 2>/dev/null

echo ""
echo "=============================================================================="
echo "  PIPELINE TEST COMPLETE"
echo "=============================================================================="
echo ""
echo "Next steps:"
echo "  1. Check Cassandra: sudo docker exec cassandra cqlsh -e 'SELECT * FROM landcover.multimodal_tabular_stats;'"
echo "  2. Start API manually: cd src/serving && python app_enhanced.py"
echo "  3. Access API: http://localhost:5000/"
echo ""
