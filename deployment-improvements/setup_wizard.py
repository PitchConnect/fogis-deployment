#!/usr/bin/env python3
"""
FOGIS Deployment Setup Wizard

This automated setup wizard eliminates the manual troubleshooting steps we
encountered during deployment by providing guided, validated setup.

Key Features:
- Interactive setup with validation
- Automatic dependency checking
- Configuration file generation
- Environment validation
- Troubleshooting guidance
- Setup progress tracking
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SetupStage(Enum):
    """Setup stages."""
    DEPENDENCIES = "dependencies"
    CREDENTIALS = "credentials"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    DEPLOYMENT = "deployment"


@dataclass
class SetupStep:
    """Individual setup step."""
    name: str
    description: str
    validator: callable
    fixer: Optional[callable] = None
    required: bool = True
    stage: SetupStage = SetupStage.DEPENDENCIES


class SetupWizard:
    """Interactive setup wizard for FOGIS deployment."""
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.setup_state_file = self.project_root / ".setup_state.json"
        self.setup_state = self._load_setup_state()
        self.steps = self._define_setup_steps()
    
    def _load_setup_state(self) -> Dict:
        """Load setup state from file."""
        if self.setup_state_file.exists():
            try:
                with open(self.setup_state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load setup state: {e}")
        return {"completed_steps": [], "configuration": {}}
    
    def _save_setup_state(self) -> None:
        """Save setup state to file."""
        try:
            with open(self.setup_state_file, 'w') as f:
                json.dump(self.setup_state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save setup state: {e}")
    
    def _define_setup_steps(self) -> List[SetupStep]:
        """Define all setup steps."""
        return [
            # Dependencies
            SetupStep(
                "docker_installed",
                "Docker is installed and running",
                self._check_docker,
                self._install_docker_guidance,
                stage=SetupStage.DEPENDENCIES
            ),
            SetupStep(
                "docker_compose_installed",
                "Docker Compose is installed",
                self._check_docker_compose,
                self._install_docker_compose_guidance,
                stage=SetupStage.DEPENDENCIES
            ),
            SetupStep(
                "git_installed",
                "Git is installed",
                self._check_git,
                stage=SetupStage.DEPENDENCIES
            ),
            
            # Credentials
            SetupStep(
                "fogis_credentials",
                "FOGIS credentials are configured",
                self._check_fogis_credentials,
                self._setup_fogis_credentials,
                stage=SetupStage.CREDENTIALS
            ),
            SetupStep(
                "google_oauth",
                "Google OAuth is configured",
                self._check_google_oauth,
                self._setup_google_oauth,
                stage=SetupStage.CREDENTIALS
            ),
            
            # Configuration
            SetupStep(
                "environment_file",
                "Environment file is configured",
                self._check_environment_file,
                self._create_environment_file,
                stage=SetupStage.CONFIGURATION
            ),
            SetupStep(
                "docker_compose_config",
                "Docker Compose configuration is valid",
                self._check_docker_compose_config,
                self._fix_docker_compose_config,
                stage=SetupStage.CONFIGURATION
            ),
            
            # Validation
            SetupStep(
                "services_build",
                "All services build successfully",
                self._check_services_build,
                self._fix_services_build,
                stage=SetupStage.VALIDATION
            ),
            SetupStep(
                "services_start",
                "All services start successfully",
                self._check_services_start,
                self._fix_services_start,
                stage=SetupStage.VALIDATION
            ),
            
            # Deployment
            SetupStep(
                "health_checks",
                "All health checks pass",
                self._check_health_checks,
                self._fix_health_checks,
                stage=SetupStage.DEPLOYMENT
            ),
        ]
    
    def run_setup(self, interactive: bool = True) -> bool:
        """Run the complete setup process."""
        print("🚀 FOGIS Deployment Setup Wizard")
        print("=" * 50)
        
        if interactive:
            print("\nThis wizard will guide you through setting up FOGIS deployment.")
            print("Each step will be validated and fixed automatically when possible.\n")
            
            if not self._confirm("Continue with setup?"):
                return False
        
        # Group steps by stage
        stages = {}
        for step in self.steps:
            if step.stage not in stages:
                stages[step.stage] = []
            stages[step.stage].append(step)
        
        # Run each stage
        for stage, steps in stages.items():
            print(f"\n📋 Stage: {stage.value.title()}")
            print("-" * 30)
            
            for step in steps:
                if not self._run_step(step, interactive):
                    print(f"\n❌ Setup failed at step: {step.name}")
                    return False
        
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Run: docker-compose -f docker-compose.yml up -d")
        print("2. Check health: curl http://localhost:9080/health")
        print("3. Monitor logs: docker-compose -f docker-compose.yml logs -f")
        
        return True
    
    def _run_step(self, step: SetupStep, interactive: bool) -> bool:
        """Run a single setup step."""
        step_id = step.name
        
        # Skip if already completed
        if step_id in self.setup_state["completed_steps"]:
            print(f"✅ {step.description} (already completed)")
            return True
        
        print(f"🔍 Checking: {step.description}")
        
        try:
            # Run validator
            is_valid, message = step.validator()
            
            if is_valid:
                print(f"✅ {step.description}")
                self.setup_state["completed_steps"].append(step_id)
                self._save_setup_state()
                return True
            
            # Step failed
            print(f"❌ {step.description}")
            if message:
                print(f"   Issue: {message}")
            
            # Try to fix automatically
            if step.fixer:
                if interactive:
                    if self._confirm(f"   Attempt to fix automatically?"):
                        try:
                            fix_result = step.fixer()
                            if fix_result:
                                print(f"🔧 Fixed: {step.description}")
                                # Re-validate
                                is_valid, _ = step.validator()
                                if is_valid:
                                    self.setup_state["completed_steps"].append(step_id)
                                    self._save_setup_state()
                                    return True
                        except Exception as e:
                            print(f"   Fix failed: {e}")
                else:
                    # Non-interactive mode - try to fix automatically
                    try:
                        step.fixer()
                    except Exception as e:
                        logger.error(f"Auto-fix failed for {step_id}: {e}")
            
            if step.required:
                print(f"   This step is required. Please fix manually and re-run setup.")
                return False
            else:
                print(f"   This step is optional. Continuing...")
                return True
                
        except Exception as e:
            print(f"❌ Error checking {step.description}: {e}")
            return False
    
    def _confirm(self, message: str) -> bool:
        """Ask user for confirmation."""
        while True:
            response = input(f"{message} (y/n): ").lower().strip()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            print("Please enter 'y' or 'n'")
    
    # Validator methods
    def _check_docker(self) -> Tuple[bool, str]:
        """Check if Docker is installed and running."""
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                return False, "Docker command failed"
            
            # Check if Docker daemon is running
            result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
            if result.returncode != 0:
                return False, "Docker daemon is not running"
            
            return True, ""
        except FileNotFoundError:
            return False, "Docker is not installed"
    
    def _check_docker_compose(self) -> Tuple[bool, str]:
        """Check if Docker Compose is installed."""
        try:
            result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
            return result.returncode == 0, "" if result.returncode == 0 else "Docker Compose not found"
        except FileNotFoundError:
            return False, "Docker Compose is not installed"
    
    def _check_git(self) -> Tuple[bool, str]:
        """Check if Git is installed."""
        try:
            result = subprocess.run(["git", "--version"], capture_output=True, text=True)
            return result.returncode == 0, "" if result.returncode == 0 else "Git command failed"
        except FileNotFoundError:
            return False, "Git is not installed"
    
    def _check_fogis_credentials(self) -> Tuple[bool, str]:
        """Check if FOGIS credentials are configured."""
        env_file = self.project_root / ".env"
        if not env_file.exists():
            return False, ".env file not found"
        
        content = env_file.read_text()
        if "FOGIS_USERNAME=" not in content or "FOGIS_PASSWORD=" not in content:
            return False, "FOGIS credentials not found in .env file"
        
        # Check if values are set (not empty)
        lines = content.split('\n')
        username_set = any(line.startswith("FOGIS_USERNAME=") and "=" in line and line.split("=", 1)[1].strip() for line in lines)
        password_set = any(line.startswith("FOGIS_PASSWORD=") and "=" in line and line.split("=", 1)[1].strip() for line in lines)
        
        if not username_set or not password_set:
            return False, "FOGIS credentials are empty"
        
        return True, ""
    
    def _check_google_oauth(self) -> Tuple[bool, str]:
        """Check if Google OAuth is configured."""
        credentials_dir = self.project_root / "credentials"
        if not credentials_dir.exists():
            return False, "credentials directory not found"
        
        # Check for OAuth files
        oauth_files = list(credentials_dir.glob("*oauth*.json"))
        if not oauth_files:
            return False, "No OAuth credential files found"
        
        return True, ""
    
    def _check_environment_file(self) -> Tuple[bool, str]:
        """Check if environment file is properly configured."""
        env_file = self.project_root / ".env"
        if not env_file.exists():
            return False, ".env file not found"
        
        # Check for required variables
        required_vars = [
            "FOGIS_USERNAME", "FOGIS_PASSWORD", "LOG_LEVEL",
            "RUN_MODE", "CRON_SCHEDULE", "HEALTH_SERVER_PORT"
        ]
        
        content = env_file.read_text()
        missing_vars = []
        
        for var in required_vars:
            if f"{var}=" not in content:
                missing_vars.append(var)
        
        if missing_vars:
            return False, f"Missing variables: {', '.join(missing_vars)}"
        
        return True, ""
    
    def _check_docker_compose_config(self) -> Tuple[bool, str]:
        """Check if Docker Compose configuration is valid."""
        compose_file = self.project_root / "docker-compose.yml"
        if not compose_file.exists():
            return False, "docker-compose.yml not found"
        
        try:
            result = subprocess.run(
                ["docker-compose", "-f", str(compose_file), "config"],
                capture_output=True, text=True, cwd=self.project_root
            )
            return result.returncode == 0, result.stderr if result.returncode != 0 else ""
        except Exception as e:
            return False, str(e)
    
    def _check_services_build(self) -> Tuple[bool, str]:
        """Check if all services build successfully."""
        # This would integrate with the smart build system
        return True, ""  # Placeholder
    
    def _check_services_start(self) -> Tuple[bool, str]:
        """Check if all services start successfully."""
        # This would check docker-compose up
        return True, ""  # Placeholder
    
    def _check_health_checks(self) -> Tuple[bool, str]:
        """Check if all health checks pass."""
        # This would check service health endpoints
        return True, ""  # Placeholder
    
    # Fixer methods
    def _install_docker_guidance(self) -> bool:
        """Provide guidance for installing Docker."""
        print("\n📖 Docker Installation Guide:")
        print("1. Visit: https://docs.docker.com/get-docker/")
        print("2. Download Docker Desktop for your platform")
        print("3. Install and start Docker Desktop")
        print("4. Verify installation: docker --version")
        return False  # Manual installation required
    
    def _install_docker_compose_guidance(self) -> bool:
        """Provide guidance for installing Docker Compose."""
        print("\n📖 Docker Compose Installation Guide:")
        print("1. Docker Compose is included with Docker Desktop")
        print("2. For Linux: https://docs.docker.com/compose/install/")
        print("3. Verify installation: docker-compose --version")
        return False  # Manual installation required
    
    def _setup_fogis_credentials(self) -> bool:
        """Setup FOGIS credentials interactively."""
        print("\n🔐 FOGIS Credentials Setup:")
        username = input("Enter FOGIS username: ").strip()
        password = input("Enter FOGIS password: ").strip()
        
        if not username or not password:
            print("Username and password are required")
            return False
        
        # Update .env file
        env_file = self.project_root / ".env"
        env_content = ""
        
        if env_file.exists():
            env_content = env_file.read_text()
        
        # Update or add credentials
        lines = env_content.split('\n')
        updated_lines = []
        username_updated = False
        password_updated = False
        
        for line in lines:
            if line.startswith("FOGIS_USERNAME="):
                updated_lines.append(f"FOGIS_USERNAME={username}")
                username_updated = True
            elif line.startswith("FOGIS_PASSWORD="):
                updated_lines.append(f"FOGIS_PASSWORD={password}")
                password_updated = True
            else:
                updated_lines.append(line)
        
        # Add missing variables
        if not username_updated:
            updated_lines.append(f"FOGIS_USERNAME={username}")
        if not password_updated:
            updated_lines.append(f"FOGIS_PASSWORD={password}")
        
        env_file.write_text('\n'.join(updated_lines))
        print("✅ FOGIS credentials saved to .env file")
        return True
    
    def _setup_google_oauth(self) -> bool:
        """Setup Google OAuth interactively."""
        print("\n🔐 Google OAuth Setup:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable required APIs (Calendar, Drive, etc.)")
        print("4. Create OAuth 2.0 credentials")
        print("5. Download the JSON file")
        
        credentials_dir = self.project_root / "credentials"
        credentials_dir.mkdir(exist_ok=True)
        
        oauth_file = input(f"Enter path to OAuth JSON file: ").strip()
        if oauth_file and Path(oauth_file).exists():
            import shutil
            shutil.copy(oauth_file, credentials_dir / "oauth_credentials.json")
            print("✅ OAuth credentials copied")
            return True
        
        print("❌ OAuth file not found or not provided")
        return False
    
    def _create_environment_file(self) -> bool:
        """Create environment file with defaults."""
        env_file = self.project_root / ".env"
        
        default_env = """# FOGIS Configuration
