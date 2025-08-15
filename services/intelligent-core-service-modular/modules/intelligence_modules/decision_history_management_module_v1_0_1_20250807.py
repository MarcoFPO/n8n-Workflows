"""
Decision History Management Module - Single Function Module
Manages decision history, learns from past decisions, and provides decision context
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

try:
    from shared.common_imports import datetime, Dict, Any, structlog
    from shared.single_function_module_base import SingleFunctionModuleBase
except ImportError:
    from datetime import datetime, timedelta
    from typing import Dict, Any, List, Optional
    
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


class DecisionHistoryManagementModule(SingleFunctionModuleBase):
    """Manage decision history and provide context for investment decisions"""
    
    def __init__(self, event_bus):
        super().__init__("decision_history_management", event_bus)
        
        # Decision tracking configuration
        self.decision_config = {
            'max_history_length': 1000,        # Maximum decisions to store
            'performance_tracking_days': 30,    # Days to track decision performance
            'confidence_threshold': 0.6,       # Minimum confidence to consider decision
            'similarity_threshold': 0.8,       # Threshold for similar decisions
            'learning_rate': 0.1               # Rate of learning from outcomes
        }
        
        # Decision outcome scoring
        self.outcome_weights = {
            'price_movement_weight': 0.4,      # Actual price movement vs prediction
            'timing_accuracy_weight': 0.3,     # How quickly the prediction materialized
            'volatility_handling_weight': 0.2, # How well volatility was anticipated
            'risk_management_weight': 0.1      # Risk assessment accuracy
        }
        
        # Decision categories for analysis
        self.decision_categories = {
            'BUY': {'threshold': 0.6, 'direction': 1},
            'STRONG_BUY': {'threshold': 0.8, 'direction': 1},
            'SELL': {'threshold': 0.4, 'direction': -1},
            'STRONG_SELL': {'threshold': 0.2, 'direction': -1},
            'HOLD': {'threshold': 0.5, 'direction': 0}
        }
        
        # In-memory decision storage (in production, this would be a database)
        self.decision_history = []
        self.performance_cache = {}
        self.pattern_cache = {}
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('decision.history.request', self.process_event)
            await self.event_bus.subscribe('decision.store.request', self.process_event)
            await self.event_bus.subscribe('decision.performance.request', self.process_event)
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
                'decision_config': self.decision_config,
                'decision_count': len(self.decision_history),
                'performance_cache_size': len(self.performance_cache),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'decision.store.request':
            decision_data = event.get('decision_data', {})
            
            store_result = await self.store_decision(decision_data)
            
            response_event = {
                'event_type': 'decision.store.response',
                'success': store_result['success'],
                'decision_id': store_result.get('decision_id'),
                'message': store_result.get('message', ''),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
        
        elif event_type == 'decision.history.request':
            symbol = event.get('symbol', None)
            limit = event.get('limit', 10)
            
            history_result = await self.get_decision_history(symbol, limit)
            
            response_event = {
                'event_type': 'decision.history.response',
                'symbol': symbol,
                'decisions': history_result['decisions'],
                'total_count': history_result['total_count'],
                'performance_summary': history_result['performance_summary'],
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
        
        elif event_type == 'decision.performance.request':
            decision_id = event.get('decision_id')
            current_data = event.get('current_data', {})
            
            performance_result = await self.evaluate_decision_performance(decision_id, current_data)
            
            response_event = {
                'event_type': 'decision.performance.response',
                'decision_id': decision_id,
                'performance_score': performance_result['performance_score'],
                'performance_analysis': performance_result['performance_analysis'],
                'outcome_components': performance_result['outcome_components'],
                'lessons_learned': performance_result['lessons_learned'],
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def store_decision(self, decision_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a new decision in the history"""
        try:
            # Generate decision ID
            decision_id = f"{decision_data.get('symbol', 'UNKNOWN')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Prepare decision record
            decision_record = {
                'decision_id': decision_id,
                'timestamp': datetime.now(),
                'symbol': decision_data.get('symbol', 'UNKNOWN'),
                'recommendation': decision_data.get('recommendation', 'HOLD'),
                'confidence': decision_data.get('confidence', 0.5),
                'composite_score': decision_data.get('composite_score', 0.5),
                'indicators': decision_data.get('indicators', {}),
                'ml_scores': decision_data.get('ml_scores', {}),
                'reasoning': decision_data.get('reasoning', []),
                'risk_assessment': decision_data.get('risk_assessment', {}),
                'market_conditions': decision_data.get('market_conditions', {}),
                'decision_context': {
                    'current_price': decision_data.get('indicators', {}).get('current_price', 0.0),
                    'volatility': decision_data.get('indicators', {}).get('volatility', 0.0),
                    'volume_ratio': decision_data.get('indicators', {}).get('volume_ratio', 1.0),
                    'trend_strength': decision_data.get('indicators', {}).get('trend_strength', 0.0)
                },
                'performance_tracking': {
                    'tracking_start': datetime.now(),
                    'initial_price': decision_data.get('indicators', {}).get('current_price', 0.0),
                    'expected_direction': self._get_decision_direction(decision_data.get('recommendation', 'HOLD')),
                    'target_timeframe': decision_data.get('target_timeframe', 30)  # days
                }
            }
            
            # Store decision
            self.decision_history.append(decision_record)
            
            # Maintain history size limit
            if len(self.decision_history) > self.decision_config['max_history_length']:
                self.decision_history = self.decision_history[-self.decision_config['max_history_length']:]
            
            # Analyze similar past decisions for context
            similar_decisions = await self._find_similar_decisions(decision_record)
            
            self.logger.info("Decision stored successfully",
                           decision_id=decision_id,
                           symbol=decision_record['symbol'],
                           recommendation=decision_record['recommendation'],
                           confidence=decision_record['confidence'],
                           similar_count=len(similar_decisions))
            
            return {
                'success': True,
                'decision_id': decision_id,
                'message': f'Decision stored successfully. Found {len(similar_decisions)} similar past decisions.',
                'similar_decisions': similar_decisions[:5]  # Return top 5 similar decisions
            }
            
        except Exception as e:
            self.logger.error("Error storing decision", error=str(e))
            return {
                'success': False,
                'message': f'Failed to store decision: {str(e)}'
            }
    
    async def get_decision_history(self, symbol: str = None, limit: int = 10) -> Dict[str, Any]:
        """Get decision history with optional filtering"""
        try:
            # Filter decisions
            if symbol:
                filtered_decisions = [
                    decision for decision in self.decision_history 
                    if decision['symbol'].upper() == symbol.upper()
                ]
            else:
                filtered_decisions = self.decision_history.copy()
            
            # Sort by timestamp (most recent first)
            filtered_decisions.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Apply limit
            limited_decisions = filtered_decisions[:limit]
            
            # Calculate performance summary
            performance_summary = await self._calculate_performance_summary(filtered_decisions)
            
            # Format decisions for response (remove complex objects)
            formatted_decisions = []
            for decision in limited_decisions:
                formatted_decision = {
                    'decision_id': decision['decision_id'],
                    'timestamp': decision['timestamp'].isoformat(),
                    'symbol': decision['symbol'],
                    'recommendation': decision['recommendation'],
                    'confidence': decision['confidence'],
                    'composite_score': decision['composite_score'],
                    'current_price': decision['decision_context']['current_price'],
                    'reasoning_summary': decision['reasoning'][:3] if decision['reasoning'] else [],  # First 3 reasons
                    'risk_level': decision['risk_assessment'].get('risk_level', 'unknown'),
                    'performance_tracking': decision.get('performance_tracking', {})
                }
                formatted_decisions.append(formatted_decision)
            
            return {
                'decisions': formatted_decisions,
                'total_count': len(filtered_decisions),
                'performance_summary': performance_summary
            }
            
        except Exception as e:
            self.logger.error("Error getting decision history", error=str(e))
            return {
                'decisions': [],
                'total_count': 0,
                'performance_summary': {'error': str(e)}
            }
    
    async def evaluate_decision_performance(self, decision_id: str, current_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate the performance of a specific decision"""
        try:
            # Find the decision
            decision = None
            for d in self.decision_history:
                if d['decision_id'] == decision_id:
                    decision = d
                    break
            
            if not decision:
                return {
                    'performance_score': 0.0,
                    'performance_analysis': ['Decision not found'],
                    'outcome_components': {},
                    'lessons_learned': []
                }
            
            # Calculate time elapsed since decision
            time_elapsed = datetime.now() - decision['timestamp']
            days_elapsed = time_elapsed.days
            
            # Get current market data
            current_price = current_data.get('current_price', 0.0)
            initial_price = decision['performance_tracking']['initial_price']
            expected_direction = decision['performance_tracking']['expected_direction']
            
            if initial_price == 0 or current_price == 0:
                return {
                    'performance_score': 0.0,
                    'performance_analysis': ['Insufficient price data for evaluation'],
                    'outcome_components': {},
                    'lessons_learned': []
                }
            
            # Calculate performance components
            outcome_components = {}
            
            # 1. Price Movement Accuracy
            actual_return = (current_price - initial_price) / initial_price
            predicted_direction_correct = (
                (expected_direction > 0 and actual_return > 0) or
                (expected_direction < 0 and actual_return < 0) or
                (expected_direction == 0 and abs(actual_return) < 0.02)  # 2% tolerance for HOLD
            )
            
            direction_accuracy = 1.0 if predicted_direction_correct else 0.0
            magnitude_accuracy = max(0.0, 1.0 - abs(abs(actual_return) - abs(expected_direction * 0.1)) / 0.1)  # Expected 10% move
            
            outcome_components['price_movement'] = {
                'score': (direction_accuracy * 0.7 + magnitude_accuracy * 0.3),
                'actual_return': actual_return,
                'direction_correct': predicted_direction_correct,
                'expected_direction': expected_direction
            }
            
            # 2. Timing Accuracy
            target_timeframe = decision['performance_tracking']['target_timeframe']
            timing_score = 1.0
            
            if predicted_direction_correct and abs(actual_return) > 0.05:  # Significant move
                if days_elapsed <= target_timeframe:
                    timing_score = 1.0 - (days_elapsed / target_timeframe) * 0.3  # Bonus for early achievement
                else:
                    timing_score = max(0.3, 1.0 - ((days_elapsed - target_timeframe) / target_timeframe) * 0.7)
            elif not predicted_direction_correct:
                timing_score = max(0.0, 1.0 - (days_elapsed / target_timeframe))
            
            outcome_components['timing_accuracy'] = {
                'score': timing_score,
                'days_elapsed': days_elapsed,
                'target_timeframe': target_timeframe
            }
            
            # 3. Volatility Handling
            expected_volatility = decision['decision_context']['volatility']
            current_volatility = current_data.get('volatility', expected_volatility)
            
            volatility_prediction_accuracy = 1.0 - min(1.0, abs(current_volatility - expected_volatility) / max(0.1, expected_volatility))
            
            outcome_components['volatility_handling'] = {
                'score': volatility_prediction_accuracy,
                'expected_volatility': expected_volatility,
                'actual_volatility': current_volatility
            }
            
            # 4. Risk Management
            risk_level = decision['risk_assessment'].get('risk_level', 'moderate')
            max_drawdown = current_data.get('max_drawdown', abs(min(0, actual_return)))
            
            risk_score = 1.0
            if risk_level == 'low' and max_drawdown > 0.05:
                risk_score = 0.5
            elif risk_level == 'moderate' and max_drawdown > 0.15:
                risk_score = 0.7
            elif risk_level == 'high' and max_drawdown > 0.25:
                risk_score = 0.8
            
            outcome_components['risk_management'] = {
                'score': risk_score,
                'expected_risk_level': risk_level,
                'max_drawdown': max_drawdown
            }
            
            # Calculate composite performance score
            performance_score = 0.0
            for component_name, weight in self.outcome_weights.items():
                component_key = component_name.replace('_weight', '')
                if component_key in outcome_components:
                    performance_score += outcome_components[component_key]['score'] * weight
            
            # Generate performance analysis
            performance_analysis = []
            
            if performance_score >= 0.8:
                performance_analysis.append("Excellent decision performance")
            elif performance_score >= 0.6:
                performance_analysis.append("Good decision performance")
            elif performance_score >= 0.4:
                performance_analysis.append("Moderate decision performance")
            else:
                performance_analysis.append("Poor decision performance")
            
            if predicted_direction_correct:
                performance_analysis.append(f"Direction prediction correct: {actual_return:.1%} return")
            else:
                performance_analysis.append(f"Direction prediction incorrect: {actual_return:.1%} return")
            
            if timing_score > 0.8:
                performance_analysis.append("Excellent timing accuracy")
            elif timing_score < 0.4:
                performance_analysis.append("Poor timing - prediction took longer than expected")
            
            # Generate lessons learned
            lessons_learned = await self._extract_lessons_learned(decision, outcome_components, performance_score)
            
            # Update performance cache
            self.performance_cache[decision_id] = {
                'performance_score': performance_score,
                'outcome_components': outcome_components,
                'last_updated': datetime.now(),
                'days_tracked': days_elapsed
            }
            
            self.logger.debug("Decision performance evaluated",
                            decision_id=decision_id,
                            performance_score=performance_score,
                            days_elapsed=days_elapsed)
            
            return {
                'performance_score': float(performance_score),
                'performance_analysis': performance_analysis,
                'outcome_components': outcome_components,
                'lessons_learned': lessons_learned
            }
            
        except Exception as e:
            self.logger.error("Error evaluating decision performance", error=str(e))
            return {
                'performance_score': 0.0,
                'performance_analysis': [f"Performance evaluation error: {str(e)}"],
                'outcome_components': {},
                'lessons_learned': []
            }
    
    async def _find_similar_decisions(self, decision: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """Find similar past decisions for context"""
        try:
            similar_decisions = []
            current_symbol = decision['symbol']
            current_indicators = decision['indicators']
            
            for past_decision in self.decision_history:
                if past_decision['decision_id'] == decision.get('decision_id'):
                    continue  # Skip the same decision
                
                similarity_score = 0.0
                components = 0
                
                # Symbol similarity (exact match gets high score)
                if past_decision['symbol'] == current_symbol:
                    similarity_score += 0.3
                components += 1
                
                # Recommendation similarity
                if past_decision['recommendation'] == decision['recommendation']:
                    similarity_score += 0.2
                components += 1
                
                # Confidence similarity
                conf_diff = abs(past_decision['confidence'] - decision['confidence'])
                similarity_score += (1.0 - conf_diff) * 0.1
                components += 1
                
                # Indicator similarity (check key indicators)
                indicator_similarity = 0.0
                indicator_count = 0
                
                for indicator in ['rsi', 'macd', 'trend_strength', 'volatility']:
                    if indicator in current_indicators and indicator in past_decision['indicators']:
                        current_val = current_indicators[indicator]
                        past_val = past_decision['indicators'][indicator]
                        
                        if current_val != 0 and past_val != 0:
                            diff = abs(current_val - past_val) / max(abs(current_val), abs(past_val))
                            indicator_similarity += max(0.0, 1.0 - diff)
                            indicator_count += 1
                
                if indicator_count > 0:
                    similarity_score += (indicator_similarity / indicator_count) * 0.4
                
                # Normalize similarity score
                final_similarity = similarity_score / max(1, components) if components > 0 else 0.0
                
                # Only include if above threshold
                if final_similarity >= self.decision_config['similarity_threshold']:
                    # Get performance if available
                    performance_data = self.performance_cache.get(past_decision['decision_id'], {})
                    
                    similar_decisions.append({
                        'decision_id': past_decision['decision_id'],
                        'timestamp': past_decision['timestamp'].isoformat(),
                        'symbol': past_decision['symbol'],
                        'recommendation': past_decision['recommendation'],
                        'confidence': past_decision['confidence'],
                        'similarity_score': final_similarity,
                        'performance_score': performance_data.get('performance_score', None),
                        'outcome': 'positive' if performance_data.get('performance_score', 0) > 0.6 else 'negative' if performance_data.get('performance_score', 0) < 0.4 else 'neutral'
                    })
            
            # Sort by similarity score (highest first)
            similar_decisions.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return similar_decisions[:limit]
            
        except Exception as e:
            self.logger.error("Error finding similar decisions", error=str(e))
            return []
    
    async def _calculate_performance_summary(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance summary for a set of decisions"""
        try:
            if not decisions:
                return {'total_decisions': 0}
            
            # Performance statistics
            performance_scores = []
            recommendation_performance = {}
            
            for decision in decisions:
                decision_id = decision['decision_id']
                perf_data = self.performance_cache.get(decision_id)
                
                if perf_data:
                    performance_scores.append(perf_data['performance_score'])
                    
                    recommendation = decision['recommendation']
                    if recommendation not in recommendation_performance:
                        recommendation_performance[recommendation] = {'scores': [], 'count': 0}
                    
                    recommendation_performance[recommendation]['scores'].append(perf_data['performance_score'])
                    recommendation_performance[recommendation]['count'] += 1
            
            summary = {
                'total_decisions': len(decisions),
                'tracked_decisions': len(performance_scores)
            }
            
            if performance_scores:
                summary.update({
                    'average_performance': sum(performance_scores) / len(performance_scores),
                    'best_performance': max(performance_scores),
                    'worst_performance': min(performance_scores),
                    'success_rate': sum(1 for score in performance_scores if score > 0.6) / len(performance_scores)
                })
                
                # Performance by recommendation type
                for rec_type, data in recommendation_performance.items():
                    if data['scores']:
                        summary[f'{rec_type.lower()}_performance'] = {
                            'average': sum(data['scores']) / len(data['scores']),
                            'count': data['count'],
                            'success_rate': sum(1 for score in data['scores'] if score > 0.6) / len(data['scores'])
                        }
            
            return summary
            
        except Exception as e:
            self.logger.error("Error calculating performance summary", error=str(e))
            return {'error': str(e)}
    
    async def _extract_lessons_learned(self, decision: Dict[str, Any], outcome_components: Dict[str, Any], performance_score: float) -> List[str]:
        """Extract lessons learned from decision outcomes"""
        try:
            lessons = []
            
            # Performance-based lessons
            if performance_score >= 0.8:
                lessons.append("Decision methodology was highly effective - continue using similar approach")
            elif performance_score <= 0.3:
                lessons.append("Decision methodology needs improvement - analyze key factors that led to poor outcome")
            
            # Direction accuracy lessons
            price_component = outcome_components.get('price_movement', {})
            if not price_component.get('direction_correct', False):
                lessons.append("Direction prediction failed - review technical analysis and market conditions")
                
                if decision['confidence'] > 0.8:
                    lessons.append("High confidence decision was wrong - recalibrate confidence calculation")
            
            # Timing lessons
            timing_component = outcome_components.get('timing_accuracy', {})
            if timing_component.get('score', 0) < 0.4:
                lessons.append("Timing was poor - consider extending target timeframes or improving entry/exit signals")
            
            # Volatility lessons
            vol_component = outcome_components.get('volatility_handling', {})
            if vol_component.get('score', 0) < 0.5:
                expected_vol = vol_component.get('expected_volatility', 0)
                actual_vol = vol_component.get('actual_volatility', 0)
                
                if actual_vol > expected_vol * 1.5:
                    lessons.append("Volatility was underestimated - improve volatility prediction or risk management")
                else:
                    lessons.append("Volatility prediction needs refinement")
            
            # Risk management lessons
            risk_component = outcome_components.get('risk_management', {})
            if risk_component.get('score', 0) < 0.6:
                max_drawdown = risk_component.get('max_drawdown', 0)
                if max_drawdown > 0.15:
                    lessons.append("Risk management failed - consider tighter stop losses or position sizing")
            
            # Confidence-specific lessons
            confidence = decision.get('confidence', 0.5)
            if confidence > 0.8 and performance_score < 0.4:
                lessons.append("Overconfidence detected - review confidence calculation methodology")
            elif confidence < 0.4 and performance_score > 0.7:
                lessons.append("Underconfidence detected - decision was better than expected")
            
            # Market condition lessons
            market_conditions = decision.get('market_conditions', {})
            volatility_regime = market_conditions.get('volatility_regime', 'normal')
            
            if volatility_regime == 'high' and performance_score < 0.5:
                lessons.append("High volatility regime negatively impacted performance - adjust strategy for volatile markets")
            
            return lessons[:5]  # Return top 5 lessons
            
        except Exception as e:
            self.logger.error("Error extracting lessons learned", error=str(e))
            return ["Error extracting lessons from decision outcome"]
    
    def _get_decision_direction(self, recommendation: str) -> int:
        """Get expected direction for a recommendation"""
        category = self.decision_categories.get(recommendation.upper())
        return category['direction'] if category else 0
    
    def get_decision_patterns(self, symbol: str = None) -> Dict[str, Any]:
        """Analyze decision patterns and trends"""
        try:
            # Filter decisions
            if symbol:
                decisions = [d for d in self.decision_history if d['symbol'].upper() == symbol.upper()]
            else:
                decisions = self.decision_history
            
            if not decisions:
                return {'error': 'No decisions found'}
            
            # Analyze patterns
            patterns = {
                'recommendation_distribution': {},
                'confidence_trends': [],
                'performance_by_confidence': {},
                'timing_patterns': {},
                'market_condition_impact': {}
            }
            
            # Recommendation distribution
            for decision in decisions:
                rec = decision['recommendation']
                patterns['recommendation_distribution'][rec] = patterns['recommendation_distribution'].get(rec, 0) + 1
            
            # Confidence trends (last 30 decisions)
            recent_decisions = decisions[-30:] if len(decisions) > 30 else decisions
            patterns['confidence_trends'] = [
                {
                    'timestamp': d['timestamp'].isoformat(),
                    'confidence': d['confidence'],
                    'performance': self.performance_cache.get(d['decision_id'], {}).get('performance_score', None)
                }
                for d in recent_decisions
            ]
            
            # Performance by confidence buckets
            for decision in decisions:
                perf_data = self.performance_cache.get(decision['decision_id'])
                if perf_data:
                    confidence = decision['confidence']
                    bucket = 'low' if confidence < 0.4 else 'medium' if confidence < 0.7 else 'high'
                    
                    if bucket not in patterns['performance_by_confidence']:
                        patterns['performance_by_confidence'][bucket] = []
                    
                    patterns['performance_by_confidence'][bucket].append(perf_data['performance_score'])
            
            # Calculate averages for confidence buckets
            for bucket, scores in patterns['performance_by_confidence'].items():
                if scores:
                    patterns['performance_by_confidence'][bucket] = {
                        'average_performance': sum(scores) / len(scores),
                        'count': len(scores),
                        'success_rate': sum(1 for s in scores if s > 0.6) / len(scores)
                    }
            
            return patterns
            
        except Exception as e:
            self.logger.error("Error analyzing decision patterns", error=str(e))
            return {'error': str(e)}
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'decision_history_management',
            'decision_config': self.decision_config.copy(),
            'outcome_weights': self.outcome_weights.copy(),
            'decision_categories': self.decision_categories.copy(),
            'current_history_size': len(self.decision_history),
            'performance_cache_size': len(self.performance_cache),
            'features': [
                'decision_storage_and_retrieval',
                'performance_tracking_and_evaluation',
                'similarity_based_decision_matching',
                'lessons_learned_extraction',
                'pattern_analysis_and_trends',
                'confidence_calibration_insights',
                'market_condition_impact_analysis',
                'recommendation_performance_tracking',
                'timing_accuracy_assessment',
                'risk_management_effectiveness'
            ],
            'supported_evaluations': [
                'price_movement_accuracy',
                'timing_accuracy',
                'volatility_handling',
                'risk_management_effectiveness'
            ],
            'description': 'Manages comprehensive decision history, tracks performance, and provides learning insights for continuous improvement'
        }