"""
Account Balance Module - Single Function Module
Verantwortlich ausschließlich für Account Balance Retrieval Logic
"""

from typing import Dict, Any, List, Optional
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from ..single_function_module_base import SingleFunctionModule


class AccountBalance(BaseModel):
    currency_code: str
    available: str
    locked: str
    total: str
    last_updated: datetime


class BalanceRetrievalResult(BaseModel):
    balances: Dict[str, Dict[str, Any]]
    currencies_count: int
    portfolio_summary: Optional[Dict[str, Any]] = None
    last_updated: datetime
    retrieval_timestamp: datetime


class AccountBalanceModule(SingleFunctionModule):
    """
    Single Function Module: Account Balance Retrieval
    Verantwortlichkeit: Ausschließlich Account-Balance-Retrieval-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("account_balance", event_bus)
        
        # Balance Cache und History
        self.balance_cache = {}
        self.balance_retrieval_history = []
        self.retrieval_counter = 0
        
        # Event-Bus Integration Setup
        if self.event_bus:
            self._setup_event_subscriptions()
        
        # Mock Account Balances (normalerweise aus Datenbank/API)
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
        
        # Portfolio Summary Cache
        self.portfolio_summary_cache = None
        self.portfolio_cache_timestamp = None
        
        # Mock Market Prices für Portfolio Valuation
        self.mock_prices = {
            'EUR': 1.0,
            'USD': 0.85,    # EUR/USD rate
            'BTC': 45000.0, # BTC/EUR
            'ETH': 2800.0   # ETH/EUR
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Account Balance Retrieval
        
        Args:
            input_data: {
                'include_portfolio_summary': optional bool (default: true),
                'refresh_cache': optional bool (default: false),
                'filter_currencies': optional list of currency codes to return
            }
            
        Returns:
            Dict mit Balance-Retrieval-Result
        """
        include_portfolio = input_data.get('include_portfolio_summary', True)
        refresh_cache = input_data.get('refresh_cache', False)
        filter_currencies = input_data.get('filter_currencies', [])
        
        self.retrieval_counter += 1
        
        # Portfolio Summary aktualisieren falls erforderlich
        portfolio_summary = None
        if include_portfolio:
            portfolio_summary = await self._get_or_update_portfolio_summary(refresh_cache)
        
        # Balances verarbeiten
        balances_dict = await self._process_account_balances(filter_currencies)
        
        # Result erstellen
        result = BalanceRetrievalResult(
            balances=balances_dict,
            currencies_count=len(balances_dict),
            portfolio_summary=portfolio_summary,
            last_updated=datetime.now(),
            retrieval_timestamp=datetime.now()
        )
        
        # Cache aktualisieren
        cache_key = f"retrieval_{self.retrieval_counter}"
        self.balance_cache[cache_key] = result
        
        # Balance Retrieval History
        self.balance_retrieval_history.append({
            'timestamp': datetime.now(),
            'currencies_retrieved': len(balances_dict),
            'portfolio_included': include_portfolio,
            'cache_refreshed': refresh_cache,
            'retrieval_id': cache_key
        })
        
        # Limit History auf 100 Einträge
        if len(self.balance_retrieval_history) > 100:
            self.balance_retrieval_history.pop(0)
        
        self.logger.info(f"Account balances retrieved",
                       currencies_count=len(balances_dict),
                       portfolio_included=include_portfolio,
                       retrieval_id=cache_key)
        
        return {
            'balances': result.balances,
            'currencies_count': result.currencies_count,
            'portfolio_summary': result.portfolio_summary,
            'last_updated': result.last_updated.isoformat(),
            'retrieval_timestamp': result.retrieval_timestamp.isoformat()
        }
    
    async def _process_account_balances(self, filter_currencies: List[str]) -> Dict[str, Dict[str, Any]]:
        """Verarbeitet Account Balances mit optionalem Filter"""
        
        balances_dict = {}
        
        for currency, balance in self.account_balances.items():
            # Currency Filter anwenden
            if filter_currencies and currency not in filter_currencies:
                continue
            
            # Balance zu Dict konvertieren
            balances_dict[currency] = {
                'currency_code': balance.currency_code,
                'available': balance.available,
                'locked': balance.locked,
                'total': balance.total,
                'last_updated': balance.last_updated.isoformat(),
                'available_float': float(balance.available),
                'locked_float': float(balance.locked),
                'total_float': float(balance.total)
            }
        
        return balances_dict
    
    async def _get_or_update_portfolio_summary(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Gibt Portfolio Summary zurück (mit Cache)"""
        
        # Cache Check
        if (not force_refresh and 
            self.portfolio_summary_cache and 
            self.portfolio_cache_timestamp and
            (datetime.now() - self.portfolio_cache_timestamp).seconds < 60):  # 1 Minute Cache
            
            return self.portfolio_summary_cache
        
        # Portfolio Summary neu berechnen
        total_value_eur = 0.0
        positions = {}
        
        for currency, balance in self.account_balances.items():
            total_balance = float(balance.total)
            if total_balance > 0:
                price_eur = self.mock_prices.get(currency, 1.0)
                value_eur = total_balance * price_eur
                total_value_eur += value_eur
                
                positions[currency] = {
                    'balance': total_balance,
                    'price_eur': price_eur,
                    'value_eur': round(value_eur, 2),
                    'percentage': 0  # Wird unten berechnet
                }
        
        # Percentage Calculation
        for currency in positions:
            if total_value_eur > 0:
                positions[currency]['percentage'] = round(
                    (positions[currency]['value_eur'] / total_value_eur) * 100, 2
                )
        
        # Portfolio Summary erstellen
        self.portfolio_summary_cache = {
            'total_value_eur': round(total_value_eur, 2),
            'positions': positions,
            'currencies_count': len(positions),
            'largest_position': self._find_largest_position(positions),
            'diversification_score': self._calculate_diversification_score(positions),
            'last_updated': datetime.now().isoformat()
        }
        
        self.portfolio_cache_timestamp = datetime.now()
        
        return self.portfolio_summary_cache
    
    def _find_largest_position(self, positions: Dict[str, Dict]) -> Optional[Dict[str, Any]]:
        """Findet die größte Position im Portfolio"""
        if not positions:
            return None
        
        largest = max(positions.items(), key=lambda x: x[1]['value_eur'])
        return {
            'currency': largest[0],
            'value_eur': largest[1]['value_eur'],
            'percentage': largest[1]['percentage']
        }
    
    def _calculate_diversification_score(self, positions: Dict[str, Dict]) -> float:
        """Berechnet Diversification Score (0-1, höher = besser diversifiziert)"""
        if not positions:
            return 0.0
        
        # Herfindahl-Index basierte Diversifikation
        percentages = [pos['percentage'] / 100 for pos in positions.values()]
        herfindahl_index = sum(p**2 for p in percentages)
        
        # Diversification Score: 1 - HHI (normalisiert)
        diversification = 1 - herfindahl_index
        return round(diversification, 3)
    
    def update_account_balance(self, currency_code: str, available: str, 
                             locked: str = "0.00", total: str = None):
        """Aktualisiert Account Balance (für externe Updates)"""
        if total is None:
            total = str(float(available) + float(locked))
        
        self.account_balances[currency_code] = AccountBalance(
            currency_code=currency_code,
            available=available,
            locked=locked,
            total=total,
            last_updated=datetime.now()
        )
        
        # Portfolio Cache invalidieren
        self.portfolio_summary_cache = None
        self.portfolio_cache_timestamp = None
        
        # Event-Bus: Balance Update Event publizieren
        if self.event_bus:
            balance_update_event = {
                'event_type': 'account.balance.updated',
                'stream_id': f'account-balance-{currency_code}',
                'data': {
                    'currency_code': currency_code,
                    'available': available,
                    'locked': locked,
                    'total': total,
                    'updated_at': datetime.now().isoformat()
                },
                'source': self.module_name
            }
            # Publish asynchronous - ohne await in sync method
            import asyncio
            if asyncio.get_event_loop().is_running():
                asyncio.create_task(self.event_bus.publish(balance_update_event))
        
        self.logger.info(f"Account balance updated",
                       currency=currency_code,
                       available=available,
                       locked=locked,
                       total=total)
    
    def update_market_prices(self, prices: Dict[str, float]):
        """Aktualisiert Market Prices für Portfolio Valuation"""
        for currency, price in prices.items():
            if price > 0:
                self.mock_prices[currency] = float(price)
        
        # Portfolio Cache invalidieren
        self.portfolio_summary_cache = None
        self.portfolio_cache_timestamp = None
        
        # Event-Bus: Market Prices Update Event publizieren
        if self.event_bus and prices:
            price_update_event = {
                'event_type': 'market.prices.updated',
                'stream_id': 'market-prices',
                'data': {
                    'updated_prices': prices,
                    'currencies_updated': list(prices.keys()),
                    'updated_at': datetime.now().isoformat()
                },
                'source': self.module_name
            }
            # Publish asynchronous
            import asyncio
            if asyncio.get_event_loop().is_running():
                asyncio.create_task(self.event_bus.publish(price_update_event))
        
        self.logger.info(f"Market prices updated",
                       updated_currencies=list(prices.keys()))
    
    def get_balance_for_currency(self, currency_code: str) -> Optional[AccountBalance]:
        """Gibt Balance für spezifische Currency zurück"""
        return self.account_balances.get(currency_code)
    
    def get_total_portfolio_value_eur(self) -> float:
        """Gibt Total Portfolio Value in EUR zurück"""
        total_value = 0.0
        for currency, balance in self.account_balances.items():
            total_balance = float(balance.total)
            price_eur = self.mock_prices.get(currency, 1.0)
            total_value += total_balance * price_eur
        
        return round(total_value, 2)
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'account_balance',
            'description': 'Retrieves account balances and portfolio summary',
            'responsibility': 'Account balance retrieval logic only',
            'input_parameters': {
                'include_portfolio_summary': 'Whether to include portfolio summary (default: true)',
                'refresh_cache': 'Whether to refresh portfolio cache (default: false)',
                'filter_currencies': 'Optional list of currencies to filter'
            },
            'output_format': {
                'balances': 'Dictionary of currency balances with details',
                'currencies_count': 'Number of currencies with balances',
                'portfolio_summary': 'Optional portfolio valuation and analysis',
                'last_updated': 'Balance last update timestamp',
                'retrieval_timestamp': 'Balance retrieval timestamp'
            },
            'supported_currencies': list(self.account_balances.keys()),
            'market_prices': self.mock_prices,
            'cache_duration_seconds': 60,
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_balance_statistics(self) -> Dict[str, Any]:
        """Balance Retrieval Statistiken abrufen"""
        total_retrievals = len(self.balance_retrieval_history)
        
        if total_retrievals == 0:
            return {
                'total_retrievals': 0,
                'cached_results': len(self.balance_cache),
                'portfolio_cache_active': self.portfolio_summary_cache is not None
            }
        
        # Recent Activity
        recent_retrievals = [
            r for r in self.balance_retrieval_history
            if (datetime.now() - r['timestamp']).seconds < 3600  # Last hour
        ]
        
        # Cache Statistics
        cache_refreshes = sum(1 for r in self.balance_retrieval_history if r['cache_refreshed'])
        portfolio_inclusions = sum(1 for r in self.balance_retrieval_history if r['portfolio_included'])
        
        return {
            'total_retrievals': total_retrievals,
            'recent_retrievals_last_hour': len(recent_retrievals),
            'cached_results': len(self.balance_cache),
            'portfolio_cache_active': self.portfolio_summary_cache is not None,
            'cache_refresh_rate': round(cache_refreshes / total_retrievals * 100, 1) if total_retrievals > 0 else 0,
            'portfolio_inclusion_rate': round(portfolio_inclusions / total_retrievals * 100, 1) if total_retrievals > 0 else 0,
            'average_processing_time': self.average_execution_time,
            'supported_currencies_count': len(self.account_balances),
            'total_portfolio_value_eur': self.get_total_portfolio_value_eur()
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
