"""
Data Processing Service - Pydantic Models
Clean Architecture v6.0.0

Request/Response Models für FastAPI Endpoints
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal


# Stock Data Models
class StockDataItem(BaseModel):
    """Individual stock data point"""
    symbol: str = Field(..., description="Stock symbol")
    date: datetime = Field(..., description="Trading date")
    open_price: float = Field(..., gt=0, description="Opening price")
    high_price: float = Field(..., gt=0, description="Highest price")
    low_price: float = Field(..., gt=0, description="Lowest price")
    close_price: float = Field(..., gt=0, description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")
    adjusted_close: Optional[float] = Field(None, description="Adjusted closing price")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "AAPL",
                "date": "2024-08-25T09:30:00",
                "open_price": 150.25,
                "high_price": 152.80,
                "low_price": 149.50,
                "close_price": 151.75,
                "volume": 45678900,
                "adjusted_close": 151.75
            }
        }
    )


class StockDataIngestionRequest(BaseModel):
    """Request for stock data ingestion"""
    stock_data: List[StockDataItem] = Field(..., min_length=1, description="List of stock data points")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "stock_data": [
                    {
                        "symbol": "AAPL",
                        "date": "2024-08-25T09:30:00",
                        "open_price": 150.25,
                        "high_price": 152.80,
                        "low_price": 149.50,
                        "close_price": 151.75,
                        "volume": 45678900
                    }
                ]
            }
        }
    )


class StockDataIngestionResponse(BaseModel):
    """Response for stock data ingestion"""
    success: bool = Field(..., description="Ingestion success status")
    records_processed: int = Field(..., description="Number of records processed")
    quality_assessment: Dict[str, Any] = Field(..., description="Data quality assessment")
    message: str = Field(..., description="Result message")
    error: Optional[str] = Field(None, description="Error message if failed")


# Prediction Job Models
class PredictionJobRequest(BaseModel):
    """Request for creating prediction job"""
    symbol: str = Field(..., description="Stock symbol to predict")
    requested_models: List[str] = Field(..., min_length=1, description="ML model types to use")
    prediction_horizon_days: int = Field(1, ge=1, le=30, description="Prediction horizon in days")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "AAPL",
                "requested_models": ["linear_regression", "random_forest", "neural_network"],
                "prediction_horizon_days": 1
            }
        }
    )


class PredictionJobResponse(BaseModel):
    """Response for prediction job creation"""
    job_id: str = Field(..., description="Unique job identifier")
    symbol: str = Field(..., description="Stock symbol")
    requested_models: List[str] = Field(..., description="Requested model types")
    prediction_horizon_days: int = Field(..., description="Prediction horizon")
    status: str = Field(..., description="Job status")
    message: str = Field(..., description="Result message")


# Prediction Analysis Models
class PredictionAnalysisRequest(BaseModel):
    """Request for prediction analysis"""
    symbol: str = Field(..., description="Stock symbol to analyze")
    analysis_period_days: int = Field(30, ge=1, le=365, description="Analysis period in days")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "AAPL",
                "analysis_period_days": 30
            }
        }
    )


class PredictionAnalysisResponse(BaseModel):
    """Response for prediction analysis"""
    symbol: str = Field(..., description="Stock symbol")
    analysis_period_days: int = Field(..., description="Analysis period")
    predictions_analyzed: int = Field(..., description="Number of predictions analyzed")
    accuracy_metrics: Dict[str, Any] = Field(..., description="Accuracy metrics")
    model_performance: Dict[str, Any] = Field(..., description="Individual model performance")
    analysis_timestamp: str = Field(..., description="Analysis completion timestamp")


# Maintenance Models
class MaintenanceOperation(BaseModel):
    """Individual maintenance operation result"""
    operation: str = Field(..., description="Operation type")
    deleted_records: int = Field(..., description="Number of deleted records")
    success: bool = Field(..., description="Operation success status")


class MaintenanceCleanupResponse(BaseModel):
    """Response for maintenance cleanup"""
    success: bool = Field(..., description="Overall cleanup success")
    total_deleted_records: int = Field(..., description="Total records deleted")
    operations: List[MaintenanceOperation] = Field(..., description="Individual operation results")
    timestamp: str = Field(..., description="Cleanup timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")


# System Statistics Models
class SystemStatisticsResponse(BaseModel):
    """Response for system statistics"""
    storage_statistics: Dict[str, Any] = Field(..., description="Storage utilization statistics")
    health_status: Dict[str, Any] = Field(..., description="Service health status")
    service_statistics: Dict[str, Any] = Field(..., description="Service performance statistics")
    timestamp: str = Field(..., description="Statistics generation timestamp")


# Job Processing Models
class JobProcessingRequest(BaseModel):
    """Request for job processing"""
    max_jobs: int = Field(5, ge=1, le=20, description="Maximum jobs to process")


class JobProcessingResponse(BaseModel):
    """Response for job processing"""
    jobs_processed: int = Field(..., description="Number of jobs processed")
    successful_jobs: int = Field(..., description="Number of successful jobs")
    failed_jobs: int = Field(..., description="Number of failed jobs")
    processing_timestamp: str = Field(..., description="Processing completion timestamp")
    message: str = Field(..., description="Processing result message")


# Health Check Models
class HealthCheckResponse(BaseModel):
    """Response for health check"""
    status: str = Field(..., description="Service status (healthy/unhealthy)")
    message: str = Field(..., description="Status message")
    health_status: Dict[str, Any] = Field(..., description="Detailed health information")
    timestamp: str = Field(..., description="Health check timestamp")


# Stock Data Query Models
class StockDataResponse(BaseModel):
    """Response for stock data queries"""
    symbol: str = Field(..., description="Stock symbol")
    date: str = Field(..., description="Trading date")
    open_price: float = Field(..., description="Opening price")
    high_price: float = Field(..., description="Highest price")
    low_price: float = Field(..., description="Lowest price")
    close_price: float = Field(..., description="Closing price")
    volume: int = Field(..., description="Trading volume")
    adjusted_close: Optional[float] = Field(None, description="Adjusted closing price")
    daily_return: float = Field(..., description="Daily return percentage")
    price_range: float = Field(..., description="Price range (high - low)")


# Ensemble Prediction Models
class IndividualPredictionInfo(BaseModel):
    """Individual model prediction within ensemble"""
    model_type: str = Field(..., description="ML model type")
    predicted_price: float = Field(..., description="Predicted price")
    confidence_score: float = Field(..., description="Prediction confidence")
    is_high_confidence: bool = Field(..., description="High confidence indicator")


class EnsemblePredictionResponse(BaseModel):
    """Response for ensemble prediction"""
    ensemble_id: str = Field(..., description="Ensemble prediction ID")
    symbol: str = Field(..., description="Stock symbol")
    ensemble_price: Optional[float] = Field(None, description="Ensemble predicted price")
    ensemble_confidence: Optional[float] = Field(None, description="Ensemble confidence")
    weight_strategy: str = Field(..., description="Weight calculation strategy")
    model_count: int = Field(..., description="Number of models in ensemble")
    consensus_strength: float = Field(..., description="Consensus strength among models")
    prediction_horizon_days: int = Field(..., description="Prediction horizon")
    created_at: str = Field(..., description="Creation timestamp")
    data_quality_score: Optional[str] = Field(None, description="Data quality assessment")
    individual_predictions: List[IndividualPredictionInfo] = Field(..., description="Individual model predictions")


# Error Response Models
class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    timestamp: str = Field(..., description="Error timestamp")


# Batch Processing Models
class BatchJobRequest(BaseModel):
    """Request for batch job processing"""
    symbols: List[str] = Field(..., min_length=1, description="Stock symbols to process")
    model_types: List[str] = Field(..., min_length=1, description="ML model types")
    prediction_horizon_days: int = Field(1, ge=1, le=30, description="Prediction horizon")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbols": ["AAPL", "GOOGL", "MSFT"],
                "model_types": ["linear_regression", "random_forest"],
                "prediction_horizon_days": 1
            }
        }
    )


class BatchJobResponse(BaseModel):
    """Response for batch job creation"""
    job_ids: List[str] = Field(..., description="Created job identifiers")
    symbols_processed: int = Field(..., description="Number of symbols processed")
    total_jobs_created: int = Field(..., description="Total jobs created")
    message: str = Field(..., description="Batch processing result")


# Model Statistics Models
class ModelStatistics(BaseModel):
    """Statistics for individual ML model"""
    model_type: str = Field(..., description="ML model type")
    total_predictions: int = Field(..., description="Total predictions generated")
    average_confidence: float = Field(..., description="Average confidence score")
    average_accuracy: Optional[float] = Field(None, description="Average accuracy score")
    success_rate: float = Field(..., description="Prediction success rate")


class ModelStatisticsResponse(BaseModel):
    """Response for model statistics"""
    model_statistics: List[ModelStatistics] = Field(..., description="Individual model statistics")
    overall_statistics: Dict[str, Any] = Field(..., description="Overall system statistics")
    timestamp: str = Field(..., description="Statistics generation timestamp")