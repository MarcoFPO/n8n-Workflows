#!/usr/bin/env python3
"""
Debug Script für KI-Prognosen GUI Problem
Simuliert den Aufruf und analysiert die Response
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def debug_prognosen_issue():
    """Debug KI-Prognosen GUI Problem"""
    
    print("🔍 Debug: KI-Prognosen GUI Problem")
    print("=" * 50)
    
    # Test 1: Direkte Backend-API (Data Processing Service)
    print("\n1. 📡 Teste Data Processing Service (Port 8017)")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://10.1.1.174:8017/api/v1/data/predictions?timeframe=1M") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Backend API funktioniert: {len(data.get('predictions', []))} Predictions")
                    print(f"   Status: {data.get('status', 'N/A')}")
                    print(f"   Count: {data.get('count', 0)}")
                    
                    if data.get('predictions'):
                        sample = data['predictions'][0]
                        print(f"   Sample: {sample.get('symbol', 'N/A')} - {sample.get('prediction_percent', 'N/A')}")
                else:
                    print(f"❌ Backend API Fehler: Status {response.status}")
    except Exception as e:
        print(f"❌ Backend API Exception: {e}")
    
    # Test 2: Frontend Service /prognosen Endpoint 
    print("\n2. 🌐 Teste Frontend Service /prognosen")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://10.1.1.174:8080/prognosen?timeframe=1M") as response:
                if response.status == 200:
                    html_content = await response.text()
                    
                    # Analyse der HTML Response
                    has_table = "<table" in html_content
                    has_alert = "alert-warning" in html_content or "Keine Prognosen" in html_content
                    has_tbody = "<tbody>" in html_content
                    table_rows_count = html_content.count("<tr>") - 1  # -1 für Header
                    
                    print(f"✅ Frontend Response: {len(html_content)} bytes")
                    print(f"   HTML Table vorhanden: {has_table}")
                    print(f"   Alert-Warning vorhanden: {has_alert}")
                    print(f"   TBody vorhanden: {has_tbody}")
                    print(f"   Tabellen-Rows: {table_rows_count}")
                    
                    # Suche nach spezifischen Indikatoren
                    if "Keine Prognosen verfügbar" in html_content:
                        print("⚠️  PROBLEM: 'Keine Prognosen verfügbar' Meldung gefunden!")
                    
                    if "Loading KI-Prognosen from:" in html_content:
                        print("📡 Backend-URL wird aufgerufen")
                    
                    # Suche nach Error-Indikatoren
                    error_indicators = ["error", "exception", "failed", "unavailable"]
                    for indicator in error_indicators:
                        if indicator.lower() in html_content.lower():
                            print(f"⚠️  Error-Indikator gefunden: {indicator}")
                    
                else:
                    print(f"❌ Frontend Fehler: Status {response.status}")
    except Exception as e:
        print(f"❌ Frontend Exception: {e}")
    
    # Test 3: Service-Konfiguration prüfen
    print("\n3. ⚙️ Service-Konfiguration")
    print(f"   DATA_PROCESSING_URL: http://10.1.1.174:8017 (Standard)")
    print(f"   get_prediction_url(1M): http://10.1.1.174:8017/api/v1/data/predictions?timeframe=1M")
    
    # Test 4: Potential Issues identifizieren
    print("\n4. 🐛 Potentielle Probleme")
    print("   a) HTTP Client Timeout/Error")
    print("   b) JSON Response Parsing Fehler")
    print("   c) Data Processing Service HTTP Handler")
    print("   d) Template Rendering Logic")
    print("   e) JavaScript Frontend-Logik")
    
    print("\n" + "=" * 50)
    print("🔍 Debug abgeschlossen")

if __name__ == "__main__":
    asyncio.run(debug_prognosen_issue())