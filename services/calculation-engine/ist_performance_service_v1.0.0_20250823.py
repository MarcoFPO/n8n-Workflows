#!/usr/bin/env python3
"""
IST-Performance Service v1.0.0
Separater Service für echte Kursperformance-Berechnung

Läuft auf eigenem Port (8019) und stört die ML-Pipeline nicht
Integration: SOLL-IST Vergleichsanalyse mit echten Kursdaten

Autor: Claude Code
Datum: 23. August 2025
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

# Import des IST Performance Calculator Moduls
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Calculator Funktionen direkt aus der Datei
exec(open('ist_performance_calculator_v1.0.0_20250823.py').read())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI Application Setup
app = FastAPI(
    title="IST-Performance Service",
    version="1.0.0",
    description="Service für echte Kursperformance-Berechnung (SOLL-IST Vergleich)"
)

# CORS Configuration - Relaxed für private Entwicklungsumgebung
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Service Health Check"""
    return {
        "status": "healthy",
        "service": "ist-performance-service",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "description": "IST-Performance Calculator für echte Kursdaten"
    }

@app.get("/api/v1/ist-performance")
async def get_ist_performance_endpoint(
    symbols: str = Query(..., description="Komma-getrennte Liste von Stock Symbols"),
    timeframe: str = Query(default="1M", description="Zeitraum: 1W, 1M, 3M, 6M, 1Y")
):
    """
    IST-Performance für mehrere Symbole berechnen
    
    Args:
        symbols: Komma-getrennte Symbole (z.B. "AAPL,NVDA,TSLA")
        timeframe: Zeitraum (1W, 1M, 3M, 6M, 1Y)
        
    Returns:
        JSON mit symbol -> performance_percent mapping
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        logger.info(f"📊 Calculating IST performance for {len(symbol_list)} symbols ({timeframe})")
        
        performance_data = await get_ist_performance_data(symbol_list, timeframe)
        
        return {
            "status": "success",
            "timeframe": timeframe,
            "symbol_count": len(symbol_list),
            "performance_data": performance_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error calculating IST performance: {e}")
        raise HTTPException(status_code=500, detail=f"Error calculating performance: {str(e)}")

@app.get("/api/v1/vergleichsanalyse/csv")
async def get_soll_ist_vergleich_with_real_data(
    timeframe: str = Query(default="1M", description="Zeitraum: 1W, 1M, 3M, 6M, 1Y")
):
    """
    SOLL-IST Vergleichsanalyse mit echten IST-Kursdaten
    
    Holt SOLL-Daten vom Data Processing Service und berechnet echte IST-Daten
    """
    try:
        import requests
        import csv
        import io
        
        # SOLL-Daten vom Data Processing Service holen (localhost für Development)
        soll_url = f"http://localhost:8017/api/v1/data/predictions?timeframe={timeframe}"
        logger.info(f"📊 Fetching SOLL data from: {soll_url}")
        
        soll_response = requests.get(soll_url, timeout=10)
        if soll_response.status_code != 200:
            raise HTTPException(status_code=404, detail="Could not fetch SOLL predictions data")
        
        soll_csv_content = soll_response.text
        
        # SOLL-Daten parsen
        soll_data = []
        csv_reader = csv.DictReader(io.StringIO(soll_csv_content))
        for row in csv_reader:
            if row['Symbol'] != 'Error' and row['Symbol'].strip():
                try:
                    soll_gewinn = float(row['Vorhergesagter_Gewinn'].replace('%', ''))
                    soll_data.append({
                        'symbol': row['Symbol'].strip(),
                        'company': row['Company'],
                        'soll_gewinn': soll_gewinn,
                        'risiko': row['Risiko']
                    })
                except (ValueError, KeyError) as e:
                    logger.warning(f"⚠️ Skipping invalid SOLL data row: {e}")
                    continue
        
        if not soll_data:
            raise HTTPException(status_code=404, detail="No valid SOLL data found")
        
        logger.info(f"📊 Found {len(soll_data)} valid SOLL entries")
        
        # IST-Performance für alle Symbole berechnen
        symbols = [item['symbol'] for item in soll_data]
        ist_performance_data = await get_ist_performance_data(symbols, timeframe)
        
        # SOLL-IST CSV generieren
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Symbol", "Company", "SOLL_Gewinn", "IST_Gewinn", "Abweichung", "Status", "Risiko"])
        
        for soll in soll_data:
            symbol = soll['symbol']
            ist_gewinn = ist_performance_data.get(symbol, 0.0)
            abweichung = ist_gewinn - soll['soll_gewinn']
            
            # Status basierend auf Abweichung
            if abweichung >= 5.0:
                status = "ÜBERTROFFEN"
            elif abweichung >= -5.0:
                status = "ERREICHT"
            else:
                status = "VERFEHLT"
            
            writer.writerow([
                symbol,
                soll['company'],
                f"{soll['soll_gewinn']:.1f}%",
                f"{ist_gewinn:.1f}%", 
                f"{abweichung:+.1f}%",
                status,
                soll['risiko']
            ])
        
        csv_result = output.getvalue()
        logger.info(f"✅ Generated SOLL-IST comparison with real IST data for {len(soll_data)} entries")
        
        return Response(
            content=csv_result,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=soll_ist_real_{timeframe.lower()}.csv"}
        )
        
    except requests.RequestException as e:
        logger.error(f"❌ Error fetching SOLL data: {e}")
        raise HTTPException(status_code=503, detail=f"Could not fetch SOLL data: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error generating SOLL-IST comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating comparison: {str(e)}")

@app.get("/api/v1/test-performance")
async def test_performance_calculation(
    symbols: str = Query(default="AAPL,NVDA,TSLA", description="Test symbols"),
    timeframe: str = Query(default="1M", description="Test timeframe")
):
    """Test endpoint für Performance-Berechnung"""
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    
    logger.info(f"🧪 Testing performance calculation for: {symbol_list}")
    
    # Detaillierte Performance-Daten für Test
    performance_data = await ist_calculator.calculate_batch_performance(symbol_list, timeframe)
    
    test_results = {}
    for symbol, perf_data in performance_data.items():
        test_results[symbol] = {
            "success": perf_data.success,
            "start_price": perf_data.start_price,
            "end_price": perf_data.end_price,
            "performance_percent": perf_data.performance_percent,
            "start_date": perf_data.start_date.isoformat(),
            "end_date": perf_data.end_date.isoformat(),
            "error": perf_data.error_message
        }
    
    return {
        "test_results": test_results,
        "summary": {
            "total_symbols": len(symbol_list),
            "successful": len([r for r in performance_data.values() if r.success]),
            "failed": len([r for r in performance_data.values() if not r.success])
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint mit Service Info"""
    return {
        "service": "IST-Performance Service",
        "version": "1.0.0",
        "description": "Service für echte Kursperformance-Berechnung",
        "endpoints": [
            "/health",
            "/api/v1/ist-performance",
            "/api/v1/vergleichsanalyse/csv", 
            "/api/v1/test-performance"
        ],
        "port": 8030,
        "isolated": "Läuft getrennt von ML-Pipeline"
    }

if __name__ == "__main__":
    logger.info("🚀 Starting IST-Performance Service v1.0.0 on Port 8030")
    logger.info("🔒 Isolated from ML-Pipeline - No interference with training")
    
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=8030,
        log_level="info"
    )