"""
Risk Assessment Module - Single Function Module
Comprehensive risk assessment and analysis for investment recommendations
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


class RiskAssessmentModule(SingleFunctionModuleBase):
    """Comprehensive risk assessment and analysis for investment decisions"""
    
    def __init__(self, event_bus):
        super().__init__("risk_assessment", event_bus)
        self.risk_categories = {
            'market_risk': {'weight': 0.25, 'description': 'Overall market and systematic risk'},
            'technical_risk': {'weight': 0.20, 'description': 'Technical indicator-based risk'},
            'volatility_risk': {'weight': 0.20, 'description': 'Price volatility and stability risk'},
            'liquidity_risk': {'weight': 0.15, 'description': 'Trading volume and liquidity risk'},
            'model_risk': {'weight': 0.10, 'description': 'ML model uncertainty and prediction risk'},
            'sentiment_risk': {'weight': 0.10, 'description': 'Market sentiment and momentum risk'}
        }
        self.risk_thresholds = {
            'low_risk': 3.0,
            'medium_risk': 6.0,
            'high_risk': 8.0,
            'extreme_risk': 9.0
        }
        self.risk_scale = {1: 'very_low', 2: 'low', 3: 'low_medium', 4: 'medium', 5: 'medium', 
                          6: 'medium_high', 7: 'high', 8: 'high', 9: 'very_high', 10: 'extreme'}
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('risk.assessment.request', self.process_event)
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
                'risk_categories_count': len(self.risk_categories),
                'risk_thresholds': self.risk_thresholds,
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'risk.assessment.request':
            indicators = event.get('indicators', {})
            ml_scores = event.get('ml_scores', {})
            symbol = event.get('symbol', 'UNKNOWN')
            recommendation = event.get('recommendation', 'HOLD')
            confidence = event.get('confidence', 0.5)
            
            risk_assessment = await self.generate_risk_assessment(
                indicators, ml_scores, symbol, recommendation, confidence
            )
            
            response_event = {
                'event_type': 'risk.assessment.response',
                'risk_assessment': risk_assessment,
                'symbol': symbol,
                'recommendation': recommendation,
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def generate_risk_assessment(self, indicators: Dict[str, float], ml_scores: Dict[str, float], 
                                     symbol: str = "UNKNOWN", recommendation: str = "HOLD", 
                                     confidence: float = 0.5) -> Dict[str, Any]:
        """Generate comprehensive risk assessment"""
        try:
            risk_assessment = {
                'overall_risk': 'medium',
                'risk_score': 5.0,
                'risk_level': 'medium',
                'key_risks': [],
                'mitigation_strategies': [],
                'risk_breakdown': {},
                'risk_factors_analysis': {},
                'position_sizing_recommendation': {},
                'monitoring_requirements': [],
                'risk_horizon': {},
                'stress_test_scenarios': []
            }
            
            # Calculate individual risk category scores
            risk_scores = {}
            
            # Market Risk Analysis
            risk_scores['market_risk'] = await self._assess_market_risk(indicators, ml_scores)
            
            # Technical Risk Analysis  
            risk_scores['technical_risk'] = await self._assess_technical_risk(indicators)
            
            # Volatility Risk Analysis
            risk_scores['volatility_risk'] = await self._assess_volatility_risk(indicators)
            
            # Liquidity Risk Analysis
            risk_scores['liquidity_risk'] = await self._assess_liquidity_risk(indicators)
            
            # Model Risk Analysis
            risk_scores['model_risk'] = await self._assess_model_risk(ml_scores, confidence)
            
            # Sentiment Risk Analysis
            risk_scores['sentiment_risk'] = await self._assess_sentiment_risk(indicators, recommendation)
            
            # Calculate composite risk score
            composite_risk_score = await self._calculate_composite_risk_score(risk_scores)
            
            # Update risk assessment with calculated values
            risk_assessment['risk_score'] = composite_risk_score
            risk_assessment['risk_level'] = await self._determine_risk_level(composite_risk_score)
            risk_assessment['overall_risk'] = risk_assessment['risk_level']
            risk_assessment['risk_breakdown'] = risk_scores
            
            # Generate comprehensive risk analysis
            risk_assessment['key_risks'] = await self._identify_key_risks(risk_scores, indicators, ml_scores)
            risk_assessment['mitigation_strategies'] = await self._generate_mitigation_strategies(
                risk_scores, indicators, recommendation
            )
            risk_assessment['risk_factors_analysis'] = await self._analyze_risk_factors(
                risk_scores, indicators, ml_scores
            )
            risk_assessment['position_sizing_recommendation'] = await self._recommend_position_sizing(
                composite_risk_score, confidence, recommendation
            )
            risk_assessment['monitoring_requirements'] = await self._determine_monitoring_requirements(
                risk_scores, composite_risk_score
            )
            risk_assessment['risk_horizon'] = await self._assess_risk_horizon(
                indicators, composite_risk_score
            )
            risk_assessment['stress_test_scenarios'] = await self._generate_stress_test_scenarios(
                indicators, composite_risk_score
            )
            
            self.logger.debug("Risk assessment completed",
                            symbol=symbol,
                            risk_score=composite_risk_score,
                            risk_level=risk_assessment['risk_level'],
                            key_risks_count=len(risk_assessment['key_risks']))
            
            return risk_assessment
            
        except Exception as e:
            self.logger.error("Error generating risk assessment", 
                            symbol=symbol,
                            error=str(e))
            return {
                'overall_risk': 'high',
                'risk_score': 7.0,
                'risk_level': 'high',
                'key_risks': [f'Risk assessment error: {str(e)}'],
                'mitigation_strategies': ['Increase caution due to analysis error'],
                'risk_breakdown': {},
                'risk_factors_analysis': {'error': str(e)},
                'position_sizing_recommendation': {'recommendation': 'reduced', 'reason': 'assessment_error'},
                'monitoring_requirements': ['Immediate re-assessment required'],
                'risk_horizon': {'error': str(e)},
                'stress_test_scenarios': []
            }
    
    async def _assess_market_risk(self, indicators: Dict[str, float], ml_scores: Dict[str, float]) -> Dict[str, Any]:
        """Assess market and systematic risk"""
        try:
            risk_score = 5.0  # Base medium risk
            risk_factors = []
            
            # Price volatility impact on market risk
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.4:
                risk_score += 2.0
                risk_factors.append(f"High market volatility ({volatility:.1%}) increases systematic risk")
            elif volatility > 0.25:
                risk_score += 1.0
                risk_factors.append(f"Elevated volatility ({volatility:.1%}) adds market risk")
            elif volatility < 0.1:
                risk_score -= 1.0
                risk_factors.append(f"Low volatility ({volatility:.1%}) reduces market risk")
            
            # Trend strength and market direction risk
            trend_strength = indicators.get('trend_strength', 0.0)
            trend_direction = indicators.get('trend_direction', 'neutral')
            
            if trend_strength > 0.8:
                risk_score += 1.0
                risk_factors.append(f"Very strong {trend_direction} trend may be overextended")
            elif trend_strength < 0.2:
                risk_score += 0.5
                risk_factors.append("Lack of clear market trend increases uncertainty")
            
            # Market momentum risk
            price_change_percent = indicators.get('price_change_percent', 0.0)
            if abs(price_change_percent) > 10:
                risk_score += 1.5
                direction = "upward" if price_change_percent > 0 else "downward"
                risk_factors.append(f"Extreme {direction} momentum ({price_change_percent:+.1f}%) suggests elevated risk")
            elif abs(price_change_percent) > 5:
                risk_score += 0.5
                risk_factors.append(f"Strong price movement ({price_change_percent:+.1f}%) adds momentum risk")
            
            # Support/resistance proximity risk
            current_price = indicators.get('current_price', 100.0)
            support_level = indicators.get('support_level', 0.0)
            resistance_level = indicators.get('resistance_level', 0.0)
            
            if resistance_level > 0 and current_price > resistance_level * 0.98:
                risk_score += 1.0
                risk_factors.append(f"Price near resistance (${resistance_level:.2f}) increases rejection risk")
            elif support_level > 0 and current_price < support_level * 1.02:
                risk_score += 1.0
                risk_factors.append(f"Price near support (${support_level:.2f}) increases breakdown risk")
            
            # Ensure risk score stays within bounds
            risk_score = max(1.0, min(10.0, risk_score))
            
            return {
                'score': risk_score,
                'factors': risk_factors,
                'category': 'market_risk',
                'assessment': self._get_risk_assessment_text(risk_score)
            }
            
        except Exception as e:
            self.logger.error("Error assessing market risk", error=str(e))
            return {'score': 7.0, 'factors': ['Market risk assessment error'], 'category': 'market_risk'}
    
    async def _assess_technical_risk(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Assess technical analysis-based risks"""
        try:
            risk_score = 5.0
            risk_factors = []
            
            # RSI extreme conditions
            rsi = indicators.get('rsi', 50.0)
            if rsi > 85:
                risk_score += 2.0
                risk_factors.append(f"Extremely overbought RSI ({rsi:.1f}) signals high reversal risk")
            elif rsi > 75:
                risk_score += 1.0
                risk_factors.append(f"Overbought RSI ({rsi:.1f}) suggests potential pullback")
            elif rsi < 15:
                risk_score += 2.0
                risk_factors.append(f"Extremely oversold RSI ({rsi:.1f}) may indicate continued weakness")
            elif rsi < 25:
                risk_score += 1.0
                risk_factors.append(f"Oversold RSI ({rsi:.1f}) could signal further decline")
            
            # MACD divergence and momentum risk
            macd = indicators.get('macd', 0.0)
            macd_signal = indicators.get('macd_signal', 0.0)
            macd_histogram = indicators.get('macd_histogram', 0.0)
            
            # MACD extreme readings
            if abs(macd) > 2.0:
                risk_score += 1.0
                risk_factors.append(f"Extreme MACD reading ({macd:.2f}) suggests momentum exhaustion risk")
            
            # MACD histogram divergence
            if abs(macd_histogram) < 0.1 and abs(macd - macd_signal) > 0.5:
                risk_score += 0.5
                risk_factors.append("MACD histogram showing potential momentum divergence")
            
            # Moving average configuration risk
            current_price = indicators.get('current_price', 100.0)
            sma_20 = indicators.get('sma_20', current_price)
            sma_50 = indicators.get('sma_50', current_price)
            
            # Price gap from moving averages
            if sma_20 > 0:
                sma20_gap = abs(current_price - sma_20) / sma_20
                if sma20_gap > 0.1:
                    risk_score += 1.0
                    risk_factors.append(f"Large gap from 20-day MA ({sma20_gap:.1%}) increases mean reversion risk")
                elif sma20_gap > 0.05:
                    risk_score += 0.5
                    risk_factors.append(f"Moderate gap from 20-day MA ({sma20_gap:.1%}) adds technical risk")
            
            # Bollinger Bands extremes
            bb_percent_b = indicators.get('bb_percent_b', 0.5)
            if bb_percent_b > 1.0 or bb_percent_b < 0.0:
                risk_score += 1.5
                extreme_type = "above upper" if bb_percent_b > 1.0 else "below lower"
                risk_factors.append(f"Price {extreme_type} Bollinger Band (%B: {bb_percent_b:.2f}) signals extreme conditions")
            elif bb_percent_b > 0.9 or bb_percent_b < 0.1:
                risk_score += 0.5
                risk_factors.append(f"Price near Bollinger Band extreme (%B: {bb_percent_b:.2f})")
            
            risk_score = max(1.0, min(10.0, risk_score))
            
            return {
                'score': risk_score,
                'factors': risk_factors,
                'category': 'technical_risk',
                'assessment': self._get_risk_assessment_text(risk_score)
            }
            
        except Exception as e:
            self.logger.error("Error assessing technical risk", error=str(e))
            return {'score': 7.0, 'factors': ['Technical risk assessment error'], 'category': 'technical_risk'}
    
    async def _assess_volatility_risk(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Assess volatility and price stability risks"""
        try:
            risk_score = 5.0
            risk_factors = []
            
            # Historical volatility analysis
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.5:
                risk_score += 3.0
                risk_factors.append(f"Extreme volatility ({volatility:.1%}) creates significant price risk")
            elif volatility > 0.35:
                risk_score += 2.0
                risk_factors.append(f"High volatility ({volatility:.1%}) increases position risk")
            elif volatility > 0.25:
                risk_score += 1.0
                risk_factors.append(f"Elevated volatility ({volatility:.1%}) adds uncertainty")
            elif volatility < 0.08:
                risk_score -= 1.0
                risk_factors.append(f"Very low volatility ({volatility:.1%}) suggests stability")
            elif volatility < 0.15:
                risk_score -= 0.5
                risk_factors.append(f"Low volatility ({volatility:.1%}) reduces price risk")
            
            # ATR-based volatility assessment
            atr_percentage = indicators.get('atr_percentage', 0.0)
            if atr_percentage > 8.0:
                risk_score += 2.0
                risk_factors.append(f"High ATR ({atr_percentage:.1f}%) indicates large daily price swings")
            elif atr_percentage > 5.0:
                risk_score += 1.0
                risk_factors.append(f"Elevated ATR ({atr_percentage:.1f}%) shows increased daily volatility")
            elif atr_percentage < 1.0:
                risk_score -= 0.5
                risk_factors.append(f"Low ATR ({atr_percentage:.1f}%) suggests price stability")
            
            # Bollinger Band width (volatility expansion/contraction)
            bb_width = indicators.get('bb_width', 0.0)
            if bb_width > 0.15:
                risk_score += 1.0
                risk_factors.append(f"Wide Bollinger Bands ({bb_width:.2f}) indicate high volatility regime")
            elif bb_width < 0.03:
                risk_score += 0.5
                risk_factors.append(f"Narrow Bollinger Bands ({bb_width:.2f}) may precede volatility expansion")
            
            # Price gap risk
            price_change_percent = indicators.get('price_change_percent', 0.0)
            if abs(price_change_percent) > 8:
                risk_score += 1.5
                risk_factors.append(f"Large price gap ({price_change_percent:+.1f}%) increases volatility risk")
            
            risk_score = max(1.0, min(10.0, risk_score))
            
            return {
                'score': risk_score,
                'factors': risk_factors,
                'category': 'volatility_risk',
                'assessment': self._get_risk_assessment_text(risk_score)
            }
            
        except Exception as e:
            self.logger.error("Error assessing volatility risk", error=str(e))
            return {'score': 7.0, 'factors': ['Volatility risk assessment error'], 'category': 'volatility_risk'}
    
    async def _assess_liquidity_risk(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Assess liquidity and trading volume risks"""
        try:
            risk_score = 5.0
            risk_factors = []
            
            # Volume ratio analysis
            volume_ratio = indicators.get('volume_ratio', 1.0)
            current_volume = indicators.get('current_volume', 0)
            avg_volume = indicators.get('avg_volume', 0)
            
            if volume_ratio < 0.2:
                risk_score += 3.0
                risk_factors.append(f"Very low volume ({volume_ratio:.1f}x average) creates liquidity risk")
            elif volume_ratio < 0.4:
                risk_score += 2.0
                risk_factors.append(f"Low volume ({volume_ratio:.1f}x average) may impact execution")
            elif volume_ratio < 0.6:
                risk_score += 1.0
                risk_factors.append(f"Below-average volume ({volume_ratio:.1f}x) reduces liquidity")
            elif volume_ratio > 3.0:
                risk_score += 1.0
                risk_factors.append(f"Extremely high volume ({volume_ratio:.1f}x) may indicate news-driven volatility")
            elif volume_ratio > 2.0:
                risk_score += 0.5
                risk_factors.append(f"High volume ({volume_ratio:.1f}x) requires careful execution")
            
            # Absolute volume assessment
            if avg_volume > 0:
                if current_volume < avg_volume * 0.1:
                    risk_score += 2.0
                    risk_factors.append("Extremely thin trading creates execution risk")
                elif current_volume < avg_volume * 0.3:
                    risk_score += 1.0
                    risk_factors.append("Light trading volume increases spread risk")
            
            # Price-volume relationship
            price_volume_correlation = indicators.get('price_volume_correlation', 0.0)
            price_change_percent = indicators.get('price_change_percent', 0.0)
            
            if abs(price_change_percent) > 5 and abs(price_volume_correlation) < 0.3:
                risk_score += 1.0
                risk_factors.append("Large price move without volume confirmation suggests liquidity gaps")
            
            # Volume trend analysis
            volume_trend = indicators.get('volume_trend', 'neutral')
            if volume_trend == 'declining' and volume_ratio < 0.8:
                risk_score += 1.0
                risk_factors.append("Declining volume trend reduces market participation")
            
            risk_score = max(1.0, min(10.0, risk_score))
            
            return {
                'score': risk_score,
                'factors': risk_factors,
                'category': 'liquidity_risk',
                'assessment': self._get_risk_assessment_text(risk_score)
            }
            
        except Exception as e:
            self.logger.error("Error assessing liquidity risk", error=str(e))
            return {'score': 7.0, 'factors': ['Liquidity risk assessment error'], 'category': 'liquidity_risk'}
    
    async def _assess_model_risk(self, ml_scores: Dict[str, float], confidence: float) -> Dict[str, Any]:
        """Assess ML model prediction and uncertainty risks"""
        try:
            risk_score = 5.0
            risk_factors = []
            
            # Confidence-based risk assessment
            if confidence < 0.3:
                risk_score += 3.0
                risk_factors.append(f"Very low model confidence ({confidence:.1%}) creates high prediction risk")
            elif confidence < 0.5:
                risk_score += 2.0
                risk_factors.append(f"Low model confidence ({confidence:.1%}) increases uncertainty")
            elif confidence < 0.7:
                risk_score += 1.0
                risk_factors.append(f"Moderate model confidence ({confidence:.1%}) suggests caution")
            elif confidence > 0.9:
                risk_score -= 1.0
                risk_factors.append(f"Very high model confidence ({confidence:.1%}) reduces prediction risk")
            elif confidence > 0.8:
                risk_score -= 0.5
                risk_factors.append(f"High model confidence ({confidence:.1%}) supports prediction")
            
            # Model consensus analysis
            if ml_scores and len(ml_scores) > 1:
                scores = [v for k, v in ml_scores.items() if k != 'composite_score']
                if scores:
                    score_variance = max(scores) - min(scores)
                    
                    if score_variance > 0.5:
                        risk_score += 2.0
                        risk_factors.append(f"High model disagreement (variance: {score_variance:.2f}) increases uncertainty")
                    elif score_variance > 0.3:
                        risk_score += 1.0
                        risk_factors.append(f"Moderate model disagreement (variance: {score_variance:.2f}) adds risk")
                    elif score_variance < 0.1:
                        risk_score -= 0.5
                        risk_factors.append(f"Strong model consensus (variance: {score_variance:.2f}) reduces risk")
            
            # Composite score extremity risk
            composite_score = ml_scores.get('composite_score', 0.5)
            if composite_score > 0.95 or composite_score < 0.05:
                risk_score += 1.0
                risk_factors.append(f"Extreme prediction score ({composite_score:.2f}) may indicate model overconfidence")
            elif composite_score > 0.9 or composite_score < 0.1:
                risk_score += 0.5
                risk_factors.append(f"Very strong prediction score ({composite_score:.2f}) requires validation")
            
            # Model coverage analysis
            if not ml_scores or len(ml_scores) <= 1:
                risk_score += 1.5
                risk_factors.append("Limited model coverage increases prediction risk")
            
            # Neutral prediction risk
            if 0.45 <= composite_score <= 0.55 and confidence < 0.6:
                risk_score += 1.0
                risk_factors.append("Neutral prediction with low confidence suggests high uncertainty")
            
            risk_score = max(1.0, min(10.0, risk_score))
            
            return {
                'score': risk_score,
                'factors': risk_factors,
                'category': 'model_risk',
                'assessment': self._get_risk_assessment_text(risk_score)
            }
            
        except Exception as e:
            self.logger.error("Error assessing model risk", error=str(e))
            return {'score': 7.0, 'factors': ['Model risk assessment error'], 'category': 'model_risk'}
    
    async def _assess_sentiment_risk(self, indicators: Dict[str, float], recommendation: str) -> Dict[str, Any]:
        """Assess market sentiment and momentum-related risks"""
        try:
            risk_score = 5.0
            risk_factors = []
            
            # RSI momentum extremes
            rsi = indicators.get('rsi', 50.0)
            if recommendation in ['BUY', 'STRONG_BUY'] and rsi > 70:
                risk_score += 2.0
                risk_factors.append(f"Bullish recommendation with overbought RSI ({rsi:.1f}) creates sentiment risk")
            elif recommendation in ['SELL', 'STRONG_SELL'] and rsi < 30:
                risk_score += 2.0
                risk_factors.append(f"Bearish recommendation with oversold RSI ({rsi:.1f}) may face reversal")
            
            # Trend momentum vs recommendation alignment
            trend_direction = indicators.get('trend_direction', 'neutral')
            trend_strength = indicators.get('trend_strength', 0.0)
            
            if ((recommendation in ['BUY', 'STRONG_BUY'] and trend_direction == 'bearish') or
                (recommendation in ['SELL', 'STRONG_SELL'] and trend_direction == 'bullish')) and trend_strength > 0.5:
                risk_score += 2.0
                risk_factors.append(f"Recommendation against strong {trend_direction} trend increases risk")
            
            # Price momentum extremes
            price_change_percent = indicators.get('price_change_percent', 0.0)
            if abs(price_change_percent) > 15:
                risk_score += 2.0
                direction = "positive" if price_change_percent > 0 else "negative"
                risk_factors.append(f"Extreme {direction} momentum ({price_change_percent:+.1f}%) suggests sentiment exhaustion risk")
            elif abs(price_change_percent) > 8:
                risk_score += 1.0
                risk_factors.append(f"Strong momentum ({price_change_percent:+.1f}%) may face reversal")
            
            # Volume-price divergence (sentiment warning)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if abs(price_change_percent) > 5 and volume_ratio < 0.8:
                risk_score += 1.0
                risk_factors.append("Price movement without volume support suggests weak sentiment")
            
            # MACD momentum divergence
            macd = indicators.get('macd', 0.0)
            macd_signal = indicators.get('macd_signal', 0.0)
            if ((macd < macd_signal and recommendation in ['BUY', 'STRONG_BUY']) or
                (macd > macd_signal and recommendation in ['SELL', 'STRONG_SELL'])):
                risk_score += 1.0
                risk_factors.append("MACD momentum diverges from recommendation")
            
            # Bollinger Band squeeze (low sentiment, potential breakout risk)
            bb_width = indicators.get('bb_width', 0.0)
            if bb_width < 0.05:
                risk_score += 1.0
                risk_factors.append("Bollinger Band squeeze suggests impending volatility breakout")
            
            risk_score = max(1.0, min(10.0, risk_score))
            
            return {
                'score': risk_score,
                'factors': risk_factors,
                'category': 'sentiment_risk',
                'assessment': self._get_risk_assessment_text(risk_score)
            }
            
        except Exception as e:
            self.logger.error("Error assessing sentiment risk", error=str(e))
            return {'score': 7.0, 'factors': ['Sentiment risk assessment error'], 'category': 'sentiment_risk'}
    
    async def _calculate_composite_risk_score(self, risk_scores: Dict[str, Dict[str, Any]]) -> float:
        """Calculate weighted composite risk score"""
        try:
            total_weighted_score = 0.0
            total_weight = 0.0
            
            for category, risk_data in risk_scores.items():
                if category in self.risk_categories:
                    weight = self.risk_categories[category]['weight']
                    score = risk_data.get('score', 5.0)
                    
                    total_weighted_score += score * weight
                    total_weight += weight
            
            if total_weight == 0:
                return 5.0  # Default medium risk
            
            composite_score = total_weighted_score / total_weight
            return max(1.0, min(10.0, composite_score))
            
        except Exception as e:
            self.logger.error("Error calculating composite risk score", error=str(e))
            return 7.0  # Higher risk if calculation fails
    
    async def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level from numeric score"""
        try:
            if risk_score <= self.risk_thresholds['low_risk']:
                return 'low'
            elif risk_score <= self.risk_thresholds['medium_risk']:
                return 'medium'
            elif risk_score <= self.risk_thresholds['high_risk']:
                return 'high'
            else:
                return 'very_high'
        except Exception:
            return 'high'
    
    def _get_risk_assessment_text(self, risk_score: float) -> str:
        """Get descriptive text for risk score"""
        try:
            risk_level = int(round(risk_score))
            return self.risk_scale.get(risk_level, 'medium')
        except Exception:
            return 'medium'
    
    async def _identify_key_risks(self, risk_scores: Dict[str, Dict[str, Any]], 
                                indicators: Dict[str, float], ml_scores: Dict[str, float]) -> List[str]:
        """Identify the most significant risk factors"""
        try:
            key_risks = []
            
            # Get highest risk categories
            sorted_risks = sorted(risk_scores.items(), key=lambda x: x[1].get('score', 5.0), reverse=True)
            
            # Add top risk factors from highest-scoring categories
            for category, risk_data in sorted_risks[:3]:  # Top 3 risk categories
                factors = risk_data.get('factors', [])
                if factors:
                    key_risks.extend(factors[:2])  # Top 2 factors per category
            
            # Add specific high-impact risks
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.4:
                key_risks.append(f"Extreme volatility ({volatility:.1%}) creates significant downside risk")
            
            confidence = 0.5  # Default if not available
            if ml_scores:
                confidence = ml_scores.get('confidence', 0.5)
            
            if confidence < 0.4:
                key_risks.append(f"Low prediction confidence ({confidence:.1%}) increases decision risk")
            
            return key_risks[:5]  # Limit to top 5 key risks
            
        except Exception as e:
            self.logger.error("Error identifying key risks", error=str(e))
            return ["Risk identification error - exercise additional caution"]
    
    async def _generate_mitigation_strategies(self, risk_scores: Dict[str, Dict[str, Any]], 
                                            indicators: Dict[str, float], recommendation: str) -> List[str]:
        """Generate risk mitigation strategies"""
        try:
            strategies = []
            
            # Volatility mitigation
            volatility_risk = risk_scores.get('volatility_risk', {}).get('score', 5.0)
            if volatility_risk > 7.0:
                strategies.append("Use smaller position sizes and wider stop-losses due to high volatility")
                strategies.append("Consider options strategies to limit downside risk")
            elif volatility_risk > 6.0:
                strategies.append("Implement gradual position building to reduce timing risk")
            
            # Liquidity mitigation
            liquidity_risk = risk_scores.get('liquidity_risk', {}).get('score', 5.0)
            if liquidity_risk > 6.0:
                strategies.append("Execute trades gradually to minimize market impact")
                strategies.append("Use limit orders instead of market orders")
            
            # Technical risk mitigation
            technical_risk = risk_scores.get('technical_risk', {}).get('score', 5.0)
            if technical_risk > 6.0:
                rsi = indicators.get('rsi', 50.0)
                if rsi > 70:
                    strategies.append("Wait for RSI to normalize before initiating bullish positions")
                elif rsi < 30:
                    strategies.append("Consider scaling into positions as RSI improves")
            
            # Model risk mitigation
            model_risk = risk_scores.get('model_risk', {}).get('score', 5.0)
            if model_risk > 6.0:
                strategies.append("Increase monitoring frequency due to model uncertainty")
                strategies.append("Consider reducing position size until model confidence improves")
            
            # General high-risk mitigation
            composite_risk = await self._calculate_composite_risk_score(risk_scores)
            if composite_risk > 7.0:
                strategies.append("Implement strict stop-loss levels and position size limits")
                strategies.append("Increase diversification to reduce concentration risk")
            
            return strategies[:5]  # Limit to top 5 strategies
            
        except Exception as e:
            self.logger.error("Error generating mitigation strategies", error=str(e))
            return ["Implement conservative risk management practices"]
    
    async def _analyze_risk_factors(self, risk_scores: Dict[str, Dict[str, Any]], 
                                  indicators: Dict[str, float], ml_scores: Dict[str, float]) -> Dict[str, Any]:
        """Analyze risk factors in detail"""
        try:
            analysis = {
                'primary_risk_drivers': [],
                'secondary_risk_factors': [],
                'risk_correlations': {},
                'time_sensitivity': {},
                'impact_assessment': {}
            }
            
            # Primary risk drivers (score > 7.0)
            for category, risk_data in risk_scores.items():
                score = risk_data.get('score', 5.0)
                if score > 7.0:
                    analysis['primary_risk_drivers'].append({
                        'category': category,
                        'score': score,
                        'impact': 'high',
                        'description': self.risk_categories.get(category, {}).get('description', '')
                    })
                elif score > 6.0:
                    analysis['secondary_risk_factors'].append({
                        'category': category,
                        'score': score,
                        'impact': 'moderate',
                        'description': self.risk_categories.get(category, {}).get('description', '')
                    })
            
            # Risk correlations
            volatility = indicators.get('volatility', 0.2)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            
            if volatility > 0.3 and volume_ratio < 0.5:
                analysis['risk_correlations']['volatility_liquidity'] = "High volatility with low volume creates compounded execution risk"
            
            # Time sensitivity
            rsi = indicators.get('rsi', 50.0)
            if rsi > 80 or rsi < 20:
                analysis['time_sensitivity']['technical_reversal'] = "Extreme RSI levels suggest immediate reversal risk"
            
            # Impact assessment
            composite_risk = await self._calculate_composite_risk_score(risk_scores)
            if composite_risk > 8.0:
                analysis['impact_assessment']['overall'] = "Very high risk environment requires immediate attention"
            elif composite_risk > 6.0:
                analysis['impact_assessment']['overall'] = "Elevated risk requires enhanced monitoring"
            
            return analysis
            
        except Exception as e:
            self.logger.error("Error analyzing risk factors", error=str(e))
            return {'error': str(e)}
    
    async def _recommend_position_sizing(self, risk_score: float, confidence: float, recommendation: str) -> Dict[str, Any]:
        """Recommend position sizing based on risk assessment"""
        try:
            sizing = {
                'recommendation': 'normal',
                'multiplier': 1.0,
                'reasoning': '',
                'max_position_percent': 5.0,
                'stop_loss_percentage': 5.0
            }
            
            # Base position sizing on risk score
            if risk_score > 8.0:
                sizing['recommendation'] = 'very_small'
                sizing['multiplier'] = 0.3
                sizing['max_position_percent'] = 1.0
                sizing['stop_loss_percentage'] = 3.0
                sizing['reasoning'] = "Very high risk requires minimal position size"
            elif risk_score > 6.5:
                sizing['recommendation'] = 'small'
                sizing['multiplier'] = 0.5
                sizing['max_position_percent'] = 2.5
                sizing['stop_loss_percentage'] = 4.0
                sizing['reasoning'] = "High risk suggests reduced position size"
            elif risk_score > 5.0:
                sizing['recommendation'] = 'reduced'
                sizing['multiplier'] = 0.75
                sizing['max_position_percent'] = 3.5
                sizing['stop_loss_percentage'] = 5.0
                sizing['reasoning'] = "Moderate risk recommends slightly smaller position"
            elif risk_score < 3.0:
                sizing['recommendation'] = 'large'
                sizing['multiplier'] = 1.5
                sizing['max_position_percent'] = 7.5
                sizing['stop_loss_percentage'] = 7.0
                sizing['reasoning'] = "Low risk allows larger position size"
            
            # Adjust for confidence
            if confidence < 0.5:
                sizing['multiplier'] *= 0.7
                sizing['reasoning'] += " (reduced for low confidence)"
            elif confidence > 0.8:
                sizing['multiplier'] *= 1.2
                sizing['reasoning'] += " (increased for high confidence)"
            
            # Adjust for recommendation strength
            if recommendation in ['STRONG_BUY', 'STRONG_SELL']:
                sizing['multiplier'] *= 1.1
                sizing['reasoning'] += " (slight increase for strong conviction)"
            
            # Ensure reasonable bounds
            sizing['multiplier'] = max(0.1, min(2.0, sizing['multiplier']))
            sizing['max_position_percent'] = max(0.5, min(10.0, sizing['max_position_percent']))
            
            return sizing
            
        except Exception as e:
            self.logger.error("Error recommending position sizing", error=str(e))
            return {
                'recommendation': 'small',
                'multiplier': 0.5,
                'reasoning': 'Conservative sizing due to assessment error',
                'max_position_percent': 2.0,
                'stop_loss_percentage': 3.0
            }
    
    async def _determine_monitoring_requirements(self, risk_scores: Dict[str, Dict[str, Any]], composite_risk: float) -> List[str]:
        """Determine monitoring requirements based on risk assessment"""
        try:
            requirements = []
            
            # High-risk monitoring
            if composite_risk > 7.0:
                requirements.append("Monitor position every 15-30 minutes during market hours")
                requirements.append("Set up real-time alerts for 2% price movements")
            elif composite_risk > 5.5:
                requirements.append("Check position hourly during active trading")
                requirements.append("Set up alerts for 3% price movements")
            else:
                requirements.append("Standard daily monitoring sufficient")
            
            # Volatility-specific monitoring
            volatility_risk = risk_scores.get('volatility_risk', {}).get('score', 5.0)
            if volatility_risk > 7.0:
                requirements.append("Monitor implied volatility changes")
                requirements.append("Track intraday price ranges vs. ATR")
            
            # Technical monitoring
            technical_risk = risk_scores.get('technical_risk', {}).get('score', 5.0)
            if technical_risk > 6.5:
                requirements.append("Watch for RSI divergences and MACD crossovers")
                requirements.append("Monitor support/resistance level breaks")
            
            # Liquidity monitoring
            liquidity_risk = risk_scores.get('liquidity_risk', {}).get('score', 5.0)
            if liquidity_risk > 6.0:
                requirements.append("Monitor daily volume trends")
                requirements.append("Track bid-ask spreads if available")
            
            return requirements[:4]  # Limit to top 4 requirements
            
        except Exception as e:
            self.logger.error("Error determining monitoring requirements", error=str(e))
            return ["Implement enhanced monitoring due to assessment error"]
    
    async def _assess_risk_horizon(self, indicators: Dict[str, float], risk_score: float) -> Dict[str, str]:
        """Assess risk factors across different time horizons"""
        try:
            horizon = {
                'immediate': 'low',      # Next few hours
                'short_term': 'medium',  # Next few days  
                'medium_term': 'medium', # Next few weeks
                'long_term': 'low'       # Next few months
            }
            
            # Immediate risk (technical extremes)
            rsi = indicators.get('rsi', 50.0)
            if rsi > 80 or rsi < 20:
                horizon['immediate'] = 'high'
            elif rsi > 70 or rsi < 30:
                horizon['immediate'] = 'medium'
            
            # Short-term risk (momentum and volatility)
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.3:
                horizon['short_term'] = 'high'
            elif risk_score > 6.0:
                horizon['short_term'] = 'medium'
            
            # Medium-term risk (trend and fundamentals)
            trend_strength = indicators.get('trend_strength', 0.0)
            if trend_strength > 0.8:
                horizon['medium_term'] = 'medium'  # Overextended trends
            elif risk_score > 7.0:
                horizon['medium_term'] = 'high'
            
            # Long-term risk (typically lower for diversified positions)
            if risk_score > 8.0:
                horizon['long_term'] = 'medium'
            
            return horizon
            
        except Exception as e:
            self.logger.error("Error assessing risk horizon", error=str(e))
            return {
                'immediate': 'medium',
                'short_term': 'medium',
                'medium_term': 'medium', 
                'long_term': 'medium'
            }
    
    async def _generate_stress_test_scenarios(self, indicators: Dict[str, float], risk_score: float) -> List[Dict[str, Any]]:
        """Generate stress test scenarios for risk assessment"""
        try:
            scenarios = []
            
            current_price = indicators.get('current_price', 100.0)
            volatility = indicators.get('volatility', 0.2)
            
            # Volatility shock scenario
            vol_shock_loss = current_price * (volatility * 2.5)  # 2.5x current volatility
            scenarios.append({
                'name': 'Volatility Shock',
                'description': 'Market volatility doubles from current levels',
                'potential_loss': vol_shock_loss,
                'probability': 'low' if volatility < 0.2 else 'medium' if volatility < 0.4 else 'high',
                'impact': 'high' if vol_shock_loss > current_price * 0.15 else 'medium'
            })
            
            # Technical breakdown scenario
            support_level = indicators.get('support_level', current_price * 0.95)
            if support_level > 0 and support_level < current_price:
                breakdown_loss = current_price - support_level
                scenarios.append({
                    'name': 'Support Level Break',
                    'description': f'Price breaks below support at ${support_level:.2f}',
                    'potential_loss': breakdown_loss,
                    'probability': 'medium' if risk_score > 6 else 'low',
                    'impact': 'high' if breakdown_loss > current_price * 0.1 else 'medium'
                })
            
            # Liquidity crisis scenario
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio < 0.5:
                scenarios.append({
                    'name': 'Liquidity Crisis',
                    'description': 'Trading volume drops significantly, widening spreads',
                    'potential_loss': current_price * 0.05,  # Spread impact
                    'probability': 'medium',
                    'impact': 'medium'
                })
            
            return scenarios[:3]  # Limit to top 3 scenarios
            
        except Exception as e:
            self.logger.error("Error generating stress test scenarios", error=str(e))
            return []
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'risk_assessment',
            'risk_categories': list(self.risk_categories.keys()),
            'risk_thresholds': self.risk_thresholds,
            'risk_scale': self.risk_scale,
            'assessment_components': [
                'market_risk_analysis',
                'technical_risk_analysis',
                'volatility_risk_analysis',
                'liquidity_risk_analysis', 
                'model_risk_analysis',
                'sentiment_risk_analysis',
                'composite_risk_calculation',
                'mitigation_strategies',
                'position_sizing_recommendations',
                'monitoring_requirements',
                'risk_horizon_analysis',
                'stress_test_scenarios'
            ],
            'features': [
                'multi_category_risk_assessment',
                'weighted_composite_scoring',
                'dynamic_position_sizing',
                'time_horizon_analysis',
                'stress_testing',
                'mitigation_strategy_generation',
                'monitoring_requirements_analysis'
            ],
            'description': 'Comprehensive risk assessment module providing multi-dimensional risk analysis and management recommendations'
        }