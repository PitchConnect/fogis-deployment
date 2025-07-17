# Container Image Strategy for FOGIS System

## Current State Analysis

### Local Patches in Use
1. **match-list-change-detector**: Persistent service mode with event-driven architecture
2. **match-list-processor**: Event-driven webhook processing with health fixes

### Published Images Available
- `ghcr.io/pitchconnect/match-list-change-detector:latest` - Basic oneshot mode only
- `ghcr.io/pitchconnect/match-list-processor:latest` - Basic oneshot mode only

## Upstream Contribution Status

### GitHub Issues Created
1. **match-list-change-detector**: Issue #27 - Persistent Service Mode
   - URL: https://github.com/PitchConnect/match-list-change-detector/issues/27
   - Status: Open, awaiting review
   - Priority: High (architectural improvement)

2. **match-list-processor**: Issue #20 - Event-Driven Architecture  
   - URL: https://github.com/PitchConnect/match-list-processor/issues/20
   - Status: Open, awaiting review
   - Priority: High (architectural improvement)

## Migration Strategy

### Phase 1: Maintain Local Patches (Current)
**Timeline**: Until upstream PRs are merged
**Status**: ✅ **ACTIVE**

```yaml
# Current configuration using local builds
match-list-change-detector:
  build:
    context: local-patches/match-list-change-detector
    dockerfile: Dockerfile.patched

match-list-processor:
  build:
    context: local-patches/match-list-processor
    dockerfile: Dockerfile.patched
```

**Benefits**:
- ✅ Full event-driven architecture functionality
- ✅ Optimal resource utilization (90% reduction in restarts)
- ✅ Production-ready monitoring and health checks
- ✅ Immediate processing response to changes

**Maintenance Requirements**:
- Keep local patches synchronized with upstream changes
- Monitor upstream repositories for merge status
- Maintain local build infrastructure

### Phase 2: Transition to Published Images (Future)
**Timeline**: After upstream PRs are merged and released
**Status**: ⏳ **PENDING UPSTREAM MERGE**

```yaml
# Future configuration using published images
match-list-change-detector:
  image: ghcr.io/pitchconnect/match-list-change-detector:v2.0.0
  environment:
    - RUN_MODE=service
    - CRON_SCHEDULE=0 * * * *

match-list-processor:
  image: ghcr.io/pitchconnect/match-list-processor:v2.0.0
  environment:
    - RUN_MODE=service
```

**Benefits**:
- ✅ Standardized, maintainable components
- ✅ Automatic security updates from upstream
- ✅ Reduced local build complexity
- ✅ Better CI/CD integration

### Phase 3: Cleanup Local Patches (Final)
**Timeline**: After successful transition to published images
**Status**: 🔮 **FUTURE**

**Actions**:
1. Remove `local-patches/` directories
2. Update documentation to reference published images
3. Archive local patch history for reference
4. Update deployment scripts and CI/CD pipelines

## Container Image Versioning Strategy

### Current Local Builds
- **Tag Strategy**: `local-build-YYYYMMDD-HHMMSS`
- **Build Trigger**: Manual or on configuration changes
- **Registry**: Local Docker daemon only

### Future Published Images
- **Tag Strategy**: Semantic versioning (v1.0.0, v1.1.0, v2.0.0)
- **Build Trigger**: Automated on merge to main branch
- **Registry**: GitHub Container Registry (ghcr.io)

### Version Mapping
| **Feature** | **Local Patch** | **Future Published** |
|-------------|-----------------|---------------------|
| Persistent Service Mode | ✅ Available | v2.0.0+ |
| Event-Driven Processing | ✅ Available | v2.0.0+ |
| Health Check Fixes | ✅ Available | v1.1.0+ |
| Webhook Integration | ✅ Available | v2.0.0+ |

## Migration Preparation Checklist

### Pre-Migration Validation
- [ ] Verify upstream issues are reviewed and approved
- [ ] Confirm PRs are created and under review
- [ ] Test local patches against latest upstream main branch
- [ ] Validate all functionality works with current configuration

### Migration Readiness Criteria
- [ ] Upstream PRs merged to main branch
- [ ] New container images published to GHCR
- [ ] Images tagged with appropriate version numbers
- [ ] All architectural improvements included in published images
- [ ] Backward compatibility maintained

### Migration Execution Plan
1. **Update docker-compose.yml**:
   ```bash
   # Replace build contexts with image references
   sed -i 's/build:/# build:/' docker-compose-master.yml
   sed -i 's/context:/# context:/' docker-compose-master.yml
   sed -i 's/dockerfile:/# dockerfile:/' docker-compose-master.yml
   ```

