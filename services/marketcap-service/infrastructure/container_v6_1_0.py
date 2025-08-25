#!/usr/bin/env python3
"""
MarketCap Service v6.1.0 - Dependency Injection Container
Clean Architecture v6.1.0 - Database Manager Integration

Service Lifecycle Management und Dependency Injection mit PostgreSQL
- Database Manager für zentrale Verbindungsverwaltung
- Clean Architecture Compliance
- Comprehensive Health Management

Autor: Claude Code
Datum: 25. August 2025
Version: 6.1.0
"""

import asyncio
import structlog
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from functools import lru_cache
import sys

# Database Manager Import - Direct Path Import
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from database_connection_manager_v1_0_0_20250825 import (
    DatabaseConnectionManager, 
    DatabaseConfiguration
)

# Domain Interfaces
from ..domain.repositories.market_data_repository import (
    IMarketDataRepository,
    IMarketDataCache,
    IMarketDataProvider
)
from ..application.interfaces.event_publisher import IEventPublisher
from ..application.use_cases.get_market_data_use_case import (
    GetMarketDataUseCase,
    GetAllMarketDataUseCase
)

# Infrastructure - PostgreSQL
from .persistence.postgresql_market_data_repository import PostgreSQLMarketDataRepository

# Infrastructure - Other Components
from .external_services.mock_data_provider import MockMarketDataProvider
from .cache.memory_cache import MemoryMarketDataCache
from .events.mock_event_publisher import MockEventPublisher

# Presentation
from ..presentation.controllers.marketcap_controller import MarketCapController

logger = structlog.get_logger(__name__)


