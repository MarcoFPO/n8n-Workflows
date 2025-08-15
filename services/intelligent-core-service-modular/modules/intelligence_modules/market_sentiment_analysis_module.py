"""
Market Sentiment Analysis Module - Single Function Module
Analyzes and tracks overall market sentiment based on technical indicators and market conditions
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
        
        async def _setup_event_subscriptions(self):
            """Setup event subscriptions for market sentiment analysis - Mock fallback implementation"""
            try:
                # In production, this would set up proper event subscriptions
                # For fallback mode, we initialize basic logging
                print("⚠️  Mock event subscription setup - production requires proper Event Bus integration")
                return True
            except Exception as e:
                print(f"❌ Mock event setup failed: {e}")
                return False


class MarketSentimentAnalysisModule(SingleFunctionModuleBase):
    """Analyze and track market sentiment using technical indicators and market conditions"""
    
    def __init__(self, event_bus):
        super().__init__("market_sentiment_analysis", event_bus)
        self.sentiment_weights = {
            'trend_weight': 0.25,          # Overall trend direction
            'momentum_weight': 0.20,       # Price momentum indicators
            'volatility_weight': 0.15,     # Market volatility impact
            'volume_weight': 0.15,         # Volume participation
            'technical_weight': 0.15,      # Technical indicator consensus
            'market_structure_weight': 0.10 # Market structure health
        }
        
        self.sentiment_thresholds = {
            'very_bullish': 0.75,          # Very positive sentiment
            'bullish': 0.60,               # Positive sentiment
            'neutral_positive': 0.55,       # Slightly positive
            'neutral': 0.50,               # Neutral sentiment
            'neutral_negative': 0.45,       # Slightly negative
            'bearish': 0.40,               # Negative sentiment
            'very_bearish': 0.25,          # Very negative sentiment
            'extreme_threshold': 0.20      # Extreme sentiment levels
        }
        
        self.sentiment_indicators = {
            'fear_greed_neutral': 50,      # Fear & Greed neutral point
            'high_volatility_threshold': 0.30,  # High volatility threshold
            'low_volume_threshold': 0.7,   # Low volume threshold
            'trend_strength_threshold': 0.6, # Strong trend threshold
            'momentum_threshold': 0.15     # Significant momentum threshold
        }
        
        # Historical sentiment tracking (in-memory for this module)
        self.sentiment_history = []
        self.max_history_length = 50
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('sentiment.analysis.request', self.process_event)
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
                'sentiment_weights': self.sentiment_weights,
                'sentiment_thresholds': self.sentiment_thresholds,
                'sentiment_history_count': len(self.sentiment_history),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'sentiment.analysis.request':
            indicators = event.get('indicators', {})
            symbol = event.get('symbol', 'UNKNOWN')
            market_data = event.get('market_data', {})
            
            sentiment_result = await self.analyze_market_sentiment(
                indicators, symbol, market_data
            )
            
            response_event = {
                'event_type': 'sentiment.analysis.response',
                'symbol': symbol,
                'sentiment_score': sentiment_result['sentiment_score'],
                'sentiment_level': sentiment_result['sentiment_level'],
                'sentiment_components': sentiment_result['sentiment_components'],
                'sentiment_analysis': sentiment_result['sentiment_analysis'],
                'market_conditions': sentiment_result['market_conditions'],
                'sentiment_trend': sentiment_result['sentiment_trend'],
                'confidence': sentiment_result['confidence'],
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def analyze_market_sentiment(self, indicators: Dict[str, float], symbol: str = "UNKNOWN", market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze comprehensive market sentiment"""
        try:
            if market_data is None:
                market_data = {}
            
            # Initialize sentiment tracking
            sentiment_components = {}
            sentiment_analysis = []
            total_sentiment = 0.0
            component_count = 0
            
            # 1. Trend Sentiment Analysis
            trend_sentiment = await self._analyze_trend_sentiment(indicators)
            sentiment_components['trend'] = trend_sentiment
            total_sentiment += trend_sentiment['weighted_score']
            component_count += 1
            if trend_sentiment['analysis']:
                sentiment_analysis.extend(trend_sentiment['analysis'])
            
            # 2. Momentum Sentiment Analysis
            momentum_sentiment = await self._analyze_momentum_sentiment(indicators)
            sentiment_components['momentum'] = momentum_sentiment
            total_sentiment += momentum_sentiment['weighted_score']
            component_count += 1
            if momentum_sentiment['analysis']:
                sentiment_analysis.extend(momentum_sentiment['analysis'])
            
            # 3. Volatility Sentiment Analysis
            volatility_sentiment = await self._analyze_volatility_sentiment(indicators)
            sentiment_components['volatility'] = volatility_sentiment
            total_sentiment += volatility_sentiment['weighted_score']
            component_count += 1
            if volatility_sentiment['analysis']:
                sentiment_analysis.extend(volatility_sentiment['analysis'])
            
            # 4. Volume Sentiment Analysis
            volume_sentiment = await self._analyze_volume_sentiment(indicators)
            sentiment_components['volume'] = volume_sentiment
            total_sentiment += volume_sentiment['weighted_score']
            component_count += 1
            if volume_sentiment['analysis']:
                sentiment_analysis.extend(volume_sentiment['analysis'])
            
            # 5. Technical Indicator Sentiment
            technical_sentiment = await self._analyze_technical_sentiment(indicators)
            sentiment_components['technical'] = technical_sentiment
            total_sentiment += technical_sentiment['weighted_score']
            component_count += 1
            if technical_sentiment['analysis']:
                sentiment_analysis.extend(technical_sentiment['analysis'])
            
            # 6. Market Structure Sentiment
            structure_sentiment = await self._analyze_market_structure_sentiment(indicators, market_data)
            sentiment_components['market_structure'] = structure_sentiment
            total_sentiment += structure_sentiment['weighted_score']
            component_count += 1
            if structure_sentiment['analysis']:
                sentiment_analysis.extend(structure_sentiment['analysis'])
            
            # Calculate composite sentiment score
            composite_sentiment = total_sentiment / max(1, component_count) if component_count > 0 else 0.5
            composite_sentiment = max(0.0, min(1.0, composite_sentiment))  # Ensure valid range
            
            # Determine sentiment level and confidence
            sentiment_level, confidence = await self._determine_sentiment_level(composite_sentiment, sentiment_components)
            
            # Analyze market conditions
            market_conditions = await self._analyze_market_conditions(indicators, composite_sentiment)
            
            # Track sentiment trend
            sentiment_trend = await self._track_sentiment_trend(composite_sentiment, symbol)
            
            # Store in history
            self._update_sentiment_history({
                'timestamp': datetime.now(),
                'symbol': symbol,
                'sentiment_score': composite_sentiment,
                'sentiment_level': sentiment_level,
                'components': sentiment_components
            })
            
            self.logger.debug("Market sentiment analysis completed successfully",
                            symbol=symbol,
                            sentiment_score=composite_sentiment,
                            sentiment_level=sentiment_level,
                            confidence=confidence)
            
            return {
                'sentiment_score': float(composite_sentiment),
                'sentiment_level': sentiment_level,
                'sentiment_components': sentiment_components,
                'sentiment_analysis': sentiment_analysis,
                'market_conditions': market_conditions,
                'sentiment_trend': sentiment_trend,
                'confidence': float(confidence),
                'component_count': component_count
            }
            
        except Exception as e:
            self.logger.error("Error analyzing market sentiment", error=str(e))
            return {
                'sentiment_score': 0.5,
                'sentiment_level': 'neutral',
                'sentiment_components': {},
                'sentiment_analysis': [f"Sentiment analysis error: {str(e)}"],
                'market_conditions': {'error': True},
                'sentiment_trend': {'trend': 'neutral', 'strength': 0.0},
                'confidence': 0.0,
                'component_count': 0
            }
    
    async def _analyze_trend_sentiment(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Analyze trend-based market sentiment"""
        try:
            current_price = indicators.get('current_price', 100.0)
            sma_20 = indicators.get('sma_20', current_price)
            sma_50 = indicators.get('sma_50', current_price)
            trend_strength = indicators.get('trend_strength', 0.0)
            trend_direction = indicators.get('trend_direction', 'neutral')
            
            sentiment_score = 0.5  # Start neutral
            analysis = []
            
            # Price position relative to moving averages
            if current_price > sma_20 > sma_50:
                # Strong uptrend alignment
                ma_strength = min(1.0, (current_price - sma_50) / sma_50)
                sentiment_score = 0.5 + (ma_strength * 0.4)  # Max 0.9
                analysis.append(f"Strong bullish trend: Price above both MAs (strength: {ma_strength:.2f})")
                
            elif current_price < sma_20 < sma_50:
                # Strong downtrend alignment
                ma_weakness = min(1.0, (sma_50 - current_price) / sma_50)
                sentiment_score = 0.5 - (ma_weakness * 0.4)  # Min 0.1
                analysis.append(f"Strong bearish trend: Price below both MAs (weakness: {ma_weakness:.2f})")
                
            elif current_price > sma_20:
                # Mixed signal - price above short-term MA
                sentiment_score = 0.55
                analysis.append("Mixed trend signals: Price above SMA20 but trend unclear")
                
            elif current_price < sma_20:
                # Mixed signal - price below short-term MA
                sentiment_score = 0.45
                analysis.append("Mixed trend signals: Price below SMA20 but trend unclear")
            
            # Trend strength confirmation
            if trend_strength > self.sentiment_indicators['trend_strength_threshold']:
                if trend_direction == 'bullish':
                    sentiment_score = min(0.95, sentiment_score + (trend_strength * 0.1))
                    analysis.append(f"Strong bullish trend confirmed (strength: {trend_strength:.2f})")
                elif trend_direction == 'bearish':
                    sentiment_score = max(0.05, sentiment_score - (trend_strength * 0.1))
                    analysis.append(f"Strong bearish trend confirmed (strength: {trend_strength:.2f})")
            
            weighted_score = sentiment_score * self.sentiment_weights['trend_weight']
            
            return {
                'raw_score': sentiment_score,
                'weighted_score': weighted_score,
                'analysis': analysis,
                'trend_alignment': current_price > sma_20 > sma_50,
                'trend_strength': trend_strength,
                'trend_direction': trend_direction
            }
            
        except Exception as e:
            self.logger.error("Error analyzing trend sentiment", error=str(e))
            return {
                'raw_score': 0.5,
                'weighted_score': 0.5 * self.sentiment_weights['trend_weight'],
                'analysis': [],
                'trend_alignment': False,
                'trend_strength': 0.0,
                'trend_direction': 'neutral'
            }
    
    async def _analyze_momentum_sentiment(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Analyze momentum-based market sentiment"""
        try:
            macd = indicators.get('macd', 0.0)
            macd_signal = indicators.get('macd_signal', 0.0)
            macd_histogram = indicators.get('macd_histogram', 0.0)
            trend_momentum = indicators.get('trend_momentum', 0.0)
            
            sentiment_score = 0.5  # Start neutral
            analysis = []
            
            # MACD momentum analysis
            if macd > macd_signal:
                if macd > 0:
                    # Strong bullish momentum
                    momentum_strength = min(1.0, abs(macd - macd_signal) / max(abs(macd), 0.001))
                    sentiment_score = 0.5 + (momentum_strength * 0.35)
                    analysis.append(f"Strong bullish momentum: MACD above signal and zero ({momentum_strength:.2f})")
                else:
                    # Recovering momentum
                    momentum_strength = min(0.5, abs(macd - macd_signal) / max(abs(macd), 0.001))
                    sentiment_score = 0.5 + (momentum_strength * 0.2)
                    analysis.append(f"Recovering momentum: MACD above signal below zero")
            else:
                if macd < 0:
                    # Strong bearish momentum
                    momentum_strength = min(1.0, abs(macd - macd_signal) / max(abs(macd), 0.001))
                    sentiment_score = 0.5 - (momentum_strength * 0.35)
                    analysis.append(f"Strong bearish momentum: MACD below signal and zero ({momentum_strength:.2f})")
                else:
                    # Weakening momentum
                    momentum_strength = min(0.5, abs(macd - macd_signal) / max(abs(macd), 0.001))
                    sentiment_score = 0.5 - (momentum_strength * 0.2)
                    analysis.append(f"Weakening momentum: MACD below signal above zero")
            
            # Histogram confirmation
            if abs(macd_histogram) > self.sentiment_indicators['momentum_threshold']:
                histogram_factor = min(0.1, abs(macd_histogram) * 0.2)
                if macd_histogram > 0 and sentiment_score > 0.5:
                    sentiment_score = min(0.95, sentiment_score + histogram_factor)
                    analysis.append("Histogram confirms bullish momentum")
                elif macd_histogram < 0 and sentiment_score < 0.5:
                    sentiment_score = max(0.05, sentiment_score - histogram_factor)
                    analysis.append("Histogram confirms bearish momentum")
            
            # Trend momentum confirmation
            if abs(trend_momentum) > self.sentiment_indicators['momentum_threshold']:
                if trend_momentum > 0:
                    sentiment_score = min(0.95, sentiment_score + (trend_momentum * 0.15))
                    analysis.append(f"Positive trend momentum detected ({trend_momentum:.2f})")
                else:
                    sentiment_score = max(0.05, sentiment_score - (abs(trend_momentum) * 0.15))
                    analysis.append(f"Negative trend momentum detected ({trend_momentum:.2f})")
            
            weighted_score = sentiment_score * self.sentiment_weights['momentum_weight']
            
            return {
                'raw_score': sentiment_score,
                'weighted_score': weighted_score,
                'analysis': analysis,
                'macd_bullish': macd > macd_signal,
                'histogram_direction': 'positive' if macd_histogram > 0 else 'negative' if macd_histogram < 0 else 'neutral',
                'momentum_strength': abs(trend_momentum)
            }
            
        except Exception as e:
            self.logger.error("Error analyzing momentum sentiment", error=str(e))
            return {
                'raw_score': 0.5,
                'weighted_score': 0.5 * self.sentiment_weights['momentum_weight'],
                'analysis': [],
                'macd_bullish': False,
                'histogram_direction': 'neutral',
                'momentum_strength': 0.0
            }
    
    async def _analyze_volatility_sentiment(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Analyze volatility impact on market sentiment"""
        try:
            volatility = indicators.get('volatility', 0.2)
            atr_percentage = indicators.get('atr_percentage', 0.0)
            bollinger_position = indicators.get('bollinger_position', 0.5)
            
            sentiment_score = 0.5  # Start neutral
            analysis = []
            
            # High volatility generally negative for sentiment
            if volatility > self.sentiment_indicators['high_volatility_threshold']:
                volatility_impact = min(1.0, (volatility - 0.2) / 0.3)
                sentiment_score = 0.5 - (volatility_impact * 0.2)  # Reduce sentiment
                analysis.append(f"High volatility reduces market confidence ({volatility:.1%})")
                
                # Extreme volatility
                if volatility > 0.5:
                    sentiment_score = max(0.1, sentiment_score - 0.15)
                    analysis.append("Extreme volatility creates market fear")
            
            # Low volatility can be positive (stable) or negative (complacency)
            elif volatility < 0.10:
                # Very low volatility - depends on trend context
                low_vol_factor = (0.10 - volatility) / 0.08
                sentiment_score = 0.5 + (low_vol_factor * 0.1)  # Slight positive for stability
                analysis.append(f"Low volatility suggests market stability ({volatility:.1%})")
            
            # ATR analysis for intraday sentiment
            if atr_percentage > 0:
                if atr_percentage > 4.0:  # High ATR
                    sentiment_score = max(0.2, sentiment_score - 0.1)
                    analysis.append(f"High ATR indicates increased uncertainty ({atr_percentage:.1%})")
                elif atr_percentage < 1.0:  # Low ATR
                    sentiment_score = min(0.8, sentiment_score + 0.05)
                    analysis.append(f"Low ATR suggests reduced uncertainty")
            
            # Bollinger Band position analysis
            if bollinger_position <= 0.1:
                # Near lower band - potential oversold, but negative sentiment
                sentiment_score = max(0.15, sentiment_score - 0.15)
                analysis.append("Price near Bollinger lower band suggests negative sentiment")
            elif bollinger_position >= 0.9:
                # Near upper band - potential overbought, mixed sentiment
                sentiment_score = min(0.85, sentiment_score + 0.1)
                analysis.append("Price near Bollinger upper band suggests strong sentiment but overbought risk")
            
            weighted_score = sentiment_score * self.sentiment_weights['volatility_weight']
            
            return {
                'raw_score': sentiment_score,
                'weighted_score': weighted_score,
                'analysis': analysis,
                'volatility_level': volatility,
                'high_volatility': volatility > self.sentiment_indicators['high_volatility_threshold'],
                'bollinger_position': bollinger_position
            }
            
        except Exception as e:
            self.logger.error("Error analyzing volatility sentiment", error=str(e))
            return {
                'raw_score': 0.5,
                'weighted_score': 0.5 * self.sentiment_weights['volatility_weight'],
                'analysis': [],
                'volatility_level': 0.2,
                'high_volatility': False,
                'bollinger_position': 0.5
            }
    
    async def _analyze_volume_sentiment(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Analyze volume-based market sentiment"""
        try:
            volume_ratio = indicators.get('volume_ratio', 1.0)
            price_volume_correlation = indicators.get('price_volume_correlation', 0.0)
            volume_trend = indicators.get('volume_trend', 'stable')
            
            sentiment_score = 0.5  # Start neutral
            analysis = []
            
            # High volume analysis
            if volume_ratio > 1.5:
                if abs(price_volume_correlation) > 0.3:
                    # High volume with price confirmation
                    correlation_strength = abs(price_volume_correlation)
                    volume_strength = min(1.0, volume_ratio - 1.0)
                    
                    if price_volume_correlation > 0:
                        # Bullish volume confirmation
                        sentiment_score = 0.5 + (correlation_strength * volume_strength * 0.3)
                        analysis.append(f"High volume confirms bullish sentiment ({volume_ratio:.1f}x, correlation: {price_volume_correlation:.2f})")
                    else:
                        # Bearish volume confirmation
                        sentiment_score = 0.5 - (correlation_strength * volume_strength * 0.3)
                        analysis.append(f"High volume confirms bearish sentiment ({volume_ratio:.1f}x, correlation: {price_volume_correlation:.2f})")
                else:
                    # High volume without clear direction - uncertainty
                    sentiment_score = 0.4  # Slightly negative due to uncertainty
                    analysis.append(f"High volume without clear direction suggests uncertainty ({volume_ratio:.1f}x)")
            
            # Low volume analysis
            elif volume_ratio < self.sentiment_indicators['low_volume_threshold']:
                low_volume_factor = (self.sentiment_indicators['low_volume_threshold'] - volume_ratio) / 0.5
                sentiment_score = 0.5 - (low_volume_factor * 0.15)  # Low participation is negative
                analysis.append(f"Low volume suggests reduced market participation ({volume_ratio:.1f}x)")
                
                # Very low volume
                if volume_ratio < 0.3:
                    sentiment_score = max(0.2, sentiment_score - 0.1)
                    analysis.append("Very low volume indicates market apathy")
            
            # Volume trend analysis
            if volume_trend == 'increasing':
                sentiment_score = min(0.9, sentiment_score + 0.1)
                analysis.append("Increasing volume trend supports current sentiment")
            elif volume_trend == 'decreasing':
                sentiment_score = max(0.1, sentiment_score - 0.05)
                analysis.append("Decreasing volume trend weakens sentiment")
            
            weighted_score = sentiment_score * self.sentiment_weights['volume_weight']
            
            return {
                'raw_score': sentiment_score,
                'weighted_score': weighted_score,
                'analysis': analysis,
                'volume_ratio': volume_ratio,
                'high_volume': volume_ratio > 1.5,
                'low_volume': volume_ratio < self.sentiment_indicators['low_volume_threshold'],
                'volume_correlation': price_volume_correlation
            }
            
        except Exception as e:
            self.logger.error("Error analyzing volume sentiment", error=str(e))
            return {
                'raw_score': 0.5,
                'weighted_score': 0.5 * self.sentiment_weights['volume_weight'],
                'analysis': [],
                'volume_ratio': 1.0,
                'high_volume': False,
                'low_volume': False,
                'volume_correlation': 0.0
            }
    
    async def _analyze_technical_sentiment(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Analyze technical indicator consensus for sentiment"""
        try:
            rsi = indicators.get('rsi', 50.0)
            stoch_k = indicators.get('stoch_k', 50.0)
            williams_r = indicators.get('williams_r', -50.0)
            
            sentiment_score = 0.5  # Start neutral
            analysis = []
            bullish_indicators = 0
            bearish_indicators = 0
            total_indicators = 0
            
            # RSI analysis
            total_indicators += 1
            if rsi >= 70:
                bearish_indicators += 1
                overbought_strength = min(1.0, (rsi - 70) / 10)
                sentiment_score -= overbought_strength * 0.15
                analysis.append(f"RSI overbought ({rsi:.1f}) - negative sentiment")
            elif rsi <= 30:
                bullish_indicators += 1
                oversold_strength = min(1.0, (30 - rsi) / 10)
                sentiment_score += oversold_strength * 0.15
                analysis.append(f"RSI oversold ({rsi:.1f}) - potential bullish reversal")
            elif rsi > 50:
                bullish_indicators += 0.5
                sentiment_score += (rsi - 50) / 200  # Small positive adjustment
            else:
                bearish_indicators += 0.5
                sentiment_score -= (50 - rsi) / 200  # Small negative adjustment
            
            # Stochastic analysis (if available)
            if stoch_k != 50.0:  # Non-default value
                total_indicators += 1
                if stoch_k >= 80:
                    bearish_indicators += 1
                    sentiment_score -= 0.1
                    analysis.append(f"Stochastic overbought ({stoch_k:.1f})")
                elif stoch_k <= 20:
                    bullish_indicators += 1
                    sentiment_score += 0.1
                    analysis.append(f"Stochastic oversold ({stoch_k:.1f})")
                elif stoch_k > 50:
                    bullish_indicators += 0.5
                else:
                    bearish_indicators += 0.5
            
            # Williams %R analysis (if available)
            if williams_r != -50.0:  # Non-default value
                total_indicators += 1
                if williams_r >= -20:  # Overbought
                    bearish_indicators += 1
                    sentiment_score -= 0.1
                    analysis.append(f"Williams %R overbought ({williams_r:.1f})")
                elif williams_r <= -80:  # Oversold
                    bullish_indicators += 1
                    sentiment_score += 0.1
                    analysis.append(f"Williams %R oversold ({williams_r:.1f})")
            
            # Calculate indicator consensus
            if total_indicators > 0:
                bullish_ratio = bullish_indicators / total_indicators
                bearish_ratio = bearish_indicators / total_indicators
                
                if bullish_ratio > 0.6:
                    analysis.append(f"Technical indicator consensus: Bullish ({bullish_ratio:.1%})")
                elif bearish_ratio > 0.6:
                    analysis.append(f"Technical indicator consensus: Bearish ({bearish_ratio:.1%})")
                else:
                    analysis.append("Technical indicators show mixed signals")
            
            # Ensure valid range
            sentiment_score = max(0.0, min(1.0, sentiment_score))
            
            weighted_score = sentiment_score * self.sentiment_weights['technical_weight']
            
            return {
                'raw_score': sentiment_score,
                'weighted_score': weighted_score,
                'analysis': analysis,
                'bullish_indicators': bullish_indicators,
                'bearish_indicators': bearish_indicators,
                'total_indicators': total_indicators,
                'consensus': 'bullish' if bullish_indicators > bearish_indicators else 'bearish' if bearish_indicators > bullish_indicators else 'mixed'
            }
            
        except Exception as e:
            self.logger.error("Error analyzing technical sentiment", error=str(e))
            return {
                'raw_score': 0.5,
                'weighted_score': 0.5 * self.sentiment_weights['technical_weight'],
                'analysis': [],
                'bullish_indicators': 0,
                'bearish_indicators': 0,
                'total_indicators': 0,
                'consensus': 'neutral'
            }
    
    async def _analyze_market_structure_sentiment(self, indicators: Dict[str, float], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market structure for sentiment insights"""
        try:
            # Support and resistance levels
            support_level = indicators.get('support_level', 0.0)
            resistance_level = indicators.get('resistance_level', 0.0)
            current_price = indicators.get('current_price', 100.0)
            
            # Market breadth indicators (if available)
            market_breadth = market_data.get('market_breadth', {})
            advancing_stocks = market_breadth.get('advancing', 50)
            declining_stocks = market_breadth.get('declining', 50)
            
            sentiment_score = 0.5  # Start neutral
            analysis = []
            
            # Support/Resistance analysis
            if support_level > 0 and resistance_level > 0:
                price_range = resistance_level - support_level
                if price_range > 0:
                    price_position = (current_price - support_level) / price_range
                    
                    if price_position > 0.8:
                        sentiment_score = min(0.85, sentiment_score + 0.2)
                        analysis.append(f"Price near resistance suggests bullish momentum but potential ceiling")
                    elif price_position < 0.2:
                        sentiment_score = max(0.15, sentiment_score - 0.2)
                        analysis.append(f"Price near support suggests bearish pressure but potential floor")
                    else:
                        # Middle range - neutral to slightly positive
                        sentiment_score += (price_position - 0.5) * 0.2
            
            # Market breadth analysis
            if advancing_stocks + declining_stocks > 0:
                advance_decline_ratio = advancing_stocks / (advancing_stocks + declining_stocks)
                
                if advance_decline_ratio > 0.6:
                    breadth_strength = min(1.0, (advance_decline_ratio - 0.5) * 2)
                    sentiment_score = min(0.9, sentiment_score + (breadth_strength * 0.15))
                    analysis.append(f"Market breadth positive: {advance_decline_ratio:.1%} advancing")
                elif advance_decline_ratio < 0.4:
                    breadth_weakness = min(1.0, (0.5 - advance_decline_ratio) * 2)
                    sentiment_score = max(0.1, sentiment_score - (breadth_weakness * 0.15))
                    analysis.append(f"Market breadth negative: {advance_decline_ratio:.1%} advancing")
                else:
                    analysis.append("Market breadth neutral")
            
            # Market sector performance (if available)
            sector_performance = market_data.get('sector_performance', {})
            if sector_performance:
                positive_sectors = sum(1 for perf in sector_performance.values() if perf > 0)
                total_sectors = len(sector_performance)
                
                if total_sectors > 0:
                    sector_ratio = positive_sectors / total_sectors
                    if sector_ratio > 0.7:
                        sentiment_score = min(0.95, sentiment_score + 0.1)
                        analysis.append(f"Broad sector strength: {sector_ratio:.1%} sectors positive")
                    elif sector_ratio < 0.3:
                        sentiment_score = max(0.05, sentiment_score - 0.1)
                        analysis.append(f"Broad sector weakness: {sector_ratio:.1%} sectors positive")
            
            # VIX or fear gauge (if available)
            vix_level = market_data.get('vix', 0)
            if vix_level > 0:
                if vix_level > 30:  # High fear
                    fear_impact = min(1.0, (vix_level - 20) / 30)
                    sentiment_score = max(0.1, sentiment_score - (fear_impact * 0.2))
                    analysis.append(f"High VIX ({vix_level:.1f}) indicates market fear")
                elif vix_level < 15:  # Low fear/complacency
                    complacency_factor = (15 - vix_level) / 10
                    sentiment_score = min(0.8, sentiment_score + (complacency_factor * 0.1))
                    analysis.append(f"Low VIX ({vix_level:.1f}) suggests market complacency")
            
            # Ensure valid range
            sentiment_score = max(0.0, min(1.0, sentiment_score))
            
            weighted_score = sentiment_score * self.sentiment_weights['market_structure_weight']
            
            return {
                'raw_score': sentiment_score,
                'weighted_score': weighted_score,
                'analysis': analysis,
                'support_resistance_position': (current_price - support_level) / max(1, resistance_level - support_level) if resistance_level > support_level else 0.5,
                'market_breadth_ratio': advancing_stocks / max(1, advancing_stocks + declining_stocks),
                'vix_level': vix_level
            }
            
        except Exception as e:
            self.logger.error("Error analyzing market structure sentiment", error=str(e))
            return {
                'raw_score': 0.5,
                'weighted_score': 0.5 * self.sentiment_weights['market_structure_weight'],
                'analysis': [],
                'support_resistance_position': 0.5,
                'market_breadth_ratio': 0.5,
                'vix_level': 0
            }
    
    async def _determine_sentiment_level(self, sentiment_score: float, components: Dict[str, Any]) -> tuple:
        """Determine sentiment level and confidence from score and components"""
        try:
            # Determine sentiment level
            if sentiment_score >= self.sentiment_thresholds['very_bullish']:
                sentiment_level = 'very_bullish'
            elif sentiment_score >= self.sentiment_thresholds['bullish']:
                sentiment_level = 'bullish'
            elif sentiment_score >= self.sentiment_thresholds['neutral_positive']:
                sentiment_level = 'neutral_positive'
            elif sentiment_score >= self.sentiment_thresholds['neutral']:
                sentiment_level = 'neutral'
            elif sentiment_score >= self.sentiment_thresholds['neutral_negative']:
                sentiment_level = 'neutral_negative'
            elif sentiment_score >= self.sentiment_thresholds['bearish']:
                sentiment_level = 'bearish'
            else:
                sentiment_level = 'very_bearish'
            
            # Calculate confidence based on component agreement
            component_scores = [comp.get('raw_score', 0.5) for comp in components.values() if isinstance(comp, dict)]
            
            if len(component_scores) > 1:
                # Calculate standard deviation of component scores
                mean_score = sum(component_scores) / len(component_scores)
                variance = sum((score - mean_score) ** 2 for score in component_scores) / len(component_scores)
                std_dev = variance ** 0.5
                
                # Higher agreement = higher confidence
                max_std_dev = 0.5  # Maximum expected standard deviation
                agreement = 1 - min(1.0, std_dev / max_std_dev)
                
                # Base confidence from sentiment extremity
                extremity = abs(sentiment_score - 0.5) * 2  # 0 = neutral, 1 = extreme
                
                # Combine agreement and extremity
                confidence = (agreement * 0.6) + (extremity * 0.4)
            else:
                # Single component or no components - base confidence on extremity
                confidence = abs(sentiment_score - 0.5) * 2
            
            # Ensure valid range
            confidence = max(0.1, min(1.0, confidence))
            
            return sentiment_level, confidence
            
        except Exception as e:
            self.logger.error("Error determining sentiment level", error=str(e))
            return 'neutral', 0.5
    
    async def _analyze_market_conditions(self, indicators: Dict[str, float], sentiment_score: float) -> Dict[str, Any]:
        """Analyze current market conditions"""
        try:
            conditions = {
                'overall_condition': 'neutral',
                'volatility_regime': 'normal',
                'trend_regime': 'sideways',
                'volume_regime': 'normal',
                'risk_level': 'moderate'
            }
            
            # Overall condition based on sentiment
            if sentiment_score >= 0.7:
                conditions['overall_condition'] = 'bullish'
            elif sentiment_score <= 0.3:
                conditions['overall_condition'] = 'bearish'
            elif sentiment_score >= 0.55:
                conditions['overall_condition'] = 'neutral_positive'
            elif sentiment_score <= 0.45:
                conditions['overall_condition'] = 'neutral_negative'
            
            # Volatility regime
            volatility = indicators.get('volatility', 0.2)
            if volatility > 0.4:
                conditions['volatility_regime'] = 'high'
                conditions['risk_level'] = 'high'
            elif volatility > 0.25:
                conditions['volatility_regime'] = 'elevated'
                conditions['risk_level'] = 'elevated'
            elif volatility < 0.1:
                conditions['volatility_regime'] = 'low'
            
            # Trend regime
            trend_strength = indicators.get('trend_strength', 0.0)
            if trend_strength > 0.6:
                trend_direction = indicators.get('trend_direction', 'neutral')
                if trend_direction == 'bullish':
                    conditions['trend_regime'] = 'strong_uptrend'
                elif trend_direction == 'bearish':
                    conditions['trend_regime'] = 'strong_downtrend'
                else:
                    conditions['trend_regime'] = 'trending'
            elif trend_strength > 0.3:
                conditions['trend_regime'] = 'weak_trend'
            
            # Volume regime
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 2.0:
                conditions['volume_regime'] = 'very_high'
            elif volume_ratio > 1.5:
                conditions['volume_regime'] = 'high'
            elif volume_ratio < 0.5:
                conditions['volume_regime'] = 'low'
            
            return conditions
            
        except Exception as e:
            self.logger.error("Error analyzing market conditions", error=str(e))
            return {'error': True, 'overall_condition': 'unknown'}
    
    async def _track_sentiment_trend(self, current_sentiment: float, symbol: str) -> Dict[str, Any]:
        """Track sentiment trend over time"""
        try:
            # Get recent sentiment history for this symbol
            recent_history = [
                entry for entry in self.sentiment_history[-10:] 
                if entry['symbol'] == symbol
            ]
            
            if len(recent_history) < 2:
                return {
                    'trend': 'neutral',
                    'strength': 0.0,
                    'direction': 'stable',
                    'periods': len(recent_history)
                }
            
            # Calculate trend
            sentiment_values = [entry['sentiment_score'] for entry in recent_history]
            sentiment_values.append(current_sentiment)
            
            # Simple linear regression for trend
            n = len(sentiment_values)
            x_values = list(range(n))
            
            # Calculate slope
            sum_x = sum(x_values)
            sum_y = sum(sentiment_values)
            sum_xy = sum(x * y for x, y in zip(x_values, sentiment_values))
            sum_x_squared = sum(x * x for x in x_values)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x * sum_x)
            
            # Determine trend characteristics
            if abs(slope) < 0.01:
                trend = 'neutral'
                direction = 'stable'
            elif slope > 0:
                trend = 'improving'
                direction = 'upward'
            else:
                trend = 'deteriorating'
                direction = 'downward'
            
            # Calculate trend strength
            strength = min(1.0, abs(slope) * 10)  # Scale slope to 0-1
            
            return {
                'trend': trend,
                'strength': strength,
                'direction': direction,
                'slope': slope,
                'periods': len(recent_history) + 1
            }
            
        except Exception as e:
            self.logger.error("Error tracking sentiment trend", error=str(e))
            return {
                'trend': 'neutral',
                'strength': 0.0,
                'direction': 'stable',
                'periods': 0
            }
    
    def _update_sentiment_history(self, sentiment_data: Dict[str, Any]):
        """Update sentiment history with new data point"""
        try:
            self.sentiment_history.append(sentiment_data)
            
            # Maintain history length limit
            if len(self.sentiment_history) > self.max_history_length:
                self.sentiment_history = self.sentiment_history[-self.max_history_length:]
            
        except Exception as e:
            self.logger.error("Error updating sentiment history", error=str(e))
    
    def update_sentiment_weights(self, new_weights: Dict[str, float]) -> bool:
        """Update sentiment component weights"""
        try:
            valid_weights = set(self.sentiment_weights.keys())
            
            for weight_name, weight_value in new_weights.items():
                if weight_name in valid_weights and 0.0 <= weight_value <= 1.0:
                    self.sentiment_weights[weight_name] = weight_value
                    self.logger.info("Updated sentiment weight", weight=weight_name, value=weight_value)
                else:
                    self.logger.warning("Invalid sentiment weight", weight=weight_name, value=weight_value)
            
            return True
            
        except Exception as e:
            self.logger.error("Error updating sentiment weights", error=str(e))
            return False
    
    def get_sentiment_summary(self, symbol: str = None) -> Dict[str, Any]:
        """Get summary of recent sentiment analysis"""
        try:
            if symbol:
                relevant_history = [
                    entry for entry in self.sentiment_history 
                    if entry['symbol'] == symbol
                ]
            else:
                relevant_history = self.sentiment_history
            
            if not relevant_history:
                return {'error': 'No sentiment history available'}
            
            # Calculate summary statistics
            sentiment_scores = [entry['sentiment_score'] for entry in relevant_history]
            sentiment_levels = [entry['sentiment_level'] for entry in relevant_history]
            
            summary = {
                'total_analyses': len(relevant_history),
                'average_sentiment': sum(sentiment_scores) / len(sentiment_scores),
                'min_sentiment': min(sentiment_scores),
                'max_sentiment': max(sentiment_scores),
                'current_sentiment': sentiment_scores[-1] if sentiment_scores else 0.5,
                'most_recent_level': sentiment_levels[-1] if sentiment_levels else 'neutral',
                'level_distribution': {},
                'symbol_filter': symbol,
                'time_range': {
                    'from': relevant_history[0]['timestamp'].isoformat() if relevant_history else None,
                    'to': relevant_history[-1]['timestamp'].isoformat() if relevant_history else None
                }
            }
            
            # Calculate level distribution
            for level in sentiment_levels:
                summary['level_distribution'][level] = summary['level_distribution'].get(level, 0) + 1
            
            return summary
            
        except Exception as e:
            self.logger.error("Error generating sentiment summary", error=str(e))
            return {'error': str(e)}
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'market_sentiment_analysis',
            'sentiment_weights': self.sentiment_weights.copy(),
            'sentiment_thresholds': self.sentiment_thresholds.copy(),
            'sentiment_indicators': self.sentiment_indicators.copy(),
            'history_length': len(self.sentiment_history),
            'max_history_length': self.max_history_length,
            'supported_components': [
                'trend_sentiment',
                'momentum_sentiment', 
                'volatility_sentiment',
                'volume_sentiment',
                'technical_sentiment',
                'market_structure_sentiment'
            ],
            'features': [
                'multi_component_sentiment_analysis',
                'weighted_composite_scoring',
                'sentiment_level_classification',
                'confidence_calculation',
                'market_condition_analysis',
                'sentiment_trend_tracking',
                'historical_sentiment_tracking',
                'technical_indicator_consensus',
                'market_breadth_analysis',
                'volatility_regime_detection'
            ],
            'description': 'Analyzes comprehensive market sentiment using technical indicators, market conditions, and historical patterns'
        }