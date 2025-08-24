#!/usr/bin/env python3
"""
ML Prediction Publisher v1.0.0
Event-Publisher für ML-Vorhersagen mit Clean Architecture

CLEAN ARCHITECTURE PRINCIPLES:
- Single Responsibility: Nur ML-Event Publishing
- Dependency Inversion: Interface-basierte Event-Bus Integration
- Open/Closed: Erweiterbar für neue Event-Typen
- Interface Segregation: Spezifische Publisher-Interfaces

Autor: Claude Code
Datum: 23. August 2025
Version: 1.0.0
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# Import shared modules
from shared.event_bus_v1_0_1_20250822 import EventBusConnection
from shared.ml_prediction_event_types_v1_0_0_20250823 import (
    MLEventFactory,
    IndividualModelPrediction,
    EnsemblePredictionData,
    MLIndividualPredictionEvent,
    MLEnsemblePredictionEvent,
    MLPredictionStorageRequestEvent
)

logger = logging.getLogger(__name__)


class IMLPredictionPublisher:
    """Interface für ML-Prediction Publisher (Interface Segregation Principle)"""
    
    async def publish_individual_prediction(self, symbol: str, prediction: IndividualModelPrediction, 
                                          correlation_id: Optional[str] = None) -> bool:
        """Publiziert individuelle Modell-Vorhersage"""
        raise NotImplementedError
    
    async def publish_ensemble_prediction(self, symbol: str, 
                                        individual_predictions: Dict[str, IndividualModelPrediction],
                                        final_prediction: EnsemblePredictionData,
                                        forecast_period_days: int,
                                        target_date: datetime,
                                        correlation_id: Optional[str] = None) -> bool:
        """Publiziert vollständige Ensemble-Vorhersage"""
        raise NotImplementedError
    
    async def request_prediction_storage(self, prediction_data: Dict[str, Any],
                                       correlation_id: Optional[str] = None) -> bool:
        """Fordert Speicherung von Vorhersagedaten an"""
        raise NotImplementedError


class MLPredictionPublisher(IMLPredictionPublisher):
    """
    Konkrete Implementierung des ML-Prediction Publishers
    
    SOLID PRINCIPLES:
    - Single Responsibility: Nur ML-Event Publishing
    - Open/Closed: Erweiterbar ohne Änderung bestehender Funktionalität
    - Dependency Inversion: Abhängig von EventBusConnection Interface
    """
    
    def __init__(self, event_bus: EventBusConnection):
        self.event_bus = event_bus
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.published_events = []
        self.error_count = 0
        
    async def publish_individual_prediction(self, symbol: str, prediction: IndividualModelPrediction, 
                                          correlation_id: Optional[str] = None) -> bool:
        """
        Publiziert individuelle Modell-Vorhersage via Event-Bus
        
        Args:
            symbol: Aktien-Symbol
            prediction: Individuelle Modell-Vorhersage
            correlation_id: Optional correlation ID für Event-Tracking
            
        Returns:
            bool: True wenn erfolgreich publiziert
        """
        try:
            # Event erstellen
            event = MLEventFactory.create_individual_prediction_event(
                symbol=symbol,
                prediction=prediction,
                correlation_id=correlation_id
            )
            
            # Event publizieren
            success = await self.event_bus.publish_event(
                event_type=event.event_type,
                event_data=event.to_dict()
            )
            
            if success:
                self.published_events.append(event.event_id)
                self.logger.info(f"Published individual prediction for {symbol} ({prediction.model_type})")
                return True
            else:
                self.error_count += 1
                self.logger.error(f"Failed to publish individual prediction for {symbol}")
                return False
                
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error publishing individual prediction for {symbol}: {str(e)}")
            return False
    
    async def publish_ensemble_prediction(self, symbol: str, 
                                        individual_predictions: Dict[str, IndividualModelPrediction],
                                        final_prediction: EnsemblePredictionData,
                                        forecast_period_days: int,
                                        target_date: datetime,
                                        correlation_id: Optional[str] = None) -> bool:
        """
        Publiziert vollständige Ensemble-Vorhersage via Event-Bus
        
        Args:
            symbol: Aktien-Symbol
            individual_predictions: Dict mit individuellen Modell-Vorhersagen
            final_prediction: Finale Ensemble-Vorhersage
            forecast_period_days: Vorhersage-Zeitraum in Tagen
            target_date: Ziel-Datum der Vorhersage
            correlation_id: Optional correlation ID für Event-Tracking
            
        Returns:
            bool: True wenn erfolgreich publiziert
        """
        try:
            # Event erstellen
            event = MLEventFactory.create_ensemble_prediction_event(
                symbol=symbol,
                individual_predictions=individual_predictions,
                final_prediction=final_prediction,
                forecast_period_days=forecast_period_days,
                target_date=target_date,
                correlation_id=correlation_id
            )
            
            # Event publizieren
            success = await self.event_bus.publish_event(
                event_type=event.event_type,
                event_data=event.to_dict()
            )
            
            if success:
                self.published_events.append(event.event_id)
                self.logger.info(f"Published ensemble prediction for {symbol} "
                               f"(models: {list(individual_predictions.keys())})")
                
                # Zusätzlich Storage-Request senden
                await self._request_ensemble_storage(event)
                return True
            else:
                self.error_count += 1
                self.logger.error(f"Failed to publish ensemble prediction for {symbol}")
                return False
                
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error publishing ensemble prediction for {symbol}: {str(e)}")
            return False
    
    async def request_prediction_storage(self, prediction_data: Dict[str, Any],
                                       correlation_id: Optional[str] = None) -> bool:
        """
        Fordert Speicherung von Vorhersagedaten an
        
        Args:
            prediction_data: Vorhersagedaten für Speicherung
            correlation_id: Optional correlation ID für Event-Tracking
            
        Returns:
            bool: True wenn erfolgreich publiziert
        """
        try:
            # Event erstellen
            event = MLEventFactory.create_storage_request_event(
                prediction_data=prediction_data,
                correlation_id=correlation_id
            )
            
            # Event publizieren
            success = await self.event_bus.publish_event(
                event_type=event.event_type,
                event_data=event.to_dict()
            )
            
            if success:
                self.published_events.append(event.event_id)
                self.logger.info(f"Requested storage for prediction data: {prediction_data.get('symbol', 'unknown')}")
                return True
            else:
                self.error_count += 1
                self.logger.error(f"Failed to request prediction storage")
                return False
                
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error requesting prediction storage: {str(e)}")
            return False
    
    async def _request_ensemble_storage(self, ensemble_event: MLEnsemblePredictionEvent) -> bool:
        """
        Private Methode: Fordert Speicherung für Ensemble-Vorhersage an
        
        Args:
            ensemble_event: Ensemble-Event mit Vorhersagedaten
            
        Returns:
            bool: True wenn erfolgreich
        """
        try:
            # Strukturierte Daten für Speicherung vorbereiten
            storage_data = {
                "symbol": ensemble_event.symbol,
                "company_name": f"{ensemble_event.symbol} Corporation",  # Default fallback
                "individual_models": ensemble_event.data["individual_predictions"],
                "ensemble_prediction": {
                    "profit_forecast": ensemble_event.data["final_prediction"]["profit_forecast"],
                    "confidence_level": ensemble_event.data["final_prediction"]["confidence_level"],
                    "recommendation": ensemble_event.data["final_prediction"]["recommendation"],
                    "risk_assessment": ensemble_event.data["final_prediction"]["risk_assessment"],
                    "ensemble_method": ensemble_event.data["final_prediction"]["ensemble_method"],
                    "model_weights": ensemble_event.data["final_prediction"]["model_weights"]
                },
                "forecast_period_days": ensemble_event.forecast_period_days,
                "target_date": ensemble_event.target_date.isoformat(),
                "created_at": ensemble_event.timestamp.isoformat(),
                "ensemble_id": ensemble_event.ensemble_id
            }
            
            return await self.request_prediction_storage(
                prediction_data=storage_data,
                correlation_id=ensemble_event.correlation_id
            )
            
        except Exception as e:
            self.logger.error(f"Error requesting ensemble storage: {str(e)}")
            return False
    
    def get_publisher_stats(self) -> Dict[str, Any]:
        """
        Gibt Publisher-Statistiken zurück
        
        Returns:
            Dict mit Statistiken
        """
        return {
            "published_events_count": len(self.published_events),
            "error_count": self.error_count,
            "last_published": self.published_events[-1] if self.published_events else None,
            "publisher_health": "healthy" if self.error_count == 0 else "degraded"
        }


class MLPredictionPublisherFactory:
    """Factory für ML-Prediction Publisher (Factory Pattern)"""
    
    @staticmethod
    async def create_publisher(event_bus_connection: EventBusConnection) -> IMLPredictionPublisher:
        """
        Erstellt ML-Prediction Publisher
        
        Args:
            event_bus_connection: Event-Bus Connection
            
        Returns:
            IMLPredictionPublisher: Publisher-Instance
        """
        publisher = MLPredictionPublisher(event_bus_connection)
        
        # Verbindung testen
        if hasattr(event_bus_connection, 'is_connected') and not await event_bus_connection.is_connected():
            raise ConnectionError("Event-Bus is not connected")
        
        return publisher


# Convenience Functions für einfache Nutzung
async def publish_individual_model_prediction(event_bus: EventBusConnection, 
                                            symbol: str, 
                                            model_type: str,
                                            prediction_values: List[float],
                                            confidence_score: float,
                                            horizon_days: int,
                                            correlation_id: Optional[str] = None) -> bool:
    """
    Convenience-Funktion für individuelle Modell-Vorhersage
    
    Args:
        event_bus: Event-Bus Connection
        symbol: Aktien-Symbol
        model_type: Modell-Typ (technical, sentiment, fundamental, meta)
        prediction_values: Vorhersagewerte
        confidence_score: Konfidenz-Score
        horizon_days: Vorhersage-Zeitraum
        correlation_id: Optional correlation ID
        
    Returns:
        bool: True wenn erfolgreich publiziert
    """
    publisher = await MLPredictionPublisherFactory.create_publisher(event_bus)
    
    prediction = IndividualModelPrediction(
        model_type=model_type,
        model_version="1.0.0",
        prediction_values=prediction_values,
        confidence_score=confidence_score,
        volatility_estimate=0.1,  # Default
        feature_importance={},    # Default
        horizon_days=horizon_days,
        prediction_timestamp=datetime.utcnow()
    )
    
    return await publisher.publish_individual_prediction(
        symbol=symbol,
        prediction=prediction,
        correlation_id=correlation_id
    )