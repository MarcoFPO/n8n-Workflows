#!/usr/bin/env python3
"""
ML-Analytics Manual Fix v1.0.0 - 25. August 2025
==================================================

Manual fix for ML-Analytics Service - Clean approach
Replace problematic database code with correct DatabasePool integration
"""

import os

def fix_ml_analytics():
    """Apply manual fix to ML Analytics service"""
    service_file = "/opt/aktienanalyse-ökosystem/services/ml-analytics-service/ml_analytics_daemon_v6_1_0.py"
    
    print("🔧 Applying manual ML-Analytics fix...")
    
    try:
        with open(service_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find and replace the problematic init_database function
        new_lines = []
        in_init_db = False
        skip_until_return = False
        
        for i, line in enumerate(lines):
            if 'async def init_database():' in line:
                in_init_db = True
                new_lines.append(line)
                new_lines.append('    """Initialize PostgreSQL database using DatabasePool"""\\n')
                new_lines.append('    global db_pool\\n')
                new_lines.append('\\n')
                new_lines.append('    try:\\n')
                new_lines.append('        # Initialize DatabasePool singleton\\n')
                new_lines.append('        db_pool = DatabasePool()\\n')
                new_lines.append('        await db_pool.initialize()\\n')
                new_lines.append('\\n')
                new_lines.append('        # Create ML analytics tables using pool\\n')
                new_lines.append('        async with db_pool.acquire() as conn:\\n')
                skip_until_return = True
                continue
                
            elif in_init_db and skip_until_return:
                if 'return True' in line:
                    skip_until_return = False
                    in_init_db = False
                    new_lines.append(line)
                continue
                    
            elif in_init_db and 'except Exception as e:' in line:
                skip_until_return = False
                new_lines.append(line)
                continue
                
            elif '# PostgreSQL Configuration' in line:
                new_lines.append('# Database configuration handled by DatabasePool\\n')
                # Skip POSTGRES_CONFIG definition
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('#') and not lines[j].strip() == '':
                    if lines[j].strip().startswith('POSTGRES_CONFIG') or lines[j].strip().startswith("'") or lines[j].strip().startswith('}'):
                        j += 1
                        continue
                    break
                i = j - 1
                continue
                
            else:
                new_lines.append(line)
        
        # Write fixed content
        with open(service_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
        print("✅ Manual fix applied successfully")
        return True
        
    except Exception as e:
        print(f"❌ Manual fix failed: {e}")
        return False

def main():
    print("🚀 ML-ANALYTICS MANUAL FIX")
    print("=" * 40)
    
    if fix_ml_analytics():
        print("✅ ML-Analytics service fixed!")
        return True
    else:
        print("❌ Fix failed!")
        return False

if __name__ == "__main__":
    main()