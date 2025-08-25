"""
Data Processing Service - Application Use Cases
Clean Architecture v6.0.0

Business Logic Orchestration für ML-basierte Stock Prediction Pipeline
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import asyncio
import structlog
from decimal import Decimal

from domain.entities.prediction_entities import (
    StockData, ModelPrediction, EnsemblePrediction, PredictionJob,
    DataProcessingMetrics, PredictionModelType, PredictionStatus,
    EnsembleWeightStrategy, DataQuality
)
from domain.repositories.prediction_repository import (
    IStockDataRepository, IModelPredictionRepository, IEnsemblePredictionRepository,
    IPredictionJobRepository, IDataProcessingMetricsRepository, IMLModelRepository
)
from application.interfaces.ml_service_provider import IMLServiceProvider
from application.interfaces.event_publisher import IEventPublisher

logger = structlog.get_logger(__name__)


class StockDataIngestionUseCase:
    """Use Case für Stock Data Ingestion und Quality Assessment"""
    
    def __init__(
        self,
        stock_data_repository: IStockDataRepository,
        event_publisher: IEventPublisher
    ):
        self.stock_data_repository = stock_data_repository
        self.event_publisher = event_publisher

    async def ingest_stock_data(
        self, 
        stock_data_list: List[StockData]
    ) -> Dict[str, Any]:
        """Ingest stock data with quality assessment"""
        logger.info(f"Starting stock data ingestion for {len(stock_data_list)} records")
        
        try:
            # Data quality validation
            quality_assessment = await self._assess_data_quality(stock_data_list)
            
            # Store data if quality is acceptable
            if quality_assessment['overall_quality'] != DataQuality.INSUFFICIENT:
                success = await self.stock_data_repository.store_stock_data(stock_data_list)
                
                if success:
                    await self.event_publisher.publish_event(
                        "data.ingested",
                        {
                            "record_count": len(stock_data_list),
                            "symbols": list(set(data.symbol for data in stock_data_list)),
                            "quality_score": quality_assessment['quality_score'],
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    logger.info("Stock data ingestion completed successfully")
                    
                return {
                    "success": success,
                    "records_processed": len(stock_data_list),
                    "quality_assessment": quality_assessment,
                    "message": "Data ingestion completed"
                }
            else:
                logger.warning("Data quality insufficient for ingestion")
                return {
                    "success": False,
                    "records_processed": 0,
                    "quality_assessment": quality_assessment,
                    "message": "Data quality insufficient for ingestion"
                }
                
        except Exception as e:
            logger.error(f"Stock data ingestion failed: {str(e)}")
            await self.event_publisher.publish_event(
                "data.ingestion_failed",
                {"error": str(e), "timestamp": datetime.now().isoformat()}
            )
            return {
                "success": False,
                "records_processed": 0,
                "error": str(e),
                "message": "Data ingestion failed"
            }

    async def _assess_data_quality(self, stock_data_list: List[StockData]) -> Dict[str, Any]:
        """Assess quality of incoming stock data"""
        if not stock_data_list:
            return {
                "overall_quality": DataQuality.INSUFFICIENT,
                "quality_score": 0.0,
                "issues": ["No data provided"]
            }

        quality_issues = []
        quality_scores = []
        
        # Check data completeness
        complete_records = 0
        for data in stock_data_list:
            record_score = 1.0
            
            # Required field validation
            if not data.symbol or data.open_price <= 0 or data.close_price <= 0:
                quality_issues.append(f"Invalid data for {data.symbol}")
                record_score -= 0.3
            
            # Volume validation
            if data.volume <= 0:
                quality_issues.append(f"No volume data for {data.symbol}")
                record_score -= 0.2
            
            # Price consistency validation
            if data.high_price < max(data.open_price, data.close_price):
                quality_issues.append(f"Inconsistent price data for {data.symbol}")
                record_score -= 0.3
                
            if record_score >= 0.5:
                complete_records += 1
            
            quality_scores.append(max(0.0, record_score))

        completeness_ratio = complete_records / len(stock_data_list)
        average_quality = sum(quality_scores) / len(quality_scores)
        overall_score = (completeness_ratio + average_quality) / 2.0

        # Determine overall quality level
        if overall_score >= 0.9:
            quality_level = DataQuality.EXCELLENT
        elif overall_score >= 0.7:
            quality_level = DataQuality.GOOD
        elif overall_score >= 0.5:
            quality_level = DataQuality.ACCEPTABLE
        elif overall_score >= 0.3:
            quality_level = DataQuality.POOR
        else:
            quality_level = DataQuality.INSUFFICIENT

        return {
            "overall_quality": quality_level,
            "quality_score": overall_score,
            "completeness_ratio": completeness_ratio,
            "complete_records": complete_records,
            "total_records": len(stock_data_list),
            "issues": quality_issues[:10]  # Limit to first 10 issues
        }


class PredictionProcessingUseCase:
    """Use Case für ML Model Prediction Processing"""
    
    def __init__(
        self,
        job_repository: IPredictionJobRepository,
        stock_data_repository: IStockDataRepository,
        model_prediction_repository: IModelPredictionRepository,
        ensemble_repository: IEnsemblePredictionRepository,
        ml_service: IMLServiceProvider,
        event_publisher: IEventPublisher
    ):
        self.job_repository = job_repository
        self.stock_data_repository = stock_data_repository
        self.model_prediction_repository = model_prediction_repository
        self.ensemble_repository = ensemble_repository
        self.ml_service = ml_service
        self.event_publisher = event_publisher

    async def create_prediction_job(
        self, 
        symbol: str,
        model_types: List[PredictionModelType],
        prediction_horizon_days: int = 1
    ) -> str:
        """Create new prediction job"""
        logger.info(f"Creating prediction job for {symbol} with {len(model_types)} models")
        
        job = PredictionJob(
            symbol=symbol,
            requested_models=model_types,
            prediction_horizon_days=prediction_horizon_days
        )
        
        success = await self.job_repository.create_job(job)
        
        if success:
            await self.event_publisher.publish_event(
                "prediction.job_created",
                {
                    "job_id": job.job_id,
                    "symbol": symbol,
                    "model_types": [mt.value for mt in model_types],
                    "timestamp": datetime.now().isoformat()
                }
            )
            logger.info(f"Prediction job created: {job.job_id}")
        
        return job.job_id

    async def process_pending_jobs(self, max_jobs: int = 5) -> Dict[str, Any]:
        """Process pending prediction jobs"""
        logger.info("Processing pending prediction jobs")
        
        pending_jobs = await self.job_repository.get_pending_jobs(limit=max_jobs)
        
        if not pending_jobs:
            return {
                "jobs_processed": 0,
                "message": "No pending jobs found"
            }

        results = []
        
        for job in pending_jobs:
            result = await self._process_single_job(job)
            results.append(result)
        
        successful_jobs = sum(1 for r in results if r["success"])
        
        return {
            "jobs_processed": len(results),
            "successful_jobs": successful_jobs,
            "failed_jobs": len(results) - successful_jobs,
            "results": results
        }

    async def _process_single_job(self, job: PredictionJob) -> Dict[str, Any]:
        """Process individual prediction job"""
        logger.info(f"Processing job {job.job_id} for symbol {job.symbol}")
        
        try:
            # Mark job as started
            job.start_processing()
            await self.job_repository.update_job(job)
            
            # Get historical stock data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)  # 1 year of historical data
            
            historical_data = await self.stock_data_repository.get_stock_data(
                job.symbol, start_date, end_date
            )
            
            if len(historical_data) < 30:  # Minimum data requirement
                job.mark_failed("Insufficient historical data")
                await self.job_repository.update_job(job)
                return {
                    "success": False,
                    "job_id": job.job_id,
                    "error": "Insufficient historical data"
                }
            
            job.input_data_size = len(historical_data)
            
            # Generate predictions for each requested model
            individual_predictions = []
            
            for model_type in job.requested_models:
                try:
                    prediction = await self.ml_service.generate_prediction(
                        model_type=model_type,
                        symbol=job.symbol,
                        historical_data=historical_data,
                        prediction_horizon_days=job.prediction_horizon_days
                    )
                    
                    # Store individual prediction
                    await self.model_prediction_repository.store_prediction(prediction)
                    individual_predictions.append(prediction)
                    
                    logger.info(f"Generated prediction for {model_type.value}: {prediction.predicted_price}")
                    
                except Exception as e:
                    logger.warning(f"Failed to generate prediction for {model_type.value}: {str(e)}")
                    continue
            
            if not individual_predictions:
                job.mark_failed("No successful predictions generated")
                await self.job_repository.update_job(job)
                return {
                    "success": False,
                    "job_id": job.job_id,
                    "error": "No successful predictions generated"
                }
            
            # Create ensemble prediction
            ensemble = EnsemblePrediction(
                symbol=job.symbol,
                individual_predictions=individual_predictions,
                weight_strategy=EnsembleWeightStrategy.ACCURACY_WEIGHTED,
                prediction_horizon_days=job.prediction_horizon_days
            )
            
            # Store ensemble prediction
            await self.ensemble_repository.store_ensemble_prediction(ensemble)
            
            # Complete job successfully
            job.complete_successfully(ensemble)
            await self.job_repository.update_job(job)
            
            # Publish event
            await self.event_publisher.publish_event(
                "prediction.completed",
                {
                    "job_id": job.job_id,
                    "symbol": job.symbol,
                    "ensemble_id": ensemble.ensemble_id,
                    "ensemble_price": str(ensemble.ensemble_price),
                    "confidence": ensemble.ensemble_confidence,
                    "model_count": ensemble.get_model_count(),
                    "processing_time": job.processing_duration_seconds,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Job {job.job_id} completed successfully")
            
            return {
                "success": True,
                "job_id": job.job_id,
                "ensemble_id": ensemble.ensemble_id,
                "predicted_price": str(ensemble.ensemble_price),
                "confidence": ensemble.ensemble_confidence,
                "processing_time": job.processing_duration_seconds
            }
            
        except Exception as e:
            logger.error(f"Job {job.job_id} failed: {str(e)}")
            job.mark_failed(str(e))
            await self.job_repository.update_job(job)
            
            await self.event_publisher.publish_event(
                "prediction.failed",
                {
                    "job_id": job.job_id,
                    "symbol": job.symbol,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return {
                "success": False,
                "job_id": job.job_id,
                "error": str(e)
            }


class PredictionAnalysisUseCase:
    """Use Case für Prediction Analysis und Performance Evaluation"""
    
    def __init__(
        self,
        model_prediction_repository: IModelPredictionRepository,
        ensemble_repository: IEnsemblePredictionRepository,
        stock_data_repository: IStockDataRepository,
        metrics_repository: IDataProcessingMetricsRepository,
        event_publisher: IEventPublisher
    ):
        self.model_prediction_repository = model_prediction_repository
        self.ensemble_repository = ensemble_repository
        self.stock_data_repository = stock_data_repository
        self.metrics_repository = metrics_repository
        self.event_publisher = event_publisher

    async def analyze_prediction_performance(
        self, 
        symbol: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Analyze prediction performance for symbol over time period"""
        logger.info(f"Analyzing prediction performance for {symbol} over {days} days")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get historical predictions and actual stock data
        predictions = await self.ensemble_repository.get_ensemble_predictions_by_symbol(
            symbol, limit=days
        )
        
        actual_data = await self.stock_data_repository.get_stock_data(
            symbol, start_date, end_date
        )
        
        if not predictions or not actual_data:
            return {
                "symbol": symbol,
                "analysis_period_days": days,
                "predictions_found": len(predictions),
                "actual_data_points": len(actual_data),
                "message": "Insufficient data for analysis"
            }

        # Calculate accuracy metrics
        accuracy_metrics = await self._calculate_accuracy_metrics(predictions, actual_data)
        
        # Model comparison
        model_performance = await self._analyze_model_performance(symbol, days)
        
        # Generate performance summary
        performance_summary = {
            "symbol": symbol,
            "analysis_period_days": days,
            "predictions_analyzed": len(predictions),
            "accuracy_metrics": accuracy_metrics,
            "model_performance": model_performance,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        # Publish analysis event
        await self.event_publisher.publish_event(
            "prediction.analysis_completed",
            performance_summary
        )
        
        return performance_summary

    async def _calculate_accuracy_metrics(
        self, 
        predictions: List[EnsemblePrediction],
        actual_data: List[StockData]
    ) -> Dict[str, float]:
        """Calculate prediction accuracy metrics"""
        if not predictions or not actual_data:
            return {}

        # Create date-indexed actual prices
        actual_prices = {data.date.date(): data.close_price for data in actual_data}
        
        accuracy_scores = []
        price_errors = []
        
        for prediction in predictions:
            pred_date = prediction.created_at.date()
            target_date = pred_date + timedelta(days=prediction.prediction_horizon_days)
            
            if target_date in actual_prices and prediction.ensemble_price:
                actual_price = actual_prices[target_date]
                predicted_price = prediction.ensemble_price
                
                # Calculate percentage error
                error = abs(float(actual_price - predicted_price)) / float(actual_price)
                price_errors.append(error)
                
                # Accuracy score (1 - error percentage)
                accuracy = max(0.0, 1.0 - error)
                accuracy_scores.append(accuracy)

        if not accuracy_scores:
            return {}

        return {
            "average_accuracy": sum(accuracy_scores) / len(accuracy_scores),
            "median_accuracy": sorted(accuracy_scores)[len(accuracy_scores) // 2],
            "best_accuracy": max(accuracy_scores),
            "worst_accuracy": min(accuracy_scores),
            "average_price_error_percent": sum(price_errors) / len(price_errors) * 100,
            "predictions_evaluated": len(accuracy_scores)
        }

    async def _analyze_model_performance(self, symbol: str, days: int) -> Dict[str, Any]:
        """Analyze individual model performance"""
        model_stats = {}
        
        for model_type in PredictionModelType:
            stats = await self.model_prediction_repository.get_model_performance_statistics(
                model_type, symbol
            )
            
            trend = await self.model_prediction_repository.get_prediction_accuracy_trend(
                model_type, days
            )
            
            model_stats[model_type.value] = {
                "statistics": stats,
                "trend": trend
            }

        return model_stats


class DataMaintenanceUseCase:
    """Use Case für Data Maintenance und Cleanup Operations"""
    
    def __init__(
        self,
        stock_data_repository: IStockDataRepository,
        model_prediction_repository: IModelPredictionRepository,
        ensemble_repository: IEnsemblePredictionRepository,
        job_repository: IPredictionJobRepository,
        metrics_repository: IDataProcessingMetricsRepository,
        ml_model_repository: IMLModelRepository,
        event_publisher: IEventPublisher
    ):
        self.stock_data_repository = stock_data_repository
        self.model_prediction_repository = model_prediction_repository
        self.ensemble_repository = ensemble_repository
        self.job_repository = job_repository
        self.metrics_repository = metrics_repository
        self.ml_model_repository = ml_model_repository
        self.event_publisher = event_publisher

    async def perform_routine_cleanup(self) -> Dict[str, Any]:
        """Perform routine data cleanup operations"""
        logger.info("Starting routine data cleanup")
        
        cleanup_results = {
            "timestamp": datetime.now().isoformat(),
            "operations": []
        }
        
        try:
            # Clean up old stock data (keep 2 years)
            deleted_stock_data = await self.stock_data_repository.cleanup_old_stock_data(days_to_keep=730)
            cleanup_results["operations"].append({
                "operation": "stock_data_cleanup",
                "deleted_records": deleted_stock_data,
                "success": True
            })
            
            # Clean up old predictions (keep 6 months)
            deleted_predictions = await self.model_prediction_repository.cleanup_old_predictions(days_to_keep=180)
            cleanup_results["operations"].append({
                "operation": "predictions_cleanup",
                "deleted_records": deleted_predictions,
                "success": True
            })
            
            # Clean up old ensemble predictions (keep 1 year)
            deleted_ensembles = await self.ensemble_repository.cleanup_old_ensembles(days_to_keep=365)
            cleanup_results["operations"].append({
                "operation": "ensembles_cleanup",
                "deleted_records": deleted_ensembles,
                "success": True
            })
            
            # Clean up completed jobs (keep 1 month)
            deleted_jobs = await self.job_repository.cleanup_completed_jobs(days_to_keep=30)
            cleanup_results["operations"].append({
                "operation": "jobs_cleanup",
                "deleted_records": deleted_jobs,
                "success": True
            })
            
            # Clean up old metrics (keep 2 years)
            deleted_metrics = await self.metrics_repository.cleanup_old_metrics(days_to_keep=730)
            cleanup_results["operations"].append({
                "operation": "metrics_cleanup",
                "deleted_records": deleted_metrics,
                "success": True
            })
            
            # Clean up old ML models (keep 3 months)
            deleted_models = await self.ml_model_repository.cleanup_old_models(days_to_keep=90)
            cleanup_results["operations"].append({
                "operation": "models_cleanup",
                "deleted_records": deleted_models,
                "success": True
            })
            
            total_deleted = sum(op["deleted_records"] for op in cleanup_results["operations"])
            
            await self.event_publisher.publish_event(
                "maintenance.cleanup_completed",
                {
                    "total_records_deleted": total_deleted,
                    "operations_completed": len(cleanup_results["operations"]),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            cleanup_results["total_deleted_records"] = total_deleted
            cleanup_results["success"] = True
            
            logger.info(f"Routine cleanup completed, deleted {total_deleted} records")
            
        except Exception as e:
            logger.error(f"Cleanup operation failed: {str(e)}")
            cleanup_results["success"] = False
            cleanup_results["error"] = str(e)
            
            await self.event_publisher.publish_event(
                "maintenance.cleanup_failed",
                {"error": str(e), "timestamp": datetime.now().isoformat()}
            )
        
        return cleanup_results

    async def get_system_storage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics"""
        logger.info("Generating system storage statistics")
        
        try:
            stats = {
                "timestamp": datetime.now().isoformat(),
                "repositories": {}
            }
            
            # Stock data statistics
            symbols = await self.stock_data_repository.get_available_symbols()
            total_stock_records = 0
            for symbol in symbols:
                count = await self.stock_data_repository.get_stock_data_count(symbol)
                total_stock_records += count
            
            stats["repositories"]["stock_data"] = {
                "total_symbols": len(symbols),
                "total_records": total_stock_records,
                "symbols": symbols[:20]  # First 20 symbols
            }
            
            # Job statistics
            job_stats = await self.job_repository.get_job_statistics()
            stats["repositories"]["prediction_jobs"] = job_stats
            
            # Model usage statistics
            model_usage = await self.ml_model_repository.get_model_usage_statistics()
            stats["repositories"]["ml_models"] = model_usage
            
            # System performance summary
            performance_summary = await self.metrics_repository.get_system_performance_summary()
            stats["performance"] = performance_summary
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to generate storage statistics: {str(e)}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "success": False
            }