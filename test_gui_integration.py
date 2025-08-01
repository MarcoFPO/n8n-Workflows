#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Test GUI Integration der neuen Features
Testet die Integration aller Provider in die unified_frontend_service.py
"""

import asyncio
import sys
from pathlib import Path

# Pfad zum Frontend-Verzeichnis hinzufügen
sys.path.append(str(Path(__file__).parent / "frontend-domain"))

from unified_frontend_service import (
    UnifiedFrontendService,
    UnifiedEventBusConnector,
    UnifiedAPIGatewayConnector
)

async def test_gui_integration():
    """Teste die GUI-Integration aller neuen Provider"""
    print("🧪 TESTE GUI-INTEGRATION DER NEUEN FEATURES")
    print("=" * 60)
    
    try:
        # Service initialisieren
        service = UnifiedFrontendService()
        await service.initialize()
        
        # Test alle Provider
        test_sections = [
            'dashboard',
            'predictions', 
            'technical-analysis',
            'market-data',
            'portfolio-analytics',
            'trading-interface',
            'depot-overview',
            'depot-details',
            'depot-trading'
        ]
        
        results = {}
        
        for section in test_sections:
            try:
                print(f"\n📊 Teste {section}...")
                content = await service.get_content(section, {})
                
                if content and len(content) > 100:
                    print(f"   ✅ {section}: {len(content):,} Zeichen generiert")
                    results[section] = "SUCCESS"
                else:
                    print(f"   ⚠️  {section}: Zu wenig Content ({len(content) if content else 0} Zeichen)")
                    results[section] = "WARNING"
                    
            except Exception as e:
                print(f"   ❌ {section}: Fehler - {str(e)}")
                results[section] = "ERROR"
        
        # Ergebnisse zusammenfassen
        print("\n" + "=" * 60)
        print("📈 TESTERGEBNISSE ZUSAMMENFASSUNG:")
        print("=" * 60)
        
        success_count = sum(1 for r in results.values() if r == "SUCCESS")
        warning_count = sum(1 for r in results.values() if r == "WARNING")  
        error_count = sum(1 for r in results.values() if r == "ERROR")
        
        for section, result in results.items():
            status_icon = "✅" if result == "SUCCESS" else "⚠️" if result == "WARNING" else "❌"
            print(f"   {status_icon} {section:<20} {result}")
        
        print(f"\n📊 Gesamtergebnis: {success_count}/{len(test_sections)} Provider erfolgreich")
        
        if success_count >= 7:  # Mindestens 7 von 9 sollten funktionieren
            print("🎉 GUI-INTEGRATION ERFOLGREICH!")
            return True
        else:
            print("⚠️  GUI-Integration benötigt Nachbesserung")
            return False
            
    except Exception as e:
        print(f"❌ Kritischer Fehler: {str(e)}")
        return False
    finally:
        # Cleanup
        try:
            await service.event_bus.disconnect()
            await service.api_gateway.cleanup()
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(test_gui_integration())
    sys.exit(0 if success else 1)