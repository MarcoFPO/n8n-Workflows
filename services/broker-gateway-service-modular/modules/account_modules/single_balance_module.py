from typing import Dict, Any, Optional
import sys
from shared.common_imports import (
import asyncio
from ..single_function_module_base import SingleFunctionModule
"""
Single Balance Module - Single Function Module
Verantwortlich ausschließlich für Single Currency Balance Retrieval Logic
"""

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

    datetime, BaseModel, structlog
)


class SingleBalanceResult(BaseModel):
    currency_code: str
    available: str
    locked: str
    total: str
    available_float: float
    locked_float: float
    total_float: float
    last_updated: datetime
    balance_age_seconds: float
    retrieval_timestamp: datetime


class SingleBalanceModule(SingleFunctionModule):
    """
    Single Function Module: Single Balance Retrieval
    Verantwortlichkeit: Ausschließlich Single-Currency-Balance-Retrieval-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("single_balance", event_bus)
        
        # Balance Data (normalerweise aus Account Service/DB)
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
        
        # Single Balance Retrieval Statistics
        self.retrieval_history = []
        self.retrieval_counter = 0
        self.currency_access_counts = {}
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Single Currency Balance Retrieval
        
        Args:
            input_data: {
                'currency_code': required string - currency to retrieve,
                'include_age_info': optional bool (default: true),
                'validate_currency': optional bool (default: true)
            }
            
        Returns:
            Dict mit Single-Balance-Result
        """
        currency_code = input_data.get('currency_code')
        include_age_info = input_data.get('include_age_info', True)
        validate_currency = input_data.get('validate_currency', True)
        
        if not currency_code:
            raise ValueError('No currency code provided')
        
        # Currency Code normalisieren
        currency_code = currency_code.upper()
        
        # Validation
        if validate_currency and not self._is_valid_currency_code(currency_code):
            raise ValueError(f'Invalid currency code format: {currency_code}')
        
        # Balance Retrieval
        balance_result = await self._retrieve_single_balance(currency_code, include_age_info)
        
        # Statistics Update
        self.retrieval_counter += 1
        self.currency_access_counts[currency_code] = self.currency_access_counts.get(currency_code, 0) + 1
        
        # History Update
        self.retrieval_history.append({
            'timestamp': datetime.now(),
            'currency_code': currency_code,
            'balance_found': balance_result is not None,
            'retrieval_id': self.retrieval_counter
        })
        
        # Limit History
        if len(self.retrieval_history) > 200:
            self.retrieval_history.pop(0)
        
        if not balance_result:
            self.logger.warning(f"Balance not found for currency",
                              currency_code=currency_code,
                              retrieval_id=self.retrieval_counter)
            
            return {
                'success': False,
                'error': f'Currency {currency_code} not found in account',
                'currency_code': currency_code,
                'available_currencies': list(self.account_balances.keys())
            }
        
        self.logger.info(f"Single balance retrieved successfully",
                       currency_code=currency_code,
                       available=balance_result.available,
                       total=balance_result.total,
                       retrieval_id=self.retrieval_counter)
        
        return {
            'success': True,
            'balance': {
                'currency_code': balance_result.currency_code,
                'available': balance_result.available,
                'locked': balance_result.locked,
                'total': balance_result.total,
                'available_float': balance_result.available_float,
                'locked_float': balance_result.locked_float,
                'total_float': balance_result.total_float,
                'last_updated': balance_result.last_updated.isoformat(),
                'balance_age_seconds': balance_result.balance_age_seconds if include_age_info else None,
                'retrieval_timestamp': balance_result.retrieval_timestamp.isoformat()
            }
        }
    
    async def _retrieve_single_balance(self, currency_code: str, 
                                     include_age_info: bool) -> Optional[SingleBalanceResult]:
        """Retrieves Balance für spezifische Currency"""
        
        if currency_code not in self.account_balances:
            return None
        
        balance_data = self.account_balances[currency_code]
        
        # Balance Age berechnen
        balance_age_seconds = 0.0
        if include_age_info and balance_data.get('last_updated'):
            balance_age_seconds = (datetime.now() - balance_data['last_updated']).total_seconds()
        
        # Balance Result erstellen
        result = SingleBalanceResult(
            currency_code=currency_code,
            available=balance_data['available'],
            locked=balance_data['locked'],
            total=balance_data['total'],
            available_float=float(balance_data['available']),
            locked_float=float(balance_data['locked']),
            total_float=float(balance_data['total']),
            last_updated=balance_data['last_updated'],
            balance_age_seconds=balance_age_seconds,
            retrieval_timestamp=datetime.now()
        )
        
        return result
    

        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())

    def _is_valid_currency_code(self, currency_code: str) -> bool:
        """Validiert Currency Code Format"""
        if not currency_code or not isinstance(currency_code, str):
            return False
        
        # Basic validation: 3-4 characters, alphanumeric
        if len(currency_code) < 3 or len(currency_code) > 4:
            return False
        
        if not currency_code.isalpha():
            return False
        
        return True
    
    def update_balance(self, currency_code: str, available: str, 
                      locked: str = "0.00", total: str = None):
        """Updates Balance für Currency (externe Updates)"""
        currency_code = currency_code.upper()
        
        if total is None:
            total = str(float(available) + float(locked))
        
        self.account_balances[currency_code] = {
            'available': available,
            'locked': locked,
            'total': total,
            'last_updated': datetime.now()
        }
        
        self.logger.info(f"Balance updated for currency",
                       currency_code=currency_code,
                       available=available,
                       locked=locked,
                       total=total)
    
    def remove_currency(self, currency_code: str):
        """Entfernt Currency aus Balances"""
        currency_code = currency_code.upper()
        
        if currency_code in self.account_balances:
            del self.account_balances[currency_code]
            self.logger.info(f"Currency removed from balances",
                           currency_code=currency_code)
    
    def get_available_currencies(self) -> List[str]:
        """Gibt Liste verfügbarer Currencies zurück"""
        return list(self.account_balances.keys())
    
    def has_sufficient_balance(self, currency_code: str, required_amount: float) -> Dict[str, Any]:
        """Prüft ob ausreichend Balance vorhanden ist"""
        currency_code = currency_code.upper()
        
        if currency_code not in self.account_balances:
            return {
                'sufficient': False,
                'reason': f'Currency {currency_code} not found',
                'available': 0.0,
                'required': required_amount,
                'shortfall': required_amount
            }
        
        available = float(self.account_balances[currency_code]['available'])
        sufficient = available >= required_amount
        
        return {
            'sufficient': sufficient,
            'reason': 'Sufficient balance' if sufficient else 'Insufficient balance',
            'available': available,
            'required': required_amount,
            'shortfall': max(0, required_amount - available)
        }
    
    def get_most_accessed_currency(self) -> Optional[Dict[str, Any]]:
        """Gibt die meistabgefragte Currency zurück"""
        if not self.currency_access_counts:
            return None
        
        most_accessed = max(self.currency_access_counts.items(), key=lambda x: x[1])
        
        return {
            'currency_code': most_accessed[0],
            'access_count': most_accessed[1],
            'percentage_of_total': round(
                most_accessed[1] / sum(self.currency_access_counts.values()) * 100, 1
            )
        }
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'single_balance',
            'description': 'Retrieves balance information for a specific currency',
            'responsibility': 'Single currency balance retrieval logic only',
            'input_parameters': {
                'currency_code': 'Required currency code to retrieve balance for',
                'include_age_info': 'Whether to include balance age information (default: true)',
                'validate_currency': 'Whether to validate currency code format (default: true)'
            },
            'output_format': {
                'balance': {
                    'currency_code': 'Currency code',
                    'available': 'Available balance as string',
                    'locked': 'Locked balance as string', 
                    'total': 'Total balance as string',
                    'available_float': 'Available balance as float',
                    'locked_float': 'Locked balance as float',
                    'total_float': 'Total balance as float',
                    'last_updated': 'Balance last update timestamp',
                    'balance_age_seconds': 'Age of balance data in seconds',
                    'retrieval_timestamp': 'Balance retrieval timestamp'
                }
            },
            'supported_currencies': list(self.account_balances.keys()),
            'validation_rules': {
                'currency_code_length': '3-4 characters',
                'currency_code_format': 'Alphabetic characters only'
            },
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_balance_statistics(self) -> Dict[str, Any]:
        """Single Balance Retrieval Statistiken"""
        total_retrievals = len(self.retrieval_history)
        
        if total_retrievals == 0:
            return {
                'total_retrievals': 0,
                'supported_currencies': len(self.account_balances),
                'most_accessed_currency': None
            }
        
        # Success Rate
        successful_retrievals = sum(1 for r in self.retrieval_history if r['balance_found'])
        success_rate = round(successful_retrievals / total_retrievals * 100, 1) if total_retrievals > 0 else 0
        
        # Recent Activity
        recent_retrievals = [
            r for r in self.retrieval_history
            if (datetime.now() - r['timestamp']).seconds < 3600  # Last hour
        ]
        
        # Currency Distribution
        currency_distribution = {}
        for record in self.retrieval_history:
            currency = record['currency_code']
            currency_distribution[currency] = currency_distribution.get(currency, 0) + 1
        
        return {
            'total_retrievals': total_retrievals,
            'successful_retrievals': successful_retrievals,
            'success_rate_percent': success_rate,
            'recent_retrievals_last_hour': len(recent_retrievals),
            'supported_currencies': len(self.account_balances),
            'currency_access_distribution': dict(sorted(
                currency_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'most_accessed_currency': self.get_most_accessed_currency(),
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
