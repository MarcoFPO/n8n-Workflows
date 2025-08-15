"""
Account Balance Module - Event-Bus Integration Extensions
Erweitert das Account Balance Module um vollständige Event-Bus Integration
"""

import asyncio
from typing import Dict, Any
from datetime import datetime


class AccountBalanceEventIntegration:
    """
    Event-Bus Integration Mixin für Account Balance Module
    Erweitert bestehende Module um Event-Bus Capabilities
    """
    
    async def _setup_event_subscriptions(self):
        """Setup Event-Bus Subscriptions für Account Balance Module"""
        try:
            # Subscribe to market price updates
            await self.event_bus.subscribe('market.prices.updated', self._handle_market_price_event)
            
            # Subscribe to balance update requests
            await self.event_bus.subscribe('account.balance.request', self._handle_balance_request_event)
            
            # Subscribe to portfolio summary requests
            await self.event_bus.subscribe('portfolio.summary.request', self._handle_portfolio_summary_event)
            
            # Subscribe to balance sync requests
            await self.event_bus.subscribe('account.balance.sync', self._handle_balance_sync_event)
            
            self.logger.info("Event subscriptions setup completed", 
                           module=self.module_name)
        except Exception as e:
            self.logger.error("Failed to setup event subscriptions",
                            error=str(e), module=self.module_name)
    
    async def _handle_market_price_event(self, event):
        """Handle Market Price Update Events"""
        try:
            event_data = event.get('data', {})
            updated_prices = event_data.get('updated_prices', {})
            
            if updated_prices:
                # Update internal prices
                old_value = self.get_total_portfolio_value_eur()
                self.update_market_prices(updated_prices)
                new_value = self.get_total_portfolio_value_eur()
                
                # Publish portfolio value update if significant change
                if abs(new_value - old_value) > 100:  # Significant change threshold
                    portfolio_event = {
                        'event_type': 'portfolio.value.changed',
                        'stream_id': 'portfolio-value',
                        'data': {
                            'old_value_eur': old_value,
                            'new_value_eur': new_value,
                            'change_eur': new_value - old_value,
                            'change_percentage': ((new_value - old_value) / old_value * 100) if old_value > 0 else 0,
                            'updated_at': datetime.now().isoformat(),
                            'trigger': 'market_price_update'
                        },
                        'source': self.module_name
                    }
                    await self.event_bus.publish(portfolio_event)
                    
            self.logger.info("Market price event processed", prices_updated=len(updated_prices))
            
        except Exception as e:
            self.logger.error("Failed to handle market price event", 
                            error=str(e), event=str(event))
    
    async def _handle_balance_request_event(self, event):
        """Handle Balance Request Events"""
        try:
            event_data = event.get('data', {})
            
            # Execute balance retrieval with event data
            result = await self.execute_function(event_data)
            
            # Publish response event
            response_event = {
                'event_type': 'account.balance.response',
                'stream_id': event.get('stream_id', 'balance-request'),
                'data': {
                    'request_id': event.get('correlation_id'),
                    'balances': result.get('balances', {}),
                    'currencies_count': result.get('currencies_count', 0),
                    'portfolio_summary': result.get('portfolio_summary'),
                    'total_portfolio_value_eur': self.get_total_portfolio_value_eur(),
                    'retrieved_at': datetime.now().isoformat()
                },
                'source': self.module_name,
                'correlation_id': event.get('correlation_id')
            }
            await self.event_bus.publish(response_event)
            
            self.logger.info("Balance request event processed",
                           currencies_returned=result.get('currencies_count', 0),
                           correlation_id=event.get('correlation_id'))
            
        except Exception as e:
            self.logger.error("Failed to handle balance request event",
                            error=str(e), event=str(event))
    
    async def _handle_portfolio_summary_event(self, event):
        """Handle Portfolio Summary Request Events"""
        try:
            # Get fresh portfolio summary
            portfolio_summary = await self._get_or_update_portfolio_summary(refresh_cache=True)
            
            # Publish detailed response
            response_event = {
                'event_type': 'portfolio.summary.response',
                'stream_id': event.get('stream_id', 'portfolio-request'),
                'data': {
                    'portfolio_summary': portfolio_summary,
                    'total_value_eur': self.get_total_portfolio_value_eur(),
                    'currencies_count': len(self.account_balances),
                    'largest_position': self._get_largest_position(portfolio_summary.get('positions', {})) if portfolio_summary else None,
                    'diversification_score': portfolio_summary.get('diversification_score', 0) if portfolio_summary else 0,
                    'generated_at': datetime.now().isoformat()
                },
                'source': self.module_name,
                'correlation_id': event.get('correlation_id')
            }
            await self.event_bus.publish(response_event)
            
            self.logger.info("Portfolio summary event processed",
                           correlation_id=event.get('correlation_id'))
            
        except Exception as e:
            self.logger.error("Failed to handle portfolio summary event",
                            error=str(e), event=str(event))
    
    async def _handle_balance_sync_event(self, event):
        """Handle Balance Synchronization Events"""
        try:
            event_data = event.get('data', {})
            sync_data = event_data.get('balance_updates', {})
            
            updated_currencies = []
            for currency_code, balance_data in sync_data.items():
                if isinstance(balance_data, dict):
                    available = balance_data.get('available', '0.00')
                    locked = balance_data.get('locked', '0.00')
                    
                    # Update balance
                    self.update_account_balance(currency_code, available, locked)
                    updated_currencies.append(currency_code)
            
            # Publish sync completion event
            if updated_currencies:
                sync_response = {
                    'event_type': 'account.balance.sync.completed',
                    'stream_id': event.get('stream_id', 'balance-sync'),
                    'data': {
                        'synchronized_currencies': updated_currencies,
                        'new_portfolio_value_eur': self.get_total_portfolio_value_eur(),
                        'sync_timestamp': datetime.now().isoformat()
                    },
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(sync_response)
            
            self.logger.info("Balance sync event processed",
                           currencies_updated=len(updated_currencies))
            
        except Exception as e:
            self.logger.error("Failed to handle balance sync event",
                            error=str(e), event=str(event))
    
    async def process_event(self, event):
        """Process incoming events - Enhanced Event Processing"""
        try:
            event_type = event.get('event_type', '')
            
            if event_type == 'system.health.request':
                # Comprehensive health check response
                health_response = {
                    'event_type': 'system.health.response',
                    'stream_id': 'health-check',
                    'data': {
                        'module_name': self.module_name,
                        'status': 'healthy',
                        'currencies_managed': len(self.account_balances),
                        'retrieval_counter': self.retrieval_counter,
                        'cache_size': len(self.balance_cache),
                        'total_portfolio_value_eur': self.get_total_portfolio_value_eur(),
                        'event_subscriptions_active': True,
                        'last_execution_time_ms': self.average_execution_time,
                        'health_check_timestamp': datetime.now().isoformat()
                    },
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(health_response)
                
                self.logger.info("Health check event processed",
                               module=self.module_name)
            
            elif event_type == 'market.prices.updated':
                await self._handle_market_price_event(event)
            
            elif event_type == 'account.balance.request':
                await self._handle_balance_request_event(event)
            
            elif event_type == 'portfolio.summary.request':
                await self._handle_portfolio_summary_event(event)
            
            elif event_type == 'account.balance.sync':
                await self._handle_balance_sync_event(event)
            
            elif event_type.startswith('account.'):
                # Handle any account-related events
                self.logger.info("Account-related event received",
                               event_type=event_type, module=self.module_name)
            
            else:
                self.logger.debug("Unhandled event type", 
                                event_type=event_type, module=self.module_name)
                
        except Exception as e:
            self.logger.error("Failed to process event",
                            error=str(e), event=str(event), module=self.module_name)
    
    async def publish_balance_changed_event(self, currency_code: str, old_balance: Dict, new_balance: Dict):
        """Publish balance change event when balance is updated"""
        if not self.event_bus:
            return
        
        try:
            balance_change_event = {
                'event_type': 'account.balance.changed',
                'stream_id': f'balance-change-{currency_code}',
                'data': {
                    'currency_code': currency_code,
                    'old_balance': old_balance,
                    'new_balance': new_balance,
                    'change_amount': float(new_balance.get('available', '0')) - float(old_balance.get('available', '0')),
                    'timestamp': datetime.now().isoformat()
                },
                'source': self.module_name
            }
            await self.event_bus.publish(balance_change_event)
            
        except Exception as e:
            self.logger.error("Failed to publish balance change event",
                            error=str(e), currency=currency_code)


def apply_event_integration_to_balance_module(balance_module_class):
    """
    Applies Event-Bus Integration to Account Balance Module Class
    
    Args:
        balance_module_class: The AccountBalanceModule class to extend
    
    Returns:
        Enhanced class with Event-Bus integration
    """
    
    class EnhancedAccountBalanceModule(balance_module_class, AccountBalanceEventIntegration):
        """Account Balance Module mit vollständiger Event-Bus Integration"""
        
        def __init__(self, event_bus=None):
            super().__init__(event_bus)
            
            # Setup Event-Bus Integration if available
            if self.event_bus:
                asyncio.create_task(self._setup_event_subscriptions())
        
        async def update_account_balance_with_events(self, currency_code: str, available: str, 
                                                   locked: str = "0.00", total: str = None):
            """Enhanced balance update with event publishing"""
            # Get old balance for comparison
            old_balance = None
            if currency_code in self.account_balances:
                old_balance = {
                    'available': self.account_balances[currency_code].available,
                    'locked': self.account_balances[currency_code].locked,
                    'total': self.account_balances[currency_code].total
                }
            
            # Update balance
            self.update_account_balance(currency_code, available, locked, total)
            
            # Publish change event
            if old_balance:
                new_balance = {
                    'available': available,
                    'locked': locked, 
                    'total': total or str(float(available) + float(locked))
                }
                await self.publish_balance_changed_event(currency_code, old_balance, new_balance)
    
    return EnhancedAccountBalanceModule