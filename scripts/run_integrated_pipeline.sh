#!/bin/bash

################################################################################
# Integrated Pipeline Runner
# Runs the complete pre-ingestion integrated multimodal lambda architecture
################################################################################

set -e  # Exit on error

echo "=============================================================================="
echo "  Pre-Ingestion Integrated Multimodal Lambda Architecture"
echo "=============================================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
print_info "Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi
print_info "✓ Docker is running"

# Step 1: Start infrastructure
print_info "Starting infrastructure (HDFS, Kafka, Cassandra, Spark)..."
docker-compose up -d

print_info "Waiting for services to be ready (60 seconds)..."
sleep 60

# Check service status
print_info "Checking service status..."
docker-compose ps

# Step 2: Verify HDFS data
print_info "Verifying HDFS data..."
if hdfs dfs -test -e hdfs://localhost:8020/data/processed/processed_images.parquet; then
    print_info "✓ processed_images.parquet found in HDFS"
else
    print_warn "processed_images.parquet not found. Run pre_ingestion_layer.py first!"
fi

if hdfs dfs -test -e hdfs://localhost:8020/data/processed/texture/texture_features.parquet; then
    print_info "✓ texture_features.parquet found in HDFS"
else
    print_warn "texture_features.parquet not found. Run compute_texture_features.py first!"
fi

# Step 3: Initialize Cassandra schema
print_info "Initializing Cassandra schema..."
if docker exec cassandra cqlsh -e "DESCRIBE KEYSPACE landcover;" > /dev/null 2>&1; then
    print_info "✓ Keyspace 'landcover' already exists"
else
    print_info "Creating keyspace and tables..."
    docker exec -i cassandra cqlsh < infrastructure/cassandra_enhanced.cql
    print_info "✓ Cassandra schema initialized"
fi

# Step 4: Verify Cassandra tables
print_info "Verifying Cassandra tables..."
TABLES=$(docker exec cassandra cqlsh -e "USE landcover; DESCRIBE TABLES;" 2>/dev/null | tr -d '\n')
if [[ $TABLES == *"multimodal_ml_features"* ]] && [[ $TABLES == *"multimodal_texture_stats"* ]]; then
    print_info "✓ Enhanced tables created"
else
    print_warn "Enhanced tables not found. Schema may need re-initialization."
fi

# Step 5: Start components (in background)
echo ""
print_info "=============================================================================="
print_info "  Starting Pipeline Components"
print_info "=============================================================================="
echo ""

# Check if components are already running
if pgrep -f "kafka_producer_from_parquet.py" > /dev/null; then
    print_warn "Producer already running (PID: $(pgrep -f kafka_producer_from_parquet.py))"
else
    print_info "Starting Kafka Producer..."
    print_info "→ Run in separate terminal: cd src/producer && python kafka_producer_from_parquet.py"
fi

if pgrep -f "spark_streaming_enhanced.py" > /dev/null; then
    print_warn "Spark Streaming already running (PID: $(pgrep -f spark_streaming_enhanced.py))"
else
    print_info "Starting Spark Streaming..."
    print_info "→ Run in separate terminal: cd src/speed_layer && spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 spark_streaming_enhanced.py"
fi

if pgrep -f "app_enhanced.py" > /dev/null; then
    print_warn "Flask API already running (PID: $(pgrep -f app_enhanced.py))"
else
    print_info "Starting Flask API..."
    print_info "→ Run in separate terminal: cd src/serving && python app_enhanced.py"
fi

# Step 6: Summary
echo ""
print_info "=============================================================================="
print_info "  Setup Complete!"
print_info "=============================================================================="
echo ""
print_info "Infrastructure Services:"
print_info "  • HDFS:      http://localhost:9870"
print_info "  • Spark:     http://localhost:8080"
print_info "  • Cassandra: localhost:9042"
print_info "  • Kafka:     localhost:29092"
echo ""
print_info "Application Components (start in separate terminals):"
print_info "  1. Producer:  cd src/producer && python kafka_producer_from_parquet.py"
print_info "  2. Streaming: cd src/speed_layer && spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 spark_streaming_enhanced.py"
print_info "  3. API:       cd src/serving && python app_enhanced.py"
echo ""
print_info "API Endpoints:"
print_info "  • Documentation: http://localhost:5000/"
print_info "  • Health Check:  http://localhost:5000/api/health"
print_info "  • ML Features:   http://localhost:5000/api/enhanced/ml-features"
print_info "  • Texture Stats: http://localhost:5000/api/enhanced/texture-stats"
print_info "  • Summary:       http://localhost:5000/api/enhanced/summary"
echo ""
print_info "To stop infrastructure: docker-compose down"
print_info "For detailed guide: See INTEGRATION_GUIDE.md"
echo ""
print_info "=============================================================================="
