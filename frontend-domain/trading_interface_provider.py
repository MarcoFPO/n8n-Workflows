"""
🔄 Trading Interface Provider
Provides comprehensive trading functionality with order management
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class TradingInterfaceProvider:
    """Trading Interface Content Provider"""
    
    def __init__(self, event_bus, api_gateway):
        self.event_bus = event_bus
        self.api_gateway = api_gateway
        self.logger = logger
        
    async def get_trading_interface_content(self, context: Dict[str, Any]) -> str:
        """Generate trading interface dashboard content"""
        await self.event_bus.emit("frontend.trading_interface.requested", {"context": context})
        
        # Get trading data
        trading_data = await self._get_trading_data()
        
        return f'''
        <div class="row">
            <!-- Trading Status Banner -->
            <div class="col-12 mb-4">
                <div class="alert alert-{self._get_market_status_color(trading_data['market_status'])} alert-dismissible">
                    <h5><i class="fas fa-chart-line me-2"></i>Trading Status: {trading_data['market_status']}</h5>
                    <p class="mb-0">
                        <strong>Verfügbares Kapital:</strong> {trading_data['available_balance']:,.2f}€ | 
                        <strong>Investiert:</strong> {trading_data['invested_balance']:,.2f}€ |
                        <strong>P&L Today:</strong> <span class="text-{self._get_pnl_color(trading_data['daily_pnl'])}">{trading_data['daily_pnl']:+,.2f}€</span>
                    </p>
                </div>
            </div>
        </div>
        
        <div class="row">
            <!-- Buy/Sell Order Interface ---> 
            <div class="col-md-6 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-exchange-alt me-2"></i>Order Placement</h5>
                        <div class="card-tools">
                            <div class="btn-group" role="group">
                                <button class="btn btn-success btn-sm active" onclick="switchOrderType('buy')">
                                    <i class="fas fa-arrow-up"></i> BUY
                                </button>
                                <button class="btn btn-danger btn-sm" onclick="switchOrderType('sell')">
                                    <i class="fas fa-arrow-down"></i> SELL
                                </button>
                            </div>
                        </div>
                    </div>
                    <div class="card-body">
                        <form id="trading-form">
                            <div class="row mb-3">
                                <div class="col-md-8">
                                    <label class="form-label">Symbol</label>
                                    <div class="input-group">
                                        <input type="text" class="form-control" id="symbol-input" 
                                               placeholder="z.B. AAPL" value="AAPL" onchange="updateSymbolPrice()">
                                        <button class="btn btn-outline-secondary" type="button" onclick="searchSymbol()">
                                            <i class="fas fa-search"></i>
                                        </button>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <label class="form-label">Aktueller Preis</label>
                                    <div class="input-group">
                                        <span class="input-group-text">€</span>
                                        <input type="text" class="form-control" id="current-price" 
                                               value="145.67" readonly>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <label class="form-label">Order Type</label>
                                    <select class="form-select" id="order-type" onchange="togglePriceInput()">
                                        <option value="market">Market Order</option>
                                        <option value="limit">Limit Order</option>
                                        <option value="stop_loss">Stop-Loss</option>
                                        <option value="stop_limit">Stop-Limit</option>
                                    </select>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Limit Price</label>
                                    <div class="input-group">
                                        <span class="input-group-text">€</span>
                                        <input type="number" class="form-control" id="limit-price" 
                                               step="0.01" disabled onchange="calculateTotalValue()">
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <label class="form-label">Quantity</label>
                                    <div class="input-group">
                                        <input type="number" class="form-control" id="quantity" 
                                               value="10" min="1" onchange="calculateTotalValue()">
                                        <span class="input-group-text">Stück</span>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Total Value</label>
                                    <div class="input-group">
                                        <span class="input-group-text">€</span>
                                        <input type="text" class="form-control" id="total-value" 
                                               value="1,456.70" readonly>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Risk Management Section -->
                            <div class="card bg-light mb-3">
                                <div class="card-body">
                                    <h6><i class="fas fa-shield-alt me-2"></i>Risk Management</h6>
                                    <div class="row">
                                        <div class="col-md-6">
                                            <small class="text-muted">Portfolio Weight:</small>
                                            <div class="progress mb-2" style="height: 8px;">
                                                <div class="progress-bar bg-{self._get_risk_color(12.5)}" 
                                                     style="width: 12.5%" id="portfolio-weight-bar"></div>
                                            </div>
                                            <small id="portfolio-weight-text">12.5% of Portfolio</small>
                                        </div>
                                        <div class="col-md-6">
                                            <small class="text-muted">Risk Score:</small>
                                            <div class="text-center">
                                                <span class="badge bg-{self._get_risk_color(12.5)} fs-6" id="risk-score">MEDIUM</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="d-grid gap-2">
                                <button type="button" class="btn btn-success btn-lg" id="buy-button" onclick="submitOrder('buy')">
                                    <i class="fas fa-arrow-up me-2"></i>BUY ORDER - 1,456.70€
                                </button>
                                <button type="button" class="btn btn-danger btn-lg d-none" id="sell-button" onclick="submitOrder('sell')">
                                    <i class="fas fa-arrow-down me-2"></i>SELL ORDER - 1,456.70€
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            
            <!-- Current Positions -->
            <div class="col-md-6 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-briefcase me-2"></i>Current Positions</h5>
                        <div class="card-tools">
                            <button class="btn btn-sm btn-primary" onclick="refreshPositions()">
                                <i class="fas fa-sync"></i>
                            </button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover table-sm">
                                <thead>
                                    <tr>
                                        <th>Symbol</th>
                                        <th>Qty</th>
                                        <th>Avg Price</th>
                                        <th>Current</th>
                                        <th>P&L</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {self._generate_positions_table(trading_data['positions'])}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <!-- Order History -->
            <div class="col-md-8 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-history me-2"></i>Order History</h5>
                        <div class="card-tools">
                            <div class="btn-group" role="group">
                                <button class="btn btn-sm btn-outline-primary active" onclick="filterOrders('all')">All</button>
                                <button class="btn btn-sm btn-outline-primary" onclick="filterOrders('filled')">Filled</button>
                                <button class="btn btn-sm btn-outline-primary" onclick="filterOrders('pending')">Pending</button>
                                <button class="btn btn-sm btn-outline-primary" onclick="filterOrders('cancelled')">Cancelled</button>
                            </div>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover table-sm">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Time</th>
                                        <th>Symbol</th>
                                        <th>Side</th>
                                        <th>Type</th>
                                        <th>Qty</th>
                                        <th>Price</th>
                                        <th>Status</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody id="order-history-tbody">
                                    {self._generate_order_history_table(trading_data['order_history'])}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Trading Statistics -->
            <div class="col-md-4 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-pie me-2"></i>Trading Stats</h5>
                    </div>
                    <div class="card-body">
                        <div class="text-center mb-3">
                            <h4 class="text-{self._get_pnl_color(trading_data['total_pnl'])}">{trading_data['total_pnl']:+,.2f}€</h4>
                            <p class="mb-0">Total P&L</p>
                        </div>
                        
                        <div class="row text-center">
                            <div class="col-6 mb-3">
                                <small class="text-muted">Win Rate</small>
                                <br>
                                <strong class="text-success">{trading_data['win_rate']:.1f}%</strong>
                            </div>
                            <div class="col-6 mb-3">
                                <small class="text-muted">Total Trades</small>
                                <br>
                                <strong>{trading_data['total_trades']}</strong>
                            </div>
                            <div class="col-6 mb-3">
                                <small class="text-muted">Avg Profit</small>
                                <br>
                                <strong class="text-success">{trading_data['avg_profit']:+.2f}€</strong>
                            </div>
                            <div class="col-6 mb-3">
                                <small class="text-muted">Avg Loss</small>
                                <br>
                                <strong class="text-danger">{trading_data['avg_loss']:.2f}€</strong>
                            </div>
                        </div>
                        
                        <div class="mt-3">
                            <small class="text-muted">Portfolio Allocation</small>
                            <div class="progress mt-1" style="height: 20px;">
                                <div class="progress-bar bg-success" style="width: 65%" title="Invested: 65%">65%</div>
                                <div class="progress-bar bg-secondary" style="width: 35%" title="Cash: 35%">35%</div>
                            </div>
                            <div class="d-flex justify-content-between mt-1">
                                <small>Invested</small>
                                <small>Cash</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Order Confirmation Modal -->
        <div class="modal fade" id="orderConfirmModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="fas fa-exclamation-triangle me-2"></i>Confirm Order</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-warning">
                            <strong>Please confirm your order:</strong>
                        </div>
                        <div id="order-confirmation-details">
                            <!-- Order details will be populated here -->
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="confirmOrder()">Confirm Order</button>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        let currentOrderType = 'buy';
        let orderData = {{}};
        
        function switchOrderType(type) {{
            currentOrderType = type;
            const buyBtn = document.getElementById('buy-button');
            const sellBtn = document.getElementById('sell-button');
            const buyToggle = document.querySelector('[onclick="switchOrderType(\\'buy\\')"]');
            const sellToggle = document.querySelector('[onclick="switchOrderType(\\'sell\\')"]');
            
            if (type === 'buy') {{
                buyBtn.classList.remove('d-none');
                sellBtn.classList.add('d-none');
                buyToggle.classList.add('active');
                sellToggle.classList.remove('active');
            }} else {{
                sellBtn.classList.remove('d-none');
                buyBtn.classList.add('d-none');
                sellToggle.classList.add('active');
                buyToggle.classList.remove('active');
            }}
        }}
        
        function togglePriceInput() {{
            const orderType = document.getElementById('order-type').value;
            const limitPrice = document.getElementById('limit-price');
            
            if (orderType === 'market') {{
                limitPrice.disabled = true;
                limitPrice.value = '';
            }} else {{
                limitPrice.disabled = false;
                limitPrice.value = document.getElementById('current-price').value;
            }}
            calculateTotalValue();
        }}
        
        function calculateTotalValue() {{
            const quantity = parseFloat(document.getElementById('quantity').value) || 0;
            const orderType = document.getElementById('order-type').value;
            let price = 0;
            
            if (orderType === 'market') {{
                price = parseFloat(document.getElementById('current-price').value) || 0;
            }} else {{
                price = parseFloat(document.getElementById('limit-price').value) || 0;
            }}
            
            const totalValue = quantity * price;
            document.getElementById('total-value').value = totalValue.toLocaleString('de-DE', {{
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }});
            
            // Update button text
            const buyButton = document.getElementById('buy-button');
            const sellButton = document.getElementById('sell-button');
            
            if (buyButton && !buyButton.classList.contains('d-none')) {{
                buyButton.innerHTML = `<i class="fas fa-arrow-up me-2"></i>BUY ORDER - ${{totalValue.toLocaleString('de-DE', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}€`;
            }}
            if (sellButton && !sellButton.classList.contains('d-none')) {{
                sellButton.innerHTML = `<i class="fas fa-arrow-down me-2"></i>SELL ORDER - ${{totalValue.toLocaleString('de-DE', {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}€`;
            }}
            
            updateRiskMetrics(totalValue);
        }}
        
        function updateRiskMetrics(orderValue) {{
            // Mock portfolio value for calculation
            const portfolioValue = 157580;
            const weight = (orderValue / portfolioValue) * 100;
            
            document.getElementById('portfolio-weight-bar').style.width = Math.min(weight, 100) + '%';
            document.getElementById('portfolio-weight-text').textContent = weight.toFixed(1) + '% of Portfolio';
            
            let riskLevel = 'LOW';
            let riskColor = 'success';
            
            if (weight > 20) {{
                riskLevel = 'HIGH';
                riskColor = 'danger';
            }} else if (weight > 10) {{
                riskLevel = 'MEDIUM';
                riskColor = 'warning';
            }}
            
            const riskScore = document.getElementById('risk-score');
            riskScore.textContent = riskLevel;
            riskScore.className = `badge bg-${{riskColor}} fs-6`;
            
            const progressBar = document.getElementById('portfolio-weight-bar');
            progressBar.className = `progress-bar bg-${{riskColor}}`;
        }}
        
        function updateSymbolPrice() {{
            const symbol = document.getElementById('symbol-input').value;
            // Mock price update - would be real API call
            const mockPrices = {{
                'AAPL': 145.67,
                'MSFT': 312.45,
                'GOOGL': 125.80,
                'TSLA': 245.30,
                'NVDA': 418.95
            }};
            
            const price = mockPrices[symbol] || 100.00;
            document.getElementById('current-price').value = price.toFixed(2);
            calculateTotalValue();
        }}
        
        function searchSymbol() {{
            // Mock symbol search - would open symbol search modal
            alert('Symbol search functionality - would open search dialog');
        }}
        
        function submitOrder(side) {{
            const symbol = document.getElementById('symbol-input').value;
            const quantity = document.getElementById('quantity').value;
            const orderType = document.getElementById('order-type').value;
            const price = orderType === 'market' ? 
                document.getElementById('current-price').value : 
                document.getElementById('limit-price').value;
            
            orderData = {{
                symbol: symbol,
                side: side,
                quantity: quantity,
                orderType: orderType,
                price: price,
                totalValue: document.getElementById('total-value').value
            }};
            
            // Show confirmation modal
            document.getElementById('order-confirmation-details').innerHTML = `
                <table class="table table-sm">
                    <tr><td><strong>Symbol:</strong></td><td>${{symbol}}</td></tr>
                    <tr><td><strong>Side:</strong></td><td class="text-${{side === 'buy' ? 'success' : 'danger'}}">${{side.toUpperCase()}}</td></tr>
                    <tr><td><strong>Quantity:</strong></td><td>${{quantity}} Stück</td></tr>
                    <tr><td><strong>Order Type:</strong></td><td>${{orderType.toUpperCase()}}</td></tr>
                    <tr><td><strong>Price:</strong></td><td>${{price}}€</td></tr>
                    <tr><td><strong>Total Value:</strong></td><td><strong>${{orderData.totalValue}}€</strong></td></tr>
                </table>
            `;
            
            const modal = new bootstrap.Modal(document.getElementById('orderConfirmModal'));
            modal.show();
        }}
        
        function confirmOrder() {{
            // Mock order submission - would be real API call
            console.log('Submitting order:', orderData);
            
            // Show success message
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-success alert-dismissible fade show';
            alertDiv.innerHTML = `
                <strong>Order Submitted!</strong> Your ${{orderData.side.toUpperCase()}} order for ${{orderData.quantity}} ${{orderData.symbol}} has been placed.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            document.querySelector('.row').prepend(alertDiv);
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('orderConfirmModal'));
            modal.hide();
            
            // Reset form
            document.getElementById('trading-form').reset();
            updateSymbolPrice();
        }}
        
        function refreshPositions() {{
            // Mock refresh - would reload position data
            location.reload();
        }}
        
        function closePosition(symbol) {{
            if (confirm(`Close entire position in ${{symbol}}?`)) {{
                console.log(`Closing position in ${{symbol}}`);
                // Would submit market sell order for entire position
            }}
        }}
        
        function cancelOrder(orderId) {{
            if (confirm(`Cancel order ${{orderId}}?`)) {{
                console.log(`Cancelling order ${{orderId}}`);
                // Would cancel the order via API
            }}
        }}
        
        function filterOrders(status) {{
            const rows = document.querySelectorAll('#order-history-tbody tr');
            rows.forEach(row => {{
                const orderStatus = row.querySelector('.badge').textContent.toLowerCase();
                if (status === 'all' || orderStatus.includes(status)) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
            
            // Update active button
            document.querySelectorAll('[onclick^="filterOrders"]').forEach(btn => {{
                btn.classList.remove('active');
            }});
            event.target.classList.add('active');
        }}
        
        // Initialize
        document.addEventListener('DOMContentLoaded', function() {{
            updateSymbolPrice();
            calculateTotalValue();
        }});
        </script>
        '''
    
    async def _get_trading_data(self) -> Dict[str, Any]:
        """Get trading data - mock data for now"""
        # TODO: Replace with real API calls to trading services
        return {
            'market_status': 'OPEN',
            'available_balance': 45230.50,
            'invested_balance': 112349.50,
            'daily_pnl': 1245.30,
            'total_pnl': 8467.25,
            'win_rate': 68.5,
            'total_trades': 47,
            'avg_profit': 425.80,
            'avg_loss': -235.50,
            'positions': [
                {
                    'symbol': 'AAPL',
                    'quantity': 150,
                    'avg_price': 135.50,
                    'current_price': 145.67,
                    'pnl': 1525.50,
                    'pnl_percent': 7.51
                },
                {
                    'symbol': 'MSFT', 
                    'quantity': 75,
                    'avg_price': 305.20,
                    'current_price': 312.45,
                    'pnl': 543.75,
                    'pnl_percent': 2.37
                },
                {
                    'symbol': 'GOOGL',
                    'quantity': 200,
                    'avg_price': 115.30,
                    'current_price': 125.80,
                    'pnl': 2100.00,
                    'pnl_percent': 9.11
                },
                {
                    'symbol': 'TSLA',
                    'quantity': 180,
                    'avg_price': 265.80,
                    'current_price': 245.30,
                    'pnl': -3690.00,
                    'pnl_percent': -7.72
                }
            ],
            'order_history': [
                {
                    'id': 'ORD-001',
                    'timestamp': '2025-08-01 14:30:25',
                    'symbol': 'AAPL',
                    'side': 'BUY',
                    'type': 'MARKET',
                    'quantity': 50,
                    'price': 145.67,
                    'status': 'FILLED'
                },
                {
                    'id': 'ORD-002',
                    'timestamp': '2025-08-01 13:15:10',
                    'symbol': 'MSFT',
                    'side': 'BUY',
                    'type': 'LIMIT',
                    'quantity': 25,
                    'price': 310.00,
                    'status': 'PENDING'
                },
                {
                    'id': 'ORD-003',
                    'timestamp': '2025-08-01 12:45:33',
                    'symbol': 'TSLA',
                    'side': 'SELL',
                    'type': 'STOP_LOSS',
                    'quantity': 30,
                    'price': 240.00,
                    'status': 'CANCELLED'
                },
                {
                    'id': 'ORD-004',
                    'timestamp': '2025-08-01 11:20:15',
                    'symbol': 'GOOGL',
                    'side': 'BUY',
                    'type': 'MARKET',
                    'quantity': 100,
                    'price': 125.80,
                    'status': 'FILLED'
                }
            ]
        }
    
    def _generate_positions_table(self, positions: List[Dict]) -> str:
        """Generate HTML table rows for current positions"""
        html = ""
        for position in positions:
            pnl_color = "success" if position['pnl'] >= 0 else "danger"
            pnl_icon = "arrow-up" if position['pnl'] >= 0 else "arrow-down"
            
            html += f'''
            <tr>
                <td><strong>{position['symbol']}</strong></td>
                <td>{position['quantity']:,}</td>
                <td>{position['avg_price']:.2f}€</td>
                <td>{position['current_price']:.2f}€</td>
                <td class="text-{pnl_color}">
                    <i class="fas fa-{pnl_icon}"></i> {position['pnl']:+,.2f}€
                    <br><small>({position['pnl_percent']:+.2f}%)</small>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" onclick="closePosition('{position['symbol']}')" title="Close Position">
                        <i class="fas fa-times"></i>
                    </button>
                </td>
            </tr>
            '''
        return html
    
    def _generate_order_history_table(self, orders: List[Dict]) -> str:
        """Generate HTML table rows for order history"""
        html = ""
        for order in orders:
            side_color = "success" if order['side'] == 'BUY' else "danger"
            status_color = self._get_order_status_color(order['status'])
            
            html += f'''
            <tr>
                <td>{order['timestamp']}</td>
                <td><strong>{order['symbol']}</strong></td>
                <td><span class="badge bg-{side_color}">{order['side']}</span></td>
                <td>{order['type']}</td>
                <td>{order['quantity']:,}</td>
                <td>{order['price']:.2f}€</td>
                <td><span class="badge bg-{status_color}">{order['status']}</span></td>
                <td>
                    {self._get_order_action_button(order)}
                </td>
            </tr>
            '''
        return html
    
    def _get_order_action_button(self, order: Dict) -> str:
        """Get action button for order based on status"""
        if order['status'] == 'PENDING':
            return f'''
            <button class="btn btn-sm btn-outline-warning" onclick="cancelOrder('{order['id']}')" title="Cancel Order">
                <i class="fas fa-ban"></i>
            </button>
            '''
        else:
            return '<span class="text-muted">-</span>'
    
    def _get_market_status_color(self, status: str) -> str:
        """Get color based on market status"""
        colors = {
            'OPEN': 'success',
            'CLOSED': 'danger', 
            'PRE_MARKET': 'warning',
            'AFTER_HOURS': 'info'
        }
        return colors.get(status, 'secondary')
    
    def _get_pnl_color(self, pnl: float) -> str:
        """Get color based on P&L value"""
        return "success" if pnl >= 0 else "danger"
        
    def _get_risk_color(self, weight: float) -> str:
        """Get color based on portfolio weight"""
        if weight > 20:
            return "danger"
        elif weight > 10:
            return "warning"
        else:
            return "success"
    
    def _get_order_status_color(self, status: str) -> str:
        """Get color based on order status"""
        colors = {
            'FILLED': 'success',
            'PENDING': 'warning',
            'CANCELLED': 'danger',
            'REJECTED': 'dark'
        }
        return colors.get(status, 'secondary')