#!/usr/bin/env python3
"""
ML Prediction Event Types v1.0.0
Event-Typen für ML-Model-Vorhersagen und Ensemble-Integration

CLEAN ARCHITECTURE PRINCIPLES:
- Single Responsibility: Nur Event-Type Definitionen
- Open/Closed: Erweiterbar durch neue Event-Types
- Interface Segregation: Spezifische Event-Interfaces
- Dependency Inversion: Abhängig von Abstraktionen

Autor: Claude Code
Datum: 23. August 2025
Version: 1.0.0
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


class MLEventType(Enum):
    """ML-spezifische Event-Typen für Event-Bus Integration"""
    
    # Individual Model Events
    ML_INDIVIDUAL_PREDICTION_GENERATED = "ml.individual.prediction.generated"
    ML_MODEL_TRAINING_COMPLETED = "ml.model.training.completed"
    ML_MODEL_VALIDATION_COMPLETED = "ml.model.validation.completed"
    
    # Ensemble Events
    ML_ENSEMBLE_PREDICTION_COMPLETED = "ml.ensemble.prediction.completed"
    ML_ENSEMBLE_WEIGHTS_UPDATED = "ml.ensemble.weights.updated"
    
    # Storage Events
    ML_PREDICTION_STORAGE_REQUESTED = "ml.prediction.storage.requested"
    ML_PREDICTION_STORAGE_COMPLETED = "ml.prediction.storage.completed"
    ML_PREDICTION_STORAGE_FAILED = "ml.prediction.storage.failed"
    
    # Performance Events
    ML_MODEL_PERFORMANCE_EVALUATED = "ml.model.performance.evaluated"
    ML_RETRAINING_TRIGGERED = "ml.retraining.triggered"


@dataclass
class MLBaseEvent:
    """Basis-Event für alle ML-Events"""
    event_id: str
    event_type: str
    timestamp: datetime
    correlation_id: str
    source_service: str
    version: str = "1.0.0"
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow()


@dataclass
class IndividualModelPrediction:
    """Struktur für individuelle Modell-Vorhersage"""
    model_type: str  # technical, sentiment, fundamental, meta
    model_version: str
    prediction_values: List[float]
    confidence_score: float
    volatility_estimate: float
    feature_importance: Dict[str, float]
    horizon_days: int
    prediction_timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertierung zu Dictionary für JSON-Serialisierung"""
        return {
            "model_type": self.model_type,
            "model_version": self.model_version,
            "prediction_values": self.prediction_values,
            "confidence_score": self.confidence_score,
            "volatility_estimate": self.volatility_estimate,
            "feature_importance": self.feature_importance,
            "horizon_days": self.horizon_days,
            "prediction_timestamp": self.prediction_timestamp.isoformat() if self.prediction_timestamp else None
        }


