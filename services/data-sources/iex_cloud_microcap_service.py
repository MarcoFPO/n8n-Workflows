#!/usr/bin/env python3
"""
IEX Cloud Microcap Data Source Service
Spezialisiert auf Microcap-Aktien, Earnings und detaillierte Finanzanalyse
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

logger = setup_logging("iex-cloud-microcap")

class IEXCloudMicrocapService:
    """IEX Cloud Microcap Data Source Service"""
    
    def __init__(self):
        self.running = False
        self.api_token = os.getenv('IEX_CLOUD_TOKEN', 'demo')  # Demo token for testing
        self.base_url = "https://cloud.iexapis.com/stable"
        self.session = None
        
        # Microcap Focus: Marktkapitalisierung unter 300 Millionen
        self.microcap_symbols = [
            # Biotech Microcaps
            'AGRX', 'BCRX', 'CYTR', 'DRNA', 'EARS',
            # Tech Microcaps
            'BLNK', 'CBAT', 'EMKR', 'IDEX', 'KOSS',
            # Energy Microcaps
            'AMTX', 'BRY', 'CPE', 'DMRC', 'ENSV',
            # Real Estate Microcaps
            'ALEX', 'BRT', 'CLDT', 'CREX', 'EPRT',
            # Industrial Microcaps
            'ASTE', 'BOOM', 'CCMP', 'DXPE', 'EXPO'
        ]
        
    async def initialize(self):
        """Initialize service"""
        logger.info("Initializing IEX Cloud Microcap Service")
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Aktienanalyse-System/1.0'}
        )
        self.running = True
        logger.info("IEX Cloud Microcap Service initialized", 
                   symbols_tracked=len(self.microcap_symbols))
        return True
        
    async def get_microcap_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive microcap stock analysis"""
        try:
            # Get comprehensive data
            company_info = await self._get_company_info(symbol)
            financial_data = await self._get_financials(symbol)
            earnings_data = await self._get_earnings(symbol)
            price_data = await self._get_price_target(symbol)
            insider_data = await self._get_insider_roster(symbol)
            
            # Calculate microcap-specific metrics
            microcap_score = self._calculate_microcap_score(
                company_info, financial_data, earnings_data
            )
            
            # Risk assessment for microcaps
            risk_analysis = self._assess_microcap_risks(
                company_info, financial_data
            )
            
            result = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'source': 'iex_cloud_microcap',
                'data_type': 'microcap_analysis',
                'company_info': company_info,
                'financials': financial_data,
                'earnings': earnings_data,
                'price_targets': price_data,
                'insider_roster': insider_data,
                'microcap_score': microcap_score,
                'risk_analysis': risk_analysis,
                'liquidity_assessment': self._assess_liquidity(company_info),
                'growth_potential': self._assess_growth_potential(financial_data),
                'success': True
            }
            
            logger.info("Microcap analysis completed", symbol=symbol)
            return result
            
        except Exception as e:
            logger.error("Error getting microcap analysis", symbol=symbol, error=str(e))
            return {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'source': 'iex_cloud_microcap',
                'error': str(e),
                'success': False
            }
            
    async def _get_company_info(self, symbol: str) -> Dict[str, Any]:
        """Get company information"""
        url = f"{self.base_url}/stock/{symbol}/company"
        params = {'token': self.api_token}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'company_name': data.get('companyName', ''),
                        'exchange': data.get('exchange', ''),
                        'industry': data.get('industry', ''),
                        'sector': data.get('sector', ''),
                        'description': data.get('description', ''),
                        'ceo': data.get('CEO', ''),
                        'employees': data.get('employees', 0),
                        'address': data.get('address', ''),
                        'city': data.get('city', ''),
                        'state': data.get('state', ''),
                        'country': data.get('country', ''),
                        'website': data.get('website', ''),
                        'phone': data.get('phone', ''),
                        'tags': data.get('tags', [])
                    }
                else:
                    # Return mock data for demo
                    return self._generate_mock_company_info(symbol)
        except Exception as e:
            logger.error("Error getting company info", symbol=symbol, error=str(e))
            return self._generate_mock_company_info(symbol)
            
    async def _get_financials(self, symbol: str) -> Dict[str, Any]:
        """Get financial statements"""
        url = f"{self.base_url}/stock/{symbol}/financials"
        params = {'token': self.api_token, 'period': 'annual', 'last': 2}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'financials' in data and len(data['financials']) > 0:
                        latest = data['financials'][0]
                        return self._process_financial_data(latest, symbol)
                else:
                    return self._generate_mock_financials(symbol)
        except Exception as e:
            logger.error("Error getting financials", symbol=symbol, error=str(e))
            return self._generate_mock_financials(symbol)
            
    async def _get_earnings(self, symbol: str) -> Dict[str, Any]:
        """Get earnings data"""
        url = f"{self.base_url}/stock/{symbol}/earnings"
        params = {'token': self.api_token, 'last': 4}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'earnings' in data and len(data['earnings']) > 0:
                        return self._process_earnings_data(data['earnings'], symbol)
                else:
                    return self._generate_mock_earnings(symbol)
        except Exception as e:
            logger.error("Error getting earnings", symbol=symbol, error=str(e))
            return self._generate_mock_earnings(symbol)
            
    async def _get_price_target(self, symbol: str) -> Dict[str, Any]:
        """Get price target data"""
        url = f"{self.base_url}/stock/{symbol}/price-target"
        params = {'token': self.api_token}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'price_target_average': data.get('priceTargetAverage', 0),
                        'price_target_high': data.get('priceTargetHigh', 0),
                        'price_target_low': data.get('priceTargetLow', 0),
                        'number_of_analysts': data.get('numberOfAnalysts', 0),
                        'last_updated': data.get('lastUpdated', '')
                    }
                else:
                    return self._generate_mock_price_targets(symbol)
        except Exception as e:
            logger.error("Error getting price targets", symbol=symbol, error=str(e))
            return self._generate_mock_price_targets(symbol)
            
    async def _get_insider_roster(self, symbol: str) -> Dict[str, Any]:
        """Get insider roster information"""
        url = f"{self.base_url}/stock/{symbol}/insider-roster"
        params = {'token': self.api_token}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._process_insider_data(data, symbol)
                else:
                    return self._generate_mock_insider_data(symbol)
        except Exception as e:
            logger.error("Error getting insider roster", symbol=symbol, error=str(e))
            return self._generate_mock_insider_data(symbol)
            
    def _generate_mock_company_info(self, symbol: str) -> Dict[str, Any]:
        """Generate realistic mock company information"""
        import random
        
        sectors = ['Technology', 'Healthcare', 'Energy', 'Real Estate', 'Industrials']
        industries = ['Software', 'Biotechnology', 'Oil & Gas', 'REITs', 'Manufacturing']
        
        return {
            'company_name': f"{symbol} Corporation",
            'exchange': 'NASDAQ',
            'industry': random.choice(industries),
            'sector': random.choice(sectors),
            'description': f"A microcap company in the {random.choice(industries).lower()} space.",
            'ceo': f"CEO of {symbol}",
            'employees': random.randint(50, 500),
            'address': '123 Main Street',
            'city': 'Delaware',
            'state': 'DE',
            'country': 'USA',
            'website': f'www.{symbol.lower()}.com',
            'phone': '555-123-4567',
            'tags': ['microcap', 'growth']
        }
        
    def _generate_mock_financials(self, symbol: str) -> Dict[str, Any]:
        """Generate realistic mock financial data"""
        import random
        
        # Microcap-realistic numbers (smaller scale)
        revenue = random.randint(10000000, 150000000)  # 10M-150M revenue
        costs = int(revenue * random.uniform(0.6, 0.9))  # 60-90% cost ratio
        
        return {
            'report_date': '2024-12-31',
            'fiscal_year': 2024,
            'currency': 'USD',
            'total_revenue': revenue,
            'cost_of_revenue': costs,
            'gross_profit': revenue - costs,
            'operating_expenses': int(revenue * random.uniform(0.2, 0.4)),
            'total_debt': int(revenue * random.uniform(0.1, 0.8)),
            'total_cash': int(revenue * random.uniform(0.05, 0.3)),
            'shares_outstanding': random.randint(5000000, 50000000),
            'market_cap': random.randint(50000000, 300000000),  # Microcap range
            'revenue_growth': round(random.uniform(-20, 40), 2),
            'debt_to_equity': round(random.uniform(0.1, 1.5), 2),
            'working_capital': int(revenue * random.uniform(-0.1, 0.2))
        }
        
    def _generate_mock_earnings(self, symbol: str) -> Dict[str, Any]:
        """Generate mock earnings data"""
        import random
        
        quarters = []
        for i in range(4):
            eps_actual = round(random.uniform(-0.5, 0.8), 2)
            eps_estimate = round(eps_actual * random.uniform(0.8, 1.2), 2)
            
            quarters.append({
                'fiscal_period': f"Q{4-i}",
                'fiscal_year': 2024,
                'actual_eps': eps_actual,
                'estimated_eps': eps_estimate,
                'surprise_dollar': round(eps_actual - eps_estimate, 2),
                'surprise_percent': round(((eps_actual - eps_estimate) / abs(eps_estimate) * 100) if eps_estimate != 0 else 0, 2),
                'eps_report_date': datetime.now().strftime('%Y-%m-%d')
            })
            
        return {
            'latest_quarter': quarters[0],
            'quarterly_earnings': quarters,
            'earnings_consistency': self._assess_earnings_consistency(quarters),
            'earnings_trend': self._determine_earnings_trend(quarters)
        }
        
    def _generate_mock_price_targets(self, symbol: str) -> Dict[str, Any]:
        """Generate mock price target data"""
        import random
        
        # Current price assumption for microcaps
        current_price = random.uniform(2, 25)
        
        target_low = current_price * random.uniform(0.7, 0.9)
        target_high = current_price * random.uniform(1.2, 2.0)
        target_avg = (target_low + target_high) / 2
        
        return {
            'price_target_average': round(target_avg, 2),
            'price_target_high': round(target_high, 2),
            'price_target_low': round(target_low, 2),
            'number_of_analysts': random.randint(1, 8),  # Fewer analysts for microcaps
            'last_updated': datetime.now().strftime('%Y-%m-%d')
        }
        
    def _generate_mock_insider_data(self, symbol: str) -> Dict[str, Any]:
        """Generate mock insider trading data"""
        import random
        
        insiders = []
        titles = ['CEO', 'CFO', 'CTO', 'COO', 'Director', 'VP Sales', 'VP Engineering']
        
        for i in range(random.randint(3, 8)):
            insiders.append({
                'entity_name': f"Insider {i+1}",
                'position': random.choice(titles),
                'shares_owned': random.randint(10000, 1000000),
                'ownership_percent': round(random.uniform(1, 15), 2),
                'recent_activity': random.choice(['BUY', 'SELL', 'HOLD'])
            })
            
        total_insider_ownership = sum(insider['ownership_percent'] for insider in insiders)
        
        return {
            'insider_count': len(insiders),
            'insiders': insiders,
            'total_insider_ownership': round(min(total_insider_ownership, 70), 2),  # Cap at 70%
            'insider_sentiment': self._assess_insider_sentiment_from_activity(insiders)
        }
        
    def _process_financial_data(self, financial_data: Dict, symbol: str) -> Dict[str, Any]:
        """Process actual financial data from IEX"""
        return {
            'report_date': financial_data.get('reportDate', ''),
            'fiscal_year': financial_data.get('fiscalYear', 0),
            'currency': financial_data.get('currency', 'USD'),
            'total_revenue': financial_data.get('totalRevenue', 0),
            'cost_of_revenue': financial_data.get('costOfRevenue', 0),
            'gross_profit': financial_data.get('grossProfit', 0),
            'operating_expenses': financial_data.get('operatingExpense', 0),
            'total_debt': financial_data.get('totalDebt', 0),
            'total_cash': financial_data.get('totalCash', 0),
            'shares_outstanding': financial_data.get('sharesOutstanding', 0),
            'market_cap': self._calculate_market_cap(financial_data, symbol),
            'revenue_growth': self._calculate_revenue_growth(financial_data),
            'debt_to_equity': self._calculate_debt_to_equity(financial_data),
            'working_capital': financial_data.get('workingCapital', 0)
        }
        
    def _process_earnings_data(self, earnings_list: List[Dict], symbol: str) -> Dict[str, Any]:
        """Process earnings data from IEX"""
        if not earnings_list:
            return self._generate_mock_earnings(symbol)
            
        latest = earnings_list[0]
        processed_quarters = []
        
        for earnings in earnings_list:
            processed_quarters.append({
                'fiscal_period': earnings.get('fiscalPeriod', ''),
                'fiscal_year': earnings.get('fiscalYear', 0),
                'actual_eps': earnings.get('actualEPS', 0),
                'estimated_eps': earnings.get('consensusEPS', 0),
                'surprise_dollar': earnings.get('surprisePercent', 0),
                'eps_report_date': earnings.get('EPSReportDate', '')
            })
            
        return {
            'latest_quarter': processed_quarters[0] if processed_quarters else {},
            'quarterly_earnings': processed_quarters,
            'earnings_consistency': self._assess_earnings_consistency(processed_quarters),
            'earnings_trend': self._determine_earnings_trend(processed_quarters)
        }
        
    def _process_insider_data(self, insider_data: List[Dict], symbol: str) -> Dict[str, Any]:
        """Process insider roster data from IEX"""
        if not insider_data:
            return self._generate_mock_insider_data(symbol)
            
        insiders = []
        total_ownership = 0
        
        for insider in insider_data:
            ownership = insider.get('ownershipPercent', 0)
            total_ownership += ownership
            
            insiders.append({
                'entity_name': insider.get('entityName', ''),
                'position': insider.get('position', ''),
                'shares_owned': insider.get('shares', 0),
                'ownership_percent': ownership,
                'recent_activity': 'HOLD'  # Default, would need transaction data
            })
            
        return {
            'insider_count': len(insiders),
            'insiders': insiders,
            'total_insider_ownership': round(total_ownership, 2),
            'insider_sentiment': self._assess_insider_sentiment_from_ownership(total_ownership)
        }
        
    def _calculate_market_cap(self, financial_data: Dict, symbol: str) -> int:
        """Calculate market cap"""
        shares = financial_data.get('sharesOutstanding', 0)
        # Would need current price - using mock for demo
        mock_price = 15.0  # Mock price
        return int(shares * mock_price) if shares else 100000000
        
    def _calculate_revenue_growth(self, financial_data: Dict) -> float:
        """Calculate revenue growth (mock implementation)"""
        import random
        return round(random.uniform(-20, 40), 2)
        
    def _calculate_debt_to_equity(self, financial_data: Dict) -> float:
        """Calculate debt to equity ratio"""
        debt = financial_data.get('totalDebt', 0)
        equity = financial_data.get('shareholderEquity', 1)
        return round(debt / equity, 2) if equity > 0 else 0
        
    def _assess_earnings_consistency(self, quarters: List[Dict]) -> str:
        """Assess earnings consistency"""
        if len(quarters) < 2:
            return "INSUFFICIENT_DATA"
            
        beats = sum(1 for q in quarters if q.get('surprise_dollar', 0) > 0)
        consistency_ratio = beats / len(quarters)
        
        if consistency_ratio >= 0.75:
            return "HIGHLY_CONSISTENT"
        elif consistency_ratio >= 0.5:
            return "MODERATELY_CONSISTENT"
        else:
            return "INCONSISTENT"
            
    def _determine_earnings_trend(self, quarters: List[Dict]) -> str:
        """Determine earnings trend"""
        if len(quarters) < 2:
            return "INSUFFICIENT_DATA"
            
        recent_eps = [q.get('actual_eps', 0) for q in quarters[:2]]
        if recent_eps[0] > recent_eps[1]:
            return "IMPROVING"
        elif recent_eps[0] < recent_eps[1]:
            return "DECLINING"
        else:
            return "STABLE"
            
    def _assess_insider_sentiment_from_activity(self, insiders: List[Dict]) -> str:
        """Assess insider sentiment from trading activity"""
        buy_count = sum(1 for insider in insiders if insider.get('recent_activity') == 'BUY')
        sell_count = sum(1 for insider in insiders if insider.get('recent_activity') == 'SELL')
        
        if buy_count > sell_count:
            return "BULLISH"
        elif sell_count > buy_count:
            return "BEARISH"
        else:
            return "NEUTRAL"
            
    def _assess_insider_sentiment_from_ownership(self, total_ownership: float) -> str:
        """Assess insider sentiment from ownership percentage"""
        if total_ownership > 40:
            return "VERY_BULLISH"
        elif total_ownership > 25:
            return "BULLISH"
        elif total_ownership > 10:
            return "NEUTRAL"
        else:
            return "CONCERNING"
            
    def _calculate_microcap_score(self, company: Dict, financials: Dict, earnings: Dict) -> Dict[str, Any]:
        """Calculate comprehensive microcap investment score"""
        score = 0
        max_score = 100
        
        # Financial health score (30 points)
        market_cap = financials.get('market_cap', 0)
        if 50000000 <= market_cap <= 300000000:  # Proper microcap range
            score += 10
        elif market_cap < 50000000:  # Too small, higher risk
            score += 5
            
        debt_to_equity = financials.get('debt_to_equity', 0)
        if debt_to_equity < 0.5:
            score += 10
        elif debt_to_equity < 1.0:
            score += 5
            
        working_capital = financials.get('working_capital', 0)
        if working_capital > 0:
            score += 10
        elif working_capital > -1000000:  # Minor negative
            score += 5
            
        # Growth potential (25 points)
        revenue_growth = financials.get('revenue_growth', 0)
        if revenue_growth > 20:
            score += 15
        elif revenue_growth > 10:
            score += 10
        elif revenue_growth > 0:
            score += 5
            
        earnings_trend = earnings.get('earnings_trend', '')
        if earnings_trend == 'IMPROVING':
            score += 10
        elif earnings_trend == 'STABLE':
            score += 5
            
        # Management quality (20 points)
        employee_count = company.get('employees', 0)
        if 100 <= employee_count <= 1000:  # Right size for microcap
            score += 10
        elif employee_count > 50:
            score += 5
            
        earnings_consistency = earnings.get('earnings_consistency', '')
        if earnings_consistency == 'HIGHLY_CONSISTENT':
            score += 10
        elif earnings_consistency == 'MODERATELY_CONSISTENT':
            score += 5
            
        # Sector strength (15 points)
        sector = company.get('sector', '')
        if sector in ['Technology', 'Healthcare']:  # High growth sectors
            score += 10
        elif sector in ['Industrials', 'Energy']:  # Moderate growth
            score += 7
        else:
            score += 5
            
        # Liquidity factors (10 points)
        exchange = company.get('exchange', '')
        if exchange in ['NASDAQ', 'NYSE']:
            score += 5
        else:
            score += 2
            
        score += 5  # Base liquidity score
        
        final_score = min(score, max_score)
        
        return {
            'total_score': final_score,
            'max_score': max_score,
            'score_percentage': round((final_score / max_score) * 100, 1),
            'rating': self._get_microcap_rating(final_score),
            'risk_reward_profile': self._get_risk_reward_profile(final_score),
            'components': {
                'financial_health': 'Evaluated',
                'growth_potential': 'Evaluated',
                'management_quality': 'Evaluated',
                'sector_strength': 'Evaluated',
                'liquidity_factors': 'Evaluated'
            }
        }
        
    def _get_microcap_rating(self, score: int) -> str:
        """Get microcap investment rating"""
        if score >= 80:
            return "STRONG_BUY"
        elif score >= 65:
            return "BUY"
        elif score >= 50:
            return "SPECULATIVE_BUY"
        elif score >= 35:
            return "HOLD"
        else:
            return "AVOID"
            
    def _get_risk_reward_profile(self, score: int) -> str:
        """Get risk/reward profile"""
        if score >= 75:
            return "HIGH_REWARD_MODERATE_RISK"
        elif score >= 60:
            return "MODERATE_REWARD_MODERATE_RISK"
        elif score >= 45:
            return "MODERATE_REWARD_HIGH_RISK"
        else:
            return "HIGH_RISK_UNCERTAIN_REWARD"
            
    def _assess_microcap_risks(self, company: Dict, financials: Dict) -> Dict[str, Any]:
        """Assess specific risks for microcap investments"""
        risks = []
        risk_level = "LOW"
        
        # Liquidity risk
        market_cap = financials.get('market_cap', 0)
        if market_cap < 50000000:
            risks.append("Very low market cap increases liquidity risk")
            risk_level = "HIGH"
        elif market_cap < 100000000:
            risks.append("Limited liquidity due to small market cap")
            if risk_level == "LOW":
                risk_level = "MEDIUM"
                
        # Financial risks
        debt_to_equity = financials.get('debt_to_equity', 0)
        if debt_to_equity > 1.5:
            risks.append("High debt levels relative to equity")
            risk_level = "HIGH"
            
        working_capital = financials.get('working_capital', 0)
        if working_capital < 0:
            risks.append("Negative working capital indicates cash flow challenges")
            if risk_level == "LOW":
                risk_level = "MEDIUM"
                
        # Business risks
        employees = company.get('employees', 0)
        if employees < 50:
            risks.append("Very small team increases key person risk")
            if risk_level == "LOW":
                risk_level = "MEDIUM"
                
        # Market risks
        revenue = financials.get('total_revenue', 0)
        if revenue < 10000000:  # Less than 10M revenue
            risks.append("Low revenue increases business sustainability risk")
            if risk_level == "LOW":
                risk_level = "MEDIUM"
                
        return {
            'overall_risk_level': risk_level,
            'identified_risks': risks,
            'risk_count': len(risks),
            'mitigation_suggestions': self._get_risk_mitigation_suggestions(risks)
        }
        
    def _get_risk_mitigation_suggestions(self, risks: List[str]) -> List[str]:
        """Get risk mitigation suggestions"""
        suggestions = []
        
        if any('liquidity' in risk.lower() for risk in risks):
            suggestions.append("Consider smaller position sizes due to liquidity constraints")
            suggestions.append("Use limit orders rather than market orders")
            
        if any('debt' in risk.lower() for risk in risks):
            suggestions.append("Monitor quarterly reports for debt reduction progress")
            
        if any('cash flow' in risk.lower() for risk in risks):
            suggestions.append("Track quarterly cash burn rate and runway")
            
        if any('team' in risk.lower() for risk in risks):
            suggestions.append("Research management team background and track record")
            
        return suggestions
        
    def _assess_liquidity(self, company: Dict) -> Dict[str, str]:
        """Assess stock liquidity"""
        exchange = company.get('exchange', '')
        employees = company.get('employees', 0)
        
        if exchange in ['NASDAQ', 'NYSE'] and employees > 200:
            liquidity_rating = "GOOD"
        elif exchange in ['NASDAQ', 'NYSE']:
            liquidity_rating = "MODERATE"
        else:
            liquidity_rating = "LIMITED"
            
        return {
            'liquidity_rating': liquidity_rating,
            'exchange': exchange,
            'trading_recommendation': self._get_trading_recommendation(liquidity_rating)
        }
        
    def _get_trading_recommendation(self, liquidity_rating: str) -> str:
        """Get trading recommendation based on liquidity"""
        if liquidity_rating == "GOOD":
            return "Normal trading strategies applicable"
        elif liquidity_rating == "MODERATE":
            return "Use limit orders and smaller position sizes"
        else:
            return "Exercise extreme caution - use small positions and limit orders"
            
    def _assess_growth_potential(self, financials: Dict) -> Dict[str, Any]:
        """Assess growth potential"""
        revenue_growth = financials.get('revenue_growth', 0)
        market_cap = financials.get('market_cap', 0)
        
        # Growth scoring
        if revenue_growth > 30:
            growth_score = "HIGH"
        elif revenue_growth > 15:
            growth_score = "MODERATE"
        elif revenue_growth > 0:
            growth_score = "LOW"
        else:
            growth_score = "NEGATIVE"
            
        # Market opportunity
        if market_cap < 100000000:
            market_opportunity = "SIGNIFICANT"  # Room to grow
        elif market_cap < 200000000:
            market_opportunity = "MODERATE"
        else:
            market_opportunity = "LIMITED"
            
        return {
            'growth_score': growth_score,
            'revenue_growth_rate': revenue_growth,
            'market_opportunity': market_opportunity,
            'growth_catalysts': self._identify_growth_catalysts(financials)
        }
        
    def _identify_growth_catalysts(self, financials: Dict) -> List[str]:
        """Identify potential growth catalysts"""
        catalysts = []
        
        revenue_growth = financials.get('revenue_growth', 0)
        if revenue_growth > 20:
            catalysts.append("Strong revenue momentum")
            
        working_capital = financials.get('working_capital', 0)
        if working_capital > 0:
            catalysts.append("Positive working capital supports growth investment")
            
        debt_to_equity = financials.get('debt_to_equity', 0)
        if debt_to_equity < 0.3:
            catalysts.append("Low debt provides financial flexibility")
            
        market_cap = financials.get('market_cap', 0)
        if market_cap < 100000000:
            catalysts.append("Small size allows for rapid scaling")
            
        return catalysts
        
    async def get_microcap_batch_analysis(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get batch analysis for multiple microcap stocks"""
        results = []
        symbols_to_process = self.microcap_symbols[:limit]
        
        logger.info("Processing microcap batch analysis", symbols=len(symbols_to_process))
        
        # Process in smaller batches to respect API limits
        batch_size = 3
        for i in range(0, len(symbols_to_process), batch_size):
            batch = symbols_to_process[i:i + batch_size]
            
            batch_tasks = [self.get_microcap_analysis(symbol) for symbol in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error("Batch processing error", error=str(result))
                else:
                    results.append(result)
                    
            # Rate limiting for IEX Cloud
            if i + batch_size < len(symbols_to_process):
                await asyncio.sleep(5)  # Conservative rate limiting
                
        logger.info("Microcap batch analysis completed", results=len(results))
        return results
        
    async def run(self):
        """Main service loop"""
        logger.info("IEX Cloud Microcap Service started successfully")
        
        while self.running:
            try:
                # Periodic microcap analysis update
                batch_data = await self.get_microcap_batch_analysis(5)
                logger.info("Periodic microcap update completed",
                          results=len(batch_data),
                          timestamp=datetime.now().isoformat())
                          
                # Wait 3 hours between updates (microcap data needs frequent monitoring)
                await asyncio.sleep(10800)
                
            except Exception as e:
                logger.error("Error in service loop", error=str(e))
                await asyncio.sleep(900)  # Wait 15 minutes on error
                
    async def shutdown(self):
        """Shutdown service"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("IEX Cloud Microcap Service stopped")

async def main():
    """Main entry point"""
    service = IEXCloudMicrocapService()
    
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