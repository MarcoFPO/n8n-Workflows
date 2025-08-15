"""
Action Priority Calculation Module - Single Function Module
Calculates action priority, timing, and urgency for trading decisions
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

try:
    from shared.common_imports import datetime, Dict, Any, List, structlog
    from shared.single_function_module_base import SingleFunctionModuleBase
except ImportError:
    from datetime import datetime
    from typing import Dict, Any, List
    
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


class ActionPriorityCalculationModule(SingleFunctionModuleBase):
    """Calculate action priority, timing, and urgency for investment decisions"""
    
    def __init__(self, event_bus):
        super().__init__("action_priority_calculation", event_bus)
        self.priority_weights = {
            'recommendation_strength': 0.25,  # How strong the recommendation is
            'confidence_level': 0.20,        # Model confidence
            'market_conditions': 0.15,       # Current market environment
            'volatility_factor': 0.15,       # Volatility considerations
            'technical_signals': 0.15,       # Technical analysis urgency
            'time_sensitivity': 0.10         # Time-based factors
        }
        self.priority_levels = {
            'critical': {'min_score': 8.0, 'description': 'Immediate action required'},
            'high': {'min_score': 6.5, 'description': 'Action needed within hours'},
            'medium': {'min_score': 4.5, 'description': 'Action needed within days'},
            'low': {'min_score': 2.5, 'description': 'Action can wait'},
            'very_low': {'min_score': 0.0, 'description': 'No immediate action needed'}
        }
        self.urgency_factors = {
            'immediate': 'Within 15 minutes',
            'very_high': 'Within 1 hour',
            'high': 'Within 4 hours',
            'medium': 'Within 1 day',
            'low': 'Within 3 days',
            'very_low': 'No specific timeline'
        }
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('action.priority.calculation.request', self.process_event)
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
                'priority_weights': self.priority_weights,
                'priority_levels_count': len(self.priority_levels),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'action.priority.calculation.request':
            recommendation = event.get('recommendation', 'HOLD')
            confidence = event.get('confidence', 0.5)
            indicators = event.get('indicators', {})
            symbol = event.get('symbol', 'UNKNOWN')
            ml_scores = event.get('ml_scores', {})
            risk_assessment = event.get('risk_assessment', {})
            
            priority_result = await self.calculate_action_priority(
                recommendation, confidence, indicators, symbol, ml_scores, risk_assessment
            )
            
            response_event = {
                'event_type': 'action.priority.calculation.response',
                'action_priority': priority_result,
                'symbol': symbol,
                'recommendation': recommendation,
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def calculate_action_priority(self, recommendation: str, confidence: float, 
                                      indicators: Dict[str, float], symbol: str = "UNKNOWN",
                                      ml_scores: Dict[str, float] = None, 
                                      risk_assessment: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calculate comprehensive action priority and timing"""
        try:
            if ml_scores is None:
                ml_scores = {}
            if risk_assessment is None:
                risk_assessment = {}
            
            priority_result = {
                'priority_level': 'medium',
                'priority_score': 5.0,
                'urgency': 'medium',
                'timing': 'market_hours',
                'position_size': 'normal',
                'execution_strategy': 'standard',
                'priority_breakdown': {},
                'timing_analysis': {},
                'execution_recommendations': [],
                'monitoring_schedule': {},
                'risk_considerations': [],
                'market_timing_factors': {}
            }
            
            # Calculate individual priority components
            priority_components = {}
            
            # Recommendation Strength Component
            priority_components['recommendation_strength'] = await self._assess_recommendation_strength(
                recommendation, confidence
            )
            
            # Confidence Level Component
            priority_components['confidence_level'] = await self._assess_confidence_impact(
                confidence, ml_scores
            )
            
            # Market Conditions Component
            priority_components['market_conditions'] = await self._assess_market_conditions(
                indicators
            )
            
            # Volatility Factor Component
            priority_components['volatility_factor'] = await self._assess_volatility_impact(
                indicators, recommendation
            )
            
            # Technical Signals Component
            priority_components['technical_signals'] = await self._assess_technical_urgency(
                indicators, recommendation
            )
            
            # Time Sensitivity Component
            priority_components['time_sensitivity'] = await self._assess_time_sensitivity(
                indicators, recommendation
            )
            
            # Calculate composite priority score
            composite_score = await self._calculate_composite_priority_score(priority_components)
            
            # Determine priority level and urgency
            priority_level = await self._determine_priority_level(composite_score)
            urgency = await self._determine_urgency(composite_score, indicators, recommendation)
            
            # Generate detailed analysis
            timing_analysis = await self._analyze_timing_factors(indicators, composite_score)
            execution_strategy = await self._recommend_execution_strategy(
                composite_score, indicators, recommendation, risk_assessment
            )
            position_sizing = await self._calculate_position_sizing_priority(
                composite_score, confidence, risk_assessment
            )
            monitoring_schedule = await self._create_monitoring_schedule(
                priority_level, urgency, recommendation
            )
            
            # Update priority result
            priority_result.update({
                'priority_level': priority_level,
                'priority_score': composite_score,
                'urgency': urgency,
                'timing': timing_analysis.get('optimal_timing', 'market_hours'),
                'position_size': position_sizing['recommendation'],
                'execution_strategy': execution_strategy['strategy'],
                'priority_breakdown': priority_components,
                'timing_analysis': timing_analysis,
                'execution_recommendations': execution_strategy['recommendations'],
                'monitoring_schedule': monitoring_schedule,
                'risk_considerations': await self._identify_priority_risks(composite_score, indicators),
                'market_timing_factors': await self._analyze_market_timing_factors(indicators)
            })
            
            self.logger.debug("Action priority calculation completed",
                            symbol=symbol,
                            priority_level=priority_level,
                            priority_score=composite_score,
                            urgency=urgency)
            
            return priority_result
            
        except Exception as e:
            self.logger.error("Error calculating action priority", 
                            symbol=symbol,
                            recommendation=recommendation,
                            error=str(e))
            return {
                'priority_level': 'medium',
                'priority_score': 5.0,
                'urgency': 'medium',
                'timing': 'market_hours',
                'position_size': 'reduced',
                'execution_strategy': 'cautious',
                'priority_breakdown': {},
                'timing_analysis': {'error': str(e)},
                'execution_recommendations': ['Exercise caution due to calculation error'],
                'monitoring_schedule': {'immediate': 'Monitor closely due to error'},
                'risk_considerations': [f'Priority calculation error: {str(e)}'],
                'market_timing_factors': {'error': str(e)}
            }
    
    async def _assess_recommendation_strength(self, recommendation: str, confidence: float) -> Dict[str, Any]:
        """Assess the strength and priority impact of the recommendation"""
        try:
            component = {
                'score': 5.0,
                'factors': [],
                'impact_assessment': ''
            }
            
            # Base score by recommendation type
            if recommendation == 'STRONG_BUY':
                component['score'] = 8.5
                component['factors'].append("Strong Buy recommendation demands high priority")
                component['impact_assessment'] = "Very high impact - significant upside potential"
            elif recommendation == 'BUY':
                component['score'] = 7.0
                component['factors'].append("Buy recommendation suggests good opportunity")
                component['impact_assessment'] = "High impact - positive return potential"
            elif recommendation == 'STRONG_SELL':
                component['score'] = 8.0
                component['factors'].append("Strong Sell recommendation requires urgent action")
                component['impact_assessment'] = "Very high impact - significant downside protection"
            elif recommendation == 'SELL':
                component['score'] = 6.5
                component['factors'].append("Sell recommendation indicates risk management need")
                component['impact_assessment'] = "Medium-high impact - downside protection"
            else:  # HOLD
                component['score'] = 3.0
                component['factors'].append("Hold recommendation suggests no immediate action")
                component['impact_assessment'] = "Low impact - maintain current position"
            
            # Adjust for confidence
            if confidence > 0.8:
                component['score'] += 1.0
                component['factors'].append(f"Very high confidence ({confidence:.1%}) increases priority")
            elif confidence > 0.6:
                component['score'] += 0.5
                component['factors'].append(f"High confidence ({confidence:.1%}) supports priority")
            elif confidence < 0.4:
                component['score'] -= 1.0
                component['factors'].append(f"Low confidence ({confidence:.1%}) reduces priority")
            elif confidence < 0.5:
                component['score'] -= 0.5
                component['factors'].append(f"Moderate confidence ({confidence:.1%}) slightly reduces priority")
            
            # Ensure score bounds
            component['score'] = max(1.0, min(10.0, component['score']))
            
            return component
            
        except Exception as e:
            self.logger.error("Error assessing recommendation strength", error=str(e))
            return {'score': 5.0, 'factors': ['Assessment error'], 'impact_assessment': 'Error in assessment'}
    
    async def _assess_confidence_impact(self, confidence: float, ml_scores: Dict[str, float]) -> Dict[str, Any]:
        """Assess how confidence levels impact action priority"""
        try:
            component = {
                'score': 5.0,
                'factors': [],
                'confidence_analysis': ''
            }
            
            # Base confidence impact
            if confidence > 0.9:
                component['score'] = 9.0
                component['factors'].append("Exceptional confidence demands immediate attention")
                component['confidence_analysis'] = "Extremely high confidence suggests strong signal"
            elif confidence > 0.8:
                component['score'] = 7.5
                component['factors'].append("Very high confidence increases action priority")
                component['confidence_analysis'] = "Very strong confidence in prediction"
            elif confidence > 0.7:
                component['score'] = 6.5
                component['factors'].append("High confidence supports elevated priority")
                component['confidence_analysis'] = "Strong confidence supports action"
            elif confidence > 0.6:
                component['score'] = 5.5
                component['factors'].append("Good confidence level supports action")
                component['confidence_analysis'] = "Moderate confidence in recommendation"
            elif confidence < 0.3:
                component['score'] = 2.0
                component['factors'].append("Very low confidence suggests delaying action")
                component['confidence_analysis'] = "Low confidence reduces action priority"
            elif confidence < 0.5:
                component['score'] = 3.5
                component['factors'].append("Low confidence reduces action urgency")
                component['confidence_analysis'] = "Below-average confidence"
            
            # Model consensus factor
            if ml_scores and len(ml_scores) > 1:
                scores = [v for k, v in ml_scores.items() if k != 'composite_score']
                if scores:
                    score_variance = max(scores) - min(scores)
                    if score_variance < 0.15:
                        component['score'] += 0.5
                        component['factors'].append("Strong model consensus increases confidence priority")
                    elif score_variance > 0.4:
                        component['score'] -= 1.0
                        component['factors'].append("High model disagreement reduces confidence priority")
            
            component['score'] = max(1.0, min(10.0, component['score']))
            
            return component
            
        except Exception as e:
            self.logger.error("Error assessing confidence impact", error=str(e))
            return {'score': 5.0, 'factors': ['Assessment error'], 'confidence_analysis': 'Error in analysis'}
    
    async def _assess_market_conditions(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Assess current market conditions impact on action priority"""
        try:
            component = {
                'score': 5.0,
                'factors': [],
                'market_assessment': ''
            }
            
            # Volatility environment
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.4:
                component['score'] += 2.0
                component['factors'].append(f"High volatility ({volatility:.1%}) creates urgent market conditions")
                component['market_assessment'] = "High volatility environment demands quick action"
            elif volatility > 0.25:
                component['score'] += 1.0
                component['factors'].append(f"Elevated volatility ({volatility:.1%}) increases action priority")
                component['market_assessment'] = "Moderately volatile environment"
            elif volatility < 0.1:
                component['score'] -= 0.5
                component['factors'].append(f"Low volatility ({volatility:.1%}) allows patient execution")
                component['market_assessment'] = "Calm market environment allows patience"
            
            # Volume environment
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 2.5:
                component['score'] += 1.5
                component['factors'].append(f"Exceptional volume ({volume_ratio:.1f}x) signals market urgency")
            elif volume_ratio > 1.8:
                component['score'] += 1.0
                component['factors'].append(f"High volume ({volume_ratio:.1f}x) increases execution priority")
            elif volume_ratio < 0.4:
                component['score'] -= 1.0
                component['factors'].append(f"Low volume ({volume_ratio:.1f}x) reduces execution urgency")
            
            # Trend momentum
            trend_strength = indicators.get('trend_strength', 0.0)
            trend_momentum = indicators.get('trend_momentum', 0.0)
            
            if trend_strength > 0.7 and abs(trend_momentum) > 0.5:
                component['score'] += 1.0
                component['factors'].append("Strong trending market with momentum increases priority")
            elif trend_strength < 0.2:
                component['score'] -= 0.5
                component['factors'].append("Lack of clear trend reduces action urgency")
            
            # Market stress indicators
            current_price = indicators.get('current_price', 100.0)
            support_level = indicators.get('support_level', 0.0)
            resistance_level = indicators.get('resistance_level', 0.0)
            
            if support_level > 0 and current_price < support_level * 1.02:
                component['score'] += 1.5
                component['factors'].append("Price near critical support increases action urgency")
            elif resistance_level > 0 and current_price > resistance_level * 0.98:
                component['score'] += 1.0
                component['factors'].append("Price near resistance requires timely action")
            
            component['score'] = max(1.0, min(10.0, component['score']))
            
            return component
            
        except Exception as e:
            self.logger.error("Error assessing market conditions", error=str(e))
            return {'score': 5.0, 'factors': ['Assessment error'], 'market_assessment': 'Error in assessment'}
    
    async def _assess_volatility_impact(self, indicators: Dict[str, float], recommendation: str) -> Dict[str, Any]:
        """Assess how volatility impacts action timing priority"""
        try:
            component = {
                'score': 5.0,
                'factors': [],
                'volatility_impact': ''
            }
            
            volatility = indicators.get('volatility', 0.2)
            atr_percentage = indicators.get('atr_percentage', 0.0)
            
            # High volatility increases urgency for protective actions
            if recommendation in ['SELL', 'STRONG_SELL'] and volatility > 0.35:
                component['score'] += 2.5
                component['factors'].append("High volatility with sell signal demands immediate protection")
                component['volatility_impact'] = "Risk protection urgency due to volatility"
            elif recommendation in ['BUY', 'STRONG_BUY'] and volatility > 0.35:
                component['score'] += 1.5
                component['factors'].append("High volatility creates opportunity urgency but execution risk")
                component['volatility_impact'] = "Opportunity urgency with execution caution"
            
            # Moderate volatility considerations
            elif volatility > 0.25:
                if recommendation != 'HOLD':
                    component['score'] += 1.0
                    component['factors'].append("Elevated volatility increases action timing importance")
                    component['volatility_impact'] = "Elevated volatility requires careful timing"
            
            # Low volatility allows patience
            elif volatility < 0.12:
                component['score'] -= 1.0
                component['factors'].append("Low volatility allows patient execution")
                component['volatility_impact'] = "Low volatility permits patient approach"
            
            # ATR-based urgency
            if atr_percentage > 6.0:
                component['score'] += 1.0
                component['factors'].append(f"High daily range ({atr_percentage:.1f}%) requires quick execution")
            elif atr_percentage < 1.5:
                component['score'] -= 0.5
                component['factors'].append(f"Low daily range ({atr_percentage:.1f}%) allows deliberate execution")
            
            # Volatility regime change detection
            bb_width = indicators.get('bb_width', 0.0)
            if bb_width < 0.05:  # Very narrow bands
                component['score'] += 0.5
                component['factors'].append("Volatility compression may precede breakout - timing critical")
            elif bb_width > 0.2:  # Very wide bands
                component['score'] += 1.0
                component['factors'].append("High volatility regime requires swift execution")
            
            component['score'] = max(1.0, min(10.0, component['score']))
            
            return component
            
        except Exception as e:
            self.logger.error("Error assessing volatility impact", error=str(e))
            return {'score': 5.0, 'factors': ['Assessment error'], 'volatility_impact': 'Error in assessment'}
    
    async def _assess_technical_urgency(self, indicators: Dict[str, float], recommendation: str) -> Dict[str, Any]:
        """Assess technical analysis factors that create urgency"""
        try:
            component = {
                'score': 5.0,
                'factors': [],
                'technical_urgency': ''
            }
            
            # RSI extreme conditions
            rsi = indicators.get('rsi', 50.0)
            if rsi > 80:
                if recommendation in ['SELL', 'STRONG_SELL']:
                    component['score'] += 2.0
                    component['factors'].append(f"Extremely overbought RSI ({rsi:.1f}) aligns with sell signal")
                    component['technical_urgency'] = "Extreme overbought condition supports urgent action"
                else:
                    component['score'] += 0.5
                    component['factors'].append(f"Overbought RSI ({rsi:.1f}) suggests caution")
            elif rsi < 20:
                if recommendation in ['BUY', 'STRONG_BUY']:
                    component['score'] += 2.0
                    component['factors'].append(f"Extremely oversold RSI ({rsi:.1f}) aligns with buy signal")
                    component['technical_urgency'] = "Extreme oversold condition supports urgent action"
                else:
                    component['score'] += 0.5
                    component['factors'].append(f"Oversold RSI ({rsi:.1f}) creates complexity")
            
            # MACD momentum urgency
            macd = indicators.get('macd', 0.0)
            macd_signal = indicators.get('macd_signal', 0.0)
            macd_histogram = indicators.get('macd_histogram', 0.0)
            
            # Fresh MACD crossover
            if abs(macd - macd_signal) < 0.1 and abs(macd_histogram) < 0.05:
                component['score'] += 1.5
                component['factors'].append("Fresh MACD crossover requires timely action")
            
            # Strong MACD divergence
            elif abs(macd - macd_signal) > 1.0:
                component['score'] += 1.0
                component['factors'].append("Strong MACD signal supports action urgency")
            
            # Support/Resistance proximity urgency
            current_price = indicators.get('current_price', 100.0)
            support_level = indicators.get('support_level', 0.0)
            resistance_level = indicators.get('resistance_level', 0.0)
            
            if support_level > 0:
                distance_to_support = (current_price - support_level) / support_level
                if distance_to_support < 0.02:  # Within 2% of support
                    component['score'] += 2.0
                    component['factors'].append(f"Price very close to support (${support_level:.2f}) - critical level")
                    component['technical_urgency'] = "Critical support level proximity demands immediate attention"
            
            if resistance_level > 0:
                distance_to_resistance = (resistance_level - current_price) / current_price
                if distance_to_resistance < 0.02:  # Within 2% of resistance
                    component['score'] += 1.5
                    component['factors'].append(f"Price very close to resistance (${resistance_level:.2f}) - key level")
            
            # Bollinger Band extremes
            bb_percent_b = indicators.get('bb_percent_b', 0.5)
            if bb_percent_b > 1.0 or bb_percent_b < 0.0:
                component['score'] += 1.5
                component['factors'].append(f"Price outside Bollinger Bands (%B: {bb_percent_b:.2f}) creates urgency")
            
            # Moving average alignment urgency
            sma_20 = indicators.get('sma_20', current_price)
            sma_50 = indicators.get('sma_50', current_price)
            
            # Golden/Death cross proximity
            if sma_20 > 0 and sma_50 > 0:
                ma_convergence = abs(sma_20 - sma_50) / sma_50
                if ma_convergence < 0.02:  # MAs converging
                    component['score'] += 1.0
                    component['factors'].append("Moving averages converging - potential trend change")
            
            component['score'] = max(1.0, min(10.0, component['score']))
            
            return component
            
        except Exception as e:
            self.logger.error("Error assessing technical urgency", error=str(e))
            return {'score': 5.0, 'factors': ['Assessment error'], 'technical_urgency': 'Error in assessment'}
    
    async def _assess_time_sensitivity(self, indicators: Dict[str, float], recommendation: str) -> Dict[str, Any]:
        """Assess time-sensitive factors affecting action priority"""
        try:
            component = {
                'score': 5.0,
                'factors': [],
                'time_factors': ''
            }
            
            # Price momentum acceleration/deceleration
            trend_momentum = indicators.get('trend_momentum', 0.0)
            if abs(trend_momentum) > 0.5:
                component['score'] += 1.5
                momentum_direction = "accelerating" if trend_momentum > 0 else "decelerating"
                component['factors'].append(f"Strong momentum {momentum_direction} increases time sensitivity")
                component['time_factors'] = f"Momentum {momentum_direction} suggests timing importance"
            
            # Volume spike timing
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 3.0:
                component['score'] += 2.0
                component['factors'].append(f"Volume spike ({volume_ratio:.1f}x) suggests immediate market interest")
                component['time_factors'] = "Volume spike indicates market timing opportunity"
            elif volume_ratio > 2.0:
                component['score'] += 1.0
                component['factors'].append(f"High volume ({volume_ratio:.1f}x) supports timely action")
            
            # Volatility expansion timing
            bb_width = indicators.get('bb_width', 0.0)
            volatility = indicators.get('volatility', 0.2)
            
            if bb_width < 0.05 and volatility < 0.15:
                component['score'] += 1.0
                component['factors'].append("Low volatility regime may end soon - positioning window closing")
            elif bb_width > 0.15 and volatility > 0.3:
                component['score'] += 1.5
                component['factors'].append("High volatility regime requires immediate action")
            
            # Price gap considerations
            price_change_percent = indicators.get('price_change_percent', 0.0)
            if abs(price_change_percent) > 5:
                component['score'] += 1.0
                gap_direction = "up" if price_change_percent > 0 else "down"
                component['factors'].append(f"Price gap {gap_direction} ({price_change_percent:+.1f}%) creates timing urgency")
            
            # Trend exhaustion timing
            trend_strength = indicators.get('trend_strength', 0.0)
            if trend_strength > 0.8:
                component['score'] += 0.5
                component['factors'].append("Very strong trend may be exhausted - timing becomes critical")
            
            component['score'] = max(1.0, min(10.0, component['score']))
            
            return component
            
        except Exception as e:
            self.logger.error("Error assessing time sensitivity", error=str(e))
            return {'score': 5.0, 'factors': ['Assessment error'], 'time_factors': 'Error in assessment'}
    
    async def _calculate_composite_priority_score(self, priority_components: Dict[str, Dict[str, Any]]) -> float:
        """Calculate weighted composite priority score"""
        try:
            total_weighted_score = 0.0
            total_weight = 0.0
            
            for component_name, component_data in priority_components.items():
                if component_name in self.priority_weights:
                    weight = self.priority_weights[component_name]
                    score = component_data.get('score', 5.0)
                    
                    total_weighted_score += score * weight
                    total_weight += weight
            
            if total_weight == 0:
                return 5.0
            
            composite_score = total_weighted_score / total_weight
            return max(1.0, min(10.0, composite_score))
            
        except Exception as e:
            self.logger.error("Error calculating composite priority score", error=str(e))
            return 5.0
    
    async def _determine_priority_level(self, priority_score: float) -> str:
        """Determine priority level from composite score"""
        try:
            for level, config in sorted(self.priority_levels.items(), 
                                       key=lambda x: x[1]['min_score'], reverse=True):
                if priority_score >= config['min_score']:
                    return level
            return 'very_low'
            
        except Exception as e:
            self.logger.error("Error determining priority level", error=str(e))
            return 'medium'
    
    async def _determine_urgency(self, priority_score: float, indicators: Dict[str, float], recommendation: str) -> str:
        """Determine urgency level for action"""
        try:
            # Base urgency on priority score
            if priority_score >= 9.0:
                base_urgency = 'immediate'
            elif priority_score >= 7.5:
                base_urgency = 'very_high'
            elif priority_score >= 6.0:
                base_urgency = 'high'
            elif priority_score >= 4.0:
                base_urgency = 'medium'
            elif priority_score >= 2.0:
                base_urgency = 'low'
            else:
                base_urgency = 'very_low'
            
            # Adjust for specific conditions
            volatility = indicators.get('volatility', 0.2)
            rsi = indicators.get('rsi', 50.0)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            
            # Increase urgency for extreme conditions
            if ((rsi > 85 or rsi < 15) and recommendation != 'HOLD') or volatility > 0.5 or volume_ratio > 4.0:
                urgency_levels = ['very_low', 'low', 'medium', 'high', 'very_high', 'immediate']
                current_index = urgency_levels.index(base_urgency) if base_urgency in urgency_levels else 2
                new_index = min(len(urgency_levels) - 1, current_index + 1)
                return urgency_levels[new_index]
            
            return base_urgency
            
        except Exception as e:
            self.logger.error("Error determining urgency", error=str(e))
            return 'medium'
    
    async def _analyze_timing_factors(self, indicators: Dict[str, float], priority_score: float) -> Dict[str, Any]:
        """Analyze optimal timing factors for action execution"""
        try:
            timing_analysis = {
                'optimal_timing': 'market_hours',
                'execution_window': '1-4 hours',
                'timing_factors': [],
                'market_session_preference': 'any',
                'intraday_timing': 'flexible'
            }
            
            # High priority timing
            if priority_score >= 8.0:
                timing_analysis['optimal_timing'] = 'immediate'
                timing_analysis['execution_window'] = '15-60 minutes'
                timing_analysis['timing_factors'].append("High priority requires immediate execution")
            elif priority_score >= 6.5:
                timing_analysis['optimal_timing'] = 'priority'
                timing_analysis['execution_window'] = '1-4 hours'
                timing_analysis['timing_factors'].append("Elevated priority suggests prompt execution")
            
            # Volume-based timing
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 2.0:
                timing_analysis['market_session_preference'] = 'current_session'
                timing_analysis['timing_factors'].append("High volume suggests executing in current session")
            elif volume_ratio < 0.5:
                timing_analysis['execution_window'] = '1-3 days'
                timing_analysis['timing_factors'].append("Low volume allows patient execution across sessions")
            
            # Volatility timing considerations
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.35:
                timing_analysis['intraday_timing'] = 'avoid_extremes'
                timing_analysis['timing_factors'].append("High volatility - avoid market open/close extremes")
            elif volatility < 0.15:
                timing_analysis['intraday_timing'] = 'flexible'
                timing_analysis['timing_factors'].append("Low volatility allows flexible intraday timing")
            
            # Technical level timing
            current_price = indicators.get('current_price', 100.0)
            support_level = indicators.get('support_level', 0.0)
            resistance_level = indicators.get('resistance_level', 0.0)
            
            if support_level > 0 and current_price < support_level * 1.05:
                timing_analysis['optimal_timing'] = 'urgent'
                timing_analysis['timing_factors'].append("Price near support - timing critical")
            elif resistance_level > 0 and current_price > resistance_level * 0.95:
                timing_analysis['optimal_timing'] = 'priority'
                timing_analysis['timing_factors'].append("Price near resistance - timely execution needed")
            
            return timing_analysis
            
        except Exception as e:
            self.logger.error("Error analyzing timing factors", error=str(e))
            return {
                'optimal_timing': 'market_hours',
                'execution_window': '1-4 hours',
                'timing_factors': ['Error in timing analysis'],
                'market_session_preference': 'any',
                'intraday_timing': 'flexible'
            }
    
    async def _recommend_execution_strategy(self, priority_score: float, indicators: Dict[str, float], 
                                          recommendation: str, risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend execution strategy based on priority and conditions"""
        try:
            strategy = {
                'strategy': 'standard',
                'recommendations': [],
                'order_type_preference': 'limit',
                'execution_approach': 'single_order',
                'risk_management': []
            }
            
            volatility = indicators.get('volatility', 0.2)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            risk_level = risk_assessment.get('risk_level', 'medium')
            
            # High priority strategies
            if priority_score >= 8.5:
                strategy['strategy'] = 'aggressive'
                strategy['order_type_preference'] = 'market_with_protection'
                strategy['recommendations'].append("Use market orders with stop protection for urgent execution")
                strategy['execution_approach'] = 'immediate_full'
                strategy['risk_management'].append("Implement tight stop-losses immediately after execution")
                
            elif priority_score >= 7.0:
                strategy['strategy'] = 'active'
                if volatility > 0.3:
                    strategy['order_type_preference'] = 'limit_aggressive'
                    strategy['recommendations'].append("Use aggressive limit orders for fast execution in volatile conditions")
                else:
                    strategy['order_type_preference'] = 'market'
                    strategy['recommendations'].append("Market orders acceptable given priority and stable conditions")
                strategy['execution_approach'] = 'quick_execution'
                
            # Standard priority strategies
            elif priority_score >= 5.5:
                strategy['strategy'] = 'standard'
                strategy['order_type_preference'] = 'limit'
                strategy['recommendations'].append("Use limit orders for favorable execution")
                if volume_ratio < 0.6:
                    strategy['execution_approach'] = 'scaled_entry'
                    strategy['recommendations'].append("Consider scaling into position due to lower volume")
                
            # Low priority strategies
            else:
                strategy['strategy'] = 'patient'
                strategy['order_type_preference'] = 'limit_patient'
                strategy['recommendations'].append("Use patient limit orders to optimize entry/exit price")
                strategy['execution_approach'] = 'scaled_entry'
                strategy['recommendations'].append("Scale into position over time for optimal pricing")
            
            # Risk-based adjustments
            if risk_level in ['high', 'very_high']:
                strategy['risk_management'].append("Use smaller initial position size due to high risk assessment")
                strategy['risk_management'].append("Implement protective stops immediately")
                if strategy['execution_approach'] != 'immediate_full':
                    strategy['execution_approach'] = 'scaled_entry'
            
            # Volatility adjustments
            if volatility > 0.4:
                strategy['risk_management'].append("Use wider spreads and patient execution due to high volatility")
                if strategy['order_type_preference'] == 'market':
                    strategy['order_type_preference'] = 'limit_aggressive'
            
            # Liquidity adjustments
            if volume_ratio < 0.4:
                strategy['execution_approach'] = 'scaled_entry'
                strategy['recommendations'].append("Scale execution due to low liquidity conditions")
                strategy['risk_management'].append("Monitor market impact carefully")
            
            return strategy
            
        except Exception as e:
            self.logger.error("Error recommending execution strategy", error=str(e))
            return {
                'strategy': 'cautious',
                'recommendations': ['Use cautious execution due to analysis error'],
                'order_type_preference': 'limit',
                'execution_approach': 'scaled_entry',
                'risk_management': ['Implement conservative risk management']
            }
    
    async def _calculate_position_sizing_priority(self, priority_score: float, confidence: float, 
                                                risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate position sizing based on priority and risk"""
        try:
            sizing = {
                'recommendation': 'normal',
                'sizing_factor': 1.0,
                'max_position_percent': 5.0,
                'reasoning': []
            }
            
            # Base sizing on priority
            if priority_score >= 8.5:
                sizing['recommendation'] = 'large'
                sizing['sizing_factor'] = 1.5
                sizing['max_position_percent'] = 7.5
                sizing['reasoning'].append("Very high priority supports larger position")
            elif priority_score >= 7.0:
                sizing['recommendation'] = 'above_normal'
                sizing['sizing_factor'] = 1.25
                sizing['max_position_percent'] = 6.25
                sizing['reasoning'].append("High priority supports increased position size")
            elif priority_score <= 3.0:
                sizing['recommendation'] = 'small'
                sizing['sizing_factor'] = 0.5
                sizing['max_position_percent'] = 2.5
                sizing['reasoning'].append("Low priority suggests smaller position size")
            
            # Adjust for confidence
            if confidence > 0.8:
                sizing['sizing_factor'] *= 1.2
                sizing['reasoning'].append(f"High confidence ({confidence:.1%}) supports larger sizing")
            elif confidence < 0.4:
                sizing['sizing_factor'] *= 0.7
                sizing['reasoning'].append(f"Low confidence ({confidence:.1%}) suggests smaller sizing")
            
            # Risk assessment adjustments
            risk_level = risk_assessment.get('risk_level', 'medium')
            risk_score = risk_assessment.get('risk_score', 5.0)
            
            if risk_level in ['very_high', 'high'] or risk_score > 7.0:
                sizing['sizing_factor'] *= 0.6
                sizing['max_position_percent'] = min(sizing['max_position_percent'], 3.0)
                sizing['reasoning'].append("High risk assessment reduces position size")
            elif risk_level == 'low' or risk_score < 3.0:
                sizing['sizing_factor'] *= 1.1
                sizing['reasoning'].append("Low risk assessment allows slightly larger position")
            
            # Ensure reasonable bounds
            sizing['sizing_factor'] = max(0.2, min(2.0, sizing['sizing_factor']))
            sizing['max_position_percent'] = max(1.0, min(10.0, sizing['max_position_percent']))
            
            # Update recommendation based on final factor
            if sizing['sizing_factor'] >= 1.5:
                sizing['recommendation'] = 'large'
            elif sizing['sizing_factor'] >= 1.2:
                sizing['recommendation'] = 'above_normal'
            elif sizing['sizing_factor'] <= 0.5:
                sizing['recommendation'] = 'small'
            elif sizing['sizing_factor'] <= 0.75:
                sizing['recommendation'] = 'below_normal'
            else:
                sizing['recommendation'] = 'normal'
            
            return sizing
            
        except Exception as e:
            self.logger.error("Error calculating position sizing priority", error=str(e))
            return {
                'recommendation': 'small',
                'sizing_factor': 0.5,
                'max_position_percent': 2.5,
                'reasoning': ['Conservative sizing due to calculation error']
            }
    
    async def _create_monitoring_schedule(self, priority_level: str, urgency: str, recommendation: str) -> Dict[str, str]:
        """Create monitoring schedule based on priority and urgency"""
        try:
            schedule = {}
            
            if priority_level == 'critical' or urgency == 'immediate':
                schedule['immediate'] = 'Monitor continuously for first 30 minutes'
                schedule['short_term'] = 'Check every 15 minutes for first 2 hours'
                schedule['medium_term'] = 'Hourly monitoring for remainder of day'
                schedule['ongoing'] = 'Standard daily monitoring thereafter'
                
            elif priority_level == 'high' or urgency in ['very_high', 'high']:
                schedule['immediate'] = 'Monitor within 30 minutes of execution'
                schedule['short_term'] = 'Check every 30 minutes for first 4 hours'
                schedule['medium_term'] = 'Every 2 hours for remainder of trading day'
                schedule['ongoing'] = 'Daily monitoring with periodic intraday checks'
                
            elif priority_level == 'medium':
                schedule['immediate'] = 'Check within 1 hour of execution'
                schedule['short_term'] = 'Monitor every 2-4 hours on execution day'
                schedule['medium_term'] = 'Daily monitoring with key level alerts'
                schedule['ongoing'] = 'Standard daily review'
                
            else:  # low or very_low priority
                schedule['immediate'] = 'No immediate monitoring required'
                schedule['short_term'] = 'End-of-day check on execution day'
                schedule['medium_term'] = 'Daily monitoring sufficient'
                schedule['ongoing'] = 'Standard periodic review'
            
            # Special conditions
            if recommendation in ['STRONG_SELL', 'STRONG_BUY']:
                schedule['special'] = 'Enhanced monitoring due to strong conviction recommendation'
            
            return schedule
            
        except Exception as e:
            self.logger.error("Error creating monitoring schedule", error=str(e))
            return {
                'immediate': 'Standard monitoring due to error',
                'short_term': 'Hourly checks recommended',
                'medium_term': 'Daily monitoring',
                'ongoing': 'Standard review schedule'
            }
    
    async def _identify_priority_risks(self, priority_score: float, indicators: Dict[str, float]) -> List[str]:
        """Identify risks specific to high-priority actions"""
        try:
            risks = []
            
            if priority_score >= 8.0:
                risks.append("High priority may lead to rushed decisions - verify analysis")
                risks.append("Urgent execution may result in suboptimal pricing")
            
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.35 and priority_score >= 7.0:
                risks.append("High volatility with urgent action increases execution risk")
            
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio < 0.5 and priority_score >= 6.0:
                risks.append("Low volume with elevated priority may impact execution quality")
            
            rsi = indicators.get('rsi', 50.0)
            if (rsi > 80 or rsi < 20) and priority_score >= 7.0:
                risks.append("Extreme RSI with high priority suggests potential reversal risk")
            
            if priority_score >= 8.5:
                risks.append("Very high priority demands continuous monitoring to manage risk")
            
            return risks[:4]  # Limit to top 4 priority-specific risks
            
        except Exception as e:
            self.logger.error("Error identifying priority risks", error=str(e))
            return ["Risk identification error - exercise additional caution"]
    
    async def _analyze_market_timing_factors(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Analyze market timing factors affecting execution"""
        try:
            timing_factors = {
                'session_timing': 'any_session',
                'intraday_preferences': [],
                'timing_risks': [],
                'optimal_conditions': []
            }
            
            # Volume timing
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.8:
                timing_factors['session_timing'] = 'current_high_volume'
                timing_factors['optimal_conditions'].append("High volume provides good execution conditions")
            elif volume_ratio < 0.6:
                timing_factors['timing_risks'].append("Low volume may lead to poor execution")
                timing_factors['intraday_preferences'].append("Avoid market open/close periods")
            
            # Volatility timing
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.3:
                timing_factors['intraday_preferences'].append("Execute during mid-session for stability")
                timing_factors['timing_risks'].append("High volatility increases timing risk")
            elif volatility < 0.15:
                timing_factors['optimal_conditions'].append("Low volatility allows flexible timing")
            
            # Technical level timing
            current_price = indicators.get('current_price', 100.0)
            support_level = indicators.get('support_level', 0.0)
            resistance_level = indicators.get('resistance_level', 0.0)
            
            if support_level > 0 and current_price < support_level * 1.05:
                timing_factors['timing_risks'].append("Price near support - timing critical for entries")
                timing_factors['session_timing'] = 'immediate_attention'
            
            if resistance_level > 0 and current_price > resistance_level * 0.95:
                timing_factors['timing_risks'].append("Price near resistance - timing important for exits")
            
            return timing_factors
            
        except Exception as e:
            self.logger.error("Error analyzing market timing factors", error=str(e))
            return {
                'session_timing': 'standard',
                'intraday_preferences': [],
                'timing_risks': ['Error in timing analysis'],
                'optimal_conditions': []
            }
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'action_priority_calculation',
            'priority_weights': self.priority_weights,
            'priority_levels': list(self.priority_levels.keys()),
            'urgency_factors': list(self.urgency_factors.keys()),
            'assessment_components': [
                'recommendation_strength_assessment',
                'confidence_impact_analysis',
                'market_conditions_assessment',
                'volatility_impact_analysis',
                'technical_urgency_assessment',
                'time_sensitivity_analysis',
                'composite_priority_calculation',
                'timing_analysis',
                'execution_strategy_recommendations',
                'position_sizing_priority',
                'monitoring_schedule_creation',
                'priority_risk_identification',
                'market_timing_analysis'
            ],
            'features': [
                'multi_factor_priority_scoring',
                'weighted_composite_calculation',
                'dynamic_urgency_determination',
                'execution_strategy_optimization',
                'risk_based_position_sizing',
                'adaptive_monitoring_schedules',
                'market_timing_analysis',
                'priority_risk_assessment'
            ],
            'description': 'Comprehensive action priority calculation module providing timing, urgency, and execution guidance for investment decisions'
        }