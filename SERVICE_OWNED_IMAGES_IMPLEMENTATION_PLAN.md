# Service-Owned Images Implementation Plan

> **⚠️ IMPORTANT**: Refer back to this file after completing each step to ensure nothing is missed.
> Check off completed items using `[x]` to track progress.

## 🎯 **Executive Summary**

**Discovery**: The deployment repository is already successfully using service-owned images architecture! The failing CI/CD workflows are redundant because each service repository builds and publishes its own Docker images to GHCR.

**Goal**: Clean up legacy artifacts, remove redundant workflows, and properly document the current architecture.

---

## 📋 **Implementation Checklist**

### **Phase 0: Setup and Preparation**
- [x] Create this implementation plan file
- [x] Install and configure pre-commit hooks
- [x] Verify code quality tools are working
- [x] Test pre-commit setup with a small change

### **Phase 1: Remove Redundant CI/CD** *(Separate commits for each)*
- [ ] Disable redundant `docker-build.yml` workflow (rename to `.disabled`)
- [ ] Remove/comment out service source code directories
  - [ ] `fogis-calendar-phonebook-sync/`
  - [ ] `match-list-processor/`
  - [ ] Other service directories if present
- [ ] Update `.gitignore` to prevent re-adding service source code
- [ ] Clean up `local-patches/` directory (no longer used)

### **Phase 2: Update Documentation**
- [ ] Update `README.md` with service-owned images architecture
- [ ] Update `container_image_strategy.md` to reflect migration completion
- [ ] Create/update architecture documentation
- [ ] Document current CI/CD workflow (service repos build, deployment repo references)

### **Phase 3: Optimize Configuration**
- [ ] Implement semantic versioning in `docker-compose.yml`
  - [ ] Replace `:latest` tags with specific versions
  - [ ] Research current versions of each service image
- [ ] Add dependabot configuration for automated image updates
- [ ] Update deployment scripts to reflect new architecture
- [ ] Add monitoring/alerting for image updates

### **Phase 4: Final Validation and PR**
- [ ] Verify all pre-commit hooks pass
- [ ] Test docker-compose with new configuration
- [ ] Create comprehensive PR with summary of all changes
- [ ] Update this checklist with final status

---

## 🔍 **Current Architecture Analysis**

### **✅ What's Already Working**
- Service repositories build and publish their own images
- Deployment repository uses published images from GHCR
- Docker-compose.yml references `ghcr.io/pitchconnect/*:latest` images
- Enhanced features are preserved in upstream repositories

### **❌ What Needs Cleanup**
- Redundant docker-build.yml workflow causing GHCR permission errors
- Legacy service source code directories in deployment repo
- Unused local-patches directory
- Documentation doesn't reflect current architecture
- Using `:latest` tags instead of semantic versions

---

## 🛠 **Technical Implementation Details**

### **Services Using Published Images**
```yaml
# Current docker-compose.yml already uses:
- ghcr.io/pitchconnect/fogis-api-client-python:latest
- ghcr.io/pitchconnect/match-list-processor:latest
- ghcr.io/pitchconnect/fogis-calendar-phonebook-sync:latest
- ghcr.io/pitchconnect/team-logo-combiner:latest
- ghcr.io/pitchconnect/google-drive-service:latest
```

### **Redundant Workflows to Remove**
- `.github/workflows/docker-build.yml` - Builds images that services already build
- `.github/workflows/tests.yml` - Tests code that doesn't exist in deployment repo
- `.github/workflows/code-quality.yml` - Checks code that should be in service repos

### **Legacy Artifacts to Clean**
- Service source code directories (already published as images)
- `local-patches/` directory (features already in upstream)
- Unused Dockerfiles in service directories

---

## ⚠️ **Risk Mitigation**

### **Low Risk Items**
- Disabling redundant workflows (can be re-enabled)
- Removing legacy source code (exists in service repositories)
- Documentation updates (reversible)

### **Medium Risk Items**
- Changing from `:latest` to semantic versions (test thoroughly)
- Removing local-patches (verify features exist upstream)

### **Rollback Plan**
1. Re-enable workflows by removing `.disabled` extension
2. Restore source code from git history if needed
3. Revert docker-compose.yml changes if issues arise

---

## 📊 **Success Metrics**

### **Immediate Goals**
- [ ] No failing CI/CD workflows
- [ ] Clear documentation of current architecture
- [ ] Removal of redundant/legacy artifacts

### **Long-term Goals**
- [ ] Automated image updates via dependabot
- [ ] Semantic versioning for all services
- [ ] Clear separation between service development and deployment

---

## 🔄 **Next Steps After Completion**

1. **Monitor Service Repositories**: Ensure they continue building images properly
2. **Implement GitOps**: Consider tools like ArgoCD for automated deployments
3. **Version Management**: Establish process for coordinating service version updates
4. **Team Training**: Educate team on the clean architecture

---

*Last Updated: 2025-09-24*
*Status: In Progress*
