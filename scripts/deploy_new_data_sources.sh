#!/bin/bash
"""
Deployment Script für neue Datenquellen-Module
Kopiert Module zur Produktionsumgebung und startet Services
"""

set -e

# Konfiguration
LOCAL_BASE="/home/mdoehler/aktienanalyse-ökosystem"
PROD_SERVER="10.1.1.174"
PROD_BASE="/opt/aktienanalyse-ökosystem"
PROD_USER="root"

echo "🚀 Starting deployment of new data sources modules..."

# Farben für Output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Funktion für farbigen Output
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check ob Produktionsserver erreichbar ist
check_production_server() {
    log_info "Checking production server connectivity..."
    if ping -c 1 "$PROD_SERVER" &> /dev/null; then
        log_info "Production server $PROD_SERVER is reachable"
    else
        log_error "Production server $PROD_SERVER is not reachable"
        exit 1
    fi
}

# Backup alte Services falls vorhanden
backup_existing_services() {
    log_info "Creating backup of existing services..."
    ssh "$PROD_USER@$PROD_SERVER" "
        if [ -d $PROD_BASE/services/data-sources ]; then
            sudo cp -r $PROD_BASE/services/data-sources $PROD_BASE/services/data-sources.backup.$(date +%Y%m%d_%H%M%S)
            echo 'Backup created successfully'
        else
            echo 'No existing data-sources directory found'
        fi
    "
}

