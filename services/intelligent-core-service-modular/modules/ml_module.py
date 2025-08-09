"""
ML Module für Intelligent-Core-Service
Machine Learning Models und Predictions
"""

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

# Shared Library Import für Code-Duplikation-Eliminierung
from shared.common_imports import (
    np, pd, datetime, Dict, Any, Optional, os, structlog
)
from backend_base_module import BackendBaseModule
from event_bus import EventType

# Typing import für sklearn-spezifische Types
from typing import Tuple


class MLModule(BackendBaseModule):
    """Machine Learning Models und Prediction Engine"""
    
    def __init__(self, event_bus):
        super().__init__("ml", event_bus)
        self.models = {}
        self.scalers = {}
        self.model_metrics = {}
        self.is_trained = False
        self.feature_importance = {}
        self.prediction_cache = {}
        self.cache_ttl = 180  # 3 Minuten für ML predictions
        
    async def _initialize_module(self) -> bool:
        """Initialize ML module"""
        try:
            self.logger.info("Initializing ML Module")
            
            # Initialize models
            self.models = {
                'price_prediction': RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                ),
                'trend_prediction': GradientBoostingRegressor(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=6,
                    random_state=42
                ),
                'volatility_prediction': RandomForestRegressor(
                    n_estimators=50,
                    max_depth=8,
                    random_state=42
                )
            }
            
            # Initialize scalers
            self.scalers = {
                'features': StandardScaler(),
                'robust': RobustScaler()
            }
            
            # Try to load pre-trained models
            await self._load_pretrained_models()
            
            # If no models loaded, initialize with dummy data
            if not self.is_trained:
                await self._initialize_dummy_models()
            
            self.logger.info("ML module initialized", 
                           models_count=len(self.models),
                           is_trained=self.is_trained)
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize ML module", error=str(e))
            return False
    
    async def _subscribe_to_events(self):
        """Subscribe to relevant events"""
        await self.subscribe_to_event(
            EventType.ANALYSIS_STATE_CHANGED,
            self._handle_analysis_event
        )
        await self.subscribe_to_event(
            EventType.DATA_SYNCHRONIZED,
            self._handle_data_sync_event
        )
        await self.subscribe_to_event(
            EventType.INTELLIGENCE_TRIGGERED,
            self._handle_intelligence_event
        )
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Main ML processing logic"""
        try:
            request_type = data.get('type', 'prediction')
            
            if request_type == 'prediction':
                return await self._process_prediction_request(data)
            elif request_type == 'training':
                return await self._process_training_request(data)
            elif request_type == 'model_info':
                return await self._get_model_info()
            else:
                return {
                    'success': False,
                    'error': f'Unknown request type: {request_type}'
                }
                
        except Exception as e:
            self.logger.error("Error in ML processing", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _process_prediction_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process ML prediction request"""
        try:
            indicators = data.get('indicators', {})
            symbol = data.get('symbol', 'UNKNOWN')
            
            if not indicators:
                return {
                    'success': False,
                    'error': 'No indicators provided for prediction'
                }
            
            # Check cache
            cache_key = f"{symbol}_{hash(str(sorted(indicators.items())))}"
            if cache_key in self.prediction_cache:
                cache_entry = self.prediction_cache[cache_key]
                cache_age = (datetime.now() - cache_entry['timestamp']).total_seconds()
                if cache_age < self.cache_ttl:
                    self.logger.debug("Returning cached ML prediction", symbol=symbol)
                    return cache_entry['data']
            
            # Calculate ML scores
            ml_scores = await self._calculate_ml_scores(indicators)
            
            # Generate prediction confidence
            confidence = self._calculate_prediction_confidence(indicators, ml_scores)
            
            # Generate feature importance explanation
            feature_explanation = self._explain_prediction(indicators, ml_scores)
            
            result = {
                'success': True,
                'symbol': symbol,
                'ml_scores': ml_scores,
                'confidence': confidence,
                'feature_explanation': feature_explanation,
                'model_info': {
                    'is_trained': self.is_trained,
                    'models_available': list(self.models.keys()),
                    'prediction_timestamp': datetime.now().isoformat()
                }
            }
            
            # Cache result
            self.prediction_cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }
            
            # Publish ML prediction event
            await self.publish_module_event(
                EventType.INTELLIGENCE_TRIGGERED,
                {
                    'symbol': symbol,
                    'ml_scores': ml_scores,
                    'confidence': confidence,
                    'source': 'ml_module'
                },
                f"ml-prediction-{symbol}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Error processing prediction request", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _calculate_ml_scores(self, indicators: Dict[str, float]) -> Dict[str, float]:
        """Calculate ML scores using trained models"""
        try:
            if not self.is_trained:
                # Return neutral scores if no model is trained
                return {
                    'price_score': 0.5,
                    'trend_score': 0.5,
                    'volatility_score': 0.5,
                    'composite_score': 0.5
                }
            
            # Prepare features
            features = self._prepare_features(indicators)
            
            if features is None:
                return {
                    'price_score': 0.5,
                    'trend_score': 0.5,
                    'volatility_score': 0.5,
                    'composite_score': 0.5
                }
            
            # Scale features
            features_scaled = self.scalers['features'].transform(features.reshape(1, -1))
            
            # Generate predictions
            scores = {}
            
            # Price prediction score
            if 'price_prediction' in self.models:
                price_pred = self.models['price_prediction'].predict(features_scaled)[0]
                scores['price_score'] = float(max(0.0, min(1.0, price_pred)))
            else:
                scores['price_score'] = 0.5
            
            # Trend prediction score
            if 'trend_prediction' in self.models:
                trend_pred = self.models['trend_prediction'].predict(features_scaled)[0]
                scores['trend_score'] = float(max(0.0, min(1.0, trend_pred)))
            else:
                scores['trend_score'] = 0.5
            
            # Volatility prediction score
            if 'volatility_prediction' in self.models:
                vol_pred = self.models['volatility_prediction'].predict(features_scaled)[0]
                scores['volatility_score'] = float(max(0.0, min(1.0, vol_pred)))
            else:
                scores['volatility_score'] = 0.5
            
            # Composite score (weighted average)
            scores['composite_score'] = float(
                0.4 * scores['price_score'] +
                0.4 * scores['trend_score'] +
                0.2 * scores['volatility_score']
            )
            
            return scores
            
        except Exception as e:
            self.logger.error("Error calculating ML scores", error=str(e))
            # Return safe default scores
            return {
                'price_score': 0.5,
                'trend_score': 0.5,
                'volatility_score': 0.5,
                'composite_score': 0.5
            }
    
    def _prepare_features(self, indicators: Dict[str, float]) -> Optional[np.ndarray]:
        """Prepare feature vector from indicators"""
        try:
            # Define expected features in order
            feature_keys = [
                'rsi', 'macd', 'current_price', 'sma_20', 'sma_50',
                'bb_upper', 'bb_lower', 'volume_ratio', 'volatility',
                'price_change_percent', 'trend_strength'
            ]
            
            features = []
            for key in feature_keys:
                value = indicators.get(key, 0.0)
                # Handle potential None values
                if value is None:
                    value = 0.0
                features.append(float(value))
            
            # Add derived features
            if 'current_price' in indicators and 'sma_20' in indicators:
                price_to_sma = indicators['current_price'] / max(indicators['sma_20'], 1.0)
                features.append(price_to_sma)
            else:
                features.append(1.0)
            
            if 'bb_upper' in indicators and 'bb_lower' in indicators and 'current_price' in indicators:
                bb_position = (indicators['current_price'] - indicators['bb_lower']) / max(
                    indicators['bb_upper'] - indicators['bb_lower'], 1.0
                )
                features.append(bb_position)
            else:
                features.append(0.5)
            
            return np.array(features)
            
        except Exception as e:
            self.logger.error("Error preparing features", error=str(e))
            return None
    
    def _calculate_prediction_confidence(self, indicators: Dict[str, float], ml_scores: Dict[str, float]) -> float:
        """Calculate confidence level for ML predictions"""
        try:
            confidence_factors = []
            
            # Model training confidence
            if self.is_trained and 'price_prediction' in self.model_metrics:
                model_r2 = self.model_metrics['price_prediction'].get('r2_score', 0.5)
                confidence_factors.append(max(0.2, model_r2))
            else:
                confidence_factors.append(0.3)
            
            # Data quality confidence
            required_indicators = ['rsi', 'macd', 'current_price', 'sma_20', 'volume_ratio']
            available_indicators = sum(1 for key in required_indicators if key in indicators)
            data_quality = available_indicators / len(required_indicators)
            confidence_factors.append(data_quality)
            
            # Prediction consistency
            scores = [ml_scores.get('price_score', 0.5), ml_scores.get('trend_score', 0.5)]
            score_std = np.std(scores)
            consistency = max(0.3, 1.0 - score_std * 2)
            confidence_factors.append(consistency)
            
            # Market conditions confidence
            volatility = indicators.get('volatility', 0.2)
            vol_confidence = max(0.2, 1.0 - min(volatility, 1.0))
            confidence_factors.append(vol_confidence)
            
            # Calculate weighted average
            weights = [0.3, 0.3, 0.2, 0.2]
            confidence = sum(w * f for w, f in zip(weights, confidence_factors))
            
            return round(max(0.1, min(1.0, confidence)), 3)
            
        except Exception as e:
            self.logger.error("Error calculating prediction confidence", error=str(e))
            return 0.5
    
    def _explain_prediction(self, indicators: Dict[str, float], ml_scores: Dict[str, float]) -> Dict[str, Any]:
        """Generate explanation for ML prediction"""
        try:
            explanation = {
                'key_factors': [],
                'risk_factors': [],
                'confidence_drivers': []
            }
            
            # Analyze key technical factors
            rsi = indicators.get('rsi', 50.0)
            if rsi > 70:
                explanation['risk_factors'].append('Overbought condition (RSI > 70)')
            elif rsi < 30:
                explanation['key_factors'].append('Oversold condition (RSI < 30)')
            
            # Trend analysis
            trend_strength = indicators.get('trend_strength', 0.0)
            if abs(trend_strength) > 0.5:
                direction = 'upward' if trend_strength > 0 else 'downward'
                explanation['key_factors'].append(f'Strong {direction} trend detected')
            
            # Volume analysis
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:
                explanation['confidence_drivers'].append('High volume confirms price movement')
            elif volume_ratio < 0.5:
                explanation['risk_factors'].append('Low volume may indicate weak signal')
            
            # Price position analysis
            current_price = indicators.get('current_price', 100.0)
            sma_20 = indicators.get('sma_20', 100.0)
            if current_price > sma_20 * 1.05:
                explanation['key_factors'].append('Price trading above 20-day SMA')
            elif current_price < sma_20 * 0.95:
                explanation['risk_factors'].append('Price trading below 20-day SMA')
            
            # ML model confidence
            composite_score = ml_scores.get('composite_score', 0.5)
            if composite_score > 0.7:
                explanation['confidence_drivers'].append('ML models show strong bullish signal')
            elif composite_score < 0.3:
                explanation['confidence_drivers'].append('ML models show strong bearish signal')
            
            return explanation
            
        except Exception as e:
            self.logger.error("Error generating prediction explanation", error=str(e))
            return {
                'key_factors': ['Analysis error occurred'],
                'risk_factors': [],
                'confidence_drivers': []
            }
    
    async def _initialize_dummy_models(self):
        """Initialize models with dummy data for demonstration"""
        try:
            self.logger.info("Initializing ML models with dummy data")
            
            # Generate synthetic training data
            np.random.seed(42)
            n_samples = 1000
            n_features = 13  # Based on feature preparation
            
            X = np.random.rand(n_samples, n_features)
            # Create realistic target values
            y_price = 0.3 + 0.4 * X[:, 0] + 0.3 * np.random.rand(n_samples)  # RSI influence
            y_trend = 0.2 + 0.5 * X[:, 1] + 0.3 * np.random.rand(n_samples)  # MACD influence
            y_vol = 0.1 + 0.8 * X[:, 8] + 0.1 * np.random.rand(n_samples)    # Volatility influence
            
            # Normalize targets to 0-1 range
            y_price = np.clip(y_price, 0, 1)
            y_trend = np.clip(y_trend, 0, 1)
            y_vol = np.clip(y_vol, 0, 1)
            
            # Train models
            X_train, X_test, y_price_train, y_price_test = train_test_split(
                X, y_price, test_size=0.2, random_state=42
            )
            
            # Fit scaler
            self.scalers['features'].fit(X_train)
            X_train_scaled = self.scalers['features'].transform(X_train)
            X_test_scaled = self.scalers['features'].transform(X_test)
            
            # Train price prediction model
            self.models['price_prediction'].fit(X_train_scaled, y_price_train)
            y_pred = self.models['price_prediction'].predict(X_test_scaled)
            self.model_metrics['price_prediction'] = {
                'mse': mean_squared_error(y_price_test, y_pred),
                'r2_score': r2_score(y_price_test, y_pred)
            }
            
            # Train trend prediction model (reuse same data structure)
            _, _, y_trend_train, y_trend_test = train_test_split(
                X, y_trend, test_size=0.2, random_state=42
            )
            self.models['trend_prediction'].fit(X_train_scaled, y_trend_train)
            
            # Train volatility model
            _, _, y_vol_train, y_vol_test = train_test_split(
                X, y_vol, test_size=0.2, random_state=42
            )
            self.models['volatility_prediction'].fit(X_train_scaled, y_vol_train)
            
            self.is_trained = True
            self.logger.info("Dummy ML models trained successfully",
                           price_r2=self.model_metrics['price_prediction']['r2_score'])
            
        except Exception as e:
            self.logger.error("Failed to initialize dummy models", error=str(e))
            self.is_trained = False
    
    async def _load_pretrained_models(self):
        """Load pre-trained models from disk if available"""
        try:
            model_dir = "/home/mdoehler/aktienanalyse-ökosystem/models"
            if not os.path.exists(model_dir):
                self.logger.debug("No pre-trained models directory found")
                return
            
            for model_name in self.models.keys():
                model_path = os.path.join(model_dir, f"{model_name}.joblib")
                scaler_path = os.path.join(model_dir, f"{model_name}_scaler.joblib")
                
                if os.path.exists(model_path) and os.path.exists(scaler_path):
                    self.models[model_name] = joblib.load(model_path)
                    # Load associated scaler if exists
                    model_scaler = joblib.load(scaler_path)
                    self.scalers[f"{model_name}_scaler"] = model_scaler
                    self.logger.info("Pre-trained model loaded", model=model_name)
            
            if any(os.path.exists(os.path.join(model_dir, f"{name}.joblib")) 
                   for name in self.models.keys()):
                self.is_trained = True
                
        except Exception as e:
            self.logger.warning("Could not load pre-trained models", error=str(e))
    
    async def _handle_analysis_event(self, event):
        """Handle analysis state changed events"""
        try:
            self.logger.debug("Received analysis event")
            # Clear prediction cache when new analysis is available
            self.prediction_cache.clear()
        except Exception as e:
            self.logger.error("Error handling analysis event", error=str(e))
    
    async def _handle_data_sync_event(self, event):
        """Handle data synchronization events"""
        try:
            self.logger.info("Received data sync event")
            # Clear caches and potentially retrain models
            self.prediction_cache.clear()
        except Exception as e:
            self.logger.error("Error handling data sync event", error=str(e))
    
    async def _handle_intelligence_event(self, event):
        """Handle intelligence triggered events"""
        try:
            self.logger.debug("Received intelligence trigger event")
            # Could trigger model retraining or validation
        except Exception as e:
            self.logger.error("Error handling intelligence event", error=str(e))
    
    async def _get_model_info(self) -> Dict[str, Any]:
        """Get information about current ML models"""
        return {
            'success': True,
            'model_info': {
                'is_trained': self.is_trained,
                'models': list(self.models.keys()),
                'scalers': list(self.scalers.keys()),
                'metrics': self.model_metrics,
                'cache_size': len(self.prediction_cache),
                'last_training': 'dummy_data' if self.is_trained else 'not_trained'
            }
        }