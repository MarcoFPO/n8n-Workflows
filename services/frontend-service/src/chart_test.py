#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chart Test Seite - Isolierte Implementierung für Chart-Funktionalität
Einfache Test-Umgebung ohne Abhängigkeiten zum Hauptsystem
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="Chart Test Service", version="1.0.0")

# Test-Daten für Charts
test_stock_data = [
    {"symbol": "AAPL", "price": 175.43, "change": 2.34, "change_percent": 1.35},
    {"symbol": "GOOGL", "price": 2843.12, "change": -15.67, "change_percent": -0.55},
    {"symbol": "MSFT", "price": 384.52, "change": 8.91, "change_percent": 2.37},
    {"symbol": "TSLA", "price": 248.67, "change": 12.45, "change_percent": 5.27},
    {"symbol": "NVDA", "price": 456.78, "change": 23.12, "change_percent": 5.33}
]

test_prediction_data = [
    {"symbol": "AAPL", "prediction_7d": 178.50, "prediction_1m": 185.20, "prediction_1y": 220.15},
    {"symbol": "GOOGL", "prediction_7d": 2890.45, "prediction_1m": 2950.33, "prediction_1y": 3200.78},
    {"symbol": "MSFT", "prediction_7d": 392.15, "prediction_1m": 410.67, "prediction_1y": 465.23},
    {"symbol": "TSLA", "prediction_7d": 265.34, "prediction_1m": 289.12, "prediction_1y": 320.45},
    {"symbol": "NVDA", "prediction_7d": 485.67, "prediction_1m": 520.34, "prediction_1y": 678.90}
]

