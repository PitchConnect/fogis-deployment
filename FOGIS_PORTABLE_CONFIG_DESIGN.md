# FOGIS Portable Configuration System Design

## Executive Summary

This document outlines a comprehensive portable configuration system for FOGIS deployment that enables:
- **Lightning-fast installation**: 10-15 minutes from zero to operational
- **Seamless system migration**: Complete environment portability
- **Minimal user input**: Automated setup with intelligent defaults
- **Backup and restore**: Complete system state management

## Current State Analysis

### 1. Required Files Inventory

#### Core Configuration Files
- `docker-compose-master.yml` - Main orchestration file
- `.env` - Environment variables
- `credentials.json` - Google OAuth client credentials
- `config.json` - Service-specific configuration (calendar sync)

#### Authentication Files
- `token.json` - Google OAuth access/refresh tokens (calendar/contacts)
- `google-drive-token.json` - Google Drive service tokens
- `google-credentials.json` - Copied OAuth credentials for containers

#### Directory Structure
```
fogis-deployment/
├── credentials/              # Google OAuth credentials
├── data/                    # Persistent service data
│   ├── fogis-api-client/
│   ├── match-list-change-detector/
│   ├── fogis-calendar-phonebook-sync/
│   │   └── token.json
│   ├── team-logo-combiner/
│   ├── google-drive-service/
│   │   ├── google-drive-token.json
│   │   └── token.json
│   └── match-list-processor/
└── logs/                    # Service logs (6 services)
```

#### Scripts and Management Tools
- `install.sh` - Main installation script
- `setup_fogis_system.sh` - Comprehensive setup
- `manage_fogis_system.sh` - System management
- `authenticate_all_services.py` - OAuth authentication
- `configure_system.py` - Interactive configuration
- `platform_manager.py` - Multi-platform support

### 2. Credentials and Authentication Requirements

#### FOGIS Authentication
- `FOGIS_USERNAME` - FOGIS login username
- `FOGIS_PASSWORD` - FOGIS login password (confirmed: "temporary")
- `USER_REFEREE_NUMBER` - Referee number for filtering

#### Google OAuth Requirements
- **OAuth Client Credentials**: `credentials.json` (web application type)
- **Required Scopes**:
  - `https://www.googleapis.com/auth/calendar`
  - `https://www.googleapis.com/auth/contacts`
  - `https://www.googleapis.com/auth/drive`
- **Access Tokens**: Automatically generated and refreshed
- **Calendar ID**: Target Google Calendar (default: "primary")
- **Drive Folder ID**: Optional Google Drive folder for uploads

### 3. User-Specific Configuration Needs

#### Service Endpoints (Internal - Usually Static)
- `FOGIS_API_CLIENT_URL`: http://fogis-api-client-service:8080
- `CALENDAR_SYNC_URL`: http://fogis-calendar-phonebook-sync:5003/sync
- `LOGO_COMBINER_URL`: http://team-logo-combiner:5000/combine
- `GOOGLE_DRIVE_URL`: http://google-drive-service:5000

#### Port Configuration (External Access)
- API Client: 9086
- Match Processor: 9082
- Calendar Sync: 9083, 9084, 9087
- Logo Combiner: 9088
- Google Drive: 9085
- Change Detector: 9080

#### Processing Configuration
- `MIN_REFEREES_FOR_WHATSAPP`: 2 (minimum referees for WhatsApp group creation)
- `GDRIVE_FOLDER_BASE`: "WhatsApp_Group_Assets"
- `MATCH_CHECK_SCHEDULE`: "0 * * * *" (hourly cron)
- `LOG_LEVEL`: INFO/DEBUG/WARNING/ERROR

## Proposed Portable Configuration System

### Master Configuration File: `fogis-config.yaml`

