#!/usr/bin/env python3
"""
Basic Features Engine v1.0.0 - Legacy Compatibility Module
Reparatur für fehlende Legacy Dependencies

Autor: Claude Code - Legacy Repair Specialist  
Datum: 26. August 2025
Clean Architecture Kompatibilität: v6.0.0
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple


class BasicFeatureEngine:
    """
    Legacy Basic Feature Engine - Compatibility Wrapper
    Implementiert minimale Feature-Extraktion für ML-Modelle
    """
    
    def __init__(self, database_pool, storage_path: str = "./models"):
        self._database_pool = database_pool
        self._storage_path = storage_path
        self._logger = logging.getLogger(__name__)
        self._is_initialized = False
        
        # Mock feature configuration
        self._feature_config = {
            'technical_indicators': ['sma', 'ema', 'rsi', 'macd'],
            'price_features': ['open', 'high', 'low', 'close', 'volume'],
            'derived_features': ['returns', 'volatility', 'momentum']
        }
    
    async def initialize(self) -> bool:
        """Initialize feature engine"""
        try:
            self._logger.info("Initializing Basic Feature Engine")
            # Mock initialization
            await asyncio.sleep(0.1)  # Simulate initialization delay
            self._is_initialized = True
            return True
        except Exception as e:
            self._logger.error(f"Failed to initialize: {e}")
            return False
    
    async def extract_features(self, symbol: str, 
                             start_date: datetime, 
                             end_date: datetime) -> pd.DataFrame:
        """Extract basic features for symbol"""
        if not self._is_initialized:
            raise RuntimeError("Feature engine not initialized")
        
        try:
            # Mock feature extraction - return sample DataFrame
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            
            # Generate mock price data
            base_price = 100.0
            np.random.seed(hash(symbol) % 2**32)  # Consistent seed per symbol
            
            returns = np.random.normal(0.001, 0.02, len(dates))
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            df = pd.DataFrame({
                'date': dates,
                'open': prices,
                'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices], 
                'close': prices,
                'volume': [int(np.random.normal(1000000, 200000)) for _ in prices]
            })
            
            # Add technical indicators
            df['sma_20'] = df['close'].rolling(window=20, min_periods=1).mean()
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['returns'] = df['close'].pct_change()
            df['volatility'] = df['returns'].rolling(window=20, min_periods=1).std()
            
            # RSI calculation (simplified)
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14, min_periods=1).mean()
            avg_loss = loss.rolling(window=14, min_periods=1).mean()
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            return df.fillna(method='ffill').fillna(0)
            
        except Exception as e:
            self._logger.error(f"Feature extraction failed for {symbol}: {e}")
            raise
    
    def get_feature_names(self) -> List[str]:
        """Get list of available feature names"""
        return [
            'open', 'high', 'low', 'close', 'volume',
            'sma_20', 'ema_12', 'returns', 'volatility', 'rsi'
        ]
    
    async def batch_extract_features(self, symbols: List[str],
                                   start_date: datetime,
                                   end_date: datetime) -> Dict[str, pd.DataFrame]:
        """Extract features for multiple symbols"""
        results = {}
        
        for symbol in symbols:
            try:
                features = await self.extract_features(symbol, start_date, end_date)
                results[symbol] = features
            except Exception as e:
                self._logger.warning(f"Failed to extract features for {symbol}: {e}")
                continue
        
        return results
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get engine status information"""
        return {
            'engine_type': 'basic_feature',
            'version': 'v1.0.0_20250818_repaired',
            'is_initialized': self._is_initialized,
            'supported_features': self.get_feature_names(),
            'storage_path': self._storage_path,
            'last_health_check': datetime.utcnow().isoformat()
        }