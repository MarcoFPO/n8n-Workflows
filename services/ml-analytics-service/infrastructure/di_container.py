#!/usr/bin/env python3
"""
Dependency Injection Container

Autor: Claude Code - DI Container Architect  
Datum: 26. August 2025
Clean Architecture v6.0.0 - Infrastructure Layer
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Type, TypeVar, List
from abc import ABC, abstractmethod

# Application Layer Imports
from ..application.interfaces.ml_prediction_service import IMLPredictionService, IStreamingAnalyticsService, IMLModelTrainingService
from ..application.interfaces.portfolio_service import IPortfolioOptimizationService, IGlobalPortfolioService
from ..application.interfaces.event_publisher import IEventPublisher
from ..application.use_cases.prediction_use_cases import (
    GenerateSinglePredictionUseCase, GenerateEnsemblePredictionUseCase, BatchPredictionUseCase
)

# Domain Layer Imports  
from ..domain.entities.ml_engine import MLEngineRegistry, MLEngine, MLEngineConfiguration, MLEngineType, PredictionHorizon
from ..domain.services.prediction_domain_service import PredictionDomainService

# Infrastructure Layer Imports
from .ml_engines.lstm_engine_adapter import LSTMEngineAdapter
from .external_services.event_publisher_impl import EventPublisherImpl
from .repositories.ml_analytics_repository import MLAnalyticsRepository

# Configuration
from .configuration.ml_service_config import MLServiceConfig

logger = logging.getLogger(__name__)

T = TypeVar('T')


class IDIContainer(ABC):
    """Interface für Dependency Injection Container"""
    
    @abstractmethod
    async def configure(self, config: Dict[str, Any]) -> None:
        """Configure container with settings"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize all registered services"""
        pass
    
    @abstractmethod
    def get(self, interface_type: Type[T]) -> T:
        """Get service instance by interface type"""
        pass
    
    @abstractmethod
    def get_use_case(self, use_case_type: Type[T]) -> T:
        """Get use case instance"""
        pass


