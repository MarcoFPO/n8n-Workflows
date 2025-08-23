#!/usr/bin/env python3
"""
Configuration Manager v1.0.0 - Central Configuration & Service Discovery
Ersetzt hardcoded URLs und implementiert SOLID Dependency Inversion Principle

Code-Qualität: HÖCHSTE PRIORITÄT
- Single Responsibility: Nur Configuration Management
- Open/Closed: Erweiterbar für neue Services
- Dependency Inversion: Abstract Service Discovery
- Interface Segregation: Separate Config Concerns
"""

import os
import logging
from typing import Dict, Optional, Protocol, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)

class Environment(Enum):
    """Deployment Environment Types"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
    LXC_CONTAINER = "lxc_container"

class ServiceType(Enum):
    """Service Types in Aktienanalyse Ecosystem"""
    FRONTEND = "frontend"
    INTELLIGENT_CORE = "intelligent_core"
    BROKER_GATEWAY = "broker_gateway"
    DATA_PROCESSING = "data_processing"
    EVENT_BUS = "event_bus"
    MONITORING = "monitoring"
    DIAGNOSTIC = "diagnostic"
    PREDICTION_TRACKING = "prediction_tracking"
    ML_ANALYTICS = "ml_analytics"
    CSV_SERVICE = "csv_service"
    VERGLEICHSANALYSE = "vergleichsanalyse"
    HEALTH_MONITOR = "health_monitor"

@dataclass
class ServiceEndpoint:
    """Service Endpoint Configuration"""
    host: str = "localhost"
    port: int = 8080
    protocol: str = "http"
    path: str = ""
    timeout: int = 10
    retries: int = 3
    health_check_path: str = "/health"
    
    @property
    def base_url(self) -> str:
        """Generate base URL for service"""
        return f"{self.protocol}://{self.host}:{self.port}{self.path}"
    
    @property
    def health_url(self) -> str:
        """Generate health check URL"""
        return f"{self.base_url}{self.health_check_path}"

@dataclass
class DatabaseConfig:
    """Database Configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "aktienanalyse_events"
    username: str = "aktienanalyse"
    password: str = ""
    ssl_mode: str = "disable"
    
    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?sslmode={self.ssl_mode}"

@dataclass
class RedisConfig:
    """Redis Configuration"""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    
    @property
    def connection_string(self) -> str:
        """Generate Redis connection string"""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.database}"

class IServiceDiscovery(Protocol):
    """Interface for Service Discovery - Dependency Inversion Principle"""
    
    def get_service_endpoint(self, service_type: ServiceType) -> ServiceEndpoint:
        """Get service endpoint configuration"""
        ...
    
    def get_service_url(self, service_type: ServiceType) -> str:
        """Get full service URL"""
        ...
    
    def is_service_available(self, service_type: ServiceType) -> bool:
        """Check if service is available"""
        ...

