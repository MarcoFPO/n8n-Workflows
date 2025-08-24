#!/usr/bin/env python3
"""
Copy Integration Files to Production Script v1.0.0
Kopiert die 4-Modell-Integration Dateien auf den Produktionsserver

Autor: Claude Code
Datum: 23. August 2025
Version: 1.0.0
"""

import shutil
import os
import sys
from pathlib import Path
import subprocess
import json
from datetime import datetime

def log_message(message, level="INFO"):
    """Log message with timestamp"""
    timestamp = datetime.utcnow().isoformat()
    print(f"[{timestamp}] [{level}] {message}")

def copy_integration_files():
    """Kopiert Integration-Dateien auf den Produktionsserver"""
    
    # Source and destination paths
    source_base = "/home/mdoehler/aktienanalyse-ökosystem"
    dest_base = "/opt/aktienanalyse-ökosystem"
    
    files_to_copy = [
        {
            "source": f"{source_base}/shared/ml_prediction_event_types_v1.0.0_20250823.py",
            "dest": f"{dest_base}/shared/ml_prediction_event_types_v1.0.0_20250823.py",
            "description": "ML Event Types"
        },
        {
            "source": f"{source_base}/services/ml-analytics-service-modular/ml_prediction_publisher_v1.0.0_20250823.py",
            "dest": f"{dest_base}/services/ml-analytics-service-modular/ml_prediction_publisher_v1.0.0_20250823.py",
            "description": "ML Prediction Publisher"
        },
        {
            "source": f"{source_base}/services/data-processing-service-modular/ml_prediction_storage_handler_v1.0.0_20250823.py",
            "dest": f"{dest_base}/services/data-processing-service-modular/ml_prediction_storage_handler_v1.0.0_20250823.py",
            "description": "ML Prediction Storage Handler"
        },
        {
            "source": f"{source_base}/services/data-processing-service-modular/enhanced_data_processing_service_v4.3.0_20250823.py",
            "dest": f"{dest_base}/services/data-processing-service-modular/enhanced_data_processing_service_v4.3.0_20250823.py",
            "description": "Enhanced Data Processing Service"
        }
    ]
    
    log_message("Starting file copy to production...")
    
    copied_files = []
    failed_files = []
    
    for file_info in files_to_copy:
        source_path = file_info["source"]
        dest_path = file_info["dest"]
        description = file_info["description"]
        
        log_message(f"Copying {description}...")
        
        try:
            # Check if source exists
            if not os.path.exists(source_path):
                log_message(f"Source file not found: {source_path}", "ERROR")
                failed_files.append(file_info)
                continue
            
            # Create destination directory if needed
            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            
            # Copy file
            shutil.copy2(source_path, dest_path)
            
            # Set ownership to aktienanalyse:aktienanalyse
            os.system(f"sudo chown aktienanalyse:aktienanalyse {dest_path}")
            os.system(f"sudo chmod 644 {dest_path}")
            
            log_message(f"✅ Successfully copied {description}")
            copied_files.append(file_info)
            
        except Exception as e:
            log_message(f"❌ Failed to copy {description}: {str(e)}", "ERROR")
            failed_files.append(file_info)
    
    # Generate deployment report
    deployment_report = {
        "deployment_timestamp": datetime.utcnow().isoformat(),
        "deployment_type": "4_model_integration_file_copy",
        "copied_files_count": len(copied_files),
        "failed_files_count": len(failed_files),
        "copied_files": [f["description"] for f in copied_files],
        "failed_files": [f["description"] for f in failed_files],
        "status": "success" if len(failed_files) == 0 else "partial_failure"
    }
    
    # Save report
    report_path = f"{dest_base}/data/file_copy_deployment_report.json"
    try:
        with open(report_path, 'w') as f:
            json.dump(deployment_report, f, indent=2)
        log_message(f"Deployment report saved to {report_path}")
    except Exception as e:
        log_message(f"Failed to save deployment report: {str(e)}", "ERROR")
    
    # Summary
    log_message(f"File copy completed:")
    log_message(f"✅ Successfully copied: {len(copied_files)} files")
    if failed_files:
        log_message(f"❌ Failed to copy: {len(failed_files)} files")
    
    return len(failed_files) == 0

if __name__ == "__main__":
    success = copy_integration_files()
    sys.exit(0 if success else 1)