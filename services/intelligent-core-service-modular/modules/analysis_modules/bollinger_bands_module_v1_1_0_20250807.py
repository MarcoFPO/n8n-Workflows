"""
Bollinger Bands Module - Single Function Module  
Calculates Bollinger Bands volatility indicator
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import pd, np, datetime, Dict, Any, structlog
from shared.single_function_module_base import SingleFunctionModuleBase


class BollingerBandsModule(SingleFunctionModuleBase):
    """Calculate Bollinger Bands volatility indicator"""
    
    def __init__(self, event_bus):
        super().__init__("bollinger_bands", event_bus)
        self.default_period = 20
        self.default_std_dev = 2
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('bollinger_bands.calculation.request', self.process_event)
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
                    'default_period': self.default_period,
                    'default_std_dev': self.default_std_dev
                },
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'bollinger_bands.calculation.request':
            data = event.get('price_data', [])
            period = event.get('period', self.default_period)
            std_dev = event.get('std_dev', self.default_std_dev)
            
            bb_result = await self.calculate_bollinger_bands(data, period, std_dev)
            
            response_event = {
                'event_type': 'bollinger_bands.calculation.response',
                'upper_band': bb_result.get('upper_band', 0.0),
                'lower_band': bb_result.get('lower_band', 0.0),
                'middle_band': bb_result.get('middle_band', 0.0),
                'band_width': bb_result.get('band_width', 0.0),
                'percent_b': bb_result.get('percent_b', 0.0),
                'parameters': {
                    'period': period,
                    'std_dev': std_dev
                },
                'data_points': len(data),
                'success': bb_result.get('success', False),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def calculate_bollinger_bands(self, price_data: list, period: int = None, std_dev: float = None) -> Dict[str, Any]:
        """Calculate Bollinger Bands"""
        try:
            if period is None:
                period = self.default_period
            if std_dev is None:
                std_dev = self.default_std_dev
            
            if len(price_data) < period:
                self.logger.warning("Insufficient data for Bollinger Bands", 
                                  data_points=len(price_data), 
                                  required=period)
                current_price = price_data[-1] if price_data else 100.0
                return {
                    'success': False,
                    'upper_band': current_price * 1.1,
                    'lower_band': current_price * 0.9,
                    'middle_band': current_price,
                    'band_width': current_price * 0.2,
                    'percent_b': 0.5,
                    'error': 'Insufficient data'
                }
            
            # Convert to pandas Series
            if isinstance(price_data, list):
                prices = pd.Series(price_data)
            elif isinstance(price_data, pd.DataFrame):
                prices = price_data['Close'] if 'Close' in price_data.columns else price_data.iloc[:, 0]
            else:
                prices = pd.Series(price_data)
            
            # Calculate middle band (SMA)
            middle_band = prices.rolling(window=period).mean()
            
            # Calculate standard deviation
            rolling_std = prices.rolling(window=period).std()
            
            # Calculate upper and lower bands
            upper_band = middle_band + (rolling_std * std_dev)
            lower_band = middle_band - (rolling_std * std_dev)
            
            # Get final values
            current_price = float(prices.iloc[-1])
            upper_value = float(upper_band.iloc[-1]) if not upper_band.empty and not pd.isna(upper_band.iloc[-1]) else current_price * 1.1
            lower_value = float(lower_band.iloc[-1]) if not lower_band.empty and not pd.isna(lower_band.iloc[-1]) else current_price * 0.9
            middle_value = float(middle_band.iloc[-1]) if not middle_band.empty and not pd.isna(middle_band.iloc[-1]) else current_price
            
            # Calculate additional metrics
            band_width = upper_value - lower_value
            
            # %B (Percent B) - Position within the bands
            if band_width > 0:
                percent_b = (current_price - lower_value) / band_width
            else:
                percent_b = 0.5
            
            self.logger.debug("Bollinger Bands calculated successfully", 
                            upper=upper_value,
                            lower=lower_value,
                            width=band_width,
                            percent_b=percent_b,
                            data_points=len(price_data))
            
            return {
                'success': True,
                'upper_band': upper_value,
                'lower_band': lower_value,
                'middle_band': middle_value,
                'band_width': band_width,
                'percent_b': percent_b,
                'current_price': current_price
            }
            
        except Exception as e:
            self.logger.error("Error calculating Bollinger Bands", 
                            period=period,
                            std_dev=std_dev,
                            data_points=len(price_data) if price_data else 0,
                            error=str(e))
            current_price = price_data[-1] if price_data else 100.0
            return {
                'success': False,
                'upper_band': current_price * 1.1,
                'lower_band': current_price * 0.9,
                'middle_band': current_price,
                'band_width': current_price * 0.2,
                'percent_b': 0.5,
                'error': str(e)
            }
    
    async def calculate_bollinger_bands_from_dataframe(self, data: pd.DataFrame, period: int = None, std_dev: float = None) -> Dict[str, Any]:
        """Calculate Bollinger Bands from DataFrame with Close column"""
        try:
            if 'Close' not in data.columns:
                raise ValueError("DataFrame must have 'Close' column for Bollinger Bands calculation")
            
            return await self.calculate_bollinger_bands(data['Close'].tolist(), period, std_dev)
            
        except Exception as e:
            self.logger.error("Error calculating Bollinger Bands from DataFrame", error=str(e))
            return {
                'success': False,
                'upper_band': 110.0,
                'lower_band': 90.0,
                'middle_band': 100.0,
                'band_width': 20.0,
                'percent_b': 0.5,
                'error': str(e)
            }
    
    def interpret_bollinger_signals(self, percent_b: float, band_width: float, current_price: float, upper_band: float, lower_band: float) -> Dict[str, str]:
        """Interpret Bollinger Bands signals"""
        try:
            signals = {}
            
            # %B interpretation
            if percent_b > 1.0:
                signals['position'] = 'above_upper_band'
                signals['signal'] = 'potentially_overbought'
            elif percent_b < 0.0:
                signals['position'] = 'below_lower_band' 
                signals['signal'] = 'potentially_oversold'
            elif percent_b > 0.8:
                signals['position'] = 'near_upper_band'
                signals['signal'] = 'approaching_overbought'
            elif percent_b < 0.2:
                signals['position'] = 'near_lower_band'
                signals['signal'] = 'approaching_oversold'
            else:
                signals['position'] = 'within_bands'
                signals['signal'] = 'neutral'
            
            # Band width interpretation (volatility)
            avg_price = (upper_band + lower_band) / 2
            width_percentage = (band_width / avg_price) * 100
            
            if width_percentage > 20:
                signals['volatility'] = 'high_volatility'
            elif width_percentage < 10:
                signals['volatility'] = 'low_volatility'
            else:
                signals['volatility'] = 'normal_volatility'
            
            # Squeeze detection (narrow bands)
            if width_percentage < 5:
                signals['squeeze'] = 'bollinger_squeeze'
            else:
                signals['squeeze'] = 'no_squeeze'
            
            return signals
            
        except Exception as e:
            self.logger.error("Error interpreting Bollinger signals", error=str(e))
            return {'signal': 'neutral', 'volatility': 'normal_volatility'}
    
    def detect_bollinger_bounce(self, prices: list, upper_bands: list, lower_bands: list) -> str:
        """Detect Bollinger Band bounce patterns"""
        try:
            if len(prices) < 3 or len(upper_bands) < 3 or len(lower_bands) < 3:
                return 'insufficient_data'
            
            current_price = prices[-1]
            prev_price = prices[-2]
            
            current_upper = upper_bands[-1]
            current_lower = lower_bands[-1]
            
            # Upper band bounce
            if prev_price >= current_upper and current_price < current_upper:
                return 'upper_band_bounce'
            
            # Lower band bounce
            if prev_price <= current_lower and current_price > current_lower:
                return 'lower_band_bounce'
            
            return 'no_bounce'
            
        except Exception as e:
            self.logger.error("Error detecting Bollinger bounce", error=str(e))
            return 'no_bounce'
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'technical_indicator',
            'indicator': 'Bollinger Bands',
            'parameters': {
                'default_period': self.default_period,
                'default_std_dev': self.default_std_dev
            },
            'description': 'Calculates Bollinger Bands volatility indicator with %B and band width'
        }