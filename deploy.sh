#!/bin/bash

# VPBank253 Deployment Script
# This script sets up the FastAPI app with systemd and nginx

set -e  # Exit on any error

echo "🚀 Starting VPBank253 deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Variables
SERVICE_NAME="vpbank253"
NGINX_SITE_NAME="vpbank253"
APP_DIR="/home/ubuntu/VPBankHackathon"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
NGINX_SITE_FILE="/etc/nginx/sites-available/${NGINX_SITE_NAME}"

print_status "Setting up VPBank253 FastAPI application..."

# 1. Create systemd service file
print_status "Creating systemd service file..."
sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=VPBank253 FastAPI App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --log-level info
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=AWS_ACCESS_KEY_ID=your_aws_access_key
Environment=AWS_SECRET_ACCESS_KEY=your_aws_secret_key
Environment=AWS_REGION=ap-southeast-1

[Install]
WantedBy=multi-user.target
EOF

# 2. Create nginx site configuration
print_status "Creating nginx site configuration..."
sudo tee $NGINX_SITE_FILE > /dev/null <<EOF
server {
    listen 80;
    server_name 13.251.81.237;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Proxy settings for FastAPI app
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Faster timeout for health checks
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;
    }

    # API documentation
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Static files (if any)
    location /static/ {
        alias $APP_DIR/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Logging
    access_log /var/log/nginx/vpbank253_access.log;
    error_log /var/log/nginx/vpbank253_error.log;
}
EOF

# 3. Enable nginx site
print_status "Enabling nginx site..."
sudo ln -sf $NGINX_SITE_FILE /etc/nginx/sites-enabled/

# 4. Test nginx configuration
print_status "Testing nginx configuration..."
sudo nginx -t

# 5. Reload systemd and enable service
print_status "Reloading systemd and enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

# 6. Start the service
print_status "Starting VPBank253 service..."
sudo systemctl start $SERVICE_NAME

# 7. Reload nginx
print_status "Reloading nginx..."
sudo systemctl reload nginx

# 8. Check service status
print_status "Checking service status..."
sleep 3
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    print_status "✅ VPBank253 service is running successfully!"
else
    print_error "❌ VPBank253 service failed to start"
    sudo systemctl status $SERVICE_NAME
    exit 1
fi

# 9. Show useful commands
echo ""
print_status "Deployment completed successfully! 🎉"
echo ""
echo "Useful commands:"
echo "  Check service status: sudo systemctl status $SERVICE_NAME"
echo "  View service logs: sudo journalctl -u $SERVICE_NAME -f"
echo "  Restart service: sudo systemctl restart $SERVICE_NAME"
echo "  Stop service: sudo systemctl stop $SERVICE_NAME"
echo "  View nginx logs: sudo tail -f /var/log/nginx/vpbank253_*.log"
echo ""
echo "Your API is now available at:"
echo "  http://13.251.81.237"
echo "  http://13.251.81.237/docs (API documentation)"
echo "  http://13.251.81.237/health (Health check)"
echo ""

print_warning "Remember to:"
echo "  1. Update AWS credentials in $SERVICE_FILE"
echo "  2. Configure SSL certificate for production"
echo "  3. Set up proper firewall rules"
echo "  4. Monitor logs regularly" 