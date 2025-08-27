#!/usr/bin/env python3
"""
Structured Logging Migration Script
Ersetzt print() Statements durch strukturierte Logging-Calls
"""

import os
import re
from pathlib import Path

def replace_print_statements():
    """Replace print statements with structured logging"""
    
    # Files to process (avoiding venv directories)
    target_files = []
    services_dir = Path("/opt/aktienanalyse-ökosystem/services")
    
    for service_dir in services_dir.glob("*"):
        if service_dir.is_dir() and not service_dir.name.startswith('.') and service_dir.name != 'venv':
            for py_file in service_dir.rglob("*.py"):
                # Skip venv directories
                if 'venv' not in str(py_file) and '__pycache__' not in str(py_file):
                    target_files.append(py_file)
    
    print("Structured Logging Migration")
    print("=" * 50)
    print(f"Processing {len(target_files)} Python files...")
    
    # Common print statement patterns and their replacements
    patterns = [
        # Debug/Info prints
        (r'print\(f?"🚀([^"]*)".*?\)', r'logger.info("🚀\1")'),
        (r'print\(f?"✅([^"]*)".*?\)', r'logger.info("✅\1")'),
        (r'print\(f?"📨([^"]*)".*?\)', r'logger.info("📨\1")'),
        (r'print\(f?"🔧([^"]*)".*?\)', r'logger.info("🔧\1")'),
        (r'print\(f?"📍([^"]*)".*?\)', r'logger.info("📍\1")'),
        (r'print\(f?"🎯([^"]*)".*?\)', r'logger.info("🎯\1")'),
        (r'print\(f?"ℹ️([^"]*)".*?\)', r'logger.info("ℹ️\1")'),
        
        # Error prints
        (r'print\(f?"❌([^"]*)".*?\)', r'logger.error("❌\1")'),
        (r'print\(f?"🚨([^"]*)".*?\)', r'logger.error("🚨\1")'),
        (r'print\(f?"ERROR([^"]*)".*?\)', r'logger.error("ERROR\1")'),
        
        # Warning prints
        (r'print\(f?"⚠️([^"]*)".*?\)', r'logger.warning("⚠️\1")'),
        (r'print\(f?"WARNING([^"]*)".*?\)', r'logger.warning("WARNING\1")'),
        
        # Generic prints
        (r'print\(f?"([^"]+)"\)', r'logger.info("\1")'),
        (r'print\("([^"]+)"\)', r'logger.info("\1")'),
        (r'print\(([^)]+)\)', r'logger.info(f"{\\1}")'),
    ]
    
    # Import pattern to add logging
    logging_import = """import logging

logger = logging.getLogger(__name__)
"""
    
    total_replacements = 0
    processed_files = 0
    
    for file_path in target_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            file_replacements = 0
            
            # Count print statements
            print_count = len(re.findall(r'print\(', content))
            if print_count == 0:
                continue
            
            print(f"\nProcessing: {file_path}")
            print(f"  Found {print_count} print statements")
            
            # Add logging import if not present
            if 'import logging' not in content and print_count > 0:
                # Find a good place to insert logging import
                if 'import os' in content:
                    content = content.replace('import os', f'import os\n{logging_import}')
                elif 'import sys' in content:
                    content = content.replace('import sys', f'import sys\n{logging_import}')
                elif 'from ' in content:
                    # Insert after first import block
                    lines = content.split('\n')
                    insert_index = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith(('import ', 'from ')):
                            insert_index = i + 1
                        elif line.strip() == '' and insert_index > 0:
                            break
                    
                    lines.insert(insert_index, logging_import)
                    content = '\n'.join(lines)
                else:
                    # Add at the beginning after shebang/docstring
                    lines = content.split('\n')
                    insert_index = 0
                    for i, line in enumerate(lines):
                        if line.startswith('#') or line.startswith('"""') or line.startswith("'''"):
                            insert_index = i + 1
                        else:
                            break
                    lines.insert(insert_index, logging_import)
                    content = '\n'.join(lines)
            
            # Apply print replacement patterns
            for pattern, replacement in patterns:
                matches = re.findall(pattern, content)
                if matches:
                    content = re.sub(pattern, replacement, content)
                    file_replacements += len(matches)
            
            # Save file if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"  ✅ Replaced {file_replacements} print statements")
                total_replacements += file_replacements
                processed_files += 1
            else:
                print(f"  ℹ️  No patterns matched")
                
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")
    
    print(f"\n🎯 Structured Logging Migration Summary:")
    print(f"  - Files processed: {processed_files}")
    print(f"  - Total replacements: {total_replacements}")
    print(f"  - Print statements converted to logger calls")
    
    # Create logging configuration template
    logging_config = '''# Structured Logging Configuration
import logging
import sys
from datetime import datetime

def setup_structured_logging(service_name: str, log_level: str = "INFO"):
    """Setup structured logging for service"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=f'{{"service": "{service_name}", "timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}}',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"/tmp/{service_name}-{datetime.now().strftime('%Y%m%d')}.log")
        ]
    )
    
    # Suppress noisy external loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    
    return logging.getLogger(service_name)
'''
    
    with open('/home/mdoehler/aktienanalyse-ökosystem/shared/structured_logging.py', 'w') as f:
        f.write(logging_config)
    
    print(f"\n📝 Created shared/structured_logging.py for centralized logging setup")

if __name__ == "__main__":
    replace_print_statements()