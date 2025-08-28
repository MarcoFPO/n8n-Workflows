"""
Event-Bus Service Dependency Injection Container
Clean Architecture Implementation - Centralized Dependencies

CLEAN ARCHITECTURE LAYERS:
- Configuration Management
- Domain Service Registration  
- Application Use Case Wiring
- Infrastructure Service Setup
- Presentation Controller Dependencies

Code-Qualität: HÖCHSTE PRIORITÄT
Autor: Claude Code - DI Container Specialist
Datum: 24. August 2025  
Version: 7.0.0
"""

import logging
import os
from typing import Optional, Dict, Any

import aioredis
import asyncpg

# Shared Imports - Centralized Database Management
from shared.database_connection_manager_v1_0_0_20250825 import (
    get_database_manager, 
    DatabaseConfiguration as CentralDatabaseConfiguration
)

# Application Layer Imports
from application.use_cases.event_publishing import EventPublishingUseCase
from application.use_cases.event_subscription import EventSubscriptionUseCase  
from application.use_cases.event_store_query import EventStoreQueryUseCase
from application.interfaces.event_publisher import IEventPublisher
from application.interfaces.event_subscriber import IEventSubscriber
from application.interfaces.event_repository import IEventRepository

# Infrastructure Layer Imports
from infrastructure.events.redis_event_publisher import RedisEventPublisher
from infrastructure.events.redis_event_subscriber import RedisEventSubscriber
from infrastructure.persistence.postgresql_event_repository import PostgreSQLEventRepository
from infrastructure.services.event_service_registry import EventServiceRegistry

# Presentation Layer Imports  
from presentation.controllers.event_controller import EventController
from presentation.controllers.event_store_controller import EventStoreController

# Domain Layer Imports
from domain.services.event_validator import EventValidatorService
from domain.services.event_routing_service import EventRoutingService


