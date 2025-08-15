"""
Order Config Handler Module - Single Function Module
Verantwortlich ausschließlich für Configuration Event Handling Logic
"""

import asyncio
from typing import Dict, Any, List, Optional, Union
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from ..single_function_module_base import SingleFunctionModule


class ConfigChange(BaseModel):
    config_key: str
    old_value: Optional[Union[str, int, float, bool, Dict, List]] = None
    new_value: Union[str, int, float, bool, Dict, List]
    change_type: str  # 'create', 'update', 'delete'
    timestamp: datetime
    source: str
    validation_passed: bool = True
    validation_errors: List[str] = []


class ConfigUpdateResult(BaseModel):
    config_key: str
    update_successful: bool
    changes_applied: List[ConfigChange]
    affected_orders: List[str]
    restart_required: bool
    validation_errors: List[str]
    rollback_available: bool
    update_timestamp: datetime


class OrderConfigHandlerModule(SingleFunctionModule):
    """
    Single Function Module: Order Config Handler
    Verantwortlichkeit: Ausschließlich Configuration-Event-Handling-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_config_handler", event_bus)
        
        # Configuration Management
        self.current_config = {}
        self.config_history = {}
        self.config_validators = {}
        self.config_update_counter = 0
        
        # Default Order Configuration
        self._initialize_default_config()
        
        # Configuration Change Tracking
        self.applied_changes = {}
        self.pending_changes = {}
        self.rollback_stack = []
        
        # Configuration Categories
        self.config_categories = {
            'execution_rules': [
                'max_slippage_percent',
                'min_order_amount', 
                'max_order_amount',
                'daily_order_limit',
                'risk_check_enabled',
                'position_size_limit'
            ],
            'risk_management': [
                'max_position_size_percent',
                'max_daily_volume_percent',
                'max_volatility_threshold',
                'min_liquidity_threshold',
                'max_concentration_per_asset'
            ],
            'order_routing': [
                'primary_broker',
                'fallback_brokers',
                'order_splitting_enabled',
                'max_order_split_count'
            ],
            'timing_controls': [
                'market_hours_only',
                'pre_market_enabled',
                'after_hours_enabled',
                'order_expiry_default'
            ],
            'instrument_limits': [
                'allowed_instruments',
                'blocked_instruments',
                'instrument_order_limits'
            ]
        }
        
    def _initialize_default_config(self):
        """Initialisiert Default Configuration"""
        self.current_config = {
            # Execution Rules
            'max_slippage_percent': 2.0,
            'min_order_amount': 10.0,
            'max_order_amount': 100000.0,
            'daily_order_limit': 1000000.0,
            'risk_check_enabled': True,
            'position_size_limit': 0.1,
            
            # Risk Management
            'max_position_size_percent': 10.0,
            'max_daily_volume_percent': 20.0,
            'max_volatility_threshold': 0.05,
            'min_liquidity_threshold': 1000000,
            'max_concentration_per_asset': 0.25,
            
            # Order Routing
            'primary_broker': 'bitpanda_pro',
            'fallback_brokers': ['kraken', 'binance'],
            'order_splitting_enabled': True,
            'max_order_split_count': 5,
            
            # Timing Controls
            'market_hours_only': False,
            'pre_market_enabled': True,
            'after_hours_enabled': True,
            'order_expiry_default': 'GTC',
            
            # Instrument Limits
            'allowed_instruments': ['BTC_EUR', 'ETH_EUR', 'ADA_EUR', 'DOT_EUR'],
            'blocked_instruments': [],
            'instrument_order_limits': {
                'BTC_EUR': 50000.0,
                'ETH_EUR': 30000.0,
                'ADA_EUR': 10000.0,
                'DOT_EUR': 10000.0
            }
        }
        
        # Validators registrieren
        self._register_config_validators()
    
    def _register_config_validators(self):
        """Registriert Configuration Validators"""
        self.config_validators = {
            'max_slippage_percent': self._validate_percentage,
            'min_order_amount': self._validate_positive_number,
            'max_order_amount': self._validate_positive_number,
            'daily_order_limit': self._validate_positive_number,
            'risk_check_enabled': self._validate_boolean,
            'position_size_limit': self._validate_percentage,
            'max_position_size_percent': self._validate_percentage,
            'max_daily_volume_percent': self._validate_percentage,
            'max_volatility_threshold': self._validate_percentage,
            'min_liquidity_threshold': self._validate_positive_number,
            'max_concentration_per_asset': self._validate_percentage,
            'primary_broker': self._validate_broker,
            'fallback_brokers': self._validate_broker_list,
            'order_splitting_enabled': self._validate_boolean,
            'max_order_split_count': self._validate_positive_integer,
            'market_hours_only': self._validate_boolean,
            'pre_market_enabled': self._validate_boolean,
            'after_hours_enabled': self._validate_boolean,
            'order_expiry_default': self._validate_time_in_force,
            'allowed_instruments': self._validate_instrument_list,
            'blocked_instruments': self._validate_instrument_list,
            'instrument_order_limits': self._validate_instrument_limits
        }
    
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Configuration Event Handling
        
        Args:
            input_data: {
                'event': configuration change event,
                'current_orders': optional list of current orders for impact analysis,
                'validation_mode': 'strict' or 'permissive'
            }
            
        Returns:
            Dict mit Config-Update-Result
        """
        event_data = input_data.get('event')
        current_orders = input_data.get('current_orders', [])
        validation_mode = input_data.get('validation_mode', 'strict')
        
        if not event_data:
            raise ValueError('No configuration event provided')
        
        # Configuration Changes extrahieren
        config_changes = await self._extract_config_changes(event_data)
        
        # Configuration Update verarbeiten
        update_result = await self._process_config_update(
            config_changes, current_orders, validation_mode
        )
        
        return {
            'config_key': update_result.config_key,
            'update_successful': update_result.update_successful,
            'changes_applied': [change.dict() for change in update_result.changes_applied],
            'affected_orders': update_result.affected_orders,
            'restart_required': update_result.restart_required,
            'validation_errors': update_result.validation_errors,
            'rollback_available': update_result.rollback_available,
            'update_timestamp': update_result.update_timestamp.isoformat()
        }
    
    async def _extract_config_changes(self, event_data: Dict[str, Any]) -> List[ConfigChange]:
        """Extrahiert Configuration Changes aus Event Data"""
        
        data = event_data.get('data', {})
        changes = []
        
        # Single Config Change
        if 'config_key' in data:
            change = ConfigChange(
                config_key=data['config_key'],
                old_value=self.current_config.get(data['config_key']),
                new_value=data['new_value'],
                change_type=data.get('change_type', 'update'),
                timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
                source=data.get('source', 'unknown')
            )
            changes.append(change)
        
        # Bulk Config Changes
        elif 'config_changes' in data:
            for change_data in data['config_changes']:
                change = ConfigChange(
                    config_key=change_data['config_key'],
                    old_value=self.current_config.get(change_data['config_key']),
                    new_value=change_data['new_value'],
                    change_type=change_data.get('change_type', 'update'),
                    timestamp=datetime.fromisoformat(change_data.get('timestamp', datetime.now().isoformat())),
                    source=change_data.get('source', 'unknown')
                )
                changes.append(change)
        
        return changes
    
    async def _process_config_update(self, config_changes: List[ConfigChange],
                                   current_orders: List[Dict],
                                   validation_mode: str) -> ConfigUpdateResult:
        """Verarbeitet Configuration Update"""
        self.config_update_counter += 1
        
        # Primary Config Key (für Bulk Updates nehme ersten)
        primary_key = config_changes[0].config_key if config_changes else 'unknown'
        
        validated_changes = []
        validation_errors = []
        
        # Validation Phase
        for change in config_changes:
            validation_result = await self._validate_config_change(change, validation_mode)
            change.validation_passed = validation_result['valid']
            change.validation_errors = validation_result['errors']
            
            if validation_result['valid']:
                validated_changes.append(change)
            else:
                validation_errors.extend(validation_result['errors'])
        
        # Fehler-Handling basierend auf Validation Mode
        if validation_errors and validation_mode == 'strict':
            return ConfigUpdateResult(
                config_key=primary_key,
                update_successful=False,
                changes_applied=[],
                affected_orders=[],
                restart_required=False,
                validation_errors=validation_errors,
                rollback_available=False,
                update_timestamp=datetime.now()
            )
        
        # Configuration Changes anwenden
        applied_changes = []
        affected_orders = []
        restart_required = False
        
        # Rollback Point erstellen
        rollback_point = self._create_rollback_point()
        
        try:
            for change in validated_changes:
                # Change anwenden
                apply_result = await self._apply_config_change(change, current_orders)
                
                if apply_result['success']:
                    applied_changes.append(change)
                    affected_orders.extend(apply_result['affected_orders'])
                    
                    # Restart Requirements prüfen
                    if self._requires_restart(change.config_key):
                        restart_required = True
                
                # Config History aktualisieren
                self._update_config_history(change)
            
            update_successful = len(applied_changes) > 0
            
        except Exception as e:
            # Rollback bei Fehler
            self._rollback_to_point(rollback_point)
            validation_errors.append(f"Configuration update failed: {str(e)}")
            update_successful = False
            applied_changes = []
        
        # Event-Bus Notification für erfolgreiche Updates
        if update_successful and applied_changes:
            await self._publish_config_update_event(applied_changes, affected_orders)
        
        update_result = ConfigUpdateResult(
            config_key=primary_key,
            update_successful=update_successful,
            changes_applied=applied_changes,
            affected_orders=list(set(affected_orders)),  # Remove duplicates
            restart_required=restart_required,
            validation_errors=validation_errors,
            rollback_available=len(self.rollback_stack) > 0,
            update_timestamp=datetime.now()
        )
        
        self.logger.info(f"Configuration update processed",
                       config_key=primary_key,
                       success=update_successful,
                       changes_count=len(applied_changes),
                       affected_orders_count=len(set(affected_orders)),
                       restart_required=restart_required)
        
        return update_result
    
    async def _validate_config_change(self, change: ConfigChange, validation_mode: str) -> Dict[str, Any]:
        """Validiert einzelne Configuration Change"""
        
        config_key = change.config_key
        new_value = change.new_value
        
        errors = []
        
        # Validator für diesen Config Key
        validator = self.config_validators.get(config_key)
        if validator:
            validation_result = validator(new_value)
            if not validation_result['valid']:
                errors.extend(validation_result['errors'])
        
        # Cross-Validation (Config Key Dependencies)
        cross_validation_errors = await self._cross_validate_config(config_key, new_value)
        errors.extend(cross_validation_errors)
        
        # Business Logic Validation
        business_validation_errors = await self._business_validate_config(config_key, new_value)
        errors.extend(business_validation_errors)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    async def _apply_config_change(self, change: ConfigChange, current_orders: List[Dict]) -> Dict[str, Any]:
        """Wendet Configuration Change an"""
        
        config_key = change.config_key
        new_value = change.new_value
        
        # Affected Orders identifizieren
        affected_orders = await self._identify_affected_orders_by_config(
            config_key, new_value, current_orders
        )
        
        # Configuration anwenden
        if change.change_type == 'delete':
            if config_key in self.current_config:
                del self.current_config[config_key]
        else:
            self.current_config[config_key] = new_value
        
        self.logger.info(f"Configuration change applied",
                       config_key=config_key,
                       change_type=change.change_type,
                       affected_orders=len(affected_orders))
        
        return {
            'success': True,
            'affected_orders': [order.get('order_id') for order in affected_orders]
        }
    
    async def _identify_affected_orders_by_config(self, config_key: str, new_value: Any,
                                                current_orders: List[Dict]) -> List[Dict]:
        """Identifiziert Orders die von Config Change betroffen sind"""
        
        affected_orders = []
        
        # Config-spezifische Impact Analysis
        if config_key == 'max_order_amount':
            max_amount = float(new_value)
            affected_orders = [
                order for order in current_orders
                if float(order.get('amount', '0')) * 45000 > max_amount  # Beispiel BTC Price
            ]
        
        elif config_key == 'allowed_instruments':
            allowed = new_value if isinstance(new_value, list) else []
            affected_orders = [
                order for order in current_orders
                if order.get('instrument_code') not in allowed
            ]
        
        elif config_key == 'blocked_instruments':
            blocked = new_value if isinstance(new_value, list) else []
            affected_orders = [
                order for order in current_orders
                if order.get('instrument_code') in blocked
            ]
        
        elif config_key == 'market_hours_only' and new_value is True:
            # Prüfe Orders außerhalb Market Hours
            current_hour = datetime.now().hour
            if not (9 <= current_hour <= 17):  # Außerhalb Market Hours
                affected_orders = [
                    order for order in current_orders
                    if order.get('status') in ['OPEN', 'PARTIALLY_FILLED']
                ]
        
        elif config_key in ['max_slippage_percent', 'risk_check_enabled']:
            # Risk-bezogene Changes betreffen alle aktiven Orders
            affected_orders = [
                order for order in current_orders
                if order.get('status') in ['OPEN', 'PARTIALLY_FILLED']
            ]
        
        return affected_orders
    
    async def _cross_validate_config(self, config_key: str, new_value: Any) -> List[str]:
        """Cross-Validation zwischen Config Keys"""
        
        errors = []
        
        # Min/Max Order Amount Consistency
        if config_key == 'min_order_amount':
            max_amount = self.current_config.get('max_order_amount', float('inf'))
            if float(new_value) >= max_amount:
                errors.append("min_order_amount must be less than max_order_amount")
        
        elif config_key == 'max_order_amount':
            min_amount = self.current_config.get('min_order_amount', 0)
            if float(new_value) <= min_amount:
                errors.append("max_order_amount must be greater than min_order_amount")
        
        # Position Size vs Daily Limit
        if config_key == 'max_position_size_percent':
            daily_volume_percent = self.current_config.get('max_daily_volume_percent', 100)
            if float(new_value) > daily_volume_percent:
                errors.append("max_position_size_percent should not exceed max_daily_volume_percent")
        
        # Broker Configuration
        if config_key == 'primary_broker':
            fallback_brokers = self.current_config.get('fallback_brokers', [])
            if new_value in fallback_brokers:
                errors.append("primary_broker cannot be in fallback_brokers list")
        
        return errors
    
    async def _business_validate_config(self, config_key: str, new_value: Any) -> List[str]:
        """Business Logic Validation"""
        
        errors = []
        
        # Reasonable Limits Check
        if config_key == 'max_slippage_percent' and float(new_value) > 10.0:
            errors.append("max_slippage_percent exceeds reasonable limit of 10%")
        
        if config_key == 'daily_order_limit' and float(new_value) > 10000000.0:  # €10M
            errors.append("daily_order_limit exceeds reasonable limit of €10M")
        
        if config_key == 'max_order_split_count' and int(new_value) > 20:
            errors.append("max_order_split_count exceeds reasonable limit of 20")
        
        # Instrument Validation
        if config_key in ['allowed_instruments', 'blocked_instruments']:
            valid_instruments = ['BTC_EUR', 'ETH_EUR', 'ADA_EUR', 'DOT_EUR', 'AAPL', 'TSLA', 'MSFT']
            invalid_instruments = [inst for inst in new_value if inst not in valid_instruments]
            if invalid_instruments:
                errors.append(f"Invalid instruments: {invalid_instruments}")
        
        return errors
    
    # Validation Helper Methods
    def _validate_percentage(self, value: Any) -> Dict[str, Any]:
        """Validiert Percentage Value (0.0 - 1.0)"""
        try:
            float_val = float(value)
            if 0.0 <= float_val <= 1.0:
                return {'valid': True, 'errors': []}
            else:
                return {'valid': False, 'errors': ['Value must be between 0.0 and 1.0']}
        except (ValueError, TypeError):
            return {'valid': False, 'errors': ['Value must be a valid number']}
    
    def _validate_positive_number(self, value: Any) -> Dict[str, Any]:
        """Validiert Positive Number"""
        try:
            float_val = float(value)
            if float_val > 0:
                return {'valid': True, 'errors': []}
            else:
                return {'valid': False, 'errors': ['Value must be positive']}
        except (ValueError, TypeError):
            return {'valid': False, 'errors': ['Value must be a valid number']}
    
    def _validate_positive_integer(self, value: Any) -> Dict[str, Any]:
        """Validiert Positive Integer"""
        try:
            int_val = int(value)
            if int_val > 0:
                return {'valid': True, 'errors': []}
            else:
                return {'valid': False, 'errors': ['Value must be a positive integer']}
        except (ValueError, TypeError):
            return {'valid': False, 'errors': ['Value must be a valid integer']}
    
    def _validate_boolean(self, value: Any) -> Dict[str, Any]:
        """Validiert Boolean Value"""
        if isinstance(value, bool):
            return {'valid': True, 'errors': []}
        elif str(value).lower() in ['true', 'false', '1', '0']:
            return {'valid': True, 'errors': []}
        else:
            return {'valid': False, 'errors': ['Value must be boolean (true/false)']}
    
    def _validate_broker(self, value: Any) -> Dict[str, Any]:
        """Validiert Broker Name"""
        valid_brokers = ['bitpanda_pro', 'kraken', 'binance', 'coinbase_pro']
        if str(value) in valid_brokers:
            return {'valid': True, 'errors': []}
        else:
            return {'valid': False, 'errors': [f'Invalid broker. Valid options: {valid_brokers}']}
    
    def _validate_broker_list(self, value: Any) -> Dict[str, Any]:
        """Validiert Broker List"""
        if not isinstance(value, list):
            return {'valid': False, 'errors': ['Value must be a list']}
        
        valid_brokers = ['bitpanda_pro', 'kraken', 'binance', 'coinbase_pro']
        invalid_brokers = [broker for broker in value if broker not in valid_brokers]
        
        if invalid_brokers:
            return {'valid': False, 'errors': [f'Invalid brokers: {invalid_brokers}']}
        else:
            return {'valid': True, 'errors': []}
    
    def _validate_time_in_force(self, value: Any) -> Dict[str, Any]:
        """Validiert Time In Force"""
        valid_tif = ['GTC', 'IOC', 'FOK', 'DAY']
        if str(value) in valid_tif:
            return {'valid': True, 'errors': []}
        else:
            return {'valid': False, 'errors': [f'Invalid time in force. Valid options: {valid_tif}']}
    
    def _validate_instrument_list(self, value: Any) -> Dict[str, Any]:
        """Validiert Instrument List"""
        if not isinstance(value, list):
            return {'valid': False, 'errors': ['Value must be a list']}
        return {'valid': True, 'errors': []}
    
    def _validate_instrument_limits(self, value: Any) -> Dict[str, Any]:
        """Validiert Instrument Limits Dict"""
        if not isinstance(value, dict):
            return {'valid': False, 'errors': ['Value must be a dictionary']}
        
        errors = []
        for instrument, limit in value.items():
            try:
                float_limit = float(limit)
                if float_limit <= 0:
                    errors.append(f'Limit for {instrument} must be positive')
            except (ValueError, TypeError):
                errors.append(f'Invalid limit for {instrument}: must be a number')
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    def _requires_restart(self, config_key: str) -> bool:
        """Prüft ob Config Change einen Restart erfordert"""
        restart_required_configs = [
            'primary_broker',
            'fallback_brokers',
            'order_routing_enabled'
        ]
        return config_key in restart_required_configs
    
    def _create_rollback_point(self) -> Dict[str, Any]:
        """Erstellt Rollback Point"""
        rollback_point = {
            'timestamp': datetime.now(),
            'config_snapshot': self.current_config.copy()
        }
        
        self.rollback_stack.append(rollback_point)
        
        # Limitiere Rollback Stack auf 10 Einträge
        if len(self.rollback_stack) > 10:
            self.rollback_stack.pop(0)
        
        return rollback_point
    
    def _rollback_to_point(self, rollback_point: Dict[str, Any]):
        """Führt Rollback zu bestimmtem Point durch"""
        self.current_config = rollback_point['config_snapshot'].copy()
        self.logger.info("Configuration rolled back",
                       rollback_timestamp=rollback_point['timestamp'].isoformat())
    
    def _update_config_history(self, change: ConfigChange):
        """Aktualisiert Configuration History"""
        config_key = change.config_key
        
        if config_key not in self.config_history:
            self.config_history[config_key] = []
        
        self.config_history[config_key].append(change)
        
        # Limitiere History auf 50 Einträge pro Key
        if len(self.config_history[config_key]) > 50:
            self.config_history[config_key].pop(0)
    
    async def _publish_config_update_event(self, applied_changes: List[ConfigChange],
                                         affected_orders: List[str]):
        """Publisht Config Update Event über Event-Bus"""
        if not self.event_bus or not self.event_bus.connected:
            return
        
        from event_bus import Event
        
        event = Event(
            event_type="order_config_updated",
            stream_id=f"config-update-{int(datetime.now().timestamp())}",
            data={
                'changes_count': len(applied_changes),
                'changed_keys': [change.config_key for change in applied_changes],
                'affected_orders_count': len(affected_orders),
                'affected_orders': affected_orders,
                'update_timestamp': datetime.now().isoformat(),
                'config_snapshot': self.current_config
            },
            source="order_config_handler"
        )
        
        await self.event_bus.publish(event)
    
    def get_current_config(self) -> Dict[str, Any]:
        """Gibt aktuelle Configuration zurück"""
        return self.current_config.copy()
    
    def get_config_history(self, config_key: str) -> List[ConfigChange]:
        """Gibt Configuration History für Key zurück"""
        return self.config_history.get(config_key, [])
    
    def get_config_categories(self) -> Dict[str, List[str]]:
        """Gibt Configuration Categories zurück"""
        return self.config_categories.copy()
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_config_handler',
            'description': 'Processes configuration change events and applies validated updates',
            'responsibility': 'Configuration event handling and validation logic only',
            'input_parameters': {
                'event': 'Configuration change event with config key(s) and new value(s)',
                'current_orders': 'Optional list of current orders for impact analysis',
                'validation_mode': 'Validation strictness (strict or permissive)'
            },
            'output_format': {
                'config_key': 'Primary configuration key updated',
                'update_successful': 'Whether update was successful',
                'changes_applied': 'List of configuration changes that were applied',
                'affected_orders': 'List of order IDs affected by configuration change',
                'restart_required': 'Whether service restart is required',
                'validation_errors': 'List of validation errors encountered',
                'rollback_available': 'Whether rollback is possible',
                'update_timestamp': 'Update processing timestamp'
            },
            'config_categories': self.config_categories,
            'supported_validators': list(self.config_validators.keys()),
            'validation_modes': ['strict', 'permissive'],
            'change_types': ['create', 'update', 'delete'],
            'rollback_stack_size': len(self.rollback_stack),
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_config_statistics(self) -> Dict[str, Any]:
        """Configuration Management Statistiken abrufen"""
        total_config_keys = len(self.current_config)
        total_updates = self.config_update_counter
        
        # History Statistics
        keys_with_history = len(self.config_history)
        total_historical_changes = sum(len(changes) for changes in self.config_history.values())
        
        # Most Changed Configs
        change_counts = {
            key: len(changes) for key, changes in self.config_history.items()
        }
        most_changed = sorted(change_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_config_keys': total_config_keys,
            'total_config_updates': total_updates,
            'config_categories_count': len(self.config_categories),
            'keys_with_history': keys_with_history,
            'total_historical_changes': total_historical_changes,
            'most_changed_configs': dict(most_changed),
            'rollback_points_available': len(self.rollback_stack),
            'validators_registered': len(self.config_validators),
            'average_processing_time': self.average_execution_time,
            'current_config_snapshot': self.current_config

    async def _setup_event_subscriptions(self):
        """Setup Event-Bus Subscriptions for Order Module"""
        try:
            # Subscribe to system health requests
            await self.event_bus.subscribe('system.health.request', self.process_event)
            
            # Subscribe to module-specific order events
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('order.status.request', self.process_event)
            await self.event_bus.subscribe('order.update', self.process_event)
            
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
                        'execution_count': len(self.execution_history),
                        'average_execution_time_ms': self.average_execution_time,
                        'orders_processed': getattr(self, 'orders_processed', 0),
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
            
            elif event_type == 'order.status.request':
                # Order status request
                order_id = event.get('data', {}).get('order_id')
                if order_id and hasattr(self, 'get_order_status'):
                    status = self.get_order_status(order_id)
                    status_response = {
                        'event_type': 'order.status.response',
                        'stream_id': event.get('stream_id', 'order-status'),
                        'data': {
                            'order_id': order_id,
                            'status': status,
                            'module': self.module_name
                        },
                        'source': self.module_name,
                        'correlation_id': event.get('correlation_id')
                    }
                    await self.event_bus.publish(status_response)
            
            else:
                self.logger.debug("Unhandled event type",
                                event_type=event_type, module=self.module_name)
                
        except Exception as e:
            self.logger.error("Failed to process event",
                            error=str(e), event=str(event), module=self.module_name)

    async def publish_order_event(self, event_type: str, order_data: dict):
        """Publish order-related events"""
        if not self.event_bus:
            return
            
        try:
            order_event = {
                'event_type': event_type,
                'stream_id': f'order-{order_data.get("order_id", "unknown")}',
                'data': {
                    **order_data,
                    'timestamp': datetime.now().isoformat(),
                    'processing_module': self.module_name
                },
                'source': self.module_name
            }
            await self.event_bus.publish(order_event)
            
        except Exception as e:
            self.logger.error("Failed to publish order event",
                            error=str(e), event_type=event_type)
        }