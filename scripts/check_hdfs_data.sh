#!/bin/bash

echo "=============================================================================="
echo "  HDFS Data Verification"
echo "=============================================================================="
echo ""

# Check if processed_images.parquet exists
echo "1. Checking processed_images.parquet..."
if sudo docker exec namenode hdfs dfs -test -e /data/processed/processed_images.parquet 2>/dev/null; then
    echo "✓ processed_images.parquet EXISTS"
    echo ""
    echo "Details:"
    sudo docker exec namenode hdfs dfs -ls -h /data/processed/processed_images.parquet
    echo ""
    echo "Row count (first few lines):"
    sudo docker exec namenode hdfs dfs -cat /data/processed/processed_images.parquet/_SUCCESS 2>/dev/null && echo "✓ File is complete"
else
    echo "✗ processed_images.parquet NOT FOUND"
    echo "  Run: python pre_ingestion_layer.py"
fi

echo ""
echo "=============================================================================="
echo ""

# Check if texture_features.parquet exists
echo "2. Checking texture_features.parquet..."
if sudo docker exec namenode hdfs dfs -test -e /data/processed/texture/texture_features.parquet 2>/dev/null; then
    echo "✓ texture_features.parquet EXISTS"
    echo ""
    echo "Details:"
    sudo docker exec namenode hdfs dfs -ls -h /data/processed/texture/texture_features.parquet
    echo ""
    sudo docker exec namenode hdfs dfs -cat /data/processed/texture/texture_features.parquet/_SUCCESS 2>/dev/null && echo "✓ File is complete"
else
    echo "✗ texture_features.parquet NOT FOUND"
    echo "  Run: python compute_texture_features.py"
fi

echo ""
echo "=============================================================================="
echo ""

# List all files in /data/processed/
echo "3. Complete directory listing:"
sudo docker exec namenode hdfs dfs -ls -R -h /data/processed/ 2>/dev/null || echo "No data found in /data/processed/"

echo ""
echo "=============================================================================="
echo ""
echo "Alternative: Use Python script to verify:"
echo "  python verify_hdfs_output.py"
echo "=============================================================================="
