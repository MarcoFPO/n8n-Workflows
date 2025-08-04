"""
Performance Module für Intelligent-Core-Service
Performance Analytics und Risk-Metriken
"""

import sys
sys.path.append('/opt/aktienanalyse-ökosystem')

# Shared Library Import für Code-Duplikation-Eliminierung
from shared.common_imports import (
    np, pd, datetime, timedelta, Dict, Any, List, Optional, structlog
)
from backend_base_module import BackendBaseModule
from event_bus import EventType


class PerformanceModule(BackendBaseModule):
    """Performance Analytics und Risk Assessment"""
    
    def __init__(self, event_bus):
        super().__init__("performance", event_bus)
        self.performance_cache = {}
        self.risk_metrics_cache = {}
        self.benchmark_data = {}
        self.cache_ttl = 600  # 10 Minuten für Performance-Daten
        
    async def _initialize_module(self) -> bool:
        """Initialize performance module"""
        try:
            self.logger.info("Initializing Performance Module")
            
            # Initialize benchmark data (S&P 500 proxy)
            self.benchmark_data = {
                'symbol': 'SPY',
                'annual_return': 0.10,  # 10% average
                'volatility': 0.16,     # 16% volatility
                'sharpe_ratio': 0.625,  # (10% - 2%) / 16%
                'max_drawdown': 0.34    # Historical max drawdown
            }
            
            # Test performance calculations
            test_returns = np.random.normal(0.001, 0.02, 252)  # Daily returns
            test_metrics = await self._calculate_performance_metrics(test_returns)
            
            self.logger.info("Performance module test successful", 
                           metrics_count=len(test_metrics))
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize performance module", error=str(e))
            return False
    
    async def _subscribe_to_events(self):
        """Subscribe to relevant events"""
        await self.subscribe_to_event(
            EventType.TRADING_STATE_CHANGED,
            self._handle_trading_event
        )
        await self.subscribe_to_event(
            EventType.PORTFOLIO_STATE_CHANGED,
            self._handle_portfolio_event
        )
        await self.subscribe_to_event(
            EventType.ANALYSIS_STATE_CHANGED,
            self._handle_analysis_event
        )
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Main performance processing logic"""
        try:
            request_type = data.get('type', 'performance_analysis')
            
            if request_type == 'performance_analysis':
                return await self._process_performance_analysis(data)
            elif request_type == 'risk_assessment':
                return await self._process_risk_assessment(data)
            elif request_type == 'confidence_calculation':
                return await self._process_confidence_calculation(data)
            elif request_type == 'benchmark_comparison':
                return await self._process_benchmark_comparison(data)
            else:
                return {
                    'success': False,
                    'error': f'Unknown request type: {request_type}'
                }
                
        except Exception as e:
            self.logger.error("Error in performance processing", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _process_performance_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process performance analysis request"""
        try:
            symbol = data.get('symbol', 'UNKNOWN')
            price_data = data.get('price_data', [])
            period = data.get('period', '1y')
            
            if not price_data:
                return {
                    'success': False,
                    'error': 'No price data provided for performance analysis'
                }
            
            # Check cache
            cache_key = f"{symbol}_{period}_{len(price_data)}"
            if cache_key in self.performance_cache:
                cache_entry = self.performance_cache[cache_key]
                cache_age = (datetime.now() - cache_entry['timestamp']).total_seconds()
                if cache_age < self.cache_ttl:
                    self.logger.debug("Returning cached performance analysis", symbol=symbol)
                    return cache_entry['data']
            
            # Calculate returns
            returns = self._calculate_returns(price_data)
            
            # Calculate performance metrics
            performance_metrics = await self._calculate_performance_metrics(returns)
            
            # Calculate risk metrics
            risk_metrics = await self._calculate_risk_metrics(returns, price_data)
            
            # Compare to benchmark
            benchmark_comparison = await self._compare_to_benchmark(performance_metrics)
            
            result = {
                'success': True,
                'symbol': symbol,
                'period': period,
                'performance_metrics': performance_metrics,
                'risk_metrics': risk_metrics,
                'benchmark_comparison': benchmark_comparison,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            # Cache result
            self.performance_cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }
            
            # Publish performance event
            await self.publish_module_event(
                EventType.PORTFOLIO_STATE_CHANGED,
                {
                    'symbol': symbol,
                    'performance_metrics': performance_metrics,
                    'risk_level': risk_metrics.get('risk_level', 'medium')
                },
                f"performance-{symbol}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Error processing performance analysis", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _process_confidence_calculation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process confidence calculation request"""
        try:
            indicators = data.get('indicators', {})
            ml_scores = data.get('ml_scores', {})
            symbol = data.get('symbol', 'UNKNOWN')
            
            # Calculate confidence score
            confidence = await self._calculate_confidence(indicators, ml_scores)
            
            # Generate confidence breakdown
            confidence_breakdown = self._generate_confidence_breakdown(indicators, ml_scores)
            
            result = {
                'success': True,
                'symbol': symbol,
                'confidence': confidence,
                'confidence_breakdown': confidence_breakdown,
                'calculation_timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            self.logger.error("Error calculating confidence", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_returns(self, price_data: List[float]) -> np.ndarray:
        """Calculate returns from price data"""
        try:
            prices = np.array(price_data)
            returns = np.diff(prices) / prices[:-1]
            return returns[~np.isnan(returns)]  # Remove NaN values
        except Exception as e:
            self.logger.error("Error calculating returns", error=str(e))
            return np.array([])
    
    async def _calculate_performance_metrics(self, returns: np.ndarray) -> Dict[str, float]:
        """Calculate comprehensive performance metrics"""
        try:
            if len(returns) == 0:
                return self._get_default_performance_metrics()
            
            metrics = {}
            
            # Basic return metrics
            metrics['total_return'] = float(np.prod(1 + returns) - 1)
            metrics['annualized_return'] = float((1 + metrics['total_return']) ** (252 / len(returns)) - 1)
            metrics['average_daily_return'] = float(np.mean(returns))
            
            # Volatility metrics
            metrics['daily_volatility'] = float(np.std(returns))
            metrics['annualized_volatility'] = float(metrics['daily_volatility'] * np.sqrt(252))
            
            # Risk-adjusted returns
            risk_free_rate = 0.02  # 2% risk-free rate
            excess_returns = metrics['annualized_return'] - risk_free_rate
            
            if metrics['annualized_volatility'] > 0:
                metrics['sharpe_ratio'] = float(excess_returns / metrics['annualized_volatility'])
            else:
                metrics['sharpe_ratio'] = 0.0
            
            # Drawdown metrics
            cumulative_returns = np.cumprod(1 + returns)
            rolling_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            
            metrics['max_drawdown'] = float(abs(np.min(drawdowns)))
            metrics['current_drawdown'] = float(abs(drawdowns[-1]))
            
            # Additional risk metrics
            metrics['value_at_risk_95'] = float(np.percentile(returns, 5))
            metrics['value_at_risk_99'] = float(np.percentile(returns, 1))
            
            # Sortino ratio (downside deviation)
            negative_returns = returns[returns < 0]
            if len(negative_returns) > 0:
                downside_deviation = np.std(negative_returns) * np.sqrt(252)
                if downside_deviation > 0:
                    metrics['sortino_ratio'] = float(excess_returns / downside_deviation)
                else:
                    metrics['sortino_ratio'] = 0.0
            else:
                metrics['sortino_ratio'] = float('inf')
            
            # Win rate and average win/loss
            winning_days = returns[returns > 0]
            losing_days = returns[returns < 0]
            
            metrics['win_rate'] = float(len(winning_days) / len(returns)) if len(returns) > 0 else 0.0
            metrics['average_win'] = float(np.mean(winning_days)) if len(winning_days) > 0 else 0.0
            metrics['average_loss'] = float(np.mean(losing_days)) if len(losing_days) > 0 else 0.0
            
            if metrics['average_loss'] != 0:
                metrics['win_loss_ratio'] = float(abs(metrics['average_win'] / metrics['average_loss']))
            else:
                metrics['win_loss_ratio'] = float('inf')
            
            # Calmar ratio (annual return / max drawdown)
            if metrics['max_drawdown'] > 0:
                metrics['calmar_ratio'] = float(metrics['annualized_return'] / metrics['max_drawdown'])
            else:
                metrics['calmar_ratio'] = float('inf')
            
            return metrics
            
        except Exception as e:
            self.logger.error("Error calculating performance metrics", error=str(e))
            return self._get_default_performance_metrics()
    
    async def _calculate_risk_metrics(self, returns: np.ndarray, price_data: List[float]) -> Dict[str, Any]:
        """Calculate risk assessment metrics"""
        try:
            if len(returns) == 0:
                return self._get_default_risk_metrics()
            
            risk_metrics = {}
            
            # Volatility-based risk classification
            volatility = np.std(returns) * np.sqrt(252)
            
            if volatility < 0.15:
                risk_level = 'low'
                risk_score = 1
            elif volatility < 0.25:
                risk_level = 'medium'
                risk_score = 2
            elif volatility < 0.40:
                risk_level = 'high'
                risk_score = 3
            else:
                risk_level = 'very_high'
                risk_score = 4
            
            risk_metrics['risk_level'] = risk_level
            risk_metrics['risk_score'] = risk_score
            risk_metrics['volatility'] = float(volatility)
            
            # Beta calculation (simplified using SPY benchmark)
            market_volatility = 0.16  # SPY average volatility
            correlation = 0.75  # Assumed correlation (could be calculated)
            beta = volatility / market_volatility * correlation
            risk_metrics['beta'] = float(min(3.0, max(0.0, beta)))
            
            # Alpha calculation
            market_return = 0.10  # SPY average return
            risk_free_rate = 0.02
            annualized_return = (1 + np.prod(1 + returns) - 1) ** (252 / len(returns)) - 1
            expected_return = risk_free_rate + beta * (market_return - risk_free_rate)
            alpha = annualized_return - expected_return
            risk_metrics['alpha'] = float(alpha)
            
            # Skewness and Kurtosis
            risk_metrics['skewness'] = float(self._calculate_skewness(returns))
            risk_metrics['kurtosis'] = float(self._calculate_kurtosis(returns))
            
            # Tail risk measures
            risk_metrics['tail_ratio'] = float(abs(np.percentile(returns, 5)) / abs(np.percentile(returns, 95)))
            
            # Consistency metrics
            monthly_returns = self._get_monthly_returns(returns)
            if len(monthly_returns) > 1:
                risk_metrics['return_consistency'] = float(1.0 - np.std(monthly_returns) / abs(np.mean(monthly_returns)) 
                                                          if np.mean(monthly_returns) != 0 else 0.5)
            else:
                risk_metrics['return_consistency'] = 0.5
            
            return risk_metrics
            
        except Exception as e:
            self.logger.error("Error calculating risk metrics", error=str(e))
            return self._get_default_risk_metrics()
    
    async def _calculate_confidence(self, indicators: Dict[str, float], ml_scores: Dict[str, float]) -> float:
        """Calculate confidence level for analysis"""
        try:
            confidence_factors = []
            
            # Technical indicators confidence
            rsi = indicators.get('rsi', 50.0)
            if 20 <= rsi <= 80:  # RSI in reasonable range
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.6)
            
            # Volume confirmation
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if 0.5 <= volume_ratio <= 3.0:  # Volume in normal range
                volume_confidence = min(1.0, 0.5 + 0.5 * volume_ratio)
                confidence_factors.append(volume_confidence)
            else:
                confidence_factors.append(0.4)
            
            # ML model confidence
            if ml_scores:
                composite_score = ml_scores.get('composite_score', 0.5)
                # Distance from neutral (0.5) indicates confidence
                ml_confidence = 0.5 + abs(composite_score - 0.5)
                confidence_factors.append(ml_confidence)
            else:
                confidence_factors.append(0.3)
            
            # Trend consistency
            trend_strength = indicators.get('trend_strength', 0.0)
            macd = indicators.get('macd', 0.0)
            macd_signal = indicators.get('macd_signal', 0.0)
            
            # Check if MACD and trend agree
            macd_trend = 1 if macd > macd_signal else -1
            trend_direction = 1 if trend_strength > 0 else -1
            
            if macd_trend == trend_direction:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.4)
            
            # Price position confidence
            current_price = indicators.get('current_price', 100.0)
            bb_upper = indicators.get('bb_upper', 110.0)
            bb_lower = indicators.get('bb_lower', 90.0)
            
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
            
            # Confidence higher when price is not at extremes
            if 0.2 <= bb_position <= 0.8:
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.5)
            
            # Calculate weighted average
            weights = [0.2, 0.2, 0.25, 0.2, 0.15]
            confidence = sum(w * f for w, f in zip(weights, confidence_factors))
            
            return round(max(0.1, min(1.0, confidence)), 3)
            
        except Exception as e:
            self.logger.error("Error calculating confidence", error=str(e))
            return 0.5
    
    def _generate_confidence_breakdown(self, indicators: Dict[str, float], ml_scores: Dict[str, float]) -> Dict[str, Any]:
        """Generate detailed confidence breakdown"""
        try:
            breakdown = {
                'technical_indicators': 0.0,
                'volume_analysis': 0.0,
                'ml_models': 0.0,
                'trend_consistency': 0.0,
                'price_position': 0.0,
                'explanations': []
            }
            
            # Technical indicators score
            rsi = indicators.get('rsi', 50.0)
            if 20 <= rsi <= 80:
                breakdown['technical_indicators'] = 0.8
                breakdown['explanations'].append('RSI in normal range')
            else:
                breakdown['technical_indicators'] = 0.6
                breakdown['explanations'].append('RSI at extreme levels')
            
            # Volume analysis
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:
                breakdown['volume_analysis'] = 0.9
                breakdown['explanations'].append('High volume confirms signal')
            elif volume_ratio > 0.8:
                breakdown['volume_analysis'] = 0.7
                breakdown['explanations'].append('Normal volume')
            else:
                breakdown['volume_analysis'] = 0.4
                breakdown['explanations'].append('Low volume reduces confidence')
            
            # ML models score
            if ml_scores and 'composite_score' in ml_scores:
                composite_score = ml_scores['composite_score']
                if composite_score > 0.7 or composite_score < 0.3:
                    breakdown['ml_models'] = 0.8
                    breakdown['explanations'].append('ML models show strong signal')
                else:
                    breakdown['ml_models'] = 0.5
                    breakdown['explanations'].append('ML models show neutral signal')
            else:
                breakdown['ml_models'] = 0.3
                breakdown['explanations'].append('ML models not available')
            
            return breakdown
            
        except Exception as e:
            self.logger.error("Error generating confidence breakdown", error=str(e))
            return {
                'technical_indicators': 0.5,
                'volume_analysis': 0.5,
                'ml_models': 0.5,
                'trend_consistency': 0.5,
                'price_position': 0.5,
                'explanations': ['Error in confidence calculation']
            }
    
    def _calculate_skewness(self, returns: np.ndarray) -> float:
        """Calculate skewness of returns"""
        try:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            if std_return == 0:
                return 0.0
            
            skewness = np.mean(((returns - mean_return) / std_return) ** 3)
            return skewness
        except:
            return 0.0
    
    def _calculate_kurtosis(self, returns: np.ndarray) -> float:
        """Calculate kurtosis of returns"""
        try:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            if std_return == 0:
                return 0.0
            
            kurtosis = np.mean(((returns - mean_return) / std_return) ** 4) - 3
            return kurtosis
        except:
            return 0.0
    
    def _get_monthly_returns(self, daily_returns: np.ndarray) -> np.ndarray:
        """Convert daily returns to monthly returns"""
        try:
            # Approximate monthly returns (every 21 trading days)
            monthly_returns = []
            for i in range(0, len(daily_returns), 21):
                month_returns = daily_returns[i:i+21]
                if len(month_returns) > 0:
                    monthly_return = np.prod(1 + month_returns) - 1
                    monthly_returns.append(monthly_return)
            
            return np.array(monthly_returns)
        except:
            return np.array([])
    
    async def _compare_to_benchmark(self, performance_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Compare performance to benchmark"""
        try:
            comparison = {}
            
            # Compare key metrics to benchmark
            comparison['return_vs_benchmark'] = performance_metrics.get('annualized_return', 0.0) - self.benchmark_data['annual_return']
            comparison['volatility_vs_benchmark'] = performance_metrics.get('annualized_volatility', 0.0) - self.benchmark_data['volatility']
            comparison['sharpe_vs_benchmark'] = performance_metrics.get('sharpe_ratio', 0.0) - self.benchmark_data['sharpe_ratio']
            
            # Performance rating
            if comparison['return_vs_benchmark'] > 0.05:  # 5% outperformance
                comparison['performance_rating'] = 'excellent'
            elif comparison['return_vs_benchmark'] > 0.02:  # 2% outperformance
                comparison['performance_rating'] = 'good'
            elif comparison['return_vs_benchmark'] > -0.02:  # Within 2%
                comparison['performance_rating'] = 'market'
            else:
                comparison['performance_rating'] = 'underperform'
            
            return comparison
            
        except Exception as e:
            self.logger.error("Error comparing to benchmark", error=str(e))
            return {
                'return_vs_benchmark': 0.0,
                'volatility_vs_benchmark': 0.0,
                'sharpe_vs_benchmark': 0.0,
                'performance_rating': 'unknown'
            }
    
    def _get_default_performance_metrics(self) -> Dict[str, float]:
        """Return default performance metrics when calculation fails"""
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'daily_volatility': 0.02,
            'annualized_volatility': 0.20,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.1,
            'value_at_risk_95': -0.03,
            'win_rate': 0.5,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0
        }
    
    def _get_default_risk_metrics(self) -> Dict[str, Any]:
        """Return default risk metrics when calculation fails"""
        return {
            'risk_level': 'medium',
            'risk_score': 2,
            'volatility': 0.20,
            'beta': 1.0,
            'alpha': 0.0,
            'skewness': 0.0,
            'kurtosis': 0.0,
            'tail_ratio': 1.0,
            'return_consistency': 0.5
        }
    
    async def _handle_trading_event(self, event):
        """Handle trading state changed events"""
        try:
            self.logger.debug("Received trading event")
            # Clear performance cache on trading events
            self.performance_cache.clear()
        except Exception as e:
            self.logger.error("Error handling trading event", error=str(e))
    
    async def _handle_portfolio_event(self, event):
        """Handle portfolio state changed events"""
        try:
            self.logger.debug("Received portfolio event")
            # Update performance tracking
        except Exception as e:
            self.logger.error("Error handling portfolio event", error=str(e))
    
    async def _handle_analysis_event(self, event):
        """Handle analysis state changed events"""
        try:
            self.logger.debug("Received analysis event")
            # Performance module can react to analysis updates
        except Exception as e:
            self.logger.error("Error handling analysis event", error=str(e))