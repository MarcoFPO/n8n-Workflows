#!/usr/bin/env python3
"""
Presentation Layer - Pydantic Models
Unified Profit Engine Enhanced v6.0 - Clean Architecture

PRESENTATION MODELS:
- Request/Response DTOs
- Input Validation
- API Documentation Support
- Type Safety

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Principles
Autor: Claude Code - Architecture Refactoring Specialist
Datum: 24. August 2025
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Optional
from datetime import date, datetime


# =============================================================================
# REQUEST MODELS
# =============================================================================

class MultiHorizonPredictionRequest(BaseModel):
    """Request model für Multi-Horizon Prediction Generation"""
    
    symbols: List[str] = Field(
        ..., 
        description="List of stock symbols (e.g., ['AAPL', 'GOOGL', 'MSFT'])",
        min_items=1,
        max_items=50,
        example=["AAPL", "GOOGL", "MSFT"]
    )
    
    prediction_date: Optional[date] = Field(
        None,
        description="Target date for predictions (defaults to today)",
        example="2025-08-24"
    )
    
    options: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional options for prediction generation",
        example={"use_ml_ensemble": True, "confidence_threshold": 0.7}
    )
    
    @validator('symbols')
    def validate_symbols(cls, v):
        """Validate symbol format"""
        if not v:
            raise ValueError("At least one symbol is required")
        
        for symbol in v:
            if not symbol or not symbol.strip():
                raise ValueError("Empty symbol is not allowed")
            if len(symbol) > 10:
                raise ValueError(f"Symbol {symbol} too long (max 10 characters)")
        
        return [s.upper().strip() for s in v]
    
    class Config:
        schema_extra = {
            "example": {
                "symbols": ["AAPL", "GOOGL", "MSFT"],
                "prediction_date": "2025-08-24",
                "options": {
                    "use_ml_ensemble": True,
                    "confidence_threshold": 0.7
                }
            }
        }


class ISTCalculationRequest(BaseModel):
    """Request model für IST Performance Calculation"""
    
    symbols: List[str] = Field(
        ...,
        description="List of stock symbols for IST calculation",
        min_items=1,
        max_items=50,
        example=["AAPL", "GOOGL", "MSFT"]
    )
    
    calculation_date: Optional[date] = Field(
        None,
        description="Date for IST calculation (defaults to today)",
        example="2025-08-24"
    )
    
    @validator('symbols')
    def validate_symbols(cls, v):
        """Validate symbol format"""
        return [s.upper().strip() for s in v if s.strip()]
    
    class Config:
        schema_extra = {
            "example": {
                "symbols": ["AAPL", "GOOGL", "MSFT"],
                "calculation_date": "2025-08-24"
            }
        }


class PerformanceAnalysisRequest(BaseModel):
    """Request model für Performance Analysis"""
    
    symbol: Optional[str] = Field(
        None,
        description="Filter by specific symbol",
        example="AAPL"
    )
    
    horizon: Optional[str] = Field(
        None,
        description="Filter by prediction horizon (1W, 1M, 3M, 12M)",
        example="1M"
    )
    
    start_date: Optional[date] = Field(
        None,
        description="Start date for analysis period",
        example="2025-07-01"
    )
    
    end_date: Optional[date] = Field(
        None,
        description="End date for analysis period", 
        example="2025-08-24"
    )
    
    limit: Optional[int] = Field(
        100,
        description="Maximum number of records to return",
        ge=1,
        le=1000
    )
    
    @validator('horizon')
    def validate_horizon(cls, v):
        """Validate horizon format"""
        if v and v not in ["1W", "1M", "3M", "12M"]:
            raise ValueError("Horizon must be one of: 1W, 1M, 3M, 12M")
        return v
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate symbol format"""
        if v:
            return v.upper().strip()
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "horizon": "1M",
                "start_date": "2025-07-01",
                "end_date": "2025-08-24",
                "limit": 100
            }
        }


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class MultiHorizonPredictionResponse(BaseModel):
    """Response model für Multi-Horizon Predictions"""
    
    success: bool = Field(
        ...,
        description="Whether the operation was successful"
    )
    
    predictions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Generated predictions data"
    )
    
    processed_count: int = Field(
        0,
        description="Number of symbols successfully processed"
    )
    
    processing_time: float = Field(
        0.0,
        description="Processing time in seconds"
    )
    
    error: Optional[str] = Field(
        None,
        description="Error message if operation failed"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the operation"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "predictions": [
                    {
                        "symbol": "AAPL",
                        "company_name": "Apple Inc.",
                        "market_region": "US",
                        "datum": "2025-08-24",
                        "soll_gewinn_1w": 150.25,
                        "soll_gewinn_1m": 152.75,
                        "soll_gewinn_3m": 158.30,
                        "soll_gewinn_12m": 175.50,
                        "created_at": "2025-08-24T10:30:00"
                    }
                ],
                "processed_count": 1,
                "processing_time": 2.34,
                "metadata": {
                    "service": "unified-profit-engine-enhanced",
                    "version": "6.0"
                }
            }
        }


