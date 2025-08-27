#!/usr/bin/env python3
"""
Configuration Manager - Zentralisierte Konfiguration
Clean Architecture konforme Environment-Variable Verwaltung

Alle Services sollen diese zentrale Konfiguration verwenden
anstatt hardcodierte URLs und Werte zu nutzen.
"""

import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DatabaseConfig:
    """PostgreSQL Database Konfiguration"""
    host: str
    port: int
    database: str
    user: str
    password: str
    
    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class RedisConfig:
    """Redis Cache Konfiguration"""
    host: str
    port: int
    db: int
    
    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class ServiceConfig:
    """Service-zu-Service Kommunikation Konfiguration"""
    host: str
    port: int
    
    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class ConfigManager:
    """Zentraler Configuration Manager für alle Services"""
    
    def __init__(self, env_file: Optional[Path] = None):
        if env_file and env_file.exists():
            self._load_env_file(env_file)
    
    def _load_env_file(self, env_file: Path):
        """Lädt Environment Variables aus .env Datei"""
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, _, value = line.partition('=')
                    os.environ[key.strip()] = value.strip()
    
    @property
    def database(self) -> DatabaseConfig:
        """PostgreSQL Database Konfiguration"""
        return DatabaseConfig(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', '5432')),
            database=os.getenv('POSTGRES_DB', 'aktienanalyse_events'),
            user=os.getenv('POSTGRES_USER', 'aktienanalyse'),
            password=os.getenv('POSTGRES_PASSWORD', 'secure_password_2025')
        )
    
    @property
    def redis(self) -> RedisConfig:
        """Redis Cache Konfiguration"""
        return RedisConfig(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0'))
        )
    
    @property
    def frontend_service(self) -> ServiceConfig:
        """Frontend Service Konfiguration"""
        return ServiceConfig(
            host=os.getenv('FRONTEND_HOST', 'localhost'),
            port=int(os.getenv('FRONTEND_PORT', '8080'))
        )
    
    @property
    def prediction_tracking_service(self) -> ServiceConfig:
        """Prediction Tracking Service Konfiguration"""
        return ServiceConfig(
            host=os.getenv('PREDICTION_TRACKING_HOST', 'localhost'),
            port=int(os.getenv('PREDICTION_TRACKING_PORT', '8018'))
        )
    
    @property
    def event_bus_service(self) -> ServiceConfig:
        """Event Bus Service Konfiguration"""
        return ServiceConfig(
            host=os.getenv('EVENT_BUS_HOST', 'localhost'),
            port=int(os.getenv('EVENT_BUS_PORT', '8014'))
        )
    
    @property
    def ml_analytics_service(self) -> ServiceConfig:
        """ML Analytics Service Konfiguration"""
        return ServiceConfig(
            host=os.getenv('ML_ANALYTICS_HOST', 'localhost'),
            port=int(os.getenv('ML_ANALYTICS_PORT', '8021'))
        )
    
    @property
    def data_processing_service(self) -> ServiceConfig:
        """Data Processing Service Konfiguration"""
        return ServiceConfig(
            host=os.getenv('DATA_PROCESSING_HOST', 'localhost'),
            port=int(os.getenv('DATA_PROCESSING_PORT', '8017'))
        )
    
    @property
    def broker_gateway_service(self) -> ServiceConfig:
        """Broker Gateway Service Konfiguration"""
        return ServiceConfig(
            host=os.getenv('BROKER_GATEWAY_HOST', 'localhost'),
            port=int(os.getenv('BROKER_GATEWAY_PORT', '8012'))
        )
    
    @property
    def intelligent_core_service(self) -> ServiceConfig:
        """Intelligent Core Service Konfiguration"""
        return ServiceConfig(
            host=os.getenv('INTELLIGENT_CORE_HOST', 'localhost'),
            port=int(os.getenv('INTELLIGENT_CORE_PORT', '8001'))
        )
    
    @property
    def monitoring_service(self) -> ServiceConfig:
        """System Monitoring Service Konfiguration"""
        return ServiceConfig(
            host=os.getenv('MONITORING_HOST', 'localhost'),
            port=int(os.getenv('MONITORING_PORT', '8015'))
        )
    
    @property
    def diagnostic_service(self) -> ServiceConfig:
        """Diagnostic Service Konfiguration"""
        return ServiceConfig(
            host=os.getenv('DIAGNOSTIC_HOST', 'localhost'),
            port=int(os.getenv('DIAGNOSTIC_PORT', '8013'))
        )
    
    @property
    def marketcap_service(self) -> ServiceConfig:
        """MarketCap Service Konfiguration"""
        return ServiceConfig(
            host=os.getenv('MARKETCAP_HOST', 'localhost'),
            port=int(os.getenv('MARKETCAP_PORT', '8011'))
        )
    
    @property
    def log_level(self) -> str:
        """Logging Level"""
        return os.getenv('LOG_LEVEL', 'INFO')
    
    @property
    def log_file(self) -> Optional[str]:
        """Log File Path"""
        return os.getenv('LOG_FILE')
    
    @property
    def debug_mode(self) -> bool:
        """Debug Mode Status"""
        return os.getenv('DEBUG_MODE', 'false').lower() == 'true'


# Globale Config-Instanz für alle Services
config = ConfigManager(Path('/opt/aktienanalyse-ökosystem/.env'))