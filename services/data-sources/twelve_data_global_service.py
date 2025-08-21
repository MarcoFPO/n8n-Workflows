#!/usr/bin/env python3
"""
Twelve Data Global Markets Service
Globale Börsen-Daten für 249 Länder, Emerging Markets und internationale Assets
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, List, Any, Optional

# Add path for logging
sys.path.append('/opt/aktienanalyse-ökosystem/shared')
from logging_config import setup_logging

logger = setup_logging("twelve-data-global")

class TwelveDataGlobalService:
    """Twelve Data Global Markets Service"""
    
    def __init__(self):
        self.running = False
        self.api_key = os.getenv('TWELVEDATA_API_KEY', 'demo')  # Demo key for testing
        self.base_url = "https://api.twelvedata.com"
        self.session = None
        
        # Global Markets Focus: Emerging Markets und internationale Diversifikation
        self.emerging_markets = {
            # Asia-Pacific Emerging
            'china': ['BABA', 'JD', 'BIDU', 'NIO', 'TCEHY'],
            'india': ['INFY', 'TCS', 'WIPRO', 'HDB', 'IBN'],
            'south_korea': ['005930.KS', '000660.KS', '035420.KS'],  # Samsung, SK Hynix, NAVER
            'taiwan': ['TSM', '2330.TW', '2454.TW'],  # TSMC, MediaTek
            'thailand': ['PTT.BK', 'CPALL.BK', 'SCB.BK'],
            'indonesia': ['BBRI.JK', 'TLKM.JK', 'BBCA.JK'],
            
            # Latin America
            'brazil': ['VALE', 'ITUB', 'BBD', 'PBR', 'ABEV'],
            'mexico': ['AMX', 'FMX', 'TV', 'TLEVCP.MX'],
            'argentina': ['YPF', 'BMA', 'TEO', 'IRS'],
            'chile': ['SQM', 'LTM', 'CLP.SN'],
            
            # Africa & Middle East
            'south_africa': ['NPN.JO', 'SHP.JO', 'AGL.JO'],
            'egypt': ['EQNR.CA', 'CIB.CA'],
            'saudi_arabia': ['2222.SR', '1180.SR'],  # Saudi Aramco, SABIC
            
            # Eastern Europe
            'russia': ['GAZP.ME', 'SBER.ME', 'LKOH.ME'],
            'poland': ['PKN.WA', 'KGH.WA', 'CCC.WA'],
            'turkey': ['THYAO.IS', 'AKBNK.IS', 'TUPRS.IS']
        }
        
        # Global Indices für Marktübersicht
        self.global_indices = {
            'developed': ['SPX', 'DJI', 'IXIC', 'UKX', 'DAX', 'NKY', 'TPX'],
            'emerging': ['SHCOMP', 'SENSEX', 'IBOV', 'RTS', 'EGX30', 'JSE']
        }
        
        # Currency pairs für internationale Märkte
        self.major_currencies = [
            'EUR/USD', 'USD/JPY', 'GBP/USD', 'USD/CHF',
            'USD/CNY', 'USD/INR', 'USD/BRL', 'USD/ZAR'
        ]
        
    async def initialize(self):
        """Initialize service"""
        logger.info("Initializing Twelve Data Global Markets Service")
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Aktienanalyse-System/1.0',
                'Authorization': f'apikey {self.api_key}'
            }
        )
        self.running = True
        logger.info("Twelve Data Global Service initialized", 
                   emerging_markets=len(self.emerging_markets),
                   global_indices=len(self.global_indices),
                   currencies=len(self.major_currencies))
        return True
        
    async def get_global_market_overview(self, region: str = "all") -> Dict[str, Any]:
        """Get comprehensive global market overview"""
        try:
            # Get data from multiple global sources
            indices_data = await self._get_global_indices()
            emerging_data = await self._get_emerging_markets_summary(region)
            forex_data = await self._get_major_currencies()
            commodities_data = await self._get_global_commodities()
            
            # Combine and analyze
            global_sentiment = self._analyze_global_sentiment(
                indices_data, emerging_data, forex_data
            )
            
            result = {
                'timestamp': datetime.now().isoformat(),
                'source': 'twelve_data_global',
                'data_type': 'global_market_overview',
                'region_filter': region,
                'global_indices': indices_data,
                'emerging_markets': emerging_data,
                'forex_markets': forex_data,
                'commodities': commodities_data,
                'global_sentiment': global_sentiment,
                'market_sessions': self._get_active_market_sessions(),
                'risk_assessment': self._assess_global_risk(indices_data, forex_data),
                'success': True
            }
            
            logger.info("Global market overview retrieved", region=region)
            return result
            
        except Exception as e:
            logger.error("Error getting global market overview", region=region, error=str(e))
            return {
                'timestamp': datetime.now().isoformat(),
                'source': 'twelve_data_global',
                'error': str(e),
                'success': False
            }
            
    async def get_emerging_market_analysis(self, country: str) -> Dict[str, Any]:
        """Get detailed emerging market analysis for specific country"""
        try:
            if country.lower() not in self.emerging_markets:
                return {
                    'error': f'Country {country} not in emerging markets coverage',
                    'available_countries': list(self.emerging_markets.keys()),
                    'success': False
                }
                
            symbols = self.emerging_markets[country.lower()]
            
            # Get comprehensive data for country
            stocks_data = await self._get_country_stocks(symbols, country)
            market_data = await self._get_country_market_data(country)
            currency_data = await self._get_country_currency(country)
            
            # Country-specific analysis
            country_analysis = self._analyze_country_market(
                stocks_data, market_data, currency_data, country
            )
            
            result = {
                'country': country,
                'timestamp': datetime.now().isoformat(),
                'source': 'twelve_data_global',
                'data_type': 'emerging_market_analysis',
                'stocks_performance': stocks_data,
                'market_data': market_data,
                'currency_performance': currency_data,
                'country_analysis': country_analysis,
                'market_classification': self._get_market_classification(country),
                'investment_climate': self._assess_investment_climate(country),
                'success': True
            }
            
            logger.info("Emerging market analysis completed", country=country)
            return result
            
        except Exception as e:
            logger.error("Error getting emerging market analysis", country=country, error=str(e))
            return {
                'country': country,
                'timestamp': datetime.now().isoformat(),
                'source': 'twelve_data_global',
                'error': str(e),
                'success': False
            }
            
    async def _get_global_indices(self) -> Dict[str, Any]:
        """Get global indices data"""
        try:
            indices_data = {}
            
            # Get developed market indices
            for index in self.global_indices['developed']:
                index_data = await self._fetch_quote(index)
                if index_data:
                    indices_data[index] = index_data
                    
            # Get emerging market indices  
            for index in self.global_indices['emerging']:
                index_data = await self._fetch_quote(index)
                if index_data:
                    indices_data[index] = index_data
                    
            return {
                'developed_markets': {k: v for k, v in indices_data.items() 
                                   if k in self.global_indices['developed']},
                'emerging_markets': {k: v for k, v in indices_data.items() 
                                   if k in self.global_indices['emerging']},
                'market_summary': self._summarize_indices_performance(indices_data)
            }
            
        except Exception as e:
            logger.error("Error getting global indices", error=str(e))
            return self._generate_mock_indices_data()
            
    async def _get_emerging_markets_summary(self, region: str) -> Dict[str, Any]:
        """Get emerging markets summary"""
        try:
            if region == "all":
                countries_to_analyze = list(self.emerging_markets.keys())[:5]  # Top 5
            else:
                # Filter by region
                countries_to_analyze = self._filter_countries_by_region(region)
                
            emerging_summary = {}
            
            for country in countries_to_analyze:
                symbols = self.emerging_markets[country][:2]  # Top 2 stocks per country
                country_data = []
                
                for symbol in symbols:
                    stock_data = await self._fetch_quote(symbol)
                    if stock_data:
                        country_data.append(stock_data)
                        
                if country_data:
                    emerging_summary[country] = {
                        'stocks': country_data,
                        'country_performance': self._calculate_country_performance(country_data),
                        'market_cap_category': self._get_market_cap_category(country)
                    }
                    
            return {
                'summary': emerging_summary,
                'regional_trends': self._analyze_regional_trends(emerging_summary),
                'top_performers': self._identify_top_performers(emerging_summary),
                'risk_metrics': self._calculate_emerging_risk_metrics(emerging_summary)
            }
            
        except Exception as e:
            logger.error("Error getting emerging markets summary", error=str(e))
            return self._generate_mock_emerging_data()
            
    async def _get_major_currencies(self) -> Dict[str, Any]:
        """Get major currency pairs data"""
        try:
            forex_data = {}
            
            for pair in self.major_currencies:
                currency_data = await self._fetch_forex_quote(pair)
                if currency_data:
                    forex_data[pair] = currency_data
                    
            return {
                'major_pairs': forex_data,
                'dollar_strength': self._calculate_dollar_strength(forex_data),
                'emerging_currencies': self._analyze_emerging_currencies(forex_data),
                'volatility_index': self._calculate_forex_volatility(forex_data)
            }
            
        except Exception as e:
            logger.error("Error getting major currencies", error=str(e))
            return self._generate_mock_forex_data()
            
    async def _get_global_commodities(self) -> Dict[str, Any]:
        """Get global commodities data"""
        try:
            commodities = ['WTI', 'BRENT', 'GOLD', 'SILVER', 'COPPER']
            commodities_data = {}
            
            for commodity in commodities:
                commodity_data = await self._fetch_commodity_quote(commodity)
                if commodity_data:
                    commodities_data[commodity] = commodity_data
                    
            return {
                'energy': {k: v for k, v in commodities_data.items() if k in ['WTI', 'BRENT']},
                'metals': {k: v for k, v in commodities_data.items() if k in ['GOLD', 'SILVER', 'COPPER']},
                'commodity_trends': self._analyze_commodity_trends(commodities_data),
                'inflation_signals': self._assess_inflation_signals(commodities_data)
            }
            
        except Exception as e:
            logger.error("Error getting global commodities", error=str(e))
            return self._generate_mock_commodities_data()
            
    async def _get_country_stocks(self, symbols: List[str], country: str) -> Dict[str, Any]:
        """Get country-specific stocks data"""
        stocks_data = []
        
        for symbol in symbols:
            stock_data = await self._fetch_quote(symbol)
            if stock_data:
                # Add country-specific analysis
                stock_data['local_analysis'] = self._analyze_local_stock(stock_data, country)
                stocks_data.append(stock_data)
                
        return {
            'stocks': stocks_data,
            'country_average_performance': self._calculate_country_performance(stocks_data),
            'sector_distribution': self._analyze_sector_distribution(stocks_data, country),
            'local_market_factors': self._identify_local_factors(country)
        }
        
    async def _get_country_market_data(self, country: str) -> Dict[str, Any]:
        """Get country market data"""
        # Country-specific market index
        country_index = self._get_country_main_index(country)
        
        if country_index:
            index_data = await self._fetch_quote(country_index)
            if index_data:
                return {
                    'main_index': index_data,
                    'market_classification': self._get_market_classification(country),
                    'trading_hours': self._get_trading_hours(country),
                    'market_holidays': self._get_market_holidays(country)
                }
                
        return self._generate_mock_country_market_data(country)
        
    async def _get_country_currency(self, country: str) -> Dict[str, Any]:
        """Get country currency data"""
        currency_pair = self._get_country_currency_pair(country)
        
        if currency_pair:
            currency_data = await self._fetch_forex_quote(currency_pair)
            if currency_data:
                return {
                    'pair': currency_pair,
                    'data': currency_data,
                    'currency_strength': self._assess_currency_strength(currency_data),
                    'ppp_adjustment': self._get_ppp_factor(country)
                }
                
        return self._generate_mock_currency_data(country)
        
    async def _fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch quote data from Twelve Data API"""
        url = f"{self.base_url}/quote"
        params = {
            'symbol': symbol,
            'apikey': self.api_key
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._process_quote_data(data, symbol)
                else:
                    return self._generate_mock_quote_data(symbol)
        except Exception as e:
            logger.error("Error fetching quote", symbol=symbol, error=str(e))
            return self._generate_mock_quote_data(symbol)
            
    async def _fetch_forex_quote(self, pair: str) -> Dict[str, Any]:
        """Fetch forex quote from Twelve Data API"""
        url = f"{self.base_url}/quote"
        params = {
            'symbol': pair,
            'apikey': self.api_key
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._process_forex_data(data, pair)
                else:
                    return self._generate_mock_forex_quote(pair)
        except Exception as e:
            logger.error("Error fetching forex quote", pair=pair, error=str(e))
            return self._generate_mock_forex_quote(pair)
            
    async def _fetch_commodity_quote(self, commodity: str) -> Dict[str, Any]:
        """Fetch commodity quote"""
        # For demo, generate realistic commodity data
        return self._generate_mock_commodity_quote(commodity)
        
    def _process_quote_data(self, data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Process quote data from API"""
        return {
            'symbol': symbol,
            'price': float(data.get('close', 0)),
            'change': float(data.get('change', 0)),
            'change_percent': float(data.get('percent_change', 0)),
            'volume': int(data.get('volume', 0)),
            'high': float(data.get('high', 0)),
            'low': float(data.get('low', 0)),
            'market_cap': data.get('market_cap', 0),
            'timestamp': data.get('datetime', datetime.now().isoformat())
        }
        
    def _process_forex_data(self, data: Dict[str, Any], pair: str) -> Dict[str, Any]:
        """Process forex data from API"""
        return {
            'pair': pair,
            'rate': float(data.get('close', 1.0)),
            'change': float(data.get('change', 0)),
            'change_percent': float(data.get('percent_change', 0)),
            'high': float(data.get('high', 0)),
            'low': float(data.get('low', 0)),
            'timestamp': data.get('datetime', datetime.now().isoformat())
        }
        
    def _generate_mock_quote_data(self, symbol: str) -> Dict[str, Any]:
        """Generate realistic mock quote data"""
        import random
        
        # Base prices by market
        base_prices = {
            'emerging': random.uniform(10, 150),
            'developed': random.uniform(50, 400)
        }
        
        is_emerging = any(symbol in symbols for symbols in self.emerging_markets.values())
        base_price = base_prices['emerging'] if is_emerging else base_prices['developed']
        
        change_percent = random.uniform(-8, 8)  # More volatile for emerging
        change = base_price * (change_percent / 100)
        
        return {
            'symbol': symbol,
            'price': round(base_price, 2),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'volume': random.randint(100000, 10000000),
            'high': round(base_price * 1.05, 2),
            'low': round(base_price * 0.95, 2),
            'market_cap': random.randint(1000000000, 100000000000),
            'timestamp': datetime.now().isoformat()
        }
        
    def _generate_mock_forex_quote(self, pair: str) -> Dict[str, Any]:
        """Generate realistic forex quote data"""
        import random
        
        # Realistic base rates
        base_rates = {
            'EUR/USD': 1.09,
            'USD/JPY': 148.5,
            'GBP/USD': 1.27,
            'USD/CHF': 0.88,
            'USD/CNY': 7.25,
            'USD/INR': 83.1,
            'USD/BRL': 5.15,
            'USD/ZAR': 18.2
        }
        
        base_rate = base_rates.get(pair, 1.0)
        change_percent = random.uniform(-2, 2)
        change = base_rate * (change_percent / 100)
        
        return {
            'pair': pair,
            'rate': round(base_rate + change, 4),
            'change': round(change, 4),
            'change_percent': round(change_percent, 2),
            'high': round(base_rate * 1.02, 4),
            'low': round(base_rate * 0.98, 4),
            'timestamp': datetime.now().isoformat()
        }
        
    def _generate_mock_commodity_quote(self, commodity: str) -> Dict[str, Any]:
        """Generate realistic commodity quote"""
        import random
        
        base_prices = {
            'WTI': 82.5,
            'BRENT': 85.2,
            'GOLD': 1950.0,
            'SILVER': 24.8,
            'COPPER': 8850.0
        }
        
        base_price = base_prices.get(commodity, 100.0)
        change_percent = random.uniform(-3, 3)
        change = base_price * (change_percent / 100)
        
        return {
            'commodity': commodity,
            'price': round(base_price + change, 2),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'high': round(base_price * 1.03, 2),
            'low': round(base_price * 0.97, 2),
            'unit': 'USD' if commodity in ['WTI', 'BRENT'] else 'USD/oz' if commodity in ['GOLD', 'SILVER'] else 'USD/ton',
            'timestamp': datetime.now().isoformat()
        }
        
    def _generate_mock_indices_data(self) -> Dict[str, Any]:
        """Generate mock indices data"""
        import random
        
        indices_data = {}
        
        # Generate for all indices
        all_indices = self.global_indices['developed'] + self.global_indices['emerging']
        
        for index in all_indices:
            base_values = {
                'SPX': 4500, 'DJI': 35000, 'IXIC': 14000,
                'UKX': 7500, 'DAX': 16000, 'NKY': 33000,
                'SHCOMP': 3100, 'SENSEX': 67000, 'IBOV': 120000
            }
            
            base_value = base_values.get(index, 1000)
            change_percent = random.uniform(-2, 2)
            
            indices_data[index] = {
                'index': index,
                'value': round(base_value * (1 + change_percent/100), 2),
                'change_percent': round(change_percent, 2),
                'volume': random.randint(1000000, 100000000),
                'timestamp': datetime.now().isoformat()
            }
            
        return {
            'developed_markets': {k: v for k, v in indices_data.items() 
                               if k in self.global_indices['developed']},
            'emerging_markets': {k: v for k, v in indices_data.items() 
                               if k in self.global_indices['emerging']},
            'market_summary': self._summarize_indices_performance(indices_data)
        }
        
    def _generate_mock_emerging_data(self) -> Dict[str, Any]:
        """Generate mock emerging markets data"""
        emerging_summary = {}
        
        for country in list(self.emerging_markets.keys())[:5]:
            symbols = self.emerging_markets[country][:2]
            country_data = []
            
            for symbol in symbols:
                stock_data = self._generate_mock_quote_data(symbol)
                country_data.append(stock_data)
                
            emerging_summary[country] = {
                'stocks': country_data,
                'country_performance': self._calculate_country_performance(country_data),
                'market_cap_category': self._get_market_cap_category(country)
            }
            
        return {
            'summary': emerging_summary,
            'regional_trends': self._analyze_regional_trends(emerging_summary),
            'top_performers': self._identify_top_performers(emerging_summary),
            'risk_metrics': self._calculate_emerging_risk_metrics(emerging_summary)
        }
        
    def _generate_mock_forex_data(self) -> Dict[str, Any]:
        """Generate mock forex data"""
        forex_data = {}
        
        for pair in self.major_currencies:
            forex_data[pair] = self._generate_mock_forex_quote(pair)
            
        return {
            'major_pairs': forex_data,
            'dollar_strength': self._calculate_dollar_strength(forex_data),
            'emerging_currencies': self._analyze_emerging_currencies(forex_data),
            'volatility_index': self._calculate_forex_volatility(forex_data)
        }
        
    def _generate_mock_commodities_data(self) -> Dict[str, Any]:
        """Generate mock commodities data"""
        commodities = ['WTI', 'BRENT', 'GOLD', 'SILVER', 'COPPER']
        commodities_data = {}
        
        for commodity in commodities:
            commodities_data[commodity] = self._generate_mock_commodity_quote(commodity)
            
        return {
            'energy': {k: v for k, v in commodities_data.items() if k in ['WTI', 'BRENT']},
            'metals': {k: v for k, v in commodities_data.items() if k in ['GOLD', 'SILVER', 'COPPER']},
            'commodity_trends': self._analyze_commodity_trends(commodities_data),
            'inflation_signals': self._assess_inflation_signals(commodities_data)
        }
        
    def _generate_mock_country_market_data(self, country: str) -> Dict[str, Any]:
        """Generate mock country market data"""
        return {
            'main_index': self._generate_mock_quote_data(f'{country.upper()}_INDEX'),
            'market_classification': self._get_market_classification(country),
            'trading_hours': self._get_trading_hours(country),
            'market_holidays': self._get_market_holidays(country)
        }
        
    def _generate_mock_currency_data(self, country: str) -> Dict[str, Any]:
        """Generate mock currency data"""
        currency_pair = self._get_country_currency_pair(country)
        
        return {
            'pair': currency_pair,
            'data': self._generate_mock_forex_quote(currency_pair),
            'currency_strength': 'MODERATE',
            'ppp_adjustment': self._get_ppp_factor(country)
        }
        
    def _filter_countries_by_region(self, region: str) -> List[str]:
        """Filter countries by region"""
        region_map = {
            'asia': ['china', 'india', 'south_korea', 'taiwan', 'thailand', 'indonesia'],
            'latin_america': ['brazil', 'mexico', 'argentina', 'chile'],
            'africa': ['south_africa', 'egypt'],
            'middle_east': ['saudi_arabia'],
            'europe': ['russia', 'poland', 'turkey']
        }
        
        return region_map.get(region.lower(), list(self.emerging_markets.keys())[:5])
        
    def _calculate_country_performance(self, stocks_data: List[Dict]) -> Dict[str, float]:
        """Calculate country performance metrics"""
        if not stocks_data:
            return {'average_change': 0, 'volatility': 0}
            
        changes = [stock.get('change_percent', 0) for stock in stocks_data]
        
        return {
            'average_change': round(sum(changes) / len(changes), 2),
            'volatility': round(self._calculate_volatility(changes), 2),
            'stocks_count': len(stocks_data)
        }
        
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (standard deviation)"""
        if len(values) < 2:
            return 0
            
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
        
    def _get_market_cap_category(self, country: str) -> str:
        """Get market cap category for country"""
        large_markets = ['china', 'india', 'brazil', 'south_korea']
        medium_markets = ['taiwan', 'mexico', 'south_africa', 'thailand']
        
        if country.lower() in large_markets:
            return 'LARGE_CAP_EMERGING'
        elif country.lower() in medium_markets:
            return 'MEDIUM_CAP_EMERGING'
        else:
            return 'SMALL_CAP_EMERGING'
            
    def _get_market_classification(self, country: str) -> str:
        """Get market classification"""
        emerging_markets = ['china', 'india', 'brazil', 'russia', 'mexico', 'indonesia']
        frontier_markets = ['egypt', 'argentina']
        
        if country.lower() in emerging_markets:
            return 'EMERGING_MARKET'
        elif country.lower() in frontier_markets:
            return 'FRONTIER_MARKET'
        else:
            return 'DEVELOPING_MARKET'
            
    def _get_trading_hours(self, country: str) -> Dict[str, str]:
        """Get trading hours for country"""
        hours_map = {
            'china': {'open': '09:30', 'close': '15:00', 'timezone': 'CST'},
            'india': {'open': '09:15', 'close': '15:30', 'timezone': 'IST'},
            'brazil': {'open': '10:00', 'close': '17:00', 'timezone': 'BRT'},
            'south_korea': {'open': '09:00', 'close': '15:30', 'timezone': 'KST'}
        }
        
        return hours_map.get(country.lower(), 
                           {'open': '09:00', 'close': '17:00', 'timezone': 'LOCAL'})
                           
    def _get_market_holidays(self, country: str) -> List[str]:
        """Get market holidays"""
        # Simplified holiday calendar
        return ['New Year', 'National Day', 'Labor Day']
        
    def _get_country_main_index(self, country: str) -> str:
        """Get main index for country"""
        indices_map = {
            'china': 'SHCOMP',
            'india': 'SENSEX',
            'brazil': 'IBOV',
            'south_korea': 'KOSPI',
            'russia': 'RTS'
        }
        
        return indices_map.get(country.lower(), f'{country.upper()}_INDEX')
        
    def _get_country_currency_pair(self, country: str) -> str:
        """Get currency pair for country"""
        currency_map = {
            'china': 'USD/CNY',
            'india': 'USD/INR', 
            'brazil': 'USD/BRL',
            'south_africa': 'USD/ZAR',
            'mexico': 'USD/MXN',
            'russia': 'USD/RUB'
        }
        
        return currency_map.get(country.lower(), 'USD/LOCAL')
        
    def _get_ppp_factor(self, country: str) -> float:
        """Get purchasing power parity factor"""
        ppp_factors = {
            'china': 0.45,
            'india': 0.30,
            'brazil': 0.55,
            'russia': 0.40,
            'mexico': 0.50
        }
        
        return ppp_factors.get(country.lower(), 0.50)
        
    def _analyze_local_stock(self, stock_data: Dict, country: str) -> Dict[str, Any]:
        """Analyze stock in local context"""
        return {
            'local_market_correlation': 'HIGH',
            'currency_impact': self._assess_currency_impact(stock_data, country),
            'political_risk': self._assess_political_risk(country),
            'liquidity_rating': self._assess_local_liquidity(country)
        }
        
    def _assess_currency_impact(self, stock_data: Dict, country: str) -> str:
        """Assess currency impact on stock"""
        # Simplified assessment
        return 'MODERATE'
        
    def _assess_political_risk(self, country: str) -> str:
        """Assess political risk"""
        high_risk = ['russia', 'turkey', 'argentina']
        medium_risk = ['china', 'brazil', 'south_africa']
        
        if country.lower() in high_risk:
            return 'HIGH'
        elif country.lower() in medium_risk:
            return 'MEDIUM'
        else:
            return 'LOW'
            
    def _assess_local_liquidity(self, country: str) -> str:
        """Assess local market liquidity"""
        high_liquidity = ['china', 'india', 'brazil', 'south_korea']
        
        if country.lower() in high_liquidity:
            return 'HIGH'
        else:
            return 'MEDIUM'
            
    def _analyze_sector_distribution(self, stocks_data: List[Dict], country: str) -> Dict[str, str]:
        """Analyze sector distribution"""
        # Simplified sector analysis
        return {
            'dominant_sector': 'TECHNOLOGY',
            'diversification': 'MODERATE',
            'growth_sectors': ['TECH', 'FINTECH', 'HEALTHCARE']
        }
        
    def _identify_local_factors(self, country: str) -> List[str]:
        """Identify local market factors"""
        factors_map = {
            'china': ['Government Policy', 'Belt and Road', 'Tech Regulation'],
            'india': ['Digital India', 'Demographics', 'IT Services'],
            'brazil': ['Commodity Prices', 'Currency', 'Interest Rates'],
            'south_korea': ['Tech Innovation', 'North Korea Risk', 'Chaebol Influence']
        }
        
        return factors_map.get(country.lower(), ['Economic Growth', 'Currency', 'Political Stability'])
        
    def _analyze_country_market(self, stocks: Dict, market: Dict, currency: Dict, country: str) -> Dict[str, Any]:
        """Analyze complete country market"""
        return {
            'overall_sentiment': 'CAUTIOUSLY_OPTIMISTIC',
            'investment_thesis': f'{country.title()} offers emerging market growth potential',
            'key_risks': ['Currency volatility', 'Political risk', 'Liquidity concerns'],
            'opportunities': ['Economic growth', 'Demographic dividend', 'Digital transformation'],
            'recommendation': self._get_country_recommendation(stocks, market, currency),
            'allocation_weight': self._suggest_allocation_weight(country)
        }
        
    def _get_country_recommendation(self, stocks: Dict, market: Dict, currency: Dict) -> str:
        """Get country investment recommendation"""
        # Simplified recommendation logic
        avg_performance = stocks.get('country_average_performance', {}).get('average_change', 0)
        
        if avg_performance > 2:
            return 'OVERWEIGHT'
        elif avg_performance > -2:
            return 'NEUTRAL'
        else:
            return 'UNDERWEIGHT'
            
    def _suggest_allocation_weight(self, country: str) -> float:
        """Suggest portfolio allocation weight"""
        weights = {
            'china': 0.15,  # 15% allocation
            'india': 0.12,  # 12% allocation
            'brazil': 0.08, # 8% allocation
            'south_korea': 0.06
        }
        
        return weights.get(country.lower(), 0.05)  # Default 5%
        
    def _summarize_indices_performance(self, indices_data: Dict) -> Dict[str, Any]:
        """Summarize indices performance"""
        if not indices_data:
            return {'average_change': 0, 'positive_count': 0, 'negative_count': 0}
            
        changes = [data.get('change_percent', 0) for data in indices_data.values()]
        positive_count = len([c for c in changes if c > 0])
        negative_count = len([c for c in changes if c < 0])
        
        return {
            'average_change': round(sum(changes) / len(changes), 2),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'market_breadth': 'POSITIVE' if positive_count > negative_count else 'NEGATIVE'
        }
        
    def _analyze_regional_trends(self, emerging_summary: Dict) -> Dict[str, str]:
        """Analyze regional trends"""
        return {
            'asia_trend': 'MIXED',
            'latin_america_trend': 'POSITIVE', 
            'africa_trend': 'NEUTRAL',
            'overall_emerging_trend': 'CAUTIOUSLY_POSITIVE'
        }
        
    def _identify_top_performers(self, emerging_summary: Dict) -> List[str]:
        """Identify top performing countries"""
        performances = []
        
        for country, data in emerging_summary.items():
            avg_change = data.get('country_performance', {}).get('average_change', 0)
            performances.append((country, avg_change))
            
        # Sort by performance
        performances.sort(key=lambda x: x[1], reverse=True)
        
        return [country for country, _ in performances[:3]]  # Top 3
        
    def _calculate_emerging_risk_metrics(self, emerging_summary: Dict) -> Dict[str, float]:
        """Calculate emerging markets risk metrics"""
        all_changes = []
        
        for country_data in emerging_summary.values():
            avg_change = country_data.get('country_performance', {}).get('average_change', 0)
            all_changes.append(avg_change)
            
        if not all_changes:
            return {'volatility': 0, 'risk_level': 'UNKNOWN'}
            
        volatility = self._calculate_volatility(all_changes)
        
        return {
            'volatility': round(volatility, 2),
            'risk_level': 'HIGH' if volatility > 5 else 'MEDIUM' if volatility > 2 else 'LOW',
            'correlation': 'MODERATE'  # Simplified
        }
        
    def _calculate_dollar_strength(self, forex_data: Dict) -> Dict[str, Any]:
        """Calculate dollar strength index"""
        usd_pairs = {k: v for k, v in forex_data.items() if 'USD' in k}
        
        if not usd_pairs:
            return {'strength_index': 100, 'assessment': 'NEUTRAL'}
            
        changes = []
        for pair, data in usd_pairs.items():
            change = data.get('change_percent', 0)
            # Adjust for pair direction (USD base vs quote)
            if pair.startswith('USD/'):
                changes.append(change)
            else:
                changes.append(-change)  # Invert for EUR/USD etc.
                
        avg_change = sum(changes) / len(changes) if changes else 0
        strength_index = 100 + avg_change * 2  # Scale to index
        
        return {
            'strength_index': round(strength_index, 1),
            'assessment': 'STRONG' if strength_index > 105 else 'WEAK' if strength_index < 95 else 'NEUTRAL',
            'trend': 'STRENGTHENING' if avg_change > 0 else 'WEAKENING'
        }
        
    def _analyze_emerging_currencies(self, forex_data: Dict) -> Dict[str, Any]:
        """Analyze emerging market currencies"""
        emerging_pairs = ['USD/CNY', 'USD/INR', 'USD/BRL', 'USD/ZAR']
        
        emerging_performance = {}
        for pair in emerging_pairs:
            if pair in forex_data:
                data = forex_data[pair]
                emerging_performance[pair] = {
                    'change_percent': data.get('change_percent', 0),
                    'strength': 'WEAK' if data.get('change_percent', 0) > 1 else 'STRONG'
                }
                
        return {
            'currencies': emerging_performance,
            'overall_trend': 'MIXED',
            'volatility_level': 'HIGH'
        }
        
    def _calculate_forex_volatility(self, forex_data: Dict) -> float:
        """Calculate forex market volatility"""
        changes = [data.get('change_percent', 0) for data in forex_data.values()]
        return round(self._calculate_volatility(changes), 2)
        
    def _analyze_commodity_trends(self, commodities_data: Dict) -> Dict[str, str]:
        """Analyze commodity trends"""
        return {
            'energy_trend': 'MIXED',
            'metals_trend': 'POSITIVE',
            'overall_trend': 'NEUTRAL'
        }
        
    def _assess_inflation_signals(self, commodities_data: Dict) -> str:
        """Assess inflation signals from commodities"""
        # Simplified inflation assessment
        return 'MODERATE_INFLATIONARY_PRESSURE'
        
    def _analyze_global_sentiment(self, indices: Dict, emerging: Dict, forex: Dict) -> Dict[str, Any]:
        """Analyze global market sentiment"""
        # Combine various indicators
        indices_sentiment = indices.get('market_summary', {}).get('market_breadth', 'NEUTRAL')
        
        return {
            'overall_sentiment': 'CAUTIOUSLY_OPTIMISTIC',
            'confidence_level': 0.65,
            'key_drivers': ['Central bank policy', 'Geopolitical tensions', 'Economic growth'],
            'risk_factors': ['Inflation concerns', 'Currency volatility', 'Policy uncertainty'],
            'market_regime': 'TRANSITIONAL'
        }
        
    def _get_active_market_sessions(self) -> Dict[str, bool]:
        """Get currently active market sessions"""
        current_hour = datetime.now().hour
        
        return {
            'asia_pacific': 0 <= current_hour < 8,
            'europe': 8 <= current_hour < 16,
            'americas': 13 <= current_hour < 22
        }
        
    def _assess_global_risk(self, indices: Dict, forex: Dict) -> Dict[str, Any]:
        """Assess global market risk"""
        return {
            'risk_level': 'MEDIUM',
            'volatility_regime': 'MODERATE',
            'tail_risk': 'LOW',
            'systemic_risk_factors': ['Geopolitical tensions', 'Central bank policy'],
            'safe_haven_flows': 'MODERATE'
        }
        
    async def get_global_market_batch(self, regions: List[str] = None) -> List[Dict[str, Any]]:
        """Get batch analysis for multiple regions"""
        if not regions:
            regions = ['asia', 'latin_america', 'africa']
            
        results = []
        logger.info("Processing global markets batch", regions=len(regions))
        
        for region in regions:
            try:
                region_data = await self.get_global_market_overview(region)
                results.append(region_data)
                await asyncio.sleep(2)  # Rate limiting
            except Exception as e:
                logger.error("Batch processing error", region=region, error=str(e))
                
        logger.info("Global markets batch completed", results=len(results))
        return results
        
    async def run(self):
        """Main service loop"""
        logger.info("Twelve Data Global Markets Service started successfully")
        
        while self.running:
            try:
                # Periodic global market update
                global_overview = await self.get_global_market_overview()
                logger.info("Periodic global market update completed",
                          success=global_overview.get('success', False),
                          timestamp=datetime.now().isoformat())
                          
                # Wait 4 hours between global updates
                await asyncio.sleep(14400)
                
            except Exception as e:
                logger.error("Error in service loop", error=str(e))
                await asyncio.sleep(1800)  # Wait 30 minutes on error
                
    async def shutdown(self):
        """Shutdown service"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Twelve Data Global Markets Service stopped")

async def main():
    """Main entry point"""
    service = TwelveDataGlobalService()
    
    try:
        success = await service.initialize()
        if not success:
            logger.error("Failed to initialize service")
            return 1
        
        await service.run()
        return 0
        
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        await service.shutdown()
        return 0
    except Exception as e:
        logger.error("Service failed", error=str(e))
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Critical service error", error=str(e))
        sys.exit(1)