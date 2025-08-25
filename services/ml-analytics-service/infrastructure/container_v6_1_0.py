#!/usr/bin/env python3
"""
ML Analytics Dependency Injection Container v6.1.0 - PostgreSQL Clean Architecture
Composition Root for Machine Learning Service Dependencies

INFRASTRUCTURE LAYER - DEPENDENCY INJECTION:
- PostgreSQL Database Manager Integration
- Complete DI Container for all ML components
- Configurable service implementations
- Health monitoring and lifecycle management
- All 16 ML Engine integrations

DESIGN PATTERNS IMPLEMENTED:
- Dependency Injection: Centralized dependency management
- Factory Pattern: Service instance creation
- Singleton Pattern: Single container instance
- Observer Pattern: Health monitoring

DATABASE ARCHITECTURE:
- Centralized Database Connection Manager
- PostgreSQL with connection pooling
- ACID compliance and transaction support
- Advanced indexing and query optimization

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.1.0
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

# Add shared module to path for Database Manager import
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from database_connection_manager_v1_0_0_20250825 import DatabaseConnectionManager, DatabaseConfiguration

# Application Layer Imports
from ..application.use_cases.ml_training_use_cases import (
    TrainModelUseCase,
    EvaluateModelUseCase,
    RetrainOutdatedModelsUseCase
)
from ..application.use_cases.ml_prediction_use_cases import (
    GeneratePredictionUseCase,
    BatchPredictionUseCase,
    GetPredictionHistoryUseCase,
    CalculateRiskMetricsUseCase
)
from ..application.interfaces.ml_service_provider import IMLServiceProvider
from ..application.interfaces.event_publisher import IEventPublisher

# Domain Layer Imports
from ..domain.repositories.ml_repository import IMLAnalyticsRepository

# Infrastructure Layer Imports
from .persistence.postgresql_ml_repository import PostgreSQLMLAnalyticsRepository
from .external_services.ml_model_providers import MLServiceProviderImplementation
from .events.ml_event_publisher import MLEventPublisher

# Presentation Layer Imports
from ..presentation.controllers.ml_analytics_controller import MLAnalyticsController


logger = logging.getLogger(__name__)


# =============================================================================
# DEPENDENCY INJECTION CONTAINER v6.1.0
# =============================================================================

class MLAnalyticsDIContainer:
    """
    ML Analytics Dependency Injection Container v6.1.0
    
    PostgreSQL-enabled dependency management with centralized Database Manager
    following Composition Root pattern.
    
    SOLID Principles:
    - Single Responsibility: Only dependency configuration
    - Open/Closed: Extensible for new service implementations
    - Dependency Inversion: Uses interfaces, not concrete types
    
    DATABASE FEATURES:
    - PostgreSQL with connection pooling
    - ACID transactions and consistency
    - Advanced indexing and query optimization
    - Centralized connection management
    """
    
    def __init__(self):
        self._config: Dict[str, Any] = {}
        
        # Database Manager (v6.1.0 addition)
        self._db_manager: Optional[DatabaseConnectionManager] = None
        
        # Core Infrastructure Services
        self._repository: Optional[IMLAnalyticsRepository] = None
        self._ml_service_provider: Optional[IMLServiceProvider] = None
        self._event_publisher: Optional[IEventPublisher] = None
        
        # Use Cases
        self._train_model_use_case: Optional[TrainModelUseCase] = None
        self._evaluate_model_use_case: Optional[EvaluateModelUseCase] = None
        self._retrain_models_use_case: Optional[RetrainOutdatedModelsUseCase] = None
        self._generate_prediction_use_case: Optional[GeneratePredictionUseCase] = None
        self._batch_prediction_use_case: Optional[BatchPredictionUseCase] = None
        self._get_prediction_history_use_case: Optional[GetPredictionHistoryUseCase] = None
        self._calculate_risk_metrics_use_case: Optional[CalculateRiskMetricsUseCase] = None
        
        # Controllers
        self._controller: Optional[MLAnalyticsController] = None
        
        # Health Status
        self._initialized: bool = False
        self._initialization_time: Optional[datetime] = None
        
        logger.info("ML Analytics DI Container v6.1.0 initialized (PostgreSQL-enabled)")
    
    def configure(self, config: Dict[str, Any]):
        """
        Configure container with service settings
        
        Args:
            config: Configuration dictionary with service settings
                   Must include 'database' section for PostgreSQL connection
        """
        self._config = config.copy()
        
        # Reset initialized state when reconfiguring
        self._initialized = False
        self._reset_services()
        
        logger.info("ML Analytics DI Container v6.1.0 configured")
    
    def _reset_services(self):
        """Reset all service instances"""
        self._db_manager = None
        self._repository = None
        self._ml_service_provider = None
        self._event_publisher = None
        
        self._train_model_use_case = None
        self._evaluate_model_use_case = None
        self._retrain_models_use_case = None
        self._generate_prediction_use_case = None
        self._batch_prediction_use_case = None
        self._get_prediction_history_use_case = None
        self._calculate_risk_metrics_use_case = None
        
        self._controller = None
    
    async def initialize(self) -> bool:
        """
        Initialize all services and dependencies
        
        Returns:
            True if initialization successful
        """
        try:
            logger.info("Initializing ML Analytics DI Container v6.1.0...")
            start_time = datetime.now()
            
            # Initialize Database Manager first (v6.1.0 PostgreSQL)
            await self._initialize_database_manager()
            
            # Initialize repository with Database Manager
            await self._initialize_repository()
            
            # Initialize other core services
            await self._initialize_ml_service_provider()
            await self._initialize_event_publisher()
            
            # Initialize use cases
            self._initialize_use_cases()
            
            # Initialize controller
            self._initialize_controller()
            
            # Mark as initialized
            self._initialized = True
            self._initialization_time = datetime.now(timezone.utc)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"ML Analytics DI Container v6.1.0 initialized successfully in {duration:.2f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ML Analytics DI Container v6.1.0: {str(e)}")
            return False
    
    async def _initialize_database_manager(self):
        """Initialize centralized Database Connection Manager"""
        try:
            # Configure Database Manager with PostgreSQL settings
            db_config = DatabaseConfiguration(
                host=self._config.get('database', {}).get('host', 'localhost'),
                port=self._config.get('database', {}).get('port', 5432),
                database=self._config.get('database', {}).get('database', 'aktienanalyse'),
                user=self._config.get('database', {}).get('user', 'aktienanalyse_user'),
                password=self._config.get('database', {}).get('password', ''),
                min_connections=self._config.get('database', {}).get('min_connections', 5),
                max_connections=self._config.get('database', {}).get('max_connections', 20),
                connection_timeout=self._config.get('database', {}).get('connection_timeout', 30),
                command_timeout=self._config.get('database', {}).get('command_timeout', 60)
            )
            
            self._db_manager = DatabaseConnectionManager(db_config)
            await self._db_manager.initialize()
            
            logger.info("Database Connection Manager v6.1.0 initialized (PostgreSQL)")
            
        except Exception as e:
            logger.error(f"Failed to initialize Database Manager: {str(e)}")
            raise
    
    async def _initialize_repository(self):
        """Initialize PostgreSQL repository with Database Manager"""
        try:
            self._repository = PostgreSQLMLAnalyticsRepository(self._db_manager)
            
            # Initialize database schemas
            await self._repository.initialize_schemas()
            
            logger.info("PostgreSQL ML Analytics Repository initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize ML repository: {str(e)}")
            raise
    
    async def _initialize_ml_service_provider(self):
        """Initialize ML service provider with all 16 ML engines"""
        ml_config = self._config.get('ml_services', {
            'model_storage_path': '/opt/aktienanalyse-ökosystem/models/ml-analytics',
            'use_mock_providers': True,
            'enable_gpu_acceleration': False,
            'max_concurrent_trainings': 3,
            'feature_cache_size': 1000,
            'prediction_cache_ttl_minutes': 15
        })
        
        self._ml_service_provider = MLServiceProviderImplementation(ml_config)
        await self._ml_service_provider.initialize_services(ml_config)
        
        logger.info("ML Service Provider initialized with 16 ML engines")
    
    async def _initialize_event_publisher(self):
        """Initialize event publisher"""
        event_config = self._config.get('events', {
            'enabled': True,
            'event_bus_url': 'http://10.1.1.174:8014',
            'batch_size': 10,
            'flush_interval_seconds': 5,
            'max_retry_attempts': 3
        })
        
        self._event_publisher = MLEventPublisher(event_config)
        await self._event_publisher.initialize()
        
        logger.info("ML Event Publisher initialized")
    
    def _initialize_use_cases(self):
        """Initialize all use cases with dependencies"""
        
        # Training Use Cases
        self._train_model_use_case = TrainModelUseCase(
            repository=self._repository,
            model_trainer=self._ml_service_provider.trainer,
            event_publisher=self._event_publisher
        )
        
        self._evaluate_model_use_case = EvaluateModelUseCase(
            repository=self._repository,
            model_evaluator=self._ml_service_provider.evaluator,
            event_publisher=self._event_publisher
        )
        
        self._retrain_models_use_case = RetrainOutdatedModelsUseCase(
            repository=self._repository,
            train_model_use_case=self._train_model_use_case
        )
        
        # Prediction Use Cases
        self._generate_prediction_use_case = GeneratePredictionUseCase(
            repository=self._repository,
            predictor=self._ml_service_provider.predictor,
            risk_calculator=self._ml_service_provider.risk_calculator,
            event_publisher=self._event_publisher
        )
        
        self._batch_prediction_use_case = BatchPredictionUseCase(
            generate_prediction_use_case=self._generate_prediction_use_case
        )
        
        self._get_prediction_history_use_case = GetPredictionHistoryUseCase(
            repository=self._repository
        )
        
        self._calculate_risk_metrics_use_case = CalculateRiskMetricsUseCase(
            repository=self._repository,
            risk_calculator=self._ml_service_provider.risk_calculator,
            event_publisher=self._event_publisher
        )
        
        logger.info("All Use Cases initialized")
    
    def _initialize_controller(self):
        """Initialize presentation layer controller"""
        self._controller = MLAnalyticsController(
            train_model_use_case=self._train_model_use_case,
            evaluate_model_use_case=self._evaluate_model_use_case,
            retrain_models_use_case=self._retrain_models_use_case,
            generate_prediction_use_case=self._generate_prediction_use_case,
            batch_prediction_use_case=self._batch_prediction_use_case,
            get_prediction_history_use_case=self._get_prediction_history_use_case,
            calculate_risk_metrics_use_case=self._calculate_risk_metrics_use_case
        )
        
        logger.info("ML Analytics Controller initialized")
    
    # =============================================================================
    # SERVICE GETTERS
    # =============================================================================
    
    def get_database_manager(self) -> DatabaseConnectionManager:
        """Get database manager instance"""
        if not self._db_manager:
            raise RuntimeError("Database Manager not initialized - call initialize() first")
        return self._db_manager
    
    def get_repository(self) -> IMLAnalyticsRepository:
        """Get repository instance"""
        if not self._repository:
            raise RuntimeError("Repository not initialized - call initialize() first")
        return self._repository
    
    def get_ml_service_provider(self) -> IMLServiceProvider:
        """Get ML service provider instance"""
        if not self._ml_service_provider:
            raise RuntimeError("ML Service Provider not initialized - call initialize() first")
        return self._ml_service_provider
    
    def get_event_publisher(self) -> IEventPublisher:
        """Get event publisher instance"""
        if not self._event_publisher:
            raise RuntimeError("Event Publisher not initialized - call initialize() first")
        return self._event_publisher
    
    def get_controller(self) -> MLAnalyticsController:
        """Get controller instance"""
        if not self._controller:
            raise RuntimeError("Controller not initialized - call initialize() first")
        return self._controller
    
    # =============================================================================
    # USE CASE GETTERS
    # =============================================================================
    
    def get_train_model_use_case(self) -> TrainModelUseCase:
        """Get train model use case"""
        if not self._train_model_use_case:
            raise RuntimeError("Use cases not initialized - call initialize() first")
        return self._train_model_use_case
    
    def get_evaluate_model_use_case(self) -> EvaluateModelUseCase:
        """Get evaluate model use case"""
        if not self._evaluate_model_use_case:
            raise RuntimeError("Use cases not initialized - call initialize() first")
        return self._evaluate_model_use_case
    
    def get_retrain_models_use_case(self) -> RetrainOutdatedModelsUseCase:
        """Get retrain models use case"""
        if not self._retrain_models_use_case:
            raise RuntimeError("Use cases not initialized - call initialize() first")
        return self._retrain_models_use_case
    
    def get_generate_prediction_use_case(self) -> GeneratePredictionUseCase:
        """Get generate prediction use case"""
        if not self._generate_prediction_use_case:
            raise RuntimeError("Use cases not initialized - call initialize() first")
        return self._generate_prediction_use_case
    
    def get_batch_prediction_use_case(self) -> BatchPredictionUseCase:
        """Get batch prediction use case"""
        if not self._batch_prediction_use_case:
            raise RuntimeError("Use cases not initialized - call initialize() first")
        return self._batch_prediction_use_case
    
    def get_prediction_history_use_case(self) -> GetPredictionHistoryUseCase:
        """Get prediction history use case"""
        if not self._get_prediction_history_use_case:
            raise RuntimeError("Use cases not initialized - call initialize() first")
        return self._get_prediction_history_use_case
    
    def get_risk_metrics_use_case(self) -> CalculateRiskMetricsUseCase:
        """Get risk metrics use case"""
        if not self._calculate_risk_metrics_use_case:
            raise RuntimeError("Use cases not initialized - call initialize() first")
        return self._calculate_risk_metrics_use_case
    
    # =============================================================================
    # HEALTH AND LIFECYCLE MANAGEMENT
    # =============================================================================
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status of all services
        
        Returns:
            Dictionary with health status information including PostgreSQL status
        """
        health_status = {
            "container": {
                "version": "6.1.0",
                "database_type": "PostgreSQL",
                "initialized": self._initialized,
                "initialization_time": self._initialization_time.isoformat() if self._initialization_time else None,
                "configuration_keys": list(self._config.keys())
            }
        }
        
        if self._initialized:
            try:
                # Database Manager health (v6.1.0)
                if self._db_manager:
                    health_status["database_manager"] = await self._db_manager.get_connection_pool_status()
                
                # Repository health
                if self._repository:
                    health_status["repository"] = await self._repository.get_health_status()
                
                # ML Service Provider health
                if self._ml_service_provider:
                    health_status["ml_services"] = await self._ml_service_provider.get_service_health()
                
                # Event Publisher health
                if self._event_publisher:
                    health_status["event_publisher"] = await self._event_publisher.get_publisher_health()
                    
            except Exception as e:
                health_status["error"] = f"Error getting health status: {str(e)}"
        
        return health_status
    
    async def shutdown(self):
        """Gracefully shutdown all services"""
        try:
            logger.info("Shutting down ML Analytics DI Container v6.1.0...")
            
            # Shutdown services in reverse order
            if self._event_publisher:
                try:
                    if hasattr(self._event_publisher, 'shutdown'):
                        await self._event_publisher.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down event publisher: {str(e)}")
            
            if self._ml_service_provider:
                try:
                    await self._ml_service_provider.shutdown_services()
                except Exception as e:
                    logger.warning(f"Error shutting down ML services: {str(e)}")
            
            if self._repository:
                try:
                    if hasattr(self._repository, 'close'):
                        await self._repository.close()
                except Exception as e:
                    logger.warning(f"Error shutting down repository: {str(e)}")
            
            # Shutdown Database Manager last (v6.1.0)
            if self._db_manager:
                try:
                    await self._db_manager.close_all_connections()
                    logger.info("Database Connection Manager closed")
                except Exception as e:
                    logger.warning(f"Error shutting down Database Manager: {str(e)}")
            
            # Reset state
            self._initialized = False
            self._reset_services()
            
            logger.info("ML Analytics DI Container v6.1.0 shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during container shutdown: {str(e)}")
    
    def reset(self):
        """Reset container to uninitialized state"""
        self._initialized = False
        self._initialization_time = None
        self._config.clear()
        self._reset_services()
        
        logger.info("ML Analytics DI Container v6.1.0 reset")
    
    def is_initialized(self) -> bool:
        """Check if container is fully initialized"""
        return self._initialized
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self._config.copy()
    
    def get_initialization_time(self) -> Optional[datetime]:
        """Get initialization timestamp"""
        return self._initialization_time


# =============================================================================
# GLOBAL CONTAINER INSTANCE
# =============================================================================

# Global container instance (Singleton pattern)
container = MLAnalyticsDIContainer()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_container() -> MLAnalyticsDIContainer:
    """Get global container instance"""
    return container


async def initialize_container(config: Dict[str, Any]) -> bool:
    """Initialize global container with configuration"""
    container.configure(config)
    return await container.initialize()


async def shutdown_container():
    """Shutdown global container"""
    await container.shutdown()


def reset_container():
    """Reset global container"""
    container.reset()