class ConfigurationManager:
    """
    Central Configuration Manager - Single Responsibility
    Manages all application configuration with environment awareness
    """
    
    def __init__(self, environment: Environment = Environment.PRODUCTION):
        self.environment = environment
        self.project_root = Path("/home/mdoehler/aktienanalyse-ökosystem")
        self.config_file = self.project_root / ".env"
        
        # Service Configuration per Environment
        self._service_configs = self._initialize_service_configs()
        self._database_config = self._initialize_database_config()
        self._redis_config = self._initialize_redis_config()
        
        # Load environment overrides
        self._load_environment_config()
        
    def _initialize_service_configs(self) -> Dict[ServiceType, ServiceEndpoint]:
        """Initialize default service configurations"""
        base_configs = {
            ServiceType.FRONTEND: ServiceEndpoint(port=8080),
            ServiceType.INTELLIGENT_CORE: ServiceEndpoint(port=8001),
            ServiceType.BROKER_GATEWAY: ServiceEndpoint(port=8002),
            ServiceType.DATA_PROCESSING: ServiceEndpoint(port=8017),
            ServiceType.EVENT_BUS: ServiceEndpoint(port=8014),
            ServiceType.MONITORING: ServiceEndpoint(port=8015),
            ServiceType.DIAGNOSTIC: ServiceEndpoint(port=8016),
            ServiceType.PREDICTION_TRACKING: ServiceEndpoint(port=8018),
            ServiceType.ML_ANALYTICS: ServiceEndpoint(port=8021),
            ServiceType.CSV_SERVICE: ServiceEndpoint(port=8019),
            ServiceType.VERGLEICHSANALYSE: ServiceEndpoint(port=8020),
            ServiceType.HEALTH_MONITOR: ServiceEndpoint(port=8090),
        }
        
        # Environment-specific overrides
        if self.environment == Environment.LXC_CONTAINER:
            # LXC Container uses specific IP
            for config in base_configs.values():
                config.host = "10.1.1.174"
        elif self.environment == Environment.DEVELOPMENT:
            # Development might use different ports
            pass
            
        return base_configs
    
    def _initialize_database_config(self) -> DatabaseConfig:
        """Initialize database configuration"""
        config = DatabaseConfig()
        
        if self.environment == Environment.LXC_CONTAINER:
            config.host = "10.1.1.174"
        elif self.environment == Environment.TESTING:
            config.database = "aktienanalyse_test"
            config.port = 5433
            
        return config
    
    def _initialize_redis_config(self) -> RedisConfig:
        """Initialize Redis configuration"""
        config = RedisConfig()
        
        if self.environment == Environment.LXC_CONTAINER:
            config.host = "10.1.1.174"
        elif self.environment == Environment.TESTING:
            config.database = 1
            
        return config
    
    def _load_environment_config(self) -> None:
        """Load configuration from environment variables and .env file"""
        try:
            if self.config_file.exists():
                # Load from .env file
                with open(self.config_file, 'r') as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.strip().split('=', 1)
                            os.environ[key] = value
            
            # Override with environment variables
            for service_type, config in self._service_configs.items():
                env_prefix = f"{service_type.value.upper()}_"
                
                if host := os.getenv(f"{env_prefix}HOST"):
                    config.host = host
                if port := os.getenv(f"{env_prefix}PORT"):
                    config.port = int(port)
                if protocol := os.getenv(f"{env_prefix}PROTOCOL"):
                    config.protocol = protocol
                    
        except Exception as e:
            logger.warning(f"Failed to load environment config: {e}")
    
    @property
    def service_configs(self) -> Dict[ServiceType, ServiceEndpoint]:
        """Get all service configurations"""
        return self._service_configs.copy()
    
    @property
    def database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        return self._database_config
    
    @property
    def redis_config(self) -> RedisConfig:
        """Get Redis configuration"""
        return self._redis_config

class ServiceDiscovery(IServiceDiscovery):
    """
    Service Discovery Implementation - Dependency Inversion Principle
    Provides service endpoint resolution with fallback strategies
    """
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config_manager = config_manager
        self._health_cache: Dict[ServiceType, bool] = {}
        
    def get_service_endpoint(self, service_type: ServiceType) -> ServiceEndpoint:
        """Get service endpoint configuration"""
        if service_type not in self.config_manager.service_configs:
            raise ValueError(f"Unknown service type: {service_type}")
        
        return self.config_manager.service_configs[service_type]
    
    def get_service_url(self, service_type: ServiceType) -> str:
        """Get full service URL"""
        endpoint = self.get_service_endpoint(service_type)
        return endpoint.base_url
    
    def get_health_url(self, service_type: ServiceType) -> str:
        """Get health check URL for service"""
        endpoint = self.get_service_endpoint(service_type)
        return endpoint.health_url
    
    def is_service_available(self, service_type: ServiceType) -> bool:
        """Check if service is available (cached result)"""
        # Return cached result if available
        if service_type in self._health_cache:
            return self._health_cache[service_type]
        
        # For now, assume services are available
        # TODO: Implement actual health checks
        self._health_cache[service_type] = True
        return True
    
    def invalidate_health_cache(self, service_type: Optional[ServiceType] = None) -> None:
        """Invalidate health cache for service or all services"""
        if service_type:
            self._health_cache.pop(service_type, None)
        else:
            self._health_cache.clear()

