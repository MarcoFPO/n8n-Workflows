#!/usr/bin/env python3
"""
Simple LSTM Model v1.0.0
Einfaches LSTM für 7-Tage AAPL Prognosen

Autor: Claude Code
Datum: 18. August 2025
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import asyncpg
import json
import pickle
import os
from pathlib import Path

# TensorFlow Imports
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    IMPORT_ERROR = str(e)

logger = logging.getLogger("ml-analytics")


class SimpleLSTMModel:
    """
    Einfaches LSTM-Modell für 7-Tage Prognosen
    Verwendet Features aus der Feature Engine
    """
    
    def __init__(self, database_pool: asyncpg.Pool, model_storage_path: str):
        self.database_pool = database_pool
        self.model_storage_path = Path(model_storage_path)
        self.model_storage_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Model Configuration
        self.sequence_length = 60  # 60 Tage Historie
        self.prediction_horizon = 7  # 7 Tage Vorhersage
        self.feature_count = 23  # Anzahl der technischen Indikatoren
        
        # Model Components
        self.model = None
        self.scaler = None
        self.feature_columns = None
        
        # Check dependencies
        if not DEPENDENCIES_AVAILABLE:
            self.logger.error(f"ML dependencies not available: {IMPORT_ERROR}")
    
    async def train_model(self, symbol: str = "AAPL") -> Dict[str, Any]:
        """
        Trainiert LSTM-Modell für 7-Tage Prognosen
        """
        try:
            if not DEPENDENCIES_AVAILABLE:
                return {"error": f"ML dependencies not available: {IMPORT_ERROR}"}
            
            self.logger.info(f"Starting LSTM training for {symbol}")
            
            # 1. Lade Trainingsdaten
            training_data = await self._prepare_training_data(symbol)
            if training_data is None:
                return {"error": "Insufficient training data"}
            
            # 2. Erstelle Sequenzen
            X, y = self._create_sequences(training_data)
            if len(X) < 50:  # Mindestens 50 Sequenzen für Training
                return {"error": f"Insufficient sequences for training: {len(X)}"}
            
            # 3. Trainiere Modell
            model_metrics = await self._train_lstm_model(X, y)
            
            # 4. Speichere Modell
            model_path = await self._save_model(symbol)
            
            # 5. Registriere Modell in Datenbank
            await self._register_model(symbol, model_metrics, model_path)
            
            self.logger.info(f"LSTM training completed for {symbol}")
            
            return {
                "symbol": symbol,
                "model_type": "lstm",
                "horizon_days": self.prediction_horizon,
                "training_samples": len(X),
                "model_metrics": model_metrics,
                "model_path": str(model_path),
                "trained_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to train LSTM model for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    async def _prepare_training_data(self, symbol: str, days_back: int = 200) -> Optional[pd.DataFrame]:
        """
        Bereitet Trainingsdaten vor - kombiniert historische Preise mit Features
        """
        try:
            # Generiere historische Sample-Daten für Training
            # In einer echten Implementierung würden diese aus der Produktions-DB kommen
            training_data = self._generate_training_data(symbol, days_back)
            
            if len(training_data) < self.sequence_length + self.prediction_horizon:
                self.logger.warning(f"Insufficient data for {symbol}: {len(training_data)} days")
                return None
            
            return training_data
            
        except Exception as e:
            self.logger.error(f"Failed to prepare training data: {str(e)}")
            return None
    
    def _generate_training_data(self, symbol: str, days: int) -> pd.DataFrame:
        """
        Generiert realistische Trainingsdaten mit Features für LSTM
        """
        np.random.seed(42)  # Reproduzierbare Daten
        
        base_price = 150.0 if symbol == "AAPL" else 100.0
        data = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=days-i)
            
            # Simuliere realistische Kursbewegungen mit Trend
            trend = 0.0002  # Leichter Aufwärtstrend
            volatility = 0.02
            change = np.random.normal(trend, volatility)
            base_price *= (1 + change)
            
            # OHLC-Daten
            daily_vol = np.random.uniform(0.005, 0.025)
            open_price = base_price * (1 + np.random.normal(0, 0.003))
            high_price = open_price * (1 + daily_vol)
            low_price = open_price * (1 - daily_vol * 0.8)
            close_price = open_price + (high_price - low_price) * np.random.uniform(-0.4, 0.6)
            volume = int(np.random.uniform(80_000_000, 120_000_000))
            
            data.append({
                'date': date,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Berechne technische Indikatoren für jede Zeile
        df = self._calculate_features_for_training(df)
        
        return df
    
    def _calculate_features_for_training(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Berechnet alle technischen Indikatoren für Trainingsdaten
        """
        # Moving Averages
        for period in [5, 10, 20, 50]:
            df[f'SMA_{period}'] = df['close'].rolling(window=period).mean()
            df[f'SMA_{period}_ratio'] = df['close'] / df[f'SMA_{period}']
        
        # Exponential Moving Averages
        df['EMA_12'] = df['close'].ewm(span=12).mean()
        df['EMA_26'] = df['close'].ewm(span=26).mean()
        
        # MACD
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['BB_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
        df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
        df['BB_position'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])
        
        # Volume indicators
        df['Volume_SMA_10'] = df['volume'].rolling(window=10).mean()
        df['Volume_ratio'] = df['volume'] / df['Volume_SMA_10']
        
        # Price-based features
        df['daily_return'] = df['close'].pct_change()
        df['volatility_10d'] = df['daily_return'].rolling(window=10).std()
        df['daily_range'] = (df['high'] - df['low']) / df['close']
        
        # Forward-fill NaN values
        df = df.fillna(method='ffill').fillna(0)
        
        return df
    
    def _create_sequences(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Erstellt Sequenzen für LSTM Training
        """
        # Feature Columns (alle außer Datum und Basis-OHLCV)
        feature_cols = [col for col in df.columns if col not in ['date', 'open', 'high', 'low', 'close', 'volume']]
        self.feature_columns = feature_cols
        
        # Normalisierung
        self.scaler = MinMaxScaler()
        scaled_features = self.scaler.fit_transform(df[feature_cols].values)
        
        # Target: 7-Tage Zukunfts-Close-Preis (normalisiert)
        target_scaler = MinMaxScaler()
        scaled_prices = target_scaler.fit_transform(df[['close']].values)
        
        # Speichere Target Scaler für spätere Denormalisierung
        self.target_scaler = target_scaler
        
        X, y = [], []
        
        for i in range(len(scaled_features) - self.sequence_length - self.prediction_horizon + 1):
            # Features der letzten sequence_length Tage
            X.append(scaled_features[i:(i + self.sequence_length)])
            
            # Target: Close-Preis nach prediction_horizon Tagen
            target_idx = i + self.sequence_length + self.prediction_horizon - 1
            y.append(scaled_prices[target_idx][0])
        
        return np.array(X), np.array(y)
    
    async def _train_lstm_model(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Trainiert das LSTM-Modell
        """
        # Train/Validation Split
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # LSTM Model
        self.model = Sequential([
            LSTM(64, return_sequences=True, input_shape=(self.sequence_length, len(self.feature_columns))),
            Dropout(0.2),
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            Dense(16, activation='relu'),
            Dense(1, activation='linear')
        ])
        
        # Compile
        self.model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        # Early Stopping
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        # Training
        history = self.model.fit(
            X_train, y_train,
            epochs=50,
            batch_size=32,
            validation_data=(X_val, y_val),
            callbacks=[early_stopping],
            verbose=0
        )
        
        # Evaluation
        train_pred = self.model.predict(X_train, verbose=0)
        val_pred = self.model.predict(X_val, verbose=0)
        
        train_mse = mean_squared_error(y_train, train_pred)
        val_mse = mean_squared_error(y_val, val_pred)
        train_mae = mean_absolute_error(y_train, train_pred)
        val_mae = mean_absolute_error(y_val, val_pred)
        
        metrics = {
            'train_mse': float(train_mse),
            'val_mse': float(val_mse),
            'train_mae': float(train_mae),
            'val_mae': float(val_mae),
            'epochs_trained': len(history.history['loss'])
        }
        
        self.logger.info(f"Training completed - Val MSE: {val_mse:.6f}, Val MAE: {val_mae:.6f}")
        
        return metrics
    
    async def _save_model(self, symbol: str) -> Path:
        """
        Speichert trainiertes Modell und Metadaten
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        model_dir = self.model_storage_path / f"{symbol}_lstm_7d_{timestamp}"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Speichere Keras Model
        model_path = model_dir / "model.h5"
        self.model.save(str(model_path))
        
        # Speichere Scaler
        scaler_path = model_dir / "scaler.pkl"
        with open(scaler_path, 'wb') as f:
            pickle.dump({
                'feature_scaler': self.scaler,
                'target_scaler': self.target_scaler,
                'feature_columns': self.feature_columns
            }, f)
        
        # Speichere Metadaten
        metadata = {
            'symbol': symbol,
            'model_type': 'lstm',
            'horizon_days': self.prediction_horizon,
            'sequence_length': self.sequence_length,
            'feature_count': len(self.feature_columns),
            'feature_columns': self.feature_columns,
            'created_at': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        }
        
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.logger.info(f"Model saved to {model_dir}")
        return model_dir
    
    async def _register_model(self, symbol: str, metrics: Dict[str, float], model_path: Path):
        """
        Registriert Modell in der ML-Datenbank
        """
        try:
            import uuid
            
            async with self.database_pool.acquire() as conn:
                # Deaktiviere alte Modelle
                await conn.execute("""
                    UPDATE ml_model_metadata 
                    SET status = 'deprecated' 
                    WHERE model_type = 'technical' AND horizon_days = $1
                """, self.prediction_horizon)
                
                # Registriere neues Modell
                model_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO ml_model_metadata 
                    (model_id, model_type, model_version, horizon_days, status, 
                     file_path, scaler_path, performance_metrics, training_config)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, 
                model_id, 'technical', '1.0.0', self.prediction_horizon, 'active',
                str(model_path / "model.h5"), str(model_path / "scaler.pkl"),
                json.dumps(metrics), json.dumps({'symbol': symbol, 'feature_count': len(self.feature_columns)}))
                
                self.logger.info(f"Model registered with ID: {model_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to register model: {str(e)}")
    
    async def predict(self, symbol: str, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Generiert 7-Tage Prognose basierend auf aktuellen Features
        """
        try:
            if not DEPENDENCIES_AVAILABLE:
                return {"error": f"ML dependencies not available: {IMPORT_ERROR}"}
            
            # Lade aktuelles Modell
            model_info = await self._load_latest_model(symbol)
            if not model_info:
                return {"error": f"No trained model found for {symbol}"}
            
            # Bereite Features vor
            prediction_features = self._prepare_prediction_features(features)
            if prediction_features is None:
                return {"error": "Invalid features for prediction"}
            
            # Generiere Vorhersage
            prediction = self.model.predict(prediction_features, verbose=0)[0][0]
            
            # Denormalisierung
            actual_price = self.target_scaler.inverse_transform([[prediction]])[0][0]
            
            # Konfidenz-Score (vereinfacht basierend auf Model-Performance)
            confidence = max(0.3, min(0.9, 1.0 - model_info['val_mse']))
            
            result = {
                "symbol": symbol,
                "model_type": "lstm",
                "horizon_days": 7,
                "predicted_price": round(float(actual_price), 2),
                "confidence_score": round(confidence, 3),
                "prediction_timestamp": datetime.utcnow().isoformat(),
                "model_version": model_info.get('version', '1.0.0')
            }
            
            # Speichere Vorhersage in Datenbank
            await self._store_prediction(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to generate prediction for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    async def _load_latest_model(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Lädt das neueste aktive Modell für ein Symbol
        """
        try:
            async with self.database_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT file_path, scaler_path, performance_metrics, model_version
                    FROM ml_model_metadata
                    WHERE model_type = 'technical' 
                    AND horizon_days = $1 AND status = 'active'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, self.prediction_horizon)
                
                if not row:
                    return None
                
                model_path = Path(row['file_path'])
                scaler_path = Path(row['scaler_path'])
                
                if not model_path.exists():
                    self.logger.error(f"Model path does not exist: {model_path}")
                    return None
                
                if not scaler_path.exists():
                    self.logger.error(f"Scaler path does not exist: {scaler_path}")
                    return None
                
                # Lade Modell
                self.model = tf.keras.models.load_model(str(model_path))
                
                # Lade Scaler
                with open(scaler_path, 'rb') as f:
                    scaler_data = pickle.load(f)
                    self.scaler = scaler_data['feature_scaler']
                    self.target_scaler = scaler_data['target_scaler']
                    self.feature_columns = scaler_data['feature_columns']
                
                metrics = json.loads(row['performance_metrics'])
                return {
                    'model_path': str(model_path),
                    'version': row['model_version'],
                    **metrics
                }
                
        except Exception as e:
            self.logger.error(f"Failed to load model: {str(e)}")
            return None
    
    def _prepare_prediction_features(self, features: Dict[str, float]) -> Optional[np.ndarray]:
        """
        Bereitet Features für Vorhersage vor
        """
        try:
            if not self.feature_columns:
                return None
            
            # Erstelle Feature-Array in der richtigen Reihenfolge
            feature_array = []
            for col in self.feature_columns:
                if col in features:
                    feature_array.append(features[col])
                else:
                    # Fallback für fehlende Features
                    feature_array.append(0.0)
            
            # Normalisierung
            scaled_features = self.scaler.transform([feature_array])
            
            # Erstelle Sequenz (wiederhole aktuelle Features für sequence_length)
            # In einer echten Implementierung würden historische Features verwendet
            sequence = np.repeat(scaled_features, self.sequence_length, axis=0)
            
            return sequence.reshape(1, self.sequence_length, len(self.feature_columns))
            
        except Exception as e:
            self.logger.error(f"Failed to prepare prediction features: {str(e)}")
            return None
    
    async def _store_prediction(self, prediction: Dict[str, Any]):
        """
        Speichert Vorhersage in der Datenbank
        """
        try:
            async with self.database_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO ml_predictions 
                    (symbol, model_type, horizon_days, predicted_value, confidence_score, prediction_timestamp)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, 
                prediction['symbol'],
                prediction['model_type'],
                prediction['horizon_days'],
                prediction['predicted_price'],
                prediction['confidence_score'],
                datetime.fromisoformat(prediction['prediction_timestamp'].replace('Z', '+00:00'))
                )
                
        except Exception as e:
            self.logger.error(f"Failed to store prediction: {str(e)}")