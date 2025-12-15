#!/bin/bash

echo "=============================================================================="
echo "  Starting Spark Streaming with proper dependency management"
echo "=============================================================================="
echo ""

# Set Spark local directory
export SPARK_LOCAL_DIRS=/tmp/spark-temp
mkdir -p $SPARK_LOCAL_DIRS

echo "Downloading dependencies from Maven Central..."
echo ""

# Download missing JARs directly to Spark jars directory
SPARK_JARS_DIR="/home/top/bigData/remote-satellite-lambda-pipeline/venv/lib/python3.12/site-packages/pyspark/jars"

# Create temp directory for downloads
TEMP_DIR=$(mktemp -d)
cd $TEMP_DIR

# Download missing dependencies
echo "Downloading kafka-clients..."
wget -q https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar -O kafka-clients-3.4.1.jar

echo "Downloading slf4j-api..."
wget -q https://repo1.maven.org/maven2/org/slf4j/slf4j-api/2.0.7/slf4j-api-2.0.7.jar -O slf4j-api-2.0.7.jar

echo "Downloading commons-lang3..."
wget -q https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.10/commons-lang3-3.10.jar -O commons-lang3-3.10.jar

echo "Downloading scala-reflect..."
wget -q https://repo1.maven.org/maven2/org/scala-lang/scala-reflect/2.12.11/scala-reflect-2.12.11.jar -O scala-reflect-2.12.11.jar

echo "Downloading metrics-core..."
wget -q https://repo1.maven.org/maven2/io/dropwizard/metrics/metrics-core/4.1.18/metrics-core-4.1.18.jar -O metrics-core-4.1.18.jar

echo "Downloading jsr305..."
wget -q https://repo1.maven.org/maven2/com/google/code/findbugs/jsr305/3.0.2/jsr305-3.0.2.jar -O jsr305-3.0.2.jar

echo "Downloading spark-sql-kafka..."
wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.1/spark-sql-kafka-0-10_2.12-3.5.1.jar -O spark-sql-kafka-0-10_2.12-3.5.1.jar

echo "Downloading spark-token-provider..."
wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.1/spark-token-provider-kafka-0-10_2.12-3.5.1.jar -O spark-token-provider-kafka-0-10_2.12-3.5.1.jar

echo "Downloading cassandra connector..."
wget -q https://repo1.maven.org/maven2/com/datastax/spark/spark-cassandra-connector_2.12/3.4.1/spark-cassandra-connector_2.12-3.4.1.jar -O spark-cassandra-connector_2.12-3.4.1.jar

echo "Downloading cassandra connector driver..."
wget -q https://repo1.maven.org/maven2/com/datastax/spark/spark-cassandra-connector-driver_2.12/3.4.1/spark-cassandra-connector-driver_2.12-3.4.1.jar -O spark-cassandra-connector-driver_2.12-3.4.1.jar

echo ""
echo "All dependencies downloaded successfully!"
echo ""

# Build full paths for JARs
JARS=$(ls -1 *.jar | sed "s|^|$TEMP_DIR/|" | tr '\n' ',' | sed 's/,$//')

echo "JARs location: $TEMP_DIR"
echo "Starting Spark Streaming job..."
echo ""

# Run Spark with downloaded JARs
cd /home/top/bigData/remote-satellite-lambda-pipeline/src/speed_layer
spark-submit \
  --jars "$JARS" \
  --conf spark.cassandra.connection.host=localhost \
  --conf spark.cassandra.connection.port=9042 \
  --conf spark.sql.extensions=com.datastax.spark.connector.CassandraSparkExtensions \
  spark_streaming_enhanced.py

# Cleanup
echo "Cleaning up temporary files..."
rm -rf $TEMP_DIR
