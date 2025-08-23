#!/usr/bin/env python3
"""
Direkter Test des GUI-Testing-Moduls
"""

import sys

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_v1_0_0_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/opt/aktienanalyse-ökosystem') -> Import Manager
import asyncio

from services.diagnostic_service.modules.gui_testing_module import GUITestingModule

async def test_gui_module():
    """GUI-Testing-Modul testen"""
    print("🔧 Initializing GUI Testing Module...")
    
    # GUI-Testing-Modul initialisieren
    gui_module = GUITestingModule("gui_testing", {
        "frontend_url": "http://10.1.1.174:8005",
        "timeout": 5
    })
    
    print("✅ GUI Testing Module initialized")
    print(f"   Target URL: {gui_module.frontend_url}")
    
    # Health-Check
    health = await gui_module.get_health()
    print(f"📊 Module Health: {health}")
    
    # GUI-Quality-Check durchführen (vereinfacht für Demo)
    print("\n🚀 Running GUI Quality Check...")
    
    try:
        result = await gui_module.run_gui_quality_check()
        
        print(f"✅ GUI Quality Check completed!")
        print(f"   Success Rate: {result.success_rate:.1f}%")
        print(f"   Total Tests: {result.total_tests}")
        print(f"   Passed: {result.passed_tests}")
        print(f"   Failed: {result.failed_tests}")
        print(f"   Warnings: {result.warning_tests}")
        print(f"   Duration: {result.total_duration_ms:.0f}ms")
        
        # Detaillierte Test-Ergebnisse
        print("\n📋 Detailed Test Results:")
        for test in result.tests:
            status_emoji = "✅" if test.status == "success" else ("⚠️" if test.status == "warning" else "❌")
            print(f"   {status_emoji} {test.test_name}: {test.status} ({test.duration_ms:.0f}ms)")
            if test.error_message:
                print(f"      Error: {test.error_message}")
        
        return result
        
    except Exception as e:
        print(f"❌ GUI Quality Check failed: {e}")
        return None

if __name__ == "__main__":
    result = asyncio.run(test_gui_module())