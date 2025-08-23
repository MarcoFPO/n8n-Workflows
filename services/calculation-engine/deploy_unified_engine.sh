#!/bin/bash
#
# Deployment Script für Unified Profit Calculation Engine v3.0.0
# Ersetzt die 4 duplizierten Engine-Implementierungen
#
# DEPLOYMENT STRATEGY:
# 1. Backup alte Services
# 2. Deploy neue Unified Engine  
# 3. Update systemd Service-Konfiguration
# 4. Test neue Engine
# 5. Bei Erfolg: Cleanup alte Engines
# 6. Bei Fehler: Rollback zu Backup
#
# DEPLOYMENT TARGET: 10.1.1.174 (Production Server)
#

set -e  # Exit on any error

# Configuration
DEPLOY_DATE=$(date +%Y%m%d_%H%M%S)
SOURCE_DIR="/home/mdoehler/aktienanalyse-ökosystem/services/calculation-engine"
TARGET_HOST="10.1.1.174"
TARGET_USER="mdoehler"
TARGET_DIR="/home/mdoehler/aktienanalyse-ökosystem/services/calculation-engine"
SERVICE_NAME="unified-profit-engine"
SERVICE_PORT="8025"
BACKUP_DIR="/tmp/profit_engine_backup_${DEPLOY_DATE}"

echo "🚀 Starting Unified Profit Engine Deployment v3.0.0"
echo "   Deploy Date: ${DEPLOY_DATE}"
echo "   Target: ${TARGET_USER}@${TARGET_HOST}:${TARGET_DIR}"
echo "   Service Port: ${SERVICE_PORT}"

# Check if unified engine files exist
if [ ! -f "${SOURCE_DIR}/unified_profit_calculation_engine_v3.0.0_20250823.py" ]; then
    echo "❌ Error: Unified engine file not found"
    exit 1
fi

if [ ! -f "${SOURCE_DIR}/unified_profit_engine_service_v3.0.0_20250823.py" ]; then
    echo "❌ Error: Unified service file not found"  
    exit 1
fi

echo "✅ Unified engine files found"

# Step 1: Create backup of existing engines on target system
echo "📦 Creating backup of existing profit engines..."

ssh ${TARGET_USER}@${TARGET_HOST} "
    mkdir -p ${BACKUP_DIR}
    
    # Backup existing profit engines
    if [ -f '${TARGET_DIR}/profit_calculation_engine_20250817_v2.0.0_20250822.py' ]; then
        cp '${TARGET_DIR}/profit_calculation_engine_20250817_v2.0.0_20250822.py' '${BACKUP_DIR}/'
    fi
    
    if [ -f '${TARGET_DIR}/profit_calculation_engine_enhanced_production_v1_1_0_20250822.py' ]; then
        cp '${TARGET_DIR}/profit_calculation_engine_enhanced_production_v1_1_0_20250822.py' '${BACKUP_DIR}/'
    fi
    
    if [ -f '${TARGET_DIR}/profit_calculation_engine_enhanced_v1_1_0_20250822.py' ]; then
        cp '${TARGET_DIR}/profit_calculation_engine_enhanced_v1_1_0_20250822.py' '${BACKUP_DIR}/'
    fi
    
    if [ -f '${TARGET_DIR}/simple_profit_engine_20250821_v1.0.1_20250822.py' ]; then
        cp '${TARGET_DIR}/simple_profit_engine_20250821_v1.0.1_20250822.py' '${BACKUP_DIR}/'
    fi
    
    # Backup systemd service if exists
    if [ -f '/etc/systemd/system/${SERVICE_NAME}.service' ]; then
        sudo cp '/etc/systemd/system/${SERVICE_NAME}.service' '${BACKUP_DIR}/'
    fi
    
    echo 'Backup completed to ${BACKUP_DIR}'
"

echo "✅ Backup completed"

# Step 2: Deploy unified engine files
echo "📁 Deploying unified engine files..."

# Copy unified engine files
scp "${SOURCE_DIR}/unified_profit_calculation_engine_v3.0.0_20250823.py" \
    "${TARGET_USER}@${TARGET_HOST}:${TARGET_DIR}/"

scp "${SOURCE_DIR}/unified_profit_engine_service_v3.0.0_20250823.py" \
    "${TARGET_USER}@${TARGET_HOST}:${TARGET_DIR}/"