class ISTCalculationResponse(BaseModel):
    """Response model für IST Performance Calculations"""
    
    success: bool = Field(
        ...,
        description="Whether the operation was successful"
    )
    
    ist_profits: Dict[str, float] = Field(
        default_factory=dict,
        description="Calculated IST profits by symbol"
    )
    
    calculated_count: int = Field(
        0,
        description="Number of symbols successfully calculated"
    )
    
    processing_time: float = Field(
        0.0,
        description="Processing time in seconds"
    )
    
    error: Optional[str] = Field(
        None,
        description="Error message if operation failed"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the operation"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "ist_profits": {
                    "AAPL": 148.75,
                    "GOOGL": 2651.30,
                    "MSFT": 412.45
                },
                "calculated_count": 3,
                "processing_time": 1.89,
                "metadata": {
                    "service": "unified-profit-engine-enhanced",
                    "version": "6.0"
                }
            }
        }


class PerformanceAnalysisResponse(BaseModel):
    """Response model für Performance Analysis"""
    
    success: bool = Field(
        ...,
        description="Whether the operation was successful"
    )
    
    analysis_data: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Performance analysis data"
    )
    
    record_count: int = Field(
        0,
        description="Number of records returned"
    )
    
    processing_time: float = Field(
        0.0,
        description="Processing time in seconds"
    )
    
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Applied filters for the analysis"
    )
    
    error: Optional[str] = Field(
        None,
        description="Error message if operation failed"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata about the operation"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "analysis_data": [
                    {
                        "symbol": "AAPL",
                        "tracking_date": "2025-08-24",
                        "ist_gewinn": 148.75,
                        "soll_1w": 150.25,
                        "soll_1m": 152.75,
                        "diff_1w": -1.50,
                        "diff_1m": -4.00,
                        "accuracy_1w": 0.99,
                        "accuracy_1m": 0.97,
                        "best_horizon": "1W",
                        "overall_accuracy": 0.95
                    }
                ],
                "record_count": 1,
                "processing_time": 0.45,
                "filters": {
                    "symbol": "AAPL",
                    "horizon": "1M"
                }
            }
        }


class HealthCheckResponse(BaseModel):
    """Response model für Health Check"""
    
    healthy: bool = Field(
        ...,
        description="Overall service health status"
    )
    
    service: str = Field(
        "unified-profit-engine-enhanced",
        description="Service name"
    )
    
    version: str = Field(
        "6.0",
        description="Service version"
    )
    
    uptime_seconds: Optional[int] = Field(
        None,
        description="Service uptime in seconds"
    )
    
    timestamp: str = Field(
        ...,
        description="Health check timestamp"
    )
    
    error: Optional[str] = Field(
        None,
        description="Error message if unhealthy"
    )
    
    dependencies: Optional[Dict[str, Dict[str, str]]] = Field(
        None,
        description="Status of service dependencies"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "healthy": True,
                "service": "unified-profit-engine-enhanced",
                "version": "6.0",
                "uptime_seconds": 3600,
                "timestamp": "2025-08-24T10:30:00",
                "dependencies": {
                    "database": {"status": "healthy", "description": "PostgreSQL connection OK"},
                    "redis": {"status": "healthy", "description": "Redis connection OK"}
                }
            }
        }


class ServiceMetricsResponse(BaseModel):
    """Response model für Service Metrics"""
    
    service: str = Field(
        "unified-profit-engine-enhanced",
        description="Service name"
    )
    
    version: str = Field(
        "6.0",
        description="Service version"
    )
    
    uptime_seconds: int = Field(
        ...,
        description="Service uptime in seconds"
    )
    
    request_count: int = Field(
        ...,
        description="Total number of requests processed"
    )
    
    error_count: int = Field(
        ...,
        description="Total number of errors"
    )
    
    success_rate: float = Field(
        ...,
        description="Success rate percentage"
    )
    
    timestamp: str = Field(
        ...,
        description="Metrics collection timestamp"
    )
    
    additional_metrics: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional service-specific metrics"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "service": "unified-profit-engine-enhanced",
                "version": "6.0",
                "uptime_seconds": 3600,
                "request_count": 1250,
                "error_count": 15,
                "success_rate": 98.8,
                "timestamp": "2025-08-24T10:30:00",
                "additional_metrics": {
                    "startup_time": "2025-08-24T09:30:00",
                    "error_rate_percent": 1.2
                }
            }
        }