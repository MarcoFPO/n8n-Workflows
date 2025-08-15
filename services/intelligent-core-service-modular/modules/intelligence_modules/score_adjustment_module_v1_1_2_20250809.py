"""
Score Adjustment Module - Single Function Module
Adjusts ML scores with technical analysis indicators
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

try:
    from shared.common_imports import datetime, Dict, Any, structlog
    from shared.single_function_module_base import SingleFunctionModuleBase
except ImportError:
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


class ScoreAdjustmentModule(SingleFunctionModuleBase):
    """Adjust ML scores with technical analysis for more accurate predictions"""
    
    def __init__(self, event_bus):
        super().__init__("score_adjustment", event_bus)
        self.adjustment_weights = {
            'rsi_weight': 0.15,
            'macd_weight': 0.10,
            'moving_average_weight': 0.10,
            'volume_weight': 0.05,
            'volatility_weight': 0.05,
            'trend_weight': 0.05
        }
        self.adjustment_rules = {
            'max_adjustment': 0.3,  # Maximum adjustment ±30%
            'min_confidence': 0.1,   # Minimum confidence for adjustments
            'extreme_rsi_threshold': 80,  # RSI levels for extreme adjustments
            'high_volatility_threshold': 0.4,  # High volatility threshold
            'strong_trend_threshold': 0.6  # Strong trend threshold
        }
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('score.adjustment.request', self.process_event)
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
                'adjustment_weights': self.adjustment_weights,
                'adjustment_rules': self.adjustment_rules,
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'score.adjustment.request':
            base_score = event.get('base_score', 0.5)
            indicators = event.get('indicators', {})
            confidence = event.get('confidence', 0.5)
            
            adjustment_result = await self.adjust_score_with_technical_analysis(
                base_score, indicators, confidence
            )
            
            response_event = {
                'event_type': 'score.adjustment.response',
                'original_score': base_score,
                'adjusted_score': adjustment_result['adjusted_score'],
                'total_adjustment': adjustment_result['total_adjustment'],
                'adjustment_components': adjustment_result['adjustment_components'],
                'adjustment_reasoning': adjustment_result['adjustment_reasoning'],
                'confidence_factor': adjustment_result['confidence_factor'],
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def adjust_score_with_technical_analysis(self, base_score: float, indicators: Dict[str, float], confidence: float = 0.5) -> Dict[str, Any]:
        """Adjust ML score with comprehensive technical analysis"""
        try:
            # Initialize adjustment tracking
            adjustment_components = {}
            adjustment_reasoning = []
            total_adjustment = 0.0
            
            # Apply confidence factor to limit adjustments for low-confidence predictions
            confidence_factor = max(self.adjustment_rules['min_confidence'], confidence)
            
            # 1. RSI Adjustment
            rsi_adjustment = await self._calculate_rsi_adjustment(indicators, confidence_factor)
            adjustment_components['rsi'] = rsi_adjustment
            total_adjustment += rsi_adjustment['value']
            if rsi_adjustment['reasoning']:
                adjustment_reasoning.append(rsi_adjustment['reasoning'])
            
            # 2. MACD Adjustment
            macd_adjustment = await self._calculate_macd_adjustment(indicators, confidence_factor)
            adjustment_components['macd'] = macd_adjustment
            total_adjustment += macd_adjustment['value']
            if macd_adjustment['reasoning']:
                adjustment_reasoning.append(macd_adjustment['reasoning'])
            
            # 3. Moving Average Adjustment
            ma_adjustment = await self._calculate_moving_average_adjustment(indicators, confidence_factor)
            adjustment_components['moving_averages'] = ma_adjustment
            total_adjustment += ma_adjustment['value']
            if ma_adjustment['reasoning']:
                adjustment_reasoning.append(ma_adjustment['reasoning'])
            
            # 4. Volume Confirmation Adjustment
            volume_adjustment = await self._calculate_volume_adjustment(indicators, confidence_factor, base_score)
            adjustment_components['volume'] = volume_adjustment
            total_adjustment += volume_adjustment['value']
            if volume_adjustment['reasoning']:
                adjustment_reasoning.append(volume_adjustment['reasoning'])
            
            # 5. Volatility Adjustment
            volatility_adjustment = await self._calculate_volatility_adjustment(indicators, confidence_factor, base_score)
            adjustment_components['volatility'] = volatility_adjustment
            total_adjustment += volatility_adjustment['value']
            if volatility_adjustment['reasoning']:
                adjustment_reasoning.append(volatility_adjustment['reasoning'])
            
            # 6. Trend Strength Adjustment
            trend_adjustment = await self._calculate_trend_adjustment(indicators, confidence_factor, base_score)
            adjustment_components['trend'] = trend_adjustment
            total_adjustment += trend_adjustment['value']
            if trend_adjustment['reasoning']:
                adjustment_reasoning.append(trend_adjustment['reasoning'])
            
            # Apply maximum adjustment limit
            capped_adjustment = max(-self.adjustment_rules['max_adjustment'], 
                                  min(self.adjustment_rules['max_adjustment'], total_adjustment))
            
            # Calculate final adjusted score
            adjusted_score = base_score + capped_adjustment
            adjusted_score = max(0.0, min(1.0, adjusted_score))  # Ensure valid range
            
            # Add capping reasoning if adjustment was limited
            if abs(total_adjustment) > self.adjustment_rules['max_adjustment']:
                adjustment_reasoning.append(f"Total adjustment capped at ±{self.adjustment_rules['max_adjustment']:.1%}")
            
            self.logger.debug("Score adjustment completed successfully",
                            original_score=base_score,
                            adjusted_score=adjusted_score,
                            total_adjustment=capped_adjustment,
                            confidence_factor=confidence_factor)
            
            return {
                'adjusted_score': float(adjusted_score),
                'total_adjustment': float(capped_adjustment),
                'raw_adjustment': float(total_adjustment),
                'adjustment_components': adjustment_components,
                'adjustment_reasoning': adjustment_reasoning,
                'confidence_factor': float(confidence_factor),
                'adjustment_capped': abs(total_adjustment) > self.adjustment_rules['max_adjustment']
            }
            
        except Exception as e:
            self.logger.error("Error adjusting score with technical analysis", error=str(e))
            return {
                'adjusted_score': base_score,
                'total_adjustment': 0.0,
                'raw_adjustment': 0.0,
                'adjustment_components': {},
                'adjustment_reasoning': [f"Adjustment error: {str(e)}"],
                'confidence_factor': confidence,
                'adjustment_capped': False
            }
    
    async def _calculate_rsi_adjustment(self, indicators: Dict[str, float], confidence_factor: float) -> Dict[str, Any]:
        """Calculate RSI-based score adjustment"""
        try:
            rsi = indicators.get('rsi', 50.0)
            adjustment = 0.0
            reasoning = ""
            
            # Extreme RSI conditions
            if rsi >= self.adjustment_rules['extreme_rsi_threshold']:
                # Overbought - negative adjustment
                extreme_factor = min(1.0, (rsi - 70) / 10)  # Scale 0-1 for RSI 70-80+
                adjustment = -self.adjustment_weights['rsi_weight'] * extreme_factor * confidence_factor
                reasoning = f"RSI overbought ({rsi:.1f}) suggests downward pressure"
                
            elif rsi <= (100 - self.adjustment_rules['extreme_rsi_threshold']):
                # Oversold - positive adjustment  
                extreme_factor = min(1.0, (30 - rsi) / 10)  # Scale 0-1 for RSI 20-30
                adjustment = self.adjustment_weights['rsi_weight'] * extreme_factor * confidence_factor
                reasoning = f"RSI oversold ({rsi:.1f}) suggests upward potential"
                
            # Moderate RSI adjustments
            elif rsi > 60:
                moderate_factor = (rsi - 60) / 10  # Scale 0-1 for RSI 60-70
                adjustment = -self.adjustment_weights['rsi_weight'] * 0.5 * moderate_factor * confidence_factor
                reasoning = f"RSI elevated ({rsi:.1f}) suggests caution"
                
            elif rsi < 40:
                moderate_factor = (40 - rsi) / 10  # Scale 0-1 for RSI 30-40
                adjustment = self.adjustment_weights['rsi_weight'] * 0.5 * moderate_factor * confidence_factor
                reasoning = f"RSI depressed ({rsi:.1f}) suggests opportunity"
            
            return {
                'value': adjustment,
                'reasoning': reasoning,
                'rsi_level': rsi,
                'extreme_condition': rsi >= 80 or rsi <= 20
            }
            
        except Exception as e:
            self.logger.error("Error calculating RSI adjustment", error=str(e))
            return {'value': 0.0, 'reasoning': "", 'rsi_level': 50.0, 'extreme_condition': False}
    
    async def _calculate_macd_adjustment(self, indicators: Dict[str, float], confidence_factor: float) -> Dict[str, Any]:
        """Calculate MACD-based score adjustment"""
        try:
            macd = indicators.get('macd', 0.0)
            macd_signal = indicators.get('macd_signal', 0.0)
            macd_histogram = indicators.get('macd_histogram', 0.0)
            
            adjustment = 0.0
            reasoning = ""
            
            # MACD crossover signals
            if macd > macd_signal and macd > 0:
                # Bullish MACD above zero line
                strength = min(1.0, abs(macd - macd_signal) / max(abs(macd), 0.001))
                adjustment = self.adjustment_weights['macd_weight'] * strength * confidence_factor
                reasoning = f"MACD bullish crossover above zero ({macd:.3f})"
                
            elif macd < macd_signal and macd < 0:
                # Bearish MACD below zero line
                strength = min(1.0, abs(macd - macd_signal) / max(abs(macd), 0.001))
                adjustment = -self.adjustment_weights['macd_weight'] * strength * confidence_factor
                reasoning = f"MACD bearish crossover below zero ({macd:.3f})"
                
            elif macd > macd_signal:
                # Bullish crossover but below zero - weaker signal
                strength = min(1.0, abs(macd - macd_signal) / max(abs(macd), 0.001))
                adjustment = self.adjustment_weights['macd_weight'] * 0.5 * strength * confidence_factor
                reasoning = f"MACD bullish crossover below zero ({macd:.3f})"
                
            elif macd < macd_signal:
                # Bearish crossover but above zero - weaker signal
                strength = min(1.0, abs(macd - macd_signal) / max(abs(macd), 0.001))
                adjustment = -self.adjustment_weights['macd_weight'] * 0.5 * strength * confidence_factor
                reasoning = f"MACD bearish crossover above zero ({macd:.3f})"
            
            # Histogram momentum confirmation
            if macd_histogram != 0:
                histogram_factor = min(0.02, abs(macd_histogram) * 0.1)  # Small additional factor
                if (adjustment > 0 and macd_histogram > 0) or (adjustment < 0 and macd_histogram < 0):
                    adjustment *= (1 + histogram_factor)  # Amplify if histogram confirms
                    if reasoning:
                        reasoning += " (histogram confirms)"
            
            return {
                'value': adjustment,
                'reasoning': reasoning,
                'macd_value': macd,
                'macd_signal': macd_signal,
                'crossover_strength': abs(macd - macd_signal)
            }
            
        except Exception as e:
            self.logger.error("Error calculating MACD adjustment", error=str(e))
            return {'value': 0.0, 'reasoning': "", 'macd_value': 0.0, 'macd_signal': 0.0, 'crossover_strength': 0.0}
    
    async def _calculate_moving_average_adjustment(self, indicators: Dict[str, float], confidence_factor: float) -> Dict[str, Any]:
        """Calculate moving average-based score adjustment"""
        try:
            current_price = indicators.get('current_price', 100.0)
            sma_20 = indicators.get('sma_20', current_price)
            sma_50 = indicators.get('sma_50', current_price)
            ema_12 = indicators.get('ema_12', current_price)
            
            adjustment = 0.0
            reasoning = ""
            
            # Price position relative to moving averages
            price_above_sma20 = current_price > sma_20
            price_above_sma50 = current_price > sma_50
            sma20_above_sma50 = sma_20 > sma_50
            
            # Strong uptrend: Price > SMA20 > SMA50
            if price_above_sma20 and price_above_sma50 and sma20_above_sma50:
                strength = min(1.0, ((current_price - sma_50) / sma_50))
                adjustment = self.adjustment_weights['moving_average_weight'] * strength * confidence_factor
                reasoning = f"Strong uptrend: Price above both MAs (${current_price:.2f} > ${sma_20:.2f} > ${sma_50:.2f})"
                
            # Strong downtrend: Price < SMA20 < SMA50
            elif not price_above_sma20 and not price_above_sma50 and not sma20_above_sma50:
                strength = min(1.0, ((sma_50 - current_price) / sma_50))
                adjustment = -self.adjustment_weights['moving_average_weight'] * strength * confidence_factor
                reasoning = f"Strong downtrend: Price below both MAs (${current_price:.2f} < ${sma_20:.2f} < ${sma_50:.2f})"
                
            # Partial trend signals
            elif price_above_sma20 and not sma20_above_sma50:
                # Price above short MA but long-term trend bearish
                strength = min(0.5, ((current_price - sma_20) / sma_20))
                adjustment = self.adjustment_weights['moving_average_weight'] * 0.3 * strength * confidence_factor
                reasoning = f"Mixed signals: Price above SMA20 but SMA20 < SMA50"
                
            elif not price_above_sma20 and sma20_above_sma50:
                # Price below short MA but long-term trend bullish
                strength = min(0.5, ((sma_20 - current_price) / sma_20))
                adjustment = -self.adjustment_weights['moving_average_weight'] * 0.3 * strength * confidence_factor
                reasoning = f"Mixed signals: Price below SMA20 but SMA20 > SMA50"
            
            # EMA confirmation
            if ema_12 != current_price:
                ema_factor = (current_price - ema_12) / ema_12
                if (adjustment > 0 and ema_factor > 0) or (adjustment < 0 and ema_factor < 0):
                    adjustment *= 1.1  # Small boost if EMA confirms trend
                    if reasoning:
                        reasoning += " (EMA confirms)"
            
            return {
                'value': adjustment,
                'reasoning': reasoning,
                'price_above_sma20': price_above_sma20,
                'price_above_sma50': price_above_sma50,
                'trend_alignment': price_above_sma20 and price_above_sma50 and sma20_above_sma50
            }
            
        except Exception as e:
            self.logger.error("Error calculating moving average adjustment", error=str(e))
            return {'value': 0.0, 'reasoning': "", 'price_above_sma20': False, 'price_above_sma50': False, 'trend_alignment': False}
    
    async def _calculate_volume_adjustment(self, indicators: Dict[str, float], confidence_factor: float, base_score: float) -> Dict[str, Any]:
        """Calculate volume-based score adjustment"""
        try:
            volume_ratio = indicators.get('volume_ratio', 1.0)
            price_volume_correlation = indicators.get('price_volume_correlation', 0.0)
            
            adjustment = 0.0
            reasoning = ""
            
            # High volume confirmation
            if volume_ratio > 1.5:
                # High volume - amplify signal if volume confirms price movement
                if abs(price_volume_correlation) > 0.3:
                    # Volume confirms price direction
                    volume_strength = min(1.0, (volume_ratio - 1.0))
                    correlation_strength = abs(price_volume_correlation)
                    
                    if base_score > 0.5:  # Bullish score
                        adjustment = self.adjustment_weights['volume_weight'] * volume_strength * correlation_strength * confidence_factor
                        reasoning = f"High volume ({volume_ratio:.1f}x) confirms bullish signal"
                    elif base_score < 0.5:  # Bearish score  
                        adjustment = -self.adjustment_weights['volume_weight'] * volume_strength * correlation_strength * confidence_factor
                        reasoning = f"High volume ({volume_ratio:.1f}x) confirms bearish signal"
                else:
                    # High volume but no clear correlation - caution
                    adjustment = -self.adjustment_weights['volume_weight'] * 0.3 * confidence_factor
                    reasoning = f"High volume ({volume_ratio:.1f}x) without price correlation suggests uncertainty"
            
            # Low volume - reduce signal strength
            elif volume_ratio < 0.5:
                volume_weakness = min(0.5, (0.8 - volume_ratio))
                if base_score != 0.5:  # Any directional signal
                    adjustment = -(abs(base_score - 0.5)) * self.adjustment_weights['volume_weight'] * volume_weakness * confidence_factor
                    reasoning = f"Low volume ({volume_ratio:.1f}x) weakens price signal reliability"
            
            return {
                'value': adjustment,
                'reasoning': reasoning,
                'volume_ratio': volume_ratio,
                'price_volume_correlation': price_volume_correlation,
                'high_volume': volume_ratio > 1.5,
                'low_volume': volume_ratio < 0.5
            }
            
        except Exception as e:
            self.logger.error("Error calculating volume adjustment", error=str(e))
            return {'value': 0.0, 'reasoning': "", 'volume_ratio': 1.0, 'price_volume_correlation': 0.0, 'high_volume': False, 'low_volume': False}
    
    async def _calculate_volatility_adjustment(self, indicators: Dict[str, float], confidence_factor: float, base_score: float) -> Dict[str, Any]:
        """Calculate volatility-based score adjustment"""
        try:
            volatility = indicators.get('volatility', 0.2)
            atr_percentage = indicators.get('atr_percentage', 0.0)
            
            adjustment = 0.0
            reasoning = ""
            
            # High volatility adjustment
            if volatility > self.adjustment_rules['high_volatility_threshold']:
                # High volatility reduces confidence in extreme positions
                volatility_factor = min(1.0, (volatility - 0.2) / 0.3)  # Scale from 0.2-0.5 volatility
                
                if abs(base_score - 0.5) > 0.3:  # Strong directional signals
                    # Reduce extreme positions in high volatility
                    adjustment = -(abs(base_score - 0.5)) * self.adjustment_weights['volatility_weight'] * volatility_factor * confidence_factor
                    reasoning = f"High volatility ({volatility:.1%}) reduces confidence in extreme positions"
                
            # Low volatility - signals may be more reliable
            elif volatility < 0.15:
                # Low volatility may indicate trend continuation
                volatility_factor = (0.15 - volatility) / 0.10
                if abs(base_score - 0.5) > 0.1:  # Any directional signal
                    direction = 1 if base_score > 0.5 else -1
                    adjustment = direction * self.adjustment_weights['volatility_weight'] * volatility_factor * confidence_factor * 0.5
                    reasoning = f"Low volatility ({volatility:.1%}) increases signal reliability"
            
            # ATR confirmation
            if atr_percentage > 0:
                if atr_percentage > 5.0:  # High ATR suggests high volatility
                    if adjustment == 0:  # No volatility adjustment yet
                        adjustment = -abs(base_score - 0.5) * 0.02 * confidence_factor
                        reasoning = f"High ATR ({atr_percentage:.1%}) suggests increased risk"
            
            return {
                'value': adjustment,
                'reasoning': reasoning,
                'volatility_level': volatility,
                'atr_percentage': atr_percentage,
                'high_volatility': volatility > self.adjustment_rules['high_volatility_threshold'],
                'low_volatility': volatility < 0.15
            }
            
        except Exception as e:
            self.logger.error("Error calculating volatility adjustment", error=str(e))
            return {'value': 0.0, 'reasoning': "", 'volatility_level': 0.2, 'atr_percentage': 0.0, 'high_volatility': False, 'low_volatility': False}
    
    async def _calculate_trend_adjustment(self, indicators: Dict[str, float], confidence_factor: float, base_score: float) -> Dict[str, Any]:
        """Calculate trend strength-based score adjustment"""
        try:
            trend_strength = indicators.get('trend_strength', 0.0)
            trend_direction = indicators.get('trend_direction', 'neutral')
            trend_momentum = indicators.get('trend_momentum', 0.0)
            
            adjustment = 0.0
            reasoning = ""
            
            # Strong trend adjustment
            if trend_strength > self.adjustment_rules['strong_trend_threshold']:
                trend_factor = min(1.0, trend_strength)
                
                if trend_direction == 'bullish' and base_score > 0.5:
                    # Strong uptrend confirms bullish signal
                    adjustment = self.adjustment_weights['trend_weight'] * trend_factor * confidence_factor
                    reasoning = f"Strong uptrend ({trend_strength:.2f}) supports bullish outlook"
                    
                elif trend_direction == 'bearish' and base_score < 0.5:
                    # Strong downtrend confirms bearish signal
                    adjustment = -self.adjustment_weights['trend_weight'] * trend_factor * confidence_factor
                    reasoning = f"Strong downtrend ({trend_strength:.2f}) supports bearish outlook"
                    
                elif (trend_direction == 'bullish' and base_score < 0.5) or (trend_direction == 'bearish' and base_score > 0.5):
                    # Strong trend contradicts ML signal - caution
                    adjustment = -abs(base_score - 0.5) * self.adjustment_weights['trend_weight'] * 0.5 * confidence_factor
                    reasoning = f"Strong {trend_direction} trend conflicts with ML signal"
            
            # Momentum confirmation
            if abs(trend_momentum) > 0.3:
                momentum_factor = min(0.5, abs(trend_momentum))
                if (trend_momentum > 0 and adjustment > 0) or (trend_momentum < 0 and adjustment < 0):
                    adjustment *= (1 + momentum_factor * 0.2)  # Small boost for momentum confirmation
                    if reasoning:
                        reasoning += " (momentum confirms)"
            
            return {
                'value': adjustment,
                'reasoning': reasoning,
                'trend_strength': trend_strength,
                'trend_direction': trend_direction,
                'trend_momentum': trend_momentum,
                'strong_trend': trend_strength > self.adjustment_rules['strong_trend_threshold']
            }
            
        except Exception as e:
            self.logger.error("Error calculating trend adjustment", error=str(e))
            return {'value': 0.0, 'reasoning': "", 'trend_strength': 0.0, 'trend_direction': 'neutral', 'trend_momentum': 0.0, 'strong_trend': False}
    
    def update_adjustment_weights(self, new_weights: Dict[str, float]) -> bool:
        """Update adjustment weights"""
        try:
            valid_weights = set(self.adjustment_weights.keys())
            
            for weight_name, weight_value in new_weights.items():
                if weight_name in valid_weights and 0.0 <= weight_value <= 1.0:
                    self.adjustment_weights[weight_name] = weight_value
                    self.logger.info("Updated adjustment weight", weight=weight_name, value=weight_value)
                else:
                    self.logger.warning("Invalid adjustment weight", weight=weight_name, value=weight_value)
            
            return True
            
        except Exception as e:
            self.logger.error("Error updating adjustment weights", error=str(e))
            return False
    
    def update_adjustment_rules(self, new_rules: Dict[str, float]) -> bool:
        """Update adjustment rules"""
        try:
            valid_rules = set(self.adjustment_rules.keys())
            
            for rule_name, rule_value in new_rules.items():
                if rule_name in valid_rules and rule_value >= 0:
                    self.adjustment_rules[rule_name] = rule_value
                    self.logger.info("Updated adjustment rule", rule=rule_name, value=rule_value)
                else:
                    self.logger.warning("Invalid adjustment rule", rule=rule_name, value=rule_value)
            
            return True
            
        except Exception as e:
            self.logger.error("Error updating adjustment rules", error=str(e))
            return False
    
    def get_adjustment_analysis(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Analyze potential adjustments without applying them"""
        try:
            analysis = {
                'rsi_analysis': {},
                'macd_analysis': {},
                'moving_average_analysis': {},
                'volume_analysis': {},
                'volatility_analysis': {},
                'trend_analysis': {},
                'overall_assessment': {}
            }
            
            # RSI analysis
            rsi = indicators.get('rsi', 50.0)
            if rsi >= 70:
                analysis['rsi_analysis'] = {'condition': 'overbought', 'level': rsi, 'impact': 'negative'}
            elif rsi <= 30:
                analysis['rsi_analysis'] = {'condition': 'oversold', 'level': rsi, 'impact': 'positive'}
            else:
                analysis['rsi_analysis'] = {'condition': 'neutral', 'level': rsi, 'impact': 'minimal'}
            
            # MACD analysis
            macd = indicators.get('macd', 0.0)
            macd_signal = indicators.get('macd_signal', 0.0)
            if macd > macd_signal:
                analysis['macd_analysis'] = {'condition': 'bullish_crossover', 'strength': abs(macd - macd_signal), 'impact': 'positive'}
            elif macd < macd_signal:
                analysis['macd_analysis'] = {'condition': 'bearish_crossover', 'strength': abs(macd - macd_signal), 'impact': 'negative'}
            else:
                analysis['macd_analysis'] = {'condition': 'neutral', 'strength': 0, 'impact': 'minimal'}
            
            # Volume analysis
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:
                analysis['volume_analysis'] = {'condition': 'high_volume', 'ratio': volume_ratio, 'impact': 'amplifies_signal'}
            elif volume_ratio < 0.5:
                analysis['volume_analysis'] = {'condition': 'low_volume', 'ratio': volume_ratio, 'impact': 'weakens_signal'}
            else:
                analysis['volume_analysis'] = {'condition': 'normal_volume', 'ratio': volume_ratio, 'impact': 'neutral'}
            
            # Overall assessment
            total_positive_indicators = sum(1 for a in analysis.values() if isinstance(a, dict) and a.get('impact') == 'positive')
            total_negative_indicators = sum(1 for a in analysis.values() if isinstance(a, dict) and a.get('impact') == 'negative')
            
            if total_positive_indicators > total_negative_indicators:
                analysis['overall_assessment'] = {'bias': 'positive', 'strength': total_positive_indicators - total_negative_indicators}
            elif total_negative_indicators > total_positive_indicators:
                analysis['overall_assessment'] = {'bias': 'negative', 'strength': total_negative_indicators - total_positive_indicators}
            else:
                analysis['overall_assessment'] = {'bias': 'neutral', 'strength': 0}
            
            return analysis
            
        except Exception as e:
            self.logger.error("Error performing adjustment analysis", error=str(e))
            return {'error': str(e)}
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'score_adjustment',
            'adjustment_weights': self.adjustment_weights.copy(),
            'adjustment_rules': self.adjustment_rules.copy(),
            'supported_indicators': [
                'rsi', 'macd', 'macd_signal', 'macd_histogram',
                'sma_20', 'sma_50', 'ema_12', 'current_price',
                'volume_ratio', 'price_volume_correlation',
                'volatility', 'atr_percentage',
                'trend_strength', 'trend_direction', 'trend_momentum'
            ],
            'features': [
                'rsi_extremes_detection',
                'macd_crossover_analysis',
                'moving_average_trend_analysis',
                'volume_confirmation',
                'volatility_risk_adjustment',
                'trend_strength_confirmation',
                'confidence_based_scaling',
                'maximum_adjustment_capping'
            ],
            'description': 'Adjusts ML scores using comprehensive technical analysis indicators with confidence-based scaling'
        }