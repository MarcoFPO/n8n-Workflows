"""
Reasoning Generation Module - Single Function Module
Generates detailed reasoning and explanations for investment recommendations
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


class ReasoningGenerationModule(SingleFunctionModuleBase):
    """Generate comprehensive reasoning and explanations for investment recommendations"""
    
    def __init__(self, event_bus):
        super().__init__("reasoning_generation", event_bus)
        self.reasoning_templates = {
            'STRONG_BUY': "Strong bullish outlook with {confidence:.1%} confidence based on {composite_score:.2f} ML composite score",
            'BUY': "Bullish outlook with {confidence:.1%} confidence based on {composite_score:.2f} ML composite score",
            'HOLD': "Neutral outlook with {confidence:.1%} confidence, holding position recommended",
            'SELL': "Bearish outlook with {confidence:.1%} confidence based on {composite_score:.2f} ML composite score", 
            'STRONG_SELL': "Strong bearish outlook with {confidence:.1%} confidence based on {composite_score:.2f} ML composite score"
        }
        self.reasoning_categories = {
            'key_factors': [],
            'risk_factors': [],
            'supporting_indicators': [],
            'conflicting_signals': [],
            'market_context': [],
            'technical_analysis': [],
            'ml_insights': []
        }
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('reasoning.generation.request', self.process_event)
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
                'reasoning_templates_count': len(self.reasoning_templates),
                'reasoning_categories_count': len(self.reasoning_categories),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'reasoning.generation.request':
            ml_scores = event.get('ml_scores', {})
            indicators = event.get('indicators', {})
            confidence = event.get('confidence', 0.5)
            recommendation = event.get('recommendation', 'HOLD')
            symbol = event.get('symbol', 'UNKNOWN')
            
            reasoning = await self.generate_reasoning(ml_scores, indicators, confidence, recommendation, symbol)
            
            response_event = {
                'event_type': 'reasoning.generation.response',
                'reasoning': reasoning,
                'symbol': symbol,
                'recommendation': recommendation,
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def generate_reasoning(self, ml_scores: Dict[str, float], indicators: Dict[str, float], 
                               confidence: float, recommendation: str, symbol: str = "UNKNOWN") -> Dict[str, Any]:
        """Generate comprehensive reasoning for investment recommendation"""
        try:
            reasoning = {
                'summary': '',
                'key_factors': [],
                'risk_factors': [],
                'supporting_indicators': [],
                'conflicting_signals': [],
                'market_context': [],
                'technical_analysis': [],
                'ml_insights': [],
                'confidence_analysis': {},
                'recommendation_rationale': {},
                'detailed_analysis': {}
            }
            
            # Generate summary based on recommendation template
            composite_score = ml_scores.get('composite_score', 0.5)
            reasoning['summary'] = self.reasoning_templates.get(recommendation, 
                f"Investment recommendation: {recommendation}").format(
                confidence=confidence,
                composite_score=composite_score
            )
            
            # Analyze ML model insights
            reasoning['ml_insights'] = await self._analyze_ml_insights(ml_scores, confidence)
            
            # Analyze technical indicators
            reasoning['technical_analysis'] = await self._analyze_technical_indicators(indicators)
            
            # Generate key factors
            reasoning['key_factors'] = await self._identify_key_factors(ml_scores, indicators, recommendation)
            
            # Identify risk factors
            reasoning['risk_factors'] = await self._identify_risk_factors(indicators, ml_scores, confidence)
            
            # Find supporting indicators
            reasoning['supporting_indicators'] = await self._find_supporting_indicators(indicators, recommendation)
            
            # Detect conflicting signals
            reasoning['conflicting_signals'] = await self._detect_conflicting_signals(ml_scores, indicators, recommendation)
            
            # Analyze market context
            reasoning['market_context'] = await self._analyze_market_context(indicators, symbol)
            
            # Provide confidence analysis
            reasoning['confidence_analysis'] = await self._analyze_confidence_factors(confidence, ml_scores, indicators)
            
            # Generate recommendation rationale
            reasoning['recommendation_rationale'] = await self._generate_recommendation_rationale(
                recommendation, ml_scores, indicators, confidence
            )
            
            # Create detailed analysis summary
            reasoning['detailed_analysis'] = await self._create_detailed_analysis(reasoning, symbol)
            
            self.logger.debug("Reasoning generation completed",
                            symbol=symbol,
                            recommendation=recommendation,
                            key_factors_count=len(reasoning['key_factors']),
                            risk_factors_count=len(reasoning['risk_factors']))
            
            return reasoning
            
        except Exception as e:
            self.logger.error("Error generating reasoning", 
                            symbol=symbol,
                            recommendation=recommendation,
                            error=str(e))
            return {
                'summary': f'Error generating reasoning for {recommendation}',
                'key_factors': [],
                'risk_factors': [f'Analysis error: {str(e)}'],
                'supporting_indicators': [],
                'conflicting_signals': [],
                'market_context': [],
                'technical_analysis': [],
                'ml_insights': [],
                'confidence_analysis': {'error': str(e)},
                'recommendation_rationale': {'error': str(e)},
                'detailed_analysis': {'error': str(e)}
            }
    
    async def _analyze_ml_insights(self, ml_scores: Dict[str, float], confidence: float) -> Dict[str, Any]:
        """Analyze and explain ML model insights"""
        try:
            insights = {
                'model_consensus': '',
                'score_analysis': {},
                'confidence_assessment': '',
                'model_strengths': [],
                'model_concerns': []
            }
            
            # Analyze individual ML scores
            if ml_scores:
                score_analysis = {}
                
                for score_name, score_value in ml_scores.items():
                    if score_name == 'composite_score':
                        continue
                        
                    score_analysis[score_name] = {
                        'value': score_value,
                        'interpretation': self._interpret_ml_score(score_value),
                        'strength': 'strong' if abs(score_value - 0.5) > 0.3 else 'moderate' if abs(score_value - 0.5) > 0.15 else 'weak'
                    }
                
                insights['score_analysis'] = score_analysis
                
                # Analyze model consensus
                if len(ml_scores) > 1:
                    scores = [v for k, v in ml_scores.items() if k != 'composite_score']
                    score_variance = max(scores) - min(scores) if scores else 0
                    
                    if score_variance < 0.2:
                        insights['model_consensus'] = f"Strong consensus among ML models (variance: {score_variance:.2f})"
                        insights['model_strengths'].append("High agreement between different ML approaches")
                    elif score_variance < 0.4:
                        insights['model_consensus'] = f"Moderate consensus among ML models (variance: {score_variance:.2f})"
                    else:
                        insights['model_consensus'] = f"Low consensus among ML models (variance: {score_variance:.2f})"
                        insights['model_concerns'].append("Significant disagreement between ML models increases uncertainty")
            
            # Confidence assessment
            if confidence > 0.8:
                insights['confidence_assessment'] = "Very high model confidence suggests strong predictive signal"
                insights['model_strengths'].append("Exceptional model confidence in prediction")
            elif confidence > 0.6:
                insights['confidence_assessment'] = "High model confidence supports recommendation reliability"
                insights['model_strengths'].append("Strong model confidence in prediction")
            elif confidence > 0.4:
                insights['confidence_assessment'] = "Moderate model confidence requires additional validation"
            else:
                insights['confidence_assessment'] = "Low model confidence suggests high uncertainty"
                insights['model_concerns'].append("Low model confidence increases prediction risk")
            
            # Composite score insights
            composite_score = ml_scores.get('composite_score', 0.5)
            if composite_score > 0.7:
                insights['model_strengths'].append(f"Strong bullish ML composite score ({composite_score:.2f})")
            elif composite_score < 0.3:
                insights['model_strengths'].append(f"Strong bearish ML composite score ({composite_score:.2f})")
            elif 0.45 <= composite_score <= 0.55:
                insights['model_concerns'].append("ML models show neutral/uncertain outlook")
            
            return insights
            
        except Exception as e:
            self.logger.error("Error analyzing ML insights", error=str(e))
            return {'error': str(e)}
    
    def _interpret_ml_score(self, score: float) -> str:
        """Interpret individual ML score"""
        if score > 0.8:
            return "Very bullish"
        elif score > 0.65:
            return "Bullish"
        elif score > 0.55:
            return "Slightly bullish"
        elif score > 0.45:
            return "Neutral"
        elif score > 0.35:
            return "Slightly bearish"
        elif score > 0.2:
            return "Bearish"
        else:
            return "Very bearish"
    
    async def _analyze_technical_indicators(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Analyze technical indicators and their implications"""
        try:
            analysis = {
                'momentum_indicators': {},
                'trend_indicators': {},
                'volume_indicators': {},
                'volatility_indicators': {},
                'support_resistance': {},
                'overall_technical_picture': ''
            }
            
            # Momentum indicators
            rsi = indicators.get('rsi', 50.0)
            macd = indicators.get('macd', 0.0)
            macd_signal = indicators.get('macd_signal', 0.0)
            
            analysis['momentum_indicators'] = {
                'rsi': {
                    'value': rsi,
                    'condition': 'overbought' if rsi > 70 else 'oversold' if rsi < 30 else 'neutral',
                    'implication': self._interpret_rsi(rsi)
                },
                'macd': {
                    'value': macd,
                    'signal': macd_signal,
                    'crossover': 'bullish' if macd > macd_signal else 'bearish',
                    'implication': self._interpret_macd(macd, macd_signal)
                }
            }
            
            # Trend indicators
            current_price = indicators.get('current_price', 100.0)
            sma_20 = indicators.get('sma_20', current_price)
            sma_50 = indicators.get('sma_50', current_price)
            trend_strength = indicators.get('trend_strength', 0.0)
            
            analysis['trend_indicators'] = {
                'price_vs_sma20': 'above' if current_price > sma_20 else 'below',
                'price_vs_sma50': 'above' if current_price > sma_50 else 'below',
                'ma_alignment': 'bullish' if sma_20 > sma_50 else 'bearish',
                'trend_strength': {
                    'value': trend_strength,
                    'interpretation': self._interpret_trend_strength(trend_strength)
                }
            }
            
            # Volume indicators
            volume_ratio = indicators.get('volume_ratio', 1.0)
            analysis['volume_indicators'] = {
                'volume_ratio': volume_ratio,
                'volume_condition': 'high' if volume_ratio > 1.5 else 'low' if volume_ratio < 0.5 else 'normal',
                'volume_confirmation': self._interpret_volume(volume_ratio)
            }
            
            # Volatility indicators
            volatility = indicators.get('volatility', 0.2)
            atr_percentage = indicators.get('atr_percentage', 0.0)
            analysis['volatility_indicators'] = {
                'volatility_level': 'high' if volatility > 0.3 else 'low' if volatility < 0.15 else 'normal',
                'atr_percentage': atr_percentage,
                'risk_assessment': self._interpret_volatility(volatility)
            }
            
            # Support/Resistance
            support_level = indicators.get('support_level', 0.0)
            resistance_level = indicators.get('resistance_level', 0.0)
            if support_level > 0 and resistance_level > 0:
                price_position = (current_price - support_level) / (resistance_level - support_level) if resistance_level > support_level else 0.5
                analysis['support_resistance'] = {
                    'support_level': support_level,
                    'resistance_level': resistance_level,
                    'price_position': price_position,
                    'position_interpretation': self._interpret_price_position(price_position)
                }
            
            # Overall technical picture
            analysis['overall_technical_picture'] = await self._synthesize_technical_picture(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error("Error analyzing technical indicators", error=str(e))
            return {'error': str(e)}
    
    def _interpret_rsi(self, rsi: float) -> str:
        """Interpret RSI value"""
        if rsi > 80:
            return "Extremely overbought, potential reversal signal"
        elif rsi > 70:
            return "Overbought conditions, caution advised"
        elif rsi < 20:
            return "Extremely oversold, potential buying opportunity"
        elif rsi < 30:
            return "Oversold conditions, potential bounce"
        elif 40 <= rsi <= 60:
            return "Neutral momentum, no clear directional bias"
        else:
            return "Moderate momentum conditions"
    
    def _interpret_macd(self, macd: float, macd_signal: float) -> str:
        """Interpret MACD indicators"""
        if macd > macd_signal and macd > 0:
            return "Strong bullish momentum above zero line"
        elif macd > macd_signal:
            return "Bullish crossover but below zero line"
        elif macd < macd_signal and macd < 0:
            return "Strong bearish momentum below zero line"
        elif macd < macd_signal:
            return "Bearish crossover but above zero line"
        else:
            return "MACD at signal line, neutral momentum"
    
    def _interpret_trend_strength(self, trend_strength: float) -> str:
        """Interpret trend strength"""
        if trend_strength > 0.8:
            return "Very strong trend"
        elif trend_strength > 0.6:
            return "Strong trend"
        elif trend_strength > 0.4:
            return "Moderate trend"
        elif trend_strength > 0.2:
            return "Weak trend"
        else:
            return "No clear trend"
    
    def _interpret_volume(self, volume_ratio: float) -> str:
        """Interpret volume conditions"""
        if volume_ratio > 2.0:
            return "Exceptionally high volume confirms price movement"
        elif volume_ratio > 1.5:
            return "High volume supports price action"
        elif volume_ratio < 0.3:
            return "Very low volume suggests weak conviction"
        elif volume_ratio < 0.5:
            return "Low volume may indicate lack of interest"
        else:
            return "Normal volume levels"
    
    def _interpret_volatility(self, volatility: float) -> str:
        """Interpret volatility levels"""
        if volatility > 0.4:
            return "High volatility increases risk and opportunity"
        elif volatility > 0.25:
            return "Elevated volatility requires careful position sizing"
        elif volatility < 0.1:
            return "Low volatility suggests stable price environment"
        else:
            return "Normal volatility levels"
    
    def _interpret_price_position(self, position: float) -> str:
        """Interpret price position between support and resistance"""
        if position > 0.8:
            return "Near resistance, potential selling pressure"
        elif position > 0.6:
            return "Upper range, approaching resistance"
        elif position < 0.2:
            return "Near support, potential buying opportunity"
        elif position < 0.4:
            return "Lower range, approaching support"
        else:
            return "Middle range between support and resistance"
    
    async def _synthesize_technical_picture(self, analysis: Dict[str, Any]) -> str:
        """Synthesize overall technical analysis picture"""
        try:
            positive_signals = 0
            negative_signals = 0
            
            # Count positive/negative technical signals
            if analysis.get('momentum_indicators', {}).get('rsi', {}).get('condition') == 'oversold':
                positive_signals += 1
            elif analysis.get('momentum_indicators', {}).get('rsi', {}).get('condition') == 'overbought':
                negative_signals += 1
            
            if analysis.get('momentum_indicators', {}).get('macd', {}).get('crossover') == 'bullish':
                positive_signals += 1
            elif analysis.get('momentum_indicators', {}).get('macd', {}).get('crossover') == 'bearish':
                negative_signals += 1
            
            if analysis.get('trend_indicators', {}).get('ma_alignment') == 'bullish':
                positive_signals += 1
            elif analysis.get('trend_indicators', {}).get('ma_alignment') == 'bearish':
                negative_signals += 1
            
            if analysis.get('volume_indicators', {}).get('volume_condition') == 'high':
                positive_signals += 0.5  # Volume is confirmation, not directional
            
            # Generate synthesis
            if positive_signals > negative_signals + 1:
                return "Technical indicators show predominantly bullish signals"
            elif negative_signals > positive_signals + 1:
                return "Technical indicators show predominantly bearish signals"
            else:
                return "Technical indicators show mixed signals with no clear consensus"
                
        except Exception as e:
            return "Unable to synthesize technical picture"
    
    async def _identify_key_factors(self, ml_scores: Dict[str, float], indicators: Dict[str, float], recommendation: str) -> List[str]:
        """Identify key factors supporting the recommendation"""
        try:
            key_factors = []
            
            # ML-based factors
            composite_score = ml_scores.get('composite_score', 0.5)
            if recommendation in ['STRONG_BUY', 'BUY'] and composite_score > 0.6:
                key_factors.append(f"Strong ML composite score of {composite_score:.2f} supports bullish outlook")
            elif recommendation in ['STRONG_SELL', 'SELL'] and composite_score < 0.4:
                key_factors.append(f"Low ML composite score of {composite_score:.2f} supports bearish outlook")
            
            # Technical factors
            rsi = indicators.get('rsi', 50.0)
            if recommendation in ['STRONG_BUY', 'BUY'] and rsi < 30:
                key_factors.append(f"RSI oversold at {rsi:.1f} suggests potential upside")
            elif recommendation in ['STRONG_SELL', 'SELL'] and rsi > 70:
                key_factors.append(f"RSI overbought at {rsi:.1f} suggests potential downside")
            
            # Trend factors
            trend_strength = indicators.get('trend_strength', 0.0)
            trend_direction = indicators.get('trend_direction', 'neutral')
            if trend_strength > 0.5 and ((trend_direction == 'bullish' and recommendation in ['STRONG_BUY', 'BUY']) or 
                                       (trend_direction == 'bearish' and recommendation in ['STRONG_SELL', 'SELL'])):
                key_factors.append(f"Strong {trend_direction} trend (strength: {trend_strength:.2f}) aligns with recommendation")
            
            # Volume factors
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:
                key_factors.append(f"High volume ({volume_ratio:.1f}x average) confirms price action")
            
            # Price action factors
            current_price = indicators.get('current_price', 100.0)
            sma_20 = indicators.get('sma_20', current_price)
            sma_50 = indicators.get('sma_50', current_price)
            
            if recommendation in ['STRONG_BUY', 'BUY'] and current_price > sma_20 > sma_50:
                key_factors.append(f"Price trading above both 20-day (${sma_20:.2f}) and 50-day (${sma_50:.2f}) moving averages")
            elif recommendation in ['STRONG_SELL', 'SELL'] and current_price < sma_20 < sma_50:
                key_factors.append(f"Price trading below both 20-day (${sma_20:.2f}) and 50-day (${sma_50:.2f}) moving averages")
            
            return key_factors[:5]  # Limit to top 5 key factors
            
        except Exception as e:
            self.logger.error("Error identifying key factors", error=str(e))
            return ["Error analyzing key factors"]
    
    async def _identify_risk_factors(self, indicators: Dict[str, float], ml_scores: Dict[str, float], confidence: float) -> List[str]:
        """Identify risk factors that could affect the recommendation"""
        try:
            risk_factors = []
            
            # Confidence risk
            if confidence < 0.4:
                risk_factors.append(f"Low model confidence ({confidence:.1%}) increases prediction uncertainty")
            
            # Volatility risk
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.3:
                risk_factors.append(f"High volatility ({volatility:.1%}) increases price risk and potential losses")
            
            # RSI extremes
            rsi = indicators.get('rsi', 50.0)
            if rsi > 80:
                risk_factors.append(f"Extremely overbought RSI ({rsi:.1f}) suggests potential reversal risk")
            elif rsi < 20:
                risk_factors.append(f"Extremely oversold RSI ({rsi:.1f}) may indicate continued weakness")
            
            # Volume risk
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio < 0.3:
                risk_factors.append(f"Very low volume ({volume_ratio:.1f}x average) may indicate liquidity issues")
            
            # Model disagreement risk
            if ml_scores and len(ml_scores) > 1:
                scores = [v for k, v in ml_scores.items() if k != 'composite_score']
                if scores and (max(scores) - min(scores)) > 0.4:
                    risk_factors.append("High disagreement between ML models increases prediction risk")
            
            # Trend reversal risk
            trend_strength = indicators.get('trend_strength', 0.0)
            if trend_strength > 0.8:
                risk_factors.append(f"Very strong trend (strength: {trend_strength:.2f}) may be overextended")
            
            # Support/resistance risk
            support_level = indicators.get('support_level', 0.0)
            resistance_level = indicators.get('resistance_level', 0.0)
            current_price = indicators.get('current_price', 100.0)
            
            if resistance_level > 0 and current_price > resistance_level * 0.95:
                risk_factors.append(f"Price near resistance level (${resistance_level:.2f}) may face selling pressure")
            elif support_level > 0 and current_price < support_level * 1.05:
                risk_factors.append(f"Price near support level (${support_level:.2f}) may face further downside")
            
            return risk_factors[:5]  # Limit to top 5 risk factors
            
        except Exception as e:
            self.logger.error("Error identifying risk factors", error=str(e))
            return ["Error analyzing risk factors"]
    
    async def _find_supporting_indicators(self, indicators: Dict[str, float], recommendation: str) -> List[str]:
        """Find technical indicators that support the recommendation"""
        try:
            supporting = []
            
            # MACD support
            macd = indicators.get('macd', 0.0)
            macd_signal = indicators.get('macd_signal', 0.0)
            
            if recommendation in ['STRONG_BUY', 'BUY'] and macd > macd_signal:
                supporting.append("MACD line above signal line indicates bullish momentum")
            elif recommendation in ['STRONG_SELL', 'SELL'] and macd < macd_signal:
                supporting.append("MACD line below signal line indicates bearish momentum")
            
            # Moving average support
            current_price = indicators.get('current_price', 100.0)
            sma_20 = indicators.get('sma_20', current_price)
            
            if recommendation in ['STRONG_BUY', 'BUY'] and current_price > sma_20:
                supporting.append(f"Price (${current_price:.2f}) trading above 20-day moving average (${sma_20:.2f})")
            elif recommendation in ['STRONG_SELL', 'SELL'] and current_price < sma_20:
                supporting.append(f"Price (${current_price:.2f}) trading below 20-day moving average (${sma_20:.2f})")
            
            # Volume support
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.2:
                supporting.append(f"Above-average volume ({volume_ratio:.1f}x) supports price movement")
            
            # Trend support
            trend_direction = indicators.get('trend_direction', 'neutral')
            trend_strength = indicators.get('trend_strength', 0.0)
            
            if ((recommendation in ['STRONG_BUY', 'BUY'] and trend_direction == 'bullish') or
                (recommendation in ['STRONG_SELL', 'SELL'] and trend_direction == 'bearish')) and trend_strength > 0.3:
                supporting.append(f"Established {trend_direction} trend supports recommendation")
            
            # Bollinger Bands support
            bb_percent_b = indicators.get('bb_percent_b', 0.5)
            if recommendation in ['STRONG_BUY', 'BUY'] and bb_percent_b < 0.2:
                supporting.append(f"Price near lower Bollinger Band (%B: {bb_percent_b:.2f}) suggests oversold conditions")
            elif recommendation in ['STRONG_SELL', 'SELL'] and bb_percent_b > 0.8:
                supporting.append(f"Price near upper Bollinger Band (%B: {bb_percent_b:.2f}) suggests overbought conditions")
            
            return supporting[:4]  # Limit to top 4 supporting indicators
            
        except Exception as e:
            self.logger.error("Error finding supporting indicators", error=str(e))
            return ["Error analyzing supporting indicators"]
    
    async def _detect_conflicting_signals(self, ml_scores: Dict[str, float], indicators: Dict[str, float], recommendation: str) -> List[str]:
        """Detect signals that conflict with the recommendation"""
        try:
            conflicts = []
            
            # RSI conflicts
            rsi = indicators.get('rsi', 50.0)
            if recommendation in ['STRONG_BUY', 'BUY'] and rsi > 70:
                conflicts.append(f"RSI overbought ({rsi:.1f}) conflicts with bullish recommendation")
            elif recommendation in ['STRONG_SELL', 'SELL'] and rsi < 30:
                conflicts.append(f"RSI oversold ({rsi:.1f}) conflicts with bearish recommendation")
            
            # Moving average conflicts
            current_price = indicators.get('current_price', 100.0)
            sma_20 = indicators.get('sma_20', current_price)
            sma_50 = indicators.get('sma_50', current_price)
            
            if recommendation in ['STRONG_BUY', 'BUY'] and current_price < sma_50:
                conflicts.append(f"Price below 50-day MA (${sma_50:.2f}) challenges bullish outlook")
            elif recommendation in ['STRONG_SELL', 'SELL'] and current_price > sma_50:
                conflicts.append(f"Price above 50-day MA (${sma_50:.2f}) challenges bearish outlook")
            
            # Volume conflicts
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio < 0.5:
                conflicts.append(f"Low volume ({volume_ratio:.1f}x average) provides weak confirmation")
            
            # ML score conflicts
            if ml_scores and len(ml_scores) > 1:
                scores = [v for k, v in ml_scores.items() if k != 'composite_score']
                if scores:
                    min_score = min(scores)
                    max_score = max(scores)
                    
                    if recommendation in ['STRONG_BUY', 'BUY'] and min_score < 0.4:
                        conflicts.append(f"Some ML models show bearish signals (min score: {min_score:.2f})")
                    elif recommendation in ['STRONG_SELL', 'SELL'] and max_score > 0.6:
                        conflicts.append(f"Some ML models show bullish signals (max score: {max_score:.2f})")
            
            # Trend conflicts
            trend_direction = indicators.get('trend_direction', 'neutral')
            if ((recommendation in ['STRONG_BUY', 'BUY'] and trend_direction == 'bearish') or
                (recommendation in ['STRONG_SELL', 'SELL'] and trend_direction == 'bullish')):
                conflicts.append(f"Established {trend_direction} trend conflicts with recommendation")
            
            return conflicts[:3]  # Limit to top 3 conflicts
            
        except Exception as e:
            self.logger.error("Error detecting conflicting signals", error=str(e))
            return ["Error analyzing conflicting signals"]
    
    async def _analyze_market_context(self, indicators: Dict[str, float], symbol: str) -> List[str]:
        """Analyze broader market context"""
        try:
            context = []
            
            # Volatility regime
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.3:
                context.append("High volatility environment suggests increased market uncertainty")
            elif volatility < 0.15:
                context.append("Low volatility environment suggests stable market conditions")
            
            # Price momentum
            price_change_percent = indicators.get('price_change_percent', 0.0)
            if abs(price_change_percent) > 5:
                direction = "positive" if price_change_percent > 0 else "negative"
                context.append(f"Strong recent price momentum ({price_change_percent:+.1f}%) shows {direction} sentiment")
            
            # Volume environment
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 2.0:
                context.append("Unusually high trading volume suggests heightened investor interest")
            elif volume_ratio < 0.3:
                context.append("Low trading volume suggests reduced investor engagement")
            
            # Market structure
            support_level = indicators.get('support_level', 0.0)
            resistance_level = indicators.get('resistance_level', 0.0)
            if support_level > 0 and resistance_level > 0:
                range_pct = ((resistance_level - support_level) / support_level) * 100
                if range_pct < 5:
                    context.append(f"Narrow trading range ({range_pct:.1f}%) suggests consolidation phase")
                elif range_pct > 15:
                    context.append(f"Wide trading range ({range_pct:.1f}%) indicates high volatility")
            
            return context[:3]  # Limit to top 3 context items
            
        except Exception as e:
            self.logger.error("Error analyzing market context", error=str(e))
            return ["Error analyzing market context"]
    
    async def _analyze_confidence_factors(self, confidence: float, ml_scores: Dict[str, float], indicators: Dict[str, float]) -> Dict[str, Any]:
        """Analyze factors affecting confidence in the recommendation"""
        try:
            analysis = {
                'confidence_level': 'very_high' if confidence > 0.8 else 'high' if confidence > 0.6 else 'moderate' if confidence > 0.4 else 'low',
                'confidence_drivers': [],
                'confidence_detractors': [],
                'reliability_assessment': ''
            }
            
            # Confidence drivers
            if confidence > 0.7:
                analysis['confidence_drivers'].append("Strong model confidence suggests reliable prediction")
            
            if ml_scores and len(ml_scores) > 1:
                scores = [v for k, v in ml_scores.items() if k != 'composite_score']
                if scores and (max(scores) - min(scores)) < 0.2:
                    analysis['confidence_drivers'].append("High agreement between ML models")
            
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:
                analysis['confidence_drivers'].append("High volume supports signal reliability")
            
            # Confidence detractors
            if confidence < 0.5:
                analysis['confidence_detractors'].append("Low model confidence increases uncertainty")
            
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.3:
                analysis['confidence_detractors'].append("High volatility reduces prediction reliability")
            
            if volume_ratio < 0.5:
                analysis['confidence_detractors'].append("Low volume weakens signal confirmation")
            
            # Reliability assessment
            if len(analysis['confidence_drivers']) > len(analysis['confidence_detractors']):
                analysis['reliability_assessment'] = "Multiple factors support recommendation reliability"
            elif len(analysis['confidence_detractors']) > len(analysis['confidence_drivers']):
                analysis['reliability_assessment'] = "Several factors reduce recommendation reliability"
            else:
                analysis['reliability_assessment'] = "Mixed factors suggest moderate reliability"
            
            return analysis
            
        except Exception as e:
            self.logger.error("Error analyzing confidence factors", error=str(e))
            return {'error': str(e)}
    
    async def _generate_recommendation_rationale(self, recommendation: str, ml_scores: Dict[str, float], 
                                               indicators: Dict[str, float], confidence: float) -> Dict[str, Any]:
        """Generate detailed rationale for the specific recommendation"""
        try:
            rationale = {
                'primary_justification': '',
                'secondary_factors': [],
                'risk_considerations': '',
                'timing_assessment': '',
                'strength_assessment': ''
            }
            
            composite_score = ml_scores.get('composite_score', 0.5)
            
            # Primary justification
            if recommendation == 'STRONG_BUY':
                rationale['primary_justification'] = f"Exceptionally strong ML signal ({composite_score:.2f}) with high confidence ({confidence:.1%}) suggests significant upside potential"
                rationale['strength_assessment'] = "Very strong conviction recommendation"
            elif recommendation == 'BUY':
                rationale['primary_justification'] = f"Positive ML signal ({composite_score:.2f}) with decent confidence ({confidence:.1%}) suggests upward potential"
                rationale['strength_assessment'] = "Moderate conviction recommendation"
            elif recommendation == 'SELL':
                rationale['primary_justification'] = f"Negative ML signal ({composite_score:.2f}) with decent confidence ({confidence:.1%}) suggests downward risk"
                rationale['strength_assessment'] = "Moderate conviction recommendation"
            elif recommendation == 'STRONG_SELL':
                rationale['primary_justification'] = f"Exceptionally weak ML signal ({composite_score:.2f}) with high confidence ({confidence:.1%}) suggests significant downside risk"
                rationale['strength_assessment'] = "Very strong conviction recommendation"
            else:  # HOLD
                rationale['primary_justification'] = f"Neutral ML signal ({composite_score:.2f}) or low confidence ({confidence:.1%}) suggests maintaining current position"
                rationale['strength_assessment'] = "Conservative recommendation"
            
            # Secondary factors
            trend_strength = indicators.get('trend_strength', 0.0)
            if trend_strength > 0.5:
                rationale['secondary_factors'].append(f"Strong trend momentum (strength: {trend_strength:.2f})")
            
            rsi = indicators.get('rsi', 50.0)
            if recommendation in ['STRONG_BUY', 'BUY'] and rsi < 40:
                rationale['secondary_factors'].append(f"Favorable RSI level ({rsi:.1f}) suggests limited downside")
            elif recommendation in ['STRONG_SELL', 'SELL'] and rsi > 60:
                rationale['secondary_factors'].append(f"Elevated RSI level ({rsi:.1f}) suggests limited upside")
            
            # Risk considerations
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.3:
                rationale['risk_considerations'] = f"High volatility ({volatility:.1%}) requires careful position sizing and risk management"
            elif confidence < 0.5:
                rationale['risk_considerations'] = f"Low confidence ({confidence:.1%}) suggests increased monitoring and smaller position sizes"
            else:
                rationale['risk_considerations'] = "Standard risk management practices apply"
            
            # Timing assessment
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:
                rationale['timing_assessment'] = "High volume suggests good timing for position changes"
            elif volume_ratio < 0.5:
                rationale['timing_assessment'] = "Low volume suggests waiting for better entry/exit timing"
            else:
                rationale['timing_assessment'] = "Standard market conditions for position implementation"
            
            return rationale
            
        except Exception as e:
            self.logger.error("Error generating recommendation rationale", error=str(e))
            return {'error': str(e)}
    
    async def _create_detailed_analysis(self, reasoning: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Create comprehensive detailed analysis summary"""
        try:
            detailed = {
                'investment_thesis': '',
                'key_strengths': len(reasoning.get('key_factors', [])),
                'main_risks': len(reasoning.get('risk_factors', [])),
                'technical_consensus': '',
                'ml_consensus': '',
                'overall_conviction': '',
                'action_recommendations': []
            }
            
            # Investment thesis
            key_factors_count = len(reasoning.get('key_factors', []))
            risk_factors_count = len(reasoning.get('risk_factors', []))
            
            if key_factors_count > risk_factors_count:
                detailed['investment_thesis'] = f"Positive outlook for {symbol} supported by {key_factors_count} key factors outweighing {risk_factors_count} risk considerations"
            elif risk_factors_count > key_factors_count:
                detailed['investment_thesis'] = f"Cautious outlook for {symbol} with {risk_factors_count} risk factors exceeding {key_factors_count} positive factors"
            else:
                detailed['investment_thesis'] = f"Balanced outlook for {symbol} with equal weight of positive and negative factors"
            
            # Technical consensus
            technical_analysis = reasoning.get('technical_analysis', {})
            if isinstance(technical_analysis, dict) and 'overall_technical_picture' in technical_analysis:
                detailed['technical_consensus'] = technical_analysis['overall_technical_picture']
            else:
                detailed['technical_consensus'] = "Technical analysis inconclusive"
            
            # ML consensus
            ml_insights = reasoning.get('ml_insights', {})
            if isinstance(ml_insights, dict) and 'model_consensus' in ml_insights:
                detailed['ml_consensus'] = ml_insights['model_consensus']
            else:
                detailed['ml_consensus'] = "ML model consensus unavailable"
            
            # Overall conviction
            confidence_analysis = reasoning.get('confidence_analysis', {})
            if isinstance(confidence_analysis, dict):
                detailed['overall_conviction'] = confidence_analysis.get('reliability_assessment', 'Moderate conviction based on available analysis')
            
            # Action recommendations
            conflicting_signals_count = len(reasoning.get('conflicting_signals', []))
            
            if conflicting_signals_count == 0:
                detailed['action_recommendations'].append("Proceed with recommended action - signals are aligned")
            elif conflicting_signals_count <= 2:
                detailed['action_recommendations'].append("Proceed with caution - minor conflicting signals present")
            else:
                detailed['action_recommendations'].append("Exercise caution - multiple conflicting signals require careful consideration")
            
            if risk_factors_count > 3:
                detailed['action_recommendations'].append("Consider reduced position size due to elevated risk factors")
            
            detailed['action_recommendations'].append("Monitor key indicators for any changes in thesis")
            
            return detailed
            
        except Exception as e:
            self.logger.error("Error creating detailed analysis", error=str(e))
            return {'error': str(e)}
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'reasoning_generation',
            'reasoning_templates': list(self.reasoning_templates.keys()),
            'reasoning_categories': list(self.reasoning_categories.keys()),
            'supported_recommendations': ['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'],
            'analysis_components': [
                'ml_insights_analysis',
                'technical_indicators_analysis',
                'key_factors_identification',
                'risk_factors_identification',
                'supporting_indicators_analysis',
                'conflicting_signals_detection',
                'market_context_analysis',
                'confidence_factors_analysis',
                'recommendation_rationale',
                'detailed_analysis_synthesis'
            ],
            'features': [
                'comprehensive_reasoning_generation',
                'multi_factor_analysis',
                'signal_conflict_detection',
                'confidence_assessment',
                'risk_factor_identification',
                'market_context_integration',
                'technical_analysis_synthesis',
                'ml_insights_interpretation'
            ],
            'description': 'Generates comprehensive, detailed reasoning and explanations for investment recommendations using multi-factor analysis'
        }