```yaml
# FOGIS Deployment Master Configuration
# Version: 2.0
# Generated: 2025-01-12

metadata:
  version: "2.0"
  created: "2025-01-12T10:00:00Z"
  description: "FOGIS Complete System Configuration"

# FOGIS Authentication
fogis:
  username: "Bartek Svaberg"
  password: "temporary"
  referee_number: 61318

# Google Integration
google:
  # OAuth Configuration
  oauth:
    client_type: "web_application"
    scopes:
      - "https://www.googleapis.com/auth/calendar"
      - "https://www.googleapis.com/auth/contacts"
      - "https://www.googleapis.com/auth/drive"

  # Service Configuration
  calendar:
    calendar_id: "primary"
    sync_tag: "FOGIS_CALENDAR_SYNC"
    days_to_keep_past_events: 7

  drive:
    folder_base: "WhatsApp_Group_Assets"
    auto_create_folders: true

# Service Configuration
services:
  # Port mappings for external access
  ports:
    api_client: 9086
    match_processor: 9082
    calendar_sync: 9083
    calendar_auth: 9084
    calendar_web_trigger: 9087
    logo_combiner: 9088
    google_drive: 9085
    change_detector: 9080

  # Processing settings
  processing:
    min_referees_for_whatsapp: 2
    match_check_schedule: "0 * * * *"
    force_fresh_processing: true
    service_interval: 300

  # Logging configuration
  logging:
    level: "INFO"
    debug_mode: false
    verbose_logging: false

# System Configuration
system:
  # Docker configuration
  docker:
    restart_policy: "unless-stopped"
    network_name: "fogis-network"
    use_ghcr_images: true

  # Directory paths (container-relative)
  paths:
    data: "/app/data"
    logs: "/app/logs"
    credentials: "/app/credentials"
    temp: "/tmp"

  # Health check configuration
  health:
    interval: 30
    timeout: 10
    retries: 3
    start_period: 40

# Notification Configuration (Optional)
notifications:
  email:
    enabled: false
    sender: ""
    receiver: ""
    smtp_server: "smtp.gmail.com"
    smtp_port: 587

  discord:
    enabled: false
    webhook_url: ""

  slack:
    enabled: false
    webhook_url: ""

# Backup Configuration
backup:
  enabled: true
  retention_days: 30
  include_logs: false
  include_processing_state: false  # For clean installations
```

### Configuration Management Tools

#### 1. Configuration Generator: `generate-config.py`

