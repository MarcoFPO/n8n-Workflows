"""
Support Resistance Module - Single Function Module
Calculates support and resistance levels
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import pd, np, datetime, Dict, Any, structlog
from shared.single_function_module_base import SingleFunctionModuleBase


class SupportResistanceModule(SingleFunctionModuleBase):
    """Calculate support and resistance levels using multiple methods"""
    
    def __init__(self, event_bus):
        super().__init__("support_resistance", event_bus)
        self.lookback_period = 20
        self.pivot_strength = 5
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('support_resistance.calculation.request', self.process_event)
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
                    'lookback_period': self.lookback_period,
                    'pivot_strength': self.pivot_strength
                },
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'support_resistance.calculation.request':
            high_data = event.get('high_data', [])
            low_data = event.get('low_data', [])
            close_data = event.get('close_data', [])
            lookback = event.get('lookback_period', self.lookback_period)
            
            sr_result = await self.calculate_support_resistance(high_data, low_data, close_data, lookback)
            
            response_event = {
                'event_type': 'support_resistance.calculation.response',
                'resistance_level': sr_result.get('resistance_level', 0.0),
                'support_level': sr_result.get('support_level', 0.0),
                'pivot_points': sr_result.get('pivot_points', {}),
                'price_position': sr_result.get('price_position', 0.5),
                'strength_score': sr_result.get('strength_score', 0.0),
                'data_points': len(high_data),
                'success': sr_result.get('success', False),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def calculate_support_resistance(self, high_data: list, low_data: list, close_data: list, lookback_period: int = None) -> Dict[str, Any]:
        """Calculate support and resistance levels"""
        try:
            if lookback_period is None:
                lookback_period = self.lookback_period
            
            if not high_data or not low_data or not close_data:
                return {
                    'success': False,
                    'error': 'Missing price data',
                    'resistance_level': 110.0,
                    'support_level': 90.0
                }
            
            if len(high_data) < lookback_period:
                lookback_period = len(high_data)
            
            # Convert to pandas Series
            highs = pd.Series(high_data[-lookback_period:] if lookback_period < len(high_data) else high_data)
            lows = pd.Series(low_data[-lookback_period:] if lookback_period < len(low_data) else low_data)
            closes = pd.Series(close_data[-lookback_period:] if lookback_period < len(close_data) else close_data)
            
            current_price = float(closes.iloc[-1])
            
            # Method 1: Simple High/Low levels
            resistance_simple = float(highs.max())
            support_simple = float(lows.min())
            
            # Method 2: Rolling High/Low levels
            resistance_rolling = float(highs.rolling(window=min(10, len(highs))).max().iloc[-1])
            support_rolling = float(lows.rolling(window=min(10, len(lows))).min().iloc[-1])
            
            # Method 3: Pivot Points
            pivot_points = await self._calculate_pivot_points(highs, lows, closes)
            
            # Method 4: Volume-weighted levels (if we had volume data)
            # For now, use price-weighted levels
            price_levels = await self._find_significant_levels(highs, lows, closes)
            
            # Combine methods for final levels
            resistance_level = max(resistance_simple, resistance_rolling, pivot_points.get('r1', resistance_simple))
            support_level = min(support_simple, support_rolling, pivot_points.get('s1', support_simple))
            
            # Calculate price position within the range
            price_range = resistance_level - support_level
            if price_range > 0:
                price_position = (current_price - support_level) / price_range
            else:
                price_position = 0.5
            
            # Calculate strength score based on how well-defined the levels are
            strength_score = await self._calculate_level_strength(highs, lows, closes, resistance_level, support_level)
            
            self.logger.debug("Support/Resistance calculated successfully", 
                            resistance=resistance_level,
                            support=support_level,
                            price_position=price_position,
                            strength=strength_score)
            
            return {
                'success': True,
                'resistance_level': resistance_level,
                'support_level': support_level,
                'pivot_points': pivot_points,
                'price_position': price_position,
                'strength_score': strength_score,
                'current_price': current_price,
                'price_range': price_range,
                'significant_levels': price_levels
            }
            
        except Exception as e:
            self.logger.error("Error calculating support/resistance", 
                            lookback_period=lookback_period,
                            data_points=len(high_data) if high_data else 0,
                            error=str(e))
            return {
                'success': False,
                'error': str(e),
                'resistance_level': 110.0,
                'support_level': 90.0,
                'price_position': 0.5
            }
    
    async def _calculate_pivot_points(self, highs: pd.Series, lows: pd.Series, closes: pd.Series) -> Dict[str, float]:
        """Calculate classic pivot points"""
        try:
            if len(highs) < 3 or len(lows) < 3 or len(closes) < 3:
                return {}
            
            # Use last complete period for pivot calculation
            high = float(highs.iloc[-2])  # Previous high
            low = float(lows.iloc[-2])    # Previous low
            close = float(closes.iloc[-2]) # Previous close
            
            # Calculate pivot point
            pivot = (high + low + close) / 3
            
            # Calculate support and resistance levels
            r1 = (2 * pivot) - low
            r2 = pivot + (high - low)
            r3 = high + 2 * (pivot - low)
            
            s1 = (2 * pivot) - high
            s2 = pivot - (high - low)
            s3 = low - 2 * (high - pivot)
            
            return {
                'pivot': pivot,
                'r1': r1,
                'r2': r2,
                'r3': r3,
                's1': s1,
                's2': s2,
                's3': s3
            }
            
        except Exception as e:
            self.logger.error("Error calculating pivot points", error=str(e))
            return {}
    
    async def _find_significant_levels(self, highs: pd.Series, lows: pd.Series, closes: pd.Series) -> Dict[str, list]:
        """Find significant price levels based on historical importance"""
        try:
            # Find local maxima and minima
            resistance_levels = []
            support_levels = []
            
            # Simple approach: find peaks and troughs
            for i in range(self.pivot_strength, len(highs) - self.pivot_strength):
                # Resistance (local high)
                is_peak = True
                for j in range(i - self.pivot_strength, i + self.pivot_strength + 1):
                    if j != i and highs.iloc[j] >= highs.iloc[i]:
                        is_peak = False
                        break
                if is_peak:
                    resistance_levels.append(float(highs.iloc[i]))
                
                # Support (local low)
                is_trough = True
                for j in range(i - self.pivot_strength, i + self.pivot_strength + 1):
                    if j != i and lows.iloc[j] <= lows.iloc[i]:
                        is_trough = False
                        break
                if is_trough:
                    support_levels.append(float(lows.iloc[i]))
            
            # Sort and return most significant levels
            resistance_levels.sort(reverse=True)
            support_levels.sort()
            
            return {
                'resistance_levels': resistance_levels[:5],  # Top 5 resistance levels
                'support_levels': support_levels[:5]         # Top 5 support levels
            }
            
        except Exception as e:
            self.logger.error("Error finding significant levels", error=str(e))
            return {'resistance_levels': [], 'support_levels': []}
    
    async def _calculate_level_strength(self, highs: pd.Series, lows: pd.Series, closes: pd.Series, resistance: float, support: float) -> float:
        """Calculate the strength/reliability of support and resistance levels"""
        try:
            strength_score = 0.0
            
            # Count touches of resistance level (within 1% tolerance)
            resistance_touches = 0
            tolerance = resistance * 0.01
            for high in highs:
                if abs(high - resistance) <= tolerance:
                    resistance_touches += 1
            
            # Count touches of support level
            support_touches = 0
            tolerance = support * 0.01
            for low in lows:
                if abs(low - support) <= tolerance:
                    support_touches += 1
            
            # More touches = stronger level
            strength_score += min(resistance_touches, 5) * 0.1
            strength_score += min(support_touches, 5) * 0.1
            
            # Check if price has respected these levels recently
            recent_closes = closes.iloc[-5:]  # Last 5 closes
            respected_support = all(close >= support * 0.99 for close in recent_closes)
            respected_resistance = all(close <= resistance * 1.01 for close in recent_closes)
            
            if respected_support:
                strength_score += 0.2
            if respected_resistance:
                strength_score += 0.2
            
            # Normalize to 0-1 range
            return min(strength_score, 1.0)
            
        except Exception as e:
            self.logger.error("Error calculating level strength", error=str(e))
            return 0.5
    
    def interpret_support_resistance_signals(self, current_price: float, support_level: float, resistance_level: float, price_position: float) -> Dict[str, str]:
        """Interpret support/resistance signals"""
        try:
            signals = {}
            
            # Distance from levels
            distance_to_support = abs(current_price - support_level) / current_price
            distance_to_resistance = abs(current_price - resistance_level) / current_price
            
            # Position-based signals
            if price_position > 0.8:
                signals['position'] = 'near_resistance'
                signals['signal'] = 'potential_reversal_down'
            elif price_position < 0.2:
                signals['position'] = 'near_support'
                signals['signal'] = 'potential_reversal_up'
            elif 0.4 <= price_position <= 0.6:
                signals['position'] = 'mid_range'
                signals['signal'] = 'neutral'
            else:
                signals['position'] = 'trending'
                signals['signal'] = 'momentum_continuation'
            
            # Breakout potential
            if distance_to_resistance < 0.02:  # Within 2%
                signals['breakout_potential'] = 'resistance_test'
            elif distance_to_support < 0.02:  # Within 2%
                signals['breakout_potential'] = 'support_test'
            else:
                signals['breakout_potential'] = 'no_immediate_test'
            
            return signals
            
        except Exception as e:
            self.logger.error("Error interpreting S/R signals", error=str(e))
            return {'signal': 'neutral'}
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'technical_analysis',
            'analysis_type': 'support_resistance',
            'parameters': {
                'lookback_period': self.lookback_period,
                'pivot_strength': self.pivot_strength
            },
            'methods': [
                'rolling_high_low',
                'pivot_points',
                'significant_levels',
                'strength_scoring'
            ],
            'description': 'Calculates support and resistance levels using multiple technical analysis methods'
        }