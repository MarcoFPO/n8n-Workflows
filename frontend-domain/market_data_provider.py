"""
📡 Market Data Integration Provider
Provides live market data and real-time updates
"""

import asyncio
import logging
import json
import aiohttp
from typing import Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class MarketDataProvider:
    """Live Market Data Integration Provider"""
    
    def __init__(self, event_bus, api_gateway):
        self.event_bus = event_bus
        self.api_gateway = api_gateway
        self.logger = logger
        self.websocket_connections = []
        
    async def get_market_data_content(self, context: Dict[str, Any]) -> str:
        """Generate live market data dashboard content"""
        await self.event_bus.emit("frontend.market_data.requested", {"context": context})
        
        # Get live market data
        market_data = await self._get_live_market_data()
        
        return f'''
        <div class="row">
            <!-- Market Status Banner -->
            <div class="col-12 mb-4">
                <div class="alert alert-{self._get_market_status_color(market_data['market_status'])} alert-dismissible">
                    <h5><i class="fas fa-globe me-2"></i>Markt Status: {market_data['market_status']}</h5>
                    <p class="mb-0">
                        <strong>Letztes Update:</strong> {market_data['last_update']} | 
                        <strong>Nächste Aktualisierung:</strong> {market_data['next_update']}
                    </p>
                </div>
            </div>
        </div>
        
        <div class="row">
            <!-- Major Indices -->
            <div class="col-md-4 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-bar me-2"></i>Major Indices</h5>
                        <div class="card-tools">
                            <span class="badge bg-success" id="indices-status">LIVE</span>
                        </div>
                    </div>
                    <div class="card-body">
                        {self._generate_indices_cards(market_data['indices'])}
                    </div>
                </div>
            </div>
            
            <!-- Top Movers -->
            <div class="col-md-4 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-fire me-2"></i>Top Movers</h5>
                        <div class="card-tools">
                            <button class="btn btn-sm btn-outline-primary" onclick="refreshTopMovers()">
                                <i class="fas fa-sync"></i>
                            </button>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Symbol</th>
                                        <th>Price</th>
                                        <th>Change</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {self._generate_top_movers_table(market_data['top_movers'])}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Market Sentiment -->
            <div class="col-md-4 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-thermometer-half me-2"></i>Market Sentiment</h5>
                    </div>
                    <div class="card-body">
                        <div class="text-center mb-3">
                            <div class="sentiment-gauge">
                                <i class="fas fa-smile fa-3x text-{self._get_sentiment_color(market_data['sentiment']['score'])}"></i>
                                <h4 class="mt-2">{market_data['sentiment']['score']}/100</h4>
                                <p class="text-muted">{market_data['sentiment']['label']}</p>
                            </div>
                        </div>
                        <div class="row text-center">
                            <div class="col-4">
                                <small class="text-muted">Fear</small>
                                <br>
                                <span class="text-danger">{market_data['sentiment']['fear']}%</span>
                            </div>
                            <div class="col-4">
                                <small class="text-muted">Neutral</small>
                                <br>
                                <span class="text-warning">{market_data['sentiment']['neutral']}%</span>
                            </div>
                            <div class="col-4">
                                <small class="text-muted">Greed</small>
                                <br>
                                <span class="text-success">{market_data['sentiment']['greed']}%</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Live Market Data Table -->
        <div class="row">
            <div class="col-12 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-table me-2"></i>Live Market Data</h5>
                        <div class="card-tools">
                            <div class="btn-group" role="group">
                                <button class="btn btn-sm btn-outline-primary active" onclick="filterMarketData('all')">Alle</button>
                                <button class="btn btn-sm btn-outline-primary" onclick="filterMarketData('gainers')">Gewinner</button>
                                <button class="btn btn-sm btn-outline-primary" onclick="filterMarketData('losers')">Verlierer</button>
                                <button class="btn btn-sm btn-outline-primary" onclick="filterMarketData('volume')">Volume</button>
                            </div>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover" id="market-data-table">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Symbol</th>
                                        <th>Name</th>
                                        <th>Price</th>
                                        <th>Change</th>
                                        <th>Change %</th>
                                        <th>Volume</th>
                                        <th>Market Cap</th>
                                        <th>P/E</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody id="market-data-tbody">
                                    {self._generate_market_data_table(market_data['stocks'])}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Real-time Connection Status -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-wifi me-2"></i>Real-time Connection Status</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-3 text-center">
                                <div class="connection-status">
                                    <i class="fas fa-circle text-{self._get_connection_status_color('websocket')} fa-2x"></i>
                                    <p class="mt-2 mb-0">WebSocket</p>
                                    <small class="text-muted">Live Data Feed</small>
                                </div>
                            </div>
                            <div class="col-md-3 text-center">
                                <div class="connection-status">
                                    <i class="fas fa-circle text-{self._get_connection_status_color('api')} fa-2x"></i>
                                    <p class="mt-2 mb-0">API Gateway</p>
                                    <small class="text-muted">Data Services</small>
                                </div>
                            </div>
                            <div class="col-md-3 text-center">
                                <div class="connection-status">
                                    <i class="fas fa-circle text-{self._get_connection_status_color('database')} fa-2x"></i>
                                    <p class="mt-2 mb-0">Database</p>
                                    <small class="text-muted">Historical Data</small>
                                </div>
                            </div>
                            <div class="col-md-3 text-center">
                                <div class="connection-status">
                                    <i class="fas fa-circle text-{self._get_connection_status_color('external')} fa-2x"></i>
                                    <p class="mt-2 mb-0">External APIs</p>
                                    <small class="text-muted">Market Data Sources</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
        let marketDataWebSocket = null;
        
        function initializeWebSocket() {{
            // Initialize WebSocket connection for live data
            if (window.WebSocket) {{
                marketDataWebSocket = new WebSocket('wss://' + window.location.host + '/ws/market-data');
                
                marketDataWebSocket.onopen = function(event) {{
                    console.log('Market Data WebSocket connected');
                    document.getElementById('indices-status').textContent = 'LIVE';
                    document.getElementById('indices-status').className = 'badge bg-success';
                }};
                
                marketDataWebSocket.onmessage = function(event) {{
                    const data = JSON.parse(event.data);
                    updateMarketData(data);
                }};
                
                marketDataWebSocket.onclose = function(event) {{
                    console.log('Market Data WebSocket disconnected');
                    document.getElementById('indices-status').textContent = 'OFFLINE';
                    document.getElementById('indices-status').className = 'badge bg-danger';
                    
                    // Reconnect after 5 seconds
                    setTimeout(initializeWebSocket, 5000);
                }};
            }}
        }}
        
        function updateMarketData(data) {{
            // Update market data in real-time
            if (data.type === 'price_update') {{
                updatePriceInTable(data.symbol, data.price, data.change);
            }} else if (data.type === 'market_status') {{
                updateMarketStatus(data.status);
            }}
        }}
        
        function updatePriceInTable(symbol, price, change) {{
            // Update specific stock price in table
            const row = document.querySelector(`tr[data-symbol="${{symbol}}"]`);
            if (row) {{
                const priceCell = row.querySelector('.price-cell');
                const changeCell = row.querySelector('.change-cell');
                
                if (priceCell) priceCell.textContent = price.toFixed(2) + '€';
                if (changeCell) {{
                    changeCell.textContent = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';
                    changeCell.className = 'change-cell text-' + (change >= 0 ? 'success' : 'danger');
                }}
            }}
        }}
        
        function refreshTopMovers() {{
            // Refresh top movers data
            location.reload();
        }}
        
        function filterMarketData(filter) {{
            // Filter market data table
            const tbody = document.getElementById('market-data-tbody');
            const rows = tbody.querySelectorAll('tr');
            
            rows.forEach(row => {{
                const changeCell = row.querySelector('.change-cell');
                const volumeCell = row.querySelector('.volume-cell');
                let show = true;
                
                if (filter === 'gainers') {{
                    show = changeCell && changeCell.textContent.includes('+');
                }} else if (filter === 'losers') {{
                    show = changeCell && changeCell.textContent.includes('-');
                }} else if (filter === 'volume') {{
                    show = volumeCell && parseFloat(volumeCell.dataset.volume) > 1000000;
                }}
                
                row.style.display = show ? '' : 'none';
            }});
            
            // Update active button
            document.querySelectorAll('.btn-group .btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            event.target.classList.add('active');
        }}
        
        // Initialize WebSocket connection when page loads
        document.addEventListener('DOMContentLoaded', function() {{
            initializeWebSocket();
        }});
        
        // Auto-refresh every 30 seconds as fallback
        setInterval(function() {{
            if (!marketDataWebSocket || marketDataWebSocket.readyState !== WebSocket.OPEN) {{
                console.log('Fallback: Refreshing market data via HTTP...');
                // Could implement HTTP fallback here
            }}
        }}, 30000);
        </script>
        '''
    
    async def _get_live_market_data(self) -> Dict[str, Any]:
        """Get live market data - mock data for now"""
        # TODO: Replace with real API calls to market data services
        return {
            'market_status': 'OPEN',
            'last_update': datetime.now().strftime('%H:%M:%S'),
            'next_update': (datetime.now() + timedelta(seconds=30)).strftime('%H:%M:%S'),
            'indices': [
                {'name': 'DAX', 'value': 15847.65, 'change': 1.23, 'change_percent': 0.78},
                {'name': 'S&P 500', 'value': 4185.47, 'change': -12.45, 'change_percent': -0.30},
                {'name': 'NASDAQ', 'value': 12567.89, 'change': 45.67, 'change_percent': 0.36}
            ],
            'top_movers': [
                {'symbol': 'NVDA', 'price': 418.95, 'change': 15.67},
                {'symbol': 'TSLA', 'price': 245.30, 'change': -18.45},
                {'symbol': 'AAPL', 'price': 145.67, 'change': 3.25}
            ],
            'sentiment': {
                'score': 67,
                'label': 'Optimistisch',
                'fear': 15,
                'neutral': 18,
                'greed': 67
            },
            'stocks': [
                {
                    'symbol': 'AAPL',
                    'name': 'Apple Inc.',
                    'price': 145.67,
                    'change': 3.25,
                    'change_percent': 2.28,
                    'volume': '45.2M',
                    'market_cap': '2.3T',
                    'pe_ratio': 28.5,
                    'status': 'LIVE'
                },
                {
                    'symbol': 'MSFT',
                    'name': 'Microsoft Corporation',
                    'price': 312.45,
                    'change': -5.80,
                    'change_percent': -1.82,
                    'volume': '28.1M',
                    'market_cap': '2.1T',
                    'pe_ratio': 31.2,
                    'status': 'LIVE'
                },
                {
                    'symbol': 'GOOGL',
                    'name': 'Alphabet Inc.',
                    'price': 125.80,
                    'change': 2.45,
                    'change_percent': 1.99,
                    'volume': '22.8M',
                    'market_cap': '1.6T',
                    'pe_ratio': 25.8,
                    'status': 'LIVE'
                }
            ]
        }
    
    def _generate_indices_cards(self, indices: List[Dict]) -> str:
        """Generate HTML cards for major indices"""
        html = ""
        for index in indices:
            color = "success" if index['change'] >= 0 else "danger"
            icon = "arrow-up" if index['change'] >= 0 else "arrow-down"
            
            html += f'''
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                    <strong>{index['name']}</strong>
                    <br>
                    <span class="h5">{index['value']:,.2f}</span>
                </div>
                <div class="text-{color} text-end">
                    <i class="fas fa-{icon}"></i>
                    {index['change']:+.2f}<br>
                    <small>({index['change_percent']:+.2f}%)</small>
                </div>
            </div>
            <hr class="my-2">
            '''
        return html
    
    def _generate_top_movers_table(self, movers: List[Dict]) -> str:
        """Generate HTML table rows for top movers"""
        html = ""
        for mover in movers:
            color = "success" if mover['change'] >= 0 else "danger"
            
            html += f'''
            <tr>
                <td><strong>{mover['symbol']}</strong></td>
                <td>{mover['price']:.2f}€</td>
                <td class="text-{color}">{mover['change']:+.2f}</td>
            </tr>
            '''
        return html
    
    def _generate_market_data_table(self, stocks: List[Dict]) -> str:
        """Generate HTML table rows for market data"""
        html = ""
        for stock in stocks:
            change_color = "success" if stock['change'] >= 0 else "danger"
            status_color = "success" if stock['status'] == 'LIVE' else "warning"
            
            html += f'''
            <tr data-symbol="{stock['symbol']}">
                <td><strong>{stock['symbol']}</strong></td>
                <td>{stock['name']}</td>
                <td class="price-cell">{stock['price']:.2f}€</td>
                <td class="change-cell text-{change_color}">{stock['change']:+.2f}</td>
                <td class="change-cell text-{change_color}">{stock['change_percent']:+.2f}%</td>
                <td class="volume-cell" data-volume="{stock['volume'].replace('M', '000000')}">{stock['volume']}</td>
                <td>{stock['market_cap']}</td>
                <td>{stock['pe_ratio']:.1f}</td>
                <td><span class="badge bg-{status_color}">{stock['status']}</span></td>
            </tr>
            '''
        return html
    
    def _get_market_status_color(self, status: str) -> str:
        """Get color based on market status"""
        colors = {
            'OPEN': 'success',
            'CLOSED': 'danger',
            'PRE_MARKET': 'warning',
            'AFTER_HOURS': 'info'
        }
        return colors.get(status, 'secondary')
    
    def _get_sentiment_color(self, score: int) -> str:
        """Get color based on sentiment score"""
        if score >= 70:
            return "success"
        elif score >= 40:
            return "warning"
        else:
            return "danger"
    
    def _get_connection_status_color(self, service: str) -> str:
        """Get color based on connection status"""
        # Mock connection status - should be real status checks
        statuses = {
            'websocket': 'success',
            'api': 'success',
            'database': 'success',
            'external': 'warning'  # Some external APIs might have issues
        }
        return statuses.get(service, 'danger')