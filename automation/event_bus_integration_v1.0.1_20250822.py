#!/usr/bin/env python3
"""
Event-Bus Integration für Pipeline Automation
Erweitert den Event-Bus um Pipeline-spezifische Trigger
"""

import requests
import json
from datetime import datetime
import sys
import sqlite3
from pathlib import Path

class PipelineEventBus:
    """Event-Bus Integration für Pipeline Events"""
    
    def __init__(self, event_bus_url="http://localhost:8014"):
        self.event_bus_url = event_bus_url
        self.db_path = "/opt/aktienanalyse-ökosystem/data/ki_recommendations.db"
    
    def publish_event(self, event_type: str, data: dict):
        """Event an Event-Bus senden"""
        event_payload = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        try:
            # Versuche verschiedene Event-Bus Endpoints
            endpoints = ["/events", "/publish", "/event"]
            
            for endpoint in endpoints:
                try:
                    response = requests.post(
                        f"{self.event_bus_url}{endpoint}",
                        json=event_payload,
                        timeout=5
                    )
                    if response.status_code == 200:
                        print(f"✅ Event published to {endpoint}: {event_type}")
                        return True
                except:
                    continue
            
            # Falls Event-Bus nicht verfügbar, logge lokal
            self._log_event_locally(event_payload)
            return False
            
        except Exception as e:
            print(f"❌ Event-Bus error: {e}")
            self._log_event_locally(event_payload)
            return False
    
    def _log_event_locally(self, event_payload):
        """Event lokal loggen falls Event-Bus nicht verfügbar"""
        log_file = "/opt/aktienanalyse-ökosystem/logs/events_local.log"
        try:
            with open(log_file, "a") as f:
                f.write(f"{json.dumps(event_payload)}\n")
            print(f"📝 Event logged locally: {event_payload['event_type']}")
        except Exception as e:
            print(f"❌ Local logging failed: {e}")
    
    def get_predictions_count(self) -> int:
        """Aktuelle Anzahl Predictions aus DB"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ki_recommendations WHERE DATE(created_at) = DATE('now')")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def publish_pipeline_completed(self, status="success"):
        """Pipeline Completion Event"""
        data = {
            "status": status,
            "predictions_count": self.get_predictions_count(),
            "execution_time": datetime.now().isoformat(),
            "source": "pipeline_automation"
        }
        return self.publish_event("pipeline.automation.completed", data)
    
    def publish_pipeline_started(self):
        """Pipeline Start Event"""
        data = {
            "execution_time": datetime.now().isoformat(),
            "source": "pipeline_automation"
        }
        return self.publish_event("pipeline.automation.started", data)
    
    def publish_pipeline_failed(self, error_message):
        """Pipeline Failure Event"""
        data = {
            "status": "failed",
            "error": error_message,
            "execution_time": datetime.now().isoformat(),
            "source": "pipeline_automation"
        }
        return self.publish_event("pipeline.automation.failed", data)

def main():
    """CLI Interface für Event-Bus Integration"""
    if len(sys.argv) < 2:
        print("Usage: python3 event_bus_integration.py <event_type> [data]")
        sys.exit(1)
    
    event_bus = PipelineEventBus()
    event_type = sys.argv[1]
    
    if event_type == "pipeline.completed":
        status = sys.argv[2] if len(sys.argv) > 2 else "success"
        event_bus.publish_pipeline_completed(status)
    elif event_type == "pipeline.started":
        event_bus.publish_pipeline_started()
    elif event_type == "pipeline.failed":
        error = sys.argv[2] if len(sys.argv) > 2 else "Unknown error"
        event_bus.publish_pipeline_failed(error)
    else:
        print(f"Unknown event type: {event_type}")
        sys.exit(1)

if __name__ == "__main__":
    main()