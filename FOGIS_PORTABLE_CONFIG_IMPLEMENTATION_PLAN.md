# FOGIS Portable Configuration System - Implementation Plan

## Executive Summary

This implementation plan provides a detailed roadmap for integrating the portable configuration system into the existing fogis-deployment repository while preserving existing functionality and maintaining backward compatibility.

## 1. Current State Assessment

### Existing Repository Structure Analysis

#### ✅ **Strong Foundation Elements**
- **Comprehensive management scripts**: `manage_fogis_system.sh`, `setup_fogis_system.sh`
- **Enhanced OAuth wizard**: `lib/enhanced_oauth_wizard.py` with browser automation
- **Multi-platform support**: `platform_manager.py`, headless deployment capabilities
- **Robust testing framework**: Unit, integration, and e2e tests
- **Docker orchestration**: `docker-compose.yml` with health checks
- **Installation safety**: Backup/restore, conflict detection, rollback capabilities

#### ⚠️ **Current Configuration Approach**
- **Scattered configuration**: Multiple files (`.env`, `config.json`, docker-compose variables)
- **Manual credential management**: `configure_system.py` for interactive setup
- **Limited portability**: No single source of truth for system state
- **Complex migration**: No standardized backup/restore for complete system state

#### 🔧 **Key Integration Points**
1. **`setup_fogis_system.sh`**: Main setup orchestration (1,072 lines)
2. **`configure_system.py`**: Interactive configuration collection (198 lines)
3. **`manage_fogis_system.sh`**: System management commands (308 lines)
4. **`lib/enhanced_oauth_wizard.py`**: OAuth automation
5. **`docker-compose.yml`**: Service orchestration with environment variables

### Compatibility Analysis

#### ✅ **Compatible Components**
- **OAuth wizard**: Can be enhanced to work with YAML configuration
- **Docker compose**: Already uses environment variable substitution
- **Management scripts**: Can be extended to support both configuration methods
- **Testing framework**: Can validate both old and new configuration approaches

#### ⚠️ **Potential Conflicts**
- **Environment variable precedence**: Need clear hierarchy (YAML → .env → environment)
- **Configuration validation**: Current validation in multiple places
- **File path assumptions**: Some scripts assume specific file locations
- **Backup/restore**: Current approach doesn't handle YAML configuration

## 2. Integration Strategy

### Core Principles

1. **Backward Compatibility**: Existing `.env` + `config.json` approach continues to work
2. **Gradual Migration**: Users can opt-in to portable configuration system
3. **Enhanced Functionality**: New system provides additional capabilities
4. **Preservation of Investments**: Leverage existing OAuth wizard, management scripts
5. **Clear Migration Path**: Automated conversion from old to new configuration

### Configuration Hierarchy Strategy

```
Priority Order (Highest to Lowest):
1. Environment Variables (runtime overrides)
2. fogis-config.yaml (portable configuration)
3. .env file (legacy configuration)
4. Default values (hardcoded fallbacks)
```

### Dual-Mode Operation

#### Legacy Mode (Current Behavior)
- Uses existing `.env` + `config.json` approach
- All current scripts work unchanged
- No new dependencies required

#### Portable Mode (New Capability)
- Uses `fogis-config.yaml` as single source of truth
- Generates `.env` and `config.json` automatically
- Enhanced backup/restore capabilities
- Infrastructure as Code support

### Detection Logic

```python
def detect_configuration_mode():
    """Detect which configuration mode to use"""
    if os.path.exists('fogis-config.yaml'):
        return 'portable'
    elif os.path.exists('.env'):
        return 'legacy'
    else:
        return 'new_installation'
```

## 3. Implementation Phases

### Phase 1: Foundation and Core Components (Week 1-2)

#### Objectives
- Establish portable configuration infrastructure
- Create configuration management tools
- Ensure backward compatibility

#### Deliverables

