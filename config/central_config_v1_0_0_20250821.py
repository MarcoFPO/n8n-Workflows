"""
Central Configuration Module v1.0.0
Zentrale Konfigurationsverwaltung für alle Services
Eliminiert hardcoded Pfade und Service-URLs
"""

import os
from pathlib import Path
from typing import Dict, Any

class CentralConfig:
    """Zentrale Konfigurationsverwaltung"""
    
    def __init__(self):
        # Basis-Pfade dynamisch ermitteln
        self.PROJECT_ROOT = Path(__file__).parent.parent.absolute()
        self.SERVICES_DIR = self.PROJECT_ROOT / "services"
        self.DATA_DIR = self.PROJECT_ROOT / "data"
        self.LOGS_DIR = self.PROJECT_ROOT / "logs"
        
        # Service-Konfiguration
        self.SERVICES = {
            "intelligent_core": {
                "host": "localhost",
                "port": 8001,
                "health_endpoint": "/health"
            },
            "broker_gateway": {
                "host": "localhost", 
                "port": 8002,
                "health_endpoint": "/health"
            },
            "frontend": {
                "host": "0.0.0.0",
                "port": 8080,
                "health_endpoint": "/health"
            },
            "event_bus": {
                "host": "localhost",
                "port": 8014,
                "health_endpoint": "/health"
            },
            "monitoring": {
                "host": "localhost",
                "port": 8015,
                "health_endpoint": "/health"
            },
            "diagnostic": {
                "host": "localhost",
                "port": 8013,
                "health_endpoint": "/health"
            },
            "data_processing": {
                "host": "localhost",
                "port": 8017,
                "health_endpoint": "/health"
            },
            "prediction_tracking": {
                "host": "localhost",
                "port": 8018,
                "health_endpoint": "/health"
            },
            "health_monitor": {
                "host": "localhost",
                "port": 8090,
                "health_endpoint": "/health"
            }
        }
        
        # Trading-Konfiguration
        self.TRADING_CONFIG = {
            "fees": {
                "BTC_EUR": 0.0015,  # 0.15%
                "ETH_EUR": 0.0015,  # 0.15%
                "ADA_EUR": 0.002,   # 0.2%
                "default": 0.001    # 0.1%
            },
            "limits": {
                "max_order_size": 10000,
                "min_order_size": 10,
                "daily_limit": 50000
            }
        }
        
        # Database-Konfiguration
        self.DATABASE_CONFIG = {
            "event_store": {
                "host": "localhost",
                "port": 5432,
                "database": "event_store_db",
                "user": os.getenv("DB_USER", "postgres"),
                "password": os.getenv("DB_PASSWORD", ""),
            },
            "redis_cache": {
                "host": "localhost",
                "port": 6379,
                "db": 0
            }
        }
    
    def get_service_url(self, service_name: str) -> str:
        """Service-URL dynamisch generieren"""
        if service_name not in self.SERVICES:
            raise ValueError(f"Unknown service: {service_name}")
        
        service = self.SERVICES[service_name]
        return f"http://{service['host']}:{service['port']}"
    
    def get_service_health_url(self, service_name: str) -> str:
        """Service Health-Check URL generieren"""
        base_url = self.get_service_url(service_name)
        health_endpoint = self.SERVICES[service_name]["health_endpoint"]
        return f"{base_url}{health_endpoint}"
    
    def get_project_path(self, *paths) -> Path:
        """Relativen Projekt-Pfad generieren"""
        return self.PROJECT_ROOT.joinpath(*paths)
    
    def add_project_to_python_path(self) -> None:
        """Projekt-Root zu Python-Path hinzufügen (Clean Way)"""
        import sys
        project_str = str(self.PROJECT_ROOT)
        if project_str not in sys.path:
            sys.path.insert(0, project_str)

# Globale Instanz
config = CentralConfig()

# Convenience-Funktionen
def get_service_url(service_name: str) -> str:
    return config.get_service_url(service_name)

def get_project_path(*paths) -> Path:
    return config.get_project_path(*paths)

def setup_python_path() -> None:
    config.add_project_to_python_path()