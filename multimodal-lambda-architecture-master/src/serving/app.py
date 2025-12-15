from flask import Flask, jsonify
from flask_cors import CORS
from cassandra.cluster import Cluster
from cassandra.query import dict_factory
from pyspark.sql import SparkSession

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Cassandra setup
cluster = Cluster(['127.0.0.1'], port=9042)
session = cluster.connect('landcover')
session.row_factory = dict_factory

# Spark (for Hive) setup - optional lazy init
spark = None

def get_spark():
    global spark
    if spark is None:
        spark = SparkSession.builder \
            .appName("ServingLayer") \
            .master("local[1]") \
            .config("spark.driver.bindAddress", "127.0.0.1") \
            .config("spark.driver.host", "127.0.0.1") \
            .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
            .config("hive.metastore.uris", "thrift://localhost:9083") \
            .enableHiveSupport() \
            .getOrCreate()
    return spark

@app.route('/api/realtime/ndvi')
def realtime_ndvi():
    rows = session.execute("SELECT class_name, ndvi_avg, ndvi_stddev FROM realtime_ndvi_by_class")
    return jsonify(list(rows))

@app.route('/api/anomalies')
def anomalies():
    rows = session.execute("SELECT image_id, class_name, ndvi_mean, ndvi_min, ndvi_max, timestamp FROM anomaly_alerts")
    return jsonify(list(rows))

@app.route('/api/batch/class-stats')
def batch_class_stats():
    """Return mock batch data - full integration would require Hive metastore access"""
    # For demonstration: mock data representing batch aggregation results
    mock_data = [
        {"class_name": "AnnualCrop", "ndvi_avg": 0.65, "ndvi_stddev": 0.12, "ndvi_min": 0.3, "ndvi_max": 0.9, "count": 3000},
        {"class_name": "Forest", "ndvi_avg": 0.78, "ndvi_stddev": 0.08, "ndvi_min": 0.5, "ndvi_max": 0.95, "count": 3000},
        {"class_name": "HerbaceousVegetation", "ndvi_avg": 0.62, "ndvi_stddev": 0.14, "ndvi_min": 0.25, "ndvi_max": 0.88, "count": 3000},
        {"class_name": "Highway", "ndvi_avg": 0.18, "ndvi_stddev": 0.09, "ndvi_min": -0.1, "ndvi_max": 0.45, "count": 2500},
        {"class_name": "Industrial", "ndvi_avg": 0.22, "ndvi_stddev": 0.10, "ndvi_min": 0.0, "ndvi_max": 0.5, "count": 2500},
        {"class_name": "Pasture", "ndvi_avg": 0.65, "ndvi_stddev": 0.10, "ndvi_min": 0.35, "ndvi_max": 0.87, "count": 2000},
        {"class_name": "PermanentCrop", "ndvi_avg": 0.37, "ndvi_stddev": 0.12, "ndvi_min": 0.1, "ndvi_max": 0.68, "count": 2500},
        {"class_name": "Residential", "ndvi_avg": 0.34, "ndvi_stddev": 0.11, "ndvi_min": 0.05, "ndvi_max": 0.62, "count": 3000},
        {"class_name": "River", "ndvi_avg": -0.05, "ndvi_stddev": 0.15, "ndvi_min": -0.45, "ndvi_max": 0.35, "count": 2500},
        {"class_name": "SeaLake", "ndvi_avg": -0.25, "ndvi_stddev": 0.14, "ndvi_min": -0.6, "ndvi_max": 0.25, "count": 3000}
    ]
    return jsonify(mock_data)

# ============ MULTIMODAL ENDPOINTS ============

@app.route('/api/multimodal/tabular-stats')
def multimodal_tabular():
    """Get multimodal tabular statistics (CSV-derived features)"""
    rows = session.execute("""
        SELECT class_name, ndvi_avg, ndvi_stddev, red_avg, green_avg, 
               blue_avg, nir_avg, brightness_avg, sample_count 
        FROM multimodal_tabular_stats
    """)
    return jsonify(list(rows))

@app.route('/api/multimodal/image-stats')
def multimodal_image():
    """Get multimodal image statistics (RGB-derived features)"""
    rows = session.execute("""
        SELECT class_name, avg_red_channel, avg_green_channel, avg_blue_channel,
               avg_brightness, avg_contrast, image_count
        FROM multimodal_image_stats
    """)
    return jsonify(list(rows))

@app.route('/api/multimodal/anomalies')
def multimodal_anomalies():
    """Get multimodal anomalies (fusion of CSV + RGB features)"""
    rows = session.execute("""
        SELECT class_name, image_id, ndvi_mean, brightness, contrast, 
               timestamp, anomaly_type
        FROM multimodal_anomalies 
        LIMIT 100
    """)
    return jsonify(list(rows))

@app.route('/api/multimodal/summary')
def multimodal_summary():
    """Get summary statistics across all tables"""
    # Tabular stats
    tabular = session.execute("SELECT COUNT(*) as count FROM multimodal_tabular_stats")
    tabular_count = list(tabular)[0]['count'] if tabular else 0
    
    # Image stats
    image = session.execute("SELECT COUNT(*) as count FROM multimodal_image_stats")
    image_count = list(image)[0]['count'] if image else 0
    
    # Anomalies
    anomalies = session.execute("SELECT COUNT(*) as count FROM multimodal_anomalies")
    anomaly_count = list(anomalies)[0]['count'] if anomalies else 0
    
    # Total events processed - use cumulative totals table
    try:
        cumulative = session.execute("SELECT SUM(total_events) as total FROM multimodal_event_totals")
        cumulative_list = list(cumulative)
        total_events = cumulative_list[0]['total'] if cumulative_list and cumulative_list[0].get('total') else 0
    except Exception as e:
        # Fallback to sample_count if cumulative table doesn't exist yet
        try:
            events = session.execute("SELECT SUM(sample_count) as total FROM multimodal_tabular_stats")
            events_list = list(events)
            total_events = events_list[0]['total'] if events_list and events_list[0].get('total') else 0
        except:
            total_events = 0
    
    return jsonify({
        'classes_with_tabular_stats': tabular_count,
        'classes_with_image_stats': image_count,
        'total_anomalies_detected': anomaly_count,
        'total_events_processed': total_events
    })

@app.route('/api/multimodal/cumulative-totals')
def multimodal_cumulative_totals():
    """Get cumulative event totals per class"""
    try:
        rows = session.execute("SELECT * FROM multimodal_event_totals")
        return jsonify(list(rows))
    except Exception as e:
        return jsonify({"error": str(e), "message": "Cumulative totals table not yet populated"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
