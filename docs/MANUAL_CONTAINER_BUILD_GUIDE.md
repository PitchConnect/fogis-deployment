# Manual Container Build Guide

This guide provides step-by-step instructions for manually triggering container builds for FOGIS services, particularly useful when automatic builds need to be initiated or verified.

## 🐳 Calendar Service Container Build

### **GitHub Actions Workflow Dispatch Method**

#### **1. Via GitHub Web Interface**

1. **Navigate to Repository**:
   ```
   https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions
   ```

2. **Select Docker Build Workflow**:
   - Click on "Docker Build and Publish" workflow
   - Click "Run workflow" button
   - Select branch (usually `main`)
   - Click "Run workflow"

#### **2. Via GitHub CLI**

```bash
# Install GitHub CLI if not already installed
# macOS: brew install gh
# Login: gh auth login

# Trigger Docker build workflow
gh workflow run docker-build.yml \
  --repo PitchConnect/fogis-calendar-phonebook-sync \
  --ref main

# Check workflow status
gh run list --workflow=docker-build.yml \
  --repo PitchConnect/fogis-calendar-phonebook-sync \
  --limit 5
```

#### **3. Via GitHub API**

```bash
# Using curl with GitHub token
curl -X POST \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  https://api.github.com/repos/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/docker-build.yml/dispatches \
  -d '{"ref":"main"}'
```

### **Command-Line Alternatives**

#### **Local Docker Build**

```bash
# Clone repository
git clone https://github.com/PitchConnect/fogis-calendar-phonebook-sync.git
cd fogis-calendar-phonebook-sync

# Build multi-platform image
docker buildx create --use --name multiarch-builder
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest \
  --tag ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:$(git rev-parse --short HEAD) \
  --push .

# Note: Requires GHCR authentication
# docker login ghcr.io -u USERNAME -p GITHUB_TOKEN
```

## 🔍 Verification Methods

### **1. Check Build Completion**

#### **GitHub Actions Status**

```bash
# Check latest workflow runs
gh run list --workflow=docker-build.yml \
  --repo PitchConnect/fogis-calendar-phonebook-sync \
  --limit 5

# Get specific run details
gh run view RUN_ID \
  --repo PitchConnect/fogis-calendar-phonebook-sync
```

#### **Build Logs**

```bash
# View build logs
gh run view RUN_ID --log \
  --repo PitchConnect/fogis-calendar-phonebook-sync
```

### **2. Verify GHCR Image Availability**

#### **Check Image Tags**

```bash
# List available tags
curl -H "Authorization: Bearer GITHUB_TOKEN" \
  https://api.github.com/orgs/PitchConnect/packages/container/fogis-calendar-phonebook-sync/versions

# Or using GitHub CLI
gh api /orgs/PitchConnect/packages/container/fogis-calendar-phonebook-sync/versions
```

#### **Pull and Inspect Image**

```bash
# Pull latest image
docker pull ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest

# Inspect image details
docker inspect ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest

# Check image creation date
docker images ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest \
  --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}"
```

### **3. Test Health Check Enhancement**

#### **Local Container Test**

```bash
# Run container locally
docker run -d --name test-calendar-service \
  -p 9083:9083 \
  -e GOOGLE_CALENDAR_TOKEN_FILE=/app/credentials/tokens/calendar/token.json \
  ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest

# Test health endpoint
curl -s http://localhost:9083/health | jq '.'

# Expected response with health check enhancement:
# {
#   "status": "warning",
#   "message": "OAuth token not found, may need authentication",
#   "checked_locations": [
#     "/app/credentials/tokens/calendar/token.json",
#     "/app/data/token.json",
#     "/app/token.json"
#   ],
#   "auth_url": "http://localhost:9083/authorize"
# }

# Cleanup
docker stop test-calendar-service
docker rm test-calendar-service
```

## 🚀 Production Deployment Verification

### **Update Deployment**

```bash
# In fogis-deployment directory
cd fogis-deployment

# Pull latest image
docker-compose pull fogis-calendar-phonebook-sync

# Restart service with new image
docker-compose up -d fogis-calendar-phonebook-sync

# Verify service is running
docker-compose ps fogis-calendar-phonebook-sync
```

### **Health Check Verification**

```bash
# Test enhanced health check
curl -s http://localhost:9083/health | jq '.'

# With OAuth token present, expect:
# {
#   "status": "healthy",
#   "auth_status": "authenticated",
#   "token_location": "/app/credentials/tokens/calendar/token.json",
#   "version": "dev",
#   "environment": "development"
# }
```

## 📋 Troubleshooting

### **Build Failures**

1. **Check Workflow Logs**:
   ```bash
   gh run view --log FAILED_RUN_ID
   ```

2. **Common Issues**:
   - **Authentication**: Ensure GHCR_TOKEN has package write permissions
   - **Platform Support**: Verify buildx setup for multi-platform builds
   - **Resource Limits**: Check if build exceeds GitHub Actions limits

### **Image Not Available**

1. **Check Package Visibility**:
   - Ensure package is public or you have access
   - Verify organization package settings

2. **Authentication Issues**:
   ```bash
   # Re-authenticate with GHCR
   echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
   ```

### **Health Check Issues**

1. **Environment Variables**:
   ```bash
   # Verify environment variable is set
   docker exec CONTAINER_NAME env | grep GOOGLE_CALENDAR_TOKEN_FILE
   ```

2. **Token File Permissions**:
   ```bash
   # Check token file accessibility
   docker exec CONTAINER_NAME ls -la /app/credentials/tokens/calendar/token.json
   ```

## 🔗 Related Documentation

- [OAuth Automation Guide](OAUTH_AUTOMATION_GUIDE.md)
- [Main README](../README.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Container Registry Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
