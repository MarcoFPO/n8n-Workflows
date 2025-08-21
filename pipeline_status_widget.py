#!/usr/bin/env python3
"""
Pipeline Status Widget für das Dashboard
"""

def add_pipeline_status_endpoint():
    """Fügt Pipeline Status Endpoint zum Frontend hinzu"""
    
    frontend_file = "/opt/aktienanalyse-ökosystem/services/frontend-service-modular/frontend_service_v7_0_1_20250816.py"
    
    # Pipeline Status Endpoint
    pipeline_endpoint = '''
@app.get("/api/pipeline/status", response_class=JSONResponse)
async def get_pipeline_status():
    """Pipeline Status und letzte Ausführung"""
    try:
        import subprocess
        import os
        import sqlite3
        from datetime import datetime
        
        # Check if pipeline automation exists
        pipeline_script = "/opt/aktienanalyse-ökosystem/automation/pipeline_automation.sh"
        pipeline_log = "/opt/aktienanalyse-ökosystem/logs/pipeline_automation.log"
        
        status = {
            "pipeline_script_exists": os.path.exists(pipeline_script),
            "log_file_exists": os.path.exists(pipeline_log),
            "last_execution": None,
            "cron_status": "unknown",
            "recent_predictions": 0,
            "status": "unknown"
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
                                status["status"] = "success"
                                break
                        elif "Pipeline execution failed" in line or "ERROR" in line.upper():
                            if line.startswith("["):
                                timestamp_str = line[1:20]
                                status["last_execution"] = timestamp_str
                                status["status"] = "failed"
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
            conn = sqlite3.connect("/opt/aktienanalyse-ökosystem/data/ki_recommendations.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ki_recommendations WHERE DATE(created_at) = DATE('now')")
            status["recent_predictions"] = cursor.fetchone()[0]
            conn.close()
        except:
            pass
        
        return status
        
    except Exception as e:
        return {"error": str(e), "status": "error"}

'''
    
    # Read file
    with open(frontend_file, 'r') as f:
        content = f.read()
    
    # Add before the main check
    if 'get_pipeline_status' not in content:
        # Insert before if __name__ == "__main__":
        content = content.replace('if __name__ == "__main__":', pipeline_endpoint + 'if __name__ == "__main__":')
        
        # Write back
        with open(frontend_file, 'w') as f:
            f.write(content)
        
        print("✅ Pipeline status endpoint added successfully")
    else:
        print("✅ Pipeline status endpoint already exists")

if __name__ == "__main__":
    add_pipeline_status_endpoint()