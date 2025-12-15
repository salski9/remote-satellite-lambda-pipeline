#!/bin/bash

################################################################################
# Batch Processing Layer Runner
# Runs Spark batch job to compute accurate aggregations from HDFS
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

BATCH_LOG="$LOG_DIR/batch_processing.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "================================================================================"
echo "                    BATCH PROCESSING LAYER"
echo "================================================================================"
echo "Started: $TIMESTAMP"
echo "Log: $BATCH_LOG"
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "⚠ No virtual environment found, using system Python"
fi

# Run batch processing
echo ""
echo "Running Spark batch job..."
echo "================================================================================"

spark-submit \
    --master local[4] \
    --driver-memory 4g \
    --executor-memory 4g \
    --conf spark.sql.warehouse.dir=hdfs://localhost:8020/user/hive/warehouse \
    src/batch_layer/spark_batch_processor.py \
    2>&1 | tee -a "$BATCH_LOG"

EXIT_CODE=$?

echo ""
echo "================================================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ BATCH PROCESSING COMPLETED SUCCESSFULLY"
    echo ""
    echo "Batch views stored in:"
    echo "  • Hive database: batch_views"
    echo "  • HDFS location: hdfs://localhost:8020/user/hive/warehouse/batch_views.db/"
    echo ""
    echo "To query batch views:"
    echo "  spark-sql --database batch_views"
    echo "  spark-sql -e 'SELECT * FROM batch_views.class_statistics;'"
else
    echo "✗ BATCH PROCESSING FAILED (exit code: $EXIT_CODE)"
fi
echo "================================================================================"
echo "Finished: $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================================"

exit $EXIT_CODE