@dataclass
class EnsemblePredictionData:
    """Struktur für finale Ensemble-Vorhersage"""
    profit_forecast: float
    confidence_level: float
    recommendation: str  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    risk_assessment: str  # NIEDRIG, MODERAT, HOCH, SEHR_HOCH
    ensemble_method: str
    model_weights: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertierung zu Dictionary für JSON-Serialisierung"""
        return {
            "profit_forecast": self.profit_forecast,
            "confidence_level": self.confidence_level,
            "recommendation": self.recommendation,
            "risk_assessment": self.risk_assessment,
            "ensemble_method": self.ensemble_method,
            "model_weights": self.model_weights
        }


@dataclass
class MLIndividualPredictionEvent(MLBaseEvent):
    """Event für individuelle Modell-Vorhersage"""
    symbol: str
    prediction: IndividualModelPrediction
    
    def __init__(self, symbol: str, prediction: IndividualModelPrediction, 
                 correlation_id: Optional[str] = None, source_service: str = "ml-analytics"):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type=MLEventType.ML_INDIVIDUAL_PREDICTION_GENERATED.value,
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id or str(uuid.uuid4()),
            source_service=source_service
        )
        self.symbol = symbol
        self.prediction = prediction
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertierung zu Event-Dictionary für Event-Bus"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "source_service": self.source_service,
            "version": self.version,
            "data": {
                "symbol": self.symbol,
                "prediction": self.prediction.to_dict()
            }
        }


@dataclass
class MLEnsemblePredictionEvent(MLBaseEvent):
    """Event für vollständige Ensemble-Vorhersage"""
    symbol: str
    ensemble_id: str
    individual_predictions: Dict[str, IndividualModelPrediction]
    final_prediction: EnsemblePredictionData
    forecast_period_days: int
    target_date: datetime
    
    def __init__(self, symbol: str, individual_predictions: Dict[str, IndividualModelPrediction],
                 final_prediction: EnsemblePredictionData, forecast_period_days: int, 
                 target_date: datetime, correlation_id: Optional[str] = None, 
                 source_service: str = "ml-analytics"):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type=MLEventType.ML_ENSEMBLE_PREDICTION_COMPLETED.value,
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id or str(uuid.uuid4()),
            source_service=source_service
        )
        self.symbol = symbol
        self.ensemble_id = str(uuid.uuid4())
        self.individual_predictions = individual_predictions
        self.final_prediction = final_prediction
        self.forecast_period_days = forecast_period_days
        self.target_date = target_date
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertierung zu Event-Dictionary für Event-Bus"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "source_service": self.source_service,
            "version": self.version,
            "data": {
                "symbol": self.symbol,
                "ensemble_id": self.ensemble_id,
                "individual_predictions": {
                    k: v.to_dict() for k, v in self.individual_predictions.items()
                },
                "final_prediction": self.final_prediction.to_dict(),
                "forecast_period_days": self.forecast_period_days,
                "target_date": self.target_date.isoformat()
            }
        }


@dataclass
class MLPredictionStorageRequestEvent(MLBaseEvent):
    """Event für Speicherungsanfrage von ML-Vorhersagen"""
    prediction_data: Dict[str, Any]
    
    def __init__(self, prediction_data: Dict[str, Any], 
                 correlation_id: Optional[str] = None, 
                 source_service: str = "ml-analytics"):
        super().__init__(
            event_id=str(uuid.uuid4()),
            event_type=MLEventType.ML_PREDICTION_STORAGE_REQUESTED.value,
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id or str(uuid.uuid4()),
            source_service=source_service
        )
        self.prediction_data = prediction_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertierung zu Event-Dictionary für Event-Bus"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "source_service": self.source_service,
            "version": self.version,
            "data": {
                "prediction_data": self.prediction_data
            }
        }


class MLEventFactory:
    """Factory für ML-Event Erstellung (Factory Pattern)"""
    
    @staticmethod
    def create_individual_prediction_event(symbol: str, prediction: IndividualModelPrediction, 
                                         correlation_id: Optional[str] = None) -> MLIndividualPredictionEvent:
        """Erstellt Individual-Prediction Event"""
        return MLIndividualPredictionEvent(
            symbol=symbol,
            prediction=prediction,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_ensemble_prediction_event(symbol: str, 
                                       individual_predictions: Dict[str, IndividualModelPrediction],
                                       final_prediction: EnsemblePredictionData,
                                       forecast_period_days: int,
                                       target_date: datetime,
                                       correlation_id: Optional[str] = None) -> MLEnsemblePredictionEvent:
        """Erstellt Ensemble-Prediction Event"""
        return MLEnsemblePredictionEvent(
            symbol=symbol,
            individual_predictions=individual_predictions,
            final_prediction=final_prediction,
            forecast_period_days=forecast_period_days,
            target_date=target_date,
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_storage_request_event(prediction_data: Dict[str, Any], 
                                   correlation_id: Optional[str] = None) -> MLPredictionStorageRequestEvent:
        """Erstellt Storage-Request Event"""
        return MLPredictionStorageRequestEvent(
            prediction_data=prediction_data,
            correlation_id=correlation_id
        )