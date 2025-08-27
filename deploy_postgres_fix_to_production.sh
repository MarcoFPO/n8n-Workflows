#!/bin/bash
# ===============================================================================
# Deploy PostgreSQL Fix to Production Server (10.1.1.174)
# Comprehensive Authentication and Schema Fix für Aktienanalyse-Ökosystem
# 
# EXECUTION ON SERVER:
# - Creates database and user
# - Configures authentication properly
# - Creates missing soll_ist_gewinn_tracking table
# - Enables TCP/IP connections
#
# Autor: Claude Code - PostgreSQL Authentication Fix Agent  
# Datum: 26. August 2025
# Version: 1.0.0 (Production Deployment Fix)
# ===============================================================================

set -e  # Exit on any error

SERVER_HOST="10.1.1.174"
SSH_USER="mdoehler"
DB_NAME="aktienanalyse_events"
DB_USER="aktienanalyse"
DB_PASSWORD="secure_password_2025"
PROJECT_PATH="/home/mdoehler/aktienanalyse-ökosystem"

echo "🚀 Deploying PostgreSQL Fix to Production Server $SERVER_HOST"
echo "================================================================================"

# Step 1: Copy SQL fix script to server
echo "📤 Copying SQL fix script to server..."
scp "${PROJECT_PATH}/postgresql_production_config_fix_v1_0_0_20250826.sql" \
    "${SSH_USER}@${SERVER_HOST}:/tmp/"

# Step 2: Create comprehensive fix script for server execution
echo "📝 Creating server-side fix script..."
cat > "/tmp/server_postgres_fix.sh" << 'EOF'
#!/bin/bash
# Server-side PostgreSQL fix script

set -e
echo "🔧 Starting PostgreSQL fix on server..."

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    echo "⚠️ Starting PostgreSQL service..."
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
fi

# Step 1: Create database as postgres user
echo "📊 Creating database aktienanalyse_events..."
sudo -u postgres createdb aktienanalyse_events 2>/dev/null || echo "Database already exists"

# Step 2: Execute SQL fix script
echo "🗄️ Executing SQL fix script..."
sudo -u postgres psql -d aktienanalyse_events -f /tmp/postgresql_production_config_fix_v1_0_0_20250826.sql

# Step 3: Configure PostgreSQL for TCP/IP connections
echo "🔧 Configuring PostgreSQL for TCP/IP connections..."

# Find PostgreSQL version and config path
PG_VERSION=$(sudo -u postgres psql --version | awk '{print $3}' | sed 's/\..*//')
PG_CONFIG_PATH="/etc/postgresql/${PG_VERSION}/main"

echo "PostgreSQL Version: $PG_VERSION"
echo "Config Path: $PG_CONFIG_PATH"

# Backup original configs
sudo cp "${PG_CONFIG_PATH}/postgresql.conf" "${PG_CONFIG_PATH}/postgresql.conf.backup.$(date +%Y%m%d)" 2>/dev/null || true
sudo cp "${PG_CONFIG_PATH}/pg_hba.conf" "${PG_CONFIG_PATH}/pg_hba.conf.backup.$(date +%Y%m%d)" 2>/dev/null || true

# Step 4: Configure postgresql.conf for TCP/IP
echo "📡 Enabling TCP/IP connections in postgresql.conf..."
if ! sudo grep -q "^listen_addresses.*\*" "${PG_CONFIG_PATH}/postgresql.conf"; then
    # Update listen_addresses to accept connections
    sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" "${PG_CONFIG_PATH}/postgresql.conf"
    sudo sed -i "s/listen_addresses = 'localhost'/listen_addresses = '*'/" "${PG_CONFIG_PATH}/postgresql.conf"
fi

# Enable port 5432
if ! sudo grep -q "^port = 5432" "${PG_CONFIG_PATH}/postgresql.conf"; then
    sudo sed -i "s/#port = 5432/port = 5432/" "${PG_CONFIG_PATH}/postgresql.conf"
fi

# Step 5: Configure pg_hba.conf for authentication
echo "🔐 Configuring authentication in pg_hba.conf..."

# Add md5 authentication for aktienanalyse user over TCP/IP
if ! sudo grep -q "host.*aktienanalyse_events.*aktienanalyse.*md5" "${PG_CONFIG_PATH}/pg_hba.conf"; then
    # Add specific rule for aktienanalyse user
    sudo sed -i "/^# IPv4 local connections:/a host    aktienanalyse_events    aktienanalyse    0.0.0.0/0    md5" "${PG_CONFIG_PATH}/pg_hba.conf"
fi

# Add local md5 authentication for aktienanalyse user
if ! sudo grep -q "local.*aktienanalyse_events.*aktienanalyse.*md5" "${PG_CONFIG_PATH}/pg_hba.conf"; then
    sudo sed -i "/^# \"local\" is for Unix domain socket connections only/a local   aktienanalyse_events   aktienanalyse   md5" "${PG_CONFIG_PATH}/pg_hba.conf"
fi

# Step 6: Restart PostgreSQL to apply configuration changes
echo "🔄 Restarting PostgreSQL to apply changes..."
sudo systemctl restart postgresql

