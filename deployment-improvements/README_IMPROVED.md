# FOGIS Deployment System - Improved

This improved deployment system eliminates the manual troubleshooting steps and provides a streamlined, automated deployment experience.

## 🚀 Quick Start (5-Minute Setup)

### Option 1: Automated Deployment (Recommended)
```bash
# Clone and deploy in one command
curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/quick-deploy.sh | bash
```

### Option 2: Manual Deployment
```bash
# 1. Clone repository
git clone https://github.com/PitchConnect/fogis-deployment.git
cd fogis-deployment

# 2. Run automated deployment
python3 deployment-improvements/deploy_fogis.py
```

## 📋 Prerequisites

The deployment script will automatically check and guide you through installing:

- **Docker Desktop** (includes Docker Compose)
- **Git**
- **Python 3.8+**
- **FOGIS Account** (username/password)
- **Google Cloud Project** (for OAuth)

## 🔧 What's New in the Improved System

### ✅ Problems Solved

| **Previous Issue** | **Solution Implemented** |
|-------------------|-------------------------|
| Environment variables not working | Enhanced configuration system with validation |
| Docker cache issues causing stale builds | Smart build system with cache management |
| Manual health checking | Automated validation and monitoring |
| Complex setup process | Interactive setup wizard |
| Difficult troubleshooting | Comprehensive error diagnosis |
| Restart loops in services | Fixed persistent service mode |

### 🆕 New Features

1. **Enhanced Configuration System**
   - Automatic validation of all environment variables
   - Clear error messages for configuration issues
   - Type conversion and validation
   - Configuration export for debugging

2. **Smart Build System**
   - Intelligent cache invalidation
   - Parallel builds for efficiency
   - Build validation and testing
   - Automatic cleanup of old images

3. **Setup Wizard**
   - Interactive guided setup
   - Automatic dependency checking
   - Configuration file generation
   - Progress tracking

4. **Validation System**
   - Comprehensive health checking
   - Service interaction testing
   - Performance monitoring
   - Continuous monitoring capabilities

5. **Master Deployment Script**
   - Orchestrates complete deployment
   - Progress tracking and reporting
   - Automatic issue diagnosis
   - Rollback capabilities

## 📖 Detailed Setup Guide

### Step 1: Environment Setup

The setup wizard will guide you through:

```bash
python3 deployment-improvements/setup_wizard.py
```

This will:
- ✅ Check Docker installation
- ✅ Validate FOGIS credentials
- ✅ Setup Google OAuth
- ✅ Generate configuration files
- ✅ Test service connectivity

### Step 2: Configuration

The enhanced configuration system provides:

```bash
# Test configuration
python3 deployment-improvements/enhanced_config_system.py

# Example output:
✅ Configuration loaded successfully!
Run mode: service
Health server: 0.0.0.0:8000
```

### Step 3: Build Services

Smart build system with caching:

```bash
# Build all services
python3 deployment-improvements/smart_build_system.py --all

# Build specific service
python3 deployment-improvements/smart_build_system.py --service match-list-change-detector

# Force rebuild (bypass cache)
python3 deployment-improvements/smart_build_system.py --all --force
```

### Step 4: Deploy

```bash
# Complete deployment
python3 deployment-improvements/deploy_fogis.py

# Skip phases if needed
python3 deployment-improvements/deploy_fogis.py --skip-setup --skip-build
```

### Step 5: Validate

```bash
# Quick validation
python3 deployment-improvements/validation_system.py

# Comprehensive validation
python3 deployment-improvements/validation_system.py --comprehensive

# Continuous monitoring
python3 deployment-improvements/validation_system.py --monitor 60
```

## 🔍 Monitoring and Troubleshooting

### Health Monitoring

```bash
# Check all services
curl http://localhost:9080/health  # match-list-change-detector
curl http://localhost:9082/health  # match-list-processor
curl http://localhost:9083/health  # calendar-sync
curl http://localhost:9084/health  # google-drive
curl http://localhost:9085/health  # team-logo-combiner

# Automated health checking
python3 deployment-improvements/validation_system.py
```

### Service Management

