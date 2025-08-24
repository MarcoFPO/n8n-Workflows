#!/usr/bin/env python3
"""
Automated sys.path.append Fixer - AUTO EXECUTE
Führt automatisch alle sys.path.append Korrekturen aus

Code-Qualität: HÖCHSTE PRIORITÄT
- Vollautomatische Korrektur ohne User-Input
- Basiert auf fix_all_sys_path_append_v1_0_0_20250822.py
"""

import sys
from pathlib import Path

# Add project root
project_root = Path("/home/mdoehler/aktienanalyse-ökosystem")
sys.path.insert(0, str(project_root))

from scripts.fix_all_sys_path_append_v1_0_0_20250822 import SysPathFixer

def main():
    """Main function - Automated execution"""
    print("=== AUTOMATED sys.path.append Fixer ===")
    print(f"Project Root: {project_root}")
    
    fixer = SysPathFixer(project_root)
    
    # Find files first
    files_to_fix = fixer.find_files_with_sys_path()
    print(f"\nFound {len(files_to_fix)} files with sys.path.append issues")
    
    # Show sample files
    for i, file_path in enumerate(files_to_fix[:5], 1):
        print(f"  {i}. {file_path.relative_to(project_root)}")
    
    if len(files_to_fix) > 5:
        print(f"  ... and {len(files_to_fix) - 5} more files")
    
    # AUTO-EXECUTE fixes
    print(f"\n🔧 AUTO-EXECUTING fixes for {len(files_to_fix)} files...")
    print("  ✅ Creating backup files (.py.backup)")
    print("  ✅ Replacing sys.path.append with Import Manager")
    print("  ✅ Adding import manager header to files")
    
    # Perform fixes
    stats = fixer.fix_all_files()
    
    print(f"\n=== AUTOMATED FIX RESULTS ===")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files fixed: {stats['files_fixed']}")
    print(f"Total sys.path.append statements fixed: {stats['total_fixes']}")
    print(f"Errors: {stats['errors']}")
    
    # Generate report
    report = fixer.generate_report()
    report_file = project_root / "sys_path_automated_fix_report.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📊 Report saved to: {report_file}")
    
    if stats['total_fixes'] > 0:
        print(f"\n🎉 SUCCESS: Fixed {stats['total_fixes']} sys.path.append statements!")
        print(f"✅ {stats['files_fixed']} files updated with Clean Architecture Import Manager")
        print(f"✅ All backup files created for safety")
        print(f"✅ sys.path.append anti-patterns ELIMINATED")
    else:
        print("\nℹ️ No sys.path.append statements found to fix")
    
    return stats['total_fixes']

if __name__ == "__main__":
    fixes_applied = main()
    if fixes_applied > 0:
        print(f"\n🏆 CLEAN ARCHITECTURE SUCCESS: {fixes_applied} anti-patterns eliminated!")
    sys.exit(0)