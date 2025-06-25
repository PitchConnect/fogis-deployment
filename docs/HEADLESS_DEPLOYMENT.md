# FOGIS Headless Deployment Guide

## Overview

The FOGIS Headless Deployment system extends the existing safe installation system to support fully automated, non-interactive deployments suitable for CI/CD pipelines, Infrastructure as Code, and automated maintenance scenarios.

## Quick Start

### Basic Headless Installation

```bash
# Simple headless installation
curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless

# Headless upgrade with auto-confirmation
curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless --mode=upgrade --auto-confirm
```

### CI/CD Integration

```bash
# GitHub Actions / GitLab CI / Jenkins
# Headless mode is automatically detected in CI/CD environments
curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash
```

## Configuration Methods

### 1. Command Line Arguments

```bash
curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- [options]
```

**Available Options:**
- `--headless` - Enable headless mode (non-interactive)
- `--mode=MODE` - Installation mode: `fresh|upgrade|force|check`
- `--auto-confirm` - Automatically confirm all prompts
- `--backup-retention=DAYS` - Backup retention period (default: 30)
- `--timeout=SECONDS` - Operation timeout (default: 300)
- `--operation-id=ID` - Unique operation identifier for logging
- `--install-dir=PATH` - Installation directory (default: ~/fogis-deployment)
- `--branch=BRANCH` - Git branch to use (default: main)
- `--help` - Show help message

### 2. Environment Variables

```bash
export FOGIS_HEADLESS=true
export FOGIS_INSTALL_MODE=upgrade
export FOGIS_AUTO_CONFIRM=true
export FOGIS_TIMEOUT=600
export FOGIS_INSTALL_DIR=/opt/fogis
export FOGIS_BRANCH=main

curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash
```

**Environment Variables:**
- `FOGIS_HEADLESS` - Enable headless mode (true/false)
- `FOGIS_INSTALL_MODE` - Installation mode
- `FOGIS_AUTO_CONFIRM` - Auto-confirm prompts (true/false)
- `FOGIS_BACKUP_RETENTION` - Backup retention days
- `FOGIS_TIMEOUT` - Operation timeout seconds
- `FOGIS_INSTALL_DIR` - Installation directory
- `FOGIS_BRANCH` - Git branch

### 3. Automatic CI/CD Detection

Headless mode is automatically enabled when these environment variables are detected:
- `CI=true`
- `GITHUB_ACTIONS=true`
- `JENKINS_URL` (any value)
- `GITLAB_CI=true`

## Installation Modes

### Fresh Installation (`fresh`)
- Clean installation on empty system
- Fastest installation method
- **Use when:** No existing FOGIS installation

### Safe Upgrade (`upgrade`)
- Preserves credentials and important data
- Graceful service shutdown and cleanup
- Automatic backup creation
- Rollback capability on failure
- **Use when:** Existing healthy installation needs updating

### Force Clean Install (`force`)
- Removes all existing data and configurations
- Creates backup before destruction
- **Use when:** Existing installation is corrupted beyond repair
- **⚠️ WARNING:** This will destroy all existing data!

### Conflict Check Only (`check`)
- Check for conflicts without making changes
- Generate detailed conflict report
- **Use when:** Diagnosing installation issues

## Intelligent Default Behavior

When conflicts are detected and no explicit mode is specified, the system automatically selects the most appropriate mode:

### Decision Matrix

| Scenario | Running Containers | Credentials | Config Files | Selected Mode | Rationale |
|----------|-------------------|-------------|--------------|---------------|-----------|
| Healthy Installation | ✅ | ✅ | ✅ | `upgrade` | Preserve working system |
| Partial Installation | ❌ | ✅ | ✅ | `upgrade` | Preserve important data |
| Broken Installation | ❌ | ❌ | ❌ | `force` | Clean slate needed |
| Mixed State | ❌ | ✅ | ❌ | `upgrade` | Preserve credentials |

## Structured Logging

In headless mode, all output is structured JSON for easy parsing by monitoring systems:

