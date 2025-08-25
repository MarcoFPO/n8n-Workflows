#!/usr/bin/env python3
"""
Prediction Tracking Service Exception Definitions - Clean Architecture v6.1.0
Domain-spezifische Exceptions für Prediction Tracking Service

DOMAIN LAYER - EXCEPTIONS:
- Prediction-spezifische Fehlerklassen
- Tracking und Monitoring Validierungen
- Inheritance vom Shared Error Framework
- Structured Error Context für Prediction Operations

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.1.0
"""

import sys
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import shared error framework
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from error_handling_framework_v1_0_0_20250825 import (
    BaseServiceError,
    ValidationError,
    NotFoundError,
    BusinessLogicError,
    DatabaseError
)


# =============================================================================
# PREDICTION TRACKING EXCEPTIONS
# =============================================================================

class PredictionNotFoundError(NotFoundError):
    """Prediction nicht gefunden"""
    
    def __init__(self, prediction_id: str, symbol: str = None, **kwargs):
        super().__init__(
            message=f"Prediction {prediction_id} not found" + (f" for symbol {symbol}" if symbol else ""),
            resource_type="prediction",
            resource_id=prediction_id,
            error_code="PREDICTION_NOT_FOUND",
            context={
                "prediction_id": prediction_id,
                "symbol": symbol
            },
            **kwargs
        )


class PredictionValidationError(ValidationError):
    """Prediction Validierungsfehler"""
    
    def __init__(
        self, 
        message: str, 
        prediction_id: str = None,
        validation_fields: List[str] = None, 
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="PREDICTION_VALIDATION_ERROR",
            context={
                "prediction_id": prediction_id,
                "validation_fields": validation_fields
            },
            **kwargs
        )


class PredictionExpiredError(BusinessLogicError):
    """Prediction ist abgelaufen"""
    
    def __init__(
        self, 
        prediction_id: str,
        expiry_date: datetime = None,
        current_date: datetime = None,
        **kwargs
    ):
        super().__init__(
            message=f"Prediction {prediction_id} has expired",
            error_code="PREDICTION_EXPIRED_ERROR",
            context={
                "prediction_id": prediction_id,
                "expiry_date": expiry_date.isoformat() if expiry_date else None,
                "current_date": current_date.isoformat() if current_date else None
            },
            **kwargs
        )


class PredictionAccuracyError(BusinessLogicError):
    """Prediction Genauigkeitsfehler"""
    
    def __init__(
        self, 
        message: str,
        prediction_id: str = None,
        expected_accuracy: float = None,
        actual_accuracy: float = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="PREDICTION_ACCURACY_ERROR",
            context={
                "prediction_id": prediction_id,
                "expected_accuracy": expected_accuracy,
                "actual_accuracy": actual_accuracy
            },
            **kwargs
        )


class PredictionTrackingError(BaseServiceError):
    """Allgemeiner Prediction Tracking Fehler"""
    
    def __init__(
        self, 
        message: str,
        tracking_id: str = None,
        operation: str = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="PREDICTION_TRACKING_ERROR",
            context={
                "tracking_id": tracking_id,
                "operation": operation
            },
            **kwargs
        )


# =============================================================================
# SYMBOL TRACKING EXCEPTIONS
# =============================================================================

class SymbolNotSupportedError(ValidationError):
    """Symbol wird nicht unterstützt"""
    
    def __init__(
        self, 
        symbol: str,
        supported_symbols: List[str] = None,
        **kwargs
    ):
        super().__init__(
            message=f"Symbol {symbol} is not supported for prediction tracking",
            error_code="SYMBOL_NOT_SUPPORTED_ERROR",
            context={
                "symbol": symbol,
                "supported_symbols": supported_symbols
            },
            **kwargs
        )


class SymbolDataMissingError(BusinessLogicError):
    """Symbol-Daten fehlen für Tracking"""
    
    def __init__(
        self, 
        symbol: str,
        missing_data_types: List[str] = None,
        **kwargs
    ):
        super().__init__(
            message=f"Missing data for symbol {symbol} tracking",
            error_code="SYMBOL_DATA_MISSING_ERROR",
            context={
                "symbol": symbol,
                "missing_data_types": missing_data_types
            },
            **kwargs
        )


# =============================================================================
# PERFORMANCE TRACKING EXCEPTIONS
# =============================================================================

class PerformanceTrackingError(BaseServiceError):
    """Performance Tracking Fehler"""
    
    def __init__(
        self, 
        message: str,
        metric_name: str = None,
        time_period: str = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="PERFORMANCE_TRACKING_ERROR",
            context={
                "metric_name": metric_name,
                "time_period": time_period
            },
            **kwargs
        )