##### A. Configuration Management Library (`lib/config_manager.py`)
```python
class ConfigManager:
    """Unified configuration management for both legacy and portable modes"""

    def __init__(self):
        self.mode = self.detect_mode()
        self.config = self.load_configuration()

    def detect_mode(self):
        """Auto-detect configuration mode"""
        if os.path.exists('fogis-config.yaml'):
            return 'portable'
        elif os.path.exists('.env'):
            return 'legacy'
        return 'new_installation'

    def load_configuration(self):
        """Load configuration based on detected mode"""
        if self.mode == 'portable':
            return self.load_yaml_config()
        elif self.mode == 'legacy':
            return self.load_legacy_config()
        return self.get_default_config()

    def get_value(self, key, default=None):
        """Get configuration value with hierarchy support"""
        # 1. Environment variables (highest priority)
        env_value = os.environ.get(key)
        if env_value is not None:
            return env_value

        # 2. Configuration file (YAML or legacy)
        config_value = self.config.get(key, default)
        return config_value
```

##### B. Configuration Generator (`lib/config_generator.py`)
```python
class ConfigGenerator:
    """Generate configuration files from fogis-config.yaml"""

    def generate_env_file(self, config):
        """Generate .env file from YAML configuration"""
        # Implementation from design document

    def generate_docker_compose_env(self, config):
        """Generate environment variables for docker-compose"""
        # Implementation from design document

    def generate_calendar_config(self, config):
        """Generate config.json for calendar sync service"""
        # Implementation from design document
```

##### C. Configuration Validator (`lib/config_validator.py`)
```python
class ConfigValidator:
    """Validate configuration completeness and correctness"""

    def validate_config(self, config):
        """Comprehensive configuration validation"""
        errors = []
        warnings = []

        # Validate required sections
        # Validate FOGIS credentials
        # Validate Google OAuth configuration
        # Check for port conflicts
        # Validate file paths

        return errors, warnings
```

#### Testing Strategy
- Unit tests for all configuration management components
- Integration tests with existing scripts
- Backward compatibility tests with current `.env` approach

### Phase 2: Script Integration and Enhancement (Week 3-4)

#### Objectives
- Integrate portable configuration with existing scripts
- Enhance management commands
- Add migration capabilities

#### Deliverables

##### A. Enhanced Setup Script (`setup_fogis_system.sh` modifications)
```bash
# Add configuration mode detection
detect_config_mode() {
    if [[ -f "fogis-config.yaml" ]]; then
        echo "portable"
    elif [[ -f ".env" ]]; then
        echo "legacy"
    else
        echo "new_installation"
    fi
}

# Enhanced credential setup
setup_credentials() {
    local config_mode=$(detect_config_mode)

    case $config_mode in
        "portable")
            setup_portable_credentials
            ;;
        "legacy")
            setup_legacy_credentials
            ;;
        "new_installation")
            offer_configuration_choice
            ;;
    esac
}
```

##### B. Enhanced Management Script (`manage_fogis_system.sh` additions)
```bash
# New commands for portable configuration
case "$1" in
    # ... existing commands ...

    config-init)
        print_info "Initializing portable configuration..."
        python3 lib/config_manager.py init
        ;;
    config-migrate)
        print_info "Migrating from legacy to portable configuration..."
        python3 lib/config_manager.py migrate
        ;;
    config-validate)
        print_info "Validating configuration..."
        python3 lib/config_validator.py
        ;;
    config-generate)
        print_info "Generating configuration files..."
        python3 lib/config_generator.py
        ;;
    backup-config)
        print_info "Creating configuration backup..."
        python3 lib/backup_manager.py create
        ;;
    restore-config)
        print_info "Restoring configuration from backup..."
        python3 lib/backup_manager.py restore "$2"
        ;;
esac
```

##### C. Migration Tool (`lib/migration_tool.py`)
```python
class MigrationTool:
    """Migrate from legacy to portable configuration"""

    def migrate_legacy_to_portable(self):
        """Convert .env + config.json to fogis-config.yaml"""
        # Load existing configuration
        legacy_config = self.load_legacy_config()

        # Convert to YAML structure
        yaml_config = self.convert_to_yaml_structure(legacy_config)

        # Validate converted configuration
        validator = ConfigValidator()
        errors, warnings = validator.validate_config(yaml_config)

        if not errors:
            # Save YAML configuration
            self.save_yaml_config(yaml_config)

            # Backup legacy files
            self.backup_legacy_files()

            print("✅ Migration completed successfully!")
        else:
            print("❌ Migration failed due to validation errors:")
            for error in errors:
                print(f"   • {error}")
```

