"""
MACD Calculator Module - Single Function Module
Calculates Moving Average Convergence Divergence indicator
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import pd, np, datetime, Dict, Any, structlog
from shared.single_function_module_base import SingleFunctionModuleBase


class MACDCalculatorModule(SingleFunctionModuleBase):
    """Calculate Moving Average Convergence Divergence (MACD) indicator"""
    
    def __init__(self, event_bus):
        super().__init__("macd_calculator", event_bus)
        self.fast_period = 12
        self.slow_period = 26
        self.signal_period = 9
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('macd.calculation.request', self.process_event)
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
                'parameters': {
                    'fast_period': self.fast_period,
                    'slow_period': self.slow_period,
                    'signal_period': self.signal_period
                },
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'macd.calculation.request':
            data = event.get('price_data', [])
            fast_period = event.get('fast_period', self.fast_period)
            slow_period = event.get('slow_period', self.slow_period)
            signal_period = event.get('signal_period', self.signal_period)
            
            macd_result = await self.calculate_macd(data, fast_period, slow_period, signal_period)
            
            response_event = {
                'event_type': 'macd.calculation.response',
                'macd': macd_result.get('macd', 0.0),
                'macd_signal': macd_result.get('signal', 0.0),
                'macd_histogram': macd_result.get('histogram', 0.0),
                'parameters': {
                    'fast_period': fast_period,
                    'slow_period': slow_period,
                    'signal_period': signal_period
                },
                'data_points': len(data),
                'success': macd_result.get('success', False),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def calculate_macd(self, price_data: list, fast_period: int = None, slow_period: int = None, signal_period: int = None) -> Dict[str, Any]:
        """Calculate MACD indicator"""
        try:
            # Use default parameters if not provided
            if fast_period is None:
                fast_period = self.fast_period
            if slow_period is None:
                slow_period = self.slow_period
            if signal_period is None:
                signal_period = self.signal_period
            
            # Validate input
            min_data_points = max(slow_period, fast_period) + signal_period
            if len(price_data) < min_data_points:
                self.logger.warning("Insufficient data for MACD calculation", 
                                  data_points=len(price_data), 
                                  required=min_data_points)
                return {
                    'success': False,
                    'macd': 0.0,
                    'signal': 0.0,
                    'histogram': 0.0,
                    'error': 'Insufficient data'
                }
            
            # Convert to pandas Series
            if isinstance(price_data, list):
                prices = pd.Series(price_data)
            elif isinstance(price_data, pd.DataFrame):
                prices = price_data['Close'] if 'Close' in price_data.columns else price_data.iloc[:, 0]
            else:
                prices = pd.Series(price_data)
            
            # Calculate EMAs
            ema_fast = prices.ewm(span=fast_period, min_periods=fast_period).mean()
            ema_slow = prices.ewm(span=slow_period, min_periods=slow_period).mean()
            
            # Calculate MACD line
            macd_line = ema_fast - ema_slow
            
            # Calculate Signal line (EMA of MACD)
            signal_line = macd_line.ewm(span=signal_period, min_periods=signal_period).mean()
            
            # Calculate Histogram
            histogram = macd_line - signal_line
            
            # Get final values
            macd_value = float(macd_line.iloc[-1]) if not macd_line.empty and not pd.isna(macd_line.iloc[-1]) else 0.0
            signal_value = float(signal_line.iloc[-1]) if not signal_line.empty and not pd.isna(signal_line.iloc[-1]) else 0.0
            histogram_value = float(histogram.iloc[-1]) if not histogram.empty and not pd.isna(histogram.iloc[-1]) else 0.0
            
            self.logger.debug("MACD calculated successfully", 
                            macd=macd_value,
                            signal=signal_value,
                            histogram=histogram_value,
                            data_points=len(price_data))
            
            return {
                'success': True,
                'macd': macd_value,
                'signal': signal_value,
                'histogram': histogram_value,
                'fast_ema': float(ema_fast.iloc[-1]) if not ema_fast.empty else 0.0,
                'slow_ema': float(ema_slow.iloc[-1]) if not ema_slow.empty else 0.0
            }
            
        except Exception as e:
            self.logger.error("Error calculating MACD", 
                            fast_period=fast_period,
                            slow_period=slow_period,
                            signal_period=signal_period,
                            data_points=len(price_data) if price_data else 0,
                            error=str(e))
            return {
                'success': False,
                'macd': 0.0,
                'signal': 0.0,
                'histogram': 0.0,
                'error': str(e)
            }
    
    async def calculate_macd_from_dataframe(self, data: pd.DataFrame, fast_period: int = None, slow_period: int = None, signal_period: int = None) -> Dict[str, Any]:
        """Calculate MACD from DataFrame with Close column"""
        try:
            if 'Close' not in data.columns:
                raise ValueError("DataFrame must have 'Close' column for MACD calculation")
            
            return await self.calculate_macd(data['Close'].tolist(), fast_period, slow_period, signal_period)
            
        except Exception as e:
            self.logger.error("Error calculating MACD from DataFrame", error=str(e))
            return {
                'success': False,
                'macd': 0.0,
                'signal': 0.0,
                'histogram': 0.0,
                'error': str(e)
            }
    
    def interpret_macd_signal(self, macd: float, signal: float, histogram: float) -> str:
        """Interpret MACD values to trading signal"""
        try:
            if macd > signal and histogram > 0:
                return "bullish_momentum" if histogram > abs(macd * 0.1) else "bullish"
            elif macd < signal and histogram < 0:
                return "bearish_momentum" if abs(histogram) > abs(macd * 0.1) else "bearish"
            elif abs(macd - signal) < abs(macd * 0.05):
                return "neutral"
            else:
                return "transitioning"
                
        except Exception as e:
            self.logger.error("Error interpreting MACD signal", error=str(e))
            return "neutral"
    
    def get_macd_crossover_signal(self, current_histogram: float, previous_histogram: float) -> str:
        """Detect MACD crossover signals"""
        try:
            if previous_histogram <= 0 and current_histogram > 0:
                return "bullish_crossover"
            elif previous_histogram >= 0 and current_histogram < 0:
                return "bearish_crossover"
            else:
                return "no_crossover"
                
        except Exception as e:
            self.logger.error("Error detecting MACD crossover", error=str(e))
            return "no_crossover"
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'technical_indicator',
            'indicator': 'MACD',
            'parameters': {
                'fast_period': self.fast_period,
                'slow_period': self.slow_period,
                'signal_period': self.signal_period
            },
            'description': 'Calculates Moving Average Convergence Divergence (MACD) indicator'
        }