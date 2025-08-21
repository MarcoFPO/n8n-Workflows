#!/bin/bash
"""
Production API Keys Setup Script
Setzt Produktions-API-Keys für alle globalen Datenquellen
"""

# Konfiguration
PROD_SERVER="10.1.1.174"
PROD_USER="root"
ENV_FILE="/opt/aktienanalyse-ökosystem/.env"

# Farben für Output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🔑 PRODUCTION API KEYS SETUP"
echo "============================"
echo "Server: $PROD_SERVER"
echo "Time: $(date)"
echo ""

# Funktion für sicheren API Key Input
secure_input() {
    local prompt="$1"
    local var_name="$2"
    echo -n "$prompt: "
    read -s value
    echo ""
    eval "$var_name='$value'"
}

# Funktion für API Key Validierung
validate_api_key() {
    local service="$1"
    local api_key="$2"
    
    echo "Validating $service API key..."
    
    case $service in
        "twelve_data")
            # Teste Twelve Data API
            local response=$(curl -s "https://api.twelvedata.com/time_series?symbol=AAPL&interval=1min&apikey=$api_key&outputsize=1" | grep -o '"status":"ok"' || echo "error")
            if [[ $response == *'"status":"ok"'* ]]; then
                echo -e "${GREEN}✅ Twelve Data API key valid${NC}"
                return 0
            else
                echo -e "${RED}❌ Twelve Data API key invalid${NC}"
                return 1
            fi
            ;;
        "eod_historical")
            # Teste EOD Historical API
            local response=$(curl -s "https://eodhistoricaldata.com/api/eod/AAPL.US?api_token=$api_key&fmt=json&limit=1" | grep -o '"close"' || echo "error")
            if [[ $response == *'"close"'* ]]; then
                echo -e "${GREEN}✅ EOD Historical API key valid${NC}"
                return 0
            else
                echo -e "${RED}❌ EOD Historical API key invalid${NC}"
                return 1
            fi
            ;;
        "marketstack")
            # Teste Marketstack API
            local response=$(curl -s "http://api.marketstack.com/v1/eod?access_key=$api_key&symbols=AAPL&limit=1" | grep -o '"data"' || echo "error")
            if [[ $response == *'"data"'* ]]; then
                echo -e "${GREEN}✅ Marketstack API key valid${NC}"
                return 0
            else
                echo -e "${RED}❌ Marketstack API key invalid${NC}"
                return 1
            fi
            ;;
        *)
            echo -e "${YELLOW}⚠️  Unknown service: $service${NC}"
            return 0
            ;;
    esac
}

# API Keys Input
echo "📝 Please enter your production API keys:"
echo ""

echo "1. Twelve Data Global Markets API Key"
echo "   (Get from: https://twelvedata.com/)"
secure_input "Twelve Data API Key" "TWELVE_DATA_KEY"

echo ""
echo "2. EOD Historical Data API Key"
echo "   (Get from: https://eodhistoricaldata.com/)"
secure_input "EOD Historical API Key" "EOD_HISTORICAL_KEY"

echo ""
echo "3. Marketstack Global Exchanges API Key"
echo "   (Get from: https://marketstack.com/)"
secure_input "Marketstack API Key" "MARKETSTACK_KEY"

echo ""
echo "4. Alpha Vantage API Key (optional - already configured)"
secure_input "Alpha Vantage API Key (optional)" "ALPHA_VANTAGE_KEY"

echo ""
echo "5. Finnhub API Key (optional - already configured)"
secure_input "Finnhub API Key (optional)" "FINNHUB_KEY"

echo ""
echo "6. IEX Cloud API Key (optional - already configured)"
secure_input "IEX Cloud API Key (optional)" "IEX_CLOUD_KEY"

echo ""
echo "🔍 VALIDATING API KEYS..."
echo "========================="

# Validate API Keys
valid_keys=0
total_keys=3

if [ -n "$TWELVE_DATA_KEY" ]; then
    if validate_api_key "twelve_data" "$TWELVE_DATA_KEY"; then
        ((valid_keys++))
    fi
else
    echo -e "${YELLOW}⚠️  Twelve Data API key not provided - using demo mode${NC}"
fi

if [ -n "$EOD_HISTORICAL_KEY" ]; then
    if validate_api_key "eod_historical" "$EOD_HISTORICAL_KEY"; then
        ((valid_keys++))
    fi
else
    echo -e "${YELLOW}⚠️  EOD Historical API key not provided - using demo mode${NC}"
fi

if [ -n "$MARKETSTACK_KEY" ]; then
    if validate_api_key "marketstack" "$MARKETSTACK_KEY"; then
        ((valid_keys++))
    fi
else
    echo -e "${YELLOW}⚠️  Marketstack API key not provided - using demo mode${NC}"
fi

echo ""
echo "Validation Results: $valid_keys/$total_keys keys valid"

# Ask for confirmation
echo ""
echo "🚀 DEPLOYMENT CONFIRMATION"
echo "=========================="
echo "Valid API keys: $valid_keys/$total_keys"
echo "Services will use demo mode for invalid/missing keys"
echo ""
read -p "Deploy API keys to production? (y/N): " confirm

