"""
Order Validation Module - Single Function Module
Verantwortlich ausschließlich für Order Validation Logic
"""

import asyncio
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from ..single_function_module_base import SingleFunctionModule
from .order_placement_module import OrderRequest, OrderSide, OrderType


class ValidationError(BaseModel):
    field: str
    error: str
    severity: str  # 'error', 'warning', 'info'


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    risk_score: float  # 0.0 = low risk, 1.0 = high risk


class OrderValidationModule(SingleFunctionModule):
    """
    Single Function Module: Order Validation
    Verantwortlichkeit: Ausschließlich Order-Validations-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_validation", event_bus)
        
        # Validation Rules Configuration
        self.min_order_amounts = {
            'BTC_EUR': '0.0001',
            'ETH_EUR': '0.001', 
            'ADA_EUR': '1.0',
            'DOT_EUR': '0.1'
        }
        
        self.max_order_amounts = {
            'BTC_EUR': '10.0',
            'ETH_EUR': '100.0',
            'ADA_EUR': '100000.0',
            'DOT_EUR': '10000.0'
        }
        
        self.daily_order_limit = Decimal('50000.0')  # EUR
        self.single_order_limit = Decimal('10000.0')  # EUR
        
        # Risk Assessment Weights
        self.risk_weights = {
            'amount_risk': 0.4,
            'volatility_risk': 0.3,
            'liquidity_risk': 0.2,
            'timing_risk': 0.1
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Order Validation
        
        Args:
            input_data: {
                'order_request': OrderRequest dict,
                'account_info': Optional account information,
                'market_conditions': Optional market data
            }
            
        Returns:
            Dict mit Validation-Result
        """
        order_request_data = input_data.get('order_request')
        account_info = input_data.get('account_info', {})
        market_conditions = input_data.get('market_conditions', {})
        
        if not order_request_data:
            raise ValueError('No order request provided for validation')
        
        # OrderRequest parsieren
        try:
            order_request = OrderRequest(**order_request_data)
        except Exception as e:
            raise ValueError(f'Invalid order request format: {str(e)}')
        
        # Vollständige Validierung durchführen
        validation_result = await self._validate_order_comprehensive(
            order_request, account_info, market_conditions
        )
        
        return {
            'is_valid': validation_result.is_valid,
            'errors': [error.dict() for error in validation_result.errors],
            'warnings': [warning.dict() for warning in validation_result.warnings],
            'risk_score': validation_result.risk_score,
            'validation_timestamp': datetime.now().isoformat(),
            'order_summary': {
                'instrument': order_request.instrument_code,
                'side': order_request.side.value,
                'amount': order_request.amount,
                'type': order_request.type.value
            }
        }
    
    async def _validate_order_comprehensive(self, order_request: OrderRequest, 
                                          account_info: Dict, 
                                          market_conditions: Dict) -> ValidationResult:
        """Umfassende Order-Validierung"""
        errors = []
        warnings = []
        
        # 1. Basic Format Validation
        format_errors = await self._validate_format(order_request)
        errors.extend(format_errors)
        
        # 2. Amount Validation
        amount_errors, amount_warnings = await self._validate_amount(order_request)
        errors.extend(amount_errors)
        warnings.extend(amount_warnings)
        
        # 3. Price Validation
        price_errors, price_warnings = await self._validate_price(order_request)
        errors.extend(price_errors)
        warnings.extend(price_warnings)
        
        # 4. Account Balance Validation
        if account_info:
            balance_errors = await self._validate_account_balance(order_request, account_info)
            errors.extend(balance_errors)
        
        # 5. Risk Assessment
        risk_score = await self._calculate_risk_score(order_request, market_conditions)
        
        # 6. Market Conditions Check
        if market_conditions:
            market_warnings = await self._validate_market_conditions(order_request, market_conditions)
            warnings.extend(market_warnings)
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            risk_score=risk_score
        )
    
    async def _validate_format(self, order_request: OrderRequest) -> List[ValidationError]:
        """Format-Validierung der Order-Parameter"""
        errors = []
        
        # Instrument Code Validation
        if not order_request.instrument_code or '_' not in order_request.instrument_code:
            errors.append(ValidationError(
                field='instrument_code',
                error='Invalid instrument code format. Expected format: BASE_QUOTE (e.g., BTC_EUR)',
                severity='error'
            ))
        
        # Amount Format Validation
        try:
            amount_decimal = Decimal(order_request.amount)
            if amount_decimal <= 0:
                errors.append(ValidationError(
                    field='amount',
                    error='Order amount must be greater than zero',
                    severity='error'
                ))
        except (InvalidOperation, ValueError):
            errors.append(ValidationError(
                field='amount',
                error='Invalid amount format. Must be a valid decimal number',
                severity='error'
            ))
        
        # Price Format Validation (für LIMIT orders)
        if order_request.type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and order_request.price:
            try:
                price_decimal = Decimal(order_request.price)
                if price_decimal <= 0:
                    errors.append(ValidationError(
                        field='price',
                        error='Order price must be greater than zero',
                        severity='error'
                    ))
            except (InvalidOperation, ValueError):
                errors.append(ValidationError(
                    field='price',
                    error='Invalid price format. Must be a valid decimal number',
                    severity='error'
                ))
        
        return errors
    
    async def _validate_amount(self, order_request: OrderRequest) -> tuple[List[ValidationError], List[ValidationError]]:
        """Order-Amount-Validierung"""
        errors = []
        warnings = []
        
        instrument = order_request.instrument_code
        amount = Decimal(order_request.amount)
        
        # Minimum Amount Check
        min_amount = Decimal(self.min_order_amounts.get(instrument, '0.001'))
        if amount < min_amount:
            errors.append(ValidationError(
                field='amount',
                error=f'Amount {amount} below minimum {min_amount} for {instrument}',
                severity='error'
            ))
        
        # Maximum Amount Check
        max_amount = Decimal(self.max_order_amounts.get(instrument, '1000000'))
        if amount > max_amount:
            errors.append(ValidationError(
                field='amount',
                error=f'Amount {amount} exceeds maximum {max_amount} for {instrument}',
                severity='error'
            ))
        
        # Large Order Warning
        if amount > max_amount * Decimal('0.5'):
            warnings.append(ValidationError(
                field='amount',
                error=f'Large order detected: {amount}. Consider splitting into smaller orders.',
                severity='warning'
            ))
        
        return errors, warnings
    
    async def _validate_price(self, order_request: OrderRequest) -> tuple[List[ValidationError], List[ValidationError]]:
        """Price-Validierung"""
        errors = []
        warnings = []
        
        # Nur für LIMIT und STOP_LIMIT Orders
        if order_request.type not in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            return errors, warnings
        
        if not order_request.price:
            errors.append(ValidationError(
                field='price',
                error=f'Price required for {order_request.type.value} orders',
                severity='error'
            ))
            return errors, warnings
        
        # Price Reasonableness Check (würde normalerweise Current Market Price verwenden)
        # Simulation: Warnung bei extrem hohen/niedrigen Preisen
        price = Decimal(order_request.price)
        
        # Beispiel-Marktpreise für Validierung
        market_prices = {
            'BTC_EUR': Decimal('45000'),
            'ETH_EUR': Decimal('2500'),
            'ADA_EUR': Decimal('0.50'),
            'DOT_EUR': Decimal('25.00')
        }
        
        instrument = order_request.instrument_code
        if instrument in market_prices:
            market_price = market_prices[instrument]
            
            # Price Deviation Check
            deviation = abs(price - market_price) / market_price
            
            if deviation > 0.1:  # 10% Abweichung
                warnings.append(ValidationError(
                    field='price',
                    error=f'Price {price} deviates {deviation:.1%} from market price {market_price}',
                    severity='warning'
                ))
            
            if deviation > 0.5:  # 50% Abweichung
                errors.append(ValidationError(
                    field='price',
                    error=f'Price {price} deviates {deviation:.1%} from market price. Possible error.',
                    severity='error'
                ))
        
        return errors, warnings
    
    async def _validate_account_balance(self, order_request: OrderRequest, account_info: Dict) -> List[ValidationError]:
        """Account Balance Validation"""
        errors = []
        
        # Simulierte Account Balance Validation
        available_balance = Decimal(account_info.get('available_balance', '0'))
        order_value = Decimal(order_request.amount)
        
        if order_request.side == OrderSide.BUY:
            # Für BUY Orders: Genügend Quote Currency (EUR)
            estimated_cost = order_value * Decimal(order_request.price or '50000')  # Fallback Price
            
            if estimated_cost > available_balance:
                errors.append(ValidationError(
                    field='amount',
                    error=f'Insufficient balance. Required: {estimated_cost}, Available: {available_balance}',
                    severity='error'
                ))
        
        return errors
    
    async def _validate_market_conditions(self, order_request: OrderRequest, market_conditions: Dict) -> List[ValidationError]:
        """Market Conditions Validation"""
        warnings = []
        
        # Beispiel Market Conditions Checks
        volatility = market_conditions.get('volatility', 0)
        if volatility > 0.05:  # 5% Volatilität
            warnings.append(ValidationError(
                field='market_conditions',
                error=f'High market volatility detected: {volatility:.1%}. Consider timing.',
                severity='warning'
            ))
        
        return warnings
    
    async def _calculate_risk_score(self, order_request: OrderRequest, market_conditions: Dict) -> float:
        """Risk Score Berechnung (0.0 = niedrig, 1.0 = hoch)"""
        
        # Amount Risk (basiert auf Order-Größe)
        amount = Decimal(order_request.amount)
        max_amount = Decimal(self.max_order_amounts.get(order_request.instrument_code, '1000'))
        amount_risk = min(float(amount / max_amount), 1.0)
        
        # Volatility Risk (basiert auf Market Conditions)
        volatility_risk = market_conditions.get('volatility', 0.02)
        
        # Liquidity Risk (basiert auf Instrument)
        liquidity_risk = 0.1 if order_request.instrument_code.startswith('BTC') else 0.3
        
        # Timing Risk (basiert auf Order Type)
        timing_risk = 0.1 if order_request.type == OrderType.MARKET else 0.3
        
        # Gewichteter Risk Score
        total_risk = (
            self.risk_weights['amount_risk'] * amount_risk +
            self.risk_weights['volatility_risk'] * volatility_risk +
            self.risk_weights['liquidity_risk'] * liquidity_risk +
            self.risk_weights['timing_risk'] * timing_risk
        )
        
        return min(total_risk, 1.0)
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_validation',
            'description': 'Validates trading orders for compliance and risk',
            'responsibility': 'Order validation logic only',
            'input_parameters': {
                'order_request': 'OrderRequest object to validate',
                'account_info': 'Optional account balance information',
                'market_conditions': 'Optional market data for risk assessment'
            },
            'output_format': {
                'is_valid': 'Boolean validation result',
                'errors': 'List of validation errors',
                'warnings': 'List of validation warnings',
                'risk_score': 'Risk assessment score (0.0-1.0)',
                'validation_timestamp': 'Validation execution time'
            },
            'validation_rules': {
                'min_amounts': self.min_order_amounts,
                'max_amounts': self.max_order_amounts,
                'daily_limit': str(self.daily_order_limit),
                'single_order_limit': str(self.single_order_limit)
            },
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'

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