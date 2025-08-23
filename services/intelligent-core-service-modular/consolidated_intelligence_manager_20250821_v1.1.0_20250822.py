#!/usr/bin/env python3
"""
Consolidated Intelligence Manager v1.0.0
Clean Architecture - Konsolidiert 8 Over-Engineering Module in eine saubere Klasse

Konsolidierte Module:
- action_priority_calculation_module_v1_0_0_20250806.py
- decision_history_management_module_v1_0_1_20250807.py
- market_sentiment_analysis_module_v1_2_0_20250810.py
- reasoning_generation_module_v1_0_3_20250808.py
- recommendation_generator_module_v1_4_0_20250812.py
- risk_assessment_module_v1_3_1_20250811.py
- rules_management_module_v1_0_0_20250805.py
- score_adjustment_module_v1_1_2_20250809.py

Code-Qualität: HÖCHSTE PRIORITÄT
- SOLID Principles: Single Class für alle Intelligence Funktionen
- Clean Code Architecture: Klare Methoden-Trennung
- DRY Principle: Eliminiert Code-Duplikation zwischen Modulen
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Import Manager für Clean Architecture
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from config.central_config_v1_0_0_20250821 import config
except ImportError:
    config = None

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Action Type Enumeration"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WATCH = "watch"
    ANALYZE = "analyze"


class RiskLevel(Enum):
    """Risk Level Enumeration"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class MarketSentiment(Enum):
    """Market Sentiment Enumeration"""
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


@dataclass
class IntelligenceRecommendation:
    """Comprehensive Intelligence Recommendation"""
    symbol: str
    timestamp: str
    
    # Core Recommendation
    action: ActionType
    confidence_score: float  # 0-100
    priority_score: float   # 0-100
    
    # Risk Assessment
    risk_level: RiskLevel
    risk_score: float      # 0-100
    
    # Market Analysis
    market_sentiment: MarketSentiment
    sentiment_score: float  # -100 to +100
    
    # Reasoning
    reasoning: str
    key_factors: List[str]
    
    # Price Targets
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    
    # Metadata
    rule_triggers: List[str] = None
    decision_id: str = ""
    
    def __post_init__(self):
        if self.rule_triggers is None:
            self.rule_triggers = []


@dataclass
class DecisionHistory:
    """Decision History Record"""
    decision_id: str
    symbol: str
    timestamp: str
    recommendation: IntelligenceRecommendation
    outcome: Optional[str] = None
    performance: Optional[float] = None


