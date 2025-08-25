#!/usr/bin/env python3
"""
ML Analytics Presentation Models - Clean Architecture v6.0.0
Request/Response DTOs for Machine Learning Operations

PRESENTATION LAYER - DATA TRANSFER OBJECTS:
- Pydantic models for request/response validation
- HTTP-specific data structures
- Serialization/deserialization for API layer
- Input validation and documentation

DESIGN PATTERNS:
- Data Transfer Object Pattern: Separates API models from domain models
- Validation Pattern: Pydantic validation for all inputs
- Documentation Pattern: OpenAPI schema generation

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

from pydantic import BaseModel, Field, validator, root_validator


# =============================================================================
# BASE RESPONSE MODELS
# =============================================================================

class SuccessResponseDTO(BaseModel):
    """Base success response DTO"""
    success: bool = True
    data: Optional[Dict[str, Any]] = None
    message: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ErrorResponseDTO(BaseModel):
    """Base error response DTO"""
    success: bool = False
    error: Dict[str, Any] = Field(...)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# =============================================================================
# MODEL TRAINING REQUEST/RESPONSE MODELS
# =============================================================================

class TrainModelRequestDTO(BaseModel):
    """Request DTO for model training"""
    model_type: str = Field(..., description="Type of ML model to train",
                            regex="^(lstm_basic|lstm_multi_horizon|xgboost_sentiment|xgboost_fundamental|lightgbm_meta|ensemble_multi_horizon|risk_management|esg_analytics|market_intelligence|quantum_enhanced|portfolio_optimizer|correlation_engine|microstructure_engine|options_pricing|derivatives_engine|streaming_analytics)$")
    symbol: str = Field(..., description="Stock symbol for training", min_length=1, max_length=10)
    prediction_horizon: str = Field(default="short_term", description="Prediction horizon",
                                   regex="^(intraday|short_term|medium_term|long_term|multi_horizon)$")
    training_window_days: int = Field(default=252, description="Training data window in days", ge=30, le=2000)
    hyperparameters: Optional[Dict[str, Any]] = Field(default=None, description="Model hyperparameters")
    feature_set: Optional[List[str]] = Field(default=None, description="Features to use for training")
    force_retrain: bool = Field(default=False, description="Force retrain even if model is not outdated")
    background_training: bool = Field(default=True, description="Run training in background")
    
    class Config:
        schema_extra = {
            "example": {
                "model_type": "lstm_basic",
                "symbol": "AAPL",
                "prediction_horizon": "short_term",
                "training_window_days": 252,
                "hyperparameters": {"learning_rate": 0.001, "epochs": 100},
                "feature_set": ["close", "volume", "sma_20", "rsi"],
                "force_retrain": False,
                "background_training": True
            }
        }


class ModelEvaluationRequestDTO(BaseModel):
    """Request DTO for model evaluation"""
    model_id: str = Field(..., description="Model identifier to evaluate")
    evaluation_period_days: int = Field(default=30, description="Evaluation period in days", ge=1, le=365)
    include_risk_metrics: bool = Field(default=True, description="Include risk metrics in evaluation")
    comparison_models: Optional[List[str]] = Field(default=None, description="Models to compare against")
    
    class Config:
        schema_extra = {
            "example": {
                "model_id": "model_123",
                "evaluation_period_days": 30,
                "include_risk_metrics": True,
                "comparison_models": ["model_456", "model_789"]
            }
        }


class RetrainModelsRequestDTO(BaseModel):
    """Request DTO for batch model retraining"""
    max_age_days: int = Field(default=30, description="Maximum model age in days", ge=1, le=365)
    model_types: Optional[List[str]] = Field(default=None, description="Specific model types to retrain")
    force_retrain_poor_performers: bool = Field(default=True, description="Force retrain poor performing models")
    max_concurrent_jobs: int = Field(default=3, description="Maximum concurrent training jobs", ge=1, le=10)
    
    @validator('model_types')
    def validate_model_types(cls, v):
        if v is not None:
            valid_types = {
                "lstm_basic", "lstm_multi_horizon", "xgboost_sentiment", "xgboost_fundamental",
                "lightgbm_meta", "ensemble_multi_horizon", "risk_management", "esg_analytics",
                "market_intelligence", "quantum_enhanced", "portfolio_optimizer", "correlation_engine",
                "microstructure_engine", "options_pricing", "derivatives_engine", "streaming_analytics"
            }
            for model_type in v:
                if model_type not in valid_types:
                    raise ValueError(f"Invalid model type: {model_type}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "max_age_days": 30,
                "model_types": ["lstm_basic", "xgboost_sentiment"],
                "force_retrain_poor_performers": True,
                "max_concurrent_jobs": 3
            }
        }


# =============================================================================
# PREDICTION REQUEST/RESPONSE MODELS
# =============================================================================

class GeneratePredictionRequestDTO(BaseModel):
    """Request DTO for prediction generation"""
    symbol: str = Field(..., description="Stock symbol for prediction", min_length=1, max_length=10)
    model_type: str = Field(..., description="Type of ML model to use for prediction",
                           regex="^(lstm_basic|lstm_multi_horizon|xgboost_sentiment|xgboost_fundamental|lightgbm_meta|ensemble_multi_horizon|risk_management|esg_analytics|market_intelligence|quantum_enhanced|portfolio_optimizer|correlation_engine|microstructure_engine|options_pricing|derivatives_engine|streaming_analytics)$")
    prediction_horizon: str = Field(default="short_term", description="Prediction time horizon",
                                   regex="^(intraday|short_term|medium_term|long_term|multi_horizon)$")
    include_risk_metrics: bool = Field(default=True, description="Include risk assessment")
    use_ensemble: bool = Field(default=False, description="Use ensemble of models")
    confidence_threshold: float = Field(default=0.0, description="Minimum confidence threshold", ge=0.0, le=1.0)
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "model_type": "lstm_basic",
                "prediction_horizon": "short_term",
                "include_risk_metrics": True,
                "use_ensemble": False,
                "confidence_threshold": 0.7
            }
        }


class BatchPredictionRequestDTO(BaseModel):
    """Request DTO for batch prediction generation"""
    symbols: List[str] = Field(..., description="List of stock symbols", min_items=1, max_items=50)
    model_types: Optional[List[str]] = Field(default=None, description="Model types to use")
    prediction_horizon: str = Field(default="short_term", description="Prediction time horizon",
                                   regex="^(intraday|short_term|medium_term|long_term|multi_horizon)$")
    include_risk_metrics: bool = Field(default=True, description="Include risk assessment")
    max_concurrent_predictions: int = Field(default=5, description="Maximum concurrent predictions", ge=1, le=20)
    min_confidence_threshold: float = Field(default=0.5, description="Minimum confidence threshold", ge=0.0, le=1.0)
    
    @validator('symbols')
    def validate_symbols(cls, v):
        for symbol in v:
            if len(symbol) > 10 or len(symbol) < 1:
                raise ValueError(f"Symbol '{symbol}' length must be between 1 and 10 characters")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "symbols": ["AAPL", "GOOGL", "MSFT"],
                "model_types": ["lstm_basic", "xgboost_sentiment"],
                "prediction_horizon": "short_term",
                "include_risk_metrics": True,
                "max_concurrent_predictions": 5,
                "min_confidence_threshold": 0.5
            }
        }


class PredictionHistoryRequestDTO(BaseModel):
    """Request DTO for prediction history retrieval"""
    symbol: Optional[str] = Field(default=None, description="Filter by stock symbol", max_length=10)
    model_id: Optional[str] = Field(default=None, description="Filter by model ID")
    model_type: Optional[str] = Field(default=None, description="Filter by model type")
    prediction_horizon: Optional[str] = Field(default=None, description="Filter by prediction horizon")
    min_confidence: float = Field(default=0.0, description="Minimum confidence filter", ge=0.0, le=1.0)
    days_back: int = Field(default=30, description="Days back to search", ge=1, le=365)
    limit: int = Field(default=100, description="Maximum results", ge=1, le=1000)
    
    @root_validator
    def validate_filters(cls, values):
        filters = [values.get('symbol'), values.get('model_id'), values.get('model_type')]
        if not any(filters):
            # At least one filter should be provided for performance
            pass  # Allow general queries
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "model_type": "lstm_basic",
                "prediction_horizon": "short_term",
                "min_confidence": 0.7,
                "days_back": 30,
                "limit": 100
            }
        }


# =============================================================================
# RISK ASSESSMENT REQUEST/RESPONSE MODELS
# =============================================================================

class RiskAssessmentRequestDTO(BaseModel):
    """Request DTO for risk assessment"""
    prediction_id: Optional[str] = Field(default=None, description="Prediction ID for risk assessment")
    symbol: Optional[str] = Field(default=None, description="Symbol for risk assessment", max_length=10)
    portfolio_symbols: Optional[List[str]] = Field(default=None, description="Portfolio symbols")
    portfolio_weights: Optional[List[float]] = Field(default=None, description="Portfolio weights")
    risk_horizon_days: int = Field(default=252, description="Risk calculation horizon in days", ge=30, le=1000)
    confidence_level: float = Field(default=0.95, description="VaR confidence level", ge=0.8, le=0.99)
    
    @root_validator
    def validate_risk_assessment(cls, values):
        prediction_id = values.get('prediction_id')
        symbol = values.get('symbol')
        portfolio_symbols = values.get('portfolio_symbols')
        portfolio_weights = values.get('portfolio_weights')
        
        # Must have one of: prediction_id, symbol, or portfolio
        if not any([prediction_id, symbol, portfolio_symbols]):
            raise ValueError("Must specify prediction_id, symbol, or portfolio_symbols")
        
        # Portfolio validation
        if portfolio_symbols and portfolio_weights:
            if len(portfolio_symbols) != len(portfolio_weights):
                raise ValueError("Portfolio symbols and weights must have same length")
            if abs(sum(portfolio_weights) - 1.0) > 0.01:
                raise ValueError("Portfolio weights must sum to 1.0")
        elif bool(portfolio_symbols) != bool(portfolio_weights):
            raise ValueError("Portfolio symbols and weights must be provided together")
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "risk_horizon_days": 252,
                "confidence_level": 0.95
            }
        }


# =============================================================================
# RESPONSE DATA MODELS
# =============================================================================

class PredictionDataDTO(BaseModel):
    """Prediction data DTO"""
    prediction_id: str
    symbol: str
    predicted_price: float
    confidence_score: float
    prediction_horizon: str
    high_confidence: bool
    created_at: str
    features_used: List[str] = Field(default_factory=list)


class RiskMetricsDataDTO(BaseModel):
    """Risk metrics data DTO"""
    risk_score: float
    risk_category: str
    var_95: float
    var_99: Optional[float] = None
    volatility: float
    beta: Optional[float] = None
    position_sizing_factor: float
    requires_validation: bool


class ModelInfoDTO(BaseModel):
    """Model information DTO"""
    model_id: str
    model_type: str
    model_age_days: int
    is_outdated: bool
    version: Optional[str] = None


class PerformanceMetricsDTO(BaseModel):
    """Performance metrics DTO"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    r2_score: float
    mse: Optional[float] = None
    mae: Optional[float] = None


