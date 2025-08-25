#!/usr/bin/env python3
"""
ML Service Provider Interfaces - Clean Architecture v6.0.0
External Service Interfaces for Machine Learning Operations

APPLICATION LAYER - SERVICE INTERFACES:
- IMLModelTrainer: Interface for model training operations
- IMLPredictor: Interface for prediction generation
- IMLModelEvaluator: Interface for model performance evaluation
- IRiskCalculator: Interface for risk metrics calculation
- IFeatureEngineer: Interface for feature engineering operations

DESIGN PATTERNS IMPLEMENTED:
- Interface Segregation Principle: Focused, specific interfaces
- Dependency Inversion Principle: Application defines interfaces
- Adapter Pattern: External services implement interfaces
- Strategy Pattern: Pluggable ML implementations

Autor: Claude Code - Architecture Modernization Specialist
Datum: 25. August 2025
Version: 6.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from decimal import Decimal
from datetime import datetime

from ...domain.entities.ml_entities import (
    MLModel,
    MLPrediction,
    MLPerformanceMetrics,
    MLRiskMetrics,
    MLModelType,
    MLPredictionHorizon,
    ModelConfiguration
)


# =============================================================================
# ML MODEL TRAINING INTERFACE
# =============================================================================

class IMLModelTrainer(ABC):
    """
    Interface for ML Model Training Operations
    
    Defines contract for training different types of ML models
    with progress tracking and validation capabilities.
    """
    
    @abstractmethod
    async def train_model(self, 
                        model_type: MLModelType,
                        model_id: str,
                        configuration: ModelConfiguration,
                        progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        """
        Train ML model with specified configuration
        
        Args:
            model_type: Type of ML model to train
            model_id: Unique identifier for the model
            configuration: Model configuration and hyperparameters
            progress_callback: Optional callback for training progress updates
            
        Returns:
            True if training completed successfully
        """
        pass
    
    @abstractmethod
    async def validate_model_configuration(self, 
                                         model_type: MLModelType,
                                         configuration: ModelConfiguration) -> Dict[str, Any]:
        """
        Validate model configuration before training
        
        Args:
            model_type: Type of ML model
            configuration: Configuration to validate
            
        Returns:
            Dictionary with validation results and recommendations
        """
        pass
    
    @abstractmethod
    async def get_training_data_requirements(self, 
                                           model_type: MLModelType) -> Dict[str, Any]:
        """
        Get data requirements for specific model type
        
        Args:
            model_type: Type of ML model
            
        Returns:
            Dictionary with data requirements and specifications
        """
        pass
    
    @abstractmethod
    async def estimate_training_time(self, 
                                   model_type: MLModelType,
                                   configuration: ModelConfiguration,
                                   data_size: int) -> float:
        """
        Estimate training time for model
        
        Args:
            model_type: Type of ML model
            configuration: Model configuration
            data_size: Size of training dataset
            
        Returns:
            Estimated training time in minutes
        """
        pass
    
    @abstractmethod
    async def get_supported_model_types(self) -> List[MLModelType]:
        """
        Get list of supported model types
        
        Returns:
            List of supported ML model types
        """
        pass


# =============================================================================
# ML PREDICTION INTERFACE
# =============================================================================

class IMLPredictor(ABC):
    """
    Interface for ML Prediction Operations
    
    Defines contract for generating predictions from trained models
    with different horizons and validation capabilities.
    """
    
    @abstractmethod
    async def generate_prediction(self, 
                                model_id: str,
                                symbol: str,
                                prediction_horizon: MLPredictionHorizon,
                                features: Optional[Dict[str, Any]] = None) -> Optional[MLPrediction]:
        """
        Generate prediction using trained model
        
        Args:
            model_id: Identifier of trained model
            symbol: Stock symbol for prediction
            prediction_horizon: Time horizon for prediction
            features: Optional pre-computed features
            
        Returns:
            ML prediction entity or None if prediction failed
        """
        pass
    
    @abstractmethod
    async def batch_predict(self, 
                          model_id: str,
                          symbols: List[str],
                          prediction_horizon: MLPredictionHorizon) -> List[MLPrediction]:
        """
        Generate batch predictions for multiple symbols
        
        Args:
            model_id: Identifier of trained model
            symbols: List of stock symbols
            prediction_horizon: Time horizon for predictions
            
        Returns:
            List of ML prediction entities
        """
        pass
    
    @abstractmethod
    async def validate_prediction_inputs(self, 
                                       model_id: str,
                                       symbol: str,
                                       prediction_horizon: MLPredictionHorizon) -> Dict[str, Any]:
        """
        Validate inputs for prediction generation
        
        Args:
            model_id: Model identifier
            symbol: Stock symbol
            prediction_horizon: Prediction horizon
            
        Returns:
            Dictionary with validation results
        """
        pass
    
    @abstractmethod
    async def get_model_capabilities(self, model_id: str) -> Dict[str, Any]:
        """
        Get capabilities and supported features of model
        
        Args:
            model_id: Model identifier
            
        Returns:
            Dictionary with model capabilities
        """
        pass
    
    @abstractmethod
    async def explain_prediction(self, 
                               prediction_id: str) -> Dict[str, Any]:
        """
        Get explanation for generated prediction
        
        Args:
            prediction_id: Prediction identifier
            
        Returns:
            Dictionary with prediction explanation and feature importance
        """
        pass


# =============================================================================
# ML MODEL EVALUATION INTERFACE
# =============================================================================

class IMLModelEvaluator(ABC):
    """
    Interface for ML Model Evaluation Operations
    
    Defines contract for evaluating model performance with
    comprehensive metrics and comparison capabilities.
    """
    
    @abstractmethod
    async def evaluate_model(self, 
                           model_id: str,
                           model_type: MLModelType,
                           evaluation_period_days: int = 30) -> Optional[MLPerformanceMetrics]:
        """
        Evaluate model performance over specified period
        
        Args:
            model_id: Model identifier
            model_type: Type of ML model
            evaluation_period_days: Evaluation time period
            
        Returns:
            Performance metrics entity or None if evaluation failed
        """
        pass
    
    @abstractmethod
    async def compare_models(self, 
                           model_ids: List[str],
                           evaluation_metrics: List[str] = None) -> Dict[str, Dict[str, float]]:
        """
        Compare performance of multiple models
        
        Args:
            model_ids: List of model identifiers to compare
            evaluation_metrics: Specific metrics to compare
            
        Returns:
            Dictionary with model comparison results
        """
        pass
    
    @abstractmethod
    async def calculate_prediction_accuracy(self, 
                                          model_id: str,
                                          days_back: int = 30) -> Dict[str, float]:
        """
        Calculate prediction accuracy for historical predictions
        
        Args:
            model_id: Model identifier
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with accuracy metrics
        """
        pass
    
    @abstractmethod
    async def generate_performance_report(self, 
                                        model_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive performance report for model
        
        Args:
            model_id: Model identifier
            
        Returns:
            Dictionary with detailed performance analysis
        """
        pass
    
    @abstractmethod
    async def detect_model_drift(self, 
                               model_id: str,
                               baseline_period_days: int = 90) -> Dict[str, Any]:
        """
        Detect performance drift in model over time
        
        Args:
            model_id: Model identifier
            baseline_period_days: Baseline period for comparison
            
        Returns:
            Dictionary with drift detection results
        """
        pass