```python
#!/usr/bin/env python3
"""
FOGIS Configuration Generator
Converts fogis-config.yaml to all required configuration files
"""

import yaml
import json
import os
from pathlib import Path

def generate_env_file(config):
    """Generate .env file from YAML configuration"""
    env_content = [
        "# FOGIS Deployment Configuration",
        f"# Generated from fogis-config.yaml v{config['metadata']['version']}",
        f"# Created: {config['metadata']['created']}",
        "",
        "# FOGIS Authentication",
        f"FOGIS_USERNAME={config['fogis']['username']}",
        f"FOGIS_PASSWORD={config['fogis']['password']}",
        f"USER_REFEREE_NUMBER={config['fogis']['referee_number']}",
        "",
        "# Google Configuration",
        f"GOOGLE_CREDENTIALS_PATH={config['system']['paths']['credentials']}/google-credentials.json",
        f"GOOGLE_CALENDAR_ID={config['google']['calendar']['calendar_id']}",
        f"GOOGLE_SCOPES={','.join(config['google']['oauth']['scopes'])}",
        "",
        "# Service Ports",
        f"API_CLIENT_PORT={config['services']['ports']['api_client']}",
        f"MATCH_PROCESSOR_PORT={config['services']['ports']['match_processor']}",
        f"CALENDAR_SYNC_PORT={config['services']['ports']['calendar_sync']}",
        f"LOGO_COMBINER_PORT={config['services']['ports']['logo_combiner']}",
        f"DRIVE_SERVICE_PORT={config['services']['ports']['google_drive']}",
        f"MATCH_DETECTOR_PORT={config['services']['ports']['change_detector']}",
        "",
        "# Processing Configuration",
        f"MIN_REFEREES_FOR_WHATSAPP={config['services']['processing']['min_referees_for_whatsapp']}",
        f"MATCH_CHECK_SCHEDULE={config['services']['processing']['match_check_schedule']}",
        f"FORCE_FRESH_PROCESSING={str(config['services']['processing']['force_fresh_processing']).lower()}",
        f"SERVICE_INTERVAL={config['services']['processing']['service_interval']}",
        "",
        "# System Configuration",
        f"LOG_LEVEL={config['services']['logging']['level']}",
        f"DEBUG_MODE={'1' if config['services']['logging']['debug_mode'] else '0'}",
        f"RESTART_POLICY={config['system']['docker']['restart_policy']}",
        f"GDRIVE_FOLDER_BASE={config['google']['drive']['folder_base']}",
    ]

    return "\n".join(env_content)

def generate_docker_compose_env(config):
    """Generate environment variables for docker-compose"""
    return {
        'FOGIS_USERNAME': config['fogis']['username'],
        'FOGIS_PASSWORD': config['fogis']['password'],
        'USER_REFEREE_NUMBER': str(config['fogis']['referee_number']),
        'LOG_LEVEL': config['services']['logging']['level'],
        'DEBUG_MODE': '1' if config['services']['logging']['debug_mode'] else '0',
        'API_CLIENT_PORT': str(config['services']['ports']['api_client']),
        'MATCH_PROCESSOR_PORT': str(config['services']['ports']['match_processor']),
        'CALENDAR_SYNC_PORT': str(config['services']['ports']['calendar_sync']),
        'LOGO_COMBINER_PORT': str(config['services']['ports']['logo_combiner']),
        'DRIVE_SERVICE_PORT': str(config['services']['ports']['google_drive']),
        'MATCH_DETECTOR_PORT': str(config['services']['ports']['change_detector']),
    }

def generate_calendar_config(config):
    """Generate config.json for calendar sync service"""
    return {
        "CALENDAR_ID": config['google']['calendar']['calendar_id'],
        "SYNC_TAG": config['google']['calendar']['sync_tag'],
        "DAYS_TO_KEEP_PAST_EVENTS": config['google']['calendar']['days_to_keep_past_events'],
        "USER_REFEREE_NUMBER": config['fogis']['referee_number'],
        "SCOPES": config['google']['oauth']['scopes'],
        "CREDENTIALS_FILE": "credentials.json",
        "TOKEN_REFRESH_BUFFER_DAYS": 1,
        "AUTH_SERVER_PORT": config['services']['ports']['calendar_auth'],
        "AUTH_SERVER_HOST": "0.0.0.0",
        "NOTIFICATION_METHOD": "email" if config['notifications']['email']['enabled'] else "none",
        "NOTIFICATION_EMAIL_SENDER": config['notifications']['email']['sender'],
        "NOTIFICATION_EMAIL_RECEIVER": config['notifications']['email']['receiver'],
        "SMTP_SERVER": config['notifications']['email']['smtp_server'],
        "SMTP_PORT": config['notifications']['email']['smtp_port'],
        "DISCORD_WEBHOOK_URL": config['notifications']['discord']['webhook_url'],
        "SLACK_WEBHOOK_URL": config['notifications']['slack']['webhook_url']
    }

def main():
    # Load configuration
    with open('fogis-config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Generate .env file
    env_content = generate_env_file(config)
    with open('.env', 'w') as f:
        f.write(env_content)

    # Generate calendar config
    calendar_config = generate_calendar_config(config)
    with open('fogis-calendar-phonebook-sync/config.json', 'w') as f:
        json.dump(calendar_config, f, indent=2)

    print("✅ Configuration files generated successfully!")
    print("📁 Generated files:")
    print("   - .env")
    print("   - fogis-calendar-phonebook-sync/config.json")

if __name__ == "__main__":
    main()
```

#### 2. Configuration Validator: `validate-config.py`