#### Testing Strategy
- Test script integration with both configuration modes
- Validate migration tool with various legacy configurations
- End-to-end testing of enhanced management commands

### Phase 3: OAuth Integration and User Experience (Week 5-6)

#### Objectives
- Integrate portable configuration with OAuth wizard
- Enhance user experience for configuration setup
- Add intelligent defaults and validation

#### Deliverables

##### A. Enhanced OAuth Wizard (`lib/enhanced_oauth_wizard.py` modifications)
```python
class EnhancedOAuthWizard:
    """Enhanced OAuth wizard with portable configuration support"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.mode = self.config_manager.mode

    def run_wizard(self):
        """Run OAuth setup wizard based on configuration mode"""
        if self.mode == 'portable':
            return self.run_portable_wizard()
        else:
            return self.run_legacy_wizard()

    def run_portable_wizard(self):
        """OAuth wizard for portable configuration mode"""
        print("🚀 Enhanced OAuth Setup (Portable Configuration)")

        # Check if fogis-config.yaml exists and has OAuth section
        if self.has_oauth_config():
            print("✅ Found existing OAuth configuration")
            if not self.prompt_reconfigure():
                return True

        # Guide user through OAuth setup
        oauth_config = self.collect_oauth_config()

        # Update fogis-config.yaml
        self.update_yaml_config(oauth_config)

        # Generate configuration files
        generator = ConfigGenerator()
        generator.generate_all_configs()

        # Run OAuth flow
        return self.execute_oauth_flow()
```

##### B. Interactive Configuration Setup (`lib/interactive_setup.py`)
```python
class InteractiveSetup:
    """Interactive setup wizard for new installations"""

    def run_setup_wizard(self):
        """Run complete setup wizard for new users"""
        print("🎯 FOGIS Configuration Setup Wizard")
        print("=" * 50)

        # Step 1: Choose configuration mode
        mode = self.choose_configuration_mode()

        if mode == 'portable':
            return self.setup_portable_configuration()
        else:
            return self.setup_legacy_configuration()

    def choose_configuration_mode(self):
        """Let user choose between portable and legacy configuration"""
        print("\n📋 Configuration Mode Selection")
        print("1. Portable Configuration (Recommended)")
        print("   ✅ Single configuration file")
        print("   ✅ Easy backup and migration")
        print("   ✅ Infrastructure as Code support")
        print("   ✅ Enhanced validation")
        print()
        print("2. Legacy Configuration (Current approach)")
        print("   ⚠️  Multiple configuration files")
        print("   ⚠️  Manual backup required")
        print()

        while True:
            choice = input("Choose configuration mode (1/2) [1]: ").strip() or "1"
            if choice in ["1", "2"]:
                return "portable" if choice == "1" else "legacy"
            print("❌ Invalid choice. Please enter 1 or 2.")

    def setup_portable_configuration(self):
        """Setup portable configuration from scratch"""
        # Collect all required configuration
        config = self.collect_complete_configuration()

        # Validate configuration
        validator = ConfigValidator()
        errors, warnings = validator.validate_config(config)

        if errors:
            print("❌ Configuration validation failed:")
            for error in errors:
                print(f"   • {error}")
            return False

        # Save configuration
        self.save_yaml_config(config)

        # Generate derived configuration files
        generator = ConfigGenerator()
        generator.generate_all_configs()

        print("✅ Portable configuration setup completed!")
        return True
```