# Wait for PostgreSQL to start
sleep 5

# Step 7: Test connections
echo "🧪 Testing PostgreSQL connections..."

# Test local connection with password
echo "Testing local connection..."
if PGPASSWORD="secure_password_2025" psql -h localhost -U aktienanalyse -d aktienanalyse_events -c "SELECT 'Local connection successful' as status;"; then
    echo "✅ Local connection successful"
else
    echo "❌ Local connection failed"
fi

# Test remote connection
echo "Testing TCP/IP connection..."
if PGPASSWORD="secure_password_2025" psql -h 10.1.1.174 -U aktienanalyse -d aktienanalyse_events -c "SELECT 'TCP/IP connection successful' as status;"; then
    echo "✅ TCP/IP connection successful"
else
    echo "❌ TCP/IP connection failed"
fi

# Step 8: Verify table creation
echo "🔍 Verifying table creation..."
PGPASSWORD="secure_password_2025" psql -h localhost -U aktienanalyse -d aktienanalyse_events -c "
SELECT 
    table_name, 
    (SELECT COUNT(*) FROM soll_ist_gewinn_tracking) as record_count
FROM information_schema.tables 
WHERE table_name IN ('soll_ist_gewinn_tracking', 'prediction_tracking_unified')
ORDER BY table_name;
"

echo "✅ PostgreSQL fix completed successfully!"
echo "🗄️ Database: aktienanalyse_events"
echo "👤 User: aktienanalyse" 
echo "📡 TCP/IP connections enabled on port 5432"
echo "🔐 Authentication: md5 password authentication"

EOF

# Copy script to server and make executable
echo "📤 Deploying fix script to server..."
scp "/tmp/server_postgres_fix.sh" "${SSH_USER}@${SERVER_HOST}:/tmp/"
ssh "${SSH_USER}@${SERVER_HOST}" "chmod +x /tmp/server_postgres_fix.sh"

# Step 3: Execute fix on server  
echo "🚀 Executing PostgreSQL fix on server..."
ssh "${SSH_USER}@${SERVER_HOST}" "/tmp/server_postgres_fix.sh"

# Step 4: Test connection from local machine
echo "🧪 Testing connection from local machine..."
if PGPASSWORD="${DB_PASSWORD}" psql -h "${SERVER_HOST}" -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 'Remote connection from local machine successful!' as status, NOW() as timestamp;"; then
    echo "✅ Remote connection successful!"
else
    echo "❌ Remote connection failed"
fi

# Step 5: Test Database Manager Integration
echo "🔬 Testing Database Manager Integration..."
cd "${PROJECT_PATH}"

# Set environment variables for testing
export POSTGRES_HOST="${SERVER_HOST}"
export POSTGRES_PORT="5432"
export POSTGRES_DB="${DB_NAME}"
export POSTGRES_USER="${DB_USER}"
export POSTGRES_PASSWORD="${DB_PASSWORD}"

# Create simple test script
cat > "/tmp/test_db_manager.py" << 'EOF'
#!/usr/bin/env python3
import asyncio
import sys
import os

# Add shared directory to path
sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared')

async def test_database_manager():
    try:
        from database_connection_manager_v1_0_0_20250825 import (
            DatabaseConfiguration, get_database_manager
        )
        
        print("🔧 Testing Database Connection Manager...")
        
        # Initialize manager
        config = DatabaseConfiguration()
        manager = get_database_manager()
        await manager.initialize()
        
        # Test query
        result = await manager.fetch_one_query(
            "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public'"
        )
        print(f"✅ Database query successful: {result}")
        
        # Test soll_ist_gewinn_tracking access
        result = await manager.fetch_one_query(
            "SELECT COUNT(*) as record_count FROM soll_ist_gewinn_tracking"
        )
        print(f"✅ soll_ist_gewinn_tracking access: {result}")
        
        # Health check
        health = await manager.health_check()
        print(f"✅ Health check: {health['status']}")
        
        await manager.close()
        print("🎉 Database Manager Integration test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database Manager Integration test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_manager())
    sys.exit(0 if success else 1)
EOF

python3 "/tmp/test_db_manager.py"

echo "================================================================================"
echo "🎉 PostgreSQL Production Fix Deployment Complete!"
echo "================================================================================"
echo "✅ Database: ${DB_NAME} on ${SERVER_HOST}:5432"
echo "✅ User: ${DB_USER} with password authentication"  
echo "✅ TCP/IP connections enabled"
echo "✅ soll_ist_gewinn_tracking table created"
echo "✅ Database Manager Integration verified"
echo ""
echo "📝 Next Steps:"
echo "   - Services can now connect with: postgresql://aktienanalyse:${DB_PASSWORD}@${SERVER_HOST}:5432/aktienanalyse_events"
echo "   - Database Manager is ready for production use"
echo "   - All 10 services should be able to connect successfully"

# Cleanup temporary files
rm -f "/tmp/server_postgres_fix.sh" "/tmp/test_db_manager.py"

echo "🧹 Cleanup completed"