class MLAnalyticsDIContainer(IDIContainer):
    """
    ML Analytics Dependency Injection Container
    
    Orchestrates all service dependencies following Clean Architecture principles
    - Domain Layer: Keine externen Dependencies
    - Application Layer: Nur Domain Dependencies via Interfaces  
    - Infrastructure Layer: Implementiert alle Interfaces
    - Presentation Layer: Nur Application Dependencies
    """
    
    def __init__(self):
        self._config: Optional[MLServiceConfig] = None
        self._is_initialized = False
        
        # Service Registry
        self._services: Dict[Type, Any] = {}
        self._use_cases: Dict[Type, Any] = {}
        
        # ML Engine Registry (Domain Entity)
        self._ml_engine_registry = MLEngineRegistry()
        
        # Infrastructure Services
        self._database_pool = None
        self._event_publisher = None
        self._repository = None
        
        # ML Engine Adapters
        self._lstm_adapter = None
        self._xgboost_adapter = None
        self._ensemble_adapter = None
        
        # Domain Services
        self._prediction_domain_service = None
    
    async def configure(self, config: Dict[str, Any]) -> None:
        """Configure container with ML service settings"""
        
        try:
            self._config = MLServiceConfig(config)
            logger.info("DI Container configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to configure DI container: {str(e)}")
            raise
    
    async def initialize(self) -> bool:
        """
        Initialize all services in proper dependency order
        
        Follows Clean Architecture layering:
        1. Infrastructure Services (Database, External Services)
        2. Domain Services (Pure Business Logic)  
        3. ML Engine Adapters (Infrastructure → Application Interface)
        4. Application Use Cases (Orchestration)
        """
        
        if self._is_initialized:
            return True
        
        try:
            logger.info("Starting ML Analytics DI Container initialization...")
            
            # Phase 1: Initialize Infrastructure Services
            await self._initialize_infrastructure_services()
            
            # Phase 2: Initialize Domain Services  
            await self._initialize_domain_services()
            
            # Phase 3: Initialize ML Engine Adapters
            await self._initialize_ml_engine_adapters()
            
            # Phase 4: Initialize Application Use Cases
            await self._initialize_use_cases()
            
            # Phase 5: Validate Service Health
            await self._validate_service_health()
            
            self._is_initialized = True
            logger.info("ML Analytics DI Container initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize DI container: {str(e)}")
            self._is_initialized = False
            raise
    
    async def _initialize_infrastructure_services(self) -> None:
        """Initialize infrastructure services (Database, Event Publisher, Repository)"""
        
        logger.info("Initializing infrastructure services...")
        
        # Initialize Database Pool (mock for now)
        self._database_pool = await self._create_database_pool()
        
        # Initialize Event Publisher
        self._event_publisher = EventPublisherImpl()
        await self._event_publisher.initialize()
        self._services[IEventPublisher] = self._event_publisher
        
        # Initialize Repository
        self._repository = MLAnalyticsRepository(self._database_pool)
        await self._repository.initialize()
        
        logger.info("Infrastructure services initialized")
    
    async def _initialize_domain_services(self) -> None:
        """Initialize domain services (Pure business logic)"""
        
        logger.info("Initializing domain services...")
        
        # Prediction Domain Service (no dependencies)
        self._prediction_domain_service = PredictionDomainService()
        
        logger.info("Domain services initialized")
    
    async def _initialize_ml_engine_adapters(self) -> None:
        """Initialize ML engine adapters and register in ML Engine Registry"""
        
        logger.info("Initializing ML engine adapters...")
        
        model_storage_path = self._config.get_model_storage_path()
        
        # Initialize LSTM Engine Adapter
        self._lstm_adapter = LSTMEngineAdapter(self._database_pool, model_storage_path)
        await self._lstm_adapter.initialize()
        
        # Register LSTM Engines in Domain Registry
        await self._register_lstm_engines()
        
        # Register ML Prediction Service (LSTM Adapter implements interface)
        self._services[IMLPredictionService] = self._lstm_adapter
        
        logger.info("ML engine adapters initialized")
    
    async def _initialize_use_cases(self) -> None:
        """Initialize application use cases with injected dependencies"""
        
        logger.info("Initializing application use cases...")
        
        # Generate Single Prediction Use Case
        self._use_cases[GenerateSinglePredictionUseCase] = GenerateSinglePredictionUseCase(
            prediction_service=self._services[IMLPredictionService],
            domain_service=self._prediction_domain_service,
            event_publisher=self._services[IEventPublisher]
        )
        
        # Generate Ensemble Prediction Use Case
        self._use_cases[GenerateEnsemblePredictionUseCase] = GenerateEnsemblePredictionUseCase(
            prediction_service=self._services[IMLPredictionService],
            domain_service=self._prediction_domain_service,
            event_publisher=self._services[IEventPublisher]
        )
        
        # Batch Prediction Use Case  
        self._use_cases[BatchPredictionUseCase] = BatchPredictionUseCase(
            prediction_service=self._services[IMLPredictionService],
            domain_service=self._prediction_domain_service,
            event_publisher=self._services[IEventPublisher]
        )
        
        logger.info("Application use cases initialized")
    
    async def _register_lstm_engines(self) -> None:
        """Register LSTM engines in ML Engine Registry (Domain Entity)"""
        
        # Simple LSTM Engine Configuration
        simple_lstm_config = MLEngineConfiguration(
            engine_type=MLEngineType.SIMPLE_LSTM,
            supported_horizons=[
                PredictionHorizon.SHORT_TERM,
                PredictionHorizon.MEDIUM_TERM
            ],
            requires_database=True,
            requires_model_storage=True,
            initialization_priority=2
        )
        
        # Multi-Horizon LSTM Engine Configuration  
        multi_horizon_config = MLEngineConfiguration(
            engine_type=MLEngineType.MULTI_HORIZON_LSTM,
            supported_horizons=[
                PredictionHorizon.INTRADAY,
                PredictionHorizon.SHORT_TERM,
                PredictionHorizon.MEDIUM_TERM,
                PredictionHorizon.LONG_TERM,
                PredictionHorizon.EXTENDED
            ],
            requires_database=True,
            requires_model_storage=True,
            initialization_priority=1
        )
        
        # Create ML Engine Entities
        simple_lstm_engine = MLEngine(
            engine_type=MLEngineType.SIMPLE_LSTM,
            configuration=simple_lstm_config,
            health=self._create_engine_health(MLEngineType.SIMPLE_LSTM)
        )
        
        multi_horizon_engine = MLEngine(
            engine_type=MLEngineType.MULTI_HORIZON_LSTM,
            configuration=multi_horizon_config,
            health=self._create_engine_health(MLEngineType.MULTI_HORIZON_LSTM)
        )
        
        # Register engines in domain registry
        self._ml_engine_registry.register_engine(simple_lstm_engine)
        self._ml_engine_registry.register_engine(multi_horizon_engine)
        
        # Mark engines as initialized
        simple_lstm_engine.mark_as_initialized()
        multi_horizon_engine.mark_as_initialized()
    
    def _create_engine_health(self, engine_type: MLEngineType):
        """Create ML Engine Health entity"""
        from ..domain.entities.ml_engine import MLEngineHealth, MLEngineStatus
        from datetime import datetime
        
        return MLEngineHealth(
            engine_type=engine_type,
            status=MLEngineStatus.READY,
            last_check=datetime.utcnow()
        )
    
    async def _validate_service_health(self) -> None:
        """Validate health of all initialized services"""
        
        logger.info("Validating service health...")
        
        # Check ML Engine Registry health
        if self._ml_engine_registry.has_critical_issues():
            raise Exception("ML Engine Registry has critical issues")
        
        healthy_engines = self._ml_engine_registry.get_healthy_engines()
        logger.info(f"Healthy ML engines: {len(healthy_engines)}")
        
        # Check Event Publisher health
        if self._event_publisher:
            health = await self._event_publisher.get_publisher_health()
            if not health.get("healthy", False):
                logger.warning("Event Publisher health check failed")
        
        logger.info("Service health validation completed")
    
    async def _create_database_pool(self):
        """Create database connection pool (mock implementation)"""
        
        # Mock database pool - in real implementation would create asyncpg pool
        logger.info(f"Creating database pool for: {self._config.get_database_url()}")
        
        # Return mock pool object
        return {"mock_pool": True, "database_url": self._config.get_database_url()}
    
    def get(self, interface_type: Type[T]) -> T:
        """Get service instance by interface type"""
        
        if not self._is_initialized:
            raise RuntimeError("Container not initialized")
        
        service = self._services.get(interface_type)
        if service is None:
            raise ValueError(f"Service not registered for interface: {interface_type.__name__}")
        
        return service
    
    def get_use_case(self, use_case_type: Type[T]) -> T:
        """Get use case instance"""
        
        if not self._is_initialized:
            raise RuntimeError("Container not initialized")
        
        use_case = self._use_cases.get(use_case_type)
        if use_case is None:
            raise ValueError(f"Use case not registered: {use_case_type.__name__}")
        
        return use_case
    
    def get_ml_engine_registry(self) -> MLEngineRegistry:
        """Get ML Engine Registry (Domain Entity)"""
        return self._ml_engine_registry
    
    async def get_container_status(self) -> Dict[str, Any]:
        """Get comprehensive container status"""
        
        engine_status = self._ml_engine_registry.get_engine_count_by_status()
        
        return {
            "is_initialized": self._is_initialized,
            "services_registered": len(self._services),
            "use_cases_registered": len(self._use_cases),
            "ml_engines": {
                "total_registered": len(self._ml_engine_registry.engines),
                "status_breakdown": {status.value: count for status, count in engine_status.items()},
                "healthy_engines": len(self._ml_engine_registry.get_healthy_engines()),
                "has_critical_issues": self._ml_engine_registry.has_critical_issues()
            },
            "configuration": {
                "model_storage_path": self._config.get_model_storage_path() if self._config else None,
                "database_configured": self._database_pool is not None
            }
        }
    
    async def shutdown(self) -> None:
        """Graceful container shutdown"""
        
        logger.info("Shutting down ML Analytics DI Container...")
        
        # Shutdown services in reverse order
        if self._event_publisher:
            await self._event_publisher.shutdown()
        
        if self._repository:
            await self._repository.shutdown()
        
        # Clear registries
        self._services.clear()
        self._use_cases.clear()
        
        self._is_initialized = False
        logger.info("ML Analytics DI Container shutdown completed")