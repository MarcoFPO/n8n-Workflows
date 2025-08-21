#!/usr/bin/env python3
"""
Technical Feature Engine v1.0.0
Technische Indikator-Berechnung für ML-Pipeline

Integration: Event-Driven Feature Engineering
Autor: Claude Code
Datum: 17. August 2025
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import uuid

import numpy as np
import pandas as pd
import talib
from dataclasses import dataclass

# Import shared modules
from shared.database import DatabaseConnection
from shared.event_bus import EventBusConnection
from config.ml_service_config import ML_SERVICE_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class FeatureQualityMetrics:
    """Datenqualitäts-Metriken für Features"""
    total_features: int
    valid_features: int
    missing_ratio: float
    outlier_count: int
    quality_score: float


class TechnicalFeatureEngine:
    """
    Technical Feature Engine für ML-Pipeline
    Berechnet technische Indikatoren für Prognose-Modelle
    """
    
    def __init__(self, database: DatabaseConnection, event_bus: EventBusConnection):
        self.database = database
        self.event_bus = event_bus
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Feature-Konfiguration aus Config laden
        self.feature_config = ML_SERVICE_CONFIG['features']['technical_indicators']
        self.quality_thresholds = ML_SERVICE_CONFIG['features']['quality_thresholds']
        
        # Feature-Cache
        self.feature_cache = {}
        self.cache_ttl_hours = ML_SERVICE_CONFIG['caching']['feature_cache_ttl_hours']
        
        # Performance-Tracking
        self.calculation_times = []
        self.is_initialized = False
    
    async def initialize(self):
        """Initialisiert Feature Engine"""
        try:
            self.logger.info("Initializing Technical Feature Engine...")
            
            # Datenbank-Schema prüfen
            await self._verify_database_schema()
            
            # Cache initialisieren
            await self._initialize_feature_cache()
            
            self.is_initialized = True
            self.logger.info("Technical Feature Engine initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Technical Feature Engine: {str(e)}")
            raise
    
    async def calculate_features_for_symbol(self, symbol: str, trigger_event: Dict[str, Any]) -> str:
        """
        Berechnet technische Features für ein Symbol
        Publiziert ml.features.calculated Event
        """
        start_time = time.time()
        correlation_id = trigger_event.get('correlation_id', str(uuid.uuid4()))
        
        try:
            self.logger.info(f"Calculating technical features for {symbol}")
            
            # Marktdaten laden
            market_data = await self._load_market_data(symbol)
            
            if market_data.empty:
                self.logger.warning(f"No market data available for {symbol}")
                return None
            
            # Features berechnen
            features = await self._calculate_all_features(market_data)
            
            # Qualitätsprüfung
            quality_metrics = self._assess_feature_quality(features)
            
            if quality_metrics.quality_score < self.quality_thresholds['min_quality_score']:
                self.logger.warning(f"Low feature quality for {symbol}: {quality_metrics.quality_score}")
            
            # Features in Datenbank speichern
            feature_id = await self._store_features(symbol, features, quality_metrics)
            
            # Event publizieren
            await self._publish_features_calculated_event(
                symbol, features, quality_metrics, correlation_id, 
                trigger_event.get('event_id')
            )
            
            # Performance-Tracking
            calculation_duration = (time.time() - start_time) * 1000
            self.calculation_times.append(calculation_duration)
            
            self.logger.info(f"Features calculated for {symbol} in {calculation_duration:.1f}ms")
            return feature_id
            
        except Exception as e:
            self.logger.error(f"Failed to calculate features for {symbol}: {str(e)}")
            raise
    
    async def _load_market_data(self, symbol: str, lookback_days: int = 200) -> pd.DataFrame:
        """Lädt Marktdaten für Feature-Berechnung"""
        query = """
            SELECT 
                date,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                adjusted_close
            FROM market_data_daily 
            WHERE symbol = %s 
            AND date >= %s 
            ORDER BY date ASC
        """
        
        start_date = datetime.now() - timedelta(days=lookback_days)
        
        result = await self.database.fetch_all(query, [symbol, start_date])
        
        if not result:
            return pd.DataFrame()
        
        df = pd.DataFrame(result)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        return df
    
    async def _calculate_all_features(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Berechnet alle technischen Indikatoren"""
        features = {}
        
        # Basis-Preis-Daten
        close = data['close_price'].values
        high = data['high_price'].values
        low = data['low_price'].values
        volume = data['volume'].values
        
        # Momentum-Indikatoren
        features.update(await self._calculate_momentum_features(close, high, low))
        
        # Trend-Indikatoren
        features.update(await self._calculate_trend_features(close))
        
        # Volatilitäts-Indikatoren
        features.update(await self._calculate_volatility_features(close, high, low))
        
        # Volumen-Indikatoren
        features.update(await self._calculate_volume_features(close, volume))
        
        # Price-Action-Features
        features.update(await self._calculate_price_action_features(data))
        
        # Aktuelle Werte (letzter verfügbarer Tag)
        current_features = {k: v[-1] if isinstance(v, np.ndarray) and len(v) > 0 else v 
                          for k, v in features.items() if not pd.isna(v[-1] if isinstance(v, np.ndarray) and len(v) > 0 else v)}
        
        return current_features
    
    async def _calculate_momentum_features(self, close: np.ndarray, high: np.ndarray, low: np.ndarray) -> Dict[str, float]:
        """Berechnet Momentum-Indikatoren"""
        features = {}
        
        try:
            # RSI (Relative Strength Index)
            rsi_14 = talib.RSI(close, timeperiod=14)
            features['RSI_14'] = rsi_14
            
            # MACD (Moving Average Convergence Divergence)
            macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
            features['MACD_12_26_9'] = macd
            features['MACD_SIGNAL_9'] = macd_signal
            features['MACD_HISTOGRAM'] = macd_hist
            
            # Stochastic Oscillator
            stoch_k, stoch_d = talib.STOCH(high, low, close, fastk_period=14, slowk_period=3, slowd_period=3)
            features['STOCH_14_3'] = stoch_k
            features['STOCH_D_3'] = stoch_d
            
            # Williams %R
            willr = talib.WILLR(high, low, close, timeperiod=14)
            features['WILLIAMS_R_14'] = willr
            
            # Rate of Change
            roc = talib.ROC(close, timeperiod=10)
            features['ROC_10'] = roc
            
        except Exception as e:
            self.logger.error(f"Error calculating momentum features: {str(e)}")
        
        return features
    
    async def _calculate_trend_features(self, close: np.ndarray) -> Dict[str, float]:
        """Berechnet Trend-Indikatoren"""
        features = {}
        
        try:
            # Simple Moving Averages
            features['SMA_20'] = talib.SMA(close, timeperiod=20)
            features['SMA_50'] = talib.SMA(close, timeperiod=50)
            features['SMA_200'] = talib.SMA(close, timeperiod=200)
            
            # Exponential Moving Averages
            features['EMA_20'] = talib.EMA(close, timeperiod=20)
            features['EMA_50'] = talib.EMA(close, timeperiod=50)
            features['EMA_200'] = talib.EMA(close, timeperiod=200)
            
            # Relative Position zu Moving Averages
            if len(close) > 0:
                current_price = close[-1]
                features['PRICE_ABOVE_SMA_20'] = 1.0 if current_price > features['SMA_20'][-1] else 0.0
                features['PRICE_ABOVE_SMA_50'] = 1.0 if current_price > features['SMA_50'][-1] else 0.0
                features['PRICE_ABOVE_EMA_20'] = 1.0 if current_price > features['EMA_20'][-1] else 0.0
            
            # ADX (Average Directional Index) - Trend-Stärke
            adx = talib.ADX(close, close, close, timeperiod=14)  # Benötigt high, low, close
            features['ADX_14'] = adx
            
        except Exception as e:
            self.logger.error(f"Error calculating trend features: {str(e)}")
        
        return features
    
    async def _calculate_volatility_features(self, close: np.ndarray, high: np.ndarray, low: np.ndarray) -> Dict[str, float]:
        """Berechnet Volatilitäts-Indikatoren"""
        features = {}
        
        try:
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
            features['BB_UPPER_20'] = bb_upper
            features['BB_MIDDLE_20'] = bb_middle
            features['BB_LOWER_20'] = bb_lower
            
            # Bollinger Band Width
            bb_width = (bb_upper - bb_lower) / bb_middle
            features['BB_WIDTH_20'] = bb_width
            
            # Bollinger Band Position
            bb_position = (close - bb_lower) / (bb_upper - bb_lower)
            features['BB_POSITION_20'] = bb_position
            
            # Average True Range
            atr = talib.ATR(high, low, close, timeperiod=14)
            features['ATR_14'] = atr
            
            # Relative ATR (normalisiert auf Preis)
            if len(close) > 0 and len(atr) > 0:
                relative_atr = atr / close * 100
                features['RELATIVE_ATR_14'] = relative_atr
            
            # Standard Deviation
            std_dev = talib.STDDEV(close, timeperiod=20)
            features['STDDEV_20'] = std_dev
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility features: {str(e)}")
        
        return features
    
    async def _calculate_volume_features(self, close: np.ndarray, volume: np.ndarray) -> Dict[str, float]:
        """Berechnet Volumen-Indikatoren"""
        features = {}
        
        try:
            # Volume Moving Average
            volume_sma_20 = talib.SMA(volume, timeperiod=20)
            features['VOLUME_SMA_20'] = volume_sma_20
            
            # Volume Ratio (aktuelles Volumen vs. Durchschnitt)
            if len(volume) > 0 and len(volume_sma_20) > 0:
                volume_ratio = volume / volume_sma_20
                features['VOLUME_RATIO'] = volume_ratio
            
            # On Balance Volume
            obv = talib.OBV(close, volume)
            features['OBV'] = obv
            
            # Volume Rate of Change
            volume_roc = talib.ROC(volume, timeperiod=10)
            features['VOLUME_ROC_10'] = volume_roc
            
            # Money Flow Index
            # Benötigt high, low, close, volume
            # mfi = talib.MFI(high, low, close, volume, timeperiod=14)
            # features['MFI_14'] = mfi
            
        except Exception as e:
            self.logger.error(f"Error calculating volume features: {str(e)}")
        
        return features
    
    async def _calculate_price_action_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Berechnet Price-Action Features"""
        features = {}
        
        try:
            # Daily Returns
            returns = data['close_price'].pct_change()
            features['DAILY_RETURN'] = returns.iloc[-1] if len(returns) > 0 else 0.0
            
            # Return Volatility
            return_std = returns.rolling(window=20).std()
            features['RETURN_VOLATILITY_20'] = return_std.iloc[-1] if len(return_std) > 0 else 0.0
            
            # Weekly Return (5 Tage)
            if len(returns) >= 5:
                weekly_return = returns.iloc[-5:].sum()
                features['WEEKLY_RETURN'] = weekly_return
            
            # High-Low Ratio
            hl_ratio = (data['high_price'] - data['low_price']) / data['close_price']
            features['HIGH_LOW_RATIO'] = hl_ratio.iloc[-1] if len(hl_ratio) > 0 else 0.0
            
            # Price Gap (Open vs Previous Close)
            price_gap = (data['open_price'] - data['close_price'].shift(1)) / data['close_price'].shift(1)
            features['PRICE_GAP'] = price_gap.iloc[-1] if len(price_gap) > 0 else 0.0
            
            # Intraday Range
            intraday_range = (data['high_price'] - data['low_price']) / data['open_price']
            features['INTRADAY_RANGE'] = intraday_range.iloc[-1] if len(intraday_range) > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating price action features: {str(e)}")
        
        return features
    
    def _assess_feature_quality(self, features: Dict[str, Any]) -> FeatureQualityMetrics:
        """Bewertet Qualität der berechneten Features"""
        total_features = len(features)
        valid_features = 0
        outlier_count = 0
        
        for key, value in features.items():
            if pd.notna(value) and np.isfinite(value):
                valid_features += 1
                
                # Outlier-Detection (einfache Z-Score-Methode)
                if abs(value) > self.quality_thresholds['outlier_detection_threshold']:
                    outlier_count += 1
        
        missing_ratio = (total_features - valid_features) / total_features if total_features > 0 else 1.0
        quality_score = valid_features / total_features if total_features > 0 else 0.0
        
        # Quality-Score reduzieren bei zu vielen Outliern
        if outlier_count > total_features * 0.1:  # Mehr als 10% Outlier
            quality_score *= 0.8
        
        return FeatureQualityMetrics(
            total_features=total_features,
            valid_features=valid_features,
            missing_ratio=missing_ratio,
            outlier_count=outlier_count,
            quality_score=quality_score
        )
    
    async def _store_features(self, symbol: str, features: Dict[str, Any], 
                            quality_metrics: FeatureQualityMetrics) -> str:
        """Speichert Features in Datenbank"""
        feature_id = str(uuid.uuid4())
        
        query = """
            INSERT INTO ml_features (
                feature_id, symbol, feature_type, calculation_timestamp,
                features_json, feature_count, quality_score, 
                missing_values_ratio, outlier_count
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        await self.database.execute(query, [
            feature_id,
            symbol,
            'technical',
            datetime.utcnow(),
            features,
            quality_metrics.total_features,
            quality_metrics.quality_score,
            quality_metrics.missing_ratio,
            quality_metrics.outlier_count
        ])
        
        return feature_id
    
    async def _publish_features_calculated_event(self, symbol: str, features: Dict[str, Any],
                                               quality_metrics: FeatureQualityMetrics,
                                               correlation_id: str, trigger_event_id: str):
        """Publiziert ml.features.calculated Event"""
        
        # Features in Event-Schema-Format konvertieren
        event_features = {
            'technical': self._format_features_for_event(features)
        }
        
        payload = {
            'symbol': symbol,
            'feature_type': 'technical',
            'calculation_timestamp': datetime.utcnow().isoformat(),
            'features': event_features,
            'feature_count': quality_metrics.total_features,
            'data_quality_score': quality_metrics.quality_score,
            'calculation_duration_ms': int(self.calculation_times[-1] if self.calculation_times else 0)
        }
        
        await self.event_bus.publish_ml_event(
            'ml.features.calculated',
            payload,
            correlation_id=correlation_id
        )
    
    def _format_features_for_event(self, features: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Formatiert Features für Event-Schema"""
        formatted = {
            'momentum': {},
            'trend': {},
            'volatility': {},
            'volume': {},
            'price_action': {}
        }
        
        # Feature-Mapping basierend auf Konfiguration
        feature_mapping = {
            'momentum': ['RSI_14', 'MACD_12_26_9', 'STOCH_14_3', 'WILLIAMS_R_14', 'ROC_10'],
            'trend': ['SMA_20', 'SMA_50', 'SMA_200', 'EMA_20', 'EMA_50', 'PRICE_ABOVE_SMA_20'],
            'volatility': ['BB_UPPER_20', 'BB_LOWER_20', 'ATR_14', 'BB_WIDTH_20', 'RELATIVE_ATR_14'],
            'volume': ['VOLUME_SMA_20', 'VOLUME_RATIO', 'OBV', 'VOLUME_ROC_10'],
            'price_action': ['DAILY_RETURN', 'WEEKLY_RETURN', 'HIGH_LOW_RATIO', 'PRICE_GAP']
        }
        
        for category, feature_names in feature_mapping.items():
            for feature_name in feature_names:
                if feature_name in features:
                    formatted[category][feature_name.lower()] = float(features[feature_name])
        
        return formatted
    
    async def _verify_database_schema(self):
        """Prüft ob ML-Schema existiert"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'ml_features'
            )
        """
        
        result = await self.database.fetch_one(query)
        if not result[0]:
            raise RuntimeError("ML database schema not found. Please deploy ml-schema-extension.sql first.")
    
    async def _initialize_feature_cache(self):
        """Initialisiert Feature-Cache"""
        self.feature_cache = {}
        self.logger.info("Feature cache initialized")
    
    async def health_check(self) -> Dict[str, Any]:
        """Health Check für Feature Engine"""
        try:
            # Performance-Statistiken
            avg_calculation_time = np.mean(self.calculation_times[-100:]) if self.calculation_times else 0
            
            # Cache-Statistiken
            cache_size = len(self.feature_cache)
            
            return {
                'status': 'healthy' if self.is_initialized else 'warning',
                'initialized': self.is_initialized,
                'avg_calculation_time_ms': round(avg_calculation_time, 2),
                'recent_calculations': len(self.calculation_times),
                'cache_size': cache_size,
                'supported_features': len(self.feature_config['momentum']) + 
                                   len(self.feature_config['trend']) + 
                                   len(self.feature_config['volatility'])
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'error': str(e)
            }
    
    async def shutdown(self):
        """Graceful Shutdown"""
        try:
            self.logger.info("Shutting down Technical Feature Engine...")
            
            # Cache leeren
            self.feature_cache.clear()
            
            # Performance-Statistiken ausgeben
            if self.calculation_times:
                avg_time = np.mean(self.calculation_times)
                self.logger.info(f"Average feature calculation time: {avg_time:.1f}ms")
            
            self.is_initialized = False
            self.logger.info("Technical Feature Engine shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during Feature Engine shutdown: {str(e)}")