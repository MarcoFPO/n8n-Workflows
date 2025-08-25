#!/usr/bin/env python3
"""
Prediction Tracking Service - Dependency Injection Container
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
import os
from typing import Optional
from functools import lru_cache

# Domain interfaces
from ..domain.repositories.prediction_repository import (
    IPredictionRepository,
    IPerformanceCalculator,
    IPredictionProvider,
    IPredictionCache
)
from ..application.interfaces.event_publisher import IEventPublisher

# Application use cases
from ..application.use_cases.prediction_use_cases import (
    StorePredictionUseCase,
    GetPerformanceComparisonUseCase,
    GetStatisticsUseCase,
    EvaluatePredictionsUseCase
)

# Presentation controller
from ..presentation.controllers.prediction_controller import PredictionController

# Infrastructure implementations
from .persistence.sqlite_prediction_repository import SQLitePredictionRepository
from .external_services.performance_calculator import PerformanceCalculatorService
from .external_services.unified_profit_provider import UnifiedProfitEngineProvider
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
        
        self._singletons: dict = {}
        self._config = {
            'database_path': os.getenv('PREDICTION_DB_PATH', 'predictions.db'),
            'use_real_provider': True,
            'profit_engine_host': os.getenv('PROFIT_ENGINE_HOST', '10.1.1.174'),
            'profit_engine_port': int(os.getenv('PROFIT_ENGINE_PORT', 8025)),
            'event_publishing_enabled': True,
            'accuracy_threshold': float(os.getenv('ACCURACY_THRESHOLD', 5.0)),
            'cache_enabled': False,  # Simplified for Phase 1
            'provider_timeout': int(os.getenv('PROVIDER_TIMEOUT', 10))
        }
        self._initialized = True
        logger.info("Prediction Tracking DIContainer initialized")
    
    def configure(self, config: dict) -> None:
        """
        Configure container with custom settings
        
        Args:
            config: Configuration dictionary
        """
        self._config.update(config)
        
        # Clear singletons to force recreation with new config
        self._singletons.clear()
        logger.info(f"Prediction Tracking DIContainer reconfigured with: {config}")
    
    @lru_cache(maxsize=None)
    def get_repository(self) -> IPredictionRepository:
        """
        Get prediction repository instance
        
        Returns:
            IPredictionRepository implementation
        """
        if 'repository' not in self._singletons:
            repository = SQLitePredictionRepository(
                db_path=self._config['database_path']
            )
            self._singletons['repository'] = repository
            logger.debug("Created SQLitePredictionRepository instance")
        
        return self._singletons['repository']
    
    @lru_cache(maxsize=None)
    def get_performance_calculator(self) -> IPerformanceCalculator:
        """
        Get performance calculator instance
        
        Returns:
            IPerformanceCalculator implementation
        """
        if 'performance_calculator' not in self._singletons:
            calculator = PerformanceCalculatorService(
                repository=self.get_repository(),
                accuracy_threshold=self._config['accuracy_threshold']
            )
            self._singletons['performance_calculator'] = calculator
            logger.debug("Created PerformanceCalculatorService instance")
        
        return self._singletons['performance_calculator']
    
    @lru_cache(maxsize=None)
    def get_provider(self) -> Optional[IPredictionProvider]:
        """
        Get prediction provider instance
        
        Returns:
            IPredictionProvider implementation or None if disabled
        """
        if not self._config.get('use_real_provider', True):
            return None
        
        if 'provider' not in self._singletons:
            provider = UnifiedProfitEngineProvider(
                host=self._config['profit_engine_host'],
                port=self._config['profit_engine_port'],
                timeout_seconds=self._config['provider_timeout'],
                fallback_to_mock=True
            )
            self._singletons['provider'] = provider
            logger.debug("Created UnifiedProfitEngineProvider instance")
        
        return self._singletons['provider']
    
    @lru_cache(maxsize=None)
    def get_cache(self) -> Optional[IPredictionCache]:
        """
        Get prediction cache instance
        
        Returns:
            IPredictionCache implementation or None if disabled
        """
        if not self._config.get('cache_enabled', False):
            return None
        
        # TODO: Implement cache in future iteration
        logger.debug("Cache not implemented yet - returning None")
        return None
    
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
            publisher = MockEventPublisher(max_stored_events=500)
            self._singletons['event_publisher'] = publisher
            logger.debug("Created MockEventPublisher instance")
        
        return self._singletons['event_publisher']
    
    def get_store_prediction_use_case(self) -> StorePredictionUseCase:
        """
        Get store prediction use case instance
        
        Returns:
            StorePredictionUseCase with injected dependencies
        """
        return StorePredictionUseCase(
            repository=self.get_repository(),
            cache=self.get_cache(),
            event_publisher=self.get_event_publisher()
        )
    
    def get_performance_comparison_use_case(self) -> GetPerformanceComparisonUseCase:
        """
        Get performance comparison use case instance
        
        Returns:
            GetPerformanceComparisonUseCase with injected dependencies
        """
        return GetPerformanceComparisonUseCase(
            repository=self.get_repository(),
            performance_calculator=self.get_performance_calculator(),
            cache=self.get_cache(),
            external_provider=self.get_provider()
        )
    
    def get_statistics_use_case(self) -> GetStatisticsUseCase:
        """
        Get statistics use case instance
        
        Returns:
            GetStatisticsUseCase with injected dependencies
        """
        return GetStatisticsUseCase(
            repository=self.get_repository(),
            performance_calculator=self.get_performance_calculator()
        )
    
    def get_evaluation_use_case(self) -> EvaluatePredictionsUseCase:
        """
        Get evaluation use case instance
        
        Returns:
            EvaluatePredictionsUseCase with injected dependencies
        """
        return EvaluatePredictionsUseCase(
            repository=self.get_repository(),
            external_provider=self.get_provider(),
            event_publisher=self.get_event_publisher()
        )
    
    def get_controller(self) -> PredictionController:
        """
        Get prediction controller instance
        
        Returns:
            PredictionController with injected use cases
        """
        return PredictionController(
            store_prediction_use_case=self.get_store_prediction_use_case(),
            performance_comparison_use_case=self.get_performance_comparison_use_case(),
            statistics_use_case=self.get_statistics_use_case(),
            evaluation_use_case=self.get_evaluation_use_case()
        )
    
    def get_health_status(self) -> dict:
        """
        Get container health status
        
        Returns:
            Health status dictionary
        """
        return {
            'container': 'PredictionTrackingDIContainer',
            'version': '6.0.0',
            'initialized': self._initialized,
            'singletons_count': len(self._singletons),
            'configuration': self._config.copy(),
            'registered_singletons': list(self._singletons.keys()),
            'features': {
                'repository': 'SQLite',
                'performance_calculator': 'enabled',
                'external_provider': 'unified_profit_engine' if self._config['use_real_provider'] else 'disabled',
                'event_publisher': 'mock' if self._config['event_publishing_enabled'] else 'disabled',
                'cache': 'disabled'
            }
        }
    
    async def health_check(self) -> dict:
        """
        Perform comprehensive health check
        
        Returns:
            Detailed health status
        """
        try:
            health_status = {
                'container': self.get_health_status(),
                'components': {}
            }
            
            # Check repository health
            try:
                repo = self.get_repository()
                repo_stats = await repo.get_repository_stats()
                health_status['components']['repository'] = {
                    'status': 'healthy',
                    'stats': repo_stats
                }
            except Exception as e:
                health_status['components']['repository'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
            
            # Check performance calculator
            try:
                calculator = self.get_performance_calculator()
                calc_stats = await calculator.get_calculator_stats()
                health_status['components']['performance_calculator'] = {
                    'status': 'healthy',
                    'stats': calc_stats
                }
            except Exception as e:
                health_status['components']['performance_calculator'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
            
            # Check external provider
            provider = self.get_provider()
            if provider:
                try:
                    is_available = await provider.is_available()
                    provider_info = await provider.get_provider_info()
                    health_status['components']['external_provider'] = {
                        'status': 'healthy' if is_available else 'degraded',
                        'available': is_available,
                        'info': provider_info
                    }
                except Exception as e:
                    health_status['components']['external_provider'] = {
                        'status': 'unhealthy',
                        'error': str(e)
                    }
            else:
                health_status['components']['external_provider'] = {
                    'status': 'disabled'
                }
            
            # Check event publisher
            event_publisher = self.get_event_publisher()
            if event_publisher:
                try:
                    publisher_health = await event_publisher.get_health_status()
                    health_status['components']['event_publisher'] = {
                        'status': 'healthy',
                        'info': publisher_health
                    }
                except Exception as e:
                    health_status['components']['event_publisher'] = {
                        'status': 'unhealthy',
                        'error': str(e)
                    }
            else:
                health_status['components']['event_publisher'] = {
                    'status': 'disabled'
                }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def reset(self) -> None:
        """
        Reset container (for testing)
        """
        self._singletons.clear()
        logger.info("Prediction Tracking DIContainer reset - all singletons cleared")


# Global container instance
container = DIContainer()