```bash
# View service status
docker-compose -f docker-compose.yml ps

# View logs
docker-compose -f docker-compose.yml logs -f

# Restart specific service
docker-compose -f docker-compose.yml restart match-list-change-detector

# Scale services
docker-compose -f docker-compose.yml up -d --scale match-list-processor=2
```

### Troubleshooting Common Issues

#### Issue: Service Won't Start
```bash
# Check logs
docker logs <service-name>

# Check configuration
python3 deployment-improvements/enhanced_config_system.py

# Rebuild service
python3 deployment-improvements/smart_build_system.py --service <service-name> --force
```

#### Issue: Environment Variables Not Working
```bash
# Validate configuration
python3 deployment-improvements/enhanced_config_system.py

# Check .env file
cat .env

# Re-run setup
python3 deployment-improvements/setup_wizard.py
```

#### Issue: Services Can't Communicate
```bash
# Check network
docker network ls
docker network inspect fogis-deployment_fogis-network

# Test connectivity
python3 deployment-improvements/validation_system.py --comprehensive
```

## 📊 Performance Monitoring

### Resource Usage
```bash
# Monitor resource usage
docker stats

# Automated resource monitoring
python3 deployment-improvements/validation_system.py --monitor 30
```

### Service Metrics
```bash
# Get service metrics
curl http://localhost:9080/health | jq '.uptime_seconds, .execution_count'

# Performance validation
python3 deployment-improvements/validation_system.py --comprehensive
```

## 🔄 Maintenance

### Regular Maintenance Tasks

```bash
# Clean up old Docker images
python3 deployment-improvements/smart_build_system.py --cleanup

# Update services
git pull
python3 deployment-improvements/deploy_fogis.py --skip-setup

# Backup configuration
cp .env .env.backup
cp -r credentials credentials.backup
```

### Automated Maintenance

```bash
# Set up cron job for monitoring
echo "0 * * * * cd /path/to/fogis-deployment && python3 deployment-improvements/validation_system.py >> monitoring.log 2>&1" | crontab -
```

## 🆘 Support and Troubleshooting

### Getting Help

1. **Check the validation system first:**
   ```bash
   python3 deployment-improvements/validation_system.py --comprehensive
   ```

2. **Review deployment logs:**
   ```bash
   docker-compose -f docker-compose.yml logs
   ```

3. **Run diagnostics:**
   ```bash
   python3 deployment-improvements/setup_wizard.py
   ```

### Common Solutions

| **Problem** | **Solution** |
|-------------|--------------|
| Services won't start | Check Docker is running, validate .env file |
| Environment variables ignored | Use enhanced config system, rebuild containers |
| Build failures | Clear Docker cache, check Dockerfile syntax |
| Network issues | Restart Docker, check firewall settings |
| Performance issues | Monitor resources, scale services |

### Emergency Recovery

```bash
# Complete reset
docker-compose -f docker-compose.yml down
docker system prune -f
python3 deployment-improvements/deploy_fogis.py

# Restore from backup
cp .env.backup .env
cp -r credentials.backup credentials
python3 deployment-improvements/deploy_fogis.py --skip-setup
```

## 📈 Advanced Configuration

### Custom Service Configuration

```python
# Example: Custom match-list-change-detector config
from deployment-improvements.enhanced_config_system import ConfigField, EnhancedConfig

custom_config = [
    ConfigField("CUSTOM_SETTING", "default_value", description="Custom setting"),
    # ... other fields
]

config = EnhancedConfig("my-service", custom_config)
```

### Performance Tuning

```yaml
# docker-compose.yml
services:
  match-list-change-detector:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

## 🔮 Future Enhancements

The improved system provides a foundation for:

- **Kubernetes deployment** support
- **Multi-environment** management (dev/staging/prod)
- **Advanced monitoring** with Prometheus/Grafana
- **Automated scaling** based on workload
- **CI/CD integration** with GitHub Actions
- **Backup and disaster recovery** automation

---

## 📞 Support

For issues not covered by this guide:

1. Check the [troubleshooting section](#-support-and-troubleshooting)
2. Run the validation system for diagnostics
3. Review service logs for specific error messages
4. Create an issue with the validation system output

**Remember**: The improved system is designed to be self-diagnosing and self-healing. Most issues can be resolved by running the appropriate automation script.
