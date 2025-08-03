"""
Account Module für Broker-Gateway-Service
Account Management und Balance Tracking
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')
from backend_base_module import BackendBaseModule
from event_bus import EventType
import structlog


class AccountBalance(BaseModel):
    currency_code: str
    available: str
    locked: str
    total: str
    last_updated: datetime


class Transaction(BaseModel):
    transaction_id: str
    type: str  # deposit, withdrawal, trade, fee
    currency_code: str
    amount: str
    balance_after: str
    description: str
    timestamp: datetime


class AccountModule(BackendBaseModule):
    """Account Management und Balance Tracking"""
    
    def __init__(self, event_bus):
        super().__init__("account", event_bus)
        self.account_balances = {}
        self.transaction_history = []
        self.account_limits = {}
        self.withdrawal_limits = {}
        self.portfolio_summary = {}
        
    async def _initialize_module(self) -> bool:
        """Initialize account module"""
        try:
            self.logger.info("Initializing Account Module")
            
            # Initialize demo account balances
            self.account_balances = {
                "EUR": AccountBalance(
                    currency_code="EUR",
                    available="10000.00",
                    locked="0.00",
                    total="10000.00",
                    last_updated=datetime.now()
                ),
                "USD": AccountBalance(
                    currency_code="USD",
                    available="5000.00",
                    locked="0.00",
                    total="5000.00",
                    last_updated=datetime.now()
                ),
                "BTC": AccountBalance(
                    currency_code="BTC",
                    available="0.25",
                    locked="0.00",
                    total="0.25",
                    last_updated=datetime.now()
                ),
                "ETH": AccountBalance(
                    currency_code="ETH",
                    available="2.5",
                    locked="0.00",
                    total="2.5",
                    last_updated=datetime.now()
                )
            }
            
            # Initialize account limits
            self.account_limits = {
                'daily_withdrawal_limit': 50000.0,  # €50k per day
                'monthly_trading_limit': 1000000.0,  # €1M per month
                'max_open_orders': 100,
                'max_position_size': 100000.0,  # €100k per position
                'verification_level': 'fully_verified'
            }
            
            # Initialize withdrawal limits per currency
            self.withdrawal_limits = {
                'EUR': {'daily': 10000.0, 'monthly': 100000.0},
                'USD': {'daily': 10000.0, 'monthly': 100000.0},
                'BTC': {'daily': 1.0, 'monthly': 10.0},
                'ETH': {'daily': 10.0, 'monthly': 100.0}
            }
            
            # Add initial transaction history
            self.transaction_history = [
                Transaction(
                    transaction_id="TXN_INITIAL_DEPOSIT",
                    type="deposit",
                    currency_code="EUR",
                    amount="10000.00",
                    balance_after="10000.00",
                    description="Initial deposit",
                    timestamp=datetime.now() - timedelta(days=30)
                )
            ]
            
            self.logger.info("Account module initialized successfully",
                           currencies=len(self.account_balances),
                           transaction_history=len(self.transaction_history))
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize account module", error=str(e))
            return False
    
    async def _subscribe_to_events(self):
        """Subscribe to relevant events"""
        await self.subscribe_to_event(
            EventType.TRADING_STATE_CHANGED,
            self._handle_trading_event
        )
        await self.subscribe_to_event(
            EventType.PORTFOLIO_STATE_CHANGED,
            self._handle_portfolio_event
        )
        await self.subscribe_to_event(
            EventType.CONFIG_UPDATED,
            self._handle_config_event
        )
        await self.subscribe_to_event(
            EventType.SYSTEM_ALERT_RAISED,
            self._handle_system_alert_event
        )
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Main account processing logic"""
        try:
            request_type = data.get('type', 'get_balances')
            
            if request_type == 'get_balances':
                return await self._get_account_balances(data)
            elif request_type == 'get_balance':
                return await self._get_single_balance(data)
            elif request_type == 'get_transaction_history':
                return await self._get_transaction_history(data)
            elif request_type == 'process_transaction':
                return await self._process_transaction(data)
            elif request_type == 'get_account_limits':
                return await self._get_account_limits()
            elif request_type == 'get_portfolio_summary':
                return await self._get_portfolio_summary()
            elif request_type == 'check_trading_capacity':
                return await self._check_trading_capacity(data)
            else:
                return {
                    'success': False,
                    'error': f'Unknown request type: {request_type}'
                }
                
        except Exception as e:
            self.logger.error("Error in account processing", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_account_balances(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get all account balances"""
        try:
            # Update portfolio summary
            await self._update_portfolio_summary()
            
            balances_dict = {
                currency: balance.dict() 
                for currency, balance in self.account_balances.items()
            }
            
            return {
                'success': True,
                'balances': balances_dict,
                'currencies_count': len(self.account_balances),
                'portfolio_summary': self.portfolio_summary,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Error getting account balances", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_single_balance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get balance for specific currency"""
        try:
            currency_code = data.get('currency_code')
            if not currency_code:
                return {
                    'success': False,
                    'error': 'No currency code provided'
                }
            
            if currency_code not in self.account_balances:
                return {
                    'success': False,
                    'error': f'Currency {currency_code} not found in account'
                }
            
            balance = self.account_balances[currency_code]
            
            return {
                'success': True,
                'balance': balance.dict(),
                'currency_code': currency_code
            }
            
        except Exception as e:
            self.logger.error("Error getting single balance", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_transaction_history(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get transaction history"""
        try:
            limit = data.get('limit', 50)
            currency_filter = data.get('currency_code')
            transaction_type_filter = data.get('transaction_type')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            # Filter transactions
            filtered_transactions = []
            for txn in self.transaction_history:
                # Apply filters
                if currency_filter and txn.currency_code != currency_filter:
                    continue
                
                if transaction_type_filter and txn.type != transaction_type_filter:
                    continue
                
                if start_date:
                    try:
                        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        if txn.timestamp < start:
                            continue
                    except ValueError:
                        pass
                
                if end_date:
                    try:
                        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        if txn.timestamp > end:
                            continue
                    except ValueError:
                        pass
                
                filtered_transactions.append(txn.dict())
            
            # Sort by timestamp (most recent first) and apply limit
            filtered_transactions.sort(key=lambda x: x['timestamp'], reverse=True)
            filtered_transactions = filtered_transactions[:limit]
            
            return {
                'success': True,
                'transactions': filtered_transactions,
                'total_transactions': len(self.transaction_history),
                'filtered_count': len(filtered_transactions),
                'filters_applied': {
                    'currency_code': currency_filter,
                    'transaction_type': transaction_type_filter,
                    'start_date': start_date,
                    'end_date': end_date,
                    'limit': limit
                }
            }
            
        except Exception as e:
            self.logger.error("Error getting transaction history", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _process_transaction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process account transaction"""
        try:
            transaction_type = data.get('transaction_type')  # trade, deposit, withdrawal, fee
            currency_code = data.get('currency_code')
            amount = data.get('amount')
            description = data.get('description', '')
            order_id = data.get('order_id')  # For trade transactions
            
            if not all([transaction_type, currency_code, amount]):
                return {
                    'success': False,
                    'error': 'Missing required transaction parameters'
                }
            
            try:
                amount_float = float(amount)
            except ValueError:
                return {
                    'success': False,
                    'error': 'Invalid amount format'
                }
            
            # Get current balance
            if currency_code not in self.account_balances:
                # Create new currency balance if it doesn't exist
                self.account_balances[currency_code] = AccountBalance(
                    currency_code=currency_code,
                    available="0.00",
                    locked="0.00",
                    total="0.00",
                    last_updated=datetime.now()
                )
            
            current_balance = self.account_balances[currency_code]
            current_available = float(current_balance.available)
            current_locked = float(current_balance.locked)
            current_total = float(current_balance.total)
            
            # Process different transaction types
            if transaction_type == 'trade_buy':
                # Buying: decrease fiat, increase crypto/stock
                if amount_float > current_available:
                    return {
                        'success': False,
                        'error': f'Insufficient {currency_code} balance for trade'
                    }
                
                new_available = current_available - amount_float
                new_total = current_total - amount_float
                
            elif transaction_type == 'trade_sell':
                # Selling: increase fiat, decrease crypto/stock
                new_available = current_available + amount_float
                new_total = current_total + amount_float
                
            elif transaction_type == 'deposit':
                # Deposit: increase balance
                new_available = current_available + amount_float
                new_total = current_total + amount_float
                
            elif transaction_type == 'withdrawal':
                # Withdrawal: decrease balance
                if amount_float > current_available:
                    return {
                        'success': False,
                        'error': f'Insufficient {currency_code} balance for withdrawal'
                    }
                
                new_available = current_available - amount_float
                new_total = current_total - amount_float
                
            elif transaction_type == 'fee':
                # Fee: decrease balance
                if amount_float > current_available:
                    # Take fee from total if not enough available
                    new_available = max(0, current_available - amount_float)
                    new_total = current_total - amount_float
                else:
                    new_available = current_available - amount_float
                    new_total = current_total - amount_float
                    
            elif transaction_type == 'lock':
                # Lock funds (for pending orders)
                if amount_float > current_available:
                    return {
                        'success': False,
                        'error': f'Insufficient available {currency_code} to lock'
                    }
                
                new_available = current_available - amount_float
                new_locked = current_locked + amount_float
                new_total = current_total
                
            elif transaction_type == 'unlock':
                # Unlock funds (cancel order)
                new_available = current_available + amount_float
                new_locked = max(0, current_locked - amount_float)
                new_total = current_total
                
            else:
                return {
                    'success': False,
                    'error': f'Unknown transaction type: {transaction_type}'
                }
            
            # Update balance
            current_balance.available = f"{new_available:.8f}".rstrip('0').rstrip('.')
            if transaction_type in ['lock', 'unlock']:
                current_balance.locked = f"{new_locked:.8f}".rstrip('0').rstrip('.')
            current_balance.total = f"{new_total:.8f}".rstrip('0').rstrip('.')
            current_balance.last_updated = datetime.now()
            
            # Create transaction record
            transaction_id = f"TXN_{int(datetime.now().timestamp())}_{len(self.transaction_history)}"
            
            transaction = Transaction(
                transaction_id=transaction_id,
                type=transaction_type,
                currency_code=currency_code,
                amount=amount,
                balance_after=current_balance.total,
                description=description or f"{transaction_type.title()} transaction",
                timestamp=datetime.now()
            )
            
            self.transaction_history.append(transaction)
            
            # Keep only last 1000 transactions to prevent memory issues
            if len(self.transaction_history) > 1000:
                self.transaction_history = self.transaction_history[-1000:]
            
            # Publish portfolio event if significant change
            if abs(amount_float) > 100:  # Significant transaction
                await self.publish_module_event(
                    EventType.PORTFOLIO_STATE_CHANGED,
                    {
                        'transaction_id': transaction_id,
                        'currency_code': currency_code,
                        'transaction_type': transaction_type,
                        'amount': amount,
                        'new_balance': current_balance.total
                    },
                    f"account-transaction-{transaction_id}"
                )
            
            self.logger.info("Transaction processed successfully",
                           transaction_id=transaction_id,
                           type=transaction_type,
                           currency=currency_code,
                           amount=amount)
            
            return {
                'success': True,
                'transaction': transaction.dict(),
                'updated_balance': current_balance.dict()
            }
            
        except Exception as e:
            self.logger.error("Error processing transaction", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_account_limits(self) -> Dict[str, Any]:
        """Get account limits and restrictions"""
        try:
            return {
                'success': True,
                'account_limits': self.account_limits,
                'withdrawal_limits': self.withdrawal_limits,
                'current_usage': await self._calculate_current_usage()
            }
        except Exception as e:
            self.logger.error("Error getting account limits", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _calculate_current_usage(self) -> Dict[str, Any]:
        """Calculate current usage against limits"""
        try:
            today = datetime.now().date()
            month_start = datetime.now().replace(day=1).date()
            
            daily_withdrawals = 0.0
            monthly_trading = 0.0
            
            for txn in self.transaction_history:
                txn_date = txn.timestamp.date()
                
                if txn_date == today and txn.type == 'withdrawal':
                    if txn.currency_code == 'EUR':
                        daily_withdrawals += float(txn.amount)
                
                if txn_date >= month_start and txn.type.startswith('trade'):
                    if txn.currency_code == 'EUR':
                        monthly_trading += float(txn.amount)
            
            return {
                'daily_withdrawals_used': daily_withdrawals,
                'daily_withdrawals_limit': self.account_limits['daily_withdrawal_limit'],
                'daily_withdrawals_remaining': self.account_limits['daily_withdrawal_limit'] - daily_withdrawals,
                'monthly_trading_used': monthly_trading,
                'monthly_trading_limit': self.account_limits['monthly_trading_limit'],
                'monthly_trading_remaining': self.account_limits['monthly_trading_limit'] - monthly_trading
            }
            
        except Exception as e:
            self.logger.error("Error calculating current usage", error=str(e))
            return {}
    
    async def _update_portfolio_summary(self):
        """Update portfolio summary with current market values"""
        try:
            # Mock portfolio valuation (in production, use real market prices)
            mock_prices = {
                'EUR': 1.0,
                'USD': 0.85,  # EUR/USD rate
                'BTC': 45000.0,  # BTC/EUR
                'ETH': 2800.0   # ETH/EUR
            }
            
            total_value_eur = 0.0
            positions = {}
            
            for currency, balance in self.account_balances.items():
                total_balance = float(balance.total)
                if total_balance > 0:
                    price_eur = mock_prices.get(currency, 1.0)
                    value_eur = total_balance * price_eur
                    total_value_eur += value_eur
                    
                    positions[currency] = {
                        'balance': total_balance,
                        'price_eur': price_eur,
                        'value_eur': value_eur,
                        'percentage': 0  # Will be calculated below
                    }
            
            # Calculate percentages
            for currency in positions:
                if total_value_eur > 0:
                    positions[currency]['percentage'] = (positions[currency]['value_eur'] / total_value_eur) * 100
            
            self.portfolio_summary = {
                'total_value_eur': total_value_eur,
                'positions': positions,
                'currencies_count': len(positions),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Error updating portfolio summary", error=str(e))
    
    async def _get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        try:
            await self._update_portfolio_summary()
            
            return {
                'success': True,
                'portfolio_summary': self.portfolio_summary
            }
            
        except Exception as e:
            self.logger.error("Error getting portfolio summary", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _check_trading_capacity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if account has capacity for trading"""
        try:
            currency_code = data.get('currency_code')
            amount = data.get('amount')
            
            if not all([currency_code, amount]):
                return {
                    'success': False,
                    'error': 'Currency code and amount required'
                }
            
            amount_float = float(amount)
            
            # Check balance
            if currency_code not in self.account_balances:
                return {
                    'success': True,
                    'has_capacity': False,
                    'reason': f'No {currency_code} balance'
                }
            
            available = float(self.account_balances[currency_code].available)
            
            if amount_float > available:
                return {
                    'success': True,
                    'has_capacity': False,
                    'reason': f'Insufficient balance. Available: {available}, Required: {amount_float}'
                }
            
            # Check limits
            current_usage = await self._calculate_current_usage()
            monthly_remaining = current_usage.get('monthly_trading_remaining', 0)
            
            if currency_code == 'EUR' and amount_float > monthly_remaining:
                return {
                    'success': True,
                    'has_capacity': False,
                    'reason': f'Monthly trading limit exceeded. Remaining: {monthly_remaining}'
                }
            
            return {
                'success': True,
                'has_capacity': True,
                'available_balance': available,
                'monthly_trading_remaining': monthly_remaining
            }
            
        except Exception as e:
            self.logger.error("Error checking trading capacity", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _handle_trading_event(self, event):
        """Handle trading state changed events"""
        try:
            self.logger.debug("Received trading event")
            
            # Process trading-related balance changes
            event_data = event.data
            action = event_data.get('action')
            
            if action == 'order_placed':
                # Lock funds for placed orders
                order_id = event_data.get('order_id')
                instrument = event_data.get('instrument')
                side = event_data.get('side')
                amount = event_data.get('amount')
                
                if all([order_id, instrument, side, amount]):
                    # Determine currency to lock based on order side and instrument
                    if side == 'BUY':
                        # Lock fiat currency (EUR/USD)
                        lock_currency = 'EUR' if '_EUR' in instrument else 'USD'
                    else:
                        # Lock the asset being sold
                        lock_currency = instrument.split('_')[0] if '_' in instrument else instrument
                    
                    # Lock the funds
                    await self._process_transaction({
                        'transaction_type': 'lock',
                        'currency_code': lock_currency,
                        'amount': amount,
                        'description': f'Locked for order {order_id}',
                        'order_id': order_id
                    })
                    
        except Exception as e:
            self.logger.error("Error handling trading event", error=str(e))
    
    async def _handle_portfolio_event(self, event):
        """Handle portfolio state changed events"""
        try:
            self.logger.debug("Received portfolio event")
            # Update portfolio summary when portfolio changes
            await self._update_portfolio_summary()
        except Exception as e:
            self.logger.error("Error handling portfolio event", error=str(e))
    
    async def _handle_config_event(self, event):
        """Handle configuration update events"""
        try:
            self.logger.info("Received config update event")
            
            config_data = event.data
            if 'account_limits' in config_data:
                self.account_limits.update(config_data['account_limits'])
                self.logger.info("Account limits updated")
            
            if 'withdrawal_limits' in config_data:
                self.withdrawal_limits.update(config_data['withdrawal_limits'])
                self.logger.info("Withdrawal limits updated")
                
        except Exception as e:
            self.logger.error("Error handling config event", error=str(e))
    
    async def _handle_system_alert_event(self, event):
        """Handle system alert events"""
        try:
            self.logger.info("Received system alert event")
            
            alert_type = event.data.get('alert_type')
            if alert_type == 'account_frozen':
                # Freeze account operations
                self.logger.warning("Account freeze alert received")
                # Could implement account freeze logic
                
        except Exception as e:
            self.logger.error("Error handling system alert event", error=str(e))