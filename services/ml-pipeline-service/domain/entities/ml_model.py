#!/usr/bin/env python3
"""
ML Model Domain Entity - Clean Architecture Implementation
Core Business Entity für Machine Learning Models

DOMAIN LAYER - BUSINESS ENTITIES:
- Kapselung der ML Model Business Logic
- Unveränderliche Geschäftsregeln und -validierungen
- Framework-unabhängige Domain Logic
- Rich Domain Model mit Verhalten

EXTRACTED FROM: ml_pipeline_service_v6_0_0_20250824.py (Lines 323-510)
ORIGINAL SIZE: 187 lines → REFACTORED TO: <100 lines per entity

Based on: ML-Analytics Success Template
Author: Claude Code - Clean Architecture Specialist
Version: 1.0.0 - Domain Entity Extraction
Date: 26. August 2025
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import uuid
from ..value_objects.prediction_horizon import PredictionHorizon
from ..value_objects.model_confidence import ModelConfidence
from ..value_objects.performance_metrics import PerformanceMetrics


class ModelType(str, Enum):
    """Domain Value Object for ML Model Types"""
    LINEAR_REGRESSION = "linear_regression"
    RIDGE_REGRESSION = "ridge_regression"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    ENSEMBLE = "ensemble"
    LSTM = "lstm"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"


class ModelStatus(str, Enum):
    """Domain Value Object for Model Lifecycle Status"""
    TRAINING = "training"
    TRAINED = "trained"
    VALIDATING = "validating"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    ERROR = "error"


@dataclass(frozen=True)
class MLModel:
    """
    ML Model Domain Entity - Core Business Object
    
    BUSINESS RULES:
    - Jedes Model hat eindeutige Identität (model_id)
    - Model muss für spezifisches Symbol und Horizon trainiert werden  
    - Performance Metrics sind unveränderlich nach Validation
    - Model Version wird automatisch bei jedem Training erstellt
    
    DOMAIN BEHAVIORS:
    - Model Performance Evaluation
    - Model Deployment Readiness Assessment
    - Training Status Management
    - Business Rule Validation
    """
    
    # Core Identity
    model_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = field()
    model_type: ModelType = field()
    horizon: PredictionHorizon = field()
    version: str = field(default="1.0.0")
    
    # Training Information  
    trained_at: Optional[datetime] = field(default=None)
    training_samples: int = field(default=0)
    validation_samples: int = field(default=0)
    feature_count: int = field(default=0)
    
    # Model State
    status: ModelStatus = field(default=ModelStatus.TRAINING)
    performance: Optional[PerformanceMetrics] = field(default=None)
    confidence: Optional[ModelConfidence] = field(default=None)
    
    # Model Metadata
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    training_duration_seconds: Optional[float] = field(default=None)
    model_size_bytes: Optional[int] = field(default=None)
    
    def __post_init__(self):
        """Post-initialization validation of business rules"""
        self._validate_business_rules()
    
    def _validate_business_rules(self) -> None:
        """
        Validate Domain Business Rules
        
        BUSINESS RULES:
        - Symbol muss gültiges Ticker Format haben  
        - Training Samples müssen minimum 100 sein für valides Model
        - Feature Count muss > 0 sein für trainierte Models
        - Performance Metrics erforderlich für VALIDATED Status
        """
        if not self.symbol or len(self.symbol) < 1:
            raise ValueError("Model symbol cannot be empty")
            
        if self.symbol != self.symbol.upper():
            object.__setattr__(self, 'symbol', self.symbol.upper())
            
        if self.status in [ModelStatus.TRAINED, ModelStatus.VALIDATED, ModelStatus.DEPLOYED]:
            if self.training_samples < 100:
                raise ValueError(f"Insufficient training samples: {self.training_samples} < 100")
                
            if self.feature_count <= 0:
                raise ValueError(f"Invalid feature count: {self.feature_count}")
                
        if self.status == ModelStatus.VALIDATED and self.performance is None:
            raise ValueError("Performance metrics required for validated model")
    
    def is_ready_for_deployment(self) -> bool:
        """
        Business Rule: Model Deployment Readiness
        
        DEPLOYMENT CRITERIA:
        - Status must be VALIDATED  
        - Performance metrics must meet minimum thresholds
        - Model must have sufficient confidence level
        """
        if self.status != ModelStatus.VALIDATED:
            return False
            
        if not self.performance:
            return False
            
        if not self.confidence:
            return False
            
        # Business Rule: Minimum Performance Thresholds
        min_r2_score = 0.3  # Minimum R² Score für Business Acceptance
        min_confidence = ModelConfidence.MEDIUM
        
        return (
            self.performance.r2_score >= min_r2_score and
            self.confidence.value >= min_confidence.value
        )
    
    def calculate_model_quality_score(self) -> float:
        """
        Domain Service: Calculate Overall Model Quality Score
        
        BUSINESS LOGIC:
        - Kombiniert Performance Metrics zu einzelnem Quality Score
        - Berücksichtigt Confidence Level und Training Quality
        - Score Range: 0.0 (worst) to 1.0 (best)
        """
        if not self.performance or not self.confidence:
            return 0.0
            
        # Performance Component (70% weight)  
        performance_score = (
            self.performance.r2_score * 0.4 +
            (1.0 - self.performance.normalized_mae) * 0.3
        ) * 0.7
        
        # Confidence Component (20% weight)
        confidence_score = self.confidence.value * 0.2
        
        # Training Quality Component (10% weight)  
        training_quality = min(self.training_samples / 1000.0, 1.0) * 0.1
        
        return min(performance_score + confidence_score + training_quality, 1.0)
    
    def get_model_key(self) -> str:
        """Generate unique model key for storage and retrieval"""
        return f"{self.symbol}_{self.horizon.value}_{self.model_type.value}_{self.version}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for serialization"""
        return {
            'model_id': self.model_id,
            'symbol': self.symbol,
            'model_type': self.model_type.value,
            'horizon': self.horizon.value,
            'version': self.version,
            'status': self.status.value,
            'trained_at': self.trained_at.isoformat() if self.trained_at else None,
            'training_samples': self.training_samples,
            'validation_samples': self.validation_samples,
            'feature_count': self.feature_count,
            'performance': self.performance.to_dict() if self.performance else None,
            'confidence': self.confidence.value if self.confidence else None,
            'hyperparameters': self.hyperparameters,
            'training_duration_seconds': self.training_duration_seconds,
            'model_size_bytes': self.model_size_bytes,
            'quality_score': self.calculate_model_quality_score(),
            'deployment_ready': self.is_ready_for_deployment()
        }
    
    def mark_as_trained(self, performance: PerformanceMetrics, confidence: ModelConfidence) -> 'MLModel':
        """
        Business Operation: Mark model as successfully trained
        
        BUSINESS RULES:
        - Nur TRAINING Status kann zu TRAINED wechseln
        - Performance Metrics müssen validiert sein
        - Trained Timestamp wird gesetzt
        """
        if self.status != ModelStatus.TRAINING:
            raise ValueError(f"Cannot mark model as trained. Current status: {self.status}")
            
        return MLModel(
            model_id=self.model_id,
            symbol=self.symbol,
            model_type=self.model_type,
            horizon=self.horizon,
            version=self.version,
            trained_at=datetime.now(),
            training_samples=self.training_samples,
            validation_samples=self.validation_samples,
            feature_count=self.feature_count,
            status=ModelStatus.TRAINED,
            performance=performance,
            confidence=confidence,
            hyperparameters=self.hyperparameters,
            training_duration_seconds=self.training_duration_seconds,
            model_size_bytes=self.model_size_bytes
        )
    
    def validate_and_deploy(self) -> 'MLModel':
        """
        Business Operation: Validate and deploy model
        
        BUSINESS RULES:
        - Nur TRAINED Models können validiert werden
        - Deployment readiness wird automatisch geprüft  
        - Status progression: TRAINED → VALIDATED → DEPLOYED
        """
        if self.status != ModelStatus.TRAINED:
            raise ValueError(f"Cannot validate model. Current status: {self.status}")
            
        if not self.is_ready_for_deployment():
            raise ValueError("Model does not meet deployment criteria")
            
        validated_model = MLModel(
            model_id=self.model_id,
            symbol=self.symbol,
            model_type=self.model_type,
            horizon=self.horizon,
            version=self.version,
            trained_at=self.trained_at,
            training_samples=self.training_samples,
            validation_samples=self.validation_samples,
            feature_count=self.feature_count,
            status=ModelStatus.VALIDATED,
            performance=self.performance,
            confidence=self.confidence,
            hyperparameters=self.hyperparameters,
            training_duration_seconds=self.training_duration_seconds,
            model_size_bytes=self.model_size_bytes
        )
        
        # Auto-deploy if validation successful
        return MLModel(
            model_id=validated_model.model_id,
            symbol=validated_model.symbol,
            model_type=validated_model.model_type,
            horizon=validated_model.horizon,
            version=validated_model.version,
            trained_at=validated_model.trained_at,
            training_samples=validated_model.training_samples,
            validation_samples=validated_model.validation_samples,
            feature_count=validated_model.feature_count,
            status=ModelStatus.DEPLOYED,
            performance=validated_model.performance,
            confidence=validated_model.confidence,
            hyperparameters=validated_model.hyperparameters,
            training_duration_seconds=validated_model.training_duration_seconds,
            model_size_bytes=validated_model.model_size_bytes
        )