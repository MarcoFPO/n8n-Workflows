#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Test Deutsche Steuerberechnung
Testet die Umstellung von österreichischer auf deutsche Steuerberechnung
"""

import sys
from pathlib import Path

# Pfad zum Frontend-Verzeichnis hinzufügen
sys.path.append(str(Path(__file__).parent / "frontend-domain"))

from portfolio_analytics_provider import PortfolioAnalyticsProvider

def test_german_tax_calculation():
    """Teste die deutsche Steuerberechnung ohne Kirchensteuer"""
    print("🧪 TESTE DEUTSCHE STEUERBERECHNUNG")
    print("=" * 50)
    
    # Mock Provider erstellen
    provider = PortfolioAnalyticsProvider(None, None)
    
    # Test-Szenarien
    test_cases = [
        {"name": "Kleiner Gewinn", "gross_gain": 1000.0},
        {"name": "Mittlerer Gewinn", "gross_gain": 5000.0}, 
        {"name": "Großer Gewinn", "gross_gain": 10000.0},
        {"name": "Sehr großer Gewinn", "gross_gain": 50000.0},
        {"name": "Verlust", "gross_gain": -2000.0},
        {"name": "Null", "gross_gain": 0.0}
    ]
    
    print("🇩🇪 DEUTSCHE STEUERBERECHNUNG (ohne Kirchensteuer):")
    print("Steuersätze: 25% KESt + 5,5% SolZ = 26,375% Gesamtsteuersatz")
    print("-" * 50)
    
    for test_case in test_cases:
        gross_gain = test_case["gross_gain"]
        tax_result = provider._calculate_german_taxes(gross_gain)
        
        print(f"\n📊 {test_case['name']}: {gross_gain:,.2f}€")
        if gross_gain > 0:
            print(f"   KESt (25%):     {tax_result['kest']:8,.2f}€")
            print(f"   SolZ (5,5%):    {tax_result['solz']:8,.2f}€")
            print(f"   Gesamtsteuer:   {tax_result['total_tax']:8,.2f}€")
            print(f"   Netto-Gewinn:   {tax_result['net_gain']:8,.2f}€")
            print(f"   Effektivsatz:   {tax_result['effective_rate_percent']:8.3f}%")
        else:
            print(f"   Keine Steuern:  {tax_result['total_tax']:8,.2f}€")
            print(f"   Netto-Ergebnis: {tax_result['net_gain']:8,.2f}€")
    
    # Vergleich Österreich vs. Deutschland
    print("\n" + "=" * 50)
    print("🆚 VERGLEICH: ÖSTERREICH vs. DEUTSCHLAND")
    print("=" * 50)
    
    example_gain = 10000.0
    german_result = provider._calculate_german_taxes(example_gain)
    
    # Österreichische Berechnung (alt)
    austrian_kest = example_gain * 0.275  # 27,5%
    austrian_total = austrian_kest
    austrian_net = example_gain - austrian_total
    
    print(f"Beispiel-Gewinn: {example_gain:,.2f}€")
    print(f"")
    print(f"🇦🇹 ÖSTERREICH (alt):")
    print(f"   KESt (27,5%):   {austrian_kest:8,.2f}€")
    print(f"   Gesamtsteuer:   {austrian_total:8,.2f}€") 
    print(f"   Netto-Gewinn:   {austrian_net:8,.2f}€")
    print(f"   Effektivsatz:   {(austrian_total/example_gain)*100:8.1f}%")
    print(f"")
    print(f"🇩🇪 DEUTSCHLAND (neu):")
    print(f"   KESt (25%):     {german_result['kest']:8,.2f}€")
    print(f"   SolZ (5,5%):    {german_result['solz']:8,.2f}€")
    print(f"   Gesamtsteuer:   {german_result['total_tax']:8,.2f}€")
    print(f"   Netto-Gewinn:   {german_result['net_gain']:8,.2f}€")
    print(f"   Effektivsatz:   {german_result['effective_rate_percent']:8.3f}%")
    print(f"")
    print(f"💰 VORTEIL DEUTSCHLAND:")
    savings = austrian_total - german_result['total_tax']
    savings_percent = (savings / austrian_total) * 100
    print(f"   Steuerersparnis: {savings:8,.2f}€")
    print(f"   Prozentuale Ersparnis: {savings_percent:5.2f}%")
    
    # Validierung
    print("\n" + "=" * 50)
    print("✅ VALIDIERUNG")
    print("=" * 50)
    
    expected_rate = 0.26375  # 26,375%
    actual_rate = german_result['effective_rate']
    
    if abs(actual_rate - expected_rate) < 0.0001:
        print(f"✅ Effektivsatz korrekt: {actual_rate:.5f} = {expected_rate:.5f}")
        print("✅ Deutsche Steuerberechnung funktioniert korrekt!")
        return True
    else:
        print(f"❌ Effektivsatz falsch: {actual_rate:.5f} ≠ {expected_rate:.5f}")
        return False

if __name__ == "__main__":
    success = test_german_tax_calculation()
    sys.exit(0 if success else 1)