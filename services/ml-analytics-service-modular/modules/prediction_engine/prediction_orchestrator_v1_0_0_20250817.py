#!/usr/bin/env python3
"""
Prediction Orchestrator v1.0.0
ML-Prediction-Engine für aktienanalyse-ökosystem

Integration: Event-Driven Prediction Pipeline
Autor: Claude Code  
Datum: 17. August 2025
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import uuid
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Import shared modules
from shared.database import DatabaseConnection
from shared.event_bus import EventBusConnection
from config.ml_service_config import ML_SERVICE_CONFIG

# Import ML modules
from modules.feature_engineering.technical_feature_engine_v1_0_0_20250817 import TechnicalFeatureEngine
from modules.model_management.model_manager_v1_0_0_20250817 import ModelManager

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Einzelne Modell-Prediction"""
    prediction_id: str
    model_type: str
    model_version: str
    horizon_days: int
    prediction_values: List[float]
    confidence_score: float
    volatility_estimate: float
    feature_importance: Dict[str, float]


@dataclass
class EnsemblePrediction:
    """Finale Ensemble-Prediction"""
    ensemble_prediction_id: str
    symbol: str
    individual_predictions: Dict[str, PredictionResult]
    final_predictions: Dict[str, Dict[str, Any]]
    ensemble_confidence: Dict[str, float]
    ensemble_method: str


