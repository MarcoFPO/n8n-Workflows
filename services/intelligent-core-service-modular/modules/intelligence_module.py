"""
Intelligence Module für Intelligent-Core-Service
Business Intelligence und Recommendation Engine
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from backend_base_module import BackendBaseModule
from event_bus import EventType
import structlog


class IntelligenceModule(BackendBaseModule):
    """Business Intelligence und Recommendation Logic"""
    
    def __init__(self, event_bus):
        super().__init__("intelligence", event_bus)
        self.recommendation_cache = {}
        self.intelligence_rules = {}
        self.market_sentiment = {}
        self.decision_history = []
        self.cache_ttl = 120  # 2 Minuten für Intelligence-Entscheidungen
        
    async def _initialize_module(self) -> bool:
        """Initialize intelligence module"""
        try:
            self.logger.info("Initializing Intelligence Module")
            
            # Initialize intelligence rules
            self.intelligence_rules = {
                'strong_buy_threshold': 0.8,
                'buy_threshold': 0.65,
                'sell_threshold': 0.35,
                'strong_sell_threshold': 0.2,
                'confidence_minimum': 0.4,
                'volume_weight': 0.2,
                'technical_weight': 0.3,
                'ml_weight': 0.5
            }
            
            # Initialize market sentiment tracking
            self.market_sentiment = {
                'overall_sentiment': 'neutral',
                'sentiment_score': 0.5,
                'volatility_regime': 'normal',
                'last_update': datetime.now()
            }
            
            self.logger.info("Intelligence module initialized successfully",
                           rules_count=len(self.intelligence_rules))
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize intelligence module", error=str(e))
            return False
    
    async def _subscribe_to_events(self):
        """Subscribe to relevant events"""
        await self.subscribe_to_event(
            EventType.ANALYSIS_STATE_CHANGED,
            self._handle_analysis_event
        )
        await self.subscribe_to_event(
            EventType.TRADING_STATE_CHANGED,
            self._handle_trading_event
        )
        await self.subscribe_to_event(
            EventType.CONFIG_UPDATED,
            self._handle_config_event
        )
        await self.subscribe_to_event(
            EventType.SYSTEM_ALERT_RAISED,
            self._handle_system_alert_event
        )
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Main intelligence processing logic"""
        try:
            request_type = data.get('type', 'recommendation')
            
            if request_type == 'recommendation':
                return await self._process_recommendation_request(data)
            elif request_type == 'market_analysis':
                return await self._process_market_analysis(data)
            elif request_type == 'intelligence_trigger':
                return await self._process_intelligence_trigger(data)
            elif request_type == 'decision_history':
                return await self._get_decision_history()
            else:
                return {
                    'success': False,
                    'error': f'Unknown request type: {request_type}'
                }
                
        except Exception as e:
            self.logger.error("Error in intelligence processing", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _process_recommendation_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process recommendation generation request"""
        try:
            symbol = data.get('symbol', 'UNKNOWN')
            ml_scores = data.get('ml_scores', {})
            indicators = data.get('indicators', {})
            confidence = data.get('confidence', 0.5)
            
            # Check cache
            cache_key = f"{symbol}_{hash(str(sorted(ml_scores.items())))}"
            if cache_key in self.recommendation_cache:
                cache_entry = self.recommendation_cache[cache_key]
                cache_age = (datetime.now() - cache_entry['timestamp']).total_seconds()
                if cache_age < self.cache_ttl:
                    self.logger.debug("Returning cached recommendation", symbol=symbol)
                    return cache_entry['data']
            
            # Generate recommendation
            recommendation = await self._generate_recommendation(ml_scores, indicators, confidence)
            
            # Generate reasoning
            reasoning = await self._generate_reasoning(ml_scores, indicators, confidence, recommendation)
            
            # Calculate action priority
            action_priority = self._calculate_action_priority(recommendation, confidence, indicators)
            
            # Generate risk assessment
            risk_assessment = self._generate_risk_assessment(indicators, ml_scores)
            
            result = {
                'success': True,
                'symbol': symbol,
                'recommendation': recommendation,
                'confidence': confidence,
                'reasoning': reasoning,
                'action_priority': action_priority,
                'risk_assessment': risk_assessment,
                'market_context': self.market_sentiment.copy(),
                'generated_at': datetime.now().isoformat()
            }
            
            # Cache result
            self.recommendation_cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }
            
            # Store in decision history
            self.decision_history.append({
                'symbol': symbol,
                'recommendation': recommendation,
                'confidence': confidence,
                'timestamp': datetime.now(),
                'reasoning_summary': reasoning.get('summary', 'No reasoning provided')
            })
            
            # Keep only last 100 decisions
            if len(self.decision_history) > 100:
                self.decision_history = self.decision_history[-100:]
            
            # Publish intelligence event
            await self.publish_module_event(
                EventType.INTELLIGENCE_TRIGGERED,
                {
                    'symbol': symbol,
                    'recommendation': recommendation,
                    'confidence': confidence,
                    'action_priority': action_priority
                },
                f"intelligence-{symbol}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Error processing recommendation request", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _generate_recommendation(self, ml_scores: Dict[str, float], 
                                     indicators: Dict[str, float], 
                                     confidence: float) -> str:
        """Generate investment recommendation"""
        try:
            # Get composite score from ML or calculate weighted score
            if 'composite_score' in ml_scores:
                composite_score = ml_scores['composite_score']
            else:
                # Calculate composite score from available ML scores
                price_score = ml_scores.get('price_score', 0.5)
                trend_score = ml_scores.get('trend_score', 0.5)
                vol_score = ml_scores.get('volatility_score', 0.5)
                composite_score = (price_score * 0.4 + trend_score * 0.4 + vol_score * 0.2)
            
            # Adjust score based on technical indicators
            adjusted_score = await self._adjust_score_with_technical_analysis(
                composite_score, indicators
            )
            
            # Apply confidence filter
            if confidence < self.intelligence_rules['confidence_minimum']:
                return "HOLD"
            
            # Generate recommendation based on adjusted score
            if adjusted_score >= self.intelligence_rules['strong_buy_threshold']:
                return "STRONG_BUY"
            elif adjusted_score >= self.intelligence_rules['buy_threshold']:
                return "BUY"
            elif adjusted_score <= self.intelligence_rules['strong_sell_threshold']:
                return "STRONG_SELL"
            elif adjusted_score <= self.intelligence_rules['sell_threshold']:
                return "SELL"
            else:
                return "HOLD"
                
        except Exception as e:
            self.logger.error("Error generating recommendation", error=str(e))
            return "HOLD"
    
    async def _adjust_score_with_technical_analysis(self, base_score: float, 
                                                  indicators: Dict[str, float]) -> float:
        """Adjust ML score with technical analysis"""
        try:
            adjusted_score = base_score
            
            # RSI adjustment
            rsi = indicators.get('rsi', 50.0)
            if rsi > 70:  # Overbought
                adjusted_score -= 0.15
            elif rsi < 30:  # Oversold
                adjusted_score += 0.15
            elif rsi > 60:
                adjusted_score -= 0.05
            elif rsi < 40:
                adjusted_score += 0.05
            
            # MACD adjustment
            macd = indicators.get('macd', 0.0)
            macd_signal = indicators.get('macd_signal', 0.0)
            
            if macd > macd_signal and macd > 0:  # Bullish MACD
                adjusted_score += 0.1
            elif macd < macd_signal and macd < 0:  # Bearish MACD
                adjusted_score -= 0.1
            
            # Moving Average adjustment
            current_price = indicators.get('current_price', 100.0)
            sma_20 = indicators.get('sma_20', 100.0)
            sma_50 = indicators.get('sma_50', 100.0)
            
            # Price above/below moving averages
            if current_price > sma_20 > sma_50:  # Strong uptrend
                adjusted_score += 0.1
            elif current_price < sma_20 < sma_50:  # Strong downtrend
                adjusted_score -= 0.1
            elif current_price > sma_20:  # Above short MA
                adjusted_score += 0.05
            elif current_price < sma_20:  # Below short MA
                adjusted_score -= 0.05
            
            # Volume confirmation
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:  # High volume
                # Amplify the signal if volume confirms
                if adjusted_score > base_score:
                    adjusted_score += 0.05
                elif adjusted_score < base_score:
                    adjusted_score -= 0.05
            elif volume_ratio < 0.5:  # Low volume
                # Reduce signal strength on low volume
                adjustment = (adjusted_score - base_score) * 0.5
                adjusted_score = base_score + adjustment
            
            # Volatility adjustment
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.4:  # High volatility - reduce confidence
                adjustment = (adjusted_score - 0.5) * 0.8
                adjusted_score = 0.5 + adjustment
            
            # Trend strength adjustment
            trend_strength = indicators.get('trend_strength', 0.0)
            if abs(trend_strength) > 0.5:  # Strong trend
                if trend_strength > 0 and adjusted_score > 0.5:
                    adjusted_score += 0.05
                elif trend_strength < 0 and adjusted_score < 0.5:
                    adjusted_score -= 0.05
            
            # Ensure score stays within bounds
            adjusted_score = max(0.0, min(1.0, adjusted_score))
            
            return adjusted_score
            
        except Exception as e:
            self.logger.error("Error adjusting score with technical analysis", error=str(e))
            return base_score
    
    async def _generate_reasoning(self, ml_scores: Dict[str, float], 
                                indicators: Dict[str, float], 
                                confidence: float, 
                                recommendation: str) -> Dict[str, Any]:
        """Generate detailed reasoning for recommendation"""
        try:
            reasoning = {
                'summary': '',
                'key_factors': [],
                'risk_factors': [],
                'supporting_indicators': [],
                'conflicting_signals': []
            }
            
            # Generate summary based on recommendation
            composite_score = ml_scores.get('composite_score', 0.5)
            
            if recommendation in ['STRONG_BUY', 'BUY']:
                reasoning['summary'] = f"Bullish outlook with {confidence:.1%} confidence based on ML score of {composite_score:.2f}"
            elif recommendation in ['STRONG_SELL', 'SELL']:
                reasoning['summary'] = f"Bearish outlook with {confidence:.1%} confidence based on ML score of {composite_score:.2f}"
            else:
                reasoning['summary'] = f"Neutral outlook with {confidence:.1%} confidence, holding position recommended"
            
            # Analyze key factors
            rsi = indicators.get('rsi', 50.0)
            if rsi > 70:
                reasoning['risk_factors'].append(f"RSI at {rsi:.1f} indicates overbought conditions")
            elif rsi < 30:
                reasoning['key_factors'].append(f"RSI at {rsi:.1f} indicates oversold conditions")
            
            # MACD analysis
            macd = indicators.get('macd', 0.0)
            macd_signal = indicators.get('macd_signal', 0.0)
            
            if macd > macd_signal:
                reasoning['supporting_indicators'].append("MACD line above signal line (bullish momentum)")
            else:
                reasoning['supporting_indicators'].append("MACD line below signal line (bearish momentum)")
            
            # Volume analysis
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:
                reasoning['supporting_indicators'].append(f"High volume ({volume_ratio:.1f}x average) confirms price movement")
            elif volume_ratio < 0.5:
                reasoning['risk_factors'].append(f"Low volume ({volume_ratio:.1f}x average) suggests weak conviction")
            
            # Trend analysis
            trend_strength = indicators.get('trend_strength', 0.0)
            if abs(trend_strength) > 0.5:
                direction = "upward" if trend_strength > 0 else "downward"
                reasoning['key_factors'].append(f"Strong {direction} trend with strength {abs(trend_strength):.2f}")
            
            # Moving average analysis
            current_price = indicators.get('current_price', 100.0)
            sma_20 = indicators.get('sma_20', 100.0)
            sma_50 = indicators.get('sma_50', 100.0)
            
            if current_price > sma_20 > sma_50:
                reasoning['supporting_indicators'].append("Price trading above both 20-day and 50-day moving averages")
            elif current_price < sma_20 < sma_50:
                reasoning['supporting_indicators'].append("Price trading below both 20-day and 50-day moving averages")
            elif current_price > sma_20 and sma_20 < sma_50:
                reasoning['conflicting_signals'].append("Price above short-term MA but long-term trend is bearish")
            
            # ML model analysis
            if 'price_score' in ml_scores and 'trend_score' in ml_scores:
                price_score = ml_scores['price_score']
                trend_score = ml_scores['trend_score']
                
                if abs(price_score - trend_score) > 0.2:
                    reasoning['conflicting_signals'].append(f"ML models show disagreement: price model {price_score:.2f} vs trend model {trend_score:.2f}")
                else:
                    reasoning['supporting_indicators'].append("ML models show consistent signals")
            
            # Market context
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.3:
                reasoning['risk_factors'].append(f"High market volatility ({volatility:.1%}) increases risk")
            
            return reasoning
            
        except Exception as e:
            self.logger.error("Error generating reasoning", error=str(e))
            return {
                'summary': 'Error generating reasoning',
                'key_factors': [],
                'risk_factors': ['Analysis error occurred'],
                'supporting_indicators': [],
                'conflicting_signals': []
            }
    
    def _calculate_action_priority(self, recommendation: str, confidence: float, 
                                 indicators: Dict[str, float]) -> Dict[str, Any]:
        """Calculate action priority and timing"""
        try:
            priority = {
                'level': 'medium',
                'urgency': 'normal',
                'timing': 'market_hours',
                'position_size': 'normal'
            }
            
            # Base priority on recommendation strength
            if recommendation == 'STRONG_BUY':
                priority['level'] = 'high'
                priority['urgency'] = 'high' if confidence > 0.8 else 'medium'
            elif recommendation == 'STRONG_SELL':
                priority['level'] = 'high'
                priority['urgency'] = 'high' if confidence > 0.8 else 'medium'
            elif recommendation in ['BUY', 'SELL']:
                priority['level'] = 'medium'
                priority['urgency'] = 'medium' if confidence > 0.7 else 'normal'
            else:  # HOLD
                priority['level'] = 'low'
                priority['urgency'] = 'low'
            
            # Adjust based on market conditions
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.4:
                priority['urgency'] = 'high'  # High volatility requires quick action
                priority['position_size'] = 'reduced'
            elif volatility < 0.1:
                priority['urgency'] = 'low'  # Low volatility allows patience
            
            # Volume consideration
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 2.0:
                priority['urgency'] = 'high'  # Unusual volume requires attention
            
            # Trend strength consideration
            trend_strength = indicators.get('trend_strength', 0.0)
            if abs(trend_strength) > 0.7:
                priority['timing'] = 'immediate'  # Strong trends don't wait
            
            return priority
            
        except Exception as e:
            self.logger.error("Error calculating action priority", error=str(e))
            return {
                'level': 'medium',
                'urgency': 'normal',
                'timing': 'market_hours',
                'position_size': 'normal'
            }
    
    def _generate_risk_assessment(self, indicators: Dict[str, float], 
                                ml_scores: Dict[str, float]) -> Dict[str, Any]:
        """Generate comprehensive risk assessment"""
        try:
            risk_assessment = {
                'overall_risk': 'medium',
                'risk_score': 5,  # 1-10 scale
                'key_risks': [],
                'mitigation_strategies': []
            }
            
            risk_factors = 0
            
            # Volatility risk
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.4:
                risk_factors += 3
                risk_assessment['key_risks'].append(f"High volatility ({volatility:.1%}) increases price risk")
                risk_assessment['mitigation_strategies'].append("Consider reduced position size or options strategies")
            elif volatility > 0.25:
                risk_factors += 1
                risk_assessment['key_risks'].append(f"Elevated volatility ({volatility:.1%})")
            
            # Technical risk (RSI extremes)
            rsi = indicators.get('rsi', 50.0)
            if rsi > 80 or rsi < 20:
                risk_factors += 2
                risk_assessment['key_risks'].append(f"RSI at extreme level ({rsi:.1f})")
                risk_assessment['mitigation_strategies'].append("Wait for RSI normalization or use smaller position")
            
            # Liquidity risk (volume)
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio < 0.3:
                risk_factors += 2
                risk_assessment['key_risks'].append("Low volume may indicate liquidity issues")
                risk_assessment['mitigation_strategies'].append("Execute trades gradually to avoid market impact")
            
            # Model uncertainty
            if ml_scores and len(ml_scores) > 1:
                scores = list(ml_scores.values())
                score_variance = max(scores) - min(scores)
                if score_variance > 0.3:
                    risk_factors += 1
                    risk_assessment['key_risks'].append("High disagreement between ML models")
                    risk_assessment['mitigation_strategies'].append("Increase monitoring frequency")
            
            # Trend risk
            trend_strength = indicators.get('trend_strength', 0.0)
            if abs(trend_strength) > 0.8:
                risk_factors += 1
                risk_assessment['key_risks'].append("Strong trend may be overextended")
                risk_assessment['mitigation_strategies'].append("Consider profit-taking or trailing stops")
            
            # Calculate overall risk
            risk_assessment['risk_score'] = min(10, max(1, 3 + risk_factors))
            
            if risk_assessment['risk_score'] <= 3:
                risk_assessment['overall_risk'] = 'low'
            elif risk_assessment['risk_score'] <= 6:
                risk_assessment['overall_risk'] = 'medium'
            elif risk_assessment['risk_score'] <= 8:
                risk_assessment['overall_risk'] = 'high'
            else:
                risk_assessment['overall_risk'] = 'very_high'
            
            return risk_assessment
            
        except Exception as e:
            self.logger.error("Error generating risk assessment", error=str(e))
            return {
                'overall_risk': 'medium',
                'risk_score': 5,
                'key_risks': ['Risk assessment error'],
                'mitigation_strategies': ['Increase caution']
            }
    
    async def _handle_analysis_event(self, event):
        """Handle analysis state changed events"""
        try:
            self.logger.debug("Received analysis event")
            # Clear recommendation cache when new analysis is available
            self.recommendation_cache.clear()
            
            # Update market sentiment based on analysis
            symbol = event.data.get('symbol')
            indicators = event.data.get('indicators', {})
            
            if symbol and indicators:
                await self._update_market_sentiment(symbol, indicators)
                
        except Exception as e:
            self.logger.error("Error handling analysis event", error=str(e))
    
    async def _update_market_sentiment(self, symbol: str, indicators: Dict[str, float]):
        """Update overall market sentiment tracking"""
        try:
            # Simple market sentiment calculation
            rsi = indicators.get('rsi', 50.0)
            trend_strength = indicators.get('trend_strength', 0.0)
            volatility = indicators.get('volatility', 0.2)
            
            # Calculate sentiment score (0 = bearish, 1 = bullish)
            sentiment_score = 0.5
            
            if rsi > 60:
                sentiment_score += 0.1
            elif rsi < 40:
                sentiment_score -= 0.1
            
            if trend_strength > 0.3:
                sentiment_score += 0.2
            elif trend_strength < -0.3:
                sentiment_score -= 0.2
            
            # Update market sentiment
            self.market_sentiment['sentiment_score'] = max(0.0, min(1.0, sentiment_score))
            
            if sentiment_score > 0.6:
                self.market_sentiment['overall_sentiment'] = 'bullish'
            elif sentiment_score < 0.4:
                self.market_sentiment['overall_sentiment'] = 'bearish'
            else:
                self.market_sentiment['overall_sentiment'] = 'neutral'
            
            # Volatility regime
            if volatility > 0.3:
                self.market_sentiment['volatility_regime'] = 'high'
            elif volatility < 0.15:
                self.market_sentiment['volatility_regime'] = 'low'
            else:
                self.market_sentiment['volatility_regime'] = 'normal'
            
            self.market_sentiment['last_update'] = datetime.now()
            
        except Exception as e:
            self.logger.error("Error updating market sentiment", error=str(e))
    
    async def _handle_trading_event(self, event):
        """Handle trading state changed events"""
        try:
            self.logger.debug("Received trading event")
            # Intelligence module can react to trading events
        except Exception as e:
            self.logger.error("Error handling trading event", error=str(e))
    
    async def _handle_config_event(self, event):
        """Handle configuration update events"""
        try:
            self.logger.info("Received config update event")
            
            # Update intelligence rules if provided
            config_data = event.data
            if 'intelligence_rules' in config_data:
                self.intelligence_rules.update(config_data['intelligence_rules'])
                self.logger.info("Intelligence rules updated")
                
        except Exception as e:
            self.logger.error("Error handling config event", error=str(e))
    
    async def _handle_system_alert_event(self, event):
        """Handle system alert events"""
        try:
            self.logger.info("Received system alert event")
            # Intelligence module can adjust behavior based on system alerts
        except Exception as e:
            self.logger.error("Error handling system alert event", error=str(e))
    
    async def _get_decision_history(self) -> Dict[str, Any]:
        """Get recent decision history"""
        try:
            return {
                'success': True,
                'decision_count': len(self.decision_history),
                'recent_decisions': self.decision_history[-10:],  # Last 10 decisions
                'current_market_sentiment': self.market_sentiment.copy()
            }
        except Exception as e:
            self.logger.error("Error getting decision history", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }