#!/usr/bin/env python3
"""
SOLL-IST Vergleichsanalyse CSV Service
Stellt SOLL-IST Vergleichsdaten als CSV für die Frontend Vergleichsanalyse bereit
"""

import aiohttp
import json
import io
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import structlog

# Logging setup
logger = structlog.get_logger("vergleichsanalyse-csv")

# FastAPI App
app = FastAPI(title="Vergleichsanalyse CSV Service", version="1.0.0")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prediction Tracking Service URL
PREDICTION_TRACKING_URL = "http://localhost:8018"

def generate_vergleichsanalyse_csv(comparison_data: list) -> str:
    """Generate CSV for SOLL-IST comparison data"""
    output = io.StringIO()
    
    # CSV Header - Angepasst für Symbol und Company Spalten
    header = "Datum,Symbol,Company,Vorhergesagter_Gewinn_%,Wirklicher_Gewinn_%,Unterschied_%,Zeitintervall\n"
    output.write(header)
    
    # CSV Rows
    # Sort by predicted profit (soll_return) descending - Höchster Gewinn zuerst
    comparison_data = sorted(comparison_data, key=lambda x: float(x.get("soll_return", 0)), reverse=True)

    for item in comparison_data:
        # Parse predicted_date to get date only
        try:
            pred_date = datetime.fromisoformat(item['prediction_date'].replace(' ', 'T')).date()
        except:
            pred_date = item['prediction_date'][:10]  # Extract date part
        
        # Row mit Symbol und Company Spalten
        symbol = item['symbol']
        company = f"{symbol} Corporation"
        
        row = f"{pred_date},{symbol},{company},{item['soll_return']:.1f}%,{item['ist_return']:.1f}%,{item['difference']:+.1f}%,{item['timeframe']}\n"
        output.write(row)
    
    return output.getvalue()

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "vergleichsanalyse-csv",
        "prediction_tracking_url": PREDICTION_TRACKING_URL,
        "version": "2.0.0_fixed_symbols_sorting"
    }

@app.get("/api/v1/vergleichsanalyse/csv")
async def get_vergleichsanalyse_csv(timeframe: str = Query(default="1M", description="Zeitintervall: 1W, 1M, 3M")):
    """SOLL-IST Vergleichsanalyse als CSV für gewähltes Zeitintervall - Sortiert nach Vorhergesagter_Gewinn"""
    try:
        # Fetch data from Prediction Tracking Service
        url = f"{PREDICTION_TRACKING_URL}/performance-comparison/{timeframe}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise HTTPException(status_code=500, detail=f"Failed to fetch comparison data: {response.status}")
                
                data = await response.json()
                
                if not data.get('comparison_data'):
                    # Return empty CSV with headers
                    csv_content = "Datum,Symbol,Company,Vorhergesagter_Gewinn_%,Wirklicher_Gewinn_%,Unterschied_%,Zeitintervall\n"
                    csv_content += f"# Keine Daten verfügbar für Zeitintervall {timeframe},,,,,"
                else:
                    csv_content = generate_vergleichsanalyse_csv(data['comparison_data'])
                
                logger.info(f"✅ Generated SOLL-IST CSV for {timeframe}: {len(data.get('comparison_data', []))} comparisons")
                
                return Response(
                    content=csv_content,
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": f"attachment; filename=vergleichsanalyse_{timeframe.lower()}.csv",
                        "Access-Control-Allow-Origin": "*"
                    }
                )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating SOLL-IST CSV for {timeframe}: {e}")
        # Return error CSV
        error_csv = "Datum,Symbol,Company,Vorhergesagter_Gewinn_%,Wirklicher_Gewinn_%,Unterschied_%,Zeitintervall\n"
        error_csv += f"# Fehler beim Laden der Daten: {str(e)},,,,,"
        
        return Response(
            content=error_csv,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=vergleichsanalyse_error_{timeframe.lower()}.csv"}
        )

@app.get("/api/v1/vergleichsanalyse/summary")
async def get_vergleichsanalyse_summary(timeframe: str = Query(default="1M", description="Zeitintervall: 1W, 1M, 3M")):
    """SOLL-IST Vergleichsanalyse Summary für gewähltes Zeitintervall"""
    try:
        # Fetch data from Prediction Tracking Service
        url = f"{PREDICTION_TRACKING_URL}/performance-comparison/{timeframe}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise HTTPException(status_code=500, detail=f"Failed to fetch comparison data: {response.status}")
                
                data = await response.json()
                comparison_data = data.get('comparison_data', [])
                
                if not comparison_data:
                    return {
                        "timeframe": timeframe,
                        "total_comparisons": 0,
                        "summary": "Keine Daten verfügbar",
                        "avg_difference": 0.0,
                        "best_prediction": None,
                        "worst_prediction": None
                    }
                
                # Calculate summary metrics
                differences = [item['difference'] for item in comparison_data]
                avg_difference = sum(differences) / len(differences)
                
                best_prediction = max(comparison_data, key=lambda x: x['difference'])
                worst_prediction = min(comparison_data, key=lambda x: x['difference'])
                
                return {
                    "timeframe": timeframe,
                    "total_comparisons": len(comparison_data),
                    "avg_difference": round(avg_difference, 2),
                    "best_prediction": {
                        "symbol": best_prediction['symbol'],
                        "difference": best_prediction['difference']
                    },
                    "worst_prediction": {
                        "symbol": worst_prediction['symbol'],
                        "difference": worst_prediction['difference']
                    }
                }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating summary for {timeframe}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("🚀 Starting SOLL-IST Vergleichsanalyse CSV Service...")
    uvicorn.run(app, host="0.0.0.0", port=8019)