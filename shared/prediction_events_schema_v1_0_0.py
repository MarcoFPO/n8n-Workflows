#!/usr/bin/env python3
"""
Standardisierte Event-Schema für Prediction Tracking
Clean Architecture Event-Driven Communication

STANDARDISIERT ALLE 3 ZEITSTEMPEL:
a) calculation_date - Tag der Berechnung  
b) target_date - Zeitpunkt für Eintritt der Vorhersage
c) evaluation_date - IST-Gewinn zum Zeitpunkt des Eintritts

Autor: Claude Code
Datum: 25. August 2025
Version: 1.0.0
"""

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum

logger = logging.getLogger(__name__)

# ===============================================================================
# ENUMS - Standardisierte Werte
# ===============================================================================

class HorizonType(str, Enum):
    """Standardisierte Vorhersage-Horizonte"""
    ONE_WEEK = "1W"
    ONE_MONTH = "1M"
    THREE_MONTHS = "3M"
    TWELVE_MONTHS = "12M"

class PredictionEventType(str, Enum):
    """Standardisierte Prediction Event Types"""
    PREDICTION_CREATED = "prediction.created"
    PREDICTION_UPDATED = "prediction.updated"
    PREDICTION_EVALUATED = "prediction.evaluation.completed"
    PREDICTION_EXPIRED = "prediction.expired"
    PREDICTION_FAILED = "prediction.failed"

class ModelType(str, Enum):
    """Standardisierte ML Model Types"""
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    FUNDAMENTAL = "fundamental"
    META = "meta"
    ENSEMBLE = "ensemble"

# ===============================================================================
# BASE EVENT SCHEMA
# ===============================================================================

