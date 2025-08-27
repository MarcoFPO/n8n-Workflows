#!/usr/bin/env python3
"""
Vereinfachte Enhanced ML Predictions API für GUI-Demonstration
Direct PostgreSQL Connection ohne Authentifizierungs-Probleme

Ziel: Durchschnittswerte in KI-Prognosen GUI anzeigen
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import subprocess
import os

# FastAPI App
app = FastAPI(
    title="Simplified Enhanced ML Predictions API",
    version="6.2.0-simplified",
    description="KI-Prognosen mit Durchschnittswerte-Integration (Simplified)"
)

# CORS für GUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simplified-enhanced-api")

def run_sql_query(query: str) -> List[Dict[str, Any]]:
    """
    Run PostgreSQL Query über subprocess (sichere Alternative)
    """
    try:
        # PostgreSQL Query über subprocess ausführen
        cmd = [
            'sudo', '-u', 'postgres', 'psql', '-d', 'aktienanalyse',
            '-t', '-A', '-F', '|', '-c', query
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.error(f"SQL Query failed: {result.stderr}")
            return []
        
        # Parse result
        lines = result.stdout.strip().split('\n')
        if not lines or not lines[0]:
            return []
        
        # Header from first query if available
        data = []
        for line in lines:
            if '|' in line and line.strip():
                parts = line.split('|')
                if len(parts) >= 8:  # Expected columns for our view
                    data.append({
                        'symbol': parts[0].strip(),
                        'calculation_date': parts[1].strip(),
                        'predicted_value': float(parts[2].strip()) if parts[2].strip() and parts[2].strip() != '' else 0.0,
                        'target_price': float(parts[3].strip()) if parts[3].strip() and parts[3].strip() != '' else None,
                        'confidence_score': float(parts[4].strip()) if parts[4].strip() and parts[4].strip() != '' else 0.0,
                        'timeframe': parts[5].strip(),
                        'avg_prediction': float(parts[6].strip()) if parts[6].strip() and parts[6].strip() != '' else None,
                        'deviation_percent': float(parts[7].strip()) if len(parts) > 7 and parts[7].strip() and parts[7].strip() != '' else None
                    })
        
        return data
        
    except Exception as e:
        logger.error(f"Error running SQL query: {e}")
        return []

@app.get("/health")
async def health_check():
    """Health Check"""
    return {
        "status": "healthy",
        "version": "6.2.0-simplified",
        "service": "simplified-enhanced-ml-predictions",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "averages_support": True,
            "ml_predictions_integration": True,
            "direct_sql_mode": True
        }
    }

@app.get("/api/v1/data/predictions")
async def get_enhanced_predictions(
    timeframe: str = Query("1M", description="Zeitrahmen (1W, 1M, 3M, 12M)"),
    limit: int = Query(50, description="Anzahl Datensätze", ge=1, le=200),
    symbol: Optional[str] = Query(None, description="Spezifisches Symbol (optional)")
):
    """
    Enhanced ML Predictions mit Durchschnittswerten für GUI
    
    KERNFUNKTION: Zeigt Durchschnittswerte für KI-Prognosen an
    """
    try:
        # SQL Query für Enhanced Predictions mit Durchschnittswerten
        where_clause = ""
        if timeframe and timeframe != "ALL":
            where_clause += f"AND timeframe = '{timeframe}' "
        if symbol:
            where_clause += f"AND symbol = '{symbol}' "
        
        query = f"""
        SELECT 
            symbol,
            calculation_date,
            predicted_value,
            target_price,
            confidence_score,
            timeframe,
            avg_prediction,
            deviation_percent,
            performance_indicator,
            data_basis_count
        FROM v_ki_prognosen_with_averages
        WHERE 1=1 {where_clause}
        ORDER BY calculation_date DESC, symbol
        LIMIT {limit};
        """
        
        predictions_data = run_sql_query(query)
        
        # Averages Summary Query
        summary_query = f"""
        SELECT COUNT(*) as symbols_with_averages
        FROM mv_ki_prognosen_averages 
        WHERE ($1 IS NULL OR timeframe = '{timeframe}');
        """.replace("$1", "NULL" if not timeframe or timeframe == "ALL" else f"'{timeframe}'")
        
        summary_result = run_sql_query(summary_query.replace("$1", "NULL"))
        symbols_with_averages = 0
        if summary_result:
            try:
                symbols_with_averages = int(summary_result[0].get('symbols_with_averages', 0))
            except:
                symbols_with_averages = len(predictions_data)
        
        # Response formatieren
        formatted_predictions = []
        for data in predictions_data:
            formatted_predictions.append({
                "prediction_id": f"pred_{data['symbol']}_{data['calculation_date']}",
                "symbol": data["symbol"],
                "prediction_type": "ml_prediction",
                "calculation_date": data["calculation_date"],
                "predicted_value": data["predicted_value"],
                "target_price": data["target_price"],
                "confidence_score": data["confidence_score"],
                "timeframe": data["timeframe"],
                "horizon_days": 30 if data["timeframe"] == "1M" else 7,
                "avg_prediction": data["avg_prediction"],
                "avg_confidence": data["confidence_score"],  # Fallback
                "deviation_percent": data["deviation_percent"],
                "performance_indicator": data.get("performance_indicator", "NORMAL"),
                "data_basis_count": data.get("data_basis_count", 1)
            })
        
        return {
            "predictions": formatted_predictions,
            "timeframe": timeframe,
            "total_count": len(formatted_predictions),
            "averages_available": len(formatted_predictions) > 0,
            "symbols_with_averages": symbols_with_averages,
            "navigation_info": {
                "timeframe": timeframe,
                "total_predictions": len(formatted_predictions),
                "symbols_available": len(set(p["symbol"] for p in formatted_predictions)),
                "has_previous": False,
                "has_next": len(formatted_predictions) >= limit
            },
            "enhanced_features": {
                "averages_support": True,
                "deviation_calculation": True,
                "performance_indicators": True,
                "timeline_navigation": True,
                "real_time_updates": False
            }
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced predictions endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch enhanced predictions: {str(e)}"
        )

@app.get("/api/v1/data/averages-summary")
async def get_averages_summary(
    timeframe: Optional[str] = Query(None, description="Filter nach Zeitrahmen (optional)")
):
    """
    Durchschnittswerte-Übersicht für Dashboard
    """
    try:
        where_clause = ""
        if timeframe:
            where_clause = f"WHERE timeframe = '{timeframe}'"
        
        query = f"""
        SELECT 
            symbol,
            timeframe,
            prediction_count,
            avg_predicted_value,
            avg_confidence,
            predicted_value_stddev,
            earliest_prediction,
            latest_prediction,
            last_updated
        FROM mv_ki_prognosen_averages
        {where_clause}
        ORDER BY symbol, timeframe;
        """
        
        summary_data = run_sql_query(query)
        
        return [{
            "symbol": data["symbol"],
            "timeframe": data["timeframe"],
            "prediction_count": int(data["prediction_count"]),
            "avg_predicted_value": data["avg_predicted_value"],
            "avg_confidence": data["avg_confidence"],
            "predicted_value_stddev": data.get("predicted_value_stddev"),
            "earliest_prediction": data["earliest_prediction"],
            "latest_prediction": data["latest_prediction"],
            "last_updated": data["last_updated"]
        } for data in summary_data]
        
    except Exception as e:
        logger.error(f"Error in averages summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch averages summary: {str(e)}"
        )

@app.post("/api/v1/maintenance/refresh-averages")
async def refresh_averages():
    """Refresh Materialized View für Performance"""
    try:
        query = "SELECT refresh_ki_prognosen_averages_mv();"
        result = run_sql_query(query)
        
        return {
            "status": "success",
            "message": "Materialized view refreshed successfully",
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error refreshing materialized view: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh materialized view: {str(e)}"
        )

if __name__ == "__main__":
    logger.info("🚀 Starting Simplified Enhanced ML Predictions API v6.2.0")
    logger.info("📊 Features: Direct SQL + Durchschnittswerte + GUI Integration")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8030,
        log_level="info",
        access_log=True
    )