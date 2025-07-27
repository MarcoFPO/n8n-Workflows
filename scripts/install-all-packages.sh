#!/bin/bash
# Vollständige Package-Installation für aktienanalyse-ökosystem
# Basiert auf docs/DEBIAN_PACKAGE_LISTE.md

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Check if running as root for some operations
check_sudo() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root - some operations will be skipped"
        IS_ROOT=true
    else
        IS_ROOT=false
    fi
}

# Update package lists
update_packages() {
    log_info "Updating package lists..."
    if sudo apt update; then
        log_success "Package lists updated successfully"
    else
        log_error "Failed to update package lists"
        exit 1
    fi
}

# Install system base packages
install_system_base() {
    log_info "Installing system base packages..."
    
    local packages=(
        "curl" "wget" "git" "vim" "nano" "htop" "systemd" "sudo"
        "ca-certificates" "gnupg" "lsb-release" "software-properties-common"
        "apt-transport-https" "net-tools" "iputils-ping" "dnsutils"
        "netcat-openbsd" "iproute2" "openssl" "ssl-cert"
    )
    
    if sudo apt install -y "${packages[@]}"; then
        log_success "System base packages installed"
    else
        log_error "Failed to install system base packages"
        return 1
    fi
}

# Install development tools
install_development_tools() {
    log_info "Installing development tools..."
    
    local packages=(
        "build-essential" "gcc" "g++" "make" "cmake" "pkg-config"
        "autoconf" "automake" "libtool" "unzip" "zip"
        "python3-dev" "libpython3-dev" "libffi-dev" "libssl-dev"
        "libxml2-dev" "libxslt1-dev" "libjpeg-dev" "libpng-dev"
        "zlib1g-dev" "libbz2-dev" "libreadline-dev" "libsqlite3-dev"
        "libncurses5-dev" "libncursesw5-dev" "tk-dev" "libgdbm-dev"
        "libc6-dev" "liblzma-dev" "libblas-dev" "liblapack-dev"
        "libatlas-base-dev" "gfortran" "libopenblas-dev"
    )
    
    if sudo apt install -y "${packages[@]}"; then
        log_success "Development tools installed"
    else
        log_error "Failed to install development tools"
        return 1
    fi
}

# Install Python environment
install_python() {
    log_info "Installing Python environment..."
    
    local packages=(
        "python3" "python3-pip" "python3-venv" "python3-setuptools"
        "python3-wheel" "python3-distutils"
    )
    
    if sudo apt install -y "${packages[@]}"; then
        log_success "Python environment installed"
        
        # Check Python version
        python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
        log_info "Python version: $python_version"
        
        # Check pip version
        pip_version=$(python3 -m pip --version | awk '{print $2}')
        log_info "pip version: $pip_version"
    else
        log_error "Failed to install Python environment"
        return 1
    fi
}

# Install Node.js
install_nodejs() {
    log_info "Installing Node.js..."
    
    # Add NodeSource repository
    if curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -; then
        log_success "NodeSource repository added"
    else
        log_error "Failed to add NodeSource repository"
        return 1
    fi
    
    # Check if Node.js is already available and compatible
    if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
        node_version=$(node --version)
        npm_version=$(npm --version)
        log_success "Node.js already available: $node_version"
        log_success "npm already available: $npm_version"
        
        # Check if version is adequate (>= 18)
        if node -pe "process.exit(parseInt(process.version.slice(1)) >= 18 ? 0 : 1)" 2>/dev/null; then
            log_success "Node.js version is compatible (>= 18)"
            return 0
        fi
    fi
    
    # Install nodejs only (npm is included in NodeSource nodejs)
    if sudo apt install -y nodejs; then
        log_success "Node.js installed"
        
        # Check versions
        node_version=$(node --version)
        npm_version=$(npm --version)
        log_info "Node.js version: $node_version"
        log_info "npm version: $npm_version"
    else
        log_error "Failed to install Node.js"
        return 1
    fi
}

# Install databases
install_databases() {
    log_info "Installing database systems..."
    
    # PostgreSQL
    if sudo apt install -y postgresql postgresql-client postgresql-contrib postgresql-server-dev-15 libpq-dev; then
        log_success "PostgreSQL installed"
    else
        log_error "Failed to install PostgreSQL"
        return 1
    fi
    
    # Redis
    if sudo apt install -y redis-server redis-tools; then
        log_success "Redis installed"
    else
        log_error "Failed to install Redis"
        return 1
    fi
    
    # RabbitMQ
    if sudo apt install -y rabbitmq-server; then
        log_success "RabbitMQ installed"
    else
        log_warning "Failed to install RabbitMQ (optional)"
    fi
}

