from typing import Dict, Any, List, Optional
import sys
from shared.common_imports import (
import asyncio
from ..single_function_module_base import SingleFunctionModule
"""
Risk Assessment Module - Single Function Module
Verantwortlich ausschließlich für Risk Assessment Logic
"""

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

    datetime, timedelta, BaseModel, structlog
)


class RiskAssessmentRequest(BaseModel):
    assessment_type: str  # 'portfolio', 'transaction', 'account', 'trading'
    context_data: Dict[str, Any]
    risk_tolerance: Optional[str] = 'medium'  # 'low', 'medium', 'high'
    assessment_scope: Optional[str] = 'comprehensive'  # 'basic', 'comprehensive', 'detailed'


class RiskFactor(BaseModel):
    factor_name: str
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    risk_score: float  # 0-100
    description: str
    mitigation_suggestions: List[str]


class RiskAssessmentResult(BaseModel):
    overall_risk_score: float  # 0-100, higher = more risky
    overall_risk_level: str  # 'low', 'medium', 'high', 'critical'
    risk_factors: List[RiskFactor]
    risk_categories: Dict[str, Dict[str, Any]]
    recommendations: List[str]
    compliance_status: str  # 'compliant', 'warning', 'violation'
    assessment_confidence: float  # 0-100
    assessment_timestamp: datetime


