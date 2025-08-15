"""
Analysis Orchestrator V2 - Koordiniert Single Function Analysis Module
Ersetzt das monolithische AnalysisModule durch modulare Architektur
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

try:
    from shared.common_imports import datetime, Dict, Any, structlog
    from shared.single_function_module_base import SingleFunctionModuleBase
    from security import StockAnalysisRequest, InputValidator, SecurityConfig
except ImportError:
    # Mock imports for development
    from datetime import datetime
    from typing import Dict, Any
    
    class MockLogger:
        def info(self, msg, **kwargs): print(f"ℹ️ {msg} {kwargs}")
        def debug(self, msg, **kwargs): print(f"🐛 {msg} {kwargs}")
        def error(self, msg, **kwargs): print(f"❌ {msg} {kwargs}")
        def warning(self, msg, **kwargs): print(f"⚠️ {msg} {kwargs}")
    
    class SingleFunctionModuleBase:
        def __init__(self, name, event_bus):
            self.module_name = name
            self.event_bus = event_bus
            self.logger = MockLogger()
        
        async def _setup_event_subscriptions(self): pass
    
    class StockAnalysisRequest:
        def __init__(self, symbol, period='1mo'):
            self.symbol = symbol
            self.period = period
    
    class InputValidator:
        def __init__(self, config): pass
        def validate_stock_symbol(self, symbol): return symbol.upper()
    
    class SecurityConfig: pass

# Import aller Single Function Analysis Module
from modules.analysis_modules.market_data_fetcher_module import MarketDataFetcherModule
from modules.analysis_modules.rsi_calculator_module import RSICalculatorModule  
from modules.analysis_modules.macd_calculator_module import MACDCalculatorModule
from modules.analysis_modules.moving_averages_module import MovingAveragesModule
from modules.analysis_modules.bollinger_bands_module import BollingerBandsModule
from modules.analysis_modules.volume_analysis_module import VolumeAnalysisModule
from modules.analysis_modules.support_resistance_module import SupportResistanceModule
from modules.analysis_modules.atr_calculator_module import ATRCalculatorModule
from modules.analysis_modules.trend_strength_module import TrendStrengthModule


class AnalysisOrchestratorV2(SingleFunctionModuleBase):
    """Orchestriert alle Analysis Single Function Module für komplette Aktienanalyse"""
    
    def __init__(self, event_bus):
        super().__init__("analysis_orchestrator_v2", event_bus)
        self.input_validator = InputValidator(SecurityConfig())
        self.analysis_cache = {}
        self.cache_ttl = 300  # 5 Minuten
        
        # Initialize all Single Function Analysis Modules
        self.market_data_fetcher = MarketDataFetcherModule(event_bus)
        self.rsi_calculator = RSICalculatorModule(event_bus)
        self.macd_calculator = MACDCalculatorModule(event_bus)
        self.moving_averages = MovingAveragesModule(event_bus)
        self.bollinger_bands = BollingerBandsModule(event_bus)
        self.volume_analysis = VolumeAnalysisModule(event_bus)
        self.support_resistance = SupportResistanceModule(event_bus)
        self.atr_calculator = ATRCalculatorModule(event_bus)
        self.trend_strength = TrendStrengthModule(event_bus)
        
        # List of all modules for management
        self.analysis_modules = [
            self.market_data_fetcher,
            self.rsi_calculator,
            self.macd_calculator,
            self.moving_averages,
            self.bollinger_bands,
            self.volume_analysis,
            self.support_resistance,
            self.atr_calculator,
            self.trend_strength
        ]
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('analysis.comprehensive.request', self.process_event)
            
            # Initialize all sub-modules
            for module in self.analysis_modules:
                await module._setup_event_subscriptions()
            
        except Exception as e:
            self.logger.error("Failed to setup event subscriptions", error=str(e))
    
    async def process_event(self, event):
        """Process incoming events"""
        event_type = event.get('event_type', '')
        
        if event_type == 'system.health.request':
            health_response = {
                'event_type': 'system.health.response',
                'module': self.module_name,
                'status': 'healthy',
                'sub_modules_count': len(self.analysis_modules),
                'cache_entries': len(self.analysis_cache),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'analysis.comprehensive.request':
            request_data = event.get('request_data')
            
            if isinstance(request_data, dict) and 'symbol' in request_data:
                # Convert dict to StockAnalysisRequest-like object
                class RequestObj:
                    def __init__(self, data):
                        self.symbol = data['symbol']
                        self.period = data.get('period', '1mo')
                
                analysis_request = RequestObj(request_data)
            else:
                analysis_request = request_data
            
            analysis_result = await self.orchestrate_comprehensive_analysis(analysis_request)
            
            response_event = {
                'event_type': 'analysis.comprehensive.response',
                'symbol': analysis_request.symbol if hasattr(analysis_request, 'symbol') else 'unknown',
                'success': analysis_result.get('success', False),
                'data': analysis_result.get('data', {}),
                'error': analysis_result.get('error'),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def orchestrate_comprehensive_analysis(self, request: StockAnalysisRequest) -> Dict[str, Any]:
        """Koordiniert die gesamte Aktienanalyse über alle Single Function Module"""
        try:
            # Validate stock symbol
            validated_symbol = self.input_validator.validate_stock_symbol(request.symbol)
            
            # Check cache first
            cache_key = f"{validated_symbol}_{request.period}"
            if cache_key in self.analysis_cache:
                cache_entry = self.analysis_cache[cache_key]
                cache_age = (datetime.now() - cache_entry['timestamp']).total_seconds()
                if cache_age < self.cache_ttl:
                    self.logger.debug("Returning cached comprehensive analysis", 
                                    symbol=validated_symbol, 
                                    cache_age=cache_age)
                    return {
                        'success': True,
                        'data': cache_entry['data'],
                        'source': 'cache'
                    }
            
            self.logger.info("Starting comprehensive analysis orchestration", symbol=validated_symbol)
            
            # Step 1: Fetch Market Data
            market_data = await self.market_data_fetcher.fetch_market_data(validated_symbol, request.period)
            
            if market_data is None:
                return {
                    'success': False,
                    'error': 'Market data unavailable',
                    'symbol': validated_symbol
                }
            
            # Extract price data for calculations
            close_prices = market_data['Close'].tolist()
            high_prices = market_data['High'].tolist()
            low_prices = market_data['Low'].tolist()
            volume_data = market_data['Volume'].tolist()
            
            self.logger.debug("Market data extracted", 
                            data_points=len(close_prices),
                            symbol=validated_symbol)
            
            # Step 2: Calculate all technical indicators in parallel
            analysis_tasks = await self._calculate_all_indicators(
                close_prices, high_prices, low_prices, volume_data
            )
            
            # Step 3: Compile comprehensive results
            comprehensive_indicators = await self._compile_comprehensive_results(
                analysis_tasks, validated_symbol, request.period, len(market_data)
            )
            
            # Step 4: Cache results
            analysis_result = {
                'symbol': validated_symbol,
                'period': request.period,
                'indicators': comprehensive_indicators,
                'timestamp': datetime.now().isoformat(),
                'data_points': len(market_data),
                'modules_used': len(self.analysis_modules)
            }
            
            self.analysis_cache[cache_key] = {
                'data': analysis_result,
                'timestamp': datetime.now()
            }
            
            # Step 5: Cleanup old cache entries
            await self._cleanup_old_cache_entries()
            
            self.logger.info("Comprehensive analysis orchestration completed", 
                           symbol=validated_symbol,
                           indicators_count=len(comprehensive_indicators),
                           modules_used=len(self.analysis_modules))
            
            return {
                'success': True,
                'data': analysis_result,
                'source': 'live'
            }
            
        except Exception as e:
            self.logger.error("Error in comprehensive analysis orchestration", 
                            symbol=request.symbol if hasattr(request, 'symbol') else 'unknown',
                            error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _calculate_all_indicators(self, close_prices: list, high_prices: list, low_prices: list, volume_data: list) -> Dict[str, Any]:
        """Calculate all technical indicators using Single Function Modules"""
        try:
            indicators = {}
            
            # RSI Calculation
            rsi_value = await self.rsi_calculator.calculate_rsi(close_prices)
            indicators['rsi'] = rsi_value
            
            # MACD Calculation  
            macd_result = await self.macd_calculator.calculate_macd(close_prices)
            indicators['macd'] = macd_result.get('macd', 0.0)
            indicators['macd_signal'] = macd_result.get('signal', 0.0)
            indicators['macd_histogram'] = macd_result.get('histogram', 0.0)
            
            # Moving Averages
            ma_result = await self.moving_averages.calculate_moving_averages(close_prices)
            if ma_result.get('success'):
                indicators.update(ma_result.get('sma', {}))
                indicators.update(ma_result.get('ema', {}))
            
            # Bollinger Bands
            bb_result = await self.bollinger_bands.calculate_bollinger_bands(close_prices)
            if bb_result.get('success'):
                indicators['bb_upper'] = bb_result.get('upper_band', 0.0)
                indicators['bb_lower'] = bb_result.get('lower_band', 0.0)
                indicators['bb_width'] = bb_result.get('band_width', 0.0)
                indicators['bb_percent_b'] = bb_result.get('percent_b', 0.5)
            
            # Volume Analysis
            volume_result = await self.volume_analysis.analyze_volume(volume_data, close_prices)
            if volume_result.get('success'):
                indicators['avg_volume'] = volume_result.get('avg_volume', 0.0)
                indicators['current_volume'] = volume_result.get('current_volume', 0.0)
                indicators['volume_ratio'] = volume_result.get('volume_ratio', 1.0)
                indicators['volume_trend'] = volume_result.get('volume_trend', 'neutral')
                indicators['price_volume_correlation'] = volume_result.get('price_volume_correlation', 0.0)
            
            # Support/Resistance
            sr_result = await self.support_resistance.calculate_support_resistance(
                high_prices, low_prices, close_prices
            )
            if sr_result.get('success'):
                indicators['resistance_level'] = sr_result.get('resistance_level', 0.0)
                indicators['support_level'] = sr_result.get('support_level', 0.0)
                indicators['price_position'] = sr_result.get('price_position', 0.5)
                
            # ATR (Average True Range)
            atr_result = await self.atr_calculator.calculate_atr(high_prices, low_prices, close_prices)
            if atr_result.get('success'):
                indicators['avg_true_range'] = atr_result.get('atr', 0.0)
                indicators['atr_percentage'] = atr_result.get('atr_percentage', 0.0)
                indicators['volatility_level'] = atr_result.get('volatility_level', 'normal')
            
            # Trend Strength
            trend_result = await self.trend_strength.calculate_trend_strength(close_prices, volume_data)
            if trend_result.get('success'):
                indicators['trend_strength'] = trend_result.get('trend_strength', 0.0)
                indicators['trend_direction'] = trend_result.get('trend_direction', 'neutral')
                indicators['trend_momentum'] = trend_result.get('trend_momentum', 0.0)
                indicators['trend_consistency'] = trend_result.get('trend_consistency', 0.0)
            
            # Current price information
            indicators['current_price'] = close_prices[-1] if close_prices else 100.0
            indicators['price_change'] = close_prices[-1] - close_prices[-2] if len(close_prices) > 1 else 0.0
            indicators['price_change_percent'] = (indicators['price_change'] / close_prices[-2] * 100) if len(close_prices) > 1 and close_prices[-2] != 0 else 0.0
            
            return indicators
            
        except Exception as e:
            self.logger.error("Error calculating all indicators", error=str(e))
            # Return safe defaults
            return {
                'rsi': 50.0,
                'macd': 0.0,
                'macd_signal': 0.0,
                'macd_histogram': 0.0,
                'current_price': 100.0,
                'price_change': 0.0,
                'price_change_percent': 0.0,
                'trend_strength': 0.0,
                'trend_direction': 'neutral'
            }
    
    async def _compile_comprehensive_results(self, indicators: Dict[str, Any], symbol: str, period: str, data_points: int) -> Dict[str, Any]:
        """Compile and enhance results with additional analysis"""
        try:
            # Add metadata
            indicators['analysis_metadata'] = {
                'symbol': symbol,
                'period': period,
                'data_points': data_points,
                'analysis_timestamp': datetime.now().isoformat(),
                'modules_used': [module.module_name for module in self.analysis_modules],
                'cache_ttl_seconds': self.cache_ttl
            }
            
            # Add signal interpretations
            indicators['signal_summary'] = await self._generate_signal_summary(indicators)
            
            return indicators
            
        except Exception as e:
            self.logger.error("Error compiling comprehensive results", error=str(e))
            return indicators
    
    async def _generate_signal_summary(self, indicators: Dict[str, Any]) -> Dict[str, str]:
        """Generate overall signal summary from all indicators"""
        try:
            signals = {}
            
            # RSI Signal
            rsi = indicators.get('rsi', 50)
            if rsi >= 70:
                signals['rsi_signal'] = 'overbought'
            elif rsi <= 30:
                signals['rsi_signal'] = 'oversold'
            else:
                signals['rsi_signal'] = 'neutral'
            
            # MACD Signal
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            if macd > macd_signal:
                signals['macd_signal'] = 'bullish'
            elif macd < macd_signal:
                signals['macd_signal'] = 'bearish'
            else:
                signals['macd_signal'] = 'neutral'
            
            # Trend Signal
            trend_strength = indicators.get('trend_strength', 0)
            trend_direction = indicators.get('trend_direction', 'neutral')
            if trend_strength > 0.6:
                signals['trend_signal'] = f'strong_{trend_direction}'
            elif trend_strength > 0.3:
                signals['trend_signal'] = f'weak_{trend_direction}'
            else:
                signals['trend_signal'] = 'sideways'
            
            # Volume Signal
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:
                signals['volume_signal'] = 'high_volume'
            elif volume_ratio < 0.8:
                signals['volume_signal'] = 'low_volume'
            else:
                signals['volume_signal'] = 'normal_volume'
                
            # Volatility Signal
            volatility_level = indicators.get('volatility_level', 'normal')
            signals['volatility_signal'] = volatility_level
            
            return signals
            
        except Exception as e:
            self.logger.error("Error generating signal summary", error=str(e))
            return {'overall_signal': 'neutral'}
    
    async def _cleanup_old_cache_entries(self):
        """Remove old cache entries to prevent memory buildup"""
        try:
            current_time = datetime.now()
            keys_to_remove = []
            
            for key, entry in self.analysis_cache.items():
                cache_age = (current_time - entry['timestamp']).total_seconds()
                if cache_age > self.cache_ttl * 10:  # Remove after 10x TTL
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.analysis_cache[key]
            
            if keys_to_remove:
                self.logger.debug("Cache cleanup completed", 
                                entries_removed=len(keys_to_remove))
                
        except Exception as e:
            self.logger.error("Error during cache cleanup", error=str(e))
    
    def get_analysis_module_status(self) -> Dict[str, Any]:
        """Get status of all analysis modules"""
        try:
            return {
                'orchestrator': self.module_name,
                'total_modules': len(self.analysis_modules),
                'modules': {
                    module.module_name: {
                        'type': getattr(module, 'module_type', 'analysis'),
                        'info': module.get_module_info() if hasattr(module, 'get_module_info') else {}
                    }
                    for module in self.analysis_modules
                },
                'cache_entries': len(self.analysis_cache),
                'cache_ttl_seconds': self.cache_ttl
            }
        except Exception as e:
            self.logger.error("Error getting module status", error=str(e))
            return {'error': str(e)}
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get orchestrator module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'analysis_orchestrator',
            'description': 'Orchestrates comprehensive stock analysis using 9 Single Function Modules',
            'sub_modules_count': len(self.analysis_modules),
            'sub_modules': [module.module_name for module in self.analysis_modules],
            'cache_ttl_seconds': self.cache_ttl,
            'features': [
                'market_data_fetching',
                'technical_indicators',
                'volume_analysis', 
                'trend_analysis',
                'volatility_analysis',
                'support_resistance',
                'signal_generation',
                'comprehensive_caching'
            ]
        }