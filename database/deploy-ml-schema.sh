#!/bin/bash
# =============================================
# ML Schema Deployment Script
# Deployed ML-Schema auf 10.1.1.174 PostgreSQL
#
# Autor: Claude Code
# Datum: 17. August 2025
# =============================================

set -euo pipefail

# Konfiguration
POSTGRES_HOST="10.1.1.174"
POSTGRES_PORT="5432"
POSTGRES_DB="aktienanalyse"
POSTGRES_USER="aktienanalyse"
POSTGRES_SCHEMA_FILE="./migrations/ml-schema-extension_v1_0_0_20250817.sql"

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging-Funktion
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo "========================================"
echo "   ML Schema Deployment v1.0.0"
echo "   Target: $POSTGRES_HOST:$POSTGRES_PORT"
echo "   Database: $POSTGRES_DB"
echo "========================================"
echo

# Voraussetzungen prüfen
log_info "Checking prerequisites..."

# PSQL Client prüfen
if ! command -v psql &> /dev/null; then
    log_error "psql client not found. Please install PostgreSQL client."
    exit 1
fi

# Schema-Datei prüfen
if [[ ! -f "$POSTGRES_SCHEMA_FILE" ]]; then
    log_error "Schema file not found: $POSTGRES_SCHEMA_FILE"
    exit 1
fi

log_success "Prerequisites check passed"

# Verbindung testen
log_info "Testing database connection..."

PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -c "SELECT version();" > /dev/null 2>&1

if [[ $? -eq 0 ]]; then
    log_success "Database connection successful"
else
    log_error "Database connection failed. Please check credentials and network connectivity."
    echo "Connection details:"
    echo "  Host: $POSTGRES_HOST"
    echo "  Port: $POSTGRES_PORT"
    echo "  Database: $POSTGRES_DB"
    echo "  User: $POSTGRES_USER"
    echo
    echo "Please set POSTGRES_PASSWORD environment variable if needed:"
    echo "  export POSTGRES_PASSWORD='your_password'"
    exit 1
fi

# Schema-Version prüfen
log_info "Checking current ML schema version..."

CURRENT_VERSION=$(PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -t -c "SELECT version FROM ml_schema_version ORDER BY deployed_at DESC LIMIT 1;" 2>/dev/null | xargs || echo "none")

if [[ "$CURRENT_VERSION" != "none" ]]; then
    log_warning "ML schema version $CURRENT_VERSION already exists"
    echo -n "Do you want to continue with deployment? [y/N]: "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled by user"
        exit 0
    fi
else
    log_info "No existing ML schema found"
fi

# Backup erstellen
log_info "Creating database backup before deployment..."

BACKUP_FILE="backup_before_ml_schema_$(date +%Y%m%d_%H%M%S).sql"

PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --schema-only \
    > "$BACKUP_FILE" 2>/dev/null

if [[ $? -eq 0 ]]; then
    log_success "Database backup created: $BACKUP_FILE"
else
    log_warning "Failed to create backup, continuing anyway..."
fi

# ML Schema deployen
log_info "Deploying ML Schema Extension v1.0.0..."

# Transaction für sicheres Deployment
PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -v ON_ERROR_STOP=1 \
    -f "$POSTGRES_SCHEMA_FILE"

if [[ $? -eq 0 ]]; then
    log_success "ML Schema deployed successfully!"
else
    log_error "ML Schema deployment failed!"
    
    if [[ -f "$BACKUP_FILE" ]]; then
        log_info "You can restore from backup: $BACKUP_FILE"
        echo "  psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB < $BACKUP_FILE"
    fi
    exit 1
fi

# Deployment-Verifikation
log_info "Verifying deployment..."

# ML-Tabellen zählen
ML_TABLES_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'ml_%';" | xargs)

# TimescaleDB-Hypertables prüfen
HYPERTABLES_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -t -c "SELECT COUNT(*) FROM timescaledb_information.hypertables WHERE hypertable_name LIKE 'ml_%';" 2>/dev/null | xargs || echo "0")

# Funktionen prüfen
ML_FUNCTIONS_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -t -c "SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name LIKE '%ml_%';" | xargs)

echo
echo "=== DEPLOYMENT VERIFICATION ==="
echo "ML Tables created: $ML_TABLES_COUNT"
echo "TimescaleDB Hypertables: $HYPERTABLES_COUNT"
echo "ML Functions created: $ML_FUNCTIONS_COUNT"

# Schema-Version prüfen
DEPLOYED_VERSION=$(PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -t -c "SELECT version FROM ml_schema_version ORDER BY deployed_at DESC LIMIT 1;" | xargs)

echo "Deployed Schema Version: $DEPLOYED_VERSION"

# Erwartete Werte prüfen
EXPECTED_TABLES=11
EXPECTED_FUNCTIONS=3

if [[ "$ML_TABLES_COUNT" -ge "$EXPECTED_TABLES" ]] && [[ "$ML_FUNCTIONS_COUNT" -ge "$EXPECTED_FUNCTIONS" ]]; then
    log_success "ML Schema deployment verification PASSED"
    
    echo
    echo "=== NEXT STEPS ==="
    echo "1. Configure ML service environment variables"
    echo "2. Deploy ML Analytics Service"
    echo "3. Start ML service with systemd"
    echo
    echo "Environment variables to set:"
    echo "  ML_DATABASE_HOST=$POSTGRES_HOST"
    echo "  ML_DATABASE_PORT=$POSTGRES_PORT"
    echo "  ML_DATABASE_NAME=$POSTGRES_DB"
    echo "  ML_DATABASE_USER=ml_service"
    echo "  ML_DATABASE_PASSWORD=ml_service_secure_2025"
    
else
    log_error "ML Schema deployment verification FAILED"
    echo "Expected: $EXPECTED_TABLES tables, $EXPECTED_FUNCTIONS functions"
    echo "Found: $ML_TABLES_COUNT tables, $ML_FUNCTIONS_COUNT functions"
    exit 1
fi

# Cleanup optional backup bei Erfolg
if [[ -f "$BACKUP_FILE" ]]; then
    echo
    echo -n "Remove backup file $BACKUP_FILE? [y/N]: "
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm "$BACKUP_FILE"
        log_info "Backup file removed"
    else
        log_info "Backup file kept: $BACKUP_FILE"
    fi
fi

log_success "ML Schema Deployment completed successfully!"
echo "========================================"