# Global Configuration Instance (Singleton Pattern for Easy Access)
_config_manager: Optional[ConfigurationManager] = None
_service_discovery: Optional[ServiceDiscovery] = None

def get_config_manager(environment: Optional[Environment] = None) -> ConfigurationManager:
    """Get global configuration manager instance"""
    global _config_manager
    
    if _config_manager is None:
        env = environment or Environment.PRODUCTION
        # Detect LXC environment
        if os.path.exists("/opt/aktienanalyse-ökosystem"):
            env = Environment.LXC_CONTAINER
        _config_manager = ConfigurationManager(env)
    
    return _config_manager

def get_service_discovery() -> ServiceDiscovery:
    """Get global service discovery instance"""
    global _service_discovery
    
    if _service_discovery is None:
        config_manager = get_config_manager()
        _service_discovery = ServiceDiscovery(config_manager)
    
    return _service_discovery

# Convenience Functions for Easy Migration
def get_service_url(service_type: ServiceType) -> str:
    """Convenience function to get service URL - replaces hardcoded URLs"""
    return get_service_discovery().get_service_url(service_type)

def get_database_url() -> str:
    """Get database connection string"""
    return get_config_manager().database_config.connection_string

def get_redis_url() -> str:
    """Get Redis connection string"""
    return get_config_manager().redis_config.connection_string

# Migration Helper Functions
class LegacyUrlMapper:
    """Helper class for migrating from hardcoded URLs"""
    
    URL_MAPPING = {
        "http://localhost:8017": ServiceType.DATA_PROCESSING,
        "http://localhost:8019": ServiceType.CSV_SERVICE,
        "http://localhost:8018": ServiceType.PREDICTION_TRACKING,
        "http://localhost:8021": ServiceType.ML_ANALYTICS,
        "http://localhost:8011": ServiceType.INTELLIGENT_CORE,
        "http://localhost:8001": ServiceType.INTELLIGENT_CORE,
        "http://localhost:8012": ServiceType.BROKER_GATEWAY,
        "http://localhost:8002": ServiceType.BROKER_GATEWAY,
        "http://localhost:8014": ServiceType.EVENT_BUS,
        "http://localhost:8015": ServiceType.MONITORING,
        "http://localhost:8013": ServiceType.DIAGNOSTIC,
        "http://localhost:8016": ServiceType.DIAGNOSTIC,
        "http://localhost:8020": ServiceType.VERGLEICHSANALYSE,
        "http://localhost:8090": ServiceType.HEALTH_MONITOR,
        "http://localhost:8080": ServiceType.FRONTEND,
    }
    
    @classmethod
    def migrate_url(cls, old_url: str) -> str:
        """Migrate old hardcoded URL to new service discovery"""
        if old_url in cls.URL_MAPPING:
            service_type = cls.URL_MAPPING[old_url]
            return get_service_url(service_type)
        return old_url

if __name__ == "__main__":
    # Test the configuration system
    config = get_config_manager()
    discovery = get_service_discovery()
    
    print("=== Configuration Manager Test ===")
    print(f"Environment: {config.environment}")
    print(f"Project Root: {config.project_root}")
    
    print("\n=== Service Discovery Test ===")
    for service_type in ServiceType:
        try:
            url = discovery.get_service_url(service_type)
            health_url = discovery.get_health_url(service_type)
            print(f"{service_type.value}: {url} (health: {health_url})")
        except ValueError as e:
            print(f"{service_type.value}: {e}")
    
    print(f"\n=== Database Config ===")
    print(f"Database URL: {get_database_url()}")
    
    print(f"\n=== Redis Config ===")
    print(f"Redis URL: {get_redis_url()}")
    
    print("\n=== Legacy URL Migration Test ===")
    test_urls = [
        "http://localhost:8017",
        "http://localhost:8001",
        "http://localhost:8014"
    ]
    
    for old_url in test_urls:
        new_url = LegacyUrlMapper.migrate_url(old_url)
        print(f"{old_url} -> {new_url}")