##### C. Configuration Templates (`templates/`)
```yaml
# templates/fogis-config.template.yaml
# FOGIS Deployment Configuration Template
# Copy this file to fogis-config.yaml and customize

metadata:
  version: "2.0"
  created: "{{ timestamp }}"
  description: "FOGIS Complete System Configuration"

# FOGIS Authentication (REQUIRED)
fogis:
  username: "{{ fogis_username | default('') }}"
  password: "{{ fogis_password | default('') }}"
  referee_number: {{ referee_number | default(0) }}

# Google Integration (REQUIRED)
google:
  oauth:
    client_type: "web_application"
    scopes:
      - "https://www.googleapis.com/auth/calendar"
      - "https://www.googleapis.com/auth/contacts"
      - "https://www.googleapis.com/auth/drive"

  calendar:
    calendar_id: "{{ calendar_id | default('primary') }}"
    sync_tag: "FOGIS_CALENDAR_SYNC"
    days_to_keep_past_events: 7

  drive:
    folder_base: "WhatsApp_Group_Assets"
    auto_create_folders: true

# Service Configuration
services:
  ports:
    api_client: 9086
    match_processor: 9082
    calendar_sync: 9083
    calendar_auth: 9084
    calendar_web_trigger: 9087
    logo_combiner: 9088
    google_drive: 9085
    change_detector: 9080

  processing:
    min_referees_for_whatsapp: 2
    match_check_schedule: "0 * * * *"
    force_fresh_processing: true
    service_interval: 300

  logging:
    level: "INFO"
    debug_mode: false
    verbose_logging: false

# System Configuration
system:
  docker:
    restart_policy: "unless-stopped"
    network_name: "fogis-network"
    use_ghcr_images: true

  paths:
    data: "/app/data"
    logs: "/app/logs"
    credentials: "/app/credentials"
    temp: "/tmp"

# Notification Configuration (Optional)
notifications:
  email:
    enabled: false
    sender: "{{ email_sender | default('') }}"
    receiver: "{{ email_receiver | default('') }}"
    smtp_server: "smtp.gmail.com"
    smtp_port: 587

# Backup Configuration
backup:
  enabled: true
  retention_days: 30
  include_logs: false
  include_processing_state: false
```

#### Testing Strategy
- Test OAuth wizard with both configuration modes
- Validate interactive setup wizard with various user inputs
- Test template generation and customization

### Phase 4: Backup/Restore and Advanced Features (Week 7-8)

#### Objectives
- Implement comprehensive backup/restore system
- Add advanced features (Infrastructure as Code, monitoring)
- Complete testing and documentation

#### Deliverables

##### A. Backup/Restore System (`lib/backup_manager.py`)
```python
class BackupManager:
    """Complete system backup and restore capabilities"""

    def create_backup(self, backup_type='complete'):
        """Create system backup"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = Path(f"fogis-backup-{timestamp}")

        if backup_type == 'complete':
            return self.create_complete_backup(backup_dir)
        elif backup_type == 'config_only':
            return self.create_config_backup(backup_dir)
        elif backup_type == 'credentials_only':
            return self.create_credentials_backup(backup_dir)

    def create_complete_backup(self, backup_dir):
        """Create complete system backup including all state"""
        backup_dir.mkdir()

        # Backup configuration
        if Path("fogis-config.yaml").exists():
            shutil.copy2("fogis-config.yaml", backup_dir)

        # Backup credentials
        self.backup_credentials(backup_dir)

        # Backup OAuth tokens
        self.backup_oauth_tokens(backup_dir)

        # Backup processing state (optional)
        self.backup_processing_state(backup_dir)

        # Create manifest
        manifest = self.create_backup_manifest(backup_dir, 'complete')

        # Create compressed archive
        return self.create_archive(backup_dir)
```

##### B. Infrastructure as Code Support (`lib/iac_generator.py`)
```python
class IaCGenerator:
    """Generate Infrastructure as Code templates"""

    def generate_terraform(self, config):
        """Generate Terraform configuration"""
        terraform_template = """
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
"""
        return terraform_template

    def generate_ansible(self, config):
        """Generate Ansible playbook"""
        # Implementation for Ansible playbook generation

    def generate_docker_compose_override(self, config):
        """Generate docker-compose.override.yml for customizations"""
        # Implementation for Docker Compose overrides
```

#### Testing Strategy
- Test backup/restore with various system states
- Validate Infrastructure as Code templates
- Performance testing with large configurations

## 4. Realistic Constraints and Migration Strategy

### Addressing Revised User Input Requirements

#### Time Expectations Management

