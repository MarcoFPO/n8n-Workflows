#!/usr/bin/env python3
"""
FRONTEND-NAV-001 Direct Route Fix Test
Minimal implementation to test navigation routes
"""

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(
    title="FRONTEND-NAV-001 Fix Test",
    version="1.0.0"
)

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Navigation Test</title></head>
    <body>
        <h1>🚀 FRONTEND-NAV-001 Fix Test</h1>
        <nav>
            <a href="/dashboard">📈 Dashboard</a> | 
            <a href="/ki-vorhersage">🤖 KI-Vorhersage</a> | 
            <a href="/soll-ist-vergleich">📊 SOLL-IST</a> | 
            <a href="/depot">💼 Depot</a>
        </nav>
        <p>Testing all 4 navigation routes...</p>
    </body>
    </html>
    """

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return """
    <html><body>
        <h1>✅ Dashboard Route Works!</h1>
        <p>FRONTEND-NAV-001 Fix: Dashboard route is functional</p>
        <a href="/">🔙 Back to Home</a>
    </body></html>
    """

@app.get("/ki-vorhersage", response_class=HTMLResponse)
async def ki_vorhersage():
    return """
    <html><body>
        <h1>✅ KI-Vorhersage Route Works!</h1>
        <p>FRONTEND-NAV-001 Fix: KI-Vorhersage route is functional</p>
        <a href="/">🔙 Back to Home</a>
    </body></html>
    """

@app.get("/soll-ist-vergleich", response_class=HTMLResponse)
async def soll_ist_vergleich():
    return """
    <html><body>
        <h1>✅ SOLL-IST Vergleich Route Works!</h1>
        <p>FRONTEND-NAV-001 Fix: SOLL-IST route is functional</p>
        <a href="/">🔙 Back to Home</a>
    </body></html>
    """

@app.get("/depot", response_class=HTMLResponse)
async def depot():
    return """
    <html><body>
        <h1>✅ Depot Route Works!</h1>
        <p>FRONTEND-NAV-001 Fix: Depot route is functional</p>
        <a href="/">🔙 Back to Home</a>
    </body></html>
    """

@app.get("/health")
async def health():
    return {"status": "ok", "message": "FRONTEND-NAV-001 Fix Test Service"}

if __name__ == "__main__":
    print("🧪 Starting FRONTEND-NAV-001 Fix Test Service on port 8081")
    uvicorn.run(app, host="0.0.0.0", port=8081)