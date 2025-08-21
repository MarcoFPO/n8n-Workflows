#!/bin/bash
"""
Global Data Sources Health Monitor
Überwacht alle 9 Datenquellen-Services und sendet Alerts bei Problemen
"""

# Konfiguration
PROD_SERVER="10.1.1.174"
PROD_USER="root"
ALERT_EMAIL="admin@aktienanalyse.local"
LOG_FILE="/var/log/aktienanalyse/health_monitor.log"

# Farben für Output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Services Liste (alle 9 Services)
SERVICES=(
    "alpha-vantage-smallcap"
    "finnhub-fundamentals"
    "ecb-macroeconomics"
    "dealroom-eu-startup"
    "iex-cloud-microcap"
    "twelve-data-global"
    "eod-historical-emerging"
    "marketstack-global-exchanges"
    "data-sources-integration"
)

# Funktion für Logging
log_message() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Funktion für Service Status Check
check_service_status() {
    local service=$1
    local status=$(ssh "$PROD_USER@$PROD_SERVER" "systemctl is-active $service.service 2>/dev/null || echo 'failed'")
    echo "$status"
}

# Funktion für Service Health Check
check_service_health() {
    local service=$1
    local memory_usage=$(ssh "$PROD_USER@$PROD_SERVER" "systemctl show $service.service --property=MemoryCurrent | cut -d= -f2")
    local cpu_usage=$(ssh "$PROD_USER@$PROD_SERVER" "systemctl show $service.service --property=CPUUsageNSec | cut -d= -f2")
    local restart_count=$(ssh "$PROD_USER@$PROD_SERVER" "systemctl show $service.service --property=NRestarts | cut -d= -f2")
    
    echo "Memory: $memory_usage, CPU: $cpu_usage, Restarts: $restart_count"
}

