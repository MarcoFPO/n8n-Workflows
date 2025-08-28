#!/usr/bin/env python3
"""
Prediction DTOs (Data Transfer Objects)

Autor: Claude Code - API Contract Designer
Datum: 26. August 2025
Clean Architecture v6.0.0 - Presentation Layer
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator
from enum import Enum


class PredictionHorizonDTO(str, Enum):
    """Prediction Horizon DTO"""
    INTRADAY = "intraday"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"
    EXTENDED = "extended"


class MLEngineTypeDTO(str, Enum):
    """ML Engine Type DTO"""
    SIMPLE_LSTM = "simple_lstm"
    MULTI_HORIZON_LSTM = "multi_horizon_lstm"
    SENTIMENT_XGBOOST = "sentiment_xgboost"
    FUNDAMENTAL_XGBOOST = "fundamental_xgboost"
    ENSEMBLE_MANAGER = "ensemble_manager"


class GeneratePredictionRequestDTO(BaseModel):
    """Request DTO for single prediction generation"""
    
    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)", min_length=1, max_length=10)
    engine_type: MLEngineTypeDTO = Field(..., description="ML engine type to use")
    horizon: PredictionHorizonDTO = Field(..., description="Prediction time horizon")
    include_risk_metrics: bool = Field(default=True, description="Include risk assessment metrics")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or not v.strip():
            raise ValueError('Symbol cannot be empty')
        
        # Basic symbol validation
        clean_symbol = v.strip().upper()
        if not clean_symbol.isalnum():
            raise ValueError('Symbol must be alphanumeric')
        
        return clean_symbol
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "engine_type": "multi_horizon_lstm",
                "horizon": "short_term",
                "include_risk_metrics": True
            }
        }


class PredictionMetricsDTO(BaseModel):
    """Prediction Metrics DTO"""
    
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence (0-1)")
    confidence_level: str = Field(..., description="Confidence level (very_low, low, medium, high, very_high)")
    volatility_estimate: Optional[float] = Field(None, ge=0.0, description="Volatility estimate")
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Risk score (0-1)")
    accuracy_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Historical accuracy")


class GeneratePredictionResponseDTO(BaseModel):
    """Response DTO for single prediction generation"""
    
    prediction_id: UUID = Field(..., description="Unique prediction identifier")
    symbol: str = Field(..., description="Stock symbol")
    predicted_price: float = Field(..., gt=0, description="Predicted stock price")
    current_price: Optional[float] = Field(None, gt=0, description="Current stock price")
    price_change: Optional[float] = Field(None, description="Absolute price change")
    price_change_percent: Optional[float] = Field(None, description="Percentage price change")
    recommendation: str = Field(..., description="Investment recommendation")
    target_date: datetime = Field(..., description="Prediction target date")
    engine_used: str = Field(..., description="ML engine used for prediction")
    is_actionable: bool = Field(..., description="Whether prediction is actionable for trading")
    metrics: Optional[PredictionMetricsDTO] = Field(None, description="Prediction quality metrics")
    created_at: datetime = Field(..., description="Prediction creation timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "prediction_id": "123e4567-e89b-12d3-a456-426614174000",
                "symbol": "AAPL",
                "predicted_price": 182.50,
                "current_price": 175.00,
                "price_change": 7.50,
                "price_change_percent": 4.29,
                "recommendation": "BUY",
                "target_date": "2025-09-02T12:00:00Z",
                "engine_used": "multi_horizon_lstm",
                "is_actionable": True,
                "metrics": {
                    "confidence_score": 0.85,
                    "confidence_level": "high",
                    "volatility_estimate": 0.15,
                    "risk_score": 0.3
                },
                "created_at": "2025-08-26T12:00:00Z"
            }
        }


class GenerateEnsemblePredictionRequestDTO(BaseModel):
    """Request DTO for ensemble prediction generation"""
    
    symbol: str = Field(..., description="Stock symbol", min_length=1, max_length=10)
    engine_types: List[MLEngineTypeDTO] = Field(..., description="List of ML engines to use", min_items=2, max_items=5)
    horizon: PredictionHorizonDTO = Field(..., description="Prediction time horizon")
    include_individual_predictions: bool = Field(default=True, description="Include individual prediction details")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or not v.strip():
            raise ValueError('Symbol cannot be empty')
        return v.strip().upper()
    
    @validator('engine_types')
    def validate_engine_types(cls, v):
        if len(set(v)) != len(v):
            raise ValueError('Duplicate engine types not allowed')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "engine_types": ["simple_lstm", "multi_horizon_lstm", "sentiment_xgboost"],
                "horizon": "medium_term",
                "include_individual_predictions": True
            }
        }


class IndividualPredictionDTO(BaseModel):
    """Individual prediction within ensemble"""
    
    engine_type: str = Field(..., description="ML engine type used")
    predicted_price: float = Field(..., gt=0, description="Predicted price")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight in ensemble")


class GenerateEnsemblePredictionResponseDTO(BaseModel):
    """Response DTO for ensemble prediction generation"""
    
    ensemble_id: UUID = Field(..., description="Unique ensemble identifier")
    symbol: str = Field(..., description="Stock symbol")
    ensemble_prediction: GeneratePredictionResponseDTO = Field(..., description="Final ensemble prediction")
    individual_predictions: List[IndividualPredictionDTO] = Field(default_factory=list, description="Individual engine predictions")
    consensus_recommendation: str = Field(..., description="Consensus investment recommendation")
    ensemble_confidence: float = Field(..., ge=0.0, le=1.0, description="Ensemble prediction confidence")
    weights: Dict[str, float] = Field(default_factory=dict, description="Engine weights in ensemble")
    created_at: datetime = Field(..., description="Ensemble creation timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "ensemble_id": "456e7890-e89b-12d3-a456-426614174001",
                "symbol": "AAPL",
                "ensemble_prediction": {
                    "prediction_id": "789e0123-e89b-12d3-a456-426614174002",
                    "symbol": "AAPL",
                    "predicted_price": 185.75,
                    "current_price": 175.00,
                    "price_change": 10.75,
                    "price_change_percent": 6.14,
                    "recommendation": "BUY",
                    "target_date": "2025-09-26T12:00:00Z",
                    "engine_used": "ensemble",
                    "is_actionable": True
                },
                "consensus_recommendation": "BUY",
                "ensemble_confidence": 0.87,
                "weights": {
                    "simple_lstm": 0.3,
                    "multi_horizon_lstm": 0.5,
                    "sentiment_xgboost": 0.2
                }
            }
        }


class BatchPredictionRequestDTO(BaseModel):
    """Request DTO for batch prediction generation"""
    
    symbols: List[str] = Field(..., description="List of stock symbols", min_items=1, max_items=20)
    engine_types: List[MLEngineTypeDTO] = Field(..., description="ML engines to use", min_items=1)
    horizon: PredictionHorizonDTO = Field(..., description="Prediction time horizon")
    include_risk_metrics: bool = Field(default=True, description="Include risk assessment")
    
    @validator('symbols')
    def validate_symbols(cls, v):
        # Clean and validate symbols
        clean_symbols = []
        for symbol in v:
            if not symbol or not symbol.strip():
                continue
            clean_symbol = symbol.strip().upper()
            if clean_symbol.isalnum() and 1 <= len(clean_symbol) <= 5:
                clean_symbols.append(clean_symbol)
        
        if not clean_symbols:
            raise ValueError('No valid symbols provided')
        
        # Remove duplicates while preserving order
        seen = set()
        unique_symbols = []
        for symbol in clean_symbols:
            if symbol not in seen:
                seen.add(symbol)
                unique_symbols.append(symbol)
        
        return unique_symbols
    
    class Config:
        schema_extra = {
            "example": {
                "symbols": ["AAPL", "GOOGL", "MSFT", "TSLA"],
                "engine_types": ["multi_horizon_lstm", "sentiment_xgboost"],
                "horizon": "short_term",
                "include_risk_metrics": True
            }
        }


class BatchPredictionItemDTO(BaseModel):
    """Single item in batch prediction response"""
    
    symbol: str = Field(..., description="Stock symbol")
    predictions: List[GeneratePredictionResponseDTO] = Field(default_factory=list, description="Predictions from different engines")
    best_prediction: Optional[GeneratePredictionResponseDTO] = Field(None, description="Best prediction based on confidence")
    consensus_recommendation: Optional[str] = Field(None, description="Consensus recommendation")


class BatchPredictionResponseDTO(BaseModel):
    """Response DTO for batch prediction generation"""
    
    total_requested: int = Field(..., ge=0, description="Total symbols requested")
    predictions_generated: int = Field(..., ge=0, description="Successful predictions generated")
    failed_symbols: List[str] = Field(default_factory=list, description="Symbols that failed prediction")
    results: List[BatchPredictionItemDTO] = Field(default_factory=list, description="Prediction results per symbol")
    horizon: PredictionHorizonDTO = Field(..., description="Prediction horizon used")
    engines_used: List[str] = Field(default_factory=list, description="ML engines used")
    processing_time_seconds: Optional[float] = Field(None, ge=0, description="Total processing time")
    created_at: datetime = Field(..., description="Batch creation timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "total_requested": 4,
                "predictions_generated": 8,
                "failed_symbols": [],
                "results": [
                    {
                        "symbol": "AAPL",
                        "predictions": [],
                        "best_prediction": None,
                        "consensus_recommendation": "BUY"
                    }
                ],
                "horizon": "short_term",
                "engines_used": ["multi_horizon_lstm", "sentiment_xgboost"],
                "processing_time_seconds": 2.45,
                "created_at": "2025-08-26T12:00:00Z"
            }
        }


class PredictionHistoryRequestDTO(BaseModel):
    """Request DTO for prediction history"""
    
    symbol: Optional[str] = Field(None, description="Filter by symbol", max_length=10)
    engine_type: Optional[MLEngineTypeDTO] = Field(None, description="Filter by engine type")
    horizon: Optional[PredictionHorizonDTO] = Field(None, description="Filter by horizon")
    limit: int = Field(default=50, ge=1, le=200, description="Maximum results to return")
    hours_ago: int = Field(default=24, ge=1, le=8760, description="Look back period in hours")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if v is None:
            return v
        if not v.strip():
            raise ValueError('Symbol cannot be empty string')
        return v.strip().upper()


class PredictionHistoryResponseDTO(BaseModel):
    """Response DTO for prediction history"""
    
    total_found: int = Field(..., ge=0, description="Total predictions found")
    predictions: List[GeneratePredictionResponseDTO] = Field(default_factory=list, description="Historical predictions")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")
    retrieved_at: datetime = Field(..., description="History retrieval timestamp")