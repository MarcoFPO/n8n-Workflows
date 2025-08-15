from typing import Dict, Any, List, Optional
import sys
from shared.common_imports import (
import asyncio
from ..single_function_module_base import SingleFunctionModule
"""
Balance Update Module - Single Function Module
Verantwortlich ausschließlich für Account Balance Update Logic
"""

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

    datetime, BaseModel, structlog
)


class BalanceUpdateRequest(BaseModel):
    currency_code: str
    update_type: str  # 'set', 'add', 'subtract', 'lock', 'unlock'
    amount: str
    available_amount: Optional[str] = None
    locked_amount: Optional[str] = None
    total_amount: Optional[str] = None
    description: Optional[str] = None
    source_transaction_id: Optional[str] = None


class BalanceUpdateResult(BaseModel):
    update_successful: bool
    currency_code: str
    balance_before: Dict[str, str]
    balance_after: Dict[str, str]
    balance_changes: Dict[str, str]
    validation_warnings: List[str]
    update_timestamp: datetime


class BalanceUpdateModule(SingleFunctionModule):
    """
    Single Function Module: Balance Update
    Verantwortlichkeit: Ausschließlich Account-Balance-Update-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("balance_update", event_bus)
        
        # Account Balances Storage
        self.account_balances = {
            "EUR": {
                'available': '10000.00',
                'locked': '0.00',
                'total': '10000.00',
                'last_updated': datetime.now()
            },
            "USD": {
                'available': '5000.00',
                'locked': '0.00',
                'total': '5000.00',
                'last_updated': datetime.now()
            },
            "BTC": {
                'available': '0.25',
                'locked': '0.00',
                'total': '0.25',
                'last_updated': datetime.now()
            },
            "ETH": {
                'available': '2.5',
                'locked': '0.00',
                'total': '2.5',
                'last_updated': datetime.now()
            }
        }
        
        # Balance Update History
        self.update_history = []
        self.update_counter = 0
        
        # Balance Validation Rules
        self.validation_rules = {
            'min_balance_values': {
                'EUR': 0.01,
                'USD': 0.01,
                'BTC': 0.00000001,  # 1 satoshi
                'ETH': 0.000000001   # 1 gwei
            },
            'max_balance_values': {
                'EUR': 10000000.0,  # 10M EUR
                'USD': 10000000.0,  # 10M USD
                'BTC': 100.0,       # 100 BTC
                'ETH': 1000.0       # 1000 ETH
            },
            'precision_decimals': {
                'EUR': 2,
                'USD': 2,
                'BTC': 8,
                'ETH': 9
            },
            'allow_negative_balances': False,
            'require_balance_consistency': True  # total = available + locked
        }
        
        # Balance Change Notifications
        self.notification_thresholds = {
            'significant_change_threshold': {
                'EUR': 1000.0,  # Changes > 1000 EUR
                'USD': 1000.0,  # Changes > 1000 USD  
                'BTC': 0.1,     # Changes > 0.1 BTC
                'ETH': 1.0      # Changes > 1 ETH
            },
            'large_change_threshold': {
                'EUR': 10000.0, # Changes > 10k EUR
                'USD': 10000.0, # Changes > 10k USD
                'BTC': 1.0,     # Changes > 1 BTC
                'ETH': 10.0     # Changes > 10 ETH
            }
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Balance Update
        
        Args:
            input_data: {
                'currency_code': required string,
                'update_type': required string ('set', 'add', 'subtract', 'lock', 'unlock'),
                'amount': required string,
                'available_amount': optional string (for direct available balance set),
                'locked_amount': optional string (for direct locked balance set),
                'total_amount': optional string (for direct total balance set),
                'description': optional string,
                'source_transaction_id': optional string,
                'validate_before_update': optional bool (default: true),
                'force_update': optional bool (default: false)
            }
            
        Returns:
            Dict mit Balance-Update-Result
        """
        try:
            # Balance Update Request erstellen
            update_request = BalanceUpdateRequest(
                currency_code=input_data.get('currency_code'),
                update_type=input_data.get('update_type'),
                amount=input_data.get('amount'),
                available_amount=input_data.get('available_amount'),
                locked_amount=input_data.get('locked_amount'),
                total_amount=input_data.get('total_amount'),
                description=input_data.get('description'),
                source_transaction_id=input_data.get('source_transaction_id')
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Invalid balance update request: {str(e)}'
            }
        
        validate_before_update = input_data.get('validate_before_update', True)
        force_update = input_data.get('force_update', False)
        
        # Balance Update durchführen
        update_result = await self._execute_balance_update(
            update_request, validate_before_update, force_update
        )
        
        # Statistics Update
        self.update_counter += 1
        
        # Update History
        self.update_history.append({
            'timestamp': datetime.now(),
            'currency_code': update_request.currency_code,
            'update_type': update_request.update_type,
            'amount': update_request.amount,
            'update_successful': update_result.update_successful,
            'source_transaction_id': update_request.source_transaction_id,
            'warnings_count': len(update_result.validation_warnings),
            'update_id': self.update_counter
        })
        
        # Limit History
        if len(self.update_history) > 300:
            self.update_history.pop(0)
        
        # Event Publishing für signifikante Balance Changes
        if update_result.update_successful:
            await self._publish_balance_change_event(update_result)
        
        self.logger.info(f"Balance update processed",
                       currency_code=update_request.currency_code,
                       update_type=update_request.update_type,
                       amount=update_request.amount,
                       update_successful=update_result.update_successful,
                       warnings_count=len(update_result.validation_warnings),
                       update_id=self.update_counter)
        
        return {
            'success': True,
            'update_successful': update_result.update_successful,
            'currency_code': update_result.currency_code,
            'balance_before': update_result.balance_before,
            'balance_after': update_result.balance_after,
            'balance_changes': update_result.balance_changes,
            'validation_warnings': update_result.validation_warnings,
            'update_timestamp': update_result.update_timestamp.isoformat()
        }
    
    async def _execute_balance_update(self, request: BalanceUpdateRequest, 
                                    validate_before: bool, 
                                    force_update: bool) -> BalanceUpdateResult:
        """Führt Balance Update aus"""
        
        currency_code = request.currency_code.upper()
        validation_warnings = []
        
        # Current Balance abrufen oder initialisieren
        if currency_code not in self.account_balances:
            self.account_balances[currency_code] = {
                'available': '0.00',
                'locked': '0.00',
                'total': '0.00',
                'last_updated': datetime.now()
            }
        
        current_balance = self.account_balances[currency_code].copy()
        balance_before = {
            'available': current_balance['available'],
            'locked': current_balance['locked'],
            'total': current_balance['total']
        }
        
        # New Balance berechnen basierend auf update_type
        try:
            new_balance = await self._calculate_new_balance(request, current_balance)
        except Exception as e:
            return BalanceUpdateResult(
                update_successful=False,
                currency_code=currency_code,
                balance_before=balance_before,
                balance_after=balance_before,
                balance_changes={},
                validation_warnings=[f'Balance calculation failed: {str(e)}'],
                update_timestamp=datetime.now()
            )
        
        # Validation vor Update
        if validate_before and not force_update:
            validation_result = await self._validate_balance_update(
                currency_code, new_balance, current_balance
            )
            
            if not validation_result['valid']:
                return BalanceUpdateResult(
                    update_successful=False,
                    currency_code=currency_code,
                    balance_before=balance_before,
                    balance_after=balance_before,
                    balance_changes={},
                    validation_warnings=validation_result['errors'],
                    update_timestamp=datetime.now()
                )
            
            validation_warnings.extend(validation_result['warnings'])
        
        # Balance Update ausführen
        self.account_balances[currency_code] = {
            'available': new_balance['available'],
            'locked': new_balance['locked'],
            'total': new_balance['total'],
            'last_updated': datetime.now()
        }
        
        # Balance Changes berechnen
        balance_changes = await self._calculate_balance_changes(balance_before, new_balance)
        
        return BalanceUpdateResult(
            update_successful=True,
            currency_code=currency_code,
            balance_before=balance_before,
            balance_after=new_balance,
            balance_changes=balance_changes,
            validation_warnings=validation_warnings,
            update_timestamp=datetime.now()
        )
    
    async def _calculate_new_balance(self, request: BalanceUpdateRequest, 
                                   current_balance: Dict[str, Any]) -> Dict[str, str]:
        """Berechnet neue Balance basierend auf Update Type"""
        
        current_available = float(current_balance['available'])
        current_locked = float(current_balance['locked'])
        current_total = float(current_balance['total'])
        
        update_amount = float(request.amount)
        
        if request.update_type == 'set':
            # Direct Balance Set
            if request.available_amount is not None:
                new_available = float(request.available_amount)
            else:
                new_available = current_available
                
            if request.locked_amount is not None:
                new_locked = float(request.locked_amount)
            else:
                new_locked = current_locked
                
            if request.total_amount is not None:
                new_total = float(request.total_amount)
            else:
                new_total = new_available + new_locked
        
        elif request.update_type == 'add':
            # Add to available balance
            new_available = current_available + update_amount
            new_locked = current_locked
            new_total = new_available + new_locked
        
        elif request.update_type == 'subtract':
            # Subtract from available balance
            new_available = max(0, current_available - update_amount)
            new_locked = current_locked
            new_total = new_available + new_locked
        
        elif request.update_type == 'lock':
            # Move from available to locked
            if update_amount > current_available:
                raise ValueError(f'Cannot lock {update_amount} - only {current_available} available')
            
            new_available = current_available - update_amount
            new_locked = current_locked + update_amount
            new_total = current_total  # Total remains same
        
        elif request.update_type == 'unlock':
            # Move from locked to available
            if update_amount > current_locked:
                # Allow partial unlock
                unlock_amount = min(update_amount, current_locked)
            else:
                unlock_amount = update_amount
            
            new_available = current_available + unlock_amount
            new_locked = max(0, current_locked - unlock_amount)
            new_total = new_available + new_locked
        
        else:
            raise ValueError(f'Unknown update type: {request.update_type}')
        
        # Format with appropriate precision
        precision = self.validation_rules['precision_decimals'].get(request.currency_code.upper(), 2)
        
        return {
            'available': f"{new_available:.{precision}f}".rstrip('0').rstrip('.'),
            'locked': f"{new_locked:.{precision}f}".rstrip('0').rstrip('.'),
            'total': f"{new_total:.{precision}f}".rstrip('0').rstrip('.')
        }
    
    async def _validate_balance_update(self, currency_code: str, 
                                     new_balance: Dict[str, str],
                                     current_balance: Dict[str, str]) -> Dict[str, Any]:
        """Validiert Balance Update vor Ausführung"""
        
        errors = []
        warnings = []
        
        new_available = float(new_balance['available'])
        new_locked = float(new_balance['locked'])
        new_total = float(new_balance['total'])
        
        # Negative Balance Check
        if not self.validation_rules['allow_negative_balances']:
            if new_available < 0:
                errors.append(f'Available balance cannot be negative: {new_available}')
            if new_locked < 0:
                errors.append(f'Locked balance cannot be negative: {new_locked}')
            if new_total < 0:
                errors.append(f'Total balance cannot be negative: {new_total}')
        
        # Balance Consistency Check
        if self.validation_rules['require_balance_consistency']:
            calculated_total = new_available + new_locked
            if abs(calculated_total - new_total) > 0.0001:  # Allow small floating point errors
                errors.append(f'Balance inconsistency: available + locked ({calculated_total}) != total ({new_total})')
        
        # Min/Max Balance Validation
        min_balance = self.validation_rules['min_balance_values'].get(currency_code, 0)
        max_balance = self.validation_rules['max_balance_values'].get(currency_code, float('inf'))
        
        if new_total > 0 and new_total < min_balance:
            warnings.append(f'Balance below minimum threshold: {new_total} < {min_balance}')
        
        if new_total > max_balance:
            errors.append(f'Balance exceeds maximum allowed: {new_total} > {max_balance}')
        
        # Precision Validation
        precision = self.validation_rules['precision_decimals'].get(currency_code, 2)
        
        for balance_type, value in new_balance.items():
            decimal_places = len(value.split('.')[1]) if '.' in value else 0
            if decimal_places > precision:
                warnings.append(f'{balance_type} balance has too many decimal places: {decimal_places} > {precision}')
        
        # Significant Change Warning
        current_total = float(current_balance['total'])
        change_amount = abs(new_total - current_total)
        
        significant_threshold = self.notification_thresholds['significant_change_threshold'].get(currency_code, 0)
        if change_amount > significant_threshold:
            warnings.append(f'Significant balance change: {change_amount} {currency_code}')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    async def _calculate_balance_changes(self, balance_before: Dict[str, str], 
                                       balance_after: Dict[str, str]) -> Dict[str, str]:
        """Berechnet Balance Changes"""
        
        changes = {}
        
        for balance_type in ['available', 'locked', 'total']:
            before_value = float(balance_before[balance_type])
            after_value = float(balance_after[balance_type])
            change_value = after_value - before_value
            
            # Format change mit Vorzeichen
            if change_value > 0:
                changes[f'{balance_type}_change'] = f'+{change_value:.8f}'.rstrip('0').rstrip('.')
            elif change_value < 0:
                changes[f'{balance_type}_change'] = f'{change_value:.8f}'.rstrip('0').rstrip('.')
            else:
                changes[f'{balance_type}_change'] = '0'
        
        return changes
    
    async def _publish_balance_change_event(self, update_result: BalanceUpdateResult):
        """Published Balance Change Event über Event-Bus"""
        
        if not self.event_bus or not self.event_bus.connected:
            return
        
        # Check if change is significant enough to publish
        total_change = float(update_result.balance_changes.get('total_change', '0').replace('+', ''))
        significant_threshold = self.notification_thresholds['significant_change_threshold'].get(
            update_result.currency_code, 0
        )
        
        if abs(total_change) < significant_threshold:
            return  # Not significant enough
        
        from event_bus import Event
        
        event = Event(
            event_type="balance_updated",
            stream_id=f"balance-{update_result.currency_code}-{self.update_counter}",
            data={
                'currency_code': update_result.currency_code,
                'balance_before': update_result.balance_before,
                'balance_after': update_result.balance_after,
                'balance_changes': update_result.balance_changes,
                'update_timestamp': update_result.update_timestamp.isoformat(),
                'change_magnitude': 'large' if abs(total_change) > self.notification_thresholds['large_change_threshold'].get(
                    update_result.currency_code, float('inf')
                ) else 'significant'
            },
            source="balance_update"
        )
        
        await self.event_bus.publish(event)
    

        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())

    def get_current_balance(self, currency_code: str) -> Optional[Dict[str, str]]:
        """Gibt aktuelle Balance für Currency zurück"""
        currency_code = currency_code.upper()
        if currency_code in self.account_balances:
            balance = self.account_balances[currency_code]
            return {
                'available': balance['available'],
                'locked': balance['locked'],
                'total': balance['total'],
                'last_updated': balance['last_updated'].isoformat()
            }
        return None
    
    def get_all_balances(self) -> Dict[str, Dict[str, str]]:
        """Gibt alle aktuellen Balances zurück"""
        all_balances = {}
        for currency, balance in self.account_balances.items():
            all_balances[currency] = {
                'available': balance['available'],
                'locked': balance['locked'],
                'total': balance['total'],
                'last_updated': balance['last_updated'].isoformat()
            }
        return all_balances
    
    def set_validation_rules(self, rules_update: Dict[str, Any]):
        """Aktualisiert Validation Rules"""
        for rule_category, rule_values in rules_update.items():
            if rule_category in self.validation_rules:
                self.validation_rules[rule_category].update(rule_values)
                self.logger.info(f"Validation rules updated",
                               category=rule_category,
                               updated_values=list(rule_values.keys()))
    
    def reset_balance(self, currency_code: str, available: str = "0.00", 
                     locked: str = "0.00"):
        """Reset Balance für Currency (Administrative Function)"""
        currency_code = currency_code.upper()
        
        total = str(float(available) + float(locked))
        
        self.account_balances[currency_code] = {
            'available': available,
            'locked': locked,
            'total': total,
            'last_updated': datetime.now()
        }
        
        self.logger.warning(f"Balance reset for currency",
                          currency=currency_code,
                          available=available,
                          locked=locked,
                          total=total)
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'balance_update',
            'description': 'Updates account balances with comprehensive validation and change tracking',
            'responsibility': 'Account balance update logic only',
            'input_parameters': {
                'currency_code': 'Required currency code to update',
                'update_type': 'Required update type (set, add, subtract, lock, unlock)',
                'amount': 'Required amount for the update',
                'available_amount': 'Optional direct available balance amount (for set operation)',
                'locked_amount': 'Optional direct locked balance amount (for set operation)',
                'total_amount': 'Optional direct total balance amount (for set operation)',
                'description': 'Optional description of the update',
                'source_transaction_id': 'Optional transaction ID that triggered this update',
                'validate_before_update': 'Whether to validate before update (default: true)',
                'force_update': 'Whether to force update despite validation warnings (default: false)'
            },
            'output_format': {
                'update_successful': 'Whether the balance update was successful',
                'currency_code': 'Currency code that was updated',
                'balance_before': 'Balance values before the update',
                'balance_after': 'Balance values after the update',
                'balance_changes': 'Calculated changes in each balance component',
                'validation_warnings': 'List of validation warnings if any',
                'update_timestamp': 'Timestamp of the balance update'
            },
            'supported_currencies': list(self.account_balances.keys()),
            'supported_update_types': ['set', 'add', 'subtract', 'lock', 'unlock'],
            'validation_rules': self.validation_rules,
            'notification_thresholds': self.notification_thresholds,
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_balance_update_statistics(self) -> Dict[str, Any]:
        """Balance Update Module Statistiken"""
        total_updates = len(self.update_history)
        
        if total_updates == 0:
            return {
                'total_updates': 0,
                'supported_currencies': len(self.account_balances),
                'validation_rules_active': len(self.validation_rules)
            }
        
        # Success Rate
        successful_updates = sum(1 for update in self.update_history if update['update_successful'])
        success_rate = round((successful_updates / total_updates) * 100, 1) if total_updates > 0 else 0
        
        # Update Type Distribution
        update_type_distribution = {}
        for update in self.update_history:
            update_type = update['update_type']
            update_type_distribution[update_type] = update_type_distribution.get(update_type, 0) + 1
        
        # Currency Distribution
        currency_distribution = {}
        for update in self.update_history:
            currency = update['currency_code']
            currency_distribution[currency] = currency_distribution.get(currency, 0) + 1
        
        # Warning Rate
        updates_with_warnings = sum(1 for update in self.update_history if update['warnings_count'] > 0)
        warning_rate = round((updates_with_warnings / total_updates) * 100, 1) if total_updates > 0 else 0
        
        # Recent Activity
        recent_updates = [
            update for update in self.update_history
            if (datetime.now() - update['timestamp']).seconds < 3600  # Last hour
        ]
        
        return {
            'total_updates': total_updates,
            'successful_updates': successful_updates,
            'success_rate_percent': success_rate,
            'recent_updates_last_hour': len(recent_updates),
            'update_type_distribution': dict(sorted(
                update_type_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'currency_update_distribution': dict(sorted(
                currency_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'updates_with_warnings': updates_with_warnings,
            'warning_rate_percent': warning_rate,
            'supported_currencies': len(self.account_balances),
            'validation_rules_categories': len(self.validation_rules),
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
