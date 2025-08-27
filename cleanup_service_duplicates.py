#!/usr/bin/env python3
"""
Service Duplicate Cleanup Script
Entfernt veraltete Service-Versionen und behält nur die aktuelle main.py
"""

import os
import shutil
from pathlib import Path
import argparse

class ServiceDuplicateCleanup:
    """Bereinigt Service-Duplikate"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.removed_files = []
    
    def cleanup_service_directory(self, service_path: Path):
        """Bereinigt ein Service-Verzeichnis von alten Versionen"""
        main_files = list(service_path.glob("main*.py"))
        
        # Finde die aktuelle main.py
        current_main = None
        versioned_mains = []
        
        for main_file in main_files:
            if main_file.name == "main.py":
                current_main = main_file
            elif "_v" in main_file.name or "_20" in main_file.name:
                versioned_mains.append(main_file)
        
        if current_main and versioned_mains:
            print(f"\n=== {service_path.name} ===")
            print(f"Current: {current_main.name}")
            print(f"Old versions: {[f.name for f in versioned_mains]}")
            
            if not self.dry_run:
                for old_file in versioned_mains:
                    old_file.unlink()
                    print(f"Removed: {old_file}")
            else:
                print(f"Would remove {len(versioned_mains)} old main files")
            
            self.removed_files.extend(versioned_mains)
    
    def cleanup_versioned_files(self, service_path: Path):
        """Entfernt andere versionierte Dateien (requirements, README, etc.)"""
        versioned_files = []
        
        # Finde versionierte Dateien
        for pattern in ["*_v*.txt", "*_v*.md", "*_v*.py", "*_20*.py", "*_20*.txt"]:
            versioned_files.extend(service_path.glob(pattern))
        
        # Filtere bereits behandelte main.py Dateien aus
        versioned_files = [f for f in versioned_files if not f.name.startswith("main")]
        
        if versioned_files:
            print(f"Additional versioned files in {service_path.name}:")
            for vf in versioned_files:
                print(f"  - {vf.name}")
                if not self.dry_run:
                    vf.unlink()
                    print(f"    Removed: {vf}")
            
            self.removed_files.extend(versioned_files)
    
    def cleanup_services_directory(self, services_path: Path):
        """Bereinigt das gesamte services/ Verzeichnis"""
        service_dirs = [d for d in services_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
        
        print(f"Processing {len(service_dirs)} service directories...")
        
        for service_dir in service_dirs:
            self.cleanup_service_directory(service_dir)
            self.cleanup_versioned_files(service_dir)
    
    def print_summary(self):
        """Zeigt Zusammenfassung der bereinigten Dateien"""
        if not self.removed_files:
            print("\nNo duplicate files found to remove")
            return
        
        print(f"\n{'DRY RUN' if self.dry_run else 'CLEANUP'} SUMMARY")
        print("=" * 50)
        print(f"Total files {'would be ' if self.dry_run else ''}removed: {len(self.removed_files)}")
        
        # Gruppiere nach Service
        services = {}
        for file in self.removed_files:
            service_name = file.parent.name
            if service_name not in services:
                services[service_name] = []
            services[service_name].append(file.name)
        
        print("\nFiles by service:")
        for service, files in services.items():
            print(f"  {service}: {len(files)} files")
            for file in files:
                print(f"    - {file}")


def main():
    parser = argparse.ArgumentParser(description='Cleanup service duplicate files')
    parser.add_argument('services_path', help='Path to services directory')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry run)')
    
    args = parser.parse_args()
    
    services_path = Path(args.services_path)
    if not services_path.exists() or not services_path.is_dir():
        print(f"Error: {services_path} is not a valid directory")
        return 1
    
    cleanup = ServiceDuplicateCleanup(dry_run=not args.apply)
    cleanup.cleanup_services_directory(services_path)
    cleanup.print_summary()
    
    if cleanup.dry_run and cleanup.removed_files:
        print(f"\nTo apply changes, run with --apply flag")
    
    return 0


if __name__ == "__main__":
    exit(main())