# Kopiere neue Module zur Produktion
deploy_modules() {
    log_info "Deploying new data source modules..."
    
    # Erstelle Verzeichnisse falls nicht vorhanden
    ssh "$PROD_USER@$PROD_SERVER" "
        mkdir -p $PROD_BASE/services/data-sources
        mkdir -p $PROD_BASE/services/integration
        mkdir -p $PROD_BASE/configs/systemd
        chown -R aktienanalyse:aktienanalyse $PROD_BASE/services
        chown -R aktienanalyse:aktienanalyse $PROD_BASE/configs
    "
    
    # Kopiere Data Source Services
    log_info "Copying data source services..."
    scp "$LOCAL_BASE/services/data-sources/alpha_vantage_smallcap_service.py" \
        "$PROD_USER@$PROD_SERVER:$PROD_BASE/services/data-sources/"
    scp "$LOCAL_BASE/services/data-sources/finnhub_fundamentals_service.py" \
        "$PROD_USER@$PROD_SERVER:$PROD_BASE/services/data-sources/"
    scp "$LOCAL_BASE/services/data-sources/ecb_macroeconomics_service.py" \
        "$PROD_USER@$PROD_SERVER:$PROD_BASE/services/data-sources/"
    scp "$LOCAL_BASE/services/data-sources/dealroom_eu_startup_service.py" \
        "$PROD_USER@$PROD_SERVER:$PROD_BASE/services/data-sources/"
    scp "$LOCAL_BASE/services/data-sources/iex_cloud_microcap_service.py" \
        "$PROD_USER@$PROD_SERVER:$PROD_BASE/services/data-sources/"
    
    # Kopiere Global Data Source Services
    log_info "Copying global data source services..."
    scp "$LOCAL_BASE/services/data-sources/twelve_data_global_service.py" \
        "$PROD_USER@$PROD_SERVER:$PROD_BASE/services/data-sources/"
    scp "$LOCAL_BASE/services/data-sources/eod_historical_emerging_service.py" \
        "$PROD_USER@$PROD_SERVER:$PROD_BASE/services/data-sources/"
    scp "$LOCAL_BASE/services/data-sources/marketstack_global_exchanges_v1.0.0_20250817.py" \
        "$PROD_USER@$PROD_SERVER:$PROD_BASE/services/data-sources/"
    
    # Kopiere Integration Service
    log_info "Copying integration service..."
    scp "$LOCAL_BASE/services/integration/data_sources_integration.py" \
        "$PROD_USER@$PROD_SERVER:$PROD_BASE/services/integration/"
    
    # Setze Permissions
    ssh "$PROD_USER@$PROD_SERVER" "
        chmod +x $PROD_BASE/services/data-sources/*.py
        chmod +x $PROD_BASE/services/integration/*.py
    "
    
    log_info "Modules deployed successfully"
}

# Kopiere systemd Service Files
deploy_systemd_services() {
    log_info "Deploying systemd service configurations..."
    
    # Kopiere Service Files
    scp "$LOCAL_BASE/configs/systemd/alpha-vantage-smallcap.service" \
        "$PROD_USER@$PROD_SERVER:/tmp/"
    scp "$LOCAL_BASE/configs/systemd/finnhub-fundamentals.service" \
        "$PROD_USER@$PROD_SERVER:/tmp/"
    scp "$LOCAL_BASE/configs/systemd/ecb-macroeconomics.service" \
        "$PROD_USER@$PROD_SERVER:/tmp/"
    scp "$LOCAL_BASE/configs/systemd/dealroom-eu-startup.service" \
        "$PROD_USER@$PROD_SERVER:/tmp/"
    scp "$LOCAL_BASE/configs/systemd/iex-cloud-microcap.service" \
        "$PROD_USER@$PROD_SERVER:/tmp/"
    scp "$LOCAL_BASE/configs/systemd/data-sources-integration.service" \
        "$PROD_USER@$PROD_SERVER:/tmp/"
    
    # Kopiere Global Service Files
    scp "$LOCAL_BASE/configs/systemd/twelve-data-global.service" \
        "$PROD_USER@$PROD_SERVER:/tmp/"
    scp "$LOCAL_BASE/configs/systemd/eod-historical-emerging.service" \
        "$PROD_USER@$PROD_SERVER:/tmp/"
    scp "$LOCAL_BASE/configs/systemd/marketstack-global-exchanges.service" \
        "$PROD_USER@$PROD_SERVER:/tmp/"
    
    # Installiere Service Files
    ssh "$PROD_USER@$PROD_SERVER" "
        mv /tmp/alpha-vantage-smallcap.service /etc/systemd/system/
        mv /tmp/finnhub-fundamentals.service /etc/systemd/system/
        mv /tmp/ecb-macroeconomics.service /etc/systemd/system/
        mv /tmp/dealroom-eu-startup.service /etc/systemd/system/
        mv /tmp/iex-cloud-microcap.service /etc/systemd/system/
        mv /tmp/data-sources-integration.service /etc/systemd/system/
        
        # Installiere Global Service Files
        mv /tmp/twelve-data-global.service /etc/systemd/system/
        mv /tmp/eod-historical-emerging.service /etc/systemd/system/
        mv /tmp/marketstack-global-exchanges.service /etc/systemd/system/
        
        systemctl daemon-reload
    "
    
    log_info "Systemd services configured successfully"
}

# Teste Module vor Aktivierung
test_modules() {
    log_info "Testing modules before activation..."
    
    ssh "$PROD_USER@$PROD_SERVER" "
        cd $PROD_BASE/services/data-sources
        
        # Test Python syntax für alle Module
        echo 'Testing Alpha Vantage module...'
        python3 -m py_compile alpha_vantage_smallcap_service.py
        
        echo 'Testing Finnhub module...'
        python3 -m py_compile finnhub_fundamentals_service.py
        
        echo 'Testing ECB module...'
        python3 -m py_compile ecb_macroeconomics_service.py
        
        echo 'Testing Dealroom module...'
        python3 -m py_compile dealroom_eu_startup_service.py
        
        echo 'Testing IEX Cloud module...'
        python3 -m py_compile iex_cloud_microcap_service.py
        
        # Test Global Modules
        echo 'Testing Twelve Data Global module...'
        python3 -m py_compile twelve_data_global_service.py
        
        echo 'Testing EOD Historical Emerging module...'
        python3 -m py_compile eod_historical_emerging_service.py
        
        echo 'Testing Marketstack Global Exchanges module...'
        python3 -m py_compile marketstack_global_exchanges_v1.0.0_20250817.py
        
        cd $PROD_BASE/services/integration
        echo 'Testing integration service...'
        python3 -m py_compile data_sources_integration.py
        
        echo 'All modules syntax check passed'
    "
    
    log_info "Module tests completed successfully"
}

# Aktiviere und starte Services
activate_services() {
    log_info "Activating and starting new services..."
    
    ssh "$PROD_USER@$PROD_SERVER" "
        # Enable services
        systemctl enable alpha-vantage-smallcap.service
        systemctl enable finnhub-fundamentals.service
        systemctl enable ecb-macroeconomics.service
        systemctl enable dealroom-eu-startup.service
        systemctl enable iex-cloud-microcap.service
        systemctl enable data-sources-integration.service
        
        # Enable Global Services
        systemctl enable twelve-data-global.service
        systemctl enable eod-historical-emerging.service
        systemctl enable marketstack-global-exchanges.service
        
        # Start services in dependency order
        echo 'Starting data source services...'
        systemctl start alpha-vantage-smallcap.service
        sleep 3
        systemctl start finnhub-fundamentals.service
        sleep 3
        systemctl start ecb-macroeconomics.service
        sleep 3
        systemctl start dealroom-eu-startup.service
        sleep 3
        systemctl start iex-cloud-microcap.service
        sleep 5
        
        # Start Global Services
        echo 'Starting global data source services...'
        systemctl start twelve-data-global.service
        sleep 4
        systemctl start eod-historical-emerging.service
        sleep 4
        systemctl start marketstack-global-exchanges.service
        sleep 5
        
        echo 'Starting integration service...'
        systemctl start data-sources-integration.service
        sleep 3
    "
    
    log_info "Services activated and started"
}

# Überprüfe Service Status
check_service_status() {
    log_info "Checking service status..."
    
    ssh "$PROD_USER@$PROD_SERVER" "
        echo '=== Service Status Check ==='
        
        services=(
            'alpha-vantage-smallcap'
            'finnhub-fundamentals'
            'ecb-macroeconomics'
            'dealroom-eu-startup'
            'iex-cloud-microcap'
            'twelve-data-global'
            'eod-historical-emerging'
            'marketstack-global-exchanges'
            'data-sources-integration'
        )
        
        all_running=true
        
        for service in \"\${services[@]}\"; do
            if systemctl is-active --quiet \"\$service.service\"; then
                echo \"✅ \$service: RUNNING\"
            else
                echo \"❌ \$service: NOT RUNNING\"
                all_running=false
            fi
        done
        
        if \$all_running; then
            echo \"\"
            echo \"🎉 All services are running successfully!\"
        else
            echo \"\"
            echo \"⚠️  Some services are not running. Check logs with:\"
            echo \"   journalctl -u <service-name> -f\"
        fi
    "
}

# Erstelle Deployment Dokumentation
create_deployment_docs() {
    log_info "Creating deployment documentation..."
    
    cat > "$LOCAL_BASE/DEPLOYMENT_$(date +%Y%m%d_%H%M%S).md" << EOF
# Data Sources Deployment Report

**Deployment Date**: $(date)
**Target Server**: $PROD_SERVER
**Deployed By**: $(whoami)

## Deployed Modules

### Data Source Services
- ✅ Alpha Vantage Small-Cap Service
- ✅ Finnhub Fundamentals Service  
- ✅ ECB Macroeconomics Service
- ✅ Dealroom EU-Startup Service
- ✅ IEX Cloud Microcap Service

### Global Data Source Services
- ✅ Twelve Data Global Markets Service
- ✅ EOD Historical Emerging Markets Service
- ✅ Marketstack Global Exchanges Service

### Integration Service
- ✅ Data Sources Integration Service (Extended with Global Sources)

### SystemD Services
- ✅ alpha-vantage-smallcap.service
- ✅ finnhub-fundamentals.service
- ✅ ecb-macroeconomics.service
- ✅ dealroom-eu-startup.service
- ✅ iex-cloud-microcap.service
- ✅ twelve-data-global.service
- ✅ eod-historical-emerging.service
- ✅ marketstack-global-exchanges.service
- ✅ data-sources-integration.service

## Service Management Commands

### Start Services
\`\`\`bash
sudo systemctl start alpha-vantage-smallcap
sudo systemctl start finnhub-fundamentals
sudo systemctl start ecb-macroeconomics
sudo systemctl start dealroom-eu-startup
sudo systemctl start iex-cloud-microcap
sudo systemctl start twelve-data-global
sudo systemctl start eod-historical-emerging
sudo systemctl start marketstack-global-exchanges
sudo systemctl start data-sources-integration
\`\`\`

### Check Status
\`\`\`bash
sudo systemctl status data-sources-integration
\`\`\`

### View Logs
\`\`\`bash
journalctl -u data-sources-integration -f
\`\`\`

## API Endpoints

### Integration Service
The integration service provides unified access to all data sources through standardized requests.

### Individual Services
Each service can be accessed directly for specialized requests.

## Notes
- All services use demo API keys initially
- Update API keys in service environment variables for production use
- Services automatically restart on failure
- Logs are available via journalctl

EOF

    log_info "Deployment documentation created: DEPLOYMENT_$(date +%Y%m%d_%H%M%S).md"
}

# Main Deployment Flow
main() {
    echo "=== New Data Sources Deployment ==="
    echo "Target: $PROD_SERVER"
    echo "Time: $(date)"
    echo ""
    
    check_production_server
    backup_existing_services
    deploy_modules
    deploy_systemd_services
    test_modules
    activate_services
    sleep 10  # Give services time to start
    check_service_status
    create_deployment_docs
    
    echo ""
    log_info "🎉 Deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Update API keys in production environment"
    echo "2. Monitor service logs for any issues"
    echo "3. Test integration with existing Event-Bus system"
    echo "4. Verify data quality and API responses"
    echo ""
    echo "Service logs: journalctl -u data-sources-integration -f"
    echo "Status check: systemctl status data-sources-integration"
}

# Error handling
trap 'log_error "Deployment failed at line $LINENO"; exit 1' ERR

# Run deployment
main "$@"