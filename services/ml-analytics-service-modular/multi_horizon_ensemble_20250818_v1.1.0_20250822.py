"""
Multi-Horizon Ensemble Manager v1.0.0
Kombination und Optimierung von Vorhersagen über verschiedene Zeithorizonte

Autor: Claude Code
Datum: 18. August 2025
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncpg

# NumPy für Berechnungen
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

logger = logging.getLogger(__name__)

class MultiHorizonEnsembleManager:
    """
    Manager für Multi-Horizon Ensemble-Strategien
    
    Funktionalitäten:
    - Kombiniert Prognosen verschiedener Horizonte
    - Bewertet Horizon-spezifische Zuverlässigkeit 
    - Erstellt Investment-Empfehlungen basierend auf Zeitraum
    - Portfolio-optimierte Allokations-Vorschläge
    """
    
    # Investment-Strategy Mapping
    INVESTMENT_STRATEGIES = {
        "day_trading": {
            "primary_horizon": 7,
            "secondary_horizons": [30],
            "weights": {"7d": 0.8, "30d": 0.2},
            "risk_tolerance": "high",
            "description": "Kurzfristige Positionen (1-7 Tage)"
        },
        "swing_trading": {
            "primary_horizon": 30,
            "secondary_horizons": [7, 150],
            "weights": {"7d": 0.3, "30d": 0.5, "150d": 0.2},
            "risk_tolerance": "medium-high",
            "description": "Mittelfristige Positionen (1-8 Wochen)"
        },
        "position_trading": {
            "primary_horizon": 150,
            "secondary_horizons": [30, 365],
            "weights": {"30d": 0.2, "150d": 0.6, "365d": 0.2},
            "risk_tolerance": "medium",
            "description": "Langfristige Positionen (3-12 Monate)"
        },
        "buy_and_hold": {
            "primary_horizon": 365,
            "secondary_horizons": [150],
            "weights": {"150d": 0.3, "365d": 0.7},
            "risk_tolerance": "low-medium",
            "description": "Langzeitinvestments (1+ Jahre)"
        }
    }
    
    def __init__(self, database_pool: asyncpg.Pool):
        self.database_pool = database_pool
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if not NUMPY_AVAILABLE:
            self.logger.warning("NumPy not available - some calculations may be limited")
    
    async def get_multi_horizon_analysis(self, symbol: str, predictions: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Vollständige Multi-Horizon Analyse mit Investment-Empfehlungen
        
        Args:
            symbol: Stock Symbol
            predictions: Dict mit Vorhersagen für verschiedene Horizonte
                        Format: {"7d": {...}, "30d": {...}, ...}
        """
        try:
            self.logger.info(f"Starting multi-horizon analysis for {symbol}")
            
            if not predictions:
                return {"error": "No predictions provided for analysis"}
            
            # Basis-Analyse
            horizon_analysis = self._analyze_horizon_predictions(predictions)
            
            # Trend-Analyse über Horizonte
            trend_analysis = self._analyze_cross_horizon_trends(predictions)
            
            # Investment-Strategy Empfehlungen
            strategy_recommendations = self._generate_strategy_recommendations(predictions, symbol)
            
            # Risk-Assessment
            risk_assessment = await self._assess_multi_horizon_risk(symbol, predictions)
            
            # Portfolio-Allocation Vorschläge
            allocation_suggestions = self._calculate_optimal_allocation(predictions, risk_assessment)
            
            return {
                "symbol": symbol,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "horizon_analysis": horizon_analysis,
                "trend_analysis": trend_analysis,
                "strategy_recommendations": strategy_recommendations,
                "risk_assessment": risk_assessment,
                "allocation_suggestions": allocation_suggestions,
                "summary": self._generate_executive_summary(
                    horizon_analysis, trend_analysis, strategy_recommendations, risk_assessment
                )
            }
            
        except Exception as e:
            self.logger.error(f"Failed multi-horizon analysis for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_horizon_predictions(self, predictions: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Analysiert Vorhersagen für einzelne Horizonte
        """
        try:
            horizon_data = {}
            prices = []
            confidences = []
            
            for horizon, pred_data in predictions.items():
                if "predicted_price" in pred_data and "confidence_score" in pred_data:
                    price = pred_data["predicted_price"]
                    confidence = pred_data["confidence_score"]
                    
                    prices.append(price)
                    confidences.append(confidence)
                    
                    horizon_data[horizon] = {
                        "predicted_price": price,
                        "confidence_score": confidence,
                        "horizon_days": pred_data.get("horizon_days", 0),
                        "prediction_strength": self._calculate_prediction_strength(price, confidence)
                    }
            
            # Aggregierte Metriken
            if prices and NUMPY_AVAILABLE:
                price_array = np.array(prices)
                conf_array = np.array(confidences)
                
                aggregated = {
                    "price_mean": float(np.mean(price_array)),
                    "price_std": float(np.std(price_array)),
                    "price_range": float(np.max(price_array) - np.min(price_array)),
                    "confidence_mean": float(np.mean(conf_array)),
                    "confidence_weighted_price": float(np.average(price_array, weights=conf_array)),
                    "horizon_agreement": self._calculate_horizon_agreement(prices),
                    "prediction_divergence": self._calculate_prediction_divergence(prices)
                }
            else:
                aggregated = {"error": "Insufficient data or NumPy unavailable"}
            
            return {
                "individual_horizons": horizon_data,
                "aggregated_metrics": aggregated,
                "total_horizons": len(horizon_data)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze horizon predictions: {str(e)}")
            return {"error": str(e)}
    
    def _analyze_cross_horizon_trends(self, predictions: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Analysiert Trends zwischen verschiedenen Horizonten
        """
        try:
            if len(predictions) < 2:
                return {"trend": "insufficient_data", "message": "Need at least 2 horizons for trend analysis"}
            
            # Sortiere nach Horizon-Länge
            sorted_horizons = []
            for horizon, pred_data in predictions.items():
                if "predicted_price" in pred_data:
                    days = int(horizon.replace('d', ''))
                    sorted_horizons.append((days, pred_data["predicted_price"]))
            
            sorted_horizons.sort()
            
            if len(sorted_horizons) < 2:
                return {"trend": "insufficient_data"}
            
            # Trend-Analyse
            short_term = sorted_horizons[0][1]  # Kürzester Horizont
            long_term = sorted_horizons[-1][1]  # Längster Horizont
            
            trend_direction = "bullish" if long_term > short_term else "bearish"
            trend_magnitude = abs((long_term - short_term) / short_term) if short_term > 0 else 0
            
            # Klassifiziere Trend-Stärke
            if trend_magnitude > 0.2:
                trend_strength = "strong"
            elif trend_magnitude > 0.1:
                trend_strength = "moderate"
            else:
                trend_strength = "weak"
            
            # Konsistenz-Check
            prices = [price for _, price in sorted_horizons]
            if NUMPY_AVAILABLE:
                consistency_score = 1.0 - (np.std(prices) / np.mean(prices)) if np.mean(prices) > 0 else 0
            else:
                consistency_score = 0.5  # Fallback
            
            return {
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,
                "trend_magnitude": round(trend_magnitude * 100, 2),
                "consistency_score": round(float(consistency_score), 3),
                "short_term_price": short_term,
                "long_term_price": long_term,
                "price_progression": [{"horizon_days": days, "price": price} for days, price in sorted_horizons],
                "trend_interpretation": self._interpret_trend(trend_direction, trend_strength, consistency_score)
            }
            
        except Exception as e:
            self.logger.error(f"Failed cross-horizon trend analysis: {str(e)}")
            return {"error": str(e)}
    
    def _generate_strategy_recommendations(self, predictions: Dict[str, Dict], symbol: str) -> Dict[str, Any]:
        """
        Generiert Investment-Strategy Empfehlungen basierend auf Multi-Horizon Daten
        """
        try:
            strategy_scores = {}
            
            for strategy_name, strategy_config in self.INVESTMENT_STRATEGIES.items():
                score = self._calculate_strategy_score(predictions, strategy_config)
                
                strategy_scores[strategy_name] = {
                    "score": score,
                    "confidence": self._calculate_strategy_confidence(predictions, strategy_config),
                    "description": strategy_config["description"],
                    "risk_tolerance": strategy_config["risk_tolerance"],
                    "primary_horizon": f"{strategy_config['primary_horizon']}d",
                    "suitability": self._assess_strategy_suitability(score)
                }
            
            # Finde beste Strategy
            best_strategy = max(strategy_scores.items(), key=lambda x: x[1]["score"])
            
            return {
                "recommendations": strategy_scores,
                "best_strategy": {
                    "name": best_strategy[0],
                    "details": best_strategy[1],
                    "recommendation_strength": "high" if best_strategy[1]["score"] > 0.7 else "medium" if best_strategy[1]["score"] > 0.5 else "low"
                },
                "symbol": symbol,
                "analysis_note": "Strategies ranked by prediction alignment and risk-adjusted returns"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate strategy recommendations: {str(e)}")
            return {"error": str(e)}
    
    async def _assess_multi_horizon_risk(self, symbol: str, predictions: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Bewertet Risiken über verschiedene Horizonte
        """
        try:
            # Basis-Risiko aus Vorhersage-Varianz
            prediction_risks = self._calculate_prediction_risks(predictions)
            
            # Historische Volatilität (Mock-Implementierung)
            historical_volatility = await self._get_historical_volatility(symbol)
            
            # Horizon-spezifische Risiken
            horizon_risks = {}
            for horizon, pred_data in predictions.items():
                days = int(horizon.replace('d', ''))
                base_risk = historical_volatility * (days / 30.0) ** 0.5  # Volatilitäts-Skalierung
                confidence = pred_data.get("confidence_score", 0.5)
                
                # Höhere Unsicherheit = höheres Risiko
                uncertainty_multiplier = (1 - confidence) * 2 + 1
                
                horizon_risks[horizon] = {
                    "base_risk": round(base_risk, 4),
                    "uncertainty_risk": round(base_risk * uncertainty_multiplier, 4),
                    "confidence_adjusted": round(confidence, 3),
                    "risk_category": self._categorize_risk(base_risk * uncertainty_multiplier)
                }
            
            # Portfolio-Risiko bei Multi-Horizon Strategy
            portfolio_risk = self._calculate_portfolio_risk(horizon_risks)
            
            return {
                "individual_horizon_risks": horizon_risks,
                "portfolio_risk": portfolio_risk,
                "prediction_risks": prediction_risks,
                "overall_risk_assessment": self._assess_overall_risk(portfolio_risk, prediction_risks),
                "risk_mitigation_suggestions": self._suggest_risk_mitigation(horizon_risks)
            }
            
        except Exception as e:
            self.logger.error(f"Failed multi-horizon risk assessment: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_optimal_allocation(self, predictions: Dict[str, Dict], risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Berechnet optimale Portfolio-Allokation basierend auf Multi-Horizon Daten
        """
        try:
            if "individual_horizon_risks" not in risk_assessment:
                return {"error": "Risk assessment data missing"}
            
            allocations = {}
            
            # Strategie-basierte Allokationen
            for strategy_name, strategy_config in self.INVESTMENT_STRATEGIES.items():
                strategy_allocation = self._calculate_strategy_allocation(
                    predictions, strategy_config, risk_assessment
                )
                allocations[strategy_name] = strategy_allocation
            
            # Risk-Parity Allocation (gleichgewichtetes Risiko)
            risk_parity = self._calculate_risk_parity_allocation(risk_assessment)
            
            # Momentum-basierte Allocation
            momentum_allocation = self._calculate_momentum_allocation(predictions)
            
            return {
                "strategy_based_allocations": allocations,
                "risk_parity_allocation": risk_parity,
                "momentum_allocation": momentum_allocation,
                "recommended_allocation": self._select_recommended_allocation(
                    allocations, risk_parity, momentum_allocation
                ),
                "allocation_rationale": "Based on multi-horizon risk-adjusted returns and trend consistency"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate optimal allocation: {str(e)}")
            return {"error": str(e)}
    
    def _generate_executive_summary(self, horizon_analysis: Dict, trend_analysis: Dict, 
                                   strategy_recommendations: Dict, risk_assessment: Dict) -> Dict[str, Any]:
        """
        Generiert Executive Summary für Multi-Horizon Analyse
        """
        try:
            # Key Insights
            key_insights = []
            
            # Trend Insight
            if "trend_direction" in trend_analysis:
                trend_msg = f"Multi-horizon trend is {trend_analysis['trend_direction']} with {trend_analysis.get('trend_strength', 'unknown')} strength"
                key_insights.append(trend_msg)
            
            # Best Strategy
            if "best_strategy" in strategy_recommendations:
                best_strategy = strategy_recommendations["best_strategy"]
                strategy_msg = f"Recommended strategy: {best_strategy['name']} (score: {best_strategy['details']['score']:.2f})"
                key_insights.append(strategy_msg)
            
            # Risk Level
            if "overall_risk_assessment" in risk_assessment:
                risk_level = risk_assessment["overall_risk_assessment"].get("risk_level", "unknown")
                risk_msg = f"Overall risk level: {risk_level}"
                key_insights.append(risk_msg)
            
            # Horizon Agreement
            if "aggregated_metrics" in horizon_analysis:
                agreement = horizon_analysis["aggregated_metrics"].get("horizon_agreement", 0)
                agreement_msg = f"Horizon agreement score: {agreement:.2f}"
                key_insights.append(agreement_msg)
            
            # Action Items
            action_items = []
            
            if "best_strategy" in strategy_recommendations:
                strategy_name = strategy_recommendations["best_strategy"]["name"]
                action_items.append(f"Consider {strategy_name} approach for position sizing")
            
            if "trend_direction" in trend_analysis:
                trend = trend_analysis["trend_direction"]
                if trend == "bullish":
                    action_items.append("Monitor for entry opportunities on pullbacks")
                else:
                    action_items.append("Consider defensive positioning or short opportunities")
            
            # Confidence Level
            confidence_levels = []
            if "aggregated_metrics" in horizon_analysis:
                avg_confidence = horizon_analysis["aggregated_metrics"].get("confidence_mean", 0)
                confidence_levels.append(("prediction_confidence", avg_confidence))
            
            overall_confidence = np.mean([conf for _, conf in confidence_levels]) if confidence_levels and NUMPY_AVAILABLE else 0.5
            
            return {
                "key_insights": key_insights,
                "action_items": action_items,
                "overall_confidence": round(float(overall_confidence), 2),
                "summary_timestamp": datetime.utcnow().isoformat(),
                "analysis_completeness": len([x for x in [horizon_analysis, trend_analysis, strategy_recommendations, risk_assessment] if not x.get("error")]) / 4.0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate executive summary: {str(e)}")
            return {"error": str(e)}
    
    # Helper Methods
    
    def _calculate_prediction_strength(self, price: float, confidence: float) -> float:
        """Berechnet Vorhersage-Stärke"""
        return confidence * min(abs(price - 150.0) / 150.0 + 0.1, 1.0)  # Normalized strength
    
    def _calculate_horizon_agreement(self, prices: List[float]) -> float:
        """Berechnet Agreement-Score zwischen Horizonten"""
        if not NUMPY_AVAILABLE or len(prices) < 2:
            return 0.5
        
        price_array = np.array(prices)
        cv = np.std(price_array) / np.mean(price_array) if np.mean(price_array) > 0 else 1
        return max(0, 1 - cv)  # Lower coefficient of variation = higher agreement
    
    def _calculate_prediction_divergence(self, prices: List[float]) -> float:
        """Berechnet Divergenz zwischen Vorhersagen"""
        if not NUMPY_AVAILABLE or len(prices) < 2:
            return 0.0
        
        return float(np.std(prices) / np.mean(prices)) if np.mean(prices) > 0 else 0.0
    
    def _interpret_trend(self, direction: str, strength: str, consistency: float) -> str:
        """Interpretiert Trend-Daten"""
        if consistency > 0.8:
            reliability = "highly reliable"
        elif consistency > 0.6:
            reliability = "moderately reliable"
        else:
            reliability = "low reliability"
        
        return f"{direction.capitalize()} {strength} trend with {reliability}"
    
    def _calculate_strategy_score(self, predictions: Dict, strategy_config: Dict) -> float:
        """Berechnet Score für Investment-Strategy"""
        score = 0.0
        total_weight = 0.0
        
        for horizon, weight in strategy_config["weights"].items():
            if horizon in predictions and "confidence_score" in predictions[horizon]:
                conf = predictions[horizon]["confidence_score"]
                score += conf * weight
                total_weight += weight
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_strategy_confidence(self, predictions: Dict, strategy_config: Dict) -> float:
        """Berechnet Confidence für Strategy"""
        confidences = []
        for horizon in strategy_config["weights"].keys():
            if horizon in predictions and "confidence_score" in predictions[horizon]:
                confidences.append(predictions[horizon]["confidence_score"])
        
        return np.mean(confidences) if confidences and NUMPY_AVAILABLE else 0.5
    
    def _assess_strategy_suitability(self, score: float) -> str:
        """Bewertet Strategy-Eignung"""
        if score > 0.7:
            return "highly_suitable"
        elif score > 0.5:
            return "moderately_suitable"
        else:
            return "low_suitability"
    
    def _calculate_prediction_risks(self, predictions: Dict) -> Dict[str, float]:
        """Berechnet Vorhersage-basierte Risiken"""
        prices = [pred.get("predicted_price", 150) for pred in predictions.values()]
        confidences = [pred.get("confidence_score", 0.5) for pred in predictions.values()]
        
        if NUMPY_AVAILABLE and len(prices) > 1:
            price_volatility = np.std(prices) / np.mean(prices) if np.mean(prices) > 0 else 0
            confidence_risk = 1 - np.mean(confidences)
            return {
                "price_volatility_risk": float(price_volatility),
                "confidence_risk": float(confidence_risk),
                "combined_risk": float((price_volatility + confidence_risk) / 2)
            }
        
        return {"price_volatility_risk": 0.1, "confidence_risk": 0.3, "combined_risk": 0.2}
    
    async def _get_historical_volatility(self, symbol: str) -> float:
        """Holt historische Volatilität (Mock)"""
        # Mock-Implementierung - in Realität aus Datenbank
        volatility_map = {
            "AAPL": 0.25,
            "MSFT": 0.22,
            "GOOGL": 0.28,
            "TSLA": 0.45
        }
        return volatility_map.get(symbol, 0.30)
    
    def _categorize_risk(self, risk_value: float) -> str:
        """Kategorisiert Risiko-Level"""
        if risk_value > 0.4:
            return "high"
        elif risk_value > 0.2:
            return "medium"
        else:
            return "low"
    
    def _calculate_portfolio_risk(self, horizon_risks: Dict) -> Dict[str, float]:
        """Berechnet Portfolio-Risiko"""
        risks = [risk_data["uncertainty_risk"] for risk_data in horizon_risks.values()]
        
        if NUMPY_AVAILABLE and risks:
            return {
                "average_risk": float(np.mean(risks)),
                "max_risk": float(np.max(risks)),
                "risk_concentration": float(np.std(risks))
            }
        
        return {"average_risk": 0.2, "max_risk": 0.3, "risk_concentration": 0.1}
    
    def _assess_overall_risk(self, portfolio_risk: Dict, prediction_risks: Dict) -> Dict[str, Any]:
        """Bewertet Gesamt-Risiko"""
        avg_risk = (portfolio_risk.get("average_risk", 0.2) + 
                   prediction_risks.get("combined_risk", 0.2)) / 2
        
        return {
            "risk_level": self._categorize_risk(avg_risk),
            "risk_score": round(avg_risk, 3),
            "risk_factors": ["prediction_uncertainty", "horizon_divergence", "market_volatility"]
        }
    
    def _suggest_risk_mitigation(self, horizon_risks: Dict) -> List[str]:
        """Schlägt Risk-Mitigation vor"""
        suggestions = []
        
        high_risk_horizons = [h for h, data in horizon_risks.items() if data.get("risk_category") == "high"]
        
        if high_risk_horizons:
            suggestions.append(f"Reduce allocation to high-risk horizons: {', '.join(high_risk_horizons)}")
        
        suggestions.extend([
            "Consider position sizing based on confidence scores",
            "Implement stop-loss orders for downside protection",
            "Diversify across multiple timeframes and assets"
        ])
        
        return suggestions
    
    def _calculate_strategy_allocation(self, predictions: Dict, strategy_config: Dict, risk_assessment: Dict) -> Dict[str, float]:
        """Berechnet Strategy-spezifische Allokation"""
        allocation = {}
        
        for horizon, weight in strategy_config["weights"].items():
            if horizon in predictions:
                conf = predictions[horizon].get("confidence_score", 0.5)
                risk_adj = 1.0 - risk_assessment.get("individual_horizon_risks", {}).get(horizon, {}).get("base_risk", 0.2)
                allocation[horizon] = weight * conf * risk_adj
        
        # Normalisiere auf 100%
        total = sum(allocation.values())
        if total > 0:
            allocation = {k: v/total for k, v in allocation.items()}
        
        return allocation
    
    def _calculate_risk_parity_allocation(self, risk_assessment: Dict) -> Dict[str, float]:
        """Berechnet Risk-Parity Allokation"""
        horizon_risks = risk_assessment.get("individual_horizon_risks", {})
        
        if not horizon_risks:
            return {}
        
        # Inverse Gewichtung nach Risiko
        inverse_risks = {}
        for horizon, risk_data in horizon_risks.items():
            risk = risk_data.get("uncertainty_risk", 0.2)
            inverse_risks[horizon] = 1.0 / (risk + 0.01)  # Avoid division by zero
        
        # Normalisiere
        total_inverse = sum(inverse_risks.values())
        return {k: v/total_inverse for k, v in inverse_risks.items()}
    
    def _calculate_momentum_allocation(self, predictions: Dict) -> Dict[str, float]:
        """Berechnet Momentum-basierte Allokation"""
        if len(predictions) < 2:
            return {}
        
        # Sortiere nach Returns
        returns = {}
        for horizon, pred_data in predictions.items():
            price = pred_data.get("predicted_price", 150)
            returns[horizon] = (price - 150.0) / 150.0  # Simple return assumption
        
        # Gewichte basierend auf relativem Return
        max_return = max(returns.values()) if returns.values() else 0
        min_return = min(returns.values()) if returns.values() else 0
        
        if max_return == min_return:
            # Gleichgewichtung wenn alle Returns gleich
            equal_weight = 1.0 / len(returns)
            return {k: equal_weight for k in returns.keys()}
        
        # Normalisierte Momentum-Gewichtung
        momentum_weights = {}
        for horizon, ret in returns.items():
            normalized = (ret - min_return) / (max_return - min_return) if max_return > min_return else 0.5
            momentum_weights[horizon] = normalized
        
        # Normalisiere auf 100%
        total_weight = sum(momentum_weights.values())
        if total_weight > 0:
            momentum_weights = {k: v/total_weight for k, v in momentum_weights.items()}
        
        return momentum_weights
    
    def _select_recommended_allocation(self, strategy_allocs: Dict, risk_parity: Dict, momentum: Dict) -> Dict[str, Any]:
        """Wählt empfohlene Allokation"""
        # Finde beste Strategy-Allocation
        best_strategy = None
        best_score = 0
        
        for strategy, allocation in strategy_allocs.items():
            if allocation and not isinstance(allocation, dict):
                continue
                
            # Einfacher Score: Summe der Gewichtungen * durchschnittliche Allokation
            if allocation:
                score = sum(allocation.values()) * len(allocation)
                if score > best_score:
                    best_score = score
                    best_strategy = strategy
        
        recommendation = {
            "primary_method": "strategy_based",
            "recommended_strategy": best_strategy,
            "allocation": strategy_allocs.get(best_strategy, {}) if best_strategy else {},
            "alternative_allocations": {
                "risk_parity": risk_parity,
                "momentum": momentum
            },
            "rationale": f"Strategy-based allocation using {best_strategy} approach" if best_strategy else "Fallback to risk parity"
        }
        
        if not recommendation["allocation"]:
            recommendation["allocation"] = risk_parity
            recommendation["primary_method"] = "risk_parity"
        
        return recommendation

# Export für einfache Imports
__all__ = ['MultiHorizonEnsembleManager']