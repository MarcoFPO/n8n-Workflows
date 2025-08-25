#!/usr/bin/env python3
"""
ML Training Use Cases - Clean Architecture v6.0.0
Business Logic Orchestration for Machine Learning Training Operations

APPLICATION LAYER - USE CASES:
- TrainModelUseCase: Orchestrates model training workflow
- RetrainOutdatedModelsUseCase: Manages model lifecycle and retraining
- EvaluateModelUseCase: Handles model performance evaluation
- ManageModelVersionsUseCase: Controls model versioning and deployment

CLEAN ARCHITECTURE PRINCIPLES:
- Use Cases contain business logic flow
- No infrastructure dependencies (Dependency Inversion)
- Single Responsibility per Use Case
- Domain entities and repository interfaces only

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..interfaces.ml_service_provider import IMLModelTrainer, IMLModelEvaluator
from ..interfaces.event_publisher import IEventPublisher
from ...domain.entities.ml_entities import (
    MLModel,
    MLTrainingJob,
    MLPerformanceMetrics,
    MLModelType,
    MLJobStatus,
    ModelConfiguration,
    ModelPerformanceCategory
)
from ...domain.repositories.ml_repository import IMLAnalyticsRepository


logger = logging.getLogger(__name__)


# =============================================================================
# USE CASE REQUEST/RESPONSE MODELS
# =============================================================================

@dataclass
class TrainModelRequest:
    """Request model for training ML models"""
    model_type: MLModelType
    configuration: ModelConfiguration
    symbol: str
    force_retrain: bool = False
    background_training: bool = True


@dataclass
class TrainModelResponse:
    """Response model for training operations"""
    success: bool
    job_id: Optional[str] = None
    model_id: Optional[str] = None
    message: str = ""
    estimated_completion_minutes: Optional[float] = None
    error_details: Optional[Dict[str, Any]] = None


@dataclass
class ModelEvaluationRequest:
    """Request model for model evaluation"""
    model_id: str
    evaluation_period_days: int = 30
    include_risk_metrics: bool = True
    comparison_models: List[str] = None


@dataclass
class ModelEvaluationResponse:
    """Response model for model evaluation"""
    success: bool
    performance_metrics: Optional[MLPerformanceMetrics] = None
    performance_category: Optional[ModelPerformanceCategory] = None
    comparison_results: Optional[Dict[str, Any]] = None
    recommendations: List[str] = None
    message: str = ""


@dataclass
class RetrainModelsRequest:
    """Request model for retraining outdated models"""
    max_age_days: int = 30
    model_types: Optional[List[MLModelType]] = None
    force_retrain_poor_performers: bool = True
    max_concurrent_jobs: int = 3


@dataclass
class RetrainModelsResponse:
    """Response model for batch retraining"""
    success: bool
    jobs_started: List[str] = None
    models_evaluated: int = 0
    message: str = ""
    estimated_total_time_minutes: Optional[float] = None


# =============================================================================
# ML TRAINING USE CASES
# =============================================================================

class TrainModelUseCase:
    """
    Use Case for Training ML Models
    
    Orchestrates the complete model training workflow including
    job creation, training execution, and result handling.
    
    Business Rules:
    - Models can be force-retrained even if not outdated
    - Training jobs must be tracked and monitored
    - Failed training jobs should provide diagnostic information
    - Background training allows non-blocking operations
    """
    
    def __init__(self, 
                 repository: IMLAnalyticsRepository,
                 model_trainer: IMLModelTrainer,
                 event_publisher: IEventPublisher):
        self.repository = repository
        self.model_trainer = model_trainer
        self.event_publisher = event_publisher
    
    async def execute(self, request: TrainModelRequest) -> TrainModelResponse:
        """
        Execute model training workflow
        
        Args:
            request: Training request parameters
            
        Returns:
            Training response with job details
        """
        try:
            logger.info(f"Starting model training for {request.model_type.value}")
            
            # Check if model exists and needs training
            existing_models = await self.repository.models.get_by_type(request.model_type)
            current_model = None
            
            if existing_models:
                # Get latest model of this type
                current_model = max(existing_models, key=lambda m: m.created_at)
                
                # Check if retraining is needed
                if not request.force_retrain and not current_model.is_outdated():
                    return TrainModelResponse(
                        success=False,
                        message=f"Model {request.model_type.value} is not outdated and force_retrain=False"
                    )
            
            # Create new model entity
            new_model = MLModel(
                model_type=request.model_type,
                configuration=request.configuration,
                is_active=False  # Will be activated after successful training
            )
            
            # Save model entity
            model_saved = await self.repository.models.save(new_model)
            if not model_saved:
                return TrainModelResponse(
                    success=False,
                    message="Failed to save model entity"
                )
            
            # Create training job
            training_job = MLTrainingJob(
                model_id=new_model.model_id,
                model_type=request.model_type,
                status=MLJobStatus.PENDING,
                training_metadata={
                    "symbol": request.symbol,
                    "configuration": request.configuration.__dict__,
                    "force_retrain": request.force_retrain,
                    "background_training": request.background_training
                }
            )
            
            # Save training job
            job_saved = await self.repository.training_jobs.save(training_job)
            if not job_saved:
                return TrainModelResponse(
                    success=False,
                    message="Failed to save training job"
                )
            
            # Publish training started event
            await self.event_publisher.publish({
                "event_type": "ModelTrainingStarted",
                "model_id": new_model.model_id,
                "model_type": request.model_type.value,
                "job_id": training_job.job_id,
                "symbol": request.symbol,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Execute training
            if request.background_training:
                # Start background training
                asyncio.create_task(self._execute_background_training(
                    training_job, new_model, request
                ))
                
                return TrainModelResponse(
                    success=True,
                    job_id=training_job.job_id,
                    model_id=new_model.model_id,
                    message=f"Training job started in background for {request.model_type.value}",
                    estimated_completion_minutes=self._estimate_training_time(request.model_type)
                )
            else:
                # Execute synchronous training
                return await self._execute_synchronous_training(
                    training_job, new_model, request
                )
                
        except Exception as e:
            logger.error(f"Error in model training: {str(e)}")
            return TrainModelResponse(
                success=False,
                message="Internal error during model training",
                error_details={"error": str(e)}
            )
    
    async def _execute_background_training(self, 
                                         job: MLTrainingJob, 
                                         model: MLModel, 
                                         request: TrainModelRequest):
        """Execute model training in background"""
        try:
            # Update job status to running
            await self.repository.training_jobs.update_job_status(
                job.job_id, MLJobStatus.RUNNING, 0.0
            )
            
            # Execute training with progress updates
            success = await self.model_trainer.train_model(
                model_type=request.model_type,
                model_id=model.model_id,
                configuration=request.configuration,
                progress_callback=lambda progress: asyncio.create_task(
                    self.repository.training_jobs.update_job_status(
                        job.job_id, MLJobStatus.RUNNING, progress
                    )
                )
            )
            
            if success:
                # Update job as completed
                await self.repository.training_jobs.update_job_status(
                    job.job_id, MLJobStatus.COMPLETED, 100.0
                )
                
                # Update model as trained and active
                await self.repository.models.update_last_trained_at(
                    model.model_id, datetime.now(timezone.utc)
                )
                
                # Deactivate previous model
                existing_models = await self.repository.models.get_by_type(request.model_type)
                for existing_model in existing_models:
                    if existing_model.model_id != model.model_id and existing_model.is_active:
                        await self.repository.models.deactivate_model(existing_model.model_id)
                
                # Publish training completed event
                await self.event_publisher.publish({
                    "event_type": "ModelTrainingCompleted",
                    "model_id": model.model_id,
                    "model_type": request.model_type.value,
                    "job_id": job.job_id,
                    "success": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
            else:
                # Update job as failed
                await self.repository.training_jobs.update_job_status(
                    job.job_id, MLJobStatus.FAILED, None, "Training failed"
                )
                
                # Publish training failed event
                await self.event_publisher.publish({
                    "event_type": "ModelTrainingFailed",
                    "model_id": model.model_id,
                    "model_type": request.model_type.value,
                    "job_id": job.job_id,
                    "error": "Training failed",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
        except Exception as e:
            logger.error(f"Background training error: {str(e)}")
            await self.repository.training_jobs.update_job_status(
                job.job_id, MLJobStatus.FAILED, None, str(e)
            )
    
    async def _execute_synchronous_training(self, 
                                          job: MLTrainingJob, 
                                          model: MLModel, 
                                          request: TrainModelRequest) -> TrainModelResponse:
        """Execute model training synchronously"""
        try:
            # Update job status to running
            await self.repository.training_jobs.update_job_status(
                job.job_id, MLJobStatus.RUNNING, 0.0
            )
            
            # Execute training
            success = await self.model_trainer.train_model(
                model_type=request.model_type,
                model_id=model.model_id,
                configuration=request.configuration
            )
            
            if success:
                # Update job as completed
                await self.repository.training_jobs.update_job_status(
                    job.job_id, MLJobStatus.COMPLETED, 100.0
                )
                
                # Update model as trained
                await self.repository.models.update_last_trained_at(
                    model.model_id, datetime.now(timezone.utc)
                )
                
                return TrainModelResponse(
                    success=True,
                    job_id=job.job_id,
                    model_id=model.model_id,
                    message=f"Model {request.model_type.value} trained successfully"
                )
            else:
                # Update job as failed
                await self.repository.training_jobs.update_job_status(
                    job.job_id, MLJobStatus.FAILED, None, "Training failed"
                )
                
                return TrainModelResponse(
                    success=False,
                    job_id=job.job_id,
                    message="Model training failed"
                )
                
        except Exception as e:
            await self.repository.training_jobs.update_job_status(
                job.job_id, MLJobStatus.FAILED, None, str(e)
            )
            raise
    
    def _estimate_training_time(self, model_type: MLModelType) -> float:
        """Estimate training time in minutes based on model type"""
        time_estimates = {
            MLModelType.LSTM_BASIC: 15.0,
            MLModelType.LSTM_MULTI_HORIZON: 30.0,
            MLModelType.XGBOOST_SENTIMENT: 10.0,
            MLModelType.XGBOOST_FUNDAMENTAL: 10.0,
            MLModelType.LIGHTGBM_META: 5.0,
            MLModelType.ENSEMBLE_MULTI_HORIZON: 45.0,
            MLModelType.QUANTUM_ENHANCED: 60.0
        }
        return time_estimates.get(model_type, 20.0)


class EvaluateModelUseCase:
    """
    Use Case for Evaluating ML Model Performance
    
    Orchestrates model evaluation including performance metrics
    calculation, comparison with other models, and recommendations.
    """
    
    def __init__(self, 
                 repository: IMLAnalyticsRepository,
                 model_evaluator: IMLModelEvaluator,
                 event_publisher: IEventPublisher):
        self.repository = repository
        self.model_evaluator = model_evaluator
        self.event_publisher = event_publisher
    
    async def execute(self, request: ModelEvaluationRequest) -> ModelEvaluationResponse:
        """
        Execute model evaluation workflow
        
        Args:
            request: Evaluation request parameters
            
        Returns:
            Evaluation response with performance metrics
        """
        try:
            logger.info(f"Evaluating model {request.model_id}")
            
            # Get model entity
            model = await self.repository.models.get_by_id(request.model_id)
            if not model:
                return ModelEvaluationResponse(
                    success=False,
                    message=f"Model {request.model_id} not found"
                )
            
            # Check if model can make predictions
            if not model.can_make_predictions():
                return ModelEvaluationResponse(
                    success=False,
                    message=f"Model {request.model_id} is not ready for evaluation"
                )
            
            # Execute model evaluation
            performance_metrics = await self.model_evaluator.evaluate_model(
                model_id=request.model_id,
                model_type=model.model_type,
                evaluation_period_days=request.evaluation_period_days
            )
            
            if not performance_metrics:
                return ModelEvaluationResponse(
                    success=False,
                    message="Model evaluation failed"
                )
            
            # Save performance metrics
            metrics_saved = await self.repository.performance.save(performance_metrics)
            if not metrics_saved:
                logger.warning("Failed to save performance metrics")
            
            # Generate recommendations
            recommendations = self._generate_recommendations(model, performance_metrics)
            
            # Handle comparison models if requested
            comparison_results = None
            if request.comparison_models:
                comparison_results = await self._compare_models(
                    request.model_id, request.comparison_models
                )
            
            # Publish evaluation completed event
            await self.event_publisher.publish({
                "event_type": "ModelEvaluationCompleted",
                "model_id": request.model_id,
                "performance_category": performance_metrics.get_performance_category().value,
                "accuracy": performance_metrics.accuracy,
                "needs_retraining": performance_metrics.needs_retraining(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            return ModelEvaluationResponse(
                success=True,
                performance_metrics=performance_metrics,
                performance_category=performance_metrics.get_performance_category(),
                comparison_results=comparison_results,
                recommendations=recommendations,
                message="Model evaluation completed successfully"
            )
            
        except Exception as e:
            logger.error(f"Error in model evaluation: {str(e)}")
            return ModelEvaluationResponse(
                success=False,
                message="Internal error during model evaluation"
            )
    
    def _generate_recommendations(self, 
                                model: MLModel, 
                                metrics: MLPerformanceMetrics) -> List[str]:
        """Generate recommendations based on performance metrics"""
        recommendations = []
        
        if metrics.needs_retraining():
            recommendations.append("Model performance is below threshold - consider retraining")
        
        if model.is_outdated():
            recommendations.append("Model is outdated - schedule retraining")
        
        if metrics.accuracy < 0.6:
            recommendations.append("Consider adjusting hyperparameters or feature engineering")
        
        if metrics.get_performance_category() == ModelPerformanceCategory.EXCELLENT:
            recommendations.append("Model performance is excellent - consider deploying for production")
        
        return recommendations
    
    async def _compare_models(self, 
                            primary_model_id: str, 
                            comparison_model_ids: List[str]) -> Dict[str, Any]:
        """Compare model performance with other models"""
        try:
            all_model_ids = [primary_model_id] + comparison_model_ids
            performance_comparison = await self.repository.performance.compare_model_performance(all_model_ids)
            
            # Calculate relative performance
            primary_metrics = performance_comparison.get(primary_model_id)
            if not primary_metrics:
                return {"error": "Primary model metrics not found"}
            
            comparisons = {}
            for model_id, metrics in performance_comparison.items():
                if model_id != primary_model_id:
                    comparisons[model_id] = {
                        "accuracy_diff": metrics.accuracy - primary_metrics.accuracy,
                        "is_better": metrics.is_better_than(primary_metrics),
                        "performance_category": metrics.get_performance_category().value
                    }
            
            return {
                "primary_model": {
                    "id": primary_model_id,
                    "accuracy": primary_metrics.accuracy,
                    "category": primary_metrics.get_performance_category().value
                },
                "comparisons": comparisons
            }
            
        except Exception as e:
            logger.error(f"Error comparing models: {str(e)}")
            return {"error": str(e)}


class RetrainOutdatedModelsUseCase:
    """
    Use Case for Retraining Outdated Models
    
    Orchestrates batch retraining of outdated models based on
    age and performance criteria.
    """
    
    def __init__(self, 
                 repository: IMLAnalyticsRepository,
                 train_model_use_case: TrainModelUseCase):
        self.repository = repository
        self.train_model_use_case = train_model_use_case
    
    async def execute(self, request: RetrainModelsRequest) -> RetrainModelsResponse:
        """
        Execute batch model retraining workflow
        
        Args:
            request: Retraining request parameters
            
        Returns:
            Retraining response with job details
        """
        try:
            logger.info("Starting batch model retraining")
            
            # Get outdated models
            outdated_models = await self.repository.models.get_outdated_models(request.max_age_days)
            
            # Filter by model types if specified
            if request.model_types:
                outdated_models = [
                    model for model in outdated_models 
                    if model.model_type in request.model_types
                ]
            
            # Get models needing retraining based on performance
            if request.force_retrain_poor_performers:
                poor_performers = await self.repository.performance.get_models_needing_retraining()
                poor_performer_model_ids = {metrics.model_id for metrics in poor_performers}
                
                # Add poor performers to outdated list
                for model_id in poor_performer_model_ids:
                    model = await self.repository.models.get_by_id(model_id)
                    if model and model not in outdated_models:
                        outdated_models.append(model)
            
            if not outdated_models:
                return RetrainModelsResponse(
                    success=True,
                    models_evaluated=0,
                    message="No models need retraining"
                )
            
            # Start training jobs (limited by max_concurrent_jobs)
            jobs_started = []
            semaphore = asyncio.Semaphore(request.max_concurrent_jobs)
            
            async def train_model_with_limit(model: MLModel):
                async with semaphore:
                    train_request = TrainModelRequest(
                        model_type=model.model_type,
                        configuration=model.configuration,
                        symbol="BATCH_RETRAIN",
                        force_retrain=True,
                        background_training=True
                    )
                    response = await self.train_model_use_case.execute(train_request)
                    if response.success and response.job_id:
                        jobs_started.append(response.job_id)
            
            # Start all training jobs
            tasks = [train_model_with_limit(model) for model in outdated_models]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Calculate estimated total time
            estimated_total_time = len(jobs_started) * 20.0 / request.max_concurrent_jobs
            
            return RetrainModelsResponse(
                success=True,
                jobs_started=jobs_started,
                models_evaluated=len(outdated_models),
                message=f"Started retraining {len(jobs_started)} models",
                estimated_total_time_minutes=estimated_total_time
            )
            
        except Exception as e:
            logger.error(f"Error in batch retraining: {str(e)}")
            return RetrainModelsResponse(
                success=False,
                message="Internal error during batch retraining"
            )