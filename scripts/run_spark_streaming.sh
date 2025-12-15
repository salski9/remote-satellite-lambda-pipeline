#!/bin/bash

echo "=============================================================================="
echo "  Starting Spark Streaming with dependency download"
echo "=============================================================================="
echo ""

# Download dependencies if needed
echo "Downloading Spark dependencies (this may take a few minutes first time)..."
echo ""

# Use spark-shell to download packages first
spark-shell --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 <<EOF
:quit
EOF

echo ""
echo "Dependencies downloaded. Starting streaming job..."
echo ""

# Now run the actual job
cd /home/top/bigData/remote-satellite-lambda-pipeline/src/speed_layer
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,com.datastax.spark:spark-cassandra-connector_2.12:3.4.1 \
  spark_streaming_enhanced.py
