"""
Data Processing Service - Dependency Injection Container
Clean Architecture v6.0.0

Service Lifecycle Management und Dependency Injection
"""
import asyncio
import structlog
from typing import Dict, Any, Optional
from datetime import datetime

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

# Infrastructure
from infrastructure.persistence.sqlite_prediction_repository import (
    SQLiteStockDataRepository, SQLiteModelPredictionRepository
)
from infrastructure.persistence.sqlite_ensemble_repository import SQLiteEnsemblePredictionRepository
from infrastructure.external_services.mock_ml_service_provider import MockMLServiceProvider
from infrastructure.events.mock_event_publisher import MockEventPublisher

logger = structlog.get_logger(__name__)


class DataProcessingServiceContainer:
    """Dependency Injection Container für Data Processing Service"""
    
    def __init__(self):
        self.is_configured = False
        self.is_initialized = False
        self.initialization_error = None
        
        # Configuration
        self.config = {}
        
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
        self.stock_ingestion_use_case: Optional[StockDataIngestionUseCase] = None
        self.prediction_processing_use_case: Optional[PredictionProcessingUseCase] = None
        self.prediction_analysis_use_case: Optional[PredictionAnalysisUseCase] = None
        self.data_maintenance_use_case: Optional[DataMaintenanceUseCase] = None

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure container with application settings"""
        self.config = config
        self.is_configured = True
        logger.info("Container configured with application settings")

    async def initialize(self) -> bool:
        """Initialize all services and dependencies"""
        if not self.is_configured:
            logger.error("Container must be configured before initialization")
            return False
        
        try:
            logger.info("🔧 Initializing Data Processing Service Container...")
            
            # Initialize repositories
            await self._initialize_repositories()
            
            # Initialize external services
            await self._initialize_external_services()
            
            # Initialize use cases
            self._initialize_use_cases()
            
            # Verify all services
            await self._verify_services()
            
            self.is_initialized = True
            logger.info("✅ Container initialization completed successfully")
            return True
            
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"❌ Container initialization failed: {str(e)}")
            return False

    async def _initialize_repositories(self) -> None:
        """Initialize repository implementations"""
        logger.info("Initializing repositories...")
        
        # Stock Data Repository
        stock_db_path = self.config.get("stock_data_db", "prediction_stock_data.db")
        self.stock_data_repository = SQLiteStockDataRepository(stock_db_path)
        await self.stock_data_repository.initialize()
        logger.info(f"Stock data repository initialized: {stock_db_path}")
        
        # Model Prediction Repository
        model_db_path = self.config.get("model_predictions_db", "prediction_models.db")
        self.model_prediction_repository = SQLiteModelPredictionRepository(model_db_path)
        await self.model_prediction_repository.initialize()
        logger.info(f"Model prediction repository initialized: {model_db_path}")
        
        # Ensemble Repository
        ensemble_db_path = self.config.get("ensemble_predictions_db", "prediction_ensembles.db")
        self.ensemble_repository = SQLiteEnsemblePredictionRepository(ensemble_db_path)
        await self.ensemble_repository.initialize()
        logger.info(f"Ensemble prediction repository initialized: {ensemble_db_path}")
        
        # Prediction Job Repository (using existing repository for now)
        from infrastructure.persistence.sqlite_job_repository import SQLitePredictionJobRepository
        job_db_path = self.config.get("prediction_jobs_db", "prediction_jobs.db")
        self.job_repository = SQLitePredictionJobRepository(job_db_path)
        await self.job_repository.initialize()
        logger.info(f"Prediction job repository initialized: {job_db_path}")
        
        # Metrics Repository (using existing repository for now)
        from infrastructure.persistence.sqlite_metrics_repository import SQLiteDataProcessingMetricsRepository
        metrics_db_path = self.config.get("processing_metrics_db", "processing_metrics.db")
        self.metrics_repository = SQLiteDataProcessingMetricsRepository(metrics_db_path)
        await self.metrics_repository.initialize()
        logger.info(f"Processing metrics repository initialized: {metrics_db_path}")
        
        # ML Model Repository (using existing repository for now)
        from infrastructure.persistence.sqlite_ml_model_repository import SQLiteMLModelRepository
        ml_model_db_path = self.config.get("ml_models_db", "ml_models.db")
        self.ml_model_repository = SQLiteMLModelRepository(ml_model_db_path)
        await self.ml_model_repository.initialize()
        logger.info(f"ML model repository initialized: {ml_model_db_path}")

    async def _initialize_external_services(self) -> None:
        """Initialize external service implementations"""
        logger.info("Initializing external services...")
        
        # ML Service Provider
        use_real_ml_service = self.config.get("use_real_ml_service", False)
        simulate_failures = self.config.get("simulate_ml_failures", False)
        failure_rate = self.config.get("ml_failure_rate", 0.0)
        
        if use_real_ml_service:
            # IMPLEMENTATION NOTE: Real ML service integration pending
            # Configure use_real_ml_service=true in config when ML Analytics Service is ready
            logger.warning("Real ML service not yet implemented, using mock")
            self.ml_service_provider = MockMLServiceProvider(simulate_failures, failure_rate)
        else:
            self.ml_service_provider = MockMLServiceProvider(simulate_failures, failure_rate)
            
        logger.info(f"ML service provider initialized (mock={not use_real_ml_service})")
        
        # Event Publisher
        use_real_event_bus = self.config.get("use_real_event_bus", False)
        
        if use_real_event_bus:
            # IMPLEMENTATION NOTE: Real event bus integration pending
            # Configure use_real_event_bus=true when Event Bus Service v6 is stable
            logger.warning("Real event bus not yet implemented, using mock")
            self.event_publisher = MockEventPublisher()
        else:
            self.event_publisher = MockEventPublisher()
            
        logger.info(f"Event publisher initialized (mock={not use_real_event_bus})")

    def _initialize_use_cases(self) -> None:
        """Initialize use case orchestrators"""
        logger.info("Initializing use cases...")
        
        # Stock Data Ingestion Use Case
        self.stock_ingestion_use_case = StockDataIngestionUseCase(
            stock_data_repository=self.stock_data_repository,
            event_publisher=self.event_publisher
        )
        
        # Prediction Processing Use Case
        self.prediction_processing_use_case = PredictionProcessingUseCase(
            job_repository=self.job_repository,
            stock_data_repository=self.stock_data_repository,
            model_prediction_repository=self.model_prediction_repository,
            ensemble_repository=self.ensemble_repository,
            ml_service=self.ml_service_provider,
            event_publisher=self.event_publisher
        )
        
        # Prediction Analysis Use Case
        self.prediction_analysis_use_case = PredictionAnalysisUseCase(
            model_prediction_repository=self.model_prediction_repository,
            ensemble_repository=self.ensemble_repository,
            stock_data_repository=self.stock_data_repository,
            metrics_repository=self.metrics_repository,
            event_publisher=self.event_publisher
        )
        
        # Data Maintenance Use Case
        self.data_maintenance_use_case = DataMaintenanceUseCase(
            stock_data_repository=self.stock_data_repository,
            model_prediction_repository=self.model_prediction_repository,
            ensemble_repository=self.ensemble_repository,
            job_repository=self.job_repository,
            metrics_repository=self.metrics_repository,
            ml_model_repository=self.ml_model_repository,
            event_publisher=self.event_publisher
        )
        
        logger.info("Use cases initialized successfully")

    async def _verify_services(self) -> None:
        """Verify all services are healthy and functional"""
        logger.info("Verifying service health...")
        
        verification_results = []
        
        # Verify repositories
        try:
            symbols = await self.stock_data_repository.get_available_symbols()
            verification_results.append(("stock_data_repository", True, f"Available symbols: {len(symbols)}"))
        except Exception as e:
            verification_results.append(("stock_data_repository", False, str(e)))
        
        # Verify ML service
        try:
            health_status = await self.ml_service_provider.get_model_health_status()
            verification_results.append(("ml_service_provider", True, f"Status: {health_status.get('service_status')}"))
        except Exception as e:
            verification_results.append(("ml_service_provider", False, str(e)))
        
        # Verify event publisher
        try:
            is_healthy = await self.event_publisher.is_healthy()
            verification_results.append(("event_publisher", is_healthy, "Publisher health check"))
        except Exception as e:
            verification_results.append(("event_publisher", False, str(e)))
        
        # Log verification results
        failed_services = []
        for service, healthy, message in verification_results:
            if healthy:
                logger.info(f"✅ {service}: {message}")
            else:
                logger.warning(f"⚠️ {service}: {message}")
                failed_services.append(service)
        
        if failed_services:
            logger.warning(f"Some services have issues: {failed_services}")
        else:
            logger.info("All services verified successfully")

    async def cleanup(self) -> None:
        """Clean up resources and connections"""
        logger.info("Cleaning up container resources...")
        
        try:
            # Cleanup external services if they have cleanup methods
            if hasattr(self.ml_service_provider, 'cleanup'):
                await self.ml_service_provider.cleanup()
            
            if hasattr(self.event_publisher, 'cleanup'):
                await self.event_publisher.cleanup()
            
            # Reset state
            self.is_initialized = False
            logger.info("Container cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of all services"""
        return {
            "container_status": {
                "configured": self.is_configured,
                "initialized": self.is_initialized,
                "initialization_error": self.initialization_error
            },
            "repositories": {
                "stock_data": self.stock_data_repository is not None,
                "model_predictions": self.model_prediction_repository is not None,
                "ensemble_predictions": self.ensemble_repository is not None,
                "prediction_jobs": self.job_repository is not None,
                "processing_metrics": self.metrics_repository is not None,
                "ml_models": self.ml_model_repository is not None
            },
            "external_services": {
                "ml_service_provider": self.ml_service_provider is not None,
                "event_publisher": self.event_publisher is not None
            },
            "use_cases": {
                "stock_ingestion": self.stock_ingestion_use_case is not None,
                "prediction_processing": self.prediction_processing_use_case is not None,
                "prediction_analysis": self.prediction_analysis_use_case is not None,
                "data_maintenance": self.data_maintenance_use_case is not None
            },
            "timestamp": datetime.now().isoformat()
        }

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get statistics about service usage and performance"""
        return {
            "configuration": {
                "total_config_keys": len(self.config),
                "config_keys": list(self.config.keys())
            },
            "service_counts": {
                "repositories": 6,
                "external_services": 2,
                "use_cases": 4
            },
            "initialization_status": {
                "configured": self.is_configured,
                "initialized": self.is_initialized,
                "has_errors": self.initialization_error is not None
            },
            "timestamp": datetime.now().isoformat()
        }