```json
{
  "timestamp": "2023-12-01T10:30:00Z",
  "level": "info",
  "operation_id": "fogis-install-1701423000",
  "message": "Starting FOGIS headless installation"
}
```

### Log Levels
- `info` - General information
- `success` - Successful operations
- `warning` - Non-critical issues
- `error` - Critical errors
- `progress` - Progress updates
- `header` - Section headers
- `decision` - Automated decision rationale
- `health_check` - Post-installation verification

### Progress Reporting

```json
{
  "timestamp": "2023-12-01T10:30:15Z",
  "level": "progress",
  "operation_id": "fogis-install-1701423000",
  "phase": "setup",
  "step": 2,
  "total_steps": 5,
  "progress_percent": 40,
  "message": "Installing components"
}
```

## Exit Codes

The system uses specific exit codes for different scenarios:

| Exit Code | Meaning | Description |
|-----------|---------|-------------|
| 0 | Success | Installation completed successfully |
| 1 | General Error | Unspecified error occurred |
| 10 | Backup Failure | Backup creation failed |
| 20 | Rollback Required | Installation failed, rollback needed |
| 30 | Conflicts Detected | Conflicts found (check mode) |
| 40 | Timeout | Operation timed out |
| 50 | Invalid Configuration | Configuration validation failed |

## Use Cases and Examples

### GitHub Actions

```yaml
name: Deploy FOGIS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy FOGIS
        run: |
          curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless --mode=upgrade --timeout=600
```

### Terraform

```hcl
resource "null_resource" "fogis_installation" {
  provisioner "remote-exec" {
    inline = [
      "curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless --mode=fresh --auto-confirm"
    ]
  }
}
```

### Ansible

```yaml
- name: Install FOGIS
  shell: |
    curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless --mode=upgrade
  environment:
    FOGIS_TIMEOUT: "900"
    FOGIS_AUTO_CONFIRM: "true"
```

### Docker Container Initialization

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y curl docker.io git

# Install FOGIS in headless mode
RUN curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless --mode=fresh --auto-confirm

CMD ["/home/fogis/fogis-deployment/manage_fogis_system.sh", "start"]
```

### Kubernetes Init Container

```yaml
apiVersion: v1
kind: Pod
spec:
  initContainers:
  - name: fogis-installer
    image: ubuntu:22.04
    command:
    - /bin/bash
    - -c
    - |
      apt-get update && apt-get install -y curl docker.io git
      curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless --mode=fresh --timeout=900
    env:
    - name: FOGIS_AUTO_CONFIRM
      value: "true"
```

### Scheduled Maintenance (Cron)

```bash
# /etc/cron.d/fogis-maintenance
0 2 * * 0 root curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless --mode=upgrade --auto-confirm > /var/log/fogis-maintenance.log 2>&1
```

## Monitoring and Alerting

### Log Parsing with jq

```bash
# Extract errors
curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless 2>&1 | jq -r 'select(.level == "error") | .message'

# Monitor progress
curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless 2>&1 | jq -r 'select(.level == "progress") | "\(.phase): \(.progress_percent)%"'
```

### Health Check Verification

```bash
# Check installation health after deployment
if curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless --mode=check; then
  echo "FOGIS installation healthy"
else
  echo "FOGIS installation issues detected"
  exit 1
fi
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Ensure Docker daemon is accessible
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **Timeout Issues**
   ```bash
   # Increase timeout for slow networks
   curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless --timeout=900
   ```

3. **Configuration Validation Errors**
   ```bash
   # Check configuration before running
   curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --help
   ```

### Debug Mode

```bash
# Enable debug output
export FOGIS_DEBUG=true
curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless
```

## Security Considerations

- Backup files contain sensitive credentials
- Use secure channels for log transmission
- Implement proper access controls for CI/CD environments
- Regularly rotate operation IDs and credentials
- Monitor for unauthorized headless installations

## Migration from Interactive Mode

Existing interactive installations can be seamlessly upgraded using headless mode:

```bash
# Upgrade existing installation
curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | bash -s -- --headless --mode=upgrade --auto-confirm
```

All existing safety features (backup, rollback, conflict detection) are preserved in headless mode.
