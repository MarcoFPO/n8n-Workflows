#!/usr/bin/env python3
"""
Finnhub Fundamentals Data Source Service
Spezialisiert auf Fundamentaldaten, Earnings und Unternehmensdaten
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, List, Any, Optional

# Add path for logging

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/opt/aktienanalyse-ökosystem/shared') -> Import Manager
from logging_config import setup_logging

logger = setup_logging("finnhub-fundamentals")

class FinnhubFundamentalsService:
    """Finnhub Fundamentals Data Source Service"""
    
    def __init__(self):
        self.running = False
        self.api_key = os.getenv('FINNHUB_API_KEY', 'demo')  # Demo key for testing
        self.base_url = "https://finnhub.io/api/v1"
        self.session = None
        
        # Focus on companies with strong fundamentals
        self.target_symbols = [
            # Tech fundamentals
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
            # Growth stocks with solid fundamentals  
            'NVDA', 'TSLA', 'NFLX', 'CRM', 'ADBE',
            # European stocks (for global perspective)
            'ASML', 'SAP', 'NESN.SW', 'NOVN.SW', 'ROG.SW',
            # Emerging small-caps with fundamentals
            'PLTR', 'SNOW', 'DDOG', 'NET', 'MDB'
        ]
        
    async def initialize(self):
        """Initialize service"""
        logger.info("Initializing Finnhub Fundamentals Service")
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Aktienanalyse-System/1.0',
                'X-Finnhub-Token': self.api_key
            }
        )
        self.running = True
        logger.info("Finnhub Fundamentals Service initialized", 
                   symbols_tracked=len(self.target_symbols))
        return True
        
    async def get_comprehensive_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive fundamental analysis"""
        try:
            # Get multiple fundamental data points
            company_profile = await self._get_company_profile(symbol)
            financial_metrics = await self._get_basic_financials(symbol)
            earnings_data = await self._get_earnings(symbol)
            recommendation = await self._get_recommendation_trends(symbol)
            insider_trading = await self._get_insider_trading(symbol)
            
            # Combine all data
            result = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'source': 'finnhub_fundamentals',
                'data_type': 'comprehensive_fundamentals',
                'company_profile': company_profile,
                'financial_metrics': financial_metrics,
                'earnings': earnings_data,
                'recommendations': recommendation,
                'insider_activity': insider_trading,
                'fundamental_score': self._calculate_fundamental_score(
                    company_profile, financial_metrics, earnings_data
                ),
                'success': True
            }
            
            logger.info("Comprehensive fundamentals retrieved", symbol=symbol)
            return result
            
        except Exception as e:
            logger.error("Error getting fundamentals", symbol=symbol, error=str(e))
            return {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'source': 'finnhub_fundamentals',
                'error': str(e),
                'success': False
            }
            
    async def _get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Get company profile data"""
        url = f"{self.base_url}/stock/profile2"
        params = {'symbol': symbol}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'name': data.get('name', ''),
                        'country': data.get('country', ''),
                        'currency': data.get('currency', ''),
                        'exchange': data.get('exchange', ''),
                        'ipo_date': data.get('ipo', ''),
                        'market_cap': data.get('marketCapitalization', 0),
                        'shares_outstanding': data.get('shareOutstanding', 0),
                        'industry': data.get('finnhubIndustry', ''),
                        'website': data.get('weburl', ''),
                        'logo': data.get('logo', '')
                    }
                else:
                    logger.warning(f"Profile API error {response.status}", symbol=symbol)
                    return {}
        except Exception as e:
            logger.error("Error getting company profile", symbol=symbol, error=str(e))
            return {}
            
    async def _get_basic_financials(self, symbol: str) -> Dict[str, Any]:
        """Get basic financial metrics"""
        url = f"{self.base_url}/stock/metric"
        params = {'symbol': symbol, 'metric': 'all'}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    metrics = data.get('metric', {})
                    
                    return {
                        # Valuation metrics
                        'pe_ratio': metrics.get('peBasicExclExtraTTM', 0),
                        'pe_forward': metrics.get('peNormalizedAnnual', 0),
                        'peg_ratio': metrics.get('pegRatio', 0),
                        'price_to_book': metrics.get('pbAnnual', 0),
                        'price_to_sales': metrics.get('psAnnual', 0),
                        'ev_to_ebitda': metrics.get('evToEbitda', 0),
                        
                        # Profitability metrics
                        'roe': metrics.get('roeRfy', 0),
                        'roa': metrics.get('roaRfy', 0),
                        'roi': metrics.get('roiAnnual', 0),
                        'gross_margin': metrics.get('grossMarginAnnual', 0),
                        'operating_margin': metrics.get('operatingMarginAnnual', 0),
                        'net_margin': metrics.get('netProfitMarginAnnual', 0),
                        
                        # Growth metrics
                        'revenue_growth': metrics.get('revenueGrowthAnnual', 0),
                        'earnings_growth': metrics.get('epsGrowthAnnual', 0),
                        'book_value_growth': metrics.get('bookValueGrowthAnnual', 0),
                        
                        # Financial strength
                        'debt_to_equity': metrics.get('totalDebtToEquity', 0),
                        'current_ratio': metrics.get('currentRatioAnnual', 0),
                        'quick_ratio': metrics.get('quickRatioAnnual', 0),
                        
                        # Dividend metrics
                        'dividend_yield': metrics.get('dividendYieldIndicatedAnnual', 0),
                        'payout_ratio': metrics.get('payoutRatioAnnual', 0),
                        
                        # Market metrics
                        'beta': metrics.get('beta', 0),
                        '52_week_high': metrics.get('52WeekHigh', 0),
                        '52_week_low': metrics.get('52WeekLow', 0)
                    }
                else:
                    logger.warning(f"Metrics API error {response.status}", symbol=symbol)
                    return {}
        except Exception as e:
            logger.error("Error getting financial metrics", symbol=symbol, error=str(e))
            return {}
            
    async def _get_earnings(self, symbol: str) -> Dict[str, Any]:
        """Get earnings data"""
        url = f"{self.base_url}/stock/earnings"
        params = {'symbol': symbol}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data and len(data) > 0:
                        latest_earnings = data[0]  # Most recent earnings
                        
                        return {
                            'period': latest_earnings.get('period', ''),
                            'actual_eps': latest_earnings.get('actual', 0),
                            'estimate_eps': latest_earnings.get('estimate', 0),
                            'surprise': latest_earnings.get('surprise', 0),
                            'surprise_percent': latest_earnings.get('surprisePercent', 0),
                            'earnings_quality': self._assess_earnings_quality(latest_earnings),
                            'historical_beats': self._count_earnings_beats(data[:4])  # Last 4 quarters
                        }
                    return {}
                else:
                    logger.warning(f"Earnings API error {response.status}", symbol=symbol)
                    return {}
        except Exception as e:
            logger.error("Error getting earnings", symbol=symbol, error=str(e))
            return {}
            
    async def _get_recommendation_trends(self, symbol: str) -> Dict[str, Any]:
        """Get analyst recommendation trends"""
        url = f"{self.base_url}/stock/recommendation"
        params = {'symbol': symbol}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data and len(data) > 0:
                        latest_rec = data[0]  # Most recent recommendations
                        
                        total_analysts = (
                            latest_rec.get('strongBuy', 0) +
                            latest_rec.get('buy', 0) +
                            latest_rec.get('hold', 0) +
                            latest_rec.get('sell', 0) +
                            latest_rec.get('strongSell', 0)
                        )
                        
                        if total_analysts > 0:
                            # Calculate consensus score (1-5 scale)
                            consensus_score = (
                                latest_rec.get('strongBuy', 0) * 5 +
                                latest_rec.get('buy', 0) * 4 +
                                latest_rec.get('hold', 0) * 3 +
                                latest_rec.get('sell', 0) * 2 +
                                latest_rec.get('strongSell', 0) * 1
                            ) / total_analysts
                            
                            return {
                                'period': latest_rec.get('period', ''),
                                'strong_buy': latest_rec.get('strongBuy', 0),
                                'buy': latest_rec.get('buy', 0),
                                'hold': latest_rec.get('hold', 0),
                                'sell': latest_rec.get('sell', 0),
                                'strong_sell': latest_rec.get('strongSell', 0),
                                'total_analysts': total_analysts,
                                'consensus_score': round(consensus_score, 2),
                                'consensus_rating': self._get_consensus_rating(consensus_score)
                            }
                    return {}
                else:
                    return {}
        except Exception as e:
            logger.error("Error getting recommendations", symbol=symbol, error=str(e))
            return {}
            
    async def _get_insider_trading(self, symbol: str) -> Dict[str, Any]:
        """Get insider trading data"""
        url = f"{self.base_url}/stock/insider-transactions"
        
        # Get data for last 3 months
        to_date = datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        params = {
            'symbol': symbol,
            'from': from_date,
            'to': to_date
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data and 'data' in data:
                        transactions = data['data']
                        
                        # Analyze insider activity
                        buy_volume = 0
                        sell_volume = 0
                        total_transactions = len(transactions)
                        
                        for tx in transactions:
                            shares = tx.get('share', 0)
                            if shares > 0:
                                buy_volume += shares
                            else:
                                sell_volume += abs(shares)
                                
                        net_insider_activity = buy_volume - sell_volume
                        
                        return {
                            'total_transactions': total_transactions,
                            'buy_volume': buy_volume,
                            'sell_volume': sell_volume,
                            'net_activity': net_insider_activity,
                            'insider_sentiment': self._assess_insider_sentiment(net_insider_activity),
                            'period_days': 90
                        }
                    return {}
                else:
                    return {}
        except Exception as e:
            logger.error("Error getting insider trading", symbol=symbol, error=str(e))
            return {}
            
    def _assess_earnings_quality(self, earnings: Dict[str, Any]) -> str:
        """Assess earnings quality"""
        surprise_percent = earnings.get('surprisePercent', 0)
        
        if surprise_percent > 10:
            return "EXCELLENT"
        elif surprise_percent > 5:
            return "GOOD"
        elif surprise_percent > 0:
            return "MEETS_EXPECTATIONS"
        elif surprise_percent > -5:
            return "SLIGHT_MISS"
        else:
            return "POOR"
            
    def _count_earnings_beats(self, earnings_history: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count earnings beats in recent history"""
        beats = 0
        misses = 0
        
        for earnings in earnings_history:
            surprise_percent = earnings.get('surprisePercent', 0)
            if surprise_percent > 0:
                beats += 1
            else:
                misses += 1
                
        return {'beats': beats, 'misses': misses}
        
    def _get_consensus_rating(self, score: float) -> str:
        """Convert consensus score to rating"""
        if score >= 4.5:
            return "STRONG_BUY"
        elif score >= 3.5:
            return "BUY"
        elif score >= 2.5:
            return "HOLD"
        elif score >= 1.5:
            return "SELL"
        else:
            return "STRONG_SELL"
            
    def _assess_insider_sentiment(self, net_activity: int) -> str:
        """Assess insider sentiment"""
        if net_activity > 10000:
            return "VERY_BULLISH"
        elif net_activity > 1000:
            return "BULLISH"
        elif net_activity > -1000:
            return "NEUTRAL"
        elif net_activity > -10000:
            return "BEARISH"
        else:
            return "VERY_BEARISH"
            
    def _calculate_fundamental_score(self, profile: Dict, metrics: Dict, earnings: Dict) -> Dict[str, Any]:
        """Calculate comprehensive fundamental score"""
        score = 0
        max_score = 100
        
        # Valuation score (20 points)
        pe_ratio = metrics.get('pe_ratio', 0)
        if 10 <= pe_ratio <= 25:
            score += 10
        elif 5 <= pe_ratio <= 35:
            score += 5
            
        peg_ratio = metrics.get('peg_ratio', 0)
        if 0.5 <= peg_ratio <= 1.5:
            score += 10
        elif 0.3 <= peg_ratio <= 2.0:
            score += 5
            
        # Profitability score (25 points)
        roe = metrics.get('roe', 0)
        if roe > 15:
            score += 10
        elif roe > 10:
            score += 5
            
        net_margin = metrics.get('net_margin', 0)
        if net_margin > 15:
            score += 10
        elif net_margin > 10:
            score += 5
            
        revenue_growth = metrics.get('revenue_growth', 0)
        if revenue_growth > 15:
            score += 5
        elif revenue_growth > 10:
            score += 3
            
        # Financial strength (20 points)
        debt_to_equity = metrics.get('debt_to_equity', 0)
        if debt_to_equity < 0.3:
            score += 10
        elif debt_to_equity < 0.6:
            score += 5
            
        current_ratio = metrics.get('current_ratio', 0)
        if current_ratio > 2:
            score += 10
        elif current_ratio > 1.5:
            score += 5
            
        # Earnings quality (20 points)
        surprise_percent = earnings.get('surprise_percent', 0)
        if surprise_percent > 5:
            score += 10
        elif surprise_percent > 0:
            score += 5
            
        beats = earnings.get('historical_beats', {}).get('beats', 0)
        if beats >= 3:
            score += 10
        elif beats >= 2:
            score += 5
            
        # Market cap consideration (15 points)
        market_cap = profile.get('market_cap', 0)
        if market_cap > 10000:  # Large cap stability
            score += 10
        elif market_cap > 2000:  # Mid cap
            score += 7
        elif market_cap > 300:   # Small cap
            score += 5
        # Micro cap gets fewer points for stability
            
        final_score = min(score, max_score)
        
        return {
            'total_score': final_score,
            'max_score': max_score,
            'score_percentage': round((final_score / max_score) * 100, 1),
            'rating': self._get_fundamental_rating(final_score),
            'components': {
                'valuation': 'Completed',
                'profitability': 'Completed', 
                'financial_strength': 'Completed',
                'earnings_quality': 'Completed',
                'market_position': 'Completed'
            }
        }
        
    def _get_fundamental_rating(self, score: int) -> str:
        """Get fundamental rating based on score"""
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
            
    async def get_fundamentals_batch(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get batch fundamental data"""
        results = []
        symbols_to_process = self.target_symbols[:limit]
        
        logger.info("Processing fundamentals batch", symbols=len(symbols_to_process))
        
        # Process with rate limiting (Finnhub allows 60 calls/minute)
        batch_size = 2
        for i in range(0, len(symbols_to_process), batch_size):
            batch = symbols_to_process[i:i + batch_size]
            
            batch_tasks = [self.get_comprehensive_fundamentals(symbol) for symbol in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error("Batch processing error", error=str(result))
                else:
                    results.append(result)
                    
            # Rate limiting
            if i + batch_size < len(symbols_to_process):
                await asyncio.sleep(3)  # Stay under 60 calls/minute
                
        logger.info("Fundamentals batch completed", results=len(results))
        return results
        
    async def run(self):
        """Main service loop"""
        logger.info("Finnhub Fundamentals Service started successfully")
        
        while self.running:
            try:
                # Periodic fundamental analysis update
                batch_data = await self.get_fundamentals_batch(3)
                logger.info("Periodic fundamentals update completed",
                          results=len(batch_data),
                          timestamp=datetime.now().isoformat())
                          
                # Wait 2 hours between updates (fundamental data changes slowly)
                await asyncio.sleep(7200)
                
            except Exception as e:
                logger.error("Error in service loop", error=str(e))
                await asyncio.sleep(600)  # Wait 10 minutes on error
                
    async def shutdown(self):
        """Shutdown service"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Finnhub Fundamentals Service stopped")

async def main():
    """Main entry point"""
    service = FinnhubFundamentalsService()
    
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