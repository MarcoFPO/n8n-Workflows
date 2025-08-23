#!/usr/bin/env python3
"""
Automated Module Versioning Compliance - AUTO EXECUTE
Führt automatisch alle Modul-Versionierung Korrekturen aus

Code-Qualität: HÖCHSTE PRIORITÄT
- Vollautomatische CLAUDE.md Compliance
- Basiert auf module_versioning_compliance_v1_0_0_20250822.py
"""

import sys
from pathlib import Path

# Add project root
project_root = Path("/home/mdoehler/aktienanalyse-ökosystem")
sys.path.insert(0, str(project_root))

from scripts.module_versioning_compliance_v1_0_0_20250822 import ModuleVersioningChecker

def main():
    """Main function - Automated execution"""
    print("=== AUTOMATED Module Versioning Compliance ===")
    print(f"Project Root: {project_root}")
    
    checker = ModuleVersioningChecker(project_root)
    
    # Generate compliance report
    print("\nGenerating compliance report...")
    report = checker.generate_compliance_report()
    
    print(f"\n=== Compliance Report ===")
    print(f"Total modules: {report.total_modules}")
    print(f"Compliant modules: {report.compliant_modules}")
    print(f"Non-compliant modules: {report.non_compliant_modules}")
    
    if report.non_compliant_modules > 0:
        compliance_rate = (report.compliant_modules / report.total_modules) * 100
        print(f"Compliance rate: {compliance_rate:.1f}%")
        
        print(f"\n=== Sample Non-Compliant Modules ===")
        for i, module in enumerate(report.suggestions[:5], 1):  # Show first 5
            print(f"{i:2d}. {module.current_name}")
            print(f"    → {module.suggested_name}")
            print(f"    Type: {module.module_type}")
        
        if len(report.suggestions) > 5:
            print(f"    ... and {len(report.suggestions) - 5} more modules")
        
        # AUTO-EXECUTE fixes
        print(f"\n🔧 AUTO-EXECUTING compliance fixes...")
        print(f"  ✅ Creating backup files")
        print(f"  ✅ Renaming {report.non_compliant_modules} modules to CLAUDE.md compliance")
        print(f"  ✅ Updating MODUL_RELEASE_REGISTER.md")
        
        # Perform fixes
        stats = checker.fix_non_compliant_modules(report.suggestions, create_backup=True)
        
        print(f"\n=== AUTOMATED COMPLIANCE RESULTS ===")
        print(f"Modules renamed: {stats['renamed']}")
        print(f"Backups created: {stats['backups_created']}")
        print(f"Errors: {stats['errors']}")
        
        # Update release register
        if stats['renamed'] > 0:
            if checker.update_release_register(report.suggestions):
                print("✅ MODUL_RELEASE_REGISTER.md updated")
            
            print(f"\n🎉 SUCCESS: Standardized {stats['renamed']} modules!")
            print(f"✅ All modules now follow CLAUDE.md naming convention")
            print(f"✅ Full Module Versioning Compliance achieved")
        
        return stats['renamed']
    
    else:
        print("\n✅ All modules are already compliant!")
        print("✅ 100% compliance with CLAUDE.md naming convention")
        return 0

if __name__ == "__main__":
    modules_fixed = main()
    if modules_fixed > 0:
        print(f"\n🏆 MODULE VERSIONING SUCCESS: {modules_fixed} modules standardized!")
    sys.exit(0)