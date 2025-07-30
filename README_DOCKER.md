# VPBank253 Docker Deployment Guide

This guide explains how to deploy the VPBank253 FastAPI application using Docker on EC2.

## 📋 Prerequisites

### EC2 Instance Requirements
- **OS**: Ubuntu 20.04 LTS or later
- **Instance Type**: t3.medium or larger (recommended: t3.large for production)
- **Storage**: At least 20GB free space
- **Memory**: Minimum 4GB RAM
- **Security Groups**: Open ports 22 (SSH), 80 (HTTP), 443 (HTTPS)

### Software Requirements
- Docker Engine
- Docker Compose
- Git

## 🚀 Quick Start

### 1. Install Docker and Docker Compose

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes to take effect
exit
# SSH back to your instance
```

### 2. Clone and Deploy

```bash
# Clone your repository
git clone <your-repo-url>
cd VPBankHackathon

# Make deployment script executable
chmod +x docker-deploy.sh

# Run deployment
./docker-deploy.sh
```

## 📁 Docker Files Overview

### `Dockerfile`
- **Base Image**: Python 3.11-slim
- **Optimizations**: Multi-stage build, non-root user, health checks
- **Dependencies**: System libraries for FAISS, OpenBLAS, LAPACK
- **Security**: Runs as non-root user

### `docker-compose.yml`
- **Services**: API and Nginx containers
- **Networking**: Custom bridge network
- **Volumes**: Persistent storage for logs and downloads
- **Environment**: AWS credentials and configuration

### `.dockerignore`
- Excludes unnecessary files from build context
- Reduces image size and build time
- Excludes development files and large datasets

## 🔧 Configuration

### Environment Variables

Create a `.env` file in your project root:

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your_actual_access_key
AWS_SECRET_ACCESS_KEY=your_actual_secret_key
AWS_REGION=ap-southeast-1

# Application Settings
PYTHONPATH=/app
```

### Nginx Configuration

Update `nginx.conf` with your domain:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Change this
    
    # ... rest of configuration
}
```

## 🐳 Docker Commands

### Basic Operations

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Rebuild and restart
docker-compose up -d --build
```

### Container Management

```bash
# View running containers
docker ps

# View container logs
docker logs vpbank253-api

# Execute commands in container
docker exec -it vpbank253-api bash

# View resource usage
docker stats
```

### Image Management

```bash
# List images
docker images

# Remove unused images
docker image prune

# Remove all unused resources
docker system prune -a
```

## 🔍 Monitoring and Debugging

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check nginx
curl http://localhost:80

# Check container health
docker-compose ps
```

### Logs

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs vpbank253-api
docker-compose logs nginx

# Follow logs in real-time
docker-compose logs -f
```

### Debugging

```bash
# Access container shell
docker exec -it vpbank253-api bash

# Check environment variables
docker exec vpbank253-api env

# Check file permissions
docker exec vpbank253-api ls -la /app
```

## 🔒 Security Considerations

### Container Security

1. **Non-root User**: Application runs as non-root user
2. **Minimal Base Image**: Uses slim Python image
3. **No Sensitive Data**: AWS credentials passed via environment variables
4. **Health Checks**: Regular health monitoring

### Network Security

```bash
# Configure firewall
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### SSL/TLS Setup

For production, add SSL certificates:

```bash
# Create SSL directory
mkdir -p ssl

# Add your certificates
cp your-cert.pem ssl/
cp your-key.pem ssl/

# Update nginx.conf for SSL
```

## 📈 Performance Optimization

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  vpbank253-api:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
```

### Scaling

```bash
# Scale API service
docker-compose up -d --scale vpbank253-api=3
```

### Monitoring

```bash
# Install monitoring tools
sudo apt install htop iotop

# Monitor system resources
htop
iotop
df -h
```

## 🔄 Updates and Maintenance

### Application Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### System Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Restart Docker
sudo systemctl restart docker

# Restart services
docker-compose restart
```

### Backup

```bash
# Backup configuration
tar -czf backup-$(date +%Y%m%d).tar.gz \
    docker-compose.yml \
    .env \
    nginx.conf \
    s3_downloads/ \
    log/
```

## 🐛 Troubleshooting

### Common Issues

1. **Container won't start**
   ```bash
   # Check logs
   docker-compose logs vpbank253-api
   
   # Check resource usage
   docker stats
   
   # Check disk space
   df -h
   ```

2. **AWS credentials error**
   ```bash
   # Verify .env file
   cat .env
   
   # Test AWS credentials
   docker exec vpbank253-api aws sts get-caller-identity
   ```

3. **Port conflicts**
   ```bash
   # Check what's using port 8000
   sudo netstat -tlnp | grep :8000
   
   # Check what's using port 80
   sudo netstat -tlnp | grep :80
   ```

4. **Memory issues**
   ```bash
   # Check memory usage
   free -h
   
   # Check swap
   swapon --show
   ```

### Performance Issues

1. **Slow startup**
   - Increase EC2 instance size
   - Use SSD storage
   - Optimize Docker layers

2. **High memory usage**
   - Monitor with `docker stats`
   - Adjust resource limits
   - Consider scaling horizontally

3. **Network issues**
   - Check security groups
   - Verify DNS resolution
   - Test connectivity

## 📊 Production Checklist

- [ ] SSL certificates configured
- [ ] Domain name pointing to EC2
- [ ] Firewall rules configured
- [ ] Monitoring set up
- [ ] Backup strategy implemented
- [ ] Log rotation configured
- [ ] Resource limits set
- [ ] Health checks working
- [ ] Error handling tested
- [ ] Performance benchmarks run

## 🆘 Support

For issues:

1. Check logs: `docker-compose logs -f`
2. Verify configuration: `docker-compose config`
3. Test connectivity: `curl http://localhost:8000/health`
4. Check resources: `docker stats` and `htop`

---

**Note**: This deployment is optimized for EC2. For other cloud providers, adjust security groups and networking accordingly. 