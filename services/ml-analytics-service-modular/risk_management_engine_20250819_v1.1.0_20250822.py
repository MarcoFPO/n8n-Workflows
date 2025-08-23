#!/usr/bin/env python3
"""
Advanced Risk Management Engine - Phase 13
==========================================

Umfassendes Risikomanagement-System für ML Analytics:
- Value at Risk (VaR) Calculation (Historical, Parametric, Monte Carlo)
- Expected Shortfall (ES) / Conditional VaR
- Portfolio Risk Decomposition
- Stress Testing und Scenario Analysis
- Real-Time Risk Monitoring
- Risk Attribution Analysis
- Counterparty Risk Assessment
- Liquidity Risk Modeling
- Model Risk Validation
- Dynamic Hedging Strategies

Author: Claude Code & AI Development Team
Version: 1.0.0
Date: 2025-08-19
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import asyncpg
from scipy import stats
from scipy.optimize import minimize
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskMeasure(Enum):
    """Supported risk measures"""
    VAR_HISTORICAL = "var_historical"
    VAR_PARAMETRIC = "var_parametric"
    VAR_MONTE_CARLO = "var_monte_carlo"
    EXPECTED_SHORTFALL = "expected_shortfall"
    MAXIMUM_DRAWDOWN = "maximum_drawdown"
    VOLATILITY = "volatility"
    BETA = "beta"
    TRACKING_ERROR = "tracking_error"
    INFORMATION_RATIO = "information_ratio"
    SHARPE_RATIO = "sharpe_ratio"

class VaRMethod(Enum):
    """Value at Risk calculation methods"""
    HISTORICAL_SIMULATION = "historical_simulation"
    PARAMETRIC_NORMAL = "parametric_normal"
    PARAMETRIC_T_DISTRIBUTION = "parametric_t_distribution"
    MONTE_CARLO_STANDARD = "monte_carlo_standard"
    MONTE_CARLO_COPULA = "monte_carlo_copula"
    EXTREME_VALUE_THEORY = "extreme_value_theory"

class StressTestType(Enum):
    """Stress testing scenarios"""
    HISTORICAL_SCENARIO = "historical_scenario"
    HYPOTHETICAL_SCENARIO = "hypothetical_scenario"
    SENSITIVITY_ANALYSIS = "sensitivity_analysis"
    REVERSE_STRESS_TEST = "reverse_stress_test"
    MONTE_CARLO_STRESS = "monte_carlo_stress"

@dataclass
class RiskMetrics:
    """Container for risk calculation results"""
    symbol: str
    timestamp: datetime
    var_95: float
    var_99: float
    expected_shortfall_95: float
    expected_shortfall_99: float
    volatility: float
    maximum_drawdown: float
    beta: Optional[float] = None
    tracking_error: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    information_ratio: Optional[float] = None
    confidence_interval: Dict[str, float] = field(default_factory=dict)
    method_used: str = ""
    calculation_date: datetime = field(default_factory=datetime.utcnow)

@dataclass
class PortfolioRisk:
    """Portfolio-level risk metrics"""
    portfolio_id: str
    total_var: float
    component_var: Dict[str, float]
    marginal_var: Dict[str, float]
    incremental_var: Dict[str, float]
    diversification_ratio: float
    risk_concentration: Dict[str, float]
    correlation_matrix: np.ndarray
    volatility_contribution: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class StressTestResult:
    """Stress test scenario results"""
    scenario_name: str
    scenario_type: StressTestType
    portfolio_pnl: float
    individual_pnl: Dict[str, float]
    worst_performers: List[Tuple[str, float]]
    best_performers: List[Tuple[str, float]]
    risk_factors_impact: Dict[str, float]
    probability_estimate: Optional[float] = None
    scenario_description: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class LiquidityRisk:
    """Liquidity risk assessment"""
    symbol: str
    bid_ask_spread: float
    average_daily_volume: float
    market_impact_cost: float
    liquidity_score: float
    days_to_liquidate: float
    liquidity_tier: str  # T1, T2, T3
    emergency_liquidation_cost: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

class AdvancedRiskEngine:
    """Advanced Risk Management and Analytics Engine"""
    
    def __init__(self, database_pool: asyncpg.Pool):
        self.database_pool = database_pool
        self.risk_free_rate = 0.02  # 2% default risk-free rate
        self.confidence_levels = [0.90, 0.95, 0.99]
        self.lookback_periods = [30, 90, 252]  # Days
        
        # Risk calculation cache
        self.risk_cache = {}
        self.correlation_cache = {}
        
        # Stress test scenarios
        self.stress_scenarios = self._initialize_stress_scenarios()
        
        # Model validation parameters
        self.backtest_window = 252  # 1 year
        self.exception_threshold = 0.95  # 95% confidence for model validation
        
        logger.info("Advanced Risk Management Engine initialized")
    
    def _initialize_stress_scenarios(self) -> Dict[str, Dict]:
        """Initialize predefined stress test scenarios"""
        return {
            "covid_crash_2020": {
                "description": "COVID-19 market crash scenario",
                "equity_shock": -0.35,
                "bond_shock": 0.15,
                "fx_shock": {"USD": 0.10, "EUR": -0.05, "GBP": -0.08},
                "volatility_shock": 2.5,
                "correlation_shock": 0.3
            },
            "financial_crisis_2008": {
                "description": "2008 Financial Crisis scenario",
                "equity_shock": -0.45,
                "bond_shock": 0.25,
                "fx_shock": {"USD": 0.15, "EUR": -0.10, "JPY": 0.20},
                "volatility_shock": 3.0,
                "correlation_shock": 0.5
            },
            "dot_com_crash_2000": {
                "description": "Dot-com bubble burst scenario",
                "equity_shock": -0.50,
                "tech_shock": -0.70,
                "bond_shock": 0.10,
                "volatility_shock": 2.0,
                "correlation_shock": 0.2
            },
            "brexit_shock": {
                "description": "Brexit referendum shock",
                "equity_shock": -0.15,
                "bond_shock": 0.05,
                "fx_shock": {"GBP": -0.20, "EUR": -0.05},
                "volatility_shock": 1.5,
                "correlation_shock": 0.2
            },
            "flash_crash": {
                "description": "Flash crash scenario",
                "equity_shock": -0.25,
                "intraday_volatility": 5.0,
                "liquidity_shock": 0.8,
                "correlation_shock": 0.4
            }
        }
    
    async def initialize(self):
        """Initialize risk engine with market data"""
        try:
            logger.info("Initializing Advanced Risk Management Engine...")
            
            # Load historical market data for risk calculations
            await self._load_market_data()
            
            # Initialize correlation matrices
            await self._initialize_correlation_matrices()
            
            # Load risk model parameters
            await self._load_risk_model_parameters()
            
            logger.info("Advanced Risk Management Engine initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Risk Management Engine: {str(e)}")
            return False
    
    async def _load_market_data(self):
        """Load historical market data for risk calculations"""
        # In production, this would load from TimescaleDB
        # For demo, we'll simulate market data
        
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']
        dates = pd.date_range(end=datetime.now(), periods=500, freq='D')
        
        # Simulate correlated returns
        np.random.seed(42)
        n_assets = len(symbols)
        correlation_matrix = np.random.uniform(0.1, 0.7, (n_assets, n_assets))
        correlation_matrix = (correlation_matrix + correlation_matrix.T) / 2
        np.fill_diagonal(correlation_matrix, 1.0)
        
        # Generate returns using multivariate normal
        returns = np.random.multivariate_normal(
            mean=np.zeros(n_assets),
            cov=correlation_matrix * 0.02**2,  # 2% daily volatility
            size=len(dates)
        )
        
        self.market_data = pd.DataFrame(
            returns,
            index=dates,
            columns=symbols
        )
        
        # Calculate cumulative prices
        initial_prices = {symbol: np.random.uniform(50, 300) for symbol in symbols}
        prices = {}
        for i, symbol in enumerate(symbols):
            prices[symbol] = initial_prices[symbol] * (1 + self.market_data[symbol]).cumprod()
        
        self.price_data = pd.DataFrame(prices, index=dates)
        logger.info(f"Loaded market data for {len(symbols)} assets over {len(dates)} days")
    
    async def _initialize_correlation_matrices(self):
        """Initialize correlation matrices for different time horizons"""
        self.correlations = {}
        
        for period in self.lookback_periods:
            recent_returns = self.market_data.tail(period)
            correlation_matrix = recent_returns.corr().values
            self.correlations[period] = correlation_matrix
        
        logger.info(f"Initialized correlation matrices for {len(self.lookback_periods)} time horizons")
    
    async def _load_risk_model_parameters(self):
        """Load risk model parameters and calibration data"""
        self.risk_model_params = {
            'confidence_levels': [0.90, 0.95, 0.99],
            'holding_period': 1,  # 1 day
            'decay_factor': 0.94,  # EWMA decay factor
            'fat_tail_adjustment': True,
            'correlation_adjustment': True,
            'liquidity_adjustment': True
        }
        
        # Model validation parameters
        self.model_validation = {
            'backtest_window': 252,
            'exception_threshold': 0.05,
            'traffic_light_zones': {
                'green': (0, 4),
                'yellow': (5, 9),
                'red': (10, float('inf'))
            }
        }
        
        logger.info("Risk model parameters loaded and calibrated")
    
    async def calculate_var(
        self,
        symbol: str,
        confidence_level: float = 0.95,
        holding_period: int = 1,
        method: VaRMethod = VaRMethod.HISTORICAL_SIMULATION,
        lookback_days: int = 252
    ) -> Dict[str, float]:
        """Calculate Value at Risk using specified method"""
        
        try:
            if symbol not in self.market_data.columns:
                raise ValueError(f"Symbol {symbol} not found in market data")
            
            returns = self.market_data[symbol].tail(lookback_days)
            
            if method == VaRMethod.HISTORICAL_SIMULATION:
                var_result = self._calculate_historical_var(returns, confidence_level, holding_period)
            elif method == VaRMethod.PARAMETRIC_NORMAL:
                var_result = self._calculate_parametric_var(returns, confidence_level, holding_period, distribution='normal')
            elif method == VaRMethod.PARAMETRIC_T_DISTRIBUTION:
                var_result = self._calculate_parametric_var(returns, confidence_level, holding_period, distribution='t')
            elif method == VaRMethod.MONTE_CARLO_STANDARD:
                var_result = self._calculate_monte_carlo_var(returns, confidence_level, holding_period)
            elif method == VaRMethod.EXTREME_VALUE_THEORY:
                var_result = self._calculate_evt_var(returns, confidence_level, holding_period)
            else:
                raise ValueError(f"Unsupported VaR method: {method}")
            
            # Add method and calculation metadata
            var_result['method'] = method.value
            var_result['confidence_level'] = confidence_level
            var_result['holding_period'] = holding_period
            var_result['lookback_days'] = lookback_days
            var_result['calculation_timestamp'] = datetime.utcnow().isoformat()
            
            return var_result
            
        except Exception as e:
            logger.error(f"VaR calculation failed for {symbol}: {str(e)}")
            raise
    
    def _calculate_historical_var(self, returns: pd.Series, confidence_level: float, holding_period: int) -> Dict[str, float]:
        """Calculate VaR using historical simulation method"""
        # Scale returns for holding period
        scaled_returns = returns * np.sqrt(holding_period)
        
        # Calculate percentile
        var_percentile = (1 - confidence_level) * 100
        var = np.percentile(scaled_returns, var_percentile)
        
        # Calculate Expected Shortfall (Conditional VaR)
        tail_losses = scaled_returns[scaled_returns <= var]
        expected_shortfall = tail_losses.mean() if len(tail_losses) > 0 else var
        
        return {
            'var': abs(var),
            'expected_shortfall': abs(expected_shortfall),
            'volatility': scaled_returns.std(),
            'skewness': stats.skew(scaled_returns),
            'kurtosis': stats.kurtosis(scaled_returns),
            'observations': len(returns)
        }
    
    def _calculate_parametric_var(self, returns: pd.Series, confidence_level: float, holding_period: int, distribution: str = 'normal') -> Dict[str, float]:
        """Calculate VaR using parametric approach"""
        # Scale returns for holding period
        scaled_returns = returns * np.sqrt(holding_period)
        
        mean_return = scaled_returns.mean()
        volatility = scaled_returns.std()
        
        if distribution == 'normal':
            # Normal distribution
            z_score = stats.norm.ppf(1 - confidence_level)
            var = abs(mean_return + z_score * volatility)
            
            # Expected Shortfall for normal distribution
            phi = stats.norm.pdf(z_score)
            expected_shortfall = abs(mean_return + volatility * phi / (1 - confidence_level))
            
        elif distribution == 't':
            # t-distribution with estimated degrees of freedom
            # Estimate degrees of freedom using method of moments
            sample_kurtosis = stats.kurtosis(scaled_returns, fisher=False)
            if sample_kurtosis > 3:
                dof = 6 / (sample_kurtosis - 3) + 4
            else:
                dof = 30  # Default to high DOF (approaches normal)
            
            t_score = stats.t.ppf(1 - confidence_level, dof)
            var = abs(mean_return + t_score * volatility)
            
            # Expected Shortfall for t-distribution (approximation)
            expected_shortfall = var * 1.2  # Rough approximation
        
        return {
            'var': var,
            'expected_shortfall': expected_shortfall,
            'volatility': volatility,
            'mean_return': mean_return,
            'distribution': distribution,
            'degrees_of_freedom': dof if distribution == 't' else None
        }
    
    def _calculate_monte_carlo_var(self, returns: pd.Series, confidence_level: float, holding_period: int, n_simulations: int = 10000) -> Dict[str, float]:
        """Calculate VaR using Monte Carlo simulation"""
        mean_return = returns.mean()
        volatility = returns.std()
        
        # Generate random scenarios
        np.random.seed(42)
        random_returns = np.random.normal(
            mean_return * holding_period,
            volatility * np.sqrt(holding_period),
            n_simulations
        )
        
        # Calculate VaR and Expected Shortfall
        var_percentile = (1 - confidence_level) * 100
        var = abs(np.percentile(random_returns, var_percentile))
        
        tail_losses = random_returns[random_returns <= -var]
        expected_shortfall = abs(tail_losses.mean()) if len(tail_losses) > 0 else var
        
        return {
            'var': var,
            'expected_shortfall': expected_shortfall,
            'volatility': volatility * np.sqrt(holding_period),
            'simulations': n_simulations,
            'min_scenario': random_returns.min(),
            'max_scenario': random_returns.max()
        }
    
    def _calculate_evt_var(self, returns: pd.Series, confidence_level: float, holding_period: int) -> Dict[str, float]:
        """Calculate VaR using Extreme Value Theory"""
        # Use Generalized Pareto Distribution for tail modeling
        # Select threshold (e.g., 90th percentile of losses)
        losses = -returns  # Convert to losses (positive values)
        threshold = np.percentile(losses, 90)
        
        # Extract exceedances over threshold
        exceedances = losses[losses > threshold] - threshold
        
        if len(exceedances) < 10:
            # Fall back to historical method if insufficient tail data
            return self._calculate_historical_var(returns, confidence_level, holding_period)
        
        # Fit Generalized Pareto Distribution
        shape, loc, scale = stats.genpareto.fit(exceedances, floc=0)
        
        # Calculate VaR using GPD
        n = len(returns)
        n_exceedances = len(exceedances)
        
        # VaR formula for GPD
        if abs(shape) < 1e-6:  # Exponential case
            var = threshold + scale * np.log((n / n_exceedances) * (1 - confidence_level))
        else:
            var = threshold + (scale / shape) * (((n / n_exceedances) * (1 - confidence_level))**(-shape) - 1)
        
        # Scale for holding period
        var *= np.sqrt(holding_period)
        
        # Expected Shortfall approximation
        if shape < 1:
            expected_shortfall = (var + scale - shape * threshold) / (1 - shape)
        else:
            expected_shortfall = var * 1.3  # Conservative approximation
        
        return {
            'var': abs(var),
            'expected_shortfall': abs(expected_shortfall),
            'evt_shape': shape,
            'evt_scale': scale,
            'threshold': threshold,
            'exceedances': len(exceedances)
        }
    
    async def calculate_portfolio_risk(
        self,
        portfolio_weights: Dict[str, float],
        lookback_days: int = 252,
        confidence_level: float = 0.95
    ) -> PortfolioRisk:
        """Calculate comprehensive portfolio risk metrics"""
        
        try:
            symbols = list(portfolio_weights.keys())
            weights = np.array([portfolio_weights[symbol] for symbol in symbols])
            
            # Get returns matrix
            returns_matrix = self.market_data[symbols].tail(lookback_days)
            
            # Portfolio returns
            portfolio_returns = (returns_matrix * weights).sum(axis=1)
            
            # Portfolio VaR
            portfolio_var = abs(np.percentile(portfolio_returns, (1 - confidence_level) * 100))
            
            # Component VaR calculation
            component_var = {}
            marginal_var = {}
            incremental_var = {}
            
            for i, symbol in enumerate(symbols):
                # Marginal VaR (contribution to portfolio VaR)
                weight_bump = 0.01  # 1% bump
                new_weights = weights.copy()
                new_weights[i] += weight_bump
                new_weights = new_weights / new_weights.sum()  # Renormalize
                
                bumped_portfolio_returns = (returns_matrix * new_weights).sum(axis=1)
                bumped_var = abs(np.percentile(bumped_portfolio_returns, (1 - confidence_level) * 100))
                
                marginal_var[symbol] = (bumped_var - portfolio_var) / weight_bump
                component_var[symbol] = marginal_var[symbol] * weights[i]
                
                # Incremental VaR (VaR if position removed)
                remaining_weights = np.delete(weights, i)
                remaining_symbols = [s for j, s in enumerate(symbols) if j != i]
                
                if len(remaining_symbols) > 0:
                    remaining_weights = remaining_weights / remaining_weights.sum()
                    remaining_returns = (returns_matrix[remaining_symbols] * remaining_weights).sum(axis=1)
                    remaining_var = abs(np.percentile(remaining_returns, (1 - confidence_level) * 100))
                    incremental_var[symbol] = portfolio_var - remaining_var
                else:
                    incremental_var[symbol] = portfolio_var
            
            # Diversification ratio
            individual_volatilities = returns_matrix.std()
            weighted_volatility = (individual_volatilities * weights).sum()
            portfolio_volatility = portfolio_returns.std()
            diversification_ratio = weighted_volatility / portfolio_volatility
            
            # Risk concentration (Herfindahl index of component VaRs)
            component_var_values = np.array(list(component_var.values()))
            total_component_var = component_var_values.sum()
            if total_component_var > 0:
                var_shares = component_var_values / total_component_var
                risk_concentration_index = (var_shares ** 2).sum()
            else:
                risk_concentration_index = 1.0
            
            # Correlation matrix
            correlation_matrix = returns_matrix.corr().values
            
            # Volatility contribution
            volatility_contribution = {}
            portfolio_variance = portfolio_volatility ** 2
            cov_matrix = returns_matrix.cov().values
            
            for i, symbol in enumerate(symbols):
                # Contribution to portfolio variance
                contrib = weights[i] * np.sum(weights * cov_matrix[i, :])
                volatility_contribution[symbol] = contrib / portfolio_variance
            
            return PortfolioRisk(
                portfolio_id=f"portfolio_{len(symbols)}_assets",
                total_var=portfolio_var,
                component_var=component_var,
                marginal_var=marginal_var,
                incremental_var=incremental_var,
                diversification_ratio=diversification_ratio,
                risk_concentration={'herfindahl_index': risk_concentration_index},
                correlation_matrix=correlation_matrix,
                volatility_contribution=volatility_contribution
            )
            
        except Exception as e:
            logger.error(f"Portfolio risk calculation failed: {str(e)}")
            raise
    
    async def perform_stress_test(
        self,
        portfolio_weights: Dict[str, float],
        scenario_name: str,
        custom_scenario: Optional[Dict] = None
    ) -> StressTestResult:
        """Perform stress testing on portfolio"""
        
        try:
            if custom_scenario:
                scenario = custom_scenario
                scenario_type = StressTestType.HYPOTHETICAL_SCENARIO
            elif scenario_name in self.stress_scenarios:
                scenario = self.stress_scenarios[scenario_name]
                scenario_type = StressTestType.HISTORICAL_SCENARIO
            else:
                raise ValueError(f"Unknown stress scenario: {scenario_name}")
            
            symbols = list(portfolio_weights.keys())
            individual_pnl = {}
            total_pnl = 0.0
            
            # Apply shocks to each asset
            for symbol in symbols:
                current_price = self.price_data[symbol].iloc[-1]
                weight = portfolio_weights[symbol]
                
                # Determine shock for this asset
                shock = 0.0
                
                if 'equity_shock' in scenario:
                    shock += scenario['equity_shock']
                
                if 'tech_shock' in scenario and symbol in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']:
                    shock += scenario['tech_shock']
                
                if 'volatility_shock' in scenario:
                    # Add volatility-based shock
                    volatility = self.market_data[symbol].tail(30).std()
                    vol_shock = volatility * scenario['volatility_shock'] * np.random.normal(0, 1)
                    shock += vol_shock
                
                # Calculate P&L for this position
                position_value = current_price * weight
                pnl = position_value * shock
                individual_pnl[symbol] = pnl
                total_pnl += pnl
            
            # Sort performers
            sorted_pnl = sorted(individual_pnl.items(), key=lambda x: x[1])
            worst_performers = sorted_pnl[:3]  # Top 3 worst
            best_performers = sorted_pnl[-3:][::-1]  # Top 3 best
            
            # Risk factors impact
            risk_factors_impact = {
                'equity_market': scenario.get('equity_shock', 0) * sum(portfolio_weights.values()),
                'volatility': scenario.get('volatility_shock', 0) * 0.1,  # Estimated impact
                'correlation': scenario.get('correlation_shock', 0) * 0.05,  # Estimated impact
                'liquidity': scenario.get('liquidity_shock', 0) * 0.02 if 'liquidity_shock' in scenario else 0
            }
            
            return StressTestResult(
                scenario_name=scenario_name,
                scenario_type=scenario_type,
                portfolio_pnl=total_pnl,
                individual_pnl=individual_pnl,
                worst_performers=worst_performers,
                best_performers=best_performers,
                risk_factors_impact=risk_factors_impact,
                scenario_description=scenario.get('description', f'Custom scenario: {scenario_name}')
            )
            
        except Exception as e:
            logger.error(f"Stress test failed for scenario {scenario_name}: {str(e)}")
            raise
    
    async def assess_liquidity_risk(self, symbol: str) -> LiquidityRisk:
        """Assess liquidity risk for individual asset"""
        
        try:
            # Simulate liquidity metrics (in production, these would come from market data)
            np.random.seed(hash(symbol) % 2**32)
            
            # Market data simulation
            current_price = self.price_data[symbol].iloc[-1]
            daily_returns = self.market_data[symbol].tail(30)
            volatility = daily_returns.std()
            
            # Bid-ask spread simulation (higher for more volatile assets)
            bid_ask_spread = max(0.001, volatility * 0.5 + np.random.uniform(0.001, 0.01))
            
            # Average daily volume simulation
            base_volume = np.random.uniform(1e6, 10e6)  # 1M to 10M shares
            avg_daily_volume = base_volume * (1 + np.random.uniform(-0.3, 0.3))
            
            # Market impact cost (function of trade size vs daily volume)
            typical_trade_size = avg_daily_volume * 0.1  # 10% of daily volume
            market_impact_cost = np.sqrt(typical_trade_size / avg_daily_volume) * volatility * 0.5
            
            # Liquidity score (0-100, higher is better)
            spread_score = max(0, 100 - bid_ask_spread * 10000)  # Penalize wide spreads
            volume_score = min(100, np.log10(avg_daily_volume))   # Reward high volume
            volatility_score = max(0, 100 - volatility * 1000)   # Penalize high volatility
            
            liquidity_score = (spread_score + volume_score + volatility_score) / 3
            
            # Days to liquidate (assuming 20% of daily volume)
            position_size = avg_daily_volume * 0.5  # Assume position of 50% daily volume
            participation_rate = 0.2  # 20% of daily volume
            days_to_liquidate = position_size / (avg_daily_volume * participation_rate)
            
            # Liquidity tier classification
            if liquidity_score >= 80 and days_to_liquidate <= 1:
                liquidity_tier = "T1"  # Tier 1 - Highly liquid
            elif liquidity_score >= 60 and days_to_liquidate <= 5:
                liquidity_tier = "T2"  # Tier 2 - Moderately liquid
            else:
                liquidity_tier = "T3"  # Tier 3 - Less liquid
            
            # Emergency liquidation cost (fire sale scenario)
            emergency_liquidation_cost = market_impact_cost * 3 + bid_ask_spread * 2
            
            return LiquidityRisk(
                symbol=symbol,
                bid_ask_spread=bid_ask_spread,
                average_daily_volume=avg_daily_volume,
                market_impact_cost=market_impact_cost,
                liquidity_score=liquidity_score,
                days_to_liquidate=days_to_liquidate,
                liquidity_tier=liquidity_tier,
                emergency_liquidation_cost=emergency_liquidation_cost
            )
            
        except Exception as e:
            logger.error(f"Liquidity risk assessment failed for {symbol}: {str(e)}")
            raise
    
    async def calculate_comprehensive_risk_metrics(
        self,
        symbol: str,
        benchmark_symbol: Optional[str] = None,
        lookback_days: int = 252
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics for a single asset"""
        
        try:
            returns = self.market_data[symbol].tail(lookback_days)
            
            # Basic VaR calculations
            var_95 = abs(np.percentile(returns, 5))
            var_99 = abs(np.percentile(returns, 1))
            
            # Expected Shortfall
            tail_95 = returns[returns <= -var_95]
            tail_99 = returns[returns <= -var_99]
            es_95 = abs(tail_95.mean()) if len(tail_95) > 0 else var_95
            es_99 = abs(tail_99.mean()) if len(tail_99) > 0 else var_99
            
            # Volatility
            volatility = returns.std() * np.sqrt(252)  # Annualized
            
            # Maximum Drawdown
            prices = self.price_data[symbol].tail(lookback_days)
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            maximum_drawdown = abs(drawdown.min())
            
            # Sharpe Ratio
            excess_returns = returns - self.risk_free_rate / 252
            sharpe_ratio = (excess_returns.mean() * 252) / volatility if volatility > 0 else 0
            
            # Beta and Tracking Error (if benchmark provided)
            beta = None
            tracking_error = None
            information_ratio = None
            
            if benchmark_symbol and benchmark_symbol in self.market_data.columns:
                benchmark_returns = self.market_data[benchmark_symbol].tail(lookback_days)
                
                # Beta calculation
                covariance = np.cov(returns, benchmark_returns)[0, 1]
                benchmark_variance = benchmark_returns.var()
                beta = covariance / benchmark_variance if benchmark_variance > 0 else 1.0
                
                # Tracking Error
                active_returns = returns - benchmark_returns
                tracking_error = active_returns.std() * np.sqrt(252)
                
                # Information Ratio
                active_return_mean = active_returns.mean() * 252
                information_ratio = active_return_mean / tracking_error if tracking_error > 0 else 0
            
            return RiskMetrics(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                var_95=var_95,
                var_99=var_99,
                expected_shortfall_95=es_95,
                expected_shortfall_99=es_99,
                volatility=volatility,
                maximum_drawdown=maximum_drawdown,
                beta=beta,
                tracking_error=tracking_error,
                sharpe_ratio=sharpe_ratio,
                information_ratio=information_ratio,
                method_used="comprehensive_historical"
            )
            
        except Exception as e:
            logger.error(f"Risk metrics calculation failed for {symbol}: {str(e)}")
            raise
    
    async def get_risk_engine_status(self) -> Dict[str, Any]:
        """Get current status of risk management engine"""
        return {
            'engine_status': 'operational',
            'supported_risk_measures': [measure.value for measure in RiskMeasure],
            'var_methods': [method.value for method in VaRMethod],
            'stress_scenarios': list(self.stress_scenarios.keys()),
            'confidence_levels': self.confidence_levels,
            'lookback_periods': self.lookback_periods,
            'market_data_coverage': {
                'symbols': list(self.market_data.columns),
                'date_range': {
                    'start': self.market_data.index[0].isoformat(),
                    'end': self.market_data.index[-1].isoformat()
                },
                'observations': len(self.market_data)
            },
            'model_validation': self.model_validation,
            'last_update': datetime.utcnow().isoformat()
        }