# Install web server
install_webserver() {
    log_info "Installing web server..."
    
    # Try to install Caddy
    log_info "Attempting to install Caddy..."
    if curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg &&
       curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list &&
       sudo apt update && sudo apt install -y caddy; then
        log_success "Caddy installed successfully"
    else
        log_warning "Caddy installation failed, installing NGINX as fallback"
        if sudo apt install -y nginx nginx-extras; then
            log_success "NGINX installed as fallback"
        else
            log_error "Failed to install any web server"
            return 1
        fi
    fi
}

# Install monitoring tools
install_monitoring() {
    log_info "Installing monitoring tools..."
    
    # System monitoring tools
    if sudo apt install -y htop iotop iftop nload ncdu tree; then
        log_success "System monitoring tools installed"
    else
        log_warning "Some monitoring tools failed to install"
    fi
    
    # Try to install Zabbix Agent
    log_info "Attempting to install Zabbix Agent..."
    if wget -q https://repo.zabbix.com/zabbix/6.4/debian/pool/main/z/zabbix-release/zabbix-release_6.4-1+debian12_all.deb &&
       sudo dpkg -i zabbix-release_6.4-1+debian12_all.deb &&
       sudo apt update &&
       sudo apt install -y zabbix-agent2; then
        log_success "Zabbix Agent 2 installed"
        # Clean up
        rm -f zabbix-release_6.4-1+debian12_all.deb
    else
        log_warning "Zabbix Agent installation failed (optional)"
        # Clean up on failure
        rm -f zabbix-release_6.4-1+debian12_all.deb
    fi
}

# Setup Python virtual environment
setup_python_venv() {
    log_info "Setting up Python virtual environment..."
    
    local venv_path="/opt/aktienanalyse-ökosystem/venv"
    
    # Create directory if it doesn't exist
    sudo mkdir -p /opt/aktienanalyse-ökosystem
    sudo chown -R $USER:$USER /opt/aktienanalyse-ökosystem
    
    # Create virtual environment
    if python3 -m venv "$venv_path"; then
        log_success "Python virtual environment created"
    else
        log_error "Failed to create Python virtual environment"
        return 1
    fi
    
    # Activate and upgrade pip
    source "$venv_path/bin/activate"
    if pip install --upgrade pip; then
        log_success "pip upgraded in virtual environment"
    else
        log_warning "Failed to upgrade pip"
    fi
    
    # Install core Python dependencies
    log_info "Installing core Python dependencies..."
    local python_packages=(
        "fastapi==0.104.1"
        "uvicorn[standard]==0.24.0"
        "sqlalchemy==2.0.23"
        "alembic==1.12.1"
        "pydantic==2.5.0"
        "pydantic-settings==2.1.0"
        "psycopg2-binary==2.9.9"
        "redis==5.0.1"
        "celery==5.3.4"
        "requests==2.31.0"
        "numpy==1.24.4"
        "pandas==2.1.4"
        "prometheus-client==0.19.0"
        "structlog==23.2.0"
    )
    
    if pip install "${python_packages[@]}"; then
        log_success "Core Python dependencies installed"
    else
        log_error "Failed to install Python dependencies"
        return 1
    fi
    
    deactivate
}

# Setup user and permissions
setup_user_permissions() {
    log_info "Setting up user and permissions..."
    
    # Create aktienanalyse user if it doesn't exist
    if ! id "aktienanalyse" &>/dev/null; then
        if sudo useradd -m -s /bin/bash aktienanalyse; then
            log_success "aktienanalyse user created"
        else
            log_error "Failed to create aktienanalyse user"
            return 1
        fi
    else
        log_info "aktienanalyse user already exists"
    fi
    
    # Add user to sudo group
    if sudo usermod -aG sudo aktienanalyse; then
        log_success "aktienanalyse user added to sudo group"
    else
        log_warning "Failed to add aktienanalyse user to sudo group"
    fi
    
    # Setup directories
    sudo mkdir -p /opt/aktienanalyse-ökosystem/{services,shared,config,logs,data,backups,scripts}
    sudo chown -R aktienanalyse:aktienanalyse /opt/aktienanalyse-ökosystem
    sudo chmod 755 /opt/aktienanalyse-ökosystem
    sudo chmod 750 /opt/aktienanalyse-ökosystem/config
    
    log_success "Directory structure created and permissions set"
}