# =============================================================================
# RISK CALCULATION INTERFACE
# =============================================================================

class IRiskCalculator(ABC):
    """
    Interface for Risk Metrics Calculation
    
    Defines contract for calculating comprehensive risk metrics
    including VaR, volatility, and portfolio risk assessment.
    """
    
    @abstractmethod
    async def calculate_risk_metrics(self, 
                                   prediction_id: str,
                                   symbol: str,
                                   predicted_price: Decimal,
                                   calculation_period_days: int = 252) -> Optional[MLRiskMetrics]:
        """
        Calculate comprehensive risk metrics for prediction
        
        Args:
            prediction_id: Prediction identifier
            symbol: Stock symbol
            predicted_price: Predicted price
            calculation_period_days: Period for risk calculation
            
        Returns:
            Risk metrics entity or None if calculation failed
        """
        pass
    
    @abstractmethod
    async def calculate_portfolio_var(self, 
                                    symbols: List[str],
                                    weights: List[float],
                                    confidence_level: float = 0.95,
                                    holding_period_days: int = 1) -> Dict[str, Decimal]:
        """
        Calculate portfolio Value at Risk
        
        Args:
            symbols: Portfolio symbols
            weights: Position weights
            confidence_level: VaR confidence level
            holding_period_days: Holding period for VaR
            
        Returns:
            Dictionary with portfolio VaR metrics
        """
        pass
    
    @abstractmethod
    async def calculate_correlation_matrix(self, 
                                         symbols: List[str],
                                         lookback_days: int = 252) -> Dict[str, Dict[str, float]]:
        """
        Calculate correlation matrix for symbols
        
        Args:
            symbols: List of symbols
            lookback_days: Historical data period
            
        Returns:
            Correlation matrix as nested dictionary
        """
        pass
    
    @abstractmethod
    async def stress_test_portfolio(self, 
                                  symbols: List[str],
                                  weights: List[float],
                                  stress_scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform stress testing on portfolio
        
        Args:
            symbols: Portfolio symbols
            weights: Position weights
            stress_scenarios: List of stress test scenarios
            
        Returns:
            Dictionary with stress test results
        """
        pass
    
    @abstractmethod
    async def calculate_beta_metrics(self, 
                                   symbol: str,
                                   benchmark_symbol: str = "SPY",
                                   lookback_days: int = 252) -> Dict[str, float]:
        """
        Calculate beta and related risk metrics
        
        Args:
            symbol: Stock symbol
            benchmark_symbol: Benchmark symbol for beta calculation
            lookback_days: Historical data period
            
        Returns:
            Dictionary with beta and related metrics
        """
        pass


# =============================================================================
# FEATURE ENGINEERING INTERFACE
# =============================================================================

class IFeatureEngineer(ABC):
    """
    Interface for Feature Engineering Operations
    
    Defines contract for creating and managing features
    for ML model training and prediction.
    """
    
    @abstractmethod
    async def generate_technical_features(self, 
                                        symbol: str,
                                        lookback_days: int = 252) -> Dict[str, List[float]]:
        """
        Generate technical analysis features
        
        Args:
            symbol: Stock symbol
            lookback_days: Historical data period
            
        Returns:
            Dictionary with technical features
        """
        pass
    
    @abstractmethod
    async def generate_fundamental_features(self, 
                                          symbol: str) -> Dict[str, float]:
        """
        Generate fundamental analysis features
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with fundamental features
        """
        pass
    
    @abstractmethod
    async def generate_sentiment_features(self, 
                                        symbol: str,
                                        lookback_days: int = 30) -> Dict[str, float]:
        """
        Generate sentiment analysis features
        
        Args:
            symbol: Stock symbol
            lookback_days: News lookback period
            
        Returns:
            Dictionary with sentiment features
        """
        pass
    
    @abstractmethod
    async def generate_macro_economic_features(self) -> Dict[str, float]:
        """
        Generate macroeconomic features
        
        Returns:
            Dictionary with macro economic indicators
        """
        pass
    
    @abstractmethod
    async def validate_features(self, 
                              features: Dict[str, Any],
                              model_type: MLModelType) -> Dict[str, Any]:
        """
        Validate features for specific model type
        
        Args:
            features: Feature dictionary
            model_type: Target model type
            
        Returns:
            Validation results and recommendations
        """
        pass
    
    @abstractmethod
    async def get_feature_importance(self, 
                                   model_id: str) -> Dict[str, float]:
        """
        Get feature importance scores from trained model
        
        Args:
            model_id: Model identifier
            
        Returns:
            Dictionary with feature importance scores
        """
        pass


# =============================================================================
# AGGREGATE ML SERVICE INTERFACE
# =============================================================================

class IMLServiceProvider(ABC):
    """
    Aggregate ML Service Provider Interface
    
    Provides unified access to all ML service interfaces
    following Facade pattern for simplified integration.
    """
    
    @property
    @abstractmethod
    def trainer(self) -> IMLModelTrainer:
        """Get model trainer service"""
        pass
    
    @property
    @abstractmethod
    def predictor(self) -> IMLPredictor:
        """Get prediction service"""
        pass
    
    @property
    @abstractmethod
    def evaluator(self) -> IMLModelEvaluator:
        """Get model evaluator service"""
        pass
    
    @property
    @abstractmethod
    def risk_calculator(self) -> IRiskCalculator:
        """Get risk calculator service"""
        pass
    
    @property
    @abstractmethod
    def feature_engineer(self) -> IFeatureEngineer:
        """Get feature engineering service"""
        pass
    
    @abstractmethod
    async def get_service_health(self) -> Dict[str, Any]:
        """
        Get health status of all ML services
        
        Returns:
            Dictionary with service health information
        """
        pass
    
    @abstractmethod
    async def initialize_services(self, config: Dict[str, Any]) -> bool:
        """
        Initialize all ML services with configuration
        
        Args:
            config: Service configuration dictionary
            
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    async def shutdown_services(self) -> bool:
        """
        Gracefully shutdown all ML services
        
        Returns:
            True if shutdown successful
        """
        pass