# ARM64 Deployment Status

**Date**: October 7, 2025
**Status**: ✅ READY FOR DEPLOYMENT (with one known issue)

## Overview

This document tracks the status of ARM64 Docker image availability for all FOGIS services and provides deployment guidance.

## Image Build Status

### ✅ Ready for Deployment

| Service | Repository | Image Tag | Platforms | Build Status | Last Updated |
|---------|-----------|-----------|-----------|--------------|--------------|
| **fogis-api-client-python** | [fogis-api-client-python](https://github.com/PitchConnect/fogis-api-client-python) | `ghcr.io/pitchconnect/fogis-api-client-python:latest` | AMD64, ARM64 | ✅ Built | 2025-10-07 00:45 UTC |
| **match-list-processor** | [match-list-processor](https://github.com/PitchConnect/match-list-processor) | `ghcr.io/pitchconnect/match-list-processor:latest` | AMD64, ARM64 | ✅ Built | 2025-10-07 13:04 UTC |
| **team-logo-combiner** | [team-logo-combiner](https://github.com/PitchConnect/team-logo-combiner) | `ghcr.io/pitchconnect/team-logo-combiner:latest` | AMD64, ARM64 | ✅ Built | 2025-10-07 00:45 UTC |
| **google-drive-service** | [google-drive-service](https://github.com/PitchConnect/google-drive-service) | `ghcr.io/pitchconnect/google-drive-service:latest` | AMD64, ARM64 | ✅ Built | 2025-10-07 00:45 UTC |

### ⚠️ Known Issue

| Service | Repository | Image Tag | Platforms | Build Status | Issue |
|---------|-----------|-----------|-----------|--------------|-------|
| **fogis-calendar-phonebook-sync** | [fogis-calendar-phonebook-sync](https://github.com/PitchConnect/fogis-calendar-phonebook-sync) | `ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest` | AMD64 only | ❌ Workflow Failing | [Issue #132](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/issues/132) |

**Issue Details**: The `docker-build.yml` workflow fails immediately upon trigger, preventing ARM64 builds. The workflow file appears syntactically correct, but runs #282 and #283 both failed with 0 jobs executed.

**Workaround**: The service can still be deployed using the latest AMD64 image. ARM64 systems will run it via emulation (slower but functional).

## Deployment Instructions

### Prerequisites

- Docker Engine with BuildKit support
- Docker Compose v2.0+
- ARM64-compatible host system (e.g., Apple Silicon Mac, AWS Graviton, Raspberry Pi 4+)

### Quick Start

The `docker-compose.yml` file is already configured to use `:latest` tags, which will automatically pull ARM64-compatible images where available:

```bash
# Pull latest images (includes ARM64 where available)
docker-compose pull

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# Check service health
docker-compose exec fogis-api-client-service curl http://localhost:8080/health
docker-compose exec process-matches-service curl http://localhost:8000/health/simple
docker-compose exec fogis-calendar-phonebook-sync curl http://localhost:5003/health
```

### Verifying ARM64 Images

To verify which services are running native ARM64 vs emulated AMD64:

```bash
# Check image architecture for each service
docker inspect fogis-api-client-service | grep Architecture
docker inspect process-matches-service | grep Architecture
docker inspect fogis-calendar-phonebook-sync | grep Architecture
docker inspect team-logo-combiner | grep Architecture
docker inspect google-drive-service | grep Architecture
```

Expected output:
- **ARM64 native**: `"Architecture": "arm64"`
- **AMD64 emulated**: `"Architecture": "amd64"`

### Performance Considerations

- **Native ARM64 services** (4/5): Full native performance
- **Emulated AMD64 service** (fogis-calendar-phonebook-sync): ~50-70% performance penalty due to emulation
  - This service is primarily I/O-bound (Google Calendar/Contacts API calls)
  - Emulation overhead should be minimal for typical workloads
  - Monitor CPU usage and consider scaling if needed

## Workflow Modifications

### Completed Changes

1. **fogis-api-client-python** - Already had ARM64 support
2. **match-list-processor** - Added `docker-publish.yml` workflow ([PR #81](https://github.com/PitchConnect/match-list-processor/pull/81))
3. **fogis-calendar-phonebook-sync** - Modified `docker-build.yml` workflow ([PR #131](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/pull/131))
4. **team-logo-combiner** - Already had ARM64 support
5. **google-drive-service** - Already had ARM64 support

### Workflow Configuration

All workflows now build multi-platform images with the following strategy:

- **PR builds**: AMD64 only (faster CI/CD)
- **Main branch pushes**: AMD64 + ARM64 (production-ready)
- **Tagged releases**: AMD64 + ARM64 (versioned releases)

## Troubleshooting

### Issue: Service fails to start on ARM64

**Symptoms**: Container exits immediately or shows architecture-related errors

**Solution**:
1. Check if the image supports ARM64: `docker manifest inspect ghcr.io/pitchconnect/<service>:latest`
2. If ARM64 is not listed, the service will run via emulation (slower but should work)
3. Check container logs: `docker-compose logs <service-name>`

### Issue: Poor performance on ARM64

**Symptoms**: High CPU usage, slow response times

**Possible causes**:
1. Service running via AMD64 emulation (check with `docker inspect`)
2. Insufficient resources allocated to Docker
3. Network latency issues

**Solutions**:
1. Wait for ARM64 native build (track [Issue #132](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/issues/132))
2. Increase Docker resource limits
3. Check network configuration and DNS resolution

### Issue: Image pull fails

**Symptoms**: `manifest unknown` or `not found` errors

**Solution**:
1. Verify you're authenticated to GHCR: `docker login ghcr.io`
2. Check image exists: `docker manifest inspect ghcr.io/pitchconnect/<service>:latest`
3. Try pulling with explicit platform: `docker pull --platform linux/arm64 ghcr.io/pitchconnect/<service>:latest`

## Monitoring

### Health Checks

All services include health check endpoints:

```bash
# API Client
curl http://localhost:9086/health

# Match List Processor
curl http://localhost:9082/health/simple

# Calendar/Phonebook Sync
curl http://localhost:9083/health

# Team Logo Combiner
curl http://localhost:9088/health

# Google Drive Service
curl http://localhost:9085/health
```

### Grafana Dashboard

Access the monitoring dashboard at http://localhost:3000 (default credentials: admin/admin)

- Service health metrics
- Container resource usage
- Log aggregation via Loki
- Performance metrics

## Next Steps

1. **Monitor deployment**: Track service health and performance on ARM64
2. **Resolve Issue #132**: Fix fogis-calendar-phonebook-sync workflow to enable ARM64 builds
3. **Performance testing**: Benchmark ARM64 vs AMD64 performance
4. **Documentation**: Update service-specific READMEs with ARM64 deployment notes

## Related Issues

- [fogis-calendar-phonebook-sync #132](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/issues/132) - docker-build.yml workflow failure

## References

- [Docker Multi-Platform Builds](https://docs.docker.com/build/building/multi-platform/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