##### First-Time Installation Reality Check
```
Realistic Timeline Breakdown:
┌─────────────────────────────────────────────────────────────┐
│ Google Cloud Setup (First Time): 15-20 minutes             │
│ ├── Create project: 2-3 minutes                            │
│ ├── Enable APIs: 3-5 minutes                               │
│ ├── Configure OAuth consent: 5-7 minutes                   │
│ └── Create OAuth client: 3-5 minutes                       │
│                                                             │
│ FOGIS Configuration: 5-8 minutes                           │
│ ├── Download credentials.json: 1-2 minutes                 │
│ ├── Run setup wizard: 2-3 minutes                          │
│ ├── OAuth authentication flow: 2-3 minutes                 │
│ └── Service startup: 2-3 minutes                           │
│                                                             │
│ Total First-Time: 20-28 minutes                            │
│ Subsequent Deployments: 5-10 minutes                       │
└─────────────────────────────────────────────────────────────┘
```

##### Enhanced User Guidance
```python
class SetupTimeEstimator:
    """Provide realistic time estimates to users"""

    def estimate_setup_time(self):
        """Estimate setup time based on user's situation"""
        print("⏱️  Setup Time Estimation")
        print("=" * 30)

        has_google_project = self.ask_yes_no("Do you already have a Google Cloud project with APIs enabled?")
        has_credentials = self.ask_yes_no("Do you already have OAuth credentials (credentials.json)?")

        if has_google_project and has_credentials:
            print("🚀 Estimated time: 5-8 minutes")
            print("   You're ready for quick setup!")
        elif has_google_project:
            print("⏱️  Estimated time: 10-15 minutes")
            print("   Need to create OAuth credentials")
        else:
            print("⏰ Estimated time: 20-28 minutes")
            print("   Full Google Cloud setup required")
            print("\n📋 We'll guide you through each step!")
```

### Migration Path for Existing Users

#### Gradual Migration Strategy

##### Phase 1: Opt-in Introduction
```bash
# Add to manage_fogis_system.sh
show_portable_config_info() {
    if [[ ! -f "fogis-config.yaml" ]] && [[ -f ".env" ]]; then
        echo ""
        echo "💡 New Feature Available: Portable Configuration"
        echo "   ✅ Single configuration file"
        echo "   ✅ Easy backup and migration"
        echo "   ✅ Infrastructure as Code support"
        echo ""
        echo "   Run: ./manage_fogis_system.sh config-migrate"
        echo "   (Your current setup will continue working)"
        echo ""
    fi
}
```

##### Phase 2: Assisted Migration
```python
class AssistedMigration:
    """Help existing users migrate to portable configuration"""

    def run_migration_wizard(self):
        """Interactive migration wizard"""
        print("🔄 Migration to Portable Configuration")
        print("=" * 40)

        # Analyze current setup
        current_setup = self.analyze_current_setup()
        self.display_migration_benefits(current_setup)

        if not self.confirm_migration():
            print("Migration cancelled. Your current setup remains unchanged.")
            return False

        # Create backup
        print("📦 Creating backup of current configuration...")
        backup_file = self.create_pre_migration_backup()

        # Perform migration
        print("🔄 Converting configuration...")
        success = self.migrate_configuration()

        if success:
            print("✅ Migration completed successfully!")
            print(f"📦 Backup saved as: {backup_file}")
            print("🚀 Your system is now using portable configuration!")

            # Offer to test new configuration
            if self.ask_yes_no("Would you like to test the new configuration?"):
                self.test_migrated_configuration()
        else:
            print("❌ Migration failed. Restoring from backup...")
            self.restore_from_backup(backup_file)

        return success

    def analyze_current_setup(self):
        """Analyze current configuration setup"""
        analysis = {
            'has_env_file': os.path.exists('.env'),
            'has_config_json': os.path.exists('fogis-calendar-phonebook-sync/config.json'),
            'has_credentials': os.path.exists('credentials.json'),
            'has_tokens': self.check_oauth_tokens(),
            'services_running': self.check_running_services()
        }
        return analysis
```

### Constraint Handling Strategies

#### Resource and Complexity Management

##### Incremental Feature Rollout
```python
class FeatureFlags:
    """Manage feature rollout and complexity"""

    def __init__(self):
        self.features = {
            'portable_config': True,
            'iac_generation': False,  # Phase 4
            'advanced_monitoring': False,  # Phase 4
            'multi_environment': False,  # Future
        }

    def is_enabled(self, feature):
        """Check if feature is enabled"""
        return self.features.get(feature, False)
```