# Funktion für Global Data Sources API Test
test_global_apis() {
    log_message "Testing Global Data Sources APIs..."
    
    # Test Twelve Data Global
    local twelve_test=$(ssh "$PROD_USER@$PROD_SERVER" "cd /opt/aktienanalyse-ökosystem/services/data-sources && python3 -c '
import asyncio
from twelve_data_global_service import TwelveDataGlobalService
async def test():
    service = TwelveDataGlobalService()
    result = await service.get_global_market_overview(\"all\")
    print(\"twelve_data_success:\" + str(result.get(\"success\", False)))
asyncio.run(test())
' 2>/dev/null | grep 'twelve_data_success:True' || echo 'twelve_data_failed'")
    
    if [[ $twelve_test == *"twelve_data_success:True"* ]]; then
        echo -e "${GREEN}✅ Twelve Data Global API: HEALTHY${NC}"
    else
        echo -e "${RED}❌ Twelve Data Global API: FAILED${NC}"
        log_message "ALERT: Twelve Data Global API test failed"
    fi
    
    # Test EOD Historical Emerging
    local eod_test=$(ssh "$PROD_USER@$PROD_SERVER" "cd /opt/aktienanalyse-ökosystem/services/data-sources && python3 -c '
import asyncio
from eod_historical_emerging_service import EODHistoricalEmergingService
async def test():
    service = EODHistoricalEmergingService()
    result = await service.get_emerging_market_historical_analysis([\"BABA\"], \"asia\")
    print(\"eod_success:\" + str(result.get(\"success\", False)))
asyncio.run(test())
' 2>/dev/null | grep 'eod_success:True' || echo 'eod_failed'")
    
    if [[ $eod_test == *"eod_success:True"* ]]; then
        echo -e "${GREEN}✅ EOD Historical Emerging API: HEALTHY${NC}"
    else
        echo -e "${RED}❌ EOD Historical Emerging API: FAILED${NC}"
        log_message "ALERT: EOD Historical Emerging API test failed"
    fi
    
    # Test Integration Service
    local integration_test=$(ssh "$PROD_USER@$PROD_SERVER" "cd /opt/aktienanalyse-ökosystem/services/integration && python3 -c '
import asyncio, sys
sys.path.append(\"/opt/aktienanalyse-ökosystem/services/data-sources\")
from data_sources_integration import DataSourcesIntegration
async def test():
    integration = DataSourcesIntegration()
    await integration.initialize()
    request = {\"source\": \"twelve_data_global\", \"type\": \"overview\", \"region\": \"all\"}
    result = await integration.handle_data_request(request)
    print(\"integration_success:\" + str(result.get(\"success\", False)))
    await integration.shutdown()
asyncio.run(test())
' 2>/dev/null | grep 'integration_success:True' || echo 'integration_failed'")
    
    if [[ $integration_test == *"integration_success:True"* ]]; then
        echo -e "${GREEN}✅ Integration Service API: HEALTHY${NC}"
    else
        echo -e "${RED}❌ Integration Service API: FAILED${NC}"
        log_message "ALERT: Integration Service API test failed"
    fi
}

# Funktion für Disk Space Check
check_disk_space() {
    local disk_usage=$(ssh "$PROD_USER@$PROD_SERVER" "df /opt/aktienanalyse-ökosystem | tail -1 | awk '{print \$5}' | sed 's/%//'")
    
    if [ "$disk_usage" -gt 90 ]; then
        echo -e "${RED}❌ Disk Usage: ${disk_usage}% (CRITICAL)${NC}"
        log_message "CRITICAL: Disk usage at ${disk_usage}%"
    elif [ "$disk_usage" -gt 80 ]; then
        echo -e "${YELLOW}⚠️  Disk Usage: ${disk_usage}% (WARNING)${NC}"
        log_message "WARNING: Disk usage at ${disk_usage}%"
    else
        echo -e "${GREEN}✅ Disk Usage: ${disk_usage}% (OK)${NC}"
    fi
}

# Funktion für Memory Check
check_memory_usage() {
    local memory_info=$(ssh "$PROD_USER@$PROD_SERVER" "free -m | awk 'NR==2{printf \"Memory Usage: %.1f%% (%s/%s MB)\", \$3*100/\$2, \$3, \$2}'")
    local memory_percent=$(ssh "$PROD_USER@$PROD_SERVER" "free | awk 'NR==2{printf \"%.0f\", \$3*100/\$2}'")
    
    if [ "$memory_percent" -gt 90 ]; then
        echo -e "${RED}❌ ${memory_info} (CRITICAL)${NC}"
        log_message "CRITICAL: ${memory_info}"
    elif [ "$memory_percent" -gt 80 ]; then
        echo -e "${YELLOW}⚠️  ${memory_info} (WARNING)${NC}"
        log_message "WARNING: ${memory_info}"
    else
        echo -e "${GREEN}✅ ${memory_info} (OK)${NC}"
    fi
}

# Funktion für Service Auto-Recovery
auto_recover_service() {
    local service=$1
    log_message "RECOVERY: Attempting to restart service: $service"
    
    ssh "$PROD_USER@$PROD_SERVER" "systemctl restart $service.service"
    sleep 10
    
    local new_status=$(check_service_status "$service")
    if [ "$new_status" = "active" ]; then
        log_message "RECOVERY SUCCESS: Service $service restarted successfully"
        echo -e "${GREEN}✅ Auto-recovery successful for $service${NC}"
        return 0
    else
        log_message "RECOVERY FAILED: Service $service failed to restart"
        echo -e "${RED}❌ Auto-recovery failed for $service${NC}"
        return 1
    fi
}

# Funktion für Alert Versendung
send_alert() {
    local message=$1
    local urgency=$2
    
    # Log alert
    log_message "ALERT [$urgency]: $message"
    
    # Email alert (falls konfiguriert)
    if command -v mail &> /dev/null && [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "Aktienanalyse [$urgency Alert]: $urgency" "$ALERT_EMAIL"
    fi
    
    # SystemD journal
    logger -t "aktienanalyse-monitor" "[$urgency] $message"
}

# Main Health Check Funktion
main_health_check() {
    echo "🏥 AKTIENANALYSE GLOBAL DATA SOURCES HEALTH CHECK"
    echo "================================================="
    echo "Server: $PROD_SERVER"
    echo "Time: $(date)"
    echo ""
    
    # System Resources Check
    echo "🖥️  SYSTEM RESOURCES:"
    check_disk_space
    check_memory_usage
    echo ""
    
    # Services Status Check
    echo "⚙️  SERVICES STATUS:"
    local failed_services=()
    local running_count=0
    
    for service in "${SERVICES[@]}"; do
        local status=$(check_service_status "$service")
        
        if [ "$status" = "active" ]; then
            echo -e "${GREEN}✅ $service: RUNNING${NC}"
            ((running_count++))
        else
            echo -e "${RED}❌ $service: $status${NC}"
            failed_services+=("$service")
            
            # Attempt auto-recovery for critical services
            if [[ "$service" == "data-sources-integration" || "$service" == "twelve-data-global" ]]; then
                echo "Attempting auto-recovery for critical service: $service"
                auto_recover_service "$service"
            fi
        fi
    done
    
    echo ""
    echo "📊 SERVICES SUMMARY:"
    echo "Running: $running_count/${#SERVICES[@]}"
    echo "Failed: ${#failed_services[@]}"
    
    if [ ${#failed_services[@]} -gt 0 ]; then
        echo -e "${RED}Failed Services: ${failed_services[*]}${NC}"
        send_alert "Services failed: ${failed_services[*]}" "HIGH"
    fi
    
    echo ""
    
    # Global APIs Test
    echo "🌍 GLOBAL APIS TEST:"
    test_global_apis
    echo ""
    
    # Overall Health Score
    local health_score=$((running_count * 100 / ${#SERVICES[@]}))
    echo "🎯 OVERALL HEALTH SCORE: $health_score%"
    
    if [ $health_score -eq 100 ]; then
        echo -e "${GREEN}🎉 All systems operational!${NC}"
    elif [ $health_score -ge 80 ]; then
        echo -e "${YELLOW}⚠️  Some issues detected but system mostly operational${NC}"
    else
        echo -e "${RED}🚨 Critical issues detected!${NC}"
        send_alert "Global Data Sources health score below 80%: $health_score%" "CRITICAL"
    fi
    
    echo ""
    echo "Next check: $(date -d '+5 minutes')"
    echo "================================================="
}

# Continuous Monitoring Funktion
continuous_monitor() {
    echo "Starting continuous health monitoring..."
    echo "Press Ctrl+C to stop"
    
    while true; do
        main_health_check
        echo ""
        echo "Waiting 5 minutes until next check..."
        sleep 300  # 5 minutes
        clear
    done
}

# Show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  check       Run single health check"
    echo "  monitor     Start continuous monitoring (5 min intervals)"
    echo "  services    Check services status only"
    echo "  apis        Test global APIs only"
    echo "  recover     Attempt auto-recovery for failed services"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 check                 # Single health check"
    echo "  $0 monitor               # Continuous monitoring"
    echo "  $0 services              # Services status only"
    echo "  $0 apis                  # Global APIs test only"
}

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

# Main script logic
case "${1:-check}" in
    "check")
        main_health_check
        ;;
    "monitor")
        continuous_monitor
        ;;
    "services")
        echo "⚙️  SERVICES STATUS CHECK:"
        for service in "${SERVICES[@]}"; do
            local status=$(check_service_status "$service")
            if [ "$status" = "active" ]; then
                echo -e "${GREEN}✅ $service: RUNNING${NC}"
            else
                echo -e "${RED}❌ $service: $status${NC}"
            fi
        done
        ;;
    "apis")
        test_global_apis
        ;;
    "recover")
        echo "🔧 AUTO-RECOVERY MODE"
        for service in "${SERVICES[@]}"; do
            local status=$(check_service_status "$service")
            if [ "$status" != "active" ]; then
                echo "Recovering service: $service"
                auto_recover_service "$service"
            fi
        done
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        echo "Unknown option: $1"
        show_usage
        exit 1
        ;;
esac