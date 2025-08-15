"""
ATR Calculator Module - Single Function Module
Calculates Average True Range volatility indicator
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import pd, np, datetime, Dict, Any, structlog
from shared.single_function_module_base import SingleFunctionModuleBase


class ATRCalculatorModule(SingleFunctionModuleBase):
    """Calculate Average True Range (ATR) volatility indicator"""
    
    def __init__(self, event_bus):
        super().__init__("atr_calculator", event_bus)
        self.default_period = 14
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('atr.calculation.request', self.process_event)
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
                'default_period': self.default_period,
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'atr.calculation.request':
            high_data = event.get('high_data', [])
            low_data = event.get('low_data', [])
            close_data = event.get('close_data', [])
            period = event.get('period', self.default_period)
            
            atr_result = await self.calculate_atr(high_data, low_data, close_data, period)
            
            response_event = {
                'event_type': 'atr.calculation.response',
                'atr_value': atr_result.get('atr', 0.0),
                'true_range': atr_result.get('current_true_range', 0.0),
                'atr_percentage': atr_result.get('atr_percentage', 0.0),
                'volatility_level': atr_result.get('volatility_level', 'normal'),
                'period': period,
                'data_points': len(high_data),
                'success': atr_result.get('success', False),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def calculate_atr(self, high_data: list, low_data: list, close_data: list, period: int = None) -> Dict[str, Any]:
        """Calculate Average True Range"""
        try:
            if period is None:
                period = self.default_period
            
            if not high_data or not low_data or not close_data:
                return {
                    'success': False,
                    'error': 'Missing price data (High, Low, Close required)',
                    'atr': 2.0
                }
            
            min_length = min(len(high_data), len(low_data), len(close_data))
            if min_length < period + 1:
                self.logger.warning("Insufficient data for ATR calculation", 
                                  data_points=min_length, 
                                  required=period + 1)
                # Return simple estimate
                if min_length >= 2:
                    simple_range = max(high_data) - min(low_data)
                    return {
                        'success': True,
                        'atr': simple_range,
                        'current_true_range': simple_range,
                        'atr_percentage': (simple_range / close_data[-1]) * 100 if close_data else 2.0,
                        'volatility_level': 'estimated'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Insufficient data',
                        'atr': 2.0
                    }
            
            # Convert to pandas DataFrame
            data = pd.DataFrame({
                'High': high_data[-min_length:],
                'Low': low_data[-min_length:],
                'Close': close_data[-min_length:]
            })
            
            # Calculate True Range components
            # TR = max(High - Low, |High - Close_prev|, |Low - Close_prev|)
            data['Close_prev'] = data['Close'].shift(1)
            
            data['hl'] = data['High'] - data['Low']
            data['hc'] = abs(data['High'] - data['Close_prev'])
            data['lc'] = abs(data['Low'] - data['Close_prev'])
            
            # True Range is the maximum of the three
            data['TrueRange'] = data[['hl', 'hc', 'lc']].max(axis=1)
            
            # Remove NaN values (first row will be NaN due to shift)
            data = data.dropna()
            
            if len(data) < period:
                period = len(data)
            
            # Calculate ATR using Simple Moving Average of True Range
            data['ATR'] = data['TrueRange'].rolling(window=period).mean()
            
            # Get final values
            atr_value = float(data['ATR'].iloc[-1]) if not data['ATR'].empty and not pd.isna(data['ATR'].iloc[-1]) else 2.0
            current_true_range = float(data['TrueRange'].iloc[-1]) if not data['TrueRange'].empty else 2.0
            current_close = float(data['Close'].iloc[-1])
            
            # Calculate ATR as percentage of price
            atr_percentage = (atr_value / current_close) * 100 if current_close > 0 else 2.0
            
            # Determine volatility level
            volatility_level = await self._classify_volatility_level(atr_percentage)
            
            self.logger.debug("ATR calculated successfully", 
                            atr=atr_value,
                            atr_percentage=atr_percentage,
                            volatility=volatility_level,
                            data_points=len(data))
            
            return {
                'success': True,
                'atr': atr_value,
                'current_true_range': current_true_range,
                'atr_percentage': atr_percentage,
                'volatility_level': volatility_level,
                'current_close': current_close,
                'period_used': period
            }
            
        except Exception as e:
            self.logger.error("Error calculating ATR", 
                            period=period,
                            data_points=(len(high_data) if high_data else 0, len(low_data) if low_data else 0, len(close_data) if close_data else 0),
                            error=str(e))
            return {
                'success': False,
                'error': str(e),
                'atr': 2.0,
                'current_true_range': 2.0,
                'atr_percentage': 2.0
            }
    
    async def calculate_atr_from_dataframe(self, data: pd.DataFrame, period: int = None) -> Dict[str, Any]:
        """Calculate ATR from DataFrame with High, Low, Close columns"""
        try:
            required_columns = ['High', 'Low', 'Close']
            if not all(col in data.columns for col in required_columns):
                raise ValueError(f"DataFrame must have columns: {required_columns}")
            
            return await self.calculate_atr(
                data['High'].tolist(),
                data['Low'].tolist(), 
                data['Close'].tolist(),
                period
            )
            
        except Exception as e:
            self.logger.error("Error calculating ATR from DataFrame", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'atr': 2.0
            }
    
    async def _classify_volatility_level(self, atr_percentage: float) -> str:
        """Classify volatility level based on ATR percentage"""
        try:
            if atr_percentage > 5.0:
                return 'very_high'
            elif atr_percentage > 3.0:
                return 'high'
            elif atr_percentage > 2.0:
                return 'normal'
            elif atr_percentage > 1.0:
                return 'low'
            else:
                return 'very_low'
        except:
            return 'normal'
    
    def calculate_atr_stop_loss(self, current_price: float, atr_value: float, multiplier: float = 2.0, direction: str = 'long') -> float:
        """Calculate ATR-based stop loss levels"""
        try:
            if direction.lower() == 'long':
                stop_loss = current_price - (atr_value * multiplier)
            else:  # short
                stop_loss = current_price + (atr_value * multiplier)
            
            return max(stop_loss, 0.0)  # Ensure non-negative
            
        except Exception as e:
            self.logger.error("Error calculating ATR stop loss", error=str(e))
            return current_price * 0.95 if direction.lower() == 'long' else current_price * 1.05
    
    def calculate_position_size(self, account_balance: float, risk_percentage: float, entry_price: float, atr_value: float, atr_multiplier: float = 2.0) -> Dict[str, float]:
        """Calculate position size based on ATR risk management"""
        try:
            # Risk amount
            risk_amount = account_balance * (risk_percentage / 100)
            
            # Stop loss distance
            stop_distance = atr_value * atr_multiplier
            
            # Position size calculation
            if stop_distance > 0:
                position_size = risk_amount / stop_distance
                position_value = position_size * entry_price
                
                return {
                    'position_size': position_size,
                    'position_value': position_value,
                    'risk_amount': risk_amount,
                    'stop_distance': stop_distance,
                    'risk_percentage_actual': (risk_amount / account_balance) * 100
                }
            else:
                return {
                    'position_size': 0.0,
                    'position_value': 0.0,
                    'risk_amount': 0.0,
                    'stop_distance': 0.0,
                    'risk_percentage_actual': 0.0
                }
                
        except Exception as e:
            self.logger.error("Error calculating position size", error=str(e))
            return {
                'position_size': 0.0,
                'position_value': 0.0,
                'risk_amount': 0.0,
                'stop_distance': 0.0,
                'risk_percentage_actual': 0.0
            }
    
    def interpret_atr_signals(self, atr_percentage: float, volatility_level: str) -> Dict[str, str]:
        """Interpret ATR-based signals"""
        try:
            signals = {}
            
            # Volatility interpretation
            signals['volatility_level'] = volatility_level
            
            # Trading implications
            if volatility_level in ['very_high', 'high']:
                signals['trading_advice'] = 'use_wider_stops'
                signals['position_sizing'] = 'reduce_position_size'
                signals['market_condition'] = 'volatile'
            elif volatility_level in ['very_low', 'low']:
                signals['trading_advice'] = 'use_tighter_stops'
                signals['position_sizing'] = 'normal_position_size'
                signals['market_condition'] = 'quiet'
            else:
                signals['trading_advice'] = 'normal_stops'
                signals['position_sizing'] = 'normal_position_size'
                signals['market_condition'] = 'normal'
            
            # Breakout potential
            if volatility_level == 'very_low':
                signals['breakout_potential'] = 'high'  # Low volatility often precedes breakouts
            elif volatility_level == 'very_high':
                signals['breakout_potential'] = 'exhaustion_possible'
            else:
                signals['breakout_potential'] = 'normal'
            
            return signals
            
        except Exception as e:
            self.logger.error("Error interpreting ATR signals", error=str(e))
            return {'volatility_level': 'normal'}
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'technical_indicator',
            'indicator': 'ATR',
            'default_period': self.default_period,
            'features': [
                'atr_calculation',
                'volatility_classification',
                'stop_loss_calculation',
                'position_sizing',
                'risk_management'
            ],
            'description': 'Calculates Average True Range (ATR) for volatility analysis and risk management'
        }