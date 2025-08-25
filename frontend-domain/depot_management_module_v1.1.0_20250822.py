#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 Depot-Management Module für GUI
Umfassendes Portfolio- und Depotverwaltungs-Interface basierend auf den Vorgaben
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import json
import uuid
from dataclasses import dataclass, asdict

# Import Management - Clean Architecture
from shared.standard_import_manager_v1_0_0_20250824 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces sys.path.append(str(Path(__file__).parent.parent))

# Import des zentralen Fallback-Systems
from core.unified_fallback_provider import fallback_provider


@dataclass
class Portfolio:
    """Portfolio-Datenmodell basierend auf API-Spezifikation"""
    portfolio_id: str
    name: str
    description: str
    currency: str
    total_value: float
    cash_balance: float
    target_allocation: Dict[str, float]
    risk_profile: str
    created_at: str
    last_updated: str
    performance_ytd: float = 0.0
    performance_1m: float = 0.0
    performance_3m: float = 0.0
    performance_1y: float = 0.0

@dataclass 
class Position:
    """Position-Datenmodell"""
    position_id: str
    portfolio_id: str
    asset_symbol: str
    asset_name: str
    quantity: float
    average_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    weight: float
    sector: str
    asset_class: str

@dataclass
class Order:
    """Order-Datenmodell"""
    order_id: str
    portfolio_id: str
    asset_symbol: str
    side: str  # buy/sell
    order_type: str
    quantity: float
    price: Optional[float]
    status: str
    created_at: str
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None


class DepotContentProvider(ABC):
    """Basis für Depot-Content-Provider"""
    
    def __init__(self, event_bus, api_gateway):
        self.event_bus = event_bus
        self.api_gateway = api_gateway
        
    @abstractmethod
    async def get_content(self, context: Dict[str, Any]) -> str:
        pass


