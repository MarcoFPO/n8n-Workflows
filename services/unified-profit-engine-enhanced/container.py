#!/usr/bin/env python3
"""
Dependency Injection Container
Unified Profit Engine Enhanced v6.0 - Clean Architecture

DEPENDENCY INJECTION:
- Centralized Dependency Management
- Interface-based Dependency Resolution  
- Configuration-driven Setup
- Testability Support

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Principles
Autor: Claude Code - Architecture Refactoring Specialist
Datum: 24. August 2025
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

import asyncpg
import aioredis
from decimal import Decimal

# Shared Imports - Centralized Database Management
from shared.database_connection_manager_v1_0_0_20250825 import (
    get_database_manager, 
    DatabaseConfiguration as CentralDatabaseConfiguration
)

# Domain Layer
from .domain.repositories import (
    ProfitPredictionRepository,
    SOLLISTTrackingRepository,
    MarketDataRepository
)

# Application Layer
from .application.use_cases import (
    GenerateMultiHorizonPredictionsUseCase,
    CalculateISTPerformanceUseCase,
    GetPerformanceAnalysisUseCase
)
from .application.interfaces import (
    EventPublisher,
    MLPredictionService,
    NotificationService,
    CacheService,
    MetricsService
)

# Infrastructure Layer
from .infrastructure.persistence.postgresql_repositories import (
    PostgreSQLProfitPredictionRepository,
    PostgreSQLSOLLISTTrackingRepository
)
from .infrastructure.external_services.yahoo_finance_adapter import (
    YahooFinanceMarketDataAdapter
)
from .infrastructure.event_bus.redis_event_publisher import (
    RedisEventPublisher
)

# Presentation Layer
from .presentation.controllers import UnifiedProfitEngineController


logger = logging.getLogger(__name__)


class ServiceConfiguration:
    """
    Centralized Service Configuration
    
    SINGLE RESPONSIBILITY: Configuration Management
    Environment-based Configuration mit Sensible Defaults
    """
    
    def __init__(self):
        # Database Configuration
        self.postgres_url = os.getenv(
            "POSTGRES_URL", 
            "postgresql://aktienanalyse:@localhost/aktienanalyse_events?sslmode=disable"
        )
        self.postgres_pool_size = int(os.getenv("POSTGRES_POOL_SIZE", "10"))
        
        # Redis Configuration
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Service Configuration
        self.service_port = int(os.getenv("SERVICE_PORT", "8025"))
        self.service_host = os.getenv("SERVICE_HOST", "0.0.0.0")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # External Services Configuration
        self.yahoo_finance_retry_count = int(os.getenv("YAHOO_FINANCE_RETRY_COUNT", "3"))
        self.yahoo_finance_timeout = float(os.getenv("YAHOO_FINANCE_TIMEOUT", "10.0"))
        
        # Event Bus Configuration
        self.event_bus_retry_count = int(os.getenv("EVENT_BUS_RETRY_COUNT", "3"))
        
        # ML Service Configuration (for integration)
        self.ml_service_url = os.getenv("ML_SERVICE_URL", "http://localhost:8021")
        
        # Feature Flags
        self.enable_event_persistence = os.getenv("ENABLE_EVENT_PERSISTENCE", "true").lower() == "true"
        self.enable_ml_integration = os.getenv("ENABLE_ML_INTEGRATION", "false").lower() == "true"
        self.enable_caching = os.getenv("ENABLE_CACHING", "false").lower() == "true"
        
    def to_dict(self) -> Dict[str, Any]:
        """Configuration als Dictionary für Logging/Debugging"""
        return {
            "postgres_url": self.postgres_url.replace(self.postgres_url.split('@')[0], "***") if '@' in self.postgres_url else self.postgres_url,
            "postgres_pool_size": self.postgres_pool_size,
            "redis_url": self.redis_url.replace(self.redis_url.split('@')[0], "***") if '@' in self.redis_url else self.redis_url,
            "service_port": self.service_port,
            "service_host": self.service_host,
            "log_level": self.log_level,
            "yahoo_finance_retry_count": self.yahoo_finance_retry_count,
            "yahoo_finance_timeout": self.yahoo_finance_timeout,
            "event_bus_retry_count": self.event_bus_retry_count,
            "ml_service_url": self.ml_service_url,
            "enable_event_persistence": self.enable_event_persistence,
            "enable_ml_integration": self.enable_ml_integration,
            "enable_caching": self.enable_caching
        }


class StubMLPredictionService(MLPredictionService):
    """
    Stub Implementation für ML Prediction Service
    
    Wird verwendet wenn ML Integration deaktiviert ist
    Provides fallback business logic ohne externe ML Dependencies
    """
    
    async def generate_prediction(self, market_data, horizon) -> Dict[str, Any]:
        """Simple Fallback Prediction Logic"""
        
        # Simple heuristische Vorhersage basierend auf current price
        current_price = float(market_data.current_price)
        
        # Horizon-basierte Adjustments
        horizon_multipliers = {
            "1W": 1.01,   # 1% Wachstum für 1 Woche
            "1M": 1.03,   # 3% Wachstum für 1 Monat  
            "3M": 1.08,   # 8% Wachstum für 3 Monate
            "12M": 1.15   # 15% Wachstum für 1 Jahr
        }
        
        multiplier = horizon_multipliers.get(horizon.value, 1.05)
        predicted_price = current_price * multiplier
        
        # Confidence basierend auf Volatilität (simple heuristic)
        confidence = min(0.8, max(0.4, 0.7 - (abs(multiplier - 1) * 2)))
        
        return {
            "profit_forecast": Decimal(str(predicted_price)),
            "confidence": confidence,
            "model_used": "simple_heuristic",
            "features_used": ["current_price", "horizon_multiplier"]
        }
    
    async def get_model_performance(self, horizon) -> Dict[str, Any]:
        """Stub Model Performance"""
        return {
            "accuracy": 0.65,
            "mae": 2.5,
            "rmse": 3.8,
            "last_trained": "2025-08-24T10:00:00"
        }
    
    async def retrain_models(self) -> Dict[str, Any]:
        """Stub Model Retraining"""
        return {
            "status": "completed",
            "message": "Stub - No actual retraining performed"
        }


class DependencyContainer:
    """
    Dependency Injection Container
    
    DEPENDENCY INVERSION PRINCIPLE:
    - High-level modules nicht abhängig von Low-level modules
    - Beide abhängig von Abstractions (Interfaces)
    - Container managed alle Dependencies und Lifecycles
    """
    
    def __init__(self, config: ServiceConfiguration):
        self.config = config
        
        # Infrastructure Components - MIGRATION to Centralized Database Manager
        self.database_manager = get_database_manager()
        self.redis_client: Optional[aioredis.Redis] = None
        
        # Repository Implementations
        self.profit_prediction_repo: Optional[ProfitPredictionRepository] = None
        self.soll_ist_repo: Optional[SOLLISTTrackingRepository] = None
        self.market_data_repo: Optional[MarketDataRepository] = None
        
        # Service Implementations
        self.event_publisher: Optional[EventPublisher] = None
        self.ml_service: Optional[MLPredictionService] = None
        
        # Use Cases
        self.prediction_use_case: Optional[GenerateMultiHorizonPredictionsUseCase] = None
        self.ist_calculation_use_case: Optional[CalculateISTPerformanceUseCase] = None
        self.performance_analysis_use_case: Optional[GetPerformanceAnalysisUseCase] = None
        
        # Controllers
        self.main_controller: Optional[UnifiedProfitEngineController] = None
        
        # Lifecycle Management
        self._initialized = False
    
    async def initialize(self):
        """
        Initializes all dependencies in correct order
        
        DEPENDENCY RESOLUTION ORDER:
        1. Infrastructure (Database, Redis)
        2. Repositories (Data Layer)
        3. Services (External Integrations)
        4. Use Cases (Application Logic)
        5. Controllers (Presentation Layer)
        """
        if self._initialized:
            logger.warning("Container already initialized")
            return
        
        try:
            logger.info("Initializing dependency container with configuration:")
            logger.info(f"Configuration: {self.config.to_dict()}")
            
            # 1. Infrastructure Layer
            await self._initialize_infrastructure()
            
            # 2. Repository Layer  
            await self._initialize_repositories()
            
            # 3. Service Layer
            await self._initialize_services()
            
            # 4. Application Layer (Use Cases)
            await self._initialize_use_cases()
            
            # 5. Presentation Layer (Controllers)
            await self._initialize_controllers()
            
            self._initialized = True
            logger.info("Dependency container initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize dependency container: {e}")
            await self.cleanup()
            raise
    
    async def _initialize_infrastructure(self):
        """Initialize Database und Redis Connections"""
        
        # MIGRATION: Use Centralized Database Manager
        try:
            # Initialize centralized database manager
            central_db_config = CentralDatabaseConfiguration()
            self.database_manager.config = central_db_config
            await self.database_manager.initialize()
            logger.info("Centralized Database Manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Centralized Database Manager: {e}")
            raise
        
        # Redis Connection
        try:
            self.redis_client = await aioredis.from_url(
                self.config.redis_url,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10
            )
            
            # Test Redis Connection
            await self.redis_client.ping()
            logger.info("Redis connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise
    
    async def _initialize_repositories(self):
        """Initialize Repository Implementations"""
        
        # Profit Prediction Repository - MIGRATION to Centralized Database Manager
        self.profit_prediction_repo = PostgreSQLProfitPredictionRepository(
            self.database_manager
        )
        
        # SOLL-IST Tracking Repository - MIGRATION to Centralized Database Manager
        self.soll_ist_repo = PostgreSQLSOLLISTTrackingRepository(
            self.database_manager
        )
        
        # Market Data Repository
        self.market_data_repo = YahooFinanceMarketDataAdapter(
            retry_count=self.config.yahoo_finance_retry_count,
            timeout=self.config.yahoo_finance_timeout
        )
        
        logger.info("Repository implementations initialized")
    
    async def _initialize_services(self):
        """Initialize Service Implementations"""
        
        # Event Publisher - MIGRATION to Centralized Database Manager
        db_manager_for_events = self.database_manager if self.config.enable_event_persistence else None
        self.event_publisher = RedisEventPublisher(
            redis_client=self.redis_client,
            database_manager=db_manager_for_events,
            retry_count=self.config.event_bus_retry_count
        )
        
        # ML Prediction Service
        if self.config.enable_ml_integration:
            # TODO: Implement real ML Service Integration
            logger.warning("ML Service integration not implemented - using stub")
            self.ml_service = StubMLPredictionService()
        else:
            self.ml_service = StubMLPredictionService()
        
        logger.info("Service implementations initialized")
    
    async def _initialize_use_cases(self):
        """Initialize Use Case Implementations"""
        
        # Multi-Horizon Predictions Use Case
        self.prediction_use_case = GenerateMultiHorizonPredictionsUseCase(
            market_data_repo=self.market_data_repo,
            prediction_repo=self.profit_prediction_repo,
            soll_ist_repo=self.soll_ist_repo,
            event_publisher=self.event_publisher,
            ml_service=self.ml_service
        )
        
        # IST Performance Calculation Use Case
        self.ist_calculation_use_case = CalculateISTPerformanceUseCase(
            market_data_repo=self.market_data_repo,
            soll_ist_repo=self.soll_ist_repo,
            event_publisher=self.event_publisher
        )
        
        # Performance Analysis Use Case
        self.performance_analysis_use_case = GetPerformanceAnalysisUseCase(
            soll_ist_repo=self.soll_ist_repo
        )
        
        logger.info("Use case implementations initialized")
    
    async def _initialize_controllers(self):
        """Initialize Controller Implementations"""
        
        # Main Unified Profit Engine Controller
        self.main_controller = UnifiedProfitEngineController(
            prediction_use_case=self.prediction_use_case,
            ist_calculation_use_case=self.ist_calculation_use_case,
            performance_analysis_use_case=self.performance_analysis_use_case
        )
        
        logger.info("Controller implementations initialized")
    
    async def cleanup(self):
        """Cleanup all resources"""
        logger.info("Cleaning up dependency container resources")
        
        # Close Redis Connection
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
        
        # Close Centralized Database Manager
        if self.database_manager:
            try:
                await self.database_manager.close()
                logger.info("Centralized Database Manager closed")
            except Exception as e:
                logger.error(f"Error closing Centralized Database Manager: {e}")
        
        self._initialized = False
    
    @asynccontextmanager
    async def get_container(self):
        """Context Manager für Container Lifecycle"""
        await self.initialize()
        try:
            yield self
        finally:
            await self.cleanup()
    
    def is_initialized(self) -> bool:
        """Check if container is initialized"""
        return self._initialized
    
    async def health_check(self) -> Dict[str, Any]:
        """Container Health Check"""
        health = {
            "initialized": self._initialized,
            "postgres": {"healthy": False, "error": None},
            "redis": {"healthy": False, "error": None}
        }
        
        # Database Manager Health Check
        if self.database_manager:
            try:
                db_health = await self.database_manager.health_check()
                health["postgres"]["healthy"] = db_health.get("status") == "healthy"
                if not health["postgres"]["healthy"]:
                    health["postgres"]["error"] = db_health.get("error", "Database Manager unhealthy")
            except Exception as e:
                health["postgres"]["error"] = str(e)
        
        # Redis Health Check
        if self.redis_client:
            try:
                await self.redis_client.ping()
                health["redis"]["healthy"] = True
            except Exception as e:
                health["redis"]["error"] = str(e)
        
        health["overall_healthy"] = (
            health["postgres"]["healthy"] and 
            health["redis"]["healthy"] and 
            health["initialized"]
        )
        
        return health