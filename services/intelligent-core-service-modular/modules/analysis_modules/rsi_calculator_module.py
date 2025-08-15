"""
RSI Calculator Module - Single Function Module
Calculates Relative Strength Index indicator
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import pd, np, datetime, Dict, Any, structlog
from shared.single_function_module_base import SingleFunctionModuleBase


class RSICalculatorModule(SingleFunctionModuleBase):
    """Calculate Relative Strength Index (RSI) technical indicator"""
    
    def __init__(self, event_bus):
        super().__init__("rsi_calculator", event_bus)
        self.default_period = 14
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('rsi.calculation.request', self.process_event)
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
        
        elif event_type == 'rsi.calculation.request':
            data = event.get('price_data', [])
            period = event.get('period', self.default_period)
            
            rsi_value = await self.calculate_rsi(data, period)
            
            response_event = {
                'event_type': 'rsi.calculation.response',
                'rsi_value': rsi_value,
                'period': period,
                'data_points': len(data),
                'success': rsi_value is not None,
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def calculate_rsi(self, price_data: list, period: int = None) -> float:
        """Calculate RSI from price data"""
        try:
            if period is None:
                period = self.default_period
            
            if len(price_data) < period + 1:
                self.logger.warning("Insufficient data for RSI calculation", 
                                  data_points=len(price_data), 
                                  required=period + 1)
                return 50.0  # Neutral RSI
            
            # Convert to pandas Series for calculation
            if isinstance(price_data, list):
                prices = pd.Series(price_data)
            elif isinstance(price_data, pd.DataFrame):
                prices = price_data['Close'] if 'Close' in price_data.columns else price_data.iloc[:, 0]
            else:
                prices = pd.Series(price_data)
            
            # Calculate price changes
            delta = prices.diff()
            
            # Separate gains and losses
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            # Calculate average gains and losses
            avg_gain = gain.rolling(window=period, min_periods=period).mean()
            avg_loss = loss.rolling(window=period, min_periods=period).mean()
            
            # Calculate RS and RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Return the most recent RSI value
            final_rsi = float(rsi.iloc[-1]) if not rsi.empty and not pd.isna(rsi.iloc[-1]) else 50.0
            
            self.logger.debug("RSI calculated successfully", 
                            rsi_value=final_rsi, 
                            period=period,
                            data_points=len(price_data))
            
            return final_rsi
            
        except Exception as e:
            self.logger.error("Error calculating RSI", 
                            period=period,
                            data_points=len(price_data) if price_data else 0,
                            error=str(e))
            return 50.0  # Return neutral RSI on error
    
    async def calculate_rsi_from_dataframe(self, data: pd.DataFrame, period: int = None) -> float:
        """Calculate RSI from DataFrame with Close column"""
        try:
            if 'Close' not in data.columns:
                raise ValueError("DataFrame must have 'Close' column for RSI calculation")
            
            return await self.calculate_rsi(data['Close'].tolist(), period)
            
        except Exception as e:
            self.logger.error("Error calculating RSI from DataFrame", error=str(e))
            return 50.0
    
    def validate_rsi_value(self, rsi: float) -> bool:
        """Validate if RSI value is within expected range (0-100)"""
        return 0 <= rsi <= 100
    
    def interpret_rsi_signal(self, rsi: float) -> str:
        """Interpret RSI value to trading signal"""
        if rsi >= 70:
            return "overbought"
        elif rsi <= 30:
            return "oversold"
        elif 50 <= rsi < 70:
            return "bullish"
        elif 30 < rsi < 50:
            return "bearish"
        else:
            return "neutral"
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'technical_indicator',
            'indicator': 'RSI',
            'default_period': self.default_period,
            'description': 'Calculates Relative Strength Index (RSI) technical indicator'
        }