#!/usr/bin/env python3
"""
Redis Deployment Validation for FOGIS

This module provides comprehensive validation for Redis deployment
in the FOGIS system. It validates infrastructure, configuration,
and integration readiness.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis deployment validation
"""

import logging
import subprocess
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from redis_infrastructure import RedisInfrastructureManager
from redis_health_monitoring import RedisHealthMonitor, HealthStatus

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of a validation check."""
    passed: bool
    message: str
    details: Dict[str, Any] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.errors is None:
            self.errors = []

@dataclass
class DeploymentValidationReport:
    """Comprehensive deployment validation report."""
    overall_status: str
    timestamp: datetime
    validation_results: Dict[str, ValidationResult]
    summary: Dict[str, Any]
    recommendations: List[str] = None

    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []

class RedisDeploymentValidator:
    """Validates Redis deployment for FOGIS system."""
    
    def __init__(self, project_root: Path = None):
        """
        Initialize Redis deployment validator.
        
        Args:
            project_root: Path to project root directory
        """
        self.project_root = project_root or Path.cwd()
        self.compose_file = self.project_root / "docker-compose.yml"
        self.infrastructure_manager = RedisInfrastructureManager(project_root=project_root)
        self.health_monitor = RedisHealthMonitor()
        
        logger.info(f"🔍 Redis Deployment Validator initialized")
        logger.info(f"   Project root: {self.project_root}")
    
    def validate_docker_compose_configuration(self) -> ValidationResult:
        """
        Validate Redis configuration in docker-compose.yml.
        
        Returns:
            ValidationResult: Docker Compose validation result
        """
        try:
            logger.debug("📋 Validating docker-compose.yml Redis configuration...")
            
            if not self.compose_file.exists():
                return ValidationResult(
                    passed=False,
                    message="docker-compose.yml file not found",
                    errors=[f"File not found: {self.compose_file}"]
                )
            
            # Read and parse docker-compose.yml
            with open(self.compose_file, 'r') as f:
                try:
                    compose_data = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    return ValidationResult(
                        passed=False,
                        message="Invalid YAML in docker-compose.yml",
                        errors=[str(e)]
                    )
            
            # Check if Redis service is defined
            services = compose_data.get('services', {})
            if 'redis' not in services:
                return ValidationResult(
                    passed=False,
                    message="Redis service not defined in docker-compose.yml",
                    errors=["Missing 'redis' service definition"]
                )
            
            redis_service = services['redis']
            
            # Validate Redis service configuration
            validation_details = {}
            errors = []
            
            # Check image
            if 'image' not in redis_service:
                errors.append("Redis service missing 'image' configuration")
            else:
                image = redis_service['image']
                validation_details['image'] = image
                if not image.startswith('redis:'):
                    errors.append(f"Unexpected Redis image: {image}")
            
            # Check ports
            if 'ports' not in redis_service:
                errors.append("Redis service missing 'ports' configuration")
            else:
                ports = redis_service['ports']
                validation_details['ports'] = ports
                if '6379:6379' not in str(ports):
                    errors.append("Redis port 6379 not exposed")
            
            # Check volumes
            if 'volumes' not in redis_service:
                errors.append("Redis service missing 'volumes' configuration")
            else:
                volumes = redis_service['volumes']
                validation_details['volumes'] = volumes
                if not any('redis-data' in str(vol) for vol in volumes):
                    errors.append("Redis data volume not configured")
            
            # Check networks
            if 'networks' not in redis_service:
                errors.append("Redis service missing 'networks' configuration")
            else:
                networks = redis_service['networks']
                validation_details['networks'] = networks
                if 'fogis-network' not in networks:
                    errors.append("Redis not connected to fogis-network")
            
            # Check health check
            if 'healthcheck' not in redis_service:
                errors.append("Redis service missing health check configuration")
            else:
                healthcheck = redis_service['healthcheck']
                validation_details['healthcheck'] = healthcheck
            
            # Check restart policy
            if 'restart' not in redis_service:
                errors.append("Redis service missing restart policy")
            else:
                restart = redis_service['restart']
                validation_details['restart'] = restart
            
            # Check Redis command configuration
            if 'command' not in redis_service:
                errors.append("Redis service missing command configuration")
            else:
                command = redis_service['command']
                validation_details['command'] = command
                if 'appendonly yes' not in str(command):
                    errors.append("Redis AOF persistence not enabled in command")
            
            # Check volumes definition
            volumes_section = compose_data.get('volumes', {})
            if 'redis-data' not in volumes_section:
                errors.append("redis-data volume not defined in volumes section")
            
            if errors:
                return ValidationResult(
                    passed=False,
                    message="Redis docker-compose.yml configuration issues found",
                    details=validation_details,
                    errors=errors
                )
            else:
                return ValidationResult(
                    passed=True,
                    message="Redis docker-compose.yml configuration valid",
                    details=validation_details
                )
                
        except Exception as e:
            return ValidationResult(
                passed=False,
                message=f"Docker Compose validation failed: {e}",
                errors=[str(e)]
            )
    
    def validate_redis_deployment(self) -> ValidationResult:
        """
        Validate Redis deployment status.
        
        Returns:
            ValidationResult: Deployment validation result
        """
        try:
            logger.debug("🚀 Validating Redis deployment status...")
            
            # Check if Redis container is running
            container_check = subprocess.run([
                "docker", "ps", "-f", "name=fogis-redis", "--format", "{{.Names}}\t{{.Status}}"
            ], capture_output=True, text=True, timeout=10)
            
            if container_check.returncode != 0:
                return ValidationResult(
                    passed=False,
                    message="Failed to check Redis container status",
                    errors=[container_check.stderr]
                )
            
            if not container_check.stdout.strip():
                return ValidationResult(
                    passed=False,
                    message="Redis container is not running",
                    errors=["Container not found in docker ps output"]
                )
            
            # Parse container status
            container_info = container_check.stdout.strip().split('\t')
            container_name = container_info[0]
            container_status = container_info[1] if len(container_info) > 1 else "unknown"
            
            if "Up" not in container_status:
                return ValidationResult(
                    passed=False,
                    message=f"Redis container is not healthy: {container_status}",
                    details={"container_name": container_name, "status": container_status},
                    errors=[f"Container status: {container_status}"]
                )
            
            # Validate Redis functionality
            if not self.infrastructure_manager.validate_redis_deployment():
                return ValidationResult(
                    passed=False,
                    message="Redis deployment validation failed",
                    details={"container_name": container_name, "status": container_status},
                    errors=["Redis functionality validation failed"]
                )
            
            return ValidationResult(
                passed=True,
                message="Redis deployment is healthy and functional",
                details={
                    "container_name": container_name,
                    "status": container_status,
                    "functionality": "validated"
                }
            )
            
        except Exception as e:
            return ValidationResult(
                passed=False,
                message=f"Redis deployment validation failed: {e}",
                errors=[str(e)]
            )
    
    def validate_redis_health(self) -> ValidationResult:
        """
        Validate Redis health status.
        
        Returns:
            ValidationResult: Health validation result
        """
        try:
            logger.debug("🏥 Validating Redis health status...")
            
            health_status = self.health_monitor.get_comprehensive_health_status()
            
            overall_status = health_status.get('overall_status', 'unknown')
            
            if overall_status == 'healthy':
                return ValidationResult(
                    passed=True,
                    message="Redis health status is healthy",
                    details=health_status
                )
            elif overall_status == 'degraded':
                return ValidationResult(
                    passed=True,
                    message="Redis health status is degraded but functional",
                    details=health_status,
                    errors=["Performance or configuration warnings detected"]
                )
            else:
                return ValidationResult(
                    passed=False,
                    message=f"Redis health status is {overall_status}",
                    details=health_status,
                    errors=["Redis health check failed"]
                )
                
        except Exception as e:
            return ValidationResult(
                passed=False,
                message=f"Redis health validation failed: {e}",
                errors=[str(e)]
            )
    
    def validate_redis_integration_readiness(self) -> ValidationResult:
        """
        Validate Redis integration readiness for FOGIS services.
        
        Returns:
            ValidationResult: Integration readiness validation result
        """
        try:
            logger.debug("🔗 Validating Redis integration readiness...")
            
            # Test pub/sub functionality
            pubsub_check = self.health_monitor.check_pubsub_functionality()
            
            if pubsub_check.status != HealthStatus.HEALTHY:
                return ValidationResult(
                    passed=False,
                    message="Redis pub/sub functionality not ready",
                    details={"pubsub_status": pubsub_check.status.value},
                    errors=pubsub_check.errors
                )
            
            # Test Redis channels that will be used by FOGIS
            test_channels = [
                "fogis:matches:updates",
                "fogis:processor:status",
                "fogis:calendar:status",
                "fogis:system:alerts"
            ]
            
            channel_test_results = {}
            for channel in test_channels:
                try:
                    # Test publishing to each channel
                    publish_result = subprocess.run([
                        "docker", "exec", "fogis-redis",
                        "redis-cli", "PUBLISH", channel, f"test_message_{int(datetime.now().timestamp())}"
                    ], capture_output=True, text=True, timeout=5)
                    
                    channel_test_results[channel] = {
                        "success": publish_result.returncode == 0,
                        "subscribers": int(publish_result.stdout.strip()) if publish_result.stdout.strip().isdigit() else 0
                    }
                except Exception as e:
                    channel_test_results[channel] = {
                        "success": False,
                        "error": str(e)
                    }
            
            # Check if all channel tests passed
            failed_channels = [ch for ch, result in channel_test_results.items() if not result.get('success', False)]
            
            if failed_channels:
                return ValidationResult(
                    passed=False,
                    message=f"Redis channel tests failed for: {', '.join(failed_channels)}",
                    details={"channel_tests": channel_test_results},
                    errors=[f"Failed channels: {failed_channels}"]
                )
            
            return ValidationResult(
                passed=True,
                message="Redis integration readiness validated",
                details={
                    "pubsub_status": pubsub_check.status.value,
                    "channel_tests": channel_test_results,
                    "ready_for_integration": True
                }
            )
            
        except Exception as e:
            return ValidationResult(
                passed=False,
                message=f"Redis integration readiness validation failed: {e}",
                errors=[str(e)]
            )
    
    def generate_validation_report(self) -> DeploymentValidationReport:
        """
        Generate comprehensive Redis deployment validation report.
        
        Returns:
            DeploymentValidationReport: Complete validation report
        """
        logger.info("📊 Generating Redis deployment validation report...")
        
        validation_results = {}
        
        # Run all validations
        validation_results["docker_compose"] = self.validate_docker_compose_configuration()
        validation_results["deployment"] = self.validate_redis_deployment()
        validation_results["health"] = self.validate_redis_health()
        validation_results["integration_readiness"] = self.validate_redis_integration_readiness()
        
        # Determine overall status
        all_passed = all(result.passed for result in validation_results.values())
        critical_failed = not validation_results["deployment"].passed or not validation_results["docker_compose"].passed
        
        if all_passed:
            overall_status = "READY"
        elif critical_failed:
            overall_status = "FAILED"
        else:
            overall_status = "DEGRADED"
        
        # Generate summary
        summary = {
            "total_checks": len(validation_results),
            "passed_checks": sum(1 for result in validation_results.values() if result.passed),
            "failed_checks": sum(1 for result in validation_results.values() if not result.passed),
            "critical_issues": critical_failed,
            "ready_for_production": all_passed
        }
        
        # Generate recommendations
        recommendations = []
        for check_name, result in validation_results.items():
            if not result.passed:
                recommendations.append(f"Fix {check_name}: {result.message}")
                if result.errors:
                    recommendations.extend([f"  - {error}" for error in result.errors])
        
        if not recommendations:
            recommendations.append("Redis deployment is ready for production use")
        
        return DeploymentValidationReport(
            overall_status=overall_status,
            timestamp=datetime.now(),
            validation_results=validation_results,
            summary=summary,
            recommendations=recommendations
        )

# Convenience functions for external use
def validate_redis_infrastructure(project_root: Path = None) -> bool:
    """
    Validate Redis infrastructure deployment.
    
    Args:
        project_root: Path to project root directory
        
    Returns:
        bool: True if validation successful
    """
    validator = RedisDeploymentValidator(project_root)
    report = validator.generate_validation_report()
    return report.overall_status == "READY"

def generate_redis_deployment_report(project_root: Path = None) -> str:
    """
    Generate Redis deployment validation report.
    
    Args:
        project_root: Path to project root directory
        
    Returns:
        str: Formatted validation report
    """
    validator = RedisDeploymentValidator(project_root)
    report = validator.generate_validation_report()
    
    report_text = f"""
Redis Deployment Validation Report
==================================

Overall Status: {report.overall_status}
Timestamp: {report.timestamp.isoformat()}

Summary:
- Total Checks: {report.summary['total_checks']}
- Passed: {report.summary['passed_checks']}
- Failed: {report.summary['failed_checks']}
- Ready for Production: {report.summary['ready_for_production']}

Validation Results:
"""
    
    for check_name, result in report.validation_results.items():
        status_icon = "✅" if result.passed else "❌"
        report_text += f"\n{status_icon} {check_name.replace('_', ' ').title()}: {result.message}"
        if result.errors:
            for error in result.errors:
                report_text += f"\n   - {error}"
    
    report_text += "\n\nRecommendations:\n"
    for rec in report.recommendations:
        report_text += f"- {rec}\n"
    
    return report_text

if __name__ == "__main__":
    # Test Redis deployment validation
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🧪 Testing Redis deployment validation...")
    
    # Generate validation report
    report_text = generate_redis_deployment_report()
    print(report_text)
    
    # Check if validation passed
    if validate_redis_infrastructure():
        logger.info("✅ Redis infrastructure validation test successful")
    else:
        logger.error("❌ Redis infrastructure validation test failed")