class RiskAssessmentModule(SingleFunctionModule):
    """
    Single Function Module: Risk Assessment
    Verantwortlichkeit: Ausschließlich Risk-Assessment-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("risk_assessment", event_bus)
        
        # Risk Assessment Configuration
        self.risk_config = {
            'portfolio_risk_thresholds': {
                'concentration_limit': 0.3,  # Max 30% in single asset
                'volatility_threshold': 0.4,  # 40% volatility = high risk
                'correlation_limit': 0.8,    # 80% correlation = concentrated
                'leverage_limit': 2.0        # 2x leverage maximum
            },
            'transaction_risk_thresholds': {
                'large_amount_threshold': 10000.0,  # >10k EUR = large
                'velocity_limit': 50000.0,          # Max 50k EUR/day
                'frequency_limit': 100,             # Max 100 transactions/day
                'unusual_pattern_score': 0.7       # 70% = suspicious
            },
            'account_risk_thresholds': {
                'age_minimum_days': 30,        # Account younger than 30 days = risky
                'verification_required': True,  # KYC required
                'activity_threshold': 0.1,     # <10% activity = dormant
                'balance_volatility_limit': 0.5 # 50% balance changes = risky
            },
            'compliance_thresholds': {
                'aml_transaction_limit': 15000.0,  # >15k requires enhanced checks
                'pep_enhanced_dd': True,           # PEP requires enhanced DD
                'sanctions_check_required': True,  # Always check sanctions
                'source_of_funds_threshold': 25000.0 # >25k requires SOF documentation
            }
        }
        
        # Risk Scoring Weights
        self.risk_weights = {
            'portfolio_concentration': 0.25,
            'transaction_pattern': 0.20,
            'account_behavior': 0.15,
            'compliance_status': 0.20,
            'market_conditions': 0.10,
            'external_factors': 0.10
        }
        
        # Mock Market Data für Risk Assessment
        self.market_data = {
            'volatility_index': 0.25,  # 25% market volatility
            'correlation_matrix': {
                'EUR_USD': 0.3,
                'BTC_ETH': 0.75,
                'CRYPTO_FIAT': -0.2
            },
            'risk_free_rate': 0.02,  # 2% risk-free rate
            'market_sentiment': 'neutral'  # 'bullish', 'neutral', 'bearish'
        }
        
        # Assessment History
        self.assessment_history = []
        self.assessment_counter = 0
        
        # Risk Assessment Cache
        self.risk_cache = {}
        self.cache_timestamps = {}
        
        # Account Data für Risk Context (Mock)
        self.account_context = {
            'account_age_days': 180,
            'verification_status': 'fully_verified',
            'last_activity': datetime.now() - timedelta(hours=2),
            'transaction_count_30d': 45,
            'average_transaction_size': 2500.0,
            'kyc_risk_score': 0.15,  # Low risk
            'pep_status': False,
            'sanctions_clear': True,
            'source_of_funds_documented': True
        }
        
        # Portfolio Context (Mock)
        self.portfolio_context = {
            'total_value_eur': 87500.0,
            'largest_position_percentage': 0.35,  # 35%
            'asset_count': 6,
            'average_holding_period_days': 45,
            'turnover_ratio': 0.8,
            'realized_pnl_ytd': 12500.0,
            'max_drawdown': -0.15  # -15%
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Risk Assessment
        
        Args:
            input_data: {
                'assessment_type': required string ('portfolio', 'transaction', 'account', 'trading'),
                'context_data': required dict with relevant data for assessment,
                'risk_tolerance': optional string ('low', 'medium', 'high'),
                'assessment_scope': optional string ('basic', 'comprehensive', 'detailed'),
                'include_recommendations': optional bool (default: true),
                'force_refresh': optional bool (default: false)
            }
            
        Returns:
            Dict mit Risk-Assessment-Result
        """
        start_time = datetime.now()
        
        try:
            # Risk Assessment Request erstellen
            assessment_request = RiskAssessmentRequest(
                assessment_type=input_data.get('assessment_type'),
                context_data=input_data.get('context_data', {}),
                risk_tolerance=input_data.get('risk_tolerance', 'medium'),
                assessment_scope=input_data.get('assessment_scope', 'comprehensive')
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Invalid risk assessment request: {str(e)}'
            }
        
        include_recommendations = input_data.get('include_recommendations', True)
        force_refresh = input_data.get('force_refresh', False)
        
        # Risk Assessment durchführen
        assessment_result = await self._perform_risk_assessment(
            assessment_request, include_recommendations, force_refresh
        )
        
        # Statistics Update
        self.assessment_counter += 1
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Assessment History
        self.assessment_history.append({
            'timestamp': datetime.now(),
            'assessment_type': assessment_request.assessment_type,
            'overall_risk_score': assessment_result.overall_risk_score,
            'overall_risk_level': assessment_result.overall_risk_level,
            'risk_factors_count': len(assessment_result.risk_factors),
            'compliance_status': assessment_result.compliance_status,
            'assessment_confidence': assessment_result.assessment_confidence,
            'processing_time_ms': processing_time_ms,
            'assessment_id': self.assessment_counter
        })
        
        # Limit History
        if len(self.assessment_history) > 300:
            self.assessment_history.pop(0)
        
        # Event Publishing für High Risk Assessments
        if assessment_result.overall_risk_level in ['high', 'critical']:
            await self._publish_risk_alert_event(assessment_result)
        
        self.logger.info(f"Risk assessment completed",
                       assessment_type=assessment_request.assessment_type,
                       overall_risk_score=assessment_result.overall_risk_score,
                       overall_risk_level=assessment_result.overall_risk_level,
                       compliance_status=assessment_result.compliance_status,
                       processing_time_ms=round(processing_time_ms, 2),
                       assessment_id=self.assessment_counter)
        
        return {
            'success': True,
            'overall_risk_score': assessment_result.overall_risk_score,
            'overall_risk_level': assessment_result.overall_risk_level,
            'risk_factors': [self._risk_factor_to_dict(rf) for rf in assessment_result.risk_factors],
            'risk_categories': assessment_result.risk_categories,
            'recommendations': assessment_result.recommendations if include_recommendations else [],
            'compliance_status': assessment_result.compliance_status,
            'assessment_confidence': assessment_result.assessment_confidence,
            'assessment_timestamp': assessment_result.assessment_timestamp.isoformat()
        }
    
    async def _perform_risk_assessment(self, request: RiskAssessmentRequest,
                                     include_recommendations: bool,
                                     force_refresh: bool) -> RiskAssessmentResult:
        """Führt comprehensive Risk Assessment durch"""
        
        # Cache Check
        cache_key = f"{request.assessment_type}_{hash(str(request.context_data))}"
        if not force_refresh and self._has_valid_cache(cache_key):
            return self.risk_cache[cache_key]
        
        # Assessment Type spezifische Logic
        if request.assessment_type == 'portfolio':
            assessment_result = await self._assess_portfolio_risk(request)
        elif request.assessment_type == 'transaction':
            assessment_result = await self._assess_transaction_risk(request)
        elif request.assessment_type == 'account':
            assessment_result = await self._assess_account_risk(request)
        elif request.assessment_type == 'trading':
            assessment_result = await self._assess_trading_risk(request)
        else:
            # Comprehensive Assessment (alle Types)
            assessment_result = await self._assess_comprehensive_risk(request)
        
        # Recommendations hinzufügen
        if include_recommendations:
            assessment_result.recommendations = await self._generate_risk_recommendations(assessment_result)
        
        # Cache Update
        self.risk_cache[cache_key] = assessment_result
        self.cache_timestamps[cache_key] = datetime.now()
        
        return assessment_result
    
    async def _assess_portfolio_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResult:
        """Portfolio-spezifische Risk Assessment"""
        
        context = request.context_data
        risk_factors = []
        risk_categories = {}
        
        # Portfolio Concentration Risk
        concentration_score = await self._calculate_concentration_risk(context)
        if concentration_score > 0.3:
            risk_factors.append(RiskFactor(
                factor_name="Portfolio Concentration",
                risk_level="high" if concentration_score > 0.5 else "medium",
                risk_score=concentration_score * 100,
                description=f"Portfolio concentrated in few assets ({concentration_score:.1%} concentration)",
                mitigation_suggestions=[
                    "Diversify across more assets",
                    "Reduce position sizes in concentrated holdings",
                    "Consider correlation between holdings"
                ]
            ))
        
        # Volatility Risk
        volatility_score = await self._calculate_volatility_risk(context)
        if volatility_score > 0.4:
            risk_factors.append(RiskFactor(
                factor_name="Portfolio Volatility",
                risk_level="high" if volatility_score > 0.6 else "medium",
                risk_score=volatility_score * 100,
                description=f"High portfolio volatility ({volatility_score:.1%})",
                mitigation_suggestions=[
                    "Add stable assets to reduce volatility",
                    "Consider hedging strategies",
                    "Rebalance portfolio regularly"
                ]
            ))
        
        # Leverage Risk
        leverage_ratio = context.get('leverage_ratio', 1.0)
        if leverage_ratio > self.risk_config['portfolio_risk_thresholds']['leverage_limit']:
            risk_factors.append(RiskFactor(
                factor_name="Leverage Risk",
                risk_level="critical" if leverage_ratio > 3.0 else "high",
                risk_score=min(100, leverage_ratio * 30),
                description=f"High leverage ratio ({leverage_ratio:.1f}x)",
                mitigation_suggestions=[
                    "Reduce leverage to acceptable levels",
                    "Implement strict stop-loss orders",
                    "Monitor margin requirements closely"
                ]
            ))
        
        # Risk Categories
        risk_categories = {
            'concentration_risk': {
                'score': concentration_score * 100,
                'level': self._score_to_level(concentration_score * 100),
                'contributing_factors': ['Asset allocation', 'Position sizing']
            },
            'volatility_risk': {
                'score': volatility_score * 100,
                'level': self._score_to_level(volatility_score * 100),
                'contributing_factors': ['Asset volatility', 'Correlation structure']
            },
            'leverage_risk': {
                'score': min(100, leverage_ratio * 30),
                'level': self._score_to_level(min(100, leverage_ratio * 30)),
                'contributing_factors': ['Margin usage', 'Capital structure']
            }
        }
        
        # Overall Score berechnen
        overall_score = await self._calculate_weighted_risk_score(risk_categories)
        
        return RiskAssessmentResult(
            overall_risk_score=overall_score,
            overall_risk_level=self._score_to_level(overall_score),
            risk_factors=risk_factors,
            risk_categories=risk_categories,
            recommendations=[],
            compliance_status=self._determine_compliance_status(risk_factors, overall_score),
            assessment_confidence=self._calculate_confidence_score(context),
            assessment_timestamp=datetime.now()
        )
    
    async def _assess_transaction_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResult:
        """Transaction-spezifische Risk Assessment"""
        
        context = request.context_data
        risk_factors = []
        risk_categories = {}
        
        transaction_amount = context.get('amount', 0)
        transaction_type = context.get('type', 'unknown')
        frequency = context.get('daily_frequency', 1)
        
        # Large Amount Risk
        if transaction_amount > self.risk_config['transaction_risk_thresholds']['large_amount_threshold']:
            risk_level = "critical" if transaction_amount > 50000 else "high"
            risk_factors.append(RiskFactor(
                factor_name="Large Transaction Amount",
                risk_level=risk_level,
                risk_score=min(100, (transaction_amount / 10000) * 20),
                description=f"Large transaction amount: €{transaction_amount:,.2f}",
                mitigation_suggestions=[
                    "Split into smaller transactions",
                    "Enhanced verification required",
                    "Monitor for unusual patterns"
                ]
            ))
        
        # Velocity Risk
        daily_volume = context.get('daily_volume', transaction_amount)
        if daily_volume > self.risk_config['transaction_risk_thresholds']['velocity_limit']:
            risk_factors.append(RiskFactor(
                factor_name="High Transaction Velocity",
                risk_level="high",
                risk_score=min(100, (daily_volume / 50000) * 40),
                description=f"High daily transaction volume: €{daily_volume:,.2f}",
                mitigation_suggestions=[
                    "Implement velocity controls",
                    "Review transaction patterns",
                    "Consider cooling-off periods"
                ]
            ))
        
        # Frequency Risk
        if frequency > self.risk_config['transaction_risk_thresholds']['frequency_limit']:
            risk_factors.append(RiskFactor(
                factor_name="High Transaction Frequency",
                risk_level="medium",
                risk_score=min(100, (frequency / 100) * 30),
                description=f"High transaction frequency: {frequency} transactions/day",
                mitigation_suggestions=[
                    "Review transaction necessity",
                    "Implement rate limiting",
                    "Monitor for automated trading"
                ]
            ))
        
        # Pattern Analysis Risk
        pattern_risk_score = await self._analyze_transaction_patterns(context)
        if pattern_risk_score > 0.7:
            risk_factors.append(RiskFactor(
                factor_name="Unusual Transaction Pattern",
                risk_level="high",
                risk_score=pattern_risk_score * 100,
                description="Unusual transaction pattern detected",
                mitigation_suggestions=[
                    "Manual review required",
                    "Verify transaction legitimacy",
                    "Check for account compromise"
                ]
            ))
        
        # Risk Categories
        risk_categories = {
            'amount_risk': {
                'score': min(100, (transaction_amount / 10000) * 20),
                'level': self._score_to_level(min(100, (transaction_amount / 10000) * 20)),
                'contributing_factors': ['Transaction size', 'Account capacity']
            },
            'velocity_risk': {
                'score': min(100, (daily_volume / 50000) * 40),
                'level': self._score_to_level(min(100, (daily_volume / 50000) * 40)),
                'contributing_factors': ['Daily volume', 'Historical patterns']
            },
            'pattern_risk': {
                'score': pattern_risk_score * 100,
                'level': self._score_to_level(pattern_risk_score * 100),
                'contributing_factors': ['Transaction timing', 'Amount patterns', 'Counterparties']
            }
        }
        
        overall_score = await self._calculate_weighted_risk_score(risk_categories)
        
        return RiskAssessmentResult(
            overall_risk_score=overall_score,
            overall_risk_level=self._score_to_level(overall_score),
            risk_factors=risk_factors,
            risk_categories=risk_categories,
            recommendations=[],
            compliance_status=self._determine_compliance_status(risk_factors, overall_score),
            assessment_confidence=self._calculate_confidence_score(context),
            assessment_timestamp=datetime.now()
        )
    
    async def _assess_account_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResult:
        """Account-spezifische Risk Assessment"""
        
        context = request.context_data
        risk_factors = []
        risk_categories = {}
        
        # Account Age Risk
        account_age = self.account_context.get('account_age_days', 0)
        if account_age < self.risk_config['account_risk_thresholds']['age_minimum_days']:
            risk_factors.append(RiskFactor(
                factor_name="New Account",
                risk_level="medium",
                risk_score=max(0, (30 - account_age) * 2),
                description=f"Account age: {account_age} days (new account)",
                mitigation_suggestions=[
                    "Implement enhanced monitoring",
                    "Lower transaction limits initially",
                    "Gradual limit increases based on activity"
                ]
            ))
        
        # Verification Risk
        verification_status = self.account_context.get('verification_status', 'unverified')
        if verification_status != 'fully_verified':
            risk_level = "critical" if verification_status == 'unverified' else "high"
            risk_factors.append(RiskFactor(
                factor_name="Incomplete Verification",
                risk_level=risk_level,
                risk_score=80 if verification_status == 'unverified' else 50,
                description=f"Verification status: {verification_status}",
                mitigation_suggestions=[
                    "Complete KYC verification",
                    "Provide required documentation",
                    "Restrict high-risk activities until verified"
                ]
            ))
        
        # Activity Pattern Risk
        last_activity = self.account_context.get('last_activity', datetime.now())
        days_since_activity = (datetime.now() - last_activity).days
        
        if days_since_activity > 90:  # Dormant account
            risk_factors.append(RiskFactor(
                factor_name="Account Dormancy",
                risk_level="medium",
                risk_score=min(60, days_since_activity),
                description=f"No activity for {days_since_activity} days",
                mitigation_suggestions=[
                    "Verify account ownership",
                    "Check for unauthorized access",
                    "Reactivate with enhanced verification"
                ]
            ))
        
        # KYC Risk Score
        kyc_risk = self.account_context.get('kyc_risk_score', 0.5)
        if kyc_risk > 0.3:
            risk_factors.append(RiskFactor(
                factor_name="KYC Risk",
                risk_level="high" if kyc_risk > 0.6 else "medium",
                risk_score=kyc_risk * 100,
                description=f"KYC risk score: {kyc_risk:.2f}",
                mitigation_suggestions=[
                    "Enhanced due diligence required",
                    "Review KYC documentation",
                    "Consider risk-based monitoring"
                ]
            ))
        
        # Risk Categories
        risk_categories = {
            'account_maturity': {
                'score': max(0, (30 - account_age) * 2),
                'level': self._score_to_level(max(0, (30 - account_age) * 2)),
                'contributing_factors': ['Account age', 'Usage history']
            },
            'verification_completeness': {
                'score': 80 if verification_status == 'unverified' else 0,
                'level': self._score_to_level(80 if verification_status == 'unverified' else 0),
                'contributing_factors': ['KYC status', 'Document verification']
            },
            'activity_patterns': {
                'score': min(60, max(0, days_since_activity - 30)),
                'level': self._score_to_level(min(60, max(0, days_since_activity - 30))),
                'contributing_factors': ['Transaction frequency', 'Login patterns']
            }
        }
        
        overall_score = await self._calculate_weighted_risk_score(risk_categories)
        
        return RiskAssessmentResult(
            overall_risk_score=overall_score,
            overall_risk_level=self._score_to_level(overall_score),
            risk_factors=risk_factors,
            risk_categories=risk_categories,
            recommendations=[],
            compliance_status=self._determine_compliance_status(risk_factors, overall_score),
            assessment_confidence=self._calculate_confidence_score(context),
            assessment_timestamp=datetime.now()
        )
    
    async def _assess_trading_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResult:
        """Trading-spezifische Risk Assessment"""
        
        context = request.context_data
        risk_factors = []
        risk_categories = {}
        
        # Market Risk
        market_volatility = self.market_data.get('volatility_index', 0.2)
        if market_volatility > 0.3:
            risk_factors.append(RiskFactor(
                factor_name="High Market Volatility",
                risk_level="high" if market_volatility > 0.4 else "medium",
                risk_score=market_volatility * 100,
                description=f"Market volatility: {market_volatility:.1%}",
                mitigation_suggestions=[
                    "Reduce position sizes",
                    "Use tighter stop-losses",
                    "Consider hedging strategies"
                ]
            ))
        
        # Liquidity Risk
        liquidity_score = context.get('liquidity_score', 0.8)
        if liquidity_score < 0.5:
            risk_factors.append(RiskFactor(
                factor_name="Low Liquidity",
                risk_level="high",
                risk_score=(1 - liquidity_score) * 100,
                description=f"Low market liquidity (score: {liquidity_score:.2f})",
                mitigation_suggestions=[
                    "Avoid large position sizes",
                    "Use limit orders",
                    "Monitor bid-ask spreads"
                ]
            ))
        
        # Correlation Risk
        correlation_risk = await self._assess_correlation_risk(context)
        if correlation_risk > 0.6:
            risk_factors.append(RiskFactor(
                factor_name="High Asset Correlation",
                risk_level="medium",
                risk_score=correlation_risk * 100,
                description="High correlation between portfolio assets",
                mitigation_suggestions=[
                    "Diversify across uncorrelated assets",
                    "Consider different asset classes",
                    "Monitor correlation changes"
                ]
            ))
        
        # Risk Categories
        risk_categories = {
            'market_risk': {
                'score': market_volatility * 100,
                'level': self._score_to_level(market_volatility * 100),
                'contributing_factors': ['Volatility', 'Market sentiment']
            },
            'liquidity_risk': {
                'score': (1 - liquidity_score) * 100,
                'level': self._score_to_level((1 - liquidity_score) * 100),
                'contributing_factors': ['Trading volume', 'Bid-ask spreads']
            },
            'correlation_risk': {
                'score': correlation_risk * 100,
                'level': self._score_to_level(correlation_risk * 100),
                'contributing_factors': ['Asset correlation', 'Diversification']
            }
        }
        
        overall_score = await self._calculate_weighted_risk_score(risk_categories)
        
        return RiskAssessmentResult(
            overall_risk_score=overall_score,
            overall_risk_level=self._score_to_level(overall_score),
            risk_factors=risk_factors,
            risk_categories=risk_categories,
            recommendations=[],
            compliance_status=self._determine_compliance_status(risk_factors, overall_score),
            assessment_confidence=self._calculate_confidence_score(context),
            assessment_timestamp=datetime.now()
        )
    
    async def _assess_comprehensive_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResult:
        """Comprehensive Risk Assessment (alle Kategorien)"""
        
        # Führe alle spezifischen Assessments durch
        portfolio_assessment = await self._assess_portfolio_risk(request)
        transaction_assessment = await self._assess_transaction_risk(request)
        account_assessment = await self._assess_account_risk(request)
        trading_assessment = await self._assess_trading_risk(request)
        
        # Kombiniere Risk Factors
        all_risk_factors = (
            portfolio_assessment.risk_factors +
            transaction_assessment.risk_factors +
            account_assessment.risk_factors +
            trading_assessment.risk_factors
        )
        
        # Kombiniere Risk Categories
        combined_categories = {}
        for assessment in [portfolio_assessment, transaction_assessment, account_assessment, trading_assessment]:
            combined_categories.update(assessment.risk_categories)
        
        # Gewichteter Overall Score
        category_scores = [cat['score'] for cat in combined_categories.values()]
        overall_score = sum(category_scores) / len(category_scores) if category_scores else 0
        
        return RiskAssessmentResult(
            overall_risk_score=overall_score,
            overall_risk_level=self._score_to_level(overall_score),
            risk_factors=all_risk_factors,
            risk_categories=combined_categories,
            recommendations=[],
            compliance_status=self._determine_compliance_status(all_risk_factors, overall_score),
            assessment_confidence=self._calculate_confidence_score(request.context_data),
            assessment_timestamp=datetime.now()
        )
    
    async def _calculate_concentration_risk(self, context: Dict[str, Any]) -> float:
        """Berechnet Portfolio Concentration Risk"""
        
        # Mock Calculation basierend auf Portfolio Context
        largest_position_pct = self.portfolio_context.get('largest_position_percentage', 0.2)
        asset_count = self.portfolio_context.get('asset_count', 10)
        
        # Herfindahl-Hirschman Index Approximation
        concentration_score = largest_position_pct
        
        # Penalize for few assets
        if asset_count < 5:
            concentration_score += 0.1
        
        return min(1.0, concentration_score)
    
    async def _calculate_volatility_risk(self, context: Dict[str, Any]) -> float:
        """Berechnet Portfolio Volatility Risk"""
        
        # Mock Calculation
        market_vol = self.market_data.get('volatility_index', 0.2)
        crypto_exposure = context.get('crypto_exposure_percentage', 0.3)
        
        # Higher crypto exposure = higher volatility
        portfolio_volatility = market_vol + (crypto_exposure * 0.3)
        
        return min(1.0, portfolio_volatility)
    
    async def _analyze_transaction_patterns(self, context: Dict[str, Any]) -> float:
        """Analysiert Transaction Patterns für Anomalien"""
        
        # Mock Pattern Analysis
        amount_variation = context.get('amount_std_deviation', 0.2)
        timing_regularity = context.get('timing_regularity_score', 0.8)
        
        # Higher variation and lower regularity = more suspicious
        pattern_risk = amount_variation + (1 - timing_regularity)
        
        return min(1.0, pattern_risk)
    
    async def _assess_correlation_risk(self, context: Dict[str, Any]) -> float:
        """Bewertet Asset Correlation Risk"""
        
        # Mock Correlation Assessment
        avg_correlation = 0.4  # Average correlation between assets
        
        return min(1.0, avg_correlation)
    
    async def _calculate_weighted_risk_score(self, risk_categories: Dict[str, Dict]) -> float:
        """Berechnet gewichteten Risk Score"""
        
        if not risk_categories:
            return 0.0
        
        total_score = 0.0
        total_weight = 0.0
        
        for category, data in risk_categories.items():
            score = data.get('score', 0)
            weight = self.risk_weights.get(category, 0.1)  # Default weight
            
            total_score += score * weight
            total_weight += weight
        
        return round(total_score / total_weight if total_weight > 0 else 0, 1)
    

        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())

    def _score_to_level(self, score: float) -> str:
        """Konvertiert Risk Score zu Risk Level"""
        
        if score >= 75:
            return 'critical'
        elif score >= 50:
            return 'high'
        elif score >= 25:
            return 'medium'
        else:
            return 'low'
    
    def _determine_compliance_status(self, risk_factors: List[RiskFactor], overall_score: float) -> str:
        """Bestimmt Compliance Status"""
        
        critical_factors = [rf for rf in risk_factors if rf.risk_level == 'critical']
        high_factors = [rf for rf in risk_factors if rf.risk_level == 'high']
        
        if critical_factors or overall_score >= 80:
            return 'violation'
        elif high_factors or overall_score >= 60:
            return 'warning'
        else:
            return 'compliant'
    
    def _calculate_confidence_score(self, context: Dict[str, Any]) -> float:
        """Berechnet Assessment Confidence Score"""
        
        # Mock Confidence basierend auf verfügbaren Daten
        data_completeness = len(context) / 10  # Mehr Daten = höhere Confidence
        recency_bonus = 1.0  # Recent data gets bonus
        
        confidence = min(100, (data_completeness + recency_bonus) * 40)
        return round(confidence, 1)
    
    async def _generate_risk_recommendations(self, assessment_result: RiskAssessmentResult) -> List[str]:
        """Generiert Risk-basierte Empfehlungen"""
        
        recommendations = []
        
        # Overall Risk Level Empfehlungen
        if assessment_result.overall_risk_level == 'critical':
            recommendations.extend([
                "Immediate action required - suspend high-risk activities",
                "Enhanced monitoring and manual review recommended",
                "Consider position size reductions"
            ])
        elif assessment_result.overall_risk_level == 'high':
            recommendations.extend([
                "Implement additional risk controls",
                "Review and adjust risk parameters",
                "Consider diversification strategies"
            ])
        
        # Factor-spezifische Empfehlungen
        for risk_factor in assessment_result.risk_factors:
            if risk_factor.risk_level in ['high', 'critical']:
                recommendations.extend(risk_factor.mitigation_suggestions[:2])  # Top 2 suggestions
        
        return list(set(recommendations))  # Remove duplicates
    
    def _risk_factor_to_dict(self, risk_factor: RiskFactor) -> Dict[str, Any]:
        """Konvertiert RiskFactor zu Dictionary"""
        
        return {
            'factor_name': risk_factor.factor_name,
            'risk_level': risk_factor.risk_level,
            'risk_score': risk_factor.risk_score,
            'description': risk_factor.description,
            'mitigation_suggestions': risk_factor.mitigation_suggestions
        }
    
    def _has_valid_cache(self, cache_key: str) -> bool:
        """Prüft ob Cache für Key noch gültig ist"""
        
        if cache_key not in self.cache_timestamps:
            return False
        
        cache_age = (datetime.now() - self.cache_timestamps[cache_key]).seconds
        max_cache_age = 600  # 10 minutes
        
        return cache_age < max_cache_age
    
    async def _publish_risk_alert_event(self, assessment_result: RiskAssessmentResult):
        """Published Risk Alert Event über Event-Bus"""
        
        if not self.event_bus or not self.event_bus.connected:
            return
        
        from event_bus import Event
        
        event = Event(
            event_type="risk_alert_raised",
            stream_id=f"risk-alert-{self.assessment_counter}",
            data={
                'overall_risk_score': assessment_result.overall_risk_score,
                'overall_risk_level': assessment_result.overall_risk_level,
                'critical_factors_count': len([rf for rf in assessment_result.risk_factors if rf.risk_level == 'critical']),
                'compliance_status': assessment_result.compliance_status,
                'assessment_timestamp': assessment_result.assessment_timestamp.isoformat(),
                'requires_immediate_action': assessment_result.overall_risk_level == 'critical'
            },
            source="risk_assessment"
        )
        
        await self.event_bus.publish(event)
    
    def get_risk_summary(self, assessment_type: str = None) -> Dict[str, Any]:
        """Gibt Risk Assessment Summary zurück"""
        
        if not self.assessment_history:
            return {'error': 'No assessment history available'}
        
        # Filter by assessment type if specified
        relevant_assessments = self.assessment_history
        if assessment_type:
            relevant_assessments = [a for a in self.assessment_history if a['assessment_type'] == assessment_type]
        
        if not relevant_assessments:
            return {'error': f'No assessments found for type: {assessment_type}'}
        
        # Recent assessments (last 24 hours)
        recent_assessments = [
            a for a in relevant_assessments
            if (datetime.now() - a['timestamp']).days == 0
        ]
        
        # Risk level distribution
        risk_levels = [a['overall_risk_level'] for a in relevant_assessments]
        risk_distribution = {level: risk_levels.count(level) for level in ['low', 'medium', 'high', 'critical']}
        
        # Average risk score
        avg_risk_score = sum(a['overall_risk_score'] for a in relevant_assessments) / len(relevant_assessments)
        
        return {
            'total_assessments': len(relevant_assessments),
            'recent_assessments_24h': len(recent_assessments),
            'average_risk_score': round(avg_risk_score, 1),
            'risk_level_distribution': risk_distribution,
            'current_compliance_status': relevant_assessments[-1]['compliance_status'] if relevant_assessments else 'unknown',
            'assessment_types_available': list(set(a['assessment_type'] for a in self.assessment_history))
        }
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'risk_assessment',
            'description': 'Comprehensive risk assessment across portfolio, transactions, account and trading activities',
            'responsibility': 'Risk assessment logic only',
            'input_parameters': {
                'assessment_type': 'Required assessment type (portfolio, transaction, account, trading, comprehensive)',
                'context_data': 'Required context data specific to assessment type',
                'risk_tolerance': 'Optional risk tolerance level (low, medium, high)',
                'assessment_scope': 'Optional assessment scope (basic, comprehensive, detailed)',
                'include_recommendations': 'Whether to include risk mitigation recommendations (default: true)',
                'force_refresh': 'Whether to force refresh cached assessments (default: false)'
            },
            'output_format': {
                'overall_risk_score': 'Overall risk score from 0-100',
                'overall_risk_level': 'Overall risk level (low, medium, high, critical)',
                'risk_factors': 'List of identified risk factors with details',
                'risk_categories': 'Risk breakdown by category with scores',
                'recommendations': 'Risk mitigation recommendations',
                'compliance_status': 'Compliance status (compliant, warning, violation)',
                'assessment_confidence': 'Confidence level in assessment (0-100)',
                'assessment_timestamp': 'Timestamp of assessment'
            },
            'supported_assessment_types': ['portfolio', 'transaction', 'account', 'trading', 'comprehensive'],
            'risk_categories': list(self.risk_weights.keys()),
            'cache_duration_seconds': 600,
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_risk_statistics(self) -> Dict[str, Any]:
        """Risk Assessment Module Statistiken"""
        total_assessments = len(self.assessment_history)
        
        if total_assessments == 0:
            return {
                'total_assessments': 0,
                'supported_assessment_types': 5,
                'cache_entries': len(self.risk_cache)
            }
        
        # Assessment Type Distribution
        type_distribution = {}
        for assessment in self.assessment_history:
            assessment_type = assessment['assessment_type']
            type_distribution[assessment_type] = type_distribution.get(assessment_type, 0) + 1
        
        # Risk Level Distribution
        level_distribution = {}
        for assessment in self.assessment_history:
            risk_level = assessment['overall_risk_level']
            level_distribution[risk_level] = level_distribution.get(risk_level, 0) + 1
        
        # Compliance Status Distribution
        compliance_distribution = {}
        for assessment in self.assessment_history:
            compliance = assessment['compliance_status']
            compliance_distribution[compliance] = compliance_distribution.get(compliance, 0) + 1
        
        # Average Scores
        avg_risk_score = sum(a['overall_risk_score'] for a in self.assessment_history) / total_assessments
        avg_confidence = sum(a['assessment_confidence'] for a in self.assessment_history) / total_assessments
        
        # High Risk Rate
        high_risk_assessments = sum(1 for a in self.assessment_history if a['overall_risk_level'] in ['high', 'critical'])
        high_risk_rate = round((high_risk_assessments / total_assessments) * 100, 1)
        
        # Recent Activity
        recent_assessments = [
            a for a in self.assessment_history
            if (datetime.now() - a['timestamp']).seconds < 3600  # Last hour
        ]
        
        return {
            'total_assessments': total_assessments,
            'recent_assessments_last_hour': len(recent_assessments),
            'assessment_type_distribution': dict(sorted(
                type_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'risk_level_distribution': dict(sorted(
                level_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'compliance_status_distribution': compliance_distribution,
            'average_risk_score': round(avg_risk_score, 1),
            'average_confidence_score': round(avg_confidence, 1),
            'high_risk_rate_percent': high_risk_rate,
            'cache_entries_active': len(self.risk_cache),
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
