#!/usr/bin/env python3
"""
Enhanced Flask API - Serves Pre-Ingestion Integrated Data
New endpoints for: ML features, Texture statistics, Feature importance
"""
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from cassandra.cluster import Cluster
from cassandra.query import dict_factory
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Cassandra setup
cluster = Cluster(['127.0.0.1'], port=9042)
session = cluster.connect('landcover')
session.row_factory = dict_factory

# ============================================================================
# EXISTING ENDPOINTS (backward compatibility)
# ============================================================================

@app.route('/api/realtime/ndvi')
def realtime_ndvi():
    """Legacy endpoint for real-time NDVI"""
    rows = session.execute("SELECT class_name, ndvi_avg, ndvi_stddev FROM realtime_ndvi_by_class")
    return jsonify(list(rows))

@app.route('/api/anomalies')
def anomalies():
    """Legacy endpoint for anomalies"""
    rows = session.execute("SELECT image_id, class_name, ndvi_mean, ndvi_min, ndvi_max, timestamp FROM anomaly_alerts")
    return jsonify(list(rows))

@app.route('/api/multimodal/tabular-stats')
def multimodal_tabular():
    """Get multimodal tabular statistics (CSV-derived features)"""
    rows = session.execute("""
        SELECT class_name, ndvi_avg, ndvi_stddev, red_avg, green_avg, 
               blue_avg, nir_avg, brightness_avg, sample_count, last_updated
        FROM multimodal_tabular_stats
    """)
    return jsonify(list(rows))

@app.route('/api/multimodal/image-stats')
def multimodal_image():
    """Get multimodal image statistics (RGB-derived features)"""
    rows = session.execute("""
        SELECT class_name, avg_red_channel, avg_green_channel, avg_blue_channel,
               avg_brightness, avg_contrast, image_count, last_updated
        FROM multimodal_image_stats
    """)
    return jsonify(list(rows))

@app.route('/api/multimodal/anomalies')
def multimodal_anomalies():
    """Get multimodal anomalies (fusion of CSV + RGB features)"""
    limit = request.args.get('limit', 100, type=int)
    rows = session.execute(f"""
        SELECT class_name, image_id, ndvi_mean, brightness, contrast, 
               timestamp, anomaly_type
        FROM multimodal_anomalies 
        LIMIT {limit}
    """)
    return jsonify(list(rows))

@app.route('/api/multimodal/cumulative-totals')
def multimodal_cumulative_totals():
    """Get cumulative event totals per class"""
    try:
        rows = session.execute("SELECT * FROM multimodal_event_totals")
        return jsonify(list(rows))
    except Exception as e:
        return jsonify({"error": str(e), "message": "Cumulative totals table not yet populated"}), 404

# ============================================================================
# NEW ENHANCED ENDPOINTS (for pre-ingestion integration)
# ============================================================================

@app.route('/api/enhanced/ml-features')
def enhanced_ml_features():
    """
    Get ML-ready feature vectors (pre-normalized from pre-ingestion pipeline)
    Returns: Averaged final_features vectors per class
    """
    try:
        rows = session.execute("""
            SELECT class_name, avg_final_features, feature_dimension, 
                   sample_count, last_updated
            FROM multimodal_ml_features
        """)
        
        results = []
        for row in rows:
            result = dict(row)
            # Parse JSON string back to array
            if result.get('avg_final_features'):
                try:
                    result['avg_final_features'] = json.loads(result['avg_final_features'])
                except:
                    pass
            results.append(result)
        
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e), "message": "ML features table not yet populated"}), 404

