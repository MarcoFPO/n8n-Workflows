#!/usr/bin/env python3
"""
Frontend Service Starter v2.0.0
Clean Code - Keine hardcoded Pfade
"""

import sys
from pathlib import Path

# Zentrale Konfiguration verwenden
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.central_config_v1_0_0_20250821 import config
from frontend_service_v2 import FrontendService
import uvicorn

# Service direkt mit uvicorn starten
if __name__ == "__main__":
    service = FrontendService()
    
    # Synchrone Initialisierung für uvicorn
    import asyncio
    asyncio.run(service._setup_service())
    
    # Server mit zentraler Konfiguration starten
    frontend_config = config.SERVICES["frontend"]
    uvicorn.run(
        service.app,
        host=frontend_config["host"],
        port=frontend_config["port"],
        log_level="info"
    )