class EventBusConfiguration:
    """
    Configuration Management für Event-Bus Service
    
    CLEAN ARCHITECTURE: Infrastructure Configuration
    """
    
    def __init__(self):
        self.service_name = "event-bus-service"
        self.service_host = os.getenv("EVENT_BUS_HOST", "0.0.0.0")
        self.service_port = int(os.getenv("EVENT_BUS_PORT", "8014"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Redis Configuration für Event Publishing/Subscription
        # Redis Configuration für Event Publishing/Subscription
        # Production deployment auf 10.1.1.174
        self.redis_host = os.getenv("REDIS_HOST", "10.1.1.174") 
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_db = int(os.getenv("REDIS_EVENT_DB", "0"))
        self.redis_password = os.getenv("REDIS_PASSWORD")  # Aus Environment laden
        
        # PostgreSQL Configuration für Event Store  
        # Production deployment auf 10.1.1.174
        self.postgres_host = os.getenv("POSTGRES_HOST", "10.1.1.174")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.postgres_db = os.getenv("POSTGRES_DB", "aktienanalyse_events")
        self.postgres_user = os.getenv("POSTGRES_USER", "aktienanalyse")
        
        # SECURITY FIX: Entfernung hardcodiertes Passwort
        self.postgres_password = os.getenv("POSTGRES_PASSWORD")
        if not self.postgres_password:
            raise ValueError("POSTGRES_PASSWORD environment variable must be set for security!")
        
        # Event-Bus Specific Configuration
        self.event_channel_prefix = os.getenv("EVENT_CHANNEL_PREFIX", "events")
        self.event_ttl_seconds = int(os.getenv("EVENT_TTL_SECONDS", "86400"))  # 24 hours
        self.max_event_size = int(os.getenv("MAX_EVENT_SIZE", "1048576"))  # 1MB
        
    def get_redis_url(self) -> str:
        """Build Redis URL from configuration"""
        auth_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    def get_postgres_url(self) -> str:
        """Build PostgreSQL URL from configuration"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "service_name": self.service_name,
            "service_host": self.service_host,
            "service_port": self.service_port,
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
            "postgres_host": self.postgres_host,
            "postgres_port": self.postgres_port,
            "event_channel_prefix": self.event_channel_prefix
        }


class EventBusContainer:
    """
    Dependency Injection Container für Event-Bus Service
    
    CLEAN ARCHITECTURE: Centralized Dependency Management
    Implementiert Dependency Inversion Principle
    """
    
    def __init__(self, config: EventBusConfiguration):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        
        # Infrastructure Layer Dependencies
        self.redis_client: Optional[aioredis.Redis] = None
        # MIGRATION: Replaced postgres_pool mit centralized database manager
        self.database_manager = get_database_manager()
        self.event_publisher: Optional[IEventPublisher] = None
        self.event_subscriber: Optional[IEventSubscriber] = None
        self.event_repository: Optional[IEventRepository] = None
        self.event_service_registry: Optional[EventServiceRegistry] = None
        
        # Domain Layer Dependencies
        self.event_validator: Optional[EventValidatorService] = None
        self.event_routing_service: Optional[EventRoutingService] = None
        
        # Application Layer Dependencies  
        self.event_publishing_use_case: Optional[EventPublishingUseCase] = None
        self.event_subscription_use_case: Optional[EventSubscriptionUseCase] = None
        self.event_store_query_use_case: Optional[EventStoreQueryUseCase] = None
        
        # Presentation Layer Dependencies
        self.event_controller: Optional[EventController] = None
        self.event_store_controller: Optional[EventStoreController] = None
    
    async def initialize(self) -> None:
        """
        Initialize all dependencies
        
        CLEAN ARCHITECTURE INITIALIZATION ORDER:
        1. Infrastructure Layer (External Dependencies)
        2. Domain Layer (Business Logic)  
        3. Application Layer (Use Cases)
        4. Presentation Layer (Controllers)
        """
        try:
            self.logger.info("🏗️ Initializing Event-Bus Container - Clean Architecture")
            
            # 1. INFRASTRUCTURE LAYER INITIALIZATION
            await self._initialize_infrastructure()
            
            # 2. DOMAIN LAYER INITIALIZATION  
            self._initialize_domain_services()
            
            # 3. APPLICATION LAYER INITIALIZATION
            self._initialize_use_cases()
            
            # 4. PRESENTATION LAYER INITIALIZATION
            self._initialize_controllers()
            
            self._initialized = True
            self.logger.info("✅ Event-Bus Container initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Container initialization failed: {e}")
            raise
    
    async def _initialize_infrastructure(self) -> None:
        """Initialize Infrastructure Layer Dependencies"""
        self.logger.info("🔧 Initializing Infrastructure Layer")
        
        # Redis Client für Event Publishing/Subscription
        try:
            self.redis_client = aioredis.from_url(
                self.config.get_redis_url(),
                encoding="utf-8",
                decode_responses=True
            )
            # Test Redis connection
            await self.redis_client.ping()
            self.logger.info("✅ Redis client connected")
        except Exception as e:
            self.logger.error(f"❌ Redis connection failed: {e}")
            raise
        
        # MIGRATION: Use Centralized Database Manager
        try:
            # Initialize centralized database manager
            central_db_config = CentralDatabaseConfiguration()
            self.database_manager.config = central_db_config
            await self.database_manager.initialize()
            self.logger.info("✅ Centralized Database Manager initialized")
        except Exception as e:
            self.logger.error(f"❌ Centralized Database Manager initialization failed: {e}")
            raise
        
        # Event Publisher Implementation
        self.event_publisher = RedisEventPublisher(
            redis_client=self.redis_client,
            channel_prefix=self.config.event_channel_prefix,
            event_ttl=self.config.event_ttl_seconds
        )
        await self.event_publisher.initialize()
        
        # Event Subscriber Implementation
        self.event_subscriber = RedisEventSubscriber(
            redis_client=self.redis_client,
            channel_prefix=self.config.event_channel_prefix
        )
        await self.event_subscriber.initialize()
        
        # Event Repository Implementation - MIGRATION to Centralized Database Manager
        self.event_repository = PostgreSQLEventRepository(
            database_manager=self.database_manager,
            table_name="events"
        )
        await self.event_repository.initialize()
        
        # Event Service Registry
        self.event_service_registry = EventServiceRegistry(
            redis_client=self.redis_client
        )
        await self.event_service_registry.initialize()
        
        self.logger.info("✅ Infrastructure Layer initialized")
    
    def _initialize_domain_services(self) -> None:
        """Initialize Domain Layer Services"""
        self.logger.info("🧠 Initializing Domain Layer")
        
        # Event Validator Domain Service
        self.event_validator = EventValidatorService(
            max_event_size=self.config.max_event_size
        )
        
        # Event Routing Domain Service
        self.event_routing_service = EventRoutingService(
            service_registry=self.event_service_registry
        )
        
        self.logger.info("✅ Domain Layer initialized")
    
    def _initialize_use_cases(self) -> None:
        """Initialize Application Layer Use Cases"""
        self.logger.info("⚙️ Initializing Application Layer")
        
        # Event Publishing Use Case
        self.event_publishing_use_case = EventPublishingUseCase(
            event_publisher=self.event_publisher,
            event_repository=self.event_repository,
            event_validator=self.event_validator,
            event_routing_service=self.event_routing_service
        )
        
        # Event Subscription Use Case
        self.event_subscription_use_case = EventSubscriptionUseCase(
            event_subscriber=self.event_subscriber,
            service_registry=self.event_service_registry
        )
        
        # Event Store Query Use Case
        self.event_store_query_use_case = EventStoreQueryUseCase(
            event_repository=self.event_repository
        )
        
        self.logger.info("✅ Application Layer initialized")
    
    def _initialize_controllers(self) -> None:
        """Initialize Presentation Layer Controllers"""
        self.logger.info("🎮 Initializing Presentation Layer")
        
        # Event Controller
        self.event_controller = EventController(
            event_publishing_use_case=self.event_publishing_use_case,
            event_subscription_use_case=self.event_subscription_use_case,
            event_publisher=self.event_publisher,
            event_subscriber=self.event_subscriber,
            service_registry=self.event_service_registry
        )
        
        # Event Store Controller
        self.event_store_controller = EventStoreController(
            event_store_query_use_case=self.event_store_query_use_case,
            event_repository=self.event_repository
        )
        
        self.logger.info("✅ Presentation Layer initialized")
    
    def is_initialized(self) -> bool:
        """Check if container is fully initialized"""
        return self._initialized
    
    async def cleanup(self) -> None:
        """Cleanup all resources"""
        self.logger.info("🧹 Cleaning up Event-Bus Container")
        
        try:
            # Cleanup Infrastructure Layer
            if self.event_publisher:
                await self.event_publisher.cleanup()
            
            if self.event_subscriber:
                await self.event_subscriber.cleanup()
                
            if self.redis_client:
                await self.redis_client.aclose()
            
            # MIGRATION: Close centralized database manager
            if self.database_manager:
                await self.database_manager.close()
            
            self.logger.info("✅ Container cleanup completed")
            
        except Exception as e:
            self.logger.error(f"❌ Container cleanup failed: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        return {
            "container_initialized": self._initialized,
            "redis_connected": self.redis_client is not None,
            "database_manager_ready": self.database_manager is not None and self.database_manager.is_initialized(),
            "event_publisher_ready": self.event_publisher is not None,
            "event_subscriber_ready": self.event_subscriber is not None,
            "event_repository_ready": self.event_repository is not None,
            "controllers_initialized": (
                self.event_controller is not None and 
                self.event_store_controller is not None
            )
        }