@app.route('/api/enhanced/ml-features/<class_name>')
def enhanced_ml_features_by_class(class_name):
    """Get ML features for a specific class"""
    try:
        rows = session.execute("""
            SELECT * FROM multimodal_ml_features 
            WHERE class_name = %s
        """, [class_name])
        
        result = list(rows)
        if result:
            data = dict(result[0])
            # Parse JSON string back to array
            if data.get('avg_final_features'):
                try:
                    data['avg_final_features'] = json.loads(data['avg_final_features'])
                except:
                    pass
            return jsonify(data)
        else:
            return jsonify({"error": "Class not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/enhanced/texture-stats')
def enhanced_texture_stats():
    """
    Get texture feature statistics (GLCM + LBP from pre-ingestion)
    Returns: Aggregated texture features per class
    """
    try:
        rows = session.execute("""
            SELECT class_name, 
                   glcm_contrast_avg, glcm_homogeneity_avg, glcm_energy_avg,
                   glcm_correlation_avg, glcm_dissimilarity_avg, glcm_asm_avg,
                   lbp_entropy_avg, texture_sample_count, last_updated
            FROM multimodal_texture_stats
        """)
        return jsonify(list(rows))
    except Exception as e:
        return jsonify({"error": str(e), "message": "Texture stats table not yet populated"}), 404

@app.route('/api/enhanced/texture-stats/<class_name>')
def enhanced_texture_stats_by_class(class_name):
    """Get texture statistics for a specific class"""
    try:
        rows = session.execute("""
            SELECT * FROM multimodal_texture_stats 
            WHERE class_name = %s
        """, [class_name])
        
        result = list(rows)
        if result:
            return jsonify(dict(result[0]))
        else:
            return jsonify({"error": "Class not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/enhanced/feature-importance')
def enhanced_feature_importance():
    """
    Calculate feature importance based on variance across classes
    Uses texture features and tabular features
    """
    try:
        # Get texture features
        texture_rows = session.execute("SELECT * FROM multimodal_texture_stats")
        texture_data = list(texture_rows)
        
        if not texture_data:
            return jsonify({"error": "No texture data available"}), 404
        
        # Calculate variance for each texture feature
        features = [
            'glcm_contrast_avg', 'glcm_homogeneity_avg', 'glcm_energy_avg',
            'glcm_correlation_avg', 'glcm_dissimilarity_avg', 'glcm_asm_avg',
            'lbp_entropy_avg'
        ]
        
        importance = []
        for feature in features:
            values = [row[feature] for row in texture_data if row.get(feature) is not None]
            if values:
                mean = sum(values) / len(values)
                variance = sum((x - mean) ** 2 for x in values) / len(values)
                importance.append({
                    'feature': feature.replace('_avg', '').replace('_', ' ').title(),
                    'variance': variance,
                    'mean': mean,
                    'importance_score': variance * 100  # Scaled for visualization
                })
        
        # Sort by importance
        importance.sort(key=lambda x: x['importance_score'], reverse=True)
        
        return jsonify(importance)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/enhanced/summary')
def enhanced_summary():
    """
    Get comprehensive summary of enhanced multimodal system
    Includes counts from all tables
    """
    summary = {}
    
    # Tabular stats
    try:
        tabular = session.execute("SELECT COUNT(*) as count FROM multimodal_tabular_stats")
        summary['classes_with_tabular_stats'] = list(tabular)[0]['count']
    except:
        summary['classes_with_tabular_stats'] = 0
    
    # Image stats
    try:
        image = session.execute("SELECT COUNT(*) as count FROM multimodal_image_stats")
        summary['classes_with_image_stats'] = list(image)[0]['count']
    except:
        summary['classes_with_image_stats'] = 0
    
    # ML features (NEW)
    try:
        ml = session.execute("SELECT COUNT(*) as count FROM multimodal_ml_features")
        summary['classes_with_ml_features'] = list(ml)[0]['count']
    except:
        summary['classes_with_ml_features'] = 0
    
    # Texture stats (NEW)
    try:
        texture = session.execute("SELECT COUNT(*) as count FROM multimodal_texture_stats")
        summary['classes_with_texture_stats'] = list(texture)[0]['count']
    except:
        summary['classes_with_texture_stats'] = 0
    
    # Anomalies
    try:
        anomalies = session.execute("SELECT COUNT(*) as count FROM multimodal_anomalies")
        summary['total_anomalies_detected'] = list(anomalies)[0]['count']
    except:
        summary['total_anomalies_detected'] = 0
    
    # Total events processed
    try:
        cumulative = session.execute("SELECT SUM(total_events) as total FROM multimodal_event_totals")
        cumulative_list = list(cumulative)
        summary['total_events_processed'] = cumulative_list[0]['total'] if cumulative_list and cumulative_list[0].get('total') else 0
    except:
        summary['total_events_processed'] = 0
    
    # Total images with texture features
    try:
        texture_images = session.execute("SELECT SUM(texture_sample_count) as total FROM multimodal_texture_stats")
        texture_list = list(texture_images)
        summary['total_images_with_texture'] = texture_list[0]['total'] if texture_list and texture_list[0].get('total') else 0
    except:
        summary['total_images_with_texture'] = 0
    
    summary['timestamp'] = datetime.utcnow().isoformat()
    summary['integration'] = 'pre-ingestion-enhanced'
    
    # Add batch processing information
    now = datetime.utcnow()
    current_hour = now.hour
    next_hour = ((current_hour // 2) + 1) * 2
    if next_hour >= 24:
        next_batch = now.replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        next_batch = next_batch + timedelta(days=1)
    else:
        next_batch = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
    
    time_until_batch = (next_batch - now).total_seconds()
    hours_until = int(time_until_batch // 3600)
    minutes_until = int((time_until_batch % 3600) // 60)
    
    summary['batch_processing'] = {
        'enabled': True,
        'schedule': 'Every 2 hours',
        'next_run': next_batch.isoformat(),
        'time_until_next': f"{hours_until}h {minutes_until}m"
    }
    
    return jsonify(summary)

@app.route('/api/enhanced/class-comparison')
def enhanced_class_comparison():
    """
    Compare all features across classes
    Returns: Combined data from tabular, texture, and ML features
    """
    try:
        # Get tabular stats
        tabular_rows = session.execute("SELECT * FROM multimodal_tabular_stats")
        tabular_dict = {row['class_name']: dict(row) for row in tabular_rows}
        
        # Get texture stats
        texture_rows = session.execute("SELECT * FROM multimodal_texture_stats")
        texture_dict = {row['class_name']: dict(row) for row in texture_rows}
        
        # Get ML features
        ml_rows = session.execute("SELECT * FROM multimodal_ml_features")
        ml_dict = {row['class_name']: dict(row) for row in ml_rows}
        
        # Combine all data
        all_classes = set(list(tabular_dict.keys()) + list(texture_dict.keys()) + list(ml_dict.keys()))
        
        comparison = []
        for class_name in sorted(all_classes):
            combined = {
                'class_name': class_name,
                'tabular': tabular_dict.get(class_name, {}),
                'texture': texture_dict.get(class_name, {}),
                'ml': ml_dict.get(class_name, {})
            }
            comparison.append(combined)
        
        return jsonify(comparison)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint with batch processing info"""
    now = datetime.utcnow()
    current_hour = now.hour
    
    # Calculate next batch run (every 2 hours at :00)
    next_hour = ((current_hour // 2) + 1) * 2
    if next_hour >= 24:
        next_batch = now.replace(hour=0, minute=0, second=0, microsecond=0)
        next_batch = next_batch.replace(day=now.day + 1)
    else:
        next_batch = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
    
    time_until_batch = (next_batch - now).total_seconds()
    hours_until = int(time_until_batch // 3600)
    minutes_until = int((time_until_batch % 3600) // 60)
    
    return jsonify({
        'status': 'healthy',
        'service': 'enhanced-multimodal-api',
        'timestamp': now.isoformat(),
        'cassandra_connected': True,
        'batch_processing': {
            'schedule': 'Every 2 hours',
            'run_times': '00:00, 02:00, 04:00, 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00',
            'next_run': next_batch.isoformat(),
            'time_until_next': f"{hours_until}h {minutes_until}m"
        }
    })

@app.route('/api/batch/status')
def batch_status():
    """Batch processing status and schedule information"""
    now = datetime.utcnow()
    current_hour = now.hour
    
    # Calculate next batch run (every 2 hours at :00)
    next_hour = ((current_hour // 2) + 1) * 2
    if next_hour >= 24:
        next_batch = now.replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        next_batch = next_batch + timedelta(days=1)
    else:
        next_batch = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
    
    time_until_batch = (next_batch - now).total_seconds()
    hours_until = int(time_until_batch // 3600)
    minutes_until = int((time_until_batch % 3600) // 60)
    
    # Check if batch is currently running (within 5 minutes of a batch hour)
    is_running = (current_hour % 2 == 0) and (now.minute < 5)
    
    return jsonify({
        'schedule': {
            'frequency': 'Every 2 hours',
            'interval': '2 hours',
            'times': ['00:00', '02:00', '04:00', '06:00', '08:00', '10:00', 
                     '12:00', '14:00', '16:00', '18:00', '20:00', '22:00']
        },
        'next_run': {
            'timestamp': next_batch.isoformat(),
            'time_until': f"{hours_until}h {minutes_until}m",
            'hours': hours_until,
            'minutes': minutes_until
        },
        'current_status': 'running' if is_running else 'idle',
        'last_updated': now.isoformat(),
        'description': 'Batch layer recomputes accurate views from HDFS using Hive and Spark'
    })

@app.route('/api/analytics/separability')
def class_separability():
    """
    Calculate class separability using Euclidean distance in feature space
    Answers: Are forests separable from crops? Are residential/industrial distinguishable?
    """
    try:
        import numpy as np
        from scipy.spatial.distance import euclidean
        
        # Get all class data
        tabular = session.execute("SELECT * FROM multimodal_tabular_stats")
        texture = session.execute("SELECT * FROM multimodal_texture_stats")
        
        tabular_dict = {row['class_name']: dict(row) for row in tabular}
        texture_dict = {row['class_name']: dict(row) for row in texture}
        
        # Combine features for each class
        classes = {}
        for class_name in tabular_dict.keys():
            if class_name in texture_dict:
                features = [
                    tabular_dict[class_name].get('ndvi_avg', 0) or 0,
                    tabular_dict[class_name].get('brightness_avg', 0) or 0,
                    tabular_dict[class_name].get('red_avg', 0) or 0,
                    tabular_dict[class_name].get('green_avg', 0) or 0,
                    tabular_dict[class_name].get('blue_avg', 0) or 0,
                    texture_dict[class_name].get('glcm_contrast_avg', 0) or 0,
                    texture_dict[class_name].get('glcm_energy_avg', 0) or 0,
                    texture_dict[class_name].get('lbp_entropy_avg', 0) or 0
                ]
                classes[class_name] = np.array(features)
        
        # Calculate pairwise distances
        separability = []
        class_list = list(classes.keys())
        
        for i, class1 in enumerate(class_list):
            for class2 in class_list[i+1:]:
                distance = euclidean(classes[class1], classes[class2])
                separability.append({
                    'class1': class1,
                    'class2': class2,
                    'distance': float(distance),
                    'separable': distance > 500  # Threshold for "separable"
                })
        
        # Sort by distance (most separable first)
        separability.sort(key=lambda x: x['distance'], reverse=True)
        
        # Key questions
        insights = {
            'forest_vs_crops': None,
            'residential_vs_industrial': None,
            'river_vs_sealake': None,
            'river_vs_forest': None
        }
        
        for item in separability:
            # Forest vs crops
            if ('Forest' in [item['class1'], item['class2']] and 
                any(crop in [item['class1'], item['class2']] for crop in ['AnnualCrop', 'PermanentCrop'])):
                if not insights['forest_vs_crops']:
                    insights['forest_vs_crops'] = item
            
            # Residential vs Industrial
            if set([item['class1'], item['class2']]) == set(['Residential', 'Industrial']):
                insights['residential_vs_industrial'] = item
            
            # River vs SeaLake
            if set([item['class1'], item['class2']]) == set(['River', 'SeaLake']):
                insights['river_vs_sealake'] = item
            
            # River vs Forest
            if set([item['class1'], item['class2']]) == set(['River', 'Forest']):
                insights['river_vs_forest'] = item
        
        return jsonify({
            'all_pairs': separability,
            'key_insights': insights,
            'summary': {
                'total_pairs': len(separability),
                'separable_pairs': sum(1 for x in separability if x['separable']),
                'most_separable': separability[0] if separability else None,
                'least_separable': separability[-1] if separability else None
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/similarity')
def class_similarity():
    """
    Calculate similarity matrix between land cover types
    Lower distance = more similar
    """
    try:
        import numpy as np
        from scipy.spatial.distance import euclidean
        
        # Get all class data
        tabular = session.execute("SELECT * FROM multimodal_tabular_stats")
        texture = session.execute("SELECT * FROM multimodal_texture_stats")
        
        tabular_dict = {row['class_name']: dict(row) for row in tabular}
        texture_dict = {row['class_name']: dict(row) for row in texture}
        
        # Combine features
        classes = {}
        for class_name in tabular_dict.keys():
            if class_name in texture_dict:
                features = [
                    tabular_dict[class_name].get('ndvi_avg', 0) or 0,
                    tabular_dict[class_name].get('brightness_avg', 0) or 0,
                    tabular_dict[class_name].get('red_avg', 0) or 0,
                    texture_dict[class_name].get('glcm_contrast_avg', 0) or 0,
                    texture_dict[class_name].get('glcm_energy_avg', 0) or 0,
                    texture_dict[class_name].get('lbp_entropy_avg', 0) or 0
                ]
                classes[class_name] = np.array(features)
        
        # Build similarity matrix
        class_list = sorted(classes.keys())
        matrix = []
        
        for class1 in class_list:
            row = []
            for class2 in class_list:
                if class1 == class2:
                    distance = 0
                else:
                    distance = euclidean(classes[class1], classes[class2])
                row.append(float(distance))
            matrix.append(row)
        
        return jsonify({
            'classes': class_list,
            'similarity_matrix': matrix,
            'interpretation': 'Lower values = more similar classes'
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/band-correlation')
def band_correlation():
    """
    Calculate correlations between spectral bands
    Reveals hidden relationships (e.g., red-NIR correlation for vegetation)
    """
    try:
        import numpy as np
        
        # Get tabular data with all bands
        rows = session.execute("SELECT red_avg, green_avg, blue_avg, nir_avg, brightness_avg, ndvi_avg FROM multimodal_tabular_stats")
        data_list = list(rows)
        
        if not data_list:
            return jsonify({"error": "No data available"}), 404
        
        # Build data matrix
        bands = {
            'red': [row['red_avg'] for row in data_list if row['red_avg']],
            'green': [row['green_avg'] for row in data_list if row['green_avg']],
            'blue': [row['blue_avg'] for row in data_list if row['blue_avg']],
            'nir': [row['nir_avg'] for row in data_list if row['nir_avg']],
            'brightness': [row['brightness_avg'] for row in data_list if row['brightness_avg']],
            'ndvi': [row['ndvi_avg'] for row in data_list if row['ndvi_avg']]
        }
        
        # Calculate correlation matrix
        band_names = list(bands.keys())
        correlation_matrix = []
        
        for band1_name in band_names:
            row = []
            for band2_name in band_names:
                band1 = np.array(bands[band1_name])
                band2 = np.array(bands[band2_name])
                
                if len(band1) > 1 and len(band2) > 1:
                    corr = float(np.corrcoef(band1, band2)[0, 1])
                else:
                    corr = 0.0
                
                row.append(corr)
            correlation_matrix.append(row)
        
        # Find strong correlations
        strong_correlations = []
        for i, band1 in enumerate(band_names):
            for j, band2 in enumerate(band_names):
                if i < j:  # Upper triangle only
                    corr = correlation_matrix[i][j]
                    if abs(corr) > 0.5:  # Strong correlation
                        strong_correlations.append({
                            'band1': band1,
                            'band2': band2,
                            'correlation': corr,
                            'strength': 'strong' if abs(corr) > 0.7 else 'moderate'
                        })
        
        return jsonify({
            'bands': band_names,
            'correlation_matrix': correlation_matrix,
            'strong_correlations': sorted(strong_correlations, key=lambda x: abs(x['correlation']), reverse=True),
            'interpretation': {
                'positive': 'Bands increase together',
                'negative': 'Bands have inverse relationship',
                'near_zero': 'No linear relationship'
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    """Serve the dashboard UI"""
    return render_template('dashboard.html')

@app.route('/api')
def api_docs():
    """API documentation"""
    return jsonify({
        'service': 'Enhanced Multimodal Lambda Architecture API',
        'version': '2.0.0',
        'integration': 'pre-ingestion-enhanced',
        'dashboard': '/',
        'endpoints': {
            'legacy': [
                '/api/realtime/ndvi',
                '/api/anomalies',
                '/api/multimodal/tabular-stats',
                '/api/multimodal/image-stats',
                '/api/multimodal/anomalies',
                '/api/multimodal/cumulative-totals'
            ],
            'enhanced': [
                '/api/enhanced/ml-features',
                '/api/enhanced/ml-features/<class_name>',
                '/api/enhanced/texture-stats',
                '/api/enhanced/texture-stats/<class_name>',
                '/api/enhanced/feature-importance',
                '/api/enhanced/summary',
                '/api/enhanced/class-comparison'
            ],
            'utility': [
                '/api/health',
                '/api'
            ]
        },
        'new_capabilities': [
            'ML-ready pre-normalized feature vectors',
            'Advanced texture analysis (GLCM + LBP)',
            'Feature importance calculation',
            'Cross-modal class comparison',
            'Interactive web dashboard'
        ]
    })

if __name__ == '__main__':
    print("\n" + "="*80)
    print("ENHANCED MULTIMODAL API SERVER")
    print("="*80)
    print("Integration: Pre-Ingestion Layer + Lambda Architecture")
    print("Port: 5000")
    print("Documentation: http://localhost:5000/")
    print("="*80 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
