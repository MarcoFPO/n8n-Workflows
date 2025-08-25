#!/usr/bin/env python3
"""
Service API Patterns v1.0.0 - Clean Architecture
Spezifische API-Patterns für verschiedene Service-Typen

SHARED INFRASTRUCTURE - SERVICE API PATTERNS:
- ML Analytics API Pattern (Training, Prediction, Evaluation)
- Data Processing API Pattern (ETL, Transform, Storage)
- Tracking/Monitoring API Pattern (Metrics, Events, History)
- Business Logic API Pattern (Rules, Workflows, Operations)
- Integration API Pattern (External Services, Webhooks)

DESIGN PATTERNS:
- Template Method Pattern: Service-spezifische API-Templates
- Strategy Pattern: Verschiedene API-Strategien pro Domain
- Factory Pattern: API Endpoint Generation
- Observer Pattern: Event-driven API Patterns

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Path
from fastapi.responses import StreamingResponse

from api_standards_framework_v1_0_0_20250825 import (
    APIEndpointBuilder,
    APIStandards,
    StandardItemResponse,
    StandardListResponse,
    StandardMetadata,
    PaginationRequest,
    SortRequest,
    FilterRequest
)


# =============================================================================
# ML ANALYTICS API PATTERN
# =============================================================================

class MLModelStatus(str, Enum):
    """ML Model Status Enumeration"""
    TRAINING = "training"
    TRAINED = "trained"
    EVALUATING = "evaluating"
    READY = "ready"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class MLTrainingRequest(BaseModel):
    """Standard ML Training Request"""
    symbol: str = Field(..., description="Stock symbol")
    model_type: str = Field(..., description="Type of ML model")
    features: List[str] = Field(..., description="Feature columns")
    target: str = Field(..., description="Target variable")
    hyperparameters: Dict[str, Any] = Field(default={}, description="Model hyperparameters")
    training_data_start: datetime = Field(..., description="Training data start date")
    training_data_end: datetime = Field(..., description="Training data end date")


class MLPredictionRequest(BaseModel):
    """Standard ML Prediction Request"""
    symbol: str = Field(..., description="Stock symbol")
    model_type: Optional[str] = Field(None, description="Preferred model type")
    prediction_horizon: int = Field(default=1, description="Prediction horizon in days")
    features: Optional[Dict[str, Any]] = Field(None, description="Input features")
    confidence_threshold: float = Field(default=0.5, description="Minimum confidence threshold")


class MLBatchPredictionRequest(BaseModel):
    """Standard Batch ML Prediction Request"""
    symbols: List[str] = Field(..., description="List of stock symbols")
    model_type: Optional[str] = Field(None, description="Preferred model type")
    prediction_horizon: int = Field(default=1, description="Prediction horizon in days")
    features: Optional[Dict[str, Any]] = Field(None, description="Common input features")


class MLEvaluationRequest(BaseModel):
    """Standard ML Evaluation Request"""
    model_id: str = Field(..., description="Model ID to evaluate")
    test_data_start: datetime = Field(..., description="Test data start date")
    test_data_end: datetime = Field(..., description="Test data end date")
    metrics: List[str] = Field(default=["accuracy", "precision", "recall"], description="Evaluation metrics")


class MLAnalyticsAPIPattern:
    """API Pattern für ML Analytics Services"""
    
    def __init__(self, service_name: str, standards: APIStandards = None):
        self.service_name = service_name
        self.standards = standards or APIStandards()
        self.builder = APIEndpointBuilder(service_name, standards)
    
    def build_training_endpoints(self, controller: callable) -> APIRouter:
        """Build ML Training Endpoints"""
        
        # Train Model
        @self.builder.router.post(
            f"{self.standards.base_path}/{self.standards.current_version}/models/train",
            tags=["ML Training"],
            summary="Train ML Model",
            description="Train new ML model with specified parameters"
        )
        async def train_model(
            request: MLTrainingRequest,
            background_tasks: BackgroundTasks
        ):
            # Start training as background task for long-running operations
            task_id = await controller.start_training(request, background_tasks)
            return StandardItemResponse(
                data={"task_id": task_id, "status": "training_started"},
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        # Evaluate Model
        @self.builder.router.post(
            f"{self.standards.base_path}/{self.standards.current_version}/models/{{model_id}}/evaluate",
            tags=["ML Training"],
            summary="Evaluate ML Model",
            description="Evaluate trained ML model performance"
        )
        async def evaluate_model(
            model_id: str = Path(..., description="Model ID"),
            request: MLEvaluationRequest = None
        ):
            result = await controller.evaluate_model(model_id, request)
            return StandardItemResponse(
                data=result,
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        # Retrain Outdated Models
        @self.builder.router.post(
            f"{self.standards.base_path}/{self.standards.current_version}/models/retrain",
            tags=["ML Training"],
            summary="Retrain Models",
            description="Retrain all outdated models"
        )
        async def retrain_models(background_tasks: BackgroundTasks):
            task_id = await controller.retrain_outdated_models(background_tasks)
            return StandardItemResponse(
                data={"task_id": task_id, "status": "retraining_started"},
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        return self.builder.get_router()
    
    def build_prediction_endpoints(self, controller: callable) -> APIRouter:
        """Build ML Prediction Endpoints"""
        
        # Generate Prediction
        @self.builder.router.post(
            f"{self.standards.base_path}/{self.standards.current_version}/predictions/generate",
            tags=["ML Predictions"],
            summary="Generate Prediction",
            description="Generate ML prediction for specified symbol"
        )
        async def generate_prediction(request: MLPredictionRequest):
            result = await controller.generate_prediction(request)
            return StandardItemResponse(
                data=result,
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        # Batch Predictions
        @self.builder.router.post(
            f"{self.standards.base_path}/{self.standards.current_version}/predictions/batch",
            tags=["ML Predictions"],
            summary="Batch Predictions",
            description="Generate predictions for multiple symbols"
        )
        async def batch_predictions(request: MLBatchPredictionRequest):
            result = await controller.generate_batch_predictions(request)
            return StandardItemResponse(
                data=result,
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        # Prediction History
        @self.builder.router.get(
            f"{self.standards.base_path}/{self.standards.current_version}/predictions/{{symbol}}/history",
            tags=["ML Predictions"],
            summary="Prediction History",
            description="Get historical predictions for symbol"
        )
        async def get_prediction_history(
            symbol: str = Path(..., description="Stock symbol"),
            pagination: PaginationRequest = Depends()
        ):
            result = await controller.get_prediction_history(symbol, pagination)
            return StandardListResponse(
                data=result.get("predictions", []),
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                ),
                pagination=result.get("pagination")
            )
        
        return self.builder.get_router()


# =============================================================================
# DATA PROCESSING API PATTERN
# =============================================================================

class DataProcessingJobRequest(BaseModel):
    """Standard Data Processing Job Request"""
    job_type: str = Field(..., description="Type of processing job")
    input_sources: List[str] = Field(..., description="Input data sources")
    output_destination: str = Field(..., description="Output destination")
    parameters: Dict[str, Any] = Field(default={}, description="Processing parameters")
    schedule: Optional[str] = Field(None, description="Cron schedule expression")


class DataTransformRequest(BaseModel):
    """Standard Data Transform Request"""
    source_format: str = Field(..., description="Source data format")
    target_format: str = Field(..., description="Target data format")
    transformation_rules: List[Dict[str, Any]] = Field(..., description="Transformation rules")
    validation_rules: List[Dict[str, Any]] = Field(default=[], description="Validation rules")


class DataProcessingAPIPattern:
    """API Pattern für Data Processing Services"""
    
    def __init__(self, service_name: str, standards: APIStandards = None):
        self.service_name = service_name
        self.standards = standards or APIStandards()
        self.builder = APIEndpointBuilder(service_name, standards)
    
    def build_processing_endpoints(self, controller: callable) -> APIRouter:
        """Build Data Processing Endpoints"""
        
        # Start Processing Job
        @self.builder.router.post(
            f"{self.standards.base_path}/{self.standards.current_version}/jobs/start",
            tags=["Data Processing"],
            summary="Start Processing Job",
            description="Start new data processing job"
        )
        async def start_processing_job(
            request: DataProcessingJobRequest,
            background_tasks: BackgroundTasks
        ):
            job_id = await controller.start_processing_job(request, background_tasks)
            return StandardItemResponse(
                data={"job_id": job_id, "status": "started"},
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        # Get Job Status
        @self.builder.router.get(
            f"{self.standards.base_path}/{self.standards.current_version}/jobs/{{job_id}}/status",
            tags=["Data Processing"],
            summary="Get Job Status",
            description="Get processing job status and progress"
        )
        async def get_job_status(job_id: str = Path(..., description="Job ID")):
            result = await controller.get_job_status(job_id)
            return StandardItemResponse(
                data=result,
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        # Transform Data
        @self.builder.router.post(
            f"{self.standards.base_path}/{self.standards.current_version}/transform",
            tags=["Data Processing"],
            summary="Transform Data",
            description="Transform data according to specified rules"
        )
        async def transform_data(request: DataTransformRequest):
            result = await controller.transform_data(request)
            return StandardItemResponse(
                data=result,
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        # Stream Processing Results
        @self.builder.router.get(
            f"{self.standards.base_path}/{self.standards.current_version}/jobs/{{job_id}}/stream",
            tags=["Data Processing"],
            summary="Stream Job Results",
            description="Stream processing job results"
        )
        async def stream_job_results(job_id: str = Path(..., description="Job ID")):
            async def generate():
                async for chunk in controller.stream_job_results(job_id):
                    yield chunk
            
            return StreamingResponse(generate(), media_type="application/json")
        
        return self.builder.get_router()


# =============================================================================
# TRACKING/MONITORING API PATTERN
# =============================================================================

class TrackingEventRequest(BaseModel):
    """Standard Tracking Event Request"""
    event_type: str = Field(..., description="Type of event")
    entity_id: str = Field(..., description="ID of tracked entity")
    event_data: Dict[str, Any] = Field(..., description="Event data")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Event timestamp")
    tags: List[str] = Field(default=[], description="Event tags")


class MetricsQuery(BaseModel):
    """Standard Metrics Query"""
    metrics: List[str] = Field(..., description="Metric names to query")
    entity_id: Optional[str] = Field(None, description="Filter by entity ID")
    start_time: datetime = Field(..., description="Query start time")
    end_time: datetime = Field(..., description="Query end time")
    aggregation: str = Field(default="avg", description="Aggregation method")
    interval: Optional[str] = Field(None, description="Time interval for grouping")


class TrackingAPIPattern:
    """API Pattern für Tracking/Monitoring Services"""
    
    def __init__(self, service_name: str, standards: APIStandards = None):
        self.service_name = service_name
        self.standards = standards or APIStandards()
        self.builder = APIEndpointBuilder(service_name, standards)
    
    def build_tracking_endpoints(self, controller: callable) -> APIRouter:
        """Build Tracking Endpoints"""
        
        # Track Event
        @self.builder.router.post(
            f"{self.standards.base_path}/{self.standards.current_version}/events/track",
            tags=["Tracking"],
            summary="Track Event",
            description="Track a new event"
        )
        async def track_event(request: TrackingEventRequest):
            result = await controller.track_event(request)
            return StandardItemResponse(
                data=result,
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        # Query Metrics
        @self.builder.router.post(
            f"{self.standards.base_path}/{self.standards.current_version}/metrics/query",
            tags=["Metrics"],
            summary="Query Metrics",
            description="Query metrics data with time range and filters"
        )
        async def query_metrics(request: MetricsQuery):
            result = await controller.query_metrics(request)
            return StandardItemResponse(
                data=result,
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        # Get Entity History
        @self.builder.router.get(
            f"{self.standards.base_path}/{self.standards.current_version}/entities/{{entity_id}}/history",
            tags=["Tracking"],
            summary="Get Entity History",
            description="Get tracking history for specific entity"
        )
        async def get_entity_history(
            entity_id: str = Path(..., description="Entity ID"),
            pagination: PaginationRequest = Depends(),
            event_type: Optional[str] = Query(None, description="Filter by event type")
        ):
            result = await controller.get_entity_history(entity_id, pagination, event_type)
            return StandardListResponse(
                data=result.get("events", []),
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                ),
                pagination=result.get("pagination")
            )
        
        return self.builder.get_router()


# =============================================================================
# BUSINESS LOGIC API PATTERN
# =============================================================================

class BusinessRuleRequest(BaseModel):
    """Standard Business Rule Request"""
    rule_type: str = Field(..., description="Type of business rule")
    entity_type: str = Field(..., description="Entity type to apply rule to")
    conditions: List[Dict[str, Any]] = Field(..., description="Rule conditions")
    actions: List[Dict[str, Any]] = Field(..., description="Rule actions")
    priority: int = Field(default=0, description="Rule priority")
    active: bool = Field(default=True, description="Rule active status")


class BusinessWorkflowRequest(BaseModel):
    """Standard Business Workflow Request"""
    workflow_type: str = Field(..., description="Type of workflow")
    input_data: Dict[str, Any] = Field(..., description="Workflow input data")
    configuration: Dict[str, Any] = Field(default={}, description="Workflow configuration")
    callback_url: Optional[str] = Field(None, description="Callback URL for completion notification")


class BusinessLogicAPIPattern:
    """API Pattern für Business Logic Services"""
    
    def __init__(self, service_name: str, standards: APIStandards = None):
        self.service_name = service_name
        self.standards = standards or APIStandards()
        self.builder = APIEndpointBuilder(service_name, standards)
    
    def build_business_endpoints(self, controller: callable) -> APIRouter:
        """Build Business Logic Endpoints"""
        
        # Execute Business Rule
        @self.builder.router.post(
            f"{self.standards.base_path}/{self.standards.current_version}/rules/execute",
            tags=["Business Rules"],
            summary="Execute Business Rule",
            description="Execute business rule against provided data"
        )
        async def execute_business_rule(request: BusinessRuleRequest):
            result = await controller.execute_business_rule(request)
            return StandardItemResponse(
                data=result,
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        # Start Workflow
        @self.builder.router.post(
            f"{self.standards.base_path}/{self.standards.current_version}/workflows/start",
            tags=["Workflows"],
            summary="Start Workflow",
            description="Start business workflow execution"
        )
        async def start_workflow(
            request: BusinessWorkflowRequest,
            background_tasks: BackgroundTasks
        ):
            workflow_id = await controller.start_workflow(request, background_tasks)
            return StandardItemResponse(
                data={"workflow_id": workflow_id, "status": "started"},
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        # Get Workflow Status
        @self.builder.router.get(
            f"{self.standards.base_path}/{self.standards.current_version}/workflows/{{workflow_id}}/status",
            tags=["Workflows"],
            summary="Get Workflow Status",
            description="Get workflow execution status and progress"
        )
        async def get_workflow_status(workflow_id: str = Path(..., description="Workflow ID")):
            result = await controller.get_workflow_status(workflow_id)
            return StandardItemResponse(
                data=result,
                metadata=StandardMetadata(
                    service=self.service_name,
                    version=self.standards.current_version
                )
            )
        
        return self.builder.get_router()


# =============================================================================
# PATTERN FACTORY
# =============================================================================

class ServiceAPIPatternFactory:
    """Factory für Service API Patterns"""
    
    @staticmethod
    def create_ml_analytics_pattern(
        service_name: str, 
        standards: APIStandards = None
    ) -> MLAnalyticsAPIPattern:
        """Create ML Analytics API Pattern"""
        return MLAnalyticsAPIPattern(service_name, standards)
    
    @staticmethod
    def create_data_processing_pattern(
        service_name: str,
        standards: APIStandards = None
    ) -> DataProcessingAPIPattern:
        """Create Data Processing API Pattern"""
        return DataProcessingAPIPattern(service_name, standards)
    
    @staticmethod
    def create_tracking_pattern(
        service_name: str,
        standards: APIStandards = None
    ) -> TrackingAPIPattern:
        """Create Tracking API Pattern"""
        return TrackingAPIPattern(service_name, standards)
    
    @staticmethod
    def create_business_logic_pattern(
        service_name: str,
        standards: APIStandards = None
    ) -> BusinessLogicAPIPattern:
        """Create Business Logic API Pattern"""
        return BusinessLogicAPIPattern(service_name, standards)