# FOGIS CI/CD Workflows Documentation

## Overview

This document describes the GitHub Actions workflows implemented for automated building, testing, and deployment of FOGIS container images to GitHub Container Registry (GHCR).

## Workflow Files

### 1. Docker Build Workflow (`.github/workflows/docker-build.yml`)

**Purpose**: Automated building and publishing of Docker images for all FOGIS services.

**Triggers**:
- Release published
- Push to `main` or `develop` branches
- Pull requests to `main` branch

**Features**:
- Multi-service matrix build (6 services)
- Multi-architecture support (AMD64/ARM64)
- Automated GHCR publishing
- Security scanning with Trivy
- Build caching for performance
- Conditional building (only if Dockerfile exists)

**Services Built**:
- `fogis-api-client-service`
- `team-logo-combiner`
- `match-list-processor`
- `match-list-change-detector`
- `fogis-calendar-phonebook-sync`
- `google-drive-service`

**Image Tags Generated**:
- `latest` (for main branch)
- `main` (for main branch pushes)
- `develop` (for develop branch pushes)
- `v1.0.0` (for semantic version releases)
- `v1.0` (major.minor for releases)
- `v1` (major for releases)

### 2. Release Management Workflow (`.github/workflows/release.yml`)

**Purpose**: Automated release management and version control.

**Triggers**:
- Git tags matching `v*` pattern
- Manual workflow dispatch

**Features**:
- Automatic changelog generation
- GitHub release creation
- Version reference updates
- Release artifact documentation
- Multi-architecture build confirmation

**Process**:
1. Extract version from tag or manual input
2. Generate changelog from git commits
3. Create GitHub release with detailed notes
4. Update version references in compose files
5. Commit version updates back to repository

### 3. Dependency Updates Workflow (`.github/workflows/dependency-updates.yml`)

**Purpose**: Automated maintenance and security updates.

**Schedule**: Weekly on Monday at 2 AM UTC

**Features**:
- Python base image updates
- GitHub Actions version updates
- Automated pull request creation
- Security-focused maintenance

**Process**:
1. Check for latest Python base images
2. Scan for outdated GitHub Actions
3. Update Dockerfiles and workflow files
4. Create pull request with changes
5. Include security and compatibility notes

## Image Registry Structure

All images are published to GitHub Container Registry (GHCR):

```
ghcr.io/pitchconnect/
├── fogis-api-client-service:latest, :v1.0.0, :main
├── match-list-processor:latest, :v1.0.0, :main
├── team-logo-combiner:latest, :v1.0.0, :main
├── google-drive-service:latest, :v1.0.0, :main
├── fogis-calendar-phonebook-sync:latest, :v1.0.0, :main
└── match-list-change-detector:latest, :v1.0.0, :main
```

## Security Features

### Vulnerability Scanning
- **Tool**: Trivy security scanner
- **Scope**: All published images
- **Integration**: GitHub Security tab
- **Format**: SARIF reports for GitHub integration

### Access Control
- **Registry**: GHCR with GitHub authentication
- **Permissions**: Repository-based access control
- **Secrets**: GitHub token authentication

### Image Signing
- **Method**: GitHub's built-in container signing
- **Verification**: Automatic signature verification
- **Trust**: GitHub's security infrastructure

## Performance Optimizations

### Build Caching
- **Type**: GitHub Actions cache
- **Scope**: Docker layer caching
- **Benefits**: Faster subsequent builds

### Multi-Stage Builds
- **Pattern**: Builder and runtime stages
- **Benefits**: Smaller final images
- **Security**: Reduced attack surface

### Parallel Builds
- **Strategy**: Matrix builds for all services
- **Concurrency**: Up to 6 parallel builds
- **Efficiency**: Faster overall pipeline

## Monitoring and Notifications

### Build Status
- **Location**: GitHub Actions tab
- **Notifications**: GitHub notifications
- **Integration**: Status checks on PRs

### Security Alerts
- **Source**: Trivy scan results
- **Location**: GitHub Security tab
- **Action**: Automatic issue creation for vulnerabilities

### Performance Metrics
- **Build Times**: Tracked in workflow logs
- **Image Sizes**: Reported in build summaries
- **Success Rates**: GitHub Actions insights

## Usage Examples

### Triggering a Release Build
```bash
# Create and push a release tag
git tag v1.0.0
git push origin v1.0.0

# This triggers:
# 1. docker-build.yml workflow
# 2. release.yml workflow
# 3. Automatic image publishing
```

### Manual Workflow Dispatch
```bash
# Via GitHub UI:
# 1. Go to Actions tab
# 2. Select "Release Management" workflow
# 3. Click "Run workflow"
# 4. Enter version (e.g., v1.0.1)
```

### Checking Build Status
```bash
# View recent workflow runs
gh run list --repo PitchConnect/fogis-deployment

# View specific run details
gh run view <run-id> --repo PitchConnect/fogis-deployment
```

## Troubleshooting

### Common Issues

**Build Failures**:
- Check Dockerfile syntax
- Verify base image availability
- Review build logs in Actions tab

**Security Scan Failures**:
- Review Trivy scan results
- Update base images if needed
- Check for known vulnerabilities

**Publishing Failures**:
- Verify GHCR permissions
- Check GitHub token validity
- Review registry connectivity

### Debug Commands
```bash
# Test local build
docker build -t test-image .

# Test multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 -t test-image .

# Test image functionality
docker run --rm test-image echo "test"
```

## Best Practices

### Dockerfile Guidelines
- Use specific base image tags
- Minimize layer count
- Use multi-stage builds
- Set proper user permissions
- Include health checks

### Workflow Maintenance
- Regular dependency updates
- Monitor build performance
- Review security scan results
- Update documentation

### Version Management
- Follow semantic versioning
- Tag releases consistently
- Maintain changelog
- Test before releasing

## Integration with Deployment

The CI/CD workflows integrate seamlessly with the FOGIS deployment system:

1. **Automated Builds**: Every release creates new images
2. **Version Management**: Management script can check for updates
3. **Multi-Architecture**: Supports both Intel and ARM deployments
4. **Security**: Automated vulnerability scanning
5. **Performance**: Optimized for fast deployment times

## Future Enhancements

Potential improvements to consider:

- **Build Notifications**: Slack/email integration
- **Performance Monitoring**: Detailed metrics collection
- **Advanced Security**: Image signing with Cosign
- **Multi-Registry**: Support for additional registries
- **Automated Testing**: Integration test execution

---

For questions or issues with the CI/CD workflows, please:
1. Check the GitHub Actions logs
2. Review this documentation
3. Create an issue in the repository
4. Contact the development team