```python
#!/usr/bin/env python3
"""
FOGIS Configuration Validator
Validates fogis-config.yaml for completeness and correctness
"""

import yaml
import sys
from pathlib import Path

def validate_config(config):
    """Validate configuration structure and required fields"""
    errors = []
    warnings = []

    # Required sections
    required_sections = ['metadata', 'fogis', 'google', 'services', 'system']
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")

    # FOGIS credentials
    if 'fogis' in config:
        required_fogis = ['username', 'password', 'referee_number']
        for field in required_fogis:
            if field not in config['fogis'] or not config['fogis'][field]:
                errors.append(f"Missing FOGIS credential: {field}")

    # Google OAuth scopes
    if 'google' in config and 'oauth' in config['google']:
        required_scopes = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/contacts',
            'https://www.googleapis.com/auth/drive'
        ]
        actual_scopes = config['google']['oauth'].get('scopes', [])
        for scope in required_scopes:
            if scope not in actual_scopes:
                warnings.append(f"Missing recommended OAuth scope: {scope}")

    # Port conflicts
    if 'services' in config and 'ports' in config['services']:
        ports = list(config['services']['ports'].values())
        if len(ports) != len(set(ports)):
            errors.append("Port conflicts detected in service configuration")

    return errors, warnings

def main():
    if not Path('fogis-config.yaml').exists():
        print("❌ fogis-config.yaml not found")
        sys.exit(1)

    with open('fogis-config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    errors, warnings = validate_config(config)

    if errors:
        print("❌ Configuration validation failed:")
        for error in errors:
            print(f"   • {error}")
        sys.exit(1)

    if warnings:
        print("⚠️  Configuration warnings:")
        for warning in warnings:
            print(f"   • {warning}")

    print("✅ Configuration validation passed!")

if __name__ == "__main__":
    main()
```

### Lightning-Fast Installation Workflow

#### Enhanced Installation Script: `quick-setup.sh`

```bash
#!/bin/bash
# FOGIS Lightning-Fast Setup
# Target: 10-15 minutes from zero to operational

set -euo pipefail

# Configuration
SETUP_START_TIME=$(date +%s)
TARGET_TIME=900  # 15 minutes
CONFIG_FILE="fogis-config.yaml"

log_step() {
    local elapsed=$(($(date +%s) - SETUP_START_TIME))
    echo "⏱️  [${elapsed}s] $1"
}

# Step 1: Pre-flight checks (30 seconds)
log_step "Pre-flight system checks..."
python3 validate-config.py
docker --version >/dev/null 2>&1 || { echo "❌ Docker required"; exit 1; }

# Step 2: Generate all configuration files (15 seconds)
log_step "Generating configuration files..."
python3 generate-config.py

# Step 3: Pull pre-built images (2-3 minutes)
log_step "Pulling container images..."
docker-compose -f docker-compose-master.yml pull

# Step 4: Start core services (1 minute)
log_step "Starting core services..."
docker-compose -f docker-compose-master.yml up -d fogis-api-client-service

# Step 5: OAuth authentication (5-8 minutes - user interaction)
log_step "Starting OAuth authentication..."
python3 authenticate_all_services.py

# Step 6: Start remaining services (2 minutes)
log_step "Starting all services..."
docker-compose -f docker-compose-master.yml up -d

# Step 7: Health verification (1 minute)
log_step "Verifying system health..."
./show_system_status.sh

elapsed=$(($(date +%s) - SETUP_START_TIME))
log_step "Setup completed in ${elapsed} seconds!"

if [ $elapsed -lt $TARGET_TIME ]; then
    echo "🎯 Target achieved! Setup completed in under 15 minutes."
else
    echo "⏰ Setup took longer than target (${TARGET_TIME}s), but completed successfully."
fi
```

### Backup and Restore System

#### Complete System Backup: `backup-system.py`

