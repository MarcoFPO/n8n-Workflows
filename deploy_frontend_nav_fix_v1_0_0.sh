#!/bin/bash
# FRONTEND-NAV-001 Bug Fix Deployment Script
# Author: Claude Code
# Date: 2025-08-27
# Version: 1.0.0

echo "🚀 Deploying FRONTEND-NAV-001 Fix to Production"
echo "================================================"

# Configuration
PRODUCTION_DIR="/opt/aktienanalyse-ökosystem"
REPO_DIR="/home/mdoehler/aktienanalyse-ökosystem"
SERVICE_NAME="aktienanalyse-frontend"
BACKUP_SUFFIX="backup_$(date +%Y%m%d_%H%M%S)"

# Safety check
if [ ! -f "$REPO_DIR/services/frontend-service/main.py" ]; then
    echo "❌ ERROR: Source file not found!"
    exit 1
fi

echo "📋 Pre-deployment checks..."
echo "- Source: $REPO_DIR/services/frontend-service/main.py"
echo "- Target: $PRODUCTION_DIR/services/frontend-service/"
echo "- Service: $SERVICE_NAME"

# Step 1: Backup current production file
echo "💾 Creating backup of production file..."
sudo cp "$PRODUCTION_DIR/services/frontend-service/run_frontend_new.py" \
     "$PRODUCTION_DIR/services/frontend-service/run_frontend_new.py.$BACKUP_SUFFIX"
echo "✅ Backup created: run_frontend_new.py.$BACKUP_SUFFIX"

# Step 2: Copy fixed file to production
echo "📦 Deploying fixed frontend service..."
sudo cp "$REPO_DIR/services/frontend-service/main.py" \
     "$PRODUCTION_DIR/services/frontend-service/run_frontend_new.py"
echo "✅ File copied to production"

# Step 3: Fix ownership and permissions
echo "🔧 Fixing permissions..."
sudo chown aktienanalyse:aktienanalyse "$PRODUCTION_DIR/services/frontend-service/run_frontend_new.py"
sudo chmod +x "$PRODUCTION_DIR/services/frontend-service/run_frontend_new.py"
echo "✅ Permissions fixed"

# Step 4: Clear Python cache
echo "🗑️ Clearing Python cache..."
sudo rm -rf "$PRODUCTION_DIR/services/frontend-service/__pycache__"
echo "✅ Cache cleared"

# Step 5: Restart service
echo "🔄 Restarting frontend service..."
sudo systemctl restart "$SERVICE_NAME"
sleep 5
echo "✅ Service restarted"

# Step 6: Verify deployment
echo "🧪 Testing deployment..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✅ Service is active"
else
    echo "❌ Service failed to start!"
    echo "📋 Service status:"
    systemctl status "$SERVICE_NAME" --no-pager -l
    exit 1
fi

# Step 7: Test routes
echo "🧪 Testing navigation routes..."

# Test dashboard route
DASHBOARD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://10.1.1.174:8080/dashboard)
if [ "$DASHBOARD_STATUS" = "200" ]; then
    echo "✅ /dashboard → 200 OK"
else
    echo "❌ /dashboard → $DASHBOARD_STATUS"
fi

# Test ki-vorhersage route
KI_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://10.1.1.174:8080/ki-vorhersage)
if [ "$KI_STATUS" = "301" ]; then
    echo "✅ /ki-vorhersage → 301 Redirect"
else
    echo "❌ /ki-vorhersage → $KI_STATUS"
fi

# Test soll-ist-vergleich route
SOLL_IST_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://10.1.1.174:8080/soll-ist-vergleich)
if [ "$SOLL_IST_STATUS" = "301" ]; then
    echo "✅ /soll-ist-vergleich → 301 Redirect"
else
    echo "❌ /soll-ist-vergleich → $SOLL_IST_STATUS"
fi

# Test depot route
DEPOT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://10.1.1.174:8080/depot)
if [ "$DEPOT_STATUS" = "200" ]; then
    echo "✅ /depot → 200 OK"
else
    echo "❌ /depot → $DEPOT_STATUS"
fi

echo ""
echo "🎉 FRONTEND-NAV-001 Fix Deployment Completed"
echo "============================================"
echo "📊 Route Test Summary:"
echo "- Dashboard: $DASHBOARD_STATUS"
echo "- KI-Vorhersage: $KI_STATUS"  
echo "- SOLL-IST Vergleich: $SOLL_IST_STATUS"
echo "- Depot: $DEPOT_STATUS"
echo ""
echo "🔗 Test the navigation at: http://10.1.1.174:8080/"
echo "📝 Backup available at: run_frontend_new.py.$BACKUP_SUFFIX"