#!/usr/bin/env python3
"""
Automated sys.path.append Fixer v1.0.0
Ersetzt alle 72+ sys.path.append Statements mit Import Manager

Code-Qualität: HÖCHSTE PRIORITÄT
- Automatisierte Code-Qualitäts-Verbesserung
- Batch-Processing für alle betroffenen Dateien
- Clean Architecture Migration
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FixResult:
    """Result of fixing a file"""
    file_path: str
    fixes_applied: int
    original_lines: List[str]
    fixed_lines: List[str]
    backup_created: bool

class SysPathFixer:
    """
    Automated sys.path.append Fixer - Single Responsibility
    Replaces sys.path.append anti-patterns with Import Manager
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: List[FixResult] = []
        
        # Patterns to match sys.path.append statements
        self.sys_path_patterns = [
            r"sys\.path\.append\(['\"][^'\"]*['\"\)]",
            r"sys\.path\.insert\(\d+,\s*['\"][^'\"]*['\"\)]",
        ]
        
        # Standard replacement header
        self.import_manager_header = '''# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_v1_0_0_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements
'''
        
    def find_files_with_sys_path(self) -> List[Path]:
        """Find all Python files with sys.path.append statements"""
        files_with_issues = []
        
        for python_file in self.project_root.rglob("*.py"):
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if any(re.search(pattern, content) for pattern in self.sys_path_patterns):
                    files_with_issues.append(python_file)
                    
            except Exception as e:
                logger.warning(f"Could not read {python_file}: {e}")
                
        return files_with_issues
    
    def fix_file(self, file_path: Path) -> FixResult:
        """Fix sys.path.append statements in a single file"""
        try:
            # Read original content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()
            
            # Create backup
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.writelines(original_lines)
            
            # Process lines
            fixed_lines = []
            fixes_applied = 0
            import_manager_added = False
            
            for line in original_lines:
                # Check if line contains sys.path.append
                if any(re.search(pattern, line) for pattern in self.sys_path_patterns):
                    fixes_applied += 1
                    
                    # Add import manager header if not already added
                    if not import_manager_added:
                        # Find good position for import (after docstring/shebang)
                        if not fixed_lines or line.strip().startswith('#') or '"""' in line:
                            fixed_lines.append(line)
                            continue
                        else:
                            fixed_lines.append('\n')
                            fixed_lines.append(self.import_manager_header)
                            fixed_lines.append('\n')
                            import_manager_added = True
                    
                    # Replace the sys.path.append line with comment
                    indent = len(line) - len(line.lstrip())
                    comment_line = ' ' * indent + f"# FIXED: {line.strip()} -> Import Manager\n"
                    fixed_lines.append(comment_line)
                    
                else:
                    fixed_lines.append(line)
            
            # Write fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(fixed_lines)
            
            result = FixResult(
                file_path=str(file_path),
                fixes_applied=fixes_applied,
                original_lines=original_lines,
                fixed_lines=fixed_lines,
                backup_created=True
            )
            
            self.results.append(result)
            logger.info(f"Fixed {file_path}: {fixes_applied} sys.path.append statements")
            return result
            
        except Exception as e:
            logger.error(f"Error fixing {file_path}: {e}")
            return FixResult(
                file_path=str(file_path),
                fixes_applied=0,
                original_lines=[],
                fixed_lines=[],
                backup_created=False
            )
    
    def fix_all_files(self) -> Dict[str, int]:
        """Fix all files with sys.path.append issues"""
        files_to_fix = self.find_files_with_sys_path()
        
        logger.info(f"Found {len(files_to_fix)} files with sys.path.append issues")
        
        stats = {
            "files_processed": 0,
            "files_fixed": 0,
            "total_fixes": 0,
            "errors": 0
        }
        
        for file_path in files_to_fix:
            try:
                result = self.fix_file(file_path)
                stats["files_processed"] += 1
                
                if result.fixes_applied > 0:
                    stats["files_fixed"] += 1
                    stats["total_fixes"] += result.fixes_applied
                    
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats["errors"] += 1
        
        return stats
    
    def generate_report(self) -> str:
        """Generate fix report"""
        report = ["# Automated sys.path.append Fix Report\n"]
        report.append(f"**Generated**: {Path(__file__).name}\n")
        report.append(f"**Project**: {self.project_root}\n\n")
        
        if not self.results:
            report.append("No files processed.\n")
            return ''.join(report)
        
        # Summary
        total_fixes = sum(r.fixes_applied for r in self.results)
        files_fixed = sum(1 for r in self.results if r.fixes_applied > 0)
        
        report.append("## Summary\n")
        report.append(f"- **Files processed**: {len(self.results)}\n")
        report.append(f"- **Files with fixes**: {files_fixed}\n")
        report.append(f"- **Total sys.path.append statements fixed**: {total_fixes}\n\n")
        
        # Detailed results
        report.append("## Detailed Results\n")
        for result in self.results:
            if result.fixes_applied > 0:
                report.append(f"### {result.file_path}\n")
                report.append(f"- **Fixes applied**: {result.fixes_applied}\n")
                report.append(f"- **Backup created**: {'✅' if result.backup_created else '❌'}\n\n")
        
        return ''.join(report)

def main():
    """Main function"""
    project_root = Path("/home/mdoehler/aktienanalyse-ökosystem")
    
    print("=== Automated sys.path.append Fixer ===")
    print(f"Project Root: {project_root}")
    
    fixer = SysPathFixer(project_root)
    
    # Find files first
    files_to_fix = fixer.find_files_with_sys_path()
    print(f"\nFound {len(files_to_fix)} files with sys.path.append issues:")
    
    for file_path in files_to_fix[:10]:  # Show first 10
        print(f"  - {file_path}")
    
    if len(files_to_fix) > 10:
        print(f"  ... and {len(files_to_fix) - 10} more files")
    
    # Ask for confirmation
    print(f"\nThis will:")
    print(f"1. Create backup files (.py.backup)")
    print(f"2. Replace sys.path.append with Import Manager")
    print(f"3. Add import manager header to files")
    
    response = input("\nProceed with fixes? (y/N): ")
    
    if response.lower() != 'y':
        print("Aborted.")
        return
    
    # Perform fixes
    print("\nFixing files...")
    stats = fixer.fix_all_files()
    
    print(f"\n=== Fix Results ===")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files fixed: {stats['files_fixed']}")
    print(f"Total fixes: {stats['total_fixes']}")
    print(f"Errors: {stats['errors']}")
    
    # Generate report
    report = fixer.generate_report()
    report_file = project_root / "sys_path_fix_report.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_file}")
    
    if stats['total_fixes'] > 0:
        print(f"\n✅ Successfully fixed {stats['total_fixes']} sys.path.append statements!")
        print(f"✅ {stats['files_fixed']} files updated with Import Manager")
        print(f"✅ Backup files created for safety")
    else:
        print("\nℹ️ No sys.path.append statements found to fix")

if __name__ == "__main__":
    main()