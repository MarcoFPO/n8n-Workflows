#!/usr/bin/env python3
"""
Fix Hardcoded URLs Script v1.0.0
Aktienanalyse Ökosystem - Production URL Configuration

REPARIERT:
- Redis localhost URLs → Environment Variables
- Service Host/Port Konfigurationen
- Database Connection URLs
- Event-Bus Connection Strings

PRODUCTION CONFIGURATION:
- Redis: 10.1.1.174:6379 (Production Server)
- PostgreSQL: 10.1.1.174:5432
- Services: 10.1.1.174:80xx Ports
- Environment Variable Fallbacks

Autor: Claude Code Quality Specialist
Datum: 27. August 2025
Version: 1.0.0 - URL Hardening
"""

import os
import re
from pathlib import Path

class URLHardcodingFixer:
    """
    Repariert hardcodierte URLs und ersetzt sie durch Environment Variables
    
    CLEAN ARCHITECTURE PRINCIPLES:
    - Configuration Management durch External Dependencies
    - Environment-based Deployment Strategy
    - Production-ready URL Configuration
    """
    
    def __init__(self):
        self.project_root = Path("/home/mdoehler/aktienanalyse-ökosystem")
        self.fixes_applied = []
    
    def fix_redis_urls(self):
        """Repariert Redis localhost URLs"""
        
        # Event Bus Service Redis Fix
        event_bus_main = self.project_root / "services/event-bus-service/main.py"
        if event_bus_main.exists():
            content = event_bus_main.read_text()
            old_redis = '"redis://localhost:6379/1"'
            new_redis = 'os.getenv("REDIS_URL", "redis://10.1.1.174:6379/1")'
            
            if old_redis in content:
                # Add os import if not present
                if "import os" not in content:
                    content = content.replace("import asyncio", "import asyncio\nimport os")
                
                content = content.replace(old_redis, new_redis)
                event_bus_main.write_text(content)
                self.fixes_applied.append(f"Fixed Redis URL in {event_bus_main}")
    
    def fix_service_hosts(self):
        """Repariert Service Host/Port Konfigurationen"""
        
        # Frontend Service Container Fix
        frontend_container = self.project_root / "services/frontend-service/infrastructure/container.py"
        if frontend_container.exists():
            content = frontend_container.read_text()
            
            # Replace hardcoded localhost hosts
            localhost_fixes = [
                ("'host': 'localhost',", "'host': os.getenv('FRONTEND_HOST', '10.1.1.174'),"),
                ('"host": "localhost",', '"host": os.getenv("FRONTEND_HOST", "10.1.1.174"),'),
            ]
            
            for old, new in localhost_fixes:
                if old in content:
                    # Add os import if not present
                    if "import os" not in content:
                        content = "import os\n" + content
                    
                    content = content.replace(old, new)
                    self.fixes_applied.append(f"Fixed host config: {old} -> {new}")
            
            frontend_container.write_text(content)
            
    def fix_ml_service_config(self):
        """Repariert ML Analytics Service Konfiguration"""
        
        ml_config = self.project_root / "services/ml-analytics-service/infrastructure/configuration/ml_service_config.py"
        if ml_config.exists():
            content = ml_config.read_text()
            
            # Replace localhost URLs in ML service config
            localhost_patterns = [
                (r'localhost:(\d+)', r'os.getenv("ML_SERVICE_HOST", "10.1.1.174"):\1'),
                (r'"localhost"', 'os.getenv("ML_SERVICE_HOST", "10.1.1.174")'),
                (r"'localhost'", "os.getenv('ML_SERVICE_HOST', '10.1.1.174')"),
            ]
            
            modified = False
            for pattern, replacement in localhost_patterns:
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    modified = True
                    self.fixes_applied.append(f"Fixed ML config pattern: {pattern}")
            
            if modified:
                # Add os import if not present
                if "import os" not in content:
                    content = "import os\n" + content
                ml_config.write_text(content)
    
    def create_env_template(self):
        """Erstelle .env Template für Production"""
        
        env_template = self.project_root / ".env.production.template"
        env_content = """# Aktienanalyse Ökosystem - Production Environment Variables
# Copy to .env.production and adjust values for your production setup

# === PRODUCTION SERVER CONFIGURATION ===
PRODUCTION_SERVER_HOST=10.1.1.174
PRODUCTION_SERVER_PORT=80

# === DATABASE CONFIGURATION ===
DATABASE_HOST=10.1.1.174
DATABASE_PORT=5432
DATABASE_NAME=aktienanalyse_production
DATABASE_USER=aktienanalyse_user
DATABASE_PASSWORD=your_secure_password

# === REDIS CONFIGURATION ===
REDIS_URL=redis://10.1.1.174:6379/1
REDIS_HOST=10.1.1.174
REDIS_PORT=6379
REDIS_DB=1

# === SERVICE HOSTS ===
FRONTEND_HOST=10.1.1.174
FRONTEND_PORT=8081

ML_SERVICE_HOST=10.1.1.174
ML_SERVICE_PORT=8086

EVENT_BUS_HOST=10.1.1.174
EVENT_BUS_PORT=8014

PREDICTION_SERVICE_HOST=10.1.1.174
PREDICTION_SERVICE_PORT=8087

# === API KEYS (Set your actual keys) ===
# ALPHA_VANTAGE_API_KEY=your_key_here
# FMP_API_KEY=your_key_here
# YAHOO_FINANCE_API_KEY=your_key_here

# === LOGGING ===
LOG_LEVEL=INFO
LOG_FILE=/var/log/aktienanalyse/system.log

# === SECURITY (for future use) ===
# JWT_SECRET_KEY=your_jwt_secret
# CORS_ORIGINS=https://yourdomain.com
"""
        env_template.write_text(env_content)
        self.fixes_applied.append(f"Created environment template: {env_template}")
    
    def apply_all_fixes(self):
        """Wende alle URL-Fixes an"""
        print("=== HARDCODED URL FIXES STARTING ===")
        
        self.fix_redis_urls()
        self.fix_service_hosts() 
        self.fix_ml_service_config()
        self.create_env_template()
        
        print(f"\n=== FIXES APPLIED ===")
        for fix in self.fixes_applied:
            print(f"✓ {fix}")
            
        print(f"\nTotal fixes applied: {len(self.fixes_applied)}")
        print("\n=== NEXT STEPS ===")
        print("1. Copy .env.production.template to .env.production")
        print("2. Update .env.production with your actual values")
        print("3. Load environment variables in service startup")
        print("4. Test services with new configuration")

def main():
    fixer = URLHardcodingFixer()
    fixer.apply_all_fixes()

if __name__ == "__main__":
    main()