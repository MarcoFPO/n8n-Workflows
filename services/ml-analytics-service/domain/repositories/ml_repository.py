#!/usr/bin/env python3
"""
ML Analytics Repository Interfaces - Clean Architecture v6.0.0
Repository Pattern Interfaces for Machine Learning Operations

DOMAIN LAYER - REPOSITORY INTERFACES:
- IMLModelRepository: ML model persistence operations
- IMLPredictionRepository: Prediction storage and retrieval
- IMLTrainingJobRepository: Training job lifecycle management
- IMLPerformanceRepository: Performance metrics storage
- IMLRiskRepository: Risk metrics persistence

DESIGN PATTERNS IMPLEMENTED:
- Repository Pattern: Abstract data access layer
- Interface Segregation: Specific interfaces for different concerns
- Dependency Inversion: Domain defines interfaces, infrastructure implements

SOLID PRINCIPLES:
- Interface Segregation: Focused, minimal interfaces
- Dependency Inversion: Domain owns the interfaces
- Single Responsibility: Each repository has one data concern

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal

from ..entities.ml_entities import (
    MLModel,
    MLPrediction,
    MLTrainingJob,
    MLPerformanceMetrics,
    MLRiskMetrics,
    MLModelType,
    MLJobStatus,
    MLPredictionHorizon,
    ModelPerformanceCategory
)


# =============================================================================
# REPOSITORY INTERFACES
# =============================================================================

class IMLModelRepository(ABC):
    """
    ML Model Repository Interface
    
    Defines contract for ML model persistence operations
    following Repository Pattern principles.
    """
    
    @abstractmethod
    async def save(self, model: MLModel) -> bool:
        """
        Save or update ML model
        
        Args:
            model: ML model entity to save
            
        Returns:
            True if save was successful
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, model_id: str) -> Optional[MLModel]:
        """
        Retrieve ML model by ID
        
        Args:
            model_id: Unique model identifier
            
        Returns:
            ML model entity or None if not found
        """
        pass
    
    @abstractmethod
    async def get_by_type(self, model_type: MLModelType) -> List[MLModel]:
        """
        Retrieve all models of specific type
        
        Args:
            model_type: Type of ML models to retrieve
            
        Returns:
            List of ML model entities
        """
        pass
    
    @abstractmethod
    async def get_active_models(self) -> List[MLModel]:
        """
        Retrieve all active ML models
        
        Returns:
            List of active ML model entities
        """
        pass
    
    @abstractmethod
    async def get_outdated_models(self, max_age_days: int = 30) -> List[MLModel]:
        """
        Retrieve outdated models that need retraining
        
        Args:
            max_age_days: Maximum age in days before model is outdated
            
        Returns:
            List of outdated ML model entities
        """
        pass
    
    @abstractmethod
    async def update_last_trained_at(self, model_id: str, trained_at: datetime) -> bool:
        """
        Update model's last training timestamp
        
        Args:
            model_id: Model identifier
            trained_at: Training completion timestamp
            
        Returns:
            True if update was successful
        """
        pass
    
    @abstractmethod
    async def deactivate_model(self, model_id: str) -> bool:
        """
        Deactivate ML model
        
        Args:
            model_id: Model identifier to deactivate
            
        Returns:
            True if deactivation was successful
        """
        pass
    
    @abstractmethod
    async def delete(self, model_id: str) -> bool:
        """
        Delete ML model
        
        Args:
            model_id: Model identifier to delete
            
        Returns:
            True if deletion was successful
        """
        pass
    
    @abstractmethod
    async def get_model_versions(self, model_type: MLModelType) -> List[MLModel]:
        """
        Get all versions of specific model type
        
        Args:
            model_type: Type of model
            
        Returns:
            List of model versions ordered by creation date
        """
        pass


