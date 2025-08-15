"""
Recommendation Generator Module - Single Function Module
Generates investment recommendations based on ML scores and indicators
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


class RecommendationGeneratorModule(SingleFunctionModuleBase):
    """Generate investment recommendations based on ML scores and technical indicators"""
    
    def __init__(self, event_bus):
        super().__init__("recommendation_generator", event_bus)
        self.recommendation_rules = {
            'strong_buy_threshold': 0.8,
            'buy_threshold': 0.65,
            'sell_threshold': 0.35,
            'strong_sell_threshold': 0.2,
            'confidence_minimum': 0.4
        }
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('recommendation.generation.request', self.process_event)
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
                'rules': self.recommendation_rules,
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'recommendation.generation.request':
            ml_scores = event.get('ml_scores', {})
            indicators = event.get('indicators', {})
            confidence = event.get('confidence', 0.5)
            adjusted_score = event.get('adjusted_score')
            
            recommendation = await self.generate_recommendation(ml_scores, indicators, confidence, adjusted_score)
            
            response_event = {
                'event_type': 'recommendation.generation.response',
                'recommendation': recommendation['recommendation'],
                'base_score': recommendation['base_score'],
                'final_score': recommendation['final_score'],
                'confidence_applied': recommendation['confidence_applied'],
                'rules_applied': recommendation['rules_applied'],
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def generate_recommendation(self, ml_scores: Dict[str, float], indicators: Dict[str, float], confidence: float, adjusted_score: float = None) -> Dict[str, Any]:
        """Generate investment recommendation from ML scores and indicators"""
        try:
            # Calculate base score if not provided
            if adjusted_score is None:
                base_score = await self._calculate_composite_score(ml_scores)
            else:
                base_score = adjusted_score
            
            # Apply confidence filter
            if confidence < self.recommendation_rules['confidence_minimum']:
                self.logger.info("Low confidence recommendation override", 
                               confidence=confidence, 
                               minimum=self.recommendation_rules['confidence_minimum'])
                return {
                    'recommendation': 'HOLD',
                    'base_score': base_score,
                    'final_score': base_score,
                    'confidence_applied': True,
                    'rules_applied': ['confidence_filter']
                }
            
            # Generate recommendation based on score thresholds
            recommendation, rules_applied = await self._apply_recommendation_rules(base_score)
            
            self.logger.debug("Recommendation generated", 
                            recommendation=recommendation,
                            base_score=base_score,
                            confidence=confidence)
            
            return {
                'recommendation': recommendation,
                'base_score': base_score,
                'final_score': base_score,
                'confidence_applied': False,
                'rules_applied': rules_applied
            }
            
        except Exception as e:
            self.logger.error("Error generating recommendation", error=str(e))
            return {
                'recommendation': 'HOLD',
                'base_score': 0.5,
                'final_score': 0.5,
                'confidence_applied': False,
                'rules_applied': ['error_fallback']
            }
    
    async def _calculate_composite_score(self, ml_scores: Dict[str, float]) -> float:
        """Calculate composite score from ML scores"""
        try:
            # Use existing composite score if available
            if 'composite_score' in ml_scores:
                return ml_scores['composite_score']
            
            # Calculate weighted composite from individual scores
            if not ml_scores:
                return 0.5  # Neutral score
            
            # Standard ML score components with weights
            score_weights = {
                'price_score': 0.4,
                'trend_score': 0.4,
                'volatility_score': 0.2,
                'volume_score': 0.1,
                'momentum_score': 0.3
            }
            
            total_weight = 0.0
            weighted_sum = 0.0
            
            for score_key, weight in score_weights.items():
                if score_key in ml_scores:
                    weighted_sum += ml_scores[score_key] * weight
                    total_weight += weight
            
            # If no recognized scores, use simple average
            if total_weight == 0:
                return sum(ml_scores.values()) / len(ml_scores)
            
            # Normalize by actual weights used
            composite_score = weighted_sum / total_weight
            
            # Ensure score is in valid range
            return max(0.0, min(1.0, composite_score))
            
        except Exception as e:
            self.logger.error("Error calculating composite score", error=str(e))
            return 0.5
    
    async def _apply_recommendation_rules(self, score: float) -> tuple:
        """Apply recommendation rules to score"""
        try:
            rules_applied = []
            
            # Apply threshold-based rules
            if score >= self.recommendation_rules['strong_buy_threshold']:
                recommendation = "STRONG_BUY"
                rules_applied.append(f"strong_buy_threshold_{self.recommendation_rules['strong_buy_threshold']}")
            elif score >= self.recommendation_rules['buy_threshold']:
                recommendation = "BUY"
                rules_applied.append(f"buy_threshold_{self.recommendation_rules['buy_threshold']}")
            elif score <= self.recommendation_rules['strong_sell_threshold']:
                recommendation = "STRONG_SELL"
                rules_applied.append(f"strong_sell_threshold_{self.recommendation_rules['strong_sell_threshold']}")
            elif score <= self.recommendation_rules['sell_threshold']:
                recommendation = "SELL"
                rules_applied.append(f"sell_threshold_{self.recommendation_rules['sell_threshold']}")
            else:
                recommendation = "HOLD"
                rules_applied.append("neutral_zone")
            
            return recommendation, rules_applied
            
        except Exception as e:
            self.logger.error("Error applying recommendation rules", error=str(e))
            return "HOLD", ["error_fallback"]
    
    def update_recommendation_rules(self, new_rules: Dict[str, float]) -> bool:
        """Update recommendation threshold rules"""
        try:
            valid_rules = ['strong_buy_threshold', 'buy_threshold', 'sell_threshold', 'strong_sell_threshold', 'confidence_minimum']
            
            for rule_name, rule_value in new_rules.items():
                if rule_name in valid_rules and 0.0 <= rule_value <= 1.0:
                    self.recommendation_rules[rule_name] = rule_value
                    self.logger.info("Updated recommendation rule", rule=rule_name, value=rule_value)
                else:
                    self.logger.warning("Invalid recommendation rule", rule=rule_name, value=rule_value)
            
            return True
            
        except Exception as e:
            self.logger.error("Error updating recommendation rules", error=str(e))
            return False
    
    def validate_recommendation_logic(self) -> Dict[str, Any]:
        """Validate recommendation rule logic for consistency"""
        try:
            validation = {
                'valid': True,
                'issues': [],
                'rules': self.recommendation_rules.copy()
            }
            
            # Check threshold ordering
            thresholds = [
                ('strong_sell_threshold', self.recommendation_rules['strong_sell_threshold']),
                ('sell_threshold', self.recommendation_rules['sell_threshold']),
                ('buy_threshold', self.recommendation_rules['buy_threshold']),
                ('strong_buy_threshold', self.recommendation_rules['strong_buy_threshold'])
            ]
            
            for i in range(len(thresholds) - 1):
                if thresholds[i][1] >= thresholds[i + 1][1]:
                    validation['valid'] = False
                    validation['issues'].append(f"{thresholds[i][0]} ({thresholds[i][1]}) should be less than {thresholds[i + 1][0]} ({thresholds[i + 1][1]})")
            
            # Check confidence minimum
            confidence_min = self.recommendation_rules['confidence_minimum']
            if not 0.0 <= confidence_min <= 1.0:
                validation['valid'] = False
                validation['issues'].append(f"confidence_minimum ({confidence_min}) should be between 0.0 and 1.0")
            
            return validation
            
        except Exception as e:
            self.logger.error("Error validating recommendation logic", error=str(e))
            return {
                'valid': False,
                'issues': [str(e)],
                'rules': {}
            }
    
    def get_recommendation_distribution(self, scores: list) -> Dict[str, Any]:
        """Analyze recommendation distribution for given scores"""
        try:
            if not scores:
                return {'error': 'No scores provided'}
            
            distribution = {
                'STRONG_BUY': 0,
                'BUY': 0,
                'HOLD': 0,
                'SELL': 0,
                'STRONG_SELL': 0
            }
            
            for score in scores:
                if score >= self.recommendation_rules['strong_buy_threshold']:
                    distribution['STRONG_BUY'] += 1
                elif score >= self.recommendation_rules['buy_threshold']:
                    distribution['BUY'] += 1
                elif score <= self.recommendation_rules['strong_sell_threshold']:
                    distribution['STRONG_SELL'] += 1
                elif score <= self.recommendation_rules['sell_threshold']:
                    distribution['SELL'] += 1
                else:
                    distribution['HOLD'] += 1
            
            total = len(scores)
            percentages = {k: (v / total * 100) for k, v in distribution.items()}
            
            return {
                'total_scores': total,
                'distribution': distribution,
                'percentages': percentages,
                'rules_used': self.recommendation_rules.copy()
            }
            
        except Exception as e:
            self.logger.error("Error analyzing recommendation distribution", error=str(e))
            return {'error': str(e)}
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'recommendation_generator',
            'recommendation_rules': self.recommendation_rules.copy(),
            'supported_recommendations': ['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'],
            'features': [
                'composite_score_calculation',
                'threshold_based_recommendations',
                'confidence_filtering',
                'rule_validation',
                'recommendation_distribution_analysis'
            ],
            'description': 'Generates investment recommendations based on ML scores and confidence levels'
        }