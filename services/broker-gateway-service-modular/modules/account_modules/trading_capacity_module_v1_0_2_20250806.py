from typing import Dict, Any, Optional, List
import sys
from shared.common_imports import (
import asyncio
from ..single_function_module_base import SingleFunctionModule
"""
Trading Capacity Module - Single Function Module
Verantwortlich ausschließlich für Trading Capacity Assessment Logic
"""

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

    datetime, timedelta, BaseModel, structlog
)


class TradingCapacityRequest(BaseModel):
    currency_code: str
    amount: float
    side: str  # 'buy' or 'sell'
    instrument: Optional[str] = None
    order_type: Optional[str] = 'market'


class CapacityAssessmentResult(BaseModel):
    has_capacity: bool
    capacity_score: float  # 0-100, higher = better capacity
    limiting_factors: List[str]
    recommendations: List[str]
    balance_sufficient: bool
    limits_sufficient: bool
    risk_acceptable: bool
    estimated_fees: float
    maximum_tradeable_amount: float


class TradingCapacityModule(SingleFunctionModule):
    """
    Single Function Module: Trading Capacity Assessment
    Verantwortlichkeit: Ausschließlich Trading-Capacity-Assessment-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("trading_capacity", event_bus)
        
        # Mock Account Balances
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
        
        # Account Limits
        self.account_limits = {
            'daily_withdrawal_limit': 50000.0,
            'monthly_trading_limit': 1000000.0,
            'max_open_orders': 100,
            'max_position_size': 100000.0,
            'verification_level': 'fully_verified'
        }
        
        # Trading Fees Configuration
        self.trading_fees = {
            'market_order': 0.001,  # 0.1%
            'limit_order': 0.0005,  # 0.05%
            'stop_order': 0.001,    # 0.1%
            'minimum_fee_eur': 0.50
        }
        
        # Mock Current Usage Data
        self.current_usage = {
            'daily_withdrawals_used': 1500.0,
            'monthly_trading_used': 25000.0,
            'open_orders_count': 3,
            'largest_position_eur': 15000.0
        }
        
        # Capacity Assessment History
        self.assessment_history = []
        self.assessment_counter = 0
        
        # Risk Assessment Parameters
        self.risk_parameters = {
            'max_single_trade_percentage': 20.0,  # Max 20% of portfolio in single trade
            'max_currency_exposure_percentage': 50.0,  # Max 50% in single currency
            'min_emergency_reserve_eur': 1000.0,  # Always keep 1k EUR reserve
            'high_risk_amount_threshold': 10000.0,  # >10k EUR = high risk trade
            'volatility_multipliers': {
                'EUR': 1.0,
                'USD': 1.1,
                'BTC': 2.5,  # High volatility
                'ETH': 2.0   # High volatility
            }
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Trading Capacity Assessment
        
        Args:
            input_data: {
                'currency_code': required string,
                'amount': required float,
                'side': required string ('buy' or 'sell'),
                'instrument': optional string,
                'order_type': optional string (default: 'market'),
                'include_detailed_assessment': optional bool (default: true)
            }
            
        Returns:
            Dict mit Trading-Capacity-Assessment-Result
        """
        try:
            # Trading Request validieren
            trading_request = TradingCapacityRequest(
                currency_code=input_data.get('currency_code'),
                amount=float(input_data.get('amount')),
                side=input_data.get('side'),
                instrument=input_data.get('instrument'),
                order_type=input_data.get('order_type', 'market')
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Invalid trading capacity request: {str(e)}'
            }
        
        include_detailed = input_data.get('include_detailed_assessment', True)
        
        # Capacity Assessment durchführen
        capacity_result = await self._assess_trading_capacity(trading_request, include_detailed)
        
        # Statistics Update
        self.assessment_counter += 1
        
        # Assessment History
        self.assessment_history.append({
            'timestamp': datetime.now(),
            'currency_code': trading_request.currency_code,
            'amount': trading_request.amount,
            'side': trading_request.side,
            'has_capacity': capacity_result.has_capacity,
            'capacity_score': capacity_result.capacity_score,
            'assessment_id': self.assessment_counter
        })
        
        # Limit History
        if len(self.assessment_history) > 200:
            self.assessment_history.pop(0)
        
        self.logger.info(f"Trading capacity assessed",
                       currency_code=trading_request.currency_code,
                       amount=trading_request.amount,
                       side=trading_request.side,
                       has_capacity=capacity_result.has_capacity,
                       capacity_score=capacity_result.capacity_score,
                       assessment_id=self.assessment_counter)
        
        return {
            'success': True,
            'has_capacity': capacity_result.has_capacity,
            'capacity_score': capacity_result.capacity_score,
            'limiting_factors': capacity_result.limiting_factors,
            'recommendations': capacity_result.recommendations,
            'balance_sufficient': capacity_result.balance_sufficient,
            'limits_sufficient': capacity_result.limits_sufficient,
            'risk_acceptable': capacity_result.risk_acceptable,
            'estimated_fees': capacity_result.estimated_fees,
            'maximum_tradeable_amount': capacity_result.maximum_tradeable_amount
        }
    
    async def _assess_trading_capacity(self, request: TradingCapacityRequest, 
                                     include_detailed: bool) -> CapacityAssessmentResult:
        """Führt umfassende Trading Capacity Assessment durch"""
        
        limiting_factors = []
        recommendations = []
        capacity_score = 100.0  # Start mit perfekter Capacity
        
        # 1. Balance Assessment
        balance_assessment = await self._assess_balance_capacity(request)
        balance_sufficient = balance_assessment['sufficient']
        
        if not balance_sufficient:
            limiting_factors.extend(balance_assessment['factors'])
            recommendations.extend(balance_assessment['recommendations'])
            capacity_score -= 50  # Major penalty for insufficient balance
        
        # 2. Limits Assessment
        limits_assessment = await self._assess_limits_capacity(request)
        limits_sufficient = limits_assessment['sufficient']
        
        if not limits_sufficient:
            limiting_factors.extend(limits_assessment['factors'])
            recommendations.extend(limits_assessment['recommendations'])
            capacity_score -= 30  # Moderate penalty for limit issues
        
        # 3. Risk Assessment
        risk_assessment = await self._assess_risk_capacity(request)
        risk_acceptable = risk_assessment['acceptable']
        
        if not risk_acceptable:
            limiting_factors.extend(risk_assessment['factors'])
            recommendations.extend(risk_assessment['recommendations'])
            capacity_score -= 20  # Penalty for risk issues
        
        # 4. Fee Calculation
        estimated_fees = await self._calculate_estimated_fees(request)
        
        # 5. Maximum Tradeable Amount
        max_amount = await self._calculate_maximum_tradeable_amount(request)
        
        # Capacity Score anpassen basierend auf anderen Faktoren
        capacity_score = await self._adjust_capacity_score(
            capacity_score, request, balance_assessment, limits_assessment, risk_assessment
        )
        
        # Final Capacity Decision
        has_capacity = (balance_sufficient and limits_sufficient and 
                       risk_acceptable and capacity_score >= 50)
        
        return CapacityAssessmentResult(
            has_capacity=has_capacity,
            capacity_score=max(0, round(capacity_score, 1)),
            limiting_factors=limiting_factors,
            recommendations=recommendations,
            balance_sufficient=balance_sufficient,
            limits_sufficient=limits_sufficient,
            risk_acceptable=risk_acceptable,
            estimated_fees=estimated_fees,
            maximum_tradeable_amount=max_amount
        )
    
    async def _assess_balance_capacity(self, request: TradingCapacityRequest) -> Dict[str, Any]:
        """Bewertet Balance Capacity für Trading Request"""
        
        factors = []
        recommendations = []
        sufficient = True
        
        currency = request.currency_code.upper()
        amount = request.amount
        side = request.side.lower()
        
        # Get current balance
        balance_info = self.account_balances.get(currency)
        
        if not balance_info:
            factors.append(f'No {currency} balance found')
            recommendations.append(f'Deposit {currency} to enable trading')
            return {'sufficient': False, 'factors': factors, 'recommendations': recommendations}
        
        available = float(balance_info['available'])
        
        # Balance Requirements je nach Side
        if side == 'buy':
            # Für Buy Orders: benötigen Fiat Currency (EUR/USD)
            if currency in ['BTC', 'ETH']:
                # Buying crypto - need fiat
                required_currency = 'EUR'  # Default to EUR
                required_balance = self.account_balances.get(required_currency)
                
                if not required_balance:
                    factors.append(f'No {required_currency} balance for buying {currency}')
                    sufficient = False
                else:
                    required_available = float(required_balance['available'])
                    estimated_cost = amount  # Assuming amount is in EUR for crypto purchases
                    
                    if estimated_cost > required_available:
                        factors.append(f'Insufficient {required_currency} balance for purchase')
                        recommendations.append(f'Need {estimated_cost - required_available:.2f} more {required_currency}')
                        sufficient = False
                    
                    # Reserve Check
                    if required_available - estimated_cost < self.risk_parameters['min_emergency_reserve_eur']:
                        factors.append('Purchase would deplete emergency reserves')
                        recommendations.append('Consider smaller purchase amount to maintain reserves')
        
        elif side == 'sell':
            # Für Sell Orders: benötigen das Asset selbst
            if amount > available:
                factors.append(f'Insufficient {currency} balance for sale')
                recommendations.append(f'Maximum sellable amount: {available} {currency}')
                sufficient = False
            
            # Partial Sale Warning
            if amount > available * 0.8:
                recommendations.append('Selling >80% of holdings - consider keeping some position')
        
        return {
            'sufficient': sufficient,
            'factors': factors,
            'recommendations': recommendations
        }
    
    async def _assess_limits_capacity(self, request: TradingCapacityRequest) -> Dict[str, Any]:
        """Bewertet Limits Capacity für Trading Request"""
        
        factors = []
        recommendations = []
        sufficient = True
        
        amount_eur = request.amount  # Assuming amount is in EUR equivalent
        
        # Monthly Trading Limit Check
        monthly_used = self.current_usage['monthly_trading_used']
        monthly_limit = self.account_limits['monthly_trading_limit']
        monthly_remaining = monthly_limit - monthly_used
        
        if amount_eur > monthly_remaining:
            factors.append('Monthly trading limit exceeded')
            recommendations.append(f'Maximum tradeable this month: €{monthly_remaining:.2f}')
            sufficient = False
        elif amount_eur > monthly_remaining * 0.9:
            recommendations.append('Trade would use >90% of remaining monthly limit')
        
        # Open Orders Limit Check
        open_orders = self.current_usage['open_orders_count']
        max_orders = self.account_limits['max_open_orders']
        
        if open_orders >= max_orders:
            factors.append('Maximum open orders limit reached')
            recommendations.append('Close existing orders before placing new ones')
            sufficient = False
        elif open_orders > max_orders * 0.8:
            recommendations.append('Approaching maximum open orders limit')
        
        # Position Size Limit Check
        max_position = self.account_limits['max_position_size']
        
        if amount_eur > max_position:
            factors.append('Trade exceeds maximum position size limit')
            recommendations.append(f'Maximum position size: €{max_position:.2f}')
            sufficient = False
        
        return {
            'sufficient': sufficient,
            'factors': factors,
            'recommendations': recommendations
        }
    
    async def _assess_risk_capacity(self, request: TradingCapacityRequest) -> Dict[str, Any]:
        """Bewertet Risk Capacity für Trading Request"""
        
        factors = []
        recommendations = []
        acceptable = True
        
        amount_eur = request.amount
        currency = request.currency_code.upper()
        
        # Portfolio Concentration Risk
        total_portfolio_value = await self._calculate_total_portfolio_value()
        trade_percentage = (amount_eur / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
        
        if trade_percentage > self.risk_parameters['max_single_trade_percentage']:
            factors.append('Single trade exceeds portfolio risk threshold')
            recommendations.append(f'Consider reducing trade size to <{self.risk_parameters["max_single_trade_percentage"]}% of portfolio')
            acceptable = False
        
        # High Risk Amount
        if amount_eur > self.risk_parameters['high_risk_amount_threshold']:
            recommendations.append('Large trade amount - consider splitting into smaller trades')
        
        # Currency-specific Risk
        volatility_multiplier = self.risk_parameters['volatility_multipliers'].get(currency, 1.0)
        risk_adjusted_amount = amount_eur * volatility_multiplier
        
        if risk_adjusted_amount > self.risk_parameters['high_risk_amount_threshold'] * 1.5:
            factors.append(f'High volatility currency increases risk exposure')
            recommendations.append(f'Consider smaller position in volatile asset {currency}')
        
        # Emergency Reserve Risk
        if request.side.lower() == 'buy' and currency in ['EUR', 'USD']:
            remaining_fiat = await self._calculate_remaining_fiat_after_trade(request)
            if remaining_fiat < self.risk_parameters['min_emergency_reserve_eur']:
                factors.append('Trade would deplete emergency fiat reserves')
                recommendations.append('Maintain minimum fiat balance for emergencies')
                acceptable = False
        
        return {
            'acceptable': acceptable,
            'factors': factors,
            'recommendations': recommendations
        }
    
    async def _calculate_estimated_fees(self, request: TradingCapacityRequest) -> float:
        """Berechnet geschätzte Trading Fees"""
        
        order_type = request.order_type or 'market'
        fee_rate = self.trading_fees.get(order_type, self.trading_fees['market_order'])
        
        amount_eur = request.amount
        calculated_fee = amount_eur * fee_rate
        
        # Minimum Fee beachten
        min_fee = self.trading_fees['minimum_fee_eur']
        estimated_fee = max(calculated_fee, min_fee)
        
        return round(estimated_fee, 2)
    
    async def _calculate_maximum_tradeable_amount(self, request: TradingCapacityRequest) -> float:
        """Berechnet maximal handelbaren Betrag"""
        
        currency = request.currency_code.upper()
        side = request.side.lower()
        
        # Balance-basierte Limits
        if side == 'sell' and currency in self.account_balances:
            balance_limit = float(self.account_balances[currency]['available'])
        else:
            # Für Buy Orders: EUR/USD Balance als Limit
            fiat_currency = 'EUR'  # Default
            balance_limit = float(self.account_balances.get(fiat_currency, {}).get('available', '0'))
        
        # Limits-basierte Beschränkungen
        monthly_remaining = self.account_limits['monthly_trading_limit'] - self.current_usage['monthly_trading_used']
        position_size_limit = self.account_limits['max_position_size']
        
        # Risk-basierte Beschränkungen
        total_portfolio = await self._calculate_total_portfolio_value()
        risk_limit = (total_portfolio * self.risk_parameters['max_single_trade_percentage']) / 100
        
        # Minimum aller Limits
        max_tradeable = min(balance_limit, monthly_remaining, position_size_limit, risk_limit)
        
        # Fees abziehen
        estimated_fee_rate = self.trading_fees.get(request.order_type or 'market', self.trading_fees['market_order'])
        max_after_fees = max_tradeable / (1 + estimated_fee_rate)
        
        return round(max(0, max_after_fees), 2)
    
    async def _adjust_capacity_score(self, base_score: float, request: TradingCapacityRequest,
                                   balance_assessment: Dict, limits_assessment: Dict, 
                                   risk_assessment: Dict) -> float:
        """Adjustiert Capacity Score basierend auf zusätzlichen Faktoren"""
        
        adjusted_score = base_score
        
        # Verification Level Bonus
        if self.account_limits['verification_level'] == 'fully_verified':
            adjusted_score += 5
        
        # Order Type Adjustment
        if request.order_type == 'limit':
            adjusted_score += 2  # Limit orders are less risky
        elif request.order_type == 'stop':
            adjusted_score -= 2  # Stop orders are riskier
        
        # Amount Size Adjustment
        amount_eur = request.amount
        if amount_eur < 100:  # Small trade
            adjusted_score += 3
        elif amount_eur > 10000:  # Large trade
            adjusted_score -= 5
        
        # Currency Stability Adjustment
        volatility_multiplier = self.risk_parameters['volatility_multipliers'].get(
            request.currency_code.upper(), 1.0
        )
        if volatility_multiplier > 2.0:  # High volatility
            adjusted_score -= 5
        elif volatility_multiplier == 1.0:  # Stable currency
            adjusted_score += 2
        
        return adjusted_score
    
    async def _calculate_total_portfolio_value(self) -> float:
        """Berechnet Total Portfolio Value in EUR"""
        
        # Mock prices (in production from market data service)
        mock_prices = {
            'EUR': 1.0,
            'USD': 0.85,
            'BTC': 45000.0,
            'ETH': 2800.0
        }
        
        total_value = 0.0
        for currency, balance_info in self.account_balances.items():
            balance = float(balance_info['total'])
            price = mock_prices.get(currency, 1.0)
            total_value += balance * price
        
        return total_value
    
    async def _calculate_remaining_fiat_after_trade(self, request: TradingCapacityRequest) -> float:
        """Berechnet verbleibendes Fiat nach Trade"""
        
        if request.side.lower() == 'sell':
            return float(self.account_balances.get('EUR', {}).get('available', '0'))
        
        # For buy orders
        current_eur = float(self.account_balances.get('EUR', {}).get('available', '0'))
        estimated_cost = request.amount + await self._calculate_estimated_fees(request)
        
        return max(0, current_eur - estimated_cost)
    

        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())

    def get_capacity_summary(self, currency: str = None) -> Dict[str, Any]:
        """Gibt Capacity Summary zurück"""
        
        summary = {
            'overall_capacity_status': 'good',  # good, limited, restricted
            'balance_status': {},
            'limits_utilization': {},
            'risk_indicators': {}
        }
        
        # Balance Status
        for curr, balance in self.account_balances.items():
            if currency and curr != currency.upper():
                continue
                
            available = float(balance['available'])
            summary['balance_status'][curr] = {
                'available': available,
                'status': 'good' if available > 100 else 'low' if available > 10 else 'critical'
            }
        
        # Limits Utilization
        monthly_utilization = (self.current_usage['monthly_trading_used'] / 
                             self.account_limits['monthly_trading_limit']) * 100
        
        orders_utilization = (self.current_usage['open_orders_count'] / 
                            self.account_limits['max_open_orders']) * 100
        
        summary['limits_utilization'] = {
            'monthly_trading_percent': round(monthly_utilization, 1),
            'open_orders_percent': round(orders_utilization, 1),
            'status': 'good' if monthly_utilization < 70 else 'approaching_limit'
        }
        
        # Risk Indicators
        total_portfolio = self.get_total_portfolio_value_sync()
        largest_position_pct = (self.current_usage['largest_position_eur'] / total_portfolio) * 100
        
        summary['risk_indicators'] = {
            'largest_position_percentage': round(largest_position_pct, 1),
            'portfolio_concentration': 'low' if largest_position_pct < 30 else 'medium' if largest_position_pct < 50 else 'high'
        }
        
        return summary
    
    def get_total_portfolio_value_sync(self) -> float:
        """Synchrone Version der Portfolio Value Berechnung"""
        mock_prices = {'EUR': 1.0, 'USD': 0.85, 'BTC': 45000.0, 'ETH': 2800.0}
        total = 0.0
        for currency, balance_info in self.account_balances.items():
            balance = float(balance_info['total'])
            price = mock_prices.get(currency, 1.0)
            total += balance * price
        return total
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'trading_capacity',
            'description': 'Assesses trading capacity based on balances, limits and risk parameters',
            'responsibility': 'Trading capacity assessment logic only',
            'input_parameters': {
                'currency_code': 'Required currency code for trading',
                'amount': 'Required trade amount in EUR equivalent',
                'side': 'Required trade side (buy or sell)',
                'instrument': 'Optional trading instrument',
                'order_type': 'Optional order type (market, limit, stop)',
                'include_detailed_assessment': 'Whether to include detailed assessment (default: true)'
            },
            'output_format': {
                'has_capacity': 'Whether account has capacity for the trade',
                'capacity_score': 'Capacity score from 0-100',
                'limiting_factors': 'List of factors limiting trading capacity',
                'recommendations': 'List of recommendations to improve capacity',
                'balance_sufficient': 'Whether balance is sufficient',
                'limits_sufficient': 'Whether account limits allow the trade',
                'risk_acceptable': 'Whether risk level is acceptable',
                'estimated_fees': 'Estimated trading fees for the trade',
                'maximum_tradeable_amount': 'Maximum amount that can be traded'
            },
            'supported_currencies': list(self.account_balances.keys()),
            'supported_order_types': list(self.trading_fees.keys()),
            'risk_parameters': self.risk_parameters,
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_capacity_statistics(self) -> Dict[str, Any]:
        """Trading Capacity Module Statistiken"""
        total_assessments = len(self.assessment_history)
        
        if total_assessments == 0:
            return {
                'total_assessments': 0,
                'supported_currencies': len(self.account_balances),
                'overall_capacity_status': 'unknown'
            }
        
        # Success Rate
        successful_assessments = sum(1 for a in self.assessment_history if a['has_capacity'])
        success_rate = round((successful_assessments / total_assessments) * 100, 1) if total_assessments > 0 else 0
        
        # Average Capacity Score
        capacity_scores = [a['capacity_score'] for a in self.assessment_history]
        avg_capacity_score = round(sum(capacity_scores) / len(capacity_scores), 1) if capacity_scores else 0
        
        # Currency Distribution
        currency_distribution = {}
        for assessment in self.assessment_history:
            currency = assessment['currency_code']
            currency_distribution[currency] = currency_distribution.get(currency, 0) + 1
        
        # Recent Activity
        recent_assessments = [
            a for a in self.assessment_history
            if (datetime.now() - a['timestamp']).seconds < 3600  # Last hour
        ]
        
        return {
            'total_assessments': total_assessments,
            'successful_assessments': successful_assessments,
            'success_rate_percent': success_rate,
            'average_capacity_score': avg_capacity_score,
            'recent_assessments_last_hour': len(recent_assessments),
            'currency_assessment_distribution': dict(sorted(
                currency_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'supported_currencies': len(self.account_balances),
            'overall_capacity_status': 'good' if avg_capacity_score > 70 else 'limited' if avg_capacity_score > 40 else 'restricted',
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
