from typing import Dict, Any, Optional
from decimal import Decimal
import sys
from shared.common_imports import (
import asyncio
from ..single_function_module_base import SingleFunctionModule
"""
Transaction Processing Module - Single Function Module
Verantwortlich ausschließlich für Transaction Processing Logic
"""

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

    datetime, BaseModel, structlog
)


class TransactionRequest(BaseModel):
    transaction_type: str  # trade_buy, trade_sell, deposit, withdrawal, fee, lock, unlock
    currency_code: str
    amount: str
    description: Optional[str] = None
    order_id: Optional[str] = None
    fee_amount: Optional[str] = None
    reference_id: Optional[str] = None


class ProcessedTransaction(BaseModel):
    transaction_id: str
    transaction_type: str
    currency_code: str
    amount: str
    amount_float: float
    balance_before: Dict[str, str]
    balance_after: Dict[str, str]
    fee_amount: Optional[str] = None
    description: str
    timestamp: datetime
    order_id: Optional[str] = None
    processing_time_ms: float
    validation_passed: bool
    validation_warnings: List[str] = []


class TransactionProcessingModule(SingleFunctionModule):
    """
    Single Function Module: Transaction Processing
    Verantwortlichkeit: Ausschließlich Transaction-Processing-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("transaction_processing", event_bus)
        
        # Account Balances (normalerweise aus Account Service)
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
        
        # Transaction Processing History
        self.processed_transactions = []
        self.processing_counter = 0
        self.failed_transactions = []
        
        # Processing Rules
        self.transaction_rules = {
            'min_transaction_amount': {
                'EUR': 0.01,
                'USD': 0.01,
                'BTC': 0.00001,
                'ETH': 0.0001
            },
            'max_transaction_amount': {
                'EUR': 100000.0,
                'USD': 100000.0,
                'BTC': 10.0,
                'ETH': 100.0
            },
            'fee_rates': {
                'trade_buy': 0.001,  # 0.1%
                'trade_sell': 0.001, # 0.1%
                'withdrawal': 0.005, # 0.5%
                'deposit': 0.0      # No fee
            }
        }
        
        # Supported Transaction Types
        self.supported_transaction_types = [
            'trade_buy', 'trade_sell', 'deposit', 'withdrawal', 
            'fee', 'lock', 'unlock'
        ]
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Transaction Processing
        
        Args:
            input_data: {
                'transaction_type': required string,
                'currency_code': required string,
                'amount': required string,
                'description': optional string,
                'order_id': optional string,
                'fee_amount': optional string,
                'reference_id': optional string,
                'validate_only': optional bool (default: false)
            }
            
        Returns:
            Dict mit Transaction-Processing-Result
        """
        start_time = datetime.now()
        validate_only = input_data.get('validate_only', False)
        
        # Transaction Request erstellen
        try:
            transaction_request = TransactionRequest(
                transaction_type=input_data.get('transaction_type'),
                currency_code=input_data.get('currency_code'),
                amount=input_data.get('amount'),
                description=input_data.get('description'),
                order_id=input_data.get('order_id'),
                fee_amount=input_data.get('fee_amount'),
                reference_id=input_data.get('reference_id')
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Invalid transaction request: {str(e)}',
                'validation_errors': [str(e)]
            }
        
        # Transaction Processing
        processing_result = await self._process_transaction_request(
            transaction_request, validate_only, start_time
        )
        
        # Statistics Update
        self.processing_counter += 1
        
        if processing_result['success']:
            if not validate_only:
                # Add to processed transactions history
                self.processed_transactions.append(processing_result['transaction'])
                
                # Limit history to prevent memory issues
                if len(self.processed_transactions) > 1000:
                    self.processed_transactions.pop(0)
            
            self.logger.info(f"Transaction processed successfully",
                           transaction_id=processing_result['transaction']['transaction_id'],
                           type=transaction_request.transaction_type,
                           currency=transaction_request.currency_code,
                           amount=transaction_request.amount,
                           validate_only=validate_only)
        else:
            # Add to failed transactions
            self.failed_transactions.append({
                'request': transaction_request.dict(),
                'error': processing_result['error'],
                'timestamp': datetime.now(),
                'processing_id': self.processing_counter
            })
            
            # Limit failed transactions history
            if len(self.failed_transactions) > 200:
                self.failed_transactions.pop(0)
        
        return processing_result
    
    async def _process_transaction_request(self, request: TransactionRequest, 
                                         validate_only: bool,
                                         start_time: datetime) -> Dict[str, Any]:
        """Verarbeitet Transaction Request"""
        
        # Validation Phase
        validation_result = await self._validate_transaction_request(request)
        
        if not validation_result['valid']:
            return {
                'success': False,
                'error': 'Transaction validation failed',
                'validation_errors': validation_result['errors'],
                'validation_warnings': validation_result['warnings']
            }
        
        # Nur Validation gewünscht
        if validate_only:
            return {
                'success': True,
                'validation_only': True,
                'validation_passed': True,
                'validation_warnings': validation_result['warnings'],
                'estimated_balance_after': validation_result['estimated_balance_after']
            }
        
        # Transaction ID generieren
        transaction_id = f"TXN_{int(datetime.now().timestamp())}_{self.processing_counter:06d}"
        
        # Balance Before Snapshot
        currency_code = request.currency_code.upper()
        balance_before = self.account_balances.get(currency_code, {
            'available': '0.00', 'locked': '0.00', 'total': '0.00'
        })
        
        # Transaction Processing
        try:
            new_balance = await self._execute_transaction_logic(request, balance_before)
        except Exception as e:
            return {
                'success': False,
                'error': f'Transaction execution failed: {str(e)}',
                'transaction_id': transaction_id
            }
        
        # Balance Update
        self.account_balances[currency_code] = {
            'available': new_balance['available'],
            'locked': new_balance['locked'],
            'total': new_balance['total'],
            'last_updated': datetime.now()
        }
        
        # Processing Time
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Processed Transaction erstellen
        processed_transaction = ProcessedTransaction(
            transaction_id=transaction_id,
            transaction_type=request.transaction_type,
            currency_code=currency_code,
            amount=request.amount,
            amount_float=float(request.amount),
            balance_before={
                'available': balance_before['available'],
                'locked': balance_before['locked'],
                'total': balance_before['total']
            },
            balance_after=new_balance,
            fee_amount=request.fee_amount,
            description=request.description or f"{request.transaction_type.title()} transaction",
            timestamp=datetime.now(),
            order_id=request.order_id,
            processing_time_ms=round(processing_time_ms, 2),
            validation_passed=True,
            validation_warnings=validation_result['warnings']
        )
        
        # Event Publishing für signifikante Transaktionen
        if abs(float(request.amount)) > 100:  # Significant transaction
            await self._publish_transaction_event(processed_transaction)
        
        return {
            'success': True,
            'transaction': processed_transaction.dict(),
            'updated_balance': new_balance
        }
    
    async def _validate_transaction_request(self, request: TransactionRequest) -> Dict[str, Any]:
        """Validiert Transaction Request"""
        
        errors = []
        warnings = []
        currency_code = request.currency_code.upper()
        
        # Transaction Type Validation
        if request.transaction_type not in self.supported_transaction_types:
            errors.append(f'Unsupported transaction type: {request.transaction_type}')
        
        # Currency Code Validation
        if not currency_code or len(currency_code) < 3 or not currency_code.isalpha():
            errors.append(f'Invalid currency code: {request.currency_code}')
        
        # Amount Validation
        try:
            amount_float = float(request.amount)
            if amount_float <= 0:
                errors.append('Transaction amount must be positive')
        except (ValueError, TypeError):
            errors.append('Invalid amount format')
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        # Amount Range Validation
        min_amount = self.transaction_rules['min_transaction_amount'].get(currency_code, 0.01)
        max_amount = self.transaction_rules['max_transaction_amount'].get(currency_code, 1000000.0)
        
        if amount_float < min_amount:
            errors.append(f'Amount below minimum: {min_amount} {currency_code}')
        
        if amount_float > max_amount:
            errors.append(f'Amount exceeds maximum: {max_amount} {currency_code}')
        
        # Balance Validation
        balance_validation = await self._validate_balance_requirements(request, amount_float)
        if balance_validation['errors']:
            errors.extend(balance_validation['errors'])
        if balance_validation['warnings']:
            warnings.extend(balance_validation['warnings'])
        
        # Fee Validation
        if request.fee_amount:
            try:
                fee_float = float(request.fee_amount)
                if fee_float < 0:
                    errors.append('Fee amount cannot be negative')
                elif fee_float > amount_float:
                    warnings.append('Fee amount exceeds transaction amount')
            except (ValueError, TypeError):
                errors.append('Invalid fee amount format')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'estimated_balance_after': balance_validation.get('estimated_balance_after', {})
        }
    
    async def _validate_balance_requirements(self, request: TransactionRequest, 
                                           amount_float: float) -> Dict[str, Any]:
        """Validiert Balance Requirements für Transaction"""
        
        errors = []
        warnings = []
        currency_code = request.currency_code.upper()
        
        # Current Balance abrufen
        current_balance = self.account_balances.get(currency_code)
        
        if not current_balance and request.transaction_type in ['trade_buy', 'withdrawal', 'fee', 'lock']:
            errors.append(f'No {currency_code} balance found')
            return {'errors': errors, 'warnings': warnings}
        
        if not current_balance:
            # Neue Currency Balance erstellen für deposit/trade_sell
            estimated_balance_after = {
                'available': str(amount_float),
                'locked': '0.00',
                'total': str(amount_float)
            }
            return {
                'errors': errors, 
                'warnings': warnings,
                'estimated_balance_after': estimated_balance_after
            }
        
        current_available = float(current_balance['available'])
        current_locked = float(current_balance['locked'])
        current_total = float(current_balance['total'])
        
        # Balance Requirements je Transaction Type
        if request.transaction_type in ['trade_buy', 'withdrawal', 'fee']:
            if amount_float > current_available:
                errors.append(f'Insufficient {currency_code} balance. Available: {current_available}, Required: {amount_float}')
            elif amount_float > current_available * 0.9:
                warnings.append(f'Transaction uses >90% of available {currency_code} balance')
        
        elif request.transaction_type == 'lock':
            if amount_float > current_available:
                errors.append(f'Insufficient available {currency_code} to lock. Available: {current_available}, Required: {amount_float}')
        
        elif request.transaction_type == 'unlock':
            if amount_float > current_locked:
                errors.append(f'Cannot unlock more than locked amount. Locked: {current_locked}, Requested: {amount_float}')
        
        # Estimated Balance After
        estimated_balance_after = self._calculate_estimated_balance_after(
            request, current_balance, amount_float
        )
        
        return {
            'errors': errors,
            'warnings': warnings,
            'estimated_balance_after': estimated_balance_after
        }
    

        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())

    def _calculate_estimated_balance_after(self, request: TransactionRequest, 
                                         current_balance: Dict[str, str],
                                         amount_float: float) -> Dict[str, str]:
        """Berechnet geschätzte Balance nach Transaction"""
        
        current_available = float(current_balance['available'])
        current_locked = float(current_balance['locked'])
        current_total = float(current_balance['total'])
        
        new_available = current_available
        new_locked = current_locked
        new_total = current_total
        
        # Transaction Type Logic
        if request.transaction_type == 'trade_buy':
            new_available -= amount_float
            new_total -= amount_float
        
        elif request.transaction_type == 'trade_sell':
            new_available += amount_float
            new_total += amount_float
        
        elif request.transaction_type == 'deposit':
            new_available += amount_float
            new_total += amount_float
        
        elif request.transaction_type == 'withdrawal':
            new_available -= amount_float
            new_total -= amount_float
        
        elif request.transaction_type == 'fee':
            new_available -= amount_float
            new_total -= amount_float
        
        elif request.transaction_type == 'lock':
            new_available -= amount_float
            new_locked += amount_float
        
        elif request.transaction_type == 'unlock':
            new_available += amount_float
            new_locked -= amount_float
        
        return {
            'available': f"{max(0, new_available):.8f}".rstrip('0').rstrip('.'),
            'locked': f"{max(0, new_locked):.8f}".rstrip('0').rstrip('.'),
            'total': f"{max(0, new_total):.8f}".rstrip('0').rstrip('.')
        }
    
    async def _execute_transaction_logic(self, request: TransactionRequest, 
                                       balance_before: Dict[str, str]) -> Dict[str, str]:
        """Führt Transaction Logic aus"""
        
        amount_float = float(request.amount)
        current_available = float(balance_before['available'])
        current_locked = float(balance_before['locked'])
        current_total = float(balance_before['total'])
        
        # Transaction Logic je Type
        if request.transaction_type == 'trade_buy':
            new_available = current_available - amount_float
            new_total = current_total - amount_float
            new_locked = current_locked
        
        elif request.transaction_type == 'trade_sell':
            new_available = current_available + amount_float
            new_total = current_total + amount_float
            new_locked = current_locked
        
        elif request.transaction_type == 'deposit':
            new_available = current_available + amount_float
            new_total = current_total + amount_float
            new_locked = current_locked
        
        elif request.transaction_type == 'withdrawal':
            new_available = current_available - amount_float
            new_total = current_total - amount_float
            new_locked = current_locked
        
        elif request.transaction_type == 'fee':
            new_available = max(0, current_available - amount_float)
            new_total = current_total - amount_float
            new_locked = current_locked
        
        elif request.transaction_type == 'lock':
            new_available = current_available - amount_float
            new_locked = current_locked + amount_float
            new_total = current_total
        
        elif request.transaction_type == 'unlock':
            new_available = current_available + amount_float
            new_locked = max(0, current_locked - amount_float)
            new_total = current_total
        
        else:
            raise ValueError(f'Unknown transaction type: {request.transaction_type}')
        
        return {
            'available': f"{max(0, new_available):.8f}".rstrip('0').rstrip('.'),
            'locked': f"{max(0, new_locked):.8f}".rstrip('0').rstrip('.'),
            'total': f"{max(0, new_total):.8f}".rstrip('0').rstrip('.')
        }
    
    async def _publish_transaction_event(self, transaction: ProcessedTransaction):
        """Publisht Transaction Event über Event-Bus"""
        if not self.event_bus or not self.event_bus.connected:
            return
        
        from event_bus import Event
        
        event = Event(
            event_type="account_transaction_processed",
            stream_id=f"transaction-{transaction.transaction_id}",
            data={
                'transaction_id': transaction.transaction_id,
                'transaction_type': transaction.transaction_type,
                'currency_code': transaction.currency_code,
                'amount': transaction.amount,
                'balance_after': transaction.balance_after,
                'order_id': transaction.order_id,
                'processing_time_ms': transaction.processing_time_ms,
                'timestamp': transaction.timestamp.isoformat()
            },
            source="transaction_processing"
        )
        
        await self.event_bus.publish(event)
    
    def get_account_balance(self, currency_code: str) -> Optional[Dict[str, str]]:
        """Gibt aktuelle Account Balance zurück"""
        return self.account_balances.get(currency_code.upper())
    
    def get_processing_rules(self) -> Dict[str, Any]:
        """Gibt Processing Rules zurück"""
        return self.transaction_rules.copy()
    
    def update_processing_rules(self, rules_update: Dict[str, Any]):
        """Aktualisiert Processing Rules"""
        for rule_category, rule_values in rules_update.items():
            if rule_category in self.transaction_rules:
                self.transaction_rules[rule_category].update(rule_values)
                self.logger.info(f"Processing rules updated",
                               category=rule_category,
                               updated_values=list(rule_values.keys()))
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'transaction_processing',
            'description': 'Processes account transactions with validation and balance updates',
            'responsibility': 'Transaction processing logic only',
            'input_parameters': {
                'transaction_type': 'Type of transaction to process',
                'currency_code': 'Currency code for transaction',
                'amount': 'Transaction amount as string',
                'description': 'Optional transaction description',
                'order_id': 'Optional order ID for trade transactions',
                'fee_amount': 'Optional fee amount',
                'reference_id': 'Optional reference ID',
                'validate_only': 'Only validate without processing (default: false)'
            },
            'output_format': {
                'transaction': 'Processed transaction details',
                'updated_balance': 'Balance after transaction processing',
                'validation_errors': 'List of validation errors if any',
                'validation_warnings': 'List of validation warnings if any'
            },
            'supported_transaction_types': self.supported_transaction_types,
            'processing_rules': self.transaction_rules,
            'supported_currencies': list(self.account_balances.keys()),
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_transaction_statistics(self) -> Dict[str, Any]:
        """Transaction Processing Statistiken"""
        total_processed = len(self.processed_transactions)
        total_failed = len(self.failed_transactions)
        total_requests = total_processed + total_failed
        
        if total_requests == 0:
            return {
                'total_requests': 0,
                'success_rate': 0.0,
                'supported_currencies': len(self.account_balances)
            }
        
        # Success Rate
        success_rate = round(total_processed / total_requests * 100, 1) if total_requests > 0 else 0
        
        # Transaction Type Distribution
        type_distribution = {}
        for txn in self.processed_transactions:
            tx_type = txn['transaction_type']
            type_distribution[tx_type] = type_distribution.get(tx_type, 0) + 1
        
        # Currency Distribution
        currency_distribution = {}
        for txn in self.processed_transactions:
            currency = txn['currency_code']
            currency_distribution[currency] = currency_distribution.get(currency, 0) + 1
        
        # Average Processing Time
        processing_times = [txn['processing_time_ms'] for txn in self.processed_transactions]
        avg_processing_time = round(sum(processing_times) / len(processing_times), 2) if processing_times else 0
        
        return {
            'total_requests': total_requests,
            'total_processed': total_processed,
            'total_failed': total_failed,
            'success_rate_percent': success_rate,
            'transaction_type_distribution': type_distribution,
            'currency_distribution': currency_distribution,
            'average_processing_time_ms': avg_processing_time,
            'supported_currencies': len(self.account_balances),
            'supported_transaction_types': len(self.supported_transaction_types),
            'average_execution_time': self.average_execution_time
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
