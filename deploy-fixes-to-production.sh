#!/bin/bash
# Deploy Fixes to Production Server 10.1.1.174
# Version: 1.0.0
# Date: 2025-08-24

set -e

PRODUCTION_SERVER="10.1.1.174"
PRODUCTION_USER="aktienanalyse"
PRODUCTION_PATH="/opt/aktienanalyse-ökosystem"
LOCAL_PATH="/home/mdoehler/aktienanalyse-ökosystem"

echo "🚀 Deploying fixes to production server $PRODUCTION_SERVER"
echo "=========================================="

# 1. Copy fixed Event-Bus Service
echo "📦 Copying fixed Event-Bus Service..."
rsync -avz --exclude='__pycache__' --exclude='*.pyc' \
    $LOCAL_PATH/services/event-bus-service/ \
    $PRODUCTION_USER@$PRODUCTION_SERVER:$PRODUCTION_PATH/services/event-bus-service/

# 2. Copy fixed main.py files
echo "📦 Copying fixed main.py files..."
for service in intelligent-core-service broker-gateway-service; do
    scp $LOCAL_PATH/services/$service/main.py \
        $PRODUCTION_USER@$PRODUCTION_SERVER:$PRODUCTION_PATH/services/$service/main.py
done

# 3. Copy health check implementations
echo "📦 Copying health check modules..."
ssh $PRODUCTION_USER@$PRODUCTION_SERVER "mkdir -p $PRODUCTION_PATH/services/event-bus-service/infrastructure/health"
scp $LOCAL_PATH/services/event-bus-service/infrastructure/health/*.py \
    $PRODUCTION_USER@$PRODUCTION_SERVER:$PRODUCTION_PATH/services/event-bus-service/infrastructure/health/

# 4. Restart services on production
echo "🔄 Restarting services on production..."
ssh $PRODUCTION_USER@$PRODUCTION_SERVER << 'EOF'
    echo "Restarting Event-Bus Service..."
    sudo systemctl restart aktienanalyse-event-bus.service
    sleep 5
    
    echo "Restarting Intelligent Core Service..."
    sudo systemctl restart aktienanalyse-core.service
    sleep 5
    
    echo "Restarting Broker Gateway Service..."
    sudo systemctl restart aktienanalyse-broker.service
    sleep 5
    
    echo "Checking service status..."
    sudo systemctl status aktienanalyse-event-bus.service --no-pager | head -10
    sudo systemctl status aktienanalyse-core.service --no-pager | head -10
    sudo systemctl status aktienanalyse-broker.service --no-pager | head -10
EOF

# 5. Test health endpoints
echo "🧪 Testing health endpoints..."
echo "Event-Bus Health Check:"
curl -s http://$PRODUCTION_SERVER:8014/health | python3 -m json.tool

echo "Intelligent Core Health Check:"
curl -s http://$PRODUCTION_SERVER:8001/health | python3 -m json.tool

echo "Unified Profit Engine Health Check:"
curl -s http://$PRODUCTION_SERVER:8025/health | python3 -m json.tool

echo "✅ Deployment completed successfully!"