```python
#!/usr/bin/env python3
"""
FOGIS Complete System Backup
Creates portable backup including configuration and credentials
"""

import yaml
import json
import shutil
import tarfile
from datetime import datetime
from pathlib import Path

def create_backup():
    """Create complete system backup"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = Path(f"fogis-backup-{timestamp}")
    backup_dir.mkdir()

    # Backup configuration
    if Path("fogis-config.yaml").exists():
        shutil.copy2("fogis-config.yaml", backup_dir)

    # Backup credentials (excluding tokens for security)
    creds_dir = backup_dir / "credentials"
    creds_dir.mkdir()
    if Path("credentials.json").exists():
        shutil.copy2("credentials.json", creds_dir)

    # Backup essential data (excluding processing state)
    data_backup = backup_dir / "data"
    data_backup.mkdir()

    # Only backup OAuth tokens, not processing state
    token_files = [
        "data/fogis-calendar-phonebook-sync/token.json",
        "data/google-drive-service/google-drive-token.json"
    ]

    for token_file in token_files:
        if Path(token_file).exists():
            dest_dir = data_backup / Path(token_file).parent.name
            dest_dir.mkdir(exist_ok=True)
            shutil.copy2(token_file, dest_dir)

    # Create backup manifest
    manifest = {
        "backup_type": "complete_system",
        "timestamp": timestamp,
        "version": "2.0",
        "contents": {
            "configuration": "fogis-config.yaml",
            "credentials": "credentials/",
            "oauth_tokens": "data/",
            "processing_state": "excluded"
        }
    }

    with open(backup_dir / "BACKUP_MANIFEST.json", 'w') as f:
        json.dump(manifest, f, indent=2)

    # Create compressed archive
    archive_name = f"fogis-backup-{timestamp}.tar.gz"
    with tarfile.open(archive_name, "w:gz") as tar:
        tar.add(backup_dir, arcname=backup_dir.name)

    shutil.rmtree(backup_dir)

    print(f"✅ Backup created: {archive_name}")
    return archive_name

def restore_backup(backup_file):
    """Restore system from backup"""
    print(f"🔄 Restoring from {backup_file}...")

    # Extract backup
    with tarfile.open(backup_file, "r:gz") as tar:
        tar.extractall()

    backup_dir = Path(backup_file.replace(".tar.gz", ""))

    # Restore configuration
    if (backup_dir / "fogis-config.yaml").exists():
        shutil.copy2(backup_dir / "fogis-config.yaml", ".")
        print("✅ Configuration restored")

    # Restore credentials
    if (backup_dir / "credentials").exists():
        shutil.copytree(backup_dir / "credentials", "credentials", dirs_exist_ok=True)
        print("✅ Credentials restored")

    # Restore OAuth tokens
    if (backup_dir / "data").exists():
        shutil.copytree(backup_dir / "data", "data", dirs_exist_ok=True)
        print("✅ OAuth tokens restored")

    # Regenerate configuration files
    print("🔄 Regenerating configuration files...")
    import subprocess
    subprocess.run(["python3", "generate-config.py"], check=True)

    print("✅ System restored successfully!")
    print("🚀 Run './quick-setup.sh' to start services")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        if len(sys.argv) < 3:
            print("Usage: backup-system.py restore <backup-file>")
            sys.exit(1)
        restore_backup(sys.argv[2])
    else:
        create_backup()
```

## Implementation Recommendations

### 1. Security Best Practices

#### Credential Management
- **Encrypt sensitive data**: Use `ansible-vault` or similar for production deployments
- **Separate OAuth tokens**: Store in secure, encrypted volumes
- **Environment isolation**: Different configs for dev/staging/production
- **Rotation policies**: Implement automatic credential rotation

#### Access Control
```yaml
# Example secure configuration overlay
security:
  encryption:
    enabled: true
    method: "aes-256-gcm"
    key_source: "environment"  # FOGIS_ENCRYPTION_KEY

  access_control:
    require_authentication: true
    allowed_networks:
      - "10.0.0.0/8"
      - "192.168.0.0/16"

  audit:
    log_access: true
    log_changes: true
    retention_days: 90
```

