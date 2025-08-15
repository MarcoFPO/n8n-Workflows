from typing import Dict, Any, List, Optional
import sys
from shared.common_imports import (
import asyncio
from ..single_function_module_base import SingleFunctionModule
"""
Withdrawal Processing Module - Single Function Module
Verantwortlich ausschließlich für Withdrawal Processing Logic
"""

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

    datetime, timedelta, BaseModel, structlog
)


class WithdrawalRequest(BaseModel):
    currency_code: str
    amount: str
    destination_address: Optional[str] = None
    destination_account: Optional[str] = None
    withdrawal_method: str = 'bank_transfer'  # bank_transfer, crypto_transfer, card
    description: Optional[str] = None
    priority: str = 'normal'  # low, normal, high, urgent
    two_factor_token: Optional[str] = None


class WithdrawalResult(BaseModel):
    withdrawal_id: str
    processing_status: str  # pending, processing, completed, failed, cancelled
    currency_code: str
    amount: str
    amount_float: float
    fee_amount: str
    net_amount: str  # amount - fee
    estimated_completion_time: datetime
    risk_assessment: Dict[str, Any]
    compliance_checks: List[str]
    processing_warnings: List[str]
    created_timestamp: datetime


class WithdrawalProcessingModule(SingleFunctionModule):
    """
    Single Function Module: Withdrawal Processing
    Verantwortlichkeit: Ausschließlich Withdrawal-Processing-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("withdrawal_processing", event_bus)
        
        # Account Balances für Withdrawal Validation
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
        
        # Withdrawal Limits
        self.withdrawal_limits = {
            'EUR': {'daily': 10000.0, 'monthly': 100000.0},
            'USD': {'daily': 10000.0, 'monthly': 100000.0},
            'BTC': {'daily': 1.0, 'monthly': 10.0},
            'ETH': {'daily': 10.0, 'monthly': 100.0}
        }
        
        # Mock aktuelle Usage
        self.current_usage = {
            'EUR': {'daily': 1500.0, 'monthly': 15000.0},
            'USD': {'daily': 800.0, 'monthly': 8000.0},
            'BTC': {'daily': 0.1, 'monthly': 2.5},
            'ETH': {'daily': 1.0, 'monthly': 8.0}
        }
        
        # Withdrawal Fees Configuration
        self.withdrawal_fees = {
            'bank_transfer': {
                'EUR': {'fixed': 2.50, 'percentage': 0.001, 'min_fee': 2.50, 'max_fee': 25.00},
                'USD': {'fixed': 3.00, 'percentage': 0.001, 'min_fee': 3.00, 'max_fee': 30.00}
            },
            'crypto_transfer': {
                'BTC': {'fixed': 0.0005, 'percentage': 0.0, 'min_fee': 0.0005, 'max_fee': 0.01},
                'ETH': {'fixed': 0.005, 'percentage': 0.0, 'min_fee': 0.005, 'max_fee': 0.05}
            },
            'card': {
                'EUR': {'fixed': 1.00, 'percentage': 0.025, 'min_fee': 1.00, 'max_fee': 50.00},
                'USD': {'fixed': 1.50, 'percentage': 0.025, 'min_fee': 1.50, 'max_fee': 60.00}
            }
        }
        
        # Processing Times (in minutes)
        self.processing_times = {
            'bank_transfer': {'EUR': 1440, 'USD': 2880},  # 1-2 business days
            'crypto_transfer': {'BTC': 60, 'ETH': 30},    # 30-60 minutes
            'card': {'EUR': 30, 'USD': 30}                # 30 minutes
        }
        
        # Withdrawal Processing History
        self.processing_history = []
        self.processing_counter = 0
        
        # Risk Assessment Configuration
        self.risk_config = {
            'high_amount_thresholds': {
                'EUR': 5000.0,
                'USD': 5000.0,
                'BTC': 0.5,
                'ETH': 5.0
            },
            'suspicious_pattern_checks': True,
            'aml_compliance_required': True,
            'max_daily_withdrawals_count': 10,
            'cooling_period_hours': 2,  # Between large withdrawals
            'require_2fa_above': {
                'EUR': 1000.0,
                'USD': 1000.0,
                'BTC': 0.1,
                'ETH': 1.0
            }
        }
        
        # Active Withdrawals Registry
        self.active_withdrawals = {}
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Withdrawal Processing
        
        Args:
            input_data: {
                'currency_code': required string,
                'amount': required string,
                'destination_address': optional string (for crypto),
                'destination_account': optional string (for bank),
                'withdrawal_method': optional string (default: bank_transfer),
                'description': optional string,
                'priority': optional string (default: normal),
                'two_factor_token': optional string,
                'validate_only': optional bool (default: false),
                'bypass_compliance': optional bool (default: false)
            }
            
        Returns:
            Dict mit Withdrawal-Processing-Result
        """
        start_time = datetime.now()
        
        try:
            # Withdrawal Request erstellen
            withdrawal_request = WithdrawalRequest(
                currency_code=input_data.get('currency_code'),
                amount=input_data.get('amount'),
                destination_address=input_data.get('destination_address'),
                destination_account=input_data.get('destination_account'),
                withdrawal_method=input_data.get('withdrawal_method', 'bank_transfer'),
                description=input_data.get('description'),
                priority=input_data.get('priority', 'normal'),
                two_factor_token=input_data.get('two_factor_token')
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Invalid withdrawal request: {str(e)}'
            }
        
        validate_only = input_data.get('validate_only', False)
        bypass_compliance = input_data.get('bypass_compliance', False)
        
        # Withdrawal Processing
        processing_result = await self._process_withdrawal_request(
            withdrawal_request, validate_only, bypass_compliance
        )
        
        # Statistics Update
        self.processing_counter += 1
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Processing History
        self.processing_history.append({
            'timestamp': datetime.now(),
            'withdrawal_id': processing_result.withdrawal_id if hasattr(processing_result, 'withdrawal_id') else None,
            'currency_code': withdrawal_request.currency_code,
            'amount': withdrawal_request.amount,
            'withdrawal_method': withdrawal_request.withdrawal_method,
            'processing_status': processing_result.processing_status if hasattr(processing_result, 'processing_status') else 'failed',
            'priority': withdrawal_request.priority,
            'validate_only': validate_only,
            'processing_time_ms': processing_time_ms,
            'processing_id': self.processing_counter
        })
        
        # Limit History
        if len(self.processing_history) > 200:
            self.processing_history.pop(0)
        
        if hasattr(processing_result, 'withdrawal_id'):
            self.logger.info(f"Withdrawal processed",
                           withdrawal_id=processing_result.withdrawal_id,
                           currency_code=withdrawal_request.currency_code,
                           amount=withdrawal_request.amount,
                           processing_status=processing_result.processing_status,
                           processing_id=self.processing_counter)
            
            return {
                'success': True,
                'withdrawal_id': processing_result.withdrawal_id,
                'processing_status': processing_result.processing_status,
                'currency_code': processing_result.currency_code,
                'amount': processing_result.amount,
                'fee_amount': processing_result.fee_amount,
                'net_amount': processing_result.net_amount,
                'estimated_completion_time': processing_result.estimated_completion_time.isoformat(),
                'risk_assessment': processing_result.risk_assessment,
                'compliance_checks': processing_result.compliance_checks,
                'processing_warnings': processing_result.processing_warnings
            }
        else:
            # Processing failed
            return {
                'success': False,
                'error': getattr(processing_result, 'error', 'Withdrawal processing failed'),
                'validation_errors': getattr(processing_result, 'validation_errors', [])
            }
    
    async def _process_withdrawal_request(self, request: WithdrawalRequest,
                                        validate_only: bool, 
                                        bypass_compliance: bool) -> WithdrawalResult:
        """Verarbeitet Withdrawal Request komplett"""
        
        currency_code = request.currency_code.upper()
        amount_float = float(request.amount)
        
        # 1. Validation Phase
        validation_result = await self._validate_withdrawal_request(request)
        if not validation_result['valid']:
            return type('FailedResult', (), {
                'error': 'Withdrawal validation failed',
                'validation_errors': validation_result['errors']
            })()
        
        # 2. Risk Assessment
        risk_assessment = await self._assess_withdrawal_risk(request, amount_float)
        
        # 3. Compliance Checks
        compliance_checks = []
        if not bypass_compliance:
            compliance_result = await self._perform_compliance_checks(request, amount_float)
            compliance_checks = compliance_result['checks']
            
            if not compliance_result['passed']:
                return type('FailedResult', (), {
                    'error': 'Compliance checks failed',
                    'validation_errors': compliance_result['failures']
                })()
        
        # 4. Fee Calculation
        fee_amount, fee_float = await self._calculate_withdrawal_fee(request, amount_float)
        net_amount = amount_float - fee_float
        
        # 5. Validate-Only Check
        if validate_only:
            return WithdrawalResult(
                withdrawal_id=f'VALIDATE_{int(datetime.now().timestamp())}',
                processing_status='validation_successful',
                currency_code=currency_code,
                amount=request.amount,
                amount_float=amount_float,
                fee_amount=fee_amount,
                net_amount=f"{net_amount:.8f}".rstrip('0').rstrip('.'),
                estimated_completion_time=datetime.now() + timedelta(minutes=self._get_processing_time(request)),
                risk_assessment=risk_assessment,
                compliance_checks=compliance_checks,
                processing_warnings=validation_result['warnings'],
                created_timestamp=datetime.now()
            )
        
        # 6. Balance Check & Lock
        balance_check = await self._check_and_lock_funds(currency_code, amount_float + fee_float)
        if not balance_check['sufficient']:
            return type('FailedResult', (), {
                'error': balance_check['error'],
                'validation_errors': [balance_check['error']]
            })()
        
        # 7. Create Withdrawal Record
        withdrawal_id = f"WD_{int(datetime.now().timestamp())}_{self.processing_counter:06d}"
        
        withdrawal_result = WithdrawalResult(
            withdrawal_id=withdrawal_id,
            processing_status='pending',
            currency_code=currency_code,
            amount=request.amount,
            amount_float=amount_float,
            fee_amount=fee_amount,
            net_amount=f"{net_amount:.8f}".rstrip('0').rstrip('.'),
            estimated_completion_time=datetime.now() + timedelta(minutes=self._get_processing_time(request)),
            risk_assessment=risk_assessment,
            compliance_checks=compliance_checks,
            processing_warnings=validation_result['warnings'],
            created_timestamp=datetime.now()
        )
        
        # 8. Add to Active Withdrawals
        self.active_withdrawals[withdrawal_id] = {
            'request': request,
            'result': withdrawal_result,
            'created_at': datetime.now(),
            'status': 'pending'
        }
        
        # 9. Publish Withdrawal Event
        await self._publish_withdrawal_event(withdrawal_result, request)
        
        return withdrawal_result
    
    async def _validate_withdrawal_request(self, request: WithdrawalRequest) -> Dict[str, Any]:
        """Validiert Withdrawal Request"""
        
        errors = []
        warnings = []
        currency_code = request.currency_code.upper()
        
        try:
            amount_float = float(request.amount)
            if amount_float <= 0:
                errors.append('Withdrawal amount must be positive')
        except (ValueError, TypeError):
            errors.append('Invalid amount format')
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        # Currency Support Check
        if currency_code not in self.account_balances:
            errors.append(f'Currency {currency_code} not supported')
        
        # Withdrawal Method Validation
        if request.withdrawal_method not in ['bank_transfer', 'crypto_transfer', 'card']:
            errors.append(f'Invalid withdrawal method: {request.withdrawal_method}')
        
        # Method-Currency Compatibility
        if request.withdrawal_method == 'crypto_transfer' and currency_code in ['EUR', 'USD']:
            errors.append(f'Crypto withdrawal not available for {currency_code}')
        elif request.withdrawal_method in ['bank_transfer', 'card'] and currency_code in ['BTC', 'ETH']:
            errors.append(f'{request.withdrawal_method} not available for {currency_code}')
        
        # Destination Validation
        if request.withdrawal_method == 'crypto_transfer' and not request.destination_address:
            errors.append('Destination address required for crypto withdrawal')
        elif request.withdrawal_method == 'bank_transfer' and not request.destination_account:
            errors.append('Destination account required for bank transfer')
        
        # Balance Availability
        if currency_code in self.account_balances:
            available = float(self.account_balances[currency_code]['available'])
            if amount_float > available:
                errors.append(f'Insufficient balance. Available: {available}, Requested: {amount_float}')
            elif amount_float > available * 0.9:
                warnings.append('Withdrawal uses >90% of available balance')
        
        # Withdrawal Limits Check
        if currency_code in self.withdrawal_limits:
            limits = self.withdrawal_limits[currency_code]
            current_usage = self.current_usage.get(currency_code, {'daily': 0, 'monthly': 0})
            
            daily_remaining = limits['daily'] - current_usage['daily']
            monthly_remaining = limits['monthly'] - current_usage['monthly']
            
            if amount_float > daily_remaining:
                errors.append(f'Daily withdrawal limit exceeded. Remaining: {daily_remaining}')
            elif amount_float > daily_remaining * 0.8:
                warnings.append('Withdrawal uses >80% of remaining daily limit')
            
            if amount_float > monthly_remaining:
                errors.append(f'Monthly withdrawal limit exceeded. Remaining: {monthly_remaining}')
        
        # Minimum/Maximum Amount Validation
        min_amounts = {'EUR': 10.0, 'USD': 10.0, 'BTC': 0.001, 'ETH': 0.01}
        max_amounts = {'EUR': 50000.0, 'USD': 50000.0, 'BTC': 10.0, 'ETH': 100.0}
        
        min_amount = min_amounts.get(currency_code, 0.01)
        max_amount = max_amounts.get(currency_code, 1000000.0)
        
        if amount_float < min_amount:
            errors.append(f'Amount below minimum: {min_amount} {currency_code}')
        if amount_float > max_amount:
            errors.append(f'Amount exceeds maximum: {max_amount} {currency_code}')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    async def _assess_withdrawal_risk(self, request: WithdrawalRequest, 
                                    amount_float: float) -> Dict[str, Any]:
        """Bewertet Withdrawal Risk"""
        
        currency_code = request.currency_code.upper()
        risk_factors = []
        risk_score = 0
        
        # High Amount Risk
        high_threshold = self.risk_config['high_amount_thresholds'].get(currency_code, float('inf'))
        if amount_float > high_threshold:
            risk_factors.append('high_amount')
            risk_score += 3
        
        # Time Pattern Analysis
        recent_withdrawals = [
            w for w in self.processing_history
            if (datetime.now() - w['timestamp']).hours < 24 and w['currency_code'] == currency_code
        ]
        
        if len(recent_withdrawals) >= 5:
            risk_factors.append('high_frequency')
            risk_score += 2
        
        # Priority Risk
        if request.priority in ['high', 'urgent']:
            risk_factors.append('urgent_priority')
            risk_score += 1
        
        # Weekend/Holiday Risk (mock)
        if datetime.now().weekday() >= 5:  # Weekend
            risk_factors.append('weekend_withdrawal')
            risk_score += 1
        
        # 2FA Check
        require_2fa_threshold = self.risk_config['require_2fa_above'].get(currency_code, 0)
        if amount_float > require_2fa_threshold and not request.two_factor_token:
            risk_factors.append('missing_2fa')
            risk_score += 2
        
        # Risk Level
        if risk_score >= 6:
            risk_level = 'high'
        elif risk_score >= 3:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'recommended_actions': self._generate_risk_recommendations(risk_level, risk_factors)
        }
    

        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())

    def _generate_risk_recommendations(self, risk_level: str, risk_factors: List[str]) -> List[str]:
        """Generiert Risk-basierte Empfehlungen"""
        
        recommendations = []
        
        if risk_level == 'high':
            recommendations.append('Manual review required')
            recommendations.append('Additional verification recommended')
        
        if 'missing_2fa' in risk_factors:
            recommendations.append('Two-factor authentication required')
        
        if 'high_frequency' in risk_factors:
            recommendations.append('Consider consolidating multiple withdrawals')
        
        if 'urgent_priority' in risk_factors:
            recommendations.append('Verify urgency justification')
        
        return recommendations
    
    async def _perform_compliance_checks(self, request: WithdrawalRequest, 
                                       amount_float: float) -> Dict[str, Any]:
        """Führt Compliance Checks durch"""
        
        checks = []
        failures = []
        
        # AML Check
        checks.append('AML compliance check')
        if self.risk_config['aml_compliance_required']:
            # Mock AML check
            if amount_float > 10000:  # Large amount requires additional AML
                checks.append('Enhanced AML verification required')
        
        # KYC Status Check
        checks.append('KYC status verification')
        # Mock: assume KYC is valid
        
        # Sanctions List Check
        checks.append('Sanctions list screening')
        # Mock: assume clean
        
        # Daily Withdrawal Count Check
        daily_withdrawals = len([
            w for w in self.processing_history
            if (datetime.now() - w['timestamp']).days == 0
        ])
        
        if daily_withdrawals >= self.risk_config['max_daily_withdrawals_count']:
            failures.append(f'Daily withdrawal count limit exceeded: {daily_withdrawals}')
        
        checks.append(f'Daily withdrawal count check: {daily_withdrawals}')
        
        return {
            'passed': len(failures) == 0,
            'checks': checks,
            'failures': failures
        }
    
    async def _calculate_withdrawal_fee(self, request: WithdrawalRequest, 
                                      amount_float: float) -> tuple:
        """Berechnet Withdrawal Fee"""
        
        currency_code = request.currency_code.upper()
        method = request.withdrawal_method
        
        if method in self.withdrawal_fees and currency_code in self.withdrawal_fees[method]:
            fee_config = self.withdrawal_fees[method][currency_code]
            
            fixed_fee = fee_config['fixed']
            percentage_fee = amount_float * fee_config['percentage']
            
            total_fee = fixed_fee + percentage_fee
            
            # Apply min/max limits
            min_fee = fee_config['min_fee']
            max_fee = fee_config['max_fee']
            
            final_fee = max(min_fee, min(total_fee, max_fee))
            
            precision = 8 if currency_code in ['BTC', 'ETH'] else 2
            fee_amount = f"{final_fee:.{precision}f}".rstrip('0').rstrip('.')
            
            return fee_amount, final_fee
        
        # Fallback fee
        default_fee = amount_float * 0.001  # 0.1%
        precision = 8 if currency_code in ['BTC', 'ETH'] else 2
        fee_amount = f"{default_fee:.{precision}f}".rstrip('0').rstrip('.')
        
        return fee_amount, default_fee
    
    def _get_processing_time(self, request: WithdrawalRequest) -> int:
        """Gibt geschätzte Processing Time in Minuten zurück"""
        
        method = request.withdrawal_method
        currency = request.currency_code.upper()
        
        if method in self.processing_times and currency in self.processing_times[method]:
            base_time = self.processing_times[method][currency]
        else:
            base_time = 60  # Default 1 hour
        
        # Priority Adjustment
        if request.priority == 'urgent':
            base_time = int(base_time * 0.5)  # 50% faster
        elif request.priority == 'high':
            base_time = int(base_time * 0.75)  # 25% faster
        elif request.priority == 'low':
            base_time = int(base_time * 1.5)  # 50% slower
        
        return base_time
    
    async def _check_and_lock_funds(self, currency_code: str, 
                                  total_amount: float) -> Dict[str, Any]:
        """Prüft Balance und lockt Funds"""
        
        if currency_code not in self.account_balances:
            return {
                'sufficient': False,
                'error': f'No {currency_code} balance available'
            }
        
        available = float(self.account_balances[currency_code]['available'])
        
        if total_amount > available:
            return {
                'sufficient': False,
                'error': f'Insufficient balance. Available: {available}, Required: {total_amount}'
            }
        
        # Mock: Lock funds (in production würde das über Balance Update Module gehen)
        new_available = available - total_amount
        current_locked = float(self.account_balances[currency_code]['locked'])
        new_locked = current_locked + total_amount
        
        self.account_balances[currency_code]['available'] = f"{new_available:.8f}".rstrip('0').rstrip('.')
        self.account_balances[currency_code]['locked'] = f"{new_locked:.8f}".rstrip('0').rstrip('.')
        self.account_balances[currency_code]['last_updated'] = datetime.now()
        
        return {
            'sufficient': True,
            'locked_amount': total_amount,
            'new_available_balance': new_available
        }
    
    async def _publish_withdrawal_event(self, result: WithdrawalResult, 
                                      request: WithdrawalRequest):
        """Published Withdrawal Event über Event-Bus"""
        
        if not self.event_bus or not self.event_bus.connected:
            return
        
        from event_bus import Event
        
        event = Event(
            event_type="withdrawal_requested",
            stream_id=f"withdrawal-{result.withdrawal_id}",
            data={
                'withdrawal_id': result.withdrawal_id,
                'currency_code': result.currency_code,
                'amount': result.amount,
                'fee_amount': result.fee_amount,
                'net_amount': result.net_amount,
                'withdrawal_method': request.withdrawal_method,
                'processing_status': result.processing_status,
                'risk_level': result.risk_assessment['risk_level'],
                'estimated_completion': result.estimated_completion_time.isoformat(),
                'priority': request.priority
            },
            source="withdrawal_processing"
        )
        
        await self.event_bus.publish(event)
    
    def get_withdrawal_status(self, withdrawal_id: str) -> Optional[Dict[str, Any]]:
        """Gibt Withdrawal Status zurück"""
        
        if withdrawal_id in self.active_withdrawals:
            withdrawal = self.active_withdrawals[withdrawal_id]
            return {
                'withdrawal_id': withdrawal_id,
                'status': withdrawal['status'],
                'currency_code': withdrawal['result'].currency_code,
                'amount': withdrawal['result'].amount,
                'created_at': withdrawal['created_at'].isoformat(),
                'estimated_completion': withdrawal['result'].estimated_completion_time.isoformat()
            }
        
        return None
    
    def get_pending_withdrawals(self) -> List[Dict[str, Any]]:
        """Gibt Liste der Pending Withdrawals zurück"""
        
        pending = []
        for withdrawal_id, withdrawal in self.active_withdrawals.items():
            if withdrawal['status'] in ['pending', 'processing']:
                pending.append({
                    'withdrawal_id': withdrawal_id,
                    'currency_code': withdrawal['result'].currency_code,
                    'amount': withdrawal['result'].amount,
                    'status': withdrawal['status'],
                    'created_at': withdrawal['created_at'].isoformat(),
                    'priority': withdrawal['request'].priority
                })
        
        return sorted(pending, key=lambda x: x['created_at'], reverse=True)
    
    def cancel_withdrawal(self, withdrawal_id: str) -> Dict[str, Any]:
        """Cancelled Withdrawal (falls noch möglich)"""
        
        if withdrawal_id not in self.active_withdrawals:
            return {'success': False, 'error': 'Withdrawal not found'}
        
        withdrawal = self.active_withdrawals[withdrawal_id]
        
        if withdrawal['status'] not in ['pending']:
            return {'success': False, 'error': 'Withdrawal cannot be cancelled'}
        
        # Unlock funds
        result = withdrawal['result']
        currency_code = result.currency_code
        total_amount = result.amount_float + float(result.fee_amount)
        
        # Unlock logic (mock)
        current_available = float(self.account_balances[currency_code]['available'])
        current_locked = float(self.account_balances[currency_code]['locked'])
        
        new_available = current_available + total_amount
        new_locked = max(0, current_locked - total_amount)
        
        self.account_balances[currency_code]['available'] = f"{new_available:.8f}".rstrip('0').rstrip('.')
        self.account_balances[currency_code]['locked'] = f"{new_locked:.8f}".rstrip('0').rstrip('.')
        
        # Update status
        withdrawal['status'] = 'cancelled'
        
        return {
            'success': True,
            'withdrawal_id': withdrawal_id,
            'status': 'cancelled',
            'unlocked_amount': total_amount
        }
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'withdrawal_processing',
            'description': 'Processes withdrawal requests with comprehensive risk assessment and compliance',
            'responsibility': 'Withdrawal processing logic only',
            'input_parameters': {
                'currency_code': 'Required currency code for withdrawal',
                'amount': 'Required withdrawal amount',
                'destination_address': 'Destination address for crypto withdrawals',
                'destination_account': 'Destination account for bank transfers',
                'withdrawal_method': 'Withdrawal method (bank_transfer, crypto_transfer, card)',
                'description': 'Optional description',
                'priority': 'Withdrawal priority (low, normal, high, urgent)',
                'two_factor_token': '2FA token for high-value withdrawals',
                'validate_only': 'Only validate without processing (default: false)',
                'bypass_compliance': 'Bypass compliance checks (default: false)'
            },
            'output_format': {
                'withdrawal_id': 'Unique withdrawal identifier',
                'processing_status': 'Current processing status',
                'currency_code': 'Withdrawal currency',
                'amount': 'Withdrawal amount',
                'fee_amount': 'Calculated withdrawal fee',
                'net_amount': 'Net amount after fees',
                'estimated_completion_time': 'Estimated completion timestamp',
                'risk_assessment': 'Risk analysis results',
                'compliance_checks': 'Compliance verification results',
                'processing_warnings': 'Processing warnings if any'
            },
            'supported_currencies': list(self.account_balances.keys()),
            'supported_methods': ['bank_transfer', 'crypto_transfer', 'card'],
            'priority_levels': ['low', 'normal', 'high', 'urgent'],
            'withdrawal_limits': self.withdrawal_limits,
            'fee_structure': self.withdrawal_fees,
            'risk_configuration': self.risk_config,
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_withdrawal_statistics(self) -> Dict[str, Any]:
        """Withdrawal Processing Module Statistiken"""
        total_processed = len(self.processing_history)
        
        if total_processed == 0:
            return {
                'total_processed': 0,
                'active_withdrawals': len(self.active_withdrawals),
                'supported_currencies': len(self.account_balances)
            }
        
        # Success Rate
        successful = sum(1 for w in self.processing_history if w['processing_status'] not in ['failed'])
        success_rate = round((successful / total_processed) * 100, 1) if total_processed > 0 else 0
        
        # Method Distribution
        method_distribution = {}
        for withdrawal in self.processing_history:
            method = withdrawal['withdrawal_method']
            method_distribution[method] = method_distribution.get(method, 0) + 1
        
        # Currency Distribution
        currency_distribution = {}
        for withdrawal in self.processing_history:
            currency = withdrawal['currency_code']
            currency_distribution[currency] = currency_distribution.get(currency, 0) + 1
        
        # Priority Distribution
        priority_distribution = {}
        for withdrawal in self.processing_history:
            priority = withdrawal['priority']
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
        
        # Recent Activity
        recent_withdrawals = [
            w for w in self.processing_history
            if (datetime.now() - w['timestamp']).seconds < 3600  # Last hour
        ]
        
        # Average Processing Time
        processing_times = [w['processing_time_ms'] for w in self.processing_history]
        avg_processing_time = round(sum(processing_times) / len(processing_times), 2) if processing_times else 0
        
        return {
            'total_processed': total_processed,
            'successful_withdrawals': successful,
            'success_rate_percent': success_rate,
            'recent_withdrawals_last_hour': len(recent_withdrawals),
            'active_withdrawals': len(self.active_withdrawals),
            'pending_withdrawals': len([w for w in self.active_withdrawals.values() if w['status'] == 'pending']),
            'method_distribution': dict(sorted(
                method_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'currency_distribution': dict(sorted(
                currency_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'priority_distribution': dict(sorted(
                priority_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'average_processing_time_ms': avg_processing_time,
            'supported_methods': len(self.withdrawal_fees),
            'module_processing_time': self.average_execution_time
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
