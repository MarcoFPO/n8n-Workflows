from typing import Dict, Any, List, Optional
import sys
from shared.common_imports import (
import asyncio
from ..single_function_module_base import SingleFunctionModule
"""
Account Settings Module - Single Function Module
Verantwortlich ausschließlich für Account Settings Management Logic
"""

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

    datetime, timedelta, BaseModel, structlog
)


class SettingsUpdateRequest(BaseModel):
    setting_category: str  # 'personal', 'security', 'trading', 'notifications', 'preferences'
    setting_key: str
    setting_value: Any
    validation_required: bool = True


class SettingValidationRule(BaseModel):
    rule_type: str  # 'required', 'type', 'range', 'format', 'custom'
    rule_parameters: Dict[str, Any]
    error_message: str


class SettingsUpdateResult(BaseModel):
    update_successful: bool
    setting_category: str
    setting_key: str
    old_value: Any
    new_value: Any
    validation_passed: bool
    validation_messages: List[str]
    requires_verification: bool
    verification_method: Optional[str] = None
    update_timestamp: datetime


class AccountSettingsModule(SingleFunctionModule):
    """
    Single Function Module: Account Settings Management
    Verantwortlichkeit: Ausschließlich Account-Settings-Management-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("account_settings", event_bus)
        
        # Account Settings Storage (Mock Database)
        self.account_settings = {
            'personal': {
                'email': 'user@example.com',
                'phone': '+49123456789',
                'first_name': 'Max',
                'last_name': 'Mustermann',
                'date_of_birth': '1990-01-01',
                'nationality': 'DE',
                'address_line1': 'Musterstraße 123',
                'address_line2': '',
                'city': 'München',
                'postal_code': '80331',
                'country': 'DE',
                'tax_id': 'DE123456789',
                'preferred_language': 'de',
                'timezone': 'Europe/Berlin'
            },
            'security': {
                'two_factor_enabled': True,
                'two_factor_method': 'app',  # 'sms', 'email', 'app'
                'login_notifications': True,
                'suspicious_activity_alerts': True,
                'password_last_changed': '2024-01-15T10:30:00Z',
                'failed_login_threshold': 5,
                'session_timeout_minutes': 30,
                'ip_whitelist_enabled': False,
                'ip_whitelist': [],
                'device_trust_enabled': True,
                'require_2fa_for_withdrawals': True,
                'require_2fa_for_settings_changes': True
            },
            'trading': {
                'default_order_type': 'limit',
                'default_time_in_force': 'GTC',  # Good Till Cancelled
                'price_alerts_enabled': True,
                'auto_refresh_portfolio': True,
                'portfolio_refresh_interval_seconds': 30,
                'show_advanced_charts': True,
                'default_chart_timeframe': '1h',
                'risk_warnings_enabled': True,
                'position_size_warnings': True,
                'concentration_warnings': True,
                'stop_loss_default_percentage': 5.0,
                'take_profit_default_percentage': 10.0,
                'max_slippage_percentage': 1.0
            },
            'notifications': {
                'email_notifications': True,
                'sms_notifications': False,
                'push_notifications': True,
                'trade_confirmations': True,
                'balance_alerts': True,
                'price_alerts': True,
                'news_updates': False,
                'promotional_emails': False,
                'security_alerts': True,
                'maintenance_notifications': True,
                'balance_threshold_eur': 1000.0,
                'large_transaction_threshold_eur': 10000.0
            },
            'preferences': {
                'dark_mode': False,
                'compact_view': False,
                'show_portfolio_percentages': True,
                'hide_small_balances': False,
                'small_balance_threshold_eur': 10.0,
                'currency_display': 'EUR',
                'number_format': 'european',  # 'european', 'american'
                'date_format': 'dd.mm.yyyy',
                'time_format': '24h',
                'dashboard_widgets': ['balance', 'portfolio', 'recent_trades', 'news'],
                'auto_logout_minutes': 60
            }
        }
        
        # Settings Validation Rules
        self.validation_rules = {
            'personal': {
                'email': [
                    SettingValidationRule(
                        rule_type='format',
                        rule_parameters={'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'},
                        error_message='Invalid email format'
                    )
                ],
                'phone': [
                    SettingValidationRule(
                        rule_type='format',
                        rule_parameters={'pattern': r'^\+[1-9]\d{1,14}$'},
                        error_message='Invalid phone format (use international format)'
                    )
                ],
                'postal_code': [
                    SettingValidationRule(
                        rule_type='format',
                        rule_parameters={'pattern': r'^\d{5}$'},
                        error_message='German postal code must be 5 digits'
                    )
                ]
            },
            'security': {
                'failed_login_threshold': [
                    SettingValidationRule(
                        rule_type='range',
                        rule_parameters={'min': 3, 'max': 10},
                        error_message='Failed login threshold must be between 3 and 10'
                    )
                ],
                'session_timeout_minutes': [
                    SettingValidationRule(
                        rule_type='range',
                        rule_parameters={'min': 5, 'max': 480},
                        error_message='Session timeout must be between 5 and 480 minutes'
                    )
                ]
            },
            'trading': {
                'portfolio_refresh_interval_seconds': [
                    SettingValidationRule(
                        rule_type='range',
                        rule_parameters={'min': 10, 'max': 300},
                        error_message='Refresh interval must be between 10 and 300 seconds'
                    )
                ],
                'stop_loss_default_percentage': [
                    SettingValidationRule(
                        rule_type='range',
                        rule_parameters={'min': 0.1, 'max': 50.0},
                        error_message='Stop loss percentage must be between 0.1% and 50%'
                    )
                ]
            },
            'notifications': {
                'balance_threshold_eur': [
                    SettingValidationRule(
                        rule_type='range',
                        rule_parameters={'min': 1.0, 'max': 100000.0},
                        error_message='Balance threshold must be between €1 and €100,000'
                    )
                ]
            },
            'preferences': {
                'small_balance_threshold_eur': [
                    SettingValidationRule(
                        rule_type='range',
                        rule_parameters={'min': 0.01, 'max': 1000.0},
                        error_message='Small balance threshold must be between €0.01 and €1,000'
                    )
                ]
            }
        }
        
        # Settings that require verification
        self.verification_required_settings = {
            'personal': ['email', 'phone', 'address_line1', 'city', 'postal_code', 'country'],
            'security': ['two_factor_enabled', 'two_factor_method', 'require_2fa_for_withdrawals'],
            'trading': [],  # No trading settings require verification
            'notifications': [],
            'preferences': []
        }
        
        # Settings Update History
        self.settings_history = []
        self.settings_counter = 0
        
        # Settings Categories Metadata
        self.category_metadata = {
            'personal': {
                'display_name': 'Personal Information',
                'description': 'Personal details and contact information',
                'requires_kyc': True,
                'sensitive': True
            },
            'security': {
                'display_name': 'Security Settings',
                'description': 'Account security and authentication settings',
                'requires_kyc': False,
                'sensitive': True
            },
            'trading': {
                'display_name': 'Trading Preferences',
                'description': 'Trading interface and default settings',
                'requires_kyc': False,
                'sensitive': False
            },
            'notifications': {
                'display_name': 'Notifications',
                'description': 'Communication preferences and alerts',
                'requires_kyc': False,
                'sensitive': False
            },
            'preferences': {
                'display_name': 'User Preferences',
                'description': 'Interface and display preferences',
                'requires_kyc': False,
                'sensitive': False
            }
        }
        
        # Settings Change Tracking
        self.settings_audit_log = []
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Account Settings Management
        
        Args:
            input_data: {
                'operation': required string ('get', 'set', 'get_category', 'reset', 'validate'),
                'setting_category': required string for set/get_category operations,
                'setting_key': required string for set operations,
                'setting_value': required for set operations,
                'validation_required': optional bool (default: true),
                'include_metadata': optional bool (default: false)
            }
            
        Returns:
            Dict mit Settings-Operation-Result
        """
        start_time = datetime.now()
        operation = input_data.get('operation', 'get')
        
        if operation == 'get':
            # Get all settings or specific category
            category = input_data.get('setting_category')
            include_metadata = input_data.get('include_metadata', False)
            return await self._get_settings(category, include_metadata)
            
        elif operation == 'set':
            # Update specific setting
            try:
                update_request = SettingsUpdateRequest(
                    setting_category=input_data.get('setting_category'),
                    setting_key=input_data.get('setting_key'),
                    setting_value=input_data.get('setting_value'),
                    validation_required=input_data.get('validation_required', True)
                )
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Invalid settings update request: {str(e)}'
                }
                
            update_result = await self._update_setting(update_request)
            
            # Statistics and History Update
            self.settings_counter += 1
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            self.settings_history.append({
                'timestamp': datetime.now(),
                'operation': 'set',
                'setting_category': update_request.setting_category,
                'setting_key': update_request.setting_key,
                'update_successful': update_result.update_successful,
                'validation_passed': update_result.validation_passed,
                'requires_verification': update_result.requires_verification,
                'processing_time_ms': processing_time_ms,
                'change_id': self.settings_counter
            })
            
            # Limit History
            if len(self.settings_history) > 500:
                self.settings_history.pop(0)
            
            # Event Publishing
            await self._publish_settings_change_event(update_result, update_request)
            
            self.logger.info(f"Setting updated",
                           category=update_request.setting_category,
                           key=update_request.setting_key,
                           update_successful=update_result.update_successful,
                           requires_verification=update_result.requires_verification,
                           processing_time_ms=round(processing_time_ms, 2),
                           change_id=self.settings_counter)
            
            return {
                'success': True,
                'update_successful': update_result.update_successful,
                'setting_category': update_result.setting_category,
                'setting_key': update_result.setting_key,
                'old_value': update_result.old_value,
                'new_value': update_result.new_value,
                'validation_passed': update_result.validation_passed,
                'validation_messages': update_result.validation_messages,
                'requires_verification': update_result.requires_verification,
                'verification_method': update_result.verification_method,
                'update_timestamp': update_result.update_timestamp.isoformat()
            }
            
        elif operation == 'validate':
            # Validate setting value without updating
            category = input_data.get('setting_category')
            key = input_data.get('setting_key')
            value = input_data.get('setting_value')
            
            validation_result = await self._validate_setting_value(category, key, value)
            
            return {
                'success': True,
                'validation_passed': validation_result['valid'],
                'validation_messages': validation_result['messages']
            }
            
        elif operation == 'reset':
            # Reset settings to defaults
            category = input_data.get('setting_category')
            return await self._reset_settings(category)
            
        else:
            return {
                'success': False,
                'error': f'Unknown operation: {operation}'
            }
    
    async def _get_settings(self, category: Optional[str] = None, 
                          include_metadata: bool = False) -> Dict[str, Any]:
        """Gibt Settings zurück (alle oder spezifische Kategorie)"""
        
        if category:
            if category not in self.account_settings:
                return {
                    'success': False,
                    'error': f'Unknown settings category: {category}'
                }
            
            settings_data = {category: self.account_settings[category]}
        else:
            settings_data = self.account_settings
        
        result = {
            'success': True,
            'settings': settings_data
        }
        
        if include_metadata:
            result['metadata'] = {}
            for cat in settings_data.keys():
                result['metadata'][cat] = self.category_metadata.get(cat, {})
                result['metadata'][cat]['verification_required_settings'] = self.verification_required_settings.get(cat, [])
        
        return result
    
    async def _update_setting(self, request: SettingsUpdateRequest) -> SettingsUpdateResult:
        """Aktualisiert spezifisches Setting"""
        
        category = request.setting_category
        key = request.setting_key
        new_value = request.setting_value
        
        # Check if category exists
        if category not in self.account_settings:
            return SettingsUpdateResult(
                update_successful=False,
                setting_category=category,
                setting_key=key,
                old_value=None,
                new_value=new_value,
                validation_passed=False,
                validation_messages=[f'Unknown settings category: {category}'],
                requires_verification=False,
                update_timestamp=datetime.now()
            )
        
        # Check if setting key exists
        if key not in self.account_settings[category]:
            return SettingsUpdateResult(
                update_successful=False,
                setting_category=category,
                setting_key=key,
                old_value=None,
                new_value=new_value,
                validation_passed=False,
                validation_messages=[f'Unknown setting key: {key} in category {category}'],
                requires_verification=False,
                update_timestamp=datetime.now()
            )
        
        old_value = self.account_settings[category][key]
        
        # Validation
        validation_passed = True
        validation_messages = []
        
        if request.validation_required:
            validation_result = await self._validate_setting_value(category, key, new_value)
            validation_passed = validation_result['valid']
            validation_messages = validation_result['messages']
        
        # Verification Check
        requires_verification = await self._requires_verification(category, key, old_value, new_value)
        verification_method = None
        
        if requires_verification:
            verification_method = await self._determine_verification_method(category, key)
        
        # Update setting if validation passed and no verification required (or verification handled separately)
        update_successful = validation_passed
        
        if update_successful and not requires_verification:
            self.account_settings[category][key] = new_value
            
            # Add to audit log
            self._add_to_audit_log(category, key, old_value, new_value, 'updated')
        elif update_successful and requires_verification:
            # Setting update pending verification
            self._add_to_audit_log(category, key, old_value, new_value, 'pending_verification')
        
        return SettingsUpdateResult(
            update_successful=update_successful,
            setting_category=category,
            setting_key=key,
            old_value=old_value,
            new_value=new_value,
            validation_passed=validation_passed,
            validation_messages=validation_messages,
            requires_verification=requires_verification,
            verification_method=verification_method,
            update_timestamp=datetime.now()
        )
    
    async def _validate_setting_value(self, category: str, key: str, value: Any) -> Dict[str, Any]:
        """Validiert Setting Value gegen definierte Rules"""
        
        validation_messages = []
        
        # Get validation rules for this setting
        rules = self.validation_rules.get(category, {}).get(key, [])
        
        if not rules:
            return {'valid': True, 'messages': []}
        
        # Apply validation rules
        for rule in rules:
            rule_valid = await self._apply_validation_rule(rule, value)
            if not rule_valid:
                validation_messages.append(rule.error_message)
        
        return {
            'valid': len(validation_messages) == 0,
            'messages': validation_messages
        }
    
    async def _apply_validation_rule(self, rule: SettingValidationRule, value: Any) -> bool:
        """Wendet einzelne Validation Rule an"""
        
        if rule.rule_type == 'required':
            return value is not None and value != ''
        
        elif rule.rule_type == 'type':
            expected_type = rule.rule_parameters.get('type')
            return isinstance(value, expected_type)
        
        elif rule.rule_type == 'range':
            if not isinstance(value, (int, float)):
                return False
            min_val = rule.rule_parameters.get('min')
            max_val = rule.rule_parameters.get('max')
            return (min_val is None or value >= min_val) and (max_val is None or value <= max_val)
        
        elif rule.rule_type == 'format':
            if not isinstance(value, str):
                return False
            import re
            pattern = rule.rule_parameters.get('pattern')
            return bool(re.match(pattern, value))
        
        elif rule.rule_type == 'custom':
            # Custom validation logic would go here
            return True
        
        return True
    
    async def _requires_verification(self, category: str, key: str, 
                                   old_value: Any, new_value: Any) -> bool:
        """Prüft ob Setting Change Verification benötigt"""
        
        # Check if this setting requires verification
        if key not in self.verification_required_settings.get(category, []):
            return False
        
        # Check if value actually changed
        if old_value == new_value:
            return False
        
        # Sensitive changes always require verification
        if category in ['personal', 'security']:
            return True
        
        return False
    
    async def _determine_verification_method(self, category: str, key: str) -> str:
        """Bestimmt erforderliche Verification Method"""
        
        # High-security settings require 2FA
        high_security_settings = {
            'security': ['two_factor_enabled', 'require_2fa_for_withdrawals'],
            'personal': ['email', 'phone']
        }
        
        if category in high_security_settings and key in high_security_settings[category]:
            return '2fa'
        
        # Personal data changes require email verification
        if category == 'personal':
            return 'email'
        
        return 'email'  # Default
    
    async def _reset_settings(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Reset Settings zu Default Values"""
        
        # Default settings (would be loaded from config)
        default_settings = {
            'trading': {
                'default_order_type': 'market',
                'default_time_in_force': 'IOC',
                'price_alerts_enabled': False,
                'auto_refresh_portfolio': True,
                'portfolio_refresh_interval_seconds': 60
            },
            'notifications': {
                'email_notifications': True,
                'sms_notifications': False,
                'push_notifications': True,
                'promotional_emails': False
            },
            'preferences': {
                'dark_mode': False,
                'compact_view': False,
                'currency_display': 'EUR',
                'number_format': 'european'
            }
        }
        
        reset_count = 0
        reset_categories = []
        
        if category:
            if category in default_settings:
                old_settings = self.account_settings[category].copy()
                self.account_settings[category].update(default_settings[category])
                reset_count = len(default_settings[category])
                reset_categories = [category]
                
                # Audit log
                for key, new_value in default_settings[category].items():
                    old_value = old_settings.get(key)
                    self._add_to_audit_log(category, key, old_value, new_value, 'reset')
            else:
                return {
                    'success': False,
                    'error': f'Cannot reset category {category} - no defaults available'
                }
        else:
            # Reset all categories that have defaults
            for cat, defaults in default_settings.items():
                old_settings = self.account_settings[cat].copy()
                self.account_settings[cat].update(defaults)
                reset_count += len(defaults)
                reset_categories.append(cat)
                
                # Audit log
                for key, new_value in defaults.items():
                    old_value = old_settings.get(key)
                    self._add_to_audit_log(cat, key, old_value, new_value, 'reset')
        
        return {
            'success': True,
            'reset_categories': reset_categories,
            'settings_reset_count': reset_count,
            'reset_timestamp': datetime.now().isoformat()
        }
    

        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())

    def _add_to_audit_log(self, category: str, key: str, old_value: Any, 
                         new_value: Any, action: str):
        """Fügt Änderung zum Audit Log hinzu"""
        
        self.settings_audit_log.append({
            'timestamp': datetime.now(),
            'category': category,
            'key': key,
            'old_value': old_value,
            'new_value': new_value,
            'action': action,  # 'updated', 'reset', 'pending_verification'
            'change_id': self.settings_counter + 1
        })
        
        # Limit audit log size
        if len(self.settings_audit_log) > 1000:
            self.settings_audit_log.pop(0)
    
    async def _publish_settings_change_event(self, result: SettingsUpdateResult, 
                                           request: SettingsUpdateRequest):
        """Published Settings Change Event über Event-Bus"""
        
        if not self.event_bus or not self.event_bus.connected:
            return
        
        # Only publish for successful updates
        if not result.update_successful:
            return
        
        from event_bus import Event
        
        # Determine event criticality
        critical_settings = {
            'security': ['two_factor_enabled', 'require_2fa_for_withdrawals'],
            'personal': ['email', 'phone']
        }
        
        is_critical = (request.setting_category in critical_settings and 
                      request.setting_key in critical_settings[request.setting_category])
        
        event = Event(
            event_type="account_settings_changed",
            stream_id=f"settings-{self.settings_counter}",
            data={
                'setting_category': result.setting_category,
                'setting_key': result.setting_key,
                'requires_verification': result.requires_verification,
                'verification_method': result.verification_method,
                'is_critical_setting': is_critical,
                'update_timestamp': result.update_timestamp.isoformat(),
                'change_id': self.settings_counter
            },
            source="account_settings"
        )
        
        await self.event_bus.publish(event)
    
    def get_settings_summary(self) -> Dict[str, Any]:
        """Gibt Settings Summary zurück"""
        
        # Count settings by category
        category_counts = {}
        for category, settings in self.account_settings.items():
            category_counts[category] = len(settings)
        
        # Recent changes
        recent_changes = [
            change for change in self.settings_audit_log
            if (datetime.now() - change['timestamp']).days < 7
        ]
        
        # Verification pending settings
        pending_verification = [
            change for change in self.settings_audit_log
            if change['action'] == 'pending_verification'
        ]
        
        # Security score
        security_score = await self._calculate_security_score()
        
        return {
            'total_settings': sum(category_counts.values()),
            'settings_by_category': category_counts,
            'recent_changes_7_days': len(recent_changes),
            'pending_verification_count': len(pending_verification),
            'security_score': security_score,
            'two_factor_enabled': self.account_settings['security']['two_factor_enabled'],
            'notification_preferences_configured': self._are_notifications_configured(),
            'last_settings_change': max([change['timestamp'] for change in self.settings_audit_log]).isoformat() if self.settings_audit_log else None
        }
    
    async def _calculate_security_score(self) -> float:
        """Berechnet Security Score basierend auf Security Settings"""
        
        security_settings = self.account_settings['security']
        score = 0.0
        
        # 2FA enabled (30 points)
        if security_settings['two_factor_enabled']:
            score += 30
            # Bonus for app-based 2FA
            if security_settings['two_factor_method'] == 'app':
                score += 10
        
        # Security notifications (20 points)
        if security_settings['login_notifications']:
            score += 10
        if security_settings['suspicious_activity_alerts']:
            score += 10
        
        # 2FA for sensitive operations (20 points)
        if security_settings['require_2fa_for_withdrawals']:
            score += 10
        if security_settings['require_2fa_for_settings_changes']:
            score += 10
        
        # Session security (10 points)
        if security_settings['session_timeout_minutes'] <= 60:
            score += 5
        if security_settings['device_trust_enabled']:
            score += 5
        
        # IP restrictions (10 points)
        if security_settings['ip_whitelist_enabled']:
            score += 10
        
        return round(score, 1)
    
    def _are_notifications_configured(self) -> bool:
        """Prüft ob Notification Preferences vernünftig konfiguriert sind"""
        
        notifications = self.account_settings['notifications']
        
        # At least one notification method should be enabled
        has_notification_method = (
            notifications['email_notifications'] or 
            notifications['sms_notifications'] or 
            notifications['push_notifications']
        )
        
        # Security alerts should be enabled
        security_alerts_enabled = notifications['security_alerts']
        
        return has_notification_method and security_alerts_enabled
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'account_settings',
            'description': 'Complete account settings management with validation and verification',
            'responsibility': 'Account settings management logic only',
            'input_parameters': {
                'operation': 'Required operation (get, set, get_category, reset, validate)',
                'setting_category': 'Setting category (personal, security, trading, notifications, preferences)',
                'setting_key': 'Specific setting key within category',
                'setting_value': 'New value for setting (required for set operation)',
                'validation_required': 'Whether to validate setting value (default: true)',
                'include_metadata': 'Whether to include category metadata (default: false)'
            },
            'output_format': {
                'success': 'Whether operation was successful',
                'settings': 'Settings data (for get operations)',
                'update_successful': 'Whether setting update was successful (for set operations)',
                'validation_passed': 'Whether validation passed',
                'validation_messages': 'Validation error messages if any',
                'requires_verification': 'Whether change requires verification',
                'verification_method': 'Required verification method',
                'update_timestamp': 'Timestamp of setting change'
            },
            'supported_operations': ['get', 'set', 'get_category', 'reset', 'validate'],
            'supported_categories': list(self.account_settings.keys()),
            'category_metadata': self.category_metadata,
            'verification_required_settings': self.verification_required_settings,
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_settings_statistics(self) -> Dict[str, Any]:
        """Account Settings Module Statistiken"""
        total_changes = len(self.settings_history)
        
        if total_changes == 0:
            return {
                'total_setting_changes': 0,
                'total_settings_count': sum(len(settings) for settings in self.account_settings.values()),
                'supported_categories': len(self.account_settings)
            }
        
        # Success Rate
        successful_changes = sum(1 for change in self.settings_history if change['update_successful'])
        success_rate = round((successful_changes / total_changes) * 100, 1)
        
        # Category Distribution
        category_distribution = {}
        for change in self.settings_history:
            category = change['setting_category']
            category_distribution[category] = category_distribution.get(category, 0) + 1
        
        # Verification Required Rate
        verification_required_changes = sum(1 for change in self.settings_history if change.get('requires_verification', False))
        verification_rate = round((verification_required_changes / total_changes) * 100, 1)
        
        # Most Changed Settings
        setting_change_counts = {}
        for change in self.settings_history:
            setting_key = f"{change['setting_category']}.{change['setting_key']}"
            setting_change_counts[setting_key] = setting_change_counts.get(setting_key, 0) + 1
        
        most_changed = dict(sorted(setting_change_counts.items(), key=lambda x: x[1], reverse=True)[:5])
        
        # Recent Activity
        recent_changes = [
            change for change in self.settings_history
            if (datetime.now() - change['timestamp']).seconds < 86400  # Last 24 hours
        ]
        
        return {
            'total_setting_changes': total_changes,
            'successful_changes': successful_changes,
            'success_rate_percent': success_rate,
            'recent_changes_24h': len(recent_changes),
            'category_change_distribution': dict(sorted(
                category_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'verification_required_rate_percent': verification_rate,
            'most_changed_settings': most_changed,
            'total_settings_count': sum(len(settings) for settings in self.account_settings.values()),
            'audit_log_entries': len(self.settings_audit_log),
            'average_processing_time': self.average_execution_time
        }

    async def _setup_event_subscriptions(self):
        """Setup Event-Bus Subscriptions"""
        try:
            # Subscribe to relevant events for this module
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            
            self.logger.info("Event subscriptions setup completed", 
                           module=self.module_name)
        except Exception as e:
            self.logger.error("Failed to setup event subscriptions",
                            error=str(e), module=self.module_name)
    
    async def process_event(self, event):
        """Process incoming events"""
        try:
            event_type = event.get('event_type', '')
            
            if event_type == 'system.health.request':
                # Health check response
                health_response = {
                    'event_type': 'system.health.response',
                    'stream_id': 'health-check',
                    'data': {
                        'module_name': self.module_name,
                        'status': 'healthy',
                        'execution_count': getattr(self, 'execution_history', []),
                        'average_execution_time_ms': self.average_execution_time,
                        'health_check_timestamp': datetime.now().isoformat()
                    },
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(health_response)
                
            elif event_type == f'{self.module_name}.request':
                # Module-specific request
                event_data = event.get('data', {})
                result = await self.execute_function(event_data)
                
                response_event = {
                    'event_type': f'{self.module_name}.response',
                    'stream_id': event.get('stream_id', f'{self.module_name}-request'),
                    'data': result,
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(response_event)
            
            else:
                self.logger.debug("Unhandled event type", 
                                event_type=event_type, module=self.module_name)
                
        except Exception as e:
            self.logger.error("Failed to process event",
                            error=str(e), event=str(event), module=self.module_name)
