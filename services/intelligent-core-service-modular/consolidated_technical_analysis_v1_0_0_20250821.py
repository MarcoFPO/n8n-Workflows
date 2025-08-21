#!/usr/bin/env python3
"""
Consolidated Technical Analysis Manager v1.0.0
Clean Architecture - Konsolidiert 9 Over-Engineering Module in eine saubere Klasse

Konsolidierte Module:
- atr_calculator_module_v1_0_0_20250803.py
- bollinger_bands_module_v1_1_0_20250807.py  
- macd_calculator_module_v1_3_0_20250809.py
- market_data_fetcher_module_v1_5_0_20250814.py
- moving_averages_module_v1_2_0_20250808.py
- rsi_calculator_module_v1_2_1_20250810.py
- support_resistance_module_v1_0_2_20250806.py
- trend_strength_module_v1_1_1_20250805.py
- volume_analysis_module_v1_0_1_20250804.py

Code-Qualität: HÖCHSTE PRIORITÄT
- SOLID Principles: Single Class für alle Technical Analysis
- Clean Code Architecture: Klare Methoden-Trennung
- DRY Principle: Eliminiert Code-Duplikation zwischen Modulen
"""

import numpy as np
import pandas as pd
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

# Import Manager für Clean Architecture
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from config.central_config_v1_0_0_20250821 import config
except ImportError:
    # Fallback für Testing ohne zentrale Konfiguration
    config = None

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    """Trend Direction Enumeration"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"
    UNKNOWN = "unknown"


@dataclass
class TechnicalIndicators:
    """Comprehensive Technical Analysis Result"""
    symbol: str
    timestamp: str
    
    # Moving Averages
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    
    # Oscillators
    rsi: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    
    # Bollinger Bands
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_width: Optional[float] = None
    
    # Volatility
    atr: Optional[float] = None
    
    # Support/Resistance
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    
    # Trend Analysis
    trend_direction: TrendDirection = TrendDirection.UNKNOWN
    trend_strength: Optional[float] = None
    
    # Volume Analysis
    volume_ma: Optional[float] = None
    volume_ratio: Optional[float] = None
    
    # Current Price
    current_price: Optional[float] = None


class ConsolidatedTechnicalAnalysis:
    """
    Konsolidierter Technical Analysis Manager
    Clean Architecture: ALLE Technical Analysis Funktionen in einer Klasse
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.market_data_cache = {}
        self.cache_expiry = timedelta(minutes=5)
        
    async def get_market_data(self, symbol: str, timeframe: str = "1d", limit: int = 200) -> Optional[pd.DataFrame]:
        """
        Market Data Fetching (konsolidiert market_data_fetcher_module)
        """
        try:
            cache_key = f"{symbol}_{timeframe}_{limit}"
            
            # Check cache
            if cache_key in self.market_data_cache:
                cached_data, cached_time = self.market_data_cache[cache_key]
                if datetime.now() - cached_time < self.cache_expiry:
                    return cached_data
            
            # Simulate market data fetching (in real implementation, use actual API)
            # For demonstration, generate sample data
            dates = pd.date_range(start=datetime.now() - timedelta(days=limit), 
                                 end=datetime.now(), freq='D')
            
            # Generate realistic price data
            base_price = 100.0
            prices = []
            volume = []
            
            for i in range(len(dates)):
                # Simulate price movement
                change = np.random.normal(0, 0.02)  # 2% daily volatility
                if i == 0:
                    price = base_price
                else:
                    price = prices[-1] * (1 + change)
                    
                prices.append(price)
                volume.append(np.random.randint(100000, 1000000))
            
            df = pd.DataFrame({
                'date': dates,
                'open': [p * np.random.uniform(0.995, 1.005) for p in prices],
                'high': [p * np.random.uniform(1.000, 1.015) for p in prices],
                'low': [p * np.random.uniform(0.985, 1.000) for p in prices],
                'close': prices,
                'volume': volume
            })
            
            # Cache the data
            self.market_data_cache[cache_key] = (df, datetime.now())
            
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to fetch market data for {symbol}: {e}")
            return None
    
    def calculate_moving_averages(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Moving Averages Calculation (konsolidiert moving_averages_module)
        """
        try:
            close_prices = df['close']
            
            return {
                'sma_20': close_prices.rolling(window=20).mean().iloc[-1],
                'sma_50': close_prices.rolling(window=50).mean().iloc[-1],
                'ema_12': close_prices.ewm(span=12).mean().iloc[-1],
                'ema_26': close_prices.ewm(span=26).mean().iloc[-1]
            }
        except Exception as e:
            self.logger.error(f"Failed to calculate moving averages: {e}")
            return {}
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """
        RSI Calculation (konsolidiert rsi_calculator_module)
        """
        try:
            close_prices = df['close']
            delta = close_prices.diff()
            
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1]
            
        except Exception as e:
            self.logger.error(f"Failed to calculate RSI: {e}")
            return None
    
    def calculate_macd(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        MACD Calculation (konsolidiert macd_calculator_module)
        """
        try:
            close_prices = df['close']
            
            ema_12 = close_prices.ewm(span=12).mean()
            ema_26 = close_prices.ewm(span=26).mean()
            
            macd_line = ema_12 - ema_26
            signal_line = macd_line.ewm(span=9).mean()
            histogram = macd_line - signal_line
            
            return {
                'macd_line': macd_line.iloc[-1],
                'macd_signal': signal_line.iloc[-1],
                'macd_histogram': histogram.iloc[-1]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate MACD: {e}")
            return {}
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Dict[str, float]:
        """
        Bollinger Bands Calculation (konsolidiert bollinger_bands_module)
        """
        try:
            close_prices = df['close']
            
            middle_band = close_prices.rolling(window=period).mean()
            std = close_prices.rolling(window=period).std()
            
            upper_band = middle_band + (std * std_dev)
            lower_band = middle_band - (std * std_dev)
            
            bb_width = ((upper_band - lower_band) / middle_band) * 100
            
            return {
                'bb_upper': upper_band.iloc[-1],
                'bb_middle': middle_band.iloc[-1],
                'bb_lower': lower_band.iloc[-1],
                'bb_width': bb_width.iloc[-1]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate Bollinger Bands: {e}")
            return {}
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """
        ATR Calculation (konsolidiert atr_calculator_module)
        """
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean()
            
            return atr.iloc[-1]
            
        except Exception as e:
            self.logger.error(f"Failed to calculate ATR: {e}")
            return None
    
    def calculate_support_resistance(self, df: pd.DataFrame, lookback: int = 50) -> Dict[str, float]:
        """
        Support/Resistance Calculation (konsolidiert support_resistance_module)
        """
        try:
            recent_data = df.tail(lookback)
            
            # Simple support/resistance calculation
            support_level = recent_data['low'].min()
            resistance_level = recent_data['high'].max()
            
            return {
                'support_level': support_level,
                'resistance_level': resistance_level
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate support/resistance: {e}")
            return {}
    
    def analyze_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Trend Analysis (konsolidiert trend_strength_module)
        """
        try:
            close_prices = df['close']
            
            # Calculate trend direction
            sma_20 = close_prices.rolling(window=20).mean()
            sma_50 = close_prices.rolling(window=50).mean()
            
            current_price = close_prices.iloc[-1]
            sma_20_current = sma_20.iloc[-1]
            sma_50_current = sma_50.iloc[-1]
            
            if current_price > sma_20_current > sma_50_current:
                trend_direction = TrendDirection.BULLISH
                trend_strength = min(abs((current_price - sma_50_current) / sma_50_current) * 100, 100)
            elif current_price < sma_20_current < sma_50_current:
                trend_direction = TrendDirection.BEARISH
                trend_strength = min(abs((current_price - sma_50_current) / sma_50_current) * 100, 100)
            else:
                trend_direction = TrendDirection.SIDEWAYS
                trend_strength = 0
            
            return {
                'trend_direction': trend_direction,
                'trend_strength': trend_strength
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze trend: {e}")
            return {
                'trend_direction': TrendDirection.UNKNOWN,
                'trend_strength': 0
            }
    
    def analyze_volume(self, df: pd.DataFrame, period: int = 20) -> Dict[str, float]:
        """
        Volume Analysis (konsolidiert volume_analysis_module)
        """
        try:
            volume = df['volume']
            
            volume_ma = volume.rolling(window=period).mean()
            current_volume = volume.iloc[-1]
            volume_ma_current = volume_ma.iloc[-1]
            
            volume_ratio = current_volume / volume_ma_current if volume_ma_current > 0 else 1.0
            
            return {
                'volume_ma': volume_ma_current,
                'volume_ratio': volume_ratio
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze volume: {e}")
            return {}
    
    async def analyze_symbol(self, symbol: str) -> Optional[TechnicalIndicators]:
        """
        Comprehensive Technical Analysis für ein Symbol
        Clean Architecture: Single Method für alle Indikatoren
        """
        try:
            self.logger.info(f"Starting comprehensive technical analysis for {symbol}")
            
            # Fetch market data
            df = await self.get_market_data(symbol)
            if df is None or len(df) < 50:
                self.logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # Calculate all indicators
            ma_data = self.calculate_moving_averages(df)
            rsi = self.calculate_rsi(df)
            macd_data = self.calculate_macd(df)
            bb_data = self.calculate_bollinger_bands(df)
            atr = self.calculate_atr(df)
            sr_data = self.calculate_support_resistance(df)
            trend_data = self.analyze_trend(df)
            volume_data = self.analyze_volume(df)
            
            # Build comprehensive result
            indicators = TechnicalIndicators(
                symbol=symbol,
                timestamp=datetime.now().isoformat(),
                current_price=df['close'].iloc[-1],
                
                # Moving Averages
                sma_20=ma_data.get('sma_20'),
                sma_50=ma_data.get('sma_50'),
                ema_12=ma_data.get('ema_12'),
                ema_26=ma_data.get('ema_26'),
                
                # Oscillators
                rsi=rsi,
                macd_line=macd_data.get('macd_line'),
                macd_signal=macd_data.get('macd_signal'),
                macd_histogram=macd_data.get('macd_histogram'),
                
                # Bollinger Bands
                bb_upper=bb_data.get('bb_upper'),
                bb_middle=bb_data.get('bb_middle'),
                bb_lower=bb_data.get('bb_lower'),
                bb_width=bb_data.get('bb_width'),
                
                # Volatility
                atr=atr,
                
                # Support/Resistance
                support_level=sr_data.get('support_level'),
                resistance_level=sr_data.get('resistance_level'),
                
                # Trend Analysis
                trend_direction=trend_data.get('trend_direction', TrendDirection.UNKNOWN),
                trend_strength=trend_data.get('trend_strength'),
                
                # Volume Analysis
                volume_ma=volume_data.get('volume_ma'),
                volume_ratio=volume_data.get('volume_ratio')
            )
            
            self.logger.info(f"Technical analysis completed for {symbol}")
            return indicators
            
        except Exception as e:
            self.logger.error(f"Technical analysis failed for {symbol}: {e}")
            return None
    
    async def analyze_multiple_symbols(self, symbols: List[str]) -> Dict[str, Optional[TechnicalIndicators]]:
        """
        Parallel Technical Analysis für mehrere Symbole
        Performance-Optimierung: Concurrent Processing
        """
        try:
            tasks = [self.analyze_symbol(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            analysis_results = {}
            for symbol, result in zip(symbols, results):
                if isinstance(result, Exception):
                    self.logger.error(f"Analysis failed for {symbol}: {result}")
                    analysis_results[symbol] = None
                else:
                    analysis_results[symbol] = result
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Multiple symbol analysis failed: {e}")
            return {}


# Globale Instanz für einfache Verwendung
technical_analyzer = ConsolidatedTechnicalAnalysis()


# Convenience Functions
async def analyze_symbol(symbol: str) -> Optional[TechnicalIndicators]:
    """Convenience-Funktion für einzelne Symbol-Analyse"""
    return await technical_analyzer.analyze_symbol(symbol)

async def analyze_symbols(symbols: List[str]) -> Dict[str, Optional[TechnicalIndicators]]:
    """Convenience-Funktion für Multiple-Symbol-Analyse"""
    return await technical_analyzer.analyze_multiple_symbols(symbols)


if __name__ == "__main__":
    # Debug/Test-Modus
    async def test_analysis():
        print("=== Consolidated Technical Analysis Test ===")
        
        symbols = ["AAPL", "MSFT", "TSLA"]
        results = await analyze_symbols(symbols)
        
        for symbol, indicators in results.items():
            if indicators:
                print(f"\n{symbol} Analysis:")
                print(f"  Current Price: {indicators.current_price:.2f}")
                print(f"  RSI: {indicators.rsi:.2f}")
                print(f"  Trend: {indicators.trend_direction.value}")
                print(f"  Trend Strength: {indicators.trend_strength:.2f}")
            else:
                print(f"\n{symbol}: Analysis failed")
    
    asyncio.run(test_analysis())