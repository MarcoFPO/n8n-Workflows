#!/usr/bin/env python3
"""
Technical LSTM Trainer v1.0.0
Training-Modul für technische LSTM-Modelle

Integration: Event-Driven Model Training
Autor: Claude Code
Datum: 17. August 2025
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import uuid
from dataclasses import dataclass

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Import shared modules
from shared.database import DatabaseConnection
from shared.event_bus import EventBusConnection
from config.ml_service_config import ML_SERVICE_CONFIG

# Import ML modules
from modules.feature_engineering.technical_feature_engine_v1_0_0_20250817 import TechnicalFeatureEngine
from modules.model_management.model_manager_v1_0_0_20250817 import ModelManager, ModelPerformance

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """LSTM Training Configuration"""
    sequence_length: int
    prediction_horizon: int
    features_count: int
    batch_size: int
    epochs: int
    learning_rate: float
    dropout_rate: float
    validation_split: float
    early_stopping_patience: int


@dataclass
class TrainingResults:
    """Training Results Container"""
    training_id: str
    model: tf.keras.Model
    scaler: StandardScaler
    training_history: Dict[str, List[float]]
    validation_metrics: Dict[str, float]
    training_duration: float
    final_loss: float


class TechnicalLSTMTrainer:
    """
    LSTM-Training für technische Indikatoren
    Erstellt Modelle für verschiedene Prediction-Horizonte
    """
    
    def __init__(self, database: DatabaseConnection, event_bus: EventBusConnection,
                 feature_engine: TechnicalFeatureEngine, model_manager: ModelManager):
        self.database = database
        self.event_bus = event_bus
        self.feature_engine = feature_engine
        self.model_manager = model_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Training-Konfiguration
        self.model_config = ML_SERVICE_CONFIG['models']['technical']
        self.training_config = ML_SERVICE_CONFIG['training']
        
        # TensorFlow Settings
        self._configure_tensorflow()
        
        self.is_initialized = False
    
    def _configure_tensorflow(self):
        """Konfiguriert TensorFlow für Training"""
        try:
            # Memory Growth für GPU
            if ML_SERVICE_CONFIG['tensorflow']['gpu_enabled']:
                gpus = tf.config.experimental.list_physical_devices('GPU')
                if gpus:
                    for gpu in gpus:
                        tf.config.experimental.set_memory_growth(gpu, True)
                        
            # Mixed Precision für Performance
            if ML_SERVICE_CONFIG['tensorflow']['mixed_precision']:
                policy = tf.keras.mixed_precision.Policy('mixed_float16')
                tf.keras.mixed_precision.set_global_policy(policy)
            
            # Reduce TF Logging
            tf.get_logger().setLevel(logging.ERROR)
            
        except Exception as e:
            self.logger.error(f"Failed to configure TensorFlow: {str(e)}")
    
    async def initialize(self):
        """Initialisiert LSTM Trainer"""
        try:
            self.logger.info("Initializing Technical LSTM Trainer...")
            
            # Verzeichnisse für Model-Checkpoints erstellen
            checkpoint_dir = os.path.join(
                ML_SERVICE_CONFIG['storage']['model_storage_path'],
                'training_checkpoints'
            )
            os.makedirs(checkpoint_dir, exist_ok=True)
            
            self.is_initialized = True
            self.logger.info("Technical LSTM Trainer initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LSTM Trainer: {str(e)}")
            raise
    
    async def train_model_for_symbol(self, symbol: str, horizon_days: int = 7) -> str:
        """
        Trainiert LSTM-Modell für spezifisches Symbol und Horizont
        Publiziert ml.model.training.started/completed Events
        """
        training_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        
        try:
            self.logger.info(f"Starting LSTM training for {symbol} {horizon_days}d horizon")
            
            # Training starten Event
            await self._publish_training_started_event(training_id, symbol, horizon_days, correlation_id)
            
            # Training-Log erstellen
            await self._create_training_log(training_id, symbol, horizon_days)
            
            # Training-Daten laden und vorbereiten
            X_train, X_val, y_train, y_val, scaler = await self._prepare_training_data(
                symbol, horizon_days
            )
            
            # Training-Konfiguration erstellen
            training_config = self._create_training_config(
                sequence_length=X_train.shape[1],
                features_count=X_train.shape[2],
                horizon_days=horizon_days
            )
            
            # LSTM-Modell erstellen
            model = self._build_lstm_model(training_config)
            
            # Modell trainieren
            training_results = await self._train_model(
                model, X_train, X_val, y_train, y_val, training_config, training_id
            )
            
            # Training-Metriken berechnen
            validation_metrics = await self._calculate_validation_metrics(
                training_results.model, X_val, y_val, scaler
            )
            
            # Model Performance-Objekt erstellen
            model_performance = ModelPerformance(
                mae_score=validation_metrics['mae'],
                mse_score=validation_metrics['mse'],
                directional_accuracy=validation_metrics['directional_accuracy'],
                r2_score=validation_metrics['r2_score'],
                sharpe_ratio=validation_metrics.get('sharpe_ratio')
            )
            
            # Training-Konfiguration für Registry
            training_config_dict = {
                'sequence_length': training_config.sequence_length,
                'prediction_horizon': training_config.prediction_horizon,
                'batch_size': training_config.batch_size,
                'epochs': training_config.epochs,
                'learning_rate': training_config.learning_rate,
                'dropout_rate': training_config.dropout_rate,
                'final_loss': training_results.final_loss,
                'training_duration': training_results.training_duration
            }
            
            # Modell im Model Manager registrieren
            model_id = await self.model_manager.register_new_model(
                model_type='technical',
                horizon_days=horizon_days,
                model_artifact=training_results.model,
                scaler=training_results.scaler,
                performance_metrics=model_performance,
                training_config=training_config_dict
            )
            
            # Training-Log aktualisieren
            await self._update_training_log(training_id, training_results, validation_metrics, model_id)
            
            # Training completed Event
            await self._publish_training_completed_event(
                training_id, symbol, horizon_days, model_id, validation_metrics, correlation_id
            )
            
            self.logger.info(f"LSTM training completed for {symbol}: {model_id}")
            return model_id
            
        except Exception as e:
            self.logger.error(f"LSTM training failed for {symbol}: {str(e)}")
            
            # Training failed Event
            await self._publish_training_failed_event(training_id, symbol, horizon_days, str(e), correlation_id)
            await self._mark_training_failed(training_id, str(e))
            
            raise
    
    async def _prepare_training_data(self, symbol: str, horizon_days: int, 
                                   lookback_days: int = 365) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
        """Bereitet Training-Daten vor"""
        
        # Marktdaten und Features laden
        market_data = await self._load_market_data(symbol, lookback_days + 30)  # Extra Puffer
        
        if len(market_data) < self.model_config['input_sequence_length'] + horizon_days:
            raise ValueError(f"Insufficient data for {symbol}: {len(market_data)} days")
        
        # Features für jeden Tag berechnen
        feature_sequences = []
        target_values = []
        
        sequence_length = self.model_config['input_sequence_length']
        
        for i in range(sequence_length, len(market_data) - horizon_days):
            # Feature-Sequenz für LSTM
            window_data = market_data.iloc[i-sequence_length:i]
            feature_sequence = await self._extract_feature_sequence(window_data)
            
            # Target: Preisveränderung nach horizon_days
            current_price = market_data.iloc[i]['close_price']
            future_price = market_data.iloc[i + horizon_days]['close_price']
            price_change_pct = (future_price - current_price) / current_price * 100
            
            feature_sequences.append(feature_sequence)
            target_values.append(price_change_pct)
        
        # Zu NumPy Arrays konvertieren
        X = np.array(feature_sequences)
        y = np.array(target_values)
        
        # Features skalieren
        scaler = StandardScaler()
        
        # Reshape für Skalierung (samples * sequence_length, features)
        original_shape = X.shape
        X_reshaped = X.reshape(-1, X.shape[-1])
        X_scaled = scaler.fit_transform(X_reshaped)
        X = X_scaled.reshape(original_shape)
        
        # Train/Validation Split
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, 
            test_size=self.training_config['validation_split'],
            shuffle=False,  # Zeitreihen: nicht shuffeln
            random_state=42
        )
        
        self.logger.info(f"Training data prepared: {X_train.shape[0]} train, {X_val.shape[0]} val samples")
        
        return X_train, X_val, y_train, y_val, scaler
    
    async def _load_market_data(self, symbol: str, days: int) -> pd.DataFrame:
        """Lädt Marktdaten für Training"""
        query = """
            SELECT date, open_price, high_price, low_price, close_price, volume, adjusted_close
            FROM market_data_daily
            WHERE symbol = %s
            AND date >= %s
            ORDER BY date ASC
        """
        
        start_date = datetime.now() - timedelta(days=days)
        result = await self.database.fetch_all(query, [symbol, start_date])
        
        if not result:
            raise ValueError(f"No market data found for {symbol}")
        
        df = pd.DataFrame(result)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        return df
    
    async def _extract_feature_sequence(self, window_data: pd.DataFrame) -> np.ndarray:
        """Extrahiert Feature-Vektor für LSTM-Sequenz"""
        
        # Basis-Features berechnen
        close = window_data['close_price'].values
        high = window_data['high_price'].values
        low = window_data['low_price'].values
        volume = window_data['volume'].values
        
        # Features für letzten Tag der Sequenz
        features = []
        
        # Price-basierte Features
        if len(close) > 1:
            features.extend([
                close[-1],  # Current price
                (close[-1] - close[-2]) / close[-2] if close[-2] != 0 else 0,  # 1-day return
                np.mean(close[-5:]) if len(close) >= 5 else close[-1],  # 5-day SMA
                np.mean(close[-10:]) if len(close) >= 10 else close[-1],  # 10-day SMA
                np.std(close[-10:]) if len(close) >= 10 else 0,  # 10-day volatility
            ])
        else:
            features.extend([close[-1], 0, close[-1], close[-1], 0])
        
        # Volume Features
        if len(volume) > 1:
            features.extend([
                volume[-1],
                volume[-1] / np.mean(volume[-10:]) if len(volume) >= 10 and np.mean(volume[-10:]) != 0 else 1,
                np.log(volume[-1] + 1)  # Log-volume
            ])
        else:
            features.extend([volume[-1], 1, np.log(volume[-1] + 1)])
        
        # Technical Indicators (vereinfacht für schnelles Training)
        if len(close) >= 14:
            # RSI (vereinfacht)
            deltas = np.diff(close[-15:])
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            rsi = 100 - (100 / (1 + (avg_gain / avg_loss))) if avg_loss != 0 else 50
            features.append(rsi)
        else:
            features.append(50)  # Neutral RSI
        
        # High-Low Range
        if len(high) > 1 and len(low) > 1:
            hl_ratio = (high[-1] - low[-1]) / close[-1] if close[-1] != 0 else 0
            features.append(hl_ratio)
        else:
            features.append(0)
        
        # NaN-Behandlung
        features = [0.0 if np.isnan(x) or np.isinf(x) else float(x) for x in features]
        
        return np.array(features)
    
    def _create_training_config(self, sequence_length: int, features_count: int, 
                              horizon_days: int) -> TrainingConfig:
        """Erstellt Training-Konfiguration"""
        
        return TrainingConfig(
            sequence_length=sequence_length,
            prediction_horizon=horizon_days,
            features_count=features_count,
            batch_size=self.training_config['batch_size'],
            epochs=self.training_config['epochs'],
            learning_rate=self.training_config['learning_rate'],
            dropout_rate=self.training_config['dropout_rate'],
            validation_split=self.training_config['validation_split'],
            early_stopping_patience=self.training_config['early_stopping_patience']
        )
    
    def _build_lstm_model(self, config: TrainingConfig) -> tf.keras.Model:
        """Erstellt LSTM-Modell-Architektur"""
        
        model = Sequential([
            # Erste LSTM-Schicht
            LSTM(
                units=self.model_config['lstm_units'],
                return_sequences=True,
                input_shape=(config.sequence_length, config.features_count),
                dropout=config.dropout_rate,
                recurrent_dropout=config.dropout_rate
            ),
            BatchNormalization(),
            
            # Zweite LSTM-Schicht
            LSTM(
                units=self.model_config['lstm_units'] // 2,
                return_sequences=False,
                dropout=config.dropout_rate,
                recurrent_dropout=config.dropout_rate
            ),
            BatchNormalization(),
            
            # Dense Layers
            Dense(self.model_config['dense_units'], activation='relu'),
            Dropout(config.dropout_rate),
            
            Dense(self.model_config['dense_units'] // 2, activation='relu'),
            Dropout(config.dropout_rate),
            
            # Output Layer
            Dense(1, activation='linear')  # Regression für Preisveränderung
        ])
        
        # Optimizer
        optimizer = Adam(
            learning_rate=config.learning_rate,
            beta_1=0.9,
            beta_2=0.999,
            epsilon=1e-7
        )
        
        # Kompilieren
        model.compile(
            optimizer=optimizer,
            loss='mse',
            metrics=['mae', 'mse']
        )
        
        self.logger.info(f"LSTM model built: {model.count_params()} parameters")
        
        return model
    
    async def _train_model(self, model: tf.keras.Model, X_train: np.ndarray, X_val: np.ndarray,
                          y_train: np.ndarray, y_val: np.ndarray, 
                          config: TrainingConfig, training_id: str) -> TrainingResults:
        """Trainiert LSTM-Modell"""
        
        start_time = time.time()
        
        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=config.early_stopping_patience,
                restore_best_weights=True,
                verbose=1
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=config.early_stopping_patience // 2,
                min_lr=1e-7,
                verbose=1
            ),
            ModelCheckpoint(
                filepath=f'/tmp/model_checkpoint_{training_id}.h5',
                monitor='val_loss',
                save_best_only=True,
                verbose=1
            )
        ]
        
        # Training
        self.logger.info(f"Training LSTM model: {config.epochs} epochs, batch size {config.batch_size}")
        
        history = model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=config.epochs,
            batch_size=config.batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        training_duration = time.time() - start_time
        
        # Bestes Modell laden
        if os.path.exists(f'/tmp/model_checkpoint_{training_id}.h5'):
            model.load_weights(f'/tmp/model_checkpoint_{training_id}.h5')
            os.remove(f'/tmp/model_checkpoint_{training_id}.h5')
        
        # Training-Results erstellen
        training_results = TrainingResults(
            training_id=training_id,
            model=model,
            scaler=None,  # Wird später gesetzt
            training_history={
                'loss': history.history['loss'],
                'val_loss': history.history['val_loss'],
                'mae': history.history['mae'],
                'val_mae': history.history['val_mae']
            },
            validation_metrics={},  # Wird später berechnet
            training_duration=training_duration,
            final_loss=min(history.history['val_loss'])
        )
        
        self.logger.info(f"Training completed in {training_duration:.1f}s, final val_loss: {training_results.final_loss:.4f}")
        
        return training_results
    
    async def _calculate_validation_metrics(self, model: tf.keras.Model, X_val: np.ndarray, 
                                          y_val: np.ndarray, scaler: StandardScaler) -> Dict[str, float]:
        """Berechnet Validation-Metriken"""
        
        # Predictions
        y_pred = model.predict(X_val).flatten()
        
        # Regression-Metriken
        mae = mean_absolute_error(y_val, y_pred)
        mse = mean_squared_error(y_val, y_pred)
        r2 = r2_score(y_val, y_pred)
        
        # Directional Accuracy (wichtigste Metrik für Trading)
        directional_accuracy = np.mean(np.sign(y_val) == np.sign(y_pred))
        
        # Sharpe Ratio (vereinfacht)
        returns_pred = y_pred / 100  # Prozent zu Decimal
        sharpe_ratio = np.mean(returns_pred) / np.std(returns_pred) if np.std(returns_pred) != 0 else 0
        
        metrics = {
            'mae': float(mae),
            'mse': float(mse),
            'r2_score': float(r2),
            'directional_accuracy': float(directional_accuracy),
            'sharpe_ratio': float(sharpe_ratio) if not np.isnan(sharpe_ratio) else None
        }
        
        self.logger.info(f"Validation metrics: DA={directional_accuracy:.3f}, MAE={mae:.3f}, R2={r2:.3f}")
        
        return metrics
    
    async def _create_training_log(self, training_id: str, symbol: str, horizon_days: int):
        """Erstellt Training-Log Eintrag"""
        
        training_config = {
            'symbol': symbol,
            'horizon_days': horizon_days,
            'sequence_length': self.model_config['input_sequence_length'],
            'lstm_units': self.model_config['lstm_units'],
            'dense_units': self.model_config['dense_units']
        }
        
        query = """
            INSERT INTO ml_training_logs (
                training_id, model_type, horizon_days, training_symbol,
                training_start, training_config, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        await self.database.execute(query, [
            training_id, 'technical', horizon_days, symbol,
            datetime.utcnow(), training_config, 'running'
        ])
    
    async def _update_training_log(self, training_id: str, results: TrainingResults, 
                                 metrics: Dict[str, float], model_id: str):
        """Aktualisiert Training-Log mit Ergebnissen"""
        
        query = """
            UPDATE ml_training_logs SET
                training_end = %s,
                training_duration_seconds = %s,
                training_metrics = %s,
                validation_metrics = %s,
                status = %s,
                model_id = %s
            WHERE training_id = %s
        """
        
        await self.database.execute(query, [
            datetime.utcnow(),
            int(results.training_duration),
            results.training_history,
            metrics,
            'completed',
            model_id,
            training_id
        ])
    
    async def _mark_training_failed(self, training_id: str, error_message: str):
        """Markiert Training als fehlgeschlagen"""
        
        query = """
            UPDATE ml_training_logs SET
                training_end = %s,
                status = %s,
                error_message = %s
            WHERE training_id = %s
        """
        
        await self.database.execute(query, [
            datetime.utcnow(), 'failed', error_message, training_id
        ])
    
    async def _publish_training_started_event(self, training_id: str, symbol: str, 
                                            horizon_days: int, correlation_id: str):
        """Publiziert ml.model.training.started Event"""
        
        payload = {
            'training_id': training_id,
            'model_type': 'technical',
            'symbol': symbol,
            'horizon_days': horizon_days,
            'training_start_timestamp': datetime.utcnow().isoformat(),
            'expected_duration_minutes': 15,  # Schätzung
            'training_config': {
                'sequence_length': self.model_config['input_sequence_length'],
                'epochs': self.training_config['epochs'],
                'batch_size': self.training_config['batch_size']
            }
        }
        
        await self.event_bus.publish_ml_event(
            'ml.model.training.started', payload, correlation_id=correlation_id
        )
    
    async def _publish_training_completed_event(self, training_id: str, symbol: str, 
                                              horizon_days: int, model_id: str,
                                              metrics: Dict[str, float], correlation_id: str):
        """Publiziert ml.model.training.completed Event"""
        
        payload = {
            'training_id': training_id,
            'model_id': model_id,
            'model_type': 'technical',
            'symbol': symbol,
            'horizon_days': horizon_days,
            'training_completion_timestamp': datetime.utcnow().isoformat(),
            'performance_metrics': {
                'directional_accuracy': metrics['directional_accuracy'],
                'mae_score': metrics['mae'],
                'r2_score': metrics['r2_score']
            },
            'deployment_eligible': metrics['directional_accuracy'] > self.training_config['min_directional_accuracy']
        }
        
        await self.event_bus.publish_ml_event(
            'ml.model.training.completed', payload, correlation_id=correlation_id
        )
    
    async def _publish_training_failed_event(self, training_id: str, symbol: str, 
                                           horizon_days: int, error_message: str, correlation_id: str):
        """Publiziert ml.model.training.failed Event"""
        
        payload = {
            'training_id': training_id,
            'model_type': 'technical',
            'symbol': symbol,
            'horizon_days': horizon_days,
            'training_failure_timestamp': datetime.utcnow().isoformat(),
            'error_message': error_message,
            'retry_suggested': 'insufficient_data' not in error_message.lower()
        }
        
        await self.event_bus.publish_ml_event(
            'ml.model.training.failed', payload, correlation_id=correlation_id
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Health Check für LSTM Trainer"""
        try:
            # TensorFlow GPU Status
            gpu_available = len(tf.config.experimental.list_physical_devices('GPU')) > 0
            
            return {
                'status': 'healthy' if self.is_initialized else 'warning',
                'initialized': self.is_initialized,
                'tensorflow_version': tf.__version__,
                'gpu_available': gpu_available,
                'mixed_precision_enabled': tf.keras.mixed_precision.global_policy().name != 'float32',
                'supported_horizons': [7, 30, 150, 365],
                'model_architecture': {
                    'lstm_units': self.model_config['lstm_units'],
                    'dense_units': self.model_config['dense_units'],
                    'sequence_length': self.model_config['input_sequence_length']
                }
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'error': str(e)
            }
    
    async def shutdown(self):
        """Graceful Shutdown"""
        try:
            self.logger.info("Shutting down Technical LSTM Trainer...")
            
            # TensorFlow Session cleanup
            tf.keras.backend.clear_session()
            
            self.is_initialized = False
            self.logger.info("Technical LSTM Trainer shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during LSTM Trainer shutdown: {str(e)}")