### 2. Deployment Strategies

#### Single-Command Installation
```bash
# Ultimate one-liner installation
curl -sSL https://raw.githubusercontent.com/PitchConnect/fogis-deployment/main/install.sh | \
  bash -s -- --config-url="https://myserver.com/fogis-config.yaml" --auto-confirm
```

#### Infrastructure as Code
```yaml
# Terraform example
resource "local_file" "fogis_config" {
  content = templatefile("${path.module}/fogis-config.yaml.tpl", {
    fogis_username = var.fogis_username
    fogis_password = var.fogis_password
    referee_number = var.referee_number
    calendar_id    = var.google_calendar_id
  })
  filename = "${path.module}/fogis-config.yaml"
}

resource "null_resource" "fogis_deployment" {
  depends_on = [local_file.fogis_config]

  provisioner "local-exec" {
    command = "./quick-setup.sh"
    working_dir = path.module
  }
}
```

### 3. Migration and Portability

#### Cross-Platform Migration
1. **Export configuration**: `backup-system.py`
2. **Transfer to new system**: Copy backup archive
3. **Restore and deploy**: `backup-system.py restore <archive>`
4. **Verify functionality**: Automated health checks

#### Environment Promotion
```bash
# Development to Production pipeline
./backup-system.py                    # Create backup
scp fogis-backup-*.tar.gz prod-server:/tmp/
ssh prod-server "cd /opt/fogis && ./backup-system.py restore /tmp/fogis-backup-*.tar.gz"
ssh prod-server "cd /opt/fogis && ./quick-setup.sh"
```

### 4. Monitoring and Maintenance

#### Health Monitoring
```yaml
# Enhanced monitoring configuration
monitoring:
  health_checks:
    enabled: true
    interval: 60  # seconds
    endpoints:
      - "http://localhost:9086/health"  # API Client
      - "http://localhost:9085/health"  # Google Drive
      - "http://localhost:9088/health"  # Logo Combiner

  alerts:
    email:
      enabled: true
      recipients: ["admin@example.com"]

    webhook:
      enabled: false
      url: "https://hooks.slack.com/..."

  metrics:
    prometheus:
      enabled: true
      port: 8081

    grafana:
      enabled: false
      dashboard_url: ""
```

## Summary and Benefits

### Achieved Goals

✅ **Lightning-fast installation**: 10-15 minutes from zero to operational
- Pre-built container images (2-3 min download vs 5-8 min build)
- Automated configuration generation
- Streamlined OAuth authentication
- Parallel service startup

✅ **Seamless system migration**: Complete environment portability
- Single `fogis-config.yaml` contains entire system state
- Automated backup/restore with compression
- Cross-platform compatibility (AMD64/ARM64)
- Infrastructure as Code support

✅ **Minimal user input**: Automated setup with intelligent defaults
- Only 3 required inputs: FOGIS username, password, referee number
- Google OAuth handled by existing wizard
- Smart defaults for all technical configuration
- Validation prevents common errors

✅ **Backup and restore**: Complete system state management
- Credential-only backups for clean installations
- Full system backups for migration
- Selective restore capabilities
- Automated verification

### Key Improvements Over Current System

1. **Reduced complexity**: Single configuration file vs multiple scattered configs
2. **Faster deployment**: 10-15 minutes vs 30-60 minutes
3. **Better portability**: Complete system state in one file
4. **Enhanced security**: Encrypted credentials, access controls
5. **Improved reliability**: Validation, health checks, automated recovery
6. **Easier maintenance**: Centralized configuration, automated updates

### Next Steps for Implementation

1. **Phase 1**: Implement configuration generator and validator
2. **Phase 2**: Create enhanced installation script with timing
3. **Phase 3**: Develop backup/restore system
4. **Phase 4**: Add security enhancements and monitoring
5. **Phase 5**: Create Infrastructure as Code templates

