"""
Order Risk Assessment Module - Single Function Module
Verantwortlich ausschließlich für Order Risk Assessment Logic
"""

import asyncio
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import timedelta
import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from shared.common_imports import (
    datetime, BaseModel, structlog
)
from ..single_function_module_base import SingleFunctionModule
from .order_placement_module import OrderSide, OrderType


class RiskAssessmentRequest(BaseModel):
    order_data: Dict[str, Any]
    account_data: Optional[Dict[str, Any]] = None
    portfolio_data: Optional[Dict[str, Any]] = None
    market_data: Optional[Dict[str, Any]] = None


class RiskFactor(BaseModel):
    factor_name: str
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    risk_score: float  # 0.0 to 1.0
    description: str
    recommendation: Optional[str] = None


class RiskAssessmentResult(BaseModel):
    order_id: str
    overall_risk_score: float  # 0.0 to 1.0
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    risk_factors: List[RiskFactor]
    recommendations: List[str]
    approval_status: str  # 'approved', 'conditional', 'rejected'
    assessment_timestamp: datetime


class OrderRiskAssessmentModule(SingleFunctionModule):
    """
    Single Function Module: Order Risk Assessment
    Verantwortlichkeit: Ausschließlich Order-Risk-Assessment-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("order_risk_assessment", event_bus)
        
        # Risk Assessment History
        self.assessment_history = {}
        self.assessment_counter = 0
        
        # Risk Thresholds
        self.risk_thresholds = {
            'low': 0.3,
            'medium': 0.6,
            'high': 0.8,
            'critical': 1.0
        }
        
        # Risk Weights für verschiedene Faktoren
        self.risk_weights = {
            'position_size_risk': 0.25,
            'volatility_risk': 0.20,
            'liquidity_risk': 0.15,
            'concentration_risk': 0.15,
            'market_timing_risk': 0.10,
            'technical_risk': 0.10,
            'regulatory_risk': 0.05
        }
        
        # Risk Limits
        self.risk_limits = {
            'max_position_size_percent': 10.0,  # Max 10% of portfolio per position
            'max_daily_volume_percent': 20.0,   # Max 20% of daily portfolio value
            'max_volatility_threshold': 0.05,   # Max 5% volatility
            'min_liquidity_threshold': 1000000, # Min €1M daily volume
            'max_concentration_per_asset': 0.25 # Max 25% in single asset
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Order Risk Assessment
        
        Args:
            input_data: {
                'assessment_request': RiskAssessmentRequest dict
            }
            
        Returns:
            Dict mit Risk-Assessment-Result
        """
        assessment_request_data = input_data.get('assessment_request')
        
        if not assessment_request_data:
            raise ValueError('No risk assessment request provided')
        
        # RiskAssessmentRequest parsieren
        try:
            assessment_request = RiskAssessmentRequest(**assessment_request_data)
        except Exception as e:
            raise ValueError(f'Invalid risk assessment request format: {str(e)}')
        
        # Risk Assessment durchführen
        assessment_result = await self._perform_comprehensive_risk_assessment(assessment_request)
        
        # Assessment in History speichern
        self.assessment_history[assessment_result.order_id] = assessment_result
        
        return {
            'order_id': assessment_result.order_id,
            'overall_risk_score': assessment_result.overall_risk_score,
            'risk_level': assessment_result.risk_level,
            'risk_factors': [factor.dict() for factor in assessment_result.risk_factors],
            'recommendations': assessment_result.recommendations,
            'approval_status': assessment_result.approval_status,
            'assessment_timestamp': assessment_result.assessment_timestamp.isoformat()
        }
    
    async def _perform_comprehensive_risk_assessment(self, 
                                                   assessment_request: RiskAssessmentRequest) -> RiskAssessmentResult:
        """Führt umfassende Risk Assessment durch"""
        self.assessment_counter += 1
        order_data = assessment_request.order_data
        order_id = order_data.get('order_id', f"RISK-ASSESS-{self.assessment_counter:06d}")
        
        # Alle Risk Factors berechnen
        risk_factors = []
        
        # 1. Position Size Risk
        position_risk = await self._assess_position_size_risk(
            order_data, assessment_request.portfolio_data
        )
        risk_factors.append(position_risk)
        
        # 2. Volatility Risk
        volatility_risk = await self._assess_volatility_risk(
            order_data, assessment_request.market_data
        )
        risk_factors.append(volatility_risk)
        
        # 3. Liquidity Risk
        liquidity_risk = await self._assess_liquidity_risk(
            order_data, assessment_request.market_data
        )
        risk_factors.append(liquidity_risk)
        
        # 4. Concentration Risk
        concentration_risk = await self._assess_concentration_risk(
            order_data, assessment_request.portfolio_data
        )
        risk_factors.append(concentration_risk)
        
        # 5. Market Timing Risk
        timing_risk = await self._assess_market_timing_risk(
            order_data, assessment_request.market_data
        )
        risk_factors.append(timing_risk)
        
        # 6. Technical Risk
        technical_risk = await self._assess_technical_risk(order_data)
        risk_factors.append(technical_risk)
        
        # 7. Regulatory Risk
        regulatory_risk = await self._assess_regulatory_risk(
            order_data, assessment_request.account_data
        )
        risk_factors.append(regulatory_risk)
        
        # Overall Risk Score berechnen
        overall_risk_score = self._calculate_overall_risk_score(risk_factors)
        
        # Risk Level bestimmen
        risk_level = self._determine_risk_level(overall_risk_score)
        
        # Recommendations generieren
        recommendations = await self._generate_risk_recommendations(risk_factors, overall_risk_score)
        
        # Approval Status bestimmen
        approval_status = self._determine_approval_status(overall_risk_score, risk_factors)
        
        assessment_result = RiskAssessmentResult(
            order_id=order_id,
            overall_risk_score=overall_risk_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            recommendations=recommendations,
            approval_status=approval_status,
            assessment_timestamp=datetime.now()
        )
        
        self.logger.info(f"Risk assessment completed",
                       order_id=order_id,
                       risk_score=overall_risk_score,
                       risk_level=risk_level,
                       approval_status=approval_status)
        
        return assessment_result
    
    async def _assess_position_size_risk(self, order_data: Dict[str, Any], 
                                       portfolio_data: Optional[Dict[str, Any]]) -> RiskFactor:
        """Bewertet Position Size Risk"""
        
        order_value = self._calculate_order_value(order_data)
        
        if not portfolio_data:
            # Konservativer Approach ohne Portfolio Daten
            return RiskFactor(
                factor_name="position_size_risk",
                risk_level="medium",
                risk_score=0.5,
                description="Cannot assess position size risk without portfolio data",
                recommendation="Provide portfolio data for accurate risk assessment"
            )
        
        portfolio_value = portfolio_data.get('total_value', 100000)  # Fallback
        position_percentage = (order_value / portfolio_value) * 100
        
        # Risk Score basierend auf Position Size
        if position_percentage <= 2.0:
            risk_score = 0.1
            risk_level = "low"
            description = f"Small position size: {position_percentage:.1f}% of portfolio"
        elif position_percentage <= 5.0:
            risk_score = 0.3
            risk_level = "medium"
            description = f"Moderate position size: {position_percentage:.1f}% of portfolio"
        elif position_percentage <= self.risk_limits['max_position_size_percent']:
            risk_score = 0.6
            risk_level = "medium"
            description = f"Large position size: {position_percentage:.1f}% of portfolio"
        else:
            risk_score = 0.9
            risk_level = "high"
            description = f"Excessive position size: {position_percentage:.1f}% of portfolio (max: {self.risk_limits['max_position_size_percent']:.1f}%)"
        
        recommendation = None
        if position_percentage > 5.0:
            recommendation = f"Consider reducing position size to below 5% of portfolio"
        
        return RiskFactor(
            factor_name="position_size_risk",
            risk_level=risk_level,
            risk_score=risk_score,
            description=description,
            recommendation=recommendation
        )
    
    async def _assess_volatility_risk(self, order_data: Dict[str, Any], 
                                    market_data: Optional[Dict[str, Any]]) -> RiskFactor:
        """Bewertet Volatility Risk"""
        
        if not market_data:
            return RiskFactor(
                factor_name="volatility_risk",
                risk_level="medium",
                risk_score=0.4,
                description="Cannot assess volatility risk without market data",
                recommendation="Provide market data for accurate volatility assessment"
            )
        
        instrument = order_data.get('instrument_code', 'UNKNOWN')
        volatility = market_data.get('volatility', {}).get(instrument, 0.02)  # Default 2%
        
        # Risk Score basierend auf Volatility
        if volatility <= 0.01:  # 1%
            risk_score = 0.1
            risk_level = "low"
            description = f"Low volatility: {volatility:.1%}"
        elif volatility <= 0.03:  # 3%
            risk_score = 0.3
            risk_level = "medium"
            description = f"Moderate volatility: {volatility:.1%}"
        elif volatility <= self.risk_limits['max_volatility_threshold']:
            risk_score = 0.6
            risk_level = "medium"
            description = f"High volatility: {volatility:.1%}"
        else:
            risk_score = 0.9
            risk_level = "high"
            description = f"Extreme volatility: {volatility:.1%} (threshold: {self.risk_limits['max_volatility_threshold']:.1%})"
        
        recommendation = None
        if volatility > 0.05:
            recommendation = "Consider using limit orders or reducing position size due to high volatility"
        
        return RiskFactor(
            factor_name="volatility_risk",
            risk_level=risk_level,
            risk_score=risk_score,
            description=description,
            recommendation=recommendation
        )
    
    async def _assess_liquidity_risk(self, order_data: Dict[str, Any], 
                                   market_data: Optional[Dict[str, Any]]) -> RiskFactor:
        """Bewertet Liquidity Risk"""
        
        if not market_data:
            return RiskFactor(
                factor_name="liquidity_risk",
                risk_level="medium",
                risk_score=0.4,
                description="Cannot assess liquidity risk without market data",
                recommendation="Provide market data for accurate liquidity assessment"
            )
        
        instrument = order_data.get('instrument_code', 'UNKNOWN')
        daily_volume = market_data.get('daily_volume', {}).get(instrument, 500000)  # Default €500k
        order_value = self._calculate_order_value(order_data)
        
        # Order als Prozent des Daily Volume
        volume_percentage = (order_value / daily_volume) * 100 if daily_volume > 0 else 100
        
        # Risk Score basierend auf Liquidity
        if daily_volume >= self.risk_limits['min_liquidity_threshold'] and volume_percentage <= 1.0:
            risk_score = 0.1
            risk_level = "low"
            description = f"Good liquidity: {order_value/1000:.0f}k order in {daily_volume/1000000:.1f}M daily volume"
        elif volume_percentage <= 5.0:
            risk_score = 0.3
            risk_level = "medium"
            description = f"Moderate liquidity impact: {volume_percentage:.1f}% of daily volume"
        elif volume_percentage <= 10.0:
            risk_score = 0.6
            risk_level = "medium"
            description = f"Significant liquidity impact: {volume_percentage:.1f}% of daily volume"
        else:
            risk_score = 0.9
            risk_level = "high"
            description = f"High liquidity risk: {volume_percentage:.1f}% of daily volume"
        
        recommendation = None
        if volume_percentage > 5.0:
            recommendation = "Consider splitting order into smaller chunks to reduce market impact"
        
        return RiskFactor(
            factor_name="liquidity_risk",
            risk_level=risk_level,
            risk_score=risk_score,
            description=description,
            recommendation=recommendation
        )
    
    async def _assess_concentration_risk(self, order_data: Dict[str, Any], 
                                       portfolio_data: Optional[Dict[str, Any]]) -> RiskFactor:
        """Bewertet Concentration Risk"""
        
        if not portfolio_data:
            return RiskFactor(
                factor_name="concentration_risk",
                risk_level="medium",
                risk_score=0.4,
                description="Cannot assess concentration risk without portfolio data",
                recommendation="Provide portfolio data for concentration analysis"
            )
        
        instrument = order_data.get('instrument_code', 'UNKNOWN')
        order_value = self._calculate_order_value(order_data)
        portfolio_value = portfolio_data.get('total_value', 100000)
        
        # Aktuelle Position in diesem Instrument
        current_position = portfolio_data.get('positions', {}).get(instrument, 0)
        new_position_value = current_position + order_value
        concentration_percentage = (new_position_value / portfolio_value) * 100
        
        # Risk Score basierend auf Concentration
        if concentration_percentage <= 5.0:
            risk_score = 0.1
            risk_level = "low"
            description = f"Good diversification: {concentration_percentage:.1f}% in {instrument}"
        elif concentration_percentage <= 15.0:
            risk_score = 0.3
            risk_level = "medium"
            description = f"Moderate concentration: {concentration_percentage:.1f}% in {instrument}"
        elif concentration_percentage <= self.risk_limits['max_concentration_per_asset'] * 100:
            risk_score = 0.6
            risk_level = "medium"
            description = f"High concentration: {concentration_percentage:.1f}% in {instrument}"
        else:
            risk_score = 0.9
            risk_level = "high"
            description = f"Excessive concentration: {concentration_percentage:.1f}% in {instrument} (max: {self.risk_limits['max_concentration_per_asset']*100:.0f}%)"
        
        recommendation = None
        if concentration_percentage > 20.0:
            recommendation = f"Consider diversifying - {instrument} concentration will be {concentration_percentage:.1f}%"
        
        return RiskFactor(
            factor_name="concentration_risk",
            risk_level=risk_level,
            risk_score=risk_score,
            description=description,
            recommendation=recommendation
        )
    
    async def _assess_market_timing_risk(self, order_data: Dict[str, Any], 
                                       market_data: Optional[Dict[str, Any]]) -> RiskFactor:
        """Bewertet Market Timing Risk"""
        
        # Zeit-basierte Faktoren
        current_hour = datetime.now().hour
        current_weekday = datetime.now().weekday()
        
        # Market Hours Check (9-17 Uhr, Mo-Fr sind optimal)
        is_market_hours = 9 <= current_hour <= 17 and current_weekday < 5
        
        # Order Type Risk
        order_type = OrderType(order_data.get('type', 'MARKET'))
        
        risk_score = 0.2  # Base risk
        risk_factors = []
        
        # Market Hours Risk
        if not is_market_hours:
            risk_score += 0.3
            risk_factors.append("Outside optimal trading hours")
        
        # Order Type Risk
        if order_type == OrderType.MARKET:
            if not is_market_hours:
                risk_score += 0.2
                risk_factors.append("Market order outside market hours")
        
        # Market Conditions Risk
        if market_data:
            market_trend = market_data.get('trend', 'neutral')
            if market_trend in ['strong_bearish', 'strong_bullish']:
                risk_score += 0.2
                risk_factors.append(f"Strong market trend: {market_trend}")
        
        # Final Risk Assessment
        risk_score = min(risk_score, 1.0)
        
        if risk_score <= 0.3:
            risk_level = "low"
            description = "Good market timing conditions"
        elif risk_score <= 0.6:
            risk_level = "medium"
            description = f"Moderate timing risk: {', '.join(risk_factors)}"
        else:
            risk_level = "high"
            description = f"Poor timing conditions: {', '.join(risk_factors)}"
        
        recommendation = None
        if not is_market_hours:
            recommendation = "Consider waiting for market open or using limit orders"
        
        return RiskFactor(
            factor_name="market_timing_risk",
            risk_level=risk_level,
            risk_score=risk_score,
            description=description,
            recommendation=recommendation
        )
    
    async def _assess_technical_risk(self, order_data: Dict[str, Any]) -> RiskFactor:
        """Bewertet Technical Risk"""
        
        risk_score = 0.1  # Base low risk
        risk_factors = []
        
        # Order Type Technical Risk
        order_type = OrderType(order_data.get('type', 'MARKET'))
        if order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            risk_score += 0.2
            risk_factors.append("Stop order execution risk")
        
        # Order Size Technical Risk
        order_amount = float(order_data.get('amount', '0'))
        if order_amount < 0.001:  # Very small orders
            risk_score += 0.1
            risk_factors.append("Very small order size")
        elif order_amount > 1000000:  # Very large orders
            risk_score += 0.3
            risk_factors.append("Very large order size")
        
        # Price Precision Risk
        if order_data.get('price'):
            price_str = str(order_data['price'])
            decimal_places = len(price_str.split('.')[-1]) if '.' in price_str else 0
            if decimal_places > 8:
                risk_score += 0.1
                risk_factors.append("High price precision")
        
        # Final Assessment
        risk_score = min(risk_score, 1.0)
        
        if risk_score <= 0.2:
            risk_level = "low"
            description = "Low technical execution risk"
        elif risk_score <= 0.5:
            risk_level = "medium"
            description = f"Moderate technical risk: {', '.join(risk_factors)}"
        else:
            risk_level = "high"
            description = f"High technical risk: {', '.join(risk_factors)}"
        
        return RiskFactor(
            factor_name="technical_risk",
            risk_level=risk_level,
            risk_score=risk_score,
            description=description,
            recommendation=None
        )
    
    async def _assess_regulatory_risk(self, order_data: Dict[str, Any], 
                                    account_data: Optional[Dict[str, Any]]) -> RiskFactor:
        """Bewertet Regulatory Risk"""
        
        risk_score = 0.1  # Base low risk
        risk_factors = []
        
        # Account Type Risk
        if account_data:
            account_type = account_data.get('account_type', 'retail')
            if account_type == 'retail':
                # Retail accounts have more restrictions
                order_value = self._calculate_order_value(order_data)
                if order_value > 50000:  # Large retail orders
                    risk_score += 0.2
                    risk_factors.append("Large retail order")
        
        # Instrument Type Risk
        instrument = order_data.get('instrument_code', '')
        if 'crypto' in instrument.lower() or any(crypto in instrument.upper() for crypto in ['BTC', 'ETH', 'ADA']):
            risk_score += 0.1
            risk_factors.append("Cryptocurrency trading")
        
        # Leverage Risk (falls applicable)
        leverage = order_data.get('leverage', 1)
        if leverage > 1:
            risk_score += min(leverage / 10, 0.4)  # Max 0.4 additional risk
            risk_factors.append(f"Leveraged trading: {leverage}x")
        
        # Final Assessment
        risk_score = min(risk_score, 1.0)
        
        if risk_score <= 0.2:
            risk_level = "low"
            description = "Low regulatory risk"
        elif risk_score <= 0.5:
            risk_level = "medium"
            description = f"Moderate regulatory considerations: {', '.join(risk_factors)}"
        else:
            risk_level = "high"
            description = f"High regulatory risk: {', '.join(risk_factors)}"
        
        recommendation = None
        if leverage > 5:
            recommendation = "Consider reducing leverage due to regulatory and risk concerns"
        
        return RiskFactor(
            factor_name="regulatory_risk",
            risk_level=risk_level,
            risk_score=risk_score,
            description=description,
            recommendation=recommendation
        )
    
    def _calculate_order_value(self, order_data: Dict[str, Any]) -> float:
        """Berechnet Order Value in EUR"""
        amount = float(order_data.get('amount', '0'))
        price = float(order_data.get('price', '0')) if order_data.get('price') else 1000  # Fallback price
        
        # Für Market Orders: Schätzung mit aktuellen Preisen
        instrument = order_data.get('instrument_code', '')
        if 'BTC' in instrument:
            estimated_price = 45000
        elif 'ETH' in instrument:
            estimated_price = 2500
        else:
            estimated_price = price if price > 0 else 100
        
        return amount * estimated_price
    
    def _calculate_overall_risk_score(self, risk_factors: List[RiskFactor]) -> float:
        """Berechnet Overall Risk Score mit Gewichtung"""
        weighted_score = 0.0
        total_weight = 0.0
        
        for factor in risk_factors:
            weight = self.risk_weights.get(factor.factor_name, 0.1)
            weighted_score += factor.risk_score * weight
            total_weight += weight
        
        return round(weighted_score / total_weight if total_weight > 0 else 0.5, 3)
    
    def _determine_risk_level(self, overall_risk_score: float) -> str:
        """Bestimmt Risk Level basierend auf Score"""
        for level, threshold in sorted(self.risk_thresholds.items(), key=lambda x: x[1]):
            if overall_risk_score <= threshold:
                return level
        return "critical"
    
    async def _generate_risk_recommendations(self, risk_factors: List[RiskFactor], 
                                           overall_risk_score: float) -> List[str]:
        """Generiert Risk Recommendations"""
        recommendations = []
        
        # Faktor-spezifische Recommendations sammeln
        for factor in risk_factors:
            if factor.recommendation:
                recommendations.append(factor.recommendation)
        
        # Overall Risk Recommendations
        if overall_risk_score > 0.8:
            recommendations.append("Consider reducing order size or postponing trade due to high overall risk")
        elif overall_risk_score > 0.6:
            recommendations.append("Monitor trade closely due to elevated risk level")
        
        # High Risk Factors
        high_risk_factors = [f for f in risk_factors if f.risk_score > 0.7]
        if len(high_risk_factors) > 2:
            recommendations.append("Multiple high-risk factors detected - consider comprehensive review")
        
        return list(set(recommendations))  # Remove duplicates
    
    def _determine_approval_status(self, overall_risk_score: float, 
                                 risk_factors: List[RiskFactor]) -> str:
        """Bestimmt Approval Status"""
        
        # Critical Risk Factors Check
        critical_factors = [f for f in risk_factors if f.risk_level == 'critical']
        if critical_factors:
            return "rejected"
        
        # Overall Risk Score Check
        if overall_risk_score >= 0.9:
            return "rejected"
        elif overall_risk_score >= 0.7:
            return "conditional"
        else:
            return "approved"
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'order_risk_assessment',
            'description': 'Comprehensive risk assessment for trading orders',
            'responsibility': 'Order risk assessment logic only',
            'input_parameters': {
                'assessment_request': 'RiskAssessmentRequest with order, account, portfolio, and market data'
            },
            'output_format': {
                'overall_risk_score': 'Weighted risk score (0.0-1.0)',
                'risk_level': 'Risk level classification',
                'risk_factors': 'Detailed risk factor analysis',
                'recommendations': 'Risk mitigation recommendations',
                'approval_status': 'Trade approval recommendation'
            },
            'risk_factors_assessed': list(self.risk_weights.keys()),
            'risk_levels': list(self.risk_thresholds.keys()),
            'risk_limits': self.risk_limits,
            'approval_statuses': ['approved', 'conditional', 'rejected'],
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_risk_statistics(self) -> Dict[str, Any]:
        """Risk Assessment Statistiken abrufen"""
        total_assessments = len(self.assessment_history)
        
        if total_assessments == 0:
            return {
                'total_assessments': 0,
                'average_risk_score': 0.0,
                'risk_level_distribution': {},
                'approval_status_distribution': {}
            }
        
        # Statistiken berechnen
        risk_scores = [a.overall_risk_score for a in self.assessment_history.values()]
        average_risk_score = sum(risk_scores) / len(risk_scores)
        
        # Verteilungen
        risk_levels = [a.risk_level for a in self.assessment_history.values()]
        approval_statuses = [a.approval_status for a in self.assessment_history.values()]
        
        risk_level_dist = {level: risk_levels.count(level) for level in set(risk_levels)}
        approval_dist = {status: approval_statuses.count(status) for status in set(approval_statuses)}
        
        return {
            'total_assessments': total_assessments,
            'average_risk_score': round(average_risk_score, 3),
            'risk_level_distribution': risk_level_dist,
            'approval_status_distribution': approval_dist,
            'average_response_time': self.average_execution_time,
            'risk_thresholds': self.risk_thresholds,
            'risk_weights': self.risk_weights

    async def _setup_event_subscriptions(self):
        """Setup Event-Bus Subscriptions for Order Module"""
        try:
            # Subscribe to system health requests
            await self.event_bus.subscribe('system.health.request', self.process_event)
            
            # Subscribe to module-specific order events
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            await self.event_bus.subscribe('order.status.request', self.process_event)
            await self.event_bus.subscribe('order.update', self.process_event)
            
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
                        'execution_count': len(self.execution_history),
                        'average_execution_time_ms': self.average_execution_time,
                        'orders_processed': getattr(self, 'orders_processed', 0),
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
            
            elif event_type == 'order.status.request':
                # Order status request
                order_id = event.get('data', {}).get('order_id')
                if order_id and hasattr(self, 'get_order_status'):
                    status = self.get_order_status(order_id)
                    status_response = {
                        'event_type': 'order.status.response',
                        'stream_id': event.get('stream_id', 'order-status'),
                        'data': {
                            'order_id': order_id,
                            'status': status,
                            'module': self.module_name
                        },
                        'source': self.module_name,
                        'correlation_id': event.get('correlation_id')
                    }
                    await self.event_bus.publish(status_response)
            
            else:
                self.logger.debug("Unhandled event type",
                                event_type=event_type, module=self.module_name)
                
        except Exception as e:
            self.logger.error("Failed to process event",
                            error=str(e), event=str(event), module=self.module_name)

    async def publish_order_event(self, event_type: str, order_data: dict):
        """Publish order-related events"""
        if not self.event_bus:
            return
            
        try:
            order_event = {
                'event_type': event_type,
                'stream_id': f'order-{order_data.get("order_id", "unknown")}',
                'data': {
                    **order_data,
                    'timestamp': datetime.now().isoformat(),
                    'processing_module': self.module_name
                },
                'source': self.module_name
            }
            await self.event_bus.publish(order_event)
            
        except Exception as e:
            self.logger.error("Failed to publish order event",
                            error=str(e), event_type=event_type)
        }