# =============================================================================
# HEALTH CHECK MODELS
# =============================================================================

class HealthCheckResponseDTO(BaseModel):
    """Health check response DTO"""
    status: str
    service: str
    version: str
    timestamp: str
    components: Dict[str, Any] = Field(default_factory=dict)


class ServiceStatsDTO(BaseModel):
    """Service statistics DTO"""
    models_count: int = 0
    predictions_count: int = 0
    training_jobs_active: int = 0
    average_prediction_confidence: float = 0.0
    last_prediction_time: Optional[str] = None
    
    
# =============================================================================
# SPECIALIZED REQUEST MODELS
# =============================================================================

class ModelComparisonRequestDTO(BaseModel):
    """Request DTO for model comparison"""
    primary_model_id: str = Field(..., description="Primary model for comparison")
    comparison_model_ids: List[str] = Field(..., description="Models to compare against", min_items=1)
    evaluation_metrics: List[str] = Field(default=["accuracy", "precision", "recall", "f1_score"], 
                                        description="Metrics to compare")
    evaluation_period_days: int = Field(default=30, description="Evaluation period", ge=1, le=365)


class FeatureImportanceRequestDTO(BaseModel):
    """Request DTO for feature importance analysis"""
    model_id: str = Field(..., description="Model ID for feature analysis")
    top_k_features: int = Field(default=10, description="Number of top features", ge=1, le=100)
    include_negative_importance: bool = Field(default=False, description="Include negative importance scores")


class ModelDriftDetectionRequestDTO(BaseModel):
    """Request DTO for model drift detection"""
    model_id: str = Field(..., description="Model ID for drift detection")
    baseline_period_days: int = Field(default=90, description="Baseline period for comparison", ge=30, le=365)
    detection_window_days: int = Field(default=30, description="Recent window for drift detection", ge=7, le=90)
    drift_threshold: float = Field(default=0.1, description="Drift threshold", ge=0.01, le=1.0)