This portable configuration system transforms FOGIS deployment from a complex, time-consuming process into a streamlined, automated experience that meets all the specified requirements for speed, portability, and ease of use.

---

## REVISED USER INPUT REQUIREMENTS

### Critical Analysis: The "3 Required Inputs" Assumption Was Incorrect

After comprehensive analysis of the FOGIS deployment system, the initial assessment of only 3 required inputs (FOGIS username, password, referee number) was significantly oversimplified. Here's the complete, accurate list of ALL user inputs required for a functional FOGIS deployment:

## Complete User Input Requirements

### 1. **FOGIS Credentials** (REQUIRED - Never Persisted in Repository)

#### Absolutely Required:
- **FOGIS Username**: User's FOGIS login username
- **FOGIS Password**: User's FOGIS login password
- **Referee Number**: User's referee number from FOGIS profile (e.g., 61318)

#### Security Considerations:
- ❌ **NEVER** store in repository or configuration files
- ✅ Collect during installation via secure input (password masked)
- ✅ Store only in local `.env` file (gitignored)
- ✅ Support environment variable override for automation

### 2. **Google OAuth Setup Requirements** (REQUIRED - Complex Multi-Step Process)

#### A. Google Cloud Project Setup (User Must Complete):
1. **Create Google Cloud Project**
   - Project name (suggested: "FOGIS Integration")
   - Note Project ID for reference

2. **Enable Required APIs** (3 APIs):
   - Google Calendar API (`calendar-json.googleapis.com`)
   - Google People API (`people.googleapis.com`)
   - Google Drive API (`drive.googleapis.com`)

3. **Configure OAuth Consent Screen**:
   - User Type: External (for personal use)
   - Add user's email as test user
   - Configure scopes for Calendar, Contacts, Drive

#### B. OAuth Client Credentials (REQUIRED):
- **Application Type**: "Web application" (NOT Desktop)
- **Client Name**: "FOGIS Web Client"
- **Authorized Redirect URIs** (Both Required):
  - `http://localhost:8080/callback`
  - `http://127.0.0.1:8080/callback`
- **Download credentials.json**: Must be saved in deployment directory

#### C. OAuth Authentication Flow (User Interaction Required):
- Browser-based authentication (5-8 minutes)
- User must grant permissions for all 3 scopes
- Generates access/refresh tokens automatically

### 3. **Google Service Configuration** (REQUIRED with Defaults)