class PortfolioOverviewProvider(DepotContentProvider):
    """Portfolio-Übersicht Content Provider"""
    
    async def get_content(self, context: Dict[str, Any]) -> str:
        await self.event_bus.emit("depot.portfolio.overview.requested", {"context": context})
        
        # Mock-Daten für Portfolio-Übersicht
        portfolios = self._get_mock_portfolios()
        
        portfolio_cards = ""
        for portfolio in portfolios:
            performance_class = "text-success" if portfolio.performance_ytd >= 0 else "text-danger"
            performance_icon = "fa-arrow-up text-success" if portfolio.performance_ytd >= 0 else "fa-arrow-down text-danger"
            
            portfolio_cards += f'''
            <div class="col-md-6 col-lg-4 mb-4">
                <div class="card portfolio-card h-100" onclick="selectPortfolio('{portfolio.portfolio_id}')">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">{portfolio.name}</h6>
                        <span class="badge bg-primary">{portfolio.currency}</span>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-6">
                                <h4 class="mb-1">{portfolio.total_value:,.2f} €</h4>
                                <small class="text-muted">Gesamtwert</small>
                            </div>
                            <div class="col-6 text-end">
                                <h5 class="{performance_class} mb-1">
                                    <i class="fas {performance_icon}"></i> {portfolio.performance_ytd:+.2f}%
                                </h5>
                                <small class="text-muted">YTD Performance</small>
                            </div>
                        </div>
                        <hr>
                        <div class="row text-center">
                            <div class="col-4">
                                <strong>{portfolio.performance_1m:+.1f}%</strong>
                                <br><small class="text-muted">1M</small>
                            </div>
                            <div class="col-4">
                                <strong>{portfolio.performance_3m:+.1f}%</strong>
                                <br><small class="text-muted">3M</small>
                            </div>
                            <div class="col-4">
                                <strong>{portfolio.performance_1y:+.1f}%</strong>
                                <br><small class="text-muted">1Y</small>
                            </div>
                        </div>
                        <div class="mt-3">
                            <div class="d-flex justify-content-between">
                                <small>Cash:</small>
                                <small>{portfolio.cash_balance:,.2f} €</small>
                            </div>
                            <div class="d-flex justify-content-between">
                                <small>Risk-Profil:</small>
                                <small>{portfolio.risk_profile}</small>
                            </div>
                        </div>
                    </div>
                    <div class="card-footer">
                        <div class="btn-group w-100" role="group">
                            <button class="btn btn-sm btn-outline-primary" onclick="viewPortfolioDetails('{portfolio.portfolio_id}')">
                                <i class="fas fa-eye"></i> Details
                            </button>
                            <button class="btn btn-sm btn-outline-success" onclick="rebalancePortfolio('{portfolio.portfolio_id}')">
                                <i class="fas fa-balance-scale"></i> Rebalance
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            '''
        
        return f'''
        <div class="row mb-4">
            <div class="col-12">
                <div class="d-flex justify-content-between align-items-center">
                    <h2><i class="fas fa-briefcase me-2"></i>Portfolio-Übersicht</h2>
                    <button class="btn btn-primary" onclick="createNewPortfolio()">
                        <i class="fas fa-plus me-2"></i>Neues Portfolio
                    </button>
                </div>
            </div>
        </div>
        
        <!-- Portfolio Summary Cards -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card text-center bg-primary text-white">
                    <div class="card-body">
                        <h3>{sum(p.total_value for p in portfolios):,.0f} €</h3>
                        <p class="mb-0">Gesamtvermögen</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center bg-success text-white">
                    <div class="card-body">
                        <h3>{len(portfolios)}</h3>
                        <p class="mb-0">Aktive Portfolios</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center bg-info text-white">
                    <div class="card-body">
                        <h3>{sum(len(self._get_mock_positions(p.portfolio_id)) for p in portfolios)}</h3>
                        <p class="mb-0">Positionen</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center bg-warning text-white">
                    <div class="card-body">
                        <h3>{sum(p.performance_ytd for p in portfolios) / len(portfolios):+.1f}%</h3>
                        <p class="mb-0">Ø Performance</p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Portfolio Cards -->
        <div class="row" id="portfolio-grid">
            {portfolio_cards}
        </div>
        
        <script>
        function selectPortfolio(portfolioId) {{
            console.log('Selected portfolio:', portfolioId);
            loadContent('depot-details', {{portfolio_id: portfolioId}});
        }}
        
        function viewPortfolioDetails(portfolioId) {{
            loadContent('depot-details', {{portfolio_id: portfolioId}});
        }}
        
        function rebalancePortfolio(portfolioId) {{
            if (confirm('Portfolio rebalancieren? Dies kann Trading-Orders auslösen.')) {{
                // Rebalancing-API aufrufen
                fetch(`/api/portfolios/${{portfolioId}}/rebalance`, {{method: 'POST'}})
                    .then(response => response.json())
                    .then(data => {{
                        alert('Rebalancing erfolgreich gestartet!');
                        location.reload();
                    }})
                    .catch(error => {{
                        alert('Rebalancing fehlgeschlagen: ' + error);
                    }});
            }}
        }}
        
        function createNewPortfolio() {{
            loadContent('depot-create');
        }}
        </script>
        
        <style>
        .portfolio-card {{
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .portfolio-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }}
        </style>
        '''
    
    def _get_mock_portfolios(self) -> List[Portfolio]:
        """Mock-Portfolio-Daten"""
        return [
            Portfolio(
                portfolio_id="12345678-1234-5678-9012-123456789012",
                name="Haupt-Portfolio",
                description="Langfristige Anlagestrategie mit ETF-Fokus",
                currency="EUR",
                total_value=125000.00,
                cash_balance=8500.00,
                target_allocation={"stocks": 0.7, "bonds": 0.2, "cash": 0.1},
                risk_profile="moderate",
                created_at="2024-01-15T10:00:00Z",
                last_updated=datetime.now().isoformat(),
                performance_ytd=12.5,
                performance_1m=2.1,
                performance_3m=8.3,
                performance_1y=15.2
            ),
            Portfolio(
                portfolio_id="87654321-4321-8765-2109-876543210987",
                name="Dividenden-Portfolio",
                description="Fokus auf dividendenstarke Aktien",
                currency="EUR",
                total_value=75000.00,
                cash_balance=3200.00,
                target_allocation={"dividend_stocks": 0.8, "reits": 0.15, "cash": 0.05},
                risk_profile="conservative",
                created_at="2024-03-10T14:30:00Z",
                last_updated=datetime.now().isoformat(),
                performance_ytd=8.7,
                performance_1m=1.5,
                performance_3m=5.2,
                performance_1y=11.8
            ),
            Portfolio(
                portfolio_id="11111111-2222-3333-4444-555555555555",
                name="Growth-Portfolio",
                description="Wachstumsorientierte Tech-Aktien",
                currency="EUR", 
                total_value=95000.00,
                cash_balance=12500.00,
                target_allocation={"tech_stocks": 0.85, "growth_etfs": 0.1, "cash": 0.05},
                risk_profile="aggressive",
                created_at="2024-02-20T09:15:00Z",
                last_updated=datetime.now().isoformat(),
                performance_ytd=18.9,
                performance_1m=4.2,
                performance_3m=12.7,
                performance_1y=22.4
            )
        ]
    
    def _get_mock_positions(self, portfolio_id: str) -> List[Position]:
        """Mock-Positionen für Portfolio"""
        positions_map = {
            "12345678-1234-5678-9012-123456789012": [
                Position("pos1", portfolio_id, "IWDA", "iShares Core MSCI World", 150, 75.20, 78.50, 11775.00, 495.00, 4.4, 9.4, "Diversified", "ETF"),
                Position("pos2", portfolio_id, "AAPL", "Apple Inc.", 25, 180.00, 193.42, 4835.50, 335.50, 7.4, 3.9, "Technology", "Stock"),
                Position("pos3", portfolio_id, "MSFT", "Microsoft Corp.", 15, 380.00, 421.18, 6317.70, 617.70, 10.9, 5.1, "Technology", "Stock")
            ],
            "87654321-4321-8765-2109-876543210987": [
                Position("pos4", portfolio_id, "KO", "Coca-Cola Co.", 100, 58.50, 61.20, 6120.00, 270.00, 4.6, 8.2, "Consumer", "Stock"),
                Position("pos5", portfolio_id, "JNJ", "Johnson & Johnson", 80, 165.00, 153.64, 12291.20, -909.20, -6.9, 16.4, "Healthcare", "Stock")
            ],
            "11111111-2222-3333-4444-555555555555": [
                Position("pos6", portfolio_id, "NVDA", "NVIDIA Corp.", 10, 750.00, 875.32, 8753.20, 1253.20, 16.7, 9.2, "Technology", "Stock"),
                Position("pos7", portfolio_id, "GOOGL", "Alphabet Inc.", 8, 2400.00, 2598.35, 20786.80, 1586.80, 8.3, 21.9, "Technology", "Stock")
            ]
        }
        return positions_map.get(portfolio_id, [])


