"""
Data Processing Service - FastAPI Controller
Clean Architecture v6.0.0

RESTful API Endpoints für ML-basierte Stock Prediction Pipeline
"""
from fastapi import HTTPException, Depends, status
from fastapi.responses import JSONResponse
import structlog
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from presentation.models.data_processing_models import (
    StockDataIngestionRequest, StockDataIngestionResponse,
    PredictionJobRequest, PredictionJobResponse,
    PredictionAnalysisRequest, PredictionAnalysisResponse,
    MaintenanceCleanupResponse, SystemStatisticsResponse
)
from domain.entities.prediction_entities import PredictionModelType
from infrastructure.container import DataProcessingServiceContainer

logger = structlog.get_logger(__name__)


class DataProcessingController:
    """FastAPI Controller für Data Processing Operations"""
    
    def __init__(self, container: DataProcessingServiceContainer):
        self.container = container

    async def ingest_stock_data(self, request: StockDataIngestionRequest) -> StockDataIngestionResponse:
        """Ingest stock market data with quality assessment"""
        try:
            if not self.container.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
            
            # Convert request to domain entities
            from domain.entities.prediction_entities import StockData
            from decimal import Decimal
            
            stock_data_list = []
            for data_item in request.stock_data:
                stock_data = StockData(
                    symbol=data_item.symbol,
                    date=data_item.date,
                    open_price=Decimal(str(data_item.open_price)),
                    high_price=Decimal(str(data_item.high_price)),
                    low_price=Decimal(str(data_item.low_price)),
                    close_price=Decimal(str(data_item.close_price)),
                    volume=data_item.volume,
                    adjusted_close=Decimal(str(data_item.adjusted_close)) if data_item.adjusted_close else None
                )
                stock_data_list.append(stock_data)
            
            # Execute use case
            result = await self.container.stock_ingestion_use_case.ingest_stock_data(stock_data_list)
            
            return StockDataIngestionResponse(
                success=result["success"],
                records_processed=result["records_processed"],
                quality_assessment=result.get("quality_assessment", {}),
                message=result["message"],
                error=result.get("error")
            )
            
        except Exception as e:
            logger.error(f"Stock data ingestion failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    async def create_prediction_job(self, request: PredictionJobRequest) -> PredictionJobResponse:
        """Create new prediction job"""
        try:
            if not self.container.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
            
            # Convert string model types to enums
            model_types = [PredictionModelType(model) for model in request.requested_models]
            
            # Create job
            job_id = await self.container.prediction_processing_use_case.create_prediction_job(
                symbol=request.symbol,
                model_types=model_types,
                prediction_horizon_days=request.prediction_horizon_days
            )
            
            return PredictionJobResponse(
                job_id=job_id,
                symbol=request.symbol,
                requested_models=request.requested_models,
                prediction_horizon_days=request.prediction_horizon_days,
                status="pending",
                message="Prediction job created successfully"
            )
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create prediction job: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Job creation failed: {str(e)}")

    async def process_pending_jobs(self, max_jobs: int = 5) -> Dict[str, Any]:
        """Process pending prediction jobs"""
        try:
            if not self.container.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
            
            result = await self.container.prediction_processing_use_case.process_pending_jobs(max_jobs)
            
            return {
                "jobs_processed": result["jobs_processed"],
                "successful_jobs": result["successful_jobs"],
                "failed_jobs": result["failed_jobs"],
                "processing_timestamp": datetime.now().isoformat(),
                "message": f"Processed {result['jobs_processed']} pending jobs"
            }
            
        except Exception as e:
            logger.error(f"Failed to process pending jobs: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Job processing failed: {str(e)}")

    async def get_prediction_analysis(self, request: PredictionAnalysisRequest) -> PredictionAnalysisResponse:
        """Get prediction performance analysis"""
        try:
            if not self.container.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
            
            result = await self.container.prediction_analysis_use_case.analyze_prediction_performance(
                symbol=request.symbol,
                days=request.analysis_period_days
            )
            
            return PredictionAnalysisResponse(
                symbol=result["symbol"],
                analysis_period_days=result["analysis_period_days"],
                predictions_analyzed=result["predictions_analyzed"],
                accuracy_metrics=result["accuracy_metrics"],
                model_performance=result["model_performance"],
                analysis_timestamp=result["analysis_timestamp"]
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze predictions: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    async def perform_maintenance_cleanup(self) -> MaintenanceCleanupResponse:
        """Perform routine data maintenance and cleanup"""
        try:
            if not self.container.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
            
            result = await self.container.data_maintenance_use_case.perform_routine_cleanup()
            
            return MaintenanceCleanupResponse(
                success=result["success"],
                total_deleted_records=result.get("total_deleted_records", 0),
                operations=result["operations"],
                timestamp=result["timestamp"],
                error=result.get("error")
            )
            
        except Exception as e:
            logger.error(f"Maintenance cleanup failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

    async def get_system_statistics(self) -> SystemStatisticsResponse:
        """Get comprehensive system statistics"""
        try:
            if not self.container.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
            
            storage_stats = await self.container.data_maintenance_use_case.get_system_storage_statistics()
            health_status = self.container.get_health_status()
            
            return SystemStatisticsResponse(
                storage_statistics=storage_stats,
                health_status=health_status,
                service_statistics=self.container.get_service_statistics(),
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to get system statistics: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Statistics failed: {str(e)}")

    async def get_available_symbols(self) -> List[str]:
        """Get list of available stock symbols"""
        try:
            if not self.container.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
            
            symbols = await self.container.stock_data_repository.get_available_symbols()
            return symbols
            
        except Exception as e:
            logger.error(f"Failed to get available symbols: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get symbols: {str(e)}")

    async def get_latest_stock_data(self, symbol: str) -> Dict[str, Any]:
        """Get latest stock data for symbol"""
        try:
            if not self.container.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
            
            stock_data = await self.container.stock_data_repository.get_latest_stock_data(symbol)
            
            if not stock_data:
                raise HTTPException(status_code=404, detail=f"No data found for symbol: {symbol}")
            
            return {
                "symbol": stock_data.symbol,
                "date": stock_data.date.isoformat(),
                "open_price": float(stock_data.open_price),
                "high_price": float(stock_data.high_price),
                "low_price": float(stock_data.low_price),
                "close_price": float(stock_data.close_price),
                "volume": stock_data.volume,
                "adjusted_close": float(stock_data.adjusted_close) if stock_data.adjusted_close else None,
                "daily_return": float(stock_data.daily_return()),
                "price_range": float(stock_data.price_range())
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get latest stock data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get stock data: {str(e)}")

    async def get_latest_ensemble_prediction(self, symbol: str) -> Dict[str, Any]:
        """Get latest ensemble prediction for symbol"""
        try:
            if not self.container.is_initialized:
                raise HTTPException(status_code=503, detail="Service not initialized")
            
            ensemble = await self.container.ensemble_repository.get_latest_ensemble_prediction(symbol)
            
            if not ensemble:
                raise HTTPException(status_code=404, detail=f"No ensemble predictions found for symbol: {symbol}")
            
            return {
                "ensemble_id": ensemble.ensemble_id,
                "symbol": ensemble.symbol,
                "ensemble_price": float(ensemble.ensemble_price) if ensemble.ensemble_price else None,
                "ensemble_confidence": ensemble.ensemble_confidence,
                "weight_strategy": ensemble.weight_strategy.value,
                "model_count": ensemble.get_model_count(),
                "consensus_strength": ensemble.get_consensus_strength(),
                "prediction_horizon_days": ensemble.prediction_horizon_days,
                "created_at": ensemble.created_at.isoformat(),
                "data_quality_score": ensemble.data_quality_score.value if ensemble.data_quality_score else None,
                "individual_predictions": [
                    {
                        "model_type": pred.model_type.value,
                        "predicted_price": float(pred.predicted_price),
                        "confidence_score": pred.confidence_score,
                        "is_high_confidence": pred.is_high_confidence()
                    }
                    for pred in ensemble.individual_predictions
                ]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get ensemble prediction: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get prediction: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """Health check endpoint"""
        try:
            health_status = self.container.get_health_status()
            
            if not health_status["container_status"]["initialized"]:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unhealthy",
                        "message": "Service not initialized",
                        "health_status": health_status,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            return {
                "status": "healthy",
                "message": "Data Processing Service is operational",
                "health_status": health_status,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "message": f"Health check failed: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
            )