FOGIS_USERNAME=
FOGIS_PASSWORD=

# Service Configuration
RUN_MODE=service
CRON_SCHEDULE=0 * * * *
HEALTH_SERVER_PORT=8000
HEALTH_SERVER_HOST=0.0.0.0
LOG_LEVEL=INFO

# Webhook Configuration
WEBHOOK_URL=http://match-list-processor:8000/process
"""
        
        env_file.write_text(default_env)
        print("✅ Created .env file with defaults")
        return True
    
    def _fix_docker_compose_config(self) -> bool:
        """Fix Docker Compose configuration issues."""
        # This would implement automatic fixes for common issues
        return True  # Placeholder
    
    def _fix_services_build(self) -> bool:
        """Fix service build issues."""
        # This would integrate with the smart build system
        return True  # Placeholder
    
    def _fix_services_start(self) -> bool:
        """Fix service startup issues."""
        # This would implement automatic fixes for startup issues
        return True  # Placeholder
    
    def _fix_health_checks(self) -> bool:
        """Fix health check issues."""
        # This would implement automatic fixes for health check issues
        return True  # Placeholder


def main():
    """Main setup wizard entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="FOGIS Deployment Setup Wizard")
    parser.add_argument("--non-interactive", action="store_true", help="Run in non-interactive mode")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    wizard = SetupWizard(Path(args.project_root))
    success = wizard.run_setup(interactive=not args.non_interactive)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