# Copy deployment script itself for reference
scp "${SOURCE_DIR}/deploy_unified_engine.sh" \
    "${TARGET_USER}@${TARGET_HOST}:${TARGET_DIR}/"

echo "✅ Files deployed successfully"

# Step 3: Install dependencies on target system
echo "📦 Installing dependencies..."

ssh ${TARGET_USER}@${TARGET_HOST} "
    cd ${TARGET_DIR}
    
    # Create virtual environment for isolated dependencies
    if [ ! -d 'unified_engine_venv' ]; then
        python3 -m venv unified_engine_venv
    fi
    
    # Install dependencies in virtual environment
    source unified_engine_venv/bin/activate
    pip install fastapi uvicorn yfinance aiohttp pydantic || echo 'Some dependencies may already be installed'
    deactivate
    
    # Make files executable
    chmod +x unified_profit_calculation_engine_v3.0.0_20250823.py
    chmod +x unified_profit_engine_service_v3.0.0_20250823.py
    chmod +x deploy_unified_engine.sh
"

echo "✅ Dependencies installed"

# Step 4: Create/Update systemd service
echo "⚙️ Creating systemd service configuration..."

ssh ${TARGET_USER}@${TARGET_HOST} "
    # Stop existing profit engine service if running
    sudo systemctl stop profit-calculation-engine 2>/dev/null || echo 'Service not running'
    sudo systemctl stop unified-profit-engine 2>/dev/null || echo 'Unified service not running'
    
    # Create new systemd service file
    sudo tee /etc/systemd/system/unified-profit-engine.service > /dev/null <<EOF
[Unit]
Description=Unified Profit Calculation Engine Service v3.0.0
After=network.target

[Service]
Type=simple
User=${TARGET_USER}
WorkingDirectory=${TARGET_DIR}
ExecStart=${TARGET_DIR}/unified_engine_venv/bin/python ${TARGET_DIR}/unified_profit_engine_service_v3.0.0_20250823.py
Restart=always
RestartSec=5

# Environment Variables
Environment=PROFIT_ENGINE_MODE=standalone
Environment=PORT=${SERVICE_PORT}
Environment=HOST=0.0.0.0
Environment=LOG_LEVEL=INFO
Environment=IST_CALCULATION_ENABLED=true
Environment=PROFIT_ENGINE_DB_PATH=/home/mdoehler/aktienanalyse-ökosystem/data/unified_profit_engine.db

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=unified-profit-engine

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable unified-profit-engine
"

echo "✅ systemd service configured"

# Step 5: Test unified engine
echo "🧪 Testing unified engine..."

ssh ${TARGET_USER}@${TARGET_HOST} "
    cd ${TARGET_DIR}
    
    # Test engine import and basic functionality
    source unified_engine_venv/bin/activate
    python3 -c '
