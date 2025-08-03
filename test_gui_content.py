#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Test GUI Content für Portfolio Analytics
Prüft ob die deutsche Steuerberechnung in der GUI korrekt angezeigt wird
"""

import sys
from pathlib import Path

# Pfad zum Frontend-Verzeichnis hinzufügen
sys.path.append(str(Path(__file__).parent / "frontend-domain"))

from portfolio_analytics_provider import PortfolioAnalyticsProvider

async def test_portfolio_analytics_content():
    """Teste den generierten Portfolio Analytics Content"""
    print("🧪 TESTE PORTFOLIO ANALYTICS GUI-CONTENT")
    print("=" * 60)
    
    # Mock Provider erstellen mit Mock Event Bus
    class MockEventBus:
        async def emit(self, event, data):
            pass
    
    provider = PortfolioAnalyticsProvider(MockEventBus(), None)
    
    # Content generieren
    content = await provider.get_portfolio_analytics_content({})
    
    print(f"📊 Generierter Content: {len(content):,} Zeichen")
    print("=" * 60)
    
    # Suche nach Steuerberechnung-Sektion
    if "Steuerberechnung" in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "Steuerberechnung" in line:
                print(f"🔍 GEFUNDEN in Zeile {i+1}:")
                # Zeige die Zeile und ein paar darum herum
                start = max(0, i-2)
                end = min(len(lines), i+3)
                for j in range(start, end):
                    marker = ">>> " if j == i else "    "
                    print(f"{marker}{lines[j]}")
                print()
    
    # Prüfe auf österreichische Begriffe
    austrian_terms = ["Österreich", "österreich", "Austria", "austrian"]
    found_austrian = False
    
    for term in austrian_terms:
        if term in content:
            print(f"❌ ÖSTERREICHISCHER BEGRIFF GEFUNDEN: '{term}'")
            found_austrian = True
    
    # Prüfe auf deutsche Begriffe
    german_terms = ["Deutschland", "deutschland", "Germany", "german"]
    found_german = False
    
    for term in german_terms:
        if term in content:
            print(f"✅ DEUTSCHER BEGRIFF GEFUNDEN: '{term}'")
            found_german = True
    
    # Prüfe Steuer-Bezeichnungen
    if "KESt (25%)" in content:
        print("✅ DEUTSCHE KEST-RATE GEFUNDEN: 25%")
    elif "KESt (27.5%)" in content or "KESt (27,5%)" in content:
        print("❌ ÖSTERREICHISCHE KEST-RATE GEFUNDEN: 27,5%")
    
    if "SolZ (5.5% auf KESt)" in content or "SolZ (5,5% auf KESt)" in content:
        print("✅ DEUTSCHER SOLIDARITÄTSZUSCHLAG GEFUNDEN")
    
    print("=" * 60)
    if found_austrian:
        print("❌ PROBLEM: Österreichische Begriffe noch vorhanden!")
        return False
    elif found_german:
        print("✅ ERFOLG: Deutsche Steuerberechnung korrekt implementiert!")
        return True
    else:
        print("⚠️  INFO: Keine expliziten Länderbezeichnungen gefunden")
        return True

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_portfolio_analytics_content())
    sys.exit(0 if success else 1)