2. **Add image references**:
   ```yaml
   image: ghcr.io/pitchconnect/match-list-change-detector:v2.0.0
   image: ghcr.io/pitchconnect/match-list-processor:v2.0.0
   ```

3. **Test migration**:
   ```bash
   docker-compose -f docker-compose-master.yml pull
   docker-compose -f docker-compose-master.yml up -d
   ```

4. **Validate functionality**:
   ```bash
   # Test event-driven architecture
   curl -X POST http://localhost:9080/trigger
   curl -s http://localhost:9082/health | jq '.mode'
   ```

### Rollback Plan
If published images don't work as expected:

1. **Immediate rollback**:
   ```bash
   git checkout HEAD~1 docker-compose-master.yml
   docker-compose -f docker-compose-master.yml up -d --build
   ```

2. **Verify local patches still work**:
   ```bash
   curl -s http://localhost:9080/health | jq '.status'
   curl -s http://localhost:9082/health | jq '.mode'
   ```

## Quality Assurance

### Testing Requirements
Before transitioning to published images:

1. **Functional Testing**:
   - [ ] Event-driven processing works correctly
   - [ ] Webhook integration functions properly
   - [ ] Health monitoring provides accurate status
   - [ ] All service dependencies are healthy

2. **Performance Testing**:
   - [ ] Resource usage remains optimized
   - [ ] No unnecessary restart cycles
   - [ ] Processing only occurs when changes detected
   - [ ] Response times meet requirements

3. **Integration Testing**:
   - [ ] End-to-end pipeline functions correctly
   - [ ] All 6 services integrate properly
   - [ ] Backup/restore system works with new images
   - [ ] Monitoring and alerting function correctly

### Acceptance Criteria
Published images must provide:
- ✅ **Feature Parity**: All local patch functionality
- ✅ **Performance Parity**: Same resource efficiency gains
- ✅ **Stability Parity**: Same or better reliability
- ✅ **Monitoring Parity**: Same health check capabilities

## Risk Assessment

### Low Risk
- **Backward Compatibility**: Upstream changes maintain oneshot mode support
- **Configuration**: Environment variables remain the same
- **Data Persistence**: No changes to data storage or formats

### Medium Risk
- **Timing**: Upstream merge timeline uncertain
- **Dependencies**: New dependencies might be added upstream
- **Testing**: Published images might have different behavior

### High Risk
- **Breaking Changes**: Upstream might introduce incompatible changes
- **Feature Gaps**: Published images might lack some local patch features
- **Regression**: Published images might have bugs not present in local patches

### Mitigation Strategies
1. **Maintain Local Patches**: Keep working until published images proven
2. **Comprehensive Testing**: Validate all functionality before migration
3. **Gradual Migration**: Test in development before production
4. **Rollback Plan**: Quick revert to local patches if needed

## Communication Plan

### Stakeholder Updates
1. **Development Team**: Regular updates on upstream contribution status
2. **Operations Team**: Migration timeline and impact assessment
3. **Management**: Resource efficiency benefits and maintenance reduction

### Documentation Updates
1. **README.md**: Update with published image references
2. **Deployment Guide**: Remove local build instructions
3. **Troubleshooting**: Update with published image specifics
4. **Architecture Docs**: Reflect standardized components

## Success Metrics

### Technical Metrics
- **Build Time**: Reduced from local builds to image pulls
- **Deployment Speed**: Faster deployments with pre-built images
- **Maintenance Overhead**: Reduced local patch management
- **Security Updates**: Automatic via upstream releases

### Operational Metrics
- **System Reliability**: Maintained or improved uptime
- **Resource Efficiency**: Preserved 90% reduction in restarts
- **Processing Performance**: Maintained event-driven benefits
- **Monitoring Accuracy**: Continued accurate health reporting

## Timeline

### Immediate (Current)
- ✅ GitHub issues created for upstream contributions
- ✅ Local patches working in production
- ✅ Event-driven architecture providing benefits

### Short Term (1-2 weeks)
- ⏳ Upstream review and feedback on issues
- ⏳ PR creation and review process
- ⏳ Testing against upstream main branch

### Medium Term (2-4 weeks)
- 🔮 Upstream PRs merged
- 🔮 Published images with new features
- 🔮 Migration testing and validation

### Long Term (1-2 months)
- 🔮 Production migration to published images
- 🔮 Local patch cleanup and archival
- 🔮 Documentation updates complete

---

**Status**: Local patches provide production-ready event-driven architecture while awaiting upstream integration. Migration to published images will occur once upstream contributions are merged and validated.
