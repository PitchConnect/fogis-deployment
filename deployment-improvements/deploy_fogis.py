#!/usr/bin/env python3
"""
FOGIS Master Deployment Script

This script orchestrates the complete FOGIS deployment process, eliminating
all the manual troubleshooting steps we encountered during our implementation.

Key Features:
- Automated setup and validation
- Intelligent build management
- Comprehensive health checking
- Issue diagnosis and resolution
- Progress tracking and reporting
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Import our custom modules
sys.path.append(str(Path(__file__).parent))
from enhanced_config_system import ConfigurationError, create_match_list_detector_config
from setup_wizard import SetupWizard
from smart_build_system import BuildError, SmartBuildSystem
from validation_system import FOGISValidator, HealthStatus
from redis_infrastructure import RedisInfrastructureManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DeploymentError(Exception):
    """Raised when deployment fails."""

    pass


class FOGISDeploymentOrchestrator:
    """Master orchestrator for FOGIS deployment."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.deployment_log = []
        self.start_time = datetime.now()

    def deploy(
        self,
        skip_setup: bool = False,
        skip_build: bool = False,
        skip_validation: bool = False,
    ) -> bool:
        """Run complete FOGIS deployment."""
        try:
            self._log_step("🚀 Starting FOGIS deployment")

            # Phase 1: Setup and Configuration
            if not skip_setup:
                self._log_step("📋 Phase 1: Setup and Configuration")
                if not self._run_setup():
                    raise DeploymentError("Setup phase failed")

            # Phase 2: Build Services
            if not skip_build:
                self._log_step("🔨 Phase 2: Building Services")
                if not self._build_services():
                    raise DeploymentError("Build phase failed")

            # Phase 3: Deploy Services
            self._log_step("🚢 Phase 3: Deploying Services")
            if not self._deploy_services():
                raise DeploymentError("Deployment phase failed")

            # Phase 4: Redis Infrastructure (optional)
            self._log_step("🔧 Phase 4: Redis Infrastructure")
            if not self._deploy_redis_infrastructure():
                self._log_step("⚠️ Redis deployment failed - pub/sub unavailable, continuing with HTTP fallback")
                # Don't fail entire deployment for Redis

            # Phase 5: Validation
            if not skip_validation:
                self._log_step("✅ Phase 5: Validation and Health Checks")
                if not self._validate_deployment():
                    raise DeploymentError("Validation phase failed")

            self._log_step("🎉 FOGIS deployment completed successfully!")
            self._print_deployment_summary()
            return True

        except Exception as e:
            self._log_step(f"❌ Deployment failed: {e}")
            self._print_failure_summary()
            return False

    def _run_setup(self) -> bool:
        """Run setup wizard."""
        try:
            wizard = SetupWizard(self.project_root)
            return wizard.run_setup(interactive=False)
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False

    def _build_services(self) -> bool:
        """Build all services using smart build system."""
        try:
            build_system = SmartBuildSystem(self.project_root)

            # Define services to build
            services_config = {
                "match-list-change-detector": {
                    "context": "local-patches/match-list-change-detector",
                    "dockerfile": "Dockerfile",
                }
            }

            # Build services
            built_images = build_system.build_all_services(services_config)

            self._log_step(f"Built {len(built_images)} services:")
            for service, image in built_images.items():
                self._log_step(f"  ✅ {service}: {image}")

            return True

        except BuildError as e:
            logger.error(f"Build failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected build error: {e}")
            return False

    def _deploy_services(self) -> bool:
        """Deploy services using docker-compose."""
        try:
            compose_file = self.project_root / "docker-compose.yml"
            if not compose_file.exists():
                logger.error("docker-compose.yml not found")
                return False

            # Stop existing services
            self._log_step("Stopping existing services...")
            subprocess.run(
                ["docker-compose", "-f", str(compose_file), "down"],
                cwd=self.project_root,
                check=False,
            )

            # Start services
            self._log_step("Starting services...")
            result = subprocess.run(
                ["docker-compose", "-f", str(compose_file), "up", "-d"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error(f"Docker compose failed: {result.stderr}")
                return False

            # Wait for services to start
            self._log_step("Waiting for services to start...")
            time.sleep(30)

            return True

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return False

    def _validate_deployment(self) -> bool:
        """Validate deployment using validation system."""
        try:
            validator = FOGISValidator(self.project_root)
            results = validator.validate_deployment(comprehensive=True)

            # Log validation results
            self._log_step(f"Validation status: {results['overall_status'].value}")

            for service_name, service_data in results["services"].items():
                status_icon = "✅" if service_data["status"] == "healthy" else "❌"
                self._log_step(
                    f"  {status_icon} {service_name}: {service_data['status']}"
                )

            # Log any recommendations
            if results["recommendations"]:
                self._log_step("Recommendations:")
                for rec in results["recommendations"]:
                    self._log_step(f"  - {rec}")

            # Consider degraded as acceptable for initial deployment
            return results["overall_status"] in [
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED,
            ]

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False

    def _deploy_redis_infrastructure(self) -> bool:
        """Deploy Redis infrastructure for pub/sub communication."""
        try:
            self._log_step("🔧 Deploying Redis infrastructure for pub/sub...")

            # Initialize Redis infrastructure manager
            redis_manager = RedisInfrastructureManager(project_root=self.project_root)

            # Deploy Redis service
            deployment_result = redis_manager.deploy_redis_service()

            if deployment_result.success:
                self._log_step("✅ Redis service deployed successfully")

                # Configure persistence
                if redis_manager.configure_redis_persistence():
                    self._log_step("💾 Redis persistence configured")
                else:
                    self._log_step("⚠️ Redis persistence configuration warning")

                # Validate deployment
                if redis_manager.validate_redis_deployment():
                    self._log_step("🔍 Redis deployment validated")
                    return True
                else:
                    self._log_step("❌ Redis deployment validation failed")
                    return False
            else:
                self._log_step(f"❌ Redis deployment failed: {deployment_result.message}")
                if deployment_result.errors:
                    for error in deployment_result.errors:
                        self._log_step(f"   - {error}")
                return False

        except Exception as e:
            logger.error(f"Redis deployment failed: {e}")
            return False

    def _log_step(self, message: str) -> None:
        """Log a deployment step."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.deployment_log.append(log_entry)
        logger.info(message)

    def _print_deployment_summary(self) -> None:
        """Print deployment summary."""
        duration = datetime.now() - self.start_time

        print("\n" + "=" * 60)
        print("🎉 FOGIS DEPLOYMENT SUCCESSFUL")
        print("=" * 60)
        print(f"Duration: {duration}")
        print(f"Steps completed: {len(self.deployment_log)}")

        print("\n📋 Next Steps:")
        print("1. Check service health:")
        print("   python3 deployment-improvements/validation_system.py")
        print("\n2. Monitor services:")
        print("   python3 deployment-improvements/validation_system.py --monitor 10")
        print("\n3. View logs:")
        print("   docker-compose -f docker-compose.yml logs -f")
        print("\n4. Access health endpoints:")
        print("   curl http://localhost:9080/health  # match-list-change-detector")
        print("   curl http://localhost:9082/health  # match-list-processor")

        print("\n🔧 Management Commands:")
        print("   # Restart services")
        print("   docker-compose -f docker-compose.yml restart")
        print("   # Stop services")
        print("   docker-compose -f docker-compose.yml down")
        print("   # View service status")
        print("   docker-compose -f docker-compose.yml ps")

    def _print_failure_summary(self) -> None:
        """Print failure summary with troubleshooting guidance."""
        duration = datetime.now() - self.start_time

        print("\n" + "=" * 60)
        print("❌ FOGIS DEPLOYMENT FAILED")
        print("=" * 60)
        print(f"Duration: {duration}")
        print(f"Steps completed: {len(self.deployment_log)}")

        print("\n🔍 Troubleshooting Steps:")
        print("1. Check Docker is running:")
        print("   docker ps")
        print("\n2. Check logs for errors:")
        print("   docker-compose -f docker-compose.yml logs")
        print("\n3. Check environment configuration:")
        print("   cat .env")
        print("\n4. Validate configuration:")
        print("   python3 deployment-improvements/enhanced_config_system.py")
        print("\n5. Run setup wizard:")
        print("   python3 deployment-improvements/setup_wizard.py")

        print("\n📞 Support:")
        print("- Check deployment log above for specific error messages")
        print("- Ensure all prerequisites are installed (Docker, Docker Compose)")
        print("- Verify FOGIS credentials are correct")
        print("- Check network connectivity and firewall settings")


def main():
    """Main deployment script entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="FOGIS Master Deployment Script")
    parser.add_argument("--skip-setup", action="store_true", help="Skip setup phase")
    parser.add_argument("--skip-build", action="store_true", help="Skip build phase")
    parser.add_argument(
        "--skip-validation", action="store_true", help="Skip validation phase"
    )
    parser.add_argument("--project-root", default=".", help="Project root directory")

    args = parser.parse_args()

    # Change to project root
    project_root = Path(args.project_root).resolve()
    os.chdir(project_root)

    print(f"🏠 Project root: {project_root}")
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run deployment
    orchestrator = FOGISDeploymentOrchestrator(project_root)
    success = orchestrator.deploy(
        skip_setup=args.skip_setup,
        skip_build=args.skip_build,
        skip_validation=args.skip_validation,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
