"""
🧠 Technical Analysis Content Provider
Provides real-time technical analysis data and charts
"""

import asyncio
import logging
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class TechnicalAnalysisProvider:
    """Technical Analysis Content Provider"""
    
    def __init__(self, event_bus, api_gateway):
        self.event_bus = event_bus
        self.api_gateway = api_gateway
        self.logger = logger
        
    async def get_technical_analysis_content(self, context: Dict[str, Any]) -> str:
        """Generate technical analysis dashboard content"""
        await self.event_bus.emit("frontend.technical_analysis.requested", {"context": context})
        
        # Mock data for now - will be replaced with real API calls
        technical_data = await self._get_technical_indicators()
        
        return f'''
        <div class="row">
            <div class="col-12 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-line me-2"></i>Technical Analysis Dashboard</h5>
                        <small class="text-muted">Real-time Technical Indicators</small>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <!-- RSI Indicator -->
                            <div class="col-md-3 mb-3">
                                <div class="card bg-light">
                                    <div class="card-body text-center">
                                        <i class="fas fa-wave-square fa-2x mb-2 text-primary"></i>
                                        <h4 class="text-{self._get_rsi_color(technical_data['rsi'])}">{technical_data['rsi']:.1f}</h4>
                                        <p class="mb-0">RSI (14)</p>
                                        <small class="text-muted">{self._get_rsi_signal(technical_data['rsi'])}</small>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- MACD Indicator -->
                            <div class="col-md-3 mb-3">
                                <div class="card bg-light">
                                    <div class="card-body text-center">
                                        <i class="fas fa-chart-area fa-2x mb-2 text-success"></i>
                                        <h4 class="text-{self._get_macd_color(technical_data['macd'])}">{technical_data['macd']:.3f}</h4>
                                        <p class="mb-0">MACD</p>
                                        <small class="text-muted">{self._get_macd_signal(technical_data['macd'])}</small>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Moving Average -->
                            <div class="col-md-3 mb-3">
                                <div class="card bg-light">
                                    <div class="card-body text-center">
                                        <i class="fas fa-chart-line fa-2x mb-2 text-warning"></i>
                                        <h4 class="text-{self._get_ma_color(technical_data['ma_signal'])}">{technical_data['sma_20']:.2f}€</h4>
                                        <p class="mb-0">SMA (20)</p>
                                        <small class="text-muted">{technical_data['ma_signal']}</small>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Bollinger Bands -->
                            <div class="col-md-3 mb-3">
                                <div class="card bg-light">
                                    <div class="card-body text-center">
                                        <i class="fas fa-compress-arrows-alt fa-2x mb-2 text-info"></i>
                                        <h4 class="text-{self._get_bb_color(technical_data['bb_position'])}">{technical_data['bb_width']:.2f}%</h4>
                                        <p class="mb-0">BB Width</p>
                                        <small class="text-muted">{technical_data['bb_signal']}</small>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Technical Analysis Table -->
                        <div class="table-responsive mt-4">
                            <table class="table table-hover">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Symbol</th>
                                        <th>Price</th>
                                        <th>RSI</th>
                                        <th>MACD</th>
                                        <th>SMA(20)</th>
                                        <th>Volume</th>
                                        <th>Signal</th>
                                        <th>Score</th>
                                    </tr>
                                </thead>
                                <tbody id="technical-analysis-table">
                                    {self._generate_technical_table(technical_data['stocks'])}
                                </tbody>
                            </table>
                        </div>
                        
                        <!-- Real-time Chart Placeholder -->
                        <div class="row mt-4">
                            <div class="col-12">
                                <div class="card">
                                    <div class="card-header">
                                        <h6><i class="fas fa-chart-candlestick me-2"></i>Price Chart with Technical Indicators</h6>
                                    </div>
                                    <div class="card-body">
                                        <div id="technical-chart" style="height: 400px;">
                                            <div class="text-center p-5">
                                                <i class="fas fa-chart-line fa-3x text-muted mb-3"></i>
                                                <p class="text-muted">Real-time Technical Analysis Chart</p>
                                                <small class="text-muted">Chart wird mit Live-Daten geladen...</small>
                                            </div>
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
        // Auto-refresh technical data every 30 seconds
        setInterval(function() {{
            // Will be implemented with WebSocket connection
            console.log('Refreshing technical analysis data...');
        }}, 30000);
        </script>
        '''
    
    async def _get_technical_indicators(self) -> Dict[str, Any]:
        """Get technical indicators - mock data for now"""
        # TODO: Replace with real API calls to data services
        return {
            'rsi': 67.8,
            'macd': 0.045,
            'sma_20': 142.85,
            'bb_width': 3.2,
            'bb_position': 0.75,
            'ma_signal': 'BULLISH',
            'bb_signal': 'EXPAND',
            'stocks': [
                {
                    'symbol': 'AAPL',
                    'price': 145.67,
                    'rsi': 67.8,
                    'macd': 0.045,
                    'sma_20': 142.85,
                    'volume': '45.2M',
                    'signal': 'BUY',
                    'score': 8.5
                },
                {
                    'symbol': 'MSFT',
                    'price': 312.45,
                    'rsi': 45.2,
                    'macd': -0.012,
                    'sma_20': 315.20,
                    'volume': '28.1M',
                    'signal': 'HOLD',
                    'score': 6.2
                },
                {
                    'symbol': 'GOOGL',
                    'price': 125.80,
                    'rsi': 72.1,
                    'macd': 0.089,
                    'sma_20': 123.45,
                    'volume': '22.8M',
                    'signal': 'BUY',
                    'score': 9.1
                },
                {
                    'symbol': 'TSLA',
                    'price': 245.30,
                    'rsi': 35.6,
                    'macd': -0.156,
                    'sma_20': 252.80,
                    'volume': '95.3M',
                    'signal': 'SELL',
                    'score': 3.8
                },
                {
                    'symbol': 'NVDA',
                    'price': 418.95,
                    'rsi': 82.4,
                    'macd': 0.234,
                    'sma_20': 395.60,
                    'volume': '67.4M',
                    'signal': 'BUY',
                    'score': 9.8
                }
            ]
        }
    
    def _generate_technical_table(self, stocks: List[Dict]) -> str:
        """Generate HTML table rows for technical analysis data"""
        html = ""
        for stock in stocks:
            signal_color = self._get_signal_color(stock['signal'])
            score_color = self._get_score_color(stock['score'])
            rsi_color = self._get_rsi_color(stock['rsi'])
            
            html += f'''
            <tr>
                <td><strong>{stock['symbol']}</strong></td>
                <td>{stock['price']:.2f}€</td>
                <td><span class="text-{rsi_color}">{stock['rsi']:.1f}</span></td>
                <td>{stock['macd']:+.3f}</td>
                <td>{stock['sma_20']:.2f}€</td>
                <td>{stock['volume']}</td>
                <td><span class="badge bg-{signal_color}">{stock['signal']}</span></td>
                <td><span class="text-{score_color}"><strong>{stock['score']:.1f}</strong></span></td>
            </tr>
            '''
        return html
    
    def _get_rsi_color(self, rsi: float) -> str:
        """Get color based on RSI value"""
        if rsi > 70:
            return "danger"  # Overbought
        elif rsi < 30:
            return "success"  # Oversold
        else:
            return "warning"  # Neutral
    
    def _get_macd_color(self, macd: float) -> str:
        """Get color based on MACD value"""
        return "success" if macd > 0 else "danger"
    
    def _get_ma_color(self, signal: str) -> str:
        """Get color based on moving average signal"""
        colors = {
            'BULLISH': 'success',
            'BEARISH': 'danger',
            'NEUTRAL': 'warning'
        }
        return colors.get(signal, 'secondary')
    
    def _get_bb_color(self, position: float) -> str:
        """Get color based on Bollinger Bands position"""
        if position > 0.8:
            return "danger"  # Near upper band
        elif position < 0.2:
            return "success"  # Near lower band
        else:
            return "info"  # Middle range
    
    def _get_signal_color(self, signal: str) -> str:
        """Get color based on trading signal"""
        colors = {
            'BUY': 'success',
            'SELL': 'danger',
            'HOLD': 'warning'
        }
        return colors.get(signal, 'secondary')
    
    def _get_score_color(self, score: float) -> str:
        """Get color based on analysis score"""
        if score >= 8:
            return "success"
        elif score >= 6:
            return "warning"
        else:
            return "danger"
    
    def _get_rsi_signal(self, rsi: float) -> str:
        """Get RSI signal description"""
        if rsi > 70:
            return "Überkauft"
        elif rsi < 30:
            return "Überverkauft"
        else:
            return "Neutral"
    
    def _get_macd_signal(self, macd: float) -> str:
        """Get MACD signal description"""
        return "Bullish" if macd > 0 else "Bearish"