#!/bin/bash

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo ""
echo "=============================================================================="
echo "                    AUTOMATED PIPELINE STARTUP"
echo "=============================================================================="
echo ""
print_info "This script will:"
print_info "  0. Run Batch Processing (Hive + HDFS) - Optional, set SKIP_BATCH=1 to skip"
print_info "  1. Start Spark Streaming (background, keeps running)"
print_info "  2. Start Kafka Producer (runs once, sends 27K events)"
print_info "  3. Start Flask API (background, keeps running)"
echo ""

# Set working directory
cd /home/top/bigData/remote-satellite-lambda-pipeline

# Activate venv (export path to ensure it's used)
source venv/bin/activate
export PATH="/home/top/bigData/remote-satellite-lambda-pipeline/venv/bin:$PATH"
export VIRTUAL_ENV="/home/top/bigData/remote-satellite-lambda-pipeline/venv"

# Create log directory
mkdir -p logs

# Kill any existing processes
print_info "Checking for existing processes..."
if pgrep -f "spark_streaming_enhanced.py" > /dev/null; then
    print_warn "Killing existing Spark Streaming process..."
    pkill -f "spark_streaming_enhanced.py"
    sleep 2
fi

if pgrep -f "app_enhanced.py" > /dev/null; then
    print_warn "Killing existing Flask API process..."
    pkill -f "app_enhanced.py"
    sleep 2
fi

# Step 0: Run Batch Processing (optional - set SKIP_BATCH=1 to skip)
if [ "${SKIP_BATCH}" != "1" ]; then
    echo ""
    print_info "=============================================================================="
    print_info "  STEP 0: Running Batch Processing Layer (Hive + HDFS)"
    print_info "=============================================================================="
    echo ""
    print_info "Computing batch views from historical data..."
    
    cd /home/top/bigData/remote-satellite-lambda-pipeline
    ./scripts/run_batch_job.sh
    
    BATCH_EXIT=$?
    if [ $BATCH_EXIT -eq 0 ]; then
        print_success "Batch processing completed successfully!"
        print_info "Batch views stored in Hive: batch_views database"
    else
        print_warn "Batch processing failed (continuing anyway...)"
    fi
    
    sleep 5
else
    print_info "Skipping batch processing (SKIP_BATCH=1)"
fi

# Step 1: Start Spark Streaming in background
echo ""
print_info "=============================================================================="
print_info "  STEP 1: Starting Spark Streaming (background)"
print_info "=============================================================================="
echo ""

# Download JARs if needed - use permanent directory
JARS_DIR="/home/top/bigData/remote-satellite-lambda-pipeline/spark_jars"
mkdir -p $JARS_DIR
cd $JARS_DIR

# Only download if JARs don't exist
if [ ! -f "spark-sql-kafka-0-10_2.12-3.5.1.jar" ]; then
    print_info "Downloading Spark dependencies..."
wget -q https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar
wget -q https://repo1.maven.org/maven2/org/slf4j/slf4j-api/2.0.7/slf4j-api-2.0.7.jar
wget -q https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.10/commons-lang3-3.10.jar
wget -q https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar
wget -q https://repo1.maven.org/maven2/org/scala-lang/scala-reflect/2.12.11/scala-reflect-2.12.11.jar
wget -q https://repo1.maven.org/maven2/io/dropwizard/metrics/metrics-core/4.1.18/metrics-core-4.1.18.jar
wget -q https://repo1.maven.org/maven2/com/google/code/findbugs/jsr305/3.0.2/jsr305-3.0.2.jar
wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.1/spark-sql-kafka-0-10_2.12-3.5.1.jar
wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.1/spark-token-provider-kafka-0-10_2.12-3.5.1.jar
wget -q https://repo1.maven.org/maven2/com/datastax/spark/spark-cassandra-connector_2.12/3.4.1/spark-cassandra-connector_2.12-3.4.1.jar
wget -q https://repo1.maven.org/maven2/com/datastax/spark/spark-cassandra-connector-driver_2.12/3.4.1/spark-cassandra-connector-driver_2.12-3.4.1.jar
wget -q https://repo1.maven.org/maven2/com/datastax/oss/java-driver-core/4.13.0/java-driver-core-4.13.0.jar
wget -q https://repo1.maven.org/maven2/com/datastax/oss/java-driver-query-builder/4.13.0/java-driver-query-builder-4.13.0.jar
wget -q https://repo1.maven.org/maven2/com/datastax/oss/java-driver-shaded-guava/25.1-jre-graal-sub-1/java-driver-shaded-guava-25.1-jre-graal-sub-1.jar
wget -q https://repo1.maven.org/maven2/com/datastax/oss/native-protocol/1.5.1/native-protocol-1.5.1.jar
wget -q https://repo1.maven.org/maven2/org/reactivestreams/reactive-streams/1.0.4/reactive-streams-1.0.4.jar
wget -q https://repo1.maven.org/maven2/com/typesafe/config/1.4.1/config-1.4.1.jar

    print_success "Dependencies downloaded"