##### Complexity Reduction Strategies
```python
class ComplexityManager:
    """Reduce setup complexity through intelligent defaults"""

    def apply_smart_defaults(self, user_input):
        """Apply intelligent defaults based on user input"""
        config = self.get_base_config()

        # Smart port assignment
        config['services']['ports'] = self.assign_available_ports()

        # Intelligent notification setup
        if user_input.get('email'):
            config['notifications']['email'] = self.setup_email_defaults(user_input['email'])

        # Environment-specific optimizations
        if self.detect_environment() == 'development':
            config['services']['logging']['level'] = 'DEBUG'
            config['services']['logging']['debug_mode'] = True

        return config
```

## 5. Detailed Deliverables and File Specifications

### Phase 1 Deliverables (Foundation)

#### New Files to Create

##### `lib/config_manager.py` (New - 200 lines)
```python
#!/usr/bin/env python3
"""
Unified Configuration Manager for FOGIS Deployment
Supports both legacy (.env) and portable (YAML) configuration modes
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

class ConfigManager:
    """Unified configuration management"""

    def __init__(self):
        self.mode = self.detect_mode()
        self.config = self.load_configuration()
        self.env_vars = self.load_environment_variables()

    # Implementation as specified in Phase 1
```

##### `lib/config_generator.py` (New - 150 lines)
```python
#!/usr/bin/env python3
"""
Configuration File Generator
Generates .env, config.json, and docker-compose environment from YAML
"""

import yaml
import json
import os
from datetime import datetime
from pathlib import Path

class ConfigGenerator:
    """Generate configuration files from fogis-config.yaml"""

    # Implementation as specified in Phase 1
```

##### `lib/config_validator.py` (New - 120 lines)
```python
#!/usr/bin/env python3
"""
Configuration Validator
Validates fogis-config.yaml for completeness and correctness
"""

import yaml
import sys
import re
from pathlib import Path

class ConfigValidator:
    """Validate configuration structure and required fields"""

    # Implementation as specified in Phase 1
```

##### `templates/fogis-config.template.yaml` (New - 80 lines)
```yaml
# FOGIS Deployment Configuration Template
# Copy this file to fogis-config.yaml and customize
# Template as specified in Phase 3
```

#### Files to Modify

##### `setup_fogis_system.sh` (Modify - Add ~50 lines)
```bash
# Add after line 50 (after initial setup functions)

# Configuration mode detection
detect_config_mode() {
    if [[ -f "fogis-config.yaml" ]]; then
        echo "portable"
    elif [[ -f ".env" ]]; then
        echo "legacy"
    else
        echo "new_installation"
    fi
}

# Enhanced credential setup function
setup_credentials() {
    local config_mode=$(detect_config_mode)

    log_info "Configuration mode: $config_mode"

    case $config_mode in
        "portable")
            setup_portable_credentials
            ;;
        "legacy")
            setup_legacy_credentials
            ;;
        "new_installation")
            offer_configuration_choice
            ;;
    esac
}

# New functions for portable configuration
setup_portable_credentials() {
    log_info "Using portable configuration mode..."

    # Validate YAML configuration
    if ! python3 lib/config_validator.py; then
        log_error "Configuration validation failed"
        exit 1
    fi

    # Generate configuration files
    python3 lib/config_generator.py

    # Continue with existing credential setup
    setup_legacy_credentials
}

offer_configuration_choice() {
    log_info "New installation detected. Choose configuration mode:"
    echo "1. Portable Configuration (Recommended)"
    echo "2. Legacy Configuration"

    read -p "Choose mode (1/2) [1]: " choice
    choice=${choice:-1}

    case $choice in
        1)
            setup_new_portable_config
            ;;
        2)
            setup_legacy_credentials
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac
}

setup_new_portable_config() {
    log_info "Setting up portable configuration..."

    # Copy template
    cp templates/fogis-config.template.yaml fogis-config.yaml

    # Run interactive setup
    python3 lib/interactive_setup.py

    # Generate configuration files
    python3 lib/config_generator.py
}
```

