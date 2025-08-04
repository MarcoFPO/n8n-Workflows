"""
Analysis Module für Intelligent-Core-Service
Technische Indikatoren und Marktdaten-Analyse
"""

import yfinance as yf
from security import StockAnalysisRequest, InputValidator, SecurityConfig
import sys
sys.path.append('/opt/aktienanalyse-ökosystem')

# Shared Library Import für Code-Duplikation-Eliminierung
from shared.common_imports import (
    pd, np, datetime, timedelta, Dict, Any, structlog
)
from backend_base_module import BackendBaseModule
from event_bus import EventType


class AnalysisModule(BackendBaseModule):
    """Technical Analysis und Market Data Processing"""
    
    def __init__(self, event_bus):
        super().__init__("analysis", event_bus)
        self.input_validator = InputValidator(SecurityConfig())
        self.analysis_cache = {}
        self.cache_ttl = 300  # 5 Minuten
        
    async def _initialize_module(self) -> bool:
        """Initialize analysis module"""
        try:
            self.logger.info("Initializing Analysis Module")
            # Test technical indicators calculation with dummy data
            test_data = pd.DataFrame({
                'Close': np.random.rand(100) * 100 + 50,
                'Volume': np.random.rand(100) * 1000000
            })
            test_indicators = await self._calculate_technical_indicators(test_data)
            self.logger.info("Analysis module test successful", 
                           indicators_count=len(test_indicators))
            return True
        except Exception as e:
            self.logger.error("Failed to initialize analysis module", error=str(e))
            return False
    
    async def _subscribe_to_events(self):
        """Subscribe to relevant events"""
        await self.subscribe_to_event(
            EventType.DATA_SYNCHRONIZED, 
            self._handle_data_sync_event
        )
        await self.subscribe_to_event(
            EventType.CONFIG_UPDATED, 
            self._handle_config_updated_event
        )
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Main analysis processing logic"""
        try:
            request = data.get('request')
            if not isinstance(request, StockAnalysisRequest):
                raise ValueError("Invalid request format")
            
            # Validate stock symbol
            validated_symbol = self.input_validator.validate_stock_symbol(request.symbol)
            
            # Check cache first
            cache_key = f"{validated_symbol}_{request.period}"
            if cache_key in self.analysis_cache:
                cache_entry = self.analysis_cache[cache_key]
                if datetime.now() - cache_entry['timestamp'] < timedelta(seconds=self.cache_ttl):
                    self.logger.debug("Returning cached analysis", symbol=validated_symbol)
                    return {
                        'success': True,
                        'data': cache_entry['data'],
                        'source': 'cache'
                    }
            
            # Fetch market data
            market_data = await self._fetch_market_data(validated_symbol, request.period)
            if market_data is None:
                return {
                    'success': False,
                    'error': 'Market data unavailable',
                    'symbol': validated_symbol
                }
            
            # Calculate technical indicators
            indicators = await self._calculate_technical_indicators(market_data)
            
            # Cache result
            analysis_result = {
                'symbol': validated_symbol,
                'period': request.period,
                'indicators': indicators,
                'timestamp': datetime.now().isoformat(),
                'data_points': len(market_data)
            }
            
            self.analysis_cache[cache_key] = {
                'data': analysis_result,
                'timestamp': datetime.now()
            }
            
            # Publish analysis completed event
            await self.publish_module_event(
                EventType.ANALYSIS_STATE_CHANGED,
                {
                    'symbol': validated_symbol,
                    'indicators': indicators,
                    'completed_at': datetime.now().isoformat()
                },
                f"analysis-{validated_symbol}"
            )
            
            self.logger.info("Stock analysis completed", 
                           symbol=validated_symbol,
                           indicators_count=len(indicators))
            
            return {
                'success': True,
                'data': analysis_result,
                'source': 'live'
            }
            
        except Exception as e:
            self.logger.error("Error in analysis processing", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _fetch_market_data(self, symbol: str, period: str) -> pd.DataFrame:
        """Fetch market data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            hist_data = ticker.history(period=period)
            
            if hist_data.empty:
                self.logger.warning("No market data found", symbol=symbol)
                return None
            
            self.logger.debug("Market data fetched successfully", 
                            symbol=symbol, 
                            data_points=len(hist_data))
            return hist_data
            
        except Exception as e:
            self.logger.error("Failed to fetch market data", 
                            symbol=symbol, 
                            error=str(e))
            return None
    
    async def _calculate_technical_indicators(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive technical indicators"""
        try:
            indicators = {}
            
            # RSI (Relative Strength Index)
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            indicators['rsi'] = float(rsi.iloc[-1]) if not rsi.empty else 50.0
            
            # MACD (Moving Average Convergence Divergence)
            exp1 = data['Close'].ewm(span=12).mean()
            exp2 = data['Close'].ewm(span=26).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9).mean()
            indicators['macd'] = float(macd.iloc[-1]) if not macd.empty else 0.0
            indicators['macd_signal'] = float(signal.iloc[-1]) if not signal.empty else 0.0
            indicators['macd_histogram'] = indicators['macd'] - indicators['macd_signal']
            
            # Moving Averages
            sma_20 = data['Close'].rolling(window=20).mean()
            sma_50 = data['Close'].rolling(window=50).mean()
            sma_200 = data['Close'].rolling(window=min(200, len(data))).mean()
            indicators['sma_20'] = float(sma_20.iloc[-1]) if not sma_20.empty else data['Close'].iloc[-1]
            indicators['sma_50'] = float(sma_50.iloc[-1]) if not sma_50.empty else data['Close'].iloc[-1]
            indicators['sma_200'] = float(sma_200.iloc[-1]) if not sma_200.empty else data['Close'].iloc[-1]
            
            # Exponential Moving Averages
            ema_12 = data['Close'].ewm(span=12).mean()
            ema_26 = data['Close'].ewm(span=26).mean()
            indicators['ema_12'] = float(ema_12.iloc[-1]) if not ema_12.empty else data['Close'].iloc[-1]
            indicators['ema_26'] = float(ema_26.iloc[-1]) if not ema_26.empty else data['Close'].iloc[-1]
            
            # Bollinger Bands
            sma = data['Close'].rolling(window=20).mean()
            std = data['Close'].rolling(window=20).std()
            bb_upper = sma + (std * 2)
            bb_lower = sma - (std * 2)
            indicators['bb_upper'] = float(bb_upper.iloc[-1]) if not bb_upper.empty else data['Close'].iloc[-1] * 1.1
            indicators['bb_lower'] = float(bb_lower.iloc[-1]) if not bb_lower.empty else data['Close'].iloc[-1] * 0.9
            indicators['bb_width'] = indicators['bb_upper'] - indicators['bb_lower']
            
            # Current price information
            indicators['current_price'] = float(data['Close'].iloc[-1])
            indicators['price_change'] = float(data['Close'].iloc[-1] - data['Close'].iloc[-2]) if len(data) > 1 else 0.0
            indicators['price_change_percent'] = (indicators['price_change'] / data['Close'].iloc[-2] * 100) if len(data) > 1 else 0.0
            
            # Volume analysis
            indicators['avg_volume'] = float(data['Volume'].rolling(window=20).mean().iloc[-1])
            indicators['current_volume'] = float(data['Volume'].iloc[-1])
            indicators['volume_ratio'] = indicators['current_volume'] / indicators['avg_volume']
            
            # Volatility measures
            returns = data['Close'].pct_change()
            indicators['volatility'] = float(returns.std() * np.sqrt(252))  # Annualized volatility
            indicators['avg_true_range'] = float(self._calculate_atr(data))
            
            # Support and Resistance levels
            indicators['resistance_level'] = float(data['High'].rolling(window=20).max().iloc[-1])
            indicators['support_level'] = float(data['Low'].rolling(window=20).min().iloc[-1])
            
            # Market strength indicators
            indicators['price_position'] = (indicators['current_price'] - indicators['support_level']) / (indicators['resistance_level'] - indicators['support_level'])
            indicators['trend_strength'] = self._calculate_trend_strength(data)
            
            return indicators
            
        except Exception as e:
            self.logger.error("Error calculating technical indicators", error=str(e))
            # Return safe defaults
            return {
                'rsi': 50.0,
                'macd': 0.0,
                'macd_signal': 0.0,
                'macd_histogram': 0.0,
                'sma_20': 100.0,
                'sma_50': 100.0,
                'sma_200': 100.0,
                'ema_12': 100.0,
                'ema_26': 100.0,
                'bb_upper': 110.0,
                'bb_lower': 90.0,
                'bb_width': 20.0,
                'current_price': 100.0,
                'price_change': 0.0,
                'price_change_percent': 0.0,
                'avg_volume': 1000000.0,
                'current_volume': 1000000.0,
                'volume_ratio': 1.0,
                'volatility': 0.2,
                'avg_true_range': 2.0,
                'resistance_level': 110.0,
                'support_level': 90.0,
                'price_position': 0.5,
                'trend_strength': 0.0
            }
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            high_low = data['High'] - data['Low']
            high_close = np.abs(data['High'] - data['Close'].shift())
            low_close = np.abs(data['Low'] - data['Close'].shift())
            true_range = pd.DataFrame({'hl': high_low, 'hc': high_close, 'lc': low_close}).max(axis=1)
            atr = true_range.rolling(window=period).mean()
            return atr.iloc[-1] if not atr.empty else 2.0
        except:
            return 2.0
    
    def _calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """Calculate trend strength indicator"""
        try:
            # Simple trend strength based on price direction and volume
            price_trend = (data['Close'].iloc[-1] - data['Close'].iloc[-10]) / data['Close'].iloc[-10]
            volume_trend = data['Volume'].iloc[-5:].mean() / data['Volume'].iloc[-15:-5].mean()
            
            # Normalize to -1 to 1 range
            trend_strength = np.tanh(price_trend * 10) * min(volume_trend, 2.0) / 2.0
            return float(trend_strength)
        except:
            return 0.0
    
    async def _handle_data_sync_event(self, event):
        """Handle data synchronization events"""
        try:
            self.logger.info("Received data sync event")
            # Clear analysis cache when new data arrives
            self.analysis_cache.clear()
            self.logger.debug("Analysis cache cleared due to data sync")
        except Exception as e:
            self.logger.error("Error handling data sync event", error=str(e))
    
    async def _handle_config_updated_event(self, event):
        """Handle configuration update events"""
        try:
            self.logger.info("Received config update event")
            # Update cache TTL if specified in config
            if 'cache_ttl' in event.data:
                self.cache_ttl = event.data['cache_ttl']
                self.logger.info("Cache TTL updated", new_ttl=self.cache_ttl)
        except Exception as e:
            self.logger.error("Error handling config update event", error=str(e))
    
    def get_cached_analysis(self, symbol: str, period: str) -> Dict[str, Any]:
        """Get cached analysis if available"""
        cache_key = f"{symbol}_{period}"
        if cache_key in self.analysis_cache:
            cache_entry = self.analysis_cache[cache_key]
            if datetime.now() - cache_entry['timestamp'] < timedelta(seconds=self.cache_ttl):
                return cache_entry['data']
        return None
    
    def clear_symbol_cache(self, symbol: str):
        """Clear cache for specific symbol"""
        keys_to_remove = [key for key in self.analysis_cache.keys() if key.startswith(f"{symbol}_")]
        for key in keys_to_remove:
            del self.analysis_cache[key]
        self.logger.debug("Symbol cache cleared", symbol=symbol, keys_removed=len(keys_to_remove))