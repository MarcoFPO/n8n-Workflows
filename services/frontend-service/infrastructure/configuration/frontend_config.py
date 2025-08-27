#!/usr/bin/env python3
"""
Frontend Service Configuration - Infrastructure Layer
Frontend Service Clean Architecture v1.0.0

INFRASTRUCTURE LAYER - CONFIGURATION:
- Environment-based Configuration Management
- Service URL Management  
- CORS and Security Settings
- Performance Configuration

CLEAN ARCHITECTURE PRINCIPLES:
- Configuration Isolation: All config in one place
- Environment Driven: No hardcoded values
- Validation: Config validation on startup

Autor: Claude Code - Clean Architecture Specialist  
Datum: 26. August 2025
Version: 1.0.0
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class Environment(Enum):
    """Environment Types"""
    PRODUCTION = "production"
    DEVELOPMENT = "development"  
    TEST = "test"


class LogLevel(Enum):
    """Log Levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class ServiceConfiguration:
    """Service Configuration Data Class"""
    name: str
    url: str
    port: str
    health_endpoint: str = "/health"
    timeout_seconds: int = 10
    is_critical: bool = False


class FrontendServiceConfig:
    """
    Frontend Service Configuration Manager
    
    RESPONSIBILITIES:
    - Environment variable management
    - Service URL configuration
    - Performance settings
    - Security settings
    
    CONFIGURATION SOURCES (Priority Order):
    1. Environment Variables
    2. Configuration File
    3. Default Values
    """
    
    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration with optional overrides
        
        Args:
            config_overrides: Optional configuration overrides
        """
        self._config_overrides = config_overrides or {}
        self._is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize and validate configuration"""
        if self._is_initialized:
            return
        
        logger.info("Initializing Frontend Service Configuration...")
        
        # Load and validate all configuration sections
        self._validate_configuration()
        
        self._is_initialized = True
        logger.info(f"Configuration initialized for {self.get_environment().value} environment")
    
    # ==========================================================================
    # CORE SERVICE CONFIGURATION
    # ==========================================================================
    
    def get_version(self) -> str:
        """Get service version"""
        return self._get_config_value("VERSION", "1.0.0")
    
    def get_service_name(self) -> str:
        """Get service name"""
        return self._get_config_value(
            "SERVICE_NAME", 
            "Frontend Service - Clean Architecture v1.0.0"
        )
    
    def get_environment(self) -> Environment:
        """Get current environment"""
        env_str = self._get_config_value("ENVIRONMENT", "production")
        try:
            return Environment(env_str)
        except ValueError:
            logger.warning(f"Invalid environment '{env_str}', defaulting to production")
            return Environment.PRODUCTION
    
    def get_host(self) -> str:
        """Get service host"""
        return self._get_config_value("FRONTEND_HOST", "0.0.0.0")
    
    def get_port(self) -> int:
        """Get service port"""
        return int(self._get_config_value("FRONTEND_PORT", "8080"))
    
    def get_log_level(self) -> LogLevel:
        """Get log level"""
        level_str = self._get_config_value("LOG_LEVEL", "INFO")
        try:
            return LogLevel(level_str.upper())
        except ValueError:
            logger.warning(f"Invalid log level '{level_str}', defaulting to INFO")
            return LogLevel.INFO
    
    # ==========================================================================
    # BACKEND SERVICE URLS
    # ==========================================================================
    
    def get_service_urls(self) -> Dict[str, str]:
        """Get all backend service URLs"""
        return {
            "data_processing": self._get_config_value(
                "DATA_PROCESSING_URL", "http://10.1.1.174:8017"
            ),
            "csv_service": self._get_config_value(
                "CSV_SERVICE_URL", "http://10.1.1.174:8030"
            ),
            "prediction_tracking": self._get_config_value(
                "PREDICTION_TRACKING_URL", "http://10.1.1.174:8018"
            ),
            "ml_analytics": self._get_config_value(
                "ML_ANALYTICS_URL", "http://10.1.1.174:8021"
            ),
            "event_bus": self._get_config_value(
                "EVENT_BUS_URL", "http://10.1.1.174:8014"
            ),
            "intelligent_core": self._get_config_value(
                "INTELLIGENT_CORE_URL", "http://10.1.1.174:8001"
            ),
            "broker_gateway": self._get_config_value(
                "BROKER_GATEWAY_URL", "http://10.1.1.174:8012"
            ),
            "system_monitoring": self._get_config_value(
                "SYSTEM_MONITORING_URL", "http://10.1.1.174:8015"
            ),
            "vergleichsanalyse": self._get_config_value(
                "VERGLEICHSANALYSE_SERVICE_URL", "http://10.1.1.174:8025"
            ),
            "enhanced_predictions_averages": self._get_config_value(
                "ENHANCED_PREDICTIONS_AVERAGES_URL", "http://10.1.1.105:8087"
            )
        }
    
    def get_service_configurations(self) -> List[ServiceConfiguration]:
        """Get detailed service configurations"""
        service_urls = self.get_service_urls()
        
        configurations = []
        service_metadata = {
            "data_processing": {"port": "8017", "critical": True},
            "csv_service": {"port": "8030", "critical": False},
            "prediction_tracking": {"port": "8018", "critical": True},
            "ml_analytics": {"port": "8021", "critical": True},
            "event_bus": {"port": "8014", "critical": True},
            "intelligent_core": {"port": "8001", "critical": False},
            "broker_gateway": {"port": "8012", "critical": False},
            "system_monitoring": {"port": "8015", "critical": False},
            "vergleichsanalyse": {"port": "8025", "critical": False},
            "enhanced_predictions_averages": {"port": "8087", "critical": False}
        }
        
        for service_name, url in service_urls.items():
            metadata = service_metadata.get(service_name, {"port": "unknown", "critical": False})
            
            configurations.append(ServiceConfiguration(
                name=service_name.replace("_", "-").title(),
                url=url,
                port=metadata["port"], 
                is_critical=metadata["critical"]
            ))
        
        return configurations
    
    # ==========================================================================
    # TIMEFRAME CONFIGURATION
    # ==========================================================================
    
    def get_timeframe_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Get timeframe configurations"""
        return {
            "1W": {
                "display_name": "1 Woche",
                "description": "Wöchentliche Analysen",
                "days": 7,
                "icon": "📊",
                "css_class": "timeframe-week"
            },
            "1M": {
                "display_name": "1 Monat", 
                "description": "Monatliche Analysen",
                "days": 30,
                "icon": "📈",
                "css_class": "timeframe-month"
            },
            "3M": {
                "display_name": "3 Monate",
                "description": "Quartalsweise Analysen", 
                "days": 90,
                "icon": "📊",
                "css_class": "timeframe-quarter"
            },
            "6M": {
                "display_name": "6 Monate",
                "description": "Halbjährliche Analysen",
                "days": 180,
                "icon": "📊", 
                "css_class": "timeframe-half-year"
            },
            "12M": {
                "display_name": "12 Monate",
                "description": "Jährliche Analysen",
                "days": 365,
                "icon": "📈",
                "css_class": "timeframe-year"
            }
        }
    
    def get_vergleichsanalyse_timeframes(self) -> Dict[str, Dict[str, Any]]:
        """Get SOLL-IST comparison timeframe configurations"""
        prediction_tracking_url = self.get_service_urls()["prediction_tracking"]
        
        timeframes = {}
        for code, config in self.get_timeframe_configurations().items():
            if code in ["1W", "1M", "3M", "12M"]:  # Only supported timeframes
                timeframes[code] = {
                    **config,
                    "url": f"{prediction_tracking_url}/api/v1/soll-ist-comparison?days_back={config['days']}"
                }
        
        return timeframes
    
    # ==========================================================================
    # CORS & SECURITY CONFIGURATION
    # ==========================================================================
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS allowed origins"""
        origins_str = self._get_config_value("CORS_ORIGINS", "*")
        if origins_str == "*":
            return ["*"]
        return [origin.strip() for origin in origins_str.split(",")]
    
    def get_cors_configuration(self) -> Dict[str, Any]:
        """Get complete CORS configuration"""
        return {
            "allow_origins": self.get_cors_origins(),
            "allow_credentials": self._get_config_bool("CORS_ALLOW_CREDENTIALS", True),
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["*"]
        }
    
    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled"""
        return self.get_environment() == Environment.DEVELOPMENT
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers configuration"""
        if self.is_debug_enabled():
            return {}  # No security headers in development
        
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        }
    
    # ==========================================================================
    # PERFORMANCE CONFIGURATION  
    # ==========================================================================
    
    def get_http_timeout(self) -> int:
        """Get HTTP client timeout in seconds"""
        return int(self._get_config_value("HTTP_TIMEOUT_SECONDS", "30"))
    
    def get_max_connections(self) -> int:
        """Get maximum HTTP connections"""
        return int(self._get_config_value("HTTP_MAX_CONNECTIONS", "100"))
    
    def get_health_check_interval(self) -> int:
        """Get health check interval in seconds"""
        return int(self._get_config_value("HEALTH_CHECK_INTERVAL_SECONDS", "60"))
    
    def get_cache_ttl(self) -> int:
        """Get cache TTL in seconds"""
        return int(self._get_config_value("CACHE_TTL_SECONDS", "300"))  # 5 minutes
    
    def get_template_cache_enabled(self) -> bool:
        """Check if template caching is enabled"""
        return self._get_config_bool("TEMPLATE_CACHE_ENABLED", True)
    
    # ==========================================================================
    # UI CONFIGURATION
    # ==========================================================================
    
    def get_default_theme(self) -> str:
        """Get default UI theme"""
        return self._get_config_value("DEFAULT_THEME", "default")
    
    def get_ui_configuration(self) -> Dict[str, Any]:
        """Get UI configuration"""
        return {
            "default_theme": self.get_default_theme(),
            "enable_dark_mode": self._get_config_bool("ENABLE_DARK_MODE", False),
            "default_timeframe": self._get_config_value("DEFAULT_TIMEFRAME", "1M"),
            "items_per_page": int(self._get_config_value("ITEMS_PER_PAGE", "15")),
            "enable_real_time_updates": self._get_config_bool("ENABLE_REAL_TIME_UPDATES", True)
        }
    
    # ==========================================================================
    # LOGGING CONFIGURATION
    # ==========================================================================
    
    def get_log_file_path(self) -> str:
        """Get log file path"""
        return self._get_config_value(
            "LOG_FILE_PATH", 
            "/opt/aktienanalyse-ökosystem/logs/frontend-service.log"
        )
    
    def get_log_configuration(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            "level": self.get_log_level().value,
            "file_path": self.get_log_file_path(),
            "max_file_size_mb": int(self._get_config_value("LOG_MAX_FILE_SIZE_MB", "50")),
            "backup_count": int(self._get_config_value("LOG_BACKUP_COUNT", "5")),
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    
    # ==========================================================================
    # VALIDATION & UTILITY METHODS
    # ==========================================================================
    
    def _validate_configuration(self) -> None:
        """Validate configuration values"""
        errors = []
        
        # Validate port range
        port = self.get_port()
        if not (1024 <= port <= 65535):
            errors.append(f"Invalid port {port}: must be between 1024 and 65535")
        
        # Validate service URLs
        for service_name, url in self.get_service_urls().items():
            if not url.startswith(("http://", "https://")):
                errors.append(f"Invalid URL for {service_name}: {url}")
        
        # Validate timeout values
        if self.get_http_timeout() <= 0:
            errors.append("HTTP timeout must be positive")
        
        if errors:
            raise ConfigurationValidationError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def _get_config_value(self, key: str, default: str) -> str:
        """Get configuration value with fallback"""
        # 1. Check overrides
        if key in self._config_overrides:
            return str(self._config_overrides[key])
        
        # 2. Check environment variables
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value
        
        # 3. Return default
        return default
    
    def _get_config_bool(self, key: str, default: bool) -> bool:
        """Get boolean configuration value"""
        value = self._get_config_value(key, str(default).lower())
        return value.lower() in ("true", "1", "yes", "on")
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get configuration summary for diagnostics"""
        return {
            "service": {
                "name": self.get_service_name(),
                "version": self.get_version(),
                "environment": self.get_environment().value,
                "host": self.get_host(),
                "port": self.get_port()
            },
            "services": {
                "total_configured": len(self.get_service_configurations()),
                "critical_services": len([s for s in self.get_service_configurations() if s.is_critical])
            },
            "performance": {
                "http_timeout": self.get_http_timeout(),
                "max_connections": self.get_max_connections(),
                "health_check_interval": self.get_health_check_interval()
            },
            "security": {
                "cors_enabled": len(self.get_cors_origins()) > 0,
                "debug_mode": self.is_debug_enabled()
            }
        }


class ConfigurationValidationError(Exception):
    """Configuration validation error"""
    pass