##### `manage_fogis_system.sh` (Modify - Add ~30 lines)
```bash
# Add new commands to the case statement (around line 200)

    config-init)
        print_info "Initializing portable configuration..."
        if [[ -f "fogis-config.yaml" ]]; then
            print_warning "fogis-config.yaml already exists"
            read -p "Overwrite? (y/N): " confirm
            if [[ $confirm != "y" ]]; then
                print_info "Operation cancelled"
                exit 0
            fi
        fi
        cp templates/fogis-config.template.yaml fogis-config.yaml
        print_success "Portable configuration initialized"
        print_info "Edit fogis-config.yaml and run: $0 config-generate"
        ;;
    config-migrate)
        print_info "Migrating from legacy to portable configuration..."
        python3 lib/migration_tool.py
        ;;
    config-validate)
        print_info "Validating configuration..."
        python3 lib/config_validator.py
        ;;
    config-generate)
        print_info "Generating configuration files..."
        python3 lib/config_generator.py
        ;;
    backup-config)
        print_info "Creating configuration backup..."
        python3 lib/backup_manager.py create
        ;;
    restore-config)
        if [[ -z "$2" ]]; then
            print_error "Usage: $0 restore-config <backup-file>"
            exit 1
        fi
        print_info "Restoring configuration from backup..."
        python3 lib/backup_manager.py restore "$2"
        ;;

# Update show_usage function to include new commands
show_usage() {
    echo "🔧 FOGIS System Management"
    echo "=========================="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start           - Start all FOGIS services"
    echo "  stop            - Stop all FOGIS services"
    echo "  restart         - Restart all FOGIS services"
    echo "  status          - Show service status"
    echo "  logs            - Show logs for all services"
    echo "  logs [name]     - Show logs for specific service"
    echo "  test            - Run a test match processing"
    echo "  health          - Check health of all services"
    echo "  cron-add        - Add hourly cron job"
    echo "  cron-remove     - Remove cron job"
    echo "  cron-status     - Show cron job status"
    echo "  setup-auth      - Enhanced OAuth setup wizard (5-8 min setup)"
    echo ""
    echo "Configuration Management:"
    echo "  config-init     - Initialize portable configuration"
    echo "  config-migrate  - Migrate from legacy to portable config"
    echo "  config-validate - Validate configuration"
    echo "  config-generate - Generate config files from YAML"
    echo "  backup-config   - Create configuration backup"
    echo "  restore-config  - Restore from backup"
    echo ""
    echo "Other Commands:"
    echo "  clean           - Clean up Docker containers and images"
    echo "  check-updates   - Check for service updates"
    echo "  update          - Update services"
    echo "  version         - Show version information"
    echo "  rollback        - Rollback to previous version"
}
```

### Phase 2 Deliverables (Script Integration)

#### New Files to Create

##### `lib/migration_tool.py` (New - 180 lines)
```python
#!/usr/bin/env python3
"""
Migration Tool for Legacy to Portable Configuration
Converts .env + config.json to fogis-config.yaml
"""

import os
import yaml
import json
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

class MigrationTool:
    """Migrate from legacy to portable configuration"""

    # Implementation as specified in Phase 2
```

##### `lib/interactive_setup.py` (New - 250 lines)
```python
#!/usr/bin/env python3
"""
Interactive Setup Wizard for New Installations
Guides users through complete FOGIS configuration
"""

import os
import yaml
import getpass
from pathlib import Path

class InteractiveSetup:
    """Interactive setup wizard for new users"""

    # Implementation as specified in Phase 3
```

#### Files to Modify

##### `configure_system.py` (Modify - Add compatibility layer)
```python
# Add at the beginning of the file (after imports)

from lib.config_manager import ConfigManager

def main():
    """Enhanced main function with configuration mode detection"""
    config_manager = ConfigManager()

    if config_manager.mode == 'portable':
        print("✅ Portable configuration detected")
        print("   Configuration managed via fogis-config.yaml")
        print("   Run: ./manage_fogis_system.sh config-generate")
        return 0

    # Continue with existing legacy configuration logic
    print_header("FOGIS SYSTEM CONFIGURATION")
    print("Setting up FOGIS deployment configuration...")

    # ... rest of existing code
```

### Phase 3 Deliverables (OAuth Integration)

#### Files to Modify

