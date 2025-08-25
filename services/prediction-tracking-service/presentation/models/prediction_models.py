#!/usr/bin/env python3
"""
Prediction Tracking Service - Presentation Models
Clean Architecture Presentation Layer DTOs

CLEAN ARCHITECTURE - PRESENTATION LAYER:
- Request/Response data transfer objects
- Input validation and serialization
- Presentation layer contracts

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Template
Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class PredictionStoreRequest(BaseModel):
    """
    Prediction Store Request DTO
    
    PRESENTATION MODEL: Input for storing predictions
    """
    
    symbol: str = Field(..., description="Stock symbol", min_length=1, max_length=10)
    timeframe: str = Field(..., description="Prediction timeframe")
    predicted_return: float = Field(..., description="Predicted return percentage")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or not v.strip():
            raise ValueError("Symbol cannot be empty")
        return v.upper().strip()
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        valid_timeframes = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']
        if v.lower() not in valid_timeframes:
            raise ValueError(f"Invalid timeframe. Must be one of: {valid_timeframes}")
        return v.lower()
    
    @validator('predicted_return')
    def validate_predicted_return(cls, v):
        if abs(v) > 1000:  # ±1000% seems like reasonable bounds
            raise ValueError("Predicted return out of realistic bounds (±1000%)")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "timeframe": "weekly",
                "predicted_return": 8.5
            }
        }


class PredictionListRequest(BaseModel):
    """
    Prediction List Request DTO
    
    PRESENTATION MODEL: Input for storing multiple predictions
    """
    
    predictions: List[PredictionStoreRequest] = Field(..., description="List of predictions to store")
    
    @validator('predictions')
    def validate_predictions_not_empty(cls, v):
        if not v:
            raise ValueError("Predictions list cannot be empty")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "predictions": [
                    {
                        "symbol": "AAPL",
                        "timeframe": "weekly",
                        "predicted_return": 8.5
                    },
                    {
                        "symbol": "GOOGL",
                        "timeframe": "monthly",
                        "predicted_return": 12.3
                    }
                ]
            }
        }


class PerformanceComparisonRequest(BaseModel):
    """
    Performance Comparison Request DTO
    
    PRESENTATION MODEL: Input for performance comparison queries
    """
    
    timeframe: str = Field(..., description="Timeframe to analyze")
    days_back: int = Field(30, description="How many days back to analyze", ge=1, le=365)
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        valid_timeframes = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'all']
        if v.lower() not in valid_timeframes:
            raise ValueError(f"Invalid timeframe. Must be one of: {valid_timeframes}")
        return v.lower()
    
    class Config:
        schema_extra = {
            "example": {
                "timeframe": "weekly",
                "days_back": 30
            }
        }


class EvaluationRequest(BaseModel):
    """
    Evaluation Request DTO
    
    PRESENTATION MODEL: Input for prediction evaluation
    """
    
    days_old: int = Field(1, description="Minimum age of predictions to evaluate", ge=1, le=30)
    
    class Config:
        schema_extra = {
            "example": {
                "days_old": 1
            }
        }


class StoreResponse(BaseModel):
    """
    Store Response DTO
    
    PRESENTATION MODEL: Output for prediction storage
    """
    
    success: bool = Field(..., description="Operation success status")
    stored_count: int = Field(0, description="Number of predictions stored")
    failed_count: int = Field(0, description="Number of predictions that failed to store")
    stored_predictions: List[Dict[str, Any]] = Field(default_factory=list, description="Successfully stored predictions")
    failed_predictions: Optional[List[Dict[str, Any]]] = Field(None, description="Failed predictions with error details")
    partial_success: Optional[bool] = Field(None, description="Whether operation was partially successful")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if failed")
    timestamp: str = Field(..., description="Response timestamp")
    controller_info: Optional[Dict[str, Any]] = Field(None, description="Controller metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "stored_count": 2,
                "failed_count": 0,
                "stored_predictions": [
                    {
                        "prediction_id": "pred_123",
                        "symbol": "AAPL",
                        "timeframe": "weekly",
                        "predicted_return": 8.5,
                        "status": "pending"
                    }
                ],
                "timestamp": "2025-08-25T10:30:15"
            }
        }


class PerformanceComparisonResponse(BaseModel):
    """
    Performance Comparison Response DTO
    
    PRESENTATION MODEL: Output for SOLL-IST comparison
    """
    
    success: bool = Field(..., description="Request success status")
    timeframe: str = Field(..., description="Analyzed timeframe")
    days_analyzed: int = Field(..., description="Number of days analyzed")
    comparison_data: List[Dict[str, Any]] = Field(default_factory=list, description="SOLL-IST comparison data")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary statistics")
    data_source: str = Field(..., description="Data source used")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if failed")
    timestamp: str = Field(..., description="Response timestamp")
    controller_info: Optional[Dict[str, Any]] = Field(None, description="Controller metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "timeframe": "weekly",
                "days_analyzed": 30,
                "comparison_data": [
                    {
                        "symbol": "AAPL",
                        "soll_return": 8.5,
                        "ist_return": 9.2,
                        "difference": 0.7,
                        "prediction_date": "2025-08-20T10:00:00",
                        "accuracy_percentage": 92.3
                    }
                ],
                "summary": {
                    "total_predictions": 15,
                    "avg_soll": 10.2,
                    "avg_ist": 9.8,
                    "avg_accuracy": 87.5
                },
                "data_source": "repository",
                "timestamp": "2025-08-25T10:30:15"
            }
        }


class StatisticsResponse(BaseModel):
    """
    Statistics Response DTO
    
    PRESENTATION MODEL: Output for service statistics
    """
    
    success: bool = Field(..., description="Request success status")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Service statistics")
    service_status: str = Field(..., description="Service status")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if failed")
    timestamp: str = Field(..., description="Response timestamp")
    controller_info: Optional[Dict[str, Any]] = Field(None, description="Controller metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "statistics": {
                    "total_predictions": 150,
                    "total_symbols": 20,
                    "recent_predictions_count": 45,
                    "pending_evaluations_count": 8,
                    "timeframe_performance": {
                        "weekly": {
                            "accuracy_rate": 87.5,
                            "total_predictions": 50
                        }
                    }
                },
                "service_status": "active",
                "timestamp": "2025-08-25T10:30:15"
            }
        }


class EvaluationResponse(BaseModel):
    """
    Evaluation Response DTO
    
    PRESENTATION MODEL: Output for prediction evaluation
    """
    
    success: bool = Field(..., description="Request success status")
    evaluated_count: int = Field(0, description="Number of predictions evaluated")
    failed_count: int = Field(0, description="Number of evaluations that failed")
    total_pending: int = Field(0, description="Total predictions that were pending evaluation")
    data_source: str = Field(..., description="Source of actual return data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if failed")
    timestamp: str = Field(..., description="Response timestamp")
    controller_info: Optional[Dict[str, Any]] = Field(None, description="Controller metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "evaluated_count": 8,
                "failed_count": 0,
                "total_pending": 8,
                "data_source": "unified_profit_engine",
                "timestamp": "2025-08-25T10:30:15"
            }
        }


class TrendsResponse(BaseModel):
    """
    Trends Response DTO
    
    PRESENTATION MODEL: Output for performance trends
    """
    
    success: bool = Field(..., description="Request success status")
    data: Dict[str, Any] = Field(default_factory=dict, description="Trend analysis data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if failed")
    controller_info: Optional[Dict[str, Any]] = Field(None, description="Controller metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "timeframe": "weekly",
                    "trend": "improving",
                    "current_accuracy": 89.5,
                    "average_accuracy": 87.2,
                    "data_points": 25
                }
            }
        }


class HealthResponse(BaseModel):
    """
    Health Response DTO
    
    PRESENTATION MODEL: Output for health checks
    """
    
    success: bool = Field(..., description="Health check success status")
    data: Optional[Dict[str, Any]] = Field(None, description="Health data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if failed")
    controller_info: Optional[Dict[str, Any]] = Field(None, description="Controller metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "controller": "PredictionController",
                    "status": "healthy",
                    "version": "6.0.0",
                    "capabilities": [
                        "store_predictions",
                        "get_performance_comparison",
                        "get_statistics"
                    ]
                }
            }
        }


class ErrorResponse(BaseModel):
    """
    Error Response DTO
    
    PRESENTATION MODEL: Standardized error format
    """
    
    success: bool = Field(False, description="Always False for errors")
    error: Dict[str, Any] = Field(..., description="Error details")
    controller_info: Optional[Dict[str, Any]] = Field(None, description="Controller metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "message": "Validation failed",
                    "code": "VALIDATION_ERROR",
                    "timestamp": "2025-08-25T10:30:15"
                }
            }
        }