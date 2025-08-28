#!/usr/bin/env python3
"""
ML Analytics Service Exception Definitions - Clean Architecture v6.1.0
Domain-spezifische Exceptions für Machine Learning Analytics Service

DOMAIN LAYER - EXCEPTIONS:
- ML-spezifische Fehlerklassen
- Geschäftslogik-Validierungen
- Inheritance vom Shared Error Framework
- Structured Error Context für ML Operations

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.1.0
"""

import sys
from typing import Dict, Any, Optional, List

# Import shared error framework
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from error_handling_framework_v1_0_0_20250825 import (
    BaseServiceError,
    ValidationError,
    NotFoundError,
    BusinessLogicError,
    ExternalServiceError
)


# =============================================================================
# ML MODEL EXCEPTIONS
# =============================================================================

class MLModelNotFoundError(NotFoundError):
    """ML Model nicht gefunden"""
    
    def __init__(self, model_id: str, model_type: str = None, **kwargs):
        super().__init__(
            message=f"ML Model {model_id} not found" + (f" of type {model_type}" if model_type else ""),
            resource_type="ml_model",
            resource_id=model_id,
            error_code="ML_MODEL_NOT_FOUND",
            context={
                "model_id": model_id,
                "model_type": model_type
            },
            **kwargs
        )


