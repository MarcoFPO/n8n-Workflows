"""
Data Processing Service - Dependency Injection Container v6.1.0
Clean Architecture v6.1.0 - PostgreSQL Migration

Service Lifecycle Management und Dependency Injection mit Database Manager
"""
import asyncio
import structlog
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import sys

# Database Manager Import - Direct Path Import
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from database_connection_manager_v1_0_0_20250825 import (
    DatabaseConnectionManager, 
    DatabaseConfiguration
)

# Domain
from domain.repositories.prediction_repository import (
    IStockDataRepository, IModelPredictionRepository, IEnsemblePredictionRepository,
    IPredictionJobRepository, IDataProcessingMetricsRepository, IMLModelRepository
)

# Application
from application.interfaces.ml_service_provider import IMLServiceProvider
from application.interfaces.event_publisher import IEventPublisher
from application.use_cases.prediction_use_cases import (
    StockDataIngestionUseCase, PredictionProcessingUseCase,
    PredictionAnalysisUseCase, DataMaintenanceUseCase
)

# Infrastructure - PostgreSQL
from infrastructure.persistence.postgresql_prediction_repository import (
    PostgreSQLStockDataRepository, PostgreSQLEnsemblePredictionRepository,
    PostgreSQLPredictionJobRepository
)
# Note: Other repositories will be created as needed
from infrastructure.external_services.mock_ml_service_provider import MockMLServiceProvider
from infrastructure.events.mock_event_publisher import MockEventPublisher

logger = structlog.get_logger(__name__)