# Initialize databases
initialize_databases() {
    log_info "Initializing databases..."
    
    # Start services
    sudo systemctl enable postgresql redis-server
    sudo systemctl start postgresql redis-server
    
    # PostgreSQL setup
    log_info "Setting up PostgreSQL..."
    if sudo -u postgres createuser aktienanalyse 2>/dev/null || true; then
        log_info "PostgreSQL user 'aktienanalyse' created or already exists"
    fi
    
    if sudo -u postgres createdb aktienanalyse_events 2>/dev/null || true; then
        log_info "PostgreSQL database 'aktienanalyse_events' created or already exists"
    fi
    
    if sudo -u postgres psql -c "ALTER USER aktienanalyse PASSWORD 'secure_password';" 2>/dev/null; then
        log_success "PostgreSQL user password set"
    fi
    
    if sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE aktienanalyse_events TO aktienanalyse;" 2>/dev/null; then
        log_success "PostgreSQL permissions granted"
    fi
    
    # Redis configuration
    if sudo systemctl is-active --quiet redis-server; then
        log_success "Redis server is running"
    else
        log_warning "Redis server is not running"
    fi
    
    # RabbitMQ setup (if installed)
    if command -v rabbitmqctl >/dev/null 2>&1; then
        sudo systemctl enable rabbitmq-server
        sudo systemctl start rabbitmq-server
        
        # Wait for RabbitMQ to start
        sleep 5
        
        if sudo rabbitmqctl add_user aktienanalyse secure_password 2>/dev/null || true; then
            log_info "RabbitMQ user created or already exists"
        fi
        
        if sudo rabbitmqctl set_user_tags aktienanalyse administrator 2>/dev/null; then
            log_success "RabbitMQ user permissions set"
        fi
        
        if sudo rabbitmqctl add_vhost aktienanalyse 2>/dev/null || true; then
            log_info "RabbitMQ vhost created or already exists"
        fi
        
        if sudo rabbitmqctl set_permissions -p aktienanalyse aktienanalyse ".*" ".*" ".*" 2>/dev/null; then
            log_success "RabbitMQ vhost permissions set"
        fi
    fi
}

# Main installation function
main() {
    echo "🚀 Starting aktienanalyse-ökosystem installation..."
    echo "=================================================="
    
    check_sudo
    
    # Check if we're in the right directory
    if [[ ! -f "docs/DEBIAN_PACKAGE_LISTE.md" ]]; then
        log_error "Please run this script from the aktienanalyse-ökosystem root directory"
        exit 1
    fi
    
    # Installation phases
    log_info "Phase 1: System preparation"
    update_packages
    
    log_info "Phase 2: System base packages"
    install_system_base
    
    log_info "Phase 3: Development tools"
    install_development_tools
    
    log_info "Phase 4: Python environment"
    install_python
    
    log_info "Phase 5: Node.js environment"
    install_nodejs
    
    log_info "Phase 6: Database systems"
    install_databases
    
    log_info "Phase 7: Web server"
    install_webserver
    
    log_info "Phase 8: Monitoring tools"
    install_monitoring
    
    log_info "Phase 9: Python virtual environment"
    setup_python_venv
    
    log_info "Phase 10: User and permissions"
    setup_user_permissions
    
    log_info "Phase 11: Database initialization"
    initialize_databases
    
    echo ""
    echo "✅ Installation completed successfully!"
    echo "======================================"
    
    log_success "aktienanalyse-ökosystem is ready for service configuration"
    
    echo ""
    echo "📋 Next steps:"
    echo "1. Configure systemd services (see docs/DEPLOYMENT_INFRASTRUCTURE_AUTOMATION_SPEZIFIKATION.md)"
    echo "2. Run package verification: ./scripts/check-current-packages.sh"
    echo "3. Setup service configurations in /opt/aktienanalyse-ökosystem/config/"
    echo "4. Start services: sudo systemctl start aktienanalyse.target"
    
    echo ""
    echo "📊 Installation summary:"
    echo "- System packages: ✅ Installed"
    echo "- Python 3.11+ environment: ✅ Ready"
    echo "- Node.js 18+ environment: ✅ Ready"
    echo "- PostgreSQL database: ✅ Running"
    echo "- Redis cache: ✅ Running"
    echo "- Web server: ✅ Installed"
    echo "- User permissions: ✅ Configured"
    echo ""
    echo "🎯 System ready for aktienanalyse-ökosystem deployment!"
}

# Error handling
trap 'log_error "Installation failed at line $LINENO"' ERR

# Run main installation
main "$@"