@app.get("/", response_class=HTMLResponse)
async def chart_test_page():
    """Test-Seite für Chart-Funktionalität"""
    
    html_content = """
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chart Test - Aktienanalyse</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
                min-height: 100vh;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            }
            
            h1 {
                text-align: center;
                color: #2c3e50;
                margin-bottom: 30px;
                font-size: 2.5em;
                background: linear-gradient(45deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            
            .chart-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                gap: 30px;
                margin-bottom: 30px;
            }
            
            .chart-container {
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            }
            
            .chart-title {
                font-size: 1.3em;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 15px;
                text-align: center;
            }
            
            canvas {
                max-height: 400px;
            }
            
            .test-info {
                background: #e8f4fd;
                border: 1px solid #b3d7ff;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
                color: #2c5282;
            }
            
            .test-buttons {
                display: flex;
                gap: 10px;
                justify-content: center;
                margin: 20px 0;
            }
            
            .btn {
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            
            .btn-primary {
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
            }
            
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔧 Chart Test Environment</h1>
            
            <div class="test-info">
                <strong>Test-Modus:</strong> Diese Seite testet die Chart-Funktionalität isoliert ohne Abhängigkeiten zum Hauptsystem.
                <br><strong>Status:</strong> Chart.js erfolgreich geladen ✅
            </div>
            
            <div class="test-buttons">
                <button class="btn btn-primary" onclick="updateCharts()">📊 Charts Aktualisieren</button>
                <button class="btn btn-primary" onclick="generateRandomData()">🎲 Zufällige Daten</button>
                <button class="btn btn-primary" onclick="testAnimation()">🎭 Animation Testen</button>
            </div>
            
            <div class="chart-grid">
                <div class="chart-container">
                    <div class="chart-title">📈 Aktienkurse Übersicht</div>
                    <canvas id="stockChart"></canvas>
                </div>
                
                <div class="chart-container">
                    <div class="chart-title">🔮 Vorhersage-Performance</div>
                    <canvas id="predictionChart"></canvas>
                </div>
                
                <div class="chart-container">
                    <div class="chart-title">📊 Marktverteilung</div>
                    <canvas id="marketChart"></canvas>
                </div>
                
                <div class="chart-container">
                    <div class="chart-title">📉 Trend-Analyse</div>
                    <canvas id="trendChart"></canvas>
                </div>
            </div>
        </div>
        
        <script>
            // Chart-Konfigurationen
            const chartConfig = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: false
                    }
                }
            };
            
            // Test-Daten
            const stockData = """ + str(test_stock_data).replace("'", '"') + """;
            const predictionData = """ + str(test_prediction_data).replace("'", '"') + """;
            
            let charts = {};
            
            // Chart Initialisierung
            function initializeCharts() {
                // Aktien-Chart (Bar Chart)
                const stockCtx = document.getElementById('stockChart').getContext('2d');
                charts.stock = new Chart(stockCtx, {
                    type: 'bar',
                    data: {
                        labels: stockData.map(item => item.symbol),
                        datasets: [{
                            label: 'Aktueller Kurs ($)',
                            data: stockData.map(item => item.price),
                            backgroundColor: 'rgba(102, 126, 234, 0.8)',
                            borderColor: 'rgba(102, 126, 234, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        ...chartConfig,
                        scales: {
                            y: {
                                beginAtZero: false
                            }
                        }
                    }
                });
                
                // Vorhersage-Chart (Line Chart)
                const predictionCtx = document.getElementById('predictionChart').getContext('2d');
                charts.prediction = new Chart(predictionCtx, {
                    type: 'line',
                    data: {
                        labels: predictionData.map(item => item.symbol),
                        datasets: [
                            {
                                label: '7 Tage Vorhersage',
                                data: predictionData.map(item => item.prediction_7d),
                                borderColor: 'rgba(255, 99, 132, 1)',
                                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                                tension: 0.4
                            },
                            {
                                label: '1 Monat Vorhersage',
                                data: predictionData.map(item => item.prediction_1m),
                                borderColor: 'rgba(54, 162, 235, 1)',
                                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                                tension: 0.4
                            },
                            {
                                label: '1 Jahr Vorhersage',
                                data: predictionData.map(item => item.prediction_1y),
                                borderColor: 'rgba(75, 192, 192, 1)',
                                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                                tension: 0.4
                            }
                        ]
                    },
                    options: {
                        ...chartConfig,
                        scales: {
                            y: {
                                beginAtZero: false
                            }
                        }
                    }
                });
                
                // Markt-Chart (Doughnut Chart)
                const marketCtx = document.getElementById('marketChart').getContext('2d');
                charts.market = new Chart(marketCtx, {
                    type: 'doughnut',
                    data: {
                        labels: stockData.map(item => item.symbol),
                        datasets: [{
                            data: stockData.map(item => Math.abs(item.change_percent)),
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.8)',
                                'rgba(54, 162, 235, 0.8)',
                                'rgba(255, 205, 86, 0.8)',
                                'rgba(75, 192, 192, 0.8)',
                                'rgba(153, 102, 255, 0.8)'
                            ],
                            borderWidth: 2
                        }]
                    },
                    options: {
                        ...chartConfig,
                        plugins: {
                            legend: {
                                position: 'right'
                            }
                        }
                    }
                });
                
                // Trend-Chart (Radar Chart)
                const trendCtx = document.getElementById('trendChart').getContext('2d');
                charts.trend = new Chart(trendCtx, {
                    type: 'radar',
                    data: {
                        labels: ['Performance', 'Volatilität', 'Volumen', 'Momentum', 'Stärke'],
                        datasets: stockData.slice(0, 3).map((item, index) => ({
                            label: item.symbol,
                            data: [
                                Math.abs(item.change_percent) * 10,
                                Math.random() * 100,
                                Math.random() * 100,
                                Math.random() * 100,
                                Math.random() * 100
                            ],
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.2)',
                                'rgba(54, 162, 235, 0.2)',
                                'rgba(255, 205, 86, 0.2)'
                            ][index],
                            borderColor: [
                                'rgba(255, 99, 132, 1)',
                                'rgba(54, 162, 235, 1)',
                                'rgba(255, 205, 86, 1)'
                            ][index],
                            pointBackgroundColor: [
                                'rgba(255, 99, 132, 1)',
                                'rgba(54, 162, 235, 1)',
                                'rgba(255, 205, 86, 1)'
                            ][index]
                        }))
                    },
                    options: {
                        ...chartConfig,
                        scales: {
                            r: {
                                beginAtZero: true,
                                max: 100
                            }
                        }
                    }
                });
            }
            
            // Chart Update-Funktionen
            function updateCharts() {
                console.log('🔄 Charts werden aktualisiert...');
                Object.values(charts).forEach(chart => {
                    chart.update('active');
                });
            }
            
            function generateRandomData() {
                console.log('🎲 Zufällige Daten werden generiert...');
                
                // Stock Chart aktualisieren
                charts.stock.data.datasets[0].data = stockData.map(() => 
                    Math.random() * 500 + 100
                );
                
                // Prediction Chart aktualisieren
                charts.prediction.data.datasets.forEach(dataset => {
                    dataset.data = predictionData.map(() => 
                        Math.random() * 600 + 150
                    );
                });
                
                // Market Chart aktualisieren
                charts.market.data.datasets[0].data = stockData.map(() => 
                    Math.random() * 10 + 1
                );
                
                // Trend Chart aktualisieren
                charts.trend.data.datasets.forEach(dataset => {
                    dataset.data = dataset.data.map(() => Math.random() * 100);
                });
                
                updateCharts();
            }
            
            function testAnimation() {
                console.log('🎭 Animation wird getestet...');
                
                // Sequenzielle Chart-Updates für Animations-Test
                setTimeout(() => charts.stock.update('show'), 100);
                setTimeout(() => charts.prediction.update('show'), 300);
                setTimeout(() => charts.market.update('show'), 500);
                setTimeout(() => charts.trend.update('show'), 700);
            }
            
            // Initialisierung beim Laden der Seite
            document.addEventListener('DOMContentLoaded', function() {
                console.log('📊 Chart Test Environment wird initialisiert...');
                initializeCharts();
                console.log('✅ Alle Charts erfolgreich initialisiert!');
            });
        </script>
    </body>
    </html>
    """
    
    return html_content

@app.get("/api/test-data")
async def get_test_data():
    """API-Endpunkt für Test-Daten"""
    return {
        "stocks": test_stock_data,
        "predictions": test_prediction_data,
        "status": "success",
        "timestamp": "2024-01-20T10:30:00Z"
    }

@app.get("/health")
async def health_check():
    """Gesundheits-Check für den Test-Service"""
    return {
        "status": "healthy",
        "service": "Chart Test Service",
        "version": "1.0.0",
        "charts_available": ["stock", "prediction", "market", "trend"]
    }

if __name__ == "__main__":
    print("🔧 Chart Test Service wird gestartet...")
    print("📊 Zugriff über: http://localhost:8085")
    print("🧪 API-Dokumentation: http://localhost:8085/docs")
    
    uvicorn.run(
        "chart_test:app",
        host="0.0.0.0",
        port=8085,
        reload=True,
        access_log=True
    )