if [[ $confirm != [yY] && $confirm != [yY][eE][sS] ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "📤 DEPLOYING API KEYS TO PRODUCTION..."
echo "======================================"

# Create environment file on production server
ssh "$PROD_USER@$PROD_SERVER" "cat > $ENV_FILE << 'EOF'
# Aktienanalyse Ökosystem - Production API Keys
# Generated: $(date)

# Global Data Sources API Keys
TWELVE_DATA_API_KEY=\"${TWELVE_DATA_KEY:-demo_key_twelve_data_global}\"
EODHD_API_KEY=\"${EOD_HISTORICAL_KEY:-demo_key_eod_historical}\"
MARKETSTACK_API_KEY=\"${MARKETSTACK_KEY:-demo_key_marketstack_global}\"

# Regional Data Sources API Keys (Optional)
ALPHA_VANTAGE_API_KEY=\"${ALPHA_VANTAGE_KEY:-demo_key_alpha_vantage}\"
FINNHUB_API_KEY=\"${FINNHUB_KEY:-demo_key_finnhub}\"
IEX_CLOUD_API_KEY=\"${IEX_CLOUD_KEY:-demo_key_iex_cloud}\"

# Service Configuration
PYTHONPATH=\"/opt/aktienanalyse-ökosystem\"
ENVIRONMENT=\"production\"
LOG_LEVEL=\"INFO\"
SERVER_ID=\"10.1.1.174\"

# Rate Limiting Configuration
TWELVE_DATA_RATE_LIMIT=8
EOD_HISTORICAL_RATE_LIMIT=20
MARKETSTACK_RATE_LIMIT=1000
ALPHA_VANTAGE_RATE_LIMIT=25
FINNHUB_RATE_LIMIT=60
IEX_CLOUD_RATE_LIMIT=100

EOF"

# Set proper permissions
ssh "$PROD_USER@$PROD_SERVER" "chown aktienanalyse:aktienanalyse $ENV_FILE && chmod 600 $ENV_FILE"

echo -e "${GREEN}✅ Environment file created: $ENV_FILE${NC}"

# Update systemd service files to use environment file
echo ""
echo "🔧 UPDATING SYSTEMD SERVICES..."
echo "==============================="

GLOBAL_SERVICES=("twelve-data-global" "eod-historical-emerging" "marketstack-global-exchanges")

for service in "${GLOBAL_SERVICES[@]}"; do
    echo "Updating $service.service..."
    
    ssh "$PROD_USER@$PROD_SERVER" "
        # Add EnvironmentFile to service
        sed -i '/Environment=/d' /etc/systemd/system/$service.service
        sed -i '/\[Service\]/a EnvironmentFile=$ENV_FILE' /etc/systemd/system/$service.service
    "
    
    echo -e "${GREEN}✅ Updated $service.service${NC}"
done

# Reload systemd and restart services
echo ""
echo "🔄 RESTARTING SERVICES WITH NEW API KEYS..."
echo "==========================================="

ssh "$PROD_USER@$PROD_SERVER" "
    # Reload systemd configuration
    systemctl daemon-reload
    
    # Restart global services with new API keys
    echo 'Restarting global services...'
    systemctl restart twelve-data-global.service
    sleep 3
    systemctl restart eod-historical-emerging.service  
    sleep 3
    systemctl restart marketstack-global-exchanges.service
    sleep 3
    
    # Restart integration service
    echo 'Restarting integration service...'
    systemctl restart data-sources-integration.service
    sleep 5
"

# Verify services are running
echo ""
echo "✅ VERIFYING SERVICE STATUS..."
echo "============================="

ALL_SERVICES=("twelve-data-global" "eod-historical-emerging" "marketstack-global-exchanges" "data-sources-integration")

running_services=0
for service in "${ALL_SERVICES[@]}"; do
    status=$(ssh "$PROD_USER@$PROD_SERVER" "systemctl is-active $service.service")
    
    if [ "$status" = "active" ]; then
        echo -e "${GREEN}✅ $service: RUNNING${NC}"
        ((running_services++))
    else
        echo -e "${RED}❌ $service: $status${NC}"
    fi
done

echo ""
echo "📊 DEPLOYMENT SUMMARY"
echo "===================="
echo "API Keys Deployed: $valid_keys/$total_keys valid"
echo "Services Running: $running_services/${#ALL_SERVICES[@]}"
echo "Environment File: $ENV_FILE"
echo "Deployment Time: $(date)"

if [ $running_services -eq ${#ALL_SERVICES[@]} ]; then
    echo -e "${GREEN}🎉 Production API keys deployment successful!${NC}"
    echo ""
    echo "🔍 NEXT STEPS:"
    echo "- Monitor service logs: journalctl -u data-sources-integration -f"
    echo "- Run health check: ./scripts/health_monitor.sh check"
    echo "- Test global APIs: ./scripts/health_monitor.sh apis"
    echo "- Performance monitoring: ./scripts/health_monitor.sh monitor"
else
    echo -e "${RED}⚠️  Some services failed to start. Check logs and restart manually.${NC}"
    echo ""
    echo "🔧 TROUBLESHOOTING:"
    echo "- Check service logs: journalctl -u <service-name> -n 50"
    echo "- Restart failed services: systemctl restart <service-name>"
    echo "- Verify API keys: cat $ENV_FILE"
fi

echo ""
echo "📚 DOCUMENTATION:"
echo "- API Keys Guide: docs/API_KEYS_SETUP.md"
echo "- Health Monitoring: docs/HEALTH_MONITORING.md"
echo "- Service Management: docs/SERVICE_MANAGEMENT.md"