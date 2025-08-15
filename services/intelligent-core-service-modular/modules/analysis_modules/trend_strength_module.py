"""
Trend Strength Module - Single Function Module
Calculates trend strength and direction indicators
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import pd, np, datetime, Dict, Any, structlog
from shared.single_function_module_base import SingleFunctionModuleBase


class TrendStrengthModule(SingleFunctionModuleBase):
    """Calculate trend strength and direction using multiple methods"""
    
    def __init__(self, event_bus):
        super().__init__("trend_strength", event_bus)
        self.trend_period = 10
        self.volume_factor_weight = 0.3
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('trend_strength.calculation.request', self.process_event)
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
                'trend_period': self.trend_period,
                'volume_factor_weight': self.volume_factor_weight,
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'trend_strength.calculation.request':
            price_data = event.get('price_data', [])
            volume_data = event.get('volume_data', [])
            period = event.get('period', self.trend_period)
            
            trend_result = await self.calculate_trend_strength(price_data, volume_data, period)
            
            response_event = {
                'event_type': 'trend_strength.calculation.response',
                'trend_strength': trend_result.get('trend_strength', 0.0),
                'trend_direction': trend_result.get('trend_direction', 'neutral'),
                'trend_momentum': trend_result.get('trend_momentum', 0.0),
                'trend_consistency': trend_result.get('trend_consistency', 0.0),
                'volume_confirmation': trend_result.get('volume_confirmation', False),
                'period': period,
                'data_points': len(price_data),
                'success': trend_result.get('success', False),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def calculate_trend_strength(self, price_data: list, volume_data: list = None, period: int = None) -> Dict[str, Any]:
        """Calculate comprehensive trend strength analysis"""
        try:
            if period is None:
                period = self.trend_period
            
            if not price_data or len(price_data) < period:
                return {
                    'success': False,
                    'error': 'Insufficient price data',
                    'trend_strength': 0.0,
                    'trend_direction': 'neutral'
                }
            
            # Convert to pandas Series
            prices = pd.Series(price_data)
            volumes = pd.Series(volume_data) if volume_data and len(volume_data) == len(price_data) else None
            
            # Method 1: Price Trend Analysis
            price_trend_strength = await self._calculate_price_trend_strength(prices, period)
            
            # Method 2: Momentum Analysis
            momentum_strength = await self._calculate_momentum_strength(prices, period)
            
            # Method 3: Consistency Analysis
            trend_consistency = await self._calculate_trend_consistency(prices, period)
            
            # Method 4: Volume Confirmation (if available)
            volume_confirmation, volume_strength = await self._calculate_volume_confirmation(prices, volumes, period)
            
            # Method 5: Linear Regression Trend
            regression_strength = await self._calculate_regression_trend_strength(prices, period)
            
            # Combine all methods with weights
            weights = {
                'price_trend': 0.25,
                'momentum': 0.25,
                'consistency': 0.20,
                'volume': self.volume_factor_weight if volume_confirmation else 0.0,
                'regression': 0.30 - (self.volume_factor_weight if not volume_confirmation else 0.0)
            }
            
            # Calculate composite trend strength
            trend_strength = (
                price_trend_strength['strength'] * weights['price_trend'] +
                momentum_strength * weights['momentum'] +
                trend_consistency * weights['consistency'] +
                volume_strength * weights['volume'] +
                regression_strength['strength'] * weights['regression']
            )
            
            # Determine trend direction
            if price_trend_strength['direction'] > 0.1:
                trend_direction = 'bullish'
            elif price_trend_strength['direction'] < -0.1:
                trend_direction = 'bearish'
            else:
                trend_direction = 'neutral'
            
            # Calculate trend momentum (rate of change)
            trend_momentum = await self._calculate_trend_momentum(prices, period)
            
            self.logger.debug("Trend strength calculated successfully", 
                            strength=trend_strength,
                            direction=trend_direction,
                            momentum=trend_momentum,
                            consistency=trend_consistency)
            
            return {
                'success': True,
                'trend_strength': float(trend_strength),
                'trend_direction': trend_direction,
                'trend_momentum': float(trend_momentum),
                'trend_consistency': float(trend_consistency),
                'volume_confirmation': volume_confirmation,
                'price_trend_component': price_trend_strength['strength'],
                'momentum_component': momentum_strength,
                'regression_component': regression_strength['strength'],
                'regression_slope': regression_strength['slope'],
                'regression_r2': regression_strength['r_squared']
            }
            
        except Exception as e:
            self.logger.error("Error calculating trend strength", 
                            period=period,
                            data_points=len(price_data) if price_data else 0,
                            error=str(e))
            return {
                'success': False,
                'error': str(e),
                'trend_strength': 0.0,
                'trend_direction': 'neutral'
            }
    
    async def _calculate_price_trend_strength(self, prices: pd.Series, period: int) -> Dict[str, float]:
        """Calculate price-based trend strength"""
        try:
            # Simple price change over period
            current_price = prices.iloc[-1]
            start_price = prices.iloc[-period]
            
            price_change = (current_price - start_price) / start_price
            
            # Normalize to -1 to 1 range using tanh
            direction = np.tanh(price_change * 10)  # Amplify for better scaling
            strength = abs(direction)
            
            return {
                'strength': strength,
                'direction': direction,
                'price_change_pct': price_change * 100
            }
            
        except Exception as e:
            self.logger.error("Error calculating price trend strength", error=str(e))
            return {'strength': 0.0, 'direction': 0.0}
    
    async def _calculate_momentum_strength(self, prices: pd.Series, period: int) -> float:
        """Calculate momentum-based trend strength"""
        try:
            # Calculate rate of change over different timeframes
            roc_short = prices.pct_change(periods=max(1, period // 4)).iloc[-1]
            roc_medium = prices.pct_change(periods=max(1, period // 2)).iloc[-1]
            roc_long = prices.pct_change(periods=period).iloc[-1]
            
            # Weight shorter timeframes more heavily for momentum
            momentum = (roc_short * 0.5 + roc_medium * 0.3 + roc_long * 0.2)
            
            # Normalize using tanh
            return float(np.tanh(abs(momentum) * 20))  # Amplify momentum signal
            
        except Exception as e:
            self.logger.error("Error calculating momentum strength", error=str(e))
            return 0.0
    
    async def _calculate_trend_consistency(self, prices: pd.Series, period: int) -> float:
        """Calculate how consistent the trend direction has been"""
        try:
            # Calculate daily changes
            daily_changes = prices.diff().dropna()
            
            if len(daily_changes) < period:
                period = len(daily_changes)
            
            recent_changes = daily_changes.iloc[-period:]
            
            # Count positive vs negative changes
            positive_days = (recent_changes > 0).sum()
            negative_days = (recent_changes < 0).sum()
            total_days = len(recent_changes)
            
            if total_days == 0:
                return 0.0
            
            # Calculate consistency as deviation from 50/50
            consistency = abs((positive_days - negative_days) / total_days)
            
            return float(consistency)
            
        except Exception as e:
            self.logger.error("Error calculating trend consistency", error=str(e))
            return 0.0
    
    async def _calculate_volume_confirmation(self, prices: pd.Series, volumes: pd.Series, period: int) -> tuple:
        """Calculate volume confirmation of price trend"""
        try:
            if volumes is None or len(volumes) == 0:
                return False, 0.0
            
            # Calculate price and volume changes
            price_changes = prices.diff().dropna()
            volume_changes = volumes.diff().dropna()
            
            min_length = min(len(price_changes), len(volume_changes), period)
            if min_length < 3:
                return False, 0.0
            
            recent_price_changes = price_changes.iloc[-min_length:]
            recent_volume_changes = volume_changes.iloc[-min_length:]
            
            # Calculate correlation
            correlation = recent_price_changes.corr(recent_volume_changes)
            
            # Volume confirmation exists if price and volume move together
            volume_confirmation = not pd.isna(correlation) and abs(correlation) > 0.3
            volume_strength = abs(correlation) if not pd.isna(correlation) else 0.0
            
            return volume_confirmation, float(volume_strength)
            
        except Exception as e:
            self.logger.error("Error calculating volume confirmation", error=str(e))
            return False, 0.0
    
    async def _calculate_regression_trend_strength(self, prices: pd.Series, period: int) -> Dict[str, float]:
        """Calculate trend strength using linear regression"""
        try:
            # Use last 'period' prices
            recent_prices = prices.iloc[-period:]
            x = np.arange(len(recent_prices))
            y = recent_prices.values
            
            # Calculate linear regression
            n = len(x)
            sum_x = np.sum(x)
            sum_y = np.sum(y)
            sum_xy = np.sum(x * y)
            sum_x2 = np.sum(x ** 2)
            
            # Slope and intercept
            denominator = n * sum_x2 - sum_x ** 2
            if denominator == 0:
                return {'strength': 0.0, 'slope': 0.0, 'r_squared': 0.0}
            
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            intercept = (sum_y - slope * sum_x) / n
            
            # Calculate R-squared
            y_pred = slope * x + intercept
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
            
            # Trend strength is R-squared (how well line fits)
            strength = max(0.0, r_squared)
            
            # Normalize slope relative to price
            normalized_slope = slope / np.mean(y) if np.mean(y) != 0 else 0.0
            
            return {
                'strength': float(strength),
                'slope': float(normalized_slope),
                'r_squared': float(r_squared)
            }
            
        except Exception as e:
            self.logger.error("Error calculating regression trend strength", error=str(e))
            return {'strength': 0.0, 'slope': 0.0, 'r_squared': 0.0}
    
    async def _calculate_trend_momentum(self, prices: pd.Series, period: int) -> float:
        """Calculate the acceleration/deceleration of trend"""
        try:
            # Calculate momentum as second derivative (change in rate of change)
            if len(prices) < period + 2:
                return 0.0
            
            # Recent rate of change
            recent_roc = prices.pct_change(periods=max(1, period // 2)).iloc[-1]
            
            # Previous rate of change
            prev_roc = prices.pct_change(periods=max(1, period // 2)).iloc[-period // 2 - 1]
            
            # Momentum is change in rate of change
            momentum = recent_roc - prev_roc if not pd.isna(recent_roc) and not pd.isna(prev_roc) else 0.0
            
            # Normalize
            return float(np.tanh(momentum * 100))  # Scale for better representation
            
        except Exception as e:
            self.logger.error("Error calculating trend momentum", error=str(e))
            return 0.0
    
    def interpret_trend_signals(self, trend_strength: float, trend_direction: str, trend_momentum: float, trend_consistency: float) -> Dict[str, str]:
        """Interpret trend analysis signals"""
        try:
            signals = {}
            
            # Strength interpretation
            if trend_strength > 0.8:
                signals['strength_level'] = 'very_strong'
            elif trend_strength > 0.6:
                signals['strength_level'] = 'strong'
            elif trend_strength > 0.4:
                signals['strength_level'] = 'moderate'
            elif trend_strength > 0.2:
                signals['strength_level'] = 'weak'
            else:
                signals['strength_level'] = 'very_weak'
            
            # Direction
            signals['direction'] = trend_direction
            
            # Momentum interpretation
            if trend_momentum > 0.3:
                signals['momentum'] = 'accelerating'
            elif trend_momentum < -0.3:
                signals['momentum'] = 'decelerating'
            else:
                signals['momentum'] = 'stable'
            
            # Consistency interpretation
            if trend_consistency > 0.7:
                signals['consistency'] = 'very_consistent'
            elif trend_consistency > 0.5:
                signals['consistency'] = 'consistent'
            else:
                signals['consistency'] = 'choppy'
            
            # Overall signal
            if trend_strength > 0.6 and trend_consistency > 0.5:
                if trend_direction == 'bullish':
                    signals['overall_signal'] = 'strong_uptrend'
                elif trend_direction == 'bearish':
                    signals['overall_signal'] = 'strong_downtrend'
                else:
                    signals['overall_signal'] = 'strong_sideways'
            elif trend_strength > 0.3:
                signals['overall_signal'] = f'weak_{trend_direction}_trend'
            else:
                signals['overall_signal'] = 'no_clear_trend'
            
            return signals
            
        except Exception as e:
            self.logger.error("Error interpreting trend signals", error=str(e))
            return {'overall_signal': 'neutral'}
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'trend_analysis',
            'trend_period': self.trend_period,
            'volume_factor_weight': self.volume_factor_weight,
            'methods': [
                'price_trend_analysis',
                'momentum_calculation', 
                'trend_consistency',
                'volume_confirmation',
                'linear_regression'
            ],
            'description': 'Calculates comprehensive trend strength using multiple analysis methods'
        }