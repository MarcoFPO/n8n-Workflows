"""
💼 Portfolio Performance Analytics Provider
Provides comprehensive portfolio performance metrics and analytics
"""

import asyncio
import logging
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class PortfolioAnalyticsProvider:
    """Portfolio Performance Analytics Content Provider"""
    
    def __init__(self, event_bus, api_gateway):
        self.event_bus = event_bus
        self.api_gateway = api_gateway
        self.logger = logger
        
    async def get_portfolio_analytics_content(self, context: Dict[str, Any]) -> str:
        """Generate portfolio analytics dashboard content"""
        await self.event_bus.emit("frontend.portfolio_analytics.requested", {"context": context})
        
        # Get portfolio performance data
        portfolio_data = await self._get_portfolio_metrics()
        
        return f'''
        <div class="row">
            <!-- Portfolio Overview Cards -->
            <div class="col-md-3 mb-4">
                <div class="card bg-gradient-success text-white">
                    <div class="card-body text-center">
                        <i class="fas fa-chart-line fa-2x mb-2"></i>
                        <h3>{portfolio_data['total_return']:+.2f}%</h3>
                        <p class="mb-0">Gesamtrendite</p>
                        <small>YTD Performance</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-4">
                <div class="card bg-gradient-primary text-white">
                    <div class="card-body text-center">
                        <i class="fas fa-euro-sign fa-2x mb-2"></i>
                        <h3>{portfolio_data['total_value']:,.0f}€</h3>
                        <p class="mb-0">Portfolio-Wert</p>
                        <small>Aktueller Marktwert</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-4">
                <div class="card bg-gradient-warning text-white">
                    <div class="card-body text-center">
                        <i class="fas fa-balance-scale fa-2x mb-2"></i>
                        <h3>{portfolio_data['sharpe_ratio']:.2f}</h3>
                        <p class="mb-0">Sharpe Ratio</p>
                        <small>Risk-adjusted Return</small>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-4">
                <div class="card bg-gradient-danger text-white">
                    <div class="card-body text-center">
                        <i class="fas fa-arrow-down fa-2x mb-2"></i>
                        <h3>{portfolio_data['max_drawdown']:.2f}%</h3>
                        <p class="mb-0">Max Drawdown</p>
                        <small>Worst-Case Verlust</small>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <!-- Risk Metrics -->
            <div class="col-md-6 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-shield-alt me-2"></i>Risk Metrics</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-6 mb-3">
                                <div class="text-center">
                                    <h4 class="text-{self._get_var_color(portfolio_data['var_95'])}">{portfolio_data['var_95']:.2f}%</h4>
                                    <p class="mb-0">VaR (95%)</p>
                                    <small class="text-muted">1-Day Value at Risk</small>
                                </div>
                            </div>
                            <div class="col-6 mb-3">
                                <div class="text-center">
                                    <h4 class="text-info">{portfolio_data['beta']:.2f}</h4>
                                    <p class="mb-0">Portfolio Beta</p>
                                    <small class="text-muted">vs. DAX</small>
                                </div>
                            </div>
                            <div class="col-6 mb-3">
                                <div class="text-center">
                                    <h4 class="text-warning">{portfolio_data['volatility']:.2f}%</h4>
                                    <p class="mb-0">Volatilität</p>
                                    <small class="text-muted">30-Tage</small>
                                </div>
                            </div>
                            <div class="col-6 mb-3">
                                <div class="text-center">
                                    <h4 class="text-success">{portfolio_data['sortino_ratio']:.2f}</h4>
                                    <p class="mb-0">Sortino Ratio</p>
                                    <small class="text-muted">Downside Risk</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Performance Chart -->
            <div class="col-md-6 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-area me-2"></i>Performance Verlauf</h5>
                    </div>
                    <div class="card-body">
                        <div id="performance-chart" style="height: 250px;">
                            <div class="text-center p-4">
                                <i class="fas fa-chart-area fa-3x text-muted mb-3"></i>
                                <p class="text-muted">Performance Chart</p>
                                <small class="text-muted">Live-Chart wird geladen...</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <!-- Portfolio Holdings -->
            <div class="col-md-8 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-briefcase me-2"></i>Portfolio Positionen</h5>
                        <div class="card-tools">
                            <button class="btn btn-sm btn-primary" onclick="refreshPortfolio()">
                                <i class="fas fa-sync"></i> Aktualisieren
                            </button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Symbol</th>
                                        <th>Stück</th>
                                        <th>Ø Preis</th>
                                        <th>Aktuell</th>
                                        <th>Wert</th>
                                        <th>P&L</th>
                                        <th>P&L %</th>
                                        <th>Gewichtung</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {self._generate_holdings_table(portfolio_data['holdings'])}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Asset Allocation -->
            <div class="col-md-4 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-pie-chart me-2"></i>Asset Allocation</h5>
                    </div>
                    <div class="card-body">
                        <div id="allocation-chart" style="height: 300px;">
                            <div class="text-center p-4">
                                <i class="fas fa-pie-chart fa-3x text-muted mb-3"></i>
                                <p class="text-muted">Asset Allocation</p>
                                <small class="text-muted">Pie Chart wird geladen...</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Tax Calculation -->
        <div class="row">
            <div class="col-12 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-calculator me-2"></i>Steuerberechnung (Deutschland)</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-3 text-center">
                                <h4 class="text-success">{portfolio_data['tax_data']['gross_gain']:,.2f}€</h4>
                                <p class="mb-0">Brutto-Gewinn</p>
                            </div>
                            <div class="col-md-3 text-center">
                                <h4 class="text-warning">{portfolio_data['tax_data']['kest']:,.2f}€</h4>
                                <p class="mb-0">KESt (25%)</p>
                            </div>
                            <div class="col-md-3 text-center">
                                <h4 class="text-info">{portfolio_data['tax_data']['solz']:,.2f}€</h4>
                                <p class="mb-0">SolZ (5.5% auf KESt)</p>
                            </div>
                            <div class="col-md-3 text-center">
                                <h4 class="text-primary">{portfolio_data['tax_data']['net_gain']:,.2f}€</h4>
                                <p class="mb-0">Netto-Gewinn</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        function refreshPortfolio() {{
            // Refresh portfolio data
            location.reload();
        }}
        
        // Auto-refresh every 60 seconds
        setInterval(function() {{
            console.log('Auto-refreshing portfolio data...');
            // Will be implemented with WebSocket
        }}, 60000);
        </script>
        '''
    
    async def _get_portfolio_metrics(self) -> Dict[str, Any]:
        """Get portfolio performance metrics - mock data for now"""
        # TODO: Replace with real API calls to portfolio service
        return {
            'total_return': 12.45,
            'total_value': 157580.00,
            'sharpe_ratio': 1.85,
            'max_drawdown': -8.32,
            'var_95': -2.45,
            'beta': 1.12,
            'volatility': 18.5,
            'sortino_ratio': 2.15,
            'holdings': [
                {
                    'symbol': 'AAPL',
                    'shares': 150,
                    'avg_price': 135.50,
                    'current_price': 145.67,
                    'value': 21850.50,
                    'pnl': 1525.50,
                    'pnl_percent': 7.51,
                    'weight': 13.9
                },
                {
                    'symbol': 'MSFT',
                    'shares': 75,
                    'avg_price': 305.20,
                    'current_price': 312.45,
                    'value': 23433.75,
                    'pnl': 543.75,
                    'pnl_percent': 2.37,
                    'weight': 14.9
                },
                {
                    'symbol': 'GOOGL',
                    'shares': 200,
                    'avg_price': 115.30,
                    'current_price': 125.80,
                    'value': 25160.00,
                    'pnl': 2100.00,
                    'pnl_percent': 9.11,
                    'weight': 16.0
                },
                {
                    'symbol': 'NVDA',
                    'shares': 100,
                    'avg_price': 385.60,
                    'current_price': 418.95,
                    'value': 41895.00,
                    'pnl': 3335.00,
                    'pnl_percent': 8.65,
                    'weight': 26.6
                },
                {
                    'symbol': 'TSLA',
                    'shares': 180,
                    'avg_price': 265.80,
                    'current_price': 245.30,
                    'value': 44154.00,
                    'pnl': -3690.00,
                    'pnl_percent': -7.72,
                    'weight': 28.0
                }
            ],
            'tax_data': self._calculate_german_taxes(3814.25)
        }
    
    def _generate_holdings_table(self, holdings: List[Dict]) -> str:
        """Generate HTML table rows for portfolio holdings"""
        html = ""
        for holding in holdings:
            pnl_color = "success" if holding['pnl'] >= 0 else "danger"
            pnl_icon = "arrow-up" if holding['pnl'] >= 0 else "arrow-down"
            
            html += f'''
            <tr>
                <td><strong>{holding['symbol']}</strong></td>
                <td>{holding['shares']:,}</td>
                <td>{holding['avg_price']:.2f}€</td>
                <td>{holding['current_price']:.2f}€</td>
                <td>{holding['value']:,.2f}€</td>
                <td class="text-{pnl_color}">
                    <i class="fas fa-{pnl_icon}"></i> {holding['pnl']:+,.2f}€
                </td>
                <td class="text-{pnl_color}">
                    <strong>{holding['pnl_percent']:+.2f}%</strong>
                </td>
                <td>
                    <div class="progress" style="height: 8px;">
                        <div class="progress-bar" style="width: {holding['weight']}%"></div>
                    </div>
                    <small>{holding['weight']:.1f}%</small>
                </td>
            </tr>
            '''
        return html
    
    def _get_var_color(self, var: float) -> str:
        """Get color based on VaR value"""
        if var < -3:
            return "danger"
        elif var < -1.5:
            return "warning"
        else:
            return "success"
    
    def _calculate_german_taxes(self, gross_gain: float) -> dict:
        """
        Deutsche Steuerberechnung für private Kapitalerträge
        - 25% Kapitalertragsteuer (Abgeltungsteuer)
        - 5,5% Solidaritätszuschlag auf die Kapitalertragsteuer
        - KEINE Kirchensteuer (nicht zutreffend)
        - Gesamtsteuersatz: 26,375%
        """
        if gross_gain <= 0:
            return {
                'gross_gain': gross_gain,
                'kest': 0.0,
                'solz': 0.0,
                'total_tax': 0.0,
                'net_gain': gross_gain,
                'effective_rate': 0.0
            }
        
        # Deutsche Steuersätze
        KAPITALERTRAGSTEUER_RATE = 0.25    # 25%
        SOLIDARITAETSZUSCHLAG_RATE = 0.055  # 5,5%
        
        # Steuerberechnung
        kest = gross_gain * KAPITALERTRAGSTEUER_RATE
        solz = kest * SOLIDARITAETSZUSCHLAG_RATE  # SolZ auf KESt, nicht auf Gewinn
        total_tax = kest + solz
        net_gain = gross_gain - total_tax
        effective_rate = total_tax / gross_gain
        
        return {
            'gross_gain': round(gross_gain, 2),
            'kest': round(kest, 2),
            'solz': round(solz, 2),
            'total_tax': round(total_tax, 2),
            'net_gain': round(net_gain, 2),
            'effective_rate': round(effective_rate, 4),  # 0.26375 = 26,375%
            'effective_rate_percent': round(effective_rate * 100, 3)  # 26,375%
        }