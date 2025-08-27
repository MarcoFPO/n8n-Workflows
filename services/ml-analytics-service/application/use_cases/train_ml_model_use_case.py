#!/usr/bin/env python3
"""
Train ML Model Use Case v1.0.0
Clean Architecture Application Layer - ML Model Training Orchestration

APPLICATION LAYER RESPONSIBILITIES:
- Orchestrates ML model training workflows through domain services
- Implements input/output validation and transformation
- Coordinates between domain services and infrastructure
- Manages use case-specific business rules and validation

BUSINESS USE CASE:
"As a system, I want to train ML models for multiple prediction horizons
with automatic performance validation and ensemble creation,
so that I can provide accurate stock price predictions."

CLEAN ARCHITECTURE COMPLIANCE:
- Depends on Domain Services and Repository Interfaces
- No direct Infrastructure dependencies
- Input/Output DTOs for clean interfaces
- Coordinated domain logic execution
- Error handling and validation

SUCCESS TEMPLATE: Based on Frontend Service Clean Architecture Migration
Integration: Event-Driven Architecture for ML Training Coordination

Autor: Claude Code - Clean Architecture Specialist
Datum: 26. August 2025
Version: 1.0.0 - Application Layer Use Case Implementation
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Application Layer Imports
from ..interfaces.ml_service_provider import IMLServiceProvider
from ..interfaces.event_publisher import IEventPublisher

# Domain Layer Imports
from ...domain.services.model_training_orchestrator_service import (
    ModelTrainingOrchestrator,
    TrainingConfiguration,
    TrainingStrategy,
    ModelType,
    TrainingResult
)
from ...domain.entities.prediction import PredictionHorizon
from ...domain.value_objects.performance_metrics import PerformanceMetrics
from ...domain.exceptions.ml_exceptions import (
    ModelTrainingError,
    InsufficientDataError,
    PerformanceThresholdError
)


class TrainingPriority(Enum):
    """Training Priority Levels - Application Layer"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TrainMLModelRequest:
    """Input DTO for Train ML Model Use Case"""
    symbols: List[str]
    horizons: List[PredictionHorizon]
    model_types: List[ModelType]
    strategy: TrainingStrategy
    performance_threshold: float
    max_training_hours: int
    priority: TrainingPriority
    validation_split: float = 0.2
    cross_validation_folds: int = 5
    early_stopping_patience: int = 10
    requested_by: str = "system"
    request_timestamp: datetime = None
    
    def __post_init__(self):
        if self.request_timestamp is None:
            self.request_timestamp = datetime.now()


@dataclass
class TrainMLModelResponse:
    """Output DTO for Train ML Model Use Case"""
    training_session_id: str
    request_accepted: bool
    training_results: List[TrainingResult]
    performance_summary: Dict[str, Any]
    production_ready_models: List[str]
    failed_models: List[str]
    total_training_time_minutes: float
    recommendations: List[str]
    next_training_scheduled: Optional[datetime]
    events_published: List[str]