##### `lib/enhanced_oauth_wizard.py` (Modify - Add portable config support)
```python
# Add portable configuration support to existing wizard

class EnhancedOAuthWizard:
    def __init__(self):
        # Add configuration manager
        from lib.config_manager import ConfigManager
        self.config_manager = ConfigManager()
        self.mode = self.config_manager.mode

    def run_wizard(self):
        """Enhanced run_wizard with portable config support"""
        if self.mode == 'portable':
            return self.run_portable_wizard()
        else:
            return self.run_legacy_wizard()

    def run_portable_wizard(self):
        """OAuth wizard for portable configuration mode"""
        # Implementation as specified in Phase 3

    def run_legacy_wizard(self):
        """Existing OAuth wizard logic"""
        # Keep existing implementation
```

### Phase 4 Deliverables (Advanced Features)

#### New Files to Create

##### `lib/backup_manager.py` (New - 200 lines)
```python
#!/usr/bin/env python3
"""
Backup and Restore Manager
Complete system backup and restore capabilities
"""

import os
import yaml
import json
import shutil
import tarfile
from datetime import datetime
from pathlib import Path

class BackupManager:
    """Complete system backup and restore capabilities"""

    # Implementation as specified in Phase 4
```

##### `lib/iac_generator.py` (New - 150 lines)
```python
#!/usr/bin/env python3
"""
Infrastructure as Code Generator
Generate Terraform, Ansible, and Docker Compose templates
"""

import yaml
import json
from pathlib import Path

class IaCGenerator:
    """Generate Infrastructure as Code templates"""

    # Implementation as specified in Phase 4
```

### Integration Testing Files

#### New Test Files to Create

##### `tests/unit/test_config_manager.py` (New - 100 lines)
##### `tests/unit/test_config_generator.py` (New - 80 lines)
##### `tests/unit/test_config_validator.py` (New - 90 lines)
##### `tests/integration/test_migration_tool.py` (New - 120 lines)
##### `tests/integration/test_portable_config_workflow.py` (New - 150 lines)
##### `tests/e2e/test_complete_portable_setup.py` (New - 200 lines)

### Documentation Updates

#### Files to Modify

##### `README.md` (Modify - Add portable configuration section)
```markdown
# Add new section after existing quick start

## 🚀 Portable Configuration (New!)

The enhanced FOGIS deployment now supports portable configuration for easier management and migration:

### Quick Start with Portable Configuration
```bash
# 1. Initialize portable configuration
./manage_fogis_system.sh config-init

# 2. Edit configuration
nano fogis-config.yaml

# 3. Generate configuration files
./manage_fogis_system.sh config-generate

# 4. Run setup
./manage_fogis_system.sh setup-auth
```

### Migration from Legacy Configuration
```bash
# Migrate existing .env setup to portable configuration
./manage_fogis_system.sh config-migrate
```
```

##### `DEPLOYMENT_PREREQUISITES.md` (Modify - Update with portable config info)
##### `docs/OAUTH_SETUP_CHECKLIST.md` (Modify - Add portable config workflow)

### Summary of File Changes

#### Phase 1 (Foundation)
- **New Files**: 4 (config_manager.py, config_generator.py, config_validator.py, template)
- **Modified Files**: 2 (setup_fogis_system.sh, manage_fogis_system.sh)
- **Total Lines Added**: ~600

#### Phase 2 (Script Integration)
- **New Files**: 2 (migration_tool.py, interactive_setup.py)
- **Modified Files**: 1 (configure_system.py)
- **Total Lines Added**: ~480

#### Phase 3 (OAuth Integration)
- **New Files**: 0
- **Modified Files**: 1 (enhanced_oauth_wizard.py)
- **Total Lines Added**: ~150

#### Phase 4 (Advanced Features)
- **New Files**: 2 (backup_manager.py, iac_generator.py)
- **Modified Files**: 0
- **Total Lines Added**: ~350

#### Testing and Documentation
- **New Test Files**: 6
- **Modified Documentation**: 3
- **Total Lines Added**: ~900

### **Grand Total Implementation**
- **New Files**: 14
- **Modified Files**: 7
- **Total Lines Added**: ~2,480
- **Estimated Development Time**: 8 weeks
- **Backward Compatibility**: 100% maintained