class PortfolioDetailsProvider(DepotContentProvider):
    """Portfolio-Details Content Provider"""
    
    async def get_content(self, context: Dict[str, Any]) -> str:
        portfolio_id = context.get('portfolio_id', '')
        await self.event_bus.emit("depot.portfolio.details.requested", {"portfolio_id": portfolio_id})
        
        # Mock-Portfolio und Positionen laden
        portfolios = PortfolioOverviewProvider(self.event_bus, self.api_gateway)._get_mock_portfolios()
        portfolio = next((p for p in portfolios if p.portfolio_id == portfolio_id), None)
        
        if not portfolio:
            return '<div class="alert alert-error">Portfolio nicht gefunden</div>'
        
        positions = PortfolioOverviewProvider(self.event_bus, self.api_gateway)._get_mock_positions(portfolio_id)
        orders = self._get_mock_orders(portfolio_id)
        
        # Positionen-Tabelle
        positions_rows = ""
        for pos in positions:
            pnl_class = "text-success" if pos.unrealized_pnl >= 0 else "text-danger"
            positions_rows += f'''
            <tr>
                <td><strong>{pos.asset_symbol}</strong><br><small class="text-muted">{pos.asset_name}</small></td>
                <td>{pos.quantity:,.2f}</td>
                <td>{pos.average_price:,.2f} €</td>
                <td>{pos.current_price:,.2f} €</td>
                <td>{pos.market_value:,.2f} €</td>
                <td class="{pnl_class}">{pos.unrealized_pnl:+,.2f} € ({pos.unrealized_pnl_percent:+.1f}%)</td>
                <td>{pos.weight:.1f}%</td>
                <td><span class="badge bg-secondary">{pos.sector}</span></td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-success" onclick="buyAsset('{pos.asset_symbol}')">
                            <i class="fas fa-plus"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="sellAsset('{pos.asset_symbol}')">
                            <i class="fas fa-minus"></i>
                        </button>
                    </div>
                </td>
            </tr>
            '''
        
        # Orders-Tabelle
        orders_rows = ""
        for order in orders:
            status_class = {
                'filled': 'bg-success',
                'pending': 'bg-warning',
                'cancelled': 'bg-danger',
                'partially_filled': 'bg-info'
            }.get(order.status, 'bg-secondary')
            
            orders_rows += f'''
            <tr>
                <td>{order.created_at}</td>
                <td><strong>{order.asset_symbol}</strong></td>
                <td><span class="badge {'bg-success' if order.side == 'buy' else 'bg-danger'}">{order.side.upper()}</span></td>
                <td>{order.order_type}</td>
                <td>{order.quantity:,.2f}</td>
                <td>{'Market' if not order.price else f'{order.price:,.2f} €'}</td>
                <td><span class="badge {status_class}">{order.status.replace('_', ' ').title()}</span></td>
                <td>
                    {f'<button class="btn btn-sm btn-outline-danger" onclick="cancelOrder({repr(order.order_id)})">Cancel</button>' if order.status == 'pending' else ''}
                </td>
            </tr>
            '''
        
        return f'''
        <div class="row mb-4">
            <div class="col-12">
                <nav aria-label="breadcrumb">
                    <ol class="breadcrumb">
                        <li class="breadcrumb-item"><a href="#" onclick="loadContent('depot-overview')">Depot-Übersicht</a></li>
                        <li class="breadcrumb-item active">{portfolio.name}</li>
                    </ol>
                </nav>
            </div>
        </div>
        
        <!-- Portfolio Header -->
        <div class="row mb-4">
            <div class="col-md-8">
                <h2><i class="fas fa-briefcase me-2"></i>{portfolio.name}</h2>
                <p class="text-muted">{portfolio.description}</p>
            </div>
            <div class="col-md-4 text-end">
                <div class="btn-group" role="group">
                    <button class="btn btn-success" onclick="showAddCashModal()">
                        <i class="fas fa-plus-circle me-2"></i>Cash hinzufügen
                    </button>
                    <button class="btn btn-primary" onclick="showBuyAssetModal()">
                        <i class="fas fa-shopping-cart me-2"></i>Asset kaufen
                    </button>
                    <button class="btn btn-warning" onclick="rebalancePortfolio('{portfolio.portfolio_id}')">
                        <i class="fas fa-balance-scale me-2"></i>Rebalancieren
                    </button>
                </div>
            </div>
        </div>
        
        <!-- Portfolio Metrics -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h4>{portfolio.total_value:,.2f} €</h4>
                        <p class="mb-0">Gesamtwert</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h4 class="{'text-success' if portfolio.performance_ytd >= 0 else 'text-danger'}">{portfolio.performance_ytd:+.2f}%</h4>
                        <p class="mb-0">YTD Performance</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h4>{portfolio.cash_balance:,.2f} €</h4>
                        <p class="mb-0">Verfügbares Cash</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h4>{len(positions)}</h4>
                        <p class="mb-0">Positionen</p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Tabs für verschiedene Ansichten -->
        <ul class="nav nav-tabs mb-4" id="portfolioTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="positions-tab" data-bs-toggle="tab" data-bs-target="#positions" type="button">
                    <i class="fas fa-chart-pie me-2"></i>Positionen
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="orders-tab" data-bs-toggle="tab" data-bs-target="#orders" type="button">
                    <i class="fas fa-list-alt me-2"></i>Orders
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="performance-tab" data-bs-toggle="tab" data-bs-target="#performance" type="button">
                    <i class="fas fa-chart-line me-2"></i>Performance
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="allocation-tab" data-bs-toggle="tab" data-bs-target="#allocation" type="button">
                    <i class="fas fa-balance-scale me-2"></i>Allokation
                </button>
            </li>
        </ul>
        
        <div class="tab-content" id="portfolioTabContent">
            <!-- Positionen Tab -->
            <div class="tab-pane fade show active" id="positions" role="tabpanel">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-pie me-2"></i>Aktuelle Positionen</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Asset</th>
                                        <th>Menge</th>
                                        <th>Ø Kaufpreis</th>
                                        <th>Aktueller Preis</th>
                                        <th>Marktwert</th>
                                        <th>Unreal. P&L</th>
                                        <th>Gewichtung</th>
                                        <th>Sektor</th>
                                        <th>Aktionen</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {positions_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Orders Tab -->
            <div class="tab-pane fade" id="orders" role="tabpanel">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-list-alt me-2"></i>Order-Historie</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Datum</th>
                                        <th>Asset</th>
                                        <th>Seite</th>
                                        <th>Typ</th>
                                        <th>Menge</th>
                                        <th>Preis</th>
                                        <th>Status</th>
                                        <th>Aktionen</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {orders_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Performance Tab -->  
            <div class="tab-pane fade" id="performance" role="tabpanel">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-line me-2"></i>Performance-Analyse</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Performance-Übersicht</h6>
                                <table class="table table-sm">
                                    <tr><td>1 Monat:</td><td class="{'text-success' if portfolio.performance_1m >= 0 else 'text-danger'}">{portfolio.performance_1m:+.2f}%</td></tr>
                                    <tr><td>3 Monate:</td><td class="{'text-success' if portfolio.performance_3m >= 0 else 'text-danger'}">{portfolio.performance_3m:+.2f}%</td></tr>
                                    <tr><td>Year-to-Date:</td><td class="{'text-success' if portfolio.performance_ytd >= 0 else 'text-danger'}">{portfolio.performance_ytd:+.2f}%</td></tr>
                                    <tr><td>1 Jahr:</td><td class="{'text-success' if portfolio.performance_1y >= 0 else 'text-danger'}">{portfolio.performance_1y:+.2f}%</td></tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <div id="performance-chart" style="height: 300px;">
                                    <div class="d-flex align-items-center justify-content-center h-100">
                                        <div class="text-muted">
                                            <i class="fas fa-chart-line fa-3x mb-3"></i>
                                            <p>Performance-Chart wird geladen...</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Allokation Tab -->
            <div class="tab-pane fade" id="allocation" role="tabpanel">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-balance-scale me-2"></i>Asset-Allokation</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Ziel-Allokation</h6>
                                {''.join([f'<div class="d-flex justify-content-between"><span>{k.title()}:</span><span>{v*100:.1f}%</span></div>' for k, v in portfolio.target_allocation.items()])}
                            </div>
                            <div class="col-md-6">
                                <div id="allocation-chart" style="height: 300px;">
                                    <div class="d-flex align-items-center justify-content-center h-100">
                                        <div class="text-muted">
                                            <i class="fas fa-chart-pie fa-3x mb-3"></i>
                                            <p>Allokation-Chart wird geladen...</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        function buyAsset(symbol) {{
            showBuyAssetModal(symbol);
        }}
        
        function sellAsset(symbol) {{
            showSellAssetModal(symbol);
        }}
        
        function showBuyAssetModal(symbol = '') {{
            // Trading-Modal öffnen
            loadContent('depot-trading', {{action: 'buy', symbol: symbol, portfolio_id: '{portfolio.portfolio_id}'}});
        }}
        
        function showSellAssetModal(symbol) {{
            loadContent('depot-trading', {{action: 'sell', symbol: symbol, portfolio_id: '{portfolio.portfolio_id}'}});
        }}
        
        function showAddCashModal() {{
            // Cash-Modal implementieren
            alert('Cash hinzufügen - Feature in Entwicklung');
        }}
        
        function cancelOrder(orderId) {{
            if (confirm('Order wirklich stornieren?')) {{
                fetch(`/api/orders/${{orderId}}/cancel`, {{method: 'POST'}})
                    .then(response => response.json())
                    .then(data => {{
                        alert('Order erfolgreich storniert!');
                        location.reload();
                    }})
                    .catch(error => alert('Stornierung fehlgeschlagen: ' + error));
            }}
        }}
        </script>
        '''
    
    def _get_mock_orders(self, portfolio_id: str) -> List[Order]:
        """Mock-Orders für Portfolio"""
        return [
            Order("ord1", portfolio_id, "AAPL", "buy", "market", 25, None, "filled", "2024-10-15T09:30:00Z", 25, 180.00),
            Order("ord2", portfolio_id, "MSFT", "buy", "limit", 15, 380.00, "filled", "2024-10-10T14:20:00Z", 15, 380.00),
            Order("ord3", portfolio_id, "GOOGL", "buy", "market", 5, None, "pending", "2024-10-20T10:15:00Z"),
            Order("ord4", portfolio_id, "NVDA", "sell", "limit", 2, 900.00, "pending", "2024-10-21T11:45:00Z")
        ]


