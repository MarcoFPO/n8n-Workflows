#!/bin/bash
"""
LXC Deployment Script - Deploy Classical-Enhanced ML Service to 10.1.1.174
===========================================================================

Complete deployment script für LXC Container 10.1.1.174
Installs dependencies, configures services, and starts ML Analytics Service

Author: Claude Code & LXC Deployment Team
Version: 1.0.0
Date: 2025-08-19
"""

set -e  # Exit on error

# Configuration
LXC_IP="10.1.1.174"
SERVICE_NAME="lxc-ml-analytics"
SERVICE_USER="mlservice"
SERVICE_DIR="/opt/ml-analytics-service"
PYTHON_VENV_DIR="/opt/ml-analytics-service/venv"

echo "🔧 LXC ML Analytics Deployment Script"
echo "🔧 Deploying to Container: $LXC_IP"
echo "=" * 60

# Function: Print step
print_step() {
    echo ""
    echo "🔧 STEP: $1"
    echo "----------------------------------------"
}

# Function: Check if we're on the target LXC
check_target_system() {
    print_step "Checking Target System"
    
    # Get current IP
    CURRENT_IP=$(hostname -I | awk '{print $1}')
    echo "Current IP: $CURRENT_IP"
    echo "Target IP: $LXC_IP"
    
    if [[ "$CURRENT_IP" != "$LXC_IP" ]]; then
        echo "⚠️  Warning: Not on target LXC container!"
        echo "   This script should be run on LXC $LXC_IP"
        echo "   Continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "❌ Deployment cancelled."
            exit 1
        fi
    fi
    
    echo "✅ Target system confirmed"
}

# Function: Install system dependencies
install_system_dependencies() {
    print_step "Installing System Dependencies"
    
    # Update package manager
    sudo apt update
    
    # Core Python and development tools
    sudo apt install -y \
        python3-full \
        python3-venv \
        python3-pip \
        python3-dev \
        build-essential \
        curl \
        wget \
        git \
        htop \
        supervisor \
        nginx
    
    # Scientific computing libraries (system level)
    sudo apt install -y \
        python3-numpy \
        python3-scipy \
        python3-pandas \
        python3-sklearn \
        python3-networkx
    
    echo "✅ System dependencies installed"
}

# Function: Create service user and directories
setup_service_user() {
    print_step "Setting up Service User and Directories"
    
    # Create service user
    if ! id "$SERVICE_USER" &>/dev/null; then
        sudo useradd -r -m -s /bin/bash "$SERVICE_USER"
        echo "✅ Service user '$SERVICE_USER' created"
    else
        echo "✅ Service user '$SERVICE_USER' already exists"
    fi
    
    # Create service directories
    sudo mkdir -p "$SERVICE_DIR"
    sudo mkdir -p "$SERVICE_DIR/logs"
    sudo mkdir -p "$SERVICE_DIR/data"
    sudo mkdir -p "$SERVICE_DIR/config"
    
    # Set ownership
    sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$SERVICE_DIR"
    
    echo "✅ Service directories created"
}

# Function: Setup Python virtual environment
setup_python_environment() {
    print_step "Setting up Python Virtual Environment"
    
    # Create virtual environment as service user
    sudo -u "$SERVICE_USER" python3 -m venv "$PYTHON_VENV_DIR"
    
    # Upgrade pip
    sudo -u "$SERVICE_USER" "$PYTHON_VENV_DIR/bin/pip" install --upgrade pip
    
    # Install Python dependencies
    echo "Installing Python packages..."
    sudo -u "$SERVICE_USER" "$PYTHON_VENV_DIR/bin/pip" install \
        fastapi \
        uvicorn[standard] \
        asyncpg \
        redis \
        aiohttp \
        psutil \
        pydantic \
        numpy \
        scipy \
        pandas \
        scikit-learn \
        networkx
    
    echo "✅ Python virtual environment ready"
}

# Function: Deploy ML Analytics Service files
deploy_service_files() {
    print_step "Deploying ML Analytics Service Files"
    
    # Copy service files to deployment directory
    SOURCE_DIR="$(dirname "$0")"
    
    sudo -u "$SERVICE_USER" cp "$SOURCE_DIR/lxc_ml_analytics_service_v1_0_0_20250819.py" "$SERVICE_DIR/"
    sudo -u "$SERVICE_USER" cp "$SOURCE_DIR/quantum_ml_engine_v1_0_0_20250819.py" "$SERVICE_DIR/"
    sudo -u "$SERVICE_USER" cp "$SOURCE_DIR/market_intelligence_engine_v1_0_0_20250819.py" "$SERVICE_DIR/"
    sudo -u "$SERVICE_USER" cp "$SOURCE_DIR/lxc_performance_monitor_v1_0_0_20250819.py" "$SERVICE_DIR/"
    sudo -u "$SERVICE_USER" cp "$SOURCE_DIR/memory_efficient_portfolio_operations_v1_0_0_20250819.py" "$SERVICE_DIR/"
    
    # Create main service script
    sudo tee "$SERVICE_DIR/start_service.py" > /dev/null << EOF
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lxc_ml_analytics_service_v1_0_0_20250819 import main

if __name__ == "__main__":
    main()
EOF
    
    # Make executable
    sudo chmod +x "$SERVICE_DIR/start_service.py"
    sudo chown "$SERVICE_USER:$SERVICE_USER" "$SERVICE_DIR/start_service.py"
    
    echo "✅ Service files deployed"
}

