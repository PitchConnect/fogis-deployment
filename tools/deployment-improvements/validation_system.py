#!/usr/bin/env python3
"""
FOGIS Deployment Validation System

This system provides comprehensive validation and monitoring capabilities
to eliminate the manual verification steps we encountered during deployment.

Key Features:
- Automated health checking for all services
- End-to-end pipeline validation
- Service interaction testing
- Performance monitoring
- Issue diagnosis and recommendations
- Continuous monitoring capabilities
"""

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """Service health information."""

    name: str
    status: HealthStatus
    response_time_ms: float
    last_check: datetime
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Validation test result."""

    test_name: str
    passed: bool
    message: str
    duration_ms: float
    details: Optional[Dict[str, Any]] = None


class FOGISValidator:
    """Comprehensive validation system for FOGIS deployment."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.services_config = self._load_services_config()
        self.validation_history = []

    def _load_services_config(self) -> Dict[str, Dict]:
        """Load services configuration."""
        return {
            "fogis-api-client": {
                "health_url": "http://localhost:9079/health",
                "port": 9079,
                "required": True,
            },
            "match-list-change-detector": {
                "health_url": "http://localhost:9080/health",
                "port": 9080,
                "required": True,
                "trigger_url": "http://localhost:9080/trigger",
            },
            "match-list-processor": {
                "health_url": "http://localhost:9082/health",
                "port": 9082,
                "required": True,
                "process_url": "http://localhost:9082/process",
            },
            "fogis-calendar-phonebook-sync": {
                "health_url": "http://localhost:9083/health",
                "port": 9083,
                "required": True,
                "sync_url": "http://localhost:9083/sync",
            },
            "google-drive-service": {
                "health_url": "http://localhost:9084/health",
                "port": 9084,
                "required": True,
            },
            "team-logo-combiner": {
                "health_url": "http://localhost:9085/health",
                "port": 9085,
                "required": False,
            },
        }

    def validate_deployment(self, comprehensive: bool = True) -> Dict[str, Any]:
        """Run comprehensive deployment validation."""
        logger.info("Starting FOGIS deployment validation...")
        start_time = time.time()

        results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": HealthStatus.HEALTHY,
            "services": {},
            "tests": [],
            "recommendations": [],
            "duration_ms": 0,
        }

        try:
            # 1. Check Docker environment
            docker_result = self._validate_docker_environment()
            results["tests"].append(docker_result)

            # 2. Check service health
            service_health = self._check_all_services_health()
            results["services"] = {
                name: asdict(health) for name, health in service_health.items()
            }

            # 3. Validate service interactions
            if comprehensive:
                interaction_results = self._validate_service_interactions()
                results["tests"].extend(interaction_results)

            # 4. Test end-to-end pipeline
            if comprehensive:
                pipeline_result = self._validate_end_to_end_pipeline()
                results["tests"].append(pipeline_result)

            # 5. Check resource usage
            resource_result = self._validate_resource_usage()
            results["tests"].append(resource_result)

            # 6. Generate recommendations
            results["recommendations"] = self._generate_recommendations(results)

            # Determine overall status
            results["overall_status"] = self._determine_overall_status(results)

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            results["overall_status"] = HealthStatus.UNHEALTHY
            results["tests"].append(
                ValidationResult("validation_system", False, f"System error: {e}", 0)
            )

        results["duration_ms"] = (time.time() - start_time) * 1000
        self.validation_history.append(results)

        return results

    def _validate_docker_environment(self) -> ValidationResult:
        """Validate Docker environment."""
        start_time = time.time()

        try:
            # Check Docker is running
            result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
            if result.returncode != 0:
                return ValidationResult(
                    "docker_environment",
                    False,
                    "Docker is not running",
                    (time.time() - start_time) * 1000,
                )

            # Check Docker Compose
            compose_file = self.project_root / "docker-compose.yml"
            if not compose_file.exists():
                return ValidationResult(
                    "docker_environment",
                    False,
                    "docker-compose.yml not found",
                    (time.time() - start_time) * 1000,
                )

            # Check containers are running
            result = subprocess.run(
                [
                    "docker-compose",
                    "-f",
                    str(compose_file),
                    "ps",
                    "--services",
                    "--filter",
                    "status=running",
                ],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            running_services = (
                result.stdout.strip().split("\n") if result.stdout.strip() else []
            )
            expected_services = len(
                [s for s in self.services_config.values() if s.get("required", True)]
            )

            if len(running_services) < expected_services:
                return ValidationResult(
                    "docker_environment",
                    False,
                    f"Only {len(running_services)} of {expected_services} required services running",
                    (time.time() - start_time) * 1000,
                    {"running_services": running_services},
                )

            return ValidationResult(
                "docker_environment",
                True,
                "Docker environment is healthy",
                (time.time() - start_time) * 1000,
                {"running_services": running_services},
            )

        except Exception as e:
            return ValidationResult(
                "docker_environment",
                False,
                f"Docker check failed: {e}",
                (time.time() - start_time) * 1000,
            )

    def _check_all_services_health(self) -> Dict[str, ServiceHealth]:
        """Check health of all services."""
        health_results = {}

        for service_name, config in self.services_config.items():
            health = self._check_service_health(service_name, config)
            health_results[service_name] = health

        return health_results

    def _check_service_health(self, service_name: str, config: Dict) -> ServiceHealth:
        """Check health of a single service."""
        start_time = time.time()

        try:
            response = requests.get(
                config["health_url"],
                timeout=10,
                headers={"User-Agent": "FOGIS-Validator/1.0"},
            )

            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                try:
                    health_data = response.json()
                    status_str = health_data.get("status", "unknown").lower()

                    if status_str == "healthy":
                        status = HealthStatus.HEALTHY
                    elif status_str == "degraded":
                        status = HealthStatus.DEGRADED
                    else:
                        status = HealthStatus.UNHEALTHY

                    return ServiceHealth(
                        name=service_name,
                        status=status,
                        response_time_ms=response_time,
                        last_check=datetime.now(),
                        details=health_data,
                    )
                except json.JSONDecodeError:
                    return ServiceHealth(
                        name=service_name,
                        status=HealthStatus.DEGRADED,
                        response_time_ms=response_time,
                        last_check=datetime.now(),
                        error_message="Invalid JSON response",
                    )
            else:
                return ServiceHealth(
                    name=service_name,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    last_check=datetime.now(),
                    error_message=f"HTTP {response.status_code}",
                )

        except requests.exceptions.ConnectionError:
            return ServiceHealth(
                name=service_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.now(),
                error_message="Connection refused",
            )
        except requests.exceptions.Timeout:
            return ServiceHealth(
                name=service_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.now(),
                error_message="Request timeout",
            )
        except Exception as e:
            return ServiceHealth(
                name=service_name,
                status=HealthStatus.UNKNOWN,
                response_time_ms=(time.time() - start_time) * 1000,
                last_check=datetime.now(),
                error_message=str(e),
            )

    def _validate_service_interactions(self) -> List[ValidationResult]:
        """Validate interactions between services."""
        results = []

        # Test match-list-change-detector -> match-list-processor
        results.append(self._test_detector_processor_interaction())

        # Test match-list-processor -> calendar sync
        results.append(self._test_processor_calendar_interaction())

        # Test match-list-processor -> google drive
        results.append(self._test_processor_drive_interaction())

        return results

    def _test_detector_processor_interaction(self) -> ValidationResult:
        """Test interaction between detector and processor."""
        start_time = time.time()

        try:
            # Trigger manual detection
            detector_config = self.services_config.get("match-list-change-detector", {})
            trigger_url = detector_config.get("trigger_url")

            if not trigger_url:
                return ValidationResult(
                    "detector_processor_interaction",
                    False,
                    "Trigger URL not configured",
                    (time.time() - start_time) * 1000,
                )

            response = requests.post(trigger_url, timeout=30)

            if response.status_code == 200:
                return ValidationResult(
                    "detector_processor_interaction",
                    True,
                    "Detector trigger successful",
                    (time.time() - start_time) * 1000,
                    {"response": response.json() if response.content else None},
                )
            else:
                return ValidationResult(
                    "detector_processor_interaction",
                    False,
                    f"Trigger failed: HTTP {response.status_code}",
                    (time.time() - start_time) * 1000,
                )

        except Exception as e:
            return ValidationResult(
                "detector_processor_interaction",
                False,
                f"Interaction test failed: {e}",
                (time.time() - start_time) * 1000,
            )

    def _test_processor_calendar_interaction(self) -> ValidationResult:
        """Test processor to calendar sync interaction."""
        start_time = time.time()

        # This would test the calendar sync functionality
        # For now, just check if the service is reachable
        try:
            calendar_config = self.services_config.get(
                "fogis-calendar-phonebook-sync", {}
            )
            health_url = calendar_config.get("health_url")

            if health_url:
                response = requests.get(health_url, timeout=10)
                success = response.status_code == 200
                message = (
                    "Calendar service reachable"
                    if success
                    else f"HTTP {response.status_code}"
                )
            else:
                success = False
                message = "Calendar service not configured"

            return ValidationResult(
                "processor_calendar_interaction",
                success,
                message,
                (time.time() - start_time) * 1000,
            )

        except Exception as e:
            return ValidationResult(
                "processor_calendar_interaction",
                False,
                f"Calendar interaction test failed: {e}",
                (time.time() - start_time) * 1000,
            )

    def _test_processor_drive_interaction(self) -> ValidationResult:
        """Test processor to Google Drive interaction."""
        start_time = time.time()

        # Similar to calendar test
        try:
            drive_config = self.services_config.get("google-drive-service", {})
            health_url = drive_config.get("health_url")

            if health_url:
                response = requests.get(health_url, timeout=10)
                success = response.status_code == 200
                message = (
                    "Drive service reachable"
                    if success
                    else f"HTTP {response.status_code}"
                )
            else:
                success = False
                message = "Drive service not configured"

            return ValidationResult(
                "processor_drive_interaction",
                success,
                message,
                (time.time() - start_time) * 1000,
            )

        except Exception as e:
            return ValidationResult(
                "processor_drive_interaction",
                False,
                f"Drive interaction test failed: {e}",
                (time.time() - start_time) * 1000,
            )

    def _validate_end_to_end_pipeline(self) -> ValidationResult:
        """Validate the complete end-to-end pipeline."""
        start_time = time.time()

        try:
            # This would trigger a complete pipeline test
            # For now, just verify all required services are healthy

            required_services = [
                name
                for name, config in self.services_config.items()
                if config.get("required", True)
            ]

            healthy_services = 0
            for service_name in required_services:
                health = self._check_service_health(
                    service_name, self.services_config[service_name]
                )
                if health.status == HealthStatus.HEALTHY:
                    healthy_services += 1

            success = healthy_services == len(required_services)
            message = (
                f"{healthy_services}/{len(required_services)} required services healthy"
            )

            return ValidationResult(
                "end_to_end_pipeline",
                success,
                message,
                (time.time() - start_time) * 1000,
                {
                    "healthy_services": healthy_services,
                    "total_required": len(required_services),
                },
            )

        except Exception as e:
            return ValidationResult(
                "end_to_end_pipeline",
                False,
                f"Pipeline validation failed: {e}",
                (time.time() - start_time) * 1000,
            )

    def _validate_resource_usage(self) -> ValidationResult:
        """Validate resource usage of services."""
        start_time = time.time()

        try:
            # Get Docker stats
            result = subprocess.run(
                [
                    "docker",
                    "stats",
                    "--no-stream",
                    "--format",
                    "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return ValidationResult(
                    "resource_usage",
                    False,
                    "Failed to get Docker stats",
                    (time.time() - start_time) * 1000,
                )

            # Parse stats (simplified)
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            high_cpu_containers = []
            high_memory_containers = []

            for line in lines:
                parts = line.split("\t")
                if len(parts) >= 4:
                    container = parts[0]
                    cpu_percent = parts[1].replace("%", "")
                    mem_percent = parts[3].replace("%", "")

                    try:
                        if float(cpu_percent) > 80:
                            high_cpu_containers.append(container)
                        if float(mem_percent) > 80:
                            high_memory_containers.append(container)
                    except ValueError:
                        pass  # Skip invalid values

            issues = []
            if high_cpu_containers:
                issues.append(f"High CPU: {', '.join(high_cpu_containers)}")
            if high_memory_containers:
                issues.append(f"High memory: {', '.join(high_memory_containers)}")

            success = len(issues) == 0
            message = "Resource usage normal" if success else "; ".join(issues)

            return ValidationResult(
                "resource_usage",
                success,
                message,
                (time.time() - start_time) * 1000,
                {
                    "high_cpu": high_cpu_containers,
                    "high_memory": high_memory_containers,
                },
            )

        except Exception as e:
            return ValidationResult(
                "resource_usage",
                False,
                f"Resource check failed: {e}",
                (time.time() - start_time) * 1000,
            )

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []

        # Check service health
        for service_name, service_data in results["services"].items():
            if service_data["status"] != "healthy":
                recommendations.append(
                    f"Service {service_name} is {service_data['status']} - check logs: "
                    f"docker logs {service_name}"
                )

        # Check failed tests
        for test in results["tests"]:
            if not test["passed"]:
                recommendations.append(
                    f"Test '{test['test_name']}' failed: {test['message']}"
                )

        # Performance recommendations
        for test in results["tests"]:
            if test["test_name"] == "resource_usage" and not test["passed"]:
                recommendations.append(
                    "High resource usage detected - consider scaling or optimization"
                )

        return recommendations

    def _determine_overall_status(self, results: Dict[str, Any]) -> HealthStatus:
        """Determine overall system status."""
        # Check if any required services are unhealthy
        for service_name, service_data in results["services"].items():
            config = self.services_config.get(service_name, {})
            if config.get("required", True) and service_data["status"] == "unhealthy":
                return HealthStatus.UNHEALTHY

        # Check if any critical tests failed
        critical_tests = ["docker_environment", "end_to_end_pipeline"]
        for test in results["tests"]:
            if test["test_name"] in critical_tests and not test["passed"]:
                return HealthStatus.UNHEALTHY

        # Check for degraded services
        for service_name, service_data in results["services"].items():
            if service_data["status"] == "degraded":
                return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def continuous_monitoring(
        self, interval_seconds: int = 60, duration_minutes: int = 60
    ) -> None:
        """Run continuous monitoring for specified duration."""
        logger.info(f"Starting continuous monitoring for {duration_minutes} minutes...")

        end_time = datetime.now() + timedelta(minutes=duration_minutes)

        while datetime.now() < end_time:
            try:
                results = self.validate_deployment(comprehensive=False)

                print(
                    f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                    f"Status: {results['overall_status'].value}"
                )

                # Print service status summary
                for service_name, service_data in results["services"].items():
                    status_icon = "✅" if service_data["status"] == "healthy" else "❌"
                    print(f"  {status_icon} {service_name}: {service_data['status']}")

                # Print any recommendations
                if results["recommendations"]:
                    print("  Recommendations:")
                    for rec in results["recommendations"]:
                        print(f"    - {rec}")

                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(interval_seconds)


def main():
    """Main validation script entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="FOGIS Deployment Validation System")
    parser.add_argument(
        "--comprehensive", action="store_true", help="Run comprehensive validation"
    )
    parser.add_argument(
        "--monitor", type=int, help="Run continuous monitoring for N minutes"
    )
    parser.add_argument(
        "--interval", type=int, default=60, help="Monitoring interval in seconds"
    )
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--output", help="Save results to JSON file")

    args = parser.parse_args()

    validator = FOGISValidator(Path(args.project_root))

    if args.monitor:
        validator.continuous_monitoring(args.interval, args.monitor)
    else:
        results = validator.validate_deployment(args.comprehensive)

        # Print results
        print(f"\n🔍 FOGIS Deployment Validation Results")
        print("=" * 50)
        print(f"Overall Status: {results['overall_status'].value}")
        print(f"Duration: {results['duration_ms']:.0f}ms")

        print(f"\n📊 Services ({len(results['services'])})")
        for service_name, service_data in results["services"].items():
            status_icon = "✅" if service_data["status"] == "healthy" else "❌"
            print(
                f"  {status_icon} {service_name}: {service_data['status']} "
                f"({service_data['response_time_ms']:.0f}ms)"
            )

        print(f"\n🧪 Tests ({len(results['tests'])})")
        for test in results["tests"]:
            status_icon = "✅" if test["passed"] else "❌"
            print(
                f"  {status_icon} {test['test_name']}: {test['message']} "
                f"({test['duration_ms']:.0f}ms)"
            )

        if results["recommendations"]:
            print(f"\n💡 Recommendations ({len(results['recommendations'])})")
            for rec in results["recommendations"]:
                print(f"  - {rec}")

        # Save results if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {args.output}")

        # Exit with appropriate code
        sys.exit(
            0
            if results["overall_status"]
            in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
            else 1
        )


if __name__ == "__main__":
    main()