class TradingInterfaceProvider(DepotContentProvider):
    """Trading-Interface Content Provider"""
    
    async def get_content(self, context: Dict[str, Any]) -> str:
        action = context.get('action', 'buy')
        symbol = context.get('symbol', '')
        portfolio_id = context.get('portfolio_id', '')
        
        await self.event_bus.emit("depot.trading.interface.requested", {
            "action": action, "symbol": symbol, "portfolio_id": portfolio_id
        })
        
        action_color = "success" if action == "buy" else "danger"
        action_icon = "plus" if action == "buy" else "minus"
        action_text = "Kaufen" if action == "buy" else "Verkaufen"
        
        return f'''
        <div class="row mb-4">
            <div class="col-12">
                <nav aria-label="breadcrumb">
                    <ol class="breadcrumb">
                        <li class="breadcrumb-item"><a href="#" onclick="loadContent('depot-overview')">Depot-Übersicht</a></li>
                        <li class="breadcrumb-item"><a href="#" onclick="loadContent('depot-details', {{portfolio_id: '{portfolio_id}'}})">Portfolio-Details</a></li>
                        <li class="breadcrumb-item active">Trading</li>
                    </ol>
                </nav>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header bg-{action_color} text-white">
                        <h5><i class="fas fa-{action_icon} me-2"></i>{action_text} Order</h5>
                    </div>
                    <div class="card-body">
                        <form id="tradingForm">
                            <input type="hidden" id="portfolioId" value="{portfolio_id}">
                            <input type="hidden" id="action" value="{action}">
                            
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <label for="assetSymbol" class="form-label">Asset Symbol</label>
                                    <input type="text" class="form-control" id="assetSymbol" value="{symbol}" placeholder="z.B. AAPL" required>
                                </div>
                                <div class="col-md-6">
                                    <label for="orderType" class="form-label">Order-Typ</label>
                                    <select class="form-control" id="orderType" required>
                                        <option value="market">Market Order</option>
                                        <option value="limit">Limit Order</option>
                                        <option value="stop">Stop Order</option>
                                        <option value="stop_limit">Stop-Limit Order</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <label for="quantity" class="form-label">Menge</label>
                                    <input type="number" step="0.01" class="form-control" id="quantity" placeholder="0.00" required>
                                </div>
                                <div class="col-md-6">
                                    <label for="price" class="form-label">Preis (€)</label>
                                    <input type="number" step="0.01" class="form-control" id="price" placeholder="Market Preis" disabled>
                                </div>
                            </div>
                            
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <label for="timeInForce" class="form-label">Gültigkeit</label>
                                    <select class="form-control" id="timeInForce">
                                        <option value="day">Day Order</option>
                                        <option value="gtc">Good Till Cancelled</option>
                                        <option value="ioc">Immediate or Cancel</option>
                                        <option value="fok">Fill or Kill</option>
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label for="estimatedValue" class="form-label">Geschätzter Wert</label>
                                    <input type="text" class="form-control" id="estimatedValue" readonly placeholder="0.00 €">
                                </div>
                            </div>
                            
                            <hr>
                            
                            <div class="row">
                                <div class="col-md-6">
                                    <button type="button" class="btn btn-secondary w-100" onclick="loadContent('depot-details', {{portfolio_id: '{portfolio_id}'}})">
                                        <i class="fas fa-arrow-left me-2"></i>Zurück
                                    </button>
                                </div>
                                <div class="col-md-6">
                                    <button type="submit" class="btn btn-{action_color} w-100">
                                        <i class="fas fa-{action_icon} me-2"></i>{action_text} Order aufgeben
                                    </button>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4">
                <!-- Asset-Informationen -->
                <div class="card mb-3">
                    <div class="card-header">
                        <h6><i class="fas fa-info-circle me-2"></i>Asset-Informationen</h6>
                    </div>
                    <div class="card-body" id="assetInfo">
                        <div class="text-muted text-center py-4">
                            <i class="fas fa-search fa-2x mb-2"></i>
                            <p>Asset-Symbol eingeben für Details</p>
                        </div>
                    </div>
                </div>
                
                <!-- Portfolio-Informationen -->
                <div class="card">
                    <div class="card-header">
                        <h6><i class="fas fa-briefcase me-2"></i>Portfolio-Status</h6>
                    </div>
                    <div class="card-body">
                        <div class="d-flex justify-content-between">
                            <span>Verfügbares Cash:</span>
                            <strong id="availableCash">8.500,00 €</strong>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>Kaufkraft:</span>
                            <strong id="buyingPower">8.500,00 €</strong>
                        </div>
                        <hr>
                        <div class="d-flex justify-content-between">
                            <span>Portfolio-Wert:</span>
                            <strong>125.000,00 €</strong>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        document.getElementById('orderType').addEventListener('change', function() {{
            const priceInput = document.getElementById('price');
            const isMarketOrder = this.value === 'market';
            priceInput.disabled = isMarketOrder;
            if (isMarketOrder) {{
                priceInput.placeholder = 'Market Preis';
                priceInput.value = '';
            }} else {{
                priceInput.placeholder = '0.00';
            }}
        }});
        
        document.getElementById('assetSymbol').addEventListener('blur', function() {{
            const symbol = this.value.toUpperCase();
            if (symbol) {{
                loadAssetInfo(symbol);
            }}
        }});
        
        document.getElementById('quantity').addEventListener('input', updateEstimatedValue);
        document.getElementById('price').addEventListener('input', updateEstimatedValue);
        
        function loadAssetInfo(symbol) {{
            // Mock-Asset-Informationen
            const mockAssets = {{
                'AAPL': {{name: 'Apple Inc.', price: 193.42, currency: 'USD', sector: 'Technology'}},
                'MSFT': {{name: 'Microsoft Corp.', price: 421.18, currency: 'USD', sector: 'Technology'}},
                'GOOGL': {{name: 'Alphabet Inc.', price: 2598.35, currency: 'USD', sector: 'Technology'}},
                'NVDA': {{name: 'NVIDIA Corp.', price: 875.32, currency: 'USD', sector: 'Technology'}}
            }};
            
            const asset = mockAssets[symbol];
            const assetInfoDiv = document.getElementById('assetInfo');
            
            if (asset) {{
                assetInfoDiv.innerHTML = `
                    <h6>${{asset.name}}</h6>
                    <div class="d-flex justify-content-between">
                        <span>Aktueller Preis:</span>
                        <strong>${{asset.price}} ${{asset.currency}}</strong>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span>Sektor:</span>
                        <span>${{asset.sector}}</span>
                    </div>
                    <hr>
                    <small class="text-muted">
                        <i class="fas fa-clock me-1"></i>
                        Live-Kurse - Letztes Update: vor 2 Min.
                    </small>
                `;
                
                // Preis für Limit-Orders vorausfüllen
                if (document.getElementById('orderType').value !== 'market') {{
                    document.getElementById('price').value = asset.price;
                }}
                updateEstimatedValue();
            }} else {{
                assetInfoDiv.innerHTML = `
                    <div class="text-warning text-center py-4">
                        <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                        <p>Asset nicht gefunden</p>
                    </div>
                `;
            }}
        }}
        
        function updateEstimatedValue() {{
            const quantity = parseFloat(document.getElementById('quantity').value) || 0;
            const price = parseFloat(document.getElementById('price').value) || 0;
            const orderType = document.getElementById('orderType').value;
            
            let estimatedValue = 0;
            if (orderType === 'market') {{
                // Für Market Orders: Verwende Mock-Preis
                const symbol = document.getElementById('assetSymbol').value.toUpperCase();
                const mockPrice = {{
                    'AAPL': 193.42, 'MSFT': 421.18, 'GOOGL': 2598.35, 'NVDA': 875.32
                }}[symbol] || 0;
                estimatedValue = quantity * mockPrice;
            }} else {{
                estimatedValue = quantity * price;
            }}
            
            document.getElementById('estimatedValue').value = estimatedValue.toFixed(2) + ' €';
        }}
        
        document.getElementById('tradingForm').addEventListener('submit', function(e) {{
            e.preventDefault();
            
            const formData = {{
                portfolio_id: document.getElementById('portfolioId').value,
                asset_symbol: document.getElementById('assetSymbol').value.toUpperCase(),
                side: document.getElementById('action').value,
                order_type: document.getElementById('orderType').value,
                quantity: parseFloat(document.getElementById('quantity').value),
                price: document.getElementById('orderType').value === 'market' ? null : parseFloat(document.getElementById('price').value),
                time_in_force: document.getElementById('timeInForce').value
            }};
            
            // Order an API senden
            fetch('/api/orders', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify(formData)
            }})
            .then(response => response.json())
            .then(data => {{
                alert('Order erfolgreich aufgegeben!');
                loadContent('depot-details', {{portfolio_id: formData.portfolio_id}});
            }})
            .catch(error => {{
                alert('Order fehlgeschlagen: ' + error);
            }});
        }});
        
        // Initial asset info laden wenn Symbol vorhanden
        if ('{symbol}') {{
            loadAssetInfo('{symbol}');
        }}
        </script>
        '''


class DepotContentProviderFactory:
    """Factory für Depot-Content-Provider"""
    
    @staticmethod
    def get_provider(provider_type: str, event_bus, api_gateway):
        providers = {
            'depot-overview': PortfolioOverviewProvider,
            'depot-details': PortfolioDetailsProvider,
            'depot-trading': TradingInterfaceProvider
        }
        provider_class = providers.get(provider_type)
        return provider_class(event_bus, api_gateway) if provider_class else None