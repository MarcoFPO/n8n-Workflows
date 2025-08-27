#!/usr/bin/env python3
"""
Migration Script: print() statements to structured logging
Automatisches Tool zur Code-Modernisierung
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple
import argparse

class PrintToLoggingMigrator:
    """Migriert print() Statements zu strukturiertem Logging"""
    
    # Patterns für verschiedene print-Typen
    PATTERNS = {
        'error': re.compile(r'print\s*\(\s*f?["\'].*(?:error|fail|exception|critical).*["\']', re.IGNORECASE),
        'warning': re.compile(r'print\s*\(\s*f?["\'].*(?:warn|caution|attention).*["\']', re.IGNORECASE),
        'debug': re.compile(r'print\s*\(\s*f?["\'].*(?:debug|trace|verbose).*["\']', re.IGNORECASE),
        'info': re.compile(r'print\s*\(')  # Default für alle anderen
    }
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.changes = []
        
    def migrate_file(self, filepath: Path) -> bool:
        """Migriert eine einzelne Python-Datei"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            
            # Check if logging is already imported
            has_logging = 'import logging' in content or 'from logging import' in content
            
            # Add logging import if needed
            if not has_logging and 'print(' in content:
                # Find the right place to add import
                import_lines = []
                lines = content.split('\n')
                insert_pos = 0
                
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        insert_pos = i + 1
                    elif line and not line.startswith('#') and not line.startswith('"""'):
                        break
                
                lines.insert(insert_pos, 'import logging')
                lines.insert(insert_pos + 1, '')
                lines.insert(insert_pos + 2, 'logger = logging.getLogger(__name__)')
                lines.insert(insert_pos + 3, '')
                content = '\n'.join(lines)
            
            # Replace print statements
            for log_level, pattern in self.PATTERNS.items():
                if log_level == 'error':
                    content = re.sub(
                        r'print\s*\(\s*(f?["\'].*error.*["\'].*?)\)',
                        r'logger.error(\1)',
                        content,
                        flags=re.IGNORECASE
                    )
                elif log_level == 'warning':
                    content = re.sub(
                        r'print\s*\(\s*(f?["\'].*warn.*["\'].*?)\)',
                        r'logger.warning(\1)',
                        content,
                        flags=re.IGNORECASE
                    )
                elif log_level == 'debug':
                    content = re.sub(
                        r'print\s*\(\s*(f?["\'].*debug.*["\'].*?)\)',
                        r'logger.debug(\1)',
                        content,
                        flags=re.IGNORECASE
                    )
            
            # Replace remaining prints with info
            content = re.sub(
                r'print\s*\((.*?)\)',
                r'logger.info(\1)',
                content
            )
            
            # Check if file was modified
            if content != original_content:
                if not self.dry_run:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                # Count changes
                original_prints = original_content.count('print(')
                remaining_prints = content.count('print(')
                migrated = original_prints - remaining_prints
                
                self.changes.append((filepath, migrated))
                return True
                
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            
        return False
    
    def migrate_directory(self, directory: Path, exclude_dirs: List[str] = None):
        """Migriert alle Python-Dateien in einem Verzeichnis"""
        if exclude_dirs is None:
            exclude_dirs = ['venv', '__pycache__', '.git', 'node_modules', 'backups']
        
        python_files = []
        for root, dirs, files in os.walk(directory):
            # Remove excluded directories from search
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        print(f"Found {len(python_files)} Python files to process")
        
        for filepath in python_files:
            self.migrate_file(filepath)
        
        return self.changes
    
    def print_summary(self):
        """Zeigt eine Zusammenfassung der Änderungen"""
        if not self.changes:
            print("No print statements found to migrate")
            return
        
        total_changes = sum(count for _, count in self.changes)
        
        print(f"\n{'DRY RUN' if self.dry_run else 'MIGRATION'} SUMMARY")
        print("=" * 50)
        print(f"Files modified: {len(self.changes)}")
        print(f"Total print statements migrated: {total_changes}")
        print("\nTop 10 files with most changes:")
        
        for filepath, count in sorted(self.changes, key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {count:3d} changes: {filepath}")


def main():
    parser = argparse.ArgumentParser(description='Migrate print statements to logging')
    parser.add_argument('path', help='Path to directory or file to migrate')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry run)')
    parser.add_argument('--exclude', nargs='+', help='Additional directories to exclude')
    
    args = parser.parse_args()
    
    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path {path} does not exist")
        sys.exit(1)
    
    migrator = PrintToLoggingMigrator(dry_run=not args.apply)
    
    if path.is_file():
        if migrator.migrate_file(path):
            print(f"Migrated {path}")
    else:
        exclude_dirs = ['venv', '__pycache__', '.git', 'node_modules', 'backups']
        if args.exclude:
            exclude_dirs.extend(args.exclude)
        
        migrator.migrate_directory(path, exclude_dirs)
    
    migrator.print_summary()
    
    if migrator.dry_run and migrator.changes:
        print(f"\nTo apply changes, run with --apply flag")


if __name__ == "__main__":
    main()