class DataProcessingServiceContainer:
    """Dependency Injection Container für Data Processing Service v6.1.0"""
    
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
            'ml_service_provider': {
                'use_mock': True,  # For development
                'timeout_seconds': 30
            },
            'event_publisher': {
                'enabled': True,
                'max_events': 1000
            },
            'maintenance': {
                'cleanup_interval_hours': 168,  # 7 days
                'max_job_retention_days': 30
            }
        }
        
        # Database Manager
        self._db_manager: Optional[DatabaseConnectionManager] = None
        
        # Repositories
        self.stock_data_repository: Optional[IStockDataRepository] = None
        self.model_prediction_repository: Optional[IModelPredictionRepository] = None
        self.ensemble_repository: Optional[IEnsemblePredictionRepository] = None
        self.job_repository: Optional[IPredictionJobRepository] = None
        self.metrics_repository: Optional[IDataProcessingMetricsRepository] = None
        self.ml_model_repository: Optional[IMLModelRepository] = None
        
        # External Services
        self.ml_service_provider: Optional[IMLServiceProvider] = None
        self.event_publisher: Optional[IEventPublisher] = None
        
        # Use Cases
        self.stock_data_ingestion_use_case: Optional[StockDataIngestionUseCase] = None
        self.prediction_processing_use_case: Optional[PredictionProcessingUseCase] = None
        self.prediction_analysis_use_case: Optional[PredictionAnalysisUseCase] = None
        self.data_maintenance_use_case: Optional[DataMaintenanceUseCase] = None

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
            logger.info("Initializing Data Processing Service Container v6.1.0...")
            
            # Initialize Database Manager
            db_config = DatabaseConfiguration()
            self._db_manager = DatabaseConnectionManager(db_config)
            await self._db_manager.initialize()
            
            # Initialize schemas
            if self.config['database_manager']['auto_initialize_schema']:
                success = await self._initialize_schemas()
                if not success:
                    logger.error("Failed to initialize database schemas")
                    return False
            
            # Initialize repositories
            await self._initialize_repositories()
            
            # Initialize external services
            await self._initialize_external_services()
            
            # Initialize use cases
            await self._initialize_use_cases()
            
            self.is_initialized = True
            self._initialized_at = datetime.now(timezone.utc)
            
            logger.info("Data Processing Service Container v6.1.0 initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Container initialization failed", error=str(e))
            self.initialization_error = str(e)
            return False

    async def _initialize_schemas(self) -> bool:
        """Initialize all database schemas"""
        try:
            # Initialize stock data schema
            stock_repo = PostgreSQLStockDataRepository(self._db_manager)
            if not await stock_repo.initialize_schema():
                return False
            
            # Initialize ensemble predictions schema
            ensemble_repo = PostgreSQLEnsemblePredictionRepository(self._db_manager)
            if not await ensemble_repo.initialize_schema():
                return False
            
            # Initialize prediction jobs schema
            job_repo = PostgreSQLPredictionJobRepository(self._db_manager)
            if not await job_repo.initialize_schema():
                return False
                
            logger.info("All data processing schemas initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Schema initialization failed", error=str(e))
            return False

    async def _initialize_repositories(self):
        """Initialize repositories mit PostgreSQL"""
        try:
            # Stock Data Repository
            self.stock_data_repository = PostgreSQLStockDataRepository(self._db_manager)
            
            # Ensemble Prediction Repository
            self.ensemble_repository = PostgreSQLEnsemblePredictionRepository(self._db_manager)
            
            # Prediction Job Repository
            self.job_repository = PostgreSQLPredictionJobRepository(self._db_manager)
            
            # IMPLEMENTATION NOTE: Additional repositories can be added as business requirements evolve:
            # self.model_prediction_repository = PostgreSQLModelPredictionRepository(self._db_manager)
            # self.metrics_repository = PostgreSQLMetricsRepository(self._db_manager)
            # self.ml_model_repository = PostgreSQLMLModelRepository(self._db_manager)
            
            logger.info("PostgreSQL repositories initialized")
            
        except Exception as e:
            logger.error("Repository initialization failed", error=str(e))
            raise

    async def _initialize_external_services(self):
        """Initialize external services"""
        try:
            # ML Service Provider
            if self.config['ml_service_provider']['use_mock']:
                self.ml_service_provider = MockMLServiceProvider()
            else:
                # IMPLEMENTATION NOTE: Integration with ML Analytics Service (Port 8021) pending
                # Replace MockMLServiceProvider with HttpMLServiceProvider when ready
                self.ml_service_provider = MockMLServiceProvider()
            
            # Event Publisher
            if self.config['event_publisher']['enabled']:
                self.event_publisher = MockEventPublisher(
                    max_stored_events=self.config['event_publisher']['max_events']
                )
            
            logger.info("External services initialized")
            
        except Exception as e:
            logger.error("External services initialization failed", error=str(e))
            raise

    async def _initialize_use_cases(self):
        """Initialize use cases mit dependencies"""
        try:
            # Stock Data Ingestion Use Case
            self.stock_data_ingestion_use_case = StockDataIngestionUseCase(
                stock_data_repository=self.stock_data_repository,
                event_publisher=self.event_publisher
            )
            
            # Prediction Processing Use Case
            self.prediction_processing_use_case = PredictionProcessingUseCase(
                stock_data_repository=self.stock_data_repository,
                ensemble_repository=self.ensemble_repository,
                job_repository=self.job_repository,
                ml_service_provider=self.ml_service_provider,
                event_publisher=self.event_publisher
            )
            
            # Prediction Analysis Use Case
            self.prediction_analysis_use_case = PredictionAnalysisUseCase(
                ensemble_repository=self.ensemble_repository,
                job_repository=self.job_repository,
                event_publisher=self.event_publisher
            )
            
            # Data Maintenance Use Case
            self.data_maintenance_use_case = DataMaintenanceUseCase(
                stock_data_repository=self.stock_data_repository,
                ensemble_repository=self.ensemble_repository,
                job_repository=self.job_repository,
                event_publisher=self.event_publisher
            )
            
            logger.info("Use cases initialized")
            
        except Exception as e:
            logger.error("Use cases initialization failed", error=str(e))
            raise

    def get_database_manager(self) -> DatabaseConnectionManager:
        """Get database manager"""
        if self._db_manager is None:
            raise RuntimeError("Database Manager not initialized")
        return self._db_manager

    # Repository Getters
    def get_stock_data_repository(self) -> IStockDataRepository:
        if not self.stock_data_repository:
            raise RuntimeError("Stock data repository not initialized")
        return self.stock_data_repository

    def get_ensemble_repository(self) -> IEnsemblePredictionRepository:
        if not self.ensemble_repository:
            raise RuntimeError("Ensemble repository not initialized")
        return self.ensemble_repository

    def get_job_repository(self) -> IPredictionJobRepository:
        if not self.job_repository:
            raise RuntimeError("Job repository not initialized")
        return self.job_repository

    # External Service Getters
    def get_ml_service_provider(self) -> IMLServiceProvider:
        if not self.ml_service_provider:
            raise RuntimeError("ML service provider not initialized")
        return self.ml_service_provider

    def get_event_publisher(self) -> IEventPublisher:
        if not self.event_publisher:
            raise RuntimeError("Event publisher not initialized")
        return self.event_publisher

    # Use Case Getters
    def get_stock_data_ingestion_use_case(self) -> StockDataIngestionUseCase:
        if not self.stock_data_ingestion_use_case:
            raise RuntimeError("Stock data ingestion use case not initialized")
        return self.stock_data_ingestion_use_case

    def get_prediction_processing_use_case(self) -> PredictionProcessingUseCase:
        if not self.prediction_processing_use_case:
            raise RuntimeError("Prediction processing use case not initialized")
        return self.prediction_processing_use_case

    def get_prediction_analysis_use_case(self) -> PredictionAnalysisUseCase:
        if not self.prediction_analysis_use_case:
            raise RuntimeError("Prediction analysis use case not initialized")
        return self.prediction_analysis_use_case

    def get_data_maintenance_use_case(self) -> DataMaintenanceUseCase:
        if not self.data_maintenance_use_case:
            raise RuntimeError("Data maintenance use case not initialized")
        return self.data_maintenance_use_case

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
            
            # Repository Health Checks
            repositories = [
                ('stock_data_repository', 'stock_data'),
                ('ensemble_repository', 'ensemble_predictions'),
                ('job_repository', 'prediction_jobs')
            ]
            
            for repo_attr, repo_name in repositories:
                repo = getattr(self, repo_attr, None)
                if repo:
                    health_data['components'][repo_name] = {
                        'status': 'healthy',
                        'initialized': True
                    }
                else:
                    health_data['components'][repo_name] = {
                        'status': 'not_initialized'
                    }
            
            # External Services Health
            if self.ml_service_provider:
                health_data['components']['ml_service_provider'] = {
                    'status': 'healthy',
                    'type': 'mock' if self.config['ml_service_provider']['use_mock'] else 'real'
                }
            
            if self.event_publisher:
                health_data['components']['event_publisher'] = {
                    'status': 'healthy',
                    'type': 'mock'
                }
            
            # Use Cases Health
            use_cases = [
                'stock_data_ingestion_use_case',
                'prediction_processing_use_case', 
                'prediction_analysis_use_case',
                'data_maintenance_use_case'
            ]
            
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
            logger.info("Shutting down Data Processing Service Container...")
            
            # Clear all services
            self.stock_data_repository = None
            self.ensemble_repository = None
            self.job_repository = None
            self.ml_service_provider = None
            self.event_publisher = None
            
            self.stock_data_ingestion_use_case = None
            self.prediction_processing_use_case = None
            self.prediction_analysis_use_case = None
            self.data_maintenance_use_case = None
            
            # Shutdown database manager
            if self._db_manager:
                await self._db_manager.close()
                self._db_manager = None
            
            self.is_initialized = False
            self._initialized_at = None
            
            logger.info("Data Processing Service Container shutdown completed")
            return True
            
        except Exception as e:
            logger.error("Error during container shutdown", error=str(e))
            return False

    async def reset_for_testing(self):
        """Reset container for testing"""
        await self.shutdown()
        self.__init__()


# Global container instance
container = DataProcessingServiceContainer()