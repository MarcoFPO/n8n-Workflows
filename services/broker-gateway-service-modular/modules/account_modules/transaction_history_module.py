from typing import Dict, Any, List, Optional
import sys
from shared.common_imports import (
import asyncio
from ..single_function_module_base import SingleFunctionModule
"""
Transaction History Module - Single Function Module
Verantwortlich ausschließlich für Transaction History Retrieval Logic
"""

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

    datetime, timedelta, BaseModel, structlog
)


class Transaction(BaseModel):
    transaction_id: str
    type: str  # deposit, withdrawal, trade, fee, lock, unlock
    currency_code: str
    amount: str
    balance_after: str
    description: str
    timestamp: datetime
    order_id: Optional[str] = None
    fee_amount: Optional[str] = None


class TransactionFilter(BaseModel):
    currency_code: Optional[str] = None
    transaction_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    order_id: Optional[str] = None
    limit: int = 50


class TransactionHistoryResult(BaseModel):
    transactions: List[Dict[str, Any]]
    total_transactions: int
    filtered_count: int
    filters_applied: Dict[str, Any]
    summary_statistics: Dict[str, Any]
    retrieval_timestamp: datetime


class TransactionHistoryModule(SingleFunctionModule):
    """
    Single Function Module: Transaction History Retrieval
    Verantwortlichkeit: Ausschließlich Transaction-History-Retrieval-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("transaction_history", event_bus)
        
        # Transaction History Storage (normalerweise aus Database)
        self.transaction_history = [
            Transaction(
                transaction_id="TXN_INITIAL_DEPOSIT",
                type="deposit",
                currency_code="EUR",
                amount="10000.00",
                balance_after="10000.00",
                description="Initial deposit",
                timestamp=datetime.now() - timedelta(days=30)
            ),
            Transaction(
                transaction_id="TXN_BTC_PURCHASE_001",
                type="trade_buy",
                currency_code="EUR",
                amount="2000.00",
                balance_after="8000.00",
                description="BTC purchase",
                timestamp=datetime.now() - timedelta(days=25),
                order_id="ORD_BTC_001",
                fee_amount="10.00"
            ),
            Transaction(
                transaction_id="TXN_ETH_PURCHASE_001",
                type="trade_buy",
                currency_code="EUR",
                amount="1500.00",
                balance_after="6500.00",
                description="ETH purchase",
                timestamp=datetime.now() - timedelta(days=20),
                order_id="ORD_ETH_001",
                fee_amount="7.50"
            ),
            Transaction(
                transaction_id="TXN_WITHDRAWAL_001",
                type="withdrawal",
                currency_code="EUR",
                amount="500.00",
                balance_after="6000.00",
                description="Withdrawal to bank account",
                timestamp=datetime.now() - timedelta(days=15),
                fee_amount="2.50"
            )
        ]
        
        # History Retrieval Statistics
        self.retrieval_history = []
        self.retrieval_counter = 0
        self.filter_usage_stats = {}
        
        # Transaction Type Mappings
        self.transaction_types = {
            'deposit': 'Deposit',
            'withdrawal': 'Withdrawal',
            'trade_buy': 'Trade Buy',
            'trade_sell': 'Trade Sell',
            'fee': 'Fee',
            'lock': 'Funds Lock',
            'unlock': 'Funds Unlock'
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Transaction History Retrieval
        
        Args:
            input_data: {
                'limit': optional int (default: 50),
                'currency_code': optional string filter,
                'transaction_type': optional string filter,
                'start_date': optional date filter (ISO format),
                'end_date': optional date filter (ISO format),
                'min_amount': optional float filter,
                'max_amount': optional float filter,
                'order_id': optional string filter,
                'include_statistics': optional bool (default: true)
            }
            
        Returns:
            Dict mit Transaction-History-Result
        """
        # Filter aus Input Data erstellen
        transaction_filter = TransactionFilter(
            limit=input_data.get('limit', 50),
            currency_code=input_data.get('currency_code'),
            transaction_type=input_data.get('transaction_type'),
            start_date=input_data.get('start_date'),
            end_date=input_data.get('end_date'),
            min_amount=input_data.get('min_amount'),
            max_amount=input_data.get('max_amount'),
            order_id=input_data.get('order_id')
        )
        
        include_statistics = input_data.get('include_statistics', True)
        
        # Transaction History verarbeiten
        history_result = await self._retrieve_filtered_transaction_history(
            transaction_filter, include_statistics
        )
        
        # Statistics Update
        self.retrieval_counter += 1
        
        # Filter Usage Statistics
        self._update_filter_usage_stats(transaction_filter)
        
        # Retrieval History
        self.retrieval_history.append({
            'timestamp': datetime.now(),
            'filters_applied': history_result.filters_applied,
            'results_count': history_result.filtered_count,
            'retrieval_id': self.retrieval_counter
        })
        
        # Limit History
        if len(self.retrieval_history) > 150:
            self.retrieval_history.pop(0)
        
        self.logger.info(f"Transaction history retrieved",
                       filtered_count=history_result.filtered_count,
                       total_transactions=history_result.total_transactions,
                       filters_applied=len([v for v in history_result.filters_applied.values() if v is not None]),
                       retrieval_id=self.retrieval_counter)
        
        return {
            'success': True,
            'transactions': history_result.transactions,
            'total_transactions': history_result.total_transactions,
            'filtered_count': history_result.filtered_count,
            'filters_applied': history_result.filters_applied,
            'summary_statistics': history_result.summary_statistics if include_statistics else {},
            'retrieval_timestamp': history_result.retrieval_timestamp.isoformat()
        }
    
    async def _retrieve_filtered_transaction_history(self, 
                                                   filter_params: TransactionFilter,
                                                   include_statistics: bool) -> TransactionHistoryResult:
        """Retrieves gefilterte Transaction History"""
        
        # Filter anwenden
        filtered_transactions = []
        
        for txn in self.transaction_history:
            if not self._transaction_matches_filter(txn, filter_params):
                continue
            
            filtered_transactions.append(txn)
        
        # Nach Timestamp sortieren (neueste zuerst)
        filtered_transactions.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Limit anwenden
        limited_transactions = filtered_transactions[:filter_params.limit]
        
        # Transactions zu Dict konvertieren
        transactions_dict = [self._transaction_to_dict(txn) for txn in limited_transactions]
        
        # Summary Statistics berechnen
        summary_statistics = {}
        if include_statistics:
            summary_statistics = await self._calculate_transaction_statistics(filtered_transactions)
        
        # Filters Applied für Response
        filters_applied = {
            'currency_code': filter_params.currency_code,
            'transaction_type': filter_params.transaction_type,
            'start_date': filter_params.start_date,
            'end_date': filter_params.end_date,
            'min_amount': filter_params.min_amount,
            'max_amount': filter_params.max_amount,
            'order_id': filter_params.order_id,
            'limit': filter_params.limit
        }
        
        return TransactionHistoryResult(
            transactions=transactions_dict,
            total_transactions=len(self.transaction_history),
            filtered_count=len(filtered_transactions),
            filters_applied=filters_applied,
            summary_statistics=summary_statistics,
            retrieval_timestamp=datetime.now()
        )
    

        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())

    def _transaction_matches_filter(self, transaction: Transaction, 
                                  filter_params: TransactionFilter) -> bool:
        """Prüft ob Transaction den Filtern entspricht"""
        
        # Currency Filter
        if filter_params.currency_code and transaction.currency_code != filter_params.currency_code:
            return False
        
        # Transaction Type Filter
        if filter_params.transaction_type and transaction.type != filter_params.transaction_type:
            return False
        
        # Start Date Filter
        if filter_params.start_date:
            try:
                start_date = datetime.fromisoformat(filter_params.start_date.replace('Z', '+00:00'))
                if transaction.timestamp < start_date:
                    return False
            except ValueError:
                pass  # Invalid date format - ignore filter
        
        # End Date Filter
        if filter_params.end_date:
            try:
                end_date = datetime.fromisoformat(filter_params.end_date.replace('Z', '+00:00'))
                if transaction.timestamp > end_date:
                    return False
            except ValueError:
                pass  # Invalid date format - ignore filter
        
        # Amount Filters
        try:
            amount = abs(float(transaction.amount))  # Use absolute value for amount filters
            
            if filter_params.min_amount is not None and amount < filter_params.min_amount:
                return False
            
            if filter_params.max_amount is not None and amount > filter_params.max_amount:
                return False
        except (ValueError, TypeError):
            pass  # Invalid amount - ignore amount filters for this transaction
        
        # Order ID Filter
        if filter_params.order_id and transaction.order_id != filter_params.order_id:
            return False
        
        return True
    
    def _transaction_to_dict(self, transaction: Transaction) -> Dict[str, Any]:
        """Konvertiert Transaction zu Dict"""
        return {
            'transaction_id': transaction.transaction_id,
            'type': transaction.type,
            'type_display': self.transaction_types.get(transaction.type, transaction.type),
            'currency_code': transaction.currency_code,
            'amount': transaction.amount,
            'amount_float': float(transaction.amount),
            'balance_after': transaction.balance_after,
            'balance_after_float': float(transaction.balance_after),
            'description': transaction.description,
            'timestamp': transaction.timestamp.isoformat(),
            'order_id': transaction.order_id,
            'fee_amount': transaction.fee_amount,
            'fee_amount_float': float(transaction.fee_amount) if transaction.fee_amount else 0.0
        }
    
    async def _calculate_transaction_statistics(self, 
                                              transactions: List[Transaction]) -> Dict[str, Any]:
        """Berechnet Transaction Statistics"""
        if not transactions:
            return {}
        
        # Basic Statistics
        total_count = len(transactions)
        
        # Type Distribution
        type_distribution = {}
        for txn in transactions:
            type_distribution[txn.type] = type_distribution.get(txn.type, 0) + 1
        
        # Currency Distribution
        currency_distribution = {}
        for txn in transactions:
            currency_distribution[txn.currency_code] = currency_distribution.get(txn.currency_code, 0) + 1
        
        # Amount Statistics per Currency
        currency_amounts = {}
        for txn in transactions:
            if txn.currency_code not in currency_amounts:
                currency_amounts[txn.currency_code] = []
            currency_amounts[txn.currency_code].append(float(txn.amount))
        
        currency_amount_stats = {}
        for currency, amounts in currency_amounts.items():
            currency_amount_stats[currency] = {
                'total': round(sum(amounts), 2),
                'average': round(sum(amounts) / len(amounts), 2),
                'min': round(min(amounts), 2),
                'max': round(max(amounts), 2),
                'count': len(amounts)
            }
        
        # Time Range
        timestamps = [txn.timestamp for txn in transactions]
        time_range = {
            'earliest': min(timestamps).isoformat(),
            'latest': max(timestamps).isoformat(),
            'span_days': (max(timestamps) - min(timestamps)).days
        }
        
        # Fee Statistics
        fees = [float(txn.fee_amount) for txn in transactions if txn.fee_amount]
        fee_stats = {}
        if fees:
            fee_stats = {
                'total_fees': round(sum(fees), 2),
                'average_fee': round(sum(fees) / len(fees), 2),
                'transactions_with_fees': len(fees),
                'fee_percentage': round(len(fees) / total_count * 100, 1)
            }
        
        return {
            'total_transactions': total_count,
            'type_distribution': type_distribution,
            'currency_distribution': currency_distribution,
            'currency_amount_statistics': currency_amount_stats,
            'time_range': time_range,
            'fee_statistics': fee_stats
        }
    
    def _update_filter_usage_stats(self, filter_params: TransactionFilter):
        """Aktualisiert Filter Usage Statistics"""
        filter_dict = filter_params.dict()
        
        for filter_name, filter_value in filter_dict.items():
            if filter_value is not None:
                if filter_name not in self.filter_usage_stats:
                    self.filter_usage_stats[filter_name] = 0
                self.filter_usage_stats[filter_name] += 1
    
    def add_transaction(self, transaction: Transaction):
        """Fügt neue Transaction hinzu (für externe Updates)"""
        self.transaction_history.append(transaction)
        
        # Keep only last 2000 transactions to prevent memory issues
        if len(self.transaction_history) > 2000:
            self.transaction_history = self.transaction_history[-2000:]
        
        self.logger.info(f"Transaction added to history",
                       transaction_id=transaction.transaction_id,
                       type=transaction.type,
                       currency=transaction.currency_code,
                       amount=transaction.amount)
    
    def get_recent_transactions(self, hours: int = 24, limit: int = 20) -> List[Dict[str, Any]]:
        """Gibt recent Transactions zurück"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent = [
            txn for txn in self.transaction_history
            if txn.timestamp >= cutoff_time
        ]
        
        # Sort by timestamp (newest first) and limit
        recent.sort(key=lambda x: x.timestamp, reverse=True)
        recent = recent[:limit]
        
        return [self._transaction_to_dict(txn) for txn in recent]
    
    def get_transaction_by_id(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Gibt spezifische Transaction zurück"""
        for txn in self.transaction_history:
            if txn.transaction_id == transaction_id:
                return self._transaction_to_dict(txn)
        return None
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'transaction_history',
            'description': 'Retrieves filtered transaction history with statistics',
            'responsibility': 'Transaction history retrieval logic only',
            'input_parameters': {
                'limit': 'Maximum number of transactions to return (default: 50)',
                'currency_code': 'Filter by currency code',
                'transaction_type': 'Filter by transaction type',
                'start_date': 'Filter by start date (ISO format)',
                'end_date': 'Filter by end date (ISO format)',
                'min_amount': 'Filter by minimum amount',
                'max_amount': 'Filter by maximum amount',
                'order_id': 'Filter by order ID',
                'include_statistics': 'Whether to include summary statistics (default: true)'
            },
            'output_format': {
                'transactions': 'List of filtered transactions with details',
                'total_transactions': 'Total number of transactions in history',
                'filtered_count': 'Number of transactions after filtering',
                'filters_applied': 'Dictionary of applied filter parameters',
                'summary_statistics': 'Statistical summary of filtered transactions',
                'retrieval_timestamp': 'History retrieval timestamp'
            },
            'supported_transaction_types': list(self.transaction_types.keys()),
            'transaction_type_display_names': self.transaction_types,
            'supported_filters': [
                'currency_code', 'transaction_type', 'start_date', 'end_date',
                'min_amount', 'max_amount', 'order_id', 'limit'
            ],
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_transaction_statistics(self) -> Dict[str, Any]:
        """Transaction History Module Statistiken"""
        total_retrievals = len(self.retrieval_history)
        total_transactions = len(self.transaction_history)
        
        if total_retrievals == 0:
            return {
                'total_retrievals': 0,
                'total_transactions_stored': total_transactions,
                'filter_usage_statistics': self.filter_usage_stats
            }
        
        # Average Results per Retrieval
        total_results = sum(r['results_count'] for r in self.retrieval_history)
        avg_results = round(total_results / total_retrievals, 1) if total_retrievals > 0 else 0
        
        # Most Used Filters
        most_used_filters = dict(sorted(
            self.filter_usage_stats.items(), key=lambda x: x[1], reverse=True
        ))
        
        # Recent Activity
        recent_retrievals = [
            r for r in self.retrieval_history
            if (datetime.now() - r['timestamp']).seconds < 3600  # Last hour
        ]
        
        return {
            'total_retrievals': total_retrievals,
            'total_transactions_stored': total_transactions,
            'average_results_per_retrieval': avg_results,
            'recent_retrievals_last_hour': len(recent_retrievals),
            'filter_usage_statistics': most_used_filters,
            'supported_transaction_types': len(self.transaction_types),
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
