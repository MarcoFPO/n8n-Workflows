#!/usr/bin/env python3
"""
Einfacher Starter für Frontend Service v2
Löst asyncio Event-Loop-Probleme
"""

import sys
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

from frontend_service_v2 import FrontendService
import uvicorn

# Service direkt mit uvicorn starten
if __name__ == "__main__":
    service = FrontendService()
    
    # Synchrone Initialisierung für uvicorn
    import asyncio
    asyncio.run(service._setup_service())
    
    # Server mit uvicorn starten
    uvicorn.run(
        service.app,
        host="0.0.0.0",
        port=8005,
        log_level="info"
    )