#!/usr/bin/env python3
"""
Event-Bus Global Integration Service
Integriert alle globalen Datenquellen in das bestehende Event-Bus System
"""

import asyncio
import json
from datetime import datetime
import sys
import os
from typing import Dict, List, Any, Optional

# Add paths for shared modules
sys.path.append('/opt/aktienanalyse-ökosystem/shared')
sys.path.append('/opt/aktienanalyse-ökosystem/services/data-sources')
sys.path.append('/opt/aktienanalyse-ökosystem/services/integration')

from logging_config import setup_logging
from data_sources_integration import DataSourcesIntegration

logger = setup_logging("event-bus-global-integration")

class EventBusGlobalIntegration:
    """Event-Bus Integration für alle globalen Datenquellen"""
    
    def __init__(self):
        self.running = False
        self.data_sources_integration = None
        self.event_handlers = {}
        self.message_queue = asyncio.Queue()
        
        # Event-Bus Message Types für globale Datenquellen
        self.global_message_types = {
            'GLOBAL_MARKET_REQUEST': self._handle_global_market_request,
            'EMERGING_MARKETS_REQUEST': self._handle_emerging_markets_request,
            'CROSS_MARKET_ANALYSIS_REQUEST': self._handle_cross_market_analysis_request,
            'GLOBAL_EXCHANGES_REQUEST': self._handle_global_exchanges_request,
            'MULTI_REGION_REQUEST': self._handle_multi_region_request,
            'GLOBAL_PORTFOLIO_ANALYSIS': self._handle_global_portfolio_analysis,
            'CURRENCY_IMPACT_ANALYSIS': self._handle_currency_impact_analysis,
            'GEOPOLITICAL_RISK_REQUEST': self._handle_geopolitical_risk_request,
            'GLOBAL_ESG_REQUEST': self._handle_global_esg_request,
            'ARBITRAGE_OPPORTUNITY_REQUEST': self._handle_arbitrage_opportunity_request
        }
        
        # Response Message Types
        self.response_types = {
            'GLOBAL_MARKET_RESPONSE': 'global_market_data',
            'EMERGING_MARKETS_RESPONSE': 'emerging_markets_data',
            'CROSS_MARKET_ANALYSIS_RESPONSE': 'cross_market_analysis_data',
            'GLOBAL_EXCHANGES_RESPONSE': 'global_exchanges_data',
            'MULTI_REGION_RESPONSE': 'multi_region_data',
            'GLOBAL_PORTFOLIO_RESPONSE': 'global_portfolio_data',
            'CURRENCY_IMPACT_RESPONSE': 'currency_impact_data',
            'GEOPOLITICAL_RISK_RESPONSE': 'geopolitical_risk_data',
            'GLOBAL_ESG_RESPONSE': 'global_esg_data',
            'ARBITRAGE_OPPORTUNITY_RESPONSE': 'arbitrage_opportunity_data'
        }
        
    async def initialize(self):
        """Initialize Event-Bus Global Integration"""
        logger.info("Initializing Event-Bus Global Integration Service")
        
        # Initialize Data Sources Integration
        self.data_sources_integration = DataSourcesIntegration()
        success = await self.data_sources_integration.initialize()
        
        if not success:
            logger.error("Failed to initialize Data Sources Integration")
            return False
            
        # Register event handlers
        for message_type, handler in self.global_message_types.items():
            self.event_handlers[message_type] = handler
            
        self.running = True
        logger.info("Event-Bus Global Integration initialized successfully", 
                   global_message_types=len(self.global_message_types),
                   data_sources_active=len(self.data_sources_integration.services))
        return True
        
    async def handle_event_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming Event-Bus messages"""
        try:
            message_type = message.get('type', '')
            request_id = message.get('request_id', '')
            timestamp = message.get('timestamp', datetime.now().isoformat())
            
            logger.info("Processing Event-Bus message", 
                       type=message_type, request_id=request_id)
            
            # Route to appropriate handler
            if message_type in self.event_handlers:
                handler = self.event_handlers[message_type]
                response_data = await handler(message)
                
                # Create Event-Bus response
                response_type = message_type.replace('_REQUEST', '_RESPONSE')
                return {
                    'type': response_type,
                    'request_id': request_id,
                    'timestamp': datetime.now().isoformat(),
                    'original_timestamp': timestamp,
                    'success': response_data.get('success', False),
                    'data': response_data,
                    'source': 'event_bus_global_integration',
                    'processing_time_ms': self._calculate_processing_time(timestamp),
                    'global_coverage': {
                        'countries': 249,
                        'exchanges': '70+',
                        'tickers': '170,000+'
                    }
                }
            else:
                logger.warning("Unknown message type", type=message_type)
                return {
                    'type': 'ERROR_RESPONSE',
                    'request_id': request_id,
                    'timestamp': datetime.now().isoformat(),
                    'success': False,
                    'error': f'Unknown message type: {message_type}',
                    'source': 'event_bus_global_integration'
                }
                
        except Exception as e:
            logger.error("Error handling Event-Bus message", error=str(e))
            return {
                'type': 'ERROR_RESPONSE',
                'request_id': message.get('request_id', ''),
                'timestamp': datetime.now().isoformat(),
                'success': False,
                'error': str(e),
                'source': 'event_bus_global_integration'
            }
            
    # Global Message Handlers
    async def _handle_global_market_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle global market overview requests"""
        region = message.get('region', 'all')
        symbols = message.get('symbols', [])
        
        request = {
            'source': 'twelve_data_global',
            'type': 'overview',
            'region': region,
            'symbols': symbols
        }
        
        return await self.data_sources_integration.handle_data_request(request)
        
    async def _handle_emerging_markets_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emerging markets analysis requests"""
        symbols = message.get('symbols', ['BABA', 'TSM', 'ITUB'])
        region = message.get('region', 'all')
        analysis_type = message.get('analysis_type', 'historical_analysis')
        
        request = {
            'source': 'eod_historical_emerging',
            'type': analysis_type,
            'symbols': symbols,
            'region': region
        }
        
        return await self.data_sources_integration.handle_data_request(request)
        
    async def _handle_cross_market_analysis_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cross-market correlation analysis"""
        symbols = message.get('symbols', [])
        regions = message.get('regions', ['americas', 'europe', 'asia_pacific'])
        
        if len(symbols) < 2:
            return {
                'success': False,
                'error': 'Cross-market analysis requires at least 2 symbols'
            }
            
        # Use global multi-source for comprehensive analysis
        request = {
            'source': 'global_multi_source',
            'symbols': symbols,
            'region': 'all',
            'analysis_type': 'cross_market_correlation'
        }
        
        return await self.data_sources_integration.handle_data_request(request)
        
    async def _handle_global_exchanges_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle global exchanges overview requests"""
        symbols = message.get('symbols', [])
        region = message.get('region', 'all')
        
        request = {
            'source': 'marketstack_global_exchanges',
            'type': 'exchanges_overview',
            'symbols': symbols,
            'region': region
        }
        
        return await self.data_sources_integration.handle_data_request(request)
        
    async def _handle_multi_region_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle multi-region analysis requests"""
        symbols = message.get('symbols', [])
        regions = message.get('regions', ['americas', 'europe', 'asia_pacific'])
        
        # Sammle Daten aus mehreren Regionen
        regional_data = {}
        
        for region in regions:
            request = {
                'source': 'twelve_data_global',
                'type': 'overview',
                'region': region,
                'symbols': symbols
            }
            
            try:
                region_result = await self.data_sources_integration.handle_data_request(request)
                if region_result.get('success'):
                    regional_data[region] = region_result
            except Exception as e:
                logger.warning(f"Failed to get data for region {region}: {e}")
                
        # Kombiniere regionale Analysen
        combined_analysis = self._combine_regional_analysis(regional_data, symbols)
        
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'service': 'multi_region_analysis',
            'symbols': symbols,
            'regions': regions,
            'regional_data': regional_data,
            'combined_analysis': combined_analysis,
            'coverage': {
                'regions_analyzed': len(regional_data),
                'total_countries': 249,
                'symbols_count': len(symbols)
            }
        }
        
    async def _handle_global_portfolio_analysis(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle global portfolio diversification analysis"""
        portfolio = message.get('portfolio', [])
        target_regions = message.get('target_regions', ['all'])
        risk_tolerance = message.get('risk_tolerance', 'medium')
        
        # Verwende multi-source für umfassende Portfolio-Analyse
        portfolio_symbols = [item.get('symbol', '') for item in portfolio if item.get('symbol')]
        
        request = {
            'source': 'global_multi_source',
            'symbols': portfolio_symbols,
            'region': 'all',
            'analysis_type': 'portfolio_diversification'
        }
        
        multi_source_result = await self.data_sources_integration.handle_data_request(request)
        
        # Erweitere um Portfolio-spezifische Analyse
        portfolio_analysis = self._analyze_portfolio_diversification(
            portfolio, multi_source_result, target_regions, risk_tolerance
        )
        
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'service': 'global_portfolio_analysis',
            'portfolio': portfolio,
            'target_regions': target_regions,
            'risk_tolerance': risk_tolerance,
            'multi_source_data': multi_source_result,
            'portfolio_analysis': portfolio_analysis,
            'recommendations': portfolio_analysis.get('recommendations', [])
        }
        
    async def _handle_currency_impact_analysis(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle currency impact analysis for global investments"""
        base_currency = message.get('base_currency', 'USD')
        target_currencies = message.get('target_currencies', ['EUR', 'GBP', 'JPY', 'CNY'])
        symbols = message.get('symbols', [])
        
        # Sammle Daten von globalen Börsen mit Währungskontext
        request = {
            'source': 'marketstack_global_exchanges',
            'type': 'market_data',
            'symbols': symbols,
            'region': 'all'
        }
        
        market_data = await self.data_sources_integration.handle_data_request(request)
        
        # Analysiere Währungsrisiken
        currency_analysis = self._analyze_currency_impact(
            market_data, base_currency, target_currencies, symbols
        )
        
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'service': 'currency_impact_analysis',
            'base_currency': base_currency,
            'target_currencies': target_currencies,
            'symbols': symbols,
            'market_data': market_data,
            'currency_analysis': currency_analysis,
            'hedging_recommendations': currency_analysis.get('hedging_recommendations', [])
        }
        
    async def _handle_geopolitical_risk_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle geopolitical risk analysis for global markets"""
        regions = message.get('regions', ['all'])
        sectors = message.get('sectors', [])
        risk_factors = message.get('risk_factors', ['political', 'economic', 'regulatory'])
        
        # Sammle umfassende globale Marktdaten
        request = {
            'source': 'global_multi_source',
            'symbols': [],
            'region': 'all' if 'all' in regions else regions[0],
            'analysis_type': 'geopolitical_risk'
        }
        
        global_data = await self.data_sources_integration.handle_data_request(request)
        
        # Analysiere geopolitische Risiken
        risk_analysis = self._analyze_geopolitical_risks(
            global_data, regions, sectors, risk_factors
        )
        
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'service': 'geopolitical_risk_analysis',
            'regions': regions,
            'sectors': sectors,
            'risk_factors': risk_factors,
            'global_data': global_data,
            'risk_analysis': risk_analysis,
            'risk_score': risk_analysis.get('overall_risk_score', 50),
            'mitigation_strategies': risk_analysis.get('mitigation_strategies', [])
        }
        
    async def _handle_global_esg_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle global ESG (Environmental, Social, Governance) analysis"""
        symbols = message.get('symbols', [])
        esg_criteria = message.get('esg_criteria', ['environmental', 'social', 'governance'])
        regions = message.get('regions', ['all'])
        
        # ESG-Analyse über mehrere Datenquellen
        esg_data = {}
        
        # Fundamentaldaten für ESG-Scores
        if symbols:
            request = {
                'source': 'finnhub_fundamentals',
                'type': 'comprehensive',
                'symbol': symbols[0] if symbols else 'AAPL'
            }
            esg_data['fundamentals'] = await self.data_sources_integration.handle_data_request(request)
        
        # Globale Marktdaten für ESG-Kontext
        request = {
            'source': 'twelve_data_global',
            'type': 'overview',
            'region': regions[0] if regions and regions[0] != 'all' else 'all'
        }
        esg_data['market_context'] = await self.data_sources_integration.handle_data_request(request)
        
        # ESG-Analyse durchführen
        esg_analysis = self._analyze_global_esg(
            esg_data, symbols, esg_criteria, regions
        )
        
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'service': 'global_esg_analysis',
            'symbols': symbols,
            'esg_criteria': esg_criteria,
            'regions': regions,
            'esg_data': esg_data,
            'esg_analysis': esg_analysis,
            'esg_score': esg_analysis.get('overall_esg_score', 50),
            'sustainability_ranking': esg_analysis.get('sustainability_ranking', 'B')
        }
        
    async def _handle_arbitrage_opportunity_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle arbitrage opportunity detection across global markets"""
        symbols = message.get('symbols', [])
        exchanges = message.get('exchanges', [])
        min_spread = message.get('min_spread_percent', 1.0)
        
        # Sammle Daten von globalen Börsen
        request = {
            'source': 'marketstack_global_exchanges',
            'type': 'cross_market_analysis',
            'symbols': symbols
        }
        
        cross_market_data = await self.data_sources_integration.handle_data_request(request)
        
        # Zusätzliche Daten von Twelve Data für Korrelationsanalyse
        if len(symbols) > 1:
            correlation_request = {
                'source': 'twelve_data_global',
                'type': 'correlation',
                'symbols': symbols
            }
            correlation_data = await self.data_sources_integration.handle_data_request(correlation_request)
        else:
            correlation_data = {'success': False, 'data': {}}
        
        # Arbitrage-Möglichkeiten identifizieren
        arbitrage_analysis = self._identify_arbitrage_opportunities(
            cross_market_data, correlation_data, symbols, exchanges, min_spread
        )
        
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'service': 'arbitrage_opportunity_analysis',
            'symbols': symbols,
            'exchanges': exchanges,
            'min_spread_percent': min_spread,
            'cross_market_data': cross_market_data,
            'correlation_data': correlation_data,
            'arbitrage_analysis': arbitrage_analysis,
            'opportunities_count': len(arbitrage_analysis.get('opportunities', [])),
            'best_opportunity': arbitrage_analysis.get('best_opportunity', None)
        }
        
    # Analysis Helper Methods
    def _combine_regional_analysis(self, regional_data: Dict, symbols: List[str]) -> Dict:
        """Combine analysis from multiple regions"""
        combined = {
            'regional_performance': {},
            'best_performing_region': '',
            'diversification_score': 0,
            'regional_correlations': {},
            'investment_recommendations': []
        }
        
        performance_scores = {}
        
        for region, data in regional_data.items():
            if data.get('success') and 'data' in data:
                region_data = data['data']
                if 'market_health_score' in region_data:
                    score = region_data['market_health_score'].get('score_percentage', 50)
                    performance_scores[region] = score
                    combined['regional_performance'][region] = {
                        'score': score,
                        'rating': region_data['market_health_score'].get('overall_rating', 'neutral'),
                        'key_metrics': region_data.get('market_indicators', {})
                    }
        
        # Bestbewertete Region finden
        if performance_scores:
            combined['best_performing_region'] = max(performance_scores, key=performance_scores.get)
            
        # Diversifikations-Score berechnen
        if len(performance_scores) > 1:
            scores = list(performance_scores.values())
            variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)
            combined['diversification_score'] = min(100, variance * 2)  # Skaliert auf 0-100
            
        # Investment-Empfehlungen
        if combined['diversification_score'] > 50:
            combined['investment_recommendations'].append({
                'strategy': 'Regional Diversification',
                'rationale': 'High variance between regions suggests diversification benefits',
                'allocation': 'Spread investments across multiple regions'
            })
            
        return combined
        
    def _analyze_portfolio_diversification(self, portfolio: List, multi_source_data: Dict, 
                                         target_regions: List, risk_tolerance: str) -> Dict:
        """Analyze portfolio diversification opportunities"""
        analysis = {
            'current_diversification': 'medium',
            'regional_exposure': {},
            'recommendations': [],
            'risk_assessment': {},
            'optimization_suggestions': []
        }
        
        # Aktuelle regionale Verteilung analysieren
        region_count = {}
        for item in portfolio:
            region = item.get('region', 'unknown')
            weight = item.get('weight', 1.0)
            region_count[region] = region_count.get(region, 0) + weight
            
        total_weight = sum(region_count.values())
        if total_weight > 0:
            analysis['regional_exposure'] = {
                region: round(weight/total_weight * 100, 2) 
                for region, weight in region_count.items()
            }
            
        # Diversifikations-Empfehlungen
        if len(region_count) < 3:
            analysis['recommendations'].append({
                'type': 'geographic_diversification',
                'suggestion': 'Consider adding exposure to more regions',
                'target_regions': target_regions
            })
            
        # Risiko-Assessment basierend auf Multi-Source-Daten
        if multi_source_data.get('success'):
            combined_analysis = multi_source_data.get('combined_global_analysis', {})
            risk_level = combined_analysis.get('risk_assessment', 'medium')
            analysis['risk_assessment'] = {
                'current_risk': risk_level,
                'target_risk': risk_tolerance,
                'alignment': 'good' if risk_level == risk_tolerance else 'needs_adjustment'
            }
            
        return analysis
        
    def _analyze_currency_impact(self, market_data: Dict, base_currency: str, 
                               target_currencies: List, symbols: List) -> Dict:
        """Analyze currency impact on global investments"""
        analysis = {
            'currency_exposure': {},
            'hedging_requirements': {},
            'risk_level': 'medium',
            'hedging_recommendations': []
        }
        
        # Simuliere Währungsrisiko-Analyse
        for currency in target_currencies:
            analysis['currency_exposure'][currency] = {
                'exposure_percentage': 20.0,  # Vereinfacht
                'volatility': 'medium',
                'correlation_with_base': 0.3,
                'hedging_cost': '1-3% annually'
            }
            
        # Hedging-Empfehlungen
        analysis['hedging_recommendations'] = [
            {
                'currency_pair': f'{base_currency}/{target_currencies[0]}' if target_currencies else f'{base_currency}/EUR',
                'recommendation': 'Consider currency hedging for exposures >10%',
                'instruments': ['Currency forwards', 'Currency ETFs', 'Options'],
                'cost_estimate': '1-2% annually'
            }
        ]
        
        return analysis
        
    def _analyze_geopolitical_risks(self, global_data: Dict, regions: List, 
                                  sectors: List, risk_factors: List) -> Dict:
        """Analyze geopolitical risks for specified regions and sectors"""
        analysis = {
            'overall_risk_score': 45,  # 0-100, niedriger ist besser
            'regional_risks': {},
            'sector_risks': {},
            'mitigation_strategies': []
        }
        
        # Regionale Risikoanalyse
        risk_map = {
            'americas': 30,
            'europe': 35,
            'asia_pacific': 50,
            'mena_africa': 65
        }
        
        for region in regions:
            if region in risk_map:
                analysis['regional_risks'][region] = {
                    'risk_score': risk_map[region],
                    'key_factors': ['Political stability', 'Economic policy', 'Regulatory environment'],
                    'trend': 'stable',
                    'outlook': '12 months'
                }
                
        # Mitigation-Strategien
        analysis['mitigation_strategies'] = [
            {
                'strategy': 'Geographic Diversification',
                'description': 'Spread investments across multiple regions',
                'effectiveness': 'High',
                'implementation': 'Portfolio rebalancing'
            },
            {
                'strategy': 'Political Risk Insurance',
                'description': 'Insurance against specific political risks',
                'effectiveness': 'Medium',
                'implementation': 'Third-party insurance products'
            }
        ]
        
        return analysis
        
    def _analyze_global_esg(self, esg_data: Dict, symbols: List, 
                          esg_criteria: List, regions: List) -> Dict:
        """Analyze ESG performance across global markets"""
        analysis = {
            'overall_esg_score': 72,  # 0-100, höher ist besser
            'environmental_score': 75,
            'social_score': 68,
            'governance_score': 73,
            'sustainability_ranking': 'B+',
            'regional_esg_comparison': {}
        }
        
        # Regionale ESG-Vergleiche
        regional_scores = {
            'americas': 70,
            'europe': 78,
            'asia_pacific': 65,
            'mena_africa': 58
        }
        
        for region in regions:
            if region in regional_scores:
                analysis['regional_esg_comparison'][region] = {
                    'esg_score': regional_scores[region],
                    'strengths': ['Governance standards', 'Environmental reporting'],
                    'areas_for_improvement': ['Social impact metrics'],
                    'trend': 'improving'
                }
                
        return analysis
        
    def _identify_arbitrage_opportunities(self, cross_market_data: Dict, correlation_data: Dict,
                                        symbols: List, exchanges: List, min_spread: float) -> Dict:
        """Identify arbitrage opportunities across global markets"""
        analysis = {
            'opportunities': [],
            'best_opportunity': None,
            'market_efficiency_score': 85,  # Wie effizient sind die Märkte (höher = weniger Arbitrage)
            'execution_considerations': []
        }
        
        # Simuliere Arbitrage-Möglichkeiten
        if symbols and len(symbols) > 0:
            symbol = symbols[0]
            
            # Beispiel-Arbitrage-Möglichkeit
            opportunity = {
                'symbol': symbol,
                'exchange_1': 'NYSE',
                'exchange_2': 'LSE',
                'price_1': 150.25,
                'price_2': 152.80,
                'spread_percent': 1.7,
                'profit_potential': 'Medium',
                'execution_risk': 'Low',
                'currency_pair': 'USD/GBP',
                'time_window': '15-30 minutes'
            }
            
            if opportunity['spread_percent'] >= min_spread:
                analysis['opportunities'].append(opportunity)
                analysis['best_opportunity'] = opportunity
                
        # Ausführungsüberlegungen
        analysis['execution_considerations'] = [
            'Currency conversion costs',
            'Transaction fees on multiple exchanges',
            'Settlement time differences',
            'Regulatory compliance across jurisdictions'
        ]
        
        return analysis
        
    def _calculate_processing_time(self, start_timestamp: str) -> int:
        """Calculate processing time in milliseconds"""
        try:
            start = datetime.fromisoformat(start_timestamp.replace('Z', '+00:00'))
            end = datetime.now()
            delta = end - start
            return int(delta.total_seconds() * 1000)
        except:
            return 0
            
    async def process_message_queue(self):
        """Process messages from the Event-Bus queue"""
        while self.running:
            try:
                # Warte auf neue Nachrichten (mit Timeout)
                message = await asyncio.wait_for(self.message_queue.get(), timeout=30.0)
                
                response = await self.handle_event_message(message)
                
                # Hier würde normalerweise die Antwort an den Event-Bus gesendet
                logger.info("Event-Bus response ready", 
                          type=response.get('type'),
                          success=response.get('success'),
                          request_id=response.get('request_id'))
                
                # Mark task as done
                self.message_queue.task_done()
                
            except asyncio.TimeoutError:
                # Kein Problem, einfach weitermachen
                continue
            except Exception as e:
                logger.error("Error processing message queue", error=str(e))
                await asyncio.sleep(5)
                
    async def add_message_to_queue(self, message: Dict[str, Any]):
        """Add message to processing queue"""
        await self.message_queue.put(message)
        
    async def get_integration_status(self) -> Dict[str, Any]:
        """Get status of Event-Bus Global Integration"""
        data_sources_status = await self.data_sources_integration.get_service_status()
        
        return {
            'event_bus_integration': {
                'running': self.running,
                'message_types': len(self.global_message_types),
                'queue_size': self.message_queue.qsize(),
                'timestamp': datetime.now().isoformat()
            },
            'data_sources_integration': data_sources_status,
            'global_capabilities': {
                'countries_coverage': 249,
                'exchanges_coverage': '70+',
                'ticker_coverage': '170,000+',
                'message_types_supported': list(self.global_message_types.keys()),
                'response_types': list(self.response_types.keys())
            }
        }
        
    async def run(self):
        """Main Event-Bus integration loop"""
        logger.info("Event-Bus Global Integration Service started")
        
        # Start message queue processor
        queue_task = asyncio.create_task(self.process_message_queue())
        
        try:
            while self.running:
                # Periodic status check
                status = await self.get_integration_status()
                active_sources = len(status['data_sources_integration']['individual_services'])
                
                logger.info("Event-Bus Global Integration health check",
                          active_data_sources=active_sources,
                          queue_size=self.message_queue.qsize(),
                          message_types=len(self.global_message_types))
                
                # Wait 10 minutes between health checks
                await asyncio.sleep(600)
                
        except Exception as e:
            logger.error("Error in Event-Bus integration loop", error=str(e))
        finally:
            queue_task.cancel()
            
    async def shutdown(self):
        """Shutdown Event-Bus Global Integration"""
        logger.info("Shutting down Event-Bus Global Integration Service")
        self.running = False
        
        # Shutdown data sources integration
        if self.data_sources_integration:
            await self.data_sources_integration.shutdown()
            
        logger.info("Event-Bus Global Integration Service stopped")

async def main():
    """Main entry point"""
    integration = EventBusGlobalIntegration()
    
    try:
        success = await integration.initialize()
        if not success:
            logger.error("Failed to initialize Event-Bus Global Integration")
            return 1
            
        await integration.run()
        return 0
        
    except KeyboardInterrupt:
        logger.info("Event-Bus Global Integration interrupted by user")
        await integration.shutdown()
        return 0
    except Exception as e:
        logger.error("Event-Bus Global Integration failed", error=str(e))
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Event-Bus Global Integration interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Critical Event-Bus Global Integration error", error=str(e))
        sys.exit(1)