"""
Volume Analysis Module - Single Function Module
Analyzes trading volume patterns and indicators
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import pd, np, datetime, Dict, Any, structlog
from shared.single_function_module_base import SingleFunctionModuleBase


class VolumeAnalysisModule(SingleFunctionModuleBase):
    """Analyze trading volume patterns and calculate volume-based indicators"""
    
    def __init__(self, event_bus):
        super().__init__("volume_analysis", event_bus)
        self.volume_ma_period = 20
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('volume.analysis.request', self.process_event)
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
                'volume_ma_period': self.volume_ma_period,
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'volume.analysis.request':
            volume_data = event.get('volume_data', [])
            price_data = event.get('price_data', [])
            
            volume_result = await self.analyze_volume(volume_data, price_data)
            
            response_event = {
                'event_type': 'volume.analysis.response',
                'current_volume': volume_result.get('current_volume', 0),
                'avg_volume': volume_result.get('avg_volume', 0),
                'volume_ratio': volume_result.get('volume_ratio', 1.0),
                'volume_trend': volume_result.get('volume_trend', 'neutral'),
                'price_volume_correlation': volume_result.get('price_volume_correlation', 0.0),
                'data_points': len(volume_data),
                'success': volume_result.get('success', False),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def analyze_volume(self, volume_data: list, price_data: list = None) -> Dict[str, Any]:
        """Comprehensive volume analysis"""
        try:
            if not volume_data:
                return {
                    'success': False,
                    'error': 'No volume data provided',
                    'current_volume': 0,
                    'avg_volume': 0,
                    'volume_ratio': 1.0
                }
            
            # Convert to pandas Series
            if isinstance(volume_data, list):
                volumes = pd.Series(volume_data)
            else:
                volumes = pd.Series(volume_data)
            
            # Basic volume metrics
            current_volume = float(volumes.iloc[-1])
            
            # Calculate volume moving average
            if len(volumes) >= self.volume_ma_period:
                avg_volume = float(volumes.rolling(window=self.volume_ma_period).mean().iloc[-1])
            else:
                avg_volume = float(volumes.mean())
            
            # Volume ratio (current vs average)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Volume trend analysis
            volume_trend = await self._calculate_volume_trend(volumes)
            
            # Price-Volume correlation if price data provided
            price_volume_correlation = 0.0
            if price_data and len(price_data) == len(volume_data) and len(price_data) > 1:
                price_volume_correlation = await self._calculate_price_volume_correlation(price_data, volume_data)
            
            # Volume distribution analysis
            volume_distribution = await self._analyze_volume_distribution(volumes)
            
            self.logger.debug("Volume analysis completed", 
                            current_volume=current_volume,
                            avg_volume=avg_volume,
                            volume_ratio=volume_ratio,
                            trend=volume_trend)
            
            return {
                'success': True,
                'current_volume': current_volume,
                'avg_volume': avg_volume,
                'volume_ratio': volume_ratio,
                'volume_trend': volume_trend,
                'price_volume_correlation': price_volume_correlation,
                'volume_distribution': volume_distribution,
                'volume_percentile': await self._calculate_volume_percentile(volumes),
                'volume_spikes_count': await self._count_volume_spikes(volumes)
            }
            
        except Exception as e:
            self.logger.error("Error in volume analysis", 
                            data_points=len(volume_data) if volume_data else 0,
                            error=str(e))
            return {
                'success': False,
                'error': str(e),
                'current_volume': 0,
                'avg_volume': 0,
                'volume_ratio': 1.0
            }
    
    async def _calculate_volume_trend(self, volumes: pd.Series) -> str:
        """Calculate volume trend over recent periods"""
        try:
            if len(volumes) < 5:
                return 'insufficient_data'
            
            # Compare recent 5 periods vs previous 5 periods
            recent_avg = volumes.iloc[-5:].mean()
            previous_avg = volumes.iloc[-10:-5].mean() if len(volumes) >= 10 else volumes.iloc[:-5].mean()
            
            if recent_avg > previous_avg * 1.2:
                return 'increasing'
            elif recent_avg < previous_avg * 0.8:
                return 'decreasing'
            else:
                return 'stable'
                
        except Exception as e:
            self.logger.error("Error calculating volume trend", error=str(e))
            return 'neutral'
    
    async def _calculate_price_volume_correlation(self, price_data: list, volume_data: list) -> float:
        """Calculate correlation between price changes and volume"""
        try:
            prices = pd.Series(price_data)
            volumes = pd.Series(volume_data)
            
            # Calculate price changes
            price_changes = prices.pct_change().dropna()
            volume_changes = volumes.pct_change().dropna()
            
            # Ensure same length
            min_length = min(len(price_changes), len(volume_changes))
            if min_length < 2:
                return 0.0
            
            price_changes = price_changes.iloc[-min_length:]
            volume_changes = volume_changes.iloc[-min_length:]
            
            correlation = price_changes.corr(volume_changes)
            return float(correlation) if not pd.isna(correlation) else 0.0
            
        except Exception as e:
            self.logger.error("Error calculating price-volume correlation", error=str(e))
            return 0.0
    
    async def _analyze_volume_distribution(self, volumes: pd.Series) -> Dict[str, float]:
        """Analyze volume distribution statistics"""
        try:
            return {
                'median_volume': float(volumes.median()),
                'volume_std': float(volumes.std()),
                'volume_skewness': float(volumes.skew()) if len(volumes) > 2 else 0.0,
                'volume_kurtosis': float(volumes.kurtosis()) if len(volumes) > 3 else 0.0
            }
        except Exception as e:
            self.logger.error("Error analyzing volume distribution", error=str(e))
            return {
                'median_volume': 0.0,
                'volume_std': 0.0,
                'volume_skewness': 0.0,
                'volume_kurtosis': 0.0
            }
    
    async def _calculate_volume_percentile(self, volumes: pd.Series) -> float:
        """Calculate current volume percentile relative to historical data"""
        try:
            current_volume = volumes.iloc[-1]
            percentile = (volumes <= current_volume).mean() * 100
            return float(percentile)
        except Exception as e:
            self.logger.error("Error calculating volume percentile", error=str(e))
            return 50.0
    
    async def _count_volume_spikes(self, volumes: pd.Series, threshold: float = 2.0) -> int:
        """Count volume spikes (volumes > threshold * average)"""
        try:
            if len(volumes) < self.volume_ma_period:
                return 0
            
            avg_volume = volumes.rolling(window=self.volume_ma_period).mean()
            spikes = (volumes > avg_volume * threshold).sum()
            return int(spikes)
        except Exception as e:
            self.logger.error("Error counting volume spikes", error=str(e))
            return 0
    
    def interpret_volume_signals(self, volume_ratio: float, volume_trend: str, price_volume_correlation: float) -> Dict[str, str]:
        """Interpret volume analysis signals"""
        try:
            signals = {}
            
            # Volume ratio interpretation
            if volume_ratio > 2.0:
                signals['volume_strength'] = 'very_high'
            elif volume_ratio > 1.5:
                signals['volume_strength'] = 'high'
            elif volume_ratio > 1.2:
                signals['volume_strength'] = 'above_average'
            elif volume_ratio < 0.5:
                signals['volume_strength'] = 'very_low'
            elif volume_ratio < 0.8:
                signals['volume_strength'] = 'low'
            else:
                signals['volume_strength'] = 'normal'
            
            # Volume trend interpretation
            signals['volume_trend'] = volume_trend
            
            # Price-volume relationship
            if abs(price_volume_correlation) > 0.7:
                signals['price_volume_sync'] = 'strong_correlation'
            elif abs(price_volume_correlation) > 0.3:
                signals['price_volume_sync'] = 'moderate_correlation'
            else:
                signals['price_volume_sync'] = 'weak_correlation'
            
            # Combined signal
            if volume_ratio > 1.5 and volume_trend == 'increasing':
                signals['overall_signal'] = 'strong_momentum'
            elif volume_ratio < 0.8 and volume_trend == 'decreasing':
                signals['overall_signal'] = 'weak_momentum'
            else:
                signals['overall_signal'] = 'neutral_momentum'
            
            return signals
            
        except Exception as e:
            self.logger.error("Error interpreting volume signals", error=str(e))
            return {'overall_signal': 'neutral_momentum'}
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'volume_analysis',
            'volume_ma_period': self.volume_ma_period,
            'features': [
                'volume_ratio_calculation',
                'volume_trend_analysis', 
                'price_volume_correlation',
                'volume_distribution_analysis',
                'volume_spike_detection'
            ],
            'description': 'Analyzes trading volume patterns and volume-based indicators'
        }