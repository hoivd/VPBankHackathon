#!/bin/bash

# VPBank253 Docker Deployment Script for EC2
# This script deploys the FastAPI app using Docker and Docker Compose

set -e  # Exit on any error

echo "🐳 Starting VPBank253 Docker deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating template..."
    cat > .env << EOF
# AWS Credentials
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=ap-southeast-1

# Application Settings
PYTHONPATH=/app
EOF
    print_warning "Please update the .env file with your actual AWS credentials before continuing."
    exit 1
fi

# Load environment variables
source .env

# Check if AWS credentials are set
if [ "$AWS_ACCESS_KEY_ID" = "your_aws_access_key_here" ] || [ -z "$AWS_ACCESS_KEY_ID" ]; then
    print_error "Please update AWS_ACCESS_KEY_ID in .env file"
    exit 1
fi

if [ "$AWS_SECRET_ACCESS_KEY" = "your_aws_secret_key_here" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    print_error "Please update AWS_SECRET_ACCESS_KEY in .env file"
    exit 1
fi

print_step "1. Stopping existing containers..."
docker-compose down --remove-orphans

print_step "2. Building Docker image..."
docker-compose build --no-cache

print_step "3. Creating necessary directories..."
mkdir -p s3_downloads/faiss_indexes/personal_faiss_index
mkdir -p log
mkdir -p ssl

print_step "4. Starting services..."
docker-compose up -d

print_step "5. Waiting for services to be ready..."
sleep 30

print_step "6. Checking service health..."

# Check API health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "✅ API is healthy"
else
    print_error "❌ API health check failed"
    docker-compose logs vpbank253-api
    exit 1
fi

# Check nginx
if curl -f http://localhost:80 > /dev/null 2>&1; then
    print_status "✅ Nginx is responding"
else
    print_error "❌ Nginx health check failed"
    docker-compose logs nginx
    exit 1
fi

print_step "7. Deployment completed successfully! 🎉"

echo ""
print_status "Your application is now running at:"
echo "  🌐 API: http://localhost:8000"
echo "  📚 Docs: http://localhost:8000/docs"
echo "  ❤️  Health: http://localhost:8000/health"
echo "  🌍 Web: http://localhost (via nginx)"
echo ""

print_status "Useful Docker commands:"
echo "  📊 View logs: docker-compose logs -f"
echo "  🔄 Restart: docker-compose restart"
echo "  ⏹️  Stop: docker-compose down"
echo "  🚀 Start: docker-compose up -d"
echo "  🏗️  Rebuild: docker-compose build --no-cache"
echo ""

print_status "Container status:"
docker-compose ps

print_warning "Remember to:"
echo "  1. Configure your domain name in nginx.conf"
echo "  2. Set up SSL certificates for production"
echo "  3. Configure firewall rules"
echo "  4. Set up monitoring and logging"
echo ""

# Show container resource usage
print_status "Container resource usage:"
docker stats --no-stream 