class BaseEventSchema(BaseModel):
    """Basis Event Schema für alle Prediction Events"""
    event_type: PredictionEventType
    event_id: str = Field(default_factory=lambda: f"evt_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    correlation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    service_name: str
    service_version: str = "1.0.0"

# ===============================================================================
# PREDICTION SCHEMAS - Mit standardisierten Zeitstempeln
# ===============================================================================

class PredictionCreatedEventData(BaseModel):
    """
    Event Data für neue Vorhersage-Erstellung
    
    PFLICHT-ZEITSTEMPEL:
    - calculation_date: Wann wurde die Vorhersage berechnet
    - target_date: Für wann gilt die Vorhersage
    """
    # Identifikation
    prediction_id: str
    symbol: str
    company_name: Optional[str] = None
    
    # ZEITSTEMPEL (a & b erforderlich)
    calculation_date: datetime = Field(description="Zeitpunkt der Vorhersage-Berechnung")
    target_date: date = Field(description="Datum für welches die Vorhersage gilt")
    
    # Vorhersage-Werte
    predicted_value: Decimal = Field(description="Vorhergesagter Gewinn/Verlust")
    horizon_type: HorizonType
    horizon_days: int
    
    # Metadaten
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    model_type: ModelType = ModelType.ENSEMBLE
    model_version: str = "v1.0.0"
    calculation_method: str = "ensemble"
    
    @validator('target_date')
    def validate_target_date(cls, v, values):
        if 'calculation_date' in values and v < values['calculation_date'].date():
            raise ValueError('target_date muss nach calculation_date liegen')
        return v

class PredictionEvaluatedEventData(BaseModel):
    """
    Event Data für Vorhersage-Evaluierung
    
    ALLE 3 ZEITSTEMPEL:
    - calculation_date: Original-Berechnungszeitpunkt
    - target_date: Original-Vorhersage-Datum
    - evaluation_date: Zeitpunkt der IST-Wert Erfassung
    """
    # Identifikation
    prediction_id: str
    symbol: str
    company_name: Optional[str] = None
    
    # ALLE 3 ZEITSTEMPEL (vollständig)
    calculation_date: datetime = Field(description="Original Berechnungszeitpunkt")
    target_date: date = Field(description="Vorhersage-Zieldatum")
    evaluation_date: datetime = Field(description="Zeitpunkt der IST-Wert Erfassung")
    
    # Werte-Vergleich
    predicted_value: Decimal = Field(description="Original vorhergesagter Wert")
    actual_value: Decimal = Field(description="Tatsächlicher IST-Wert")
    performance_diff: Decimal = Field(description="Differenz (IST - SOLL)")
    performance_accuracy: Optional[Decimal] = Field(description="Genauigkeit in %")
    
    # Zusätzliche Metadaten
    horizon_type: HorizonType
    market_price: Optional[Decimal] = Field(description="Aktueller Marktpreis")
    data_source: str = Field(default="yahoo_finance")
    evaluation_method: str = Field(default="automatic")

# ===============================================================================
# COMPLETE EVENT SCHEMAS
# ===============================================================================

class PredictionCreatedEvent(BaseEventSchema):
    """Vollständiges Event für Vorhersage-Erstellung"""
    event_type: PredictionEventType = PredictionEventType.PREDICTION_CREATED
    event_data: PredictionCreatedEventData

class PredictionEvaluatedEvent(BaseEventSchema):
    """Vollständiges Event für Vorhersage-Evaluierung"""
    event_type: PredictionEventType = PredictionEventType.PREDICTION_EVALUATED
    event_data: PredictionEvaluatedEventData

# ===============================================================================
# EVENT BUILDER - Vereinfachte Event-Erstellung
# ===============================================================================

class PredictionEventBuilder:
    """Builder für standardisierte Prediction Events"""
    
    @staticmethod
    def create_prediction_created_event(
        symbol: str,
        predicted_value: Decimal,
        horizon_type: HorizonType,
        horizon_days: int,
        service_name: str,
        company_name: Optional[str] = None,
        confidence_score: Optional[Decimal] = None,
        model_type: ModelType = ModelType.ENSEMBLE,
        prediction_id: Optional[str] = None,
        calculation_date: Optional[datetime] = None,
        target_date: Optional[date] = None
    ) -> PredictionCreatedEvent:
        """
        Erstelle standardisiertes Prediction Created Event
        
        AUTOMATISCHE ZEITSTEMPEL:
        - calculation_date: JETZT (wenn nicht anders angegeben)
        - target_date: calculation_date + horizon_days
        """
        if calculation_date is None:
            calculation_date = datetime.now()
        
        if target_date is None:
            target_date = (calculation_date + timedelta(days=horizon_days)).date()
            
        if prediction_id is None:
            prediction_id = f"pred_{calculation_date.strftime('%Y%m%d_%H%M%S')}_{symbol}"
        
        return PredictionCreatedEvent(
            service_name=service_name,
            event_data=PredictionCreatedEventData(
                prediction_id=prediction_id,
                symbol=symbol,
                company_name=company_name,
                calculation_date=calculation_date,
                target_date=target_date,
                predicted_value=predicted_value,
                horizon_type=horizon_type,
                horizon_days=horizon_days,
                confidence_score=confidence_score,
                model_type=model_type
            )
        )
    
    @staticmethod
    def create_prediction_evaluated_event(
        prediction_id: str,
        symbol: str,
        calculation_date: datetime,
        target_date: date,
        predicted_value: Decimal,
        actual_value: Decimal,
        horizon_type: HorizonType,
        service_name: str,
        company_name: Optional[str] = None,
        market_price: Optional[Decimal] = None,
        evaluation_date: Optional[datetime] = None
    ) -> PredictionEvaluatedEvent:
        """
        Erstelle standardisiertes Prediction Evaluated Event
        
        ALLE 3 ZEITSTEMPEL WERDEN ERFASST:
        - calculation_date: Original Berechnungszeitpunkt (Parameter)
        - target_date: Original Zieldatum (Parameter)
        - evaluation_date: JETZT (automatisch gesetzt)
        """
        if evaluation_date is None:
            evaluation_date = datetime.now()
        
        # Berechne Performance-Metriken
        performance_diff = actual_value - predicted_value
        performance_accuracy = None
        if predicted_value != 0:
            accuracy = (1 - abs(performance_diff) / abs(predicted_value)) * 100
            performance_accuracy = max(0, accuracy)
        
        return PredictionEvaluatedEvent(
            service_name=service_name,
            event_data=PredictionEvaluatedEventData(
                prediction_id=prediction_id,
                symbol=symbol,
                company_name=company_name,
                calculation_date=calculation_date,
                target_date=target_date,
                evaluation_date=evaluation_date,
                predicted_value=predicted_value,
                actual_value=actual_value,
                performance_diff=performance_diff,
                performance_accuracy=performance_accuracy,
                horizon_type=horizon_type,
                market_price=market_price
            )
        )

# ===============================================================================
# EVENT VALIDATOR
# ===============================================================================

class PredictionEventValidator:
    """Validator für Prediction Events"""
    
    @staticmethod
    def validate_timeframe_consistency(event: PredictionCreatedEvent) -> bool:
        """Validiere Zeitrahmen-Konsistenz"""
        data = event.event_data
        
        # target_date muss nach calculation_date liegen
        if data.target_date < data.calculation_date.date():
            logger.error(f"Invalid timeframe: target_date {data.target_date} before calculation_date {data.calculation_date.date()}")
            return False
        
        # horizon_days muss mit Datum-Differenz übereinstimmen
        expected_days = (data.target_date - data.calculation_date.date()).days
        if abs(expected_days - data.horizon_days) > 1:  # 1 Tag Toleranz
            logger.warning(f"Horizon days mismatch: expected {expected_days}, got {data.horizon_days}")
        
        return True
    
    @staticmethod
    def validate_evaluation_consistency(event: PredictionEvaluatedEvent) -> bool:
        """Validiere Evaluierungs-Konsistenz"""
        data = event.event_data
        
        # evaluation_date muss nach target_date liegen (oder gleich sein)
        if data.evaluation_date.date() < data.target_date:
            logger.error(f"Invalid evaluation: evaluation_date {data.evaluation_date.date()} before target_date {data.target_date}")
            return False
        
        # Prüfe Performance-Berechnung
        expected_diff = data.actual_value - data.predicted_value
        if abs(expected_diff - data.performance_diff) > Decimal('0.01'):
            logger.error(f"Performance calculation error: expected {expected_diff}, got {data.performance_diff}")
            return False
        
        return True

# ===============================================================================
# LEGACY COMPATIBILITY - Für Migration bestehender Services
# ===============================================================================

class LegacyEventConverter:
    """Konverter für bestehende Event-Formate"""
    
    @staticmethod
    def convert_old_prediction_event(old_event: Dict[str, Any]) -> Optional[PredictionCreatedEvent]:
        """Konvertiere altes Prediction Event Format"""
        try:
            # Mapping alter Feldnamen
            symbol = old_event.get('symbol') or old_event.get('stock_symbol')
            predicted_value = old_event.get('predicted_value') or old_event.get('profit_forecast')
            
            # Zeitstempel-Mapping
            calculation_date = old_event.get('created_at') or old_event.get('timestamp')
            if isinstance(calculation_date, str):
                calculation_date = datetime.fromisoformat(calculation_date.replace('Z', '+00:00'))
            
            target_date = old_event.get('target_date') or old_event.get('predicted_date')
            if isinstance(target_date, str):
                target_date = datetime.fromisoformat(target_date).date()
            
            # Horizont-Mapping
            horizon_map = {
                'weekly': HorizonType.ONE_WEEK,
                'monthly': HorizonType.ONE_MONTH,
                'quarterly': HorizonType.THREE_MONTHS,
                'yearly': HorizonType.TWELVE_MONTHS
            }
            horizon_type = horizon_map.get(old_event.get('timeframe'), HorizonType.ONE_MONTH)
            
            return PredictionEventBuilder.create_prediction_created_event(
                symbol=symbol,
                predicted_value=Decimal(str(predicted_value)),
                horizon_type=horizon_type,
                horizon_days=30,  # Default
                service_name=old_event.get('source', 'legacy-service'),
                calculation_date=calculation_date,
                target_date=target_date
            )
            
        except Exception as e:
            logger.error(f"Failed to convert legacy event: {e}")
            return None

# ===============================================================================
# USAGE EXAMPLES
# ===============================================================================

def example_usage():
    """Beispiele für Event-Usage"""
    
    # Beispiel 1: Neue Vorhersage erstellen
    prediction_event = PredictionEventBuilder.create_prediction_created_event(
        symbol="AAPL",
        predicted_value=Decimal("8.5"),
        horizon_type=HorizonType.ONE_MONTH,
        horizon_days=30,
        service_name="ml-analytics-service",
        company_name="Apple Inc.",
        confidence_score=Decimal("0.85")
    )
    
    print("Prediction Created Event:")
    print(prediction_event.json(indent=2))
    
    # Beispiel 2: Vorhersage evaluieren
    evaluation_event = PredictionEventBuilder.create_prediction_evaluated_event(
        prediction_id="pred_20250825_120000_AAPL",
        symbol="AAPL",
        calculation_date=datetime(2025, 8, 25, 12, 0, 0),
        target_date=date(2025, 9, 25),
        predicted_value=Decimal("8.5"),
        actual_value=Decimal("7.2"),
        horizon_type=HorizonType.ONE_MONTH,
        service_name="prediction-evaluation-service",
        company_name="Apple Inc."
    )
    
    print("\nPrediction Evaluated Event:")
    print(evaluation_event.json(indent=2))

if __name__ == "__main__":
    example_usage()