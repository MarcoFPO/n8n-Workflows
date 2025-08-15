"""
Rules Management Module - Single Function Module
Manages trading rules, validates decisions against rules, and provides rule-based constraints
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


class RulesManagementModule(SingleFunctionModuleBase):
    """Manage trading rules and validate decisions against defined constraints"""
    
    def __init__(self, event_bus):
        super().__init__("rules_management", event_bus)
        
        # Rule categories
        self.rule_categories = {
            'risk_management': 'Risk-based constraints',
            'market_conditions': 'Market condition filters',
            'technical_analysis': 'Technical indicator rules',
            'position_sizing': 'Position and portfolio constraints',
            'timing': 'Timing and frequency rules',
            'confidence': 'Confidence-based filters',
            'volatility': 'Volatility-based rules',
            'correlation': 'Correlation and diversification rules'
        }
        
        # Default trading rules
        self.default_rules = {
            # Risk Management Rules
            'max_position_risk': {
                'category': 'risk_management',
                'type': 'constraint',
                'condition': 'risk_score <= 0.8',
                'description': 'Maximum acceptable risk score for any position',
                'enabled': True,
                'priority': 1,
                'parameters': {'max_risk_score': 0.8}
            },
            'volatility_limit': {
                'category': 'risk_management',
                'type': 'constraint',
                'condition': 'volatility <= 0.5',
                'description': 'Maximum volatility threshold for new positions',
                'enabled': True,
                'priority': 2,
                'parameters': {'max_volatility': 0.5}
            },
            
            # Market Conditions Rules
            'high_vix_restriction': {
                'category': 'market_conditions',
                'type': 'filter',
                'condition': 'vix < 30 OR recommendation != "BUY"',
                'description': 'Restrict BUY recommendations when VIX is high',
                'enabled': True,
                'priority': 3,
                'parameters': {'vix_threshold': 30}
            },
            'trend_alignment': {
                'category': 'market_conditions',
                'type': 'enhancement',
                'condition': 'trend_strength > 0.4',
                'description': 'Require minimum trend strength for directional trades',
                'enabled': True,
                'priority': 4,
                'parameters': {'min_trend_strength': 0.4}
            },
            
            # Technical Analysis Rules
            'rsi_overbought': {
                'category': 'technical_analysis',
                'type': 'filter',
                'condition': 'rsi < 80 OR recommendation != "BUY"',
                'description': 'Avoid BUY recommendations when RSI is extremely overbought',
                'enabled': True,
                'priority': 5,
                'parameters': {'rsi_threshold': 80}
            },
            'rsi_oversold': {
                'category': 'technical_analysis',
                'type': 'filter',
                'condition': 'rsi > 20 OR recommendation != "SELL"',
                'description': 'Avoid SELL recommendations when RSI is extremely oversold',
                'enabled': True,
                'priority': 6,
                'parameters': {'rsi_threshold': 20}
            },
            
            # Confidence Rules
            'min_confidence': {
                'category': 'confidence',
                'type': 'constraint',
                'condition': 'confidence >= 0.4',
                'description': 'Minimum confidence required for any recommendation',
                'enabled': True,
                'priority': 7,
                'parameters': {'min_confidence': 0.4}
            },
            'high_confidence_boost': {
                'category': 'confidence',
                'type': 'enhancement',
                'condition': 'confidence >= 0.8',
                'description': 'Boost recommendations with very high confidence',
                'enabled': True,
                'priority': 8,
                'parameters': {'high_confidence_threshold': 0.8}
            },
            
            # Position Sizing Rules
            'max_single_position': {
                'category': 'position_sizing',
                'type': 'constraint',
                'condition': 'position_size <= 0.2',
                'description': 'Maximum 20% portfolio allocation to single position',
                'enabled': True,
                'priority': 9,
                'parameters': {'max_position_percentage': 0.2}
            },
            
            # Timing Rules
            'trading_hours': {
                'category': 'timing',
                'type': 'filter',
                'condition': 'market_hours == True',
                'description': 'Only generate recommendations during market hours',
                'enabled': False,  # Disabled by default for 24/7 analysis
                'priority': 10,
                'parameters': {'enforce_market_hours': False}
            }
        }
        
        # Active rules (copy of defaults, can be modified)
        self.active_rules = self.default_rules.copy()
        
        # Rule execution statistics
        self.rule_stats = {}
        
        # Custom rules (user-defined)
        self.custom_rules = {}
        
    async def _setup_event_subscriptions(self):
        """Setup event subscriptions"""
        try:
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('rules.validate.request', self.process_event)
            await self.event_bus.subscribe('rules.manage.request', self.process_event)
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
                'active_rules_count': len(self.active_rules),
                'enabled_rules_count': sum(1 for rule in self.active_rules.values() if rule['enabled']),
                'custom_rules_count': len(self.custom_rules),
                'rule_categories': list(self.rule_categories.keys()),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(health_response)
        
        elif event_type == 'rules.validate.request':
            decision_data = event.get('decision_data', {})
            market_data = event.get('market_data', {})
            
            validation_result = await self.validate_decision_rules(decision_data, market_data)
            
            response_event = {
                'event_type': 'rules.validate.response',
                'validation_passed': validation_result['validation_passed'],
                'violations': validation_result['violations'],
                'warnings': validation_result['warnings'],
                'rule_adjustments': validation_result['rule_adjustments'],
                'modified_decision': validation_result.get('modified_decision'),
                'rules_applied': validation_result['rules_applied'],
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
        
        elif event_type == 'rules.manage.request':
            action = event.get('action', 'list')  # list, add, remove, enable, disable, update
            rule_id = event.get('rule_id')
            rule_data = event.get('rule_data', {})
            
            management_result = await self.manage_rules(action, rule_id, rule_data)
            
            response_event = {
                'event_type': 'rules.manage.response',
                'action': action,
                'success': management_result['success'],
                'message': management_result['message'],
                'rule_id': rule_id,
                'active_rules': management_result.get('active_rules', {}),
                'timestamp': datetime.now().isoformat()
            }
            await self.event_bus.publish(response_event)
    
    async def validate_decision_rules(self, decision_data: Dict[str, Any], market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Validate a decision against all active rules"""
        try:
            if market_data is None:
                market_data = {}
            
            validation_result = {
                'validation_passed': True,
                'violations': [],
                'warnings': [],
                'rule_adjustments': [],
                'rules_applied': [],
                'modified_decision': None
            }
            
            # Get decision parameters
            recommendation = decision_data.get('recommendation', 'HOLD')
            confidence = decision_data.get('confidence', 0.5)
            risk_score = decision_data.get('risk_assessment', {}).get('composite_risk_score', 0.5)
            indicators = decision_data.get('indicators', {})
            symbol = decision_data.get('symbol', 'UNKNOWN')
            
            # Prepare context for rule evaluation
            rule_context = {
                'recommendation': recommendation,
                'confidence': confidence,
                'risk_score': risk_score,
                'volatility': indicators.get('volatility', 0.2),
                'rsi': indicators.get('rsi', 50.0),
                'trend_strength': indicators.get('trend_strength', 0.0),
                'vix': market_data.get('vix', 20.0),
                'market_hours': market_data.get('market_hours', True),
                'position_size': decision_data.get('position_size', 0.1),
                'symbol': symbol,
                'timestamp': datetime.now()
            }
            
            # Sort rules by priority
            sorted_rules = sorted(
                [(rule_id, rule) for rule_id, rule in self.active_rules.items() if rule['enabled']],
                key=lambda x: x[1]['priority']
            )
            
            modified_decision = decision_data.copy()
            
            # Apply each rule
            for rule_id, rule in sorted_rules:
                try:
                    rule_result = await self._evaluate_rule(rule_id, rule, rule_context, modified_decision)
                    
                    # Track rule application
                    validation_result['rules_applied'].append({
                        'rule_id': rule_id,
                        'result': rule_result['result'],
                        'category': rule['category']
                    })
                    
                    # Update statistics
                    if rule_id not in self.rule_stats:
                        self.rule_stats[rule_id] = {
                            'applications': 0,
                            'violations': 0,
                            'modifications': 0,
                            'last_applied': None
                        }
                    
                    self.rule_stats[rule_id]['applications'] += 1
                    self.rule_stats[rule_id]['last_applied'] = datetime.now()
                    
                    if rule_result['result'] == 'violation':
                        validation_result['violations'].append({
                            'rule_id': rule_id,
                            'rule_description': rule['description'],
                            'violation_details': rule_result['details'],
                            'category': rule['category'],
                            'priority': rule['priority']
                        })
                        self.rule_stats[rule_id]['violations'] += 1
                        
                        # Hard constraints fail validation
                        if rule['type'] == 'constraint':
                            validation_result['validation_passed'] = False
                    
                    elif rule_result['result'] == 'warning':
                        validation_result['warnings'].append({
                            'rule_id': rule_id,
                            'rule_description': rule['description'],
                            'warning_details': rule_result['details'],
                            'category': rule['category']
                        })
                    
                    elif rule_result['result'] == 'modification':
                        validation_result['rule_adjustments'].append({
                            'rule_id': rule_id,
                            'rule_description': rule['description'],
                            'modification_details': rule_result['details'],
                            'category': rule['category']
                        })
                        self.rule_stats[rule_id]['modifications'] += 1
                        
                        # Apply modification to decision
                        if 'modified_values' in rule_result:
                            for key, value in rule_result['modified_values'].items():
                                self._apply_modification(modified_decision, key, value)
                
                except Exception as rule_error:
                    self.logger.error("Error evaluating rule", 
                                    rule_id=rule_id, 
                                    error=str(rule_error))
                    validation_result['warnings'].append({
                        'rule_id': rule_id,
                        'rule_description': rule['description'],
                        'warning_details': f"Rule evaluation error: {str(rule_error)}",
                        'category': rule.get('category', 'unknown')
                    })
            
            # Set modified decision if any changes were made
            if modified_decision != decision_data:
                validation_result['modified_decision'] = modified_decision
            
            self.logger.debug("Rule validation completed",
                            symbol=symbol,
                            validation_passed=validation_result['validation_passed'],
                            violations_count=len(validation_result['violations']),
                            warnings_count=len(validation_result['warnings']),
                            adjustments_count=len(validation_result['rule_adjustments']))
            
            return validation_result
            
        except Exception as e:
            self.logger.error("Error validating decision rules", error=str(e))
            return {
                'validation_passed': False,
                'violations': [{'error': f"Rule validation failed: {str(e)}"}],
                'warnings': [],
                'rule_adjustments': [],
                'rules_applied': []
            }
    
    async def _evaluate_rule(self, rule_id: str, rule: Dict[str, Any], context: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a specific rule against the decision context"""
        try:
            rule_type = rule['type']
            condition = rule['condition']
            parameters = rule.get('parameters', {})
            
            # Evaluate based on rule type
            if rule_type == 'constraint':
                return await self._evaluate_constraint_rule(rule_id, rule, context, parameters)
            elif rule_type == 'filter':
                return await self._evaluate_filter_rule(rule_id, rule, context, parameters)
            elif rule_type == 'enhancement':
                return await self._evaluate_enhancement_rule(rule_id, rule, context, parameters)
            else:
                return {'result': 'unknown', 'details': f"Unknown rule type: {rule_type}"}
                
        except Exception as e:
            return {'result': 'error', 'details': f"Rule evaluation error: {str(e)}"}
    
    async def _evaluate_constraint_rule(self, rule_id: str, rule: Dict[str, Any], context: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate constraint rules (hard limits)"""
        # Max position risk
        if rule_id == 'max_position_risk':
            risk_score = context.get('risk_score', 0.5)
            max_risk = parameters.get('max_risk_score', 0.8)
            
            if risk_score > max_risk:
                return {
                    'result': 'violation',
                    'details': f"Risk score ({risk_score:.2f}) exceeds maximum ({max_risk:.2f})"
                }
        
        # Volatility limit
        elif rule_id == 'volatility_limit':
            volatility = context.get('volatility', 0.2)
            max_volatility = parameters.get('max_volatility', 0.5)
            
            if volatility > max_volatility:
                return {
                    'result': 'violation',
                    'details': f"Volatility ({volatility:.1%}) exceeds limit ({max_volatility:.1%})"
                }
        
        # Minimum confidence
        elif rule_id == 'min_confidence':
            confidence = context.get('confidence', 0.5)
            min_confidence = parameters.get('min_confidence', 0.4)
            
            if confidence < min_confidence:
                return {
                    'result': 'violation',
                    'details': f"Confidence ({confidence:.2f}) below minimum ({min_confidence:.2f})"
                }
        
        # Position sizing
        elif rule_id == 'max_single_position':
            position_size = context.get('position_size', 0.1)
            max_position = parameters.get('max_position_percentage', 0.2)
            
            if position_size > max_position:
                return {
                    'result': 'violation',
                    'details': f"Position size ({position_size:.1%}) exceeds maximum ({max_position:.1%})"
                }
        
        return {'result': 'pass', 'details': 'Constraint satisfied'}
    
    async def _evaluate_filter_rule(self, rule_id: str, rule: Dict[str, Any], context: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate filter rules (conditional restrictions)"""
        recommendation = context.get('recommendation', 'HOLD')
        
        # High VIX restriction
        if rule_id == 'high_vix_restriction':
            vix = context.get('vix', 20.0)
            vix_threshold = parameters.get('vix_threshold', 30)
            
            if vix >= vix_threshold and recommendation == 'BUY':
                return {
                    'result': 'violation',
                    'details': f"BUY recommendation blocked: VIX ({vix:.1f}) above threshold ({vix_threshold})"
                }
        
        # RSI overbought
        elif rule_id == 'rsi_overbought':
            rsi = context.get('rsi', 50.0)
            rsi_threshold = parameters.get('rsi_threshold', 80)
            
            if rsi >= rsi_threshold and recommendation == 'BUY':
                return {
                    'result': 'violation',
                    'details': f"BUY recommendation blocked: RSI overbought ({rsi:.1f} >= {rsi_threshold})"
                }
        
        # RSI oversold
        elif rule_id == 'rsi_oversold':
            rsi = context.get('rsi', 50.0)
            rsi_threshold = parameters.get('rsi_threshold', 20)
            
            if rsi <= rsi_threshold and recommendation == 'SELL':
                return {
                    'result': 'violation',
                    'details': f"SELL recommendation blocked: RSI oversold ({rsi:.1f} <= {rsi_threshold})"
                }
        
        # Trading hours
        elif rule_id == 'trading_hours':
            market_hours = context.get('market_hours', True)
            enforce_hours = parameters.get('enforce_market_hours', False)
            
            if enforce_hours and not market_hours:
                return {
                    'result': 'violation',
                    'details': "Recommendation blocked: outside trading hours"
                }
        
        return {'result': 'pass', 'details': 'Filter passed'}
    
    async def _evaluate_enhancement_rule(self, rule_id: str, rule: Dict[str, Any], context: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate enhancement rules (modifications and improvements)"""
        
        # Trend alignment requirement
        if rule_id == 'trend_alignment':
            trend_strength = context.get('trend_strength', 0.0)
            min_trend = parameters.get('min_trend_strength', 0.4)
            recommendation = context.get('recommendation', 'HOLD')
            
            if abs(trend_strength) < min_trend and recommendation != 'HOLD':
                return {
                    'result': 'warning',
                    'details': f"Weak trend strength ({trend_strength:.2f}) for directional recommendation"
                }
        
        # High confidence boost
        elif rule_id == 'high_confidence_boost':
            confidence = context.get('confidence', 0.5)
            high_confidence_threshold = parameters.get('high_confidence_threshold', 0.8)
            
            if confidence >= high_confidence_threshold:
                # Suggest position size increase for high confidence decisions
                boost_factor = min(1.5, 1.0 + (confidence - high_confidence_threshold) * 2)
                return {
                    'result': 'modification',
                    'details': f"High confidence detected - suggest {boost_factor:.1f}x position sizing",
                    'modified_values': {
                        'confidence_boost_factor': boost_factor,
                        'high_confidence_flag': True
                    }
                }
        
        return {'result': 'pass', 'details': 'Enhancement rule satisfied'}
    
    def _apply_modification(self, decision: Dict[str, Any], key: str, value: Any):
        """Apply a rule modification to the decision"""
        try:
            # Handle nested keys (e.g., 'metadata.confidence_boost')
            if '.' in key:
                keys = key.split('.')
                current = decision
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                current[keys[-1]] = value
            else:
                decision[key] = value
        except Exception as e:
            self.logger.error("Error applying rule modification", key=key, value=value, error=str(e))
    
    async def manage_rules(self, action: str, rule_id: str = None, rule_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Manage rules (add, remove, enable, disable, etc.)"""
        try:
            if action == 'list':
                return {
                    'success': True,
                    'message': 'Rules listed successfully',
                    'active_rules': {
                        rule_id: {
                            'description': rule['description'],
                            'category': rule['category'],
                            'type': rule['type'],
                            'enabled': rule['enabled'],
                            'priority': rule['priority']
                        }
                        for rule_id, rule in self.active_rules.items()
                    }
                }
            
            elif action == 'enable':
                if rule_id and rule_id in self.active_rules:
                    self.active_rules[rule_id]['enabled'] = True
                    return {'success': True, 'message': f'Rule {rule_id} enabled'}
                else:
                    return {'success': False, 'message': f'Rule {rule_id} not found'}
            
            elif action == 'disable':
                if rule_id and rule_id in self.active_rules:
                    self.active_rules[rule_id]['enabled'] = False
                    return {'success': True, 'message': f'Rule {rule_id} disabled'}
                else:
                    return {'success': False, 'message': f'Rule {rule_id} not found'}
            
            elif action == 'add':
                if not rule_id or not rule_data:
                    return {'success': False, 'message': 'Rule ID and rule data required for add operation'}
                
                # Validate required fields
                required_fields = ['category', 'type', 'condition', 'description']
                for field in required_fields:
                    if field not in rule_data:
                        return {'success': False, 'message': f'Missing required field: {field}'}
                
                # Add rule with defaults
                self.custom_rules[rule_id] = {
                    'category': rule_data['category'],
                    'type': rule_data['type'],
                    'condition': rule_data['condition'],
                    'description': rule_data['description'],
                    'enabled': rule_data.get('enabled', True),
                    'priority': rule_data.get('priority', 100),
                    'parameters': rule_data.get('parameters', {})
                }
                
                # Also add to active rules
                self.active_rules[rule_id] = self.custom_rules[rule_id]
                
                return {'success': True, 'message': f'Custom rule {rule_id} added successfully'}
            
            elif action == 'remove':
                if rule_id:
                    removed = False
                    if rule_id in self.custom_rules:
                        del self.custom_rules[rule_id]
                        removed = True
                    if rule_id in self.active_rules:
                        # Only remove if it's a custom rule, not a default rule
                        if rule_id not in self.default_rules:
                            del self.active_rules[rule_id]
                            removed = True
                        else:
                            # Just disable default rules
                            self.active_rules[rule_id]['enabled'] = False
                            removed = True
                    
                    if removed:
                        return {'success': True, 'message': f'Rule {rule_id} removed/disabled'}
                    else:
                        return {'success': False, 'message': f'Rule {rule_id} not found'}
                else:
                    return {'success': False, 'message': 'Rule ID required for remove operation'}
            
            elif action == 'update':
                if rule_id and rule_id in self.active_rules and rule_data:
                    # Update rule parameters
                    for key, value in rule_data.items():
                        if key in ['category', 'type', 'condition', 'description', 'enabled', 'priority', 'parameters']:
                            self.active_rules[rule_id][key] = value
                    
                    return {'success': True, 'message': f'Rule {rule_id} updated successfully'}
                else:
                    return {'success': False, 'message': 'Rule ID and update data required'}
            
            elif action == 'reset':
                # Reset to default rules
                self.active_rules = self.default_rules.copy()
                self.custom_rules = {}
                return {'success': True, 'message': 'Rules reset to defaults'}
            
            else:
                return {'success': False, 'message': f'Unknown action: {action}'}
                
        except Exception as e:
            self.logger.error("Error managing rules", action=action, rule_id=rule_id, error=str(e))
            return {'success': False, 'message': f'Rule management error: {str(e)}'}
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get rule application statistics"""
        try:
            stats_summary = {
                'total_rules': len(self.active_rules),
                'enabled_rules': sum(1 for rule in self.active_rules.values() if rule['enabled']),
                'custom_rules': len(self.custom_rules),
                'rule_applications': sum(stat.get('applications', 0) for stat in self.rule_stats.values()),
                'total_violations': sum(stat.get('violations', 0) for stat in self.rule_stats.values()),
                'total_modifications': sum(stat.get('modifications', 0) for stat in self.rule_stats.values()),
                'category_breakdown': {},
                'most_violated_rules': [],
                'rule_details': self.rule_stats.copy()
            }
            
            # Category breakdown
            for rule_id, rule in self.active_rules.items():
                category = rule['category']
                if category not in stats_summary['category_breakdown']:
                    stats_summary['category_breakdown'][category] = {
                        'total': 0,
                        'enabled': 0,
                        'applications': 0,
                        'violations': 0
                    }
                
                stats_summary['category_breakdown'][category]['total'] += 1
                if rule['enabled']:
                    stats_summary['category_breakdown'][category]['enabled'] += 1
                
                if rule_id in self.rule_stats:
                    stats_summary['category_breakdown'][category]['applications'] += self.rule_stats[rule_id].get('applications', 0)
                    stats_summary['category_breakdown'][category]['violations'] += self.rule_stats[rule_id].get('violations', 0)
            
            # Most violated rules
            violated_rules = [
                (rule_id, stat.get('violations', 0), stat.get('applications', 0))
                for rule_id, stat in self.rule_stats.items()
                if stat.get('violations', 0) > 0
            ]
            
            violated_rules.sort(key=lambda x: x[1], reverse=True)  # Sort by violation count
            
            for rule_id, violations, applications in violated_rules[:5]:
                rule_info = self.active_rules.get(rule_id, {})
                stats_summary['most_violated_rules'].append({
                    'rule_id': rule_id,
                    'violations': violations,
                    'applications': applications,
                    'violation_rate': violations / max(1, applications),
                    'description': rule_info.get('description', 'Unknown rule'),
                    'category': rule_info.get('category', 'unknown')
                })
            
            return stats_summary
            
        except Exception as e:
            self.logger.error("Error generating rule statistics", error=str(e))
            return {'error': str(e)}
    
    def export_rules_config(self) -> Dict[str, Any]:
        """Export current rules configuration"""
        return {
            'active_rules': self.active_rules.copy(),
            'custom_rules': self.custom_rules.copy(),
            'rule_categories': self.rule_categories.copy(),
            'export_timestamp': datetime.now().isoformat(),
            'rule_stats': self.rule_stats.copy()
        }
    
    def import_rules_config(self, config: Dict[str, Any]) -> bool:
        """Import rules configuration"""
        try:
            if 'active_rules' in config:
                self.active_rules = config['active_rules']
            
            if 'custom_rules' in config:
                self.custom_rules = config['custom_rules']
            
            if 'rule_categories' in config:
                self.rule_categories.update(config['rule_categories'])
            
            self.logger.info("Rules configuration imported successfully",
                           active_rules=len(self.active_rules),
                           custom_rules=len(self.custom_rules))
            
            return True
            
        except Exception as e:
            self.logger.error("Error importing rules configuration", error=str(e))
            return False
    
    def get_module_info(self) -> Dict[str, Any]:
        """Get module information"""
        return {
            'module_name': self.module_name,
            'module_type': 'rules_management',
            'active_rules_count': len(self.active_rules),
            'enabled_rules_count': sum(1 for rule in self.active_rules.values() if rule['enabled']),
            'custom_rules_count': len(self.custom_rules),
            'rule_categories': self.rule_categories.copy(),
            'rule_types': ['constraint', 'filter', 'enhancement'],
            'features': [
                'rule_validation_and_enforcement',
                'custom_rule_creation_and_management',
                'rule_based_decision_modification',
                'constraint_violation_detection',
                'filter_based_recommendation_blocking',
                'enhancement_rule_application',
                'rule_statistics_and_analytics',
                'configuration_import_export',
                'priority_based_rule_execution',
                'category_based_rule_organization'
            ],
            'supported_rule_categories': list(self.rule_categories.keys()),
            'rule_execution_order': 'priority_based',
            'description': 'Manages comprehensive trading rules, validates decisions, and provides rule-based constraints and enhancements'
        }