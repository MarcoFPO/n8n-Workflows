"""
Moving Averages Module - Single Function Module
Calculates Simple and Exponential Moving Averages
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import pd, np, datetime, Dict, Any, structlog
from shared.single_function_module_base import SingleFunctionModuleBase


class MovingAveragesModule(SingleFunctionModuleBase):
    """Calculate Simple Moving Averages (SMA) and Exponential Moving Averages (EMA)"""
    
    def __init__(self, event_bus):
        super().__init__("moving_averages", event_bus)
        self.default_periods = [20, 50, 200]  # Common periods
        self.ema_periods = [12, 26]  # Common EMA periods
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('moving_averages.calculation.request', self.process_event)
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
                'default_sma_periods': self.default_periods,
                'default_ema_periods': self.ema_periods,
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'moving_averages.calculation.request':
            data = event.get('price_data', [])
            sma_periods = event.get('sma_periods', self.default_periods)
            ema_periods = event.get('ema_periods', self.ema_periods)
            
            ma_result = await self.calculate_moving_averages(data, sma_periods, ema_periods)
            
            response_event = {
                'event_type': 'moving_averages.calculation.response',
                'sma_values': ma_result.get('sma', {}),
                'ema_values': ma_result.get('ema', {}),
                'data_points': len(data),
                'success': ma_result.get('success', False),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def calculate_moving_averages(self, price_data: list, sma_periods: list = None, ema_periods: list = None) -> Dict[str, Any]:
        """Calculate both SMA and EMA for given periods"""
        try:
            if sma_periods is None:
                sma_periods = self.default_periods
            if ema_periods is None:
                ema_periods = self.ema_periods
            
            # Convert to pandas Series
            if isinstance(price_data, list):
                prices = pd.Series(price_data)
            elif isinstance(price_data, pd.DataFrame):
                prices = price_data['Close'] if 'Close' in price_data.columns else price_data.iloc[:, 0]
            else:
                prices = pd.Series(price_data)
            
            if len(prices) < min(max(sma_periods, default=[1]), max(ema_periods, default=[1])):
                self.logger.warning("Insufficient data for moving averages", 
                                  data_points=len(prices))
                return {
                    'success': False,
                    'error': 'Insufficient data',
                    'sma': {},
                    'ema': {}
                }
            
            # Calculate SMAs
            sma_results = {}
            for period in sma_periods:
                if len(prices) >= period:
                    sma = prices.rolling(window=period, min_periods=period).mean()
                    sma_value = float(sma.iloc[-1]) if not sma.empty and not pd.isna(sma.iloc[-1]) else prices.iloc[-1]
                    sma_results[f'sma_{period}'] = sma_value
                else:
                    # Use available data if not enough for full period
                    sma_results[f'sma_{period}'] = float(prices.mean())
            
            # Calculate EMAs
            ema_results = {}
            for period in ema_periods:
                if len(prices) >= period:
                    ema = prices.ewm(span=period, min_periods=period).mean()
                    ema_value = float(ema.iloc[-1]) if not ema.empty and not pd.isna(ema.iloc[-1]) else prices.iloc[-1]
                    ema_results[f'ema_{period}'] = ema_value
                else:
                    # Use available data if not enough for full period
                    ema_results[f'ema_{period}'] = float(prices.mean())
            
            self.logger.debug("Moving averages calculated successfully", 
                            sma_count=len(sma_results),
                            ema_count=len(ema_results),
                            data_points=len(prices))
            
            return {
                'success': True,
                'sma': sma_results,
                'ema': ema_results,
                'current_price': float(prices.iloc[-1])
            }
            
        except Exception as e:
            self.logger.error("Error calculating moving averages", 
                            sma_periods=sma_periods,
                            ema_periods=ema_periods,
                            data_points=len(price_data) if price_data else 0,
                            error=str(e))
            return {
                'success': False,
                'error': str(e),
                'sma': {},
                'ema': {}
            }
    
    async def calculate_sma(self, price_data: list, period: int) -> float:
        """Calculate single Simple Moving Average"""
        try:
            if isinstance(price_data, list):
                prices = pd.Series(price_data)
            else:
                prices = pd.Series(price_data)
                
            if len(prices) < period:
                return float(prices.mean())
            
            sma = prices.rolling(window=period).mean()
            return float(sma.iloc[-1]) if not sma.empty and not pd.isna(sma.iloc[-1]) else float(prices.iloc[-1])
            
        except Exception as e:
            self.logger.error("Error calculating SMA", period=period, error=str(e))
            return float(price_data[-1]) if price_data else 100.0
    
    async def calculate_ema(self, price_data: list, period: int) -> float:
        """Calculate single Exponential Moving Average"""
        try:
            if isinstance(price_data, list):
                prices = pd.Series(price_data)
            else:
                prices = pd.Series(price_data)
                
            if len(prices) < period:
                return float(prices.mean())
            
            ema = prices.ewm(span=period).mean()
            return float(ema.iloc[-1]) if not ema.empty and not pd.isna(ema.iloc[-1]) else float(prices.iloc[-1])
            
        except Exception as e:
            self.logger.error("Error calculating EMA", period=period, error=str(e))
            return float(price_data[-1]) if price_data else 100.0
    
    def interpret_ma_signals(self, current_price: float, sma_values: Dict[str, float], ema_values: Dict[str, float]) -> Dict[str, str]:
        """Interpret moving average signals"""
        try:
            signals = {}
            
            # Price vs SMA signals
            for key, sma_value in sma_values.items():
                if current_price > sma_value:
                    signals[f'{key}_signal'] = 'bullish'
                elif current_price < sma_value:
                    signals[f'{key}_signal'] = 'bearish'
                else:
                    signals[f'{key}_signal'] = 'neutral'
            
            # Price vs EMA signals
            for key, ema_value in ema_values.items():
                if current_price > ema_value:
                    signals[f'{key}_signal'] = 'bullish'
                elif current_price < ema_value:
                    signals[f'{key}_signal'] = 'bearish'
                else:
                    signals[f'{key}_signal'] = 'neutral'
            
            # Golden Cross / Death Cross detection
            if 'sma_50' in sma_values and 'sma_200' in sma_values:
                if sma_values['sma_50'] > sma_values['sma_200']:
                    signals['golden_death_cross'] = 'golden_cross'
                elif sma_values['sma_50'] < sma_values['sma_200']:
                    signals['golden_death_cross'] = 'death_cross'
                else:
                    signals['golden_death_cross'] = 'neutral'
            
            return signals
            
        except Exception as e:
            self.logger.error("Error interpreting MA signals", error=str(e))
            return {}
    
    def get_trend_strength(self, sma_values: Dict[str, float]) -> str:
        """Determine trend strength based on MA alignment"""
        try:
            # Sort SMAs by period (extract number from key like 'sma_20')
            sorted_mas = []
            for key, value in sma_values.items():
                if key.startswith('sma_'):
                    period = int(key.split('_')[1])
                    sorted_mas.append((period, value))
            
            sorted_mas.sort()  # Sort by period
            
            if len(sorted_mas) < 2:
                return 'insufficient_data'
            
            # Check alignment
            is_bullish_aligned = all(sorted_mas[i][1] <= sorted_mas[i+1][1] for i in range(len(sorted_mas)-1))
            is_bearish_aligned = all(sorted_mas[i][1] >= sorted_mas[i+1][1] for i in range(len(sorted_mas)-1))
            
            if is_bullish_aligned:
                return 'strong_bullish'
            elif is_bearish_aligned:
                return 'strong_bearish'
            else:
                return 'sideways'
                
        except Exception as e:
            self.logger.error("Error determining trend strength", error=str(e))
            return 'neutral'
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'technical_indicator',
            'indicators': ['SMA', 'EMA'],
            'default_sma_periods': self.default_periods,
            'default_ema_periods': self.ema_periods,
            'description': 'Calculates Simple and Exponential Moving Averages'
        }