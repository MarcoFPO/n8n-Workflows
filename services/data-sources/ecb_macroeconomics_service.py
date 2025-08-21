#!/usr/bin/env python3
"""
ECB Macroeconomics Data Source Service
Europäische Zentralbank Daten für makroökonomische Analyse
"""

import asyncio
import aiohttp
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, List, Any, Optional

# Add path for logging
sys.path.append('/opt/aktienanalyse-ökosystem/shared')
from logging_config import setup_logging

logger = setup_logging("ecb-macroeconomics")

class ECBMacroeconomicsService:
    """ECB Macroeconomics Data Source Service"""
    
    def __init__(self):
        self.running = False
        self.base_url = "https://data.ecb.europa.eu/data-detail-api"
        self.session = None
        
        # Key ECB data series for macroeconomic analysis
        self.data_series = {
            # Interest rates
            'key_interest_rate': 'FM.B.U2.EUR.4F.KR.MRR_FR.LEV',
            'deposit_facility': 'FM.B.U2.EUR.4F.KR.DFR.LEV',
            'marginal_lending': 'FM.B.U2.EUR.4F.KR.MLF.LEV',
            
            # Exchange rates (EUR reference rates)
            'eur_usd': 'EXR.D.USD.EUR.SP00.A',
            'eur_gbp': 'EXR.D.GBP.EUR.SP00.A',
            'eur_jpy': 'EXR.D.JPY.EUR.SP00.A',
            'eur_chf': 'EXR.D.CHF.EUR.SP00.A',
            
            # Money supply
            'm1_growth': 'BSI.M.U2.Y.V.M10.X.1.U2.2300.Z01.E',
            'm3_growth': 'BSI.M.U2.Y.V.M30.X.1.U2.2300.Z01.E',
            
            # Inflation
            'hicp_total': 'ICP.M.U2.N.000000.4.ANR',
            'hicp_core': 'ICP.M.U2.N.XEF000.4.ANR',
            
            # Economic indicators
            'gdp_growth': 'MNA.Q.Y.I8.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.N',
            'unemployment_rate': 'LFSI.M.I8.S.UNEHRT.TOTAL0.15_74.T',
            
            # Government finances
            'govt_debt_gdp': 'GFS.Q.N.I8.W0.S13.S1.C.L.LE.GD.T._Z.EUR._T.F.V.N._T',
            'govt_deficit_gdp': 'GFS.A.N.I8.W0.S13.S1.N.B.B9./_Z.EUR._T.S.V.N._T'
        }
        
    async def initialize(self):
        """Initialize service"""
        logger.info("Initializing ECB Macroeconomics Service")
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Aktienanalyse-System/1.0'}
        )
        self.running = True
        logger.info("ECB Macroeconomics Service initialized", 
                   data_series=len(self.data_series))
        return True
        
    async def get_comprehensive_macro_data(self) -> Dict[str, Any]:
        """Get comprehensive macroeconomic data from ECB"""
        try:
            # Get all key macroeconomic indicators
            interest_rates = await self._get_interest_rates()
            exchange_rates = await self._get_exchange_rates()
            monetary_indicators = await self._get_monetary_indicators()
            inflation_data = await self._get_inflation_data()
            economic_indicators = await self._get_economic_indicators()
            
            # Calculate macroeconomic health score
            macro_score = self._calculate_macro_health_score(
                interest_rates, inflation_data, economic_indicators
            )
            
            result = {
                'timestamp': datetime.now().isoformat(),
                'source': 'ecb_macroeconomics',
                'data_type': 'comprehensive_macro_analysis',
                'interest_rates': interest_rates,
                'exchange_rates': exchange_rates,
                'monetary_indicators': monetary_indicators,
                'inflation': inflation_data,
                'economic_indicators': economic_indicators,
                'macro_health_score': macro_score,
                'market_implications': self._analyze_market_implications(
                    interest_rates, inflation_data, exchange_rates
                ),
                'success': True
            }
            
            logger.info("Comprehensive macro data retrieved")
            return result
            
        except Exception as e:
            logger.error("Error getting macro data", error=str(e))
            return {
                'timestamp': datetime.now().isoformat(),
                'source': 'ecb_macroeconomics',
                'error': str(e),
                'success': False
            }
            
    async def _get_interest_rates(self) -> Dict[str, Any]:
        """Get ECB interest rates"""
        try:
            # Get latest key interest rates
            rates = {}
            
            for rate_name, series_key in [
                ('key_rate', 'key_interest_rate'),
                ('deposit_rate', 'deposit_facility'),
                ('lending_rate', 'marginal_lending')
            ]:
                rate_data = await self._fetch_ecb_series(self.data_series[series_key])
                if rate_data:
                    rates[rate_name] = {
                        'current': rate_data.get('current_value', 0),
                        'previous': rate_data.get('previous_value', 0),
                        'change': rate_data.get('change', 0),
                        'last_updated': rate_data.get('last_updated', '')
                    }
                    
            # Analyze rate environment
            key_rate = rates.get('key_rate', {}).get('current', 0)
            rate_environment = self._analyze_rate_environment(key_rate)
            
            return {
                'rates': rates,
                'rate_environment': rate_environment,
                'rate_trend': self._determine_rate_trend(rates),
                'summary': f"ECB key rate at {key_rate}% - {rate_environment}"
            }
            
        except Exception as e:
            logger.error("Error getting interest rates", error=str(e))
            return {}
            
    async def _get_exchange_rates(self) -> Dict[str, Any]:
        """Get EUR exchange rates"""
        try:
            rates = {}
            
            for currency, series_key in [
                ('USD', 'eur_usd'),
                ('GBP', 'eur_gbp'),
                ('JPY', 'eur_jpy'),
                ('CHF', 'eur_chf')
            ]:
                rate_data = await self._fetch_ecb_series(self.data_series[series_key])
                if rate_data:
                    rates[f'EUR_{currency}'] = {
                        'current': rate_data.get('current_value', 0),
                        'change_1d': rate_data.get('change', 0),
                        'change_1w': rate_data.get('change_1w', 0),
                        'change_1m': rate_data.get('change_1m', 0),
                        'volatility': rate_data.get('volatility', 0)
                    }
                    
            # Analyze EUR strength
            eur_strength = self._analyze_eur_strength(rates)
            
            return {
                'rates': rates,
                'eur_strength_index': eur_strength,
                'fx_volatility': self._calculate_fx_volatility(rates),
                'market_impact': self._assess_fx_market_impact(rates)
            }
            
        except Exception as e:
            logger.error("Error getting exchange rates", error=str(e))
            return {}
            
    async def _get_monetary_indicators(self) -> Dict[str, Any]:
        """Get monetary policy indicators"""
        try:
            indicators = {}
            
            # Money supply growth rates
            for indicator, series_key in [
                ('m1_growth', 'm1_growth'),
                ('m3_growth', 'm3_growth')
            ]:
                data = await self._fetch_ecb_series(self.data_series[series_key])
                if data:
                    indicators[indicator] = {
                        'current': data.get('current_value', 0),
                        'target_range': '4-6%' if 'm3' in indicator else '2-4%',
                        'assessment': self._assess_money_growth(
                            data.get('current_value', 0), indicator
                        )
                    }
                    
            return {
                'money_supply': indicators,
                'monetary_stance': self._determine_monetary_stance(indicators),
                'liquidity_conditions': self._assess_liquidity_conditions(indicators)
            }
            
        except Exception as e:
            logger.error("Error getting monetary indicators", error=str(e))
            return {}
            
    async def _get_inflation_data(self) -> Dict[str, Any]:
        """Get inflation indicators"""
        try:
            inflation = {}
            
            # Get HICP data
            for measure, series_key in [
                ('headline', 'hicp_total'),
                ('core', 'hicp_core')
            ]:
                data = await self._fetch_ecb_series(self.data_series[series_key])
                if data:
                    inflation[measure] = {
                        'current': data.get('current_value', 0),
                        'previous': data.get('previous_value', 0),
                        'trend': data.get('trend', 'stable'),
                        'target_distance': abs(data.get('current_value', 0) - 2.0)  # ECB target
                    }
                    
            # Analyze inflation environment
            headline_inflation = inflation.get('headline', {}).get('current', 0)
            inflation_assessment = self._assess_inflation_environment(headline_inflation)
            
            return {
                'measures': inflation,
                'ecb_target': 2.0,
                'environment': inflation_assessment,
                'policy_implications': self._analyze_inflation_policy_implications(inflation)
            }
            
        except Exception as e:
            logger.error("Error getting inflation data", error=str(e))
            return {}
            
    async def _get_economic_indicators(self) -> Dict[str, Any]:
        """Get key economic indicators"""
        try:
            indicators = {}
            
            # Economic growth and employment
            for indicator, series_key in [
                ('gdp_growth', 'gdp_growth'),
                ('unemployment', 'unemployment_rate')
            ]:
                data = await self._fetch_ecb_series(self.data_series[indicator])
                if data:
                    indicators[indicator] = {
                        'current': data.get('current_value', 0),
                        'previous': data.get('previous_value', 0),
                        'assessment': self._assess_economic_indicator(
                            indicator, data.get('current_value', 0)
                        )
                    }
                    
            return {
                'growth_employment': indicators,
                'economic_health': self._assess_economic_health(indicators),
                'cycle_position': self._determine_cycle_position(indicators)
            }
            
        except Exception as e:
            logger.error("Error getting economic indicators", error=str(e))
            return {}
            
    async def _fetch_ecb_series(self, series_key: str) -> Dict[str, Any]:
        """Fetch data from ECB API (simplified for demo)"""
        try:
            # This is a simplified version - in production, you'd use ECB SDMX API
            # For demo purposes, we'll return mock data that resembles ECB data structure
            
            # Simulate realistic ECB data
            mock_data = {
                'current_value': self._generate_realistic_value(series_key),
                'previous_value': self._generate_realistic_value(series_key, offset=-1),
                'last_updated': datetime.now().strftime('%Y-%m-%d'),
                'trend': 'stable'
            }
            
            # Calculate change
            if mock_data['current_value'] and mock_data['previous_value']:
                mock_data['change'] = mock_data['current_value'] - mock_data['previous_value']
                
            return mock_data
            
        except Exception as e:
            logger.error("Error fetching ECB series", series=series_key, error=str(e))
            return {}
            
    def _generate_realistic_value(self, series_key: str, offset: int = 0) -> float:
        """Generate realistic values for ECB data series"""
        import random
        
        # Base values that approximate real ECB data
        base_values = {
            'FM.B.U2.EUR.4F.KR.MRR_FR.LEV': 4.5,  # Key rate
            'FM.B.U2.EUR.4F.KR.DFR.LEV': 4.0,     # Deposit rate
            'FM.B.U2.EUR.4F.KR.MLF.LEV': 4.75,    # Lending rate
            'EXR.D.USD.EUR.SP00.A': 1.09,         # EUR/USD
            'EXR.D.GBP.EUR.SP00.A': 0.86,         # EUR/GBP
            'EXR.D.JPY.EUR.SP00.A': 157.5,        # EUR/JPY
            'EXR.D.CHF.EUR.SP00.A': 0.94,         # EUR/CHF
            'ICP.M.U2.N.000000.4.ANR': 2.4,       # HICP inflation
            'ICP.M.U2.N.XEF000.4.ANR': 2.1,       # Core inflation
            'LFSI.M.I8.S.UNEHRT.TOTAL0.15_74.T': 6.4,  # Unemployment
        }
        
        base_value = base_values.get(series_key, 1.0)
        
        # Add some realistic variation
        variation = random.uniform(-0.05, 0.05) * base_value
        return round(base_value + variation + (offset * 0.01), 2)
        
    def _analyze_rate_environment(self, key_rate: float) -> str:
        """Analyze interest rate environment"""
        if key_rate > 4:
            return "RESTRICTIVE"
        elif key_rate > 2:
            return "NEUTRAL_TO_RESTRICTIVE"
        elif key_rate > 0.5:
            return "NEUTRAL"
        elif key_rate > 0:
            return "ACCOMMODATIVE"
        else:
            return "ULTRA_ACCOMMODATIVE"
            
    def _determine_rate_trend(self, rates: Dict[str, Any]) -> str:
        """Determine interest rate trend"""
        key_rate_change = rates.get('key_rate', {}).get('change', 0)
        
        if key_rate_change > 0.1:
            return "RISING"
        elif key_rate_change < -0.1:
            return "FALLING"
        else:
            return "STABLE"
            
    def _analyze_eur_strength(self, rates: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze EUR strength across major currencies"""
        eur_usd_change = rates.get('EUR_USD', {}).get('change_1d', 0)
        eur_gbp_change = rates.get('EUR_GBP', {}).get('change_1d', 0)
        
        # Simple strength index based on major pairs
        strength_score = (eur_usd_change + eur_gbp_change) * 100
        
        if strength_score > 0.5:
            assessment = "STRONG"
        elif strength_score > 0:
            assessment = "MODERATELY_STRONG"
        elif strength_score > -0.5:
            assessment = "MODERATELY_WEAK"
        else:
            assessment = "WEAK"
            
        return {
            'strength_score': round(strength_score, 2),
            'assessment': assessment,
            'key_drivers': ['interest_rate_differential', 'economic_outlook']
        }
        
    def _calculate_fx_volatility(self, rates: Dict[str, Any]) -> float:
        """Calculate FX volatility index"""
        volatilities = []
        for currency_pair, data in rates.items():
            if 'volatility' in data:
                volatilities.append(data['volatility'])
                
        return round(sum(volatilities) / len(volatilities) if volatilities else 0, 2)
        
    def _assess_fx_market_impact(self, rates: Dict[str, Any]) -> str:
        """Assess FX market impact on European markets"""
        eur_usd = rates.get('EUR_USD', {}).get('current', 1.09)
        
        if eur_usd > 1.15:
            return "NEGATIVE_FOR_EXPORTS"
        elif eur_usd > 1.05:
            return "NEUTRAL"
        else:
            return "POSITIVE_FOR_EXPORTS"
            
    def _assess_money_growth(self, growth_rate: float, indicator: str) -> str:
        """Assess money supply growth"""
        if 'm3' in indicator:
            target_center = 5.0
        else:
            target_center = 3.0
            
        if abs(growth_rate - target_center) < 1:
            return "ON_TARGET"
        elif growth_rate > target_center + 2:
            return "EXCESSIVE"
        elif growth_rate < target_center - 2:
            return "INSUFFICIENT"
        else:
            return "MODERATE_DEVIATION"
            
    def _determine_monetary_stance(self, indicators: Dict[str, Any]) -> str:
        """Determine overall monetary policy stance"""
        # This would analyze multiple monetary indicators
        return "RESTRICTIVE"  # Simplified for demo
        
    def _assess_liquidity_conditions(self, indicators: Dict[str, Any]) -> str:
        """Assess liquidity conditions"""
        # Analyze money supply growth patterns
        return "ADEQUATE"  # Simplified for demo
        
    def _assess_inflation_environment(self, inflation: float) -> str:
        """Assess inflation environment"""
        ecb_target = 2.0
        
        if inflation > ecb_target + 1:
            return "ABOVE_TARGET"
        elif inflation > ecb_target + 0.5:
            return "MODERATELY_ABOVE_TARGET"
        elif inflation < ecb_target - 0.5:
            return "BELOW_TARGET"
        else:
            return "ON_TARGET"
            
    def _analyze_inflation_policy_implications(self, inflation: Dict[str, Any]) -> List[str]:
        """Analyze inflation policy implications"""
        implications = []
        
        headline = inflation.get('headline', {}).get('current', 0)
        if headline > 2.5:
            implications.append("TIGHTENING_PRESSURE")
        elif headline < 1.5:
            implications.append("EASING_PRESSURE")
        else:
            implications.append("POLICY_NEUTRAL")
            
        return implications
        
    def _assess_economic_indicator(self, indicator: str, value: float) -> str:
        """Assess individual economic indicator"""
        if indicator == 'gdp_growth':
            if value > 2:
                return "STRONG"
            elif value > 0.5:
                return "MODERATE"
            elif value > -0.5:
                return "WEAK"
            else:
                return "RECESSION"
        elif indicator == 'unemployment':
            if value < 5:
                return "LOW"
            elif value < 7:
                return "MODERATE"
            elif value < 10:
                return "HIGH"
            else:
                return "VERY_HIGH"
        return "UNKNOWN"
        
    def _assess_economic_health(self, indicators: Dict[str, Any]) -> str:
        """Assess overall economic health"""
        gdp_growth = indicators.get('gdp_growth', {}).get('current', 0)
        unemployment = indicators.get('unemployment', {}).get('current', 10)
        
        if gdp_growth > 1.5 and unemployment < 6:
            return "HEALTHY"
        elif gdp_growth > 0 and unemployment < 8:
            return "MODERATE"
        else:
            return "WEAK"
            
    def _determine_cycle_position(self, indicators: Dict[str, Any]) -> str:
        """Determine economic cycle position"""
        # Simplified cycle analysis
        gdp_growth = indicators.get('gdp_growth', {}).get('current', 0)
        
        if gdp_growth > 2:
            return "EXPANSION"
        elif gdp_growth > 0:
            return "SLOW_GROWTH"
        else:
            return "CONTRACTION"
            
    def _calculate_macro_health_score(self, interest_rates: Dict, inflation: Dict, economic: Dict) -> Dict[str, Any]:
        """Calculate comprehensive macroeconomic health score"""
        score = 0
        max_score = 100
        
        # Interest rate environment (25 points)
        rate_env = interest_rates.get('rate_environment', '')
        if rate_env in ['NEUTRAL', 'NEUTRAL_TO_RESTRICTIVE']:
            score += 20
        elif rate_env in ['ACCOMMODATIVE', 'RESTRICTIVE']:
            score += 15
        else:
            score += 10
            
        # Inflation environment (25 points)
        inflation_env = inflation.get('environment', '')
        if inflation_env == 'ON_TARGET':
            score += 25
        elif inflation_env in ['MODERATELY_ABOVE_TARGET', 'BELOW_TARGET']:
            score += 15
        else:
            score += 5
            
        # Economic health (25 points)
        econ_health = economic.get('economic_health', '')
        if econ_health == 'HEALTHY':
            score += 25
        elif econ_health == 'MODERATE':
            score += 15
        else:
            score += 5
            
        # Stability factors (25 points)
        score += 15  # Base stability score for Euro area
        
        return {
            'total_score': score,
            'max_score': max_score,
            'score_percentage': round((score / max_score) * 100, 1),
            'rating': self._get_macro_rating(score),
            'key_factors': ['monetary_policy', 'inflation_control', 'economic_growth', 'stability']
        }
        
    def _get_macro_rating(self, score: int) -> str:
        """Get macroeconomic rating"""
        if score >= 80:
            return "EXCELLENT"
        elif score >= 65:
            return "GOOD"
        elif score >= 50:
            return "FAIR"
        elif score >= 35:
            return "POOR"
        else:
            return "VERY_POOR"
            
    def _analyze_market_implications(self, interest_rates: Dict, inflation: Dict, fx: Dict) -> Dict[str, Any]:
        """Analyze market implications of macro data"""
        implications = {
            'equity_markets': [],
            'bond_markets': [],
            'currency_markets': [],
            'sector_impacts': []
        }
        
        # Interest rate implications
        rate_trend = interest_rates.get('rate_trend', 'STABLE')
        if rate_trend == 'RISING':
            implications['equity_markets'].append('PRESSURE_ON_VALUATIONS')
            implications['bond_markets'].append('FALLING_PRICES')
        elif rate_trend == 'FALLING':
            implications['equity_markets'].append('SUPPORTIVE_FOR_GROWTH')
            implications['bond_markets'].append('RISING_PRICES')
            
        # Inflation implications
        inflation_env = inflation.get('environment', '')
        if inflation_env == 'ABOVE_TARGET':
            implications['sector_impacts'].append('COMMODITIES_POSITIVE')
            implications['sector_impacts'].append('REAL_ESTATE_MIXED')
            
        # FX implications
        eur_strength = fx.get('eur_strength_index', {}).get('assessment', '')
        if eur_strength in ['STRONG', 'MODERATELY_STRONG']:
            implications['sector_impacts'].append('EXPORTERS_PRESSURE')
            implications['sector_impacts'].append('IMPORTERS_BENEFIT')
            
        return implications
        
    async def run(self):
        """Main service loop"""
        logger.info("ECB Macroeconomics Service started successfully")
        
        while self.running:
            try:
                # Update macroeconomic data
                macro_data = await self.get_comprehensive_macro_data()
                logger.info("Macroeconomic data update completed",
                          success=macro_data.get('success', False),
                          timestamp=datetime.now().isoformat())
                          
                # Macroeconomic data updates every 4 hours
                await asyncio.sleep(14400)
                
            except Exception as e:
                logger.error("Error in service loop", error=str(e))
                await asyncio.sleep(1800)  # Wait 30 minutes on error
                
    async def shutdown(self):
        """Shutdown service"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("ECB Macroeconomics Service stopped")

async def main():
    """Main entry point"""
    service = ECBMacroeconomicsService()
    
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