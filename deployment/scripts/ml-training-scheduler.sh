#!/bin/bash
# =============================================
# ML Training Scheduler Script
# Triggered täglich um 02:00 Uhr via systemd timer
#
# Autor: Claude Code
# Datum: 17. August 2025
# =============================================

set -euo pipefail

# Logging-Funktion
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >&2
}

# Konfiguration
SYMBOLS=("AAPL" "MSFT" "GOOGL" "AMZN" "TSLA")
MODEL_TYPES=("technical")
HORIZONS=(7 30 150 365)
REDIS_URL="${ML_REDIS_URL:-redis://localhost:6379/2}"
MAX_CONCURRENT_TRAININGS=2

log_info "=== ML Training Scheduler Started ==="
log_info "Symbols: ${SYMBOLS[*]}"
log_info "Model Types: ${MODEL_TYPES[*]}"
log_info "Horizons: ${HORIZONS[*]} days"

# Redis Client für Event Publishing
REDIS_CLI_CMD="redis-cli -u $REDIS_URL"

# Training Events publizieren
publish_training_event() {
    local symbol=$1
    local model_type=$2
    local horizon_days=$3
    local correlation_id="scheduler_$(date +%s)_${symbol}_${model_type}_${horizon_days}"
    
    local event_data=$(cat <<EOF
{
    "event_id": "$(uuidgen)",
    "event_type": "ml.model.training.requested",
    "correlation_id": "$correlation_id",
    "source_service": "ml-scheduler",
    "target_service": "ml-training",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)",
    "version": "1.0",
    "payload": {
        "symbol": "$symbol",
        "model_type": "$model_type",
        "horizon_days": $horizon_days,
        "priority": "scheduled",
        "requested_by": "scheduler",
        "reason": "daily_scheduled_training"
    },
    "metadata": {
        "trace_id": "$correlation_id",
        "retry_count": 0,
        "ttl_seconds": 3600
    }
}
EOF
    )
    
    # Event über Redis publizieren
    echo "$event_data" | $REDIS_CLI_CMD PUBLISH "events:ml:model:training:requested" "$(cat)"
    
    if [[ $? -eq 0 ]]; then
        log_info "Training event published: $symbol $model_type ${horizon_days}d"
    else
        log_error "Failed to publish training event: $symbol $model_type ${horizon_days}d"
        return 1
    fi
}

# Batch Training Event publizieren
publish_batch_training_event() {
    local correlation_id="scheduler_batch_$(date +%s)"
    
    local event_data=$(cat <<EOF
{
    "event_id": "$(uuidgen)",
    "event_type": "ml.training.scheduled",
    "correlation_id": "$correlation_id",
    "source_service": "ml-scheduler",
    "target_service": "ml-training",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)",
    "version": "1.0",
    "payload": {
        "symbols": $(printf '%s\n' "${SYMBOLS[@]}" | jq -R . | jq -s .),
        "model_types": $(printf '%s\n' "${MODEL_TYPES[@]}" | jq -R . | jq -s .),
        "horizons": $(printf '%s\n' "${HORIZONS[@]}" | jq -R . | jq -s . | jq 'map(tonumber)'),
        "batch_size": $MAX_CONCURRENT_TRAININGS,
        "requested_by": "daily_scheduler",
        "reason": "daily_model_refresh"
    },
    "metadata": {
        "trace_id": "$correlation_id",
        "retry_count": 0,
        "ttl_seconds": 7200
    }
}
EOF
    )
    
    # Batch Event publizieren
    echo "$event_data" | $REDIS_CLI_CMD PUBLISH "events:ml:training:scheduled" "$(cat)"
    
    if [[ $? -eq 0 ]]; then
        log_info "Batch training event published for ${#SYMBOLS[@]} symbols"
    else
        log_error "Failed to publish batch training event"
        return 1
    fi
}

# Redis Verbindung testen
test_redis_connection() {
    if ! $REDIS_CLI_CMD ping > /dev/null 2>&1; then
        log_error "Redis connection failed"
        return 1
    fi
    
    log_info "Redis connection successful"
    return 0
}

# Training Services Status prüfen
check_training_service_status() {
    local training_service_active=$(systemctl is-active ml-training.service 2>/dev/null || echo "inactive")
    local analytics_service_active=$(systemctl is-active ml-analytics.service 2>/dev/null || echo "inactive")
    
    if [[ "$training_service_active" != "active" ]]; then
        log_error "ML Training Service is not active: $training_service_active"
        return 1
    fi
    
    if [[ "$analytics_service_active" != "active" ]]; then
        log_error "ML Analytics Service is not active: $analytics_service_active"
        return 1
    fi
    
    log_info "ML Services are active and ready"
    return 0
}

# Hauptausführung
main() {
    local exit_code=0
    
    # Voraussetzungen prüfen
    if ! command -v redis-cli &> /dev/null; then
        log_error "redis-cli not found"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq not found"
        exit 1
    fi
    
    if ! command -v uuidgen &> /dev/null; then
        log_error "uuidgen not found"
        exit 1
    fi
    
    # Redis-Verbindung testen
    if ! test_redis_connection; then
        log_error "Redis connection check failed"
        exit 1
    fi
    
    # Training Services Status prüfen
    if ! check_training_service_status; then
        log_error "ML Services status check failed"
        exit 1
    fi
    
    # Batch Training Event publizieren (effizienter als einzelne Events)
    if publish_batch_training_event; then
        log_info "Batch training scheduled successfully"
    else
        log_error "Failed to schedule batch training"
        exit_code=1
    fi
    
    # Alternativ: Einzelne Training Events für spezielle Fälle
    # Momentan auskommentiert, aber verfügbar für granulare Kontrolle
    
    # training_count=0
    # for symbol in "${SYMBOLS[@]}"; do
    #     for model_type in "${MODEL_TYPES[@]}"; do
    #         for horizon in "${HORIZONS[@]}"; do
    #             if publish_training_event "$symbol" "$model_type" "$horizon"; then
    #                 ((training_count++))
    #                 
    #                 # Throttling um Services nicht zu überlasten
    #                 if (( training_count % MAX_CONCURRENT_TRAININGS == 0 )); then
    #                     log_info "Throttling: waiting 30 seconds before next batch..."
    #                     sleep 30
    #                 fi
    #             else
    #                 log_error "Failed to schedule training: $symbol $model_type ${horizon}d"
    #                 exit_code=1
    #             fi
    #         done
    #     done
    # done
    
    # log_info "Scheduled $training_count training jobs"
    
    # Health Check Event publizieren
    health_check_event=$(cat <<EOF
{
    "event_id": "$(uuidgen)",
    "event_type": "ml.scheduler.health.check",
    "correlation_id": "scheduler_health_$(date +%s)",
    "source_service": "ml-scheduler",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)",
    "version": "1.0",
    "payload": {
        "scheduler_run_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)",
        "symbols_processed": ${#SYMBOLS[@]},
        "exit_code": $exit_code,
        "next_run": "$(date -d 'tomorrow 02:00' '+%Y-%m-%dT%H:%M:%S.%3NZ')"
    }
}
EOF
    )
    
    echo "$health_check_event" | $REDIS_CLI_CMD PUBLISH "events:ml:scheduler:health:check" "$(cat)"
    
    log_info "=== ML Training Scheduler Completed with exit code: $exit_code ==="
    exit $exit_code
}

# Script ausführen
main "$@"