class IMLPredictionRepository(ABC):
    """
    ML Prediction Repository Interface
    
    Defines contract for ML prediction persistence operations.
    """
    
    @abstractmethod
    async def save(self, prediction: MLPrediction) -> bool:
        """
        Save ML prediction
        
        Args:
            prediction: ML prediction entity to save
            
        Returns:
            True if save was successful
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, prediction_id: str) -> Optional[MLPrediction]:
        """
        Retrieve prediction by ID
        
        Args:
            prediction_id: Unique prediction identifier
            
        Returns:
            ML prediction entity or None if not found
        """
        pass
    
    @abstractmethod
    async def get_by_symbol(self, symbol: str, limit: int = 100) -> List[MLPrediction]:
        """
        Retrieve predictions for specific symbol
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of predictions to return
            
        Returns:
            List of ML prediction entities ordered by creation date
        """
        pass
    
    @abstractmethod
    async def get_by_model(self, model_id: str, limit: int = 100) -> List[MLPrediction]:
        """
        Retrieve predictions from specific model
        
        Args:
            model_id: Model identifier
            limit: Maximum number of predictions to return
            
        Returns:
            List of ML prediction entities
        """
        pass
    
    @abstractmethod
    async def get_high_confidence_predictions(self, 
                                            min_confidence: float = 0.8, 
                                            limit: int = 50) -> List[MLPrediction]:
        """
        Retrieve high confidence predictions
        
        Args:
            min_confidence: Minimum confidence threshold
            limit: Maximum number of predictions to return
            
        Returns:
            List of high confidence predictions
        """
        pass
    
    @abstractmethod
    async def get_expired_predictions(self) -> List[MLPrediction]:
        """
        Retrieve expired predictions for cleanup
        
        Returns:
            List of expired prediction entities
        """
        pass
    
    @abstractmethod
    async def get_predictions_by_horizon(self, 
                                       horizon: MLPredictionHorizon, 
                                       limit: int = 100) -> List[MLPrediction]:
        """
        Retrieve predictions by horizon type
        
        Args:
            horizon: Prediction horizon
            limit: Maximum number of predictions
            
        Returns:
            List of predictions for specific horizon
        """
        pass
    
    @abstractmethod
    async def get_recent_predictions(self, 
                                   hours: int = 24, 
                                   limit: int = 100) -> List[MLPrediction]:
        """
        Retrieve recent predictions
        
        Args:
            hours: Hours back to search
            limit: Maximum number of predictions
            
        Returns:
            List of recent predictions
        """
        pass
    
    @abstractmethod
    async def delete_expired_predictions(self) -> int:
        """
        Delete expired predictions
        
        Returns:
            Number of predictions deleted
        """
        pass


class IMLTrainingJobRepository(ABC):
    """
    ML Training Job Repository Interface
    
    Defines contract for training job lifecycle management.
    """
    
    @abstractmethod
    async def save(self, job: MLTrainingJob) -> bool:
        """
        Save or update training job
        
        Args:
            job: Training job entity to save
            
        Returns:
            True if save was successful
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, job_id: str) -> Optional[MLTrainingJob]:
        """
        Retrieve training job by ID
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Training job entity or None if not found
        """
        pass
    
    @abstractmethod
    async def get_by_status(self, status: MLJobStatus) -> List[MLTrainingJob]:
        """
        Retrieve training jobs by status
        
        Args:
            status: Job status to filter by
            
        Returns:
            List of training jobs with specified status
        """
        pass
    
    @abstractmethod
    async def get_running_jobs(self) -> List[MLTrainingJob]:
        """
        Retrieve all running training jobs
        
        Returns:
            List of running training job entities
        """
        pass
    
    @abstractmethod
    async def get_failed_jobs(self) -> List[MLTrainingJob]:
        """
        Retrieve failed training jobs that can be retried
        
        Returns:
            List of failed training job entities
        """
        pass
    
    @abstractmethod
    async def update_job_status(self, 
                              job_id: str, 
                              status: MLJobStatus, 
                              progress: float = None,
                              error_message: str = None) -> bool:
        """
        Update job status and progress
        
        Args:
            job_id: Job identifier
            status: New job status
            progress: Optional progress percentage
            error_message: Optional error message for failed jobs
            
        Returns:
            True if update was successful
        """
        pass
    
    @abstractmethod
    async def get_jobs_by_model_type(self, model_type: MLModelType) -> List[MLTrainingJob]:
        """
        Retrieve jobs for specific model type
        
        Args:
            model_type: Type of model
            
        Returns:
            List of training jobs for the model type
        """
        pass
    
    @abstractmethod
    async def get_job_history(self, 
                            model_id: str, 
                            limit: int = 10) -> List[MLTrainingJob]:
        """
        Get training history for specific model
        
        Args:
            model_id: Model identifier
            limit: Maximum number of jobs to return
            
        Returns:
            List of training jobs ordered by creation date
        """
        pass


