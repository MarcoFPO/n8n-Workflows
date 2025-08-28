#!/usr/bin/env python3
"""
Portfolio Service Interfaces

Autor: Claude Code - Clean Architecture Interface Designer  
Datum: 26. August 2025
Clean Architecture v6.0.0 - Application Layer
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum


class OptimizationMethod(Enum):
    """Portfolio Optimization Methods"""
    MEAN_VARIANCE = "mean_variance"
    BLACK_LITTERMAN = "black_litterman"
    RISK_PARITY = "risk_parity"
    MINIMUM_VARIANCE = "minimum_variance"
    MAXIMUM_SHARPE = "maximum_sharpe"
    HIERARCHICAL_RISK_PARITY = "hierarchical_risk_parity"


class IPortfolioOptimizationService(ABC):
    """Interface für Portfolio Optimization"""
    
    @abstractmethod
    async def optimize_portfolio(self,
                               method: OptimizationMethod,
                               custom_weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Optimize portfolio using specified method"""
        pass
    
    @abstractmethod
    async def get_portfolio_risk_metrics(self) -> Dict[str, Any]:
        """Get comprehensive portfolio risk metrics"""
        pass
    
    @abstractmethod
    async def perform_stress_testing(self) -> Dict[str, Any]:
        """Perform portfolio stress testing scenarios"""
        pass
    
    @abstractmethod
    async def get_correlation_analysis(self) -> Dict[str, Any]:
        """Get portfolio correlation analysis"""
        pass


class IGlobalPortfolioService(ABC):
    """Interface für Global Portfolio Optimization"""
    
    @abstractmethod
    async def optimize_global_portfolio(self,
                                      allocation_strategy: str,
                                      target_risk: float,
                                      currency_hedge: bool = False,
                                      constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Optimize global multi-asset portfolio"""
        pass
    
    @abstractmethod
    async def get_asset_universe(self) -> Dict[str, Any]:
        """Get available asset universe for optimization"""
        pass
    
    @abstractmethod
    async def get_cross_asset_correlations(self) -> Dict[str, Any]:
        """Get cross-asset correlation matrix"""
        pass
    
    @abstractmethod
    async def get_sector_analysis(self) -> Dict[str, Any]:
        """Get sector-based analysis"""
        pass
    
    @abstractmethod
    async def get_cross_asset_signals(self) -> Dict[str, Any]:
        """Get cross-asset trading signals"""
        pass
    
    @abstractmethod
    async def get_risk_contagion_analysis(self) -> Dict[str, Any]:
        """Get risk contagion analysis across assets"""
        pass


class IMultiAssetCorrelationService(ABC):
    """Interface für Multi-Asset Correlation Engine"""
    
    @abstractmethod
    async def get_multi_asset_status(self) -> Dict[str, Any]:
        """Get multi-asset correlation engine status"""
        pass
    
    @abstractmethod
    async def calculate_cross_correlations(self,
                                         asset_classes: List[str],
                                         lookback_days: int = 252) -> Dict[str, Any]:
        """Calculate cross-asset correlations"""
        pass
    
    @abstractmethod
    async def detect_correlation_regime_changes(self) -> Dict[str, Any]:
        """Detect correlation regime changes"""
        pass
    
    @abstractmethod
    async def get_correlation_heatmap(self,
                                    asset_classes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get correlation heatmap data"""
        pass


class IMarketMicrostructureService(ABC):
    """Interface für Market Microstructure Analytics"""
    
    @abstractmethod
    async def get_microstructure_status(self) -> Dict[str, Any]:
        """Get market microstructure engine status"""
        pass
    
    @abstractmethod
    async def get_microstructure_metrics(self, symbol: str) -> Dict[str, Any]:
        """Get microstructure metrics for symbol"""
        pass
    
    @abstractmethod
    async def get_liquidity_metrics(self, symbol: str) -> Dict[str, Any]:
        """Get liquidity metrics for symbol"""
        pass
    
    @abstractmethod
    async def get_hft_patterns(self, symbol: str) -> Dict[str, Any]:
        """Get high-frequency trading patterns"""
        pass
    
    @abstractmethod
    async def get_transaction_costs(self, symbol: str) -> Dict[str, Any]:
        """Get estimated transaction costs"""
        pass
    
    @abstractmethod
    async def get_order_book_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get order book analysis"""
        pass
    
    @abstractmethod
    async def get_tracked_symbols(self) -> List[str]:
        """Get list of tracked symbols"""
        pass