class ConsolidatedIntelligenceManager:
    """
    Konsolidierter Intelligence Manager
    Clean Architecture: ALLE Intelligence Funktionen in einer Klasse
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Decision History Management
        self.decision_history: List[DecisionHistory] = []
        self.max_history_size = 1000
        
        # Rules Management
        self.trading_rules = self._initialize_default_rules()
        
        # Market Sentiment Cache
        self.sentiment_cache = {}
        self.sentiment_cache_expiry = timedelta(hours=1)
    
    def _initialize_default_rules(self) -> Dict[str, Any]:
        """
        Initialize Default Trading Rules (konsolidiert rules_management_module)
        """
        return {
            "buy_rules": [
                {"name": "rsi_oversold", "condition": "rsi < 30", "weight": 0.8},
                {"name": "macd_bullish", "condition": "macd_histogram > 0", "weight": 0.7},
                {"name": "price_above_sma", "condition": "price > sma_20", "weight": 0.6},
                {"name": "volume_surge", "condition": "volume_ratio > 1.5", "weight": 0.5}
            ],
            "sell_rules": [
                {"name": "rsi_overbought", "condition": "rsi > 70", "weight": 0.8},
                {"name": "macd_bearish", "condition": "macd_histogram < 0", "weight": 0.7},
                {"name": "price_below_sma", "condition": "price < sma_50", "weight": 0.6},
                {"name": "stop_loss_trigger", "condition": "price < stop_loss", "weight": 1.0}
            ],
            "risk_rules": [
                {"name": "high_volatility", "condition": "atr > avg_atr * 2", "weight": 0.9},
                {"name": "low_volume", "condition": "volume_ratio < 0.5", "weight": 0.6},
                {"name": "near_resistance", "condition": "price > resistance * 0.95", "weight": 0.7}
            ]
        }
    
    def assess_risk(self, symbol: str, technical_data: Dict[str, Any]) -> Tuple[RiskLevel, float]:
        """
        Risk Assessment (konsolidiert risk_assessment_module)
        """
        try:
            risk_score = 0.0
            max_score = 0.0
            
            # Technical Risk Factors
            rsi = technical_data.get('rsi', 50)
            atr = technical_data.get('atr', 0)
            bb_width = technical_data.get('bb_width', 0)
            volume_ratio = technical_data.get('volume_ratio', 1.0)
            
            # RSI Risk (extreme values = higher risk)
            if rsi > 80 or rsi < 20:
                risk_score += 25
            elif rsi > 70 or rsi < 30:
                risk_score += 15
            max_score += 25
            
            # Volatility Risk (high ATR = higher risk)
            if atr > 0:
                volatility_risk = min(atr * 10, 30)  # Cap at 30
                risk_score += volatility_risk
            max_score += 30
            
            # Bollinger Bands Width (high width = higher volatility = higher risk)
            if bb_width > 5:
                risk_score += 20
            elif bb_width > 3:
                risk_score += 10
            max_score += 20
            
            # Volume Risk (low volume = higher risk)
            if volume_ratio < 0.5:
                risk_score += 15
            elif volume_ratio < 0.8:
                risk_score += 8
            max_score += 15
            
            # Market Position Risk
            price = technical_data.get('current_price', 0)
            resistance = technical_data.get('resistance_level', price * 1.1)
            support = technical_data.get('support_level', price * 0.9)
            
            if price > resistance * 0.98:  # Near resistance
                risk_score += 10
            elif price < support * 1.02:   # Near support
                risk_score += 10
            max_score += 10
            
            # Normalize risk score
            normalized_risk = (risk_score / max_score) * 100 if max_score > 0 else 50
            
            # Determine risk level
            if normalized_risk >= 75:
                risk_level = RiskLevel.EXTREME
            elif normalized_risk >= 50:
                risk_level = RiskLevel.HIGH
            elif normalized_risk >= 25:
                risk_level = RiskLevel.MODERATE
            else:
                risk_level = RiskLevel.LOW
            
            return risk_level, normalized_risk
            
        except Exception as e:
            self.logger.error(f"Risk assessment failed for {symbol}: {e}")
            return RiskLevel.HIGH, 75.0
    
    def analyze_market_sentiment(self, symbol: str, technical_data: Dict[str, Any]) -> Tuple[MarketSentiment, float]:
        """
        Market Sentiment Analysis (konsolidiert market_sentiment_analysis_module)
        """
        try:
            # Check cache
            cache_key = f"{symbol}_sentiment"
            if cache_key in self.sentiment_cache:
                cached_sentiment, cached_time = self.sentiment_cache[cache_key]
                if datetime.now() - cached_time < self.sentiment_cache_expiry:
                    return cached_sentiment
            
            sentiment_score = 0.0
            factors = []
            
            # Technical Sentiment Indicators
            rsi = technical_data.get('rsi', 50)
            macd_histogram = technical_data.get('macd_histogram', 0)
            price = technical_data.get('current_price', 0)
            sma_20 = technical_data.get('sma_20', price)
            sma_50 = technical_data.get('sma_50', price)
            volume_ratio = technical_data.get('volume_ratio', 1.0)
            
            # RSI Sentiment
            if rsi > 70:
                sentiment_score += 10  # Overbought = negative sentiment
                factors.append("Overbought RSI")
            elif rsi < 30:
                sentiment_score -= 10  # Oversold = positive sentiment
                factors.append("Oversold RSI")
            else:
                rsi_sentiment = (rsi - 50) * 0.2  # Scale to -10 to +10
                sentiment_score += rsi_sentiment
            
            # MACD Sentiment
            if macd_histogram > 0:
                sentiment_score -= 15  # Bullish MACD
                factors.append("Bullish MACD")
            else:
                sentiment_score += 15  # Bearish MACD
                factors.append("Bearish MACD")
            
            # Moving Average Sentiment
            if price > sma_20 > sma_50:
                sentiment_score -= 20  # Strong bullish trend
                factors.append("Strong uptrend")
            elif price < sma_20 < sma_50:
                sentiment_score += 20  # Strong bearish trend
                factors.append("Strong downtrend")
            elif price > sma_20:
                sentiment_score -= 10  # Mild bullish
                factors.append("Above short-term MA")
            elif price < sma_20:
                sentiment_score += 10  # Mild bearish
                factors.append("Below short-term MA")
            
            # Volume Sentiment
            if volume_ratio > 1.5:
                # High volume amplifies sentiment
                sentiment_score *= 1.2
                factors.append("High volume confirms trend")
            elif volume_ratio < 0.7:
                # Low volume weakens sentiment
                sentiment_score *= 0.8
                factors.append("Low volume weakens signal")
            
            # Clamp sentiment score to -100 to +100
            sentiment_score = max(-100, min(100, sentiment_score))
            
            # Determine sentiment level
            if sentiment_score <= -60:
                market_sentiment = MarketSentiment.VERY_BULLISH
            elif sentiment_score <= -20:
                market_sentiment = MarketSentiment.BULLISH
            elif sentiment_score <= 20:
                market_sentiment = MarketSentiment.NEUTRAL
            elif sentiment_score <= 60:
                market_sentiment = MarketSentiment.BEARISH
            else:
                market_sentiment = MarketSentiment.VERY_BEARISH
            
            # Cache result
            result = (market_sentiment, sentiment_score)
            self.sentiment_cache[cache_key] = (result, datetime.now())
            
            return result
            
        except Exception as e:
            self.logger.error(f"Sentiment analysis failed for {symbol}: {e}")
            return MarketSentiment.NEUTRAL, 0.0
    
    def calculate_action_priority(self, symbol: str, technical_data: Dict[str, Any], 
                                risk_level: RiskLevel, sentiment: MarketSentiment) -> Tuple[ActionType, float]:
        """
        Action Priority Calculation (konsolidiert action_priority_calculation_module)
        """
        try:
            action_scores = {
                ActionType.BUY: 0.0,
                ActionType.SELL: 0.0,
                ActionType.HOLD: 50.0,  # Base score for HOLD
                ActionType.WATCH: 30.0,  # Base score for WATCH
                ActionType.ANALYZE: 20.0  # Base score for ANALYZE
            }
            
            # Evaluate buy rules
            for rule in self.trading_rules["buy_rules"]:
                if self._evaluate_rule(rule, technical_data):
                    action_scores[ActionType.BUY] += rule["weight"] * 100
            
            # Evaluate sell rules
            for rule in self.trading_rules["sell_rules"]:
                if self._evaluate_rule(rule, technical_data):
                    action_scores[ActionType.SELL] += rule["weight"] * 100
            
            # Sentiment influence
            if sentiment in [MarketSentiment.VERY_BULLISH, MarketSentiment.BULLISH]:
                action_scores[ActionType.BUY] += 20
                action_scores[ActionType.SELL] -= 15
            elif sentiment in [MarketSentiment.VERY_BEARISH, MarketSentiment.BEARISH]:
                action_scores[ActionType.SELL] += 20
                action_scores[ActionType.BUY] -= 15
            
            # Risk influence
            if risk_level == RiskLevel.EXTREME:
                action_scores[ActionType.BUY] -= 30
                action_scores[ActionType.SELL] += 15
                action_scores[ActionType.HOLD] += 20
            elif risk_level == RiskLevel.HIGH:
                action_scores[ActionType.BUY] -= 15
                action_scores[ActionType.HOLD] += 10
            
            # Find best action
            best_action = max(action_scores, key=action_scores.get)
            priority_score = min(100, max(0, action_scores[best_action]))
            
            return best_action, priority_score
            
        except Exception as e:
            self.logger.error(f"Action priority calculation failed for {symbol}: {e}")
            return ActionType.HOLD, 50.0
    
    def _evaluate_rule(self, rule: Dict[str, Any], technical_data: Dict[str, Any]) -> bool:
        """
        Simple Rule Evaluation (konsolidiert rules_management_module)
        """
        try:
            condition = rule["condition"]
            
            # Simple condition evaluation for common technical indicators
            if "rsi < 30" in condition:
                return technical_data.get('rsi', 50) < 30
            elif "rsi > 70" in condition:
                return technical_data.get('rsi', 50) > 70
            elif "macd_histogram > 0" in condition:
                return technical_data.get('macd_histogram', 0) > 0
            elif "macd_histogram < 0" in condition:
                return technical_data.get('macd_histogram', 0) < 0
            elif "price > sma_20" in condition:
                price = technical_data.get('current_price', 0)
                sma_20 = technical_data.get('sma_20', price)
                return price > sma_20
            elif "price < sma_50" in condition:
                price = technical_data.get('current_price', 0)
                sma_50 = technical_data.get('sma_50', price)
                return price < sma_50
            elif "volume_ratio > 1.5" in condition:
                return technical_data.get('volume_ratio', 1.0) > 1.5
            elif "volume_ratio < 0.5" in condition:
                return technical_data.get('volume_ratio', 1.0) < 0.5
            
            # Default to False for unknown conditions
            return False
            
        except Exception as e:
            self.logger.error(f"Rule evaluation failed: {e}")
            return False
    
    def generate_reasoning(self, symbol: str, technical_data: Dict[str, Any], 
                          action: ActionType, risk_level: RiskLevel, 
                          sentiment: MarketSentiment) -> Tuple[str, List[str]]:
        """
        Reasoning Generation (konsolidiert reasoning_generation_module)
        """
        try:
            key_factors = []
            reasoning_parts = []
            
            # Current market state
            price = technical_data.get('current_price', 0)
            rsi = technical_data.get('rsi', 50)
            
            reasoning_parts.append(f"Current price: ${price:.2f}")
            
            # RSI Analysis
            if rsi > 70:
                reasoning_parts.append(f"RSI ({rsi:.1f}) indicates overbought conditions")
                key_factors.append("Overbought RSI")
            elif rsi < 30:
                reasoning_parts.append(f"RSI ({rsi:.1f}) indicates oversold conditions")
                key_factors.append("Oversold RSI")
            else:
                reasoning_parts.append(f"RSI ({rsi:.1f}) shows neutral momentum")
            
            # Trend Analysis
            sma_20 = technical_data.get('sma_20', price)
            sma_50 = technical_data.get('sma_50', price)
            
            if price > sma_20 > sma_50:
                reasoning_parts.append("Strong uptrend confirmed by moving averages")
                key_factors.append("Bullish trend")
            elif price < sma_20 < sma_50:
                reasoning_parts.append("Strong downtrend confirmed by moving averages")
                key_factors.append("Bearish trend")
            else:
                reasoning_parts.append("Mixed trend signals from moving averages")
                key_factors.append("Sideways trend")
            
            # Risk Assessment
            reasoning_parts.append(f"Risk level: {risk_level.value}")
            key_factors.append(f"{risk_level.value.title()} risk")
            
            # Market Sentiment
            reasoning_parts.append(f"Market sentiment: {sentiment.value}")
            key_factors.append(f"{sentiment.value.title()} sentiment")
            
            # Action Justification
            if action == ActionType.BUY:
                reasoning_parts.append("Technical indicators suggest buying opportunity")
            elif action == ActionType.SELL:
                reasoning_parts.append("Technical indicators suggest selling opportunity")
            elif action == ActionType.HOLD:
                reasoning_parts.append("Mixed signals suggest holding current position")
            else:
                reasoning_parts.append(f"Recommendation: {action.value}")
            
            reasoning = ". ".join(reasoning_parts) + "."
            
            return reasoning, key_factors
            
        except Exception as e:
            self.logger.error(f"Reasoning generation failed for {symbol}: {e}")
            return f"Analysis completed for {symbol}", ["Technical analysis"]
    
    def adjust_confidence_score(self, base_score: float, risk_level: RiskLevel, 
                              volume_ratio: float, trend_strength: float) -> float:
        """
        Score Adjustment (konsolidiert score_adjustment_module)
        """
        try:
            adjusted_score = base_score
            
            # Risk adjustment
            if risk_level == RiskLevel.LOW:
                adjusted_score *= 1.1
            elif risk_level == RiskLevel.HIGH:
                adjusted_score *= 0.8
            elif risk_level == RiskLevel.EXTREME:
                adjusted_score *= 0.6
            
            # Volume confirmation
            if volume_ratio > 1.5:
                adjusted_score *= 1.2  # High volume confirms signal
            elif volume_ratio < 0.7:
                adjusted_score *= 0.8  # Low volume weakens signal
            
            # Trend strength
            if trend_strength and trend_strength > 50:
                adjusted_score *= 1.1  # Strong trend increases confidence
            elif trend_strength and trend_strength < 25:
                adjusted_score *= 0.9  # Weak trend decreases confidence
            
            # Clamp to 0-100 range
            return max(0, min(100, adjusted_score))
            
        except Exception as e:
            self.logger.error(f"Score adjustment failed: {e}")
            return base_score
    
    def store_decision(self, recommendation: IntelligenceRecommendation) -> str:
        """
        Decision History Management (konsolidiert decision_history_management_module)
        """
        try:
            decision_id = f"{recommendation.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            decision_record = DecisionHistory(
                decision_id=decision_id,
                symbol=recommendation.symbol,
                timestamp=recommendation.timestamp,
                recommendation=recommendation
            )
            
            self.decision_history.append(decision_record)
            
            # Limit history size
            if len(self.decision_history) > self.max_history_size:
                self.decision_history = self.decision_history[-self.max_history_size:]
            
            return decision_id
            
        except Exception as e:
            self.logger.error(f"Failed to store decision: {e}")
            return ""
    
    async def generate_recommendation(self, symbol: str, technical_data: Dict[str, Any]) -> Optional[IntelligenceRecommendation]:
        """
        Comprehensive Recommendation Generation (konsolidiert recommendation_generator_module)
        Clean Architecture: Single Method für vollständige Intelligence Analysis
        """
        try:
            self.logger.info(f"Generating intelligence recommendation for {symbol}")
            
            # 1. Risk Assessment
            risk_level, risk_score = self.assess_risk(symbol, technical_data)
            
            # 2. Market Sentiment Analysis
            market_sentiment, sentiment_score = self.analyze_market_sentiment(symbol, technical_data)
            
            # 3. Action Priority Calculation
            action, priority_score = self.calculate_action_priority(symbol, technical_data, risk_level, market_sentiment)
            
            # 4. Confidence Score Adjustment
            base_confidence = priority_score
            volume_ratio = technical_data.get('volume_ratio', 1.0)
            trend_strength = technical_data.get('trend_strength', 50)
            confidence_score = self.adjust_confidence_score(base_confidence, risk_level, volume_ratio, trend_strength)
            
            # 5. Reasoning Generation
            reasoning, key_factors = self.generate_reasoning(symbol, technical_data, action, risk_level, market_sentiment)
            
            # 6. Price Targets (simple calculation)
            current_price = technical_data.get('current_price', 0)
            target_price = None
            stop_loss = None
            
            if action == ActionType.BUY and current_price > 0:
                resistance = technical_data.get('resistance_level', current_price * 1.05)
                target_price = resistance * 0.95  # Conservative target
                stop_loss = current_price * 0.95  # 5% stop loss
            elif action == ActionType.SELL and current_price > 0:
                support = technical_data.get('support_level', current_price * 0.95)
                target_price = support * 1.05  # Conservative target
                stop_loss = current_price * 1.05  # 5% stop loss
            
            # 7. Build Recommendation
            recommendation = IntelligenceRecommendation(
                symbol=symbol,
                timestamp=datetime.now().isoformat(),
                action=action,
                confidence_score=confidence_score,
                priority_score=priority_score,
                risk_level=risk_level,
                risk_score=risk_score,
                market_sentiment=market_sentiment,
                sentiment_score=sentiment_score,
                reasoning=reasoning,
                key_factors=key_factors,
                target_price=target_price,
                stop_loss=stop_loss,
                rule_triggers=[]  # Could be enhanced to track which rules triggered
            )
            
            # 8. Store Decision
            decision_id = self.store_decision(recommendation)
            recommendation.decision_id = decision_id
            
            self.logger.info(f"Intelligence recommendation generated for {symbol}: {action.value}")
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Recommendation generation failed for {symbol}: {e}")
            return None
    
    def get_decision_history(self, symbol: Optional[str] = None, limit: int = 50) -> List[DecisionHistory]:
        """Get Decision History"""
        try:
            if symbol:
                filtered_history = [d for d in self.decision_history if d.symbol == symbol]
            else:
                filtered_history = self.decision_history
            
            return filtered_history[-limit:]
            
        except Exception as e:
            self.logger.error(f"Failed to get decision history: {e}")
            return []


# Globale Instanz für einfache Verwendung
intelligence_manager = ConsolidatedIntelligenceManager()


# Convenience Functions
async def generate_recommendation(symbol: str, technical_data: Dict[str, Any]) -> Optional[IntelligenceRecommendation]:
    """Convenience-Funktion für Recommendation Generation"""
    return await intelligence_manager.generate_recommendation(symbol, technical_data)


if __name__ == "__main__":
    # Debug/Test-Modus
    async def test_intelligence():
        print("=== Consolidated Intelligence Manager Test ===")
        
        # Sample technical data
        sample_data = {
            'current_price': 150.0,
            'rsi': 65.0,
            'macd_histogram': 0.5,
            'sma_20': 148.0,
            'sma_50': 145.0,
            'atr': 2.5,
            'bb_width': 4.0,
            'volume_ratio': 1.3,
            'resistance_level': 155.0,
            'support_level': 142.0,
            'trend_strength': 65.0
        }
        
        recommendation = await generate_recommendation("AAPL", sample_data)
        
        if recommendation:
            print(f"\nRecommendation for AAPL:")
            print(f"  Action: {recommendation.action.value}")
            print(f"  Confidence: {recommendation.confidence_score:.1f}%")
            print(f"  Risk Level: {recommendation.risk_level.value}")
            print(f"  Sentiment: {recommendation.market_sentiment.value}")
            print(f"  Target Price: ${recommendation.target_price:.2f}" if recommendation.target_price else "  Target Price: N/A")
            print(f"  Stop Loss: ${recommendation.stop_loss:.2f}" if recommendation.stop_loss else "  Stop Loss: N/A")
            print(f"  Reasoning: {recommendation.reasoning}")
        else:
            print("Recommendation generation failed")
    
    asyncio.run(test_intelligence())