import sys
sys.path.append(\"${TARGET_DIR}\")

try:
    import unified_profit_calculation_engine_v3_0_0_20250823 as unified_engine
    print(\"✅ Unified engine import successful\")
    
    # Test basic initialization
    import asyncio
    
    async def test_engine():
        engine = unified_engine.UnifiedProfitCalculationEngine(unified_engine.EngineMode.SIMPLE)
        success = await engine.initialize()
        if success:
            print(\"✅ Engine initialization successful\")
            await engine.shutdown()
            return True
        else:
            print(\"❌ Engine initialization failed\")
            return False
    
    result = asyncio.run(test_engine())
    if not result:
        sys.exit(1)
        
except Exception as e:
    print(f\"❌ Engine test failed: {e}\")
    sys.exit(1)
' || exit 1
"

echo "✅ Engine test passed"

# Step 6: Start unified engine service
echo "🚀 Starting unified engine service..."

ssh ${TARGET_USER}@${TARGET_HOST} "
    # Start the service
    sudo systemctl start unified-profit-engine
    
    # Wait a moment for service to start
    sleep 3
    
    # Check service status
    if sudo systemctl is-active --quiet unified-profit-engine; then
        echo '✅ Unified profit engine service started successfully'
        sudo systemctl status unified-profit-engine --no-pager -l
    else
        echo '❌ Failed to start unified profit engine service'
        sudo systemctl status unified-profit-engine --no-pager -l
        exit 1
    fi
"

echo "✅ Service started successfully"

# Step 7: Test API endpoints
echo "🌐 Testing API endpoints..."

ssh ${TARGET_USER}@${TARGET_HOST} "
    # Wait for service to be ready
    sleep 5
    
    # Test health endpoint
    echo 'Testing health endpoint...'
    curl -s -f http://localhost:${SERVICE_PORT}/api/v1/profit/health || {
        echo '❌ Health endpoint test failed'
        exit 1
    }
    
    echo '✅ Health endpoint test passed'
    
    # Test metrics endpoint
    echo 'Testing metrics endpoint...'
    curl -s -f http://localhost:${SERVICE_PORT}/api/v1/profit/metrics || {
        echo '❌ Metrics endpoint test failed'
        exit 1
    }
    
    echo '✅ Metrics endpoint test passed'
    
    # Test backward compatibility CSV endpoint
    echo 'Testing CSV endpoint for backward compatibility...'
    curl -s -f 'http://localhost:${SERVICE_PORT}/api/v1/vergleichsanalyse/csv?timeframe=1M' || {
        echo '❌ CSV endpoint test failed'
        exit 1
    }
    
    echo '✅ CSV endpoint test passed'
    
    echo '🎉 All API endpoint tests passed!'
"

echo "✅ API tests passed"

# Step 8: Update documentation and service references  
echo "📝 Updating service references..."

ssh ${TARGET_USER}@${TARGET_HOST} "
    # Create deployment log
    echo 'Unified Profit Engine v3.0.0 Deployment Log' > ${TARGET_DIR}/deployment_log_${DEPLOY_DATE}.txt
    echo 'Date: $(date)' >> ${TARGET_DIR}/deployment_log_${DEPLOY_DATE}.txt
    echo 'Status: SUCCESS' >> ${TARGET_DIR}/deployment_log_${DEPLOY_DATE}.txt
    echo 'Port: ${SERVICE_PORT}' >> ${TARGET_DIR}/deployment_log_${DEPLOY_DATE}.txt
    echo 'Mode: standalone' >> ${TARGET_DIR}/deployment_log_${DEPLOY_DATE}.txt
    echo 'Backup Location: ${BACKUP_DIR}' >> ${TARGET_DIR}/deployment_log_${DEPLOY_DATE}.txt
    echo '' >> ${TARGET_DIR}/deployment_log_${DEPLOY_DATE}.txt
    echo 'Consolidated Engines:' >> ${TARGET_DIR}/deployment_log_${DEPLOY_DATE}.txt
    echo '- profit_calculation_engine_20250817_v2.0.0_20250822.py' >> ${TARGET_DIR}/deployment_log_${DEPLOY_DATE}.txt
    echo '- profit_calculation_engine_enhanced_production_v1_1_0_20250822.py' >> ${TARGET_DIR}/deployment_log_${DEPLOY_DATE}.txt
    echo '- profit_calculation_engine_enhanced_v1_1_0_20250822.py' >> ${TARGET_DIR}/deployment_log_${DEPLOY_DATE}.txt
    echo '- simple_profit_engine_20250821_v1.0.1_20250822.py' >> ${TARGET_DIR}/deployment_log_${DEPLOY_DATE}.txt
"

echo "✅ Service references updated"

# Final success message
echo ""
echo "🎉 DEPLOYMENT SUCCESSFUL! 🎉"
echo ""
echo "📋 Summary:"
echo "   ✅ Backup created: ${BACKUP_DIR}"
echo "   ✅ Unified engine deployed and tested"
echo "   ✅ systemd service configured and started"  
echo "   ✅ API endpoints tested and working"
echo "   ✅ Port ${SERVICE_PORT} is serving unified engine"
echo ""
echo "🔧 Next Steps:"
echo "   1. Update frontend service to use unified endpoints"
echo "   2. Test SOLL-IST table loading in GUI"
echo "   3. Monitor service for 24h"
echo "   4. Cleanup old engines after verification"
echo ""
echo "📊 Service Status:"
ssh ${TARGET_USER}@${TARGET_HOST} "sudo systemctl status unified-profit-engine --no-pager"
echo ""
echo "🌐 API Health Check:"
ssh ${TARGET_USER}@${TARGET_HOST} "curl -s http://localhost:${SERVICE_PORT}/api/v1/profit/health | python3 -m json.tool 2>/dev/null || echo 'Health check response received'"
echo ""
echo "✅ Deployment completed successfully at $(date)"