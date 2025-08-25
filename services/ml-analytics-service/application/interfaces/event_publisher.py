#!/usr/bin/env python3
"""
Event Publisher Interface - Clean Architecture v6.0.0
Domain Event Publishing Interface for ML Analytics Service

APPLICATION LAYER - EVENT INTERFACE:
- IEventPublisher: Interface for publishing domain events
- Event-driven architecture support for ML operations
- Decoupled event publishing following DIP

DESIGN PATTERNS IMPLEMENTED:
- Observer Pattern: Event publishing and subscription
- Dependency Inversion Principle: Application defines interface
- Single Responsibility: Only event publishing concern

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime


class IEventPublisher(ABC):
    """
    Interface for Publishing Domain Events
    
    Defines contract for publishing events from ML operations
    to enable event-driven architecture and loose coupling.
    """
    
    @abstractmethod
    async def publish(self, event: Dict[str, Any]) -> bool:
        """
        Publish domain event
        
        Args:
            event: Event data dictionary with event details
            
        Returns:
            True if event was published successfully
        """
        pass
    
    @abstractmethod
    async def publish_batch(self, events: List[Dict[str, Any]]) -> bool:
        """
        Publish multiple events as batch
        
        Args:
            events: List of event dictionaries
            
        Returns:
            True if all events were published successfully
        """
        pass
    
    @abstractmethod
    async def get_publisher_health(self) -> Dict[str, Any]:
        """
        Get health status of event publisher
        
        Returns:
            Dictionary with publisher health information
        """
        pass


# =============================================================================
# STANDARD ML DOMAIN EVENTS
# =============================================================================

class MLDomainEvents:
    """
    Standard ML Domain Events
    
    Defines standard event types and structures for ML operations.
    These are not interfaces but standard event definitions.
    """
    
    @staticmethod
    def model_training_started(model_id: str, 
                             model_type: str, 
                             job_id: str,
                             symbol: str = None) -> Dict[str, Any]:
        """Create ModelTrainingStarted event"""
        return {
            "event_type": "ModelTrainingStarted",
            "model_id": model_id,
            "model_type": model_type,
            "job_id": job_id,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "ml-analytics-service",
            "version": "1.0"
        }
    
    @staticmethod
    def model_training_completed(model_id: str,
                               model_type: str,
                               job_id: str,
                               success: bool,
                               training_duration_minutes: float = None) -> Dict[str, Any]:
        """Create ModelTrainingCompleted event"""
        return {
            "event_type": "ModelTrainingCompleted",
            "model_id": model_id,
            "model_type": model_type,
            "job_id": job_id,
            "success": success,
            "training_duration_minutes": training_duration_minutes,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "ml-analytics-service",
            "version": "1.0"
        }
    
    @staticmethod
    def model_training_failed(model_id: str,
                            model_type: str,
                            job_id: str,
                            error_message: str) -> Dict[str, Any]:
        """Create ModelTrainingFailed event"""
        return {
            "event_type": "ModelTrainingFailed",
            "model_id": model_id,
            "model_type": model_type,
            "job_id": job_id,
            "error_message": error_message,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "ml-analytics-service",
            "version": "1.0"
        }
    
    @staticmethod
    def prediction_generated(prediction_id: str,
                           symbol: str,
                           model_id: str,
                           model_type: str,
                           predicted_price: float,
                           confidence_score: float,
                           prediction_horizon: str,
                           high_confidence: bool = False) -> Dict[str, Any]:
        """Create PredictionGenerated event"""
        return {
            "event_type": "PredictionGenerated",
            "prediction_id": prediction_id,
            "symbol": symbol,
            "model_id": model_id,
            "model_type": model_type,
            "predicted_price": predicted_price,
            "confidence_score": confidence_score,
            "prediction_horizon": prediction_horizon,
            "high_confidence": high_confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "ml-analytics-service",
            "version": "1.0"
        }
    
    @staticmethod
    def model_evaluation_completed(model_id: str,
                                 model_type: str,
                                 performance_category: str,
                                 accuracy: float,
                                 needs_retraining: bool) -> Dict[str, Any]:
        """Create ModelEvaluationCompleted event"""
        return {
            "event_type": "ModelEvaluationCompleted",
            "model_id": model_id,
            "model_type": model_type,
            "performance_category": performance_category,
            "accuracy": accuracy,
            "needs_retraining": needs_retraining,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "ml-analytics-service",
            "version": "1.0"
        }
    
    @staticmethod
    def risk_assessment_completed(prediction_id: str,
                                symbol: str,
                                risk_score: float,
                                risk_category: str,
                                high_risk: bool) -> Dict[str, Any]:
        """Create RiskAssessmentCompleted event"""
        return {
            "event_type": "RiskAssessmentCompleted",
            "prediction_id": prediction_id,
            "symbol": symbol,
            "risk_score": risk_score,
            "risk_category": risk_category,
            "high_risk": high_risk,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "ml-analytics-service",
            "version": "1.0"
        }
    
    @staticmethod
    def batch_prediction_completed(symbols: List[str],
                                 predictions_generated: int,
                                 failed_predictions: int,
                                 processing_time_seconds: float) -> Dict[str, Any]:
        """Create BatchPredictionCompleted event"""
        return {
            "event_type": "BatchPredictionCompleted",
            "symbols": symbols,
            "predictions_generated": predictions_generated,
            "failed_predictions": failed_predictions,
            "processing_time_seconds": processing_time_seconds,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "ml-analytics-service",
            "version": "1.0"
        }
    
    @staticmethod
    def model_performance_degraded(model_id: str,
                                 model_type: str,
                                 current_accuracy: float,
                                 threshold_accuracy: float) -> Dict[str, Any]:
        """Create ModelPerformanceDegraded event"""
        return {
            "event_type": "ModelPerformanceDegraded",
            "model_id": model_id,
            "model_type": model_type,
            "current_accuracy": current_accuracy,
            "threshold_accuracy": threshold_accuracy,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "ml-analytics-service",
            "version": "1.0"
        }