class MLModelValidationError(ValidationError):
    """ML Model Validierungsfehler"""
    
    def __init__(self, message: str, model_id: str = None, validation_rules: List[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="ML_MODEL_VALIDATION_ERROR",
            context={
                "model_id": model_id,
                "validation_rules": validation_rules
            },
            **kwargs
        )


class MLModelVersionError(BusinessLogicError):
    """ML Model Versions-Konflikt"""
    
    def __init__(self, model_id: str, current_version: str, required_version: str, **kwargs):
        super().__init__(
            message=f"Model {model_id} version conflict: current {current_version}, required {required_version}",
            error_code="ML_MODEL_VERSION_ERROR",
            context={
                "model_id": model_id,
                "current_version": current_version,
                "required_version": required_version
            },
            **kwargs
        )


# =============================================================================
# ML TRAINING EXCEPTIONS
# =============================================================================

class MLTrainingError(BaseServiceError):
    """Allgemeiner ML Training Fehler"""
    
    def __init__(
        self, 
        message: str, 
        model_type: str = None, 
        training_job_id: str = None,
        hyperparameters: Dict[str, Any] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_TRAINING_ERROR",
            context={
                "model_type": model_type,
                "training_job_id": training_job_id,
                "hyperparameters": hyperparameters
            },
            **kwargs
        )


class MLDataInsufficientError(MLTrainingError):
    """Unzureichende Trainingsdaten"""
    
    def __init__(
        self, 
        message: str = "Insufficient training data", 
        required_samples: int = None,
        available_samples: int = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_DATA_INSUFFICIENT_ERROR",
            context={
                "required_samples": required_samples,
                "available_samples": available_samples
            },
            **kwargs
        )


class MLFeatureError(MLTrainingError):
    """Feature Engineering Fehler"""
    
    def __init__(
        self, 
        message: str, 
        feature_names: List[str] = None,
        missing_features: List[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_FEATURE_ERROR",
            context={
                "feature_names": feature_names,
                "missing_features": missing_features
            },
            **kwargs
        )


class MLHyperparameterError(ValidationError):
    """Hyperparameter Validierungsfehler"""
    
    def __init__(
        self, 
        message: str, 
        parameter_name: str = None,
        parameter_value: Any = None,
        valid_range: str = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_HYPERPARAMETER_ERROR",
            context={
                "parameter_name": parameter_name,
                "parameter_value": parameter_value,
                "valid_range": valid_range
            },
            **kwargs
        )


class MLConvergenceError(MLTrainingError):
    """Model Konvergenz Fehler"""
    
    def __init__(
        self, 
        message: str = "Model failed to converge", 
        epochs_completed: int = None,
        final_loss: float = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_CONVERGENCE_ERROR",
            context={
                "epochs_completed": epochs_completed,
                "final_loss": final_loss
            },
            **kwargs
        )


# =============================================================================
# ML PREDICTION EXCEPTIONS
# =============================================================================

class MLPredictionError(BaseServiceError):
    """Allgemeiner ML Prediction Fehler"""
    
    def __init__(
        self, 
        message: str, 
        model_id: str = None,
        symbol: str = None,
        prediction_type: str = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_PREDICTION_ERROR",
            context={
                "model_id": model_id,
                "symbol": symbol,
                "prediction_type": prediction_type
            },
            **kwargs
        )


class MLModelNotReadyError(MLPredictionError):
    """Model nicht bereit für Predictions"""
    
    def __init__(self, model_id: str, model_status: str = None, **kwargs):
        super().__init__(
            message=f"Model {model_id} not ready for predictions",
            error_code="ML_MODEL_NOT_READY_ERROR",
            context={
                "model_id": model_id,
                "model_status": model_status
            },
            **kwargs
        )


class MLInputValidationError(ValidationError):
    """Input Validierung für Predictions"""
    
    def __init__(
        self, 
        message: str, 
        input_features: Dict[str, Any] = None,
        expected_features: List[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_INPUT_VALIDATION_ERROR",
            context={
                "input_features": list(input_features.keys()) if input_features else None,
                "expected_features": expected_features
            },
            **kwargs
        )


class MLConfidenceError(MLPredictionError):
    """Prediction Confidence zu niedrig"""
    
    def __init__(
        self, 
        message: str = "Prediction confidence below threshold", 
        confidence_score: float = None,
        confidence_threshold: float = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_CONFIDENCE_ERROR",
            context={
                "confidence_score": confidence_score,
                "confidence_threshold": confidence_threshold
            },
            **kwargs
        )


# =============================================================================
# ML EVALUATION EXCEPTIONS
# =============================================================================

class MLEvaluationError(BaseServiceError):
    """ML Model Evaluation Fehler"""
    
    def __init__(
        self, 
        message: str, 
        model_id: str = None,
        evaluation_metrics: List[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_EVALUATION_ERROR",
            context={
                "model_id": model_id,
                "evaluation_metrics": evaluation_metrics
            },
            **kwargs
        )


class MLPerformanceDegradationError(MLEvaluationError):
    """Model Performance Verschlechterung"""
    
    def __init__(
        self, 
        model_id: str,
        current_performance: float = None,
        baseline_performance: float = None,
        metric_name: str = None,
        **kwargs
    ):
        super().__init__(
            message=f"Model {model_id} performance degradation detected",
            error_code="ML_PERFORMANCE_DEGRADATION_ERROR",
            context={
                "model_id": model_id,
                "current_performance": current_performance,
                "baseline_performance": baseline_performance,
                "metric_name": metric_name
            },
            **kwargs
        )


# =============================================================================
# RISK ANALYSIS EXCEPTIONS
# =============================================================================

class MLRiskAnalysisError(BaseServiceError):
    """Risk Analysis Fehler"""
    
    def __init__(
        self, 
        message: str, 
        symbols: List[str] = None,
        risk_model: str = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_RISK_ANALYSIS_ERROR",
            context={
                "symbols": symbols,
                "risk_model": risk_model
            },
            **kwargs
        )


class MLPortfolioError(MLRiskAnalysisError):
    """Portfolio Analysis Fehler"""
    
    def __init__(
        self, 
        message: str, 
        portfolio_id: str = None,
        positions: Dict[str, float] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_PORTFOLIO_ERROR",
            context={
                "portfolio_id": portfolio_id,
                "positions": positions
            },
            **kwargs
        )


class MLCorrelationError(MLRiskAnalysisError):
    """Korrelations-Analyse Fehler"""
    
    def __init__(
        self, 
        message: str = "Correlation analysis failed", 
        symbols: List[str] = None,
        correlation_threshold: float = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_CORRELATION_ERROR",
            context={
                "symbols": symbols,
                "correlation_threshold": correlation_threshold
            },
            **kwargs
        )


# =============================================================================
# EXTERNAL SERVICE INTEGRATION EXCEPTIONS
# =============================================================================

class MLDataProviderError(ExternalServiceError):
    """External Data Provider Fehler"""
    
    def __init__(
        self, 
        message: str, 
        provider: str = None,
        symbol: str = None,
        data_type: str = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            service="ml_data_provider",
            error_code="ML_DATA_PROVIDER_ERROR",
            context={
                "provider": provider,
                "symbol": symbol,
                "data_type": data_type
            },
            **kwargs
        )


class MLModelStorageError(BaseServiceError):
    """Model Storage Fehler"""
    
    def __init__(
        self, 
        message: str, 
        model_id: str = None,
        storage_path: str = None,
        operation: str = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_MODEL_STORAGE_ERROR",
            context={
                "model_id": model_id,
                "storage_path": storage_path,
                "operation": operation
            },
            **kwargs
        )


# =============================================================================
# BUSINESS RULE VALIDATION EXCEPTIONS  
# =============================================================================

class MLValidationError(ValidationError):
    """Allgemeine ML Business Rule Validierung"""
    
    def __init__(self, message: str, rule_name: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="ML_VALIDATION_ERROR",
            context={"rule_name": rule_name},
            **kwargs
        )


class MLTimeHorizonError(MLValidationError):
    """Time Horizon Validierungsfehler"""
    
    def __init__(
        self, 
        message: str = "Invalid prediction time horizon", 
        time_horizon: int = None,
        max_horizon: int = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_TIME_HORIZON_ERROR",
            context={
                "time_horizon": time_horizon,
                "max_horizon": max_horizon
            },
            **kwargs
        )


class MLSymbolError(MLValidationError):
    """Symbol Validierungsfehler"""
    
    def __init__(
        self, 
        message: str, 
        symbol: str = None,
        supported_symbols: List[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="ML_SYMBOL_ERROR", 
            context={
                "symbol": symbol,
                "supported_symbols": supported_symbols
            },
            **kwargs
        )


# =============================================================================
# EXCEPTION FACTORY
# =============================================================================

class MLExceptionFactory:
    """Factory für ML-spezifische Exceptions"""
    
    @staticmethod
    def create_model_error(
        error_type: str, 
        message: str, 
        context: Dict[str, Any] = None
    ) -> BaseServiceError:
        """Erstellt Model-bezogene Exception"""
        
        context = context or {}
        
        error_mapping = {
            "not_found": MLModelNotFoundError,
            "validation": MLModelValidationError,
            "version": MLModelVersionError,
            "storage": MLModelStorageError,
            "not_ready": MLModelNotReadyError
        }
        
        exception_class = error_mapping.get(error_type, MLModelNotFoundError)
        return exception_class(message, **context)
    
    @staticmethod
    def create_training_error(
        error_type: str,
        message: str,
        context: Dict[str, Any] = None
    ) -> MLTrainingError:
        """Erstellt Training-bezogene Exception"""
        
        context = context or {}
        
        error_mapping = {
            "insufficient_data": MLDataInsufficientError,
            "feature": MLFeatureError,
            "hyperparameter": MLHyperparameterError,
            "convergence": MLConvergenceError
        }
        
        exception_class = error_mapping.get(error_type, MLTrainingError)
        return exception_class(message, **context)
    
    @staticmethod
    def create_prediction_error(
        error_type: str,
        message: str, 
        context: Dict[str, Any] = None
    ) -> MLPredictionError:
        """Erstellt Prediction-bezogene Exception"""
        
        context = context or {}
        
        error_mapping = {
            "input_validation": MLInputValidationError,
            "confidence": MLConfidenceError,
            "model_not_ready": MLModelNotReadyError
        }
        
        exception_class = error_mapping.get(error_type, MLPredictionError)
        return exception_class(message, **context)