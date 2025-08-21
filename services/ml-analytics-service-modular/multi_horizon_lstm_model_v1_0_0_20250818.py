"""
Multi-Horizon LSTM Model v1.0.0
LSTM-Modell für verschiedene Vorhersagehorizonte (7, 30, 150, 365 Tage)

Autor: Claude Code
Datum: 18. August 2025
"""

import asyncio
import json
import logging
import pickle
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import asyncpg

# Core Dependencies
import numpy as np
import pandas as pd

# TensorFlow/Keras Dependencies
try:
    import tensorflow as tf
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    TENSORFLOW_AVAILABLE = True
except ImportError as e:
    TENSORFLOW_AVAILABLE = False
    tf = None
    # Keep numpy and pandas available even if TensorFlow fails
    MinMaxScaler = None
    train_test_split = None
    mean_squared_error = None
    mean_absolute_error = None
    r2_score = None

logger = logging.getLogger(__name__)

class MultiHorizonLSTMModel:
    """
    Multi-Horizon LSTM-Modell für verschiedene Vorhersagehorizonte
    
    Unterstützte Horizonte:
    - 7 Tage: Kurzfristige Trends
    - 30 Tage: Monatliche Trends
    - 150 Tage: Halbjährliche Trends
    - 365 Tage: Jährliche Trends
    """
    
    # Horizon-spezifische Konfigurationen
    HORIZON_CONFIGS = {
        7: {
            "sequence_length": 60,    # 60 Tage Historie für 7-Tage Prognose
            "lstm_units": [50, 25],   # Zwei LSTM-Layer
            "dropout": 0.2,
            "batch_size": 32,
            "epochs": 100,
            "patience": 15
        },
        30: {
            "sequence_length": 90,    # 90 Tage Historie für 30-Tage Prognose
            "lstm_units": [64, 32],   # Etwas größere Networks
            "dropout": 0.3,
            "batch_size": 32,
            "epochs": 150,
            "patience": 20
        },
        150: {
            "sequence_length": 180,   # 180 Tage Historie für 150-Tage Prognose
            "lstm_units": [80, 40],   # Größere Networks für längere Trends
            "dropout": 0.4,
            "batch_size": 16,         # Kleinere Batches für längere Sequences
            "epochs": 200,
            "patience": 25
        },
        365: {
            "sequence_length": 365,   # 1 Jahr Historie für Jahresprognose
            "lstm_units": [100, 50],  # Große Networks für komplexe Patterns
            "dropout": 0.5,
            "batch_size": 8,          # Sehr kleine Batches
            "epochs": 300,
            "patience": 30
        }
    }
    
    def __init__(self, database_pool: asyncpg.Pool, model_storage_path: str, horizon_days: int = 7):
        self.database_pool = database_pool
        self.model_storage_path = Path(model_storage_path)
        self.horizon_days = horizon_days
        
        if horizon_days not in self.HORIZON_CONFIGS:
            raise ValueError(f"Unsupported horizon: {horizon_days}. Supported: {list(self.HORIZON_CONFIGS.keys())}")
        
        self.config = self.HORIZON_CONFIGS[horizon_days]
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Model Components
        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.model_metadata = {}
        
        if not TENSORFLOW_AVAILABLE:
            self.logger.warning("TensorFlow dependencies not available - model will not function")
    
    async def train_model(self, symbol: str) -> Dict[str, Any]:
        """
        Trainiert Multi-Horizon LSTM-Modell für spezifischen Horizont
        """
        try:
            if not TENSORFLOW_AVAILABLE:
                return {"error": "TensorFlow dependencies not available"}
            
            self.logger.info(f"Starting Multi-Horizon LSTM training for {symbol} ({self.horizon_days} days)")
            
            # Sammle Training-Daten
            training_data = await self._prepare_training_data(symbol)
            
            if training_data is None or len(training_data) < self.config["sequence_length"] + self.horizon_days + 50:
                min_required = self.config["sequence_length"] + self.horizon_days + 50
                return {"error": f"Insufficient training data for {symbol} (need at least {min_required} samples)"}
            
            # Bereite Sequences vor
            X, y = self._prepare_sequences(training_data)
            
            if X is None or len(X) == 0:
                return {"error": "Failed to prepare training sequences"}
            
            # Split in Training/Validation
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42, shuffle=False
            )
            
            # Baue und trainiere Modell
            self.model = self._build_model(X_train.shape)
            history = self._train_model(X_train, y_train, X_val, y_val)
            
            # Evaluierung
            train_pred = self.model.predict(X_train, verbose=0)
            val_pred = self.model.predict(X_val, verbose=0)
            
            # Denormalisiere für Metriken
            train_pred_denorm = self.scaler.inverse_transform(train_pred.reshape(-1, 1)).flatten()
            val_pred_denorm = self.scaler.inverse_transform(val_pred.reshape(-1, 1)).flatten()
            y_train_denorm = self.scaler.inverse_transform(y_train.reshape(-1, 1)).flatten()
            y_val_denorm = self.scaler.inverse_transform(y_val.reshape(-1, 1)).flatten()
            
            metrics = {
                "train_mse": float(mean_squared_error(y_train_denorm, train_pred_denorm)),
                "val_mse": float(mean_squared_error(y_val_denorm, val_pred_denorm)),
                "train_mae": float(mean_absolute_error(y_train_denorm, train_pred_denorm)),
                "val_mae": float(mean_absolute_error(y_val_denorm, val_pred_denorm)),
                "train_r2": float(r2_score(y_train_denorm, train_pred_denorm)),
                "val_r2": float(r2_score(y_val_denorm, val_pred_denorm)),
                "epochs_trained": len(history.history['loss']),
                "final_loss": float(history.history['loss'][-1]),
                "final_val_loss": float(history.history['val_loss'][-1])
            }
            
            # Speichere Modell
            model_path = await self._save_model(symbol, metrics, history)
            
            # Registriere Modell in DB
            await self._register_model(symbol, metrics, model_path)
            
            return {
                "symbol": symbol,
                "model_type": f"multi_horizon_lstm_{self.horizon_days}d",
                "horizon_days": self.horizon_days,
                "sequence_length": self.config["sequence_length"],
                "training_samples": len(X),
                "model_metrics": metrics,
                "model_path": str(model_path),
                "trained_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to train Multi-Horizon LSTM model for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    async def _prepare_training_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Bereitet erweiterte Training-Daten vor (mehr Historie für längere Horizonte)
        """
        try:
            # Benötige mehr historische Daten für längere Horizonte
            months_needed = max(18, (self.config["sequence_length"] + self.horizon_days) // 20)
            
            async with self.database_pool.acquire() as conn:
                query = """
                WITH feature_data AS (
                    SELECT 
                        calculation_timestamp,
                        features_json
                    FROM ml_features_ts
                    WHERE symbol = $1 
                    AND feature_type = 'technical'
                    AND calculation_timestamp > NOW() - INTERVAL '%s months'
                    ORDER BY calculation_timestamp DESC
                ),
                price_data AS (
                    -- Extended Mock Price Data für Multi-Horizon (Mehr historische Daten)
                    SELECT 
                        date_trunc('day', calculation_timestamp) as date,
                        -- Realistische Preisdaten mit Trends über verschiedene Zeiträume
                        150.0 + 
                        -- Kurzfristige Volatilität (täglich)
                        (RANDOM() - 0.5) * 8 +
                        -- Mittelfristige Trends (7-30 Tage)
                        SIN(EXTRACT(epoch FROM calculation_timestamp) / 86400.0 / 14) * 12 +
                        -- Längerfristige Trends (30-150 Tage)
                        SIN(EXTRACT(epoch FROM calculation_timestamp) / 86400.0 / 60) * 18 +
                        -- Langfristige Trends (365 Tage)
                        COS(EXTRACT(epoch FROM calculation_timestamp) / 86400.0 / 180) * 25 +
                        -- Sehr langfristige Trends (mehrere Jahre)
                        SIN(EXTRACT(epoch FROM calculation_timestamp) / 86400.0 / 360) * 30 +
                        -- Saisonale Effekte
                        CASE 
                            WHEN EXTRACT(month FROM calculation_timestamp) IN (11,12,1) THEN 8.0  -- Winter rally
                            WHEN EXTRACT(month FROM calculation_timestamp) IN (5,6) THEN -5.0     -- Sell in May
                            WHEN EXTRACT(month FROM calculation_timestamp) IN (3,4) THEN 3.0      -- Spring rally
                            WHEN EXTRACT(month FROM calculation_timestamp) IN (9,10) THEN -2.0    -- Fall volatility
                            ELSE 0
                        END +
                        -- Wochentagseffekte
                        CASE EXTRACT(dow FROM calculation_timestamp)
                            WHEN 1 THEN 1.5   -- Monday effect
                            WHEN 5 THEN -1.0  -- Friday selloff
                            ELSE 0
                        END as price
                    FROM feature_data
                    GROUP BY date_trunc('day', calculation_timestamp)
                )
                SELECT 
                    DATE(f.calculation_timestamp) as feature_date,
                    f.features_json,
                    p1.price as current_price,
                    p2.price as future_price_%sd
                FROM feature_data f
                JOIN price_data p1 ON p1.date = DATE(f.calculation_timestamp)
                JOIN price_data p2 ON p2.date = DATE(f.calculation_timestamp) + INTERVAL '%s days'
                WHERE DATE(f.calculation_timestamp) <= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY f.calculation_timestamp ASC
                LIMIT 2000
                """ % (months_needed, self.horizon_days, self.horizon_days, self.horizon_days)
                
                rows = await conn.fetch(query, symbol)
                
                if not rows:
                    return None
                
                # Konvertiere zu DataFrame
                data = []
                for row in rows:
                    feature_dict = json.loads(row['features_json']) if isinstance(row['features_json'], str) else row['features_json']
                    feature_dict['current_price'] = float(row['current_price'])
                    feature_dict[f'target_price_{self.horizon_days}d'] = float(row[f'future_price_{self.horizon_days}d'])
                    feature_dict['target_return'] = (feature_dict[f'target_price_{self.horizon_days}d'] - feature_dict['current_price']) / feature_dict['current_price']
                    data.append(feature_dict)
                
                if not data:
                    return None
                
                df = pd.DataFrame(data)
                return df
                
        except Exception as e:
            self.logger.error(f"Failed to prepare training data: {str(e)}")
            return None
    
    def _prepare_sequences(self, df: pd.DataFrame) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Bereitet LSTM-Sequences vor
        """
        try:
            # Feature-Auswahl (technische Indikatoren + Preise)
            feature_columns = [col for col in df.columns if col not in [
                f'target_price_{self.horizon_days}d', 'target_return'
            ]]
            
            # Bereinige Daten
            df_clean = df[feature_columns + ['target_return']].dropna()
            
            if len(df_clean) < self.config["sequence_length"] + self.horizon_days:
                self.logger.error("Insufficient clean data after preprocessing")
                return None, None
            
            # Normalisiere Features
            features = df_clean[feature_columns].values
            targets = df_clean['target_return'].values
            
            self.scaler = MinMaxScaler()
            features_scaled = self.scaler.fit_transform(features)
            
            # Erstelle Sequences
            X, y = [], []
            sequence_length = self.config["sequence_length"]
            
            for i in range(sequence_length, len(features_scaled)):
                X.append(features_scaled[i-sequence_length:i])
                y.append(targets[i])
            
            X = np.array(X)
            y = np.array(y)
            
            self.feature_columns = feature_columns
            
            self.logger.info(f"Prepared sequences: {X.shape[0]} samples, "
                           f"{X.shape[1]} timesteps, {X.shape[2]} features")
            
            return X, y
            
        except Exception as e:
            self.logger.error(f"Failed to prepare sequences: {str(e)}")
            return None, None
    
    def _build_model(self, input_shape: tuple):
        """
        Baut Horizon-spezifisches LSTM-Modell
        """
        if not TENSORFLOW_AVAILABLE:
            self.logger.warning("TensorFlow not available, returning None model")
            return None
            
        model = tf.keras.Sequential()
        
        # Erste LSTM-Schicht
        model.add(tf.keras.layers.LSTM(
            self.config["lstm_units"][0],
            return_sequences=True,
            input_shape=(input_shape[1], input_shape[2])
        ))
        model.add(tf.keras.layers.Dropout(self.config["dropout"]))
        
        # Zweite LSTM-Schicht
        model.add(tf.keras.layers.LSTM(
            self.config["lstm_units"][1],
            return_sequences=False
        ))
        model.add(tf.keras.layers.Dropout(self.config["dropout"]))
        
        # Dense Layers (angepasst an Horizont)
        if self.horizon_days <= 30:
            # Kleinere Networks für kurze Horizonte
            model.add(tf.keras.layers.Dense(25, activation='relu'))
            model.add(tf.keras.layers.Dense(10, activation='relu'))
        else:
            # Größere Networks für lange Horizonte
            model.add(tf.keras.layers.Dense(50, activation='relu'))
            model.add(tf.keras.layers.Dense(25, activation='relu'))
            model.add(tf.keras.layers.Dense(10, activation='relu'))
        
        # Output Layer
        model.add(tf.keras.layers.Dense(1))
        
        # Horizont-spezifische Learning Rate
        learning_rate = 0.001 if self.horizon_days <= 30 else 0.0005
        
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def _train_model(self, X_train, y_train, X_val, y_val):
        """
        Trainiert das Modell mit Horizon-spezifischen Parametern
        """
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=self.config["patience"],
                restore_best_weights=True
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=self.config["patience"] // 2,
                min_lr=1e-6
            )
        ]
        
        history = self.model.fit(
            X_train, y_train,
            epochs=self.config["epochs"],
            batch_size=self.config["batch_size"],
            validation_data=(X_val, y_val),
            callbacks=callbacks,
            verbose=0
        )
        
        return history
    
    async def _save_model(self, symbol: str, metrics: Dict[str, Any], history) -> Path:
        """
        Speichert Multi-Horizon LSTM-Modell
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        model_dir = self.model_storage_path / f"{symbol}_multi_lstm_{self.horizon_days}d_{timestamp}"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Speichere TensorFlow Modell
        self.model.save(str(model_dir / "model.h5"))
        
        # Speichere Scaler und Metadaten
        with open(model_dir / "scaler.pkl", 'wb') as f:
            pickle.dump({
                'scaler': self.scaler,
                'feature_columns': self.feature_columns,
                'horizon_days': self.horizon_days,
                'config': self.config
            }, f)
        
        # Speichere Training History
        with open(model_dir / "training_history.json", 'w') as f:
            json.dump({
                k: [float(v) for v in vals] for k, vals in history.history.items()
            }, f, indent=2)
        
        # Speichere Metadaten
        metadata = {
            "symbol": symbol,
            "model_type": f"multi_horizon_lstm_{self.horizon_days}d",
            "horizon_days": self.horizon_days,
            "sequence_length": self.config["sequence_length"],
            "created_at": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "feature_count": len(self.feature_columns) if self.feature_columns else 0,
            "model_config": self.config,
            "tensorflow_version": tf.__version__
        }
        
        with open(model_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.logger.info(f"Multi-Horizon LSTM model ({self.horizon_days}d) saved to {model_dir}")
        return model_dir
    
    async def _register_model(self, symbol: str, metrics: Dict[str, Any], model_path: Path):
        """
        Registriert Multi-Horizon Modell in der Datenbank
        """
        try:
            import uuid
            
            async with self.database_pool.acquire() as conn:
                # Deaktiviere alte Modelle für diesen Horizont
                await conn.execute("""
                    UPDATE ml_model_metadata 
                    SET status = 'deprecated' 
                    WHERE model_type = $1 AND horizon_days = $2
                """, f'multi_horizon_lstm', self.horizon_days)
                
                # Registriere neues Modell
                model_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO ml_model_metadata 
                    (model_id, model_type, model_version, horizon_days, status, 
                     file_path, scaler_path, performance_metrics, training_config)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, 
                model_id, 'multi_horizon_lstm', '1.0.0', self.horizon_days, 'active',
                str(model_path / "model.h5"), str(model_path / "scaler.pkl"),
                json.dumps(metrics), json.dumps({
                    'symbol': symbol, 
                    'feature_count': len(self.feature_columns),
                    'config': self.config
                }))
                
                self.logger.info(f"Multi-Horizon LSTM model ({self.horizon_days}d) registered with ID: {model_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to register model: {str(e)}")
    
    async def predict(self, symbol: str, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Generiert Multi-Horizon Prognose
        """
        try:
            if not TENSORFLOW_AVAILABLE:
                return {"error": "TensorFlow dependencies not available"}
            
            # Lade Modell falls nicht geladen
            if self.model is None:
                model_info = await self._load_latest_model(symbol)
                if not model_info:
                    return {"error": f"No trained multi-horizon model found for {symbol} ({self.horizon_days}d)"}
            
            # Hole historische Sequence
            sequence_data = await self._get_prediction_sequence(symbol)
            if sequence_data is None:
                return {"error": "Failed to get historical sequence for prediction"}
            
            # Bereite Prediction vor
            prediction = self.model.predict(sequence_data, verbose=0)[0][0]
            
            # Denormalisiere
            current_price = features.get('current_price', 150.0)
            predicted_return = prediction
            predicted_price = current_price * (1 + predicted_return)
            
            # Berechne Horizon-spezifische Confidence
            confidence_score = self._calculate_horizon_confidence(predicted_return)
            
            return {
                "symbol": symbol,
                "model_type": f"multi_horizon_lstm_{self.horizon_days}d",
                "horizon_days": self.horizon_days,
                "predicted_price": round(float(predicted_price), 2),
                "predicted_return": round(float(predicted_return * 100), 2),
                "confidence_score": confidence_score,
                "prediction_timestamp": datetime.utcnow().isoformat(),
                "model_version": "1.0.0",
                "sequence_length": self.config["sequence_length"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate multi-horizon prediction for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    async def _get_prediction_sequence(self, symbol: str) -> Optional[np.ndarray]:
        """
        Holt die letzten sequence_length Datenpunkte für Prediction
        """
        try:
            async with self.database_pool.acquire() as conn:
                query = """
                SELECT features_json
                FROM ml_features_ts
                WHERE symbol = $1 AND feature_type = 'technical'
                ORDER BY calculation_timestamp DESC
                LIMIT $2
                """
                
                rows = await conn.fetch(query, symbol, self.config["sequence_length"])
                
                if len(rows) < self.config["sequence_length"]:
                    return None
                
                # Bereite Features vor
                features_list = []
                for row in reversed(rows):  # Chronologische Reihenfolge
                    features = json.loads(row['features_json']) if isinstance(row['features_json'], str) else row['features_json']
                    feature_vector = [features.get(col, 0.0) for col in self.feature_columns]
                    features_list.append(feature_vector)
                
                # Normalisiere und forme zu Sequence
                features_array = np.array(features_list)
                features_scaled = self.scaler.transform(features_array)
                
                return features_scaled.reshape(1, self.config["sequence_length"], len(self.feature_columns))
                
        except Exception as e:
            self.logger.error(f"Failed to get prediction sequence: {str(e)}")
            return None
    
    def _calculate_horizon_confidence(self, predicted_return: float) -> float:
        """
        Berechnet Horizon-spezifische Confidence Score
        """
        # Basis-Confidence abhängig von Horizont
        base_confidence = {
            7: 0.85,    # Hohe Confidence für kurze Horizonte
            30: 0.75,   # Mittlere Confidence für monatliche Prognosen
            150: 0.65,  # Niedrigere Confidence für halbjährlich
            365: 0.55   # Niedrigste Confidence für Jahresprognosen
        }.get(self.horizon_days, 0.70)
        
        # Penalty für extreme Vorhersagen
        abs_return = abs(predicted_return)
        if abs_return > 0.5:  # >50% Return
            base_confidence *= 0.7
        elif abs_return > 0.3:  # >30% Return
            base_confidence *= 0.85
        elif abs_return > 0.1:  # >10% Return
            base_confidence *= 0.95
        
        return min(max(base_confidence, 0.3), 0.95)
    
    async def _load_latest_model(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Lädt das neueste aktive Multi-Horizon Modell
        """
        try:
            async with self.database_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT file_path, scaler_path, performance_metrics, model_version
                    FROM ml_model_metadata
                    WHERE model_type = 'multi_horizon_lstm' 
                    AND horizon_days = $1 AND status = 'active'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, self.horizon_days)
                
                if not row:
                    return None
                
                model_path = Path(row['file_path'])
                scaler_path = Path(row['scaler_path'])
                
                if not model_path.exists() or not scaler_path.exists():
                    self.logger.error(f"Model files not found: {model_path}, {scaler_path}")
                    return None
                
                # Lade TensorFlow Modell
                self.model = tf.keras.models.load_model(str(model_path))
                
                # Lade Scaler
                with open(scaler_path, 'rb') as f:
                    scaler_data = pickle.load(f)
                    self.scaler = scaler_data['scaler']
                    self.feature_columns = scaler_data['feature_columns']
                    self.config = scaler_data.get('config', self.config)
                
                metrics = json.loads(row['performance_metrics'])
                return {
                    'model_path': str(model_path),
                    'version': row['model_version'],
                    **metrics
                }
                
        except Exception as e:
            self.logger.error(f"Failed to load multi-horizon model: {str(e)}")
            return None

# Export für einfache Imports
__all__ = ['MultiHorizonLSTMModel']