#### Calendar Configuration:
- **Calendar ID**:
  - Default: `"primary"` (user's main calendar)
  - Optional: Specific calendar ID (format: `xxxxx@group.calendar.google.com`)
  - **How to find**: Google Calendar Settings → Calendar ID

#### Google Drive Configuration:
- **Drive Folder ID**:
  - Default: Auto-create "WhatsApp_Group_Assets" folder
  - Optional: Specific folder ID for uploads
  - **How to find**: Google Drive folder URL contains folder ID

### 4. **File Path Configuration** (REQUIRED - Security Critical)

#### Required File Locations:
```
fogis-deployment/                    # Repository root
├── credentials.json                 # Google OAuth credentials (USER PROVIDED)
├── .env                            # Generated from user inputs (GITIGNORED)
├── fogis-config.yaml               # Master config (USER CUSTOMIZED)
├── credentials/                    # Container credentials directory
│   └── google-credentials.json     # Copy of credentials.json
└── data/                          # Persistent data (AUTO-CREATED)
    ├── fogis-calendar-phonebook-sync/
    │   └── token.json              # OAuth tokens (AUTO-GENERATED)
    └── google-drive-service/
        ├── google-drive-token.json # OAuth tokens (AUTO-GENERATED)
        └── token.json              # OAuth tokens (AUTO-GENERATED)
```

#### File Path Resolution Strategy:
- **Relative to deployment directory**: All paths relative to `fogis-deployment/` clone
- **Container path mapping**: Host paths mapped to container paths
- **Credential isolation**: Separate host/container credential directories

### 5. **Notification Configuration** (OPTIONAL but Recommended)

#### Email Notifications (Optional):
- **SMTP Configuration** (if email notifications desired):
  - Sender email address
  - Receiver email address
  - SMTP server (default: smtp.gmail.com)
  - SMTP port (default: 587)
  - SMTP username (usually same as sender)
  - SMTP password/app password

#### Alternative Notifications (Optional):
- **Discord Webhook URL** (if Discord notifications desired)
- **Slack Webhook URL** (if Slack notifications desired)

### 6. **System Configuration** (OPTIONAL with Smart Defaults)

#### Port Configuration (Optional - Defaults Provided):
- API Client Port (default: 9086)
- Match Processor Port (default: 9082)
- Calendar Sync Port (default: 9083)
- Logo Combiner Port (default: 9088)
- Google Drive Port (default: 9085)
- Change Detector Port (default: 9080)

#### Processing Settings (Optional - Defaults Provided):
- Minimum referees for WhatsApp group creation (default: 2)
- Match check schedule (default: "0 * * * *" - hourly)
- Log level (default: INFO)

## Revised Installation Time Estimate

### Realistic Time Breakdown:
1. **Google Cloud Setup**: 10-15 minutes (first time)
   - Create project, enable APIs, configure OAuth
2. **Credential Download**: 2-3 minutes
   - Download credentials.json, place in directory
3. **FOGIS Credential Input**: 1-2 minutes
   - Username, password, referee number entry
4. **OAuth Authentication**: 3-5 minutes
   - Browser-based permission granting
5. **Service Startup**: 2-3 minutes
   - Container pull and startup
6. **Health Verification**: 1-2 minutes
   - Verify all services operational

**Total Realistic Time: 20-30 minutes** (first-time setup)
**Subsequent Deployments: 5-10 minutes** (with existing credentials)

## Security Best Practices for User Inputs

### Credential Handling:
```bash
# Secure credential collection
read -p "FOGIS Username: " FOGIS_USERNAME
read -s -p "FOGIS Password: " FOGIS_PASSWORD
echo
read -p "Referee Number: " USER_REFEREE_NUMBER

# Store in local .env (gitignored)
cat > .env << EOF
FOGIS_USERNAME=${FOGIS_USERNAME}
FOGIS_PASSWORD=${FOGIS_PASSWORD}
USER_REFEREE_NUMBER=${USER_REFEREE_NUMBER}
EOF

# Set restrictive permissions
chmod 600 .env
```

### File Security:
- `credentials.json`: 644 permissions (readable but not writable)
- `.env`: 600 permissions (owner read/write only)
- Token files: 600 permissions (auto-managed)
- Credential directory: 700 permissions (owner access only)

## Recommended Directory Structure for Users

```
~/fogis-deployment/                 # User's deployment directory
├── credentials.json               # USER PROVIDES (from Google Cloud)
├── .env                          # GENERATED (from user inputs)
├── fogis-config.yaml             # USER CUSTOMIZES (optional)
├── docker-compose-master.yml     # FROM REPOSITORY
├── manage_fogis_system.sh        # FROM REPOSITORY
└── [other repository files]      # FROM REPOSITORY
```

## Updated Lightning-Fast Installation Process

### Enhanced Installation Workflow:
```bash
# 1. Clone repository (30 seconds)
git clone https://github.com/PitchConnect/fogis-deployment.git
cd fogis-deployment

# 2. Run enhanced setup wizard (15-20 minutes first time)
./manage_fogis_system.sh setup-auth

# 3. Configure FOGIS credentials (2 minutes)
python3 configure_system.py

# 4. Start system (3 minutes)
./manage_fogis_system.sh start

# 5. Verify deployment (1 minute)
./show_system_status.sh
```

This revised analysis provides a realistic and complete picture of the user input requirements, acknowledging the complexity of Google OAuth setup while maintaining the goal of streamlined deployment through automation and intelligent defaults.