else
    print_success "Dependencies already exist (skipping download)"
fi

JARS=$(ls -1 $JARS_DIR/*.jar | tr '\n' ',' | sed 's/,$//')

cd /home/top/bigData/remote-satellite-lambda-pipeline/src/speed_layer

print_info "Starting Spark Streaming job..."
nohup spark-submit \
  --jars "$JARS" \
  --conf spark.cassandra.connection.host=localhost \
  --conf spark.cassandra.connection.port=9042 \
  --conf spark.sql.extensions=com.datastax.spark.connector.CassandraSparkExtensions \
  spark_streaming_enhanced.py \
  > ../../logs/spark_streaming.log 2>&1 &

SPARK_PID=$!
print_success "Spark Streaming started (PID: $SPARK_PID)"
print_info "  Log: logs/spark_streaming.log"
print_info "  Monitor: tail -f logs/spark_streaming.log"

# Wait for Spark to initialize
print_info "Waiting for Spark Streaming to initialize (30 seconds)..."
sleep 30

# Check if Spark is still running
if ! ps -p $SPARK_PID > /dev/null; then
    print_error "Spark Streaming failed to start!"
    print_info "Check logs: tail -50 logs/spark_streaming.log"
    exit 1
fi

print_success "Spark Streaming is running and ready"

# Step 2: Run Kafka Producer (foreground, runs once)
echo ""
print_info "=============================================================================="
print_info "  STEP 2: Running Kafka Producer (sends 27K events)"
print_info "=============================================================================="
echo ""

cd /home/top/bigData/remote-satellite-lambda-pipeline/src/producer
print_info "Starting producer..."
python kafka_producer_from_parquet.py 2>&1 | tee ../../logs/producer.log

PRODUCER_EXIT=$?
if [ $PRODUCER_EXIT -eq 0 ]; then
    print_success "Producer completed successfully!"
    print_info "All 27,000 events sent to Kafka"
else
    print_error "Producer failed with exit code $PRODUCER_EXIT"
fi

# Wait a bit for Spark to process events
print_info "Waiting for Spark to process events (10 seconds)..."
sleep 10

# Step 3: Start Flask API in background
echo ""
print_info "=============================================================================="
print_info "  STEP 3: Starting Flask API (background)"
print_info "=============================================================================="
echo ""

cd /home/top/bigData/remote-satellite-lambda-pipeline/src/serving
nohup /home/top/bigData/remote-satellite-lambda-pipeline/venv/bin/python app_enhanced.py > ../../logs/flask_api.log 2>&1 &
API_PID=$!

print_success "Flask API started (PID: $API_PID)"
print_info "  URL: http://localhost:5000"
print_info "  Log: logs/flask_api.log"

# Wait for API to start
print_info "Waiting for API to initialize (5 seconds)..."
sleep 5

# Test API
echo ""
print_info "Testing API endpoints..."
curl -s http://localhost:5000/api/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
    print_success "API is responding!"
else
    print_warn "API might not be ready yet, give it a few more seconds"
fi

# Summary
echo ""
echo "=============================================================================="
echo "                    PIPELINE STARTED SUCCESSFULLY"
echo "=============================================================================="
echo ""
print_success "Running processes:"
echo "  • Spark Streaming (PID: $SPARK_PID) - Processing events"
echo "  • Flask API (PID: $API_PID) - Serving data"
echo ""
print_info "Monitor logs:"
echo "  • tail -f logs/spark_streaming.log"
echo "  • tail -f logs/flask_api.log"
echo ""
print_info "Test API:"
echo "  • curl http://localhost:5000/api/health"
echo "  • curl http://localhost:5000/api/enhanced/summary"
echo ""
print_info "Stop pipeline:"
echo "  • kill $SPARK_PID $API_PID"
echo "  • Or: pkill -f 'spark_streaming_enhanced|app_enhanced'"
echo ""
print_warn "Spark Streaming will keep running to process events."
print_warn "Press Ctrl+C to stop monitoring, processes will continue in background."
echo ""

# Cleanup temp directory
rm -rf $TEMP_DIR

# Keep script running and show live stats
echo "=============================================================================="
echo "                    LIVE MONITORING (Ctrl+C to exit)"
echo "=============================================================================="
echo ""

while true; do
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} Status Check..."
    
    # Check Spark
    if ps -p $SPARK_PID > /dev/null; then
        echo -e "  ${GREEN}✓${NC} Spark Streaming: Running"
    else
        echo -e "  ${RED}✗${NC} Spark Streaming: Stopped"
    fi
    
    # Check API
    if ps -p $API_PID > /dev/null; then
        echo -e "  ${GREEN}✓${NC} Flask API: Running"
    else
        echo -e "  ${RED}✗${NC} Flask API: Stopped"
    fi
    
    # Check API response
    if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} API Health: OK"
    else
        echo -e "  ${YELLOW}⚠${NC} API Health: Not responding"
    fi
    
    echo ""
    sleep 30
done
