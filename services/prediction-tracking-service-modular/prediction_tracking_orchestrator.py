#!/usr/bin/env python3

import os
import sys
import sqlite3
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from typing import List, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(title="Prediction Tracking Service", version="1.0.0")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DB_PATH = "/home/mdoehler/aktienanalyse-ökosystem/services/prediction-tracking-service-modular/predictions.db"

def init_database():
    """Initialize SQLite database with required tables."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create predictions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            predicted_return REAL NOT NULL,
            predicted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            actual_return REAL DEFAULT NULL,
            evaluation_date TIMESTAMP DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create performance tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timeframe TEXT NOT NULL,
            prediction_count INTEGER DEFAULT 0,
            correct_predictions INTEGER DEFAULT 0,
            accuracy_percentage REAL DEFAULT 0.0,
            avg_predicted_return REAL DEFAULT 0.0,
            avg_actual_return REAL DEFAULT 0.0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Pydantic models
class PredictionStore(BaseModel):
    symbol: str
    timeframe: str
    predicted_return: float

class PredictionList(BaseModel):
    predictions: List[PredictionStore]

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_database()
    logger.info("🚀 Prediction Tracking Service started successfully")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "prediction-tracking", "timestamp": datetime.now()}

@app.post("/store-prediction")
async def store_prediction(prediction_data: PredictionList):
    """Store predictions for later performance tracking."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for pred in prediction_data.predictions:
            cursor.execute('''
                INSERT INTO predictions (symbol, timeframe, predicted_return)
                VALUES (?, ?, ?)
            ''', (pred.symbol, pred.timeframe, pred.predicted_return))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Stored {len(prediction_data.predictions)} predictions")
        return {"status": "success", "stored": len(prediction_data.predictions)}
        
    except Exception as e:
        logger.error(f"❌ Error storing predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/performance-comparison/{timeframe}")
async def get_performance_comparison(timeframe: str):
    """Get SOLL-IST performance comparison for timeframe."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get recent predictions for the timeframe
        cursor.execute('''
            SELECT symbol, predicted_return, predicted_date
            FROM predictions
            WHERE timeframe = ?
            ORDER BY predicted_date DESC
            LIMIT 15
        ''', (timeframe,))
        
        predictions = cursor.fetchall()
        
        # Mock actual returns for demonstration (in production, this would fetch real market data)
        import random
        performance_data = []
        
        for symbol, predicted_return, predicted_date in predictions:
            # Simulate actual return (±20% variance from prediction)
            actual_return = predicted_return * (1 + random.uniform(-0.2, 0.2))
            
            performance_data.append({
                "symbol": symbol,
                "soll_return": round(predicted_return, 2),
                "ist_return": round(actual_return, 2),
                "difference": round(actual_return - predicted_return, 2),
                "prediction_date": predicted_date,
                "timeframe": timeframe
            })
        
        conn.close()
        
        logger.info(f"📊 Generated performance comparison for {timeframe}: {len(performance_data)} items")
        return {
            "timeframe": timeframe,
            "comparison_data": performance_data,
            "summary": {
                "total_predictions": len(performance_data),
                "avg_soll": round(sum(item["soll_return"] for item in performance_data) / len(performance_data) if performance_data else 0, 2),
                "avg_ist": round(sum(item["ist_return"] for item in performance_data) / len(performance_data) if performance_data else 0, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting performance comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics")
async def get_statistics():
    """Get overall prediction statistics."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM predictions')
        total_predictions = cursor.fetchone()[0]
        
        cursor.execute('SELECT timeframe, COUNT(*) FROM predictions GROUP BY timeframe')
        timeframe_stats = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_predictions": total_predictions,
            "timeframe_breakdown": timeframe_stats,
            "service_status": "active",
            "last_updated": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info("🎯 Starting Prediction Tracking Service on port 8018")
    uvicorn.run(app, host="0.0.0.0", port=8018, log_level="info")