class TrainMLModelUseCase:
    """
    Train ML Model Use Case - Clean Architecture Application Layer
    
    APPLICATION LAYER RESPONSIBILITIES:
    - Orchestrates ML model training workflows
    - Validates and transforms inputs/outputs
    - Coordinates between domain services
    - Publishes training events
    - Manages training sessions and scheduling
    
    BUSINESS LOGIC COORDINATION:
    - Multi-horizon model training orchestration
    - Performance validation and quality gates  
    - Production model promotion workflow
    - Training event notification
    """
    
    def __init__(
        self,
        model_training_orchestrator: ModelTrainingOrchestrator,
        ml_service_provider: IMLServiceProvider,
        event_publisher: IEventPublisher
    ):
        self.model_training_orchestrator = model_training_orchestrator
        self.ml_service_provider = ml_service_provider
        self.event_publisher = event_publisher
        self.logger = logging.getLogger(self.__class__.__name__)
        self._active_training_sessions: Dict[str, TrainMLModelRequest] = {}
        
    async def execute(self, request: TrainMLModelRequest) -> TrainMLModelResponse:
        """
        Execute ML Model Training Use Case
        
        WORKFLOW:
        1. Validate training request
        2. Prepare training data sources
        3. Execute multi-horizon training orchestration
        4. Validate performance thresholds
        5. Promote production-ready models
        6. Publish training events
        7. Schedule next training if needed
        """
        training_session_id = f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(request.symbols))}"
        
        try:
            self.logger.info(f"Executing ML model training use case: {training_session_id}")
            self.logger.info(f"Symbols: {request.symbols}, Horizons: {[h.value for h in request.horizons]}")
            
            # Validate request
            await self._validate_training_request(request)
            
            # Register training session
            self._active_training_sessions[training_session_id] = request
            
            # Prepare training configuration
            training_config = TrainingConfiguration(
                horizons=request.horizons,
                model_types=request.model_types,
                strategy=request.strategy,
                performance_threshold=request.performance_threshold,
                max_training_time_hours=request.max_training_hours,
                validation_split=request.validation_split,
                cross_validation_folds=request.cross_validation_folds,
                early_stopping_patience=request.early_stopping_patience
            )
            
            # Publish training started event
            await self._publish_training_event("training_started", training_session_id, {
                "symbols": request.symbols,
                "horizons": [h.value for h in request.horizons],
                "model_types": [mt.value for mt in request.model_types],
                "strategy": request.strategy.value,
                "priority": request.priority.value
            })
            
            # Prepare data sources
            data_sources = await self._prepare_data_sources(request.symbols)
            
            # Execute training orchestration
            training_start_time = datetime.now()
            
            training_results = await self.model_training_orchestrator.orchestrate_multi_horizon_training(
                training_config=training_config,
                data_sources=data_sources,
                target_symbols=request.symbols
            )
            
            training_end_time = datetime.now()
            total_training_time = (training_end_time - training_start_time).total_seconds() / 60
            
            # Analyze training results
            performance_summary = self._analyze_training_performance(training_results)
            production_ready_models = self._identify_production_ready_models(training_results)
            failed_models = self._identify_failed_models(training_results, request.performance_threshold)
            
            # Generate recommendations
            recommendations = self._generate_training_recommendations(training_results, training_config)
            
            # Schedule next training if needed
            next_training = self._calculate_next_training_schedule(training_results, request.priority)
            
            # Publish training completed event
            await self._publish_training_event("training_completed", training_session_id, {
                "total_models_trained": len(training_results),
                "production_ready_models": len(production_ready_models),
                "failed_models": len(failed_models),
                "training_time_minutes": total_training_time,
                "performance_summary": performance_summary
            })
            
            # Promote production-ready models
            promoted_models = await self._promote_production_models(production_ready_models, training_results)
            
            # Clean up training session
            self._active_training_sessions.pop(training_session_id, None)
            
            response = TrainMLModelResponse(
                training_session_id=training_session_id,
                request_accepted=True,
                training_results=training_results,
                performance_summary=performance_summary,
                production_ready_models=production_ready_models,
                failed_models=failed_models,
                total_training_time_minutes=total_training_time,
                recommendations=recommendations,
                next_training_scheduled=next_training,
                events_published=["training_started", "training_completed", "models_promoted"]
            )
            
            self.logger.info(f"ML model training completed successfully: {len(training_results)} models trained")
            return response
            
        except Exception as e:
            self.logger.error(f"ML model training failed: {str(e)}")
            
            # Publish training failed event
            await self._publish_training_event("training_failed", training_session_id, {
                "error": str(e),
                "symbols": request.symbols,
                "requested_by": request.requested_by
            })
            
            # Clean up failed session
            self._active_training_sessions.pop(training_session_id, None)
            
            # Return failed response
            return TrainMLModelResponse(
                training_session_id=training_session_id,
                request_accepted=False,
                training_results=[],
                performance_summary={"status": "failed", "error": str(e)},
                production_ready_models=[],
                failed_models=[],
                total_training_time_minutes=0.0,
                recommendations=[f"Training failed: {str(e)}"],
                next_training_scheduled=None,
                events_published=["training_failed"]
            )
    
    async def _validate_training_request(self, request: TrainMLModelRequest) -> None:
        """Validate training request business rules"""
        # Validate symbols
        if not request.symbols:
            raise ValueError("At least one symbol must be provided")
        
        if len(request.symbols) > 50:
            raise ValueError("Maximum 50 symbols allowed per training request")
        
        # Validate horizons
        if not request.horizons:
            raise ValueError("At least one prediction horizon must be specified")
        
        # Validate model types
        if not request.model_types:
            raise ValueError("At least one model type must be specified")
        
        # Validate performance threshold
        if request.performance_threshold < 0.5 or request.performance_threshold > 1.0:
            raise ValueError("Performance threshold must be between 50% and 100%")
        
        # Validate training time
        if request.max_training_hours < 1 or request.max_training_hours > 24:
            raise ValueError("Training time must be between 1 and 24 hours")
        
        # Check for existing active training sessions for same symbols
        for session_id, active_request in self._active_training_sessions.items():
            if set(active_request.symbols).intersection(set(request.symbols)):
                if request.priority != TrainingPriority.CRITICAL:
                    raise ValueError(f"Training already in progress for symbols: {list(set(active_request.symbols).intersection(set(request.symbols)))}")
        
        self.logger.info("Training request validation passed")
    
    async def _prepare_data_sources(self, symbols: List[str]) -> List[str]:
        """Prepare data sources for training"""
        try:
            # In real implementation, this would validate data availability
            # and prepare data pipelines through the ML service provider
            
            data_sources = []
            
            for symbol in symbols:
                # Check data availability
                data_available = await self.ml_service_provider.check_data_availability(
                    symbol, days_required=365
                )
                
                if data_available:
                    data_sources.append(f"market_data_{symbol}")
                else:
                    self.logger.warning(f"Limited data available for {symbol}")
                    data_sources.append(f"limited_data_{symbol}")
            
            if not data_sources:
                raise InsufficientDataError("No data sources available for training")
            
            self.logger.info(f"Prepared {len(data_sources)} data sources")
            return data_sources
            
        except Exception as e:
            self.logger.error(f"Data source preparation failed: {str(e)}")
            raise InsufficientDataError(f"Failed to prepare data sources: {str(e)}")
    
    def _analyze_training_performance(self, training_results: List[TrainingResult]) -> Dict[str, Any]:
        """Analyze training performance across all models"""
        if not training_results:
            return {"status": "no_results"}
        
        # Calculate aggregate metrics
        accuracies = [result.validation_accuracy for result in training_results]
        training_times = [result.training_duration_minutes for result in training_results]
        
        # Performance by horizon
        horizon_performance = {}
        for result in training_results:
            horizon = result.horizon.value
            if horizon not in horizon_performance:
                horizon_performance[horizon] = []
            horizon_performance[horizon].append(result.validation_accuracy)
        
        # Performance by model type
        model_performance = {}
        for result in training_results:
            model_type = result.model_type.value
            if model_type not in model_performance:
                model_performance[model_type] = []
            model_performance[model_type].append(result.validation_accuracy)
        
        return {
            "total_models_trained": len(training_results),
            "average_accuracy": sum(accuracies) / len(accuracies),
            "best_accuracy": max(accuracies),
            "worst_accuracy": min(accuracies),
            "total_training_time_minutes": sum(training_times),
            "average_training_time_minutes": sum(training_times) / len(training_times),
            "horizon_performance": {
                horizon: {
                    "average_accuracy": sum(accs) / len(accs),
                    "model_count": len(accs)
                } for horizon, accs in horizon_performance.items()
            },
            "model_type_performance": {
                model_type: {
                    "average_accuracy": sum(accs) / len(accs),
                    "model_count": len(accs)
                } for model_type, accs in model_performance.items()
            }
        }
    
    def _identify_production_ready_models(self, training_results: List[TrainingResult]) -> List[str]:
        """Identify models ready for production deployment"""
        production_ready = []
        
        for result in training_results:
            if result.is_production_ready and result.validation_accuracy >= 0.70:
                production_ready.append(result.model_id)
        
        return production_ready
    
    def _identify_failed_models(self, training_results: List[TrainingResult], threshold: float) -> List[str]:
        """Identify models that failed to meet performance threshold"""
        failed_models = []
        
        for result in training_results:
            if not result.is_production_ready or result.validation_accuracy < threshold:
                failed_models.append(result.model_id)
        
        return failed_models
    
    def _generate_training_recommendations(
        self, 
        training_results: List[TrainingResult], 
        config: TrainingConfiguration
    ) -> List[str]:
        """Generate recommendations based on training results"""
        recommendations = []
        
        if not training_results:
            recommendations.append("Training failed - no models were successfully trained")
            return recommendations
        
        # Performance-based recommendations
        avg_accuracy = sum(r.validation_accuracy for r in training_results) / len(training_results)
        
        if avg_accuracy < 0.60:
            recommendations.append("Low overall performance - consider improving data quality or features")
        elif avg_accuracy > 0.85:
            recommendations.append("Excellent performance - consider promoting best models to production")
        
        # Model type recommendations
        model_performance = {}
        for result in training_results:
            model_type = result.model_type.value
            if model_type not in model_performance:
                model_performance[model_type] = []
            model_performance[model_type].append(result.validation_accuracy)
        
        best_model_type = max(model_performance.items(), key=lambda x: sum(x[1])/len(x[1]))
        recommendations.append(f"Best performing model type: {best_model_type[0]} (avg: {sum(best_model_type[1])/len(best_model_type[1]):.2%})")
        
        # Strategy recommendations
        if config.strategy == TrainingStrategy.SEQUENTIAL and len(training_results) > 5:
            recommendations.append("Consider parallel training strategy for better efficiency with multiple models")
        
        # Ensemble recommendations
        production_ready_count = len([r for r in training_results if r.is_production_ready])
        if production_ready_count >= 2:
            recommendations.append("Multiple production-ready models available - consider ensemble deployment")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _calculate_next_training_schedule(self, results: List[TrainingResult], priority: TrainingPriority) -> Optional[datetime]:
        """Calculate when next training should be scheduled"""
        if not results:
            return datetime.now() + timedelta(hours=1)  # Retry soon if failed
        
        # Base scheduling based on performance
        avg_performance = sum(r.validation_accuracy for r in results) / len(results)
        
        if avg_performance >= 0.85:
            base_days = 14  # High performance - less frequent retraining
        elif avg_performance >= 0.75:
            base_days = 7   # Good performance - weekly retraining
        elif avg_performance >= 0.65:
            base_days = 3   # Acceptable performance - frequent retraining
        else:
            base_days = 1   # Poor performance - daily retraining
        
        # Adjust based on priority
        priority_adjustment = {
            TrainingPriority.LOW: 2.0,
            TrainingPriority.NORMAL: 1.0,
            TrainingPriority.HIGH: 0.5,
            TrainingPriority.CRITICAL: 0.25
        }
        
        adjusted_days = base_days * priority_adjustment.get(priority, 1.0)
        return datetime.now() + timedelta(days=adjusted_days)
    
    async def _promote_production_models(self, model_ids: List[str], training_results: List[TrainingResult]) -> List[str]:
        """Promote production-ready models to active deployment"""
        promoted_models = []
        
        try:
            for model_id in model_ids:
                # Find the training result for this model
                result = next((r for r in training_results if r.model_id == model_id), None)
                
                if result and result.is_production_ready:
                    # Promote model through ML service provider
                    success = await self.ml_service_provider.promote_model_to_production(
                        model_id=model_id,
                        model_type=result.model_type.value,
                        horizon=result.horizon.value,
                        performance_metrics=result.performance_metrics
                    )
                    
                    if success:
                        promoted_models.append(model_id)
                        self.logger.info(f"Model {model_id} promoted to production")
                        
                        # Publish model promotion event
                        await self._publish_training_event("model_promoted", model_id, {
                            "model_id": model_id,
                            "validation_accuracy": result.validation_accuracy,
                            "model_type": result.model_type.value,
                            "horizon": result.horizon.value
                        })
                    else:
                        self.logger.warning(f"Failed to promote model {model_id}")
            
            return promoted_models
            
        except Exception as e:
            self.logger.error(f"Model promotion failed: {str(e)}")
            return promoted_models
    
    async def _publish_training_event(self, event_type: str, session_id: str, event_data: Dict[str, Any]) -> None:
        """Publish training-related events"""
        try:
            event_payload = {
                "event_type": event_type,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "service": "ml-analytics-service",
                "use_case": "train_ml_model",
                **event_data
            }
            
            await self.event_publisher.publish("ml_training_events", event_payload)
            self.logger.debug(f"Published event: {event_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to publish event {event_type}: {str(e)}")
    
    def get_active_training_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active training sessions"""
        return {
            session_id: {
                "symbols": request.symbols,
                "horizons": [h.value for h in request.horizons],
                "model_types": [mt.value for mt in request.model_types],
                "strategy": request.strategy.value,
                "priority": request.priority.value,
                "requested_by": request.requested_by,
                "started_at": request.request_timestamp.isoformat()
            } for session_id, request in self._active_training_sessions.items()
        }
    
    async def cancel_training_session(self, session_id: str) -> bool:
        """Cancel an active training session"""
        if session_id in self._active_training_sessions:
            self._active_training_sessions.pop(session_id)
            
            await self._publish_training_event("training_cancelled", session_id, {
                "cancelled_at": datetime.now().isoformat()
            })
            
            self.logger.info(f"Training session {session_id} cancelled")
            return True
        
        return False