# Function: Create systemd service
create_systemd_service() {
    print_step "Creating Systemd Service"
    
    sudo tee "/etc/systemd/system/$SERVICE_NAME.service" > /dev/null << EOF
[Unit]
Description=LXC ML Analytics Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$SERVICE_DIR
Environment=PATH=$PYTHON_VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$PYTHON_VENV_DIR/bin/python start_service.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Resource limits für LXC
LimitNOFILE=65536
MemoryHigh=1G
MemoryMax=1.5G

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    
    echo "✅ Systemd service created and enabled"
}

# Function: Configure nginx reverse proxy
configure_nginx() {
    print_step "Configuring Nginx Reverse Proxy"
    
    # Create nginx configuration
    sudo tee "/etc/nginx/sites-available/$SERVICE_NAME" > /dev/null << EOF
server {
    listen 8021;
    server_name $LXC_IP localhost;
    
    # API endpoints
    location / {
        proxy_pass http://127.0.0.1:8021;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Increase timeout für ML operations
        proxy_connect_timeout       600;
        proxy_send_timeout          600;
        proxy_read_timeout          600;
        send_timeout                600;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8021/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    # Disable access logs für health checks
    location = /health {
        access_log off;
        proxy_pass http://127.0.0.1:8021/health;
    }
}
EOF
    
    # Enable site
    sudo ln -sf "/etc/nginx/sites-available/$SERVICE_NAME" "/etc/nginx/sites-enabled/"
    
    # Test nginx configuration
    sudo nginx -t
    
    # Restart nginx
    sudo systemctl restart nginx
    
    echo "✅ Nginx reverse proxy configured"
}

# Function: Start services
start_services() {
    print_step "Starting Services"
    
    # Start ML Analytics Service
    sudo systemctl start "$SERVICE_NAME"
    sudo systemctl status "$SERVICE_NAME" --no-pager
    
    # Wait for service to start
    echo "⏳ Waiting for service to start..."
    sleep 10
    
    # Check if service is running
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "✅ ML Analytics Service is running"
    else
        echo "❌ ML Analytics Service failed to start"
        sudo journalctl -u "$SERVICE_NAME" -n 20 --no-pager
        exit 1
    fi
    
    echo "✅ All services started successfully"
}

# Function: Run deployment tests
run_deployment_tests() {
    print_step "Running Deployment Tests"
    
    # Test health endpoint
    echo "Testing health endpoint..."
    if curl -f "http://localhost:8021/health" > /dev/null 2>&1; then
        echo "✅ Health endpoint responding"
    else
        echo "❌ Health endpoint not responding"
        return 1
    fi
    
    # Test API endpoints
    echo "Testing Classical-Enhanced ML status endpoint..."
    if curl -f "http://localhost:8021/api/v1/classical-enhanced/status" > /dev/null 2>&1; then
        echo "✅ Classical-Enhanced ML API responding"
    else
        echo "❌ Classical-Enhanced ML API not responding"
        return 1
    fi
    
    echo "✅ Deployment tests passed"
}

# Function: Display deployment summary
display_summary() {
    print_step "Deployment Summary"
    
    echo "🎉 LXC ML Analytics Service Deployment Complete!"
    echo ""
    echo "📍 Service Details:"
    echo "   • Container IP: $LXC_IP"
    echo "   • Service Port: 8021"
    echo "   • Service User: $SERVICE_USER"
    echo "   • Service Directory: $SERVICE_DIR"
    echo "   • Python Environment: $PYTHON_VENV_DIR"
    echo ""
    echo "🔧 Service Management:"
    echo "   • Start: sudo systemctl start $SERVICE_NAME"
    echo "   • Stop: sudo systemctl stop $SERVICE_NAME"
    echo "   • Status: sudo systemctl status $SERVICE_NAME"
    echo "   • Logs: sudo journalctl -u $SERVICE_NAME -f"
    echo ""
    echo "🌐 API Endpoints:"
    echo "   • Health Check: http://$LXC_IP:8021/health"
    echo "   • ML Status: http://$LXC_IP:8021/api/v1/classical-enhanced/status"
    echo "   • Portfolio Opt: http://$LXC_IP:8021/api/v1/classical-enhanced/vce/portfolio-optimization"
    echo ""
    echo "✅ Ready für production use!"
}

# Main deployment workflow
main() {
    echo "🚀 Starting LXC ML Analytics Deployment"
    
    check_target_system
    install_system_dependencies
    setup_service_user
    setup_python_environment
    deploy_service_files
    create_systemd_service
    # configure_nginx  # Skip nginx für direct deployment
    start_services
    run_deployment_tests
    display_summary
    
    echo "🎉 LXC ML Analytics Service Successfully Deployed!"
}

# Run main function
main "$@"