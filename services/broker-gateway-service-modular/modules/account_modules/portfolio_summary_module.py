from typing import Dict, Any, List, Optional
import sys
from shared.common_imports import (
import asyncio
from ..single_function_module_base import SingleFunctionModule
"""
Portfolio Summary Module - Single Function Module
Verantwortlich ausschließlich für Portfolio Summary Generation Logic
"""

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

    datetime, BaseModel, structlog
)


class PortfolioPosition(BaseModel):
    currency_code: str
    balance: float
    price_eur: float
    value_eur: float
    percentage: float
    performance_24h: Optional[float] = 0.0
    risk_score: float


class PortfolioSummaryResult(BaseModel):
    total_value_eur: float
    positions: Dict[str, Dict[str, Any]]
    currencies_count: int
    largest_position: Optional[Dict[str, Any]]
    diversification_score: float
    performance_summary: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    last_updated: datetime
    retrieval_timestamp: datetime


class PortfolioSummaryModule(SingleFunctionModule):
    """
    Single Function Module: Portfolio Summary Generation
    Verantwortlichkeit: Ausschließlich Portfolio-Summary-Generation-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("portfolio_summary", event_bus)
        
        # Mock Account Balances (normalerweise aus Account Service)
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
        
        # Mock Market Prices (normalerweise von Market Data Service)
        self.market_prices = {
            'EUR': {'price_eur': 1.0, 'change_24h': 0.0},
            'USD': {'price_eur': 0.85, 'change_24h': -0.5},  # EUR/USD rate
            'BTC': {'price_eur': 45000.0, 'change_24h': 2.3},  # BTC/EUR
            'ETH': {'price_eur': 2800.0, 'change_24h': -1.2}   # ETH/EUR
        }
        
        # Portfolio Summary Cache
        self.portfolio_cache = None
        self.cache_timestamp = None
        
        # Portfolio Statistics
        self.summary_generation_history = []
        self.generation_counter = 0
        
        # Risk Assessment Configuration
        self.risk_config = {
            'high_concentration_threshold': 50.0,  # >50% in single asset = high risk
            'low_diversification_threshold': 0.3,  # <0.3 diversification score = high risk
            'volatility_thresholds': {
                'low': 2.0,     # <2% daily change = low volatility
                'medium': 5.0,  # <5% daily change = medium volatility
                'high': 10.0    # >5% daily change = high volatility
            }
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Portfolio Summary Generation
        
        Args:
            input_data: {
                'refresh_cache': optional bool (default: false),
                'include_performance': optional bool (default: true),
                'include_risk_assessment': optional bool (default: true),
                'currency_filter': optional list of currencies to include,
                'min_value_eur': optional float - minimum position value to include
            }
            
        Returns:
            Dict mit Portfolio-Summary-Result
        """
        refresh_cache = input_data.get('refresh_cache', False)
        include_performance = input_data.get('include_performance', True)
        include_risk_assessment = input_data.get('include_risk_assessment', True)
        currency_filter = input_data.get('currency_filter', [])
        min_value_eur = input_data.get('min_value_eur', 0.0)
        
        # Portfolio Summary generieren
        portfolio_summary = await self._generate_portfolio_summary(
            refresh_cache, include_performance, include_risk_assessment, 
            currency_filter, min_value_eur
        )
        
        # Statistics Update
        self.generation_counter += 1
        
        # Generation History
        self.summary_generation_history.append({
            'timestamp': datetime.now(),
            'total_value_eur': portfolio_summary.total_value_eur,
            'positions_count': portfolio_summary.currencies_count,
            'diversification_score': portfolio_summary.diversification_score,
            'cache_refreshed': refresh_cache,
            'generation_id': self.generation_counter
        })
        
        # Limit History
        if len(self.summary_generation_history) > 150:
            self.summary_generation_history.pop(0)
        
        self.logger.info(f"Portfolio summary generated successfully",
                       total_value_eur=portfolio_summary.total_value_eur,
                       positions_count=portfolio_summary.currencies_count,
                       diversification_score=portfolio_summary.diversification_score,
                       generation_id=self.generation_counter)
        
        return {
            'success': True,
            'total_value_eur': portfolio_summary.total_value_eur,
            'positions': portfolio_summary.positions,
            'currencies_count': portfolio_summary.currencies_count,
            'largest_position': portfolio_summary.largest_position,
            'diversification_score': portfolio_summary.diversification_score,
            'performance_summary': portfolio_summary.performance_summary if include_performance else {},
            'risk_assessment': portfolio_summary.risk_assessment if include_risk_assessment else {},
            'last_updated': portfolio_summary.last_updated.isoformat(),
            'retrieval_timestamp': portfolio_summary.retrieval_timestamp.isoformat()
        }
    
    async def _generate_portfolio_summary(self, refresh_cache: bool, include_performance: bool,
                                        include_risk_assessment: bool, currency_filter: List[str],
                                        min_value_eur: float) -> PortfolioSummaryResult:
        """Generiert Portfolio Summary mit allen Details"""
        
        # Cache Check
        if (not refresh_cache and 
            self.portfolio_cache and 
            self.cache_timestamp and
            (datetime.now() - self.cache_timestamp).seconds < 120):  # 2 minutes cache
            
            # Apply filters to cached result if needed
            if not currency_filter and min_value_eur == 0.0:
                return self.portfolio_cache
        
        # Portfolio Positions berechnen
        total_value_eur = 0.0
        positions = {}
        
        for currency, balance_data in self.account_balances.items():
            # Currency Filter
            if currency_filter and currency not in currency_filter:
                continue
                
            total_balance = float(balance_data['total'])
            if total_balance <= 0:
                continue
            
            # Market Price abrufen
            price_info = self.market_prices.get(currency, {'price_eur': 1.0, 'change_24h': 0.0})
            price_eur = price_info['price_eur']
            value_eur = total_balance * price_eur
            
            # Min Value Filter
            if value_eur < min_value_eur:
                continue
            
            total_value_eur += value_eur
            
            # Position Details
            positions[currency] = {
                'currency_code': currency,
                'balance': total_balance,
                'price_eur': price_eur,
                'value_eur': round(value_eur, 2),
                'percentage': 0,  # Wird unten berechnet
                'performance_24h': price_info['change_24h'],
                'risk_score': self._calculate_position_risk_score(currency, value_eur, price_info['change_24h'])
            }
        
        # Percentage Calculation
        for currency in positions:
            if total_value_eur > 0:
                positions[currency]['percentage'] = round(
                    (positions[currency]['value_eur'] / total_value_eur) * 100, 2
                )
        
        # Largest Position ermitteln
        largest_position = self._find_largest_position(positions)
        
        # Diversification Score berechnen
        diversification_score = self._calculate_diversification_score(positions)
        
        # Performance Summary
        performance_summary = {}
        if include_performance:
            performance_summary = await self._calculate_performance_summary(positions, total_value_eur)
        
        # Risk Assessment
        risk_assessment = {}
        if include_risk_assessment:
            risk_assessment = await self._assess_portfolio_risk(positions, diversification_score, largest_position)
        
        # Portfolio Summary Result
        portfolio_summary = PortfolioSummaryResult(
            total_value_eur=round(total_value_eur, 2),
            positions=positions,
            currencies_count=len(positions),
            largest_position=largest_position,
            diversification_score=diversification_score,
            performance_summary=performance_summary,
            risk_assessment=risk_assessment,
            last_updated=datetime.now(),
            retrieval_timestamp=datetime.now()
        )
        
        # Cache Update
        self.portfolio_cache = portfolio_summary
        self.cache_timestamp = datetime.now()
        
        return portfolio_summary
    

        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())

    def _find_largest_position(self, positions: Dict[str, Dict]) -> Optional[Dict[str, Any]]:
        """Findet die größte Position im Portfolio"""
        if not positions:
            return None
        
        largest = max(positions.items(), key=lambda x: x[1]['value_eur'])
        return {
            'currency': largest[0],
            'value_eur': largest[1]['value_eur'],
            'percentage': largest[1]['percentage'],
            'balance': largest[1]['balance']
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
    
    def _calculate_position_risk_score(self, currency: str, value_eur: float, change_24h: float) -> float:
        """Berechnet Risk Score für einzelne Position"""
        
        risk_score = 0.0
        
        # Volatility Risk
        abs_change = abs(change_24h)
        if abs_change > self.risk_config['volatility_thresholds']['high']:
            risk_score += 3.0
        elif abs_change > self.risk_config['volatility_thresholds']['medium']:
            risk_score += 2.0
        elif abs_change > self.risk_config['volatility_thresholds']['low']:
            risk_score += 1.0
        
        # Asset Type Risk
        if currency in ['BTC', 'ETH']:  # Crypto assets
            risk_score += 2.0
        elif currency in ['USD', 'GBP']:  # Foreign fiat
            risk_score += 0.5
        # EUR = 0 additional risk (base currency)
        
        # Normalize to 0-10 scale
        return min(10.0, round(risk_score, 1))
    
    async def _calculate_performance_summary(self, positions: Dict[str, Dict], 
                                           total_value_eur: float) -> Dict[str, Any]:
        """Berechnet Performance Summary für Portfolio"""
        
        if not positions:
            return {}
        
        # Weighted Performance (by position value)
        weighted_performance_24h = 0.0
        best_performer = None
        worst_performer = None
        best_change = float('-inf')
        worst_change = float('inf')
        
        for currency, position in positions.items():
            weight = position['percentage'] / 100
            performance = position['performance_24h']
            weighted_performance_24h += performance * weight
            
            # Best/Worst Performer
            if performance > best_change:
                best_change = performance
                best_performer = {
                    'currency': currency,
                    'performance_24h': performance,
                    'value_eur': position['value_eur']
                }
            
            if performance < worst_change:
                worst_change = performance
                worst_performer = {
                    'currency': currency,
                    'performance_24h': performance,
                    'value_eur': position['value_eur']
                }
        
        # Performance Value Change
        performance_value_change_eur = (weighted_performance_24h / 100) * total_value_eur
        
        # Performance Categories
        gaining_positions = sum(1 for pos in positions.values() if pos['performance_24h'] > 0)
        losing_positions = sum(1 for pos in positions.values() if pos['performance_24h'] < 0)
        stable_positions = sum(1 for pos in positions.values() if pos['performance_24h'] == 0)
        
        return {
            'weighted_performance_24h_percent': round(weighted_performance_24h, 2),
            'performance_value_change_eur': round(performance_value_change_eur, 2),
            'best_performer': best_performer,
            'worst_performer': worst_performer,
            'gaining_positions': gaining_positions,
            'losing_positions': losing_positions,
            'stable_positions': stable_positions,
            'performance_trend': self._determine_performance_trend(weighted_performance_24h)
        }
    
    def _determine_performance_trend(self, performance_24h: float) -> str:
        """Bestimmt Performance Trend"""
        if performance_24h > 2.0:
            return 'strongly_positive'
        elif performance_24h > 0.5:
            return 'positive'
        elif performance_24h > -0.5:
            return 'stable'
        elif performance_24h > -2.0:
            return 'negative'
        else:
            return 'strongly_negative'
    
    async def _assess_portfolio_risk(self, positions: Dict[str, Dict], 
                                   diversification_score: float,
                                   largest_position: Optional[Dict]) -> Dict[str, Any]:
        """Bewertet Portfolio Risk"""
        
        risk_factors = []
        risk_score = 0
        
        # Concentration Risk
        if largest_position and largest_position['percentage'] > self.risk_config['high_concentration_threshold']:
            risk_factors.append('high_concentration')
            risk_score += 3
        
        # Diversification Risk
        if diversification_score < self.risk_config['low_diversification_threshold']:
            risk_factors.append('low_diversification')
            risk_score += 2
        
        # Volatility Risk (durchschnittliche Position Risk Scores)
        if positions:
            avg_position_risk = sum(pos['risk_score'] for pos in positions.values()) / len(positions)
            if avg_position_risk > 6.0:
                risk_factors.append('high_volatility')
                risk_score += 2
            elif avg_position_risk > 4.0:
                risk_factors.append('medium_volatility')
                risk_score += 1
        
        # Asset Type Risk (Crypto concentration)
        crypto_positions = sum(1 for pos in positions.values() if pos['currency_code'] in ['BTC', 'ETH'])
        crypto_percentage = (crypto_positions / len(positions)) * 100 if positions else 0
        
        if crypto_percentage > 70:
            risk_factors.append('high_crypto_concentration')
            risk_score += 2
        elif crypto_percentage > 40:
            risk_factors.append('medium_crypto_concentration')
            risk_score += 1
        
        # Determine overall risk level
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
            'diversification_score': diversification_score,
            'largest_position_percentage': largest_position['percentage'] if largest_position else 0,
            'crypto_concentration_percentage': round(crypto_percentage, 1),
            'recommendations': self._generate_risk_recommendations(risk_level, risk_factors)
        }
    
    def _generate_risk_recommendations(self, risk_level: str, risk_factors: list) -> list:
        """Generiert Risk-basierte Empfehlungen"""
        
        recommendations = []
        
        if risk_level == 'high':
            recommendations.append('Consider immediate portfolio rebalancing')
            
        if 'high_concentration' in risk_factors:
            recommendations.append('Reduce largest position size to improve diversification')
            
        if 'low_diversification' in risk_factors:
            recommendations.append('Add more diverse asset positions')
            
        if 'high_volatility' in risk_factors:
            recommendations.append('Consider adding stable assets to reduce volatility')
            
        if 'high_crypto_concentration' in risk_factors:
            recommendations.append('Consider reducing cryptocurrency exposure')
            
        if risk_level == 'low' and not risk_factors:
            recommendations.append('Portfolio risk profile is well-balanced')
            
        return recommendations
    
    def update_market_prices(self, prices: Dict[str, Dict[str, float]]):
        """Aktualisiert Market Prices (externe Updates)"""
        
        updated_currencies = []
        for currency, price_info in prices.items():
            if currency in self.market_prices:
                self.market_prices[currency].update(price_info)
                updated_currencies.append(currency)
        
        # Cache invalidieren
        self.portfolio_cache = None
        self.cache_timestamp = None
        
        self.logger.info(f"Market prices updated",
                       updated_currencies=updated_currencies)
    
    def update_account_balances(self, balances: Dict[str, Dict[str, str]]):
        """Aktualisiert Account Balances (externe Updates)"""
        
        updated_currencies = []
        for currency, balance_info in balances.items():
            if currency in self.account_balances:
                self.account_balances[currency].update(balance_info)
                updated_currencies.append(currency)
        
        # Cache invalidieren
        self.portfolio_cache = None
        self.cache_timestamp = None
        
        self.logger.info(f"Account balances updated",
                       updated_currencies=updated_currencies)
    
    def get_portfolio_allocation_by_type(self) -> Dict[str, Any]:
        """Gibt Portfolio Allocation nach Asset Type zurück"""
        
        if not self.portfolio_cache:
            return {}
        
        fiat_value = 0.0
        crypto_value = 0.0
        
        for currency, position in self.portfolio_cache.positions.items():
            if currency in ['EUR', 'USD', 'GBP']:
                fiat_value += position['value_eur']
            elif currency in ['BTC', 'ETH']:
                crypto_value += position['value_eur']
        
        total_value = fiat_value + crypto_value
        
        return {
            'fiat': {
                'value_eur': round(fiat_value, 2),
                'percentage': round((fiat_value / total_value) * 100, 1) if total_value > 0 else 0
            },
            'crypto': {
                'value_eur': round(crypto_value, 2),
                'percentage': round((crypto_value / total_value) * 100, 1) if total_value > 0 else 0
            },
            'total_value_eur': round(total_value, 2)
        }
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'portfolio_summary',
            'description': 'Generates comprehensive portfolio summary with performance and risk analysis',
            'responsibility': 'Portfolio summary generation logic only',
            'input_parameters': {
                'refresh_cache': 'Whether to refresh portfolio cache (default: false)',
                'include_performance': 'Whether to include performance analysis (default: true)',
                'include_risk_assessment': 'Whether to include risk assessment (default: true)',
                'currency_filter': 'Optional list of currencies to include',
                'min_value_eur': 'Minimum position value in EUR to include (default: 0.0)'
            },
            'output_format': {
                'total_value_eur': 'Total portfolio value in EUR',
                'positions': 'Detailed position information per currency',
                'currencies_count': 'Number of currency positions',
                'largest_position': 'Information about largest position',
                'diversification_score': 'Portfolio diversification score (0-1)',
                'performance_summary': 'Portfolio performance analysis',
                'risk_assessment': 'Portfolio risk analysis and recommendations',
                'last_updated': 'Portfolio data last update timestamp',
                'retrieval_timestamp': 'Summary generation timestamp'
            },
            'supported_currencies': list(self.account_balances.keys()),
            'risk_configuration': self.risk_config,
            'cache_duration_seconds': 120,
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_portfolio_statistics(self) -> Dict[str, Any]:
        """Portfolio Summary Module Statistiken"""
        total_generations = len(self.summary_generation_history)
        
        if total_generations == 0:
            return {
                'total_generations': 0,
                'cache_active': self.portfolio_cache is not None,
                'supported_currencies': len(self.account_balances)
            }
        
        # Average Portfolio Value
        total_values = [g['total_value_eur'] for g in self.summary_generation_history]
        avg_portfolio_value = round(sum(total_values) / len(total_values), 2) if total_values else 0
        
        # Average Diversification Score
        diversification_scores = [g['diversification_score'] for g in self.summary_generation_history]
        avg_diversification = round(sum(diversification_scores) / len(diversification_scores), 3) if diversification_scores else 0
        
        # Recent Activity
        recent_generations = [
            g for g in self.summary_generation_history
            if (datetime.now() - g['timestamp']).seconds < 3600  # Last hour
        ]
        
        return {
            'total_generations': total_generations,
            'recent_generations_last_hour': len(recent_generations),
            'average_portfolio_value_eur': avg_portfolio_value,
            'average_diversification_score': avg_diversification,
            'cache_active': bool(self.portfolio_cache),
            'cache_age_seconds': (datetime.now() - self.cache_timestamp).seconds if self.cache_timestamp else None,
            'supported_currencies': len(self.account_balances),
            'market_prices_count': len(self.market_prices),
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
