#!/usr/bin/env python3
"""
ML Service Configuration

Autor: Claude Code - Configuration Management Specialist
Datum: 26. August 2025
Clean Architecture v6.0.0 - Infrastructure Layer
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Database Configuration"""
    host: str
    port: int
    name: str
    user: str
    password: str
    
    def get_connection_url(self) -> str:
        """Get PostgreSQL connection URL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass
class ServiceConfig:
    """Service Configuration"""
    name: str
    port: int
    host: str = "0.0.0.0"
    
    def get_service_url(self) -> str:
        """Get service URL"""
        return f"http://{self.host}:{self.port}"


@dataclass
class StorageConfig:
    """Storage Configuration"""
    model_storage_path: str
    data_cache_path: str
    log_storage_path: str
    
    def ensure_directories(self) -> None:
        """Ensure all storage directories exist"""
        for path in [self.model_storage_path, self.data_cache_path, self.log_storage_path]:
            Path(path).mkdir(parents=True, exist_ok=True)


@dataclass
class MLEngineConfig:
    """ML Engine Configuration"""
    max_concurrent_predictions: int = 10
    prediction_timeout_seconds: int = 300
    model_cache_size: int = 100
    feature_cache_ttl_minutes: int = 60
    auto_retrain_enabled: bool = True
    retrain_threshold_accuracy: float = 0.7


class MLServiceConfig:
    """
    ML Service Configuration Manager
    
    Centralized configuration management for ML Analytics Service
    Supports environment variables, config files, and defaults
    """
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self._config = config_dict or {}
        self._load_environment_config()
        self._validate_config()
    
    def _load_environment_config(self) -> None:
        """Load configuration from environment variables"""
        
        # Service Configuration
        if "service" not in self._config:
            self._config["service"] = {}
        
        self._config["service"].setdefault("port", int(os.getenv("ML_ANALYTICS_SERVICE_PORT", "8021")))
        self._config["service"].setdefault("host", os.getenv("ML_ANALYTICS_SERVICE_HOST", "0.0.0.0"))
        self._config["service"].setdefault("name", "ml-analytics-service")
        
        # Database Configuration
        if "database" not in self._config:
            self._config["database"] = {}
        
        self._config["database"].setdefault("host", os.getenv("POSTGRES_HOST", os.getenv("ML_SERVICE_HOST", "10.1.1.174")))
        self._config["database"].setdefault("port", int(os.getenv("POSTGRES_PORT", "5432")))
        self._config["database"].setdefault("name", os.getenv("POSTGRES_DB", "aktienanalyse"))
        self._config["database"].setdefault("user", os.getenv("POSTGRES_USER", "aktienanalyse"))
        self._config["database"].setdefault("password", os.getenv("POSTGRES_PASSWORD", ""))
        
        # Storage Configuration
        if "storage" not in self._config:
            self._config["storage"] = {}
        
        base_path = os.getenv("ML_SERVICE_BASE_PATH", "/home/mdoehler/aktienanalyse-ökosystem/services/ml-analytics-service")
        self._config["storage"].setdefault("model_storage_path", os.getenv("ML_MODEL_STORAGE_PATH", f"{base_path}/models"))
        self._config["storage"].setdefault("data_cache_path", os.getenv("ML_DATA_CACHE_PATH", f"{base_path}/cache"))
        self._config["storage"].setdefault("log_storage_path", os.getenv("ML_LOG_STORAGE_PATH", f"{base_path}/logs"))
        
        # ML Engine Configuration  
        if "ml_engines" not in self._config:
            self._config["ml_engines"] = {}
        
        self._config["ml_engines"].setdefault("max_concurrent_predictions", int(os.getenv("ML_MAX_CONCURRENT_PREDICTIONS", "10")))
        self._config["ml_engines"].setdefault("prediction_timeout_seconds", int(os.getenv("ML_PREDICTION_TIMEOUT", "300")))
        self._config["ml_engines"].setdefault("model_cache_size", int(os.getenv("ML_MODEL_CACHE_SIZE", "100")))
        self._config["ml_engines"].setdefault("feature_cache_ttl_minutes", int(os.getenv("ML_FEATURE_CACHE_TTL", "60")))
        self._config["ml_engines"].setdefault("auto_retrain_enabled", os.getenv("ML_AUTO_RETRAIN_ENABLED", "true").lower() == "true")
        self._config["ml_engines"].setdefault("retrain_threshold_accuracy", float(os.getenv("ML_RETRAIN_THRESHOLD", "0.7")))
    
    def _validate_config(self) -> None:
        """Validate configuration values"""
        
        # Validate service port
        port = self._config["service"]["port"]
        if not 1024 <= port <= 65535:
            raise ValueError(f"Invalid service port: {port}. Must be between 1024 and 65535")
        
        # Validate database port
        db_port = self._config["database"]["port"]
        if not 1 <= db_port <= 65535:
            raise ValueError(f"Invalid database port: {db_port}")
        
        # Validate ML engine settings
        max_concurrent = self._config["ml_engines"]["max_concurrent_predictions"]
        if max_concurrent <= 0:
            raise ValueError(f"Max concurrent predictions must be positive: {max_concurrent}")
        
        timeout = self._config["ml_engines"]["prediction_timeout_seconds"]
        if timeout <= 0:
            raise ValueError(f"Prediction timeout must be positive: {timeout}")
        
        accuracy_threshold = self._config["ml_engines"]["retrain_threshold_accuracy"]
        if not 0.0 <= accuracy_threshold <= 1.0:
            raise ValueError(f"Retrain threshold accuracy must be between 0.0 and 1.0: {accuracy_threshold}")
    
    def get_service_config(self) -> ServiceConfig:
        """Get service configuration"""
        service_cfg = self._config["service"]
        return ServiceConfig(
            name=service_cfg["name"],
            port=service_cfg["port"],
            host=service_cfg["host"]
        )
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        db_cfg = self._config["database"]
        return DatabaseConfig(
            host=db_cfg["host"],
            port=db_cfg["port"],
            name=db_cfg["name"],
            user=db_cfg["user"],
            password=db_cfg["password"]
        )
    
    def get_storage_config(self) -> StorageConfig:
        """Get storage configuration"""
        storage_cfg = self._config["storage"]
        storage_config = StorageConfig(
            model_storage_path=storage_cfg["model_storage_path"],
            data_cache_path=storage_cfg["data_cache_path"],
            log_storage_path=storage_cfg["log_storage_path"]
        )
        storage_config.ensure_directories()
        return storage_config
    
    def get_ml_engine_config(self) -> MLEngineConfig:
        """Get ML engine configuration"""
        ml_cfg = self._config["ml_engines"]
        return MLEngineConfig(
            max_concurrent_predictions=ml_cfg["max_concurrent_predictions"],
            prediction_timeout_seconds=ml_cfg["prediction_timeout_seconds"],
            model_cache_size=ml_cfg["model_cache_size"],
            feature_cache_ttl_minutes=ml_cfg["feature_cache_ttl_minutes"],
            auto_retrain_enabled=ml_cfg["auto_retrain_enabled"],
            retrain_threshold_accuracy=ml_cfg["retrain_threshold_accuracy"]
        )
    
    def get_database_url(self) -> str:
        """Get database connection URL"""
        return self.get_database_config().get_connection_url()
    
    def get_service_url(self) -> str:
        """Get service URL"""
        return self.get_service_config().get_service_url()
    
    def get_model_storage_path(self) -> str:
        """Get model storage path"""
        return self._config["storage"]["model_storage_path"]
    
    def get_service_port(self) -> int:
        """Get service port"""
        return self._config["service"]["port"]
    
    def is_production_mode(self) -> bool:
        """Check if running in production mode"""
        return os.getenv("ML_SERVICE_ENVIRONMENT", "development").lower() == "production"
    
    def is_debug_enabled(self) -> bool:
        """Check if debug logging is enabled"""
        return os.getenv("ML_SERVICE_DEBUG", "false").lower() == "true"
    
    def get_log_level(self) -> str:
        """Get logging level"""
        if self.is_debug_enabled():
            return "DEBUG"
        elif self.is_production_mode():
            return "WARNING"
        else:
            return "INFO"
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return self._config.copy()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for logging"""
        return {
            "service": {
                "name": self._config["service"]["name"],
                "port": self._config["service"]["port"],
                "host": self._config["service"]["host"]
            },
            "database": {
                "host": self._config["database"]["host"],
                "port": self._config["database"]["port"],
                "name": self._config["database"]["name"],
                "user": self._config["database"]["user"]
                # Intentionally exclude password from summary
            },
            "storage": {
                "model_storage_path": self._config["storage"]["model_storage_path"],
                "data_cache_path": self._config["storage"]["data_cache_path"],
                "log_storage_path": self._config["storage"]["log_storage_path"]
            },
            "ml_engines": self._config["ml_engines"],
            "environment": {
                "production_mode": self.is_production_mode(),
                "debug_enabled": self.is_debug_enabled(),
                "log_level": self.get_log_level()
            }
        }