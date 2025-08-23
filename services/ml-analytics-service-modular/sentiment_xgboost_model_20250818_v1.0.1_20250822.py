"""
Sentiment XGBoost Model v1.0.0
XGBoost-basiertes Modell für Sentiment-Features Integration

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

# XGBoost Dependencies
try:
    import xgboost as xgb
    import pandas as pd
    import numpy as np
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    XGBOOST_AVAILABLE = True
except ImportError as e:
    XGBOOST_AVAILABLE = False
    xgb = None
    pd = None
    np = None

logger = logging.getLogger(__name__)

class SentimentXGBoostModel:
    """
    XGBoost-Modell für Sentiment-basierte Prognosen
    """
    
    def __init__(self, database_pool: asyncpg.Pool, model_storage_path: str):
        self.database_pool = database_pool
        self.model_storage_path = Path(model_storage_path)
        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.prediction_horizon = 7  # 7-Tage Prognosen
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if not XGBOOST_AVAILABLE:
            self.logger.warning("XGBoost dependencies not available - model will not function")
    
    async def train_model(self, symbol: str) -> Dict[str, Any]:
        """
        Trainiert XGBoost-Modell mit Sentiment-Features
        """
        try:
            if not XGBOOST_AVAILABLE:
                return {"error": "XGBoost dependencies not available"}
            
            self.logger.info(f"Starting XGBoost sentiment model training for {symbol}")
            
            # Sammle Training-Daten
            training_data = await self._prepare_training_data(symbol)
            
            if training_data is None or len(training_data) < 50:
                return {"error": f"Insufficient training data for {symbol} (need at least 50 samples)"}
            
            # Bereite Features und Targets vor
            X, y = await self._prepare_features_and_targets(training_data)
            
            if X is None or len(X) == 0:
                return {"error": "Failed to prepare training features"}
            
            # Split in Training/Validation
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42, shuffle=False
            )
            
            # Feature Scaling
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_val_scaled = self.scaler.transform(X_val)
            
            # Trainiere XGBoost Model
            self.model = xgb.XGBRegressor(
                n_estimators=500,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                early_stopping_rounds=50,
                eval_metric='rmse'
            )
            
            # Training mit Early Stopping
            self.model.fit(
                X_train_scaled, y_train,
                eval_set=[(X_val_scaled, y_val)],
                verbose=False
            )
            
            # Evaluierung
            train_pred = self.model.predict(X_train_scaled)
            val_pred = self.model.predict(X_val_scaled)
            
            metrics = {
                "train_mse": float(mean_squared_error(y_train, train_pred)),
                "val_mse": float(mean_squared_error(y_val, val_pred)),
                "train_mae": float(mean_absolute_error(y_train, train_pred)),
                "val_mae": float(mean_absolute_error(y_val, val_pred)),
                "n_estimators_used": int(self.model.best_iteration) if hasattr(self.model, 'best_iteration') else 500,
                "feature_importance": self._get_feature_importance()
            }
            
            # Speichere Modell
            model_path = await self._save_model(symbol, metrics)
            
            # Registriere Modell in DB
            await self._register_model(symbol, metrics, model_path)
            
            return {
                "symbol": symbol,
                "model_type": "sentiment_xgboost",
                "horizon_days": self.prediction_horizon,
                "training_samples": len(X),
                "model_metrics": metrics,
                "model_path": str(model_path),
                "trained_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to train sentiment XGBoost model for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    async def _prepare_training_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Bereitet Training-Daten aus verschiedenen Feature-Quellen vor
        """
        try:
            async with self.database_pool.acquire() as conn:
                # Hole kombinierte Features (Technical + Sentiment) mit Future Price
                query = """
                WITH feature_data AS (
                    SELECT 
                        calculation_timestamp,
                        features_json,
                        feature_type
                    FROM ml_features_ts
                    WHERE symbol = $1 
                    AND calculation_timestamp > NOW() - INTERVAL '6 months'
                    ORDER BY calculation_timestamp DESC
                ),
                price_data AS (
                    -- Mock Price Data - in Realität aus Stock Price Service
                    SELECT 
                        date_trunc('day', calculation_timestamp) as date,
                        150.0 + (RANDOM() - 0.5) * 10 as price
                    FROM feature_data
                    GROUP BY date_trunc('day', calculation_timestamp)
                ),
                combined_features AS (
                    SELECT 
                        DATE(f.calculation_timestamp) as feature_date,
                        jsonb_agg(f.features_json) as all_features,
                        array_agg(f.feature_type) as feature_types
                    FROM feature_data f
                    GROUP BY DATE(f.calculation_timestamp)
                )
                SELECT 
                    cf.feature_date,
                    cf.all_features,
                    p1.price as current_price,
                    p2.price as future_price
                FROM combined_features cf
                JOIN price_data p1 ON p1.date = cf.feature_date
                JOIN price_data p2 ON p2.date = cf.feature_date + INTERVAL '7 days'
                WHERE cf.feature_date <= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY cf.feature_date DESC
                LIMIT 200
                """
                
                rows = await conn.fetch(query, symbol)
                
                if not rows:
                    return None
                
                # Konvertiere zu DataFrame
                data = []
                for row in rows:
                    feature_dict = {}
                    
                    # Kombiniere alle Features
                    for feature_json in row['all_features']:
                        if isinstance(feature_json, str):
                            features = json.loads(feature_json)
                        else:
                            features = feature_json
                        feature_dict.update(features)
                    
                    # Füge Price-Features hinzu
                    feature_dict['current_price'] = float(row['current_price'])
                    feature_dict['target_price'] = float(row['future_price'])
                    feature_dict['price_change_pct'] = (feature_dict['target_price'] - feature_dict['current_price']) / feature_dict['current_price']
                    
                    data.append(feature_dict)
                
                if not data:
                    return None
                
                df = pd.DataFrame(data)
                return df
                
        except Exception as e:
            self.logger.error(f"Failed to prepare training data: {str(e)}")
            return None
    
    async def _prepare_features_and_targets(self, df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], Optional[pd.Series]]:
        """
        Bereitet Features und Targets für Training vor
        """
        try:
            # Definiere Feature-Gruppen
            sentiment_features = [col for col in df.columns if 'sentiment' in col.lower()]
            technical_features = [col for col in df.columns if any(ind in col for ind in ['sma', 'ema', 'rsi', 'macd', 'bb_', 'volume'])]
            price_features = ['current_price']
            
            # Kombiniere alle Features
            feature_columns = sentiment_features + technical_features + price_features
            feature_columns = [col for col in feature_columns if col in df.columns and col != 'target_price']
            
            if not feature_columns:
                self.logger.error("No valid feature columns found")
                return None, None
            
            # Bereinige Daten
            df_clean = df[feature_columns + ['price_change_pct']].dropna()
            
            if len(df_clean) < 10:
                self.logger.error("Insufficient clean data after preprocessing")
                return None, None
            
            X = df_clean[feature_columns]
            y = df_clean['price_change_pct']  # Vorhersage der prozentualen Preisänderung
            
            self.feature_columns = feature_columns
            
            return X, y
            
        except Exception as e:
            self.logger.error(f"Failed to prepare features and targets: {str(e)}")
            return None, None
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """
        Extrahiert Feature-Importance aus XGBoost-Modell
        """
        if self.model is None or self.feature_columns is None:
            return {}
        
        try:
            importance_scores = self.model.feature_importances_
            importance_dict = {}
            
            for feature, importance in zip(self.feature_columns, importance_scores):
                importance_dict[feature] = float(importance)
            
            # Sortiere nach Wichtigkeit
            sorted_importance = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
            
            return sorted_importance
            
        except Exception as e:
            self.logger.error(f"Failed to get feature importance: {str(e)}")
            return {}
    
    async def _save_model(self, symbol: str, metrics: Dict[str, float]) -> Path:
        """
        Speichert XGBoost-Modell auf Disk
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        model_dir = self.model_storage_path / f"{symbol}_sentiment_xgb_7d_{timestamp}"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Speichere XGBoost Modell
        self.model.save_model(str(model_dir / "model.xgb"))
        
        # Speichere Scaler und Metadaten
        with open(model_dir / "scaler.pkl", 'wb') as f:
            pickle.dump({
                'scaler': self.scaler,
                'feature_columns': self.feature_columns
            }, f)
        
        # Speichere Metadaten
        metadata = {
            "symbol": symbol,
            "model_type": "sentiment_xgboost",
            "horizon_days": self.prediction_horizon,
            "created_at": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "feature_count": len(self.feature_columns) if self.feature_columns else 0
        }
        
        with open(model_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.logger.info(f"XGBoost model saved to {model_dir}")
        return model_dir
    
    async def _register_model(self, symbol: str, metrics: Dict[str, float], model_path: Path):
        """
        Registriert Modell in der ML-Datenbank
        """
        try:
            import uuid
            
            async with self.database_pool.acquire() as conn:
                # Deaktiviere alte Sentiment-Modelle
                await conn.execute("""
                    UPDATE ml_model_metadata 
                    SET status = 'deprecated' 
                    WHERE model_type = 'sentiment' AND horizon_days = $1
                """, self.prediction_horizon)
                
                # Registriere neues Modell
                model_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO ml_model_metadata 
                    (model_id, model_type, model_version, horizon_days, status, 
                     file_path, scaler_path, performance_metrics, training_config)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, 
                model_id, 'sentiment', '1.0.0', self.prediction_horizon, 'active',
                str(model_path / "model.xgb"), str(model_path / "scaler.pkl"),
                json.dumps(metrics), json.dumps({'symbol': symbol, 'feature_count': len(self.feature_columns)}))
                
                self.logger.info(f"Sentiment XGBoost model registered with ID: {model_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to register model: {str(e)}")
    
    async def predict(self, symbol: str, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Generiert Sentiment-basierte Prognose
        """
        try:
            if not XGBOOST_AVAILABLE:
                return {"error": "XGBoost dependencies not available"}
            
            # Lade Modell falls nicht geladen
            if self.model is None:
                model_info = await self._load_latest_model(symbol)
                if not model_info:
                    return {"error": f"No trained sentiment model found for {symbol}"}
            
            # Bereite Features vor
            feature_vector = []
            for col in self.feature_columns:
                if col in features:
                    feature_vector.append(features[col])
                else:
                    feature_vector.append(0.0)  # Default für fehlende Features
            
            # Skaliere Features
            feature_vector_scaled = self.scaler.transform([feature_vector])
            
            # Vorhersage
            price_change_pred = self.model.predict(feature_vector_scaled)[0]
            
            # Konvertiere zu absolutem Preis
            current_price = features.get('current_price', 150.0)  # Fallback
            predicted_price = current_price * (1 + price_change_pred)
            
            # Berechne Confidence basierend auf Feature-Qualität
            confidence_score = self._calculate_confidence(features)
            
            return {
                "symbol": symbol,
                "model_type": "sentiment_xgboost",
                "horizon_days": self.prediction_horizon,
                "predicted_price": round(float(predicted_price), 2),
                "predicted_change_pct": round(float(price_change_pred * 100), 2),
                "confidence_score": confidence_score,
                "prediction_timestamp": datetime.utcnow().isoformat(),
                "model_version": "1.0.0"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate sentiment prediction for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    async def _load_latest_model(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Lädt das neueste aktive Sentiment-Modell
        """
        try:
            async with self.database_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT file_path, scaler_path, performance_metrics, model_version
                    FROM ml_model_metadata
                    WHERE model_type = 'sentiment' 
                    AND horizon_days = $1 AND status = 'active'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, self.prediction_horizon)
                
                if not row:
                    return None
                
                model_path = Path(row['file_path'])
                scaler_path = Path(row['scaler_path'])
                
                if not model_path.exists() or not scaler_path.exists():
                    self.logger.error(f"Model files not found: {model_path}, {scaler_path}")
                    return None
                
                # Lade XGBoost Modell
                self.model = xgb.XGBRegressor()
                self.model.load_model(str(model_path))
                
                # Lade Scaler
                with open(scaler_path, 'rb') as f:
                    scaler_data = pickle.load(f)
                    self.scaler = scaler_data['scaler']
                    self.feature_columns = scaler_data['feature_columns']
                
                metrics = json.loads(row['performance_metrics'])
                return {
                    'model_path': str(model_path),
                    'version': row['model_version'],
                    **metrics
                }
                
        except Exception as e:
            self.logger.error(f"Failed to load sentiment model: {str(e)}")
            return None
    
    def _calculate_confidence(self, features: Dict[str, float]) -> float:
        """
        Berechnet Confidence Score basierend auf Feature-Qualität
        """
        # Basis-Confidence für Sentiment-Modell
        base_confidence = 0.75
        
        # Adjustierungen basierend auf Sentiment-Features
        if 'news_volume' in features:
            volume_factor = min(features['news_volume'] / 5.0, 1.0)  # Mehr News = höhere Confidence
            base_confidence += volume_factor * 0.1
        
        if 'sentiment_volatility' in features:
            volatility_penalty = min(features['sentiment_volatility'] * 0.2, 0.15)
            base_confidence -= volatility_penalty
        
        if 'source_diversity' in features:
            diversity_bonus = features['source_diversity'] * 0.05
            base_confidence += diversity_bonus
        
        return min(max(base_confidence, 0.3), 0.95)

# Export für einfache Imports
__all__ = ['SentimentXGBoostModel']