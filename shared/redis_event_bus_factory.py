"""
Redis Event Bus Factory - Centralized Event Bus Management
Provides singleton pattern and service-specific configuration
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

import asyncio
import os
from typing import Dict, Optional
from shared.redis_event_bus import RedisEventBus, RedisEventBusConfig

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    class MockLogger:
        def info(self, msg, **kwargs): print(f"ℹ️ {msg} {kwargs}")
        def debug(self, msg, **kwargs): print(f"🐛 {msg} {kwargs}")
        def error(self, msg, **kwargs): print(f"❌ {msg} {kwargs}")
        def warning(self, msg, **kwargs): print(f"⚠️ {msg} {kwargs}")
    logger = MockLogger()


class RedisEventBusFactory:
    """Factory for creating and managing Redis Event Bus instances"""
    
    _instances: Dict[str, RedisEventBus] = {}
    _config: Optional[RedisEventBusConfig] = None
    _initialized: bool = False
    
    @classmethod
    def get_default_config(cls) -> RedisEventBusConfig:
        """Get default configuration from environment variables"""
        config = RedisEventBusConfig()
        
        # Redis Configuration from environment
        config.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        config.connection_pool_size = int(os.getenv('REDIS_POOL_SIZE', '10'))
        config.connection_timeout = int(os.getenv('REDIS_TIMEOUT', '5'))
        
        # Event Processing Configuration  
        config.max_retries = int(os.getenv('EVENT_MAX_RETRIES', '3'))
        config.retry_delay_base = float(os.getenv('EVENT_RETRY_DELAY_BASE', '1.0'))
        config.batch_size = int(os.getenv('EVENT_BATCH_SIZE', '100'))
        config.processing_timeout = int(os.getenv('EVENT_PROCESSING_TIMEOUT', '30'))
        
        # Performance Configuration
        config.enable_compression = os.getenv('EVENT_ENABLE_COMPRESSION', 'true').lower() == 'true'
        config.max_event_size = int(os.getenv('EVENT_MAX_SIZE', str(1024 * 1024)))
        config.connection_pool_max = int(os.getenv('REDIS_POOL_MAX', '20'))
        config.subscriber_buffer_size = int(os.getenv('SUBSCRIBER_BUFFER_SIZE', '1000'))
        
        # Persistence Configuration
        config.enable_persistence = os.getenv('EVENT_ENABLE_PERSISTENCE', 'true').lower() == 'true'
        config.persistence_ttl = int(os.getenv('EVENT_PERSISTENCE_TTL', str(24 * 3600)))
        config.dead_letter_ttl = int(os.getenv('EVENT_DEAD_LETTER_TTL', str(7 * 24 * 3600)))
        
        # Monitoring Configuration
        config.enable_metrics = os.getenv('EVENT_ENABLE_METRICS', 'true').lower() == 'true'
        config.metrics_interval = int(os.getenv('EVENT_METRICS_INTERVAL', '60'))
        config.health_check_interval = int(os.getenv('EVENT_HEALTH_CHECK_INTERVAL', '30'))
        
        # Circuit Breaker Configuration
        config.circuit_breaker_enabled = os.getenv('EVENT_CIRCUIT_BREAKER_ENABLED', 'true').lower() == 'true'
        config.circuit_breaker_failure_threshold = int(os.getenv('EVENT_CIRCUIT_BREAKER_THRESHOLD', '10'))
        config.circuit_breaker_timeout = int(os.getenv('EVENT_CIRCUIT_BREAKER_TIMEOUT', '60'))
        
        return config
    
    @classmethod
    def set_global_config(cls, config: RedisEventBusConfig):
        """Set global configuration for all event bus instances"""
        cls._config = config
        logger.info("Global Redis Event Bus configuration set")
    
    @classmethod
    async def create_event_bus(cls, service_name: str, config: Optional[RedisEventBusConfig] = None) -> RedisEventBus:
        """Create or get existing event bus for service"""
        
        # Use provided config, global config, or default config
        if config is None:
            config = cls._config or cls.get_default_config()
        
        # Check if instance already exists
        if service_name in cls._instances:
            logger.debug("Returning existing event bus instance", service=service_name)
            return cls._instances[service_name]
        
        # Create new instance
        event_bus = RedisEventBus(config=config, service_name=service_name)
        
        # Initialize the event bus
        if await event_bus.initialize():
            cls._instances[service_name] = event_bus
            logger.info("Event bus instance created and initialized", 
                       service=service_name,
                       redis_url=config.redis_url)
            return event_bus
        else:
            logger.error("Failed to initialize event bus", service=service_name)
            raise RuntimeError(f"Failed to initialize event bus for service: {service_name}")
    
    @classmethod
    async def get_event_bus(cls, service_name: str) -> Optional[RedisEventBus]:
        """Get existing event bus instance"""
        return cls._instances.get(service_name)
    
    @classmethod
    async def shutdown_event_bus(cls, service_name: str):
        """Shutdown specific event bus instance"""
        if service_name in cls._instances:
            await cls._instances[service_name].shutdown()
            del cls._instances[service_name]
            logger.info("Event bus instance shut down", service=service_name)
    
    @classmethod
    async def shutdown_all(cls):
        """Shutdown all event bus instances"""
        shutdown_tasks = []
        for service_name, event_bus in cls._instances.items():
            shutdown_tasks.append(event_bus.shutdown())
        
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        cls._instances.clear()
        logger.info("All event bus instances shut down")
    
    @classmethod
    def list_instances(cls) -> Dict[str, Dict[str, any]]:
        """List all active event bus instances with their status"""
        instances_info = {}
        
        for service_name, event_bus in cls._instances.items():
            instances_info[service_name] = {
                'service_name': service_name,
                'running': event_bus.running,
                'metrics': event_bus.get_metrics(),
                'active_subscriptions': len(event_bus.active_subscriptions),
                'redis_url': event_bus.config.redis_url
            }
        
        return instances_info
    
    @classmethod
    async def health_check_all(cls) -> Dict[str, Dict[str, any]]:
        """Perform health check on all event bus instances"""
        health_results = {}
        
        for service_name, event_bus in cls._instances.items():
            try:
                # Try to ping Redis
                await event_bus.redis_client.ping()
                metrics = event_bus.get_metrics()
                
                health_results[service_name] = {
                    'status': 'healthy',
                    'running': event_bus.running,
                    'last_heartbeat': metrics.get('last_heartbeat'),
                    'uptime_seconds': metrics.get('uptime_seconds', 0),
                    'events_processed': metrics.get('events_processed', 0),
                    'circuit_breaker_state': metrics.get('circuit_breaker_state', {}).get('state', 'unknown')
                }
                
            except Exception as e:
                health_results[service_name] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'running': event_bus.running if event_bus else False
                }
        
        return health_results


class ServiceEventBusRegistry:
    """Registry for service-specific event bus configurations and instances"""
    
    # Service-specific configurations
    SERVICE_CONFIGS = {
        'account-service': {
            'max_retries': 5,           # Financial operations need more retries
            'processing_timeout': 60,   # Longer timeout for complex calculations
            'enable_persistence': True, # Account data must be persistent
            'priority_channels': True   # Support priority processing
        },
        
        'order-service': {
            'max_retries': 3,           # Standard retry for orders
            'processing_timeout': 30,   # Fast order processing
            'enable_persistence': True, # Order history important
            'priority_channels': True   # High priority for urgent orders
        },
        
        'frontend-service': {
            'max_retries': 2,           # UI updates don't need many retries
            'processing_timeout': 10,   # Fast UI response
            'enable_persistence': False,# UI events are transient
            'priority_channels': False  # Standard priority for UI
        },
        
        'data-analysis-service': {
            'max_retries': 3,           # Standard retry for analysis
            'processing_timeout': 120,  # Long timeout for complex analysis
            'enable_persistence': True, # Analysis results should be cached
            'priority_channels': True   # Support priority analysis
        },
        
        'intelligent-core-service': {
            'max_retries': 5,           # ML operations need more retries
            'processing_timeout': 180,  # Very long timeout for ML inference
            'enable_persistence': True, # ML results are valuable
            'priority_channels': True   # Priority for critical decisions
        },
        
        'market-data-service': {
            'max_retries': 10,          # Market data is critical
            'processing_timeout': 60,   # Moderate timeout
            'enable_persistence': True, # Market data history important
            'priority_channels': True   # Real-time data has priority
        }
    }
    
    @classmethod
    def get_service_config(cls, service_name: str) -> RedisEventBusConfig:
        """Get service-specific configuration"""
        base_config = RedisEventBusFactory.get_default_config()
        
        # Apply service-specific overrides
        service_overrides = cls.SERVICE_CONFIGS.get(service_name, {})
        
        for key, value in service_overrides.items():
            if hasattr(base_config, key):
                setattr(base_config, key, value)
        
        return base_config
    
    @classmethod  
    async def create_service_event_bus(cls, service_name: str) -> RedisEventBus:
        """Create event bus with service-specific configuration"""
        config = cls.get_service_config(service_name)
        return await RedisEventBusFactory.create_event_bus(service_name, config)
    
    @classmethod
    def register_service_config(cls, service_name: str, config_overrides: Dict[str, any]):
        """Register custom configuration for a service"""
        cls.SERVICE_CONFIGS[service_name] = config_overrides
        logger.info("Service configuration registered", 
                   service=service_name, 
                   overrides=config_overrides)


# Global event bus factory instance
event_bus_factory = RedisEventBusFactory()

# Convenience functions for common operations
async def get_event_bus(service_name: str) -> RedisEventBus:
    """Get or create event bus for service"""
    return await ServiceEventBusRegistry.create_service_event_bus(service_name)

async def publish_event(service_name: str, event_type: str, data: dict, **kwargs) -> bool:
    """Quick publish event using service event bus"""
    event_bus = await get_event_bus(service_name)
    event = await event_bus.create_event(event_type, data, **kwargs)
    return await event_bus.publish(event)

async def subscribe_to_event(service_name: str, event_type: str, handler) -> bool:
    """Quick subscribe to event using service event bus"""
    event_bus = await get_event_bus(service_name)
    return await event_bus.subscribe(event_type, handler)

# Environment-based initialization
async def initialize_event_bus_system():
    """Initialize the entire event bus system"""
    try:
        # Set global configuration based on environment
        global_config = RedisEventBusFactory.get_default_config()
        RedisEventBusFactory.set_global_config(global_config)
        
        logger.info("Event bus system initialized",
                   redis_url=global_config.redis_url,
                   persistence_enabled=global_config.enable_persistence,
                   metrics_enabled=global_config.enable_metrics)
        
        return True
        
    except Exception as e:
        logger.error("Failed to initialize event bus system", error=str(e))
        return False

async def shutdown_event_bus_system():
    """Shutdown the entire event bus system"""
    await RedisEventBusFactory.shutdown_all()
    logger.info("Event bus system shutdown completed")