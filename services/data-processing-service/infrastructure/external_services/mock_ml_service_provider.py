"""
Data Processing Service - Mock ML Service Provider
Clean Architecture v6.0.0

Mock Implementation für ML Service Provider für Development/Testing
"""
import asyncio
import random
import structlog
from datetime import datetime
from typing import List, Dict, Optional, Any
from decimal import Decimal

from domain.entities.prediction_entities import (
    StockData, ModelPrediction, PredictionModelType
)
from application.interfaces.ml_service_provider import IMLServiceProvider

logger = structlog.get_logger(__name__)


class MockMLServiceProvider(IMLServiceProvider):
    """Mock ML Service Provider für Development und Testing"""
    
    def __init__(self, simulate_failures: bool = False, failure_rate: float = 0.1):
        self.simulate_failures = simulate_failures
        self.failure_rate = failure_rate
        self.supported_models = list(PredictionModelType)
        
        # Mock model accuracies
        self.model_accuracies = {
            PredictionModelType.LINEAR_REGRESSION: 0.72,
            PredictionModelType.RANDOM_FOREST: 0.78,
            PredictionModelType.GRADIENT_BOOSTING: 0.81,
            PredictionModelType.NEURAL_NETWORK: 0.75
        }
        
        # Mock feature importance templates
        self.feature_templates = {
            PredictionModelType.LINEAR_REGRESSION: {
                "price_trend": 0.35,
                "volume": 0.25,
                "volatility": 0.20,
                "moving_average": 0.20
            },
            PredictionModelType.RANDOM_FOREST: {
                "price_trend": 0.28,
                "volume": 0.22,
                "volatility": 0.18,
                "moving_average": 0.15,
                "rsi": 0.17
            },
            PredictionModelType.GRADIENT_BOOSTING: {
                "price_trend": 0.30,
                "volume": 0.20,
                "volatility": 0.25,
                "moving_average": 0.12,
                "macd": 0.13
            },
            PredictionModelType.NEURAL_NETWORK: {
                "price_trend": 0.25,
                "volume": 0.20,
                "volatility": 0.20,
                "moving_average": 0.15,
                "technical_indicators": 0.20
            }
        }

    async def generate_prediction(
        self,
        model_type: PredictionModelType,
        symbol: str,
        historical_data: List[StockData],
        prediction_horizon_days: int = 1
    ) -> ModelPrediction:
        """Generate mock prediction using specified ML model"""
        logger.info(f"Generating mock prediction for {symbol} using {model_type.value}")
        
        # Simulate processing time
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Simulate occasional failures
        if self.simulate_failures and random.random() < self.failure_rate:
            raise Exception(f"Mock ML service failure for {model_type.value}")
        
        if not historical_data:
            raise ValueError("No historical data provided for prediction")
        
        # Get latest price as baseline
        latest_data = historical_data[-1]
        current_price = latest_data.close_price
        
        # Generate realistic prediction based on model type
        predicted_price = self._generate_realistic_price_prediction(
            model_type, current_price, historical_data, prediction_horizon_days
        )
        
        # Generate confidence score based on model type and data quality
        confidence_score = self._calculate_mock_confidence(
            model_type, historical_data, prediction_horizon_days
        )
        
        # Generate feature importance
        feature_importance = self._generate_feature_importance(model_type)
        
        prediction = ModelPrediction(
            model_type=model_type,
            symbol=symbol,
            predicted_price=predicted_price,
            confidence_score=confidence_score,
            prediction_horizon_days=prediction_horizon_days,
            created_at=datetime.now(),
            model_accuracy=self.model_accuracies.get(model_type, 0.70),
            feature_importance=feature_importance,
            training_data_size=len(historical_data)
        )
        
        logger.info(f"Generated prediction: {predicted_price} (confidence: {confidence_score:.2f})")
        return prediction

    def _generate_realistic_price_prediction(
        self,
        model_type: PredictionModelType,
        current_price: Decimal,
        historical_data: List[StockData],
        horizon_days: int
    ) -> Decimal:
        """Generate realistic price prediction based on historical data"""
        
        # Calculate recent price trend
        if len(historical_data) >= 5:
            recent_prices = [data.close_price for data in historical_data[-5:]]
            price_change_pct = float(recent_prices[-1] - recent_prices[0]) / float(recent_prices[0])
        else:
            price_change_pct = 0.0
        
        # Model-specific prediction logic
        if model_type == PredictionModelType.LINEAR_REGRESSION:
            # Simple linear trend extrapolation
            trend_factor = price_change_pct * horizon_days * 0.5
            noise_factor = random.uniform(-0.02, 0.02)
            
        elif model_type == PredictionModelType.RANDOM_FOREST:
            # More conservative prediction with ensemble averaging
            trend_factor = price_change_pct * horizon_days * 0.3
            noise_factor = random.uniform(-0.015, 0.015)
            
        elif model_type == PredictionModelType.GRADIENT_BOOSTING:
            # Boosted prediction with non-linear adjustments
            trend_factor = price_change_pct * horizon_days * 0.4
            # Add some non-linearity
            if abs(price_change_pct) > 0.05:  # Strong trend
                trend_factor *= 1.2
            noise_factor = random.uniform(-0.018, 0.018)
            
        elif model_type == PredictionModelType.NEURAL_NETWORK:
            # Neural network with pattern recognition
            trend_factor = price_change_pct * horizon_days * 0.35
            # Add some "pattern recognition" randomness
            pattern_factor = random.uniform(-0.01, 0.01)
            noise_factor = random.uniform(-0.02, 0.02) + pattern_factor
            
        else:
            trend_factor = price_change_pct * horizon_days * 0.3
            noise_factor = random.uniform(-0.02, 0.02)
        
        # Calculate predicted price
        price_multiplier = 1.0 + trend_factor + noise_factor
        predicted_price = current_price * Decimal(str(price_multiplier))
        
        # Ensure reasonable bounds (no more than ±20% change per day)
        max_daily_change = 0.20
        max_change = max_daily_change * horizon_days
        
        min_price = current_price * Decimal(str(1.0 - max_change))
        max_price = current_price * Decimal(str(1.0 + max_change))
        
        predicted_price = max(min_price, min(max_price, predicted_price))
        
        return predicted_price.quantize(Decimal('0.01'))

    def _calculate_mock_confidence(
        self,
        model_type: PredictionModelType,
        historical_data: List[StockData],
        horizon_days: int
    ) -> float:
        """Calculate mock confidence score based on data quality and model type"""
        
        # Base confidence based on model accuracy
        base_confidence = self.model_accuracies.get(model_type, 0.70)
        
        # Adjust based on data size
        data_size_factor = min(1.0, len(historical_data) / 100.0)
        
        # Adjust based on prediction horizon (longer = less confident)
        horizon_factor = max(0.5, 1.0 - (horizon_days - 1) * 0.1)
        
        # Calculate data volatility
        if len(historical_data) >= 10:
            recent_prices = [float(data.close_price) for data in historical_data[-10:]]
            price_std = Decimal(str(self._calculate_std(recent_prices)))
            mean_price = sum(recent_prices) / len(recent_prices)
            volatility = float(price_std) / mean_price
            
            # Lower confidence for high volatility
            volatility_factor = max(0.6, 1.0 - volatility * 2.0)
        else:
            volatility_factor = 0.8
        
        # Combine factors
        confidence = base_confidence * data_size_factor * horizon_factor * volatility_factor
        
        # Add some randomness
        confidence += random.uniform(-0.05, 0.05)
        
        # Ensure bounds
        return max(0.1, min(0.95, confidence))

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5

    def _generate_feature_importance(self, model_type: PredictionModelType) -> Dict[str, float]:
        """Generate mock feature importance scores"""
        template = self.feature_templates.get(model_type, {})
        
        # Add some randomness to the template
        feature_importance = {}
        for feature, base_importance in template.items():
            # Add ±20% randomness
            randomness = random.uniform(-0.2, 0.2)
            importance = base_importance * (1.0 + randomness)
            feature_importance[feature] = max(0.0, importance)
        
        # Normalize to sum to 1.0
        total_importance = sum(feature_importance.values())
        if total_importance > 0:
            feature_importance = {
                feature: importance / total_importance
                for feature, importance in feature_importance.items()
            }
        
        return feature_importance

    async def train_model(
        self,
        model_type: PredictionModelType,
        symbol: str,
        training_data: List[StockData],
        validation_split: float = 0.2
    ) -> Dict[str, Any]:
        """Mock model training"""
        logger.info(f"Mock training {model_type.value} model for {symbol}")
        
        # Simulate training time
        training_time = random.uniform(5.0, 20.0)
        await asyncio.sleep(min(training_time, 3.0))  # Cap simulation time
        
        if self.simulate_failures and random.random() < self.failure_rate / 2:
            raise Exception(f"Mock training failure for {model_type.value}")
        
        # Generate mock training results
        base_accuracy = self.model_accuracies.get(model_type, 0.70)
        accuracy_variance = random.uniform(-0.05, 0.05)
        final_accuracy = max(0.5, min(0.95, base_accuracy + accuracy_variance))
        
        training_size = int(len(training_data) * (1 - validation_split))
        validation_size = len(training_data) - training_size
        
        return {
            "model_type": model_type.value,
            "symbol": symbol,
            "training_accuracy": final_accuracy,
            "validation_accuracy": final_accuracy - random.uniform(0.0, 0.05),
            "training_data_size": training_size,
            "validation_data_size": validation_size,
            "training_time_seconds": training_time,
            "model_parameters": self._generate_mock_parameters(model_type),
            "feature_importance": self._generate_feature_importance(model_type),
            "training_completed": True
        }

    def _generate_mock_parameters(self, model_type: PredictionModelType) -> Dict[str, Any]:
        """Generate mock model parameters"""
        if model_type == PredictionModelType.LINEAR_REGRESSION:
            return {
                "coefficients": [random.uniform(-1.0, 1.0) for _ in range(4)],
                "intercept": random.uniform(-10.0, 10.0),
                "regularization": random.choice(["none", "l1", "l2"])
            }
        elif model_type == PredictionModelType.RANDOM_FOREST:
            return {
                "n_estimators": random.choice([50, 100, 200]),
                "max_depth": random.choice([5, 10, 15, None]),
                "min_samples_split": random.choice([2, 5, 10]),
                "feature_importance_threshold": 0.01
            }
        elif model_type == PredictionModelType.GRADIENT_BOOSTING:
            return {
                "n_estimators": random.choice([100, 200, 300]),
                "learning_rate": random.choice([0.01, 0.1, 0.2]),
                "max_depth": random.choice([3, 6, 9]),
                "subsample": random.uniform(0.8, 1.0)
            }
        elif model_type == PredictionModelType.NEURAL_NETWORK:
            return {
                "hidden_layers": random.choice([[64, 32], [128, 64, 32], [256, 128]]),
                "activation": random.choice(["relu", "tanh"]),
                "optimizer": random.choice(["adam", "sgd"]),
                "learning_rate": random.uniform(0.001, 0.01),
                "dropout_rate": random.uniform(0.1, 0.3)
            }
        else:
            return {}

    async def evaluate_model_performance(
        self,
        model_type: PredictionModelType,
        symbol: str,
        test_data: List[StockData]
    ) -> Dict[str, float]:
        """Mock model performance evaluation"""
        logger.info(f"Mock evaluating {model_type.value} model for {symbol}")
        
        # Simulate evaluation time
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        base_accuracy = self.model_accuracies.get(model_type, 0.70)
        accuracy_variance = random.uniform(-0.08, 0.03)  # Slight pessimistic bias
        
        return {
            "accuracy": max(0.4, min(0.95, base_accuracy + accuracy_variance)),
            "precision": max(0.4, min(0.95, base_accuracy + random.uniform(-0.05, 0.05))),
            "recall": max(0.4, min(0.95, base_accuracy + random.uniform(-0.05, 0.05))),
            "f1_score": max(0.4, min(0.95, base_accuracy + random.uniform(-0.05, 0.05))),
            "mae": random.uniform(0.5, 2.0),  # Mean Absolute Error
            "rmse": random.uniform(1.0, 3.0),  # Root Mean Square Error
            "test_data_size": len(test_data)
        }

    async def get_model_metadata(
        self,
        model_type: PredictionModelType,
        symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Get mock model metadata"""
        return {
            "model_type": model_type.value,
            "symbol": symbol,
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "accuracy": self.model_accuracies.get(model_type, 0.70),
            "parameters": self._generate_mock_parameters(model_type),
            "feature_count": len(self.feature_templates.get(model_type, {})),
            "training_status": "completed"
        }

    async def get_feature_importance(
        self,
        model_type: PredictionModelType,
        symbol: str
    ) -> Optional[Dict[str, float]]:
        """Get mock feature importance scores"""
        return self._generate_feature_importance(model_type)

    async def is_model_available(
        self,
        model_type: PredictionModelType,
        symbol: str
    ) -> bool:
        """Check if mock model is available"""
        # Always return True for mock service
        return True

    async def get_supported_models(self) -> List[PredictionModelType]:
        """Get list of supported model types"""
        return self.supported_models

    async def get_model_health_status(self) -> Dict[str, Any]:
        """Get mock health status of ML service"""
        return {
            "service_status": "healthy",
            "available_models": len(self.supported_models),
            "supported_models": [model.value for model in self.supported_models],
            "average_prediction_time": random.uniform(1.0, 2.0),
            "success_rate": 1.0 - self.failure_rate if self.simulate_failures else 1.0,
            "last_health_check": datetime.now().isoformat()
        }