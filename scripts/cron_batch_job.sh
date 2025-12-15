#!/bin/bash

################################################################################
# Cron-compatible Batch Job Runner
# Runs every 2 hours to recompute batch views from HDFS
################################################################################

# Set full PATH for cron environment
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Project directory
PROJECT_DIR="/home/top/bigData/remote-satellite-lambda-pipeline"
cd "$PROJECT_DIR"

# Log directory
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# Timestamped log file
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
BATCH_LOG="$LOG_DIR/batch_cron_${TIMESTAMP}.log"

echo "================================================================================" >> "$BATCH_LOG"
echo "                    SCHEDULED BATCH PROCESSING" >> "$BATCH_LOG"
echo "================================================================================" >> "$BATCH_LOG"
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')" >> "$BATCH_LOG"
echo "Log: $BATCH_LOG" >> "$BATCH_LOG"
echo "" >> "$BATCH_LOG"

# Activate virtual environment
if [ -d "$PROJECT_DIR/venv" ]; then
    source "$PROJECT_DIR/venv/bin/activate" >> "$BATCH_LOG" 2>&1
    echo "✓ Virtual environment activated" >> "$BATCH_LOG"
else
    echo "⚠ No virtual environment found, using system Python" >> "$BATCH_LOG"
fi

# Check if Docker containers are running
if ! docker ps | grep -q "namenode"; then
    echo "✗ HDFS NameNode is not running!" >> "$BATCH_LOG"
    echo "Please start Docker containers first" >> "$BATCH_LOG"
    exit 1
fi

# Run batch processing
echo "" >> "$BATCH_LOG"
echo "Running Spark batch job..." >> "$BATCH_LOG"
echo "================================================================================" >> "$BATCH_LOG"

spark-submit \
    --master local[4] \
    --driver-memory 4g \
    --executor-memory 4g \
    --conf spark.sql.warehouse.dir=hdfs://localhost:8020/user/hive/warehouse \
    "$PROJECT_DIR/src/batch_layer/spark_batch_processor.py" \
    >> "$BATCH_LOG" 2>&1

EXIT_CODE=$?

echo "" >> "$BATCH_LOG"
echo "================================================================================" >> "$BATCH_LOG"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ BATCH PROCESSING COMPLETE" >> "$BATCH_LOG"
    echo "Exit code: 0" >> "$BATCH_LOG"
    
    # Keep only last 10 log files to prevent disk space issues
    cd "$LOG_DIR"
    ls -t batch_cron_*.log | tail -n +11 | xargs -r rm
else
    echo "✗ BATCH PROCESSING FAILED" >> "$BATCH_LOG"
    echo "Exit code: $EXIT_CODE" >> "$BATCH_LOG"
fi
echo "================================================================================" >> "$BATCH_LOG"
echo "Finished: $(date '+%Y-%m-%d %H:%M:%S')" >> "$BATCH_LOG"

exit $EXIT_CODE
