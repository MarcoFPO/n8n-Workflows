#!/usr/bin/env python3
"""
MarketCap Service - Dependency Injection Container
Infrastructure Layer Container Implementation

CLEAN ARCHITECTURE - INFRASTRUCTURE LAYER:
- Dependency injection container
- Manages object creation and lifetime
- Wiring of all dependencies

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import logging
from typing import Optional
from functools import lru_cache

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
from ..presentation.controllers.marketcap_controller import MarketCapController

# Infrastructure implementations
from .persistence.memory_market_data_repository import MemoryMarketDataRepository
from .external_services.mock_data_provider import MockMarketDataProvider
from .cache.memory_cache import MemoryMarketDataCache
from .events.mock_event_publisher import MockEventPublisher


logger = logging.getLogger(__name__)


class DIContainer:
    """
    Dependency Injection Container
    
    INFRASTRUCTURE CONCERN: Manages dependencies and object creation
    SINGLETON PATTERN: Ensures single instance of container
    FACTORY PATTERN: Creates objects based on configuration
    """
    
    _instance: Optional['DIContainer'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'DIContainer':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._providers: dict = {}
        self._singletons: dict = {}
        self._config = {
            'use_mock_provider': True,
            'cache_enabled': True,
            'event_publishing_enabled': True,
            'provider_latency_ms': 100,
            'provider_availability': 0.95
        }
        self._initialized = True
        logger.info("DIContainer initialized with default configuration")
    
    def configure(self, config: dict) -> None:
        """
        Configure container with custom settings
        
        Args:
            config: Configuration dictionary
        """
        self._config.update(config)
        
        # Clear singletons to force recreation with new config
        self._singletons.clear()
        logger.info(f"DIContainer reconfigured with: {config}")
    
    @lru_cache(maxsize=None)
    def get_repository(self) -> IMarketDataRepository:
        """
        Get market data repository instance
        
        Returns:
            IMarketDataRepository implementation
        """
        if 'repository' not in self._singletons:
            repository = MemoryMarketDataRepository()
            self._singletons['repository'] = repository
            logger.debug("Created MemoryMarketDataRepository instance")
        
        return self._singletons['repository']
    
    @lru_cache(maxsize=None)
    def get_cache(self) -> Optional[IMarketDataCache]:
        """
        Get market data cache instance
        
        Returns:
            IMarketDataCache implementation or None if disabled
        """
        if not self._config.get('cache_enabled', True):
            return None
        
        if 'cache' not in self._singletons:
            cache = MemoryMarketDataCache()
            self._singletons['cache'] = cache
            logger.debug("Created MemoryMarketDataCache instance")
        
        return self._singletons['cache']
    
    @lru_cache(maxsize=None)
    def get_provider(self) -> Optional[IMarketDataProvider]:
        """
        Get market data provider instance
        
        Returns:
            IMarketDataProvider implementation or None
        """
        if not self._config.get('use_mock_provider', True):
            return None
        
        if 'provider' not in self._singletons:
            provider = MockMarketDataProvider(
                latency_ms=self._config.get('provider_latency_ms', 100),
                availability=self._config.get('provider_availability', 0.95)
            )
            self._singletons['provider'] = provider
            logger.debug("Created MockMarketDataProvider instance")
        
        return self._singletons['provider']
    
    @lru_cache(maxsize=None)
    def get_event_publisher(self) -> Optional[IEventPublisher]:
        """
        Get event publisher instance
        
        Returns:
            IEventPublisher implementation or None if disabled
        """
        if not self._config.get('event_publishing_enabled', True):
            return None
        
        if 'event_publisher' not in self._singletons:
            publisher = MockEventPublisher()
            self._singletons['event_publisher'] = publisher
            logger.debug("Created MockEventPublisher instance")
        
        return self._singletons['event_publisher']
    
    def get_market_data_use_case(self) -> GetMarketDataUseCase:
        """
        Get market data use case instance
        
        Returns:
            GetMarketDataUseCase with injected dependencies
        """
        return GetMarketDataUseCase(
            repository=self.get_repository(),
            cache=self.get_cache(),
            provider=self.get_provider(),
            event_publisher=self.get_event_publisher()
        )
    
    def get_all_market_data_use_case(self) -> GetAllMarketDataUseCase:
        """
        Get all market data use case instance
        
        Returns:
            GetAllMarketDataUseCase with injected dependencies
        """
        return GetAllMarketDataUseCase(
            repository=self.get_repository()
        )
    
    def get_controller(self) -> MarketCapController:
        """
        Get market cap controller instance
        
        Returns:
            MarketCapController with injected use cases
        """
        return MarketCapController(
            get_market_data_use_case=self.get_market_data_use_case(),
            get_all_market_data_use_case=self.get_all_market_data_use_case()
        )
    
    def get_health_status(self) -> dict:
        """
        Get container health status
        
        Returns:
            Health status dictionary
        """
        return {
            'container': 'DIContainer',
            'version': '6.0.0',
            'initialized': self._initialized,
            'singletons_count': len(self._singletons),
            'configuration': self._config.copy(),
            'registered_singletons': list(self._singletons.keys())
        }
    
    def reset(self) -> None:
        """
        Reset container (for testing)
        """
        self._singletons.clear()
        self._providers.clear()
        logger.info("DIContainer reset - all singletons cleared")


# Global container instance
container = DIContainer()