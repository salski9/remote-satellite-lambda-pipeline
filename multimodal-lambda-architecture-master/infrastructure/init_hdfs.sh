#!/usr/bin/env bash
set -euo pipefail

hdfs dfs -mkdir -p /raw/landcover
hdfs dfs -put -f /data/images.csv /raw/landcover/
hdfs dfs -put -f /data/classes.csv /raw/landcover/
hdfs dfs -put -f /data/ndvi_stats.csv /raw/landcover/
hdfs dfs -put -f /data/spectral_data.csv /raw/landcover/
