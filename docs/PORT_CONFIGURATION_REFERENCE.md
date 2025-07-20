# Port Configuration Reference

This document provides a comprehensive reference for all port configurations across FOGIS services to ensure consistency and prevent deployment confusion.

## 🚢 Service Port Mappings

### **Calendar Service (fogis-calendar-phonebook-sync)**

| Component | Port | Purpose | Status |
|-----------|------|---------|--------|
| **Application Default** | 5003 | Flask app internal port | ✅ **Standard** |
| **Dockerfile EXPOSE** | 5003 | Container port exposure | ✅ **Consistent** |
| **Host Port** | 9083 | External access (API) | ✅ **Production** |
| **Port Mapping** | `9083:5003` | docker-compose mapping | ✅ **Correct** |
| **Health Check** | 5003 | Internal health endpoint | ✅ **Aligned** |

**Environment Variables**:
```yaml
- FLASK_HOST=0.0.0.0    # Bind to all interfaces
- FLASK_PORT=5003       # Explicit port configuration
```

**Access URLs**:
- **Health Check**: `http://localhost:9083/health`
- **API Endpoints**: `http://localhost:9083/*`
- **Internal (container)**: `http://fogis-calendar-phonebook-sync:5003/*`

### **Google Drive Service**

| Component | Port | Purpose | Status |
|-----------|------|---------|--------|
| **Application Default** | 5000 | Flask app internal port | ✅ **Standard** |
| **Dockerfile EXPOSE** | 5000 | Container port exposure | ✅ **Consistent** |
| **Host Port** | 9085 | External access (API) | ✅ **Production** |
| **Port Mapping** | `9085:5000` | docker-compose mapping | ✅ **Correct** |
| **Health Check** | 5000 | Internal health endpoint | ✅ **Aligned** |

**Environment Variables**:
```yaml
- FLASK_HOST=0.0.0.0    # Bind to all interfaces
- FLASK_PORT=5000       # Explicit port configuration
```

### **FOGIS API Client Service**

| Component | Port | Purpose | Status |
|-----------|------|---------|--------|
| **Application Default** | 8080 | FastAPI internal port | ✅ **Standard** |
| **Host Port** | 9086 | External access (API) | ✅ **Production** |
| **Port Mapping** | `9086:8080` | docker-compose mapping | ✅ **Correct** |

### **Match List Processor**

| Component | Port | Purpose | Status |
|-----------|------|---------|--------|
| **Application Default** | 8000 | Health/webhook endpoints | ✅ **Standard** |
| **Host Port** | 9082 | External access | ✅ **Production** |
| **Port Mapping** | `9082:8000` | docker-compose mapping | ✅ **Correct** |

### **Team Logo Combiner**

| Component | Port | Purpose | Status |
|-----------|------|---------|--------|
| **Application Default** | 5002 | Flask app internal port | ✅ **Standard** |
| **Host Port** | 9088 | External access (API) | ✅ **Production** |
| **Port Mapping** | `9088:5002` | docker-compose mapping | ✅ **Correct** |

## 🔧 Configuration Best Practices

### **1. Consistent Environment Variables**

All Flask-based services should include:
```yaml
environment:
  - FLASK_HOST=0.0.0.0     # Enable inter-container communication
  - FLASK_PORT=XXXX        # Explicit port matching application default
```

### **2. Dockerfile Port Exposure**

Ensure Dockerfile EXPOSE matches application default:
```dockerfile
# Expose the port the app runs on
EXPOSE 5003  # Must match app.py default port
```

### **3. Health Check Configuration**

Health checks should use internal container port:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5003/health"]
```

### **4. Inter-Service Communication**

Services communicate using container names and internal ports:
```yaml
environment:
  - CALENDAR_SYNC_URL=http://fogis-calendar-phonebook-sync:5003/sync
  - GOOGLE_DRIVE_URL=http://google-drive-service:5000
```

## 🚨 Common Issues and Solutions

### **Issue 1: Port Mapping Confusion**

**Problem**: Container exposes different port than application uses
**Solution**: Ensure Dockerfile EXPOSE matches app default port

**Example Fix**:
```dockerfile
# Wrong
EXPOSE 5000
# Correct (if app runs on 5003)
EXPOSE 5003
```

### **Issue 2: Health Check Failures**

**Problem**: Health check uses wrong internal port
**Solution**: Use container's internal port, not host port

**Example Fix**:
```yaml
# Wrong
test: ["CMD", "curl", "-f", "http://localhost:9083/health"]
# Correct
test: ["CMD", "curl", "-f", "http://localhost:5003/health"]
```

### **Issue 3: Inter-Service Communication Failures**

**Problem**: Services can't communicate due to wrong ports
**Solution**: Use container names and internal ports

**Example Fix**:
```yaml
# Wrong
- CALENDAR_SYNC_URL=http://localhost:9083/sync
# Correct
- CALENDAR_SYNC_URL=http://fogis-calendar-phonebook-sync:5003/sync
```

## 📋 Port Allocation Strategy

### **Host Port Ranges**

| Range | Purpose | Services |
|-------|---------|----------|
| **9080-9089** | FOGIS Core Services | API Client, Calendar, Drive, etc. |
| **9090-9099** | Infrastructure | Auth, Monitoring, etc. |
| **8000-8099** | Development/Testing | Local development ports |

### **Internal Port Standards**

| Port | Framework | Services |
|------|-----------|----------|
| **5000** | Flask (default) | Google Drive Service |
| **5001-5010** | Flask (custom) | Custom Flask services |
| **8000** | FastAPI/Django | Match List Processor |
| **8080** | FastAPI | FOGIS API Client |

## 🔍 Verification Commands

### **Check Port Configurations**

```bash
# Verify docker-compose port mappings
docker-compose config | grep -A 5 -B 5 ports

# Check running container ports
docker-compose ps

# Verify specific service ports
docker port CONTAINER_NAME

# Test health endpoints
curl -s http://localhost:9083/health  # Calendar service
curl -s http://localhost:9085/health  # Google Drive service
```

### **Debug Port Issues**

```bash
# Check if port is in use
lsof -i :9083

# Verify container internal ports
docker exec CONTAINER_NAME netstat -tlnp

# Check service logs for port binding
docker logs CONTAINER_NAME | grep -i port
```

## 📚 Related Documentation

- [OAuth Automation Guide](OAUTH_AUTOMATION_GUIDE.md)
- [Manual Container Build Guide](MANUAL_CONTAINER_BUILD_GUIDE.md)
- [Main README](../README.md)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)

---

**Last Updated**: 2025-07-20  
**Related Issues**: OAuth automation enhancement port configuration fixes
