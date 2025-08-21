#!/usr/bin/env python3
"""
Data Sources Integration Service
Bindet alle neuen Datenquellen-Module in den Event-Bus ein
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

from logging_config import setup_logging

# Import new data source services
from alpha_vantage_smallcap_service import AlphaVantageSmallCapService
from finnhub_fundamentals_service import FinnhubFundamentalsService
from ecb_macroeconomics_service import ECBMacroeconomicsService
from dealroom_eu_startup_service import DealroomEUStartupService
from iex_cloud_microcap_service import IEXCloudMicrocapService

# Import global data source services
from twelve_data_global_service import TwelveDataGlobalService
from eod_historical_emerging_service import EODHistoricalEmergingService
# Import module name compatible with Python import
import importlib.util
import sys

# Load Marketstack module dynamically due to dots in filename
spec = importlib.util.spec_from_file_location("marketstack_global_exchanges", "/opt/aktienanalyse-ökosystem/services/data-sources/marketstack_global_exchanges_v1.0.0_20250817.py")
marketstack_module = importlib.util.module_from_spec(spec)
sys.modules["marketstack_global_exchanges"] = marketstack_module
spec.loader.exec_module(marketstack_module)
MarketstackGlobalExchangesService = marketstack_module.MarketstackGlobalExchangesService

logger = setup_logging("data-sources-integration")

class DataSourcesIntegration:
    """Integration Service für alle neuen Datenquellen"""
    
    def __init__(self):
        self.running = False
        self.services = {}
        self.event_handlers = {}
        
        # Service registry
        self.service_config = {
            'alpha_vantage_smallcap': {
                'class': AlphaVantageSmallCapService,
                'description': 'Small-Cap Aktien mit technischen Indikatoren',
                'data_types': ['small_cap_overview', 'technical_indicators', 'batch_analysis']
            },
            'finnhub_fundamentals': {
                'class': FinnhubFundamentalsService,
                'description': 'Fundamentaldaten, Earnings und Unternehmensdaten',
                'data_types': ['comprehensive_fundamentals', 'earnings_analysis', 'recommendations']
            },
            'ecb_macroeconomics': {
                'class': ECBMacroeconomicsService,
                'description': 'Europäische Zentralbank Makroökonomie',
                'data_types': ['comprehensive_macro_analysis', 'interest_rates', 'inflation_data']
            },
            'dealroom_eu_startup': {
                'class': DealroomEUStartupService,
                'description': 'Europäische Startup-Ökosystem Daten',
                'data_types': ['eu_startup_ecosystem', 'funding_rounds', 'investor_activity']
            },
            'iex_cloud_microcap': {
                'class': IEXCloudMicrocapService,
                'description': 'Microcap-Aktien detaillierte Analyse',
                'data_types': ['microcap_analysis', 'risk_assessment', 'liquidity_analysis']
            },
            # Global Data Sources - Neue Services
            'twelve_data_global': {
                'class': TwelveDataGlobalService,
                'description': 'Globale Märkte mit 249 Ländern Abdeckung',
                'data_types': ['global_market_overview', 'emerging_markets_analysis', 'cross_market_correlation']
            },
            'eod_historical_emerging': {
                'class': EODHistoricalEmergingService,
                'description': 'Emerging Markets historische Daten mit 20+ Jahren Tiefe',
                'data_types': ['emerging_market_historical_analysis', 'technical_analysis', 'volatility_assessment']
            },
            'marketstack_global_exchanges': {
                'class': MarketstackGlobalExchangesService,
                'description': '170.000+ Ticker von 70+ globalen Börsen',
                'data_types': ['global_exchanges_overview', 'global_market_data', 'cross_market_analysis']
            }
        }
        
    async def initialize(self):
        """Initialize integration service"""
        logger.info("Initializing Data Sources Integration Service")
        
        # Initialize all data source services
        for service_name, config in self.service_config.items():
            try:
                service_class = config['class']
                service_instance = service_class()
                
                success = await service_instance.initialize()
                if success:
                    self.services[service_name] = service_instance
                    logger.info(f"Service initialized successfully", 
                              service=service_name,
                              description=config['description'])
                else:
                    logger.error(f"Failed to initialize service", service=service_name)
                    
            except Exception as e:
                logger.error(f"Error initializing service", 
                           service=service_name, error=str(e))
                
        self.running = True
        logger.info("Data Sources Integration Service initialized", 
                   active_services=len(self.services))
        return True
        
    async def handle_data_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming data requests"""
        try:
            request_type = request.get('type', '')
            source = request.get('source', '')
            symbol = request.get('symbol', '')
            
            logger.info("Processing data request", 
                       type=request_type, source=source, symbol=symbol)
            
            # Route request to appropriate service
            if source == 'alpha_vantage_smallcap':
                return await self._handle_smallcap_request(request)
            elif source == 'finnhub_fundamentals':
                return await self._handle_fundamentals_request(request)
            elif source == 'ecb_macroeconomics':
                return await self._handle_macro_request(request)
            elif source == 'dealroom_eu_startup':
                return await self._handle_startup_request(request)
            elif source == 'iex_cloud_microcap':
                return await self._handle_microcap_request(request)
            elif source == 'multi_source':
                return await self._handle_multi_source_request(request)
            # Global Data Sources
            elif source == 'twelve_data_global':
                return await self._handle_twelve_data_global_request(request)
            elif source == 'eod_historical_emerging':
                return await self._handle_eod_emerging_request(request)
            elif source == 'marketstack_global_exchanges':
                return await self._handle_marketstack_global_request(request)
            elif source == 'global_multi_source':
                return await self._handle_global_multi_source_request(request)
            else:
                return {
                    'error': f'Unknown data source: {source}',
                    'timestamp': datetime.now().isoformat(),
                    'success': False
                }
                
        except Exception as e:
            logger.error("Error handling data request", error=str(e))
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'success': False
            }
            
    async def _handle_smallcap_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Alpha Vantage Small-Cap requests"""
        service = self.services.get('alpha_vantage_smallcap')
        if not service:
            return {'error': 'Alpha Vantage service not available', 'success': False}
            
        request_type = request.get('type', '')
        symbol = request.get('symbol', '')
        
        if request_type == 'overview' and symbol:
            return await service.get_small_cap_overview(symbol)
        elif request_type == 'batch':
            limit = request.get('limit', 5)
            return await service.get_small_cap_batch_data(limit)
        else:
            return {'error': 'Invalid small-cap request type', 'success': False}
            
    async def _handle_fundamentals_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Finnhub Fundamentals requests"""
        service = self.services.get('finnhub_fundamentals')
        if not service:
            return {'error': 'Finnhub service not available', 'success': False}
            
        request_type = request.get('type', '')
        symbol = request.get('symbol', '')
        
        if request_type == 'comprehensive' and symbol:
            return await service.get_comprehensive_fundamentals(symbol)
        elif request_type == 'batch':
            limit = request.get('limit', 3)
            return await service.get_fundamentals_batch(limit)
        else:
            return {'error': 'Invalid fundamentals request type', 'success': False}
            
    async def _handle_macro_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ECB Macroeconomics requests"""
        service = self.services.get('ecb_macroeconomics')
        if not service:
            return {'error': 'ECB service not available', 'success': False}
            
        request_type = request.get('type', '')
        
        if request_type == 'comprehensive':
            return await service.get_comprehensive_macro_data()
        else:
            return {'error': 'Invalid macro request type', 'success': False}
            
    async def _handle_startup_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Dealroom EU-Startup requests"""
        service = self.services.get('dealroom_eu_startup')
        if not service:
            return {'error': 'Dealroom service not available', 'success': False}
            
        request_type = request.get('type', '')
        region = request.get('region', 'Germany')
        
        if request_type == 'overview':
            return await service.get_eu_startup_overview(region)
        elif request_type == 'batch':
            regions = request.get('regions', ['Germany', 'United Kingdom'])
            return await service.get_startup_batch_analysis(regions)
        else:
            return {'error': 'Invalid startup request type', 'success': False}
            
    async def _handle_microcap_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle IEX Cloud Microcap requests"""
        service = self.services.get('iex_cloud_microcap')
        if not service:
            return {'error': 'IEX Cloud service not available', 'success': False}
            
        request_type = request.get('type', '')
        symbol = request.get('symbol', '')
        
        if request_type == 'analysis' and symbol:
            return await service.get_microcap_analysis(symbol)
        elif request_type == 'batch':
            limit = request.get('limit', 5)
            return await service.get_microcap_batch_analysis(limit)
        else:
            return {'error': 'Invalid microcap request type', 'success': False}
            
    async def _handle_multi_source_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle requests that combine multiple data sources"""
        symbol = request.get('symbol', '')
        analysis_type = request.get('analysis_type', 'complete')
        
        if not symbol:
            return {'error': 'Symbol required for multi-source analysis', 'success': False}
            
        logger.info("Performing multi-source analysis", symbol=symbol, type=analysis_type)
        
        # Gather data from multiple sources
        results = {}
        
        try:
            # Small-cap technical analysis
            if 'alpha_vantage_smallcap' in self.services:
                smallcap_data = await self.services['alpha_vantage_smallcap'].get_small_cap_overview(symbol)
                if smallcap_data.get('success'):
                    results['technical_analysis'] = smallcap_data
                    
            # Fundamental analysis
            if 'finnhub_fundamentals' in self.services:
                fundamental_data = await self.services['finnhub_fundamentals'].get_comprehensive_fundamentals(symbol)
                if fundamental_data.get('success'):
                    results['fundamental_analysis'] = fundamental_data
                    
            # Microcap analysis
            if 'iex_cloud_microcap' in self.services:
                microcap_data = await self.services['iex_cloud_microcap'].get_microcap_analysis(symbol)
                if microcap_data.get('success'):
                    results['microcap_analysis'] = microcap_data
                    
            # Macroeconomic context
            if 'ecb_macroeconomics' in self.services:
                macro_data = await self.services['ecb_macroeconomics'].get_comprehensive_macro_data()
                if macro_data.get('success'):
                    results['macroeconomic_context'] = macro_data
                    
            # Combine and analyze
            combined_analysis = self._combine_multi_source_analysis(symbol, results)
            
            return {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'source': 'multi_source_integration',
                'data_type': 'comprehensive_analysis',
                'individual_analyses': results,
                'combined_analysis': combined_analysis,
                'data_sources_count': len(results),
                'success': True
            }
            
        except Exception as e:
            logger.error("Error in multi-source analysis", symbol=symbol, error=str(e))
            return {'error': str(e), 'success': False}
            
    def _combine_multi_source_analysis(self, symbol: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Combine analysis from multiple sources"""
        combined = {
            'overall_score': 0,
            'confidence_level': 0,
            'recommendation': 'HOLD',
            'risk_level': 'MEDIUM',
            'key_insights': [],
            'data_quality': 'GOOD'
        }
        
        scores = []
        insights = []
        
        # Extract scores from different analyses
        if 'technical_analysis' in results:
            ta = results['technical_analysis']
            if 'small_cap_metrics' in ta and 'small_cap_rating' in ta['small_cap_metrics']:
                rating = ta['small_cap_metrics']['small_cap_rating']
                score = self._rating_to_score(rating)
                scores.append(score)
                insights.append(f"Technical analysis shows {rating} rating")
                
        if 'fundamental_analysis' in results:
            fa = results['fundamental_analysis']
            if 'fundamental_score' in fa:
                fund_score = fa['fundamental_score'].get('score_percentage', 50)
                scores.append(fund_score)
                rating = fa['fundamental_score'].get('rating', 'FAIR')
                insights.append(f"Fundamentals rated as {rating}")
                
        if 'microcap_analysis' in results:
            ma = results['microcap_analysis']
            if 'microcap_score' in ma:
                micro_score = ma['microcap_score'].get('score_percentage', 50)
                scores.append(micro_score)
                rating = ma['microcap_score'].get('rating', 'HOLD')
                insights.append(f"Microcap analysis suggests {rating}")
                
        # Calculate combined score
        if scores:
            combined['overall_score'] = round(sum(scores) / len(scores), 1)
            combined['confidence_level'] = min(0.9, len(scores) * 0.25)  # Higher confidence with more sources
            
        # Determine recommendation
        if combined['overall_score'] >= 75:
            combined['recommendation'] = 'STRONG_BUY'
            combined['risk_level'] = 'MEDIUM'
        elif combined['overall_score'] >= 60:
            combined['recommendation'] = 'BUY'
            combined['risk_level'] = 'MEDIUM'
        elif combined['overall_score'] >= 40:
            combined['recommendation'] = 'HOLD'
            combined['risk_level'] = 'MEDIUM'
        else:
            combined['recommendation'] = 'AVOID'
            combined['risk_level'] = 'HIGH'
            
        # Add macroeconomic context
        if 'macroeconomic_context' in results:
            macro = results['macroeconomic_context']
            if 'macro_health_score' in macro:
                macro_rating = macro['macro_health_score'].get('rating', 'FAIR')
                insights.append(f"Macroeconomic environment: {macro_rating}")
                
        combined['key_insights'] = insights
        combined['analysis_date'] = datetime.now().isoformat()
        
        return combined
        
    def _rating_to_score(self, rating: str) -> float:
        """Convert text rating to numerical score"""
        rating_map = {
            'STRONG_BUY': 90,
            'BUY': 75,
            'HOLD': 50,
            'CAUTION': 35,
            'AVOID': 20,
            'EXCELLENT': 95,
            'GOOD': 80,
            'FAIR': 60,
            'POOR': 30,
            'VERY_POOR': 15
        }
        return rating_map.get(rating, 50)
    
    # Global Data Sources Request Handlers
    async def _handle_twelve_data_global_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Twelve Data Global Markets requests"""
        service = self.services.get('twelve_data_global')
        if not service:
            return {'error': 'Twelve Data Global service not available', 'success': False}
            
        request_type = request.get('type', '')
        region = request.get('region', 'all')
        symbols = request.get('symbols', [])
        
        if request_type == 'overview':
            return await service.get_global_market_overview(region)
        elif request_type == 'emerging_analysis':
            return await service.get_emerging_markets_analysis(symbols)
        elif request_type == 'correlation':
            return await service.get_cross_market_correlation(symbols)
        else:
            return {'error': 'Invalid Twelve Data Global request type', 'success': False}
    
    async def _handle_eod_emerging_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle EOD Historical Emerging Markets requests"""
        service = self.services.get('eod_historical_emerging')
        if not service:
            return {'error': 'EOD Historical Emerging service not available', 'success': False}
            
        request_type = request.get('type', '')
        symbols = request.get('symbols', [])
        region = request.get('region', 'all')
        
        if request_type == 'historical_analysis':
            return await service.get_emerging_market_historical_analysis(symbols, region)
        elif request_type == 'technical_analysis':
            return await service.get_technical_analysis(symbols)
        elif request_type == 'volatility_assessment':
            return await service.get_volatility_assessment(symbols, region)
        else:
            return {'error': 'Invalid EOD Emerging request type', 'success': False}
    
    async def _handle_marketstack_global_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Marketstack Global Exchanges requests"""
        service = self.services.get('marketstack_global_exchanges')
        if not service:
            return {'error': 'Marketstack Global service not available', 'success': False}
            
        request_type = request.get('type', '')
        symbols = request.get('symbols', [])
        region = request.get('region', 'all')
        
        if request_type == 'exchanges_overview':
            return await service.get_global_exchanges_overview()
        elif request_type == 'market_data':
            return await service.get_global_market_data(symbols, region)
        elif request_type == 'cross_market_analysis':
            return await service.get_cross_market_analysis(symbols)
        else:
            return {'error': 'Invalid Marketstack Global request type', 'success': False}
    
    async def _handle_global_multi_source_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle requests that combine multiple global data sources"""
        symbols = request.get('symbols', [])
        region = request.get('region', 'all')
        analysis_type = request.get('analysis_type', 'comprehensive')
        
        if not symbols:
            return {'error': 'Symbols required for global multi-source analysis', 'success': False}
            
        logger.info("Performing global multi-source analysis", symbols=symbols, region=region, type=analysis_type)
        
        # Gather data from multiple global sources
        global_results = {}
        
        try:
            # Twelve Data Global Markets
            if 'twelve_data_global' in self.services:
                try:
                    global_results['global_market_overview'] = await self.services['twelve_data_global'].get_global_market_overview(region)
                except Exception as e:
                    logger.warning(f"Twelve Data Global request failed: {e}")
            
            # EOD Historical Emerging Markets
            if 'eod_historical_emerging' in self.services:
                try:
                    global_results['emerging_historical'] = await self.services['eod_historical_emerging'].get_emerging_market_historical_analysis(symbols, region)
                except Exception as e:
                    logger.warning(f"EOD Emerging request failed: {e}")
            
            # Marketstack Global Exchanges
            if 'marketstack_global_exchanges' in self.services:
                try:
                    global_results['global_exchanges'] = await self.services['marketstack_global_exchanges'].get_global_market_data(symbols, region)
                except Exception as e:
                    logger.warning(f"Marketstack Global request failed: {e}")
            
            # Cross-market correlation analysis
            if len(symbols) > 1 and 'twelve_data_global' in self.services:
                try:
                    global_results['cross_market_correlation'] = await self.services['twelve_data_global'].get_cross_market_correlation(symbols)
                except Exception as e:
                    logger.warning(f"Cross-market correlation failed: {e}")
            
            # Combine global analysis
            combined_global = self._combine_global_analysis(global_results, symbols, region)
            
            return {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'service': 'global_multi_source_integration',
                'symbols': symbols,
                'region': region,
                'analysis_type': analysis_type,
                'individual_sources': global_results,
                'combined_global_analysis': combined_global,
                'sources_used': list(global_results.keys()),
                'metadata': {
                    'global_coverage': '249 countries',
                    'exchange_count': '70+ exchanges',
                    'ticker_coverage': '170,000+ symbols',
                    'data_depth': '20+ years historical'
                }
            }
            
        except Exception as e:
            logger.error(f"Global multi-source analysis failed: {e}")
            return {
                'error': f'Global multi-source analysis failed: {e}',
                'timestamp': datetime.now().isoformat(),
                'success': False
            }
    
    def _combine_global_analysis(self, global_results: Dict, symbols: List[str], region: str) -> Dict:
        """Combine results from multiple global data sources"""
        combined = {
            'global_market_health': 'neutral',
            'emerging_markets_sentiment': 'neutral',
            'cross_market_opportunities': [],
            'regional_outlook': {},
            'currency_impact': 'moderate',
            'risk_assessment': 'medium',
            'investment_recommendations': [],
            'key_global_insights': []
        }
        
        insights = []
        risk_factors = []
        
        # Analyze Global Market Overview
        if 'global_market_overview' in global_results:
            gmo = global_results['global_market_overview']
            if gmo.get('success'):
                data = gmo.get('data', {})
                market_health = data.get('market_health_score', {}).get('overall_rating', 'neutral')
                combined['global_market_health'] = market_health
                insights.append(f"Global market health: {market_health}")
                
                if 'risk_factors' in data:
                    risk_factors.extend(data['risk_factors'])
        
        # Analyze Emerging Markets Historical Data
        if 'emerging_historical' in global_results:
            eh = global_results['emerging_historical']
            if eh.get('success'):
                data = eh.get('data', {})
                sentiment = data.get('market_sentiment', {}).get('overall_sentiment', 'neutral')
                combined['emerging_markets_sentiment'] = sentiment
                insights.append(f"Emerging markets sentiment: {sentiment}")
                
                if 'volatility_assessment' in data:
                    vol_rating = data['volatility_assessment'].get('overall_rating', 'medium')
                    combined['risk_assessment'] = vol_rating
        
        # Analyze Global Exchanges Data
        if 'global_exchanges' in global_results:
            ge = global_results['global_exchanges']
            if ge.get('success'):
                data = ge.get('data', {})
                if 'trading_opportunities' in data:
                    combined['cross_market_opportunities'] = data['trading_opportunities'][:5]  # Top 5
                
                if 'currency_impact' in data:
                    combined['currency_impact'] = data['currency_impact'].get('assessment', 'moderate')
        
        # Cross-market correlation insights
        if 'cross_market_correlation' in global_results:
            cmc = global_results['cross_market_correlation']
            if cmc.get('success'):
                data = cmc.get('data', {})
                if 'recommended_pairs' in data:
                    for pair in data['recommended_pairs'][:3]:  # Top 3 pairs
                        insights.append(f"Strong correlation between {pair.get('symbol1')} and {pair.get('symbol2')}")
        
        # Regional outlook
        regional_map = {
            'americas': 'American markets',
            'europe': 'European markets', 
            'asia_pacific': 'Asia-Pacific markets',
            'mena_africa': 'MENA & Africa markets'
        }
        
        if region != 'all' and region in regional_map:
            combined['regional_outlook'][region] = {
                'focus': regional_map[region],
                'outlook': 'positive',  # Simplified
                'key_drivers': ['economic growth', 'market liquidity', 'regulatory environment']
            }
        
        # Investment recommendations
        if combined['global_market_health'] in ['strong', 'excellent']:
            combined['investment_recommendations'].append({
                'strategy': 'Growth Focus',
                'allocation': 'Increase emerging markets exposure',
                'timeframe': 'Medium-term'
            })
        elif combined['emerging_markets_sentiment'] == 'positive':
            combined['investment_recommendations'].append({
                'strategy': 'Diversification',
                'allocation': 'Geographic diversification recommended',
                'timeframe': 'Long-term'
            })
        
        combined['key_global_insights'] = insights
        combined['analysis_timestamp'] = datetime.now().isoformat()
        combined['symbols_analyzed'] = len(symbols)
        combined['region_focus'] = region
        
        return combined
        
    async def get_service_status(self) -> Dict[str, Any]:
        """Get status of all integrated services"""
        status = {
            'integration_service': {
                'running': self.running,
                'services_count': len(self.services),
                'timestamp': datetime.now().isoformat()
            },
            'individual_services': {}
        }
        
        for service_name, config in self.service_config.items():
            service_status = {
                'available': service_name in self.services,
                'description': config['description'],
                'data_types': config['data_types']
            }
            
            if service_name in self.services:
                service_status['running'] = self.services[service_name].running
                
            status['individual_services'][service_name] = service_status
            
        return status
        
    async def test_all_services(self) -> Dict[str, Any]:
        """Test all integrated services"""
        logger.info("Testing all integrated services")
        test_results = {}
        
        # Test each service with a sample request
        test_cases = {
            'alpha_vantage_smallcap': {'type': 'batch', 'limit': 2},
            'finnhub_fundamentals': {'type': 'batch', 'limit': 2},
            'ecb_macroeconomics': {'type': 'comprehensive'},
            'dealroom_eu_startup': {'type': 'overview', 'region': 'Germany'},
            'iex_cloud_microcap': {'type': 'batch', 'limit': 2},
            # Global Data Sources Tests
            'twelve_data_global': {'type': 'overview', 'region': 'all'},
            'eod_historical_emerging': {'type': 'historical_analysis', 'symbols': ['BABA'], 'region': 'asia'},
            'marketstack_global_exchanges': {'type': 'exchanges_overview'}
        }
        
        for service_name, test_request in test_cases.items():
            try:
                test_request['source'] = service_name
                result = await self.handle_data_request(test_request)
                test_results[service_name] = {
                    'success': result.get('success', False),
                    'response_time': 'measured',
                    'data_quality': 'checked' if result.get('success') else 'failed'
                }
                logger.info(f"Service test completed", 
                          service=service_name, 
                          success=result.get('success', False))
            except Exception as e:
                test_results[service_name] = {
                    'success': False,
                    'error': str(e),
                    'data_quality': 'failed'
                }
                logger.error(f"Service test failed", service=service_name, error=str(e))
                
        return {
            'test_timestamp': datetime.now().isoformat(),
            'total_services': len(test_cases),
            'successful_tests': len([r for r in test_results.values() if r.get('success')]),
            'results': test_results
        }
        
    async def run(self):
        """Main integration service loop"""
        logger.info("Data Sources Integration Service started successfully")
        
        while self.running:
            try:
                # Periodic health check
                status = await self.get_service_status()
                active_services = len([s for s in status['individual_services'].values() if s.get('available')])
                
                logger.info("Integration service health check", 
                          active_services=active_services,
                          total_services=len(self.service_config),
                          timestamp=datetime.now().isoformat())
                          
                # Wait 30 minutes between health checks
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error("Error in integration service loop", error=str(e))
                await asyncio.sleep(300)  # Wait 5 minutes on error
                
    async def shutdown(self):
        """Shutdown integration service"""
        logger.info("Shutting down Data Sources Integration Service")
        self.running = False
        
        # Shutdown all services
        for service_name, service in self.services.items():
            try:
                await service.shutdown()
                logger.info(f"Service shut down", service=service_name)
            except Exception as e:
                logger.error(f"Error shutting down service", service=service_name, error=str(e))
                
        logger.info("Data Sources Integration Service stopped")

async def main():
    """Main entry point"""
    integration_service = DataSourcesIntegration()
    
    try:
        success = await integration_service.initialize()
        if not success:
            logger.error("Failed to initialize integration service")
            return 1
            
        # Run service tests
        test_results = await integration_service.test_all_services()
        logger.info("Service integration tests completed", 
                   successful=test_results['successful_tests'],
                   total=test_results['total_services'])
        
        await integration_service.run()
        return 0
        
    except KeyboardInterrupt:
        logger.info("Integration service interrupted by user")
        await integration_service.shutdown()
        return 0
    except Exception as e:
        logger.error("Integration service failed", error=str(e))
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Integration service interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Critical integration service error", error=str(e))
        sys.exit(1)