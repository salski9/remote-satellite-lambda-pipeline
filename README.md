# Satellite Image Data Pipeline

## Overview
This project presents an end-to-end data engineering pipeline designed to process and analyze satellite imagery data at scale.  
The pipeline integrates image-based feature extraction, streaming ingestion, real-time processing, batch analytics, and serving-ready storage.

The goal is to transform raw satellite images into structured, analyzable data suitable for both near real-time insights and historical analysis.

## Dataset Description
The dataset consists of satellite images representing different land-cover classes, including forests, rivers, urban areas, agricultural zones, and water bodies.

For each image:
- RGB (.jpg) and multispectral (.tif) data are available
- Domain-specific features (e.g., NDVI, vegetation index, spectral means) are provided in CSV format
- Each image is labeled with a land-cover class

## Architecture
The pipeline follows a multi-layer architecture:

- **Pre-Ingestion Layer**  
  Feature engineering and data standardization using Spark MLlib, transforming raw image data into structured numerical records.

- **Ingestion Layer**  
  Kafka is used to ingest standardized image events and decouple data producers from downstream consumers.

- **Speed Processing Layer**  
  Near real-time processing using Spark Streaming to compute fast aggregations and metrics.

- **Batch Processing Layer**  
  Large-scale historical processing using Apache Spark on Hadoop with Parquet storage.

- **Persistence Layer**  
  Processed and aggregated results are stored in Apache Cassandra for low-latency access.

- **Serving Layer**  
  A serving interface (to be defined) exposes analytical results for visualization and exploration.

## Technologies
- Apache Spark (Batch & Streaming)
- Spark MLlib
- Apache Kafka
- Hadoop (HDFS)
- Apache Cassandra
- Parquet

## Repository Structure
This repository focuses on architectural design, data modeling, and pipeline reasoning.  
Implementation details will be added progressively as the project evolves.
