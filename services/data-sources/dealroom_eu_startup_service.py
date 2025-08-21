#!/usr/bin/env python3
"""
Dealroom EU-Startup Data Source Service
Europäische Startup-Datenbank mit Fokus auf Finanzierungsrunden und Investors
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

logger = setup_logging("dealroom-eu-startup")

class DealroomEUStartupService:
    """Dealroom EU-Startup Data Source Service"""
    
    def __init__(self):
        self.running = False
        # Note: Dealroom API requires business subscription, using mock data for demo
        self.api_key = os.getenv('DEALROOM_API_KEY', 'demo')
        self.base_url = "https://api.dealroom.co"
        self.session = None
        
        # Focus auf europäische Startup-Hotspots
        self.target_regions = [
            'Germany', 'United Kingdom', 'France', 'Netherlands', 
            'Sweden', 'Switzerland', 'Spain', 'Austria'
        ]
        
        self.target_sectors = [
            'fintech', 'healthtech', 'deeptech', 'cleantech', 
            'edtech', 'insurtech', 'proptech', 'foodtech'
        ]
        
    async def initialize(self):
        """Initialize service"""
        logger.info("Initializing Dealroom EU-Startup Service")
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'Aktienanalyse-System/1.0',
                'Authorization': f'Bearer {self.api_key}'
            }
        )
        self.running = True
        logger.info("Dealroom EU-Startup Service initialized", 
                   regions=len(self.target_regions),
                   sectors=len(self.target_sectors))
        return True
        
    async def get_eu_startup_overview(self, region: str = "Germany") -> Dict[str, Any]:
        """Get comprehensive EU startup ecosystem overview"""
        try:
            # Get startup ecosystem data
            companies_data = await self._get_startup_companies(region)
            funding_data = await self._get_funding_rounds(region)
            investor_data = await self._get_investor_activity(region)
            market_trends = await self._analyze_market_trends(region)
            
            # Combine data
            result = {
                'region': region,
                'timestamp': datetime.now().isoformat(),
                'source': 'dealroom_eu_startup',
                'data_type': 'eu_startup_ecosystem',
                'companies': companies_data,
                'funding_rounds': funding_data,
                'investor_activity': investor_data,
                'market_trends': market_trends,
                'ecosystem_score': self._calculate_ecosystem_score(
                    companies_data, funding_data, investor_data
                ),
                'success': True
            }
            
            logger.info("EU startup overview retrieved", region=region)
            return result
            
        except Exception as e:
            logger.error("Error getting startup overview", region=region, error=str(e))
            return {
                'region': region,
                'timestamp': datetime.now().isoformat(),
                'source': 'dealroom_eu_startup',
                'error': str(e),
                'success': False
            }
            
    async def _get_startup_companies(self, region: str) -> Dict[str, Any]:
        """Get startup companies data (mock implementation)"""
        try:
            # In production, this would call Dealroom API
            # For demo, we generate realistic mock data
            
            total_companies = self._generate_realistic_company_count(region)
            unicorns = max(1, total_companies // 500)  # Realistic unicorn ratio
            
            # Sector distribution (realistic for EU markets)
            sector_distribution = {
                'fintech': round(total_companies * 0.18),
                'healthtech': round(total_companies * 0.15),
                'cleantech': round(total_companies * 0.12),
                'deeptech': round(total_companies * 0.10),
                'edtech': round(total_companies * 0.08),
                'enterprise_software': round(total_companies * 0.20),
                'consumer': round(total_companies * 0.10),
                'other': round(total_companies * 0.07)
            }
            
            # Growth metrics
            growth_companies = round(total_companies * 0.25)  # Companies with significant growth
            profitable_companies = round(total_companies * 0.15)  # Profitable companies
            
            return {
                'total_startups': total_companies,
                'unicorns': unicorns,
                'decacorns': max(0, unicorns // 10),
                'sector_distribution': sector_distribution,
                'stage_distribution': {
                    'seed': round(total_companies * 0.40),
                    'series_a': round(total_companies * 0.25),
                    'series_b': round(total_companies * 0.15),
                    'series_c_plus': round(total_companies * 0.10),
                    'pre_ipo': round(total_companies * 0.10)
                },
                'performance_metrics': {
                    'high_growth': growth_companies,
                    'profitable': profitable_companies,
                    'expanding_internationally': round(total_companies * 0.12)
                },
                'employment': {
                    'total_jobs': total_companies * 15,  # Average 15 employees per startup
                    'jobs_created_last_year': total_companies * 3
                }
            }
            
        except Exception as e:
            logger.error("Error getting startup companies", region=region, error=str(e))
            return {}
            
    async def _get_funding_rounds(self, region: str) -> Dict[str, Any]:
        """Get funding rounds data"""
        try:
            # Generate realistic funding data based on region
            base_funding = self._get_region_base_funding(region)
            
            # Recent funding activity (last 12 months)
            total_funding_eur = base_funding * (0.8 + (hash(region) % 40) / 100)  # Some variation
            total_rounds = max(50, int(base_funding / 5000000))  # Average 5M per round
            
            # Stage breakdown
            funding_by_stage = {
                'seed': {
                    'amount_eur': round(total_funding_eur * 0.10),
                    'round_count': round(total_rounds * 0.45),
                    'avg_round_size': 500000
                },
                'series_a': {
                    'amount_eur': round(total_funding_eur * 0.25),
                    'round_count': round(total_rounds * 0.30),
                    'avg_round_size': 8000000
                },
                'series_b': {
                    'amount_eur': round(total_funding_eur * 0.30),
                    'round_count': round(total_rounds * 0.15),
                    'avg_round_size': 25000000
                },
                'series_c_plus': {
                    'amount_eur': round(total_funding_eur * 0.35),
                    'round_count': round(total_rounds * 0.10),
                    'avg_round_size': 50000000
                }
            }
            
            # Quarterly trends
            quarterly_trends = self._generate_quarterly_trends(total_funding_eur)
            
            return {
                'total_funding_eur_12m': int(total_funding_eur),
                'total_rounds_12m': total_rounds,
                'avg_round_size_eur': int(total_funding_eur / total_rounds),
                'funding_by_stage': funding_by_stage,
                'quarterly_trends': quarterly_trends,
                'top_funded_sectors': [
                    {'sector': 'fintech', 'funding_eur': int(total_funding_eur * 0.22)},
                    {'sector': 'healthtech', 'funding_eur': int(total_funding_eur * 0.18)},
                    {'sector': 'cleantech', 'funding_eur': int(total_funding_eur * 0.15)},
                    {'sector': 'deeptech', 'funding_eur': int(total_funding_eur * 0.12)}
                ],
                'funding_growth_yoy': self._calculate_funding_growth(region),
                'market_sentiment': self._assess_market_sentiment(total_funding_eur, total_rounds)
            }
            
        except Exception as e:
            logger.error("Error getting funding rounds", region=region, error=str(e))
            return {}
            
    async def _get_investor_activity(self, region: str) -> Dict[str, Any]:
        """Get investor activity data"""
        try:
            # Realistic investor ecosystem for European regions
            investor_base = self._get_region_investor_base(region)
            
            active_investors = {
                'vc_funds': investor_base['vc_funds'],
                'angel_investors': investor_base['angels'],
                'corporate_vc': investor_base['corporate'],
                'government_funds': investor_base['government'],
                'international_investors': investor_base['international']
            }
            
            # Investment patterns
            investment_focus = {
                'local_preference': 0.65,  # 65% prefer local investments
                'cross_border_appetite': 0.35,
                'avg_check_size_eur': investor_base['avg_check'],
                'follow_on_rate': 0.40  # 40% do follow-on investments
            }
            
            # Notable investors (mock data)
            top_investors = [
                {
                    'name': f'{region} Ventures',
                    'type': 'VC Fund',
                    'investments_12m': 15,
                    'total_deployed_eur': 50000000,
                    'focus_stages': ['series_a', 'series_b']
                },
                {
                    'name': f'European Growth Partners',
                    'type': 'Growth Equity',
                    'investments_12m': 8,
                    'total_deployed_eur': 120000000,
                    'focus_stages': ['series_b', 'series_c']
                },
                {
                    'name': f'{region} Angel Network',
                    'type': 'Angel Group',
                    'investments_12m': 25,
                    'total_deployed_eur': 8000000,
                    'focus_stages': ['seed', 'series_a']
                }
            ]
            
            return {
                'active_investors': active_investors,
                'total_unique_investors': sum(active_investors.values()),
                'investment_patterns': investment_focus,
                'top_investors': top_investors,
                'investor_sentiment': self._assess_investor_sentiment(region),
                'capital_availability': self._assess_capital_availability(region),
                'exit_activity': {
                    'ipo_count_12m': max(1, investor_base['vc_funds'] // 50),
                    'acquisition_count_12m': max(5, investor_base['vc_funds'] // 10),
                    'total_exit_value_eur': investor_base['avg_check'] * 100
                }
            }
            
        except Exception as e:
            logger.error("Error getting investor activity", region=region, error=str(e))
            return {}
            
    async def _analyze_market_trends(self, region: str) -> Dict[str, Any]:
        """Analyze market trends"""
        try:
            # Current market dynamics
            market_dynamics = {
                'funding_velocity': 'MODERATE',  # How quickly deals are closing
                'valuation_trends': 'STABILIZING',  # Post-2022 correction
                'sector_rotation': ['healthtech', 'cleantech', 'deeptech'],  # Hot sectors
                'investor_selectivity': 'HIGH',  # More selective post-bubble
                'regulatory_impact': 'MODERATE'  # EU regulation effects
            }
            
            # Emerging trends
            emerging_trends = [
                {
                    'trend': 'AI Integration',
                    'adoption_rate': 0.75,
                    'impact_level': 'HIGH',
                    'affected_sectors': ['fintech', 'healthtech', 'enterprise_software']
                },
                {
                    'trend': 'Sustainability Focus',
                    'adoption_rate': 0.85,
                    'impact_level': 'HIGH',
                    'affected_sectors': ['cleantech', 'foodtech', 'mobility']
                },
                {
                    'trend': 'B2B SaaS Consolidation',
                    'adoption_rate': 0.60,
                    'impact_level': 'MEDIUM',
                    'affected_sectors': ['enterprise_software', 'fintech']
                },
                {
                    'trend': 'Deep Tech Commercialization',
                    'adoption_rate': 0.45,
                    'impact_level': 'HIGH',
                    'affected_sectors': ['deeptech', 'healthtech']
                }
            ]
            
            # Regional advantages
            competitive_advantages = self._get_regional_advantages(region)
            
            # Challenges
            market_challenges = [
                'Talent shortage in tech roles',
                'Regulatory complexity',
                'Limited growth capital',
                'Market fragmentation',
                'US competition for talent'
            ]
            
            return {
                'market_dynamics': market_dynamics,
                'emerging_trends': emerging_trends,
                'competitive_advantages': competitive_advantages,
                'market_challenges': market_challenges,
                'outlook_12m': self._generate_market_outlook(region),
                'investment_opportunities': self._identify_investment_opportunities(region)
            }
            
        except Exception as e:
            logger.error("Error analyzing market trends", region=region, error=str(e))
            return {}
            
    def _generate_realistic_company_count(self, region: str) -> int:
        """Generate realistic startup company count by region"""
        base_counts = {
            'Germany': 15000,
            'United Kingdom': 18000,
            'France': 12000,
            'Netherlands': 8000,
            'Sweden': 6000,
            'Switzerland': 4000,
            'Spain': 7000,
            'Austria': 3000
        }
        return base_counts.get(region, 5000)
        
    def _get_region_base_funding(self, region: str) -> float:
        """Get base funding amounts by region (EUR)"""
        base_funding = {
            'Germany': 7200000000,  # 7.2B EUR (based on EY data)
            'United Kingdom': 9500000000,  # 9.5B EUR  
            'France': 6800000000,  # 6.8B EUR
            'Netherlands': 3200000000,  # 3.2B EUR
            'Sweden': 2800000000,  # 2.8B EUR
            'Switzerland': 2500000000,  # 2.5B EUR
            'Spain': 2100000000,  # 2.1B EUR
            'Austria': 800000000   # 800M EUR
        }
        return base_funding.get(region, 1000000000)
        
    def _get_region_investor_base(self, region: str) -> Dict[str, int]:
        """Get investor base by region"""
        investor_bases = {
            'Germany': {
                'vc_funds': 120,
                'angels': 800,
                'corporate': 45,
                'government': 25,
                'international': 150,
                'avg_check': 5000000
            },
            'United Kingdom': {
                'vc_funds': 180,
                'angels': 1200,
                'corporate': 65,
                'government': 20,
                'international': 220,
                'avg_check': 6000000
            },
            'France': {
                'vc_funds': 100,
                'angels': 600,
                'corporate': 40,
                'government': 30,
                'international': 120,
                'avg_check': 4500000
            }
        }
        return investor_bases.get(region, {
            'vc_funds': 50, 'angels': 300, 'corporate': 20, 
            'government': 15, 'international': 80, 'avg_check': 3000000
        })
        
    def _generate_quarterly_trends(self, total_funding: float) -> List[Dict[str, Any]]:
        """Generate quarterly funding trends"""
        quarters = ['Q1 2024', 'Q2 2024', 'Q3 2024', 'Q4 2024']
        base_amount = total_funding / 4
        
        # Simulate realistic quarterly variation
        variations = [0.85, 1.1, 0.95, 1.1]  # Typical pattern
        
        return [
            {
                'quarter': quarter,
                'funding_eur': int(base_amount * variation),
                'round_count': max(10, int((base_amount * variation) / 5000000)),
                'yoy_growth': round((variation - 1) * 100 + 15, 1)  # Add base growth
            }
            for quarter, variation in zip(quarters, variations)
        ]
        
    def _calculate_funding_growth(self, region: str) -> float:
        """Calculate year-over-year funding growth"""
        # Realistic growth rates post-2022 correction
        growth_rates = {
            'Germany': 17.0,  # Based on EY data
            'United Kingdom': 12.0,
            'France': 15.0,
            'Netherlands': 20.0,
            'Sweden': 8.0,
            'Switzerland': 25.0,
            'Spain': 22.0,
            'Austria': 18.0
        }
        return growth_rates.get(region, 10.0)
        
    def _assess_market_sentiment(self, funding: float, rounds: int) -> str:
        """Assess market sentiment"""
        avg_round = funding / rounds if rounds > 0 else 0
        
        if avg_round > 10000000:  # 10M+ average
            return "OPTIMISTIC"
        elif avg_round > 5000000:  # 5M+ average
            return "CAUTIOUSLY_OPTIMISTIC"
        elif avg_round > 2000000:  # 2M+ average
            return "NEUTRAL"
        else:
            return "CAUTIOUS"
            
    def _assess_investor_sentiment(self, region: str) -> str:
        """Assess investor sentiment by region"""
        # Based on market conditions and regional factors
        sentiment_map = {
            'Germany': 'POSITIVE',
            'United Kingdom': 'CAUTIOUSLY_POSITIVE',
            'France': 'POSITIVE',
            'Netherlands': 'VERY_POSITIVE',
            'Sweden': 'POSITIVE',
            'Switzerland': 'VERY_POSITIVE',
            'Spain': 'IMPROVING',
            'Austria': 'STABLE'
        }
        return sentiment_map.get(region, 'NEUTRAL')
        
    def _assess_capital_availability(self, region: str) -> str:
        """Assess capital availability"""
        # Post-interest rate environment assessment
        availability_map = {
            'Germany': 'ABUNDANT',
            'United Kingdom': 'MODERATE',
            'France': 'ABUNDANT',
            'Netherlands': 'ABUNDANT',
            'Sweden': 'MODERATE',
            'Switzerland': 'VERY_ABUNDANT',
            'Spain': 'LIMITED',
            'Austria': 'MODERATE'
        }
        return availability_map.get(region, 'MODERATE')
        
    def _get_regional_advantages(self, region: str) -> List[str]:
        """Get competitive advantages by region"""
        advantages_map = {
            'Germany': [
                'Strong engineering talent',
                'Manufacturing expertise',
                'Automotive industry cluster',
                'Government support programs',
                'EU market access'
            ],
            'United Kingdom': [
                'Financial services expertise',
                'English language advantage',
                'Strong university research',
                'International connections',
                'Regulatory innovation'
            ],
            'France': [
                'Government innovation support',
                'Strong tech education',
                'EU headquarters location',
                'Fashion and luxury sectors',
                'Nuclear and aerospace expertise'
            ],
            'Netherlands': [
                'Strategic EU location',
                'Excellent infrastructure',
                'Multilingual workforce',
                'Trade and logistics hub',
                'Progressive regulation'
            ]
        }
        return advantages_map.get(region, [
            'EU market access',
            'Educated workforce',
            'Government support',
            'Growing ecosystem'
        ])
        
    def _generate_market_outlook(self, region: str) -> Dict[str, str]:
        """Generate 12-month market outlook"""
        return {
            'funding_outlook': 'STABLE_TO_POSITIVE',
            'valuation_outlook': 'STABILIZING',
            'exit_outlook': 'IMPROVING',
            'talent_outlook': 'COMPETITIVE',
            'regulatory_outlook': 'STABLE',
            'overall_rating': 'POSITIVE'
        }
        
    def _identify_investment_opportunities(self, region: str) -> List[Dict[str, str]]:
        """Identify key investment opportunities"""
        return [
            {
                'sector': 'HealthTech',
                'opportunity': 'AI-powered diagnostics',
                'rationale': 'Aging population and digital health trends',
                'investment_stage': 'Series A-B'
            },
            {
                'sector': 'CleanTech',
                'opportunity': 'Energy storage solutions',
                'rationale': 'EU Green Deal and energy independence',
                'investment_stage': 'Series B-C'
            },
            {
                'sector': 'FinTech',
                'opportunity': 'SME lending platforms',
                'rationale': 'Bank lending gap for SMEs',
                'investment_stage': 'Series A-B'
            },
            {
                'sector': 'DeepTech',
                'opportunity': 'Quantum computing applications',
                'rationale': 'Early commercialization phase',
                'investment_stage': 'Series A'
            }
        ]
        
    def _calculate_ecosystem_score(self, companies: Dict, funding: Dict, investors: Dict) -> Dict[str, Any]:
        """Calculate comprehensive ecosystem health score"""
        score = 0
        max_score = 100
        
        # Company diversity score (25 points)
        if companies.get('total_startups', 0) > 10000:
            score += 20
        elif companies.get('total_startups', 0) > 5000:
            score += 15
        elif companies.get('total_startups', 0) > 1000:
            score += 10
        
        if companies.get('unicorns', 0) > 5:
            score += 5
        elif companies.get('unicorns', 0) > 0:
            score += 3
            
        # Funding strength score (30 points)
        total_funding = funding.get('total_funding_eur_12m', 0)
        if total_funding > 5000000000:  # 5B+
            score += 25
        elif total_funding > 2000000000:  # 2B+
            score += 20
        elif total_funding > 500000000:   # 500M+
            score += 15
        elif total_funding > 100000000:   # 100M+
            score += 10
        
        funding_growth = funding.get('funding_growth_yoy', 0)
        if funding_growth > 15:
            score += 5
        elif funding_growth > 5:
            score += 3
            
        # Investor ecosystem score (25 points)
        total_investors = investors.get('total_unique_investors', 0)
        if total_investors > 1000:
            score += 15
        elif total_investors > 500:
            score += 10
        elif total_investors > 200:
            score += 5
            
        exits = investors.get('exit_activity', {})
        if exits.get('ipo_count_12m', 0) + exits.get('acquisition_count_12m', 0) > 20:
            score += 10
        elif exits.get('ipo_count_12m', 0) + exits.get('acquisition_count_12m', 0) > 10:
            score += 5
            
        # Innovation infrastructure (20 points)
        score += 15  # Base score for EU innovation infrastructure
        
        final_score = min(score, max_score)
        
        return {
            'total_score': final_score,
            'max_score': max_score,
            'score_percentage': round((final_score / max_score) * 100, 1),
            'rating': self._get_ecosystem_rating(final_score),
            'components': {
                'company_diversity': 'Evaluated',
                'funding_strength': 'Evaluated',
                'investor_ecosystem': 'Evaluated',
                'innovation_infrastructure': 'Evaluated'
            }
        }
        
    def _get_ecosystem_rating(self, score: int) -> str:
        """Get ecosystem rating based on score"""
        if score >= 85:
            return "WORLD_CLASS"
        elif score >= 70:
            return "STRONG"
        elif score >= 55:
            return "DEVELOPING"
        elif score >= 40:
            return "EMERGING"
        else:
            return "NASCENT"
            
    async def get_startup_batch_analysis(self, regions: List[str] = None) -> List[Dict[str, Any]]:
        """Get batch analysis for multiple regions"""
        if not regions:
            regions = self.target_regions[:3]  # Top 3 regions
            
        results = []
        logger.info("Processing startup ecosystem batch", regions=len(regions))
        
        # Process regions sequentially to avoid overwhelming mock API
        for region in regions:
            try:
                region_data = await self.get_eu_startup_overview(region)
                results.append(region_data)
                await asyncio.sleep(2)  # Rate limiting
            except Exception as e:
                logger.error("Batch processing error", region=region, error=str(e))
                
        logger.info("Startup ecosystem batch completed", results=len(results))
        return results
        
    async def run(self):
        """Main service loop"""
        logger.info("Dealroom EU-Startup Service started successfully")
        
        while self.running:
            try:
                # Periodic ecosystem analysis update
                batch_data = await self.get_startup_batch_analysis(['Germany', 'United Kingdom'])
                logger.info("Periodic ecosystem update completed",
                          results=len(batch_data),
                          timestamp=datetime.now().isoformat())
                          
                # Startup ecosystem data updates every 6 hours
                await asyncio.sleep(21600)
                
            except Exception as e:
                logger.error("Error in service loop", error=str(e))
                await asyncio.sleep(1800)  # Wait 30 minutes on error
                
    async def shutdown(self):
        """Shutdown service"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Dealroom EU-Startup Service stopped")

async def main():
    """Main entry point"""
    service = DealroomEUStartupService()
    
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