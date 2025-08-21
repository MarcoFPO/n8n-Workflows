"""
Fundamental Feature Engine v1.0.0
Finanz-Kennzahlen und Fundamental-Features für ML Analytics Service

Autor: Claude Code
Datum: 18. August 2025
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncpg

# Mock Fundamental Data für Demonstration (in Realität von Financial Data Service)
MOCK_FUNDAMENTAL_DATA = {
    "AAPL": {
        # Earnings Data
        "earnings": {
            "revenue_ttm": 365.8e9,  # Revenue TTM in USD
            "net_income_ttm": 94.3e9,  # Net Income TTM
            "eps_ttm": 6.13,  # Earnings per Share TTM
            "revenue_growth_yoy": 0.06,  # 6% YoY growth
            "earnings_growth_yoy": 0.11,  # 11% YoY growth
            "gross_margin": 0.43,  # 43% gross margin
            "operating_margin": 0.26,  # 26% operating margin
            "net_margin": 0.24,  # 24% net margin
        },
        
        # Balance Sheet
        "balance_sheet": {
            "total_assets": 352.6e9,
            "total_debt": 109.6e9,
            "cash_and_equivalents": 29.9e9,
            "shareholders_equity": 62.1e9,
            "working_capital": 2.8e9,
            "debt_to_equity": 1.76,
            "current_ratio": 1.01,
            "quick_ratio": 0.98,
        },
        
        # Cash Flow
        "cash_flow": {
            "operating_cash_flow_ttm": 110.5e9,
            "free_cash_flow_ttm": 99.8e9,
            "capex_ttm": -10.7e9,
            "dividends_paid_ttm": -15.0e9,
            "share_buybacks_ttm": -77.6e9,
        },
        
        # Valuation Metrics
        "valuation": {
            "market_cap": 2800e9,  # Market Cap
            "pe_ratio": 28.5,  # Price-to-Earnings
            "pb_ratio": 45.1,  # Price-to-Book
            "ps_ratio": 7.7,  # Price-to-Sales
            "ev_ebitda": 22.1,  # EV/EBITDA
            "dividend_yield": 0.0047,  # 0.47% dividend yield
            "peg_ratio": 2.59,  # PEG Ratio
        },
        
        # Market Data
        "market_data": {
            "shares_outstanding": 15.7e9,
            "float_shares": 15.6e9,
            "insider_ownership": 0.07,  # 7%
            "institutional_ownership": 0.62,  # 62%
            "short_interest": 0.008,  # 0.8%
            "beta": 1.29,
        }
    }
}

logger = logging.getLogger(__name__)

class FundamentalFeatureEngine:
    """
    Engine für Fundamental-basierte Features aus Finanz-Kennzahlen
    """
    
    def __init__(self, database_pool: asyncpg.Pool):
        self.database_pool = database_pool
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def calculate_fundamental_features(self, symbol: str) -> Dict[str, Any]:
        """
        Berechnet Fundamental-Features für ein Symbol
        """
        try:
            self.logger.info(f"Calculating fundamental features for {symbol}")
            
            # Hole Fundamental-Daten (Mock für jetzt)
            fundamental_data = await self._get_fundamental_data(symbol)
            
            if not fundamental_data:
                return {"error": f"No fundamental data available for {symbol}"}
            
            # Berechne Fundamental Features
            features = await self._calculate_fundamental_indicators(fundamental_data)
            
            # Speichere Features in DB
            await self._store_fundamental_features(symbol, features)
            
            return {
                "symbol": symbol,
                "feature_type": "fundamental",
                "features_calculated": len(features),
                "features": features,
                "data_sources": ["earnings", "balance_sheet", "cash_flow", "valuation", "market_data"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate fundamental features for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    async def _get_fundamental_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Holt Fundamental-Daten für Symbol (Mock Implementation)
        In Realität würde dies von Financial Data Service kommen
        """
        if symbol in MOCK_FUNDAMENTAL_DATA:
            return MOCK_FUNDAMENTAL_DATA[symbol]
        return None
    
    async def _calculate_fundamental_indicators(self, data: Dict[str, Any]) -> Dict[str, float]:
        """
        Berechnet Fundamental-Indikatoren aus Finanz-Daten
        """
        features = {}
        
        # Earnings & Profitability Features
        earnings = data.get('earnings', {})
        if earnings:
            features.update({
                # Growth Metrics
                "revenue_growth_yoy": earnings.get('revenue_growth_yoy', 0.0),
                "earnings_growth_yoy": earnings.get('earnings_growth_yoy', 0.0),
                
                # Profitability Margins
                "gross_margin": earnings.get('gross_margin', 0.0),
                "operating_margin": earnings.get('operating_margin', 0.0),
                "net_margin": earnings.get('net_margin', 0.0),
                
                # Efficiency Ratios
                "roe": self._calculate_roe(earnings, data.get('balance_sheet', {})),  # Return on Equity
                "roa": self._calculate_roa(earnings, data.get('balance_sheet', {})),  # Return on Assets
                "roic": self._calculate_roic(earnings, data.get('balance_sheet', {})),  # Return on Invested Capital
            })
        
        # Balance Sheet Features
        balance_sheet = data.get('balance_sheet', {})
        if balance_sheet:
            features.update({
                # Leverage Ratios
                "debt_to_equity": balance_sheet.get('debt_to_equity', 0.0),
                "debt_to_assets": self._calculate_debt_to_assets(balance_sheet),
                
                # Liquidity Ratios
                "current_ratio": balance_sheet.get('current_ratio', 0.0),
                "quick_ratio": balance_sheet.get('quick_ratio', 0.0),
                "cash_ratio": self._calculate_cash_ratio(balance_sheet),
                
                # Asset Quality
                "asset_turnover": self._calculate_asset_turnover(earnings, balance_sheet),
                "working_capital_ratio": self._calculate_working_capital_ratio(balance_sheet),
            })
        
        # Cash Flow Features
        cash_flow = data.get('cash_flow', {})
        if cash_flow:
            features.update({
                # Cash Generation
                "operating_cash_flow_margin": self._calculate_ocf_margin(cash_flow, earnings),
                "free_cash_flow_margin": self._calculate_fcf_margin(cash_flow, earnings),
                "cash_conversion_ratio": self._calculate_cash_conversion(cash_flow, earnings),
                
                # Capital Allocation
                "capex_intensity": self._calculate_capex_intensity(cash_flow, earnings),
                "dividend_payout_ratio": self._calculate_dividend_payout(cash_flow, earnings),
                "buyback_yield": self._calculate_buyback_yield(cash_flow, data.get('valuation', {})),
            })
        
        # Valuation Features
        valuation = data.get('valuation', {})
        if valuation:
            features.update({
                # Traditional Ratios
                "pe_ratio": valuation.get('pe_ratio', 0.0),
                "pb_ratio": valuation.get('pb_ratio', 0.0),
                "ps_ratio": valuation.get('ps_ratio', 0.0),
                "ev_ebitda": valuation.get('ev_ebitda', 0.0),
                "peg_ratio": valuation.get('peg_ratio', 0.0),
                
                # Yield Metrics
                "dividend_yield": valuation.get('dividend_yield', 0.0),
                "earnings_yield": 1.0 / valuation.get('pe_ratio', 1.0) if valuation.get('pe_ratio', 0) > 0 else 0.0,
                
                # Relative Valuation
                "price_to_sales_relative": self._calculate_relative_metric(valuation.get('ps_ratio', 0), 2.5),  # vs sector avg
                "pe_relative": self._calculate_relative_metric(valuation.get('pe_ratio', 0), 20.0),  # vs market avg
            })
        
        # Market Structure Features
        market_data = data.get('market_data', {})
        if market_data:
            features.update({
                # Risk Metrics
                "beta": market_data.get('beta', 1.0),
                "market_cap_log": self._safe_log(valuation.get('market_cap', 1e9)),  # Log market cap
                
                # Ownership Structure
                "insider_ownership": market_data.get('insider_ownership', 0.0),
                "institutional_ownership": market_data.get('institutional_ownership', 0.0),
                "short_interest": market_data.get('short_interest', 0.0),
                
                # Float Characteristics
                "float_ratio": self._calculate_float_ratio(market_data),
                "ownership_concentration": market_data.get('insider_ownership', 0) + market_data.get('institutional_ownership', 0),
            })
        
        # Cross-Category Composite Features
        features.update({
            # Quality Score (combination of profitability, stability, growth)
            "quality_score": self._calculate_quality_score(features),
            
            # Value Score (combination of valuation metrics)
            "value_score": self._calculate_value_score(features),
            
            # Growth Score (combination of growth metrics)
            "growth_score": self._calculate_growth_score(features),
            
            # Financial Strength Score
            "financial_strength": self._calculate_financial_strength(features),
        })
        
        return features
    
    def _calculate_roe(self, earnings: Dict, balance_sheet: Dict) -> float:
        """Return on Equity"""
        net_income = earnings.get('net_income_ttm', 0)
        equity = balance_sheet.get('shareholders_equity', 1)
        return net_income / equity if equity > 0 else 0.0
    
    def _calculate_roa(self, earnings: Dict, balance_sheet: Dict) -> float:
        """Return on Assets"""
        net_income = earnings.get('net_income_ttm', 0)
        assets = balance_sheet.get('total_assets', 1)
        return net_income / assets if assets > 0 else 0.0
    
    def _calculate_roic(self, earnings: Dict, balance_sheet: Dict) -> float:
        """Return on Invested Capital"""
        net_income = earnings.get('net_income_ttm', 0)
        equity = balance_sheet.get('shareholders_equity', 0)
        debt = balance_sheet.get('total_debt', 0)
        invested_capital = equity + debt
        return net_income / invested_capital if invested_capital > 0 else 0.0
    
    def _calculate_debt_to_assets(self, balance_sheet: Dict) -> float:
        """Debt to Assets Ratio"""
        debt = balance_sheet.get('total_debt', 0)
        assets = balance_sheet.get('total_assets', 1)
        return debt / assets if assets > 0 else 0.0
    
    def _calculate_cash_ratio(self, balance_sheet: Dict) -> float:
        """Cash Ratio approximation"""
        cash = balance_sheet.get('cash_and_equivalents', 0)
        debt = balance_sheet.get('total_debt', 1)
        return cash / debt if debt > 0 else 0.0
    
    def _calculate_asset_turnover(self, earnings: Dict, balance_sheet: Dict) -> float:
        """Asset Turnover Ratio"""
        revenue = earnings.get('revenue_ttm', 0)
        assets = balance_sheet.get('total_assets', 1)
        return revenue / assets if assets > 0 else 0.0
    
    def _calculate_working_capital_ratio(self, balance_sheet: Dict) -> float:
        """Working Capital to Total Assets"""
        wc = balance_sheet.get('working_capital', 0)
        assets = balance_sheet.get('total_assets', 1)
        return wc / assets if assets > 0 else 0.0
    
    def _calculate_ocf_margin(self, cash_flow: Dict, earnings: Dict) -> float:
        """Operating Cash Flow Margin"""
        ocf = cash_flow.get('operating_cash_flow_ttm', 0)
        revenue = earnings.get('revenue_ttm', 1)
        return ocf / revenue if revenue > 0 else 0.0
    
    def _calculate_fcf_margin(self, cash_flow: Dict, earnings: Dict) -> float:
        """Free Cash Flow Margin"""
        fcf = cash_flow.get('free_cash_flow_ttm', 0)
        revenue = earnings.get('revenue_ttm', 1)
        return fcf / revenue if revenue > 0 else 0.0
    
    def _calculate_cash_conversion(self, cash_flow: Dict, earnings: Dict) -> float:
        """Cash Conversion Ratio (OCF / Net Income)"""
        ocf = cash_flow.get('operating_cash_flow_ttm', 0)
        net_income = earnings.get('net_income_ttm', 1)
        return ocf / net_income if net_income > 0 else 0.0
    
    def _calculate_capex_intensity(self, cash_flow: Dict, earnings: Dict) -> float:
        """Capex Intensity (Capex / Revenue)"""
        capex = abs(cash_flow.get('capex_ttm', 0))
        revenue = earnings.get('revenue_ttm', 1)
        return capex / revenue if revenue > 0 else 0.0
    
    def _calculate_dividend_payout(self, cash_flow: Dict, earnings: Dict) -> float:
        """Dividend Payout Ratio"""
        dividends = abs(cash_flow.get('dividends_paid_ttm', 0))
        net_income = earnings.get('net_income_ttm', 1)
        return dividends / net_income if net_income > 0 else 0.0
    
    def _calculate_buyback_yield(self, cash_flow: Dict, valuation: Dict) -> float:
        """Share Buyback Yield"""
        buybacks = abs(cash_flow.get('share_buybacks_ttm', 0))
        market_cap = valuation.get('market_cap', 1)
        return buybacks / market_cap if market_cap > 0 else 0.0
    
    def _calculate_relative_metric(self, value: float, benchmark: float) -> float:
        """Relative valuation vs benchmark"""
        return value / benchmark if benchmark > 0 else 0.0
    
    def _safe_log(self, value: float) -> float:
        """Safe logarithm calculation"""
        import math
        return math.log(max(value, 1.0))
    
    def _calculate_float_ratio(self, market_data: Dict) -> float:
        """Float Shares / Total Shares"""
        float_shares = market_data.get('float_shares', 0)
        total_shares = market_data.get('shares_outstanding', 1)
        return float_shares / total_shares if total_shares > 0 else 0.0
    
    def _calculate_quality_score(self, features: Dict[str, float]) -> float:
        """Composite Quality Score (0-1)"""
        roe = min(features.get('roe', 0) * 5, 1.0)  # Scale ROE 
        margin_stability = min(features.get('net_margin', 0) * 4, 1.0)
        debt_penalty = max(1 - features.get('debt_to_equity', 0) / 2, 0)
        return (roe + margin_stability + debt_penalty) / 3
    
    def _calculate_value_score(self, features: Dict[str, float]) -> float:
        """Composite Value Score (0-1)"""
        pe_score = max(1 - features.get('pe_ratio', 20) / 40, 0)  # Lower PE = higher score
        pb_score = max(1 - features.get('pb_ratio', 3) / 6, 0)
        ev_ebitda_score = max(1 - features.get('ev_ebitda', 15) / 30, 0)
        return (pe_score + pb_score + ev_ebitda_score) / 3
    
    def _calculate_growth_score(self, features: Dict[str, float]) -> float:
        """Composite Growth Score (0-1)"""
        revenue_growth = min(features.get('revenue_growth_yoy', 0) * 2, 1.0)
        earnings_growth = min(features.get('earnings_growth_yoy', 0) * 2, 1.0)
        margin_expansion = max(features.get('operating_margin', 0.2) - 0.1, 0) * 5
        return min((revenue_growth + earnings_growth + margin_expansion) / 3, 1.0)
    
    def _calculate_financial_strength(self, features: Dict[str, float]) -> float:
        """Financial Strength Score (0-1)"""
        liquidity = min(features.get('current_ratio', 1.0), 2.0) / 2.0
        leverage = max(1 - features.get('debt_to_equity', 1) / 3, 0)
        cash_generation = min(features.get('free_cash_flow_margin', 0.1) * 5, 1.0)
        return (liquidity + leverage + cash_generation) / 3
    
    async def _store_fundamental_features(self, symbol: str, features: Dict[str, float]):
        """
        Speichert Fundamental-Features in der Datenbank
        """
        try:
            async with self.database_pool.acquire() as conn:
                # Verwende TimescaleDB-optimierte Tabelle
                await conn.execute("""
                    INSERT INTO ml_features_ts 
                    (symbol, feature_type, calculation_timestamp, features_json, 
                     feature_count, quality_score, missing_values_ratio, outlier_count)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, 
                symbol, "fundamental", datetime.utcnow(), json.dumps(features),
                len(features), 0.88, 0.0, 0)
                
                self.logger.info(f"Stored fundamental features for {symbol}")
                
        except Exception as e:
            self.logger.error(f"Failed to store fundamental features: {str(e)}")
    
    async def get_latest_fundamental_features(self, symbol: str) -> Dict[str, Any]:
        """
        Holt die neuesten Fundamental-Features für ein Symbol
        """
        try:
            async with self.database_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT features_json, feature_count, quality_score, calculation_timestamp
                    FROM ml_features_ts
                    WHERE symbol = $1 AND feature_type = 'fundamental'
                    ORDER BY calculation_timestamp DESC
                    LIMIT 1
                """, symbol)
                
                if not row:
                    return {"error": f"No fundamental features found for {symbol}"}
                
                features = json.loads(row['features_json'])
                
                return {
                    "symbol": symbol,
                    "feature_type": "fundamental",
                    "features": features,
                    "features_count": row['feature_count'],
                    "quality_score": float(row['quality_score']),
                    "calculated_at": row['calculation_timestamp'].isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get fundamental features for {symbol}: {str(e)}")
            return {"error": str(e)}

# Export für einfache Imports
__all__ = ['FundamentalFeatureEngine']