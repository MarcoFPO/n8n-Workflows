#!/usr/bin/env python3
"""
Script zur Erweiterung des Frontend-Monitorings
Fügt Pipeline und ML-Analytics zu den überwachten Services hinzu
"""

import re

def extend_frontend_monitoring():
    """Erweitert das Frontend-Monitoring um Pipeline und ML-Services"""
    
    frontend_file = "/opt/aktienanalyse-ökosystem/services/frontend-service-modular/frontend_service_v7_0_1_20250816.py"
    
    # Read the current file
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
    
    content = content.replace(old_config, new_config)
    
    # 2. Erweitere Dashboard Services
    old_services = '''    # Check all backend services
    services = {
        "Data Processing": ServiceConfig.DATA_PROCESSING_URL,
        "CSV Service": ServiceConfig.CSV_SERVICE_URL,
        "Prediction Tracking": ServiceConfig.PREDICTION_TRACKING_URL
    }'''
    
    new_services = '''    # Check all backend services
    services = {
        "Data Processing": ServiceConfig.DATA_PROCESSING_URL,
        "CSV Service": ServiceConfig.CSV_SERVICE_URL,
        "Prediction Tracking": ServiceConfig.PREDICTION_TRACKING_URL,
        "ML Analytics": ServiceConfig.ML_ANALYTICS_URL,
        "Event Bus": ServiceConfig.EVENT_BUS_URL,
        "Intelligent Core": ServiceConfig.INTELLIGENT_CORE_URL
    }'''
    
    content = content.replace(old_services, new_services)
    
    # 3. Erweitere Monitoring Services (zweite Stelle)
    old_monitoring = '''    # Service health checks
    services = {
        "Data Processing Service": ServiceConfig.DATA_PROCESSING_URL,
        "CSV Service": ServiceConfig.CSV_SERVICE_URL,
        "Prediction Tracking": ServiceConfig.PREDICTION_TRACKING_URL
    }'''
    
    new_monitoring = '''    # Service health checks
    services = {
        "Data Processing Service": ServiceConfig.DATA_PROCESSING_URL,
        "CSV Service": ServiceConfig.CSV_SERVICE_URL,
        "Prediction Tracking": ServiceConfig.PREDICTION_TRACKING_URL,
        "ML Analytics Service": ServiceConfig.ML_ANALYTICS_URL,
        "Event Bus Service": ServiceConfig.EVENT_BUS_URL,
        "Intelligent Core Service": ServiceConfig.INTELLIGENT_CORE_URL
    }'''
    
    content = content.replace(old_monitoring, new_monitoring)
    
    # 4. Füge Pipeline Status Monitoring hinzu
    pipeline_monitoring_function = '''
@app.get("/api/content/pipeline-status", response_class=JSONResponse)
async def get_pipeline_status():
    """Pipeline Status und letzte Ausführung"""
    try:
        import subprocess
        import os
        from datetime import datetime
        
        # Check if pipeline automation exists
        pipeline_script = "/opt/aktienanalyse-ökosystem/automation/pipeline_automation.sh"
        pipeline_log = "/opt/aktienanalyse-ökosystem/logs/pipeline_automation.log"
        
        status = {
            "pipeline_script_exists": os.path.exists(pipeline_script),
            "log_file_exists": os.path.exists(pipeline_log),
            "last_execution": None,
            "cron_status": "unknown",
            "recent_predictions": 0
        }
        
        # Check last execution from log
        if os.path.exists(pipeline_log):
            try:
                result = subprocess.run(
                    ["tail", "-20", pipeline_log], 
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\\n')
                    for line in reversed(lines):
                        if "Pipeline execution completed successfully" in line:
                            # Extract timestamp from log line
                            if line.startswith("["):
                                timestamp_str = line[1:20]  # [2025-08-21 19:02:30]
                                status["last_execution"] = timestamp_str
                                break
            except:
                pass
        
        # Check cron status
        try:
            result = subprocess.run(
                ["crontab", "-l"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and "pipeline_automation.sh" in result.stdout:
                status["cron_status"] = "active"
            else:
                status["cron_status"] = "inactive"
        except:
            status["cron_status"] = "error"
        
        # Check recent predictions count
        try:
            import sqlite3
            conn = sqlite3.connect("/opt/aktienanalyse-ökosystem/data/ki_recommendations.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ki_recommendations WHERE DATE(created_at) = DATE('now')")
            status["recent_predictions"] = cursor.fetchone()[0]
            conn.close()
        except:
            pass
        
        return status
        
    except Exception as e:
        return {"error": str(e)}

'''
    
    # Add pipeline monitoring before the last function
    content = content.replace("if __name__ == \"__main__\":", pipeline_monitoring_function + "if __name__ == \"__main__\":")
    
    # Write back the modified content
    with open(frontend_file, 'w') as f:
        f.write(content)
    
    print("✅ Frontend monitoring extended successfully")
    print("Added services: ML Analytics, Event Bus, Intelligent Core")
    print("Added endpoint: /api/content/pipeline-status")

if __name__ == "__main__":
    extend_frontend_monitoring()