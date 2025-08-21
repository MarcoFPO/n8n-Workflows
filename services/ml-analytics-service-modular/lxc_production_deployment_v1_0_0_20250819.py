#!/usr/bin/env python3
"""
LXC Production Deployment Script - Deploy to 10.1.1.174
=======================================================

Automated deployment script für LXC Container 10.1.1.174
Transfers service files and starts production ML Analytics Service

Author: Claude Code & Production Team
Version: 1.0.0
Date: 2025-08-19
"""

import subprocess
import sys
import os
import time
from pathlib import Path

class LXCProductionDeployment:
    """Production deployment für LXC Container 10.1.1.174"""
    
    def __init__(self):
        self.lxc_ip = "10.1.1.174"
        self.lxc_user = "root"
        self.service_port = 8021
        self.service_name = "lxc-ml-analytics"
        
        # Deployment files
        self.deployment_files = [
            "minimal_lxc_service_v1_0_0_20250819.py",
            "quantum_ml_engine_v1_0_0_20250819.py",
            "market_intelligence_engine_v1_0_0_20250819.py",
            "lxc_performance_monitor_v1_0_0_20250819.py",
            "memory_efficient_portfolio_operations_v1_0_0_20250819.py"
        ]
        
        self.remote_path = "/opt/ml-analytics"
        
    def check_lxc_connectivity(self):
        """Check if LXC container is reachable"""
        print(f"🔍 Checking connectivity to LXC {self.lxc_ip}...")
        
        try:
            result = subprocess.run(
                ["ping", "-c", "2", self.lxc_ip],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"✅ LXC {self.lxc_ip} is reachable")
                return True
            else:
                print(f"❌ LXC {self.lxc_ip} is not reachable")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"❌ Timeout connecting to LXC {self.lxc_ip}")
            return False
        except Exception as e:
            print(f"❌ Error checking connectivity: {str(e)}")
            return False
    
    def prepare_deployment_files(self):
        """Prepare deployment files locally"""
        print("📦 Preparing deployment files...")
        
        missing_files = []
        for file in self.deployment_files:
            if not Path(file).exists():
                missing_files.append(file)
        
        if missing_files:
            print(f"❌ Missing deployment files: {missing_files}")
            return False
        
        print(f"✅ All {len(self.deployment_files)} deployment files ready")
        return True
    
    def transfer_files_to_lxc(self):
        """Transfer files to LXC container"""
        print(f"📤 Transferring files to LXC {self.lxc_ip}...")
        
        try:
            # Create remote directory
            subprocess.run([
                "ssh", f"{self.lxc_user}@{self.lxc_ip}", 
                f"mkdir -p {self.remote_path}"
            ], check=True)
            
            # Transfer each file
            for file in self.deployment_files:
                print(f"   Transferring {file}...")
                subprocess.run([
                    "scp", file, 
                    f"{self.lxc_user}@{self.lxc_ip}:{self.remote_path}/"
                ], check=True)
            
            print(f"✅ Files transferred to {self.remote_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ File transfer failed: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during transfer: {str(e)}")
            return False
    
    def setup_lxc_environment(self):
        """Setup Python environment on LXC"""
        print("🔧 Setting up LXC environment...")
        
        try:
            # Install basic dependencies
            setup_commands = [
                "apt update",
                "apt install -y python3 python3-pip",
                f"chmod +x {self.remote_path}/minimal_lxc_service_v1_0_0_20250819.py"
            ]
            
            for cmd in setup_commands:
                print(f"   Running: {cmd}")
                subprocess.run([
                    "ssh", f"{self.lxc_user}@{self.lxc_ip}", cmd
                ], check=True)
            
            print("✅ LXC environment setup complete")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Environment setup failed: {str(e)}")
            return False
    
    def start_service_on_lxc(self):
        """Start ML Analytics Service on LXC"""
        print("🚀 Starting ML Analytics Service on LXC...")
        
        try:
            # Start service in background
            start_cmd = f"cd {self.remote_path} && python3 minimal_lxc_service_v1_0_0_20250819.py"
            
            subprocess.run([
                "ssh", f"{self.lxc_user}@{self.lxc_ip}", 
                f"nohup {start_cmd} > ml-service.log 2>&1 &"
            ], check=True)
            
            print(f"✅ Service started on LXC {self.lxc_ip}:{self.service_port}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Service start failed: {str(e)}")
            return False
    
    def verify_deployment(self):
        """Verify deployment by testing endpoints"""
        print("🔍 Verifying deployment...")
        
        # Wait for service to start
        print("   Waiting 15 seconds for service to start...")
        time.sleep(15)
        
        try:
            # Test health endpoint
            health_url = f"http://{self.lxc_ip}:{self.service_port}/health"
            result = subprocess.run([
                "curl", "-f", "--connect-timeout", "10", health_url
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Health endpoint responding at {health_url}")
                
                # Test ML status endpoint
                status_url = f"http://{self.lxc_ip}:{self.service_port}/api/v1/classical-enhanced/status"
                result = subprocess.run([
                    "curl", "-f", "--connect-timeout", "10", status_url
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"✅ ML Status endpoint responding at {status_url}")
                    return True
                else:
                    print(f"❌ ML Status endpoint not responding")
                    return False
            else:
                print(f"❌ Health endpoint not responding")
                return False
                
        except Exception as e:
            print(f"❌ Deployment verification failed: {str(e)}")
            return False
    
    def display_deployment_summary(self):
        """Display deployment summary"""
        print("\n" + "=" * 70)
        print("🎉 LXC PRODUCTION DEPLOYMENT COMPLETE!")
        print("=" * 70)
        print(f"📍 Container IP: {self.lxc_ip}")
        print(f"🔧 Service Port: {self.service_port}")
        print(f"📁 Remote Path: {self.remote_path}")
        print(f"👤 User: {self.lxc_user}")
        print("\n🌐 Production Endpoints:")
        print(f"   • Health: http://{self.lxc_ip}:{self.service_port}/health")
        print(f"   • Status: http://{self.lxc_ip}:{self.service_port}/api/v1/classical-enhanced/status")
        print(f"   • VCE:    http://{self.lxc_ip}:{self.service_port}/api/v1/classical-enhanced/vce/portfolio-optimization")
        print(f"   • QIAOA:  http://{self.lxc_ip}:{self.service_port}/api/v1/classical-enhanced/qiaoa/optimization")
        print("\n🔧 Management Commands:")
        print(f"   • SSH:    ssh {self.lxc_user}@{self.lxc_ip}")
        print(f"   • Logs:   ssh {self.lxc_user}@{self.lxc_ip} 'tail -f {self.remote_path}/ml-service.log'")
        print(f"   • Status: ssh {self.lxc_user}@{self.lxc_ip} 'ps aux | grep python3'")
        print("\n✅ Production ML Analytics Service is live!")
    
    def deploy(self):
        """Execute full deployment workflow"""
        print("🚀 Starting LXC Production Deployment...")
        print(f"🔧 Target: LXC Container {self.lxc_ip}")
        print("=" * 50)
        
        # Deployment steps
        steps = [
            ("Connectivity Check", self.check_lxc_connectivity),
            ("Prepare Files", self.prepare_deployment_files),
            ("Transfer Files", self.transfer_files_to_lxc),
            ("Setup Environment", self.setup_lxc_environment),
            ("Start Service", self.start_service_on_lxc),
            ("Verify Deployment", self.verify_deployment)
        ]
        
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            if not step_func():
                print(f"❌ Deployment failed at step: {step_name}")
                return False
        
        self.display_deployment_summary()
        return True

def main():
    """Main deployment function"""
    print("🔧 LXC Production Deployment Script")
    print("🔧 Classical-Enhanced ML Analytics Service")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("minimal_lxc_service_v1_0_0_20250819.py").exists():
        print("❌ Deployment files not found in current directory")
        print("   Please run this script from the ml-analytics-service-modular directory")
        sys.exit(1)
    
    # Initialize deployment
    deployment = LXCProductionDeployment()
    
    # Ask for confirmation
    print(f"🔍 Ready to deploy to LXC {deployment.lxc_ip}")
    response = input("   Continue with deployment? (y/N): ")
    
    if response.lower() != 'y':
        print("❌ Deployment cancelled by user")
        sys.exit(0)
    
    # Execute deployment
    success = deployment.deploy()
    
    if success:
        print("\n🎉 DEPLOYMENT SUCCESSFUL!")
        sys.exit(0)
    else:
        print("\n❌ DEPLOYMENT FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()