class PredictionOrchestrator:
    """
    Prediction Orchestrator für ML-Pipeline
    Koordiniert Individual- und Ensemble-Predictions
    """
    
    def __init__(self, feature_engine: TechnicalFeatureEngine, model_manager: ModelManager,
                 database: DatabaseConnection, event_bus: EventBusConnection):
        self.feature_engine = feature_engine
        self.model_manager = model_manager
        self.database = database
        self.event_bus = event_bus
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Konfiguration
        self.prediction_horizons = [7, 30, 150, 365]
        self.model_types = ['technical']  # Erweitert um 'sentiment', 'fundamental' in späteren Phasen
        self.ensemble_config = ML_SERVICE_CONFIG['models']['ensemble']
        self.performance_thresholds = ML_SERVICE_CONFIG['performance_thresholds']
        
        # Prediction Cache
        self.prediction_cache = {}
        self.cache_ttl_hours = ML_SERVICE_CONFIG['caching']['prediction_cache_ttl_hours']
        
        # Performance-Tracking
        self.prediction_times = []
        self.ensemble_times = []
        self.is_initialized = False
    
    async def initialize(self):
        """Initialisiert Prediction Orchestrator"""
        try:
            self.logger.info("Initializing Prediction Orchestrator...")
            
            # Cache initialisieren
            await self._initialize_prediction_cache()
            
            # Ensemble-Weights laden
            await self._load_ensemble_weights()
            
            self.is_initialized = True
            self.logger.info("Prediction Orchestrator initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Prediction Orchestrator: {str(e)}")
            raise
    
    async def generate_predictions(self, symbol: str, features: Dict[str, Any]) -> str:
        """
        Generiert Predictions für Symbol basierend auf Features
        Orchestriert Individual-Predictions und Ensemble
        """
        start_time = time.time()
        correlation_id = str(uuid.uuid4())
        
        try:
            self.logger.info(f"Generating predictions for {symbol}")
            
            # Individual-Predictions für alle Modell-Typen generieren
            individual_predictions = {}
            
            for model_type in self.model_types:
                predictions = await self._generate_individual_predictions(
                    symbol, model_type, features, correlation_id
                )
                individual_predictions[model_type] = predictions
            
            # Ensemble-Prediction erstellen
            ensemble_prediction = await self._create_ensemble_prediction(
                symbol, individual_predictions, correlation_id
            )
            
            # Predictions in Datenbank speichern
            await self._store_predictions(ensemble_prediction)
            
            # ml.ensemble.prediction.ready Event publizieren
            await self._publish_ensemble_prediction_event(ensemble_prediction, correlation_id)
            
            # Performance-Tracking
            total_duration = (time.time() - start_time) * 1000
            self.ensemble_times.append(total_duration)
            
            self.logger.info(f"Predictions generated for {symbol} in {total_duration:.1f}ms")
            return ensemble_prediction.ensemble_prediction_id
            
        except Exception as e:
            self.logger.error(f"Failed to generate predictions for {symbol}: {str(e)}")
            raise
    
    async def _generate_individual_predictions(self, symbol: str, model_type: str, 
                                             features: Dict[str, Any], correlation_id: str) -> Dict[int, PredictionResult]:
        """Generiert Individual-Predictions für einen Modell-Typ"""
        predictions = {}
        
        for horizon_days in self.prediction_horizons:
            try:
                start_time = time.time()
                
                # Modell laden
                model, scaler = await self.model_manager.get_model_for_prediction(model_type, horizon_days)
                
                # Features für Modell vorbereiten
                model_features = await self._prepare_features_for_model(
                    symbol, model_type, horizon_days, features
                )
                
                # Prediction durchführen
                prediction_values, confidence, volatility, feature_importance = await self._run_model_prediction(
                    model, scaler, model_features, model_type, horizon_days
                )
                
                # Prediction-Result erstellen
                prediction_result = PredictionResult(
                    prediction_id=str(uuid.uuid4()),
                    model_type=model_type,
                    model_version="v1.0.0_20250817",
                    horizon_days=horizon_days,
                    prediction_values=prediction_values,
                    confidence_score=confidence,
                    volatility_estimate=volatility,
                    feature_importance=feature_importance
                )
                
                predictions[horizon_days] = prediction_result
                
                # Individual-Prediction Event publizieren
                await self._publish_individual_prediction_event(
                    symbol, prediction_result, correlation_id
                )
                
                # Performance-Tracking
                duration = (time.time() - start_time) * 1000
                self.prediction_times.append(duration)
                
            except Exception as e:
                self.logger.error(f"Failed to generate {model_type} prediction for {horizon_days}d: {str(e)}")
                # Weiter mit anderen Horizonten
                continue
        
        return predictions
    
    async def _prepare_features_for_model(self, symbol: str, model_type: str, 
                                        horizon_days: int, features: Dict[str, Any]) -> np.ndarray:
        """Bereitet Features für spezifisches Modell vor"""
        
        if model_type == 'technical':
            return await self._prepare_technical_features(symbol, horizon_days, features)
        elif model_type == 'sentiment':
            return await self._prepare_sentiment_features(symbol, horizon_days, features)
        elif model_type == 'fundamental':
            return await self._prepare_fundamental_features(symbol, horizon_days, features)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    async def _prepare_technical_features(self, symbol: str, horizon_days: int, 
                                        features: Dict[str, Any]) -> np.ndarray:
        """Bereitet technische Features für LSTM-Modell vor"""
        
        # Sequenz-Länge aus Konfiguration
        sequence_length = ML_SERVICE_CONFIG['models']['technical']['input_sequence_length']
        
        # Historische Features aus Datenbank laden
        query = """
            SELECT features_json, calculation_timestamp
            FROM ml_features
            WHERE symbol = %s AND feature_type = 'technical'
            AND calculation_timestamp >= %s
            ORDER BY calculation_timestamp DESC
            LIMIT %s
        """
        
        start_date = datetime.now() - timedelta(days=sequence_length + 5)  # Extra Puffer
        historical_features = await self.database.fetch_all(query, [symbol, start_date, sequence_length])
        
        if len(historical_features) < sequence_length:
            # Fallback: Aktueller Wert wiederholen
            self.logger.warning(f"Insufficient historical features for {symbol}, using current features")
            feature_vector = self._extract_feature_vector(features['technical'])
            return np.tile(feature_vector, (sequence_length, 1)).reshape(1, sequence_length, -1)
        
        # Feature-Sequenz aufbauen
        feature_sequences = []
        for feature_data, _ in historical_features[:sequence_length]:
            feature_vector = self._extract_feature_vector(feature_data['technical'])
            feature_sequences.append(feature_vector)
        
        # Als LSTM-Input formatieren (batch_size=1, sequence_length, features)
        feature_array = np.array(feature_sequences).reshape(1, sequence_length, -1)
        
        return feature_array
    
    def _extract_feature_vector(self, technical_features: Dict[str, Dict[str, float]]) -> np.ndarray:
        """Extrahiert numerischen Feature-Vektor aus technischen Features"""
        
        # Feature-Reihenfolge definieren (konsistent mit Training)
        feature_order = [
            # Momentum Features
            'momentum.rsi_14', 'momentum.macd_12_26_9', 'momentum.stoch_14_3',
            'momentum.williams_r_14', 'momentum.roc_10',
            
            # Trend Features  
            'trend.sma_20', 'trend.sma_50', 'trend.sma_200',
            'trend.ema_20', 'trend.ema_50', 'trend.price_above_sma_20',
            
            # Volatility Features
            'volatility.bb_upper_20', 'volatility.bb_lower_20', 'volatility.atr_14',
            'volatility.bb_width_20', 'volatility.relative_atr_14',
            
            # Volume Features
            'volume.volume_sma_20', 'volume.volume_ratio', 'volume.obv',
            
            # Price Action Features
            'price_action.daily_return', 'price_action.weekly_return',
            'price_action.high_low_ratio', 'price_action.price_gap'
        ]
        
        feature_vector = []
        
        for feature_path in feature_order:
            category, feature_name = feature_path.split('.')
            
            if category in technical_features and feature_name in technical_features[category]:
                value = technical_features[category][feature_name]
                
                # NaN-Behandlung
                if pd.isna(value) or not np.isfinite(value):
                    value = 0.0
                
                feature_vector.append(float(value))
            else:
                # Missing Feature mit 0.0 füllen
                feature_vector.append(0.0)
        
        return np.array(feature_vector)
    
    async def _run_model_prediction(self, model: Any, scaler: Any, features: np.ndarray,
                                   model_type: str, horizon_days: int) -> Tuple[List[float], float, float, Dict[str, float]]:
        """Führt Model-Prediction aus"""
        
        try:
            # Features skalieren
            if scaler and len(features.shape) == 3:  # LSTM: (batch, sequence, features)
                original_shape = features.shape
                features_2d = features.reshape(-1, features.shape[-1])
                features_scaled = scaler.transform(features_2d)
                features = features_scaled.reshape(original_shape)
            elif scaler:  # Other models
                features = scaler.transform(features)
            
            # Model-Prediction
            if model_type == 'technical':  # LSTM/TensorFlow
                predictions = model.predict(features, verbose=0)
                
                # Multi-Head Output für verschiedene Horizonte
                if isinstance(predictions, list):
                    # Multi-Head LSTM - Index basierend auf Horizon
                    horizon_index = {7: 0, 30: 1, 150: 2, 365: 3}.get(horizon_days, 0)
                    prediction_values = predictions[horizon_index][0].tolist()
                else:
                    # Single Output
                    prediction_values = predictions[0].tolist()
            
            else:  # XGBoost/Scikit-learn
                predictions = model.predict(features)
                prediction_values = predictions.tolist()
            
            # Confidence-Score berechnen
            confidence_score = await self._calculate_confidence_score(
                prediction_values, model_type, horizon_days
            )
            
            # Volatility-Estimate
            volatility_estimate = np.std(prediction_values) if len(prediction_values) > 1 else 0.1
            
            # Feature Importance (vereinfacht)
            feature_importance = await self._calculate_feature_importance(
                model, model_type, horizon_days
            )
            
            return prediction_values, confidence_score, volatility_estimate, feature_importance
            
        except Exception as e:
            self.logger.error(f"Model prediction failed: {str(e)}")
            raise
    
    async def _calculate_confidence_score(self, prediction_values: List[float], 
                                        model_type: str, horizon_days: int) -> float:
        """Berechnet Confidence-Score für Prediction"""
        
        try:
            # Basis-Confidence basierend auf Volatilität
            prediction_volatility = np.std(prediction_values) if len(prediction_values) > 1 else 0.1
            
            # Niedrigere Volatilität = höhere Confidence
            volatility_confidence = max(0.1, 1.0 - (prediction_volatility / 10.0))
            
            # Horizon-basierter Discount (längere Horizonte = weniger Confidence)
            horizon_discount = {7: 1.0, 30: 0.9, 150: 0.7, 365: 0.5}.get(horizon_days, 0.5)
            
            # Model-Type-basierte Confidence
            model_confidence = {'technical': 0.8, 'sentiment': 0.6, 'fundamental': 0.7}.get(model_type, 0.5)
            
            # Kombinierte Confidence
            final_confidence = volatility_confidence * horizon_discount * model_confidence
            
            return max(0.1, min(1.0, final_confidence))
            
        except Exception as e:
            self.logger.error(f"Failed to calculate confidence score: {str(e)}")
            return 0.5  # Default
    
    async def _calculate_feature_importance(self, model: Any, model_type: str, 
                                          horizon_days: int) -> Dict[str, float]:
        """Berechnet Feature Importance (vereinfacht)"""
        
        # Placeholder für Feature Importance
        # In Produktion: Model-spezifische Feature Importance
        
        if model_type == 'technical':
            return {
                'RSI_14': 0.15,
                'MACD_12_26_9': 0.12,
                'SMA_20': 0.10,
                'BB_POSITION_20': 0.08,
                'VOLUME_RATIO': 0.06
            }
        
        return {}
    
    async def _create_ensemble_prediction(self, symbol: str, 
                                        individual_predictions: Dict[str, Dict[int, PredictionResult]],
                                        correlation_id: str) -> EnsemblePrediction:
        """Erstellt Ensemble-Prediction aus Individual-Predictions"""
        
        try:
            ensemble_id = str(uuid.uuid4())
            
            # Ensemble-Weights laden
            ensemble_weights = await self._get_ensemble_weights(symbol)
            
            # Final Predictions für jeden Horizon berechnen
            final_predictions = {}
            
            for horizon_days in self.prediction_horizons:
                horizon_predictions = {}
                total_weight = 0.0
                weighted_predictions = []
                weighted_confidence = 0.0
                
                # Alle verfügbaren Modell-Predictions sammeln
                available_predictions = {}
                for model_type, predictions in individual_predictions.items():
                    if horizon_days in predictions:
                        prediction = predictions[horizon_days]
                        weight = ensemble_weights.get(f"{model_type}_{horizon_days}", 0.33)
                        
                        available_predictions[model_type] = {
                            'prediction': prediction,
                            'weight': weight
                        }
                        total_weight += weight
                
                if not available_predictions:
                    continue
                
                # Gewichte normalisieren
                for model_type in available_predictions:
                    available_predictions[model_type]['weight'] /= total_weight
                
                # Weighted Average Ensemble
                ensemble_values = self._calculate_weighted_average_prediction(available_predictions)
                ensemble_confidence = self._calculate_ensemble_confidence(available_predictions)
                
                # Prediction Intervals berechnen
                prediction_intervals = self._calculate_prediction_intervals(
                    available_predictions, ensemble_values
                )
                
                final_predictions[f"{horizon_days}d"] = {
                    'prediction_values': ensemble_values,
                    'ensemble_confidence': ensemble_confidence,
                    'prediction_interval': prediction_intervals
                }
            
            # Ensemble-Prediction erstellen
            ensemble_prediction = EnsemblePrediction(
                ensemble_prediction_id=ensemble_id,
                symbol=symbol,
                individual_predictions={
                    model_type: {str(h): pred for h, pred in predictions.items()}
                    for model_type, predictions in individual_predictions.items()
                },
                final_predictions=final_predictions,
                ensemble_confidence={h: final_predictions[h]['ensemble_confidence'] 
                                   for h in final_predictions.keys()},
                ensemble_method=self.ensemble_config['method']
            )
            
            return ensemble_prediction
            
        except Exception as e:
            self.logger.error(f"Failed to create ensemble prediction: {str(e)}")
            raise
    
    def _calculate_weighted_average_prediction(self, predictions: Dict[str, Dict[str, Any]]) -> List[float]:
        """Berechnet gewichteten Durchschnitt der Predictions"""
        
        if not predictions:
            return [0.0]
        
        # Sammle alle Prediction-Values
        all_prediction_values = []
        all_weights = []
        
        for model_type, pred_data in predictions.items():
            prediction = pred_data['prediction']
            weight = pred_data['weight']
            
            all_prediction_values.append(prediction.prediction_values)
            all_weights.append(weight)
        
        # Gewichteter Durchschnitt
        ensemble_values = []
        max_length = max(len(vals) for vals in all_prediction_values)
        
        for i in range(max_length):
            weighted_sum = 0.0
            total_weight = 0.0
            
            for values, weight in zip(all_prediction_values, all_weights):
                if i < len(values):
                    weighted_sum += values[i] * weight
                    total_weight += weight
            
            if total_weight > 0:
                ensemble_values.append(weighted_sum / total_weight)
            else:
                ensemble_values.append(0.0)
        
        return ensemble_values
    
    def _calculate_ensemble_confidence(self, predictions: Dict[str, Dict[str, Any]]) -> float:
        """Berechnet Ensemble-Confidence"""
        
        if not predictions:
            return 0.0
        
        # Gewichteter Durchschnitt der Individual-Confidences
        total_confidence = 0.0
        total_weight = 0.0
        
        for model_type, pred_data in predictions.items():
            confidence = pred_data['prediction'].confidence_score
            weight = pred_data['weight']
            
            total_confidence += confidence * weight
            total_weight += weight
        
        base_confidence = total_confidence / total_weight if total_weight > 0 else 0.0
        
        # Bonus für Ensemble-Diversität
        diversity_bonus = min(0.1, len(predictions) * 0.03)
        
        return min(1.0, base_confidence + diversity_bonus)
    
    def _calculate_prediction_intervals(self, predictions: Dict[str, Dict[str, Any]], 
                                      ensemble_values: List[float]) -> Dict[str, List[float]]:
        """Berechnet Prediction Intervals"""
        
        # Volatilität aus Individual-Predictions
        volatilities = [pred_data['prediction'].volatility_estimate 
                       for pred_data in predictions.values()]
        
        avg_volatility = np.mean(volatilities) if volatilities else 0.1
        
        # 95% Konfidenzintervall (±1.96 * σ)
        interval_width = 1.96 * avg_volatility
        
        lower_bound = [val - interval_width for val in ensemble_values]
        upper_bound = [val + interval_width for val in ensemble_values]
        
        return {
            'lower_bound': lower_bound,
            'upper_bound': upper_bound
        }
    
    async def _get_ensemble_weights(self, symbol: str) -> Dict[str, float]:
        """Lädt aktuelle Ensemble-Weights"""
        
        # Default-Weights (gleichgewichtet)
        default_weights = {}
        for model_type in self.model_types:
            for horizon in self.prediction_horizons:
                default_weights[f"{model_type}_{horizon}"] = 1.0 / len(self.model_types)
        
        try:
            # Symbol-spezifische Weights aus Datenbank laden
            query = """
                SELECT model_type, horizon_days, weight
                FROM ml_ensemble_weights
                WHERE symbol = %s OR symbol = 'DEFAULT'
                ORDER BY symbol DESC, updated_at DESC
            """
            
            results = await self.database.fetch_all(query, [symbol])
            
            if results:
                custom_weights = {}
                for model_type, horizon_days, weight in results:
                    custom_weights[f"{model_type}_{horizon_days}"] = weight
                return custom_weights
            
        except Exception as e:
            self.logger.error(f"Failed to load ensemble weights: {str(e)}")
        
        return default_weights
    
    async def get_latest_predictions(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Lädt neueste Predictions für Symbol"""
        
        query = """
            SELECT prediction_data, created_at
            FROM ml_predictions
            WHERE symbol = %s
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        result = await self.database.fetch_one(query, [symbol])
        
        if result:
            return result[0]  # prediction_data JSON
        
        return None
    
    async def _store_predictions(self, ensemble_prediction: EnsemblePrediction):
        """Speichert Predictions in Datenbank"""
        
        # Einzelne Individual-Predictions speichern
        for model_type, predictions in ensemble_prediction.individual_predictions.items():
            for horizon_str, prediction in predictions.items():
                await self._store_individual_prediction(
                    ensemble_prediction.symbol, prediction, ensemble_prediction.ensemble_prediction_id
                )
        
        # Ensemble-Prediction speichern
        query = """
            INSERT INTO ml_predictions (
                prediction_id, symbol, prediction_type, prediction_data,
                ensemble_confidence, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        prediction_data = {
            'ensemble': ensemble_prediction.final_predictions,
            'individual': {
                model_type: {h: {
                    'prediction_id': pred.prediction_id,
                    'prediction_values': pred.prediction_values,
                    'confidence_score': pred.confidence_score
                } for h, pred in predictions.items()}
                for model_type, predictions in ensemble_prediction.individual_predictions.items()
            }
        }
        
        avg_confidence = np.mean(list(ensemble_prediction.ensemble_confidence.values()))
        
        await self.database.execute(query, [
            ensemble_prediction.ensemble_prediction_id,
            ensemble_prediction.symbol,
            'ensemble',
            prediction_data,
            avg_confidence,
            datetime.utcnow()
        ])
    
    async def _store_individual_prediction(self, symbol: str, prediction: PredictionResult, 
                                         ensemble_id: str):
        """Speichert Individual-Prediction"""
        
        query = """
            INSERT INTO ml_individual_predictions (
                prediction_id, symbol, model_type, model_version,
                horizon_days, prediction_values, confidence_score,
                volatility_estimate, feature_importance, ensemble_prediction_id,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        await self.database.execute(query, [
            prediction.prediction_id,
            symbol,
            prediction.model_type,
            prediction.model_version,
            prediction.horizon_days,
            prediction.prediction_values,
            prediction.confidence_score,
            prediction.volatility_estimate,
            prediction.feature_importance,
            ensemble_id,
            datetime.utcnow()
        ])
    
    async def _publish_individual_prediction_event(self, symbol: str, prediction: PredictionResult, 
                                                 correlation_id: str):
        """Publiziert ml.model.prediction.generated Event"""
        
        payload = {
            'prediction_id': prediction.prediction_id,
            'symbol': symbol,
            'model_type': prediction.model_type,
            'model_version': prediction.model_version,
            'prediction_timestamp': datetime.utcnow().isoformat(),
            'horizons': {
                f"{prediction.horizon_days}d": {
                    'prediction_values': prediction.prediction_values,
                    'confidence_score': prediction.confidence_score,
                    'volatility_estimate': prediction.volatility_estimate
                }
            },
            'feature_importance': {
                'top_features': [
                    {'feature_name': name, 'importance_score': score}
                    for name, score in list(prediction.feature_importance.items())[:5]
                ]
            },
            'inference_duration_ms': int(self.prediction_times[-1] if self.prediction_times else 0)
        }
        
        await self.event_bus.publish_ml_event(
            'ml.model.prediction.generated', payload, correlation_id=correlation_id
        )
    
    async def _publish_ensemble_prediction_event(self, ensemble_prediction: EnsemblePrediction, 
                                               correlation_id: str):
        """Publiziert ml.ensemble.prediction.ready Event"""
        
        # Individual-Predictions für Event formatieren
        individual_preds = {}
        for model_type, predictions in ensemble_prediction.individual_predictions.items():
            for horizon_str, prediction in predictions.items():
                if model_type not in individual_preds:
                    individual_preds[model_type] = {}
                
                individual_preds[model_type] = {
                    'prediction_id': prediction.prediction_id,
                    'confidence': prediction.confidence_score,
                    'weight_in_ensemble': 1.0 / len(self.model_types)  # Vereinfacht
                }
                break  # Nur ein Eintrag pro Model-Type für Event
        
        payload = {
            'ensemble_prediction_id': ensemble_prediction.ensemble_prediction_id,
            'symbol': ensemble_prediction.symbol,
            'ensemble_timestamp': datetime.utcnow().isoformat(),
            'individual_predictions': individual_preds,
            'final_predictions': ensemble_prediction.final_predictions,
            'ensemble_method': ensemble_prediction.ensemble_method,
            'ensemble_duration_ms': int(self.ensemble_times[-1] if self.ensemble_times else 0)
        }
        
        await self.event_bus.publish_ml_event(
            'ml.ensemble.prediction.ready', payload, correlation_id=correlation_id
        )
    
    async def _initialize_prediction_cache(self):
        """Initialisiert Prediction-Cache"""
        self.prediction_cache = {}
        self.logger.info("Prediction cache initialized")
    
    async def _load_ensemble_weights(self):
        """Lädt Ensemble-Weights"""
        try:
            # Default-Weights setzen falls keine in DB
            default_weights = {}
            for model_type in self.model_types:
                for horizon in self.prediction_horizons:
                    default_weights[f"{model_type}_{horizon}"] = 1.0
            
            self.logger.info("Ensemble weights loaded")
            
        except Exception as e:
            self.logger.error(f"Failed to load ensemble weights: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Health Check für Prediction Orchestrator"""
        try:
            # Performance-Statistiken
            avg_prediction_time = np.mean(self.prediction_times[-100:]) if self.prediction_times else 0
            avg_ensemble_time = np.mean(self.ensemble_times[-100:]) if self.ensemble_times else 0
            
            # Cache-Statistiken
            cache_size = len(self.prediction_cache)
            
            return {
                'status': 'healthy' if self.is_initialized else 'warning',
                'initialized': self.is_initialized,
                'avg_prediction_time_ms': round(avg_prediction_time, 2),
                'avg_ensemble_time_ms': round(avg_ensemble_time, 2),
                'recent_predictions': len(self.prediction_times),
                'cache_size': cache_size,
                'supported_model_types': self.model_types,
                'prediction_horizons': self.prediction_horizons
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'error': str(e)
            }
    
    async def shutdown(self):
        """Graceful Shutdown"""
        try:
            self.logger.info("Shutting down Prediction Orchestrator...")
            
            # Cache leeren
            self.prediction_cache.clear()
            
            # Performance-Statistiken ausgeben
            if self.prediction_times:
                avg_pred_time = np.mean(self.prediction_times)
                avg_ensemble_time = np.mean(self.ensemble_times)
                self.logger.info(f"Average prediction time: {avg_pred_time:.1f}ms")
                self.logger.info(f"Average ensemble time: {avg_ensemble_time:.1f}ms")
            
            self.is_initialized = False
            self.logger.info("Prediction Orchestrator shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during Prediction Orchestrator shutdown: {str(e)}")