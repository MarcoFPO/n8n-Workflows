"""
Synthetic Multi-Horizon Trainer v1.0.0
Trainiert Multi-Horizon LSTM Modelle mit synthetischen Daten

Autor: Claude Code
Datum: 18. August 2025
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncpg

# ML Dependencies
try:
    import tensorflow as tf
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

logger = logging.getLogger(__name__)

class SyntheticMultiHorizonTrainer:
    """
    Trainer für Multi-Horizon LSTM Modelle mit synthetischen Daten
    Erstellt realistische Trainingsdaten für verschiedene Horizonte
    """
    
    HORIZON_CONFIGS = {
        7: {
            "sequence_length": 30,    # Weniger Historie für schnelleres Training
            "lstm_units": [32, 16],   # Kleinere Networks
            "dropout": 0.2,
            "batch_size": 16,
            "epochs": 50,
            "patience": 10
        },
        30: {
            "sequence_length": 60,    # Moderate Historie
            "lstm_units": [48, 24],   
            "dropout": 0.3,
            "batch_size": 16,
            "epochs": 75,
            "patience": 15
        },
        150: {
            "sequence_length": 90,    # Längere Historie
            "lstm_units": [64, 32],   
            "dropout": 0.4,
            "batch_size": 8,
            "epochs": 100,
            "patience": 20
        },
        365: {
            "sequence_length": 120,   # Maximale Historie
            "lstm_units": [80, 40],   
            "dropout": 0.5,
            "batch_size": 8,
            "epochs": 150,
            "patience": 25
        }
    }
    
    def __init__(self, database_pool: asyncpg.Pool, model_storage_path: str):
        self.database_pool = database_pool
        self.model_storage_path = Path(model_storage_path)
        self.model_storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if not TENSORFLOW_AVAILABLE:
            self.logger.warning("TensorFlow dependencies not available")
    
    async def train_all_horizons(self, symbol: str = "AAPL") -> Dict[str, Any]:
        """
        Trainiert Modelle für alle unterstützten Horizonte
        """
        try:
            if not TENSORFLOW_AVAILABLE:
                return {"error": "TensorFlow dependencies not available"}
            
            self.logger.info(f"Starting multi-horizon training for {symbol}")
            results = {}
            
            # Generiere umfangreiche synthetische Daten
            synthetic_data = self._generate_comprehensive_data(symbol, days=1000)
            
            for horizon in [7, 30, 150, 365]:
                self.logger.info(f"Training {horizon}-day horizon model for {symbol}")
                
                try:
                    result = await self._train_single_horizon(symbol, horizon, synthetic_data)
                    results[f"{horizon}d"] = result
                    
                    if "error" not in result:
                        self.logger.info(f"Successfully trained {horizon}-day model - Val MSE: {result.get('model_metrics', {}).get('val_mse', 'N/A')}")
                    else:
                        self.logger.error(f"Failed to train {horizon}-day model: {result['error']}")
                        
                except Exception as e:
                    self.logger.error(f"Exception training {horizon}-day model: {str(e)}")
                    results[f"{horizon}d"] = {"error": str(e)}
            
            # Summary
            successful_models = len([r for r in results.values() if "error" not in r])
            
            return {
                "symbol": symbol,
                "training_completed_at": datetime.utcnow().isoformat(),
                "results": results,
                "summary": {
                    "total_horizons": len(self.HORIZON_CONFIGS),
                    "successful_models": successful_models,
                    "failed_models": len(self.HORIZON_CONFIGS) - successful_models
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed multi-horizon training for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    def _generate_comprehensive_data(self, symbol: str, days: int = 1000) -> pd.DataFrame:
        """
        Generiert umfangreiche synthetische Daten für Multi-Horizon Training
        """
        np.random.seed(42)  # Reproduzierbare Daten
        
        base_price = 150.0 if symbol == "AAPL" else 100.0
        data = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=days-i)
            
            # Komplexere Preisbewegungen mit verschiedenen Zeitzyklen
            day_of_year = date.timetuple().tm_yday
            day_of_week = date.weekday()
            
            # Langzeit-Trend (Jahr-zu-Jahr Wachstum)
            yearly_trend = 0.08 / 365  # 8% jährliches Wachstum
            
            # Saisonalität (mehrere Zyklen)
            seasonal_1 = np.sin(2 * np.pi * day_of_year / 365) * 0.15  # Jährlicher Zyklus
            seasonal_2 = np.sin(2 * np.pi * day_of_year / 90) * 0.08   # Quartals-Zyklus
            seasonal_3 = np.sin(2 * np.pi * day_of_year / 30) * 0.05   # Monats-Zyklus
            
            # Wochentagseffekte
            weekly_effect = {0: 0.002, 1: -0.001, 2: 0.0, 3: 0.0, 4: -0.002, 5: 0.0, 6: 0.0}[day_of_week]
            
            # Volatilität-Clustering (realistischer)
            if i > 0:
                prev_volatility = abs(data[-1]['daily_return']) if data else 0.02
                volatility = 0.7 * prev_volatility + 0.3 * np.random.exponential(0.015)
            else:
                volatility = 0.02
            
            # Tägliche Rendite
            daily_return = (yearly_trend + seasonal_1 + seasonal_2 + seasonal_3 + 
                          weekly_effect + np.random.normal(0, volatility))
            
            # Preis-Update
            base_price *= (1 + daily_return)
            
            # OHLCV-Daten mit realistischen Intraday-Bewegungen
            open_price = base_price * (1 + np.random.normal(0, 0.002))
            high_low_spread = np.random.uniform(0.008, 0.030)
            high_price = open_price * (1 + high_low_spread * np.random.uniform(0.3, 1.0))
            low_price = open_price * (1 - high_low_spread * np.random.uniform(0.3, 0.8))
            close_price = open_price + (high_price - low_price) * np.random.uniform(-0.4, 0.6)
            volume = int(np.random.lognormal(18.2, 0.3))  # Lognormal für realistische Volumen
            
            data.append({
                'date': date,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume,
                'daily_return': daily_return
            })
            
            base_price = close_price  # Update für nächsten Tag
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Technische Indikatoren berechnen
        df = self._calculate_comprehensive_features(df)
        
        return df
    
    def _calculate_comprehensive_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Berechnet umfangreiche technische Indikatoren
        """
        # Moving Averages (verschiedene Perioden)
        for period in [5, 10, 20, 50, 100, 200]:
            if len(df) > period:
                df[f'SMA_{period}'] = df['close'].rolling(window=period).mean()
                df[f'SMA_{period}_ratio'] = df['close'] / df[f'SMA_{period}']
        
        # Exponential Moving Averages
        for span in [12, 26, 50]:
            df[f'EMA_{span}'] = df['close'].ewm(span=span).mean()
            df[f'EMA_{span}_ratio'] = df['close'] / df[f'EMA_{span}']
        
        # MACD
        if 'EMA_12' in df.columns and 'EMA_26' in df.columns:
            df['MACD'] = df['EMA_12'] - df['EMA_26']
            df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
            df['MACD_histogram'] = df['MACD'] - df['MACD_signal']
        
        # RSI (verschiedene Perioden)
        for period in [14, 30]:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            df[f'RSI_{period}'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        for period in [20, 50]:
            sma = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()
            df[f'BB_{period}_upper'] = sma + (std * 2)
            df[f'BB_{period}_lower'] = sma - (std * 2)
            df[f'BB_{period}_position'] = ((df['close'] - df[f'BB_{period}_lower']) / 
                                          (df[f'BB_{period}_upper'] - df[f'BB_{period}_lower']))
        
        # Volatilität (verschiedene Zeitfenster)
        for period in [10, 30, 60]:
            df[f'volatility_{period}d'] = df['daily_return'].rolling(window=period).std()
        
        # Volume-basierte Indikatoren
        for period in [10, 30]:
            df[f'Volume_SMA_{period}'] = df['volume'].rolling(window=period).mean()
            df[f'Volume_ratio_{period}'] = df['volume'] / df[f'Volume_SMA_{period}']
        
        # Price-Range und True Range
        df['daily_range'] = (df['high'] - df['low']) / df['close']
        df['true_range'] = np.maximum(df['high'] - df['low'],
                                     np.maximum(abs(df['high'] - df['close'].shift(1)),
                                               abs(df['low'] - df['close'].shift(1))))
        df['ATR_14'] = df['true_range'].rolling(window=14).mean()
        
        # Momentum-Indikatoren
        for period in [10, 20]:
            df[f'momentum_{period}'] = df['close'] / df['close'].shift(period) - 1
        
        # Erweiterte Datenbereinigung für numerische Stabilität
        df = df.fillna(method='ffill').fillna(0)
        
        # Entferne Infinity und übermäßig große Werte
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            # Ersetze Inf und -Inf mit NaN
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)
            
            # Clipping extremer Werte (3 Standardabweichungen)
            if col not in ['date', 'volume']:  # Schütze bestimmte Spalten
                mean = df[col].mean()
                std = df[col].std()
                if not np.isnan(mean) and not np.isnan(std) and std > 0:
                    lower_bound = mean - 3 * std
                    upper_bound = mean + 3 * std
                    df[col] = df[col].clip(lower_bound, upper_bound)
        
        # Final cleanup
        df = df.fillna(method='ffill').fillna(0)
        
        # Validiere finale Daten
        if df.isnull().any().any():
            logger.warning("NaN values still present after cleaning")
        
        if np.isinf(df.select_dtypes(include=[np.number]).values).any():
            logger.warning("Infinity values still present after cleaning")
            # Notfall-Bereinigung
            df = df.replace([np.inf, -np.inf], 0)
        
        return df
    
    async def _train_single_horizon(self, symbol: str, horizon: int, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Trainiert ein einzelnes Multi-Horizon LSTM Modell
        """
        try:
            config = self.HORIZON_CONFIGS[horizon]
            
            # Bereite Training-Daten vor
            X, y, feature_columns, scaler = self._prepare_training_sequences(data, horizon, config)
            
            if X is None or len(X) < 50:
                return {"error": f"Insufficient training sequences: {len(X) if X is not None else 0}"}
            
            # Train/Validation Split
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42, shuffle=False
            )
            
            # Baue und trainiere Modell
            model = self._build_horizon_model(X_train.shape, config, horizon)
            history = self._train_horizon_model(model, X_train, y_train, X_val, y_val, config)
            
            # Evaluierung
            train_pred = model.predict(X_train, verbose=0)
            val_pred = model.predict(X_val, verbose=0)
            
            metrics = {
                "train_mse": float(mean_squared_error(y_train, train_pred)),
                "val_mse": float(mean_squared_error(y_val, val_pred)),
                "train_mae": float(mean_absolute_error(y_train, train_pred)),
                "val_mae": float(mean_absolute_error(y_val, val_pred)),
                "train_r2": float(r2_score(y_train, train_pred)),
                "val_r2": float(r2_score(y_val, val_pred)),
                "epochs_trained": len(history.history['loss']),
                "final_loss": float(history.history['loss'][-1]),
                "final_val_loss": float(history.history['val_loss'][-1])
            }
            
            # Speichere Modell
            model_path = await self._save_horizon_model(symbol, horizon, model, scaler, feature_columns, metrics)
            
            # Registriere in DB
            await self._register_horizon_model(symbol, horizon, metrics, model_path)
            
            return {
                "symbol": symbol,
                "model_type": f"multi_horizon_lstm_{horizon}d",
                "horizon_days": horizon,
                "sequence_length": config["sequence_length"],
                "training_samples": len(X),
                "model_metrics": metrics,
                "model_path": str(model_path),
                "trained_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to train {horizon}-day model: {str(e)}")
            return {"error": str(e)}
    
    def _prepare_training_sequences(self, df: pd.DataFrame, horizon: int, config: Dict) -> tuple:
        """
        Bereitet Training-Sequences vor
        """
        try:
            # Feature-Auswahl (alle technischen Indikatoren)
            excluded_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'daily_return']
            feature_columns = [col for col in df.columns if col not in excluded_cols]
            
            if len(feature_columns) == 0:
                return None, None, None, None
            
            # Bereinige Daten
            df_clean = df[feature_columns + ['close']].dropna()
            
            if len(df_clean) < config["sequence_length"] + horizon + 50:
                return None, None, None, None
            
            # Zusätzliche Validierung vor Normalisierung
            features_df = df_clean[feature_columns]
            
            # Prüfe auf problematische Werte
            if features_df.isnull().any().any():
                self.logger.warning("NaN values detected in features before scaling")
                features_df = features_df.fillna(0)
            
            if np.isinf(features_df.values).any():
                self.logger.warning("Infinity values detected in features before scaling")
                features_df = features_df.replace([np.inf, -np.inf], 0)
            
            # Validiere Datenbereich für Scaler
            features = features_df.values
            prices = df_clean['close'].values
            
            # Entferne Spalten mit konstanten Werten (Varianz = 0)
            feature_variance = np.var(features, axis=0)
            valid_features_mask = feature_variance > 1e-8
            
            if not valid_features_mask.any():
                self.logger.error("All features have zero variance")
                return None, None, None, None
            
            features = features[:, valid_features_mask]
            valid_feature_columns = [col for i, col in enumerate(feature_columns) if valid_features_mask[i]]
            
            self.logger.info(f"Using {len(valid_feature_columns)} valid features out of {len(feature_columns)}")
            
            # Normalisierung mit robusteren Grenzen
            scaler = MinMaxScaler(feature_range=(-1, 1))  # Symmetrischer Bereich
            
            try:
                features_scaled = scaler.fit_transform(features)
            except Exception as e:
                self.logger.error(f"Scaling failed: {str(e)}")
                return None, None, None, None
            
            # Final validation der skalierten Features
            if np.isnan(features_scaled).any() or np.isinf(features_scaled).any():
                self.logger.error("Scaled features contain NaN or Inf values")
                return None, None, None, None
            
            # Erstelle Sequences
            X, y = [], []
            sequence_length = config["sequence_length"]
            
            for i in range(len(features_scaled) - sequence_length - horizon + 1):
                X.append(features_scaled[i:i + sequence_length])
                
                # Target: Preis nach horizon Tagen (als Return)
                current_price = prices[i + sequence_length - 1]
                future_price = prices[i + sequence_length + horizon - 1]
                target_return = (future_price - current_price) / current_price
                y.append(target_return)
            
            return np.array(X), np.array(y), valid_feature_columns, scaler
            
        except Exception as e:
            self.logger.error(f"Failed to prepare training sequences: {str(e)}")
            return None, None, None, None
    
    def _build_horizon_model(self, input_shape: tuple, config: Dict, horizon: int) -> tf.keras.Model:
        """
        Baut Horizon-spezifisches LSTM-Modell
        """
        model = tf.keras.Sequential()
        
        # LSTM Layers
        model.add(tf.keras.layers.LSTM(
            config["lstm_units"][0],
            return_sequences=True,
            input_shape=(input_shape[1], input_shape[2])
        ))
        model.add(tf.keras.layers.Dropout(config["dropout"]))
        
        model.add(tf.keras.layers.LSTM(
            config["lstm_units"][1],
            return_sequences=False
        ))
        model.add(tf.keras.layers.Dropout(config["dropout"]))
        
        # Dense Layers (angepasst an Horizont)
        if horizon <= 30:
            model.add(tf.keras.layers.Dense(16, activation='relu'))
            model.add(tf.keras.layers.Dense(8, activation='relu'))
        else:
            model.add(tf.keras.layers.Dense(32, activation='relu'))
            model.add(tf.keras.layers.Dense(16, activation='relu'))
            model.add(tf.keras.layers.Dense(8, activation='relu'))
        
        # Output Layer (Return prediction)
        model.add(tf.keras.layers.Dense(1, activation='tanh'))  # tanh für bounded returns
        
        # Compile mit horizon-spezifischer Learning Rate
        learning_rate = 0.001 if horizon <= 30 else 0.0005
        
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def _train_horizon_model(self, model: tf.keras.Model, X_train, y_train, X_val, y_val, config: Dict):
        """
        Trainiert das Modell
        """
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=config["patience"],
                restore_best_weights=True
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.7,
                patience=config["patience"] // 2,
                min_lr=1e-6
            )
        ]
        
        history = model.fit(
            X_train, y_train,
            epochs=config["epochs"],
            batch_size=config["batch_size"],
            validation_data=(X_val, y_val),
            callbacks=callbacks,
            verbose=0
        )
        
        return history
    
    async def _save_horizon_model(self, symbol: str, horizon: int, model: tf.keras.Model, 
                                 scaler, feature_columns: List[str], metrics: Dict) -> Path:
        """
        Speichert Multi-Horizon Modell
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        model_dir = self.model_storage_path / f"{symbol}_multi_lstm_{horizon}d_{timestamp}"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # TensorFlow Modell
        model.save(str(model_dir / "model.h5"))
        
        # Scaler und Metadaten
        import pickle
        with open(model_dir / "scaler.pkl", 'wb') as f:
            pickle.dump({
                'scaler': scaler,
                'feature_columns': feature_columns,
                'horizon_days': horizon,
                'config': self.HORIZON_CONFIGS[horizon]
            }, f)
        
        # Metadaten
        metadata = {
            "symbol": symbol,
            "model_type": f"multi_horizon_lstm_{horizon}d",
            "horizon_days": horizon,
            "created_at": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "feature_count": len(feature_columns),
            "tensorflow_version": tf.__version__
        }
        
        with open(model_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return model_dir
    
    async def _register_horizon_model(self, symbol: str, horizon: int, metrics: Dict, model_path: Path):
        """
        Registriert Multi-Horizon Modell in der Datenbank
        """
        try:
            import uuid
            
            async with self.database_pool.acquire() as conn:
                # Deaktiviere alte Modelle
                await conn.execute("""
                    UPDATE ml_model_metadata 
                    SET status = 'deprecated' 
                    WHERE model_type = $1 AND horizon_days = $2
                """, 'multi_horizon_lstm', horizon)
                
                # Registriere neues Modell
                model_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO ml_model_metadata 
                    (model_id, model_type, model_version, horizon_days, status, 
                     file_path, scaler_path, performance_metrics, training_config)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, 
                model_id, 'multi_horizon_lstm', '1.0.0', horizon, 'active',
                str(model_path / "model.h5"), str(model_path / "scaler.pkl"),
                json.dumps(metrics), json.dumps({
                    'symbol': symbol, 
                    'config': self.HORIZON_CONFIGS[horizon]
                }))
                
        except Exception as e:
            self.logger.error(f"Failed to register model: {str(e)}")

# Export
__all__ = ['SyntheticMultiHorizonTrainer']