class PerformanceThresholdError(BusinessLogicError):
    """Performance Schwellenwert unterschritten"""
    
    def __init__(
        self, 
        metric_name: str,
        current_value: float,
        threshold: float,
        **kwargs
    ):
        super().__init__(
            message=f"Performance metric {metric_name} below threshold: {current_value} < {threshold}",
            error_code="PERFORMANCE_THRESHOLD_ERROR",
            context={
                "metric_name": metric_name,
                "current_value": current_value,
                "threshold": threshold
            },
            **kwargs
        )


# =============================================================================
# STORAGE AND PERSISTENCE EXCEPTIONS
# =============================================================================

class PredictionStorageError(DatabaseError):
    """Prediction Storage Fehler"""
    
    def __init__(
        self, 
        message: str,
        prediction_id: str = None,
        operation: str = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            operation=operation,
            error_code="PREDICTION_STORAGE_ERROR",
            context={
                "prediction_id": prediction_id,
                "storage_operation": operation
            },
            **kwargs
        )


class PredictionArchiveError(BaseServiceError):
    """Prediction Archivierungsfehler"""
    
    def __init__(
        self, 
        message: str,
        prediction_ids: List[str] = None,
        archive_reason: str = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="PREDICTION_ARCHIVE_ERROR",
            context={
                "prediction_ids": prediction_ids,
                "archive_reason": archive_reason
            },
            **kwargs
        )


# =============================================================================
# BUSINESS RULE VALIDATION EXCEPTIONS
# =============================================================================

class PredictionDuplicateError(ValidationError):
    """Doppelte Prediction für gleiche Kriterien"""
    
    def __init__(
        self, 
        symbol: str,
        prediction_date: datetime = None,
        existing_prediction_id: str = None,
        **kwargs
    ):
        super().__init__(
            message=f"Duplicate prediction for symbol {symbol}",
            error_code="PREDICTION_DUPLICATE_ERROR",
            context={
                "symbol": symbol,
                "prediction_date": prediction_date.isoformat() if prediction_date else None,
                "existing_prediction_id": existing_prediction_id
            },
            **kwargs
        )


class PredictionTimeframeMismatchError(ValidationError):
    """Prediction Zeitraum Unstimmigkeit"""
    
    def __init__(
        self, 
        message: str,
        prediction_id: str = None,
        expected_timeframe: str = None,
        actual_timeframe: str = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="PREDICTION_TIMEFRAME_MISMATCH_ERROR",
            context={
                "prediction_id": prediction_id,
                "expected_timeframe": expected_timeframe,
                "actual_timeframe": actual_timeframe
            },
            **kwargs
        )


# =============================================================================
# EXCEPTION FACTORY
# =============================================================================

class PredictionExceptionFactory:
    """Factory für Prediction-spezifische Exceptions"""
    
    @staticmethod
    def create_prediction_error(
        error_type: str,
        message: str,
        context: Dict[str, Any] = None
    ) -> BaseServiceError:
        """Erstellt Prediction-bezogene Exception"""
        
        context = context or {}
        
        error_mapping = {
            "not_found": PredictionNotFoundError,
            "validation": PredictionValidationError,
            "expired": PredictionExpiredError,
            "accuracy": PredictionAccuracyError,
            "storage": PredictionStorageError,
            "duplicate": PredictionDuplicateError
        }
        
        exception_class = error_mapping.get(error_type, PredictionTrackingError)
        return exception_class(message, **context)
    
    @staticmethod
    def create_symbol_error(
        error_type: str,
        symbol: str,
        context: Dict[str, Any] = None
    ) -> BaseServiceError:
        """Erstellt Symbol-bezogene Exception"""
        
        context = context or {}
        context["symbol"] = symbol
        
        error_mapping = {
            "not_supported": SymbolNotSupportedError,
            "data_missing": SymbolDataMissingError
        }
        
        exception_class = error_mapping.get(error_type, SymbolNotSupportedError)
        return exception_class(symbol, **context)
    
    @staticmethod
    def create_performance_error(
        error_type: str,
        message: str,
        context: Dict[str, Any] = None
    ) -> BaseServiceError:
        """Erstellt Performance-bezogene Exception"""
        
        context = context or {}
        
        error_mapping = {
            "threshold": PerformanceThresholdError,
            "tracking": PerformanceTrackingError
        }
        
        exception_class = error_mapping.get(error_type, PerformanceTrackingError)
        return exception_class(message, **context)