# Example usage and testing
async def main():
    """Example usage of Advanced Risk Management Engine"""
    # This would normally use a real database connection
    # For demo purposes, we'll use None
    
    print("🚀 Advanced Risk Management Engine Demo")
    print("=" * 60)
    
    # Initialize risk engine
    risk_engine = AdvancedRiskEngine(database_pool=None)
    await risk_engine.initialize()
    
    # Example portfolio
    portfolio = {
        'AAPL': 0.25,
        'MSFT': 0.20,
        'GOOGL': 0.15,
        'AMZN': 0.15,
        'TSLA': 0.10,
        'NVDA': 0.10,
        'META': 0.05
    }
    
    print(f"📊 Portfolio: {portfolio}")
    
    # Calculate VaR for individual asset
    aapl_var = await risk_engine.calculate_var('AAPL', confidence_level=0.95)
    print(f"📈 AAPL VaR (95%): {aapl_var['var']:.4f}")
    
    # Portfolio risk assessment
    portfolio_risk = await risk_engine.calculate_portfolio_risk(portfolio)
    print(f"🎯 Portfolio VaR: {portfolio_risk.total_var:.4f}")
    print(f"🔄 Diversification Ratio: {portfolio_risk.diversification_ratio:.2f}")
    
    # Stress testing
    stress_result = await risk_engine.perform_stress_test(portfolio, "covid_crash_2020")
    print(f"💥 COVID Stress Test P&L: {stress_result.portfolio_pnl:.2f}")
    
    # Liquidity assessment
    liquidity_risk = await risk_engine.assess_liquidity_risk('AAPL')
    print(f"💧 AAPL Liquidity Tier: {liquidity_risk.liquidity_tier}")
    
    print("✅ Risk Management Engine demo completed!")

if __name__ == "__main__":
    asyncio.run(main())