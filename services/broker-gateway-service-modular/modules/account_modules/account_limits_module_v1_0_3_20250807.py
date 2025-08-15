from typing import Dict, Any, Optional
import sys
from shared.common_imports import (
import asyncio
from ..single_function_module_base import SingleFunctionModule
"""
Account Limits Module - Single Function Module
Verantwortlich ausschließlich für Account Limits Retrieval Logic
"""

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

    datetime, timedelta, BaseModel, structlog
)


class AccountLimitsInfo(BaseModel):
    daily_withdrawal_limit: float
    monthly_trading_limit: float
    max_open_orders: int
    max_position_size: float
    verification_level: str
    last_updated: datetime


class WithdrawalLimits(BaseModel):
    currency_code: str
    daily_limit: float
    monthly_limit: float
    current_daily_used: float
    current_monthly_used: float
    remaining_daily: float
    remaining_monthly: float


class AccountLimitsResult(BaseModel):
    account_limits: Dict[str, Any]
    withdrawal_limits: Dict[str, Dict[str, Any]]
    current_usage: Dict[str, Any]
    limits_last_updated: datetime
    retrieval_timestamp: datetime


class AccountLimitsModule(SingleFunctionModule):
    """
    Single Function Module: Account Limits Retrieval
    Verantwortlichkeit: Ausschließlich Account-Limits-Retrieval-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("account_limits", event_bus)
        
        # Account Limits Configuration
        self.account_limits = AccountLimitsInfo(
            daily_withdrawal_limit=50000.0,  # €50k per day
            monthly_trading_limit=1000000.0,  # €1M per month
            max_open_orders=100,
            max_position_size=100000.0,  # €100k per position
            verification_level='fully_verified',
            last_updated=datetime.now()
        )
        
        # Withdrawal Limits per Currency
        self.withdrawal_limits_config = {
            'EUR': {'daily': 10000.0, 'monthly': 100000.0},
            'USD': {'daily': 10000.0, 'monthly': 100000.0},
            'BTC': {'daily': 1.0, 'monthly': 10.0},
            'ETH': {'daily': 10.0, 'monthly': 100.0}
        }
        
        # Mock Transaction History für Usage Calculation
        self.transaction_history = []
        
        # Limits Retrieval Statistics
        self.retrieval_history = []
        self.retrieval_counter = 0
        self.usage_calculation_cache = {}
        self.cache_timestamp = None
        
        # Risk Assessment Rules
        self.risk_rules = {
            'high_risk_threshold_eur': 25000.0,  # Above this = high risk
            'daily_limit_warning_threshold': 0.8,  # 80% of limit = warning
            'monthly_limit_warning_threshold': 0.9,  # 90% of limit = warning
            'max_consecutive_large_transactions': 5
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Account Limits Retrieval
        
        Args:
            input_data: {
                'include_usage_calculation': optional bool (default: true),
                'include_withdrawal_details': optional bool (default: true),
                'refresh_usage_cache': optional bool (default: false),
                'currency_filter': optional string - specific currency limits only
            }
            
        Returns:
            Dict mit Account-Limits-Result
        """
        include_usage = input_data.get('include_usage_calculation', True)
        include_withdrawal_details = input_data.get('include_withdrawal_details', True)
        refresh_cache = input_data.get('refresh_usage_cache', False)
        currency_filter = input_data.get('currency_filter')
        
        # Account Limits abrufen
        limits_result = await self._retrieve_account_limits(
            include_usage, include_withdrawal_details, refresh_cache, currency_filter
        )
        
        # Statistics Update
        self.retrieval_counter += 1
        
        # Retrieval History
        self.retrieval_history.append({
            'timestamp': datetime.now(),
            'include_usage': include_usage,
            'include_withdrawal_details': include_withdrawal_details,
            'currency_filter': currency_filter,
            'cache_refreshed': refresh_cache,
            'retrieval_id': self.retrieval_counter
        })
        
        # Limit History
        if len(self.retrieval_history) > 100:
            self.retrieval_history.pop(0)
        
        self.logger.info(f"Account limits retrieved successfully",
                       include_usage=include_usage,
                       include_withdrawal_details=include_withdrawal_details,
                       currency_filter=currency_filter,
                       retrieval_id=self.retrieval_counter)
        
        return {
            'success': True,
            'account_limits': limits_result.account_limits,
            'withdrawal_limits': limits_result.withdrawal_limits if include_withdrawal_details else {},
            'current_usage': limits_result.current_usage if include_usage else {},
            'limits_last_updated': limits_result.limits_last_updated.isoformat(),
            'retrieval_timestamp': limits_result.retrieval_timestamp.isoformat()
        }
    
    async def _retrieve_account_limits(self, include_usage: bool, 
                                     include_withdrawal_details: bool,
                                     refresh_cache: bool,
                                     currency_filter: Optional[str]) -> AccountLimitsResult:
        """Retrievt Account Limits mit optionalen Details"""
        
        # Basic Account Limits
        account_limits_dict = {
            'daily_withdrawal_limit': self.account_limits.daily_withdrawal_limit,
            'monthly_trading_limit': self.account_limits.monthly_trading_limit,
            'max_open_orders': self.account_limits.max_open_orders,
            'max_position_size': self.account_limits.max_position_size,
            'verification_level': self.account_limits.verification_level,
            'last_updated': self.account_limits.last_updated.isoformat()
        }
        
        # Withdrawal Limits Details
        withdrawal_limits = {}
        if include_withdrawal_details:
            withdrawal_limits = await self._calculate_withdrawal_limits_details(
                currency_filter, refresh_cache
            )
        
        # Current Usage Calculation
        current_usage = {}
        if include_usage:
            current_usage = await self._calculate_current_usage(refresh_cache)
        
        return AccountLimitsResult(
            account_limits=account_limits_dict,
            withdrawal_limits=withdrawal_limits,
            current_usage=current_usage,
            limits_last_updated=self.account_limits.last_updated,
            retrieval_timestamp=datetime.now()
        )
    
    async def _calculate_withdrawal_limits_details(self, currency_filter: Optional[str],
                                                 refresh_cache: bool) -> Dict[str, Dict[str, Any]]:
        """Berechnet detaillierte Withdrawal Limits pro Currency"""
        
        withdrawal_limits = {}
        
        # Filter currencies if requested
        currencies = [currency_filter] if currency_filter else list(self.withdrawal_limits_config.keys())
        
        for currency in currencies:
            if currency not in self.withdrawal_limits_config:
                continue
                
            limits_config = self.withdrawal_limits_config[currency]
            
            # Calculate current usage for this currency
            daily_used, monthly_used = await self._calculate_currency_withdrawal_usage(currency)
            
            # Calculate remaining limits
            remaining_daily = max(0, limits_config['daily'] - daily_used)
            remaining_monthly = max(0, limits_config['monthly'] - monthly_used)
            
            withdrawal_limits[currency] = {
                'currency_code': currency,
                'daily_limit': limits_config['daily'],
                'monthly_limit': limits_config['monthly'],
                'current_daily_used': daily_used,
                'current_monthly_used': monthly_used,
                'remaining_daily': remaining_daily,
                'remaining_monthly': remaining_monthly,
                'daily_usage_percentage': round((daily_used / limits_config['daily']) * 100, 1) if limits_config['daily'] > 0 else 0,
                'monthly_usage_percentage': round((monthly_used / limits_config['monthly']) * 100, 1) if limits_config['monthly'] > 0 else 0,
                'warning_status': self._assess_withdrawal_warning_status(daily_used, monthly_used, limits_config)
            }
        
        return withdrawal_limits
    
    async def _calculate_currency_withdrawal_usage(self, currency: str) -> tuple:
        """Berechnet aktuelle Withdrawal Usage für spezifische Currency"""
        
        today = datetime.now().date()
        month_start = datetime.now().replace(day=1).date()
        
        daily_used = 0.0
        monthly_used = 0.0
        
        # Mock calculation (in production würde aus transaction_history kommen)
        # Für Demo: simuliere einige Withdrawals
        mock_withdrawals = [
            {'currency': 'EUR', 'amount': 500.0, 'date': today},
            {'currency': 'EUR', 'amount': 1000.0, 'date': today - timedelta(days=2)},
            {'currency': 'BTC', 'amount': 0.1, 'date': today},
            {'currency': 'ETH', 'amount': 1.5, 'date': today - timedelta(days=1)},
        ]
        
        for withdrawal in mock_withdrawals:
            if withdrawal['currency'] == currency:
                withdrawal_date = withdrawal['date']
                amount = withdrawal['amount']
                
                # Daily calculation
                if withdrawal_date == today:
                    daily_used += amount
                
                # Monthly calculation  
                if withdrawal_date >= month_start:
                    monthly_used += amount
        
        return daily_used, monthly_used
    

        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())

    def _assess_withdrawal_warning_status(self, daily_used: float, monthly_used: float, 
                                        limits_config: Dict[str, float]) -> str:
        """Bewertet Warning Status für Withdrawal Limits"""
        
        daily_percentage = (daily_used / limits_config['daily']) if limits_config['daily'] > 0 else 0
        monthly_percentage = (monthly_used / limits_config['monthly']) if limits_config['monthly'] > 0 else 0
        
        # Determine warning level
        if daily_percentage >= 1.0 or monthly_percentage >= 1.0:
            return 'limit_exceeded'
        elif (daily_percentage >= self.risk_rules['daily_limit_warning_threshold'] or 
              monthly_percentage >= self.risk_rules['monthly_limit_warning_threshold']):
            return 'approaching_limit'
        elif daily_percentage >= 0.5 or monthly_percentage >= 0.5:
            return 'moderate_usage'
        else:
            return 'normal'
    
    async def _calculate_current_usage(self, refresh_cache: bool = False) -> Dict[str, Any]:
        """Berechnet aktuelle Usage gegen alle Limits"""
        
        # Cache Check
        if (not refresh_cache and 
            self.usage_calculation_cache and 
            self.cache_timestamp and
            (datetime.now() - self.cache_timestamp).seconds < 300):  # 5 minutes cache
            
            return self.usage_calculation_cache
        
        today = datetime.now().date()
        month_start = datetime.now().replace(day=1).date()
        
        # Calculate current usage (Mock Data)
        daily_withdrawals = 1500.0  # EUR
        monthly_trading = 25000.0   # EUR
        open_orders_count = 3
        largest_position_eur = 15000.0
        
        # Risk Assessment
        risk_score = await self._calculate_risk_score(daily_withdrawals, monthly_trading, largest_position_eur)
        
        # Usage Summary
        usage_summary = {
            'daily_withdrawals_used': daily_withdrawals,
            'daily_withdrawals_limit': self.account_limits.daily_withdrawal_limit,
            'daily_withdrawals_remaining': max(0, self.account_limits.daily_withdrawal_limit - daily_withdrawals),
            'daily_withdrawal_percentage': round((daily_withdrawals / self.account_limits.daily_withdrawal_limit) * 100, 1),
            
            'monthly_trading_used': monthly_trading,
            'monthly_trading_limit': self.account_limits.monthly_trading_limit,
            'monthly_trading_remaining': max(0, self.account_limits.monthly_trading_limit - monthly_trading),
            'monthly_trading_percentage': round((monthly_trading / self.account_limits.monthly_trading_limit) * 100, 1),
            
            'open_orders_count': open_orders_count,
            'max_open_orders_limit': self.account_limits.max_open_orders,
            'open_orders_remaining': max(0, self.account_limits.max_open_orders - open_orders_count),
            
            'largest_position_eur': largest_position_eur,
            'max_position_size_limit': self.account_limits.max_position_size,
            'position_size_compliance': largest_position_eur <= self.account_limits.max_position_size,
            
            'risk_assessment': risk_score,
            'last_calculated': datetime.now().isoformat()
        }
        
        # Cache Update
        self.usage_calculation_cache = usage_summary
        self.cache_timestamp = datetime.now()
        
        return usage_summary
    
    async def _calculate_risk_score(self, daily_withdrawals: float, 
                                  monthly_trading: float, largest_position: float) -> Dict[str, Any]:
        """Berechnet Risk Score basierend auf Usage Patterns"""
        
        risk_factors = []
        risk_score = 0
        
        # High withdrawal activity
        if daily_withdrawals > self.risk_rules['high_risk_threshold_eur']:
            risk_factors.append('high_daily_withdrawals')
            risk_score += 2
        
        # High trading volume
        if monthly_trading > (self.account_limits.monthly_trading_limit * 0.7):
            risk_factors.append('high_monthly_trading')
            risk_score += 2
        
        # Large position size
        if largest_position > (self.account_limits.max_position_size * 0.8):
            risk_factors.append('large_position_concentration')
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 4:
            risk_level = 'high'
        elif risk_score >= 2:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'recommendations': self._generate_risk_recommendations(risk_level, risk_factors)
        }
    
    def _generate_risk_recommendations(self, risk_level: str, risk_factors: list) -> list:
        """Generiert Empfehlungen basierend auf Risk Assessment"""
        
        recommendations = []
        
        if risk_level == 'high':
            recommendations.append('Consider reducing position sizes')
            recommendations.append('Monitor withdrawal patterns closely')
            
        if 'high_daily_withdrawals' in risk_factors:
            recommendations.append('Spread withdrawals across multiple days')
            
        if 'high_monthly_trading' in risk_factors:
            recommendations.append('Monitor monthly trading limit closely')
            
        if 'large_position_concentration' in risk_factors:
            recommendations.append('Consider diversifying positions')
            
        return recommendations
    
    def update_account_limits(self, limits_update: Dict[str, Any]):
        """Aktualisiert Account Limits (für externe Updates)"""
        
        updated_fields = []
        
        if 'daily_withdrawal_limit' in limits_update:
            self.account_limits.daily_withdrawal_limit = float(limits_update['daily_withdrawal_limit'])
            updated_fields.append('daily_withdrawal_limit')
        
        if 'monthly_trading_limit' in limits_update:
            self.account_limits.monthly_trading_limit = float(limits_update['monthly_trading_limit'])
            updated_fields.append('monthly_trading_limit')
        
        if 'max_open_orders' in limits_update:
            self.account_limits.max_open_orders = int(limits_update['max_open_orders'])
            updated_fields.append('max_open_orders')
        
        if 'max_position_size' in limits_update:
            self.account_limits.max_position_size = float(limits_update['max_position_size'])
            updated_fields.append('max_position_size')
        
        if 'verification_level' in limits_update:
            self.account_limits.verification_level = str(limits_update['verification_level'])
            updated_fields.append('verification_level')
        
        if updated_fields:
            self.account_limits.last_updated = datetime.now()
            
            # Invalidate cache
            self.usage_calculation_cache = {}
            self.cache_timestamp = None
            
            self.logger.info(f"Account limits updated",
                           updated_fields=updated_fields)
    
    def update_withdrawal_limits(self, currency: str, daily_limit: float, monthly_limit: float):
        """Aktualisiert Withdrawal Limits für Currency"""
        
        self.withdrawal_limits_config[currency.upper()] = {
            'daily': daily_limit,
            'monthly': monthly_limit
        }
        
        # Invalidate cache
        self.usage_calculation_cache = {}
        self.cache_timestamp = None
        
        self.logger.info(f"Withdrawal limits updated",
                       currency=currency,
                       daily_limit=daily_limit,
                       monthly_limit=monthly_limit)
    
    def get_limit_for_operation(self, operation: str, currency: str, amount: float) -> Dict[str, Any]:
        """Prüft ob Operation innerhalb der Limits liegt"""
        
        if operation == 'withdrawal':
            if currency in self.withdrawal_limits_config:
                limits = self.withdrawal_limits_config[currency]
                
                # Mock current usage check
                daily_used, monthly_used = 500.0, 5000.0  # Mock values
                
                daily_remaining = limits['daily'] - daily_used
                monthly_remaining = limits['monthly'] - monthly_used
                
                return {
                    'allowed': amount <= daily_remaining and amount <= monthly_remaining,
                    'reason': 'Within limits' if amount <= daily_remaining and amount <= monthly_remaining else 'Exceeds limits',
                    'daily_remaining': daily_remaining,
                    'monthly_remaining': monthly_remaining,
                    'amount_requested': amount
                }
        
        elif operation == 'trading':
            # Check monthly trading limit (für EUR)
            if currency == 'EUR':
                monthly_used = 25000.0  # Mock
                monthly_remaining = self.account_limits.monthly_trading_limit - monthly_used
                
                return {
                    'allowed': amount <= monthly_remaining,
                    'reason': 'Within limits' if amount <= monthly_remaining else 'Exceeds monthly trading limit',
                    'monthly_remaining': monthly_remaining,
                    'amount_requested': amount
                }
        
        return {
            'allowed': True,
            'reason': 'No specific limits apply'
        }
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'account_limits',
            'description': 'Retrieves account limits, restrictions and usage statistics',
            'responsibility': 'Account limits retrieval logic only',
            'input_parameters': {
                'include_usage_calculation': 'Whether to include current usage calculation (default: true)',
                'include_withdrawal_details': 'Whether to include detailed withdrawal limits (default: true)',
                'refresh_usage_cache': 'Whether to refresh usage calculation cache (default: false)',
                'currency_filter': 'Optional currency to filter withdrawal limits'
            },
            'output_format': {
                'account_limits': 'Basic account limits configuration',
                'withdrawal_limits': 'Detailed withdrawal limits per currency',
                'current_usage': 'Current usage statistics against limits',
                'limits_last_updated': 'Timestamp of last limits update',
                'retrieval_timestamp': 'Limits retrieval timestamp'
            },
            'supported_currencies': list(self.withdrawal_limits_config.keys()),
            'risk_assessment_rules': self.risk_rules,
            'cache_duration_seconds': 300,
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_limits_statistics(self) -> Dict[str, Any]:
        """Account Limits Module Statistiken"""
        total_retrievals = len(self.retrieval_history)
        
        if total_retrievals == 0:
            return {
                'total_retrievals': 0,
                'cache_active': self.usage_calculation_cache is not None,
                'supported_currencies': len(self.withdrawal_limits_config)
            }
        
        # Usage inclusion rate
        usage_inclusions = sum(1 for r in self.retrieval_history if r['include_usage'])
        usage_inclusion_rate = round((usage_inclusions / total_retrievals) * 100, 1) if total_retrievals > 0 else 0
        
        # Withdrawal details inclusion rate
        withdrawal_inclusions = sum(1 for r in self.retrieval_history if r['include_withdrawal_details'])
        withdrawal_inclusion_rate = round((withdrawal_inclusions / total_retrievals) * 100, 1) if total_retrievals > 0 else 0
        
        # Cache refresh rate
        cache_refreshes = sum(1 for r in self.retrieval_history if r['cache_refreshed'])
        cache_refresh_rate = round((cache_refreshes / total_retrievals) * 100, 1) if total_retrievals > 0 else 0
        
        # Recent Activity
        recent_retrievals = [
            r for r in self.retrieval_history
            if (datetime.now() - r['timestamp']).seconds < 3600  # Last hour
        ]
        
        return {
            'total_retrievals': total_retrievals,
            'recent_retrievals_last_hour': len(recent_retrievals),
            'usage_inclusion_rate_percent': usage_inclusion_rate,
            'withdrawal_details_inclusion_rate_percent': withdrawal_inclusion_rate,
            'cache_refresh_rate_percent': cache_refresh_rate,
            'cache_active': bool(self.usage_calculation_cache),
            'supported_currencies': len(self.withdrawal_limits_config),
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