class IMLPerformanceRepository(ABC):
    """
    ML Performance Repository Interface
    
    Defines contract for model performance metrics persistence.
    """
    
    @abstractmethod
    async def save(self, metrics: MLPerformanceMetrics) -> bool:
        """
        Save performance metrics
        
        Args:
            metrics: Performance metrics entity to save
            
        Returns:
            True if save was successful
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, metrics_id: str) -> Optional[MLPerformanceMetrics]:
        """
        Retrieve performance metrics by ID
        
        Args:
            metrics_id: Unique metrics identifier
            
        Returns:
            Performance metrics entity or None if not found
        """
        pass
    
    @abstractmethod
    async def get_by_model(self, model_id: str) -> List[MLPerformanceMetrics]:
        """
        Retrieve all performance metrics for specific model
        
        Args:
            model_id: Model identifier
            
        Returns:
            List of performance metrics ordered by evaluation date
        """
        pass
    
    @abstractmethod
    async def get_latest_performance(self, model_id: str) -> Optional[MLPerformanceMetrics]:
        """
        Get latest performance metrics for model
        
        Args:
            model_id: Model identifier
            
        Returns:
            Latest performance metrics or None if not found
        """
        pass
    
    @abstractmethod
    async def get_by_performance_category(self, 
                                        category: ModelPerformanceCategory) -> List[MLPerformanceMetrics]:
        """
        Retrieve performance metrics by category
        
        Args:
            category: Performance category to filter by
            
        Returns:
            List of performance metrics in specified category
        """
        pass
    
    @abstractmethod
    async def get_models_needing_retraining(self) -> List[MLPerformanceMetrics]:
        """
        Get models that need retraining based on performance
        
        Returns:
            List of performance metrics for models needing retraining
        """
        pass
    
    @abstractmethod
    async def get_performance_trends(self, 
                                   model_id: str, 
                                   days: int = 30) -> List[MLPerformanceMetrics]:
        """
        Get performance trends for model over time
        
        Args:
            model_id: Model identifier
            days: Number of days to look back
            
        Returns:
            List of performance metrics for trend analysis
        """
        pass
    
    @abstractmethod
    async def compare_model_performance(self, 
                                      model_ids: List[str]) -> Dict[str, MLPerformanceMetrics]:
        """
        Compare performance metrics across models
        
        Args:
            model_ids: List of model identifiers to compare
            
        Returns:
            Dictionary mapping model IDs to their latest performance metrics
        """
        pass


class IMLRiskRepository(ABC):
    """
    ML Risk Repository Interface
    
    Defines contract for risk metrics persistence operations.
    """
    
    @abstractmethod
    async def save(self, risk_metrics: MLRiskMetrics) -> bool:
        """
        Save risk metrics
        
        Args:
            risk_metrics: Risk metrics entity to save
            
        Returns:
            True if save was successful
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, risk_id: str) -> Optional[MLRiskMetrics]:
        """
        Retrieve risk metrics by ID
        
        Args:
            risk_id: Unique risk metrics identifier
            
        Returns:
            Risk metrics entity or None if not found
        """
        pass
    
    @abstractmethod
    async def get_by_prediction(self, prediction_id: str) -> Optional[MLRiskMetrics]:
        """
        Retrieve risk metrics for specific prediction
        
        Args:
            prediction_id: Prediction identifier
            
        Returns:
            Risk metrics entity or None if not found
        """
        pass
    
    @abstractmethod
    async def get_by_symbol(self, symbol: str, limit: int = 100) -> List[MLRiskMetrics]:
        """
        Retrieve risk metrics for specific symbol
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of risk metrics to return
            
        Returns:
            List of risk metrics entities
        """
        pass
    
    @abstractmethod
    async def get_high_risk_predictions(self, 
                                      min_risk_score: float = 7.0) -> List[MLRiskMetrics]:
        """
        Retrieve high risk predictions
        
        Args:
            min_risk_score: Minimum risk score threshold
            
        Returns:
            List of high risk metrics
        """
        pass
    
    @abstractmethod
    async def get_risk_distribution(self) -> Dict[str, int]:
        """
        Get risk score distribution across all predictions
        
        Returns:
            Dictionary mapping risk categories to counts
        """
        pass
    
    @abstractmethod
    async def get_portfolio_risk_metrics(self, 
                                       symbols: List[str]) -> List[MLRiskMetrics]:
        """
        Get risk metrics for portfolio symbols
        
        Args:
            symbols: List of symbols in portfolio
            
        Returns:
            List of risk metrics for portfolio analysis
        """
        pass
    
    @abstractmethod
    async def calculate_portfolio_var(self, 
                                    symbols: List[str], 
                                    weights: List[float]) -> Dict[str, Decimal]:
        """
        Calculate portfolio Value at Risk
        
        Args:
            symbols: Portfolio symbols
            weights: Position weights
            
        Returns:
            Dictionary with portfolio VaR metrics
        """
        pass
    
    @abstractmethod
    async def get_correlation_matrix(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Get correlation matrix for symbols
        
        Args:
            symbols: List of symbols
            
        Returns:
            Correlation matrix as nested dictionary
        """
        pass


# =============================================================================
# AGGREGATE REPOSITORY INTERFACE
# =============================================================================

class IMLAnalyticsRepository(ABC):
    """
    Aggregate ML Analytics Repository Interface
    
    Provides unified access to all ML-related repositories
    following Aggregate Root pattern.
    """
    
    @property
    @abstractmethod
    def models(self) -> IMLModelRepository:
        """Get ML model repository"""
        pass
    
    @property
    @abstractmethod
    def predictions(self) -> IMLPredictionRepository:
        """Get ML prediction repository"""
        pass
    
    @property
    @abstractmethod
    def training_jobs(self) -> IMLTrainingJobRepository:
        """Get training job repository"""
        pass
    
    @property
    @abstractmethod
    def performance(self) -> IMLPerformanceRepository:
        """Get performance metrics repository"""
        pass
    
    @property
    @abstractmethod
    def risk(self) -> IMLRiskRepository:
        """Get risk metrics repository"""
        pass
    
    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get repository health status
        
        Returns:
            Dictionary with health information for all repositories
        """
        pass
    
    @abstractmethod
    async def initialize_schemas(self) -> bool:
        """
        Initialize database schemas for all repositories
        
        Returns:
            True if initialization was successful
        """
        pass
    
    @abstractmethod
    async def cleanup_old_data(self, days: int = 90) -> Dict[str, int]:
        """
        Cleanup old data from all repositories
        
        Args:
            days: Number of days to retain
            
        Returns:
            Dictionary with cleanup statistics per repository
        """
        pass