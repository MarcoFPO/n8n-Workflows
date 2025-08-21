#!/usr/bin/env python3
"""
Einfache Erweiterung des Frontend-Monitorings
Nur Service-URLs hinzufügen ohne komplexe Änderungen
"""

def simple_extend_monitoring():
    """Einfache Erweiterung der Service-URLs"""
    
    frontend_file = "/opt/aktienanalyse-ökosystem/services/frontend-service-modular/frontend_service_v7_0_1_20250816.py"
    
    # Read file
    with open(frontend_file, 'r') as f:
        content = f.read()
    
    # 1. Erweitere ServiceConfig um neue URLs
    old_config = '''    # Backend Service URLs
    DATA_PROCESSING_URL = "http://localhost:8017"
    CSV_SERVICE_URL = "http://localhost:8019"
    PREDICTION_TRACKING_URL = "http://localhost:8018"'''
    
    new_config = '''    # Backend Service URLs
    DATA_PROCESSING_URL = "http://localhost:8017"
    CSV_SERVICE_URL = "http://localhost:8019"
    PREDICTION_TRACKING_URL = "http://localhost:8018"
    ML_ANALYTICS_URL = "http://localhost:8021"
    EVENT_BUS_URL = "http://localhost:8014"
    INTELLIGENT_CORE_URL = "http://localhost:8011"'''
    
    if old_config in content:
        content = content.replace(old_config, new_config)
        print("✅ Added new service URLs to ServiceConfig")
    
    # 2. Erweitere Dashboard Services
    old_services = '''    services = {
        "Data Processing": ServiceConfig.DATA_PROCESSING_URL,
        "CSV Service": ServiceConfig.CSV_SERVICE_URL,
        "Prediction Tracking": ServiceConfig.PREDICTION_TRACKING_URL
    }'''
    
    new_services = '''    services = {
        "Data Processing": ServiceConfig.DATA_PROCESSING_URL,
        "CSV Service": ServiceConfig.CSV_SERVICE_URL,
        "Prediction Tracking": ServiceConfig.PREDICTION_TRACKING_URL,
        "ML Analytics": ServiceConfig.ML_ANALYTICS_URL,
        "Event Bus": ServiceConfig.EVENT_BUS_URL,
        "Intelligent Core": ServiceConfig.INTELLIGENT_CORE_URL
    }'''
    
    if old_services in content:
        content = content.replace(old_services, new_services)
        print("✅ Extended dashboard services monitoring")
    
    # 3. Erweitere Monitoring Services für zweite Stelle
    old_monitoring = '''    services = {
        "Data Processing Service": ServiceConfig.DATA_PROCESSING_URL,
        "CSV Service": ServiceConfig.CSV_SERVICE_URL,
        "Prediction Tracking": ServiceConfig.PREDICTION_TRACKING_URL
    }'''
    
    new_monitoring = '''    services = {
        "Data Processing Service": ServiceConfig.DATA_PROCESSING_URL,
        "CSV Service": ServiceConfig.CSV_SERVICE_URL,
        "Prediction Tracking": ServiceConfig.PREDICTION_TRACKING_URL,
        "ML Analytics Service": ServiceConfig.ML_ANALYTICS_URL,
        "Event Bus Service": ServiceConfig.EVENT_BUS_URL,
        "Intelligent Core Service": ServiceConfig.INTELLIGENT_CORE_URL
    }'''
    
    if old_monitoring in content:
        content = content.replace(old_monitoring, new_monitoring)
        print("✅ Extended monitoring page services")
    
    # Write back
    with open(frontend_file, 'w') as f:
        f.write(content)
    
    print("✅ Frontend monitoring extension completed successfully")

if __name__ == "__main__":
    simple_extend_monitoring()