class MarketCapServiceContainer:
    """Dependency Injection Container für MarketCap Service v6.1.0"""
    
    def __init__(self):
        self.is_configured = False
        self.is_initialized = False
        self.initialization_error = None
        self._initialized_at = None
        
        # Configuration
        self.config = {
            'database_manager': {
                'auto_initialize_schema': True,
                'enable_connection_pooling': True,
                'pool_health_check_interval': 300  # 5 minutes
            },
            'data_provider': {
                'use_mock': True,
                'latency_ms': 100,
                'availability': 0.95,
                'timeout_seconds': 30
            },
            'cache': {
                'enabled': True,
                'max_entries': 1000,
                'ttl_minutes': 15
            },
            'event_publisher': {
                'enabled': True,
                'max_events': 1000
            }
        }
        
        # Database Manager
        self._db_manager: Optional[DatabaseConnectionManager] = None
        
        # Components
        self.market_data_repository: Optional[IMarketDataRepository] = None
        self.market_data_cache: Optional[IMarketDataCache] = None
        self.data_provider: Optional[IMarketDataProvider] = None
        self.event_publisher: Optional[IEventPublisher] = None
        
        # Use Cases
        self.get_market_data_use_case: Optional[GetMarketDataUseCase] = None
        self.get_all_market_data_use_case: Optional[GetAllMarketDataUseCase] = None
        
        # Controllers
        self.market_cap_controller: Optional[MarketCapController] = None

    async def configure_and_initialize(self, config: Dict[str, Any] = None) -> bool:
        """Configure and initialize container"""
        try:
            if config:
                self.config.update(config)
            self.is_configured = True
            
            return await self.initialize()
            
        except Exception as e:
            logger.error("Failed to configure and initialize container", error=str(e))
            self.initialization_error = str(e)
            return False

    async def initialize(self) -> bool:
        """Initialize all dependencies mit Database Manager"""
        try:
            logger.info("Initializing MarketCap Service Container v6.1.0...")
            
            # Initialize Database Manager
            db_config = DatabaseConfiguration()
            self._db_manager = DatabaseConnectionManager(db_config)
            await self._db_manager.initialize()
            
            # Initialize schema
            if self.config['database_manager']['auto_initialize_schema']:
                success = await self._initialize_schema()
                if not success:
                    logger.error("Failed to initialize database schema")
                    return False
            
            # Initialize components
            await self._initialize_repositories()
            await self._initialize_external_services()
            await self._initialize_use_cases()
            await self._initialize_controllers()
            
            self.is_initialized = True
            self._initialized_at = datetime.now(timezone.utc)
            
            logger.info("MarketCap Service Container v6.1.0 initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Container initialization failed", error=str(e))
            self.initialization_error = str(e)
            return False

    async def _initialize_schema(self) -> bool:
        """Initialize market data schema"""
        try:
            market_data_repo = PostgreSQLMarketDataRepository(self._db_manager)
            if not await market_data_repo.initialize_schema():
                return False
                
            logger.info("Market data schema initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Schema initialization failed", error=str(e))
            return False

    async def _initialize_repositories(self):
        """Initialize repository mit PostgreSQL"""
        try:
            # Market Data Repository
            self.market_data_repository = PostgreSQLMarketDataRepository(self._db_manager)
            
            logger.info("PostgreSQL repository initialized")
            
        except Exception as e:
            logger.error("Repository initialization failed", error=str(e))
            raise

    async def _initialize_external_services(self):
        """Initialize external services"""
        try:
            # Data Provider
            if self.config['data_provider']['use_mock']:
                self.data_provider = MockMarketDataProvider(
                    latency_ms=self.config['data_provider']['latency_ms'],
                    availability=self.config['data_provider']['availability']
                )
            
            # Cache
            if self.config['cache']['enabled']:
                self.market_data_cache = MemoryMarketDataCache()
            
            # Event Publisher
            if self.config['event_publisher']['enabled']:
                self.event_publisher = MockEventPublisher()
            
            logger.info("External services initialized")
            
        except Exception as e:
            logger.error("External services initialization failed", error=str(e))
            raise

    async def _initialize_use_cases(self):
        """Initialize use cases mit dependencies"""
        try:
            # Market Data Use Case
            self.get_market_data_use_case = GetMarketDataUseCase(
                repository=self.market_data_repository,
                cache=self.market_data_cache,
                provider=self.data_provider,
                event_publisher=self.event_publisher
            )
            
            # All Market Data Use Case
            self.get_all_market_data_use_case = GetAllMarketDataUseCase(
                repository=self.market_data_repository
            )
            
            logger.info("Use cases initialized")
            
        except Exception as e:
            logger.error("Use cases initialization failed", error=str(e))
            raise

    async def _initialize_controllers(self):
        """Initialize controllers mit use cases"""
        try:
            # Market Cap Controller
            self.market_cap_controller = MarketCapController(
                get_market_data_use_case=self.get_market_data_use_case,
                get_all_market_data_use_case=self.get_all_market_data_use_case
            )
            
            logger.info("Controllers initialized")
            
        except Exception as e:
            logger.error("Controllers initialization failed", error=str(e))
            raise

    def get_database_manager(self) -> DatabaseConnectionManager:
        """Get database manager"""
        if self._db_manager is None:
            raise RuntimeError("Database Manager not initialized")
        return self._db_manager

    # Component Getters
    def get_market_data_repository(self) -> IMarketDataRepository:
        if not self.market_data_repository:
            raise RuntimeError("Market data repository not initialized")
        return self.market_data_repository

    def get_market_data_cache(self) -> Optional[IMarketDataCache]:
        return self.market_data_cache

    def get_data_provider(self) -> Optional[IMarketDataProvider]:
        return self.data_provider

    def get_event_publisher(self) -> Optional[IEventPublisher]:
        return self.event_publisher

    # Use Case Getters
    def get_market_data_use_case(self) -> GetMarketDataUseCase:
        if not self.get_market_data_use_case:
            raise RuntimeError("Market data use case not initialized")
        return self.get_market_data_use_case

    def get_all_market_data_use_case(self) -> GetAllMarketDataUseCase:
        if not self.get_all_market_data_use_case:
            raise RuntimeError("All market data use case not initialized")
        return self.get_all_market_data_use_case

    # Controller Getters
    def get_controller(self) -> MarketCapController:
        if not self.market_cap_controller:
            raise RuntimeError("Market cap controller not initialized")
        return self.market_cap_controller

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            health_data = {
                'container': {
                    'version': '6.1.0',
                    'database': 'PostgreSQL',
                    'configured': self.is_configured,
                    'initialized': self.is_initialized,
                    'initialized_at': self._initialized_at.isoformat() if self._initialized_at else None,
                    'initialization_error': self.initialization_error
                },
                'components': {}
            }
            
            # Database Manager Health
            if self._db_manager:
                try:
                    db_health = await self._db_manager.health_check()
                    health_data['components']['database_manager'] = {
                        'status': 'healthy' if db_health.get('healthy') else 'unhealthy',
                        'details': db_health
                    }
                except Exception as e:
                    health_data['components']['database_manager'] = {
                        'status': 'unhealthy',
                        'error': str(e)
                    }
            
            # Repository Health
            if self.market_data_repository:
                try:
                    repo_health = await self.market_data_repository.get_health_status()
                    health_data['components']['market_data_repository'] = {
                        'status': repo_health.get('status', 'unknown'),
                        'details': repo_health
                    }
                except Exception as e:
                    health_data['components']['market_data_repository'] = {
                        'status': 'unhealthy',
                        'error': str(e)
                    }
            
            # Cache Health
            if self.market_data_cache:
                health_data['components']['cache'] = {
                    'status': 'healthy',
                    'type': 'memory',
                    'enabled': True
                }
            else:
                health_data['components']['cache'] = {
                    'status': 'disabled',
                    'enabled': False
                }
            
            # Data Provider Health
            if self.data_provider:
                health_data['components']['data_provider'] = {
                    'status': 'healthy',
                    'type': 'mock',
                    'enabled': True
                }
            
            # Event Publisher Health
            if self.event_publisher:
                health_data['components']['event_publisher'] = {
                    'status': 'healthy',
                    'type': 'mock',
                    'enabled': True
                }
            
            # Use Cases Health
            use_cases = ['get_market_data_use_case', 'get_all_market_data_use_case']
            for use_case in use_cases:
                if getattr(self, use_case, None):
                    health_data['components'][use_case] = {
                        'status': 'healthy',
                        'initialized': True
                    }
                else:
                    health_data['components'][use_case] = {
                        'status': 'not_initialized'
                    }
            
            # Controller Health
            if self.market_cap_controller:
                health_data['components']['market_cap_controller'] = {
                    'status': 'healthy',
                    'initialized': True
                }
            
            return health_data
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                'status': 'unhealthy',
                'error': str(e),
                'container': {
                    'version': '6.1.0',
                    'database': 'PostgreSQL'
                }
            }

    async def shutdown(self) -> bool:
        """Graceful shutdown of container and resources"""
        try:
            logger.info("Shutting down MarketCap Service Container...")
            
            # Clear all services
            self.market_data_repository = None
            self.market_data_cache = None
            self.data_provider = None
            self.event_publisher = None
            
            self.get_market_data_use_case = None
            self.get_all_market_data_use_case = None
            self.market_cap_controller = None
            
            # Shutdown database manager
            if self._db_manager:
                await self._db_manager.close()
                self._db_manager = None
            
            self.is_initialized = False
            self._initialized_at = None
            
            logger.info("MarketCap Service Container shutdown completed")
            return True
            
        except Exception as e:
            logger.error("Error during container shutdown", error=str(e))
            return False

    async def reset_for_testing(self):
        """Reset container for testing"""
        await self.shutdown()
        self.__init__()


# Global container instance  
container = MarketCapServiceContainer()